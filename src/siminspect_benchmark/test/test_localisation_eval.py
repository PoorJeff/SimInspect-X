"""Unit tests for yaw extraction, RMSE, and angle wrapping."""
import math, pytest

def yaw(q):
    """Quaternion to yaw angle."""
    return math.atan2(2*(q.w*q.z+q.x*q.y), 1-2*(q.y*q.y+q.z*q.z))

class Q: pass

def test_yaw_identity():
    q = Q(); q.w=1.0; q.x=0; q.y=0; q.z=0
    assert abs(yaw(q)) < 1e-9

def test_yaw_90deg():
    q = Q(); q.w=0.7071; q.x=0; q.y=0; q.z=0.7071
    assert abs(abs(yaw(q))-math.pi/2) < 0.001

def test_rmse():
    pairs = [(2.0, 3.0)] * 4
    pos_rmse = math.sqrt(sum(p[0]**2 for p in pairs)/len(pairs))
    assert abs(pos_rmse - 2.0) < 1e-9
    yaw_rmse = math.sqrt(sum(p[1]**2 for p in pairs)/len(pairs))
    assert abs(yaw_rmse - 3.0) < 1e-9

def test_yaw_wrap():
    d = math.atan2(math.sin(math.pi-(-math.pi)), math.cos(math.pi-(-math.pi)))
    assert abs(d) < 1e-9
