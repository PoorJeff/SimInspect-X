#!/usr/bin/env python3
"""E5 precision control benchmark: PID vs MPC paired comparison.

Runs independently (no ROS) — simulates differential-drive kinematics
with both controllers on identical initial conditions. Records all
metrics per docs/13.

Usage:  python run_precision_benchmark.py [--output results.json]
"""
import json, math, os, sys, time, yaml
import numpy as np
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Tuple

# Add PID/MPC modules to path
_src = os.path.join(os.path.dirname(__file__), "..", "..",
                    "siminspect_precision_control", "siminspect_precision_control")
sys.path.insert(0, _src)
from pid_controller import PIDController, PIDGains
from mpc_controller import MPCController, MPCParams


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class TrialResult:
    method: str
    condition: str
    seed: int
    target: Dict
    success: bool
    final_position_error: float
    final_yaw_error: float
    settling_time_s: float
    effort_abs: float
    effort_sq: float
    constraint_violations: int
    steps: int
    elapsed_s: float
    trajectory: List[Tuple[float, float, float]] = field(default_factory=list)
    solver_times_ms: List[float] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Simulation engine
# ---------------------------------------------------------------------------

def simulate_robot(target, controller, dt, max_steps, noise=None, slip=0.0,
                   logger=None):
    """Simulate one trial. Returns TrialResult."""
    tx, ty, tyaw = target["x"], target["y"], target["yaw"]

    # Initial state: always start at origin (fair comparison)
    x, y, yaw = 0.0, 0.0, 0.0

    # Apply initial yaw offset if specified in noise config
    if noise and "initial_yaw_offset_deg" in noise:
        yaw += math.radians(noise["initial_yaw_offset_deg"])

    traj = [(x, y, yaw)]
    v_history = []
    w_history = []
    solver_ms = []
    violations = 0
    settled = False
    settle_time = 0.0
    converged = False

    for step in range(max_steps):
        # Measurement noise
        mx, my, myaw = x, y, yaw
        if noise:
            mx += np.random.normal(0, noise.get("pos_noise_std", 0.0))
            my += np.random.normal(0, noise.get("pos_noise_std", 0.0))
            myaw += np.random.normal(0, noise.get("yaw_noise_std", 0.0))

        # Controller update
        t0 = time.perf_counter()
        v_cmd, w_cmd, pos_err, yaw_err, step_converged = controller.update(
            (mx, my, myaw), dt
        )
        t1 = time.perf_counter()
        solver_ms.append((t1 - t0) * 1000.0)

        if step_converged:
            converged = True

        # Wheel slip: velocity partially lost
        v_actual = v_cmd * (1.0 - slip)
        w_actual = w_cmd

        # Kinematic update
        x += v_actual * math.cos(yaw) * dt
        y += v_actual * math.sin(yaw) * dt
        yaw += w_actual * dt
        yaw = math.atan2(math.sin(yaw), math.cos(yaw))

        traj.append((x, y, yaw))
        v_history.append(v_actual)
        w_history.append(w_actual)

        # Constraint violations
        if abs(v_actual) > 0.5 + 1e-6 or abs(w_actual) > 1.5 + 1e-6:
            violations += 1

        # Settling time (pos < 0.05m AND |yaw_err| < 5 deg for 1s window)
        yaw_err_deg = abs(math.degrees(yaw_err))
        if not settled:
            if pos_err < 0.05 and yaw_err_deg < 5.0:
                settle_time += dt
                if settle_time >= 1.0:
                    settled = True
            else:
                settle_time = 0.0

        if converged:
            break

    # Final errors (from ground-truth pose)
    final_pos_err = math.hypot(tx - x, ty - y)
    yaw_err_final = tyaw - yaw
    yaw_err_final = math.atan2(math.sin(yaw_err_final), math.cos(yaw_err_final))

    # Control effort
    effort_abs = sum(abs(v) * dt + abs(w) * dt for v, w in zip(v_history, w_history))
    effort_sq = sum(v*v*dt + w*w*dt for v, w in zip(v_history, w_history))

    elapsed = (step + 1) * dt
    actual_settle = settle_time if settled else elapsed

    return TrialResult(
        method=type(controller).__name__.replace("Controller", "").lower(),
        condition="",  # filled by caller
        seed=0,        # filled by caller
        target=target,
        success=converged,
        final_position_error=final_pos_err,
        final_yaw_error=abs(yaw_err_final),
        settling_time_s=actual_settle,
        effort_abs=effort_abs,
        effort_sq=effort_sq,
        constraint_violations=violations,
        steps=step + 1,
        elapsed_s=elapsed,
        trajectory=traj,
        solver_times_ms=solver_ms,
    )


