#!/usr/bin/env python3
"""Normalize Gazebo's scoped laser frame to the robot TF contract."""

from __future__ import annotations

import copy

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import LaserScan


def normalize_scan_frame(message: LaserScan, frame_id: str = "laser_link") -> LaserScan:
    """Return a copy whose frame is present in robot_state_publisher's TF tree."""
    normalized = LaserScan()
    normalized.header = copy.deepcopy(message.header)
    normalized.header.frame_id = frame_id
    normalized.angle_min = message.angle_min
    normalized.angle_max = message.angle_max
    normalized.angle_increment = message.angle_increment
    normalized.time_increment = message.time_increment
    normalized.scan_time = message.scan_time
    normalized.range_min = message.range_min
    normalized.range_max = message.range_max
    normalized.ranges = list(message.ranges)
    normalized.intensities = list(message.intensities)
    return normalized


class LaserScanFrameRelay(Node):
    def __init__(self) -> None:
        super().__init__("laser_scan_frame_relay")
        self.declare_parameter("input_topic", "/scan_raw")
        self.declare_parameter("output_topic", "/scan")
        self.declare_parameter("frame_id", "laser_link")
        input_topic = str(self.get_parameter("input_topic").value)
        output_topic = str(self.get_parameter("output_topic").value)
        self._frame_id = str(self.get_parameter("frame_id").value)
        self._publisher = self.create_publisher(LaserScan, output_topic, 10)
        self._subscription = self.create_subscription(
            LaserScan, input_topic, self._callback, 10
        )

    def _callback(self, message: LaserScan) -> None:
        self._publisher.publish(normalize_scan_frame(message, self._frame_id))


def main() -> None:
    rclpy.init()
    node = LaserScanFrameRelay()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
