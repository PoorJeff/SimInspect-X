#!/usr/bin/env python3
"""Fault scenario definitions and pure helpers (P9-T01).

Pure Python, no ROS imports: unit-testable on any host (D-007 pattern).
The ROS node (fault_injector.py) imports this module.
"""
import random

import yaml

SCENARIO_IDS = (
    "F00", "F01", "F02", "F03", "F04", "F05",
    "F06", "F07", "F08", "F09", "F10", "F11",
)
MIXED_SCENARIOS = {"F11"}


def load_scenarios(path):
    """Load the scenario list from a fault_scenarios.yaml file."""
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict) or "scenarios" not in data:
        raise ValueError("fault scenarios file must contain a 'scenarios' list")
    return data["scenarios"]


def validate_scenario(sc):
    """Return a list of error strings for one scenario dict (empty = valid)."""
    errors = []
    sid = sc.get("id")
    if sid not in SCENARIO_IDS:
        errors.append(f"unknown or missing id: {sid!r}")
        return errors

    params = sc.get("params")
    if not isinstance(params, dict):
        errors.append(f"{sid}: params must be a dict")
        params = {}

    seed = sc.get("seed")
    if not isinstance(seed, int) or isinstance(seed, bool) or seed < 0:
        errors.append(f"{sid}: seed must be a non-negative int")

    if sid == "F00":
        if params:
            errors.append("F00 (nominal) must have empty params")
    else:
        dur = params.get("duration_s")
        if dur is None:
            errors.append(f"{sid}: params must include duration_s")
        elif not isinstance(dur, (int, float)) or dur < 0:
            errors.append(f"{sid}: duration_s must be a number >= 0")

    if sid in MIXED_SCENARIOS:
        if sc.get("primary_factor") != "mixed":
            errors.append(f"{sid}: primary_factor must be 'mixed'")
    elif sid != "F00":
        pf = sc.get("primary_factor")
        if pf in (None, "none", "mixed"):
            errors.append(f"{sid}: must have a single primary factor")
    return errors


def validate_all(scenarios):
    """Validate the whole list: complete, unique, in-order IDs + per-item."""
    errors = []
    ids = [sc.get("id") for sc in scenarios]
    if ids != list(SCENARIO_IDS):
        errors.append(
            f"scenario ids must be exactly {list(SCENARIO_IDS)} in order; got {ids}")
    for sc in scenarios:
        errors.extend(validate_scenario(sc))
    return errors


def resolve_seed(scenario, seed):
    """Return a copy of the scenario with the seed overridden."""
    out = dict(scenario)
    out["seed"] = seed
    return out


def deterministic_noise(seed, n, std):
    """n zero-mean Gaussian samples with std, reproducible from seed."""
    rng = random.Random(seed)
    return [rng.gauss(0.0, std) for _ in range(n)]