# ---------------------------------------------------------------------------
# Factory helpers
# ---------------------------------------------------------------------------

def make_controller(method, target, **kwargs):
    t = (target["x"], target["y"], target["yaw"])
    if method == "pid":
        return PIDController(t, gains=PIDGains(**kwargs))
    elif method == "mpc":
        return MPCController(t, params=MPCParams(**kwargs))
    else:
        raise ValueError(f"Unknown method: {method}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", default=None)
    ap.add_argument("--seeds", type=int, nargs="*", default=None)
    args = ap.parse_args()

    cfg_path = os.path.join(os.path.dirname(__file__), "..", "config",
                            "precision_benchmark.yaml")
    with open(cfg_path) as f:
        cfg = yaml.safe_load(f)

    dt = cfg["dt"]
    max_steps = cfg["max_steps"]
    methods = cfg["methods"]
    seeds = args.seeds if args.seeds else cfg["seeds"]
    conditions = cfg["conditions"]
    targets = cfg["targets"]

    all_results: List[TrialResult] = []

    for cond in conditions:
        noise = {k: v for k, v in cond.items()
                 if k not in ("id", "target_distance")}
        slip = noise.pop("slip_ratio", 0.0)
        target = targets[0]  # primary target
        if "target_distance" in cond:
            # Override target distance for saturation test
            target = {"x": cond["target_distance"], "y": 0.0, "yaw": 0.0}

        for seed in seeds:
            np.random.seed(seed)

            for method in methods:
                ctrl = make_controller(method, target)
                result = simulate_robot(target, ctrl, dt, max_steps,
                                        noise=noise, slip=slip)
                result.method = method
                result.condition = cond["id"]
                result.seed = seed
                all_results.append(result)

                tag = f"{cond['id']:25s} {method:4s} seed={seed:2d}"
                status = "OK" if result.success else "FAIL"
                print(f"  {tag}  {status}  "
                      f"pos={result.final_position_error:.3f}m  "
                      f"yaw={result.final_yaw_error:.3f}rad  "
                      f"settle={result.settling_time_s:.1f}s  "
                      f"effort={result.effort_abs:.2f}  "
                      f"steps={result.steps}")

    # Aggregate summary
    summary = _aggregate(all_results, methods, conditions, seeds)

    output = {
        "experiment": cfg["experiment"],
        "dt": dt,
        "max_steps": max_steps,
        "num_seeds": len(seeds),
        "methods": methods,
        "num_trials": len(all_results),
        "summary": summary,
        "trials": [asdict(r) for r in all_results],
    }

    out_path = args.output or os.path.join("results", "precision_results.json")
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\nResults written to {out_path} ({len(all_results)} trials)")


def _aggregate(results, methods, conditions, seeds):
    """Compute per-method per-condition summary statistics."""
    summary = {}
    for cond in conditions:
        cid = cond["id"]
        summary[cid] = {}
        for method in methods:
            subset = [r for r in results
                      if r.condition == cid and r.method == method]
            if not subset:
                continue
            n = len(subset)
            succ = sum(1 for r in subset if r.success)
            summary[cid][method] = {
                "success_rate": succ / n,
                "mean_final_pos_err": np.mean([r.final_position_error for r in subset]),
                "mean_final_yaw_err": np.mean([r.final_yaw_error for r in subset]),
                "mean_settling_s": np.mean([r.settling_time_s for r in subset]),
                "mean_effort_abs": np.mean([r.effort_abs for r in subset]),
                "mean_effort_sq": np.mean([r.effort_sq for r in subset]),
                "mean_violations": np.mean([r.constraint_violations for r in subset]),
                "mean_steps": np.mean([r.steps for r in subset]),
            }
            if method == "mpc":
                all_solver = [t for r in subset for t in r.solver_times_ms]
                if all_solver:
                    summary[cid][method]["mean_solver_ms"] = np.mean(all_solver)
                    summary[cid][method]["max_solver_ms"] = np.max(all_solver)
    return summary


if __name__ == "__main__":
    main()