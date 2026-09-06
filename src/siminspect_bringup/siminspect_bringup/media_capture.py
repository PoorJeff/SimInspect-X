"""Bind visual recordings and screenshots to the formal run timeline."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shlex
import signal
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import cv2

from .run_artifacts import write_json_atomic


REQUIRED_SCREENSHOTS = (
    "01-navigation", "02-viewpoint-selected", "03-gauge-reading",
    "04-reinspection", "05-mission-complete",
)
_EVENT_ALIASES = {
    "01-navigation": ("navigation.completed", "navigation.started"),
    "02-viewpoint-selected": ("viewpoint.selected",),
    "03-gauge-reading": ("gauge.reading",),
    "04-reinspection": ("reinspection.viewpoint_selected", "reinspection.requested"),
    "05-mission-complete": ("mission.return_home.completed", "run.acceptance_completed"),
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _timestamp(event: Mapping[str, Any]) -> str:
    value = event.get("timestamp")
    if isinstance(value, str) and value:
        return value
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def select_event_windows(events: Iterable[Mapping[str, Any]]) -> dict[str, float]:
    """Select one monotonic timestamp for each public screenshot moment."""
    event_list = list(events)
    selected: dict[str, float] = {}
    for screenshot, aliases in _EVENT_ALIASES.items():
        for event in event_list:
            if event.get("event") in aliases:
                selected[screenshot] = float(event.get("monotonic_s", 0.0))
                break
        if screenshot not in selected:
            raise ValueError(f"missing formal event for {screenshot}: {aliases}")
    return selected


def _video_metadata(video: Path) -> tuple[int, int, float, int]:
    capture = cv2.VideoCapture(str(video))
    try:
        if not capture.isOpened():
            raise ValueError(f"cannot open recorded video: {video}")
        width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = float(capture.get(cv2.CAP_PROP_FPS))
        frames = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
    finally:
        capture.release()
    if width <= 0 or height <= 0 or fps <= 0 or frames <= 0:
        raise ValueError(f"recorded video has invalid metadata: {video}")
    return width, height, fps, frames


def build_media_index(
    run_dir: Path,
    run_id: str,
    events: Sequence[Mapping[str, Any]],
    *,
    commit_sha: str,
    command: Sequence[str],
    display: str,
) -> dict[str, Any]:
    run_dir = Path(run_dir)
    if run_dir.name != run_id:
        raise ValueError(f"run_id does not match run directory: {run_id}")
    if any(event.get("run_id") not in (None, run_id) for event in events):
        raise ValueError("media events contain a different run_id")
    windows = select_event_windows(events)
    video = run_dir / "media" / "demo.mp4"
    width, height, fps, frame_count = _video_metadata(video)
    timestamps = [_timestamp(event) for event in events]
    started_at = min(timestamps) if timestamps else datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    ended_at = max(timestamps) if timestamps else started_at
    items = [{
        "kind": "video", "path": "media/demo.mp4", "sha256": _sha256(video),
        "source": "live_capture", "started_at": started_at, "ended_at": ended_at,
        "width_px": width, "height_px": height, "fps": fps,
    }]
    for screenshot in REQUIRED_SCREENSHOTS:
        path = run_dir / "media" / "screenshots" / f"{screenshot}.webp"
        if not path.is_file():
            raise FileNotFoundError(path)
        items.append({
            "kind": "screenshot", "path": f"media/screenshots/{screenshot}.webp",
            "sha256": _sha256(path), "source": "live_capture",
            "started_at": started_at, "ended_at": ended_at,
            "width_px": width, "height_px": height, "fps": fps,
            "event_monotonic_s": windows[screenshot],
        })
    metadata = {
        "schema_version": "1.0", "run_id": run_id, "commit_sha": commit_sha,
        "source": "live_capture", "command": list(command), "display": display,
        "started_at": started_at, "ended_at": ended_at,
        "width_px": width, "height_px": height, "fps": fps, "frame_count": frame_count,
        "video_sha256": _sha256(video),
    }
    write_json_atomic(run_dir / "media" / "recording-metadata.json", metadata)
    index = {"schema_version": "1.0", "run_id": run_id, "items": items}
    write_json_atomic(run_dir / "media" / "index.json", index)
    return index


def _capture_screenshots(video: Path, run_dir: Path, windows: Mapping[str, float], fps: float) -> None:
    capture = cv2.VideoCapture(str(video))
    try:
        for screenshot in REQUIRED_SCREENSHOTS:
            capture.set(cv2.CAP_PROP_POS_MSEC, float(windows[screenshot]) * 1000.0)
            ok, frame = capture.read()
            if not ok:
                capture.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ok, frame = capture.read()
            if not ok:
                raise RuntimeError(f"unable to extract screenshot {screenshot}")
            path = run_dir / "media" / "screenshots" / f"{screenshot}.webp"
            path.parent.mkdir(parents=True, exist_ok=True)
            if not cv2.imwrite(str(path), frame):
                raise RuntimeError(f"unable to write screenshot {path}")
    finally:
        capture.release()


def capture_live(
    run_dir: Path,
    *,
    commit_sha: str = "unknown",
    display: str | None = None,
    width: int = 1280,
    height: int = 720,
    fps: int = 10,
    duration_s: float | None = None,
) -> dict[str, Any]:
    """Capture an X11 desktop until interrupted, then bind screenshots to events."""
    run_dir = Path(run_dir)
    run_id = run_dir.name
    display = display or os.environ.get("DISPLAY", ":0.0")
    video = run_dir / "media" / "demo.mp4"
    command = ["ffmpeg", "-y", "-f", "x11grab", "-video_size", f"{width}x{height}", "-framerate", str(fps), "-i", f"{display}+0,0"]
    if duration_s is not None:
        command.extend(["-t", str(float(duration_s))])
    command.extend(["-pix_fmt", "yuv420p", str(video)])
    process = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        process.wait()
    except KeyboardInterrupt:
        process.send_signal(signal.SIGINT)
        process.wait(timeout=15)
    if process.returncode != 0:
        raise RuntimeError(f"ffmpeg capture failed with exit code {process.returncode}")
    events_path = run_dir / "events.jsonl"
    events = [json.loads(line) for line in events_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    windows = select_event_windows(events)
    _capture_screenshots(video, run_dir, windows, float(fps))
    return build_media_index(run_dir, run_id, events, commit_sha=commit_sha, command=command, display=display)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Capture live visual evidence for one SimInspect-X run")
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--commit-sha", default="unknown")
    parser.add_argument("--display", default=None)
    parser.add_argument("--width", type=int, default=1280)
    parser.add_argument("--height", type=int, default=720)
    parser.add_argument("--fps", type=int, default=10)
    parser.add_argument("--duration-s", type=float, default=None)
    args = parser.parse_args(argv)
    if args.commit_sha == "unknown":
        manifest_path = args.run_dir / "manifest.json"
        if manifest_path.is_file():
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            git = manifest.get("git", {})
            args.commit_sha = git.get("commit_sha", "unknown") if isinstance(git, Mapping) else "unknown"
    capture_live(args.run_dir, commit_sha=args.commit_sha, display=args.display, width=args.width, height=args.height, fps=args.fps, duration_s=args.duration_s)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
