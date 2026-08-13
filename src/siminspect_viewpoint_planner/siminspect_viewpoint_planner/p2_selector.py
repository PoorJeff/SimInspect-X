#!/usr/bin/env python3
"""P2 adaptive selector: P1 + confidence-triggered re-inspection. Max 3 attempts."""
import json
import math
import os
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PoseStamped
from siminspect_interfaces.msg import GaugeReading, AssetArray
from p1_selector import P1Selector

CONF_THRESHOLD = 0.80
MAX_ATTEMPTS = 3

class P2Selector(Node):
    def __init__(self):
        super().__init__("p2_selector")
        self.pub = self.create_publisher(PoseStamped, "/inspection/selected_viewpoint", 10)
        self.asset_sub = self.create_subscription(AssetArray, "/inspection/assets", self.on_assets, 10)
        self.reader_sub = self.create_subscription(GaugeReading, "/inspection/gauge_reading", self.on_reading, 10)
        self.p1 = P1Selector.__new__(P1Selector)
        # P9-T03 ablation support: scorer weights + re-inspection toggle.
        self.declare_parameter("weights_json", "")
        self.declare_parameter("enable_reinspect", True)
        weights = None
        wj = self.get_parameter("weights_json").value
        if not wj:
            wj = os.environ.get("SIMINSPECT_WEIGHTS", "")
        if wj:
            weights = json.loads(wj)
        self.p1.scorer = __import__("quality_scorer").QualityScorer(
            weights=weights)
        self.enable_reinspect = (
            self.get_parameter("enable_reinspect").value)
        if "SIMINSPECT_REINSPECT" in os.environ:
            self.enable_reinspect = (
                os.environ["SIMINSPECT_REINSPECT"].lower() == "true")
        self.assets = {}
        self.blacklist = []
        self.attempt = 0
        self.current_asset_id = None

    def on_assets(self, msg: AssetArray):
        for asset in msg.assets:
            self.assets[asset.id] = asset
            self.current_asset_id = asset.id
            self.blacklist = []
            self.attempt = 0
            result = self.select_for_asset(asset, self.blacklist)
            if result is not None:
                idx, ps = result
                self.blacklist.append(idx)
                self.pub.publish(ps)
                self.get_logger().info(f"P2 initial selection for {asset.id}: candidate {idx}")

    def on_reading(self, msg: GaugeReading):
        if not self.enable_reinspect:
            return  # A4: re-inspection disabled (P1-equivalent)
        if msg.confidence >= CONF_THRESHOLD:
            self.get_logger().info(f"P2 reading ok for {msg.asset_id}: conf={msg.confidence:.2f}")
            return
        if self.attempt >= MAX_ATTEMPTS:
            self.get_logger().warn(f"P2 max attempts ({MAX_ATTEMPTS}) reached for {msg.asset_id}")
            return
        self.attempt += 1
        self.get_logger().info(f"P2 re-inspection attempt {self.attempt}/{MAX_ATTEMPTS} for {msg.asset_id}")
        result = self._select_next_best()
        if result is not None:
            self.pub.publish(result)

    def select_for_asset(self, asset, blacklist):
        px, py = asset.map_pose.position.x, asset.map_pose.position.y
        q = asset.map_pose.orientation
        yaw_g = 2 * math.atan2(q.z, q.w)
        d_d = 0.8; N = 7; arc_deg = 120; th_max = math.radians(40)
        half = math.radians(arc_deg / 2)
        step = (2 * half) / (N - 1) if N > 1 else 0
        bl_set = set(blacklist)
        candidates = []
        for i in range(N):
            if i in bl_set:
                continue
            ai = yaw_g - half + i * step
            xi = px + d_d * math.cos(ai)
            yi = py + d_d * math.sin(ai)
            ywi = ai + math.pi
            ywi = math.atan2(math.sin(ywi), math.cos(ywi))
            dist = math.hypot(xi - px, yi - py)
            Dv = self.p1.scorer.score_D(dist)
            th = abs(math.atan2(py - yi, px - xi) - ywi)
            if th > math.pi: th = 2*math.pi - th
            Av = self.p1.scorer.score_A(th)
            Sv = 1.0
            candidates.append((i, xi, yi, ywi, Dv, Av, Sv, 0.0))

        if not candidates:
            return None

        robot_x, robot_y = 0.0, 0.0
        max_t = max(math.hypot(xp[1]-robot_x, xp[2]-robot_y) for xp in candidates)
        best_idx, best_Q = None, -1e9
        best_data = None
        for c in candidates:
            i, xi, yi, ywi, Dv, Av, Sv, _ = c
            tr = math.hypot(xi - robot_x, yi - robot_y)
            Tv = tr / max_t if max_t > 0 else 1.0
            Qv = self.p1.scorer.w_vis * 1.0 + self.p1.scorer.w_d * Dv + \
                 self.p1.scorer.w_theta * Av + self.p1.scorer.w_s * Sv - \
                 self.p1.scorer.w_t * Tv
            if Qv > best_Q:
                best_Q = Qv
                best_idx = i
                best_data = (xi, yi, ywi)

        if best_idx is None:
            return None

        bx, by, byw = best_data
        ps = PoseStamped()
        ps.header.frame_id = "map"
        ps.pose.position.x = bx; ps.pose.position.y = by
        ps.pose.orientation.z = math.sin(byw / 2)
        ps.pose.orientation.w = math.cos(byw / 2)
        return (best_idx, ps)

    def _select_next_best(self):
        if self.current_asset_id is None or self.current_asset_id not in self.assets:
            self.get_logger().error("No current asset for re-inspection")
            return None
        asset = self.assets[self.current_asset_id]
        result = self.select_for_asset(asset, self.blacklist)
        if result is None:
            self.get_logger().warn(f"No remaining candidates for {self.current_asset_id}")
            return None
        idx, ps = result
        self.blacklist.append(idx)
        self.get_logger().info(f"P2 selected candidate {idx} for {self.current_asset_id}")
        return ps

def main():
    rclpy.init()
    rclpy.spin(P2Selector())

if __name__ == '__main__':
    main()