#!/usr/bin/env python3
"""Fault injection node (P9-T01).

Loads fault_scenarios.yaml, selects a scenario, applies the seed override,
logs scenario+seed, publishes /benchmark/fault_state, and
dispatches to per-fault handlers.

Honest scope (T01): compute-style faults (F01-F04, F07, F08) prepare
deterministic perturbation sequences from the seed. World/service-level
faults (F05, F06, F09, F10) are documented actuator stubs to be wired by the
experiment runner (P9-T02) on the Ubuntu/Gazebo host.
"""
import os

import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from ament_index_python.packages import get_package_share_directory

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

        self.get_logger().info(
            f"Fault injector active: scenario={scenario_id} "
            f"seed={self.seed} name={self.scenario['name']}")
        self._publish_state(f"active scenario={scenario_id} seed={self.seed}")

        self._apply_scenario(scenario_id)

    def _publish_state(self, text):
        msg = String()
        msg.data = text
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
            # TODO(P9-T02): spawn occluder at the fixed viewpoint
            self.get_logger().warn(
                "F06 blocked_fixed_viewpoint: actuator stub, not wired (P9-T02)")
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


def main():
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