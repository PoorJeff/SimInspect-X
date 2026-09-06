#!/usr/bin/env python3
"""PID controller for precision approach: dual-loop (position + heading) with safety."""
import math
from dataclasses import dataclass


@dataclass
class PIDGains:
    """Configurable PID gains with sensible defaults for precision approach."""
    kp_pos: float = 1.0
    ki_pos: float = 0.1
    kd_pos: float = 0.0
    kp_yaw: float = 2.0
    ki_yaw: float = 0.0
    kd_yaw: float = 0.5
    v_max: float = 0.5
    w_max: float = 1.5
    v_rate: float = 0.3
    w_rate: float = 1.0
    integral_max: float = 2.0       # anti-windup clamp on accumulated I term
    convergence_pos: float = 0.02    # metres
    convergence_yaw: float = 0.03    # radians
    steady_count: int = 10           # consecutive steps for convergence


class PIDController:
    """Dual-loop PID: linear loop (position error -> v) + angular loop (heading error -> w).

    Features:
      - output saturation (v_max, w_max)
      - rate limiting (v_rate, w_rate)
      - anti-windup (integral clamping)
      - convergence detection
    """

    def __init__(self, target_pose, gains=None):
        """Initialise with a target pose (x, y, yaw) in the map frame."""
        self.tx = target_pose[0]
        self.ty = target_pose[1]
        self.tyaw = target_pose[2]
        self.g = gains if gains is not None else PIDGains()

        # Internal state
        self.integral_pos = 0.0
        self.integral_yaw = 0.0
        self.prev_v = 0.0
        self.prev_w = 0.0
        self.prev_yaw_err = 0.0
        self.steady_ticks = 0
        self.elapsed_total = 0.0

    def reset(self):
        """Clear integral and rate state for a fresh approach."""
        self.integral_pos = 0.0
        self.integral_yaw = 0.0
        self.prev_v = 0.0
        self.prev_w = 0.0
        self.prev_yaw_err = 0.0
        self.steady_ticks = 0
        self.elapsed_total = 0.0

    def update(self, current_pose, dt):
        """Run one PID step.  Returns (v_cmd, w_cmd, pos_err, yaw_err, converged)."""
        cx, cy, cyaw = current_pose
        self.elapsed_total += dt

        # ---- positional error ----
        dx = self.tx - cx
        dy = self.ty - cy
        pos_err = math.hypot(dx, dy)

        # ---- yaw error (normalised) ----
        yaw_err = self.tyaw - cyaw
        yaw_err = math.atan2(math.sin(yaw_err), math.cos(yaw_err))

        # ---- linear velocity loop ----
        v_raw = self.g.kp_pos * pos_err + self.g.ki_pos * self.integral_pos
        v_clipped = max(-self.g.v_max, min(self.g.v_max, v_raw))

        # Anti-windup: only accumulate integral when not saturated
        if abs(v_raw) <= self.g.v_max:
            self.integral_pos += pos_err * dt
            self.integral_pos = max(-self.g.integral_max,
                                    min(self.g.integral_max, self.integral_pos))

        # Rate limit
        dv = v_clipped - self.prev_v
        dv = max(-self.g.v_rate * dt, min(self.g.v_rate * dt, dv))
        v_out = self.prev_v + dv
        self.prev_v = v_out

        # ---- angular velocity loop ----
        yaw_deriv = (yaw_err - self.prev_yaw_err) / dt if dt > 0 else 0.0
        self.prev_yaw_err = yaw_err

        w_raw = (self.g.kp_yaw * yaw_err
                 + self.g.ki_yaw * self.integral_yaw
                 + self.g.kd_yaw * yaw_deriv)
        w_clipped = max(-self.g.w_max, min(self.g.w_max, w_raw))

        if abs(w_raw) <= self.g.w_max:
            self.integral_yaw += yaw_err * dt
            self.integral_yaw = max(-self.g.integral_max,
                                    min(self.g.integral_max, self.integral_yaw))

        dw = w_clipped - self.prev_w
        dw = max(-self.g.w_rate * dt, min(self.g.w_rate * dt, dw))
        w_out = self.prev_w + dw
        self.prev_w = w_out

        # ---- convergence check ----
        if pos_err < self.g.convergence_pos and abs(yaw_err) < self.g.convergence_yaw:
            self.steady_ticks += 1
        else:
            self.steady_ticks = 0

        converged = self.steady_ticks >= self.g.steady_count

        return v_out, w_out, pos_err, yaw_err, converged