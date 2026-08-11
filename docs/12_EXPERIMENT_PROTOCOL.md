# Experiment Protocol

## Unified experiment matrix

| Exp | Scope | Methods | Conditions | Trials (dev) | Trials (final) | Primary metrics |
|-----|-------|---------|------------|-------------|---------------|-----------------|
| E1 | State estimation | raw odom vs EKF | wheel noise, wheel slip, IMU noise | 3–5 | ≥10 | trajectory RMSE, yaw RMSE, final drift |
| E2 | Navigation | Nav2 baseline | nominal, narrow aisle, dynamic obstacle, blocked route | 3–5 | ≥10 | goal reach rate, recovery count, path length |
| E3 | Gauge reader | deterministic reader | distance, yaw/incidence, blur, brightness, occlusion | 3–5 | ≥10 | MAE, RMSE, within-tol. rate, failure-to-read rate |
| E4 | Viewpoint policy | B0, B1, P1, P2 | normal, fixed-WP occluded, pose perturbation, blur/noise, mixed | 3–5 | ≥20 | valid-read proportion, MAE, station attempts, extra distance |
| E5 | Precision control | PID, MPC | nominal, yaw error, meas. noise, wheel slip, saturation | 3–5 | ≥10 | final pos/yaw error, settling time, effort, violations |
| E6 | End-to-end | full mission pipeline | nominal + combined faults (≥3 fault classes) | 3–5 | ≥10 | mission success, station completion ratio, recovery count |

- E4 is the flagship experiment; B0 vs P1 vs P2 is the primary comparison.
- Ablations A1–A6 are run within E4/E5 as parameter variations.

## E1 — State estimation
Raw wheel odometry vs wheel+IMU EKF.
Faults:
- wheel noise;
- wheel slip;
- IMU noise.

## E2 — Navigation
Nav2 baseline success under:
- nominal;
- narrow aisle;
- dynamic obstacle;
- blocked preferred route.

## E3 — Gauge reader
Vary:
- viewing distance;
- yaw/incidence;
- blur;
- brightness;
- occlusion.

Report gauge-value error and read failure.

## E4 — Flagship: viewpoint policy

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

## E5 — Precision control
PID vs MPC:
- nominal;
- initial yaw error;
- measurement noise;
- wheel slip;
- saturation.

## E6 — End-to-end
Full multi-asset missions with combined faults.

## Paired trial policy
Use identical mission/scenario/seed across compared methods.

## Seed strategy

- **Final experiment pool:** 20 seeds, numbered 0001–0020. All final experiments draw from this pool.
- **Paired assignment:** All methods for a given condition share the same seed.
  Example: E4, condition "normal", seed 0005 → B0, B1, P1, P2 all run with seed 0005.
- **Development holdout:** 10 seeds, numbered 0021–0030. Used exclusively for development and tuning.
- **Final experiments:** ≥10 seeds per condition for non-flagship experiments (E1, E2, E3, E5, E6);
  up to 20 seeds per condition for flagship experiments (E4).
- **Development:** 3–5 seeds per condition from the holdout range (0021–0030).
- **Seed isolation:** Final experiment pool and development holdout are disjoint. Never tune parameters on final-pool seeds.

## Trial counts
Development:
3–5 runs.

Final:
minimum 10 per condition;
20–30 preferred for flagship comparisons.