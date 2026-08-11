# Baselines and Ablations

## Flagship baselines

### B0 Fixed waypoint
One manually selected pose per asset.

### B1 Nearest feasible candidate
Multiple candidates, choose minimum travel cost.

### P1 Perception-aware
Choose maximum viewpoint-quality score.

### P2 Adaptive
P1 + re-inspection when confidence is too low.

## Key ablations

A1: remove visibility term.
A2: remove incidence-angle term.
A3: remove travel-cost term.
A4: disable adaptive re-inspection.
A5: EKF on/off under wheel noise.
A6: PID vs MPC.

## Why this matters
An admissions reviewer should be able to see which part of the proposed method actually creates improvement.
