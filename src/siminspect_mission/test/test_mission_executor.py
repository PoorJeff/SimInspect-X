"""Test mission executor state machine: transitions and bounded retries."""
import math, sys, os
from unittest.mock import MagicMock

# Mock ROS stack before importing mission_executor (Windows: no rclpy)
for mod in ["rclpy", "rclpy.node", "rclpy.action",
            "action_msgs", "action_msgs.msg",
            "nav2_msgs", "nav2_msgs.action",
            "geometry_msgs", "geometry_msgs.msg",
            "nav_msgs", "nav_msgs.msg",
            "std_msgs", "std_msgs.msg",
            "siminspect_interfaces", "siminspect_interfaces.msg",
            "siminspect_interfaces.action"]:
    sys.modules[mod] = MagicMock()

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "siminspect_mission"))
import mission_executor  # noqa: E402  (module ref for GoalStatus patch)
from mission_executor import (
    MissionStateMachine,
    S_IDLE, S_LOAD_MISSION, S_SELECT_ASSET, S_SELECT_VIEWPOINT, S_NAVIGATE,
    S_PRECISION_APPROACH, S_INSPECT, S_VALIDATE, S_RECORD, S_RETURN_HOME,
    S_EXPORT_REPORT, S_DONE,
    E_START, E_ASSETS_LOADED, E_VIEWPOINT_SELECTED, E_NAV_OK, E_NAV_FAIL,
    E_APPROACH_OK, E_APPROACH_FAIL, E_READING_RECEIVED, E_READING_VALID,
    E_READING_INVALID, E_RECORDED, E_HOME_REACHED, E_REPORT_EXPORTED,
    E_RETRY_VIEWPOINT, E_TICK,
    MAX_NAV_RETRIES, MAX_VIEWPOINT_ATTEMPTS, MAX_READER_RETRIES,
    handle_nav_fail, is_nav_success,
)

class FakeAsset:
    def __init__(self, id):
        self.id = id
        self.asset_type = "analog_gauge"

def _run_asset_flow(sm):
    """Drive one asset through the happy path."""
    sm.on_event(E_VIEWPOINT_SELECTED)
    sm.on_event(E_NAV_OK)
    sm.on_event(E_APPROACH_OK)
    sm.on_event(E_READING_RECEIVED)
    sm.on_event(E_READING_VALID)
    sm.on_event(E_RECORDED)

# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------

def test_full_mission_happy_path():
    sm = MissionStateMachine()
    assert sm.state == S_IDLE

    sm.on_event(E_START)
    assert sm.state == S_LOAD_MISSION

    sm.load_assets([FakeAsset("a1"), FakeAsset("a2")])
    assert sm.state == S_SELECT_ASSET

    # Asset 1
    sm.state = S_SELECT_VIEWPOINT
    _run_asset_flow(sm)
    assert sm.state == S_SELECT_ASSET

    # Asset 2
    sm.state = S_SELECT_VIEWPOINT
    _run_asset_flow(sm)
    assert sm.state == S_SELECT_ASSET

    # No more assets -> RETURN_HOME
    sm.asset_idx = 1
    sm.state = S_RETURN_HOME
    sm.on_event(E_HOME_REACHED)
    assert sm.state == S_EXPORT_REPORT
    sm.on_event(E_REPORT_EXPORTED)
    assert sm.state == S_DONE

def test_nav_retry_limit():
    """Nav failures should retry up to MAX_NAV_RETRIES then move to next viewpoint."""
    sm = MissionStateMachine()
    sm.state = S_NAVIGATE
    sm.nav_retries = 0

    for i in range(MAX_NAV_RETRIES - 1):
        sm.on_event(E_NAV_FAIL)
        assert sm.state == S_NAVIGATE, f"Retry {i}: should stay in NAVIGATE"

    sm.on_event(E_NAV_FAIL)
    assert sm.state == S_SELECT_VIEWPOINT, "Should move to next viewpoint after retries exhausted"
    assert sm.viewpoint_attempts == 1, "Nav exhaustion should consume a viewpoint attempt"

