# SimInspect-X Research Report

**Status: framework complete; experimental results pending Ubuntu runtime
verification (OI-005).** No performance claims are made in this document;
placeholder tables are marked PENDING and will be filled only from raw
experiment files (docs/16).

## 1. Abstract and Research Questions

**Abstract.** SimInspect-X is a simulation-first autonomous inspection robot for
industrial analog gauges. A differential-drive AMR in Gazebo localises with
wheel/IMU EKF and SLAM, navigates with Nav2, selects inspection viewpoints with
a perception-aware quality score, approaches precisely with PID or constrained
linear MPC, reads gauges from camera images, and re-inspects adaptively when
reading confidence is low. The project's original contributions are the
viewpoint quality model, the adaptive re-inspection policy, the PID-vs-MPC
precision-control comparison, and a seeded fault-injection experiment harness.
The full stack is implemented, unit-tested, and packaged behind a one-command
headless demo; runtime evaluation on the Ubuntu/Gazebo target is pending
(Windows development host has no ROS runtime). This report describes the
design, implementation, and verification framework; it does not yet report
experimental results.

**Research questions** (see docs/01_PROJECT_THESIS.md for the full hypothesis
table):

- **H1** — Perception-aware viewpoint selection improves the valid-read
  proportion of inspections relative to a fixed-waypoint baseline.
  Experiment E4; comparison B0 vs P1 and B0 vs P2; alpha = 0.05,
  p-values reported unadjusted.
- **H2** — The proposed policy reduces gauge-reading error (MAE/RMSE,
  within-tolerance rate) relative to the baseline (E4, gauge metrics per
  docs/13).
- **H3** — The success gain is achieved at a bounded mission-efficiency cost
  (extra travel distance / mission time; trade-off analysis, E4).
- **H4 (Tier 1)** — MPC achieves lower final pose/yaw error and fewer
  constraint violations than PID on the precision approach, under matched
  conditions (E5). Bonferroni-corrected alpha = 0.05/4 = 0.0125
  (4 conditions).

## 2. System Architecture

Layered pipeline (docs/03_SYSTEM_ARCHITECTURE.md, docs/06_ROS_TF_CONTRACT.md):

1. **Simulation** — Gazebo Harmonic plant world, differential-drive AMR,
   LiDAR/IMU/RGB camera (P2).
2. **State estimation** — wheel odometry + IMU EKF (robot_localization);
   SLAM Toolbox mapping / saved-map localisation (P3).
3. **Navigation** — Nav2 with Navfn global planner and MPPI local controller,
   blocked-route recovery (P4).
4. **Viewpoint planning** — candidate generation, visibility/quality scoring,
   fixed-waypoint (B0), nearest-candidate (B1), perception-aware (P1),
   adaptive (P2) selectors (P6).
5. **Precision control** — handoff manager + controller interface switching
   between PID and constrained linear MPC (P7).
6. **Mission execution** — multi-asset state machine with bounded retries,
   failure recording, optional greedy ordering (P8).
7. **Gauge vision** — detection, rectification, colour-based needle reading,
   confidence proxy (P5; ROS node wired in P10-T01).
8. **Benchmark isolation** — ground-truth topics live under
   `/benchmark_ground_truth/` and are firewalled from production autonomy
   (docs/06, dual-layer CI enforcement).

ROS 2, Gazebo, Nav2, SLAM Toolbox and robot_localization are reused
infrastructure (docs/04_ORIGINALITY_BOUNDARY.md); originality is concentrated
in viewpoint scoring, adaptive re-inspection, precision-control comparison,
and the experiment harness.

## 3. Method

**Viewpoint quality score** (docs/07_ASSET_AND_VIEWPOINT_MODEL.md,
`quality_scorer.py`): for each candidate viewpoint v of asset a,

```text
Q(v,a) = w_vis*V + w_d*D + w_theta*A + w_s*S - w_t*T
```

