"""Test mission executor state machine and ROS-facing control contract."""
import importlib.util
import json
from enum import Enum
import math
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
from unittest.mock import patch


class FakeLogger:
    def info(self, _msg):
        pass

    def warn(self, _msg):
        pass

    def error(self, _msg):
        pass


class FakePublisher:
    def __init__(self):
        self.messages = []

    def publish(self, msg):
        self.messages.append(msg)


class FakeClock:
    class _Now:
        def to_msg(self):
            return SimpleNamespace(sec=123, nanosec=456)

    def now(self):
        return self._Now()


class FakeNode:
    parameter_overrides = {}

    def __init__(self, _name):
        self._parameters = {}
        self._logger = FakeLogger()
        self.declare_parameter_calls = []
        self.subscriptions = []
        self.publishers = []
        self.timers = []

    def declare_parameter(self, name, default):
        self.declare_parameter_calls.append((name, default))
        if isinstance(default, FakeParameter.Type):
            value = self.parameter_overrides.get(name)
        else:
            value = self.parameter_overrides.get(name, default)
        self._parameters[name] = value
        return SimpleNamespace(value=value, type_=default)

    def get_parameter(self, name):
        return SimpleNamespace(value=self._parameters[name])

    def create_subscription(self, msg_type, topic, callback, qos):
        subscription = SimpleNamespace(
            msg_type=msg_type, topic=topic, callback=callback, qos=qos)
        self.subscriptions.append(subscription)
        return subscription

    def create_publisher(self, msg_type, topic, qos):
        publisher = FakePublisher()
        publisher.msg_type = msg_type
        publisher.topic = topic
        publisher.qos = qos
        self.publishers.append(publisher)
        return publisher

    def create_timer(self, period, callback):
        timer = SimpleNamespace(period=period, callback=callback)
        self.timers.append(timer)
        return timer

    def get_logger(self):
        return self._logger

    def get_clock(self):
        return FakeClock()


class FakeActionClient:
    def __init__(self, _node, action_type, action_name):
        self.action_type = action_type
        self.action_name = action_name
        self.server_available = True
        self.sent_goals = []
        self.goal_futures = []

    def wait_for_server(self, timeout_sec=None):
        return self.server_available

    def send_goal_async(self, goal):
        future = DeferredFuture()
        self.sent_goals.append(goal)
        self.goal_futures.append(future)
        return future


class FakeParameter:
    class Type(Enum):
        STRING_ARRAY = 9


class FakeQoSProfile:
    def __init__(self, *, depth, reliability, durability):
        self.depth = depth
        self.reliability = reliability
        self.durability = durability


class FakeReliabilityPolicy(Enum):
    RELIABLE = 1


class FakeDurabilityPolicy(Enum):
    TRANSIENT_LOCAL = 1


class FakePoseStamped:
    def __init__(self):
        self.header = SimpleNamespace(frame_id="", stamp=None)
        self.pose = SimpleNamespace(
            position=SimpleNamespace(x=0.0, y=0.0, z=0.0),
            orientation=SimpleNamespace(x=0.0, y=0.0, z=0.0, w=1.0),
        )


class FakeMissionState:
    def __init__(self):
        self.state = ""
        self.current_asset_id = ""
        self.attempt = 0
        self.viewpoint_index = 0
        self.request_id = 0
        self.timestamp = None


class FakeNavigateToPose:
    class Goal:
        def __init__(self):
            self.pose = None


class FakePrecisionApproach:
    class Goal:
        def __init__(self):
            self.target_pose = None
            self.max_linear_vel = 0.0
            self.max_angular_vel = 0.0
            self.timeout_s = 0.0


class FakeGoalStatus:
    STATUS_SUCCEEDED = 4
    STATUS_CANCELED = 5
    STATUS_ABORTED = 6


def _module(name, **attrs):
    module = ModuleType(name)
    for key, value in attrs.items():
        setattr(module, key, value)
    return module


