# Decisions

Durable decisions with IDs. Status: ACTIVE / SUPERSEDED.

## D-001 — Platform: Ubuntu 24.04 + ROS 2 Jazzy + Gazebo Harmonic
- Status: ACTIVE
- Source: ADR-001, P0
- Impact: all Docker/CI/package config

## D-002 — Ground-truth isolation firewall
- Status: ACTIVE
- Decision: /benchmark_ground_truth/* accessible only by siminspect_benchmark;
  enforced at compile time (package.xml depend check) and runtime (rosgraph watchdog)
- Source: AGENTS.md rule 4-5, docs/06
- Impact: every new node must not import/subscribe GT topics

## D-003 — MPPI as production local controller
- Status: ACTIVE
- Source: ADR-006, P4-T02

## D-004 — Viewpoint policy ladder (B0/B1/P1/P2)
- Status: ACTIVE
- B0: fixed centre candidate; P1: max Q among visible; P2: P1 + confidence<0.80
  triggers next-best Q, max 3 attempts, blacklist
- Impact: p1_selector/p2_selector share candidate geometry (d=0.8, N=7, arc 120deg)

## D-005 — PID baseline + linear MPC parity contract (P7)
- Status: ACTIVE
- Decision: PID and linear MPC share identical bounds (v ±0.5 m/s, w ±1.5 rad/s,
  a ±0.3 m/s2, alpha ±1.0 rad/s2), dt=0.05 s, convergence (pos<0.02 m,
  yaw<0.03 rad, 10 consecutive steps) for a fair E5 paired benchmark
- Source: docs/10 §Fair experiment
- Impact: PIDGains and MPCParams dataclasses carry the same constants;
  changing one must change both

## D-006 — MPC formulation: heading-linearized kinematic model + OSQP
- Status: ACTIVE
- Decision: state [x,y,theta,v], input [a,omega]; linearize cos/sin(theta)
  around current heading; N=15 horizon; P regularized 1e-6 for PSD;
  warm-start OSQP; ImportError -> zero command (fail-safe)
- Impact: mpc_controller.py; Windows returns zero commands so MPC benchmark
  trials fail without osqp

## D-007 — Mission state machine separation for testability
- Status: ACTIVE
- Decision: pure MissionStateMachine (no ROS) + MissionExecutor node wrapper;
  E_TICK event drives S_SELECT_ASSET advancement from the node's _tick timer
- Impact: mission tests run on Windows without rclpy

## D-008 — Benchmark artifacts location
- Status: ACTIVE
- Decision: experiment outputs (JSON/PNG) live under results/, never repo root
- Impact: run_precision_benchmark.py / plot_precision_results.py default paths

## D-009 — Handoff radius contract
- Status: ACTIVE
- Decision: handoff triggers when distance to selected viewpoint <=
  approach_radius_multiplier (2.0) x desired_distance_m (0.8) = 1.6 m AND
  robot nearly stopped (|v|<0.05) AND PrecisionApproach server available
- Source: docs/06, P7-T01

## D-010 — Nav retry exhaustion consumes a viewpoint attempt
- Status: ACTIVE
- Decision: when MAX_NAV_RETRIES is exhausted for a viewpoint, the state
  machine resets nav_retries, increments viewpoint_attempts, and goes to
  S_SELECT_VIEWPOINT (attempts left) or S_SELECT_ASSET (none left). This
  guarantees the SELECT_VIEWPOINT<->NAVIGATE cycle is bounded by
  MAX_VIEWPOINT_ATTEMPTS, satisfying docs/11 "No infinite loops".
- Source: audit post-condition + verify C2 FAIL, P8-T01 (commit dc8cb7b)
- Impact: mission_executor.py S_NAVIGATE branch; test_nav_exhaustion_no_infinite_loop

