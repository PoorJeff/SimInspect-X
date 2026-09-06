#!/usr/bin/env python3
"""Benchmark-only recorder for path, reading, reinspection, and fault evidence."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any, Mapping


def _write_json_atomic(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass


def load_benchmark_truth(path: Path) -> dict[str, float]:
    """Load declared benchmark values without reading a mission report."""
    import yaml

    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    rows = data.get("assets", data) if isinstance(data, Mapping) else data
    if isinstance(rows, Mapping):
        rows = [{"id": key, "true_value": value} for key, value in rows.items()]
    truth: dict[str, float] = {}
    for row in rows or []:
        if not isinstance(row, Mapping) or "id" not in row:
            continue
        value = row.get("true_value")
        if value is None and isinstance(row.get("gauge"), Mapping):
            value = row["gauge"].get("true_value", row["gauge"].get("value"))
        if value is not None:
            truth[str(row["id"])] = float(value)
    return truth


class EvidenceRecorder:
    """Collect declared benchmark truth separately from the mission report."""

    def __init__(self, run_id: str, truth_by_asset: Mapping[str, float], output_path: Path) -> None:
        self.run_id = str(run_id)
        self.truth_by_asset = {str(key): float(value) for key, value in truth_by_asset.items()}
        self.output_path = Path(output_path)
        self._last_pose: tuple[float, float] | None = None
        self._path_length_m = 0.0
        self._reading_count = 0
        self._valid_read_count = 0
        self._absolute_errors: list[float] = []
        self._viewpoints: dict[str, set[tuple[float, ...]]] = {}
        self._recovery_count = 0
        self._f06_spawned = False
        self._f06_model: str | None = None
        self._f07_modified = False

    def _check_run_id(self, run_id: str | None) -> None:
        if run_id is not None and str(run_id) != self.run_id:
            raise ValueError(f"run_id mismatch: expected {self.run_id}, got {run_id}")

    def record_pose(self, x: float, y: float, *, run_id: str | None = None) -> None:
        self._check_run_id(run_id)
        pose = (float(x), float(y))
        if self._last_pose is not None:
            dx = pose[0] - self._last_pose[0]
            dy = pose[1] - self._last_pose[1]
            self._path_length_m += (dx * dx + dy * dy) ** 0.5
        self._last_pose = pose

    def record_reading(
        self,
        asset_id: str,
        estimated_value: float,
        *,
        confidence: float | None = None,
        run_id: str | None = None,
    ) -> None:
        self._check_run_id(run_id)
        self._reading_count += 1
        truth = self.truth_by_asset.get(str(asset_id))
        if truth is None or (confidence is not None and float(confidence) < 0.8):
            return
        self._valid_read_count += 1
        self._absolute_errors.append(round(abs(float(estimated_value) - truth), 6))

    def record_event(self, event: str, details: Mapping[str, Any], *, run_id: str | None = None) -> None:
        self._check_run_id(run_id)
        details = dict(details)
        if event == "reinspection.viewpoint_selected":
            asset_id = str(details.get("asset_id", ""))
            pose_value = details.get("pose", ())
            if isinstance(pose_value, Mapping):
                pose = tuple(round(float(pose_value[key]), 6) for key in ("x", "y", "z") if key in pose_value)
            else:
                pose = tuple(round(float(value), 6) for value in pose_value)
            self._viewpoints.setdefault(asset_id, set()).add(pose)
        if event == "navigation.completed" and bool(details.get("recovery", details.get("recovered", False))):
            self._recovery_count += 1

    def set_fault_state(self, scenario: str, *, active: bool, evidence: Mapping[str, Any] | None = None) -> None:
        evidence = dict(evidence or {})
        if scenario == "F06":
            self._f06_spawned = bool(active and evidence.get("spawned", evidence.get("success", False)))
            self._f06_model = str(evidence.get("model", "blocking_box")) if active else None
        if scenario == "F07":
            self._f07_modified = bool(active and evidence.get("frames_modified", 0))

    def finalize(self, *, run_id: str | None = None) -> dict[str, Any]:
        self._check_run_id(run_id)
        result = {
            "schema_version": "1.0",
            "run_id": self.run_id,
            "producer": "siminspect_benchmark",
            "valid_read_count": self._valid_read_count,
            "reading_count": self._reading_count,
            "absolute_errors": list(self._absolute_errors),
            "path_length_m": round(self._path_length_m, 6),
            "alternative_viewpoint_attempts": sum(len(poses) for poses in self._viewpoints.values()),
            "distinct_viewpoints_by_asset": {asset: len(poses) for asset, poses in sorted(self._viewpoints.items())},
            "recovery_count": self._recovery_count,
            "f06_occluder_spawned": self._f06_spawned,
            "f06_occluder_model": self._f06_model,
            "f07_camera_frames_modified": self._f07_modified,
        }
        _write_json_atomic(self.output_path, result)
        return result


def main() -> None:  # pragma: no cover - the ROS subscription is exercised on Ubuntu
    raise SystemExit("e4_evidence_recorder is composed by the demo orchestrator")


if __name__ == "__main__":
    main()
