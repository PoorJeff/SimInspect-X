import math
import os
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src" / "siminspect_benchmark" / "siminspect_benchmark"))
sys.path.insert(0, str(ROOT / "src" / "siminspect_bringup"))

from fault_injector import (  # noqa: E402
    build_f06_spawn_command,
    derive_f06_blocking_pose,
    wait_for_gazebo_create_service,
)
from siminspect_bringup.component_graph import build_component_graph  # noqa: E402
from siminspect_bringup.demo_config import load_demo_config  # noqa: E402


def test_f06_pose_is_derived_from_the_b0_fixed_viewpoint():
    x, y, yaw = derive_f06_blocking_pose((3.0, 1.8, math.pi), desired_distance_m=0.8)
    assert (x, y) == (2.2, 1.8)
    assert abs(yaw) < 1e-9
    command = build_f06_spawn_command("BLOCKING_BOX_SDF", (x, y, yaw))
    assert command == (
        "ros2", "run", "ros_gz_sim", "spawn_entity", "--name", "f06_blocking_box",
        "--sdf_filename", "BLOCKING_BOX_SDF", "--pos", "2.20", "1.80", "0.50",
        "--euler", "0.0", "0.0", "0.0",
    )


def test_f06_waits_for_the_bridged_create_service():
    class Result:
        stdout = "/clock\n/world/plant/create\n"

    assert wait_for_gazebo_create_service(timeout_s=0.01, poll_s=0.0, runner=lambda *args, **kwargs: Result())


def test_fault_scenario_uses_the_derived_pose_and_box_model():
    data = yaml.safe_load((ROOT / "src" / "siminspect_benchmark" / "config" / "fault_scenarios.yaml").read_text(encoding="utf-8"))
    f06 = next(item for item in data["scenarios"] if item["id"] == "F06")
    assert f06["params"]["occluder"] == "blocking_box"
    assert f06["params"]["occluder_pose"] == {"x": 2.2, "y": 1.8, "yaw": 0.0}
    assert (ROOT / "src" / "siminspect_benchmark" / "models" / "blocking_box" / "model.sdf").is_file()


def test_demo_graph_routes_vision_through_the_single_fault_relay():
    config = load_demo_config(ROOT / "config" / "demo_config.yaml")
    specs = {spec.name: spec for spec in build_component_graph(config, "headless", False, False, ROOT / "artifacts" / "runs" / "fault-unit")}
    assert "fault_image_relay" in specs
    assert "F00" in " ".join(specs["fault_image_relay"].argv)
    node_source = (ROOT / "src" / "siminspect_gauge_vision" / "siminspect_gauge_vision" / "gauge_vision_node.py").read_text(encoding="utf-8")
    assert '"/camera/image_faulted"' in node_source
    assert '"/camera/image_raw"' not in node_source
