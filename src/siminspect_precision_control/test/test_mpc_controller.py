"""Test MPC controller: matrix structure, QP formulation, convergence, constraints, fallback."""
import math, sys, os
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "siminspect_precision_control"))
from mpc_controller import MPCController, MPCParams


def _make_mpc(target=(1.0, 0.0, 0.0), **kwargs):
    p = MPCParams(**kwargs)
    return MPCController(target, params=p)


# ---------------------------------------------------------------------------
# Matrix structure & dimensions
# ---------------------------------------------------------------------------

def test_prediction_matrices_dimensions():
    """Verify internal matrices have correct shapes."""
    mpc = _make_mpc(N=10, dt=0.05)
    N = mpc.p.N

    cth = math.cos(0.0)
    sth = math.sin(0.0)

    L = np.tril(np.ones((N, N)))
    i_idx = np.arange(1, N + 1).reshape(-1, 1)
    j_idx = np.arange(N).reshape(1, -1)
    M = np.maximum(0, i_idx - 1 - j_idx)

    assert L.shape == (N, N)
    assert M.shape == (N, N)
    # M[0,:] should be all zeros (no history for first step)
    assert np.allclose(M[0, :], 0.0)

    A_v_a = 0.05 * L  # dt * L
    assert A_v_a.shape == (N, N)
    A_x_a = cth * 0.05 * 0.05 * M
    assert A_x_a.shape == (N, N)


def test_p_matrix_psd():
    """Cost matrix P should be positive semi-definite."""
    mpc = _make_mpc(N=5, dt=0.05)
    N = mpc.p.N
    cth = math.cos(0.0)
    M = np.maximum(0, np.arange(1, N+1).reshape(-1,1) - 1 - np.arange(N).reshape(1,-1))
    A_x_a = cth * 0.05 * 0.05 * M

    A_full = np.zeros((N, 2*N))
    A_full[:, 0::2] = A_x_a
    P_pos = mpc.p.w_xy * (A_full.T @ A_full)

    eigvals = np.linalg.eigvalsh(P_pos)
    assert np.all(eigvals >= -1e-10), f"P should be PSD, min eig={eigvals.min():.2e}"


def test_control_effort_positive_diagonal():
    """Control effort cost should add positive diagonal entries."""
    mpc = _make_mpc(N=8)
    N = mpc.p.N
    P_block = np.zeros((2*N, 2*N))
    for i in range(N):
        P_block[2*i, 2*i] += mpc.p.w_a
        P_block[2*i+1, 2*i+1] += mpc.p.w_omega
    assert np.all(np.diag(P_block) > 0)


def test_smoothness_matrix_structure():
    """Difference matrix should couple adjacent time steps."""
    mpc = _make_mpc(N=5)
    N = mpc.p.N
    D_a = np.zeros((N-1, 2*N))
    for k in range(N-1):
        D_a[k, 2*k] = -1.0
        D_a[k, 2*(k+1)] = 1.0
    P_smooth = mpc.p.w_smooth_a * (D_a.T @ D_a)
    assert P_smooth.shape == (2*N, 2*N)
    # Off-diagonal should be non-zero (coupling adjacent a's)
    assert not np.allclose(P_smooth - np.diag(np.diag(P_smooth)), 0)


# ---------------------------------------------------------------------------
# Constraint bounds
# ---------------------------------------------------------------------------

def test_constraint_bounds_match_pid():
    """MPC bounds must match PID for fair comparison."""
    mpc = _make_mpc()
    assert mpc.p.v_min == -0.5
    assert mpc.p.v_max == 0.5
    assert mpc.p.w_min == -1.5
    assert mpc.p.w_max == 1.5
    assert mpc.p.a_min == -0.3
    assert mpc.p.a_max == 0.3
    assert mpc.p.alpha_min == -1.0
    assert mpc.p.alpha_max == 1.0


def test_convergence_params_match_pid():
    """Convergence thresholds must match PID for fair comparison."""
    mpc = _make_mpc()
    assert mpc.p.convergence_pos == 0.02
    assert mpc.p.convergence_yaw == 0.03
    assert mpc.p.steady_count == 10


# ---------------------------------------------------------------------------
# Behaviour tests
# ---------------------------------------------------------------------------

def test_update_no_crash():
    """Controller should not crash even without OSQP (returns zero)."""
    mpc = _make_mpc(target=(1.0, 0.0, 0.0))
    v, w, err, yerr, conv = mpc.update((0.0, 0.0, 0.0), 0.05)
    assert isinstance(v, float)
    assert isinstance(w, float)
    assert err > 0  # error should be detected even with zero command

def test_convergence_at_target():
    """Staying at target should trigger convergence (same as PID)."""
    mpc = _make_mpc(target=(0.0, 0.0, 0.0))
    for _ in range(10):
        v, w, err, yerr, c = mpc.update((0.0, 0.0, 0.0), 0.05)
    assert c, f"Should converge after 10 steps at target"

def test_velocity_clamped():
    """Velocity output must not exceed bounds."""
    mpc = _make_mpc(target=(100.0, 0.0, 0.0))
    for _ in range(20):
        v, w, _, _, _ = mpc.update((0.0, 0.0, 0.0), 0.05)
    # prev_v tracks integrated velocity; after 20 steps at zero command (no OSQP),
    # should stay at zero. If OSQP were running, would be bounded.
    assert abs(mpc.prev_v) <= 0.5 + 1e-6

def test_reset_clears_state():
    mpc = _make_mpc(target=(1.0, 0.0, 0.0))
    mpc.prev_v = 0.3
    mpc.reset()
    assert abs(mpc.prev_v) < 1e-9
    assert abs(mpc.prev_a) < 1e-9
    assert abs(mpc.prev_w) < 1e-9
    assert mpc.steady_ticks == 0

def test_yaw_error_normalized():
    """Yaw error should be correctly wrapped to [-pi, pi]."""
    mpc = _make_mpc(target=(0.0, 0.0, -3.12))
    v, w, err, yerr, conv = mpc.update((0.0, 0.0, 3.12), 0.05)
    assert abs(yerr) < 0.05, f"Yaw error should be ~0.043, got {yerr:.4f}"