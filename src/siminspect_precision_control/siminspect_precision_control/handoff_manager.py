#!/usr/bin/env python3
"""Handoff manager: monitors Nav2 completion and triggers PrecisionApproach action.

When the robot reaches within approach_radius of the selected viewpoint
(Nav2 goal-reached proxy), the handoff manager dispatches a PrecisionApproach
goal. On failure it signals for a retry via /inspection/retry_viewpoint.
"""
import math
import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from geometry_msgs.msg import PoseStamped
from nav_msgs.msg import Odometry
from std_msgs.msg import String
from siminspect_interfaces.action import PrecisionApproach


class HandoffManager(Node):
    """Monitors Nav2 progress and triggers precision approach handoff.

    States: IDLE -> APPROACHING -> PRECISION -> IDLE (loop per viewpoint)
    """

    HANDOFF_RADIUS_MULTIPLIER = 2.0  # per 06 contract

    def __init__(self):
        super().__init__("handoff_manager")

        # Parameters
        self.declare_parameter("desired_distance_m", 0.8)
        self.declare_parameter("approach_radius_multiplier", self.HANDOFF_RADIUS_MULTIPLIER)
        self.declare_parameter("timeout_s", 30.0)
        self.declare_parameter("velocity_stopped_threshold", 0.05)

        # Subscribers
        self.odom_sub = self.create_subscription(
            Odometry, "/odometry/filtered", self.cb_odom, 10
        )
        self.viewpoint_sub = self.create_subscription(
            PoseStamped, "/inspection/selected_viewpoint", self.cb_viewpoint, 10
        )

        # Action client for PrecisionApproach
        self._pa_client = ActionClient(self, PrecisionApproach, "precision_approach")

        # Retry signal publisher
        self.retry_pub = self.create_publisher(String, "/inspection/retry_viewpoint", 10)

        # State
        self.current_pose = None        # (x, y, yaw) from odometry
        self.target_pose = None         # PoseStamped from /inspection/selected_viewpoint
        self.robot_velocity = (0.0, 0.0)  # (linear_x, angular_z)
        self.in_approach = False         # True while precision approach is active
        self.attempt_count = 0

        self.get_logger().info("Handoff manager ready")

    def cb_odom(self, msg: Odometry):
        p = msg.pose.pose.position
        q = msg.pose.pose.orientation
        yaw = 2.0 * math.atan2(q.z, q.w)
        self.current_pose = (p.x, p.y, yaw)
        self.robot_velocity = (msg.twist.twist.linear.x, msg.twist.twist.angular.z)

        self._check_handoff()

    def cb_viewpoint(self, msg: PoseStamped):
        self.target_pose = msg
        self.in_approach = False
        self.attempt_count = 0
        self.get_logger().info(
            f"New viewpoint: ({msg.pose.position.x:.2f}, {msg.pose.position.y:.2f})"
        )

    def _check_handoff(self):
        """Evaluate all handoff conditions and trigger if satisfied."""
        if self.in_approach:
            return  # already in precision approach
        if self.current_pose is None or self.target_pose is None:
            return  # not ready

        d = self._distance_to_target()

        dd = self.get_parameter("desired_distance_m").value
        mult = self.get_parameter("approach_radius_multiplier").value
        radius = mult * dd
        v_thresh = self.get_parameter("velocity_stopped_threshold").value

        # Condition 1: within handoff radius
        if d > radius:
            return

        # Condition 2: robot has stopped (Nav2 proxy)
        v_lin = abs(self.robot_velocity[0])
        if v_lin > v_thresh:
            return

        # Condition 3: action server available
        if not self._pa_client.wait_for_server(timeout_sec=1.0):
            self.get_logger().warn("PrecisionApproach server unavailable, deferring handoff")
            return

        self._trigger_handoff()

    def _distance_to_target(self):
        if self.current_pose is None or self.target_pose is None:
            return float("inf")
        tx = self.target_pose.pose.position.x
        ty = self.target_pose.pose.position.y
        cx, cy, _ = self.current_pose
        return math.hypot(cx - tx, cy - ty)

    def _trigger_handoff(self):
        self.in_approach = True
        self.attempt_count += 1

        goal = PrecisionApproach.Goal()
        goal.target_pose = self.target_pose
        goal.max_linear_vel = 0.2
        goal.max_angular_vel = 0.5
        goal.timeout_s = self.get_parameter("timeout_s").value

        self.get_logger().info(
            f"Handoff triggered: dist={self._distance_to_target():.2f}m, "
            f"attempt={self.attempt_count}"
        )

        send_future = self._pa_client.send_goal_async(
            goal, feedback_callback=self._pa_feedback_cb
        )
        send_future.add_done_callback(self._pa_goal_response_cb)

    def _pa_goal_response_cb(self, future):
        goal_handle = future.result()
        if not goal_handle.accepted:
            self.get_logger().warn("PrecisionApproach goal rejected")
            self._on_precision_failure("goal_rejected")
            return

        self.get_logger().info("PrecisionApproach goal accepted")
        result_future = goal_handle.get_result_async()
        result_future.add_done_callback(self._pa_result_cb)

    def _pa_feedback_cb(self, feedback_msg):
        self.get_logger().debug(
            f"PrecisionApproach feedback: pos_err={feedback_msg.feedback.position_error:.3f}, "
            f"yaw_err={feedback_msg.feedback.yaw_error:.3f}, "
            f"t={feedback_msg.feedback.time_elapsed:.1f}s"
        )

    def _pa_result_cb(self, future):
        result = future.result().result
        self.in_approach = False

        if result.success:
            self.get_logger().info(
                f"PrecisionApproach succeeded: pos_err={result.final_position_error:.3f}, "
                f"yaw_err={result.final_yaw_error:.3f}, t={result.elapsed_time:.1f}s"
            )
            self._on_precision_success()
        else:
            self.get_logger().warn(
                f"PrecisionApproach failed: pos_err={result.final_position_error:.3f}, "
                f"yaw_err={result.final_yaw_error:.3f}"
            )
            self._on_precision_failure("approach_failed")

    def _on_precision_success(self):
        """Precision approach completed successfully — return to IDLE."""
        self.get_logger().info("Viewpoint inspection complete")

    def _on_precision_failure(self, reason: str):
        """Precision approach failed — signal for retry."""
        msg = String()
        msg.data = reason
        self.retry_pub.publish(msg)
        self.get_logger().warn(
            f"Precision failure ({reason}), retry signal published "
            f"(attempt {self.attempt_count})"
        )


def main():
    rclpy.init()
    node = HandoffManager()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()