def _load_mission_executor():
    """Import with scoped ROS stubs so later test files see a clean sys.modules."""
    stubs = {
        "rclpy": _module("rclpy", init=lambda: None, spin=lambda _node: None,
                          shutdown=lambda: None),
        "rclpy.node": _module("rclpy.node", Node=FakeNode),
        "rclpy.action": _module("rclpy.action", ActionClient=FakeActionClient),
        "rclpy.parameter": _module("rclpy.parameter", Parameter=FakeParameter),
        "rclpy.qos": _module(
            "rclpy.qos",
            QoSProfile=FakeQoSProfile,
            ReliabilityPolicy=FakeReliabilityPolicy,
            DurabilityPolicy=FakeDurabilityPolicy,
        ),
        "action_msgs": _module("action_msgs"),
        "action_msgs.msg": _module("action_msgs.msg", GoalStatus=FakeGoalStatus),
        "nav2_msgs": _module("nav2_msgs"),
        "nav2_msgs.action": _module(
            "nav2_msgs.action", NavigateToPose=FakeNavigateToPose),
        "geometry_msgs": _module("geometry_msgs"),
        "geometry_msgs.msg": _module(
            "geometry_msgs.msg", PoseStamped=FakePoseStamped),
        "nav_msgs": _module("nav_msgs"),
        "nav_msgs.msg": _module("nav_msgs.msg", Odometry=type("Odometry", (), {})),
        "std_msgs": _module("std_msgs"),
        "std_msgs.msg": _module(
            "std_msgs.msg", String=type("String", (), {"data": ""})),
        "siminspect_interfaces": _module("siminspect_interfaces"),
        "siminspect_interfaces.msg": _module(
            "siminspect_interfaces.msg",
            AssetArray=type("AssetArray", (), {}),
            GaugeReading=type("GaugeReading", (), {}),
            MissionState=FakeMissionState,
        ),
        "siminspect_interfaces.action": _module(
            "siminspect_interfaces.action", PrecisionApproach=FakePrecisionApproach),
    }
    package_dir = Path(__file__).resolve().parents[1] / "siminspect_mission"
    if str(package_dir) not in sys.path:
        sys.path.insert(0, str(package_dir))
    module_path = package_dir / "mission_executor.py"
    spec = importlib.util.spec_from_file_location(
        "mission_executor_contract_under_test", module_path)
    module = importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules, stubs):
        spec.loader.exec_module(module)
    return module


mission_executor = _load_mission_executor()
_EXPORTED_NAMES = (
    "MissionExecutor", "MissionStateMachine",
    "S_IDLE", "S_LOAD_MISSION", "S_SELECT_ASSET", "S_SELECT_VIEWPOINT",
    "S_NAVIGATE", "S_PRECISION_APPROACH", "S_INSPECT", "S_VALIDATE",
    "S_RECORD", "S_RETURN_HOME", "S_EXPORT_REPORT", "S_DONE",
    "E_START", "E_ASSETS_LOADED", "E_VIEWPOINT_SELECTED", "E_NAV_OK",
    "E_NAV_FAIL", "E_APPROACH_OK", "E_APPROACH_FAIL",
    "E_READING_RECEIVED", "E_READING_VALID", "E_READING_INVALID",
    "E_RECORDED", "E_HOME_REACHED", "E_REPORT_EXPORTED",
    "E_RETRY_VIEWPOINT", "E_TICK", "MAX_NAV_RETRIES",
    "MAX_VIEWPOINT_ATTEMPTS", "MAX_READER_RETRIES", "handle_nav_fail",
    "is_nav_success",
)
globals().update({name: getattr(mission_executor, name) for name in _EXPORTED_NAMES})

class FakeAsset:
    def __init__(self, id):
        self.id = id
        self.asset_type = "analog_gauge"


def _make_executor(**parameter_overrides):
    FakeNode.parameter_overrides = dict(parameter_overrides)
    try:
        return MissionExecutor()
    finally:
        FakeNode.parameter_overrides = {}


def _reading(asset_id, confidence=0.9):
    return SimpleNamespace(
        asset_id=asset_id,
        estimated_value=42.0,
        confidence=confidence,
    )


class DeferredFuture:
    def __init__(self):
        self._done = False
        self._value = None
        self._callbacks = []

    def result(self):
        assert self._done, "future result requested before completion"
        return self._value

    def add_done_callback(self, callback):
        if self._done:
            callback(self)
        else:
            self._callbacks.append(callback)

    def set_result(self, value):
        assert not self._done, "future completed twice"
        self._done = True
        self._value = value
        callbacks = list(self._callbacks)
        self._callbacks.clear()
        for callback in callbacks:
            callback(self)


class FakeGoalHandle:
    def __init__(self, accepted, *, defer_cancel=False):
        self.accepted = accepted
        self.result_future = DeferredFuture()
        self.cancel_future = DeferredFuture()
        self.cancel_calls = 0
        if not defer_cancel:
            self.cancel_future.set_result(SimpleNamespace())

    def get_result_async(self):
        return self.result_future

    def cancel_goal_async(self):
        self.cancel_calls += 1
        return self.cancel_future


