#!/usr/bin/env python3
"""Generate candidate viewpoints from /inspection/assets using 07_ASSET_AND_VIEWPOINT_MODEL algorithm."""
import math, yaml
from ray_caster import RayCaster
import rclpy
from rclpy.node import Node
from siminspect_interfaces.msg import AssetArray, CandidateViewpoint, CandidateViewpointArray

class CandidateGenerator(Node):
    def __init__(self):
        super().__init__("candidate_generator")
        self.pub = self.create_publisher(CandidateViewpointArray, "/inspection/candidate_viewpoints", 10)
        self.sub = self.create_subscription(AssetArray, "/inspection/assets", self.on_assets, 10)

    def on_assets(self, msg: AssetArray):
        for asset in msg.assets:
            vps = self.generate(asset)
            arr = CandidateViewpointArray()
            arr.asset_id = asset.id
            arr.viewpoints = vps
            self.pub.publish(arr)
            self.get_logger().info(f"{asset.id}: {len(vps)} candidates")

    def generate(self, asset):
        """Generate N candidates on arc per 07_ASSET_AND_VIEWPOINT_MODEL.md."""
        px, py = asset.map_pose.position.x, asset.map_pose.position.y
        q = asset.map_pose.orientation
        yaw_g = 2 * math.atan2(q.z, q.w)
        d_desired = 0.8; N = 7; arc_deg = 120
        half = math.radians(arc_deg / 2)
        step = (2 * half) / (N - 1) if N > 1 else 0
        arc_center = yaw_g
        candidates = []
        for i in range(N):
            angle_i = arc_center - half + i * step
            x_i = px + d_desired * math.cos(angle_i)
            y_i = py + d_desired * math.sin(angle_i)
            yaw_i = angle_i + math.pi
            yaw_i = math.atan2(math.sin(yaw_i), math.cos(yaw_i))
            vp = CandidateViewpoint()
            vp.pose.position.x = x_i
            vp.pose.position.y = y_i
            vp.pose.position.z = 0.0
            vp.pose.orientation.z = math.sin(yaw_i / 2)
            vp.pose.orientation.w = math.cos(yaw_i / 2)
            vp.visible = True
            if hasattr(self, "caster"):
                vp.visible = self.caster.visible(x_i, y_i, px, py)
            vp.quality_score = 0.0
            candidates.append(vp)
        return candidates

def main():
    rclpy.init()
    rclpy.spin(CandidateGenerator())

if __name__ == '__main__':
    main()
