"""Bounded, dependency-free readiness probes.

The concrete ROS probes are assembled by the orchestrator later; this module
keeps the timeout and failure evidence contract testable without a running ROS
graph.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from queue import Queue
from typing import Any, Callable, Mapping


@dataclass(frozen=True)
class ProbeResult:
    probe_id: str
    status: str
    elapsed_s: float
    reason: str
    observed: Mapping[str, Any]
    evidence: tuple[str, ...]


@dataclass(frozen=True)
class ReadinessProbe:
    probe_id: str
    check: Callable[[], Any]
    expected: str = ""
    component: str = "unknown"
    log_path: str = ""
    evidence: tuple[str, ...] = ()

    def evidence_paths(self) -> tuple[str, ...]:
        paths = list(self.evidence)
        if self.log_path and self.log_path not in paths:
            paths.append(self.log_path)
        return tuple(paths)


def _probe_parts(probe: ReadinessProbe | Callable[[], Any]) -> tuple[str, Callable[[], Any], str, str, tuple[str, ...]]:
    if isinstance(probe, ReadinessProbe):
        return probe.probe_id, probe.check, probe.expected, probe.component, probe.evidence_paths()
    probe_id = str(getattr(probe, "probe_id", getattr(probe, "id", getattr(probe, "__name__", "probe"))))
    check = getattr(probe, "check", probe)
    expected = str(getattr(probe, "expected", ""))
    component = str(getattr(probe, "component", "unknown"))
    log_path = str(getattr(probe, "log_path", ""))
    evidence = tuple(getattr(probe, "evidence", ()))
    if log_path and log_path not in evidence:
        evidence += (log_path,)
    return probe_id, check, expected, component, evidence


def _normalise(value: Any) -> tuple[str, str, dict[str, Any]]:
    if isinstance(value, ProbeResult):
        return value.status, value.reason, dict(value.observed)
    if isinstance(value, Mapping):
        observed = value.get("observed")
        if not isinstance(observed, Mapping):
            observed = {str(k): v for k, v in value.items() if k not in {"status", "ok", "passed", "reason"}}
        status = value.get("status")
        if status in {"pass", "passed", "ok", True}:
            status = "passed"
        elif status in {"timeout", "timed_out"}:
            status = "timeout"
        elif status in {"fail", "failed", False}:
            status = "failed"
        elif value.get("ok", value.get("passed", False)):
            status = "passed"
        else:
            status = "failed"
        return str(status), str(value.get("reason", "")), dict(observed)
    if value is True:
        return "passed", "", {}
    return "failed", "", {"value": value}


def run_readiness_probe(
    probe: ReadinessProbe | Callable[[], Any], timeout_s: float
) -> ProbeResult:
    """Run one probe in a daemon worker and return within ``timeout_s``."""
    if timeout_s <= 0:
        raise ValueError("timeout_s must be positive")
    probe_id, check, expected, component, evidence = _probe_parts(probe)
    started = time.monotonic()
    result_queue: Queue[tuple[str, Any]] = Queue(maxsize=1)

    def worker() -> None:
        try:
            result_queue.put(("value", check()))
        except BaseException as exc:  # preserve probe failures as evidence
            result_queue.put(("error", exc))

    thread = threading.Thread(target=worker, name=f"readiness-{probe_id}", daemon=True)
    thread.start()
    thread.join(timeout_s)
    elapsed = time.monotonic() - started
    if thread.is_alive():
        elapsed = max(elapsed, timeout_s)
        observed = {"expected": expected, "timeout_s": timeout_s}
        reason = f"component={component}; expected={expected}; observed=timeout; timeout_s={timeout_s}"
        return ProbeResult(probe_id, "timeout", elapsed, reason, observed, evidence)

    kind, payload = result_queue.get_nowait()
    if kind == "error":
        observed = {"expected": expected, "exception": repr(payload)}
        reason = f"component={component}; expected={expected}; observed=exception; timeout_s={timeout_s}: {payload}"
        return ProbeResult(probe_id, "failed", elapsed, reason, observed, evidence)

    status, probe_reason, observed = _normalise(payload)
    status = status if status in {"passed", "failed", "timeout"} else "failed"
    observed = dict(observed)
    if status != "passed":
        observed.setdefault("expected", expected)
    if status == "passed":
        reason = probe_reason or "condition satisfied"
    elif status == "timeout":
        reason = f"component={component}; expected={expected}; observed=timeout; timeout_s={timeout_s}"
    else:
        reason = f"component={component}; expected={expected}; observed={observed}; timeout_s={timeout_s}"
        if probe_reason:
            reason += f": {probe_reason}"
    return ProbeResult(probe_id, status, elapsed, reason, observed, evidence)


def run_readiness_probes(
    probes: tuple[ReadinessProbe, ...] | list[ReadinessProbe], timeout_s: float
) -> tuple[ProbeResult, ...]:
    """Run probes in declaration order, stopping after the first failure."""
    results: list[ProbeResult] = []
    for probe in probes:
        result = run_readiness_probe(probe, timeout_s)
        results.append(result)
        if result.status != "passed":
            break
    return tuple(results)
