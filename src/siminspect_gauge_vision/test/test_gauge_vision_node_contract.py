"""Contract tests for mission-gated gauge vision publication."""
import importlib.util
from enum import Enum
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
from unittest.mock import patch


class FakeNode:
    def __init__(self, _name):
        self.subscriptions = []

    def create_subscription(self, _msg_type, topic, callback, qos):
        subscription = SimpleNamespace(topic=topic, callback=callback, qos=qos)
        self.subscriptions.append(subscription)
        return subscription

    def create_publisher(self, _msg_type, topic, qos):
        publisher = FakePublisher()
        publisher.topic = topic
        publisher.qos = qos
        return publisher


class FakeGaugeReading:
    def __init__(self):
        self.asset_id = ""
        self.estimated_value = 0.0
        self.unit = ""
        self.confidence = 0.0
        self.target_pixel_area = 0.0
        self.view_angle_proxy = 0.0


class FakeBridge:
    def __init__(self):
        self.calls = 0

    def imgmsg_to_cv2(self, _msg, encoding):
        self.calls += 1
        assert encoding == "bgr8"
        return "image"


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


def _module(name, **attrs):
    module = ModuleType(name)
    for key, value in attrs.items():
        setattr(module, key, value)
    return module


def _load_gauge_vision_node():
    pipeline = _module(
        "siminspect_gauge_vision.vision_pipeline",
        run_pipeline=lambda _image, asset_id: {
            "asset_id": asset_id,
            "estimated_value": 42.0,
            "unit": "psi",
            "confidence": 0.9,
            "target_pixel_area": 0.2,
            "view_angle_proxy": 0.8,
        },
    )
    stubs = {
        "rclpy": _module("rclpy", init=lambda: None, spin=lambda _node: None),
        "rclpy.node": _module("rclpy.node", Node=FakeNode),
        "rclpy.qos": _module(
            "rclpy.qos",
            QoSProfile=FakeQoSProfile,
            ReliabilityPolicy=FakeReliabilityPolicy,
            DurabilityPolicy=FakeDurabilityPolicy,
        ),
        "sensor_msgs": _module("sensor_msgs"),
        "sensor_msgs.msg": _module(
            "sensor_msgs.msg", Image=type("Image", (), {})),
        "siminspect_interfaces": _module("siminspect_interfaces"),
        "siminspect_interfaces.msg": _module(
            "siminspect_interfaces.msg",
            GaugeReading=FakeGaugeReading,
            MissionState=type("MissionState", (), {}),
        ),
        "cv_bridge": _module("cv_bridge", CvBridge=FakeBridge),
        "siminspect_gauge_vision.vision_pipeline": pipeline,
        "vision_pipeline": pipeline,
    }
    module_path = (Path(__file__).resolve().parents[1]
                   / "siminspect_gauge_vision" / "gauge_vision_node.py")
    spec = importlib.util.spec_from_file_location(
        "gauge_vision_contract_under_test", module_path)
    module = importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules, stubs):
        spec.loader.exec_module(module)
    return module


gauge_vision_node = _load_gauge_vision_node()
GaugeVisionNode = gauge_vision_node.GaugeVisionNode


def _make_node():
    node = GaugeVisionNode.__new__(GaugeVisionNode)
    node._bridge = FakeBridge()
    node._pub = FakePublisher()
    node._current_state = ""
    node._current_asset_id = ""
    return node


def _pipeline_spy(calls):
    def run_pipeline(_image, asset_id):
        calls.append(asset_id)
        return {
            "asset_id": asset_id,
            "estimated_value": 42.0,
            "unit": "psi",
            "confidence": 0.9,
            "target_pixel_area": 0.2,
            "view_angle_proxy": 0.8,
        }
    return run_pipeline


def test_image_is_ignored_outside_inspect_state():
    node = _make_node()
    node._cb_state(SimpleNamespace(state="NAVIGATE", current_asset_id="a1"))
    pipeline_calls = []

    with patch.object(gauge_vision_node, "run_pipeline",
                      _pipeline_spy(pipeline_calls)):
        node._cb_image(object())

    assert node._bridge.calls == 0
    assert pipeline_calls == []
    assert node._pub.messages == []


def test_image_is_ignored_when_inspect_asset_id_is_empty():
    node = _make_node()
    node._cb_state(SimpleNamespace(state="INSPECT", current_asset_id=""))
    pipeline_calls = []

    with patch.object(gauge_vision_node, "run_pipeline",
                      _pipeline_spy(pipeline_calls)):
        node._cb_image(object())

    assert node._bridge.calls == 0
    assert pipeline_calls == []
    assert node._pub.messages == []


def test_inspect_image_publishes_reading_for_current_asset():
    node = _make_node()
    node._cb_state(SimpleNamespace(state="INSPECT", current_asset_id="a1"))
    pipeline_calls = []

    with patch.object(gauge_vision_node, "run_pipeline",
                      _pipeline_spy(pipeline_calls)):
        node._cb_image(object())

    assert node._bridge.calls == 1
    assert pipeline_calls == ["a1"]
    assert len(node._pub.messages) == 1
    assert node._pub.messages[0].asset_id == "a1"


def test_init_wires_topics_and_transient_mission_state_qos():
    node = GaugeVisionNode()
    assert node._sub_img.topic == "/camera/image_raw"
    assert node._sub_img.callback.__name__ == "_cb_image"
    assert node._pub.topic == "/inspection/gauge_reading"
    state_subscription = next(
        subscription for subscription in node.subscriptions
        if subscription.topic == "/inspection/mission_state")
    assert state_subscription.callback.__name__ == "_cb_state"

    qos = state_subscription.qos
    assert qos.depth == 1
    assert qos.reliability is FakeReliabilityPolicy.RELIABLE
    assert qos.durability is FakeDurabilityPolicy.TRANSIENT_LOCAL
