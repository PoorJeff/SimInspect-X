#!/usr/bin/env python3
"""B0 fixed-waypoint selector: centre candidate, no quality scorer."""
import math
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy
from geometry_msgs.msg import PoseStamped
from siminspect_interfaces.msg import AssetArray, MissionState

MISSION_STATE_QOS = QoSProfile(
    depth=1,
    reliability=ReliabilityPolicy.RELIABLE,
    durability=DurabilityPolicy.TRANSIENT_LOCAL,
)

class B0Selector(Node):
    def __init__(self):
        super().__init__("b0_selector")
        self.declare_parameter("method", "B0")
        self.pub = self.create_publisher(PoseStamped, "/inspection/selected_viewpoint", 10)
        self.asset_sub = self.create_subscription(
            AssetArray, "/inspection/assets", self.on_assets, 10)
        self.state_sub = self.create_subscription(
            MissionState, "/inspection/mission_state",
            self.on_mission_state, MISSION_STATE_QOS)
        self.assets = {}
        self._published_requests = set()
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
        pose = self.select_b0(asset)
        pose.header.stamp = request_stamp
        self._published_requests.add(request_key)
        self.pub.publish(pose)
        self.get_logger().info(
            f"B0 selected for {asset_id} request {request_id}")

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
