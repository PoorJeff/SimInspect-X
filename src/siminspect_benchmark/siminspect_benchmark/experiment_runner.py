#!/usr/bin/env python3
"""Single-trial experiment runner (P9-T02).

Given experiment/method/scenario/seed, runs one benchmark trial and writes a
docs/16 trial record under experiments/raw/.

Honest scope: the runner orchestrates subprocesses (fault injector + harness).
Real ROS execution requires the Ubuntu host (OI-005); --dry-run works anywhere.
"""
import argparse
import json
import os
import subprocess
import sys
import time

try:
    from siminspect_benchmark.experiment_core import (
        validate_seed, harness_for, trial_output_path, git_commit_short,
        load_matrix, build_trial_record,
    )
except ImportError:
    from experiment_core import (
        validate_seed, harness_for, trial_output_path, git_commit_short,
        load_matrix, build_trial_record,
    )


def run_trial(exp, method, scenario, seed, root, commit=None,
              dry_run=False, inject=True):
    """Run one trial; returns (record, output_path)."""
    if not validate_seed(seed):
        raise ValueError(f"seed {seed} outside pools")
    if scenario not in exp["scenarios"]:
        raise ValueError(f"scenario {scenario} not in {exp['id']} matrix")
    if method not in exp["methods"]:
        raise ValueError(f"method {method} not in {exp['id']} matrix")
    harness = harness_for(exp["id"], method)
    if harness is None:
        raise ValueError(
            f"no harness for {exp['id']}/{method} (honest mapping; "
            f"deferred to P9-T03/T04)")

    commit = commit or git_commit_short()
    out_path = trial_output_path(root, exp, commit, method, scenario, seed)

    if dry_run:
        record = build_trial_record(
            exp, method, scenario, seed, commit,
            result="dry_run", failure_reason="",
            metrics={"planned": True})
        print(f"[dry-run] {exp['id']}/{method}/{scenario}/seed={seed} "
              f"-> {out_path}")
        return record, out_path

    start = time.time()
    injector = None
    if inject:
        injector = subprocess.Popen([
            "ros2", "run", "siminspect_benchmark", "fault_injector",
            "--ros-args", "-p", f"scenario:={scenario}",
            "-p", f"seed:={seed}"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    env = dict(os.environ)
    env["SIMINSPECT_SEED"] = str(seed)
    # NOTE: harnesses read SIMINSPECT_SEED as the seed contract; scripts that
    # ignore it (e.g. E5's internal YAML seeds) are T03 integration debt.
    proc = subprocess.run(
        ["python3", harness], capture_output=True, text=True,
        timeout=1800, env=env)
    elapsed = round(time.time() - start, 2)
    if injector is not None:
        injector.terminate()

    result = "completed" if proc.returncode == 0 else "failed"
    failure_reason = "" if proc.returncode == 0 else proc.stderr.strip()[-500:]
    record = build_trial_record(
        exp, method, scenario, seed, commit, result=result,
        failure_reason=failure_reason,
        metrics={"exit_code": proc.returncode, "elapsed_s": elapsed,
                 "stdout_tail": proc.stdout.strip()[-500:]})
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(record, f, indent=2)
    print(f"[{result}] {out_path} (exit={proc.returncode}, {elapsed}s)")
    return record, out_path


def main():
    ap = argparse.ArgumentParser(description="Run one benchmark trial (P9-T02)")
    ap.add_argument("--experiment", required=True, help="E1..E6")
    ap.add_argument("--method", required=True)
    ap.add_argument("--scenario", required=True, help="F00..F11")
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--matrix", default=None,
                    help="path to experiment_matrix.yaml")
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
    run_trial(exp, args.method, args.scenario, args.seed, args.root,
              commit=args.commit, dry_run=args.dry_run,
              inject=not args.no_inject)


if __name__ == "__main__":
    main()