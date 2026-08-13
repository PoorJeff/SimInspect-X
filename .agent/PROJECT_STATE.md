# PROJECT_STATE

Status: P10_READY
Current phase: P10_PACKAGING

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
- P9: Robustness and repeatable experiments (4/4 ACCEPTED)

## Current phase
P10: Admissions packaging
- P10-T01: One-command demo (ACCEPTED)
- P10-T02: Research-style report (TODO)
- P10-T03: README + architecture + demo video (TODO)
- P10-T04: CV/SOP evidence pack (TODO)

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
P10 must deliver one-command demo (T01), research report (T02),
README + architecture + demo video (T03), and CV/SOP evidence pack (T04).