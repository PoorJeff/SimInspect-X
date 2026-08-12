#!/usr/bin/env python3
"""Subscribe bridged Gazebo pose and republish as /benchmark_ground_truth/robot_pose."""
import rclpy
from rclpy.node import Node
from nav_msgs.msg import Odometry

class GroundTruthPublisher(Node):
    def __init__(self):
        super().__init__("ground_truth_publisher")
        self.pub = self.create_publisher(Odometry, "/benchmark_ground_truth/robot_pose", 10)
        self.sub = self.create_subscription(Odometry, "/model/siminspect_amr/pose", self.cb, 10)
        self.get_logger().info("Ground truth publisher started")

    def cb(self, msg: Odometry):
        msg.header.frame_id = "map"
        msg.child_frame_id = "base_link"
        self.pub.publish(msg)

def main():
    rclpy.init()
    rclpy.spin(GroundTruthPublisher())

if __name__ == '__main__':
    main()
