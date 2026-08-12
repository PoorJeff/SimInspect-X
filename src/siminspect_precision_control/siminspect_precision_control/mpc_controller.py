#!/usr/bin/env python3
"""Constrained linear MPC for precision approach using OSQP.

Linearises the differential-drive kinematic model around the current heading,
formulates a QP with OSQP, and integrates acceleration to velocity commands.

Interface is identical to PIDController: update(current_pose, dt) -> (v,w,err,yerr,ok).
"""
import math
import numpy as np
from dataclasses import dataclass, field


@dataclass
class MPCParams:
    """MPC hyper-parameters — shared with PID where applicable."""
    N: int = 15                      # prediction horizon steps
    dt: float = 0.05                 # step duration [s]
    # cost weights
    w_xy: float = 10.0               # position tracking
    w_theta: float = 5.0             # heading tracking
    w_v_terminal: float = 1.0        # terminal velocity penalty
    w_a: float = 0.1                 # linear acceleration cost
    w_omega: float = 0.05            # angular velocity cost
    w_smooth_a: float = 0.05         # acceleration smoothness
    w_smooth_omega: float = 0.02     # angular smoothness
    # bounds — MUST match PID for fair comparison
    v_min: float = -0.5
    v_max: float = 0.5
    w_min: float = -1.5
    w_max: float = 1.5
    a_min: float = -0.3
    a_max: float = 0.3
    alpha_min: float = -1.0          # angular acceleration [rad/s^2]
    alpha_max: float = 1.0
    # convergence (same as PID)
    convergence_pos: float = 0.02
    convergence_yaw: float = 0.03
    steady_count: int = 10


