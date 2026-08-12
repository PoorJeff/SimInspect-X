"""
Integration test: verify sensor topics publish at expected rates.
Requires Gazebo. Skips gracefully if topics unavailable.
"""
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import LaserScan, Imu, Image, CameraInfo
from nav_msgs.msg import Odometry
import time, pytest
TOPICS = {"/scan": {"type": LaserScan, "rate": 10, "tol": 0.5}, "/imu/data": {"type": Imu, "rate": 100, "tol": 0.5}, "/camera/image_raw": {"type": Image, "rate": 30, "tol": 0.5}, "/camera/camera_info": {"type": CameraInfo, "rate": 30, "tol": 0.5}, "/wheel/odometry": {"type": Odometry, "rate": 50, "tol": 0.5}}
DURATION = 5.0
class SensorCollector(Node):
    def __init__(self):
        super().__init__("collector")
        self.counts = {t: 0 for t in TOPICS}
        for t, c in TOPICS.items(): self.create_subscription(c["type"], t, lambda m, t=t: self._cb(t), 10)
    def _cb(self, t): self.counts[t] += 1
def spin(exe, node, sec):
    start = time.time()
    while time.time() - start < sec: exe.spin_once(timeout_sec=0.1)
@pytest.mark.integration
def test_sensor_topics_publish():
    try: rclpy.init()
    except Exception: pytest.skip("ROS 2 unavailable")
    node = SensorCollector()
    exe = rclpy.executors.SingleThreadedExecutor()
    exe.add_node(node)
    spin(exe, node, 2.0)
    if sum(node.counts.values()) == 0:
        node.destroy_node(); exe.shutdown(); rclpy.shutdown()
        pytest.skip("No topics -- Gazebo not running")
    spin(exe, node, DURATION)
    fails = []
    for t, c in TOPICS.items():
        n = node.counts[t]; e = c["rate"] * DURATION; lo = e * 0.5; hi = e * 1.5
        ok = n >= 3 and lo <= n <= hi
        print(f"  {t}: {n} msgs [{lo:.0f}-{hi:.0f}] {chr(0x2713) if ok else chr(0x2717)}")
        if not ok: fails.append(f"{t}: {n}, expected {lo:.0f}-{hi:.0f}")
    node.destroy_node(); exe.shutdown(); rclpy.shutdown()
    if fails: pytest.fail("; ".join(fails))