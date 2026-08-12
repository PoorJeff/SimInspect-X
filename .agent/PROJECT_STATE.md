# PROJECT_STATE

Status: P8_IN_PROGRESS
Current phase: P8_ADAPTIVE_MISSION

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

## Current phase
P8: Adaptive mission execution
- P8-T01: Mission executive state machine (READY_FOR_REVIEW)
- P8-T02: Inspection result/report schema (TODO)
- P8-T03: Route/asset retry policy (TODO)
- P8-T04: Optional mission ordering heuristic (TODO)

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
- P3-P7 code largely uncommitted in working tree.

## Next gate
P7 must deliver precision approach interface (T01), PID (T02), MPC (T03), and paired benchmark (T04).
P8 will deliver mission executive, inspection reports, and retry policy.