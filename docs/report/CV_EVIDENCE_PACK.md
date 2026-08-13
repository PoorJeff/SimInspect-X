# CV / SOP Evidence Pack

**Honesty banner:** this pack contains **no filled performance numbers**. Every
numeric CV field is marked `[pending — Ubuntu run]` and may only be filled
from raw trial files (`experiments/raw/`, docs/16) after the Ubuntu runtime
evaluation (OI-005). Usable-now statements are limited to
designed / implemented / validation-framework.

## Skills matrix

Curriculum themes from docs/02_ADMISSIONS_ALIGNMENT.md; every row carries a
verifiable evidence pointer.

| NTU curriculum theme | SimInspect-X evidence | Evidence files | Verifiability |
|---|---|---|---|
| Advanced Robotics & Autonomous Systems | end-to-end perception-cognition-action pipeline | `docs/report/REPORT.md`, `src/siminspect_mission/siminspect_mission/mission_executor.py` | 43 tests, TASK_LEDGER P8 ACCEPTED |
| Sensors and Data Fusion | wheel odometry + IMU EKF | `src/siminspect_localization/launch/ekf.launch.py`, `docs/06_ROS_TF_CONTRACT.md` | P3 ACCEPTED |
| Autonomous Mobile Robot | SLAM, localisation, planning, navigation, recovery | `src/siminspect_navigation/launch/navigation.launch.py` | P3/P4 ACCEPTED |
| Vision | gauge detection, rectification, reading, confidence proxy | `src/siminspect_gauge_vision/siminspect_gauge_vision/vision_pipeline.py` | package tests, P5 ACCEPTED |
| Advanced Linear Systems and Control | precision motion/control study | `src/siminspect_precision_control/siminspect_precision_control/pid_controller.py` | 33-test suite, P7 ACCEPTED |
| Metaverse and Digital Twin | **simulation-first** plant/asset testbed (deliberately not a digital twin; see docs/18 risk #12) | `docs/report/REPORT.md` §8, `src/siminspect_sim/worlds/plant.sdf` | honest boundary, no overclaim |
| Manufacturing Control and Automation | industrial inspection mission, asset-level workflow | `src/siminspect_mission/siminspect_mission/report_schema.py` | P8 ACCEPTED |
| Robotics Projects | end-to-end reproducible project + report | `docs/report/REPORT.md`, `run_demo.sh` | one-command entry, P10-T01 ACCEPTED |
| Computer Control Systems | digital feedback controller, sampling | `src/siminspect_precision_control/siminspect_precision_control/mpc_controller.py` | P7 ACCEPTED |
| Systems Analysis / optimisation | viewpoint scoring, optional mission ordering, quantitative models | `src/siminspect_viewpoint_planner/siminspect_viewpoint_planner/quality_scorer.py`, `src/siminspect_mission/siminspect_mission/mission_ordering.py` | P6/P8 ACCEPTED |
| Robotics & Intelligent Sensors | AMR, sensing, motion planning, integration | `run_demo.sh` (11 components) | P10-T01 ACCEPTED |
| Machine Vision | gauge reading chain | `src/siminspect_gauge_vision/siminspect_gauge_vision/gauge_vision_node.py` | node + pipeline tests |
| Multivariable Control / MPC | constrained linear MPC precision approach | `src/siminspect_precision_control/siminspect_precision_control/mpc_controller.py` | harness P7-T04 ACCEPTED (runtime evidence pending OI-003) |
| ML / optimisation electives | OSQP solver integration; scoring optimisation | `mpc_controller.py`, `quality_scorer.py` | P7/P6 ACCEPTED |

## CV bullets

Three categories per docs/19_APPLICATION_PACKAGING.md. Each has a **usable
now** version (no numbers) and a **pending numbers** template.

### Robotics / autonomy

- **Usable now:** Built a ROS 2 autonomous industrial-inspection robot
  simulation integrating state estimation, SLAM/localisation, Nav2 mission
  navigation, camera-based gauge reading and fault-tolerant multi-asset
  inspection — designed, implemented and unit-tested behind a one-command
  headless demo. *Evidence: `run_demo.sh`,
  `src/siminspect_mission/siminspect_mission/mission_executor.py`,
  `docs/report/REPORT.md`.*
- **Pending numbers:** "...evaluated `[pending — Ubuntu run]` seeded missions
  under the F00–F11 fault set (experiment harness ready; data pending OI-005)."
  *Fill only from `experiments/raw/` after the Ubuntu run.*

### Research contribution

- **Usable now:** Designed a perception-aware viewpoint-selection and
  confidence-triggered re-inspection policy (Q = w_vis*V + w_d*D + w_theta*A +
  w_s*S - w_t*T) with fixed-waypoint and nearest-candidate baselines;
  implementation, paired-trial schema, ablation config and statistical
  analysis framework are in place. *Evidence:
  `src/siminspect_viewpoint_planner/siminspect_viewpoint_planner/quality_scorer.py`,
  `p2_selector.py`, `docs/report/REPORT.md` §3–6.*
- **Pending numbers:** "...raising inspection success from
  `[pending — Ubuntu run]` to `[pending — Ubuntu run]` while changing mission
  travel cost by `[pending — Ubuntu run]` versus a fixed-waypoint baseline."
  *Fill only from `results/analysis_summary.json` after the Ubuntu run.*

### Control

- **Usable now:** Implemented and matched PID and constrained linear MPC
  (OSQP, horizon N=15) for the precision inspection-pose approach under
  identical bounds, timestep and convergence criteria (D-005/D-006).
  *Evidence: `src/siminspect_precision_control/siminspect_precision_control/
  pid_controller.py`, `mpc_controller.py`.*
- **Pending numbers:** "...reducing `[pending — Ubuntu run]` from
  `[pending — Ubuntu run]` to `[pending — Ubuntu run]` under matched kinematic
  and disturbance constraints." *Fill only from the E5 raw trials after the
  Ubuntu run (OI-003/OI-005).*

## Evidence map

| Claim | Repository file | Status |
|---|---|---|
| Full pipeline designed + implemented | `run_demo.sh`, `docs/report/REPORT.md` | P10-T01/T02 ACCEPTED |
| Viewpoint quality model | `src/siminspect_viewpoint_planner/siminspect_viewpoint_planner/quality_scorer.py` | P6 ACCEPTED |
| Adaptive re-inspection | `src/siminspect_viewpoint_planner/siminspect_viewpoint_planner/p2_selector.py` | P6 ACCEPTED |
| PID vs MPC harness | `src/siminspect_benchmark/siminspect_benchmark/run_precision_benchmark.py` | P7 ACCEPTED (runtime pending OI-003) |
| Fault injection (F00–F11) | `src/siminspect_benchmark/config/fault_scenarios.yaml` | P9-T01 ACCEPTED |
| Experiment runner + seeds | `src/siminspect_benchmark/siminspect_benchmark/experiment_runner.py` | P9-T02 ACCEPTED |
| Ablations A1–A6 | `src/siminspect_benchmark/siminspect_benchmark/run_ablations.py` | P9-T03 ACCEPTED |
| Consolidated analysis | `src/siminspect_benchmark/siminspect_benchmark/analyze_results.py` | P9-T04 ACCEPTED |
| Research report (honest placeholders) | `docs/report/REPORT.md` | P10-T02 ACCEPTED |
| Architecture diagram | `docs/report/architecture.png` | P10-T03 ACCEPTED |
| Demo video blueprint | `docs/report/demo_video_script.md` | P10-T03 ACCEPTED (video pending OI-005) |
| Reproducible demo config | `config/demo_config.yaml` | P10-T01 ACCEPTED |