#!/usr/bin/env python3
"""Normalize Gazebo-scoped odometry frame ids for the ROS navigation stack."""

import rclpy
from nav_msgs.msg import Odometry
from rclpy.node import Node


def normalize_frame_id(frame_id: str) -> str:
    """Remove the Gazebo model scope while preserving already-normalized ids."""
    prefix = "siminspect_amr/"
    return frame_id[len(prefix):] if frame_id.startswith(prefix) else frame_id


def normalize_odometry_frames(msg: Odometry) -> Odometry:
    """Normalize the odometry and child frame ids in-place and return the message."""
    msg.header.frame_id = normalize_frame_id(msg.header.frame_id)
    msg.child_frame_id = normalize_frame_id(msg.child_frame_id)
    return msg


class OdometryFrameRelay(Node):
    def __init__(self) -> None:
        super().__init__("odometry_frame_relay")
        self._pub = self.create_publisher(Odometry, "/wheel/odometry_normalized", 10)
        self._sub = self.create_subscription(
            Odometry, "/wheel/odometry", self._on_odometry, 10
        )

    def _on_odometry(self, msg: Odometry) -> None:
        self._pub.publish(normalize_odometry_frames(msg))


def main() -> None:
    rclpy.init()
    node = OdometryFrameRelay()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
