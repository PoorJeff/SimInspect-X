"""Test PID controller: convergence, saturation, anti-windup, rate limiting."""
import math, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "siminspect_precision_control"))
from pid_controller import PIDController, PIDGains


def _make_pid(target=(1.0, 0.0, 0.0), **kwargs):
    gains = PIDGains(**kwargs)
    return PIDController(target, gains=gains)


# ---------------------------------------------------------------------------
# Basic behaviour
# ---------------------------------------------------------------------------

def test_zero_error_gives_zero_output():
    pid = _make_pid(target=(0.0, 0.0, 0.0))
    v, w, err, yerr, _ = pid.update((0.0, 0.0, 0.0), 0.05)
    assert abs(v) < 1e-9, f"Expected zero v, got {v}"
    assert abs(w) < 1e-9, f"Expected zero w, got {w}"

def test_positive_position_error_gives_positive_v():
    pid = _make_pid(target=(1.0, 0.0, 0.0))
    v, w, err, yerr, _ = pid.update((0.0, 0.0, 0.0), 0.05)
    assert v > 0, f"Expected positive v, got {v}"
    assert err > 0

def test_heading_error_gives_correct_w():
    pid = _make_pid(target=(0.0, 0.0, math.pi / 4))
    v, w, err, yerr, _ = pid.update((0.0, 0.0, 0.0), 0.05)
    assert w > 0, f"Expected positive w for counter-clockwise turn, got {w}"
    assert abs(yerr - math.pi / 4) < 0.01

def test_heading_error_wraps_shortest_path():
    """-179 deg to +179 deg: shortest path is +2 deg (counter-clockwise)."""
    pid = _make_pid(target=(0.0, 0.0, -3.12))   # ~ -179 deg
    v, w, err, yerr, _ = pid.update((0.0, 0.0, 3.12), 0.05)  # ~ +179 deg
    # Shortest path from +179 to -179 is +2 deg (CCW), so w > 0
    assert w > 0, f"Shortest path is CCW, expected w>0, got {w}"
    assert abs(yerr - 0.043) < 0.01, f"Expected ~0.043 rad, got {yerr:.4f}"


# ---------------------------------------------------------------------------
# Saturation
# ---------------------------------------------------------------------------

def test_linear_saturation():
    pid = _make_pid(target=(100.0, 0.0, 0.0))
    v, w, _, _, _ = pid.update((0.0, 0.0, 0.0), 0.05)
    assert v <= 0.5 + 1e-6, f"Linear velocity saturated at 0.5, got {v}"

def test_angular_saturation():
    pid = _make_pid(target=(0.0, 0.0, math.pi))
    v, w, _, _, _ = pid.update((0.0, 0.0, 0.0), 0.05)
    assert abs(w) <= 1.5 + 1e-6, f"Angular velocity saturated at 1.5, got {w}"


# ---------------------------------------------------------------------------
# Anti-windup
# ---------------------------------------------------------------------------

def test_anti_windup_clamps_integral():
    """Integral should not exceed integral_max even after sustained error."""
    pid = _make_pid(target=(100.0, 0.0, 0.0))
    for _ in range(200):
        pid.update((0.0, 0.0, 0.0), 0.05)
    assert abs(pid.integral_pos) <= 2.0 + 1e-6, \
        f"Integral clamped at 2.0, got {pid.integral_pos}"

def test_integral_decays_when_close():
    """Integral should not grow unboundedly even when unsaturated."""
    pid = _make_pid(target=(0.3, 0.0, 0.0))
    for _ in range(100):
        pid.update((0.0, 0.0, 0.0), 0.05)
    assert abs(pid.integral_pos) < 2.0, "Integral should be bounded"


# ---------------------------------------------------------------------------
# Rate limiting
# ---------------------------------------------------------------------------

def test_rate_limiting_prevents_jump():
    pid = _make_pid(target=(5.0, 0.0, 0.0))
    v1, _, _, _, _ = pid.update((0.0, 0.0, 0.0), 0.05)
    assert v1 <= 0.3 * 0.05 + 1e-6, f"Rate limited: v1 <= 0.015, got {v1}"
    v2, _, _, _, _ = pid.update((0.0, 0.0, 0.0), 0.05)
    assert v1 <= v2 <= 2 * 0.3 * 0.05 + 1e-6, "Rate limited step 2"


# ---------------------------------------------------------------------------
# Convergence
# ---------------------------------------------------------------------------

def test_converges_to_target():
    """Simulate robot approaching target from (0,0) to (1,0)."""
    pid = _make_pid(target=(1.0, 0.0, 0.0))
    x, y, yaw = 0.0, 0.0, 0.0
    converged = False
    for step in range(500):
        v, w, pos_err, yaw_err, converged = pid.update((x, y, yaw), 0.05)
        x += v * math.cos(yaw) * 0.05
        y += v * math.sin(yaw) * 0.05
        yaw += w * 0.05
        if converged:
            break
    assert converged, "Controller did not converge within 500 steps"

def test_convergence_at_target():
    """Staying at target for steady_count steps triggers convergence."""
    pid = _make_pid(target=(0.0, 0.0, 0.0))
    for _ in range(10):
        v, w, err, yerr, c = pid.update((0.0, 0.0, 0.0), 0.05)
    assert c, f"Should converge after 10 steps at target, got {c}"


# ---------------------------------------------------------------------------
# Reset
# ---------------------------------------------------------------------------

def test_reset_clears_state():
    pid = _make_pid(target=(1.0, 0.0, 0.0))
    pid.update((0.0, 0.0, 0.0), 0.05)
    pid.reset()
    assert abs(pid.integral_pos) < 1e-9
    assert abs(pid.prev_v) < 1e-9
    assert abs(pid.prev_w) < 1e-9