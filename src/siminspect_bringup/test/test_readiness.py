import sys
import time
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src" / "siminspect_bringup"))

from siminspect_bringup.readiness import (  # noqa: E402
    ProbeResult,
    ReadinessProbe,
    run_readiness_probe,
)


def test_probe_passes_and_preserves_observation_and_evidence():
    probe = ReadinessProbe(
        "clock", lambda: {"ok": True, "observed": {"rate_hz": 20}},
        expected="/clock publishes at >= 1 Hz", evidence=("logs/gazebo.log",),
    )
    result = run_readiness_probe(probe, timeout_s=0.2)
    assert isinstance(result, ProbeResult)
    assert result.status == "passed"
    assert result.observed == {"rate_hz": 20}
    assert result.evidence == ("logs/gazebo.log",)
    assert result.elapsed_s >= 0


def test_probe_failure_contains_expected_observed_timeout_and_log_evidence():
    probe = ReadinessProbe("scan", lambda: False, expected="/scan >= 5 Hz", component="lidar", log_path="logs/gazebo.log")
    result = run_readiness_probe(probe, timeout_s=0.1)
    assert result.status == "failed"
    assert "expected=/scan >= 5 Hz" in result.reason
    assert "component=lidar" in result.reason
    assert "timeout_s=0.1" in result.reason
    assert "logs/gazebo.log" in result.evidence


def test_probe_timeout_is_bounded_and_does_not_wait_for_worker():
    probe = ReadinessProbe("tf", lambda: time.sleep(1.0), expected="map -> base_link")
    started = time.monotonic()
    result = run_readiness_probe(probe, timeout_s=0.02)
    elapsed = time.monotonic() - started
    assert result.status == "timeout"
    assert result.elapsed_s >= 0.02
    assert elapsed < 0.4


def test_probe_exception_is_a_failure():
    def broken():
        raise RuntimeError("transport closed")

    result = run_readiness_probe(ReadinessProbe("nav", broken, expected="action server"), timeout_s=0.2)
    assert result.status == "failed"
    assert "transport closed" in result.reason
