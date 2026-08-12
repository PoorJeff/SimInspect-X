# Open Issues

Unresolved issues and blockers only. Resolved items are kept with a strike-through note.

## RESOLVED — OI-001 git push blocked (network)
- RESOLVED 2026-08-13: VPN active, push succeeded. Remote main = dc8cb7b.

## RESOLVED — OI-002 Nav retry exhaustion does not consume viewpoint attempt
- RESOLVED 2026-08-13 (commit dc8cb7b): S_NAVIGATE exhaustion now sets
  nav_retries=0, viewpoint_attempts+=1, then SELECT_VIEWPOINT or SELECT_ASSET.
  Test test_nav_exhaustion_no_infinite_loop proves bounded behaviour.
  Recorded as D-010.

## OI-003 — MPC runtime evidence missing
- Severity: MEDIUM (evidence gap)
- P7-T03/T04 marked ACCEPTED "verified PASS" but MPC has never produced a real
  control command (Windows lacks osqp; fallback returns 0.0; benchmark shows
  MPC success_rate 0.0 on Windows). Needs an Ubuntu 24.04 + osqp run to
  demonstrate MPC convergence and to make the E5 comparison real.
- Ledger wording should be revisited if this run cannot happen before the
  final report.

## OI-004 — Stale boilerplate/docs
- Severity: LOW
- test_dummy.py registered in some CMakeLists (harmless but causes pytest
  module-basename collision when two packages are run in one command — see
  FA-008); HANDOFF.md and older docs still reference P1/P2 phases.
- Clean up before P10 documentation tasks.

## OI-005 — Unverified Ubuntu assumptions
- Severity: MEDIUM (risk)
- Dockerfile never built on Ubuntu; Nav2 MPPI runtime behaviour unverified;
  ros_gz_bridge sensor data unverified. All blocked on the same missing Ubuntu
  environment as OI-003.

## OI-006 — `task` subagent tool availability varies by session
- Severity: LOW (workflow)
- In the last session the `task` tool was unavailable, so /verify-work and
  /audit-work could not be invoked by the agent; the user ran them via their
  own UI, and the final C2 re-check was done with manual read-only verification
  plus pytest. Future sessions should detect tool availability early and fall
  back to manual verification rather than stalling.

## RESOLVED — OI-007 Cross-asset current_reading leakage (audit R1)
- RESOLVED 2026-08-13 (P8-T02): MissionExecutor._tick S_SELECT_ASSET now
  resets current_reading/selected_viewpoint before E_TICK. A failed asset
  that produced no reading can no longer reuse the previous asset's
  reading (was misrecorded as success). Found by /audit-work round 1;
  fix re-verified + re-audited PASS (32/32 tests).

## OI-008 — Nav retry with remaining budget does not re-trigger goal
- Severity: LOW (deferred to P8-T03)
- E_NAV_FAIL with retries left keeps state S_NAVIGATE, but MissionExecutor
  ._tick only reacts to state CHANGES, so no new Nav2 goal is sent; the
  retry relies on the original async callback path. Revisit in P8-T03
  (route/asset retry policy).

## OI-009 — docs/06 lists /inspection/candidate_viewpoints subscription
- Severity: LOW (T01 leftover)
- docs/06 ROS contract lists the mission node subscribing to
  /inspection/candidate_viewpoints, but mission_executor.py does not
  subscribe to it. Reconcile docs and code during P8-T03/P10 cleanup.
