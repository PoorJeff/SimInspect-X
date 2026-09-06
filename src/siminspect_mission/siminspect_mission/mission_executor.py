#!/usr/bin/env python3
"""Mission executive: multi-asset inspection state machine (P8-T01/T02).

Implements docs/11 state machine:
IDLE -> LOAD_MISSION -> SELECT_ASSET -> SELECT_VIEWPOINT -> NAVIGATE
     -> PRECISION_APPROACH -> INSPECT -> VALIDATE -> RECORD/NEXT
     -> RETURN_HOME -> EXPORT_REPORT -> DONE

Bounded retries per asset: nav 2, viewpoints 3, reader 3.
"""
import json
import math
import os
import time
import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from rclpy.parameter import Parameter
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy
from action_msgs.msg import GoalStatus
from nav2_msgs.action import NavigateToPose
from geometry_msgs.msg import PoseStamped
from nav_msgs.msg import Odometry
from std_msgs.msg import String
from siminspect_interfaces.msg import AssetArray, GaugeReading, MissionState
from siminspect_interfaces.action import PrecisionApproach

# Report schema (P8-T02). Dual import layout: ROS site-packages vs the
# Windows test layout where the package dir is on sys.path.
try:
    from siminspect_mission.report_schema import (
        VALID_CONFIDENCE, utc_now_iso, update_confidence_log,
        build_result_record, build_mission_report,
    )
except ImportError:
    from report_schema import (
        VALID_CONFIDENCE, utc_now_iso, update_confidence_log,
        build_result_record, build_mission_report,
    )

# Asset ordering (P8-T04). Same dual-layout import pattern.
try:
    from siminspect_mission.mission_ordering import ORDERINGS, order_assets
except ImportError:
    from mission_ordering import ORDERINGS, order_assets


# ---------------------------------------------------------------------------
# Pure state machine (ROS-free, unit-testable)
# ---------------------------------------------------------------------------

# States
S_IDLE = "IDLE"
S_LOAD_MISSION = "LOAD_MISSION"
S_SELECT_ASSET = "SELECT_ASSET"
S_SELECT_VIEWPOINT = "SELECT_VIEWPOINT"
S_NAVIGATE = "NAVIGATE"
S_PRECISION_APPROACH = "PRECISION_APPROACH"
S_INSPECT = "INSPECT"
S_VALIDATE = "VALIDATE"
S_RECORD = "RECORD"
S_NEXT_ASSET = "NEXT_ASSET"
S_RETURN_HOME = "RETURN_HOME"
S_EXPORT_REPORT = "EXPORT_REPORT"
S_DONE = "DONE"

# Events
E_TICK = "TICK"
E_START = "START"
E_ASSETS_LOADED = "ASSETS_LOADED"
E_VIEWPOINT_SELECTED = "VIEWPOINT_SELECTED"
E_NAV_OK = "NAV_OK"
E_NAV_FAIL = "NAV_FAIL"
E_APPROACH_OK = "APPROACH_OK"
E_APPROACH_FAIL = "APPROACH_FAIL"
E_READING_RECEIVED = "READING_RECEIVED"
E_READING_VALID = "READING_VALID"
E_READING_INVALID = "READING_INVALID"
E_RECORDED = "RECORDED"
E_MORE_ASSETS = "MORE_ASSETS"
E_NO_MORE_ASSETS = "NO_MORE_ASSETS"
E_HOME_REACHED = "HOME_REACHED"
E_HOME_FAILED = "HOME_FAILED"
E_REPORT_EXPORTED = "REPORT_EXPORTED"
E_RETRY_VIEWPOINT = "RETRY_VIEWPOINT"

# Retry limits (docs/11)
MAX_NAV_RETRIES = 2
MAX_VIEWPOINT_ATTEMPTS = 3
MAX_READER_RETRIES = 3
HOME_TOLERANCE_M = 0.10
MISSION_STATE_QOS = QoSProfile(
    depth=1,
    reliability=ReliabilityPolicy.RELIABLE,
    durability=DurabilityPolicy.TRANSIENT_LOCAL,
)


def handle_nav_fail(sm):
    """Fire E_NAV_FAIL and report whether the node must re-send the Nav2 goal.

    The state machine keeps state S_NAVIGATE while nav retry budget
    remains; the node layer must detect this and re-dispatch the goal
    (OI-008). Re-dispatch happens on the next tick via
    _nav_retry_pending to avoid synchronous recursion in the action
    callbacks.
    """
    _, new = sm.on_event(E_NAV_FAIL)
    return new == S_NAVIGATE


def is_nav_success(status):
    """Map a Nav2 action goal status to mission outcome (OI-010).

    navigate_to_pose returns an empty result (std_msgs/Empty), so
    success is decided by the action goal status, not by a result
    field (the previous result-field access raised AttributeError).
    """
    return status == GoalStatus.STATUS_SUCCEEDED


