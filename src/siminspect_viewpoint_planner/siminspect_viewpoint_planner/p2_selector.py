#!/usr/bin/env python3
"""P2 selector: request-driven P1 with per-asset candidate history."""
import json
import math
import os
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy
from geometry_msgs.msg import PoseStamped
from siminspect_interfaces.msg import AssetArray, MissionState

try:
    from siminspect_viewpoint_planner.quality_scorer import QualityScorer
except ImportError:  # Source-tree script execution fallback.
    from quality_scorer import QualityScorer

MISSION_STATE_QOS = QoSProfile(
    depth=1,
    reliability=ReliabilityPolicy.RELIABLE,
    durability=DurabilityPolicy.TRANSIENT_LOCAL,
)

class P2Selector(Node):
    def __init__(self):
        super().__init__("p2_selector")
        self.declare_parameter("method", "P2")
        self.pub = self.create_publisher(PoseStamped, "/inspection/selected_viewpoint", 10)
        self.asset_sub = self.create_subscription(AssetArray, "/inspection/assets", self.on_assets, 10)
        self.state_sub = self.create_subscription(
            MissionState, "/inspection/mission_state",
            self.on_mission_state, MISSION_STATE_QOS)
        # P9-T03 ablation support: scorer weights + re-inspection toggle.
        self.declare_parameter("weights_json", "")
        self.declare_parameter("enable_reinspect", True)
        weights = None
        wj = self.get_parameter("weights_json").value
        if not wj:
            wj = os.environ.get("SIMINSPECT_WEIGHTS", "")
        if wj:
            weights = json.loads(wj)
        self.scorer = QualityScorer(weights=weights)
        self.enable_reinspect = (
            self.get_parameter("enable_reinspect").value)
        if "SIMINSPECT_REINSPECT" in os.environ:
            self.enable_reinspect = (
                os.environ["SIMINSPECT_REINSPECT"].lower() == "true")
        self.assets = {}
        self._published_requests = set()
        self._published_indices = {}
        self._pending_request = None

    def on_assets(self, msg: AssetArray):
        for asset in msg.assets:
            self.assets[asset.id] = asset
        self._try_publish_pending()

    def on_mission_state(self, msg: MissionState):
        if msg.state != "SELECT_VIEWPOINT" or not msg.current_asset_id:
            self._pending_request = None
            return
        self._pending_request = (
            msg.current_asset_id, int(msg.request_id), msg.timestamp)
        self._try_publish_pending()

    def _try_publish_pending(self):
        if self._pending_request is None:
            return
        asset_id, request_id, request_stamp = self._pending_request
        request_key = (asset_id, request_id)
        if request_key in self._published_requests:
            return
        asset = self.assets.get(asset_id)
        if asset is None:
            return

        blacklist = (self._published_indices.get(asset_id, [])
                     if self.enable_reinspect else [])
        result = self.select_for_asset(asset, blacklist)
        self._published_requests.add(request_key)
        if result is None:
            self.get_logger().warn(f"No remaining candidates for {asset_id}")
            return
        idx, pose = result
        pose.header.stamp = request_stamp
        self._published_indices.setdefault(asset_id, []).append(idx)
        self.pub.publish(pose)
        self.get_logger().info(
            f"P2 selected candidate {idx} for {asset_id} request {request_id}")

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
            Dv = self.scorer.score_D(dist)
            th = abs(math.atan2(py - yi, px - xi) - ywi)
            if th > math.pi: th = 2*math.pi - th
            Av = self.scorer.score_A(th)
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
            Qv = self.scorer.w_vis * 1.0 + self.scorer.w_d * Dv + \
                 self.scorer.w_theta * Av + self.scorer.w_s * Sv - \
                 self.scorer.w_t * Tv
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

def main():
    rclpy.init()
    rclpy.spin(P2Selector())

if __name__ == '__main__':
    main()
