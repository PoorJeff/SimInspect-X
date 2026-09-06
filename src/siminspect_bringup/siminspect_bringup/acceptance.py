"""Pure-Python semantic gates for a single demo run."""

from __future__ import annotations

import hashlib
import json
import re
import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from .run_artifacts import write_json_atomic


@dataclass(frozen=True)
class GateResult:
    id: str
    status: str
    reason: str
    evidence: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "status": self.status,
            "reason": self.reason,
            "evidence": list(self.evidence),
        }


def _gate(gate_id: str, passed: bool, reason: str, *evidence: str) -> GateResult:
    return GateResult(gate_id, "passed" if passed else "failed", reason, tuple(evidence))


def validate_mission_report(
    report: Mapping[str, object], expected_assets: Sequence[str], run_id: str
) -> list[GateResult]:
    """Validate the v1.1 mission report without trusting simulator truth."""
    report_map = report if isinstance(report, Mapping) else {}
    expected = list(expected_assets)
    schema_ok = (
        report_map.get("schema_version") == "1.1"
        and report_map.get("run_id") == run_id
        and isinstance(report_map.get("results"), list)
    )
    gates = [_gate("report_schema", schema_ok, "schema v1.1 and run_id match" if schema_ok else "invalid report schema or run_id", "mission_report.json")]

    results = report_map.get("results", [])
    result_ids = [item.get("asset_id") for item in results if isinstance(item, Mapping)]
    coverage_ok = (
        len(expected) == 6
        and len(set(expected)) == 6
        and report_map.get("expected_asset_ids") == expected
        and report_map.get("num_assets") == 6
        and all(isinstance(asset_id, str) for asset_id in result_ids)
        and len(result_ids) == len(set(result_ids))
        and set(result_ids) == set(expected)
    )
    gates.append(_gate("asset_coverage", coverage_ok, "exactly six expected assets have one result each" if coverage_ok else "mission does not contain exactly six unique expected assets", "mission_report.json"))

    successful_reading = any(
        isinstance(item, Mapping)
        and item.get("status") == "success"
        and item.get("estimated_value") is not None
        and isinstance(item.get("confidence"), (int, float))
        and float(item.get("confidence")) >= 0.8
        for item in results
    )
    gates.append(_gate("camera_reading", successful_reading, "at least one successful camera-pipeline reading" if successful_reading else "no successful camera-pipeline reading", "mission_report.json"))

    bounded = bool(results) and all(
        isinstance(item, Mapping)
        and isinstance(item.get("attempts"), int)
        and not isinstance(item.get("attempts"), bool)
        and 1 <= int(item.get("attempts")) <= 3
        for item in results
    )
    gates.append(_gate("bounded_attempts", bounded, "all asset attempts are bounded to 1..3" if bounded else "an asset has missing or unbounded attempts", "mission_report.json"))

    home = report_map.get("return_home")
    distance = home.get("final_distance_m") if isinstance(home, Mapping) else None
    home_ok = (
        isinstance(home, Mapping)
        and home.get("status") == "success"
        and isinstance(distance, (int, float))
        and float(distance) <= 0.10
    )
    gates.append(_gate("return_home", home_ok, "return-home succeeded within 0.10 m" if home_ok else "return-home evidence is missing, failed, or outside 0.10 m", "mission_report.json"))
    return gates


def _verify_manifest_checksums(run_dir: Path, manifest: Mapping[str, Any]) -> bool:
    checksums = manifest.get("artifact_checksums") or manifest.get("checksums") or {}
    if not isinstance(checksums, Mapping):
        return False
    for relative, expected in checksums.items():
        path = run_dir / str(relative)
        relative_path = Path(str(relative))
        if relative_path.is_absolute() or ".." in relative_path.parts or not path.is_file():
            return False
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != expected:
            return False
    return True


def evaluate_run(
    run_dir: Path,
    *,
    expected_assets: Sequence[str],
    run_id: str | None = None,
) -> dict[str, Any]:
    """Evaluate a run and always preserve the resulting acceptance.json."""
    run_dir = Path(run_dir)
    manifest_path = run_dir / "manifest.json"
    report_path = run_dir / "mission_report.json"
    events_path = run_dir / "events.jsonl"
    manifest: Mapping[str, Any] = {}
    report: Mapping[str, Any] = {}
    manifest_ok = False
    report_ok = False
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        git = manifest.get("git", {})
        commit = git.get("commit_sha") if isinstance(git, Mapping) else None
        manifest_ok = (
            manifest.get("schema_version") == "1.0"
            and isinstance(git, Mapping)
            and not bool(git.get("dirty"))
            and isinstance(commit, str)
            and re.fullmatch(r"[0-9a-f]{40}", commit) is not None
            and (not (manifest.get("artifact_checksums") or manifest.get("checksums")) or _verify_manifest_checksums(run_dir, manifest))
        )
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        manifest_ok = False
    gates = [_gate("manifest", manifest_ok, "clean manifest with a full commit SHA and valid checksums" if manifest_ok else "manifest is missing, dirty, incomplete, or checksum-invalid", "manifest.json")]

    actual_run_id = run_id or (manifest.get("run_id") if isinstance(manifest, Mapping) else "")
    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
        report_ok = isinstance(report, Mapping)
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        report_ok = False
    if report_ok:
        gates.extend(validate_mission_report(report, expected_assets, str(actual_run_id)))
    else:
        gates.extend(validate_mission_report({}, expected_assets, str(actual_run_id)))
    events_ok = events_path.is_file()
    gates.append(_gate("events", events_ok, "events.jsonl is present" if events_ok else "events.jsonl is missing", "events.jsonl"))

    acceptance = {
        "schema_version": "1.0",
        "run_id": str(actual_run_id),
        "overall": "passed" if all(g.status == "passed" for g in gates) else "failed",
        "gates": [g.to_dict() for g in gates],
    }
    write_json_atomic(run_dir / "acceptance.json", acceptance)
    return acceptance


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate one SimInspect-X run directory")
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--expected-assets", nargs="*", default=None)
    args = parser.parse_args(argv)
    run_dir = Path(args.run_dir)
    expected = list(args.expected_assets or [])
    if not expected:
        report_path = run_dir / "mission_report.json"
        if report_path.is_file():
            try:
                report = json.loads(report_path.read_text(encoding="utf-8"))
                expected = list(report.get("expected_asset_ids", []))
            except (OSError, ValueError, TypeError, json.JSONDecodeError):
                expected = []
    result = evaluate_run(run_dir, expected_assets=expected, run_id=run_dir.name)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result["overall"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
