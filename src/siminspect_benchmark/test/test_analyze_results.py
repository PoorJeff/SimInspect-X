"""Pure-logic tests for the consolidated analysis core (P9-T04).

No ROS imports; uses synthetic data. Includes one headless plot smoke test.
"""
import json
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "siminspect_benchmark"))

from analysis_core import (  # noqa: E402
    ALPHA, group_trials, success_rate, mae_rmse_median,
    within_tolerance_rate, mean_of, extra_distance, paired_test,
    paired_values, build_summary,
)
from generate_plots import make_plots  # noqa: E402


def _rec(exp, method, scenario, seed, result="completed", metrics=None):
    return {"experiment": exp, "method": method, "scenario": scenario,
            "seed": seed, "result": result, "metrics": metrics or {}}


def test_group_trials():
    recs = [_rec("E4", "B0", "F00", 1), _rec("E4", "B0", "F00", 2),
            _rec("E4", "P2", "F00", 1), _rec("E5", "PID", "F00", 1)]
    g = group_trials(recs)
    assert g["E4"]["B0"]["F00"] == recs[:2]
    assert g["E4"]["P2"]["F00"] == [recs[2]]
    assert g["E5"]["PID"]["F00"] == [recs[3]]


def test_success_rate():
    recs = [_rec("E4", "P2", "F00", 1, result="completed"),
            _rec("E4", "P2", "F00", 2, result="failed")]
    assert success_rate(recs) == 0.5
    assert success_rate([]) is None


def test_mae_rmse_median_exact():
    out = mae_rmse_median([0.0, 2.0, 4.0])
    assert out["mae"] == pytest.approx(2.0)
    assert out["rmse"] == pytest.approx(np.sqrt((0 + 4 + 16) / 3))
    assert out["median"] == pytest.approx(2.0)


def test_within_tolerance_rate():
    assert within_tolerance_rate([1.0, 2.0, 20.0], 100.0) == pytest.approx(2 / 3)
    assert within_tolerance_rate([], 100.0) is None


def test_mean_of_missing_returns_none():
    recs = [_rec("E4", "P2", "F00", 1, metrics={"path_length_m": 5.0}),
            _rec("E4", "P2", "F00", 2)]
    assert mean_of(recs, "path_length_m") is None


def test_extra_distance():
    base = [_rec("E4", "B0", "F00", s, metrics={"path_length_m": 10.0})
            for s in (1, 2)]
    meth = [_rec("E4", "P2", "F00", s, metrics={"path_length_m": 13.0})
            for s in (1, 2)]
    assert extra_distance(base, meth) == pytest.approx(3.0)
    assert extra_distance(base, [_rec("E4", "P2", "F00", 1)]) is None


def test_paired_test_significant():
    a = [1.0, 1.1, 0.9, 1.0, 1.05]
    b = [2.0, 2.1, 1.9, 2.0, 2.05]
    out = paired_test(a, b)
    assert out["n"] == 5
    assert out["significant"] is True
    assert out["p_value"] < ALPHA


def test_paired_test_not_significant():
    a = [1.0, 1.1, 0.9, 1.0, 1.05]
    b = [1.0, 1.05, 0.95, 1.0, 1.02]
    out = paired_test(a, b)
    assert out["significant"] is False


def test_paired_test_identical_returns_none():
    out = paired_test([1.0] * 5, [1.0] * 5)
    assert out["significant"] is None
    assert out["p_value"] is None


def test_paired_test_insufficient():
    out = paired_test([1.0], [2.0])
    assert out["insufficient_pairs"] is True
    assert out["significant"] is None


def test_build_summary_structure_and_hypotheses():
    recs = []
    for seed in range(1, 6):
        recs.append(_rec("E4", "B0", "F00", seed,
                         metrics={"valid_read_rate": 0.4 + seed * 0.05,
                                  "path_length_m": 10.0}))
        recs.append(_rec("E4", "P2", "F00", seed,
                         metrics={"valid_read_rate": 0.7 + seed * 0.02,
                                  "path_length_m": 13.0}))
        recs.append(_rec("E5", "PID", "F00", seed,
                         metrics={"final_position_error": 0.04 + seed * 0.005}))
        recs.append(_rec("E5", "MPC", "F00", seed,
                         metrics={"final_position_error": 0.03 + seed * 0.004}))
    summary = build_summary(group_trials(recs))
    assert summary["experiments"]["E4"]["methods"]["P2"]["n"] == 5
    assert summary["e4_tradeoff"]["P2"]["delta_distance"] == pytest.approx(3.0)
    h1 = summary["hypothesis_tests"]["H1_B0_vs_P2"]
    assert h1["n"] == 5
    assert h1["significant"] is True
    h4 = summary["hypothesis_tests"]["H4_PID_vs_MPC_pos"]
    assert h4["n"] == 5
    assert summary["hypothesis_tests"]["H1_B0_vs_P2"]["alpha"] == 0.05
    assert h4["alpha"] == 0.0125


def test_summary_json_roundtrip():
    recs = [_rec("E4", "B0", "F00", 1, metrics={"path_length_m": 10.0})]
    summary = build_summary(group_trials(recs))
    back = json.loads(json.dumps(summary))
    assert back["experiments"]["E4"]["methods"]["B0"]["n"] == 1


def test_collect_records_normalizes_experiment(tmp_path):
    from analyze_results import collect_records
    d = tmp_path / "E4_viewpoint_policy" / "commit_x" / "P2" / "F00"
    d.mkdir(parents=True)
    (d / "seed_0001.json").write_text(json.dumps(
        {"method": "P2", "scenario": "F00", "seed": 1,
         "result": "completed", "metrics": {}}))
    recs = collect_records(str(tmp_path))
    assert recs[0]["experiment"] == "E4"


def test_generate_plots_smoke(tmp_path):
    summary = {
        "e4_tradeoff": {"P2": {"delta_success": 0.2, "delta_distance": 3.0}},
        "experiments": {
            "E4": {"methods": {
                "B0": {"success_rate": 0.5},
                "P2": {"success_rate": 0.7, "metrics": {}},
                "P2_A1": {"success_rate": 0.6, "metrics": {}}}},
            "E5": {"methods": {
                "PID": {"metrics": {"final_position_error": 0.05,
                                    "effort_abs": 1.0,
                                    "settling_time_s": 2.0,
                                    "constraint_violations": 0.0}},
                "MPC": {"metrics": {"final_position_error": 0.03,
                                    "effort_abs": 0.8,
                                    "settling_time_s": 1.5,
                                    "constraint_violations": 0.0}}}},
        },
    }
    made = make_plots(summary, str(tmp_path))
    assert set(made) == {"e4_tradeoff.png", "method_comparison.png",
                         "ablation_delta.png", "e5_pid_mpc.png"}
    for name in made:
        assert (tmp_path / name).exists()