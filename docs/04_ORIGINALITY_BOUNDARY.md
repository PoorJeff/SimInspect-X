# Originality Boundary

## Reuse mature software

Use, configure and cite:
- ROS 2 middleware;
- Gazebo;
- ros2_control;
- robot_localization;
- SLAM Toolbox;
- Nav2;
- standard optimisation solver if used.

Do not spend months reimplementing them.

## Original work that must be ours

### O1 Viewpoint model
Represent several candidate poses for each asset and score them.

### O2 Inspection quality objective
Define and test a quality score based on:
- target in camera field of view;
- distance;
- camera-to-gauge incidence angle;
- predicted image size;
- map clearance;
- estimated occlusion / line-of-sight;
- travel cost.

### O3 Adaptive re-inspection
Use reading confidence to trigger another viewpoint attempt.

### O4 Precision approach controllers
Implement, tune and compare PID and MPC.

### O5 Experiment harness
Fault injection, seeds, metrics, paired baselines and report generation.

## Strong claim
"I designed and evaluated a perception-aware inspection policy."

## Weak claim
"I used Nav2 and SLAM Toolbox."

The latter belongs in implementation details, not as the project's main achievement.