def _action_result(status, *, precision_success=None):
    result = None
    if precision_success is not None:
        result = SimpleNamespace(success=precision_success)
    return SimpleNamespace(status=status, result=result)


def _odom(x, y, yaw=0.0):
    return SimpleNamespace(
        pose=SimpleNamespace(
            pose=SimpleNamespace(
                position=SimpleNamespace(x=x, y=y),
                orientation=SimpleNamespace(
                    z=math.sin(yaw / 2.0), w=math.cos(yaw / 2.0)),
            )
        )
    )

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


def test_valid_final_reading_clears_recovered_attempt_failure():
    sm = MissionStateMachine()
    sm.state = S_VALIDATE
    sm.last_failure_reason = "nav_failed"

    sm.on_event(E_READING_VALID)

    assert sm.state == S_RECORD
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


# ---------------------------------------------------------------------------
# Demo mission control contract (Plan 02, Task 1)
# ---------------------------------------------------------------------------

def test_request_id_increments_each_time_select_viewpoint_is_entered():
    sm = MissionStateMachine()
    sm.on_event(E_START)
    sm.load_assets([FakeAsset("a1")])

    sm.on_event(E_TICK)
    assert sm.state == S_SELECT_VIEWPOINT
    assert sm.request_id == 1

    sm.on_event(E_VIEWPOINT_SELECTED)
    for _ in range(MAX_NAV_RETRIES):
        sm.on_event(E_NAV_FAIL)
    assert sm.state == S_SELECT_VIEWPOINT
    assert sm.request_id == 2


def test_duplicate_asset_inventory_does_not_reset_current_asset():
    node = _make_executor(expected_asset_ids=["a1", "a2"])
    inventory = SimpleNamespace(assets=[FakeAsset("a1"), FakeAsset("a2")])
    node._cb_assets(inventory)
    node.sm.on_event(E_TICK)
    assert node.sm.asset_idx == 0
    assert node.sm.current_asset().id == "a1"

    node._cb_assets(inventory)

    assert node.sm.asset_idx == 0
    assert node.sm.current_asset().id == "a1"
    assert node.sm.state == S_SELECT_VIEWPOINT


def test_inventory_must_match_expected_asset_ids_before_load():
    node = _make_executor(expected_asset_ids=["a1", "a2"])

    node._cb_assets(SimpleNamespace(assets=[FakeAsset("a1")]))
    assert node.sm.state == S_LOAD_MISSION
    assert node.sm.assets == []

    node._cb_assets(SimpleNamespace(assets=[FakeAsset("a1"), FakeAsset("a2")]))
    assert node.sm.state == S_SELECT_ASSET
    assert [asset.id for asset in node.sm.assets] == ["a1", "a2"]


def test_reading_for_wrong_asset_is_ignored():
    node = _make_executor()
    node.sm.assets = [FakeAsset("a1")]
    node.sm.asset_idx = 0
    node.sm.state = S_INSPECT

    node._cb_reading(_reading("a2"))

    assert node.current_reading is None
    assert node.sm.state == S_INSPECT


def test_matching_reading_is_accepted_only_while_inspecting():
    node = _make_executor()
    node.sm.assets = [FakeAsset("a1")]
    node.sm.asset_idx = 0
    node.sm.state = S_NAVIGATE
    node._cb_reading(_reading("a1"))
    assert node.current_reading is None

    node.sm.state = S_INSPECT
    node.asset_viewpoints = ["v1"]
    node._cb_reading(_reading("a1", confidence=0.75))
    assert node.current_reading.asset_id == "a1"
    assert node.sm.state == S_VALIDATE


def test_published_mission_state_includes_request_and_timestamp():
    node = _make_executor()
    node.sm.assets = [FakeAsset("a1")]
    node.sm.asset_idx = 0
    node.sm.state = S_SELECT_VIEWPOINT
    node.sm.request_id = 7

    node._publish_state()

    msg = node._mission_pub.messages[-1]
    assert msg.current_asset_id == "a1"
    assert msg.request_id == 7
    assert (msg.timestamp.sec, msg.timestamp.nanosec) == (123, 456)


