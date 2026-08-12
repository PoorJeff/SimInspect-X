#!/usr/bin/env python3
"""Asset registry: loads gauge YAML files and publishes /inspection/assets."""
import os, yaml, math
import rclpy
from rclpy.node import Node
from ament_index_python.packages import get_package_share_directory
from siminspect_interfaces.msg import Asset, AssetArray

class AssetRegistry(Node):
    def __init__(self):
        super().__init__("asset_registry")
        self.pub = self.create_publisher(AssetArray, "/inspection/assets", 10)
        self.timer = self.create_timer(1.0, self.publish)
        self.assets = self.load()

    def load(self):
        pkg = get_package_share_directory("siminspect_assets")
        d = os.path.join(pkg, "assets")
        assets = []
        if not os.path.isdir(d):
            self.get_logger().error("Assets dir not found: "+d)
            return assets
        for f in sorted(os.listdir(d)):
            if not f.endswith(".yaml"): continue
            data = yaml.safe_load(open(os.path.join(d,f)))
            a = Asset()
            a.id = data["id"]; a.asset_type = data["asset_type"]
            mp = data["map_pose"]
            a.map_pose.position.x = mp["x"]
            a.map_pose.position.y = mp["y"]
            a.map_pose.position.z = mp["z"]
            yaw = mp["yaw"]
            a.map_pose.orientation.z = math.sin(yaw/2)
            a.map_pose.orientation.w = math.cos(yaw/2)
            a.min_value = data["gauge"]["min_value"]
            a.max_value = data["gauge"]["max_value"]
            a.unit = data["gauge"]["unit"]
            assets.append(a)
            self.get_logger().info("Loaded "+a.id)
        self.get_logger().info("Total assets: "+str(len(assets)))
        return assets

    def publish(self):
        self.pub.publish(AssetArray(assets=self.assets))

def main():
    rclpy.init()
    rclpy.spin(AssetRegistry())

if __name__ == "__main__":
    main()
