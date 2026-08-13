#!/usr/bin/env python3
"""Ablation executor (P9-T03).

Reads ablations.yaml and runs each ablation's trials through the T02
experiment runner, recording overrides in planner_params and passing them
to harnesses via environment variables.

Note: A1-A4 weight/reinspect overrides reach the selector via env
(SIMINSPECT_WEIGHTS / SIMINSPECT_REINSPECT) but the E4 benchmark
harnesses are still skeletons that do not yet consume them; numeric
ablation results require the E4 harness integration (Ubuntu, OI-005).

Honest scope: A5 (EKF on/off) is launch/config-level — the runner prints
the required robot_localization instructions and does NOT fake execution.
Real ROS runs require the Ubuntu host (OI-005); --dry-run works anywhere.
"""
import argparse
import json
import os

try:
    from siminspect_benchmark.ablation_core import (
        load_ablations, overrides_to_env, ablation_methods)
    from siminspect_benchmark.experiment_core import (
        load_matrix, seeds_from_spec)
except ImportError:
    from ablation_core import (
        load_ablations, overrides_to_env, ablation_methods)
    from experiment_core import (
        load_matrix, seeds_from_spec)
from experiment_runner import run_trial  # PROGRAMS-installed sibling


def main():
    ap = argparse.ArgumentParser(description="Run ablations (P9-T03)")
    ap.add_argument("--ablation", required=True,
                    help="A1..A6 or 'all'")
    ap.add_argument("--ablations", default=None,
                    help="path to ablations.yaml")
    ap.add_argument("--matrix", default=None,
                    help="path to experiment_matrix.yaml")
    ap.add_argument("--root", default="experiments/raw")
    ap.add_argument("--commit", default=None)
    ap.add_argument("--pool", default=None, choices=["final", "dev"])
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--no-inject", action="store_true")
    args = ap.parse_args()

    base = os.path.dirname(__file__)
    abl_path = args.ablations or os.path.join(
        base, "..", "config", "ablations.yaml")
    matrix_path = args.matrix or os.path.join(
        base, "..", "config", "experiment_matrix.yaml")
    abls = load_ablations(abl_path)
    matrix = load_matrix(matrix_path)

    selected = (abls if args.ablation == "all"
                else [a for a in abls if a["id"] == args.ablation])
    if not selected:
        raise SystemExit(f"unknown ablation {args.ablation}")

    for ablation in selected:
        aid = ablation["id"]
        exp = next((e for e in matrix["experiments"]
                    if e["id"] == ablation["experiment"]), None)
        if exp is None:
            print(f"SKIP {aid}: experiment {ablation['experiment']} not in matrix")
            continue

        if aid == "A5":
            print(f"[A5] localization ablation is launch-level (no harness run):")
            print("     raw_odom: disable robot_localization EKF node in launch")
            print("     ekf:      enable robot_localization EKF node in launch")
            print("     scenario F01 (wheel_odom_noise) applies via fault_injector.")
            continue

        methods = ablation_methods(ablation)
        overrides = ablation.get("overrides") or {}
        base = ablation.get("baseline_method")
        env_extra = overrides_to_env(overrides)
        spec = dict(ablation["seeds"])
        if args.pool:
            spec["pool"] = args.pool
            lo, hi = (1, 20) if args.pool == "final" else (21, 30)
            spec["count"] = min(spec.get("count", hi - lo + 1), hi - lo + 1)
        seeds = seeds_from_spec(spec)

        print(f"Ablation {aid} ({ablation['name']}): "
              f"methods={methods} scenarios={ablation['scenarios']} "
              f"seeds={seeds[0]}..{seeds[-1]} overrides={json.dumps(overrides)}")
        for scenario in ablation["scenarios"]:
            for seed in seeds:
                for method in methods:
                    harness_method = None
                    if "methods" not in ablation and base != method:
                        harness_method = base
                    run_trial(
                        exp, method, scenario, seed, args.root,
                        commit=args.commit, dry_run=args.dry_run,
                        inject=not args.no_inject,
                        planner_params=overrides, extra_env=env_extra,
                        harness_method=harness_method)

    print("Ablations done.")


if __name__ == "__main__":
    main()