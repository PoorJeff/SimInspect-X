"""Immutable, replayable output for one SimInspect-X demo run.

The module deliberately has no ROS dependency.  The orchestrator can therefore
create the run directory before any simulator process is started and preserve
the same evidence when a probe, mission, or cleanup step fails.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import tempfile
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping


RUN_ID_RE = r"\d{8}T\d{6}Z_[0-9a-f]{7,40}_(?:headless|visual)_\d+"
_COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")


def _utc_iso(value: datetime | None = None) -> str:
    value = value or datetime.now(timezone.utc)
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def build_run_id(started_at: datetime, commit_sha: str, mode: str, seed: int) -> str:
    """Build the stable public run identifier used by logs and process names."""
    if not _COMMIT_RE.fullmatch(str(commit_sha)):
        raise ValueError("commit_sha must be a 40-character lowercase hexadecimal SHA")
    if mode not in {"headless", "visual"}:
        raise ValueError("mode must be headless or visual")
    if isinstance(seed, bool) or not isinstance(seed, int) or seed < 0:
        raise ValueError("seed must be a non-negative integer")
    return f"{started_at.astimezone(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}_{commit_sha[:7]}_{mode}_{seed}"


def write_json_atomic(path: Path, value: Any) -> None:
    """Write JSON through a same-directory temporary file and ``os.replace``."""
    path = Path(path)
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


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


@dataclass
class RunArtifacts:
    """Paths and append-only operations owned by one run."""

    run_dir: Path
    run_id: str
    started_at: str
    manifest_path: Path = field(init=False)
    environment_path: Path = field(init=False)
    config_path: Path = field(init=False)
    events_path: Path = field(init=False)
    _monotonic_origin: float = field(default_factory=time.monotonic, repr=False)

    def __post_init__(self) -> None:
        self.run_dir = Path(self.run_dir)
        self.manifest_path = self.run_dir / "manifest.json"
        self.environment_path = self.run_dir / "environment.json"
        self.config_path = self.run_dir / "config.yaml"
        self.events_path = self.run_dir / "events.jsonl"

    @classmethod
    def create(
        cls,
        artifact_root: Path,
        run_id: str,
        config_path: Path | None = None,
        *,
        config: str | bytes | Mapping[str, Any] | None = None,
        environment: Mapping[str, Any] | None = None,
        manifest: Mapping[str, Any] | None = None,
    ) -> "RunArtifacts":
        if not re.fullmatch(RUN_ID_RE, run_id):
            raise ValueError(f"invalid run_id: {run_id!r}")
        run_dir = Path(artifact_root) / run_id
        if run_dir.exists():
            raise FileExistsError(f"refusing to reuse run directory: {run_dir}")
        run_dir.mkdir(parents=True)
        (run_dir / "logs").mkdir()
        (run_dir / "media" / "screenshots").mkdir(parents=True)
        started_at = _utc_iso()
        instance = cls(run_dir=run_dir, run_id=run_id, started_at=started_at)

        if config_path is not None and config is not None:
            raise ValueError("pass either config_path or config, not both")
        if config_path is not None:
            shutil.copyfile(config_path, instance.config_path)
        elif isinstance(config, (str, bytes)):
            data = config.decode() if isinstance(config, bytes) else config
            instance.config_path.write_text(data, encoding="utf-8")
        elif config is not None:
            instance.config_path.write_text(
                json.dumps(config, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
        else:
            instance.config_path.write_text("# configuration supplied by the orchestrator\n", encoding="utf-8")

        instance.events_path.touch()
        write_json_atomic(instance.environment_path, dict(environment or {}))
        initial_manifest = {
            "schema_version": "1.0",
            "run_id": run_id,
            "started_at": started_at,
            "artifacts": {},
            **dict(manifest or {}),
        }
        initial_manifest.setdefault("schema_version", "1.0")
        initial_manifest.setdefault("run_id", run_id)
        initial_manifest.setdefault("started_at", started_at)
        write_json_atomic(instance.manifest_path, initial_manifest)
        return instance

    def append_event(
        self,
        event: str,
        *,
        component: str = "orchestrator",
        status: str = "info",
        details: Mapping[str, Any] | None = None,
        monotonic_s: float | None = None,
    ) -> dict[str, Any]:
        if not event or "\n" in event:
            raise ValueError("event must be a non-empty single-line name")
        payload = {
            "schema_version": "1.0",
            "timestamp": _utc_iso(),
            "monotonic_s": round(
                float(monotonic_s) if monotonic_s is not None else time.monotonic() - self._monotonic_origin,
                6,
            ),
            "run_id": self.run_id,
            "event": event,
            "component": component,
            "status": status,
            "details": dict(details or {}),
        }
        with self.events_path.open("a", encoding="utf-8", newline="\n") as stream:
            stream.write(json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True))
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        return payload

    def finalize_manifest(self, *, ended_at: datetime | None = None) -> dict[str, Any]:
        """Bind every current artifact except the manifest/checksum list itself."""
        manifest = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        manifest["ended_at"] = _utc_iso(ended_at)
        checksums: dict[str, str] = {}
        for path in sorted(self.run_dir.rglob("*")):
            if not path.is_file() or path.name in {"manifest.json", "SHA256SUMS"}:
                continue
            relative = path.relative_to(self.run_dir).as_posix()
            if relative.startswith("."):
                continue
            checksums[relative] = _sha256(path)
        manifest["artifact_checksums"] = checksums
        # Keep the short alias for consumers that do not need the richer manifest.
        manifest["checksums"] = dict(checksums)
        write_json_atomic(self.manifest_path, manifest)
        checksum_lines = [f"{digest}  {relative}\n" for relative, digest in sorted(checksums.items())]
        (self.run_dir / "SHA256SUMS").write_text("".join(checksum_lines), encoding="utf-8")
        return manifest