def test_nav_exhaustion_no_infinite_loop():
    """Sustained nav failure must not loop forever; it should exhaust viewpoints and move on."""
    sm = MissionStateMachine()
    sm.state = S_SELECT_VIEWPOINT
    sm.viewpoint_attempts = 0

    # Drive repeated nav failure cycles: SELECT_VIEWPOINT -> NAVIGATE -> (fail x2) -> ...
    for cycle in range(MAX_VIEWPOINT_ATTEMPTS):
        assert sm.state == S_SELECT_VIEWPOINT, f"Cycle {cycle}: should be at viewpoint selection"
        sm.on_event(E_VIEWPOINT_SELECTED)
        assert sm.state == S_NAVIGATE
        for _ in range(MAX_NAV_RETRIES):
            sm.on_event(E_NAV_FAIL)

    # After 3 viewpoint attempts all consumed, must record the failure (no loop)
    assert sm.state == S_RECORD, "Should record failure after viewpoints exhausted"
    assert sm.viewpoint_attempts == MAX_VIEWPOINT_ATTEMPTS
    assert sm.last_failure_reason == "nav_failed"
    sm.on_event(E_RECORDED)
    assert sm.state == S_SELECT_ASSET

def test_viewpoint_attempt_limit():
    """Approach failures should retry up to MAX_VIEWPOINT_ATTEMPTS."""
    sm = MissionStateMachine()
    sm.state = S_PRECISION_APPROACH
    sm.viewpoint_attempts = 0

    for i in range(MAX_VIEWPOINT_ATTEMPTS - 1):
        sm.on_event(E_APPROACH_FAIL)
        assert sm.state == S_SELECT_VIEWPOINT, f"Attempt {i}: should reselect viewpoint"
        sm.state = S_PRECISION_APPROACH

    sm.on_event(E_APPROACH_FAIL)
    assert sm.state == S_RECORD, "Should record failure after all viewpoint attempts exhausted"
    assert sm.last_failure_reason == "precision_failed"

def test_reader_retry_limit():
    """Invalid readings retry up to MAX_READER_RETRIES."""
    sm = MissionStateMachine()
    sm.state = S_VALIDATE
    sm.reader_retries = 0

    for i in range(MAX_READER_RETRIES - 1):
        sm.on_event(E_READING_INVALID)
        assert sm.state == S_INSPECT, f"Retry {i}: should re-inspect"
        sm.state = S_VALIDATE

    sm.on_event(E_READING_INVALID)
    assert sm.state in (S_SELECT_VIEWPOINT, S_RECORD)

def test_retry_viewpoint_event():
    """P7 retry signal should trigger viewpoint reselection."""
    sm = MissionStateMachine()
    sm.state = S_PRECISION_APPROACH
    sm.viewpoint_attempts = 0
    sm.on_event(E_RETRY_VIEWPOINT)
    assert sm.state == S_SELECT_VIEWPOINT
    assert sm.viewpoint_attempts == 1

def test_low_confidence_goes_to_record():
    sm = MissionStateMachine()
    sm.state = S_INSPECT
    sm.on_event(E_READING_RECEIVED)
    assert sm.state == S_VALIDATE
    sm.on_event(E_READING_VALID)
    assert sm.state == S_RECORD

def test_no_assets_returns_idle():
    sm = MissionStateMachine()
    sm.on_event(E_START)
    assert sm.state == S_LOAD_MISSION
    sm.load_assets([])
    assert sm.state == S_IDLE

def test_current_asset_tracking():
    sm = MissionStateMachine()
    sm.load_assets([FakeAsset("a1"), FakeAsset("a2")])
    sm.asset_idx = 0
    assert sm.current_asset().id == "a1"
    sm.asset_idx = 1
    assert sm.current_asset().id == "a2"
    sm.asset_idx = -1
    assert sm.current_asset() is None

def test_results_accumulate():
    sm = MissionStateMachine()
    sm.add_result({"asset_id": "a1", "status": "success"})
    sm.add_result({"asset_id": "a2", "status": "failed"})
    assert len(sm.results) == 2
    assert sm.results[0]["asset_id"] == "a1"
    assert sm.results[1]["status"] == "failed"
