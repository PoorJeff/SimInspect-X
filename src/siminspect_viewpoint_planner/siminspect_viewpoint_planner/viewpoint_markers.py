#!/usr/bin/env python3
"""Publish RViz Marker arrows for candidate viewpoints. Green=visible, Red=blocked."""
import math
from builtin_interfaces.msg import Duration
from geometry_msgs.msg import Point
from visualization_msgs.msg import Marker, MarkerArray
from std_msgs.msg import ColorRGBA
import rclpy
from rclpy.node import Node
from siminspect_interfaces.msg import CandidateViewpointArray

GREEN = ColorRGBA(r=0.0, g=0.8, b=0.0, a=0.8)
RED   = ColorRGBA(r=0.9, g=0.1, b=0.1, a=0.8)
GREY  = ColorRGBA(r=0.5, g=0.5, b=0.5, a=0.5)

class ViewpointMarkers(Node):
    def __init__(self):
        super().__init__("viewpoint_markers")
        self.pub = self.create_publisher(MarkerArray, "/inspection/viewpoint_markers", 10)
        self.sub = self.create_subscription(CandidateViewpointArray, "/inspection/candidate_viewpoints", self.on_vps, 10)

    def on_vps(self, msg: CandidateViewpointArray):
        arr = MarkerArray()
        for i, vp in enumerate(msg.viewpoints):
            # Arrow marker
            a = Marker()
            a.header.frame_id = "map"
            a.ns = msg.asset_id
            a.id = i
            a.type = Marker.ARROW
            a.action = Marker.ADD
            a.pose = vp.pose
            a.scale.x = 0.3
            a.scale.y = 0.04
            a.scale.z = 0.04
            a.color = GREEN if vp.visible else RED
            a.lifetime = Duration(sec=10, nanosec=0)
            arr.markers.append(a)

            # Text label
            t = Marker()
            t.header.frame_id = "map"
            t.ns = msg.asset_id + "_label"
            t.id = i
            t.type = Marker.TEXT_VIEW_FACING
            t.action = Marker.ADD
            t.pose.position.x = vp.pose.position.x
            t.pose.position.y = vp.pose.position.y
            t.pose.position.z = 0.15
            t.scale.z = 0.12
            t.text = f"v{i}"
            t.color = GREY
            t.lifetime = Duration(sec=10, nanosec=0)
            arr.markers.append(t)
        self.pub.publish(arr)
        self.get_logger().info(f"Published {len(arr.markers)} markers for {msg.asset_id}")

def main():
    rclpy.init()
    rclpy.spin(ViewpointMarkers())

if __name__ == '__main__':
    main()
