#!/usr/bin/env python3
"""Fault injection node (P9-T01).

Loads fault_scenarios.yaml, selects a scenario, applies the seed override,
logs scenario+seed, publishes /benchmark/fault_state, and
dispatches to per-fault handlers.

F06 is an owned Gazebo entity actuator and F07's frame mutation is implemented
by the shared image relay. Other scenarios retain their documented scope.
"""
import json
import math
import os
import subprocess
import time


def derive_f06_blocking_pose(asset_pose, desired_distance_m=0.8):
    """Return the B0 fixed-viewpoint pose for the pump gauge."""
    if isinstance(asset_pose, dict):
        x, y, yaw = asset_pose["x"], asset_pose["y"], asset_pose["yaw"]
    else:
        x, y, yaw = asset_pose
    x = float(x) + float(desired_distance_m) * math.cos(float(yaw))
    y = float(y) + float(desired_distance_m) * math.sin(float(yaw))
    viewpoint_yaw = math.atan2(math.sin(float(yaw) + math.pi), math.cos(float(yaw) + math.pi))
    if abs(viewpoint_yaw) < 1e-9:
        viewpoint_yaw = 0.0
    return round(x, 3), round(y, 3), round(viewpoint_yaw, 3)


def build_f06_spawn_command(sdf_filename, viewpoint_pose, z=0.5):
    """Build the exact ros_gz_sim command used by the owned F06 actuator."""
    x, y, _ = viewpoint_pose
    return (
        "ros2", "run", "ros_gz_sim", "spawn_entity", "--name", "f06_blocking_box",
        "--sdf_filename", str(sdf_filename), "--pos", f"{float(x):.2f}",
        f"{float(y):.2f}", f"{float(z):.2f}", "--euler", "0.0", "0.0", "0.0",
    )


def wait_for_gazebo_create_service(timeout_s=30.0, poll_s=0.5, runner=subprocess.run):
    """Wait until ros_gz_bridge exposes the world create service."""
    deadline = time.monotonic() + float(timeout_s)
    while time.monotonic() < deadline:
        result = runner(("ros2", "service", "list"), capture_output=True,
                        text=True, check=False)
        if "/world/plant/create" in result.stdout.splitlines():
            return True
        time.sleep(float(poll_s))
    return False

try:
    import rclpy
    from rclpy.node import Node
    from std_msgs.msg import String
    from ament_index_python.packages import get_package_share_directory
except ImportError:  # pure helpers remain importable on the Windows host
    rclpy = None
    Node = object
    String = None
    get_package_share_directory = None

try:
    from siminspect_benchmark.fault_scenarios import (
        SCENARIO_IDS, load_scenarios, validate_all, resolve_seed,
        deterministic_noise,
    )
except ImportError:
    from fault_scenarios import (
        SCENARIO_IDS, load_scenarios, validate_all, resolve_seed,
        deterministic_noise,
    )


