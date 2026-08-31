#!/usr/bin/env python3
"""Extract the robot transform for benchmark-only ground-truth evaluation."""
import rclpy
from rclpy.node import Node
from nav_msgs.msg import Odometry
from tf2_msgs.msg import TFMessage

from siminspect_benchmark.ground_truth import select_robot_transform

class GroundTruthPublisher(Node):
    def __init__(self):
        super().__init__("ground_truth_publisher")
        self.pub = self.create_publisher(Odometry, "/benchmark_ground_truth/robot_pose", 10)
        self.sub = self.create_subscription(TFMessage, "/pose/info", self.cb, 10)
        self.get_logger().info("Ground truth publisher started")

    def cb(self, msg: TFMessage):
        transform = select_robot_transform(msg.transforms)
        if transform is None:
            return
        robot_pose = Odometry()
        robot_pose.header = transform.header
        robot_pose.child_frame_id = "base_link"
        robot_pose.pose.pose.position.x = transform.transform.translation.x
        robot_pose.pose.pose.position.y = transform.transform.translation.y
        robot_pose.pose.pose.position.z = transform.transform.translation.z
        robot_pose.pose.pose.orientation = transform.transform.rotation
        self.pub.publish(robot_pose)

def main():
    rclpy.init()
    rclpy.spin(GroundTruthPublisher())

if __name__ == '__main__':
    main()
