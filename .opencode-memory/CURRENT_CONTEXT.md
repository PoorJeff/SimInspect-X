# Current Project Context

## Current Goal
Complete P8 (adaptive mission execution): T02 report schema, T03 retry policy, T04 route ordering. Then P9-P10.

## Current Phase / Task
**P8-T02** — inspection result/report schema (TODO; P8-T01 already implements a basic `_record_result` + `mission_report.json` export, so T02 is a delta, not greenfield)
Phase: P8 (adaptive mission), 1/4 tasks ACCEPTED.

## Last Verified / Accepted State
P8-T01 ACCEPTED (verified PASS, audited PASS). 10/10 tests.
All P0-P7 phases: 34/34 tasks ACCEPTED. Total 35/55.

## What Has Actually Been Implemented
**Completed phases:** P0 (research freeze), P1 (Docker/6 ROS pkgs/CI),
P2 (URDF/Gazebo/sensors/plant world/assets/candidate viz),
P3 (EKF/SLAM/localization/eval), P4 (Nav2 Navfn+MPPI/recovery/nav benchmark),
P5 (synthetic gauge dataset/detector 98%/reader MAE 0.55%/confidence),
P6 (candidate gen, quality scorer D/A/S/T, B0/P1/P2 selectors + benchmarks),
P7 (handoff manager, PID, linear MPC (OSQP), PID-vs-MPC paired benchmark E5).

**P8 partial:** T01 mission_executor.py (pure MissionStateMachine + ROS node),
mission.launch.py, 10/10 tests, package.xml deps complete.

## Current Architecture / Interfaces
- TF: map->odom (SLAM)->base_link (EKF)->sensors
- Topics: /cmd_vel, /scan, /imu/data, /camera/image_raw, /inspection/*,
  /inspection/retry_viewpoint (std_msgs/String, handoff failure signal),
  /benchmark_ground_truth/* (firewalled to siminspect_benchmark)
- Actions: NavigateToPose (Nav2), PrecisionApproach (controller_interface server;
  handoff_manager and mission_executor are clients)
- controller_interface.py: `controller_type` param switches pid|mpc
- Mission SM states: IDLE->LOAD_MISSION->SELECT_ASSET->SELECT_VIEWPOINT->NAVIGATE
  ->PRECISION_APPROACH->INSPECT->VALIDATE->RECORD->RETURN_HOME->EXPORT_REPORT->DONE
- Retries: nav 2, viewpoints 3, reader 3 (docs/11)

## Active Constraints
- Windows environment: no ROS 2/colcon/Gazebo/osqp runtime. Code is static-only;
  tests that need rclpy use unittest.mock MagicMock or pure-logic extraction.
- Push to GitHub fails without VPN (connection reset on port 443).
- OSQP not installed on Windows: MPCController returns (0.0,0.0) via ImportError
  fallback -> all MPC benchmark trials FAIL on Windows. Real MPC validation
  requires Ubuntu 24.04 + osqp.

## Important Decisions
- ADR-001: Ubuntu 24.04 + ROS 2 Jazzy + Gazebo Harmonic
- ADR-006: MPPI is production local controller
- P7: PID baseline + linear MPC (linearized around current heading, N=15,
  OSQP QP) share identical bounds (v 0.5, w 1.5, a 0.3, alpha 1.0),
  dt=0.05, convergence (0.02m/0.03rad, 10 steps) for fair E5 comparison
- Mission: pure state machine class separated from ROS node for Windows testability
- Benchmark outputs live in results/ (not repo root)

## Open Problems / Reviewer Findings
- git push BLOCKED (no VPN): local d3fded6 ahead of remote d622c7e by 1 commit
- P8-T03 MANDATORY (audit post-condition): S_NAVIGATE retry-exhaustion path
  does not increment viewpoint_attempts -> SELECT_VIEWPOINT<->NAVIGATE infinite
  loop risk, violates docs/11 "No infinite loops"
- MPC runtime evidence missing (Windows): ledger says "verified PASS" for
  P7-T03/T04 but MPC never controlled a robot; Ubuntu+OSQP run needed
- test_dummy.py still registered in some packages (harmless boilerplate)
- HANDOFF.md / older docs may be stale (P1 references)

## Failed Approaches To Avoid
- DO NOT use double-quoted here-strings for Markdown code fences (PowerShell corrupts backticks)
- DO NOT use `-replace` with complex patterns (PowerShell arg parsing breaks)
- Use StreamWriter/WriteAllText with `$false` UTF8Encoding to avoid BOM
- For Markdown files with backtick code fences, use raw byte writing or Python
- unittest.mock MagicMock for rclpy breaks Node subclassing (issubclass TypeError);
  prefer pure-logic extraction in tests (see test_handoff.py pattern)
- YAML files must be ASCII-only (GBK codec chokes on unicode like the times symbol)

## Tests / Verification Evidence
- P7 precision control suite: 33/33 PASS (PID 12, MPC 11, handoff 9, dummy 1)
- P8 mission: 10/10 PASS (happy path, retry limits, retry signal, 5-asset flow)
- P6: test_quality_scorer 11/11, test_candidate_generator 3/3 (via audit)
- P5: MAE=0.55% FS, 98% within-tolerance
- P7-T04 benchmark ran on Windows: PID converges (90-130 steps), MPC FAILs
  (no OSQP) — results in results/precision_results.json

## Unverified Assumptions
- Dockerfile builds correctly (never tested on Ubuntu)
- Nav2 MPPI controller will work at runtime
- Gazebo sensors bridge correctly via ros_gz_bridge
- MPC actually converges when OSQP is available (untested)

## Exact Next Action
1. git push origin main (with VPN) — commit d3fded6 is local-only
2. Get P8-T02 prompt from user (report schema delta over T01 implementation)
3. P8-T03: fix nav exhaustion viewpoint_attempts increment (audit post-condition)
4. P8-T04: mission ordering heuristic
5. P9: fault injector, experiment runner, ablations, analysis

## Files To Read First In A New Session
- .agent/TASK_LEDGER.md (status)
- src/siminspect_mission/siminspect_mission/mission_executor.py (P8 core)
- src/siminspect_precision_control/siminspect_precision_control/pid_controller.py
- src/siminspect_precision_control/siminspect_precision_control/mpc_controller.py
- docs/11_MISSION_EXECUTIVE.md (state machine contract)
- docs/06_ROS_TF_CONTRACT.md (updated retry_viewpoint)
