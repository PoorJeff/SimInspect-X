# Current Project Context

## Current Goal
Complete P6-T05 (adaptive re-inspection / P2 selector), then P7-P10 phases.

## Current Phase / Task
**P6-T05** — P2 adaptive selector (IN PROGRESS, header done, methods pending)
Phase: P6 (viewport planning), 4/5 tasks ACCEPTED.

## Last Verified / Accepted State
P6-T04 ACCEPTED (P1 selector + benchmark + paired config).
P6-T05 READY_FOR_REVIEW not yet reached — p2_selector.py has header only.
All P0-P5 phases: 25/25 tasks ACCEPTED.

## What Has Actually Been Implemented
**Completed phases:** P0 (research freeze, 5 docs), P1 (Docker/6 ROS pkgs/CI),
P2 (URDF/Gazebo/sensors/plant world/5 assets/candidate viz),
P3 (EKF/SLAM/localization/eval harness),
P4 (Nav2 NavfnPlanner+MPPI/DWB/recovery/nav benchmark),
P5 (synthetic gauge dataset 600 images/detector 98% acc/reader MAE 0.55%/confidence estimator).

**P6 partial:** T01 candidate gen+raycaster, T02 quality scorer D/A/S/T formulas,
T03 B0 fixed-waypoint selector+benchmark, T04 P1 perception-aware selector+benchmark.
**P6-T05 blocker:** p2_selector.py header exists (P2Selector class, CONF_THRESHOLD=0.80,
MAX_ATTEMPTS=3, import structure). Three methods still need to be appended:
`on_reading()`, `select_for_asset()`, `_select_next_best()`.
Also needed: run_p2_benchmark.py, p2_experiment.yaml, test_p2_selector.py, CMakeLists updates.

## Current Architecture / Interfaces
- TF: map→odom (SLAM)→base_link (EKF)→sensors
- Topics: /cmd_vel, /scan, /imu/data, /camera/image_raw, /inspection/*, /benchmark_ground_truth/*
- 12 ROS packages in src/ (6 buildable, 6 skeleton for P2-P4)
- Firewall: /benchmark_ground_truth/* only in siminspect_benchmark

## Active Constraints
- Windows environment: no ROS 2/colcon/Gazebo runtime. All code is static-only.
- Push to GitHub fails without VPN.
- Large amounts of uncommitted P3/P4/P5/P6 work in working tree.

## Important Decisions
- ADR-001: Ubuntu 24.04 + ROS 2 Jazzy + Gazebo Harmonic
- ADR-006: MPPI is production local controller
- B0 fixed waypoint: center candidate, V=0 still navigates, no switching
- P1: max Q among V>0 candidates
- P2: P1 + confidence < 0.80 → next-best Q, max 3 attempts

## Open Problems / Reviewer Findings
- All P3-P6 code uncommitted — needs git add + commit + push
- p2_selector.py incomplete (3 methods missing)
- PROJECT_STATE.md stale (says P1_COMPLETE, actually P6)
- plant.sdf walls may block some gauge access

## Failed Approaches To Avoid
- DO NOT use double-quoted here-strings for Markdown code fences (PowerShell corrupts backticks)
- DO NOT use `-replace` with complex patterns (PowerShell arg parsing breaks)
- Use StreamWriter with `$false` UTF8Encoding to avoid BOM
- For Markdown files with backtick code fences, use raw byte writing or Python

## Tests / Verification Evidence
- P5: test_gauge_reader MAE=0.0055 (0.55% FS), 98% within-tolerance
- P5: test_confidence_correlation: high-conf MAE 0.025 vs low-conf 0.071
- P6: test_quality_scorer 11/11 pass, test_candidate_generator 3/3 pass

## Unverified Assumptions
- Dockerfile builds correctly (never tested on Ubuntu)
- Nav2 MPPI controller will work at runtime
- Gazebo sensors bridge correctly via ros_gz_bridge

## Exact Next Action
1. Append 3 methods to p2_selector.py (see p2_selector.py header for class structure)
2. Create run_p2_benchmark.py, p2_experiment.yaml, test_p2_selector.py
3. Update CMakeLists.txt in both siminspect_viewpoint_planner and siminspect_benchmark
4. Update TASK_LEDGER P6-T05 → READY_FOR_REVIEW
5. git add -A && git commit -m "P3-P6: complete through P6-T04" && git push (with VPN)

## Files To Read First In A New Session
- .agent/TASK_LEDGER.md (task status)
- src/siminspect_viewpoint_planner/siminspect_viewpoint_planner/p2_selector.py (incomplete)
- src/siminspect_viewpoint_planner/siminspect_viewpoint_planner/p1_selector.py (reference)
- docs/07_ASSET_AND_VIEWPOINT_MODEL.md (quality formulas)