def test_five_asset_mission_flow():
    """>=5 assets full flow with E_TICK advancement."""
    sm = MissionStateMachine()
    sm.on_event(E_START)
    sm.load_assets([FakeAsset(f"a{i}") for i in range(1, 6)])
    assert sm.state == S_SELECT_ASSET
    assert len(sm.assets) == 5

    completed = 0
    while sm.state != S_RETURN_HOME:
        if sm.state == S_SELECT_ASSET:
            sm.on_event(E_TICK)
        elif sm.state == S_SELECT_VIEWPOINT:
            sm.on_event(E_VIEWPOINT_SELECTED)
        elif sm.state == S_NAVIGATE:
            sm.on_event(E_NAV_OK)
        elif sm.state == S_PRECISION_APPROACH:
            sm.on_event(E_APPROACH_OK)
        elif sm.state == S_INSPECT:
            sm.on_event(E_READING_RECEIVED)
        elif sm.state == S_VALIDATE:
            sm.on_event(E_READING_VALID)
        elif sm.state == S_RECORD:
            sm.add_result({"asset_id": sm.current_asset().id, "status": "success"})
            sm.on_event(E_RECORDED)
            completed += 1
        else:
            break

    assert completed == 5, f"All 5 assets should complete, got {completed}"
    assert sm.state == S_RETURN_HOME

def test_failure_reason_tracking():
    """Failure events set last_failure_reason with the schema enum value."""
    sm = MissionStateMachine()

    sm.state = S_NAVIGATE
    sm.on_event(E_NAV_FAIL)
    assert sm.last_failure_reason == "nav_failed"

    sm.state = S_PRECISION_APPROACH
    sm.on_event(E_APPROACH_FAIL)
    assert sm.last_failure_reason == "precision_failed"

    sm.state = S_PRECISION_APPROACH
    sm.on_event(E_RETRY_VIEWPOINT)
    assert sm.last_failure_reason == "precision_failed"

    sm.state = S_VALIDATE
    sm.on_event(E_READING_INVALID)
    assert sm.last_failure_reason == "low_confidence"


def test_failure_reason_reset_on_new_asset():
    """Advancing to a new asset clears the previous failure reason."""
    sm = MissionStateMachine()
    sm.on_event(E_START)
    sm.load_assets([FakeAsset("a1"), FakeAsset("a2")])
    sm.last_failure_reason = "nav_failed"

    sm.on_event(E_TICK)  # advance to asset a1
    assert sm.last_failure_reason is None


def test_nav_fail_resend_until_exhausted():
    """OI-008: node must re-send the goal while nav retry budget remains."""
    sm = MissionStateMachine()
    sm.state = S_NAVIGATE

    assert handle_nav_fail(sm) is True          # budget remains -> re-send
    assert sm.state == S_NAVIGATE
    assert sm.nav_retries == 1

    assert handle_nav_fail(sm) is False         # budget exhausted -> move on
    assert sm.state == S_SELECT_VIEWPOINT
    assert sm.nav_retries == 0                  # reset for next viewpoint
    assert sm.viewpoint_attempts == 1           # D-010 invariant preserved


def test_reader_exhaustion_consumes_viewpoint_attempts():
    """Three viewpoints x full reader budget -> RECORD with low_confidence."""
    sm = MissionStateMachine()
    for _ in range(MAX_VIEWPOINT_ATTEMPTS):
        sm.state = S_VALIDATE
        for _ in range(MAX_READER_RETRIES):
            sm.on_event(E_READING_INVALID)
            if sm.state == S_INSPECT:
                sm.on_event(E_READING_RECEIVED)   # next reading arrives

    assert sm.state == S_RECORD
    assert sm.viewpoint_attempts == MAX_VIEWPOINT_ATTEMPTS
    assert sm.last_failure_reason == "low_confidence"


def test_is_nav_success_mapping():
    """OI-010: nav success is decided by action goal status, not result fields."""
    mission_executor.GoalStatus.STATUS_SUCCEEDED = 4  # action_msgs/msg/GoalStatus
    assert is_nav_success(4) is True    # STATUS_SUCCEEDED
    assert is_nav_success(0) is False   # STATUS_UNKNOWN
    assert is_nav_success(5) is False   # STATUS_CANCELED
    assert is_nav_success(6) is False   # STATUS_ABORTED