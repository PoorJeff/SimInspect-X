# Asset and Viewpoint Model

## Asset schema

```yaml
id: gauge_pump_01
asset_type: analog_gauge
map_pose:
  x: 4.0
  y: 1.8
  z: 1.2
  yaw: 3.14          # gauge face normal direction (pointing outward from the gauge)
gauge:
  min_value: 0
  max_value: 100
  unit: psi
inspection:
  desired_distance_m: 0.8
  allowed_distance_m: [0.55, 1.30]
  max_incidence_deg: 40
  candidate_count: 7
  candidate_arc_deg: 120       # total arc span (± half from normal), default 120
  confidence_threshold: 0.80
  max_attempts: 3
  approach_radius_multiplier: 2.0   # handoff radius = multiplier * desired_distance_m
  viewpoint_weights:                # optional per-asset override
    w_vis: 0.35
    w_d:   0.25
    w_θ:   0.25
    w_s:   0.15
    w_t:   0.15
```

- `map_pose.yaw` is the **gauge face normal direction** (where the gauge "faces").
  The robot must face approximately `yaw − π` to look at the gauge.
- `viewpoint_weights` are optional per-asset overrides; if omitted, global defaults are used.

## Candidate viewpoint generation

A viewpoint is a 2D pose: `v = (x, y, yaw)` in the `map` frame, plus camera geometry
(intrinsics / FOV from the sensor model).

### Generation algorithm

Given an asset with gauge pose `(x_g, y_g, yaw_g)` and inspection parameters:

```
1. Target face centre = (x_g, y_g)
2. Gauge normal        = yaw_g           (direction the gauge face points)
3. Arc centre angle    = yaw_g           (candidates placed in front of the gauge, along the normal)
4. Arc half-span       = candidate_arc_deg / 2  (default ±60°)
5. Radius              = desired_distance_m
6. Candidate count     = N
7. Angular step        = (2 * half_span) / (N − 1)  (for N ≥ 2)
```

For i = 0 … N−1:

```
angle_i  = arc_centre_angle − half_span + i · step
x_i      = x_g + radius · cos(angle_i)
y_i      = y_g + radius · sin(angle_i)
yaw_i    = angle_i + π        # robot faces the gauge
```

- `angle_i` is the direction **from gauge to candidate position**.
- `yaw_i` is the **robot orientation** at the candidate viewpoint (opposite to `angle_i`).
- Candidates are in the `map` frame.
- For N = 1 (degenerate), place the single candidate at the arc centre angle.

### Example

Gauge at origin, normal = 0 rad (east), desired_distance = 1.0 m:

| i | angle_i (rad) | (x, y) | yaw_i (rad) | robot faces |
|---|--------------|--------|-------------|-------------|
| 0 (leftmost)  | −π/3 | (0.50, −0.87) | 2π/3 | toward gauge |
| 3 (centre)    |   0   | (1.00,  0.00) |   π  | toward gauge (B0) |
| 6 (rightmost) | +π/3 | (0.50, +0.87) | 4π/3 | toward gauge |

## Viewpoint quality score

For asset `a` and candidate viewpoint `v`, the quality score is:

```
Q(v, a) = w_vis·V(v,a) + w_d·D(v,a) + w_θ·A(v,a) + w_s·S(v,a) − w_t·T(v,a)
```

All primary terms V, D, A, S are normalised to [0, 1].
T is a penalty term normalised per-asset to [0, 1].

Score interpretation: **higher is better**. Negative scores are possible
but indicate a poor candidate.

---

### V — Visibility (ray-cast)

**Type:** binary, {0, 1}.

**Computation:**
Cast a single ray from the camera origin at candidate `v` to the gauge face centre
`(x_g, y_g, z_gauge)`.

```
V(v,a) = 1  if the ray reaches the target without intersecting any obstacle,
         0  otherwise.
```

- Obstacles are derived from the occupancy grid / costmap.
- The ray is cast in 3D (camera height → gauge height); if a 3D ray-cast is unavailable,
  a 2D projection onto the ground plane is acceptable with explicit documentation.
- A candidate with V = 0 is **rejected** (not eligible for selection).

---

### D — Distance score

**Type:** continuous, [0, 1].

**Computation:**

```
d = || (x_v, y_v) − (x_g, y_g) ||₂
```

