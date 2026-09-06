"""Evidence-backed demo entry point.

The shell wrapper only handles Docker.  This module owns one run directory,
component lifetime, bounded waits, acceptance, and final checksums.
"""

from __future__ import annotations

import argparse
import os
import signal
import subprocess
import time
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

from .acceptance import evaluate_run
from .component_graph import build_component_graph
from .demo_config import DemoConfig, load_demo_config
from .process_supervisor import ProcessSupervisor
from .readiness import ReadinessProbe, run_readiness_probe
from .run_artifacts import RunArtifacts, build_run_id


def _topic_has_publisher(output: str) -> bool:
    """Parse ``ros2 topic info -v`` without importing ROS into the orchestrator."""
    for line in output.splitlines():
        if line.strip().startswith("Publisher count:"):
            try:
                return int(line.split(":", 1)[1].strip()) > 0
            except ValueError:
                return False
    return False


def _has_map_odom_transform(output: str) -> bool:
    """Return true when one TF message contains the SLAM map edge."""
    return "frame_id: map" in output and "child_frame_id: odom" in output


def _tf2_echo_has_map_odom(output: str | bytes) -> bool:
    """Parse tf2_echo output for a resolved map -> odom transform."""
    if isinstance(output, bytes):
        output = output.decode(errors="replace")
    return "Translation:" in output and "Rotation:" in output


def _navigation_ready(process: subprocess.Popen, timeout_s: float = 55.0) -> dict[str, object]:
    """Wait for the map publisher and map->odom TF before starting mission goals."""
    deadline = time.monotonic() + max(1.0, timeout_s)
    latest: dict[str, object] = {"ok": False, "reason": "waiting for map publisher and map->odom TF", "observed": {}}
    while time.monotonic() < deadline:
        if process.poll() is not None:
            return {"ok": False, "reason": "navigation process exited", "observed": {}}
        try:
            map_info = subprocess.run(
                ("ros2", "topic", "info", "/map", "-v"),
                capture_output=True,
                text=True,
                timeout=2.0,
                check=False,
            )
            map_ready = _topic_has_publisher(map_info.stdout)
        except subprocess.SubprocessError:
            map_ready = False
        try:
            tf = subprocess.run(
                ("ros2", "run", "tf2_ros", "tf2_echo", "map", "odom"),
                capture_output=True,
                text=True,
                timeout=3.0,
                check=False,
            )
            tf_output = tf.stdout
        except subprocess.TimeoutExpired as exc:
            tf_output = exc.stdout or ""
        except subprocess.SubprocessError:
            tf_output = ""
        tf_ready = _tf2_echo_has_map_odom(tf_output)
        latest = {
            "ok": map_ready and tf_ready,
            "reason": "map publisher and map->odom TF ready" if map_ready and tf_ready else "waiting for map publisher and map->odom TF",
            "observed": {
                "map_publisher": map_ready,
                "map_odom_tf": tf_ready,
                "tf_sample": tf_output[-400:],
            },
        }
        if map_ready and tf_ready:
            return latest
        time.sleep(0.5)
    return latest


class DemoArgumentParser(argparse.ArgumentParser):
    def parse_args(self, args: Sequence[str] | None = None, namespace=None):
        parsed = super().parse_args(args, namespace)
        parsed.visual = parsed.mode == "visual"
        parsed.headless = parsed.mode == "headless"
        if parsed.record and not parsed.visual:
            self.error("--record requires --visual")
        return parsed


def build_parser() -> argparse.ArgumentParser:
    parser = DemoArgumentParser(
        description="SimInspect-X evidence-backed autonomous inspection demo",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Public invocations:\n"
            "  run_demo.sh --headless\n"
            "  run_demo.sh --visual\n"
            "  run_demo.sh --visual --record\n\n"
            "Benchmark/reproducibility overrides (internal): --method, --scenario, "
            "--seed, --benchmark-evidence, --artifact-root."
        ),
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--headless", dest="mode", action="store_const", const="headless", help="run the CPU/headless demo (default)")
    mode.add_argument("--visual", dest="mode", action="store_const", const="visual", help="run with Gazebo GUI and RViz")
    parser.set_defaults(mode="headless")
    parser.add_argument("--record", action="store_true", help="record visual media (requires --visual)")
    parser.add_argument("--config", type=Path, default=Path("config/demo_config.yaml"), help=argparse.SUPPRESS)
    parser.add_argument("--method", choices=("B0", "P2"), default=None, help="benchmark selector override")
    parser.add_argument("--scenario", choices=("F00", "F06", "F07"), default=None, help="fault scenario override")
    parser.add_argument("--seed", type=int, choices=tuple(range(1, 11)) + tuple(range(21, 26)), default=None, help="deterministic seed override")
    parser.add_argument("--artifact-root", type=Path, default=Path("artifacts/runs"), help="run output root")
    parser.add_argument("--benchmark-evidence", action="store_true", help="internal: add benchmark-only truth/recorder processes")
    parser.add_argument("--dry-run", action="store_true", help=argparse.SUPPRESS)
    return parser


def config_with_overrides(config_path: Path, args: argparse.Namespace) -> DemoConfig:
    config = load_demo_config(Path(config_path))
    changes = {}
    if args.method is not None:
        changes["method"] = args.method
    if args.scenario is not None:
        changes["scenario"] = args.scenario
    if args.seed is not None:
        changes["seed"] = args.seed
    return replace(config, **changes)


