# Metrics

## Inspection success rate
A station succeeds only if:
- robot reaches a valid inspection state;
- reader outputs a value;
- confidence threshold passes;
- no manual intervention;
- within timeout.

## Gauge error
Absolute error:
`|estimate - ground_truth|`

Report:
- MAE;
- RMSE;
- median absolute error;
- within-tolerance rate.

## Mission efficiency
- total path length;
- mission time;
- number of re-inspections;
- extra path length vs fixed-waypoint baseline.

## Viewpoint quality
- target visible;
- target pixel area;
- view angle;
- distance;
- clearance.

## Control
- final position error;
- final yaw error;
- RMSE;
- control effort;
- settling/completion;
- solver time;
- failures.

## Localisation
- trajectory/position RMSE against benchmark-only simulator truth;
- yaw RMSE;
- final drift.

## Robustness
- mission success;
- station completion ratio;
- recovery count;
- failure reason distribution.
