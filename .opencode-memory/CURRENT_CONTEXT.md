# Current Project Context

## Current Goal
Complete P8 (adaptive mission execution): T02 report schema, T03 retry policy, T04 route ordering. Then P9-P10.

## Current Phase / Task
**P8-T02** — inspection result/report schema (TODO; P8-T01 already implements a basic `_record_result` + `mission_report.json` export, so T02 is a delta, not greenfield)
Phase: P8 (adaptive mission), 1/4 tasks ACCEPTED.

## Last Verified / Accepted State
P8-T01 ACCEPTED (verified PASS after C2 fix, audited PASS, committed + pushed).
Mission tests 11/11 (test_mission_executor) + 1 dummy = 12/12 package total.
Precision control suite 33/33. All P0-P7 phases: 34/34 ACCEPTED. Total 35/55.

## What Has Actually Been Implemented
**Completed phases:** P0 (research freeze), P1 (Docker/6 ROS pkgs/CI),
P2 (URDF/Gazebo/sensors/plant world/assets/candidate viz),
P3 (EKF/SLAM/localization/eval), P4 (Nav2 Navfn+MPPI/recovery/nav benchmark),
P5 (synthetic gauge dataset/detector 98%/reader MAE 0.55%/confidence),
P6 (candidate gen, quality scorer D/A/S/T, B0/P1/P2 selectors + benchmarks),
P7 (handoff manager, PID, linear MPC (OSQP), PID-vs-MPC paired benchmark E5).

**P8-T01 complete:** mission_executor.py (pure MissionStateMachine + ROS node),
mission.launch.py, package.xml deps, 11 tests incl. nav-exhaustion-no-infinite-loop,
viewpoint_index semantics fixed, return_home error handling fixed,
docs/06 retry_viewpoint contract rows.

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
- Retries: nav 2, viewpoints 3, reader 3 (docs/11). Nav exhaustion NOW consumes
  a viewpoint attempt and resets nav_retries (D-010, no infinite loops)

## Active Constraints
- Windows environment: no ROS 2/colcon/Gazebo/osqp runtime. Code is static-only;
  tests that need rclpy use pure-logic extraction (MagicMock for rclpy breaks
  Node subclassing).
- OSQP not installed on Windows: MPCController returns (0.0,0.0) via ImportError
  fallback -> all MPC benchmark trials FAIL on Windows. Real MPC validation
  requires Ubuntu 24.04 + osqp.
- The `task` subagent tool was NOT available in the last session; /verify-work
  and /audit-work were executed via user-invoked tools, and the final C2
  re-verification was done manually with read-only checks + pytest.

## Important Decisions
- ADR-001: Ubuntu 24.04 + ROS 2 Jazzy + Gazebo Harmonic
- ADR-006: MPPI is production local controller
- D-005: PID and MPC share identical bounds/dt/convergence for fair E5
- D-006: MPC = heading-linearized kinematic model, N=15, OSQP, ImportError->zero
- D-007: pure state machine separated from ROS node for Windows testability
- D-008: benchmark artifacts live in results/
- D-010: nav retry exhaustion consumes a viewpoint attempt (bounded retries)

## Open Problems / Reviewer Findings
- OI-003: MPC runtime evidence missing (Windows) — needs Ubuntu+OSQP run before
  final report; revisit ledger wording for P7-T03/T04 if it cannot happen
- OI-004: test_dummy.py boilerplate in some packages; HANDOFF.md stale (P1)
- OI-005: Ubuntu assumptions unverified (Dockerfile build, Nav2 MPPI runtime,
  ros_gz_bridge) — blocked on same missing Ubuntu env
- NEW: pytest module-name collision when running two packages in one command
  (both have test/test_dummy.py -> "unique basename" collection error).
  Run packages separately.

## Failed Approaches To Avoid
- See FAILED_APPROACHES.md (FA-001..FA-008)
- FA-008: running `pytest src/pkgA/test src/pkgB/test` in one invocation fails
  because both packages ship test_dummy.py (module basename collision);
  run each package's tests separately

## Tests / Verification Evidence
- Precision control suite: 33/33 PASS (PID 12, MPC 11, handoff 9, dummy 1)
- Mission package: 12/12 PASS (11 state-machine tests + dummy);
  includes test_nav_exhaustion_no_infinite_loop (bounded retries proof)
- P7-T04 benchmark ran on Windows: PID converges 90-130 steps; MPC all FAIL
  (no OSQP) — results/precision_results.json
- All new/modified Python files pass ast.parse

## Git / Remote State
- Remote main = dc8cb7b, working tree clean, push works (VPN active in last session)
- Commits: d622c7e (P3-P7+T01) -> d3fded6 (P7-T02..T04 + P8-T01) -> dc8cb7b (C2 fix + memory)

## Unverified Assumptions
- Dockerfile builds correctly (never tested on Ubuntu)
- Nav2 MPPI controller will work at runtime
- Gazebo sensors bridge correctly via ros_gz_bridge
- MPC actually converges when OSQP is available (untested)

## Exact Next Action
1. Ask user for P8-T02 prompt (report schema delta over T01's _record_result)
2. P8-T03: retry policy — note nav-exhaustion part already done (D-010);
   remaining T03 work: confirm approach/validate retry paths + failure records
3. P8-T04: mission ordering heuristic
4. P9: fault injector, experiment runner, ablations, analysis

## Files To Read First In A New Session
- .agent/TASK_LEDGER.md (status)
- src/siminspect_mission/siminspect_mission/mission_executor.py (P8 core)
- docs/11_MISSION_EXECUTIVE.md (state machine contract)
- docs/12_EXPERIMENT_PROTOCOL.md + docs/13_METRICS.md (P9 prep)
- .opencode-memory/OPEN_ISSUES.md (OI-003..OI-005)
