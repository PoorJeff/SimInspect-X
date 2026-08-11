# Failure Injection

Scenario IDs:

- F00 nominal
- F01 wheel_odom_noise
- F02 wheel_slip
- F03 imu_noise
- F04 lidar_dropout_window
- F05 dynamic_obstacle
- F06 blocked_fixed_viewpoint
- F07 camera_blur
- F08 camera_dark
- F09 gauge_partial_occlusion
- F10 initial_pose_offset
- F11 mixed_stress

Each scenario:
- has deterministic config;
- records seed;
- changes one primary factor unless it is explicitly a mixed-stress test.

Do not tune on final test seeds.
