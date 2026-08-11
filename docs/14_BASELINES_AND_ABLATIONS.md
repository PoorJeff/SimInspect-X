# Baselines and Ablations

## Flagship baselines

### B0 — Fixed waypoint
**Definition.** For each asset, one pre-determined viewpoint:
```
v_B0 = the candidate with yaw = gauge_normal − π, distance = d_desired.
```
This is the centre candidate from `docs/07_ASSET_AND_VIEWPOINT_MODEL.md` (centre of the ±60° arc).
B0 does **not** use the quality score; it is an independent baseline.
If the fixed viewpoint is occluded (V = 0) or unreachable, B0 still attempts navigation;
failure to obtain a valid reading marks the asset failed for B0.

**Pseudo-code:**
```
for each asset a:
    v ← centre candidate for a  (yaw = gauge_normal − π, d = d_desired)
    navigate to v with Nav2
    approach with precision controller (if enabled)
    read gauge → value, confidence
    if valid gauge reading: asset success
    else: asset failed for B0
```

### B1 — Nearest feasible candidate
**Definition.** From the set of generated candidates with V > 0 (reachable, visible),
select the one with minimum Euclidean travel cost T.

**Pseudo-code:**
```
for each asset a:
    candidates ← generate N candidates for a
    candidates ← filter(V > 0)
    v ← argmin T(v, robot_pose)
    navigate to v with Nav2
    approach with precision controller (if enabled)
    read gauge → value, confidence
    if valid gauge reading: asset success
    else: asset failed for B1
```

### P1 — Perception-aware (proposed)
**Definition.** From the set of generated candidates with V > 0, select the one with
maximum quality score Q(v, a) as defined in `docs/07_ASSET_AND_VIEWPOINT_MODEL.md`.

**Pseudo-code:**
```
for each asset a:
    candidates ← generate N candidates for a
    candidates ← filter(V > 0)
    for each v in candidates:
        compute Q(v, a) = w_vis·V + w_d·D + w_θ·A + w_s·S − w_t·T
    v ← argmax Q(v, a)
    navigate to v with Nav2
    approach with precision controller (if enabled)
    read gauge → value, confidence
    if valid gauge reading: asset success
    else: asset failed for P1
```

### P2 — Adaptive (proposed)
**Definition.** P1 with confidence-triggered re-inspection.
After a reading, if confidence < threshold OR the reading is invalid,
blacklist the current viewpoint and select the next-best candidate by Q(v, a).
Continue until a valid reading is obtained or all reachable candidates are exhausted.

**Pseudo-code:**
```
for each asset a:
    candidates ← generate N candidates for a
    candidates ← filter(V > 0)
    blacklist ← {}
    for attempt in 1..max_attempts:
        candidates ← candidates \ blacklist
        if candidates empty: break
        for each v in candidates:
            compute Q(v, a)
        v ← argmax Q(v, a)
        navigate to v with Nav2
        approach with precision controller (if enabled)
        read gauge → value, confidence
        if valid gauge reading: asset success; break
        blacklist ← blacklist ∪ {v}
    if no valid reading: asset failed for P2
```

## Key ablations

A1: remove visibility term (w_vis = 0).
A2: remove incidence-angle term (w_θ = 0).
A3: remove travel-cost term (w_t = 0).
A4: disable adaptive re-inspection (P1 only, no re-inspection loop).
A5: EKF on/off under wheel noise.
A6: PID vs MPC.

## Why this matters
An admissions reviewer should be able to see which part of the proposed method actually creates improvement.