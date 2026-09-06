#!/usr/bin/env python3
"""Batch seed sweep over the experiment matrix (P9-T02).

Iterates scenario -> seed -> method (paired seeds per docs/12) and runs each
trial serially via experiment_runner.run_trial.
"""
import argparse
import os
import sys
import time

try:
    from siminspect_benchmark.experiment_core import (
        SEED_POOLS, seeds_from_spec, load_matrix)
except ImportError:
    from experiment_core import SEED_POOLS, seeds_from_spec, load_matrix
from experiment_runner import run_trial


def main():
    ap = argparse.ArgumentParser(description="Seed sweep (P9-T02)")
    ap.add_argument("--experiment", required=True, help="E1..E6")
    ap.add_argument("--methods", nargs="*", default=None)
    ap.add_argument("--scenarios", nargs="*", default=None)
    ap.add_argument("--pool", default=None, choices=["final", "dev"])
    ap.add_argument("--seeds", type=int, nargs="*", default=None)
    ap.add_argument("--matrix", default=None)
    ap.add_argument("--root", default="experiments/raw")
    ap.add_argument("--commit", default=None)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--no-inject", action="store_true")
    args = ap.parse_args()

    matrix_path = args.matrix or os.path.join(
        os.path.dirname(__file__), "..", "config", "experiment_matrix.yaml")
    matrix = load_matrix(matrix_path)
    exp = next((e for e in matrix["experiments"]
                if e["id"] == args.experiment), None)
    if exp is None:
        sys.exit(f"unknown experiment {args.experiment}")

    methods = args.methods or exp["methods"]
    scenarios = args.scenarios or exp["scenarios"]

    if args.seeds:
        seeds = list(args.seeds)
    elif args.pool:
        pool_spec = dict(exp["seeds"])
        pool_spec["pool"] = args.pool
        lo, hi = SEED_POOLS[args.pool]
        pool_spec["count"] = min(pool_spec.get("count", hi - lo + 1),
                                 hi - lo + 1)
        seeds = seeds_from_spec(pool_spec)
    else:
        seeds = seeds_from_spec(exp["seeds"])

    total = len(scenarios) * len(seeds) * len(methods)
    print(f"Sweep: {exp['id']} methods={methods} scenarios={scenarios} "
          f"seeds={seeds[0] if seeds else '-'}..{seeds[-1] if seeds else '-'}"
          f" ({total} trials)")
    if total == 0:
        sys.exit("nothing to run")

    completed = 0
    failed = 0
    t0 = time.time()
    for scenario in scenarios:
        for seed in seeds:
            for method in methods:
                try:
                    run_trial(exp, method, scenario, seed, args.root,
                              commit=args.commit, dry_run=args.dry_run,
                              inject=not args.no_inject)
                    completed += 1
                except ValueError as exc:
                    failed += 1
                    print(f"ERROR {exp['id']}/{method}/{scenario}/{seed}: {exc}")

    print(f"Sweep done: {completed} ok, {failed} failed, "
          f"{round(time.time() - t0, 1)}s")


if __name__ == "__main__":
    main()