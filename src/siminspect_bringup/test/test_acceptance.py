import json
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src" / "siminspect_bringup"))

from siminspect_bringup.acceptance import (  # noqa: E402
    evaluate_run,
    validate_mission_report,
)
from siminspect_bringup.run_artifacts import write_json_atomic  # noqa: E402


ASSETS = ["gauge_pipe_01", "gauge_pipe_02", "gauge_pump_01", "gauge_tank_01", "gauge_tank_02", "gauge_valve_01"]


def record(asset_id, *, status="success", attempts=1, confidence=0.9, estimated_value=42.0):
    return {
        "asset_id": asset_id,
        "attempts": attempts,
        "status": status,
        "confidence": confidence,
        "estimated_value": estimated_value,
        "failure_reason": None if status == "success" else "timeout",
    }


def report(run_id="run-1", assets=ASSETS, records=None, return_home=None):
    return {
        "schema_version": "1.1",
        "run_id": run_id,
        "expected_asset_ids": list(assets),
        "num_assets": len(assets),
        "num_results": len(records if records is not None else [record(a) for a in assets]),
        "results": records if records is not None else [record(a) for a in assets],
        "return_home": return_home or {"status": "success", "final_distance_m": 0.04, "failure_reason": None},
    }


def statuses(gates):
    return {gate.id: gate.status for gate in gates}


def test_validate_report_requires_exact_six_assets_and_camera_reading():
    gates = validate_mission_report(report(), ASSETS, "run-1")
    assert all(g.status == "passed" for g in gates)
    too_few = validate_mission_report(report(assets=ASSETS[:5]), ASSETS[:5], "run-1")
    assert statuses(too_few)["asset_coverage"] == "failed"
    no_reading = validate_mission_report(
        report(records=[record(a, status="failed", confidence=0.0, estimated_value=None) for a in ASSETS]),
        ASSETS,
        "run-1",
    )
    assert statuses(no_reading)["camera_reading"] == "failed"


def test_validate_report_rejects_unbounded_attempts_and_return_home_distance():
    gates = validate_mission_report(
        report(records=[record(a, attempts=4) if i == 0 else record(a) for i, a in enumerate(ASSETS)],
               return_home={"status": "success", "final_distance_m": 0.11, "failure_reason": None}),
        ASSETS,
        "run-1",
    )
    assert statuses(gates)["bounded_attempts"] == "failed"
    assert statuses(gates)["return_home"] == "failed"


def test_evaluate_run_writes_failed_acceptance_without_deleting_evidence(tmp_path):
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    write_json_atomic(run_dir / "manifest.json", {"schema_version": "1.0", "run_id": "run-1", "git": {"dirty": True}})
    write_json_atomic(run_dir / "mission_report.json", report(run_id="run-1"))
    (run_dir / "events.jsonl").write_text("", encoding="utf-8")
    result = evaluate_run(run_dir, expected_assets=ASSETS, run_id="run-1")
    acceptance = json.loads((run_dir / "acceptance.json").read_text(encoding="utf-8"))
    assert result["overall"] == "failed"
    assert acceptance["overall"] == "failed"
    assert (run_dir / "mission_report.json").exists()
    assert any(g["id"] == "manifest" and g["status"] == "failed" for g in acceptance["gates"])


def test_evaluate_run_passes_only_when_all_required_gates_pass(tmp_path):
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    write_json_atomic(run_dir / "manifest.json", {"schema_version": "1.0", "run_id": "run-1", "git": {"commit_sha": "a" * 40, "dirty": False}})
    write_json_atomic(run_dir / "mission_report.json", report(run_id="run-1"))
    (run_dir / "events.jsonl").write_text("", encoding="utf-8")
    result = evaluate_run(run_dir, expected_assets=ASSETS, run_id="run-1")
    assert result["overall"] == "passed"
    assert json.loads((run_dir / "acceptance.json").read_text(encoding="utf-8"))["overall"] == "passed"
