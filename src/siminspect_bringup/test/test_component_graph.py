from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src" / "siminspect_bringup"))
sys.path.insert(0, str(ROOT / "src" / "siminspect_benchmark"))

from siminspect_bringup.component_graph import ProcessSpec, build_component_graph
from siminspect_bringup.demo_config import load_demo_config
from siminspect_benchmark.ground_truth import select_robot_transform


def graph(mode="headless", record=False, benchmark_evidence=False, config=None):
    config = config or load_demo_config(ROOT / "config" / "demo_config.yaml")
    return build_component_graph(config, mode, record, benchmark_evidence,
                                 ROOT / "artifacts" / "runs" / "unit-run")


def by_name(specs):
    return {spec.name: spec for spec in specs}


def test_process_specs_are_immutable_and_headless_rejects_recording():
    spec = ProcessSpec("test", ("command",), Path("log"), ())
    with pytest.raises((AttributeError, TypeError)):
        spec.name = "other"
    with pytest.raises(ValueError, match="record"):
        graph(record=True)


def test_rejects_unknown_mode():
    with pytest.raises(ValueError, match="mode"):
        graph(mode="terminal")


def test_visual_adds_only_presentation_processes():
    headless = graph()
    visual = graph(mode="visual", record=True)
    headless_by_name = by_name(headless)
    visual_by_name = by_name(visual)

    assert tuple(spec for spec in visual if spec.name in headless_by_name) == headless
    assert set(visual_by_name) - set(headless_by_name) == {
        "gazebo_gui", "rviz", "recorder"}
    assert visual_by_name["recorder"].argv == (
        "python3", "-m", "siminspect_bringup.media_capture",
        "--run-dir", str(ROOT / "artifacts" / "runs" / "unit-run"),
    )


def test_autonomy_processes_include_all_run_contract_values():
    specs = by_name(graph())
    joined = "\n".join(" ".join(spec.argv) for spec in specs.values())

    for value in (
        "B0", "F00", "21", "pid", "unit-run", "mission_report.json",
        "gauge_pipe_01", "gauge_pipe_02", "gauge_pump_01",
        "gauge_tank_01", "gauge_tank_02", "gauge_valve_01",
    ):
        assert value in joined
    expected_assets = [arg for arg in specs["mission"].argv
                       if arg.startswith("expected_asset_ids:=")]
    assert expected_assets == [
        "expected_asset_ids:=[gauge_pipe_01,gauge_pipe_02,gauge_pump_01,"
        "gauge_tank_01,gauge_tank_02,gauge_valve_01]"
    ]
    assert specs["ekf"].name == "ekf"
    assert {
        "asset_registry", "candidate_generator", "vision", "selector",
        "precision_controller", "fault_injector", "mission",
    } <= set(specs)
    assert "include_ekf:=false" in specs["slam"].argv
    navigation_launch = (ROOT / "src" / "siminspect_navigation" / "launch" /
                         "navigation.launch.py").read_text(encoding="utf-8")
    assert "/launch/navigation_launch.py" in navigation_launch
    assert "publish_ground_truth:=false" in specs["simulation"].argv


def test_b0_and_p2_differ_only_by_selector_process(tmp_path):
    b0_config = load_demo_config(ROOT / "config" / "demo_config.yaml")
    p2_path = tmp_path / "p2.yaml"
    p2_path.write_text((ROOT / "config" / "demo_config.yaml").read_text().replace(
        "method: B0", "method: P2"), encoding="utf-8")
    p2_config = load_demo_config(p2_path)

    b0 = graph(config=b0_config)
    p2 = graph(config=p2_config)
    b0_without_selector = tuple(spec for spec in b0 if spec.name != "selector")
    p2_without_selector = tuple(spec for spec in p2 if spec.name != "selector")

    assert b0_without_selector == p2_without_selector
    assert by_name(b0)["selector"].argv != by_name(p2)["selector"].argv


def test_benchmark_evidence_alone_adds_ground_truth_processes():
    production = by_name(graph())
    benchmark = by_name(graph(benchmark_evidence=True))

    assert "benchmark_ground_truth" not in production
    assert "benchmark_recorder" not in production
    assert set(benchmark) - set(production) == {
        "benchmark_ground_truth", "benchmark_recorder"}
    assert benchmark["simulation"] == production["simulation"]
    assert benchmark["mission"] == production["mission"]
    assert benchmark["benchmark_recorder"].argv[:4] == (
        "ros2", "run", "siminspect_benchmark", "e4_evidence_recorder.py")


def test_ground_truth_selection_excludes_all_non_robot_transforms():
    class Transform:
        def __init__(self, child_frame_id):
            self.child_frame_id = child_frame_id

    robot = Transform("siminspect_amr")
    transforms = [Transform("conveyor"), robot, Transform("gauge_pipe_01")]

    assert select_robot_transform(transforms) is robot
    assert select_robot_transform([Transform("conveyor")]) is None


def test_robot_spawn_is_benchmark_gated_and_uses_pose_vector_bridge():
    launch = (ROOT / "src" / "siminspect_description" / "launch" /
              "robot_spawn.launch.py").read_text(encoding="utf-8")
    xacro = (ROOT / "src" / "siminspect_description" / "urdf" /
             "siminspect.gazebo.xacro").read_text(encoding="utf-8")
    publisher = (ROOT / "src" / "siminspect_benchmark" /
                 "siminspect_benchmark" / "ground_truth_publisher.py").read_text(
                     encoding="utf-8")

    assert 'DeclareLaunchArgument("publish_ground_truth", default_value="false")' in launch
    assert 'IfCondition(publish_ground_truth)' in launch
    assert "/model/siminspect_amr/pose@nav_msgs/msg/Odometry@gz.msgs.Pose" not in launch
    assert "/pose/info@tf2_msgs/msg/TFMessage[gz.msgs.Pose_V" in launch
    assert "/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock" in launch
    assert "/cmd_vel@geometry_msgs/msg/Twist]gz.msgs.Twist" in launch
    assert "PosePublisher" in xacro
    assert "use_pose_vector_msg" in xacro
    assert "<topic>/pose/info</topic>" in xacro
    assert "TFMessage" in publisher
    assert "select_robot_transform" in publisher
    assert "/benchmark_ground_truth/robot_pose" in publisher
