# Technical Stack

## Baseline
- Ubuntu 24.04
- ROS 2 Jazzy
- Gazebo Harmonic
- `ros_gz`
- `gz_ros2_control`
- Nav2
- SLAM Toolbox
- robot_localization
- RViz2
- OpenCV
- NumPy/SciPy
- OSQP or equivalent QP solver for MPC
- pytest / ament / launch_testing
- rosbag2
- matplotlib/pandas for offline analysis

## Language split

### C++
Prefer for:
- real-time-ish ROS control nodes;
- controller implementation if performance matters;
- Nav2 plugin only if later justified.

### Python
Prefer for:
- viewpoint planner first version;
- mission executive prototype;
- gauge vision;
- benchmark orchestration;
- analysis;
- synthetic-data generation.

## Performance rule
First make logic correct and testable.
Only port to C++ when profiling shows a reason.
