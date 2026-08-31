"""Single source of truth for headless and visual demo components."""
from dataclasses import dataclass
from pathlib import Path

from .demo_config import DemoConfig


@dataclass(frozen=True)
class ProcessSpec:
    name: str
    argv: tuple[str, ...]
    log_path: Path
    env: tuple[tuple[str, str], ...]


def build_component_graph(
    config: DemoConfig,
    mode: str,
    record: bool,
    benchmark_evidence: bool,
    run_dir: Path,
) -> tuple[ProcessSpec, ...]:
    """Return the exact process graph without launching any process."""
    if mode not in {"headless", "visual"}:
        raise ValueError("mode must be 'headless' or 'visual'")
    if record and mode != "visual":
        raise ValueError("record=True requires visual mode")

    run_dir = Path(run_dir)
    run_id = run_dir.name
    env = (("ROS_LOG_DIR", str(run_dir / "ros_logs")),)

    def process(name: str, *argv: str) -> ProcessSpec:
        return ProcessSpec(name, tuple(argv), run_dir / f"{name}.log", env)

    assets = (f"expected_asset_ids:=[{','.join(config.mission_assets)}]",)
    autonomy = (
        process("simulation", "ros2", "launch", "siminspect_description",
                "robot_spawn.launch.py", f"world:={config.world}", "gui:=false",
                f"publish_ground_truth:={'true' if benchmark_evidence else 'false'}"),
        process("ekf", "ros2", "launch", "siminspect_localization", "ekf.launch.py"),
        process("slam", "ros2", "launch", "siminspect_localization", "slam.launch.py"),
        process("navigation", "ros2", "launch", "siminspect_navigation", "navigation.launch.py"),
        process("selector", "ros2", "run", "siminspect_viewpoint_planner",
                "b0_selector.py" if config.method == "B0" else "p2_selector.py",
                "--ros-args", "-p", f"method:={config.method}"),
        process("precision_controller", "ros2", "run", "siminspect_precision_control",
                "controller_interface.py", "--ros-args", "-p",
                f"controller_type:={config.controller}"),
        process("fault_injector", "ros2", "run", "siminspect_benchmark",
                "fault_injector.py", "--ros-args", "-p",
                f"scenario:={config.scenario}", "-p", f"seed:={config.seed}"),
        process("mission", "ros2", "run", "siminspect_mission", "mission_executor.py",
                "--ros-args", "-p", f"ordering:={config.ordering}", "-p",
                f"run_id:={run_id}", "-p",
                f"report_path:={run_dir / 'mission_report.json'}", "-p",
                f"readiness_timeout_s:={config.readiness_timeout_s}", "-p",
                f"mission_timeout_s:={config.mission_timeout_s}", "-p", *assets),
    )
    specs = autonomy
    if benchmark_evidence:
        specs += (
            process("benchmark_ground_truth", "ros2", "run", "siminspect_benchmark",
                    "ground_truth_publisher.py"),
            process("benchmark_recorder", "ros2", "bag", "record", "-o",
                    str(run_dir / "benchmark"), "/benchmark_ground_truth/robot_pose"),
        )
    if mode == "visual":
        specs += (
            process("gazebo_gui", "gz", "sim", "-g"),
            process("rviz", "rviz2"),
        )
        if record:
            specs += (process("recorder", "ros2", "bag", "record", "-a", "-o",
                              str(run_dir / "visual_recording")),)
    return specs
