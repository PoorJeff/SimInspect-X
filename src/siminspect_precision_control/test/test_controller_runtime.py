"""Live ROS regressions for callback progress and map/odom frame handling."""
import math
from pathlib import Path
import subprocess
import sys
import time
import uuid

import pytest

rclpy = pytest.importorskip("rclpy", reason="Requires the Ubuntu ROS runtime")

from action_msgs.msg import GoalStatus
from geometry_msgs.msg import TransformStamped, Twist
from nav_msgs.msg import Odometry
from rclpy.action import ActionClient
from rclpy.executors import SingleThreadedExecutor
from siminspect_interfaces.action import PrecisionApproach
from tf2_ros import StaticTransformBroadcaster


@pytest.fixture
def live_controller(tmp_path):
    """Keep the server isolated so the original deadlock fails with a deadline."""
    suffix = uuid.uuid4().hex[:10]
    prefix = f"/precision_test_{suffix}"
    rclpy.init()
    node = rclpy.create_node(f"precision_test_client_{suffix}")
    executor = SingleThreadedExecutor()
    executor.add_node(node)
    state = {"x": 0.0, "frame": f"odom_{suffix}"}
    commands = []
    publisher = node.create_publisher(Odometry, prefix + "/odom", 10)

    def publish_odom():
        msg = Odometry()
        msg.header.frame_id = state["frame"]
        msg.header.stamp = node.get_clock().now().to_msg()
        msg.child_frame_id = f"base_{suffix}"
        msg.pose.pose.position.x = state["x"]
        msg.pose.pose.orientation.w = 1.0
        publisher.publish(msg)

    node.create_timer(0.02, publish_odom)
    node.create_subscription(Twist, prefix + "/cmd", commands.append, 10)
    client = ActionClient(node, PrecisionApproach, prefix + "/approach")
    script = (Path(__file__).resolve().parents[1]
              / "siminspect_precision_control" / "controller_interface.py")
    log_path = tmp_path / "controller.log"
    with log_path.open("w", encoding="utf-8") as log:
        process = subprocess.Popen([
            sys.executable, str(script), "--ros-args",
            "-r", f"__node:=precision_test_server_{suffix}",
            "-r", f"precision_approach:={prefix}/approach",
            "-r", f"/odometry/filtered:={prefix}/odom",
            "-r", f"/cmd_vel:={prefix}/cmd",
        ], stdout=log, stderr=subprocess.STDOUT)

        def wait_until(predicate, timeout_s=5.0):
            deadline = time.monotonic() + timeout_s
            while not predicate() and time.monotonic() < deadline:
                assert process.poll() is None, log_path.read_text()
                executor.spin_once(timeout_sec=0.02)
            assert predicate(), log_path.read_text()

        try:
            wait_until(client.server_is_ready, timeout_s=10.0)
            wait_until(lambda: publisher.get_subscription_count() > 0)
            yield node, client, state, commands, wait_until, suffix
        finally:
            process.terminate()
            try:
                process.wait(timeout=3.0)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=3.0)
            client.destroy()
            executor.shutdown()
            node.destroy_node()
            rclpy.shutdown()


def make_goal(frame, x, y=0.0, yaw=0.0):
    goal = PrecisionApproach.Goal()
    goal.target_pose.header.frame_id = frame
    goal.target_pose.pose.position.x = float(x)
    goal.target_pose.pose.position.y = float(y)
    goal.target_pose.pose.orientation.z = math.sin(yaw / 2.0)
    goal.target_pose.pose.orientation.w = math.cos(yaw / 2.0)
    goal.max_linear_vel = 0.5
    goal.max_angular_vel = 1.5
    goal.timeout_s = 10.0
    return goal


def test_nonconverged_goal_updates_from_fresh_odom_and_cancels(live_controller):
    _, client, state, commands, wait_until, _ = live_controller
    feedback = []
    pending = client.send_goal_async(
        make_goal(state["frame"], 2.0),
        feedback_callback=lambda msg: feedback.append(msg.feedback))
    wait_until(pending.done)
    handle = pending.result()
    assert handle.accepted
    wait_until(lambda: len(feedback) >= 3)
    assert feedback[0].position_error == pytest.approx(2.0)

    state["x"] = 0.5
    wait_until(lambda: any(
        abs(msg.position_error - 1.5) < 0.01 for msg in feedback))
    assert any(msg.linear.x > 0.0 for msg in commands)

    cancellation = handle.cancel_goal_async()
    wait_until(cancellation.done)
    assert cancellation.result().goals_canceling
    result = handle.get_result_async()
    wait_until(result.done)
    assert result.result().status == GoalStatus.STATUS_CANCELED
    assert not result.result().result.success
    wait_until(lambda: commands[-1].linear.x == 0.0
               and commands[-1].angular.z == 0.0)


def test_map_target_converges_with_nonidentity_odom_transform(live_controller):
    node, client, state, _, wait_until, suffix = live_controller
    state["x"] = 1.0
    broadcaster = StaticTransformBroadcaster(node)
    transform = TransformStamped()
    transform.header.stamp = node.get_clock().now().to_msg()
    transform.header.frame_id = f"map_{suffix}"
    transform.child_frame_id = state["frame"]
    transform.transform.translation.x = 10.0
    transform.transform.translation.y = -2.0
    transform.transform.rotation.z = math.sin(math.pi / 4.0)
    transform.transform.rotation.w = math.cos(math.pi / 4.0)
    broadcaster.sendTransform(transform)

    # Odom (1, 0, 0) is map (10, -1, pi/2), derived independently.
    pending = client.send_goal_async(
        make_goal(transform.header.frame_id, 10.0, -1.0, math.pi / 2.0))
    wait_until(pending.done)
    handle = pending.result()
    assert handle.accepted
    result = handle.get_result_async()
    wait_until(result.done)
    assert result.result().status == GoalStatus.STATUS_SUCCEEDED
    assert result.result().result.success
    assert result.result().result.final_position_error < 0.02
    assert result.result().result.final_yaw_error < 0.03