def test_viewpoint_request_stamps_are_unique_when_ros_clock_is_constant():
    node = _make_executor()
    node.sm.state = S_SELECT_VIEWPOINT
    node.sm.request_id = 1
    node._publish_state()
    first = node._mission_pub.messages[-1].timestamp

    node.sm.request_id = 2
    node._publish_state()
    second = node._mission_pub.messages[-1].timestamp

    assert (first.sec, first.nanosec) == (123, 456)
    assert (second.sec, second.nanosec) == (123, 457)

    stale = FakePoseStamped()
    stale.header.stamp = first
    node._cb_viewpoint(stale)
    assert node.sm.state == S_SELECT_VIEWPOINT
    assert node.selected_viewpoint is None


def test_expected_asset_ids_uses_explicit_string_array_parameter_type():
    node = _make_executor()

    declaration = next(
        default for name, default in node.declare_parameter_calls
        if name == "expected_asset_ids")

    assert declaration is FakeParameter.Type.STRING_ARRAY
    assert node._expected_asset_ids == ()


def test_real_init_wires_expected_topics_actions_and_timer():
    node = _make_executor()

    callbacks_by_topic = {
        subscription.topic: subscription.callback.__name__
        for subscription in node.subscriptions
    }
    assert callbacks_by_topic == {
        "/inspection/assets": "_cb_assets",
        "/inspection/gauge_reading": "_cb_reading",
        "/inspection/selected_viewpoint": "_cb_viewpoint",
        "/inspection/retry_viewpoint": "_cb_retry",
        "/odometry/filtered": "_cb_odom",
    }
    assert node._mission_pub.topic == "/inspection/mission_state"
    assert node._nav_client.action_name == "navigate_to_pose"
    assert node._pa_client.action_name == "precision_approach"
    assert [(timer.period, timer.callback.__name__) for timer in node.timers] == [
        (0.2, "_tick")
    ]


def test_mission_state_publisher_is_reliable_transient_local_depth_one():
    node = _make_executor()

    qos = node._mission_pub.qos
    assert qos.depth == 1
    assert qos.reliability is FakeReliabilityPolicy.RELIABLE
    assert qos.durability is FakeDurabilityPolicy.TRANSIENT_LOCAL


def test_viewpoint_is_ignored_outside_select_viewpoint_before_mutation():
    node = _make_executor()
    original = FakePoseStamped()
    node.selected_viewpoint = original
    node.sm.state = S_NAVIGATE
    incoming = FakePoseStamped()
    incoming.pose.position.x = 9.0

    node._cb_viewpoint(incoming)

    assert node.selected_viewpoint is original
    assert node.sm.state == S_NAVIGATE


def test_viewpoint_stamp_must_match_published_request_stamp():
    node = _make_executor()
    node.sm.state = S_SELECT_VIEWPOINT
    node._publish_state()

    stale = FakePoseStamped()
    stale.header.stamp = SimpleNamespace(sec=123, nanosec=455)
    node._cb_viewpoint(stale)
    assert node.selected_viewpoint is None
    assert node.sm.state == S_SELECT_VIEWPOINT

    matching = FakePoseStamped()
    matching.header.stamp = SimpleNamespace(sec=123, nanosec=456)
    node._cb_viewpoint(matching)
    assert node.selected_viewpoint is matching
    assert node.sm.state == S_NAVIGATE


def _arm_timeout(node, state, timeout_s=1.0):
    node.sm.state = state
    node.last_state = state
    node._state_entered_at = 10.0
    node._state_deadlines[state] = timeout_s


def test_missing_viewpoint_expires_into_timeout_result():
    node = _make_executor()
    node.sm.assets = [FakeAsset("a1")]
    node.sm.asset_idx = 0
    _arm_timeout(node, S_SELECT_VIEWPOINT)

    with patch.object(mission_executor.time, "monotonic", return_value=11.1):
        node._tick()
    assert node.sm.state == S_RECORD
    assert node.sm.last_failure_reason == "timeout"

    node._tick()
    assert node.sm.results[-1]["asset_id"] == "a1"
    assert node.sm.results[-1]["failure_reason"] == "timeout"


def test_missing_reading_expires_into_timeout_result():
    node = _make_executor()
    node.sm.assets = [FakeAsset("a1")]
    node.sm.asset_idx = 0
    node.asset_viewpoints = ["v1"]
    _arm_timeout(node, S_INSPECT)

    with patch.object(mission_executor.time, "monotonic", return_value=11.1):
        node._tick()
    node._tick()

    assert node.sm.results[-1]["failure_reason"] == "timeout"
    assert node.sm.results[-1]["status"] == "failed"


