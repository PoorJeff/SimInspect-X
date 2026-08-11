# Metrics

## Inspection success rate
A station succeeds only if:
- robot reaches a valid inspection state;
- reader outputs a value;
- confidence threshold passes (≥ 0.80);
- |estimate − ground_truth| ≤ 5 % full-scale range;
- no manual intervention;
- within timeout (per-attempt 30 s, per-asset 180 s).

## Gauge error
Absolute error:
```
|estimate − ground_truth|
```

Report:
- MAE = (1/n) Σ |err_i|
- RMSE = sqrt((1/n) Σ err_i²)
- median absolute error
- within-tolerance rate = |{i : |err_i| ≤ 5 % FS}| / total_readings

## Mission efficiency
- total path length;
- mission time;
- number of re-inspections;
- extra path length vs fixed-waypoint baseline (P2 − B0).

## Viewpoint quality
- target visible (V term, binary);
- target pixel area;
- view angle;
- distance;
- clearance.

## Control

### Control effort
```
effort_abs = ∫|v(t)|·dt + ∫|ω(t)|·dt
effort_sq  = ∫v(t)²·dt + ∫ω(t)²·dt
```
Both are reported. `effort_abs` captures total control energy; `effort_sq` penalises large spikes.

### Settling time
```
t_settle = min{ t : |pos_err(t')| < 0.05 m  ∧  |yaw_err(t')| < 5°  for all t' ∈ [t, t+1 s] }
```
The robot is "settled" when both position and yaw errors remain within tolerance
for a continuous 1 s window.

### Constraint violations
```
violations = count( |v(t)| > v_max  ∨  |ω(t)| > ω_max )
```
Count of discrete time steps where velocity or angular velocity exceeds the actuator bounds.

- final position error;
- final yaw error;
- tracking RMSE;
- solver time (MPC only);
- failure rate (timeout or controller error).

## Localisation
- trajectory/position RMSE against benchmark-only simulator truth;
- yaw RMSE;
- final drift.

## Robustness
- mission success;
- station completion ratio;
- recovery count;
- failure reason distribution.