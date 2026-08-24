"""Contract tests for request-driven B0 and P2 viewpoint selection."""
import importlib.util
from enum import Enum
import math
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
from unittest.mock import patch


class FakeNode:
    def __init__(self, _name):
        self.subscriptions = []
        self._parameters = {}

    def create_publisher(self, _msg_type, topic, qos):
        publisher = FakePublisher()
        publisher.topic = topic
        publisher.qos = qos
        return publisher

    def create_subscription(self, _msg_type, topic, callback, qos):
        subscription = SimpleNamespace(topic=topic, callback=callback, qos=qos)
        self.subscriptions.append(subscription)
        return subscription

    def declare_parameter(self, name, default):
        self._parameters[name] = default

    def get_parameter(self, name):
        return SimpleNamespace(value=self._parameters[name])

    def get_logger(self):
        return FakeLogger()


class FakePoseStamped:
    def __init__(self):
        self.header = SimpleNamespace(frame_id="", stamp=None)
        self.pose = SimpleNamespace(
            position=SimpleNamespace(x=0.0, y=0.0, z=0.0),
            orientation=SimpleNamespace(x=0.0, y=0.0, z=0.0, w=1.0),
        )


class FakePublisher:
    def __init__(self):
        self.messages = []

    def publish(self, msg):
        self.messages.append(msg)


class FakeQoSProfile:
    def __init__(self, *, depth, reliability, durability):
        self.depth = depth
        self.reliability = reliability
        self.durability = durability


class FakeReliabilityPolicy(Enum):
    RELIABLE = 1


class FakeDurabilityPolicy(Enum):
    TRANSIENT_LOCAL = 1


class FakeLogger:
    def info(self, _msg):
        pass

    def warn(self, _msg):
        pass

    def error(self, _msg):
        pass


def _module(name, **attrs):
    module = ModuleType(name)
    for key, value in attrs.items():
        setattr(module, key, value)
    return module


def _load_selector(filename, module_name):
    stubs = {
        "rclpy": _module("rclpy", init=lambda: None, spin=lambda _node: None),
        "rclpy.node": _module("rclpy.node", Node=FakeNode),
        "rclpy.qos": _module(
            "rclpy.qos",
            QoSProfile=FakeQoSProfile,
            ReliabilityPolicy=FakeReliabilityPolicy,
            DurabilityPolicy=FakeDurabilityPolicy,
        ),
        "geometry_msgs": _module("geometry_msgs"),
        "geometry_msgs.msg": _module(
            "geometry_msgs.msg", PoseStamped=FakePoseStamped),
        "siminspect_interfaces": _module("siminspect_interfaces"),
        "siminspect_interfaces.msg": _module(
            "siminspect_interfaces.msg",
            AssetArray=type("AssetArray", (), {}),
            GaugeReading=type("GaugeReading", (), {}),
            MissionState=type("MissionState", (), {}),
        ),
    }
    package_dir = (Path(__file__).resolve().parents[1]
                   / "siminspect_viewpoint_planner")
    if str(package_dir) not in sys.path:
        sys.path.insert(0, str(package_dir))
    spec = importlib.util.spec_from_file_location(
        module_name, package_dir / filename)
    module = importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules, stubs):
        spec.loader.exec_module(module)
    return module


p2_selector = _load_selector(
    "p2_selector.py", "p2_selector_contract_under_test")
b0_selector = _load_selector(
    "b0_selector.py", "b0_selector_contract_under_test")
quality_scorer = importlib.import_module("quality_scorer")
P2Selector = p2_selector.P2Selector
B0Selector = b0_selector.B0Selector


class FakeAsset:
    def __init__(self, asset_id="test", x=3.0, y=2.0, yaw=0.0):
        self.id = asset_id
        self.map_pose = SimpleNamespace(
            position=SimpleNamespace(x=x, y=y, z=1.0),
            orientation=SimpleNamespace(
                z=math.sin(yaw / 2.0), w=math.cos(yaw / 2.0)),
        )


def _state(asset_id="test", request_id=1, state="SELECT_VIEWPOINT"):
    return SimpleNamespace(
        state=state,
        current_asset_id=asset_id,
        request_id=request_id,
        timestamp=SimpleNamespace(sec=100 + request_id, nanosec=200),
    )


def _make_p2():
    sel = P2Selector.__new__(P2Selector)
    sel.p1 = p2_selector.P1Selector.__new__(p2_selector.P1Selector)
    sel.p1.scorer = quality_scorer.QualityScorer()
    sel.assets = {}
    sel.enable_reinspect = True
    sel._published_requests = set()
    sel._published_indices = {}
    sel._pending_request = None
    sel.pub = FakePublisher()
    sel._logger = FakeLogger()
    sel.get_logger = lambda: sel._logger
    return sel


def _make_b0():
    sel = B0Selector.__new__(B0Selector)
    sel.assets = {}
    sel._published_requests = set()
    sel._pending_request = None
    sel.pub = FakePublisher()
    sel.get_logger = lambda: FakeLogger()
    return sel


def _candidate_index(ps, asset=None):
    asset = asset or FakeAsset()
    half = math.radians(60.0)
    for index in range(7):
        angle = -half + index * (2.0 * half / 6.0)
        expected_x = asset.map_pose.position.x + 0.8 * math.cos(angle)
        expected_y = asset.map_pose.position.y + 0.8 * math.sin(angle)
        if (math.isclose(ps.pose.position.x, expected_x, abs_tol=1e-9)
                and math.isclose(ps.pose.position.y, expected_y, abs_tol=1e-9)):
            return index
    raise AssertionError("published pose is not one of the seven candidates")