def test_real_state_transition_resets_deadline_before_timeout():
    node = _make_executor(select_viewpoint_timeout_s=10.0)
    node.sm.assets = [FakeAsset("a1")]
    node.sm.state = S_LOAD_MISSION
    node.last_state = S_LOAD_MISSION
    node.sm.on_event(E_ASSETS_LOADED)
    assert node.sm.state == S_SELECT_ASSET

    with patch.object(mission_executor.time, "monotonic", return_value=20.0):
        node._tick()
    assert node.sm.state == S_SELECT_VIEWPOINT

    with patch.object(mission_executor.time, "monotonic", return_value=21.0):
        node._tick()
    assert node._state_entered_at == 21.0

    with patch.object(mission_executor.time, "monotonic", return_value=30.9):
        node._tick()
    assert node.sm.state == S_SELECT_VIEWPOINT

    with patch.object(mission_executor.time, "monotonic", return_value=31.0):
        node._tick()
    assert node.sm.state == S_RECORD
    assert node.sm.last_failure_reason == "timeout"


def test_missing_odom_expires_without_home_reached(tmp_path):
    report_path = tmp_path / "mission.json"
    node = _make_executor(
        run_id="run-timeout",
        report_path=str(report_path),
        return_home_timeout_s=1.0,
    )
    node.current_odom = None
    _arm_timeout(node, S_RETURN_HOME)

    with patch.object(mission_executor.time, "monotonic", return_value=11.1):
        node._tick()

    assert node.sm.state == S_EXPORT_REPORT
    assert node._return_home_status == "failed"
    assert node._return_home_failure_reason == "timeout"

    node._tick()
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["return_home"] == {
        "status": "failed",
        "final_distance_m": None,
        "failure_reason": "timeout",
    }


def test_navigation_time_accumulates_on_terminal_result_not_goal_acceptance():
    node = _make_executor()
    node.sm.state = S_NAVIGATE
    node.selected_viewpoint = FakePoseStamped()

    with patch.object(mission_executor.time, "monotonic", return_value=10.0):
        node._start_navigation()
    goal_future = node._nav_client.goal_futures[-1]
    goal_handle = FakeGoalHandle(accepted=True)

    with patch.object(mission_executor.time, "monotonic", return_value=11.0):
        goal_future.set_result(goal_handle)
    assert node.asset_nav_time == 0.0

    with patch.object(mission_executor.time, "monotonic", return_value=13.0):
        goal_handle.result_future.set_result(
            _action_result(FakeGoalStatus.STATUS_SUCCEEDED))

    assert node.asset_nav_time == 3.0
    assert node.sm.state == S_PRECISION_APPROACH


def test_navigation_timeout_cancels_goal_and_ignores_late_result():
    node = _make_executor()
    node.sm.assets = [FakeAsset("a1")]
    node.sm.asset_idx = 0
    node.sm.state = S_NAVIGATE
    node.selected_viewpoint = FakePoseStamped()

    with patch.object(mission_executor.time, "monotonic", return_value=10.0):
        node._start_navigation()
    goal_handle = FakeGoalHandle(accepted=True)
    node._nav_client.goal_futures[-1].set_result(goal_handle)
    _arm_timeout(node, S_NAVIGATE)

    with patch.object(mission_executor.time, "monotonic", return_value=11.1):
        node._tick()

    assert node.sm.state == S_RECORD
    assert goal_handle.cancel_calls == 1
    assert math.isclose(node.asset_nav_time, 1.1)

    goal_handle.result_future.set_result(
        _action_result(FakeGoalStatus.STATUS_SUCCEEDED))
    assert node.sm.state == S_RECORD


def test_pending_navigation_goal_is_cancelled_when_accepted_after_timeout():
    node = _make_executor()
    node.sm.state = S_NAVIGATE
    node.selected_viewpoint = FakePoseStamped()
    with patch.object(mission_executor.time, "monotonic", return_value=10.0):
        node._start_navigation()
    pending_goal = node._nav_client.goal_futures[-1]
    _arm_timeout(node, S_NAVIGATE)

    with patch.object(mission_executor.time, "monotonic", return_value=11.1):
        node._tick()
    stale_handle = FakeGoalHandle(accepted=True)
    pending_goal.set_result(stale_handle)

    assert node.sm.state == S_RECORD
    assert stale_handle.cancel_calls == 1


