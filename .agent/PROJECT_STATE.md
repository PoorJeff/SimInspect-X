# PROJECT_STATE

Status: P9_READY
Current phase: P9_ROBUSTNESS

## Project identity
Name: SimInspect-X
Public title:
"Perception-Aware Autonomous Industrial Inspection in a Simulation-First Plant Testbed"

## Completed phases
- P0: Research freeze (5/5 ACCEPTED)
- P1: Docker/ROS/CI (5/5 ACCEPTED)
- P2: URDF/Gazebo/sensors/plant world (5/5 ACCEPTED)
- P3: EKF/SLAM/localisation eval (4/4 ACCEPTED)
- P4: Nav2 baseline/MPPI/recovery/benchmark (4/4 ACCEPTED)
- P5: Synthetic gauge dataset/detector/reader/confidence (4/4 ACCEPTED)
- P6: Viewpoint planning (candidate gen, quality scorer, B0, P1, P2 selectors) (5/5 ACCEPTED)
- P7: Precision control (interface, PID, MPC, paired benchmark) (4/4 ACCEPTED)
- P8: Adaptive mission (state machine, reports, retry policy, ordering) (4/4 ACCEPTED)

## Current phase
P9: Robustness and repeatable experiments
- P9-T01: Fault injector (ACCEPTED)
- P9-T02: Experiment runner (READY_FOR_REVIEW)
- P9-T03: Ablations (TODO)
- P9-T04: Consolidated analysis (TODO)

## Gold Core
- differential-drive AMR in Gazebo;
- LiDAR + IMU + RGB camera + wheel odometry;
- EKF, mapping, saved-map localisation;
- Nav2 autonomous navigation;
- synthetic-but-physically-labelled analog gauge inspection task;
- candidate inspection viewpoints;
- perception-aware viewpoint scoring;
- confidence-triggered re-inspection;
- final precision approach;
- PID vs MPC benchmark;
- fault injection and repeatable experiments.

## Primary original contribution
Perception-aware viewpoint selection + adaptive re-inspection.

## Secondary original contribution
Precision approach controller comparison (PID vs constrained linear MPC).

## Infrastructure, not originality
ROS 2, Gazebo, Nav2, SLAM Toolbox, robot_localization.

## Explicitly deferred
- manipulator;
- multi-robot;
- reinforcement learning;
- VLM/LLM closed-loop control;
- cloud fleet management;
- real hardware;
- photorealistic simulation.

## Active constraints
- Windows environment: no ROS 2/colcon/Gazebo runtime. All code is static-only.
- Push to GitHub fails without VPN.

## Next gate
P9 must deliver fault injection (T01), experiment runner (T02), ablations (T03),
and consolidated analysis (T04).