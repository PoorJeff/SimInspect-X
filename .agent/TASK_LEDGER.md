# TASK_LEDGER

Status values: TODO / IN_PROGRESS / READY_FOR_REVIEW / ACCEPTED / BLOCKED / DEFERRED

| ID | Task | Status | Acceptance evidence |
|---|---|---|---|
| P0-T01 | Freeze research thesis and hypotheses | ACCEPTED | verified PASS, audited PASS |
| P0-T02 | Freeze asset/viewpoint mathematical model | ACCEPTED | verified PASS, audited PASS |
| P0-T03 | Freeze gauge task and ground-truth separation | READY_FOR_REVIEW | inspection success criteria + timeout params + ground-truth topics + dual-layer CI firewall |
| P0-T04 | Freeze TF/topic/action contract | TODO | interface audit |
| P0-T05 | Freeze experiment baselines and metrics | TODO | experiment matrix |
| P1-T01 | Reproducible Ubuntu/ROS setup | TODO | clean install/build |
| P1-T02 | ROS package skeleton | TODO | colcon build |
| P1-T03 | CI build/lint/unit smoke | TODO | CI green |
| P2-T01 | Differential-drive URDF/Xacro | TODO | model validation |
| P2-T02 | gz_ros2_control integration | TODO | cmd -> motion |
| P2-T03 | LiDAR/IMU/RGB sensors | TODO | topic/rate tests |
| P2-T04 | Plant world and semantic asset registry | TODO | 5–8 assets |
| P2-T05 | Candidate viewpoint visualisation | TODO | RViz markers |
| P3-T01 | Wheel odom + IMU EKF | TODO | filtered odom |
| P3-T02 | SLAM Toolbox mapping | TODO | saved map |
| P3-T03 | Saved-map localisation | TODO | repeatable startup |
| P3-T04 | localisation evaluation harness | TODO | RMSE results |
| P4-T01 | Nav2 baseline | TODO | goal navigation |
| P4-T02 | MPPI configuration | TODO | stable plant routes |
| P4-T03 | blocked-route recovery | TODO | recovery evidence |
| P4-T04 | navigation baseline benchmark | TODO | paired trials |
| P5-T01 | synthetic gauge asset generator | TODO | labelled gauges |
| P5-T02 | gauge detection/rectification | TODO | image tests |
| P5-T03 | gauge value estimator | TODO | MAE/RMSE |
| P5-T04 | confidence estimator | TODO | calibrated proxy |
| P6-T01 | candidate viewpoint generator | TODO | deterministic candidates |
| P6-T02 | geometric visibility/quality scorer | TODO | unit tests |
| P6-T03 | fixed waypoint baseline | TODO | baseline runs |
| P6-T04 | perception-aware selector | TODO | comparison runs |
| P6-T05 | adaptive reinspection logic | TODO | low-confidence recovery |
| P7-T01 | precision approach interface | TODO | controller handoff |
| P7-T02 | PID controller | TODO | tracking tests |
| P7-T03 | linear MPC controller | TODO | constraint tests |
| P7-T04 | PID vs MPC paired benchmark | TODO | results/plots |
| P8-T01 | mission executive | TODO | multi-asset mission |
| P8-T02 | inspection result/report schema | TODO | JSON report |
| P8-T03 | route/asset retry policy | TODO | failure handling |
| P8-T04 | optional mission ordering heuristic | TODO | route comparison |
| P9-T01 | fault injector | TODO | scenario set |
| P9-T02 | experiment runner | TODO | seed sweep |
| P9-T03 | ablations | TODO | reproducible tables |
| P9-T04 | consolidated analysis | TODO | auto-generated plots |
| P10-T01 | one-command demo | TODO | clean run |
| P10-T02 | research-style report | TODO | completed report |
| P10-T03 | README + architecture + demo video | TODO | reviewer-ready |
| P10-T04 | CV/SOP evidence pack | TODO | measured claims only |
| S-T01 | anomaly detection extension | DEFERRED | optional |
| S-T02 | LLM mission parser | DEFERRED | optional |
| S-T03 | multi-robot inspection | DEFERRED | optional |