def test_precision_timeout_cancels_goal_closes_timing_and_ignores_result():
    node = _make_executor()
    node.sm.assets = [FakeAsset("a1")]
    node.sm.asset_idx = 0
    node.sm.state = S_PRECISION_APPROACH
    node.selected_viewpoint = FakePoseStamped()

    with patch.object(mission_executor.time, "monotonic", return_value=20.0):
        node._start_precision_approach()
    goal_handle = FakeGoalHandle(accepted=True)
    node._pa_client.goal_futures[-1].set_result(goal_handle)
    _arm_timeout(node, S_PRECISION_APPROACH)
    with patch.object(mission_executor.time, "monotonic", return_value=21.25):
        node._tick()

    assert node.sm.state == S_RECORD
    assert goal_handle.cancel_calls == 1
    assert node.asset_inspect_time == 1.25

    goal_handle.result_future.set_result(
        _action_result(
            FakeGoalStatus.STATUS_SUCCEEDED, precision_success=True))
    assert node.sm.state == S_RECORD


def test_rejected_precision_goal_closes_inspection_timing():
    node = _make_executor()
    node.sm.state = S_PRECISION_APPROACH
    node.selected_viewpoint = FakePoseStamped()
    with patch.object(mission_executor.time, "monotonic", return_value=30.0):
        node._start_precision_approach()

    with patch.object(mission_executor.time, "monotonic", return_value=32.5):
        node._pa_client.goal_futures[-1].set_result(
            FakeGoalHandle(accepted=False))

    assert node.asset_inspect_time == 2.5
    assert node.sm.state == S_SELECT_VIEWPOINT


def test_cancel_barrier_waits_for_ack_and_terminal_before_new_navigation():
    node = _make_executor(cancel_wait_timeout_s=5.0)
    node.sm.state = S_PRECISION_APPROACH
    node.selected_viewpoint = FakePoseStamped()
    with patch.object(mission_executor.time, "monotonic", return_value=10.0):
        node._start_precision_approach()
    old_goal = FakeGoalHandle(accepted=True, defer_cancel=True)
    node._pa_client.goal_futures[-1].set_result(old_goal)

    with patch.object(mission_executor.time, "monotonic", return_value=10.0):
        node._cb_retry(SimpleNamespace(data="reviewer retry"))
    assert old_goal.cancel_calls == 1

    node.sm.state = S_NAVIGATE
    node.last_state = S_SELECT_VIEWPOINT
    node.selected_viewpoint = FakePoseStamped()
    with patch.object(mission_executor.time, "monotonic", return_value=11.0):
        node._tick()
    assert len(node._nav_client.sent_goals) == 0

    # Even a cancel response with no accepted goals is not terminal proof.
    old_goal.cancel_future.set_result(SimpleNamespace(goals_canceling=[]))
    with patch.object(mission_executor.time, "monotonic", return_value=12.0):
        node._tick()
    assert len(node._nav_client.sent_goals) == 0

    old_goal.result_future.set_result(
        _action_result(
            FakeGoalStatus.STATUS_CANCELED, precision_success=False))
    with patch.object(mission_executor.time, "monotonic", return_value=13.0):
        node._tick()
    assert len(node._nav_client.sent_goals) == 1


def test_cancel_barrier_tracks_goal_accepted_after_retry_invalidation():
    node = _make_executor(cancel_wait_timeout_s=5.0)
    node.sm.state = S_PRECISION_APPROACH
    node.selected_viewpoint = FakePoseStamped()
    with patch.object(mission_executor.time, "monotonic", return_value=30.0):
        node._start_precision_approach()
    pending_goal_response = node._pa_client.goal_futures[-1]

    with patch.object(mission_executor.time, "monotonic", return_value=30.0):
        node._cb_retry(SimpleNamespace(data="retry before accept"))
    node.sm.state = S_NAVIGATE
    node.last_state = S_SELECT_VIEWPOINT
    node.selected_viewpoint = FakePoseStamped()

    late_goal = FakeGoalHandle(accepted=True, defer_cancel=True)
    pending_goal_response.set_result(late_goal)
    assert late_goal.cancel_calls == 1
    with patch.object(mission_executor.time, "monotonic", return_value=31.0):
        node._tick()
    assert len(node._nav_client.sent_goals) == 0

    late_goal.cancel_future.set_result(SimpleNamespace())
    late_goal.result_future.set_result(
        _action_result(
            FakeGoalStatus.STATUS_CANCELED, precision_success=False))
    with patch.object(mission_executor.time, "monotonic", return_value=32.0):
        node._tick()
    assert len(node._nav_client.sent_goals) == 1