class MissionStateMachine:
    """Pure state machine with bounded retries. No ROS dependencies."""

    def __init__(self):
        self.state = S_IDLE
        self.assets = []
        self.asset_idx = -1
        self.nav_retries = 0
        self.viewpoint_attempts = 0
        self.reader_retries = 0
        self.request_id = 0
        self.results = []
        self.last_failure_reason = None

    # -- event handling ------------------------------------------------

    def on_event(self, event):
        """Process one event. Returns (old_state, new_state)."""
        old = self.state
        s = self.state

        if s == S_IDLE and event == E_START:
            self.state = S_LOAD_MISSION

        elif s == S_LOAD_MISSION and event == E_ASSETS_LOADED:
            self.state = S_SELECT_ASSET if self.assets else S_IDLE

        elif s == S_SELECT_ASSET and event == E_TICK:
            if self.asset_idx + 1 < len(self.assets):
                self.asset_idx += 1
                self.nav_retries = 0
                self.viewpoint_attempts = 0
                self.reader_retries = 0
                self.last_failure_reason = None
                self.state = S_SELECT_VIEWPOINT
            else:
                self.state = S_RETURN_HOME

        elif s == S_SELECT_VIEWPOINT and event == E_VIEWPOINT_SELECTED:
            self.state = S_NAVIGATE

        elif s == S_NAVIGATE:
            if event == E_NAV_OK:
                self.nav_retries = 0
                self.state = S_PRECISION_APPROACH
            elif event == E_NAV_FAIL:
                self.last_failure_reason = "nav_failed"
                self.nav_retries += 1
                if self.nav_retries < MAX_NAV_RETRIES:
                    self.state = S_NAVIGATE       # retry same viewpoint
                else:
                    self.nav_retries = 0
                    self.viewpoint_attempts += 1
                    if self.viewpoint_attempts < MAX_VIEWPOINT_ATTEMPTS:
                        self.state = S_SELECT_VIEWPOINT  # try next viewpoint
                    else:
                        self.state = S_RECORD      # record failure (P8-T02)

        elif s == S_PRECISION_APPROACH:
            if event == E_APPROACH_OK:
                self.state = S_INSPECT
            elif event == E_APPROACH_FAIL or event == E_RETRY_VIEWPOINT:
                self.last_failure_reason = "precision_failed"
                self.viewpoint_attempts += 1
                if self.viewpoint_attempts < MAX_VIEWPOINT_ATTEMPTS:
                    self.state = S_SELECT_VIEWPOINT
                else:
                    self.state = S_RECORD      # record failure (P8-T02)

        elif s == S_INSPECT:
            if event == E_READING_RECEIVED:
                self.state = S_VALIDATE
            # else: stay in INSPECT (waiting)

        elif s == S_VALIDATE:
            if event == E_READING_VALID:
                self.last_failure_reason = None
                self.state = S_RECORD
            elif event == E_READING_INVALID:
                self.last_failure_reason = "low_confidence"
                self.reader_retries += 1
                if self.reader_retries < MAX_READER_RETRIES:
                    self.state = S_INSPECT        # retry read
                else:
                    self.viewpoint_attempts += 1
                    self.reader_retries = 0
                    if self.viewpoint_attempts < MAX_VIEWPOINT_ATTEMPTS:
                        self.state = S_SELECT_VIEWPOINT
                    else:
                        self.state = S_RECORD      # record as failed

        elif s == S_RECORD and event == E_RECORDED:
            self.state = S_SELECT_ASSET

        elif s == S_RETURN_HOME and event == E_HOME_REACHED:
            self.state = S_EXPORT_REPORT

        elif s == S_RETURN_HOME and event == E_HOME_FAILED:
            self.state = S_EXPORT_REPORT

        elif s == S_EXPORT_REPORT and event == E_REPORT_EXPORTED:
            self.state = S_DONE

        if old != self.state and self.state == S_SELECT_VIEWPOINT:
            self.request_id += 1

        return old, self.state

    # -- helpers ------------------------------------------------------

    def load_assets(self, assets):
        self.assets = list(assets)
        self.asset_idx = -1
        return self.on_event(E_ASSETS_LOADED)

    def current_asset(self):
        if 0 <= self.asset_idx < len(self.assets):
            return self.assets[self.asset_idx]
        return None

    def add_result(self, record):
        self.results.append(record)


# ---------------------------------------------------------------------------
# ROS node
# ---------------------------------------------------------------------------

