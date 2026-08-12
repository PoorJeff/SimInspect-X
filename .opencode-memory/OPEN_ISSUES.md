# Open Issues

Unresolved issues and blockers only.

## OI-001 — git push blocked (network)
- Severity: HIGH (workflow)
- Local commit d3fded6 (P7-T02..T04 + P8-T01) is ahead of remote d622c7e by 1.
  Push fails: "Failed to connect to github.com port 443" (no VPN).
- Action: enable VPN, run `git push origin main`

## OI-002 — Nav retry exhaustion does not consume viewpoint attempt (P8-T03 MANDATORY)
- Severity: HIGH (correctness)
- mission_executor.py S_NAVIGATE branch: after MAX_NAV_RETRIES failures it goes
  to S_SELECT_VIEWPOINT without incrementing viewpoint_attempts. If navigation
  keeps failing, SELECT_VIEWPOINT<->NAVIGATE loops forever — violates docs/11
  "No infinite loops".
- Audit post-condition for P8-T03. Fix: increment viewpoint_attempts on nav
  exhaustion and reset nav_retries.

## OI-003 — MPC runtime evidence missing
- Severity: MEDIUM (evidence gap)
- P7-T03/T04 marked ACCEPTED "verified PASS" but MPC has never produced a real
  control command (Windows lacks osqp; fallback returns 0.0; benchmark shows
  MPC success_rate 0.0 on Windows). Needs an Ubuntu 24.04 + osqp run to
  demonstrate MPC convergence and to make the E5 comparison real.
- Ledger wording should be revisited if this run cannot happen before final report.

## OI-004 — Stale boilerplate/docs
- Severity: LOW
- test_dummy.py registered in some CMakeLists (harmless); HANDOFF.md and older
  docs still reference P1/P2 phases. Clean up before P10 documentation tasks.

## OI-005 — Unverified Ubuntu assumptions
- Severity: MEDIUM (risk)
- Dockerfile never built on Ubuntu; Nav2 MPPI runtime behaviour unverified;
  ros_gz_bridge sensor data unverified. All blocked on the same missing Ubuntu
  environment as OI-003.