```
D(v,a) = max(0, 1 − |d − d_desired| / d_desired)
```

- `d_desired` = `inspection.desired_distance_m`.
- D = 1 when distance equals desired; D → 0 as distance deviates.
- D = 0 when |d − d_desired| ≥ d_desired.

---

### A — Incidence angle score

**Type:** continuous, [0, 1].

**Computation:**

Camera-to-gauge direction in the horizontal plane:

```
θ = | atan2(y_g − y_v, x_g − x_v) − yaw_v |
```

This is the absolute horizontal angular deviation between where the camera points
and where the gauge is. Normalise θ to [0°, 180°] (wrap to [0, π]).

```
A(v,a) = max(0, (cosθ − cosθ_max) / (1 − cosθ_max))
```

- `θ_max` = `inspection.max_incidence_deg` (converted to radians).
- A = 1 when the camera points directly at the gauge (θ = 0).
- A = 0 when θ ≥ θ_max.

---

### S — Safety / clearance score

**Type:** continuous, [0, 1].

**Computation:**

Let `d_obs` be the distance from the candidate viewpoint `(x_v, y_v)` to the nearest
obstacle cell in the costmap / occupancy grid.

```
S(v,a) = min(1, d_obs / d_safe)
```

- `d_safe` = 0.50 m (global default; the robot's footprint radius plus margin).
- S = 1 when clearance ≥ safe distance; S → 0 as obstacles approach.

---

### T — Travel cost

**Type:** continuous, [0, 1] (per-asset normalised).

**Computation:**

```
d_travel(v, r) = || (x_v, y_v) − (x_r, y_r) ||₂
```

where `r` is the robot's current pose.

```
T(v,a) = d_travel(v,r) / max_j d_travel(v_j, r)
```

- Normalised across only candidates with V > 0 for the **current asset** so the worst reachable candidate has T = 1
  and the best has T = d_min / d_max.
- If only one candidate remains, T is trivially 1 (or omitted).
- The travel cost uses **Euclidean distance**, not Nav2 path length, because viewpoint scoring
  occurs before navigation and must be deterministic and fast.

---

## Default weights

Global defaults (used when `viewpoint_weights` is absent from the asset YAML):

| Symbol | Term | Weight |
|--------|------|--------|
| w_vis | Visibility | 0.35 |
| w_d   | Distance   | 0.25 |
| w_θ   | Incidence  | 0.25 |
| w_s   | Safety      | 0.15 |
| w_t   | Travel cost | 0.15 |

- Primary terms (V, D, A, S) sum to 1.0 (convex combination). Per-asset ``viewpoint_weights`` overrides must also satisfy this constraint (w_vis + w_d + w_θ + w_s = 1.0). If a per-asset override violates the constraint, the global defaults are used instead.
- w_t is an additive penalty outside the convex combination; it scales independently and can be tuned per asset.

## Fixed waypoint baseline (B0)

**Definition.** For each asset, B0 selects exactly one viewpoint:

```
v_B0 = the candidate with yaw = gauge_normal − π, distance = d_desired.
```

- This is the centre candidate from the generation algorithm (i = floor(N/2)).
- The robot directly faces the gauge at the desired standoff distance.
- It is deterministic, reproducible, and represents the pose any engineer would intuitively choose.
- B0 does **not** use the quality score; it is an independent baseline.

**Failure semantics.** B0 always navigates to its single fixed viewpoint regardless of V = 0 (occlusion) or obstruction. If the robot reaches the pose but no valid gauge reading is obtained (e.g. reader fails, confidence < 0.80, target occluded in the image), the asset is marked failed for B0. B0 does **not** switch to a different candidate viewpoint — that is the defining characteristic of the fixed-waypoint baseline.

## Baseline methods summary

| ID | Name | Description |
|----|------|-------------|
| B0 | Fixed waypoint | Single head-on pose per asset (as defined above). |
| B1 | Nearest feasible | Choose the reachable candidate with minimum travel cost. |
| P1 | Perception-aware | Choose the reachable candidate with maximum Q(v,a). |
| P2 | Adaptive | P1 + re-inspection on low confidence (try next-best candidate). |

B0 vs B1 vs P1 vs P2 forms the flagship viewpoint-policy comparison in experiment E4.