with default weights `w_vis=0.35, w_d=0.25, w_theta=0.25, w_s=0.15,
w_t=0.15`; V = visibility (binary), D = distance-to-desired term, A =
incidence-angle term (max 40 deg), S = clearance/safety term, T = normalised
travel cost. Candidates: N=7 viewpoints on a +-60 deg arc around the gauge
face normal at the desired distance.

**Policies** (docs/14_BASELINES_AND_ABLATIONS.md):
- **B0** — fixed centre viewpoint per asset; no scoring.
- **B1** — nearest feasible (visible) candidate by travel cost.
- **P1** — argmax Q over visible candidates.
- **P2** — P1 plus confidence-triggered re-inspection: reading confidence
  below 0.80 blacklists the viewpoint and selects the next-best candidate,
  up to 3 attempts per asset.

**Precision approach** (docs/10_PRECISION_CONTROL.md, D-005/D-006): PID and
MPC share identical actuator bounds, timestep and convergence criteria for a
fair paired comparison. MPC uses a heading-linearised kinematic model with
horizon N=15 and OSQP; on hosts without OSQP it falls back to zero output
(which is why MPC runtime evidence is still pending — see Section 7).

**Mission execution** (docs/11_MISSION_EXECUTIVE.md): state machine
IDLE -> LOAD_MISSION -> SELECT_ASSET -> SELECT_VIEWPOINT -> NAVIGATE ->
PRECISION_APPROACH -> INSPECT -> VALIDATE -> RECORD -> RETURN_HOME ->
EXPORT_REPORT, with bounded retries (nav 2, viewpoints 3, reader 3) and a
v1.0 JSON report schema (true_value/absolute_error left null for the
benchmark layer to fill).

## 4. Experimental Design

- **Experiments E1-E6** (docs/12_EXPERIMENT_PROTOCOL.md): E1 state
  estimation, E2 navigation, E3 gauge reader, E4 viewpoint policy
  (flagship), E5 precision control, E6 end-to-end mission.
- **Fault scenarios F00-F11** (docs/15_FAILURE_INJECTION.md,
  `fault_scenarios.yaml`): F00 nominal; F01 odom noise; F02 wheel slip;
  F03 IMU noise; F04 LiDAR dropout; F05 dynamic obstacle; F06 blocked
  fixed viewpoint; F07 camera blur; F08 camera dark; F09 gauge partial
  occlusion; F10 initial pose offset; F11 mixed stress. Each scenario is a
  single primary factor (F11 excluded), with deterministic parameters and a
  recorded seed.
- **Seeds** — final pool 0001-0020, development holdout 0021-0030; paired
  assignment: identical seeds across compared methods for a condition.
- **Ablations A1-A6** (docs/14): A1 w_vis=0; A2 w_theta=0; A3 w_t=0;
  A4 re-inspection disabled (P1-equivalent); A5 EKF on/off under wheel
  noise; A6 PID vs MPC (covered by E5).
- **Trial records** (docs/16_REPRODUCIBILITY.md): every trial stores commit,
  manifest, method, scenario, seed, world, mission, controller, planner
  params, result, failure reason, metrics under
  `experiments/raw/E{id}_{name}/{commit}/{method}/{scenario}/seed_XXXX.json`.
  Every figure in this report must be regenerated from those files.

## 5. Results (Placeholders)

> **PENDING — no Ubuntu runtime data (OI-005).** All tables below are
> placeholders. Cells will be filled exclusively from
> `experiments/raw/` via `analyze_results.py --root experiments/raw` and
> `generate_plots.py` (P9-T04); no values are invented here.

**Table 1 — E4 valid-read proportion (H1)** | method x scenario:
| Method | F00 | F06 | F07 | F10 | F11 | n |
|---|---|---|---|---|---|---|
| B0 | pending | ... | | | | pending |
| P1 | pending | ... | | | | pending |
| P2 | pending | ... | | | | pending |

*Fill from: `results/analysis_summary.json` (experiments.E4).*

