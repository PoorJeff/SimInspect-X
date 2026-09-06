#!/usr/bin/env python3
"""Evaluate localisation: time-matched position/yaw RMSE vs ground truth."""
import math, signal, sys, json
import rclpy
from rclpy.node import Node
from nav_msgs.msg import Odometry

def yaw(q): return math.atan2(2*(q.w*q.z+q.x*q.y), 1-2*(q.y*q.y+q.z*q.z))

class LocalisationEval(Node):
    def __init__(self):
        super().__init__("localisation_eval")
        self.gt_buf = []    # (stamp, pos, yaw)
        self.est_buf = []
        self.pairs = []     # (pos_err, yaw_err_deg)
        self.MAX_WINDOW = 0.2   # match within 200ms
        self.sub_gt = self.create_subscription(Odometry, "/benchmark_ground_truth/robot_pose", self.cb_gt, 10)
        self.sub_est = self.create_subscription(Odometry, "/odometry/filtered", self.cb_est, 10)
        self.get_logger().info("Localisation evaluator started. Ctrl-C to stop.")

    def cb_gt(self, m: Odometry):
        t = m.header.stamp.sec + m.header.stamp.nanosec*1e-9
        p = m.pose.pose.position
        self.gt_buf.append((t, (p.x, p.y), yaw(m.pose.pose.orientation)))

    def cb_est(self, m: Odometry):
        t = m.header.stamp.sec + m.header.stamp.nanosec*1e-9
        p = m.pose.pose.position
        self.est_buf.append((t, (p.x, p.y), yaw(m.pose.pose.orientation)))

    def match(self):
        """Pair GT and EKF messages within time window, compute errors."""
        while self.gt_buf and self.est_buf:
            gt_t = self.gt_buf[0][0]; est_t = self.est_buf[0][0]
            if abs(gt_t - est_t) <= self.MAX_WINDOW:
                gt = self.gt_buf.pop(0); est = self.est_buf.pop(0)
                dx = gt[1][0]-est[1][0]; dy = gt[1][1]-est[1][1]
                pe = math.sqrt(dx*dx+dy*dy)
                ye = abs(math.degrees(math.atan2(math.sin(gt[2]-est[2]), math.cos(gt[2]-est[2]))))
                self.pairs.append((pe, ye))
            elif gt_t < est_t: self.gt_buf.pop(0)
            else: self.est_buf.pop(0)

    def summary(self):
        self.match()
        n = len(self.pairs)
        if n == 0:
            self.get_logger().info("No matched pairs collected.")
            print(json.dumps({"samples": 0, "status": "no_data"}))
            return
        pos_rmse = math.sqrt(sum(p[0]**2 for p in self.pairs)/n)
        yaw_rmse = math.sqrt(sum(p[1]**2 for p in self.pairs)/n)
        result = {"samples": n, "position_rmse_m": round(pos_rmse,4), "yaw_rmse_deg": round(yaw_rmse,4)}
        self.get_logger().info(f"Pos RMSE: {pos_rmse:.4f} m, Yaw RMSE: {yaw_rmse:.4f} deg (n={n})")
        print(json.dumps(result))

def main():
    rclpy.init()
    node = LocalisationEval()
    while rclpy.ok():
        rclpy.spin_once(node, timeout_sec=0.05)
        node.match()
    node.summary()

if __name__ == '__main__':
    main()
