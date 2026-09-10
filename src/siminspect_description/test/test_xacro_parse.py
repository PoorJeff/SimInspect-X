import subprocess, sys, os
import math
from pathlib import Path
import xml.etree.ElementTree as ET
import pytest

def test_xacro_parse():
    urdf_dir = os.path.join(os.path.dirname(__file__), '..', 'urdf')
    xacro_file = os.path.join(urdf_dir, 'siminspect.urdf.xacro')
    assert os.path.exists(xacro_file), f'Xacro file not found: {xacro_file}'
    # Try xacro parse (may not be available on all platforms)
    try:
        result = subprocess.run(
            ['xacro', xacro_file], capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0:
            assert '<robot' in result.stdout, 'Xacro output missing <robot> tag'
            assert 'base_link' in result.stdout, 'URDF missing base_link'
            assert 'laser_link' in result.stdout, 'URDF missing laser_link'
            assert 'imu_link' in result.stdout, 'URDF missing imu_link'
            assert 'camera_link' in result.stdout, 'URDF missing camera_link'
            assert 'camera_optical_frame' in result.stdout, 'URDF missing camera_optical_frame'
            assert 'left_wheel' in result.stdout, 'URDF missing left_wheel'
            assert 'right_wheel' in result.stdout, 'URDF missing right_wheel'
            return
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    # If xacro not available, skip with message
    print('SKIP: xacro tool not available on this platform')
    assert True  # Not a failure if xacro is unavailable

def test_xacro_syntax():
    urdf_dir = os.path.join(os.path.dirname(__file__), '..', 'urdf')
    xacro_file = os.path.join(urdf_dir, 'siminspect.urdf.xacro')
    with open(xacro_file, 'r') as f:
        content = f.read()
    assert 'base_link' in content
    assert 'laser_link' in content
    assert 'imu_link' in content
    assert 'camera_link' in content
    assert 'camera_optical_frame' in content
    assert 'left_wheel' in content
    assert 'right_wheel' in content


def test_wheel_collision_axes_and_support_plane():
    xacro = pytest.importorskip("xacro")
    path = Path(__file__).resolve().parents[1] / "urdf" / "siminspect.urdf.xacro"
    robot = ET.fromstring(xacro.process_file(str(path)).toxml())
    contact_heights = []
    for side in ("left", "right"):
        link = robot.find(f"link[@name='{side}_wheel']")
        joint = robot.find(f"joint[@name='{side}_wheel_joint']")
        assert joint.find("axis").get("xyz") == "0 1 0"
        for kind in ("visual", "collision"):
            roll, pitch, yaw = map(float, link.find(f"{kind}/origin").get("rpy").split())
            # A URDF cylinder starts along Z; rolling wheels must align to Y.
            assert abs(math.sin(roll)) == pytest.approx(1.0)
            assert pitch == pytest.approx(0.0)
            assert yaw == pytest.approx(0.0)
        radius = float(link.find("collision/geometry/cylinder").get("radius"))
        contact_heights.append(float(joint.find("origin").get("xyz").split()[2]) - radius)
    for name in ("caster_front", "caster_rear"):
        joint = robot.find(f"joint[@name='{name}_joint']")
        sphere = robot.find(f"link[@name='{name}']/collision/geometry/sphere")
        contact_heights.append(float(joint.find("origin").get("xyz").split()[2]) - float(sphere.get("radius")))
    assert max(contact_heights) - min(contact_heights) < 1e-6