def test_select_for_asset_returns_pose_on_inspection_arc():
    sel = _make_p2()
    result = sel.select_for_asset(FakeAsset(), [])
    assert result is not None
    index, pose = result
    assert isinstance(index, int)
    assert math.isclose(
        math.hypot(pose.pose.position.x - 3.0,
                   pose.pose.position.y - 2.0),
        0.8,
        abs_tol=1e-9,
    )


def test_select_for_asset_respects_blacklist():
    sel = _make_p2()
    first_index, _ = sel.select_for_asset(FakeAsset(), [])
    second_index, _ = sel.select_for_asset(FakeAsset(), [first_index])
    assert second_index != first_index


def test_select_for_asset_all_blacklisted_returns_none():
    sel = _make_p2()
    assert sel.select_for_asset(FakeAsset(), list(range(7))) is None


def test_p2_asset_inventory_is_cache_only():
    sel = _make_p2()
    sel.on_assets(SimpleNamespace(assets=[FakeAsset()]))
    assert sel.pub.messages == []
    assert set(sel.assets) == {"test"}


def test_p2_publishes_once_for_matching_asset_and_request():
    sel = _make_p2()
    sel.on_assets(SimpleNamespace(assets=[FakeAsset()]))

    sel.on_mission_state(_state(request_id=11))
    sel.on_mission_state(_state(request_id=11))

    assert len(sel.pub.messages) == 1
    assert (sel.pub.messages[0].header.stamp.sec,
            sel.pub.messages[0].header.stamp.nanosec) == (111, 200)


def test_p2_later_request_excludes_previously_published_candidate():
    sel = _make_p2()
    asset = FakeAsset()
    sel.on_assets(SimpleNamespace(assets=[asset]))
    sel.on_mission_state(_state(request_id=1))
    first_index = _candidate_index(sel.pub.messages[-1], asset)

    # Mission emits a new request after low-confidence validation.
    sel.on_mission_state(_state(request_id=2))
    second_index = _candidate_index(sel.pub.messages[-1], asset)

    assert len(sel.pub.messages) == 2
    assert second_index != first_index


def test_duplicate_asset_inventory_does_not_reset_p2_candidate_history():
    sel = _make_p2()
    asset = FakeAsset()
    inventory = SimpleNamespace(assets=[asset])
    sel.on_assets(inventory)
    sel.on_mission_state(_state(request_id=1))
    first_index = _candidate_index(sel.pub.messages[-1], asset)

    sel.on_assets(inventory)
    sel.on_mission_state(_state(request_id=2))
    second_index = _candidate_index(sel.pub.messages[-1], asset)

    assert second_index != first_index


def test_p2_ignores_non_select_state_and_unknown_asset():
    sel = _make_p2()
    sel.on_assets(SimpleNamespace(assets=[FakeAsset()]))
    sel.on_mission_state(_state(state="NAVIGATE"))
    sel.on_mission_state(_state(asset_id="missing", request_id=2))
    assert sel.pub.messages == []


def test_b0_asset_inventory_is_cache_only():
    sel = _make_b0()
    sel.on_assets(SimpleNamespace(assets=[FakeAsset()]))
    assert sel.pub.messages == []


def test_b0_publishes_once_per_request_and_repeats_fixed_pose():
    sel = _make_b0()
    sel.on_assets(SimpleNamespace(assets=[FakeAsset()]))

    sel.on_mission_state(_state(request_id=1))
    sel.on_mission_state(_state(request_id=1))
    sel.on_mission_state(_state(request_id=2))

    assert len(sel.pub.messages) == 2
    first, second = sel.pub.messages
    assert (first.pose.position.x, first.pose.position.y) == (
        second.pose.position.x, second.pose.position.y)
    assert (first.pose.orientation.z, first.pose.orientation.w) == (
        second.pose.orientation.z, second.pose.orientation.w)
    assert (first.header.stamp.sec, first.header.stamp.nanosec) == (101, 200)
    assert (second.header.stamp.sec, second.header.stamp.nanosec) == (102, 200)


def test_request_waits_until_matching_asset_has_been_cached():
    sel = _make_p2()
    sel.on_mission_state(_state(asset_id="late", request_id=4))
    assert sel.pub.messages == []

    sel.on_assets(SimpleNamespace(assets=[FakeAsset(asset_id="late")]))
    assert len(sel.pub.messages) == 1


def test_selector_init_wires_topics_and_transient_mission_state_qos():
    for selector in (P2Selector(), B0Selector()):
        assert selector.asset_sub.topic == "/inspection/assets"
        assert selector.asset_sub.callback.__name__ == "on_assets"
        assert selector.pub.topic == "/inspection/selected_viewpoint"
        state_subscription = next(
            subscription for subscription in selector.subscriptions
            if subscription.topic == "/inspection/mission_state")
        assert state_subscription.callback.__name__ == "on_mission_state"
        qos = state_subscription.qos
        assert qos.depth == 1
        assert qos.reliability is FakeReliabilityPolicy.RELIABLE
        assert qos.durability is FakeDurabilityPolicy.TRANSIENT_LOCAL
