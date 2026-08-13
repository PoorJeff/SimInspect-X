#!/usr/bin/env python3
"""Experiment runner pure core (P9-T02).

Pure Python, no ROS imports: unit-testable on any host (D-007 pattern).
The executable scripts (experiment_runner.py, run_seed_sweep.py) import it.
"""
import os
import subprocess

import yaml

SEED_POOLS = {"final": (1, 20), "dev": (21, 30)}

VALID_SCENARIOS = tuple(f"F{i:02d}" for i in range(12))  # F00..F11

# Experiment/method -> default harness script (same-package executables).
# A None value means no standalone harness exists yet (honest mapping).
HARNESS_MAP = {
    "E1": {"raw_odom": "localisation_eval.py", "ekf": "localisation_eval.py"},
    "E2": {"nav2": "nav_benchmark.py"},
    "E4": {
        "B0": "run_b0_benchmark.py",
        "B1": None,
        "P1": "run_p1_benchmark.py",
        "P2": "run_p2_benchmark.py",
    },
    "E5": {"PID": "run_precision_benchmark.py",
           "MPC": "run_precision_benchmark.py"},
    # E3 (gauge reader) and E6 (end-to-end mission) have no harness yet.
}


def format_seed(seed):
    """Zero-padded 4-digit seed label, e.g. 7 -> '0007'."""
    return f"{int(seed):04d}"


def seeds_from_spec(spec):
    """Expand a {pool, count} seed spec into a deterministic list."""
    pool = spec.get("pool")
    if pool not in SEED_POOLS:
        raise ValueError(f"unknown seed pool: {pool!r}")
    start, end = SEED_POOLS[pool]
    count = int(spec.get("count", 0))
    if count <= 0 or count > end - start + 1:
        raise ValueError(f"count {count} out of range for pool {pool}")
    return list(range(start, start + count))


def validate_seed(seed):
    """Seed must be an int inside one of the pools."""
    try:
        seed = int(seed)
    except (TypeError, ValueError):
        return False
    return any(a <= seed <= b for a, b in SEED_POOLS.values())


def experiment_key(exp):
    """Directory key 'E4_viewpoint_policy' matching docs/16."""
    return f"{exp['id']}_{exp['name']}"


def trial_output_path(root, exp, commit, method, scenario, seed):
    """docs/16 path: E{id}_{name}/{commit}/{method}/{scenario}/seed_XXXX.json"""
    return os.path.join(
        root, experiment_key(exp), commit, method, scenario,
        f"seed_{format_seed(seed)}.json",
    )


def git_commit_short():
    """Short git commit of the repository (docs/16 trial field)."""
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, timeout=10,
        )
        return out.stdout.strip() or "unknown"
    except Exception:
        return "unknown"


def load_matrix(path):
    """Load and validate experiment_matrix.yaml."""
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    errors = validate_matrix(data)
    if errors:
        raise ValueError("invalid experiment matrix: " + "; ".join(errors))
    return data


def validate_matrix(data):
    """Return a list of error strings (empty = valid)."""
    errors = []
    if not isinstance(data, dict) or "experiments" not in data:
        return ["matrix must contain an 'experiments' list"]
    exps = data["experiments"]
    ids = [e.get("id") for e in exps]
    if ids != [f"E{i}" for i in range(1, 7)]:
        errors.append(f"experiment ids must be E1..E6 in order; got {ids}")
    for e in exps:
        eid = e.get("id")
        for sc in e.get("scenarios", []):
            if sc not in VALID_SCENARIOS:
                errors.append(f"{eid}: unknown scenario {sc!r}")
        for m in e.get("methods", []):
            if eid in HARNESS_MAP and m not in HARNESS_MAP[eid]:
                errors.append(f"{eid}: unknown method {m!r}")
        try:
            seeds = seeds_from_spec(e.get("seeds", {}))
        except ValueError as exc:
            errors.append(f"{eid}: {exc}")
            seeds = []
        for s in seeds:
            if not validate_seed(s):
                errors.append(f"{eid}: seed {s} outside pools")
        # Cross-check declared harness fields against the code mapping.
        declared = e.get("harness")
        harnesses = e.get("harnesses") or {}
        for m in e.get("methods", []):
            expected = harness_for(eid, m)
            got = harnesses.get(m, declared) if harnesses else declared
            if expected is not None and got is None:
                errors.append(
                    f"{eid}/{m}: matrix declares no harness but "
                    f"{expected} exists")
            elif got is not None and got != expected:
                errors.append(
                    f"{eid}/{m}: harness {got!r} != expected {expected!r}")
    return errors


def harness_for(exp_id, method):
    """Harness script for an experiment/method pair, or None if missing."""
    return HARNESS_MAP.get(exp_id, {}).get(method)


def build_trial_record(exp, method, scenario, seed, commit, result,
                       failure_reason="", metrics=None, world=None,
                       manifest=None, mission=None, controller=None,
                       planner_params=None):
    """Build a docs/16 trial record with all required fields."""
    return {
        "git_commit": commit,
        "manifest": manifest or "rosdep/manifest.json",
        "method": method,
        "scenario": scenario,
        "seed": int(seed),
        "world": world or exp.get("world", "plant.sdf"),
        "mission": mission or None,
        "controller": controller or None,
        "planner_params": planner_params or {},
        "result": result,
        "failure_reason": failure_reason,
        "metrics": metrics if metrics is not None else {},
    }