def test_cancel_barrier_timeout_records_failure_and_disables_actions(tmp_path):
    report_path = tmp_path / "cancel-timeout.json"
    node = _make_executor(
        cancel_wait_timeout_s=1.0,
        report_path=str(report_path),
    )
    node.sm.assets = [FakeAsset("a1")]
    node.sm.asset_idx = 0
    node.sm.state = S_PRECISION_APPROACH
    node.asset_viewpoints = ["v1"]
    node.selected_viewpoint = FakePoseStamped()
    with patch.object(mission_executor.time, "monotonic", return_value=20.0):
        node._start_precision_approach()
    old_goal = FakeGoalHandle(accepted=True, defer_cancel=True)
    node._pa_client.goal_futures[-1].set_result(old_goal)
    with patch.object(mission_executor.time, "monotonic", return_value=20.0):
        node._cb_retry(SimpleNamespace(data="reviewer retry"))

    node.sm.state = S_NAVIGATE
    node.selected_viewpoint = FakePoseStamped()
    with patch.object(mission_executor.time, "monotonic", return_value=21.1):
        node._tick()

    assert node._action_dispatch_disabled is True
    assert node.sm.state == S_EXPORT_REPORT
    assert node.sm.last_failure_reason == "timeout"
    assert len(node._nav_client.sent_goals) == 0

    node._tick()
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["results"][-1]["failure_reason"] == "timeout"
    assert report["return_home"]["failure_reason"] == "cancel_timeout"
    assert node.sm.state == S_DONE


def test_cancel_wait_timeout_parameter_is_always_positive():
    node = _make_executor(cancel_wait_timeout_s=0.0)
    assert node._cancel_wait_timeout_s > 0.0


def test_reader_retry_restarts_and_accumulates_inspection_timing():
    node = _make_executor()
    node.sm.assets = [FakeAsset("a1")]
    node.sm.asset_idx = 0
    node.sm.state = S_INSPECT
    node.last_state = S_VALIDATE
    node.asset_viewpoints = ["v1"]
    node.asset_inspect_time = 2.0
    node._inspect_start_ts = None

    with patch.object(mission_executor.time, "monotonic", return_value=40.0):
        node._tick()
    assert node._inspect_start_ts == 40.0

    node._cb_reading(_reading("a1", confidence=0.9))
    with patch.object(mission_executor.time, "monotonic", return_value=43.0):
        node._tick()

    assert node.sm.state == S_RECORD
    assert node.asset_inspect_time == 5.0


def test_rejected_return_home_goal_does_not_report_home_reached():
    node = _make_executor()
    node.sm.state = S_RETURN_HOME
    node.current_odom = (0.0, 0.0, 0.0)

    node._return_home()
    node._nav_client.goal_futures[-1].set_result(
        FakeGoalHandle(accepted=False))

    assert node.sm.state == S_EXPORT_REPORT
    assert node._return_home_status == "failed"
    assert node._return_home_failure_reason == "goal_rejected"


def test_aborted_return_home_goal_does_not_report_home_reached():
    node = _make_executor()
    node.sm.state = S_RETURN_HOME
    node.current_odom = (0.0, 0.0, 0.0)

    node._return_home()
    goal_handle = FakeGoalHandle(accepted=True)
    node._nav_client.goal_futures[-1].set_result(goal_handle)
    goal_handle.result_future.set_result(
        _action_result(FakeGoalStatus.STATUS_ABORTED))

    assert node.sm.state == S_EXPORT_REPORT
    assert node._return_home_status == "failed"
    assert node._return_home_failure_reason == "goal_status_6"


def test_return_home_tick_result_and_fresh_odom_chain(tmp_path):
    node = _make_executor(report_path=str(tmp_path / "mission.json"))
    node.sm.state = S_RETURN_HOME
    node.last_state = S_SELECT_ASSET
    node._cb_odom(_odom(0.5, 0.0))

    node._tick()
    assert len(node._nav_client.sent_goals) == 1
    home_goal = node._nav_client.sent_goals[0]
    assert home_goal.pose.header.frame_id == "map"
    assert home_goal.pose.pose.position.x == node.home_pose[0]
    assert home_goal.pose.pose.position.y == node.home_pose[1]
    assert home_goal.pose.pose.orientation.w == 1.0
    goal_handle = FakeGoalHandle(accepted=True)
    node._nav_client.goal_futures[-1].set_result(goal_handle)
    goal_handle.result_future.set_result(
        _action_result(FakeGoalStatus.STATUS_SUCCEEDED))

    assert node.sm.state == S_RETURN_HOME
    assert node._return_home_status == "pending"

    node._cb_odom(_odom(0.2, 0.0))
    assert node.sm.state == S_RETURN_HOME
    assert node._return_home_status == "pending"

    node._cb_odom(_odom(0.06, 0.08))  # exactly 0.10 m from home
    assert node.sm.state == S_EXPORT_REPORT
    assert node._return_home_status == "success"
    assert node._return_home_distance_m == 0.10