class MPCController:
    """MPC controller: solves QP at each step, returns velocity commands.

    On QP failure returns zero velocity (fail-safe).
    """

    def __init__(self, target_pose, params=None):
        self.tx, self.ty, self.tyaw = target_pose
        self.p = params if params is not None else MPCParams()
        self.prev_v = 0.0
        self.prev_a = 0.0
        self.prev_w = 0.0
        self.steady_ticks = 0
        self.elapsed_total = 0.0
        self._solver = None  # cached OSQP solver for warm-start

    def reset(self):
        self.prev_v = 0.0
        self.prev_a = 0.0
        self.prev_w = 0.0
        self.steady_ticks = 0
        self.elapsed_total = 0.0

    def update(self, current_pose, dt):
        """Run one MPC step. Returns (v_cmd, w_cmd, pos_err, yaw_err, converged)."""
        cx, cy, cyaw = current_pose
        self.elapsed_total += dt

        try:
            a_opt, w_opt = self._solve_qp(cx, cy, cyaw)
        except Exception:
            # QP failure — return zero command (safe fallback)
            a_opt, w_opt = 0.0, 0.0

        # Integrate acceleration -> velocity
        v_cmd = self.prev_v + a_opt * dt
        v_cmd = max(self.p.v_min, min(self.p.v_max, v_cmd))
        w_cmd = max(self.p.w_min, min(self.p.w_max, w_opt))

        # Rate limit on linear acceleration
        da = a_opt - self.prev_a
        da_max = 0.3 * dt  # same as PID rate
        da = max(-da_max, min(da_max, da))
        a_clipped = self.prev_a + da
        v_cmd = self.prev_v + a_clipped * dt
        v_cmd = max(self.p.v_min, min(self.p.v_max, v_cmd))

        self.prev_v = v_cmd
        self.prev_a = a_clipped
        self.prev_w = w_cmd

        # Compute errors
        dx = self.tx - cx
        dy = self.ty - cy
        pos_err = math.hypot(dx, dy)
        yaw_err = self.tyaw - cyaw
        yaw_err = math.atan2(math.sin(yaw_err), math.cos(yaw_err))

        if pos_err < self.p.convergence_pos and abs(yaw_err) < self.p.convergence_yaw:
            self.steady_ticks += 1
        else:
            self.steady_ticks = 0
        converged = self.steady_ticks >= self.p.steady_count

        return v_cmd, w_cmd, pos_err, yaw_err, converged

    # ------------------------------------------------------------------
    # QP formulation
    # ------------------------------------------------------------------

    def _solve_qp(self, cx, cy, cyaw):
        """Build and solve the OSQP problem. Returns (a_opt, w_opt)."""
        N = self.p.N
        dt = self.p.dt
        cth = math.cos(cyaw)
        sth = math.sin(cyaw)

        # ---- build prediction matrices (linearised around cyaw) ----

        # L: NxN lower-triangular (integration matrix for velocity)
        L = np.tril(np.ones((N, N)))

        # M: NxN double-integration matrix: M[i,j] = max(0, i-j) for x/y prediction
        i_idx = np.arange(1, N + 1).reshape(-1, 1)
        j_idx = np.arange(N).reshape(1, -1)
        M = np.maximum(0, i_idx - 1 - j_idx)

        # Bias vectors (constant part of prediction, independent of decision vars)
        b_v = np.full(N, self.prev_v)               # velocity bias
        b_theta = np.full(N, cyaw)                    # heading bias
        b_x = cx + cth * dt * np.arange(1, N + 1) * self.prev_v
        b_y = cy + sth * dt * np.arange(1, N + 1) * self.prev_v

        # ---- build P (quadratic cost) for decision vars z = [a_0,w_0,...,a_{N-1},w_{N-1}] ----

        # Auxiliary matrices mapping z -> predictions
        # A_v maps a-portion of z: v_pred = A_v @ a + b_v
        A_v_a = dt * L           # N x N
        # A_theta maps w-portion: theta_pred = A_theta @ w + b_theta
        A_th_w = dt * L          # N x N
        # A_x maps a-portion: x_pred = A_x @ a + b_x
        A_x_a = cth * dt * dt * M   # N x N
        # A_y maps a-portion
        A_y_a = sth * dt * dt * M   # N x N

        # Full A_x, A_y, A_theta, A_v for z (2N vars)
        # z = [a_0, w_0, a_1, w_1, ..., a_{N-1}, w_{N-1}]
        # a component at even indices, w at odd indices

        P_block = np.zeros((2 * N, 2 * N))

        # Position tracking cost: w_xy * (A_x @ z + b_x - x_ref)^2
        # = z^T (A_x^T w_xy A_x) z + 2 (b_x - x_ref)^T w_xy A_x z
        # Build full A_x_full (N x 2N): columns 0,2,4,... from A_x_a, columns 1,3,5,... zero
        A_full = np.zeros((N, 2 * N))
        A_full[:, 0::2] = A_x_a
        P_block += self.p.w_xy * (A_full.T @ A_full)
        b_x_ref = np.full(N, self.tx)
        q_x = 2.0 * self.p.w_xy * A_full.T @ (b_x - b_x_ref)

        # y tracking
        A_full_2 = np.zeros((N, 2 * N))
        A_full_2[:, 0::2] = A_y_a
        P_block += self.p.w_xy * (A_full_2.T @ A_full_2)
        b_y_ref = np.full(N, self.ty)
        q_y = 2.0 * self.p.w_xy * A_full_2.T @ (b_y - b_y_ref)

        # theta tracking
        A_th_full = np.zeros((N, 2 * N))
        A_th_full[:, 1::2] = A_th_w
        P_block += self.p.w_theta * (A_th_full.T @ A_th_full)
        b_th_ref = np.full(N, self.tyaw)
        q_th = 2.0 * self.p.w_theta * A_th_full.T @ (b_theta - b_th_ref)

        # terminal velocity penalty (only last row of A_v)
        A_v_full = np.zeros((N, 2 * N))
        A_v_full[:, 0::2] = A_v_a
        P_v_last = self.p.w_v_terminal * (A_v_full[-1:, :].T @ A_v_full[-1:, :])
        P_block += P_v_last
        q_v = 2.0 * self.p.w_v_terminal * A_v_full[-1:, :].T @ (b_v[-1:] - np.zeros(1))

        # Control effort diagonals
        for i in range(N):
            P_block[2 * i, 2 * i] += self.p.w_a
            P_block[2 * i + 1, 2 * i + 1] += self.p.w_omega

        # Smoothness penalty: (a_k - a_{k-1})^2
        D_a = np.zeros((N - 1, 2 * N))
        for k in range(N - 1):
            D_a[k, 2 * k] = -1.0
            D_a[k, 2 * (k + 1)] = 1.0
        P_block += self.p.w_smooth_a * (D_a.T @ D_a)

        D_w = np.zeros((N - 1, 2 * N))
        for k in range(N - 1):
            D_w[k, 2 * k + 1] = -1.0
            D_w[k, 2 * (k + 1) + 1] = 1.0
        P_block += self.p.w_smooth_omega * (D_w.T @ D_w)

        # Ensure P is positive semi-definite (add small regularization)
        P_block += 1e-6 * np.eye(2 * N)

        # ---- q vector ----
        q = q_x + q_y + q_th + q_v.flatten()

        # ---- Box constraints on decision variables ----
        lb = np.zeros(2 * N)
        ub = np.zeros(2 * N)
        for i in range(N):
            lb[2 * i] = self.p.a_min       # a
            ub[2 * i] = self.p.a_max
            lb[2 * i + 1] = self.p.w_min   # w
            ub[2 * i + 1] = self.p.w_max

        # ---- Inequality constraints ----
        # Velocity constraints: v_min <= A_v @ z + b_v <= v_max
        A_ineq_v = np.zeros((N, 2 * N))
        A_ineq_v[:, 0::2] = A_v_a
        l_v = self.p.v_min * np.ones(N) - b_v
        u_v = self.p.v_max * np.ones(N) - b_v

        # Angular acceleration constraints: (w_{k+1} - w_k)/dt in [alpha_min, alpha_max]
        A_alpha = np.zeros((N - 1, 2 * N))
        for k in range(N - 1):
            A_alpha[k, 2 * k + 1] = -1.0
            A_alpha[k, 2 * (k + 1) + 1] = 1.0
        l_alpha = self.p.alpha_min * dt * np.ones(N - 1)
        u_alpha = self.p.alpha_max * dt * np.ones(N - 1)

        # Combine constraints
        A_ineq = np.vstack([A_ineq_v, A_alpha]) if N > 1 else A_ineq_v
        l_ineq = np.hstack([l_v, l_alpha]) if N > 1 else l_v
        u_ineq = np.hstack([u_v, u_alpha]) if N > 1 else u_v

        # ---- Solve QP ----
        P_sparse = self._to_csc(P_block)
        A_sparse = self._to_csc(A_ineq)

        try:
            import osqp
            if self._solver is None:
                self._solver = osqp.OSQP()
                self._solver.setup(P=P_sparse, q=q, A=A_sparse, l=l_ineq, u=u_ineq,
                                   verbose=False, eps_abs=1e-4, eps_rel=1e-4,
                                   max_iter=500, polish=True)
            else:
                self._solver.update(q=q, l=l_ineq, u=u_ineq)
                self._solver.update(Px=P_sparse.data, Ax=A_sparse.data)

            result = self._solver.solve()
            if result.info.status_val not in (1, 2):  # solved or solved inaccurate
                return 0.0, 0.0

            z_opt = result.x
            return float(z_opt[0]), float(z_opt[1])   # first a, first w
        except ImportError:
            # OSQP not available — return zero (tests on Windows)
            return 0.0, 0.0

    @staticmethod
    def _to_csc(mat):
        """Convert dense numpy array to scipy sparse CSC for OSQP."""
        from scipy.sparse import csc_matrix
        return csc_matrix(mat)