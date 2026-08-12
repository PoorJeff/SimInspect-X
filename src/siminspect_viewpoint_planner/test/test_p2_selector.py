"""Test P2 selector: re-inspection trigger, blacklist, and selection."""
import math, sys, os, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "siminspect_viewpoint_planner"))
from p2_selector import P2Selector, CONF_THRESHOLD, MAX_ATTEMPTS

class FakeAsset:
    id = "test"
    class Pose:
        class Pos: x=3.0; y=2.0; z=1.0
        class Ori: z=0.0; w=1.0
        position = Pos(); orientation = Ori()
    map_pose = Pose()

class FakeReading:
    asset_id = "test"
    confidence = 0.90
    value = 50.0

class FakeLogger:
    def info(self, msg): pass
    def warn(self, msg): pass
    def error(self, msg): pass

class FakePublisher:
    def publish(self, msg): self.last_msg = msg

def _make_sel():
    sel = P2Selector.__new__(P2Selector)
    sel.p1 = __import__("p1_selector").P1Selector.__new__(__import__("p1_selector").P1Selector)
    sel.p1.scorer = __import__("quality_scorer").QualityScorer()
    sel.assets = {"test": FakeAsset}
    sel.current_asset_id = "test"
    sel.blacklist = []
    sel.attempt = 0
    sel.pub = FakePublisher()
    sel._logger = FakeLogger()
    sel.get_logger = lambda: sel._logger
    return sel

def test_select_for_asset_returns_pose():
    sel = P2Selector.__new__(P2Selector)
    sel.p1 = __import__("p1_selector").P1Selector.__new__(__import__("p1_selector").P1Selector)
    sel.p1.scorer = __import__("quality_scorer").QualityScorer()
    result = sel.select_for_asset(FakeAsset, [])
    assert result is not None
    idx, ps = result
    assert isinstance(idx, int)
    assert abs(math.hypot(ps.pose.position.x-3.0, ps.pose.position.y-2.0)-0.8) < 0.05

def test_select_for_asset_respects_blacklist():
    sel = P2Selector.__new__(P2Selector)
    sel.p1 = __import__("p1_selector").P1Selector.__new__(__import__("p1_selector").P1Selector)
    sel.p1.scorer = __import__("quality_scorer").QualityScorer()
    r1 = sel.select_for_asset(FakeAsset, [])
    assert r1 is not None
    best_idx, _ = r1
    r2 = sel.select_for_asset(FakeAsset, [best_idx])
    assert r2 is not None
    idx2, _ = r2
    assert idx2 != best_idx, f"Blacklist failed: got same index {best_idx}"

def test_select_for_asset_all_blacklisted_returns_none():
    sel = P2Selector.__new__(P2Selector)
    sel.p1 = __import__("p1_selector").P1Selector.__new__(__import__("p1_selector").P1Selector)
    sel.p1.scorer = __import__("quality_scorer").QualityScorer()
    result = sel.select_for_asset(FakeAsset, [0, 1, 2, 3, 4, 5, 6])
    assert result is None

def test_select_for_asset_pose_on_inspection_arc():
    """Selected viewpoint must lie on the 120-degree inspection arc.

    T-cost term biases toward robot origin (0,0); any candidate on the
    valid arc is acceptable. Yaw must face toward the gauge.
    """
    sel = P2Selector.__new__(P2Selector)
    sel.p1 = __import__("p1_selector").P1Selector.__new__(__import__("p1_selector").P1Selector)
    sel.p1.scorer = __import__("quality_scorer").QualityScorer()
    result = sel.select_for_asset(FakeAsset, [])
    assert result is not None
    _, ps = result
    yaw_v = 2*math.atan2(ps.pose.orientation.z, ps.pose.orientation.w)
    assert 2.0*math.pi/3 - 0.05 < yaw_v < 4.0*math.pi/3 + 0.05, \
        f"Yaw {yaw_v:.3f} outside valid arc [2pi/3, 4pi/3]"

def test_conf_threshold_constant():
    assert CONF_THRESHOLD == 0.80

def test_max_attempts_constant():
    assert MAX_ATTEMPTS == 3

def test_on_reading_high_confidence_no_retry():
    sel = _make_sel()
    reading = FakeReading()
    reading.confidence = 0.90
    sel.pub.last_msg = None
    sel.on_reading(reading)
    assert sel.attempt == 0, "attempt should not increment on high confidence"
    assert sel.pub.last_msg is None, "should not publish on high confidence"

def test_on_reading_low_confidence_triggers_retry():
    sel = _make_sel()
    reading = FakeReading()
    reading.confidence = 0.60
    sel.pub.last_msg = None
    sel.on_reading(reading)
    assert sel.attempt == 1, f"attempt should be 1, got {sel.attempt}"
    assert sel.pub.last_msg is not None, "should publish next best on low confidence"
    assert len(sel.blacklist) == 1, "blacklist should contain first candidate"

def test_on_reading_max_attempts_stops():
    sel = _make_sel()
    sel.attempt = MAX_ATTEMPTS
    reading = FakeReading()
    reading.confidence = 0.60
    sel.pub.last_msg = None
    sel.on_reading(reading)
    assert sel.pub.last_msg is None, "should NOT publish after max attempts"

def test_select_next_best_returns_pose():
    sel = _make_sel()
    result = sel._select_next_best()
    assert result is not None
    assert len(sel.blacklist) == 1

def test_select_next_best_all_blacklisted():
    sel = _make_sel()
    sel.blacklist = [0, 1, 2, 3, 4, 5, 6]
    sel.pub.last_msg = None
    result = sel._select_next_best()
    assert result is None

def test_select_next_best_iterates_through_candidates():
    sel = _make_sel()
    results = []
    for _ in range(7):
        r = sel._select_next_best()
        if r is None:
            break
        results.append(r)
    assert len(results) == 7
    assert len(sel.blacklist) == 7