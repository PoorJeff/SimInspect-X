#!/usr/bin/env python3
"""Gauge vision ROS node (P10-T01; closes the P5 wiring debt).

Thin glue per D-007: subscribes /camera/image_raw and /inspection/mission_state,
runs the detector -> reader -> confidence pure pipeline, publishes
/inspection/gauge_reading. All logic lives in the pure modules.
"""
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from siminspect_interfaces.msg import GaugeReading, MissionState
from cv_bridge import CvBridge

try:
    from siminspect_gauge_vision.vision_pipeline import run_pipeline
except ImportError:
    from vision_pipeline import run_pipeline


class GaugeVisionNode(Node):
    def __init__(self):
        super().__init__("gauge_vision")
        self._bridge = CvBridge()
        self._sub_img = self.create_subscription(
            Image, "/camera/image_raw", self._cb_image, 10)
        self._sub_state = self.create_subscription(
            MissionState, "/inspection/mission_state", self._cb_state, 10)
        self._pub = self.create_publisher(
            GaugeReading, "/inspection/gauge_reading", 10)
        self._current_asset_id = ""

    def _cb_state(self, msg):
        self._current_asset_id = msg.current_asset_id

    def _cb_image(self, msg):
        img = self._bridge.imgmsg_to_cv2(msg, "bgr8")
        fields = run_pipeline(img, asset_id=self._current_asset_id)
        out = GaugeReading()
        out.asset_id = fields["asset_id"]
        out.estimated_value = fields["estimated_value"]
        out.unit = fields["unit"]
        out.confidence = fields["confidence"]
        out.target_pixel_area = fields["target_pixel_area"]
        out.view_angle_proxy = fields["view_angle_proxy"]
        self._pub.publish(out)


def main():
    rclpy.init()
    rclpy.spin(GaugeVisionNode())


if __name__ == "__main__":
    main()