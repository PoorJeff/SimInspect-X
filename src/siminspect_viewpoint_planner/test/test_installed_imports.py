"""Verify planner modules import from an isolated installed-style package."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys


PACKAGE_ROOT = (Path(__file__).resolve().parents[1]
                / "siminspect_viewpoint_planner")


def _write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _make_ros_stubs(site):
    _write(site / "rclpy" / "__init__.py", "def init(): pass\ndef spin(node): pass\n")
    _write(site / "rclpy" / "node.py", "class Node: pass\n")
    _write(
        site / "rclpy" / "qos.py",
        "class QoSProfile:\n"
        "    def __init__(self, **kwargs): pass\n"
        "class ReliabilityPolicy:\n    RELIABLE = 1\n"
        "class DurabilityPolicy:\n    TRANSIENT_LOCAL = 1\n",
    )
    _write(site / "geometry_msgs" / "__init__.py", "")
    _write(
        site / "geometry_msgs" / "msg" / "__init__.py",
        "class PoseStamped: pass\n",
    )
    _write(site / "siminspect_interfaces" / "__init__.py", "")
    _write(
        site / "siminspect_interfaces" / "msg" / "__init__.py",
        "class AssetArray: pass\n"
        "class CandidateViewpoint: pass\n"
        "class CandidateViewpointArray: pass\n"
        "class MissionState: pass\n",
    )


def test_planner_cmake_registers_installed_import_contract():
    cmake = " ".join(
        (PACKAGE_ROOT.parent / "CMakeLists.txt").read_text(
            encoding="utf-8").split())
    assert "ament_add_pytest_test(test_installed_imports test/test_installed_imports.py)" in cmake


def test_candidate_p1_and_p2_import_from_isolated_package(tmp_path):
    site = tmp_path / "site"
    installed_package = site / "siminspect_viewpoint_planner"
    shutil.copytree(PACKAGE_ROOT, installed_package)
    _make_ros_stubs(site)

    module_names = [
        "siminspect_viewpoint_planner.candidate_generator",
        "siminspect_viewpoint_planner.p1_selector",
        "siminspect_viewpoint_planner.p2_selector",
    ]
    script = (
        "import importlib, json; "
        f"names={module_names!r}; "
        "print(json.dumps([importlib.import_module(name).__file__ "
        "for name in names]))"
    )
    assert "sys.path" not in script
    env = os.environ.copy()
    env["PYTHONPATH"] = str(site)
    completed = subprocess.run(
        [sys.executable, "-c", script],
        cwd=tmp_path,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    imported_paths = [Path(path).resolve()
                      for path in json.loads(completed.stdout)]
    assert all(path.is_relative_to(installed_package.resolve())
               for path in imported_paths)
