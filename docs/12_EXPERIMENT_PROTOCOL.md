# Experiment Protocol

## E1 State estimation
Raw wheel odometry vs wheel+IMU EKF.
Faults:
- wheel noise;
- wheel slip;
- IMU noise.

## E2 Navigation
Nav2 baseline success under:
- nominal;
- narrow aisle;
- dynamic obstacle;
- blocked preferred route.

## E3 Gauge reader
Vary:
- viewing distance;
- yaw/incidence;
- blur;
- brightness;
- occlusion.

Report gauge-value error and read failure.

## E4 Flagship: viewpoint policy

Methods:
- B0 fixed waypoint;
- B1 nearest candidate;
- P1 quality-aware candidate;
- P2 P1 + adaptive re-inspection.

Conditions:
- normal;
- fixed-waypoint partially occluded;
- pose perturbation;
- image blur/noise;
- mixed condition.

Primary metrics:
- successful readable inspections;
- gauge MAE;
- station attempts;
- travel distance;
- station completion time.

## E5 Precision control
PID vs MPC:
- nominal;
- initial yaw error;
- measurement noise;
- wheel slip;
- saturation.

## E6 End-to-end
Full multi-asset missions with combined faults.

## Paired trial policy
Use identical mission/scenario/seed across compared methods.

## Trial counts
Development:
3–5 runs.

Final:
minimum 10 per condition;
20–30 preferred for flagship comparisons.
