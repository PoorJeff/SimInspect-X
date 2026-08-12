"""Test P1 selector: Q maximization and pose output."""
import math, sys, os, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "siminspect_viewpoint_planner"))
from p1_selector import P1Selector

class FakeAsset:
    id = "test"
    class Pose:
        class Pos: x=3.0; y=2.0; z=1.0
        class Ori: z=0.0; w=1.0
        position = Pos(); orientation = Ori()
    map_pose = Pose()

def test_p1_returns_pose():
    sel = P1Selector.__new__(P1Selector)
    sel.scorer = __import__("quality_scorer").QualityScorer()
    ps = sel.select_p1(FakeAsset)
    assert ps is not None
    assert abs(math.hypot(ps.pose.position.x-3.0, ps.pose.position.y-2.0)-0.8) < 0.05

def test_p1_selects_pose_on_inspection_arc():
    """Selected viewpoint must lie on the 120+-degree inspection arc.

    T-cost term biases toward robot origin (0,0); any candidate on the
    valid arc is acceptable. Yaw must face toward the gauge.
    """
    sel = P1Selector.__new__(P1Selector)
    sel.scorer = __import__("quality_scorer").QualityScorer()
    ps = sel.select_p1(FakeAsset)
    yaw_v = 2*math.atan2(ps.pose.orientation.z, ps.pose.orientation.w)
    # Gauge normal=0 rad, candidates on +-60 deg arc, robot yaw = angle+pi
    assert 2.0*math.pi/3 - 0.05 < yaw_v < 4.0*math.pi/3 + 0.05, \
        f"Yaw {yaw_v:.3f} outside valid arc [2pi/3, 4pi/3]"