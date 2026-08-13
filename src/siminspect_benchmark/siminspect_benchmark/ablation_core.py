#!/usr/bin/env python3
"""Ablation config core (P9-T03).

Pure Python, no ROS imports: unit-testable on any host (D-007 pattern).
run_ablations.py (executable) imports this module.
"""
import json

import yaml

ABLATION_IDS = ("A1", "A2", "A3", "A4", "A5", "A6")

VALID_EXPERIMENTS = ("E1", "E2", "E3", "E4", "E5", "E6")

# Allowed override keys per ablation (docs/14 single-factor rule).
ALLOWED_OVERRIDE_KEYS = ("weights", "reinspect", "localization")

# Default weights mirror quality_scorer.DEFAULT_W.
DEFAULT_WEIGHTS = {"w_vis": 0.35, "w_d": 0.25, "w_theta": 0.25,
                   "w_s": 0.15, "w_t": 0.15}
WEIGHT_KEYS = tuple(DEFAULT_WEIGHTS.keys())


def load_ablations(path):
    """Load and validate ablations.yaml."""
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    errors = validate_ablations(data)
    if errors:
        raise ValueError("invalid ablations config: " + "; ".join(errors))
    return data["ablations"]


def validate_ablations(data):
    """Return a list of error strings (empty = valid)."""
    errors = []
    if not isinstance(data, dict) or "ablations" not in data:
        return ["ablations file must contain an 'ablations' list"]
    abls = data["ablations"]
    ids = [a.get("id") for a in abls]
    if ids != list(ABLATION_IDS):
        errors.append(f"ablation ids must be exactly {list(ABLATION_IDS)} "
                      f"in order; got {ids}")
    for a in abls:
        aid = a.get("id")
        if a.get("experiment") not in VALID_EXPERIMENTS:
            errors.append(f"{aid}: unknown experiment {a.get('experiment')!r}")
        overrides = a.get("overrides") or {}
        for key in overrides:
            if key not in ALLOWED_OVERRIDE_KEYS:
                errors.append(f"{aid}: unknown override key {key!r}")
        weights = overrides.get("weights", {})
        for wk, wv in weights.items():
            if wk not in WEIGHT_KEYS:
                errors.append(f"{aid}: unknown weight key {wk!r}")
            elif not (0.0 <= wv <= 1.0):
                errors.append(f"{aid}: weight {wk}={wv} outside [0,1]")
        if aid == "A6" and overrides:
            errors.append("A6 must not carry overrides (reference ablation)")
        if a.get("seeds", {}).get("pool") not in ("final", "dev"):
            errors.append(f"{aid}: seeds.pool must be final or dev")
    return errors


def apply_weights(overrides):
    """Full weight dict after applying an ablation's weight overrides.

    Does not mutate the base DEFAULT_WEIGHTS; returns a new dict.
    """
    weights = dict(DEFAULT_WEIGHTS)
    for key, value in (overrides or {}).get("weights", {}).items():
        weights[key] = value
    return weights


def weights_to_json(weights):
    """Serialize a weight dict to the JSON string form used by selectors."""
    return json.dumps(weights, sort_keys=True)


def overrides_to_env(overrides):
    """Map ablation overrides to environment variables for the harness.

    Returns a dict; empty dict when overrides is None.
    """
    overrides = overrides or {}
    env = {}
    if "weights" in overrides:
        env["SIMINSPECT_WEIGHTS"] = weights_to_json(
            apply_weights(overrides))
    if "reinspect" in overrides:
        env["SIMINSPECT_REINSPECT"] = (
            "true" if overrides["reinspect"] else "false")
    # "localization" (A5) is launch-level and intentionally has no env form.
    return env


def ablation_methods(ablation):
    """Method list an ablation runs: A1-A4 single suffixed method,
    A5/A6 explicit method lists."""
    if "methods" in ablation:
        return list(ablation["methods"])
    return [ablation["method"]]