**Table 2 — E4 gauge error (H2)**: MAE / RMSE / median / within-tolerance
rate per method — pending.

**Table 3 — E4 efficiency trade-off (H3)**: delta-success vs delta-distance
per method vs B0 — pending. *Figure: `results/plots/e4_tradeoff.png`.*

**Table 4 — E5 PID vs MPC (H4)**: final position error, final yaw error,
settling time, effort (abs/sq), constraint violations per method x condition
— pending. *Figure: `results/plots/e5_pid_mpc.png`.*

**Table 5 — Ablations A1-A4 vs P2** — pending.
*Figure: `results/plots/ablation_delta.png`.*

**Table 6 — Hypothesis tests**: H1 (B0 vs P1, B0 vs P2), H4 (PID vs MPC)
with p-values and significance at the stated alphas — pending.
*Fill from: `results/analysis_summary.json` (hypothesis_tests).*

**Table 7 — E1/E2/E6 robustness summary**: localisation RMSE, navigation
success/recovery, end-to-end mission success per fault — pending.

## 6. Statistical Methodology

- **H1**: paired t-test with Wilcoxon alternative (`scipy.stats.ttest_rel`,
  `wilcoxon`) on per-(scenario, seed) paired valid-read rates; p-values
  reported unadjusted per docs/01. The literal McNemar/paired-z notation in
  docs/01 was explicitly deferred to the analysis phase; both t and Wilcoxon
  statistics are reported for transparency.
- **H4**: Bonferroni-corrected alpha = 0.0125 (per docs/01) applied to a
  pooled final-position-error comparison across the E5 conditions; pooling is
  conservative (does not inflate significance), and the per-condition alpha
  is the correct threshold for any condition-level test.
- **Guards**: paired tests require n >= 3 paired samples; below that the
  output is `insufficient_pairs` with no significance claim. Degenerate
  (identical) pairs yield null p-values rather than NaN. Missing metrics are
  reported as null / `insufficient_data`, never estimated.

## 7. Limitations

1. **MPC runtime evidence missing (OI-003)**: MPC has never produced a real
   control command — Windows lacks OSQP, so the fallback returns zero and
   Windows benchmark trials fail. MPC convergence evidence requires an
   Ubuntu 24.04 + OSQP run.
2. **Ubuntu assumptions unverified (OI-005)**: the Dockerfile build, Nav2
   MPPI runtime behaviour, and ros_gz_bridge sensor bridging have not been
   executed; all runtime claims remain pending that environment.
3. **Missing harnesses**: B1 (nearest-candidate), E3 (standalone gauge
   reader) and E6 (end-to-end mission) benchmarks have no executable
   harnesses yet; the experiment matrix marks them `null` honestly.
4. **Synthetic gauge data**: the vision pipeline is validated on generated
   images; real Gazebo-rendered gauges may differ in appearance and
   illumination.
5. **Confidence proxy**: the confidence value is a weighted proxy of
   detection success, pointer strength, image area, view angle and
   consistency (docs/08_GAUGE_READING_TASK.md); it is uncalibrated and is
   therefore called a proxy rather than a probability (docs/18).

## 8. Claim Boundary

**Claimed** (backed by code, tests, and documentation):

- The system is *designed and implemented* end-to-end in a simulation-first
  testbed (one-command demo entry point, `run_demo.sh`).
- A *verification framework* exists: seeded fault injection, paired trial
  schema, ablation configuration, analysis and plotting scripts, and
  automated unit tests.

**Not claimed** (until Ubuntu runtime data exists):

- Any experimental result, performance number, or improvement ("improves X
  by Y%"). All such statements are reserved until the pending runs produce
  raw data, per docs/19_APPLICATION_PACKAGING.md ("Only use these after
  actual results exist").
- Physical deployment or real digital-twin synchronisation; the wording is
  deliberately "simulation-first".

When the Ubuntu runs complete, Sections 5-6 of this report are filled from
`experiments/raw/`, and the claim boundary is revised upward only with
regenerated evidence.