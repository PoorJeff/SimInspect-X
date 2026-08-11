# Project Thesis

## Primary research question

Can a **perception-aware viewpoint selection and adaptive re-inspection policy** improve the reliability of autonomous
industrial visual inspection compared with a conventional fixed-waypoint policy?

## Hypotheses

### H1 — inspection success
Perception-aware viewpoint selection increases the proportion of assets for which a valid gauge reading is obtained.

### H2 — perception quality
The method reduces absolute gauge-reading error under occlusion, viewpoint-angle and distance perturbations.

### H3 — efficiency trade-off
Adaptive re-inspection improves inspection success at a measurable cost in travel distance/time; the project should
quantify this trade-off rather than hide it.

### H4 — control
For final viewpoint alignment under constraints, MPC reduces pose/heading error or constraint violations compared
with a tuned PID baseline in at least some stress conditions.

## Why this is a research project rather than a demo

A demo answers:
"Can the robot reach a gauge?"

This project answers:
"Which camera viewpoint should the robot choose, how precisely should it approach, how does it know the view was
good enough, and what should it do if the inspection is uncertain?"
