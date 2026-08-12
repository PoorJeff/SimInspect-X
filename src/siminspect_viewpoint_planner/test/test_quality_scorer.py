"""Test quality scorer boundary cases per 07 spec."""
import math, sys, os, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "siminspect_viewpoint_planner"))
from quality_scorer import QualityScorer, DEFAULT_W

def test_D_perfect(): assert abs(QualityScorer().score_D(0.8) - 1.0) < 1e-9
def test_D_zero(): assert QualityScorer().score_D(0.0) == 0.0
def test_D_double(): assert QualityScorer().score_D(1.6) == 0.0
def test_A_perfect(): assert abs(QualityScorer().score_A(0.0) - 1.0) < 1e-9
def test_A_at_max(): assert QualityScorer(theta_max_deg=40).score_A(math.radians(40)) == 0.0
def test_A_beyond(): assert QualityScorer().score_A(math.radians(50)) == 0.0
def test_S_full(): assert abs(QualityScorer().score_S(0.5) - 1.0) < 1e-9
def test_S_zero(): assert QualityScorer().score_S(0.0) == 0.0
def test_S_double(): assert abs(QualityScorer().score_S(1.0) - 1.0) < 1e-9
def test_weights_default():
    q = QualityScorer()
    s = q.w_vis + q.w_d + q.w_theta + q.w_s
    assert abs(s - 1.0) < 1e-9, f"Sum {s} != 1.0"
def test_weights_override():
    q = QualityScorer(weights={"w_vis":0.4,"w_d":0.2,"w_theta":0.2,"w_s":0.2,"w_t":0.1})
    assert abs(q.w_vis - 0.4) < 1e-9
