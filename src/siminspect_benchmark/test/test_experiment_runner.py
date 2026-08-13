"""Pure-logic tests for the experiment runner core (P9-T02).

No ROS imports; imports experiment_core only.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "siminspect_benchmark"))

from experiment_core import (  # noqa: E402
    SEED_POOLS, format_seed, seeds_from_spec, validate_seed,
    experiment_key, trial_output_path, harness_for, load_matrix,
    build_trial_record, VALID_SCENARIOS,
)

YAML = os.path.join(os.path.dirname(__file__), "..", "config", "experiment_matrix.yaml")


def test_seed_pools():
    assert SEED_POOLS == {"final": (1, 20), "dev": (21, 30)}


def test_format_seed_zero_padded():
    assert format_seed(7) == "0007"
    assert format_seed(20) == "0020"


def test_seeds_from_spec_pools():
    assert seeds_from_spec({"pool": "final", "count": 3}) == [1, 2, 3]
    assert seeds_from_spec({"pool": "dev", "count": 5}) == [21, 22, 23, 24, 25]


def test_seeds_from_spec_rejects_bad_input():
    with pytest.raises(ValueError):
        seeds_from_spec({"pool": "nope", "count": 1})
    with pytest.raises(ValueError):
        seeds_from_spec({"pool": "final", "count": 0})
    with pytest.raises(ValueError):
        seeds_from_spec({"pool": "dev", "count": 11})


def test_validate_seed_boundaries():
    assert validate_seed(1) and validate_seed(20)
    assert validate_seed(21) and validate_seed(30)
    assert not validate_seed(0)
    assert not validate_seed(31)
    assert not validate_seed("x")


def test_matrix_loads_and_validates():
    data = load_matrix(YAML)
    assert [e["id"] for e in data["experiments"]] == ["E1", "E2", "E3", "E4", "E5", "E6"]


def test_experiment_key_matches_docs16():
    assert experiment_key({"id": "E4", "name": "viewpoint_policy"}) == "E4_viewpoint_policy"


def test_trial_path_matches_docs16():
    exp = {"id": "E4", "name": "viewpoint_policy"}
    p = trial_output_path(os.path.join("experiments", "raw"), exp,
                         "commit_abcdef", "P2", "F09", 7)
    assert p == os.path.join("experiments", "raw", "E4_viewpoint_policy",
                             "commit_abcdef", "P2", "F09", "seed_0007.json")


def test_harness_mapping_honest():
    assert harness_for("E4", "B0") == "run_b0_benchmark.py"
    assert harness_for("E4", "B1") is None
    assert harness_for("E4", "P1") == "run_p1_benchmark.py"
    assert harness_for("E4", "P2") == "run_p2_benchmark.py"
    assert harness_for("E5", "PID") == "run_precision_benchmark.py"
    assert harness_for("E3", "deterministic_reader") is None
    assert harness_for("E6", "mission") is None


def test_build_trial_record_has_all_docs16_fields():
    exp = {"id": "E4", "name": "viewpoint_policy", "world": "plant.sdf"}
    rec = build_trial_record(exp, "P2", "F09", 7, "commit_abcdef",
                             result="completed")
    for field in ("git_commit", "manifest", "method", "scenario", "seed",
                  "world", "mission", "controller", "planner_params",
                  "result", "failure_reason", "metrics"):
        assert field in rec, field
    assert rec["seed"] == 7
    assert rec["scenario"] == "F09"


def test_valid_scenarios_are_f00_to_f11():
    assert VALID_SCENARIOS == tuple(f"F{i:02d}" for i in range(12))