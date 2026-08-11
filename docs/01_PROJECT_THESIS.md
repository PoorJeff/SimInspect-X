# Project Thesis

## Primary research question

Can a **perception-aware viewpoint selection and adaptive re-inspection policy** improve the reliability of autonomous
industrial visual inspection compared with a conventional fixed-waypoint policy?

## Hypotheses

### H1 — Inspection Success

**Claim.** Under occlusion, viewpoint-angle, and distance perturbations (experiment E4),
P2 (perception-aware + adaptive re-inspection) achieves a higher proportion of
**valid gauge readings** than B0 (fixed waypoint).

A **valid gauge reading** is defined as:

> confidence ≥ 0.80  ∧  |estimated_value − ground_truth| ≤ 5 % of full-scale range.

- Dependent variable: proportion of assets yielding at least one valid reading.
- Comparison: B0 vs P1 vs P2, paired seeds.
- Statistical plan: McNemar or paired z-test for proportions, α = 0.05, paired seeds.

### H2 — Perception Quality

**Claim.** Under occlusion, viewpoint-angle, and distance perturbations (experiment E4),
P2 reduces absolute gauge-reading error compared with B0.

- Dependent variables: MAE, RMSE, within-tolerance rate (|error| ≤ 5 % FS).
- Comparison: B0 vs P1 vs P2, paired seeds.
- Statistical plan: paired difference test, α = 0.05; normality check determines
  paired t-test vs Wilcoxon signed-rank.

### H3 — Efficiency Trade-off

**Claim.** Adaptive re-inspection (P2) improves inspection success at a measurable cost
in travel distance and mission time. The project quantifies this trade-off
**without imposing a hard upper bound**.

- Dependent variables: extra travel distance (P2 − B0), extra mission time (P2 − B0),
  success-rate gain (P2 − B0).
- Analysis: descriptive statistics, paired t-test on extra distance (α = 0.05),
  trade-off table, Pareto frontier plot (x = extra distance, y = success rate).
- No hard threshold; the full distribution is reported.

### H4 — Precision Control

**Claim.** For the final precision-approach stage, constrained MPC reduces
pose/heading error or constraint violations compared with a tuned PID baseline
under stress conditions, while performing comparably under nominal conditions.

Conditions are drawn from experiment E5 and organised into two tiers:

| Tier | Conditions | Statistical treatment |
|------|-----------|----------------------|
| Tier 1 (primary) | nominal, initial yaw error, measurement noise, wheel slip | paired t-test, Bonferroni-corrected α = 0.05 / 4 = 0.0125 |
| Tier 2 (exploratory) | saturation | descriptive comparison only (n ≈ 5) |

- Dependent variables: final position error, final yaw error, constraint violations,
  settling time, control effort.
- Comparison: PID vs MPC, paired seeds.

## Operational definitions

| Term | Definition |
|------|-----------|
| **Valid gauge reading** | confidence ≥ 0.80  ∧  |estimate − ground truth| ≤ 5 % full-scale range. If confidence is null, NaN, or absent, the reading is invalid. |
| **Inspection success** (per asset) | at least one valid reading obtained within max_attempts and timeout |
| **Station attempt** | one navigation + approach + read cycle for a single asset |
| **Full-scale range** | gauge.max_value − gauge.min_value (e.g. 100 psi for a 0–100 psi gauge) |
| **Mission** | A sequence of 5–8 assets, visited in planned order, with the robot returning home |
| **Paired trial** | Two or more methods run on the same mission, scenario, and random seed |

## Statistical plan summary

| Hypothesis | Experiment | Primary metric | Comparison | Test | α | Correction |
|-----------|-----------|---------------|-----------|------|---|-----------|
| H1 | E4 | Valid-read proportion | B0 vs P1 vs P2 | McNemar / paired z-test | 0.05 | none (B0 vs P1 and B0 vs P2, report unadjusted) |
| H2 | E4 | MAE, RMSE, within-tol. rate | B0 vs P1 vs P2 | paired t-test or Wilcoxon | 0.05 | none |
| H3 | E4 | Extra distance, extra time | B0 vs P2 | paired t-test on distance | 0.05 | none; supplemented by trade-off table |
| H4 Tier 1 | E5 | Final pose error, violations | PID vs MPC | paired t-test | 0.0125 | Bonferroni (4 conditions) |
| H4 Tier 2 | E5 | Descriptive only | PID vs MPC | — | — | n ≈ 5 |

- All tests use a paired design (identical mission, scenario, and random seed across compared methods).
- Normality is assessed per hypothesis; the final test choice (t vs Wilcoxon) is deferred
  to the analysis phase.
- Minimum trial counts: 3–5 during development; ≥ 10 per condition for final results;
  20–30 preferred for flagship H1/H2/H3 comparisons.
- All failed trials are retained in the dataset.

## Cross-reference: hypothesis → experiment → metric

| Hypothesis | Experiment | Primary metric | Comparative methods |
|-----------|-----------|---------------|-------------------|
| H1 | E4 — Viewpoint policy | Valid-read proportion | B0, P1, P2 |
| H2 | E4 — Viewpoint policy | MAE, RMSE, within-tol. rate | B0, P1, P2 |
| H3 | E4 — Viewpoint policy | Extra distance, extra time | B0 vs P2 |
| H4 Tier 1 | E5 — Precision control | Final pose/yaw error, constraint violations | PID vs MPC |
| H4 Tier 2 | E5 — Precision control | Descriptive comparison | PID vs MPC |

## Why this is a research project rather than a demo

A demo answers:
"Can the robot reach a gauge?"

This project answers:
"Which camera viewpoint should the robot choose, how precisely should it approach,
how does it know the view was good enough, and what should it do if the inspection
is uncertain?"
