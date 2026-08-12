#!/usr/bin/env python3
"""E2 Navigation benchmark: run scenarios, record metrics, output JSON."""
import json, math, os, sys, time, yaml
import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from nav2_msgs.action import NavigateToPose
from nav_msgs.msg import Odometry
from geometry_msgs.msg import PoseStamped, Point

class NavBenchmark(Node):
    def __init__(self):
        super().__init__("nav_benchmark")
        self.client = ActionClient(self, NavigateToPose, "navigate_to_pose")
        self.gt_sub = self.create_subscription(Odometry, "/benchmark_ground_truth/robot_pose", self.cb_gt, 10)
        self.trajectory = []
        self.start_time = None
        self.result = None

    def cb_gt(self, msg: Odometry):
        p = msg.pose.pose.position
        self.trajectory.append((p.x, p.y))

    def run(self, scenario: dict) -> dict:
        self.trajectory = []
        timeout = scenario.get("timeout_s", 120)

        goal = PoseStamped()
        goal.header.frame_id = "map"
        g = scenario["goal"]
        goal.pose.position.x = g["x"]
        goal.pose.position.y = g["y"]
        yaw_goal = g.get("yaw", 0)
        goal.pose.orientation.z = math.sin(yaw_goal/2)
        goal.pose.orientation.w = math.cos(yaw_goal/2)

        if not self.client.wait_for_server(timeout_sec=5.0):
            return {"id": scenario["id"], "success": False, "error": "Action server unavailable"}

        self.start_time = time.time()
        self.get_logger().info(f"Starting {scenario["id"]} -> ({g["x"]}, {g["y"]})")
        future = self.client.send_goal_async(goal)
        rclpy.spin_until_future_complete(self, future, timeout_sec=5.0)
        if not future.done():
            return {"id": scenario["id"], "success": False, "error": "Goal rejected"}
        goal_handle = future.result()
        if not goal_handle.accepted:
            return {"id": scenario["id"], "success": False, "error": "Goal not accepted"}

        result_future = goal_handle.get_result_async()
        elapsed = time.time() - self.start_time
        remaining = max(timeout - elapsed, 0)
        rclpy.spin_until_future_complete(self, result_future, timeout_sec=remaining+1)

        dt = time.time() - self.start_time
        success = result_future.done() and result_future.result().result == 0
        path_len = 0.0
        for i in range(1, len(self.trajectory)):
            dx = self.trajectory[i][0] - self.trajectory[i-1][0]
            dy = self.trajectory[i][1] - self.trajectory[i-1][1]
            path_len += math.sqrt(dx*dx+dy*dy)

        return {"id": scenario["id"], "success": success, "duration_s": round(dt, 2),
            "path_length_m": round(path_len, 3), "trajectory_points": len(self.trajectory),
            "error": None if success else "timeout" if dt >= timeout else "failed"}

def main():
    pkg = os.environ.get("SIMINSPECT_BENCHMARK_DIR", ".")
    cfg = os.path.join(os.path.dirname(__file__), "..", "config", "nav_benchmark_scenarios.yaml")
    with open(cfg) as f:
        data = yaml.safe_load(f)

    rclpy.init()
    bench = NavBenchmark()
    results = []
    for s in data["scenarios"]:
        r = bench.run(s)
        results.append(r)
        bench.get_logger().info(f"{r["id"]}: success={r["success"]}, time={r["duration_s"]}s, path={r["path_length_m"]}m")

    total = len(results)
    successes = sum(1 for r in results if r["success"])
    summary = {"experiment": "E2", "scenarios": total, "successes": successes,
        "success_rate": round(successes/total, 3) if total else 0, "results": results}
    bench.get_logger().info(f"E2: {successes}/{total} passed")
    print(json.dumps(summary, indent=2))
    bench.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