class MissionExecutor(Node):
    """ROS node wrapping MissionStateMachine with real actions/subscriptions."""

    def __init__(self):
        super().__init__("mission_executor")
        self.sm = MissionStateMachine()

        # P8-T04: asset ordering strategy (list = declaration order,
        # greedy = nearest-neighbour). Default keeps existing behaviour.
        self.declare_parameter("ordering", "list")
        ordering = self.get_parameter("ordering").value
        if ordering not in ORDERINGS:
            self.get_logger().warn(
                f"Unknown ordering '{ordering}'; falling back to 'list'")
            ordering = "list"
        self._ordering = ordering

        self.declare_parameter("run_id", "")
        self.declare_parameter("report_path", "mission_report.json")
        expected_ids_parameter = self.declare_parameter(
            "expected_asset_ids", Parameter.Type.STRING_ARRAY)
        self._run_id = str(self.get_parameter("run_id").value)
        report_path = os.path.expanduser(
            str(self.get_parameter("report_path").value))
        self._report_path = os.path.abspath(report_path)
        self._expected_asset_ids = tuple(
            str(asset_id)
            for asset_id in (expected_ids_parameter.value or ()))

        deadline_defaults = {
            S_LOAD_MISSION: ("load_mission_timeout_s", 15.0),
            S_SELECT_VIEWPOINT: ("select_viewpoint_timeout_s", 10.0),
            S_NAVIGATE: ("navigate_timeout_s", 120.0),
            S_PRECISION_APPROACH: ("precision_approach_timeout_s", 30.0),
            S_INSPECT: ("inspect_timeout_s", 15.0),
            S_RETURN_HOME: ("return_home_timeout_s", 120.0),
        }
        self._state_deadlines = {}
        for state, (parameter_name, default) in deadline_defaults.items():
            self.declare_parameter(parameter_name, default)
            timeout_s = float(self.get_parameter(parameter_name).value)
            if timeout_s <= 0.0:
                self.get_logger().warn(
                    f"{parameter_name} must be positive; using {default}")
                timeout_s = default
            self._state_deadlines[state] = timeout_s

        cancel_wait_default = 5.0
        self.declare_parameter(
            "cancel_wait_timeout_s", cancel_wait_default)
        self._cancel_wait_timeout_s = float(
            self.get_parameter("cancel_wait_timeout_s").value)
        if self._cancel_wait_timeout_s <= 0.0:
            self.get_logger().warn(
                "cancel_wait_timeout_s must be positive; using 5.0")
            self._cancel_wait_timeout_s = cancel_wait_default

        # Subscriptions
        self._assets_sub = self.create_subscription(
            AssetArray, "/inspection/assets", self._cb_assets, 10)
        self._reading_sub = self.create_subscription(
            GaugeReading, "/inspection/gauge_reading", self._cb_reading, 10)
        self._viewpoint_sub = self.create_subscription(
            PoseStamped, "/inspection/selected_viewpoint", self._cb_viewpoint, 10)
        self._retry_sub = self.create_subscription(
            String, "/inspection/retry_viewpoint", self._cb_retry, 10)
        self._odom_sub = self.create_subscription(
            Odometry, "/odometry/filtered", self._cb_odom, 10)

        # Publishers
        self._mission_pub = self.create_publisher(
            MissionState, "/inspection/mission_state", MISSION_STATE_QOS)

        # Action clients
        self._nav_client = ActionClient(self, NavigateToPose, "navigate_to_pose")
        self._pa_client = ActionClient(self, PrecisionApproach, "precision_approach")

        # State
        self.current_odom = None
        self.selected_viewpoint = None
        self.current_reading = None
        self.home_pose = (0.0, 0.0, 0.0)
        self.start_time = time.time()
        self.last_state = S_IDLE
        self.asset_viewpoints = []   # poses tried for current asset
        self.asset_confidence_log = []  # last reading confidence per attempt
        self.asset_nav_time = 0.0    # navigation duration for current asset
        self.asset_inspect_time = 0.0  # precision+inspect duration
        self._nav_start_ts = None
        self._inspect_start_ts = None
        self._viewpoint_request_stamp = None
        self._last_viewpoint_request_stamp_ns = None
        self._odom_seq = 0
        self._nav_generation = 0
        self._nav_goal_handle = None
        self._nav_pending_token = None
        self._precision_generation = 0
        self._precision_goal_handle = None
        self._precision_pending_token = None
        self._home_generation = 0
        self._home_goal_handle = None
        self._home_pending_token = None
        self._cancel_barrier = None
        self._action_dispatch_disabled = False
        self._nav_retry_pending = False   # OI-008: re-send goal on next tick
        self._assets_loaded = False
        self._state_entered_at = time.monotonic()
        self._home_goal_sent = False
        self._return_home_status = "pending"
        self._return_home_distance_m = None
        self._return_home_failure_reason = None
        self._home_action_succeeded = False
        self._home_success_odom_seq = None

        # Timer drives the state machine
        self._timer = self.create_timer(0.2, self._tick)

        self.get_logger().info("Mission executor ready")
        # P10-T01: fire E_START so the node leaves IDLE (was never
        # triggered elsewhere; _tick would otherwise early-return).
        self.sm.on_event(E_START)

    # ------------------------------------------------------------------
    # Subscriber callbacks
    # ------------------------------------------------------------------

    def _cb_assets(self, msg: AssetArray):
        if self._assets_loaded:
            self.get_logger().info("Ignoring duplicate asset inventory")
            return

        assets = list(msg.assets)
        asset_ids = [asset.id for asset in assets]
        if (not asset_ids or any(not asset_id for asset_id in asset_ids)
                or len(asset_ids) != len(set(asset_ids))):
            self.get_logger().warn("Ignoring invalid asset inventory")
            return
        if (self._expected_asset_ids
                and (len(asset_ids) != len(self._expected_asset_ids)
                     or set(asset_ids) != set(self._expected_asset_ids))):
            self.get_logger().warn(
                "Ignoring asset inventory that does not match "
                "expected_asset_ids")
            return

        self.get_logger().info(f"Received {len(msg.assets)} assets")
        start = ((self.current_odom[0], self.current_odom[1])
                 if self.current_odom is not None else (0.0, 0.0))
        assets = order_assets(assets, start, self._ordering)
        self._assets_loaded = True
        self.sm.load_assets(assets)

    def _cb_viewpoint(self, msg: PoseStamped):
        if self.sm.state != S_SELECT_VIEWPOINT:
            return
        stamp = getattr(msg.header, "stamp", None)
        stamp_key = self._stamp_key(stamp)
        if (stamp_key is None
                or stamp_key != self._viewpoint_request_stamp):
            self.get_logger().warn("Ignoring stale viewpoint response")
            return
        self.selected_viewpoint = msg
        vp = f"({msg.pose.position.x:.2f},{msg.pose.position.y:.2f})"
        self.asset_viewpoints.append(vp)   # one entry per attempt (P8-T02)
        self.sm.on_event(E_VIEWPOINT_SELECTED)

    def _cb_reading(self, msg: GaugeReading):
        asset = self.sm.current_asset()
        if self.sm.state != S_INSPECT:
            return
        if asset is None or msg.asset_id != asset.id:
            self.get_logger().warn(
                f"Ignoring reading for non-current asset '{msg.asset_id}'")
            return
        self.current_reading = msg
        self.asset_confidence_log = update_confidence_log(
            self.asset_viewpoints, self.asset_confidence_log, msg.confidence)
        self.sm.on_event(E_READING_RECEIVED)

    def _cb_retry(self, msg: String):
        self.get_logger().warn(f"Retry signal received: {msg.data}")
        if self.sm.state == S_PRECISION_APPROACH:
            self._invalidate_precision_dispatch()
            self.sm.on_event(E_RETRY_VIEWPOINT)

    def _cb_odom(self, msg: Odometry):
        p = msg.pose.pose.position
        q = msg.pose.pose.orientation
        yaw = 2.0 * math.atan2(q.z, q.w)
        self.current_odom = (p.x, p.y, yaw)
        self._odom_seq += 1
        if (self.sm.state != S_RETURN_HOME
                or not self._home_action_succeeded
                or self._home_success_odom_seq is None
                or self._odom_seq <= self._home_success_odom_seq):
            return
        if (time.monotonic() - self._state_entered_at
                >= self._state_deadlines[S_RETURN_HOME]):
            self._invalidate_home_dispatch()
            self._fail_return_home("timeout")
            return
        distance_m = self._distance_home()
        self._return_home_distance_m = round(distance_m, 3)
        if distance_m <= HOME_TOLERANCE_M:
            self._return_home_status = "success"
            self._return_home_failure_reason = None
            self._home_action_succeeded = False
            self.sm.on_event(E_HOME_REACHED)

    # ------------------------------------------------------------------
    # State machine tick
    # ------------------------------------------------------------------

    def _tick(self):
        s = self.sm.state
        now = time.monotonic()
        if self._action_dispatch_disabled:
            if s == S_EXPORT_REPORT:
                self._export_report()
            return
        if self._cancel_barrier is not None:
            if (now - self._cancel_barrier["started_at"]
                    >= self._cancel_wait_timeout_s):
                self._fail_cancel_barrier()
            return
        state_changed = s != self.last_state
        if not state_changed:
            timeout_s = self._state_deadlines.get(s)
            if (timeout_s is not None
                    and now - self._state_entered_at >= timeout_s):
                self._handle_state_timeout(s)
                return
            if s == S_RETURN_HOME and not self._home_goal_sent:
                self._return_home()
                return
            if not (s == S_NAVIGATE and self._nav_retry_pending):
                return
        else:
            self.last_state = s
            self._state_entered_at = now
            if s == S_RETURN_HOME:
                self._home_goal_sent = False
                self._home_goal_handle = None
                self._return_home_status = "pending"
                self._return_home_distance_m = None
                self._return_home_failure_reason = None
                self._home_action_succeeded = False
                self._home_success_odom_seq = None
            self._publish_state()
            self.get_logger().info(f"State: {s}")

        if s == S_LOAD_MISSION:
            pass  # assets arrive via topic

        elif s == S_SELECT_ASSET:
            # New asset: reset per-asset state before E_TICK advances.
            # current_reading MUST be cleared here: a failed asset that
            # produced no reading must not reuse the previous asset's
            # reading in _record_result (audit finding #1).
            self.current_reading = None
            self.selected_viewpoint = None
            self.asset_viewpoints = []
            self.asset_confidence_log = []
            self.asset_nav_time = 0.0
            self.asset_inspect_time = 0.0
            self._nav_start_ts = None
            self._inspect_start_ts = None
            self.sm.on_event(E_TICK)  # advance to next asset or RETURN_HOME

        elif s == S_SELECT_VIEWPOINT:
            self.selected_viewpoint = None
            # Per-asset accumulators are NOT reset here: this state is
            # re-entered on every attempt retry (P8-T02).
            # Viewpoint planner publishes automatically; we just wait.
            # (In a full system we might trigger the planner here.)

        elif s == S_NAVIGATE:
            self._nav_retry_pending = False
            self._start_navigation()

        elif s == S_PRECISION_APPROACH:
            self._start_precision_approach()

        elif s == S_INSPECT:
            if self._inspect_start_ts is None:
                self._inspect_start_ts = now
            # Reading arrives via topic.

        elif s == S_VALIDATE:
            self._validate_reading()

        elif s == S_RECORD:
            self._record_result()

        elif s == S_RETURN_HOME:
            self._return_home()

        elif s == S_EXPORT_REPORT:
            self._export_report()

        elif s == S_DONE:
            self.get_logger().info("Mission complete")

    def _handle_state_timeout(self, state):
        self.get_logger().error(f"State deadline expired: {state}")
        if state == S_NAVIGATE:
            self._invalidate_nav_dispatch()
        elif state == S_PRECISION_APPROACH:
            self._invalidate_precision_dispatch()
        elif state == S_INSPECT:
            self._finish_inspection_timing()
        if state in {
                S_SELECT_VIEWPOINT, S_NAVIGATE,
                S_PRECISION_APPROACH, S_INSPECT}:
            self.current_reading = None
            self.sm.last_failure_reason = "timeout"
            self.sm.state = S_RECORD
        elif state == S_RETURN_HOME:
            self._invalidate_home_dispatch()
            self._fail_return_home("timeout")
        elif state == S_LOAD_MISSION:
            self._return_home_status = "failed"
            self._return_home_failure_reason = "timeout"
            self.sm.state = S_EXPORT_REPORT

    def _fail_cancel_barrier(self):
        self.get_logger().error(
            "Action cancellation did not reach acknowledgement and terminal "
            "state before cancel_wait_timeout_s")
        self._cancel_barrier = None
        self._action_dispatch_disabled = True
        self.current_reading = None
        self.sm.last_failure_reason = "timeout"

        asset = self.sm.current_asset()
        already_recorded = (
            asset is not None
            and any(result.get("asset_id") == asset.id
                    for result in self.sm.results)
        )
        if asset is not None and not already_recorded:
            self.sm.state = S_RECORD
            self._record_result()

        self._return_home_status = "failed"
        self._return_home_failure_reason = "cancel_timeout"
        self.sm.state = S_EXPORT_REPORT

    def _publish_state(self):
        msg = MissionState()
        msg.state = self.sm.state
        asset = self.sm.current_asset()
        msg.current_asset_id = asset.id if asset else ""
        msg.attempt = self.sm.viewpoint_attempts
        msg.viewpoint_index = self.sm.viewpoint_attempts
        msg.request_id = self.sm.request_id
        msg.timestamp = self.get_clock().now().to_msg()
        if self.sm.state == S_SELECT_VIEWPOINT:
            stamp_ns = (int(msg.timestamp.sec) * 1_000_000_000
                        + int(msg.timestamp.nanosec))
            if (self._last_viewpoint_request_stamp_ns is not None
                    and stamp_ns <= self._last_viewpoint_request_stamp_ns):
                stamp_ns = self._last_viewpoint_request_stamp_ns + 1
                msg.timestamp.sec = stamp_ns // 1_000_000_000
                msg.timestamp.nanosec = stamp_ns % 1_000_000_000
            self._last_viewpoint_request_stamp_ns = stamp_ns
            self._viewpoint_request_stamp = self._stamp_key(msg.timestamp)
        self._mission_pub.publish(msg)

    @staticmethod
    def _stamp_key(stamp):
        if stamp is None:
            return None
        return (int(stamp.sec), int(stamp.nanosec))

    # ------------------------------------------------------------------
    # Action handlers
    # ------------------------------------------------------------------

    def _begin_cancel_barrier(
            self, kind, token, *, goal_pending=False, goal_handle=None,
            terminal_callback_registered=False):
        if not goal_pending and goal_handle is None:
            return
        if self._cancel_barrier is not None:
            return
        self._cancel_barrier = {
            "kind": kind,
            "token": token,
            "started_at": time.monotonic(),
            "cancel_ack": False,
            "terminal": False,
            "goal_handle": goal_handle,
        }
        if goal_handle is not None:
            self._track_cancelled_goal(
                kind, token, goal_handle,
                terminal_callback_registered=terminal_callback_registered)

    def _track_cancelled_goal(
            self, kind, token, goal_handle, *,
            terminal_callback_registered):
        barrier = self._cancel_barrier
        if (barrier is None or barrier["kind"] != kind
                or barrier["token"] != token):
            return
        barrier["goal_handle"] = goal_handle
        if not terminal_callback_registered:
            result_future = goal_handle.get_result_async()
            result_future.add_done_callback(
                lambda done, action=kind, dispatch=token:
                self._cancel_terminal_cb(done, action, dispatch))
        cancel_future = goal_handle.cancel_goal_async()
        cancel_future.add_done_callback(
            lambda done, action=kind, dispatch=token:
            self._cancel_ack_cb(done, action, dispatch))

    def _cancel_goal_response(self, kind, token, goal_handle):
        barrier = self._cancel_barrier
        if (barrier is None or barrier["kind"] != kind
                or barrier["token"] != token):
            return False
        if not goal_handle.accepted:
            barrier["cancel_ack"] = True
            barrier["terminal"] = True
            self._clear_completed_cancel_barrier()
            return True
        self._track_cancelled_goal(
            kind, token, goal_handle,
            terminal_callback_registered=False)
        return True

    def _cancel_ack_cb(self, future, kind, token):
        barrier = self._cancel_barrier
        if (barrier is None or barrier["kind"] != kind
                or barrier["token"] != token):
            return
        try:
            future.result()
        except Exception as exc:  # service failure is handled by barrier timeout
            self.get_logger().error(f"Cancel request failed: {exc}")
            return
        barrier["cancel_ack"] = True
        self._clear_completed_cancel_barrier()

    def _cancel_terminal_cb(self, future, kind, token):
        if not self._mark_cancel_terminal(future, kind, token):
            return

    def _mark_cancel_terminal(self, future, kind, token):
        barrier = self._cancel_barrier
        if (barrier is None or barrier["kind"] != kind
                or barrier["token"] != token):
            return False
        try:
            future.result()
        except Exception as exc:  # result failure is handled by barrier timeout
            self.get_logger().error(f"Cancelled action result failed: {exc}")
            return True
        barrier["terminal"] = True
        self._clear_completed_cancel_barrier()
        return True

    def _clear_completed_cancel_barrier(self):
        barrier = self._cancel_barrier
        if (barrier is not None and barrier["cancel_ack"]
                and barrier["terminal"]):
            self._cancel_barrier = None

    def _finish_nav_timing(self):
        if self._nav_start_ts is not None:
            self.asset_nav_time += time.monotonic() - self._nav_start_ts
            self._nav_start_ts = None

    def _finish_inspection_timing(self):
        if self._inspect_start_ts is not None:
            self.asset_inspect_time += (
                time.monotonic() - self._inspect_start_ts)
            self._inspect_start_ts = None

    def _invalidate_nav_dispatch(self):
        token = self._nav_generation
        self._begin_cancel_barrier(
            "nav", token,
            goal_pending=self._nav_pending_token == token,
            goal_handle=self._nav_goal_handle,
            terminal_callback_registered=self._nav_goal_handle is not None)
        self._nav_pending_token = None
        self._nav_goal_handle = None
        self._finish_nav_timing()
        self._nav_generation += 1

    def _invalidate_precision_dispatch(self):
        token = self._precision_generation
        self._begin_cancel_barrier(
            "precision", token,
            goal_pending=self._precision_pending_token == token,
            goal_handle=self._precision_goal_handle,
            terminal_callback_registered=(
                self._precision_goal_handle is not None))
        self._precision_pending_token = None
        self._precision_goal_handle = None
        self._finish_inspection_timing()
        self._precision_generation += 1

    def _invalidate_home_dispatch(self):
        token = self._home_generation
        self._begin_cancel_barrier(
            "home", token,
            goal_pending=self._home_pending_token == token,
            goal_handle=self._home_goal_handle,
            terminal_callback_registered=self._home_goal_handle is not None)
        self._home_pending_token = None
        self._home_goal_handle = None
        self._home_action_succeeded = False
        self._home_success_odom_seq = None
        self._home_generation += 1

    def _on_nav_fail(self):
        self._nav_retry_pending = handle_nav_fail(self.sm)
        if self._nav_retry_pending:
            self._state_entered_at = time.monotonic()

    def _start_navigation(self):
        if self.selected_viewpoint is None:
            self.get_logger().warn("No viewpoint to navigate to")
            return
        self._nav_generation += 1
        token = self._nav_generation
        self._nav_goal_handle = None
        self._nav_start_ts = time.monotonic()
        if not self._nav_client.wait_for_server(timeout_sec=5):
            self.get_logger().error("Nav2 not available")
            self._finish_nav_timing()
            self._nav_generation += 1
            self._on_nav_fail()
            return

        goal = NavigateToPose.Goal()
        goal.pose = self.selected_viewpoint
        self.get_logger().info(
            f"Navigating to ({self.selected_viewpoint.pose.position.x:.2f}, "
            f"{self.selected_viewpoint.pose.position.y:.2f})"
        )
        future = self._nav_client.send_goal_async(goal)
        self._nav_pending_token = token
        future.add_done_callback(
            lambda done, dispatch=token:
            self._nav_done_cb(done, dispatch))

    def _nav_done_cb(self, future, token):
        if self._nav_pending_token == token:
            self._nav_pending_token = None
        goal_handle = future.result()
        if self._cancel_goal_response("nav", token, goal_handle):
            return
        if token != self._nav_generation or self.sm.state != S_NAVIGATE:
            if goal_handle.accepted:
                self._begin_cancel_barrier(
                    "nav", token, goal_handle=goal_handle,
                    terminal_callback_registered=False)
            return
        if not goal_handle.accepted:
            self._finish_nav_timing()
            self._nav_generation += 1
            self._on_nav_fail()
            return
        self._nav_goal_handle = goal_handle
        result_future = goal_handle.get_result_async()
        result_future.add_done_callback(
            lambda done, dispatch=token:
            self._nav_result_cb(done, dispatch))

    def _nav_result_cb(self, future, token):
        if self._mark_cancel_terminal(future, "nav", token):
            return
        if token != self._nav_generation or self.sm.state != S_NAVIGATE:
            return
        self._nav_goal_handle = None
        self._finish_nav_timing()
        self._nav_generation += 1
        if is_nav_success(future.result().status):
            self.sm.on_event(E_NAV_OK)
        else:
            self._on_nav_fail()

    def _home_done_cb(self, future, token):
        if self._home_pending_token == token:
            self._home_pending_token = None
        goal_handle = future.result()
        if self._cancel_goal_response("home", token, goal_handle):
            return
        if token != self._home_generation or self.sm.state != S_RETURN_HOME:
            if goal_handle.accepted:
                self._begin_cancel_barrier(
                    "home", token, goal_handle=goal_handle,
                    terminal_callback_registered=False)
            return
        if not goal_handle.accepted:
            self._home_generation += 1
            self._fail_return_home("goal_rejected")
            return
        self._home_goal_handle = goal_handle
        result_future = goal_handle.get_result_async()
        result_future.add_done_callback(
            lambda done, dispatch=token:
            self._home_result_cb(done, dispatch))

    def _home_result_cb(self, future, token):
        if self._mark_cancel_terminal(future, "home", token):
            return
        if token != self._home_generation or self.sm.state != S_RETURN_HOME:
            return
        self._home_goal_handle = None
        status = future.result().status
        if not is_nav_success(status):
            self._home_generation += 1
            self._fail_return_home(f"goal_status_{status}")
            return
        self._home_action_succeeded = True
        self._home_success_odom_seq = self._odom_seq
        self._home_generation += 1

    def _distance_home(self):
        if self.current_odom is None:
            return None
        cx, cy, _ = self.current_odom
        return math.hypot(
            cx - self.home_pose[0], cy - self.home_pose[1])

    def _fail_return_home(self, reason):
        self._home_action_succeeded = False
        self._return_home_status = "failed"
        self._return_home_failure_reason = reason
        self.sm.on_event(E_HOME_FAILED)

    def _start_precision_approach(self):
        if self.selected_viewpoint is None:
            self.sm.on_event(E_APPROACH_FAIL)
            return
        self._precision_generation += 1
        token = self._precision_generation
        self._precision_goal_handle = None
        if self._inspect_start_ts is None:
            self._inspect_start_ts = time.monotonic()
        if not self._pa_client.wait_for_server(timeout_sec=5):
            self.get_logger().error("PrecisionApproach not available")
            self._finish_inspection_timing()
            self._precision_generation += 1
            self.sm.on_event(E_APPROACH_FAIL)
            return

        goal = PrecisionApproach.Goal()
        goal.target_pose = self.selected_viewpoint
        goal.max_linear_vel = 0.5
        goal.max_angular_vel = 1.5
        goal.timeout_s = self._state_deadlines[S_PRECISION_APPROACH]
        future = self._pa_client.send_goal_async(goal)
        self._precision_pending_token = token
        future.add_done_callback(
            lambda done, dispatch=token:
            self._pa_done_cb(done, dispatch))

    def _pa_done_cb(self, future, token):
        if self._precision_pending_token == token:
            self._precision_pending_token = None
        goal_handle = future.result()
        if self._cancel_goal_response("precision", token, goal_handle):
            return
        if (token != self._precision_generation
                or self.sm.state != S_PRECISION_APPROACH):
            if goal_handle.accepted:
                self._begin_cancel_barrier(
                    "precision", token, goal_handle=goal_handle,
                    terminal_callback_registered=False)
            return
        if not goal_handle.accepted:
            self._finish_inspection_timing()
            self._precision_generation += 1
            self.sm.on_event(E_APPROACH_FAIL)
            return
        self._precision_goal_handle = goal_handle
        result_future = goal_handle.get_result_async()
        result_future.add_done_callback(
            lambda done, dispatch=token:
            self._pa_result_cb(done, dispatch)
        )

    def _pa_result_cb(self, future, token):
        if self._mark_cancel_terminal(future, "precision", token):
            return
        if (token != self._precision_generation
                or self.sm.state != S_PRECISION_APPROACH):
            return
        self._precision_goal_handle = None
        action_result = future.result()
        success = (is_nav_success(action_result.status)
                   and action_result.result.success)
        self._precision_generation += 1
        if success:
            self.sm.on_event(E_APPROACH_OK)
        else:
            self._finish_inspection_timing()
            self.sm.on_event(E_APPROACH_FAIL)

    def _validate_reading(self):
        self._finish_inspection_timing()
        if self.current_reading is None:
            self.sm.on_event(E_READING_INVALID)
            return
        if self.current_reading.confidence >= VALID_CONFIDENCE:
            self.sm.on_event(E_READING_VALID)
        else:
            self.get_logger().warn(
                f"Low confidence reading: {self.current_reading.confidence:.2f}"
            )
            self.sm.on_event(E_READING_INVALID)

    def _record_result(self):
        asset = self.sm.current_asset()
        if asset is None:
            self.sm.on_event(E_RECORDED)
            return

        r = self.current_reading
        record = build_result_record(
            asset_id=asset.id,
            attempts=min(self.sm.viewpoint_attempts + 1, MAX_VIEWPOINT_ATTEMPTS),
            viewpoints=self.asset_viewpoints,
            confidence_log=self.asset_confidence_log,
            estimated_value=r.estimated_value if r else None,
            confidence=r.confidence if r else None,
            navigation_time_s=self.asset_nav_time,
            inspection_time_s=self.asset_inspect_time,
            failure_reason=self.sm.last_failure_reason,
        )
        self.sm.add_result(record)
        self.get_logger().info(f"Recorded: {record}")
        self.sm.on_event(E_RECORDED)

    def _return_home(self):
        if self._home_goal_sent or self.current_odom is None:
            return
        # Navigate home via Nav2
        goal = NavigateToPose.Goal()
        ps = PoseStamped()
        ps.header.frame_id = "map"
        ps.pose.position.x = self.home_pose[0]
        ps.pose.position.y = self.home_pose[1]
        ps.pose.orientation.w = 1.0
        goal.pose = ps
        if not self._nav_client.wait_for_server(timeout_sec=5):
            self.get_logger().warn("Nav2 unavailable for return home")
            self._fail_return_home("server_unavailable")
            return
        self._home_goal_sent = True
        self._home_generation += 1
        token = self._home_generation
        self._home_goal_handle = None
        future = self._nav_client.send_goal_async(goal)
        self._home_pending_token = token
        future.add_done_callback(
            lambda done, dispatch=token:
            self._home_done_cb(done, dispatch))

    def _export_report(self):
        report = build_mission_report(
            results=self.sm.results,
            num_assets=len(self.sm.assets),
            mission_time_s=time.time() - self.start_time,
            timestamp_iso=utc_now_iso(),
            run_id=self._run_id,
            expected_asset_ids=(
                self._expected_asset_ids
                or tuple(asset.id for asset in self.sm.assets)),
            return_home={
                "status": self._return_home_status,
                "final_distance_m": self._return_home_distance_m,
                "failure_reason": self._return_home_failure_reason,
            },
        )
        out = self._report_path
        os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
        with open(out, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
        self.get_logger().info(f"Report exported to {out}")
        self.sm.on_event(E_REPORT_EXPORTED)


def main():
    rclpy.init()
    node = MissionExecutor()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
