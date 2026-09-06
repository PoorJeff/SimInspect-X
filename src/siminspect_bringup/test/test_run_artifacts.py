import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src" / "siminspect_bringup"))

from siminspect_bringup.run_artifacts import (  # noqa: E402
    RUN_ID_RE,
    RunArtifacts,
    build_run_id,
    write_json_atomic,
)


def test_run_id_is_reproducible_and_strict():
    run_id = build_run_id(
        datetime(2026, 9, 6, 12, 34, 56, tzinfo=timezone.utc),
        "a" * 40,
        "headless",
        21,
    )
    assert run_id == "20260906T123456Z_aaaaaaa_headless_21"
    assert re.fullmatch(RUN_ID_RE, run_id)


def test_create_refuses_to_reuse_a_run_directory(tmp_path):
    first = RunArtifacts.create(tmp_path, "20260906T123456Z_aaaaaaa_headless_21")
    assert first.run_dir.is_dir()
    with pytest.raises(FileExistsError):
        RunArtifacts.create(tmp_path, first.run_id)


def test_atomic_json_write_leaves_valid_json_and_no_temp_file(tmp_path):
    path = tmp_path / "nested" / "report.json"
    write_json_atomic(path, {"ok": True, "value": 3})
    assert json.loads(path.read_text(encoding="utf-8")) == {"ok": True, "value": 3}
    assert list(path.parent.glob(".report.json.*.tmp")) == []


def test_events_are_one_line_json_with_relative_run_evidence(tmp_path):
    artifacts = RunArtifacts.create(tmp_path, "20260906T123456Z_aaaaaaa_headless_21")
    artifacts.append_event(
        "mission.started", component="mission", status="started", details={"asset_id": "a1"},
        monotonic_s=0.25,
    )
    lines = artifacts.events_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    event = json.loads(lines[0])
    assert event["schema_version"] == "1.0"
    assert event["run_id"] == artifacts.run_id
    assert event["monotonic_s"] == 0.25
    assert event["details"] == {"asset_id": "a1"}
    assert not Path(event["run_id"]).is_absolute()


def test_failed_runs_are_preserved_and_manifest_excludes_itself(tmp_path):
    artifacts = RunArtifacts.create(
        tmp_path,
        "20260906T123456Z_aaaaaaa_headless_21",
        manifest={"git": {"commit_sha": "a" * 40, "short_commit": "aaaaaaa", "dirty": False}},
    )
    artifacts.append_event("run.failed", component="orchestrator", status="failed")
    write_json_atomic(artifacts.run_dir / "acceptance.json", {"overall": "failed"})
    artifacts.finalize_manifest()
    manifest = json.loads(artifacts.manifest_path.read_text(encoding="utf-8"))
    assert "manifest.json" not in manifest["artifact_checksums"]
    assert (artifacts.run_dir / "acceptance.json").exists()
    checksums = artifacts.run_dir / "SHA256SUMS"
    assert checksums.exists()
    for line in checksums.read_text(encoding="utf-8").splitlines():
        digest, relative = line.split("  ", 1)
        assert digest == hashlib.sha256((artifacts.run_dir / relative).read_bytes()).hexdigest()


def test_finalize_manifest_records_environment_and_config(tmp_path):
    config = tmp_path / "source.yaml"
    config.write_text("world: plant.sdf\n", encoding="utf-8")
    artifacts = RunArtifacts.create(
        tmp_path / "runs",
        "20260906T123456Z_aaaaaaa_headless_21",
        config_path=config,
        environment={"ros": "jazzy", "gazebo": "harmonic"},
        manifest={"git": {"commit_sha": "a" * 40, "short_commit": "aaaaaaa", "dirty": False}},
    )
    artifacts.finalize_manifest()
    assert (artifacts.run_dir / "config.yaml").read_text(encoding="utf-8") == config.read_text(encoding="utf-8")
    assert json.loads((artifacts.run_dir / "environment.json").read_text(encoding="utf-8"))["ros"] == "jazzy"
