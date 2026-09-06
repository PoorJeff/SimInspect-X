import json
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "siminspect_benchmark"))

from e4_evidence_recorder import EvidenceRecorder, load_benchmark_truth  # noqa: E402


def test_recorder_accumulates_path_joins_truth_and_counts_reinspection(tmp_path):
    recorder = EvidenceRecorder("run-1", {"gauge_pump_01": 40.0}, tmp_path / "benchmark_evaluation.json")
    recorder.record_pose(0.0, 0.0)
    recorder.record_pose(0.3, 0.4)
    recorder.record_pose(0.3, 1.4)
    recorder.record_reading("gauge_pump_01", 42.5, confidence=0.9)
    recorder.record_event("reinspection.viewpoint_selected", {"asset_id": "gauge_pump_01", "pose": [1.0, 2.0]})
    recorder.record_event("reinspection.viewpoint_selected", {"asset_id": "gauge_pump_01", "pose": [2.0, 2.0]})
    recorder.record_event("navigation.completed", {"recovery": True})
    recorder.set_fault_state("F07", active=True, evidence={"frames_modified": 12})
    output = recorder.finalize()
    assert output["producer"] == "siminspect_benchmark"
    assert output["path_length_m"] == 1.5
    assert output["valid_read_count"] == 1
    assert output["absolute_errors"] == [2.5]
    assert output["alternative_viewpoint_attempts"] == 2
    assert output["distinct_viewpoints_by_asset"]["gauge_pump_01"] == 2
    assert output["recovery_count"] == 1
    assert output["f07_camera_frames_modified"] is True
    assert json.loads((tmp_path / "benchmark_evaluation.json").read_text(encoding="utf-8"))["run_id"] == "run-1"


def test_recorder_rejects_run_id_mismatch(tmp_path):
    recorder = EvidenceRecorder("run-1", {}, tmp_path / "evaluation.json")
    with pytest.raises(ValueError, match="run_id"):
        recorder.record_pose(0.0, 0.0, run_id="other")
    with pytest.raises(ValueError, match="run_id"):
        recorder.finalize(run_id="other")


def test_recorder_does_not_fill_truth_from_mission_report(tmp_path):
    recorder = EvidenceRecorder("run-1", {}, tmp_path / "evaluation.json")
    recorder.record_reading("unknown", 42.0, confidence=0.9)
    output = recorder.finalize()
    assert output["reading_count"] == 1
    assert output["valid_read_count"] == 0
    assert output["absolute_errors"] == []


def test_truth_loader_reads_only_declared_benchmark_values(tmp_path):
    path = tmp_path / "truth.yaml"
    path.write_text("assets:\n  - id: a1\n    true_value: 12.5\n", encoding="utf-8")
    assert load_benchmark_truth(path) == {"a1": 12.5}
