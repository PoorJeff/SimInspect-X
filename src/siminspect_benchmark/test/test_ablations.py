"""Pure-logic tests for the ablation config core (P9-T03).

No ROS imports; imports ablation_core only.
"""
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "siminspect_benchmark"))

from ablation_core import (  # noqa: E402
    ABLATION_IDS, DEFAULT_WEIGHTS, load_ablations, validate_ablations,
    apply_weights, weights_to_json, overrides_to_env, ablation_methods,
)

YAML = os.path.join(os.path.dirname(__file__), "..", "config", "ablations.yaml")


def test_ablations_load_six_in_order():
    abls = load_ablations(YAML)
    assert [a["id"] for a in abls] == list(ABLATION_IDS)


def test_a1_a3_single_weight_zeroed():
    abls = load_ablations(YAML)
    by_id = {a["id"]: a for a in abls}
    assert by_id["A1"]["overrides"]["weights"] == {"w_vis": 0.0}
    assert by_id["A2"]["overrides"]["weights"] == {"w_theta": 0.0}
    assert by_id["A3"]["overrides"]["weights"] == {"w_t": 0.0}
    assert by_id["A4"]["overrides"] == {"reinspect": False}


def test_a6_has_no_overrides_and_covers_e5():
    abls = load_ablations(YAML)
    a6 = next(a for a in abls if a["id"] == "A6")
    assert a6["experiment"] == "E5"
    assert a6["covered_by"] == "E5"
    assert not a6.get("overrides")


def test_validate_rejects_unknown_id_and_bad_keys():
    errs = validate_ablations({"ablations": [
        {"id": "A9", "experiment": "E4", "seeds": {"pool": "final"}}]})
    assert any("ablation ids" in e for e in errs)
    errs = validate_ablations({"ablations": [
        {"id": "A1", "experiment": "E4", "overrides": {"bogus": 1},
         "seeds": {"pool": "final"}}]})
    assert any("unknown override key" in e for e in errs)


def test_validate_rejects_weight_out_of_range():
    errs = validate_ablations({"ablations": [
        {"id": "A1", "experiment": "E4",
         "overrides": {"weights": {"w_vis": 1.5}},
         "seeds": {"pool": "final"}}]})
    assert any("outside [0,1]" in e for e in errs)


def test_validate_rejects_a6_with_overrides():
    errs = validate_ablations({"ablations": [
        {"id": "A6", "experiment": "E5", "overrides": {"reinspect": False},
         "seeds": {"pool": "dev"}}]})
    assert any("A6 must not carry overrides" in e for e in errs)


def test_apply_weights_does_not_mutate_base():
    base_before = dict(DEFAULT_WEIGHTS)
    w = apply_weights({"weights": {"w_vis": 0.0}})
    assert w["w_vis"] == 0.0
    assert w["w_theta"] == DEFAULT_WEIGHTS["w_theta"]
    assert DEFAULT_WEIGHTS == base_before
    assert DEFAULT_WEIGHTS["w_vis"] == 0.35


def test_weights_to_json_roundtrip():
    w = apply_weights({"weights": {"w_t": 0.0}})
    parsed = json.loads(weights_to_json(w))
    assert parsed == w


def test_overrides_to_env():
    env = overrides_to_env({"weights": {"w_vis": 0.0}, "reinspect": False})
    assert env["SIMINSPECT_REINSPECT"] == "false"
    assert json.loads(env["SIMINSPECT_WEIGHTS"])["w_vis"] == 0.0
    assert overrides_to_env({"localization": "off"}) == {}
    assert overrides_to_env(None) == {}


def test_ablation_methods():
    abls = load_ablations(YAML)
    by_id = {a["id"]: a for a in abls}
    assert ablation_methods(by_id["A1"]) == ["P2_A1"]
    assert ablation_methods(by_id["A5"]) == ["raw_odom", "ekf"]
    assert ablation_methods(by_id["A6"]) == ["PID", "MPC"]