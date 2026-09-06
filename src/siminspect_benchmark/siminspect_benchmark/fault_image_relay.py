#!/usr/bin/env python3
"""One camera relay shared by nominal and benchmark fault modes.

F00 is a byte-preserving pass-through.  F07 applies the declared Gaussian
blur to the frames consumed by the production vision node; no metadata-only
fault is accepted as evidence.
"""

from __future__ import annotations

import json
from typing import Any

import cv2
import numpy as np


class FaultImageRelay:
    def __init__(self, scenario: str, blur_sigma: float = 3.0) -> None:
        if scenario not in {"F00", "F07"}:
            raise ValueError("FaultImageRelay supports F00 and F07 only")
        self.scenario = scenario
        self.blur_sigma = float(blur_sigma)
        if self.blur_sigma <= 0:
            raise ValueError("blur_sigma must be positive")
        self.frames_seen = 0
        self.frames_modified = 0

    def transform(self, frame: np.ndarray) -> np.ndarray:
        if not isinstance(frame, np.ndarray) or frame.ndim < 2:
            raise TypeError("frame must be a numpy image array")
        self.frames_seen += 1
        if self.scenario == "F00":
            return frame.copy()
        self.frames_modified += 1
        return cv2.GaussianBlur(frame, (0, 0), sigmaX=self.blur_sigma)

    def state(self) -> dict[str, Any]:
        return {
            "scenario": self.scenario,
            "seed": None,
            "actuator": "fault_image_relay",
            "active": self.scenario == "F07",
            "evidence": {
                "frames_seen": self.frames_seen,
                "frames_modified": self.frames_modified,
            },
        }


def main() -> None:
    try:
        import rclpy
        from cv_bridge import CvBridge
        from rclpy.node import Node
        from sensor_msgs.msg import Image
        from std_msgs.msg import String
    except ImportError as exc:  # pragma: no cover - exercised only outside ROS
        raise RuntimeError("fault_image_relay requires the ROS runtime") from exc

    class RelayNode(Node):
        def __init__(self) -> None:
            super().__init__("fault_image_relay")
            self.declare_parameter("scenario", "F00")
            self.declare_parameter("seed", -1)
            scenario = str(self.get_parameter("scenario").value)
            self.relay = FaultImageRelay(scenario)
            self.relay.state()["seed"] = int(self.get_parameter("seed").value)
            self.bridge = CvBridge()
            self.pub = self.create_publisher(Image, "/camera/image_faulted", 10)
            self.state_pub = self.create_publisher(String, "/benchmark/fault_state", 10)
            self.sub = self.create_subscription(Image, "/camera/image_raw", self.on_image, 10)

        def on_image(self, msg: Image) -> None:
            image = self.bridge.imgmsg_to_cv2(msg, desired_encoding="passthrough")
            output = self.relay.transform(image)
            out_msg = self.bridge.cv2_to_imgmsg(output, encoding=msg.encoding)
            out_msg.header = msg.header
            self.pub.publish(out_msg)
            state = self.relay.state()
            state["seed"] = int(self.get_parameter("seed").value)
            state_msg = String()
            state_msg.data = json.dumps(state, sort_keys=True)
            self.state_pub.publish(state_msg)

    rclpy.init()
    node = RelayNode()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
