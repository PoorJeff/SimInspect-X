#!/usr/bin/env python3
"""B0 fixed-waypoint selector: centre candidate, no quality scorer."""
import math
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PoseStamped
from siminspect_interfaces.msg import AssetArray

class B0Selector(Node):
    def __init__(self):
        super().__init__("b0_selector")
        self.pub = self.create_publisher(PoseStamped, "/inspection/selected_viewpoint", 10)
        self.sub = self.create_subscription(AssetArray, "/inspection/assets", self.on_assets, 10)

    def on_assets(self, msg: AssetArray):
        for asset in msg.assets:
            v = self.select_b0(asset)
            if v is not None:
                self.pub.publish(v)
                self.get_logger().info(f"B0 selected for {asset.id}")

    def select_b0(self, asset):
        px, py = asset.map_pose.position.x, asset.map_pose.position.y
        q = asset.map_pose.orientation
        yaw_g = 2 * math.atan2(q.z, q.w)
        d = 0.8  # desired_distance_m
        x = px + d * math.cos(yaw_g)
        y = py + d * math.sin(yaw_g)
        yaw_v = yaw_g + math.pi
        yaw_v = math.atan2(math.sin(yaw_v), math.cos(yaw_v))
        ps = PoseStamped()
        ps.header.frame_id = "map"
        ps.pose.position.x = x
        ps.pose.position.y = y
        ps.pose.position.z = 0.0
        ps.pose.orientation.z = math.sin(yaw_v / 2)
        ps.pose.orientation.w = math.cos(yaw_v / 2)
        return ps

def main():
    rclpy.init()
    rclpy.spin(B0Selector())

if __name__ == '__main__':
    main()
