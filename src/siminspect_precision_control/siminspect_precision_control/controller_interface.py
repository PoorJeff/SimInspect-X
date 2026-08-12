#!/usr/bin/env python3
"""PrecisionApproach action server skeleton — stub for T01, replaced by PID/MPC in T02/T03."""
import rclpy
from rclpy.node import Node
from rclpy.action import ActionServer, CancelResponse, GoalResponse
from siminspect_interfaces.action import PrecisionApproach

class ControllerInterface(Node):
    """Action server that receives PrecisionApproach goals and executes precision control.

    T01 stub behaviour: accept goal, simulate descending error over 2 s, return success.
    T02/T03: replace execute_callback with actual PID or MPC control loop.
    """

    def __init__(self):
        super().__init__("controller_interface")
        self._action_server = ActionServer(
            self,
            PrecisionApproach,
            "precision_approach",
            execute_callback=self.execute_callback,
            goal_callback=self.goal_callback,
            cancel_callback=self.cancel_callback,
        )
        self.get_logger().info("PrecisionApproach action server ready")

    def goal_callback(self, goal_request):
        self.get_logger().info(
            f"Received goal: target=({goal_request.target_pose.pose.position.x:.2f}, "
            f"{goal_request.target_pose.pose.position.y:.2f}), "
            f"timeout={goal_request.timeout_s:.1f}s"
        )
        return GoalResponse.ACCEPT

    def cancel_callback(self, goal_handle):
        self.get_logger().info("PrecisionApproach cancelled")
        return CancelResponse.ACCEPT

    async def execute_callback(self, goal_handle):
        """T01 stub: simulate convergence over 2 s, then return success.

        In T02/T03 this will be replaced by a real control loop (PID or MPC)
        that reads /odometry/filtered, publishes /cmd_vel, and checks constraints.
        """
        request = goal_handle.request
        target = request.target_pose.pose.position
        timeout = request.timeout_s
        self.get_logger().info(
            f"Executing precision approach to ({target.x:.2f}, {target.y:.2f}), timeout={timeout:.1f}s"
        )

        feedback_msg = PrecisionApproach.Feedback()
        start_time = self.get_clock().now()

        # Stub: simulate decreasing errors at ~10 Hz for up to 2 s
        elapsed = 0.0
        sim_duration = min(2.0, timeout)
        # Placeholder target yaw for stub feedback
        target_yaw = 2.0 * __import__("math").atan2(
            request.target_pose.pose.orientation.z,
            request.target_pose.pose.orientation.w,
        )

        while elapsed < sim_duration:
            if goal_handle.is_cancel_requested:
                goal_handle.canceled()
                result = PrecisionApproach.Result()
                result.success = False
                result.final_position_error = 1.0
                result.final_yaw_error = 1.0
                result.elapsed_time = elapsed
                return result

            now = self.get_clock().now()
            elapsed = (now - start_time).nanoseconds / 1e9

            # Stub feedback: errors decay linearly to ~0.01 m / 0.01 rad
            frac = min(1.0, elapsed / sim_duration)
            feedback_msg.position_error = max(0.01, 0.10 * (1.0 - frac))
            feedback_msg.yaw_error = max(0.01, 0.05 * (1.0 - frac))
            feedback_msg.time_elapsed = elapsed
            goal_handle.publish_feedback(feedback_msg)

        goal_handle.succeed()

        result = PrecisionApproach.Result()
        result.success = True
        result.final_position_error = feedback_msg.position_error
        result.final_yaw_error = feedback_msg.yaw_error
        result.elapsed_time = elapsed
        self.get_logger().info(
            f"PrecisionApproach complete: pos_err={result.final_position_error:.3f}, "
            f"yaw_err={result.final_yaw_error:.3f}, t={elapsed:.1f}s"
        )
        return result


def main():
    rclpy.init()
    node = ControllerInterface()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()