def _git_metadata(root: Path) -> tuple[str, bool]:
    supplied_sha = os.environ.get("SIMINSPECT_COMMIT_SHA", "")
    if len(supplied_sha) == 40 and all(character in "0123456789abcdef" for character in supplied_sha):
        return supplied_sha, os.environ.get("SIMINSPECT_GIT_DIRTY", "0") == "1"
    try:
        sha = subprocess.run(("git", "rev-parse", "HEAD"), cwd=root, capture_output=True, text=True, check=True).stdout.strip()
        dirty = bool(subprocess.run(("git", "status", "--porcelain"), cwd=root, capture_output=True, text=True, check=True).stdout.strip())
        if len(sha) != 40:
            raise ValueError("short git SHA")
        return sha, dirty
    except (OSError, subprocess.CalledProcessError, ValueError):
        return "0" * 40, True


def _environment() -> dict[str, str]:
    return {
        "ros_distribution": os.environ.get("ROS_DISTRO", "unknown"),
        "gazebo_version": os.environ.get("GZ_VERSION", "unknown"),
        "python": os.sys.version.split()[0],
    }


def run(args: argparse.Namespace) -> int:
    repo_root = Path.cwd()
    config = config_with_overrides(args.config, args)
    commit_sha, dirty = _git_metadata(repo_root)
    mode = "visual" if args.visual else "headless"
    started_at = datetime.now(timezone.utc)
    run_id = build_run_id(started_at, commit_sha, mode, config.seed)
    manifest = {
        "git": {"commit_sha": commit_sha, "short_commit": commit_sha[:7], "dirty": dirty},
        "image_id": os.environ.get("SIMINSPECT_IMAGE_ID", "unknown"),
        "ros_distribution": os.environ.get("ROS_DISTRO", "unknown"),
        "gazebo_version": os.environ.get("GZ_VERSION", "unknown"),
        "mode": mode,
        "world": str(config.world),
        "mission": "gauge_inspection",
        "method": config.method,
        "controller": config.controller,
        "scenario": config.scenario,
        "seed": config.seed,
    }
    artifacts = RunArtifacts.create(
        args.artifact_root,
        run_id,
        config_path=args.config,
        environment=_environment(),
        manifest=manifest,
    )
    supervisor = ProcessSupervisor(event_writer=artifacts)
    accepted = False
    previous_handlers = {}

    def interrupt_handler(signum, _frame):
        raise KeyboardInterrupt(f"received signal {signum}")

    for signal_name in (signal.SIGINT, signal.SIGTERM):
        previous_handlers[signal_name] = signal.signal(signal_name, interrupt_handler)
    try:
        artifacts.append_event("mission.started", component="orchestrator", status="started", details={"mode": mode, "method": config.method})
        if args.dry_run:
            artifacts.append_event("run.dry_run", component="orchestrator", status="failed", details={"reason": "dry_run"})
        else:
            specs = build_component_graph(config, mode, args.record, args.benchmark_evidence, artifacts.run_dir)
            for spec in specs:
                process = supervisor.start(spec)
                if spec.name == "navigation":
                    probe = ReadinessProbe(
                        "navigation_ready",
                        lambda process=process, timeout_s=config.readiness_timeout_s: _navigation_ready(process, timeout_s - 5.0),
                        expected="/map publisher and map -> odom TF",
                        component=spec.name,
                        log_path=str(spec.log_path.relative_to(artifacts.run_dir).as_posix()),
                    )
                else:
                    probe = ReadinessProbe(
                        spec.name,
                        lambda process=process: process.poll() is None,
                        expected=f"{spec.name} process remains alive after launch",
                        component=spec.name,
                        log_path=str(spec.log_path.relative_to(artifacts.run_dir).as_posix()),
                    )
                probe_timeout = config.readiness_timeout_s if spec.name == "navigation" else min(config.readiness_timeout_s, 5.0)
                result = run_readiness_probe(probe, probe_timeout)
                artifacts.append_event("readiness.completed", component=spec.name, status=result.status, details={"reason": result.reason, "observed": dict(result.observed), "evidence": list(result.evidence)})
                if result.status != "passed":
                    raise RuntimeError(result.reason)
            deadline = time.monotonic() + config.mission_timeout_s
            report_path = artifacts.run_dir / "mission_report.json"
            while time.monotonic() < deadline:
                if report_path.is_file():
                    break
                if any(process.poll() not in (None, 0) for process in supervisor.processes.values()):
                    break
                time.sleep(0.5)
            if not report_path.is_file():
                artifacts.append_event("mission.timeout", component="orchestrator", status="failed", details={"timeout_s": config.mission_timeout_s})
    except BaseException as exc:
        artifacts.append_event("run.failed", component="orchestrator", status="failed", details={"error": repr(exc)})
    finally:
        supervisor.terminate_all(grace_s=2.0)
        supervisor.assert_all_stopped()
        for signal_name, previous in previous_handlers.items():
            signal.signal(signal_name, previous)

    acceptance = evaluate_run(artifacts.run_dir, expected_assets=config.mission_assets, run_id=run_id)
    accepted = acceptance["overall"] == "passed"
    artifacts.append_event("run.acceptance_completed", component="acceptance", status="passed" if accepted else "failed", details={"overall": acceptance["overall"]})
    artifacts.finalize_manifest()
    print(f"RUN_ID={run_id}")
    print(f"RUN_DIR={artifacts.run_dir}")
    return 0 if accepted else 1


def main(argv: Sequence[str] | None = None) -> int:
    return run(build_parser().parse_args(argv))


if __name__ == "__main__":
    raise SystemExit(main())
