"""Pure-logic tests for the fault scenario set (P9-T01).

No ROS imports; tests import the pure fault_scenarios module only.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "siminspect_benchmark"))

from fault_scenarios import (  # noqa: E402
    SCENARIO_IDS, MIXED_SCENARIOS, load_scenarios, validate_scenario,
    validate_all, resolve_seed, deterministic_noise,
)

YAML = os.path.join(os.path.dirname(__file__), "..", "config", "fault_scenarios.yaml")


def _load():
    return load_scenarios(YAML)


def test_yaml_loads_12_scenarios_in_order():
    scs = _load()
    ids = [sc["id"] for sc in scs]
    assert ids == list(SCENARIO_IDS)
    assert len(ids) == 12


def test_all_scenarios_valid():
    assert validate_all(_load()) == []


def test_default_seeds_are_dev_pool():
    for sc in _load():
        assert 21 <= sc["seed"] <= 30, f"{sc['id']} seed {sc['seed']} outside dev pool"


def test_reject_unknown_id():
    errs = validate_scenario({"id": "F99", "params": {}, "seed": 1})
    assert any("unknown" in e for e in errs)


def test_reject_params_not_dict():
    errs = validate_scenario({"id": "F01", "params": [], "seed": 1})
    assert any("params must be a dict" in e for e in errs)


def test_reject_negative_seed():
    errs = validate_scenario({"id": "F01", "params": {"duration_s": 1}, "seed": -1})
    assert any("seed" in e for e in errs)


def test_reject_missing_duration():
    errs = validate_scenario({"id": "F02", "params": {"slip_factor": 0.9}, "seed": 1})
    assert any("duration_s" in e for e in errs)


def test_f00_must_have_empty_params():
    errs = validate_scenario({"id": "F00", "params": {"duration_s": 1}, "seed": 1})
    assert any("empty params" in e for e in errs)


def test_only_f11_is_mixed():
    assert MIXED_SCENARIOS == {"F11"}
    for sc in _load():
        if sc["id"] in MIXED_SCENARIOS:
            assert sc["primary_factor"] == "mixed"
        elif sc["id"] != "F00":
            assert sc["primary_factor"] not in (None, "none", "mixed")


def test_deterministic_noise_same_seed():
    assert deterministic_noise(7, 5, 1.0) == deterministic_noise(7, 5, 1.0)


def test_deterministic_noise_different_seed():
    assert deterministic_noise(7, 5, 1.0) != deterministic_noise(8, 5, 1.0)


def test_resolve_seed_keeps_other_fields():
    sc = _load()[1]  # F01
    out = resolve_seed(sc, 123)
    assert out["seed"] == 123
    assert out["params"] == sc["params"]
    assert out["id"] == sc["id"]
    assert sc["seed"] == 22  # original untouched (copy semantics)