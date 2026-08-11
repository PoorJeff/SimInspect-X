# PROJECT_STATE

Status: BLUEPRINT_V2_FROZEN / IMPLEMENTATION_NOT_STARTED
Current phase: P0_RESEARCH_FREEZE

## Project identity
Name: SimInspect-X
Public title:
"Perception-Aware Autonomous Industrial Inspection in a Simulation-First Plant Testbed"

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

Next gate:
P0 must freeze formulas, interfaces, ground-truth separation, success metrics and implementation scope.