class FaultInjector(Node):
    def __init__(self):
        super().__init__("fault_injector")
        self.declare_parameter("scenario", "F00")
        self.declare_parameter("seed", -1)  # -1 = use scenario default
        self.declare_parameter("config_file", "")

        self._state_pub = self.create_publisher(
            String, "/benchmark/fault_state", 10)

        scenario_id = self.get_parameter("scenario").value
        seed_override = self.get_parameter("seed").value
        config_file = self.get_parameter("config_file").value
        if not config_file:
            config_file = os.path.join(
                get_package_share_directory("siminspect_benchmark"),
                "config", "fault_scenarios.yaml")

        scenarios = load_scenarios(config_file)
        errors = validate_all(scenarios)
        if errors:
            for e in errors:
                self.get_logger().error(f"fault config error: {e}")
            raise ValueError("invalid fault_scenarios.yaml: " + "; ".join(errors))

        by_id = {sc["id"]: sc for sc in scenarios}
        if scenario_id not in by_id:
            raise ValueError(
                f"unknown scenario '{scenario_id}'; expected one of {SCENARIO_IDS}")

        self.scenario = by_id[scenario_id]
        if seed_override >= 0:
            self.scenario = resolve_seed(self.scenario, seed_override)
        self.seed = self.scenario["seed"]

        self._f06_spawned = False
        self._f06_model = None
        self.get_logger().info(
            f"Fault injector active: scenario={scenario_id} "
            f"seed={self.seed} name={self.scenario['name']}")
        self._publish_state(
            scenario=scenario_id,
            actuator="fault_image_relay" if scenario_id == "F07" else ("gazebo_spawn" if scenario_id == "F06" else "none"),
            active=scenario_id in {"F06", "F07"},
            evidence={},
        )

        self._apply_scenario(scenario_id)

    def _publish_state(self, *, scenario, actuator, active, evidence):
        msg = String()
        msg.data = json.dumps({
            "scenario": scenario,
            "seed": self.seed,
            "actuator": actuator,
            "active": active,
            "evidence": evidence,
        }, sort_keys=True)
        self._state_pub.publish(msg)

    # -- per-scenario dispatch -----------------------------------------

    def _apply_scenario(self, sid):
        p = self.scenario["params"]
        if sid == "F00":
            return  # nominal: no fault
        if sid == "F01":
            self._odom_noise = deterministic_noise(
                self.seed, 1000, p["linear_std"])
            self.get_logger().info("F01: odometry noise sequence prepared")
        elif sid == "F02":
            self._slip = p["slip_factor"]
            self.get_logger().info(f"F02: wheel slip factor {self._slip}")
        elif sid == "F03":
            self._imu_noise = deterministic_noise(
                self.seed, 1000, p["accel_std"])
            self.get_logger().info("F03: imu noise sequence prepared")
        elif sid == "F04":
            self._dropout = (p["window_s"], p["period_s"])
            self.get_logger().info("F04: lidar dropout schedule prepared")
        elif sid == "F05":
            # TODO(P9-T02): spawn dynamic obstacle via Gazebo service
            self.get_logger().warn(
                "F05 dynamic_obstacle: actuator stub, not wired (P9-T02)")
        elif sid == "F06":
            self._spawn_f06_box()
        elif sid == "F07":
            self._blur = p["blur_sigma"]
            self.get_logger().info(f"F07: blur sigma {self._blur}")
        elif sid == "F08":
            self._dark = p["brightness_factor"]
            self.get_logger().info(f"F08: brightness factor {self._dark}")
        elif sid == "F09":
            # TODO(P9-T02): spawn gauge-face occluder via Gazebo service
            self.get_logger().warn(
                "F09 gauge_partial_occlusion: actuator stub, not wired (P9-T02)")
        elif sid == "F10":
            # TODO(P9-T02): apply spawn pose offset via launch/spawn service
            self.get_logger().warn(
                "F10 initial_pose_offset: actuator stub, not wired (P9-T02)")
        elif sid == "F11":
            self._slip = p["slip_factor"]
            self._imu_noise = deterministic_noise(
                self.seed, 1000, p["imu_accel_std"])
            self._dark = p["brightness_factor"]
            self.get_logger().info("F11: mixed stress factors prepared")

    def _spawn_f06_box(self):
        pkg = get_package_share_directory("siminspect_benchmark")
        sdf = os.path.join(pkg, "models", "blocking_box", "model.sdf")
        pose = derive_f06_blocking_pose((3.0, 1.8, math.pi))
        command = build_f06_spawn_command(sdf, pose)
        if not wait_for_gazebo_create_service():
            raise RuntimeError("F06 spawn refused: /world/plant/create is not bridged")
        result = subprocess.run(command, capture_output=True, text=True, timeout=30, check=False)
        evidence = {
            "command": list(command),
            "returncode": result.returncode,
            "stdout": result.stdout[-500:],
            "stderr": result.stderr[-500:],
            "spawned": result.returncode == 0,
            "model": "blocking_box",
        }
        self._f06_spawned = bool(evidence["spawned"])
        self._f06_model = "blocking_box"
        self._publish_state(scenario="F06", actuator="gazebo_spawn", active=self._f06_spawned, evidence=evidence)
        if not self._f06_spawned:
            raise RuntimeError(f"F06 spawn failed: {evidence}")

    def destroy_node(self):
        if getattr(self, "_f06_spawned", False):
            subprocess.run(
                ("ros2", "run", "ros_gz_sim", "delete_entity", "--name", "f06_blocking_box"),
                capture_output=True, text=True, timeout=30, check=False,
            )
            self._f06_spawned = False
        return super().destroy_node()


def main():
    if rclpy is None:
        raise RuntimeError("FaultInjector requires the ROS runtime")
    rclpy.init()
    try:
        node = FaultInjector()
    except ValueError as exc:
        print(f"FaultInjector aborted: {exc}", flush=True)
        rclpy.shutdown()
        return
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
