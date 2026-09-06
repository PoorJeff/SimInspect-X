import json
import sys
from pathlib import Path

import cv2
import numpy as np
import pytest


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src" / "siminspect_bringup"))

from siminspect_bringup.media_capture import (  # noqa: E402
    REQUIRED_SCREENSHOTS,
    build_media_index,
    select_event_windows,
)
from siminspect_bringup.component_graph import build_component_graph  # noqa: E402
from siminspect_bringup.demo_config import load_demo_config  # noqa: E402


def _events():
    names = [
        "navigation.completed", "viewpoint.selected", "gauge.reading",
        "reinspection.viewpoint_selected", "mission.return_home.completed",
    ]
    return [
        {"schema_version": "1.0", "run_id": "run-1", "event": name, "monotonic_s": float(index + 1), "timestamp": "2026-09-06T00:00:00Z", "component": "test", "status": "completed", "details": {}}
        for index, name in enumerate(names)
    ]


def _make_video(path: Path):
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), 5.0, (64, 48))
    for value in range(10):
        writer.write(np.full((48, 64, 3), value * 20, dtype=np.uint8))
    writer.release()


def test_event_windows_require_the_five_public_moments():
    windows = select_event_windows(_events())
    assert tuple(windows) == REQUIRED_SCREENSHOTS
    assert windows["01-navigation"] == 1.0
    assert windows["05-mission-complete"] == 5.0


def test_media_index_contains_live_capture_paths_checksums_and_video_metadata(tmp_path):
    run_dir = tmp_path / "run-1"
    screenshots = run_dir / "media" / "screenshots"
    screenshots.mkdir(parents=True)
    video = run_dir / "media" / "demo.mp4"
    _make_video(video)
    for name in REQUIRED_SCREENSHOTS:
        (screenshots / f"{name}.webp").write_bytes(b"RIFF" + name.encode("ascii"))
    index = build_media_index(
        run_dir,
        "run-1",
        _events(),
        commit_sha="a" * 40,
        command=("ffmpeg", "-f", "x11grab"),
        display=":0",
    )
    assert index["schema_version"] == "1.0"
    assert index["run_id"] == "run-1"
    assert len(index["items"]) == 6
    assert all(item["source"] == "live_capture" for item in index["items"])
    assert all(not Path(item["path"]).is_absolute() for item in index["items"])
    assert all(len(item["sha256"]) == 64 for item in index["items"])
    metadata = json.loads((run_dir / "media" / "recording-metadata.json").read_text(encoding="utf-8"))
    assert metadata["run_id"] == "run-1"
    assert metadata["commit_sha"] == "a" * 40
    assert metadata["fps"] > 0
    assert metadata["width_px"] == 64


def test_media_index_rejects_wrong_run_id_or_missing_event(tmp_path):
    run_dir = tmp_path / "run-1"
    (run_dir / "media" / "screenshots").mkdir(parents=True)
    (run_dir / "media" / "demo.mp4").write_bytes(b"not-video")
    with pytest.raises(ValueError, match="run_id"):
        build_media_index(run_dir, "other", _events(), commit_sha="a" * 40, command=(), display="")


def test_recording_adds_only_the_visual_capture_process(tmp_path):
    config = load_demo_config(ROOT / "config" / "demo_config.yaml")
    run_dir = tmp_path / "same-run"
    plain = build_component_graph(config, "visual", False, False, run_dir)
    recorded = build_component_graph(config, "visual", True, False, run_dir)
    plain_names = {spec.name for spec in plain}
    assert [(spec.name, spec.argv) for spec in recorded if spec.name in plain_names] == [(spec.name, spec.argv) for spec in plain]
    assert {spec.name for spec in recorded} - plain_names == {"recorder"}
