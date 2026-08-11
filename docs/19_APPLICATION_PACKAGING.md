# Application Packaging

## Ideal final CV bullets

### Robotics/autonomy
Built a ROS 2 autonomous industrial-inspection robot simulation integrating state estimation, SLAM/localisation,
Nav2 mission navigation, camera-based gauge reading and fault-tolerant multi-asset inspection; evaluated **[N]**
seeded missions under **[fault set]**.

### Research contribution
Designed a perception-aware viewpoint selection and confidence-triggered re-inspection policy, improving
**inspection success from [A]% to [B]%** while changing mission travel cost by **[C]%** versus a fixed-waypoint baseline.

### Control
Implemented and compared PID and constrained linear MPC for precision inspection-pose approach, reducing
**[metric]** from **[A]** to **[B]** under matched kinematic and disturbance constraints.

Only use these after actual results exist.

## Demo structure
1. 10 sec system architecture.
2. plant + map + sensors.
3. fixed waypoint fails / gives poor view.
4. proposed method selects another viewpoint.
5. gauge reading succeeds.
6. blocked route recovery.
7. PID/MPC result plot.
8. end-to-end benchmark table.

That story is much stronger than five minutes of a robot simply driving.
