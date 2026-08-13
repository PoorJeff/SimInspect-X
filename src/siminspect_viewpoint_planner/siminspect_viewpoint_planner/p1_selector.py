#!/usr/bin/env python3
"""P1 perception-aware selector: max Q(v,a) among V>0 candidates."""
import json
import math
import os
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PoseStamped
from siminspect_interfaces.msg import AssetArray
from quality_scorer import QualityScorer

class P1Selector(Node):
    def __init__(self):
        super().__init__("p1_selector")
        self.pub = self.create_publisher(PoseStamped, "/inspection/selected_viewpoint", 10)
        self.sub = self.create_subscription(AssetArray, "/inspection/assets", self.on_assets, 10)
        # P9-T03 ablation support: optional scorer weight override.
        self.declare_parameter("weights_json", "")
        weights = None
        wj = self.get_parameter("weights_json").value
        if not wj:
            wj = os.environ.get("SIMINSPECT_WEIGHTS", "")
        if wj:
            weights = json.loads(wj)
        self.scorer = QualityScorer(weights=weights)

    def on_assets(self, msg: AssetArray):
        for asset in msg.assets:
            v = self.select_p1(asset)
            if v is not None:
                self.pub.publish(v)
                self.get_logger().info(f"P1 selected for {asset.id}")

    def select_p1(self, asset):
        px, py = asset.map_pose.position.x, asset.map_pose.position.y
        q = asset.map_pose.orientation
        yaw_g = 2 * math.atan2(q.z, q.w)
        d_d = 0.8; N = 7; arc_deg = 120; th_max = math.radians(40)
        half = math.radians(arc_deg / 2)
        step = (2 * half) / (N - 1) if N > 1 else 0
        candidates = []
        for i in range(N):
            ai = yaw_g - half + i * step
            xi = px + d_d * math.cos(ai)
            yi = py + d_d * math.sin(ai)
            ywi = ai + math.pi
            ywi = math.atan2(math.sin(ywi), math.cos(ywi))
            # D score
            dist = math.hypot(xi - px, yi - py)
            Dv = self.scorer.score_D(dist)
            # A score
            th = abs(math.atan2(py - yi, px - xi) - ywi)
            if th > math.pi: th = 2*math.pi - th
            Av = self.scorer.score_A(th)
            # S score (default 1.0 when no costmap)
            Sv = 1.0
            # T: deferred to per-asset normalization below
            candidates.append((i, xi, yi, ywi, Dv, Av, Sv, 0.0))

        if not candidates: return None
        # T normalization and Q computation
        robot_x, robot_y = 0.0, 0.0  # defaults
        max_t = max(math.hypot(xp[1]-robot_x, xp[2]-robot_y) for xp in candidates)
        best_idx, best_Q = None, -1e9
        for i, xi, yi, ywi, Dv, Av, Sv, _ in candidates:
            tr = math.hypot(xi - robot_x, yi - robot_y)
            Tv = tr / max_t if max_t > 0 else 1.0
            Qv = self.scorer.w_vis * 1.0 + self.scorer.w_d * Dv + \
                 self.scorer.w_theta * Av + self.scorer.w_s * Sv - \
                 self.scorer.w_t * Tv
            if Qv > best_Q: best_Q = Qv; best_idx = i

        _, bx, by, byw, _, _, _, _ = candidates[best_idx]
        ps = PoseStamped(); ps.header.frame_id = "map"
        ps.pose.position.x = bx; ps.pose.position.y = by
        ps.pose.orientation.z = math.sin(byw / 2)
        ps.pose.orientation.w = math.cos(byw / 2)
        return ps

def main():
    rclpy.init()
    rclpy.spin(P1Selector())

if __name__ == '__main__':
    main()
