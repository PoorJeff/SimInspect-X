"""Owned subprocess groups with deterministic, evidence-preserving cleanup."""

from __future__ import annotations

import os
import signal
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Mapping

from .component_graph import ProcessSpec


@dataclass
class _ManagedProcess:
    spec: ProcessSpec
    process: subprocess.Popen
    log_stream: object


class ProcessSupervisor:
    """Start each component in its own process group and reap it on exit."""

    def __init__(
        self,
        *,
        cwd: Path | None = None,
        base_env: Mapping[str, str] | None = None,
        event_writer: Callable[..., object] | object | None = None,
    ) -> None:
        self.cwd = str(cwd) if cwd is not None else None
        self.base_env = dict(base_env or {})
        self.event_writer = event_writer
        self._managed: dict[str, _ManagedProcess] = {}

    @property
    def processes(self) -> Mapping[str, subprocess.Popen]:
        return {name: managed.process for name, managed in self._managed.items()}

    def _emit(self, event: str, spec: ProcessSpec, status: str, **details: object) -> None:
        if self.event_writer is None:
            return
        writer = self.event_writer
        try:
            if hasattr(writer, "append_event"):
                writer.append_event(event, component=spec.name, status=status, details=details)
            else:
                writer(event, component=spec.name, status=status, details=details)
        except TypeError:
            # A minimal callback accepting only (event, details) is still useful in tests.
            writer(event, details)

    def start(self, spec: ProcessSpec) -> subprocess.Popen:
        if spec.name in self._managed:
            raise ValueError(f"process {spec.name!r} already started")
        spec.log_path.parent.mkdir(parents=True, exist_ok=True)
        log_stream = spec.log_path.open("w", encoding="utf-8", newline="\n")
        environment = os.environ.copy()
        environment.update(self.base_env)
        environment.update(dict(spec.env))
        kwargs = {
            "cwd": self.cwd,
            "env": environment,
            "stdout": log_stream,
            "stderr": subprocess.STDOUT,
        }
        if os.name == "nt":
            kwargs["creationflags"] = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        else:
            kwargs["start_new_session"] = True
        try:
            process = subprocess.Popen(spec.argv, **kwargs)
        except BaseException:
            log_stream.close()
            raise
        self._managed[spec.name] = _ManagedProcess(spec, process, log_stream)
        self._emit("process.started", spec, "started", pid=process.pid, argv=list(spec.argv), log_path=str(spec.log_path))
        return process

    @staticmethod
    def _wait(process: subprocess.Popen, timeout_s: float) -> bool:
        try:
            process.wait(timeout=max(0.0, timeout_s))
            return True
        except subprocess.TimeoutExpired:
            return False

    @staticmethod
    def _signal_group(process: subprocess.Popen, sig: int) -> None:
        if process.poll() is not None:
            return
        if os.name == "nt":
            if sig == signal.SIGINT:
                try:
                    process.send_signal(getattr(signal, "CTRL_BREAK_EVENT", signal.SIGTERM))
                    return
                except (OSError, ValueError):
                    pass
            if sig in {signal.SIGTERM, signal.SIGKILL}:
                try:
                    subprocess.run(
                        ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        check=False,
                    )
                    return
                except OSError:
                    pass
            process.terminate()
            return
        try:
            os.killpg(os.getpgid(process.pid), sig)
        except ProcessLookupError:
            pass

    def terminate_all(self, grace_s: float = 10.0) -> None:
        if grace_s < 0:
            raise ValueError("grace_s must be non-negative")
        for managed in list(self._managed.values()):
            process = managed.process
            if process.poll() is None:
                self._signal_group(process, signal.SIGINT)
                if not self._wait(process, grace_s):
                    self._signal_group(process, signal.SIGTERM)
                    if not self._wait(process, grace_s):
                        self._signal_group(process, signal.SIGKILL)
                        self._wait(process, grace_s)
            else:
                process.wait()
            managed.log_stream.close()
            self._emit("process.stopped", managed.spec, "stopped", returncode=process.returncode)

    def assert_all_stopped(self) -> None:
        active = [name for name, managed in self._managed.items() if managed.process.poll() is None]
        if active:
            raise AssertionError(f"owned processes still running: {active}")

    def __enter__(self) -> "ProcessSupervisor":
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.terminate_all()
