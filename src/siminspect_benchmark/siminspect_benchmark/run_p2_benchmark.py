#!/usr/bin/env python3
"""P2 adaptive benchmark: paired with P1, tracks retry overhead."""
import json, math, os, sys, time, yaml
import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from nav2_msgs.action import NavigateToPose
from geometry_msgs.msg import PoseStamped
from nav_msgs.msg import Odometry
from siminspect_interfaces.msg import GaugeReading

class P2Benchmark(Node):
    def __init__(self):
        super().__init__("p2_benchmark")
        self.nav = ActionClient(self, NavigateToPose, "navigate_to_pose")
        self.gt_sub = self.create_subscription(Odometry, "/benchmark_ground_truth/robot_pose", self.cb_gt, 10)
        self.reader_sub = self.create_subscription(GaugeReading, "/inspection/gauge_reading", self.cb_reading, 10)
        self.traj = []
        self.retry_count = 0
        self.reading_conf = None
        self.reading_received = False

    def cb_gt(self, m: Odometry):
        p = m.pose.pose.position; self.traj.append((p.x, p.y))

    def cb_reading(self, m: GaugeReading):
        self.reading_conf = m.confidence
        self.reading_received = True
        if m.confidence < 0.80:
            self.retry_count += 1

    def navigate(self, goal_pose, timeout=120):
        self.traj = []
        self.reading_received = False
        self.reading_conf = None
        g = PoseStamped(); g.header.frame_id = "map"; g.pose = goal_pose
        if not self.nav.wait_for_server(5):
            return False, 0, 0
        t0 = time.time()
        f = self.nav.send_goal_async(g)
        rclpy.spin_until_future_complete(self, f, timeout_sec=5)
        if not f.done():
            return False, time.time()-t0, 0
        gh = f.result()
        if not gh.accepted:
            return False, time.time()-t0, 0
        rf = gh.get_result_async()
        elapsed = time.time()-t0
        rclpy.spin_until_future_complete(self, rf, timeout_sec=max(timeout-elapsed, 1))
        dt = time.time()-t0
        success = rf.done() and rf.result().result == 0
        pl = 0.0
        for i in range(1, len(self.traj)):
            pl += math.hypot(self.traj[i][0]-self.traj[i-1][0], self.traj[i][1]-self.traj[i-1][1])
        return success, dt, pl

    def run_asset(self, asset_cfg):
        """Run P2 inspection for one asset. Returns metrics dict."""
        start = asset_cfg["start"]
        self.retry_count = 0
        total_success = True
        total_time = 0.0
        total_distance = 0.0

        # Initial navigation
        g = PoseStamped()
        g.pose.position.x = start.get("x", 0.0)
        g.pose.position.y = start.get("y", 0.0)
        g.pose.position.z = 0.0
        g.pose.orientation.z = 0.0
        g.pose.orientation.w = 1.0
        success, dt, pl = self.navigate(g, timeout=120)
        total_time += dt
        total_distance += pl
        if not success:
            total_success = False

        # Simulate up to 3 re-inspections (P2 adaptive behaviour)
        extra_time = 0.0
        extra_distance = 0.0
        for attempt in range(3):
            rclpy.spin_once(self, timeout_sec=2.0)
            if self.reading_conf is not None and self.reading_conf >= 0.80:
                break
            # Re-navigate to a next-best waypoint (offset)
            next_x = start.get("x", 0.0) + (attempt+1) * 0.3
            next_y = start.get("y", 0.0)
            g2 = PoseStamped()
            g2.pose.position.x = next_x
            g2.pose.position.y = next_y
            g2.pose.position.z = 0.0
            g2.pose.orientation.z = 0.0
            g2.pose.orientation.w = 1.0
            ok, edt, epl = self.navigate(g2, timeout=60)
            extra_time += edt
            extra_distance += epl
            if not ok:
                break

        return {
            "id": asset_cfg["id"],
            "success": total_success,
            "duration_s": round(total_time, 2),
            "path_length_m": round(total_distance, 3),
            "retry_count": self.retry_count,
            "extra_time_s": round(extra_time, 2),
            "extra_distance_m": round(extra_distance, 3),
            "final_confidence": round(self.reading_conf, 3) if self.reading_conf else None
        }

def main():
    cfg = os.path.join(os.path.dirname(__file__), "..", "config", "p2_experiment.yaml")
    with open(cfg) as f:
        data = yaml.safe_load(f)
    rclpy.init()
    node = P2Benchmark()
    results = []
    for cond in data["conditions"]:
        r = node.run_asset(cond)
        results.append(r)
        node.get_logger().info(
            f"P2 {r['id']}: ok={r['success']} dt={r['duration_s']}s "
            f"retries={r['retry_count']} extra_t={r['extra_time_s']}s extra_d={r['extra_distance_m']}m"
        )
    print(json.dumps({"experiment": "P2_adaptive", "results": results}, indent=2))
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()