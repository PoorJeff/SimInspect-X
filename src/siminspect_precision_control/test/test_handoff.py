"""Test handoff manager: trigger conditions and failure recovery.

Tests verify handoff logic correctness via standalone logic extraction.
Full ROS integration tests require colcon + rclpy (not available on Windows).
"""
import math, sys, os

# ---------------------------------------------------------------------------
# Inline logic extraction -- mirrors HandoffManager._distance_to_target
# and _check_handoff without rclpy dependency.
# ---------------------------------------------------------------------------

HANDOFF_RADIUS_MULTIPLIER = 2.0
DESIRED_DISTANCE_M = 0.8
VELOCITY_THRESHOLD = 0.05

def _compute_distance(cx, cy, tx, ty):
    return math.hypot(cx - tx, cy - ty)

def _should_trigger_handoff(current_pose, target_pose, velocity,
                             desired_distance=DESIRED_DISTANCE_M,
                             radius_mult=HANDOFF_RADIUS_MULTIPLIER,
                             v_thresh=VELOCITY_THRESHOLD):
    if current_pose is None or target_pose is None:
        return False
    d = _compute_distance(current_pose[0], current_pose[1],
                          target_pose[0], target_pose[1])
    radius = radius_mult * desired_distance
    if d > radius:
        return False, "too_far"
    if abs(velocity[0]) > v_thresh:
        return False, "still_moving"
    return True, "ready"


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_distance_to_target():
    d = _compute_distance(1.0, 0.0, 5.0, 0.0)
    assert abs(d - 4.0) < 0.01, f"Expected 4.0, got {d}"

def test_no_handoff_when_far():
    ok, reason = _should_trigger_handoff((0.0, 0.0), (5.0, 0.0), (0.0, 0.0))
    assert not ok
    assert reason == "too_far"

def test_handoff_triggers_when_close():
    ok, reason = _should_trigger_handoff((4.0, 0.0), (5.0, 0.0), (0.0, 0.0))
    assert ok, f"Expected trigger when within 1.6m, got: {reason}"

def test_no_handoff_when_moving():
    ok, reason = _should_trigger_handoff((4.0, 0.0), (5.0, 0.0), (0.5, 0.0))
    assert not ok
    assert reason == "still_moving"

def test_approach_radius_calculation():
    radius = HANDOFF_RADIUS_MULTIPLIER * DESIRED_DISTANCE_M
    assert abs(radius - 1.6) < 0.01, f"Expected 1.6, got {radius}"

def test_distance_zero_at_target():
    d = _compute_distance(5.0, 0.0, 5.0, 0.0)
    assert d < 0.001

def test_velocity_at_threshold_allows_handoff():
    # |v|=0.05 is NOT > 0.05, so robot is considered stopped and handoff triggers
    ok, reason = _should_trigger_handoff(
        (4.0, 0.0), (5.0, 0.0), (VELOCITY_THRESHOLD, 0.0))
    assert ok, f"Velocity at threshold should allow handoff, got: {reason}"

def test_boundary_distance_just_inside():
    # distance = 1.6, radius = 1.6 => d > radius is False, triggers
    ok, reason = _should_trigger_handoff((3.4, 0.0), (5.0, 0.0), (0.0, 0.0))
    assert ok, f"Boundary check failed: {reason}"

def test_boundary_distance_just_outside():
    # distance = 1.61, radius = 1.6 => d > radius blocks
    ok, reason = _should_trigger_handoff((3.39, 0.0), (5.0, 0.0), (0.0, 0.0))
    assert not ok
    assert reason == "too_far"