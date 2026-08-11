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

- `/cmd_vel`
- `/wheel/odometry`
- `/odometry/filtered`
- `/scan`
- `/imu/data`
- `/camera/image_raw`
- `/camera/camera_info`
- `/inspection/assets`
- `/inspection/candidate_viewpoints`
- `/inspection/selected_viewpoint`
- `/inspection/gauge_reading`
- `/inspection/mission_state`

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
