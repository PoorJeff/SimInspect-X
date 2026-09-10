#!/usr/bin/env python3
"""PrecisionApproach action server — T02/T03: PID or MPC control loop."""
import math
import rclpy
from rclpy.node import Node
from rclpy.action import ActionServer, CancelResponse, GoalResponse
from rclpy.clock import Clock, ClockType
from rclpy.task import Future
from rclpy.time import Time
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
from siminspect_interfaces.action import PrecisionApproach
from tf2_geometry_msgs import do_transform_pose
from tf2_ros import Buffer, TransformException, TransformListener

try:
    from siminspect_precision_control.pid_controller import PIDController, PIDGains
    from siminspect_precision_control.mpc_controller import MPCController, MPCParams
except ImportError:  # Installed executable and source-tree script layout.
    from pid_controller import PIDController, PIDGains
    from mpc_controller import MPCController, MPCParams


class ControllerInterface(Node):
    """Action server that executes precision approach using PID or MPC.

    Subscribes to /odometry/filtered for real-time pose feedback,
    publishes /cmd_vel for differential-drive actuation.
    Controller type selected via ROS parameter "controller_type" (pid|mpc).
    """

    def __init__(self):
        super().__init__("controller_interface")

        # Controller selection parameter
        self.declare_parameter("controller_type", "pid")
        self.declare_parameter("mpc_horizon", 15)

        # Odom subscriber
        self.latest_odom = None
        self._odom_frame = None
        self._odom_sub = self.create_subscription(
            Odometry, "/odometry/filtered", self._cb_odom, 10
        )
        self._tf_buffer = Buffer(node=self)
        self._tf_listener = TransformListener(self._tf_buffer, self)
        # Cancellation must still progress if the simulation clock pauses.
        self._steady_clock = Clock(clock_type=ClockType.STEADY_TIME)

        # Command publisher
        self._cmd_pub = self.create_publisher(Twist, "/cmd_vel", 10)

        # Action server
        self._action_server = ActionServer(
            self,
            PrecisionApproach,
            "precision_approach",
            execute_callback=self.execute_callback,
            goal_callback=self.goal_callback,
            cancel_callback=self.cancel_callback,
        )
        ctype = self.get_parameter("controller_type").value
        self.get_logger().info(
            f"PrecisionApproach action server ready ({ctype.upper()})"
        )

    # ------------------------------------------------------------------
    # Subscriber callbacks
    # ------------------------------------------------------------------

    def _cb_odom(self, msg: Odometry):
        p = msg.pose.pose.position
        q = msg.pose.pose.orientation
        yaw = 2.0 * math.atan2(q.z, q.w)
        self._odom_frame = msg.header.frame_id
        self.latest_odom = (p.x, p.y, yaw,
                            msg.twist.twist.linear.x,
                            msg.twist.twist.angular.z)

    # ------------------------------------------------------------------
    # Action callbacks
    # ------------------------------------------------------------------

    def goal_callback(self, goal_request):
        self.get_logger().info(
            f"Received goal: target=({goal_request.target_pose.pose.position.x:.2f}, "
            f"{goal_request.target_pose.pose.position.y:.2f}), "
            f"timeout={goal_request.timeout_s:.1f}s"
        )
        return GoalResponse.ACCEPT

    def cancel_callback(self, goal_handle):
        self.get_logger().info("PrecisionApproach cancelled")
        self._stop_robot()
        return CancelResponse.ACCEPT

    def _stop_robot(self):
        twist = Twist()
        twist.linear.x = 0.0
        twist.angular.z = 0.0
        self._cmd_pub.publish(twist)

    # ------------------------------------------------------------------
    # Main control loop
    # ------------------------------------------------------------------

    async def _wait_for_control_tick(self):
        """Yield to odometry, TF and action callbacks on the same executor."""
        ready = Future(executor=self.executor)

        def wake():
            if not ready.done():
                ready.set_result(None)

        timer = self.create_timer(0.05, wake, clock=self._steady_clock)
        try:
            await ready
        finally:
            self.destroy_timer(timer)

    async def execute_callback(self, goal_handle):
        request = goal_handle.request
        timeout = request.timeout_s
        max_v = min(request.max_linear_vel, 0.5) if request.max_linear_vel > 0 else 0.5
        max_w = min(request.max_angular_vel, 1.5) if request.max_angular_vel > 0 else 1.5

        # Convert the map goal into the frame of the measured odometry. The
        # viewpoint is a fixed spatial target; use the latest map/odom TF,
        # not its earlier request-correlation timestamp.
        target_pose = None
        for _ in range(40):
            if goal_handle.is_cancel_requested:
                self._stop_robot()
                goal_handle.canceled()
                return PrecisionApproach.Result(success=False)
            if self.latest_odom is not None and self._odom_frame:
                if request.target_pose.header.frame_id == self._odom_frame:
                    target_pose = request.target_pose.pose
                    break
                try:
                    transform = self._tf_buffer.lookup_transform(
                        self._odom_frame,
                        request.target_pose.header.frame_id, Time())
                    target_pose = do_transform_pose(
                        request.target_pose.pose, transform)
                    break
                except TransformException:
                    pass
            await self._wait_for_control_tick()

        if target_pose is None:
            self._stop_robot()
            self.get_logger().error(
                "Odometry or target-to-odometry transform unavailable, aborting")
            goal_handle.abort()
            result = PrecisionApproach.Result()
            result.success = False
            result.final_position_error = float("inf")
            result.final_yaw_error = float("inf")
            result.elapsed_time = 0.0
            return result

        target_yaw = 2.0 * math.atan2(
            target_pose.orientation.z, target_pose.orientation.w
        )
        target = (target_pose.position.x, target_pose.position.y, target_yaw)

        # Choose controller
        ctype = self.get_parameter("controller_type").value
        if ctype == "mpc":
            mpc_params = MPCParams(
                N=self.get_parameter("mpc_horizon").value,
                v_max=max_v, w_max=max_w,
            )
            controller = MPCController(target, params=mpc_params)
        else:
            gains = PIDGains(v_max=max_v, w_max=max_w)
            controller = PIDController(target, gains=gains)

        self.get_logger().info(
            f"Starting {ctype.upper()} approach to ("
            f"{target[0]:.2f}, {target[1]:.2f}, yaw={target[2]:.2f})"
        )

        start_time = self.get_clock().now()

        feedback_msg = PrecisionApproach.Feedback()
        final_pos_err = 0.0
        final_yaw_err = 0.0
        converged = False
        elapsed = 0.0

        while rclpy.ok():
            if goal_handle.is_cancel_requested:
                self._stop_robot()
                goal_handle.canceled()
                result = PrecisionApproach.Result()
                result.success = False
                result.final_position_error = final_pos_err
                result.final_yaw_error = final_yaw_err
                result.elapsed_time = elapsed
                return result

            elapsed = (self.get_clock().now() - start_time).nanoseconds / 1e9

            if elapsed > timeout:
                self._stop_robot()
                self.get_logger().warn(
                    f"{ctype.upper()} approach timed out after {elapsed:.1f}s"
                )
                goal_handle.abort()
                result = PrecisionApproach.Result()
                result.success = False
                result.final_position_error = final_pos_err
                result.final_yaw_error = final_yaw_err
                result.elapsed_time = elapsed
                return result

            if self.latest_odom is None:
                await self._wait_for_control_tick()
                continue
            cx, cy, cyaw, _, _ = self.latest_odom

            v_cmd, w_cmd, pos_err, yaw_err, converged = controller.update(
                (cx, cy, cyaw), 0.05
            )

            final_pos_err = pos_err
            final_yaw_err = yaw_err

            twist = Twist()
            twist.linear.x = v_cmd
            twist.angular.z = w_cmd
            self._cmd_pub.publish(twist)

            feedback_msg.position_error = pos_err
            feedback_msg.yaw_error = yaw_err
            feedback_msg.time_elapsed = elapsed
            goal_handle.publish_feedback(feedback_msg)

            if converged:
                break

            await self._wait_for_control_tick()

        self._stop_robot()
        elapsed = (self.get_clock().now() - start_time).nanoseconds / 1e9

        if converged:
            goal_handle.succeed()
            self.get_logger().info(
                f"{ctype.upper()} converged: pos_err={final_pos_err:.3f}m, "
                f"yaw_err={final_yaw_err:.3f}rad, t={elapsed:.1f}s"
            )
        else:
            goal_handle.abort()

        result = PrecisionApproach.Result()
        result.success = converged
        result.final_position_error = final_pos_err
        result.final_yaw_error = final_yaw_err
        result.elapsed_time = elapsed
        return result


def main():
    rclpy.init()
    node = ControllerInterface()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
