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

Namespace:
`/benchmark_ground_truth/*`

Only `siminspect_benchmark` may subscribe to it.

CI/integration test should fail if production packages depend on benchmark-ground-truth interfaces.
