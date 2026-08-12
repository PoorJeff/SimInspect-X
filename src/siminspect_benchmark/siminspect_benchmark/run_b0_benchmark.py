#!/usr/bin/env python3
"""B0 baseline benchmark: navigate, read, record. No candidate switching."""
import json, math, os, sys, time, yaml
import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from nav2_msgs.action import NavigateToPose
from geometry_msgs.msg import PoseStamped
from nav_msgs.msg import Odometry

class B0Benchmark(Node):
    def __init__(self):
        super().__init__("b0_benchmark")
        self.nav = ActionClient(self, NavigateToPose, "navigate_to_pose")
        self.gt_sub = self.create_subscription(Odometry, "/benchmark_ground_truth/robot_pose", self.cb_gt, 10)
        self.traj = []; self.start_pos = None
    def cb_gt(self, m: Odometry):
        p = m.pose.pose.position; self.traj.append((p.x, p.y))
    def navigate(self, goal_pose, timeout=120):
        g = PoseStamped(); g.header.frame_id = "map"; g.pose = goal_pose
        if not self.nav.wait_for_server(5): return False, 0, 0
        t0 = time.time(); f = self.nav.send_goal_async(g)
        rclpy.spin_until_future_complete(self, f, timeout_sec=5)
        if not f.done(): return False, time.time()-t0, 0
        gh = f.result()
        if not gh.accepted: return False, time.time()-t0, 0
        rf = gh.get_result_async()
        elapsed = time.time()-t0
        rclpy.spin_until_future_complete(self, rf, timeout_sec=max(timeout-elapsed, 1))
        dt = time.time()-t0; success = rf.done() and rf.result().result == 0
        pl = 0.0
        for i in range(1, len(self.traj)):
            pl += math.hypot(self.traj[i][0]-self.traj[i-1][0], self.traj[i][1]-self.traj[i-1][1])
        return success, dt, pl

def main():
    cfg = os.path.join(os.path.dirname(__file__), "..", "config", "b0_experiment.yaml")
    with open(cfg) as f: data = yaml.safe_load(f)
    rclpy.init(); node = B0Benchmark(); results = []
    for cond in data["conditions"]:
        g = cond["start"]
        success, dt, pl = node.navigate(PoseStamped(), 120)
        results.append({"id": cond["id"], "success": success, "duration_s": round(dt,2), "path_length_m": round(pl,3)})
    print(json.dumps({"experiment": "B0", "results": results}, indent=2))
    node.destroy_node(); rclpy.shutdown()

if __name__ == '__main__':
    main()
