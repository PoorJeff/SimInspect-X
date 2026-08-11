# Perception-Aware Viewpoint Planner

This is the main original module.

## Inputs
- semantic asset pose;
- candidate viewpoint set;
- occupancy/costmap information;
- robot current pose;
- camera intrinsics/FOV;
- previous failed viewpoints;
- latest inspection confidence.

## Output
Selected `PoseStamped`.

## Version 1 — deterministic geometric planner

For each candidate:
1. reject unreachable/occupied pose;
2. reject target outside camera FOV;
3. estimate line-of-sight;
4. score distance from desired standoff;
5. score incidence angle;
6. score local clearance;
7. subtract travel cost;
8. choose maximum score.

## Version 2 — adaptive
If gauge reading confidence < threshold:
- blacklist or penalise current viewpoint;
- choose next-best candidate;
- request re-inspection.

## Baselines

B0: single fixed waypoint.
B1: nearest feasible candidate.
P1: perception-aware quality score.
P2: perception-aware + adaptive re-inspection.

## Core comparison
B0 vs P1 vs P2.

## Optional route-level optimisation
After core acceptance:
select both asset order and candidate viewpoint to minimise mission cost while satisfying inspection constraints.
This can be formulated as a small combinatorial optimisation problem.
