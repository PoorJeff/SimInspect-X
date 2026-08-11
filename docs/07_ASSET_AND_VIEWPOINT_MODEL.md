# Asset and Viewpoint Model

## Asset schema

```yaml
id: gauge_pump_01
asset_type: analog_gauge
map_pose:
  x: 4.0
  y: 1.8
  z: 1.2
  yaw: 3.14
gauge:
  min_value: 0
  max_value: 100
  unit: psi
inspection:
  desired_distance_m: 0.8
  allowed_distance_m: [0.55, 1.30]
  max_incidence_deg: 40
  candidate_count: 7
  confidence_threshold: 0.80
  max_attempts: 3
```

## Candidate viewpoint

A viewpoint is:
`v = (x, y, yaw)` plus camera geometry.

Generate candidates on an arc or discrete ring facing the gauge.

## Quality score

Initial deterministic form:

\[
Q(v,a)=
w_{vis} V +
w_d D +
w_\theta A +
w_s S
-
w_t T
\]

Where:
- `V`: visibility / line-of-sight score;
- `D`: desired-distance score;
- `A`: camera incidence-angle score;
- `S`: obstacle/safety-clearance score;
- `T`: travel-cost term.

All terms must be normalised before weighted combination.

## Important baseline
Fixed waypoint:
one manually specified inspection pose per asset.

The project is only interesting if the proposed method is compared against this.
