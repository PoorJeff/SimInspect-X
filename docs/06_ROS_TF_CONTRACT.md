# ROS / TF Contract

## TF tree

```text
map
└── odom
    └── base_link
        ├── laser_link
        ├── imu_link
        └── camera_link
            └── camera_optical_frame
```

## Authority

- `map -> odom`: SLAM/localisation subsystem.
- `odom -> base_link`: EKF.
- fixed transforms: robot_state_publisher.

No double publishers.

## Core topics

| Topic | Message type |
|-------|-------------|
| `/cmd_vel` | `geometry_msgs/Twist` |
| `/wheel/odometry` | `nav_msgs/Odometry` |
| `/odometry/filtered` | `nav_msgs/Odometry` |
| `/scan` | `sensor_msgs/LaserScan` |
| `/imu/data` | `sensor_msgs/Imu` |
| `/camera/image_raw` | `sensor_msgs/Image` |
| `/camera/camera_info` | `sensor_msgs/CameraInfo` |
| `/inspection/assets` | `siminspect_interfaces/AssetArray` |
| `/inspection/candidate_viewpoints` | `siminspect_interfaces/CandidateViewpointArray` |
| `/inspection/selected_viewpoint` | `geometry_msgs/PoseStamped` |
| `/inspection/retry_viewpoint` | `std_msgs/String` |
| `/inspection/gauge_reading` | `siminspect_interfaces/GaugeReading` |
| `/inspection/mission_state` | `siminspect_interfaces/MissionState` |

- Custom message types (`siminspect_interfaces/*`) are defined in the `siminspect_interfaces` package.
- Standard ROS 2 types use the short-form notation (e.g. `geometry_msgs/Twist` for `geometry_msgs/msg/Twist`).

## Actions

### PrecisionApproach

```
# Goal — sent by Mission Executive to siminspect_precision_control
geometry_msgs/PoseStamped target_pose
float64 max_linear_vel
float64 max_angular_vel
float64 timeout_s
---
# Feedback — published by siminspect_precision_control during approach
float64 position_error
float64 yaw_error
float64 time_elapsed
---
# Result — returned when approach completes or times out
bool success
float64 final_position_error
float64 final_yaw_error
float64 elapsed_time
```

- The action server runs in `siminspect_precision_control`.
- The action client is `siminspect_mission` (Mission Executive).
- If `success = false` or the action times out, the Mission Executive triggers the failure recovery path.

## Controller handoff contract

The handoff from Nav2 (global/local navigation) to the precision approach controller
is governed by the Mission Executive state machine (`NAVIGATE → PRECISION_APPROACH`).

### Trigger

| Condition | Value |
|-----------|-------|
| Triggering entity | `siminspect_mission` (Mission Executive) |
| Nav2 state | Nav2 reports goal reached (success) |
| Distance threshold | `distance(current_pose, target_pose) ≤ 2.0 × desired_distance_m` |
| Handoff radius configurable | `inspection.approach_radius_multiplier` in asset YAML (default 2.0) |
| Path safety | Nav2 local costmap reports no obstacles within the approach corridor |
| Controller health | PrecisionApproach action server is available and responsive |

- The Mission Executive monitors Nav2 status, distance to target, costmap safety, and controller liveness.
- All conditions must be satisfied before the `PrecisionApproach` action is dispatched.
- If any condition fails (e.g. Nav2 fails to reach goal), the asset attempt is recorded as
  a navigation failure and the retry policy applies.

### Failure recovery

| Failure | Response |
|---------|----------|
| PrecisionApproach returns `success = false` | Try next candidate viewpoint for this asset |
| PrecisionApproach times out | Try next candidate viewpoint for this asset |
| All candidate viewpoints exhausted | Mark attempt failed; Mission Executive retries up to `max_attempts = 3` |
| All attempts exhausted | Asset marked failed; continue to next asset |

- Precision approach failure does not trigger an independent retry system.
  It is treated as one stage within a viewpoint attempt.
- On failure, control returns to Nav2 for the next navigation goal.

## Publisher / subscriber permission table

| Topic / Action | Publisher / Server | Subscriber / Client |
|---------------|-------------------|---------------------|
| `/cmd_vel` | `siminspect_navigation`, `siminspect_precision_control` | `siminspect_sim` (gz_ros2_control) |
| `/wheel/odometry` | `siminspect_sim` | `siminspect_localization` |
| `/odometry/filtered` | `siminspect_localization` | `siminspect_navigation`, `siminspect_mission` |
| `/scan` | `siminspect_sim` | `siminspect_navigation`, `siminspect_localization` |
| `/imu/data` | `siminspect_sim` | `siminspect_localization` |
| `/camera/image_raw` | `siminspect_sim` | `siminspect_gauge_vision` |
| `/camera/camera_info` | `siminspect_sim` | `siminspect_gauge_vision` |
| `/inspection/assets` | `siminspect_assets` | `siminspect_viewpoint_planner`, `siminspect_mission` |
| `/inspection/candidate_viewpoints` | `siminspect_viewpoint_planner` | `siminspect_mission` |
| `/inspection/selected_viewpoint` | `siminspect_viewpoint_planner` | `siminspect_mission`, `siminspect_navigation` |
| `/inspection/retry_viewpoint` | `siminspect_precision_control` | `siminspect_mission` |
| `/inspection/gauge_reading` | `siminspect_gauge_vision` | `siminspect_mission`, `siminspect_benchmark` |
| `/inspection/mission_state` | `siminspect_mission` | `siminspect_benchmark` |
| `PrecisionApproach` (action) | `siminspect_precision_control` (server) | `siminspect_mission` (client) |

- `siminspect_benchmark` subscribes to `/inspection/gauge_reading` and `/inspection/mission_state`
  for post-mission evaluation only; it **never** writes to any production topic.
- `siminspect_sim` represents the Gazebo simulation bridge (`gz_ros2_control`); its topics
  correspond to simulator-provided sensor and actuator data.

## Ground-truth firewall

Production autonomy nodes must never access simulator ground truth.
Only `siminspect_benchmark` is authorized to publish or subscribe to the
`/benchmark_ground_truth` namespace.

### Topics

| Topic | Message type | Publisher | Subscriber |
|-------|-------------|-----------|------------|
| `/benchmark_ground_truth/gauge_value/<asset_id>` | `std_msgs/Float64` | `siminspect_benchmark` | `siminspect_benchmark` only |
| `/benchmark_ground_truth/robot_pose` | `nav_msgs/Odometry` | `siminspect_benchmark` | `siminspect_benchmark` only |

- `<asset_id>` is a parameterised topic name, one per gauge asset (e.g. `gauge_pump_01`).
- `gauge_value` carries the simulator-known true pointer reading for that asset.
- `robot_pose` carries the simulator-ground-truth pose and twist for localisation and control accuracy evaluation.
- No production package may publish or subscribe to any topic under `/benchmark_ground_truth/`.

### Dual-layer CI enforcement

| Layer | Mechanism | Description |
|-------|-----------|-------------|
| L1 — compile-time | `ament_cmake` dependency check | Production packages (`siminspect_*` excluding `siminspect_benchmark`) must not declare `<depend>siminspect_benchmark</depend>` in `package.xml`. CI fails on violation. |
| L2 — runtime | `rosgraph` subscription monitor | `siminspect_benchmark` runs a watchdog node that queries `rosgraph` for all subscribers to `/benchmark_ground_truth/*`. Any subscriber outside the whitelist (`siminspect_benchmark` only) triggers a CI warning or failure. |

Defence-in-depth guarantees that ground-truth isolation — the scientific integrity foundation of the project — is enforced both at build time and during every experimental run.