def test_return_home_timeout_cancels_goal_and_ignores_late_success():
    node = _make_executor()
    node.sm.state = S_RETURN_HOME
    node.current_odom = (0.5, 0.0, 0.0)
    node._return_home()
    goal_handle = FakeGoalHandle(accepted=True)
    node._nav_client.goal_futures[-1].set_result(goal_handle)
    _arm_timeout(node, S_RETURN_HOME)

    with patch.object(mission_executor.time, "monotonic", return_value=11.1):
        node._tick()

    assert node.sm.state == S_EXPORT_REPORT
    assert node._return_home_status == "failed"
    assert node._return_home_failure_reason == "timeout"
    assert goal_handle.cancel_calls == 1

    goal_handle.result_future.set_result(
        _action_result(FakeGoalStatus.STATUS_SUCCEEDED))
    node._cb_odom(_odom(0.0, 0.0))
    assert node.sm.state == S_EXPORT_REPORT
    assert node._return_home_status == "failed"


def test_return_home_odom_arriving_after_deadline_is_timeout():
    node = _make_executor()
    node.sm.state = S_RETURN_HOME
    node.current_odom = (0.5, 0.0, 0.0)
    node._return_home()
    goal_handle = FakeGoalHandle(accepted=True)
    node._nav_client.goal_futures[-1].set_result(goal_handle)
    goal_handle.result_future.set_result(
        _action_result(FakeGoalStatus.STATUS_SUCCEEDED))
    _arm_timeout(node, S_RETURN_HOME)

    with patch.object(mission_executor.time, "monotonic", return_value=11.1):
        node._cb_odom(_odom(0.0, 0.0))

    assert node.sm.state == S_EXPORT_REPORT
    assert node._return_home_status == "failed"
    assert node._return_home_failure_reason == "timeout"


def test_report_uses_supplied_run_id_path_and_expected_assets(tmp_path):
    report_path = tmp_path / "nested" / "mission_report.json"
    node = _make_executor(
        run_id="run-123",
        report_path=str(report_path),
        expected_asset_ids=["a1", "a2"],
    )
    node.sm.assets = [FakeAsset("a1"), FakeAsset("a2")]
    node.sm.state = S_EXPORT_REPORT
    node._return_home_status = "success"
    node._return_home_distance_m = 0.04

    node._export_report()

    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["schema_version"] == "1.1"
    assert report["run_id"] == "run-123"
    assert report["expected_asset_ids"] == ["a1", "a2"]
    assert report["return_home"]["status"] == "success"


def test_precision_launch_has_one_server_and_no_handoff_client():
    launch_nodes = []

    class FakeLaunchDescription:
        def __init__(self, entities):
            self.entities = entities

    class FakeDeclareLaunchArgument:
        def __init__(self, name, **kwargs):
            self.name = name
            self.kwargs = kwargs

    class FakeLaunchNode:
        def __init__(self, **kwargs):
            self.kwargs = kwargs
            launch_nodes.append(self)

    launch_stubs = {
        "launch": _module("launch", LaunchDescription=FakeLaunchDescription),
        "launch.actions": _module(
            "launch.actions", DeclareLaunchArgument=FakeDeclareLaunchArgument),
        "launch.substitutions": _module(
            "launch.substitutions",
            LaunchConfiguration=lambda name, **_kwargs: f"config:{name}"),
        "launch_ros": _module("launch_ros"),
        "launch_ros.actions": _module("launch_ros.actions", Node=FakeLaunchNode),
    }
    launch_path = (Path(__file__).resolve().parents[2]
                   / "siminspect_precision_control" / "launch"
                   / "precision_approach.launch.py")
    spec = importlib.util.spec_from_file_location(
        "precision_launch_contract_under_test", launch_path)
    module = importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules, launch_stubs):
        spec.loader.exec_module(module)

    description = module.generate_launch_description()
    executables = [node.kwargs["executable"] for node in launch_nodes]
    assert executables == ["controller_interface.py"]
    assert any(entity.name == "controller_type"
               for entity in description.entities
               if isinstance(entity, FakeDeclareLaunchArgument))
    assert launch_nodes[0].kwargs["parameters"] == [
        {"controller_type": "config:controller_type"}
    ]
