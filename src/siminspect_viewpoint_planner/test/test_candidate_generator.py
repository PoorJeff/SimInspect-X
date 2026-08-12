"""Verify candidate generation: count, angles, visibility."""
import math, sys, os, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "siminspect_viewpoint_planner"))
from ray_caster import RayCaster
from candidate_generator import CandidateGenerator

class FakeAsset:
    id = "test_gauge"
    class Pose:
        class Pos: x=3.0; y=2.0; z=1.0
        class Ori: z=0.0; w=1.0
        position = Pos(); orientation = Ori()
    map_pose = Pose()

def test_generate_count():
    gen = CandidateGenerator.__new__(CandidateGenerator)
    vps = gen.generate(FakeAsset)
    assert len(vps) == 7, f"Expected 7, got {len(vps)}"

def test_generate_positions():
    gen = CandidateGenerator.__new__(CandidateGenerator)
    vps = gen.generate(FakeAsset)
    for vp in vps:
        px, py = vp.pose.position.x, vp.pose.position.y
        d = math.hypot(px-3.0, py-2.0)
        assert abs(d-0.8) < 0.05, f"Distance {d:.3f} != 0.8"
        assert vp.visible is True  # no caster set

def test_visibility_with_obstacle():
    rc = RayCaster(res=0.1, w=200, h=200)
    rc.set_origin(-5, -5)
    rc.add_box(3.4, 2.0, 0.2, 0.2)  # obstacle between asset and candidates
    gen = CandidateGenerator.__new__(CandidateGenerator)
    gen.caster = rc
    vps = gen.generate(FakeAsset)
    visible_count = sum(1 for vp in vps if vp.visible)
    assert visible_count < 7, "Obstacle should block some viewpoints"
    assert visible_count > 0, "Some viewpoints should still be visible"
