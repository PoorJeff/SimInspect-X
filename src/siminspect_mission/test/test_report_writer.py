"""Test the inspection report schema builders (P8-T02).

Pure Python, no ROS imports required.
"""
import json
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "siminspect_mission"))

from report_schema import (  # noqa: E402
    SCHEMA_VERSION, VALID_CONFIDENCE, FAILURE_REASONS,
    utc_now_iso, update_confidence_log, build_viewpoint_attempts_detail,
    build_result_record, build_mission_report,
)


def _record(**overrides):
    args = dict(
        asset_id="gauge_pump_01",
        attempts=2,
        viewpoints=["v3", "v5"],
        confidence_log=[0.61, 0.87],
        estimated_value=42.1,
        confidence=0.87,
        navigation_time_s=12.34,
        inspection_time_s=4.11,
        failure_reason=None,
    )
    args.update(overrides)
    return build_result_record(**args)


def test_schema_version():
    assert SCHEMA_VERSION == "1.0"


def test_failure_reason_enum():
    assert FAILURE_REASONS == ("nav_failed", "low_confidence", "timeout", "precision_failed")


def test_timestamp_is_iso8601():
    parsed = datetime.fromisoformat(utc_now_iso())
    assert parsed.tzinfo is not None


def test_report_contains_schema_version_and_timestamp():
    report = build_mission_report([], num_assets=5, mission_time_s=10.0,
                                  timestamp_iso=utc_now_iso())
    assert report["schema_version"] == "1.0"
    datetime.fromisoformat(report["mission_timestamp"])


def test_success_record_failure_reason_null():
    r = _record()
    assert r["status"] == "success"
    assert r["failure_reason"] is None


def test_failed_record_failure_reason():
    r = _record(confidence=0.55, failure_reason="low_confidence")
    assert r["status"] == "failed"
    assert r["failure_reason"] == "low_confidence"


def test_confidence_threshold_boundary():
    assert _record(confidence=VALID_CONFIDENCE)["status"] == "success"


def test_no_reading_record_fails():
    r = _record(estimated_value=None, confidence=None,
                confidence_log=[], failure_reason="nav_failed")
    assert r["status"] == "failed"
    assert r["estimated_value"] is None
    assert r["confidence"] == 0.0


def test_viewpoint_detail_zip_and_none_padding():
    detail = build_viewpoint_attempts_detail(["v3", "v5"], [0.9])
    assert detail == [
        {"attempt": 1, "viewpoint": "v3", "confidence": 0.9},
        {"attempt": 2, "viewpoint": "v5", "confidence": None},
    ]


def test_viewpoint_detail_one_based_attempts():
    detail = build_viewpoint_attempts_detail(["v1", "v2", "v3"], [0.5, 0.6, 0.7])
    assert [d["attempt"] for d in detail] == [1, 2, 3]


def test_multi_attempt_record_detail_length():
    r = _record(viewpoints=["v3", "v5", "v7"],
                confidence_log=[0.5, 0.6, 0.9], attempts=3, confidence=0.9)
    assert len(r["viewpoint_attempts_detail"]) == 3
    assert r["viewpoint_attempts_detail"][2] == {
        "attempt": 3, "viewpoint": "v7", "confidence": 0.9}


def test_firewall_null_placeholders_present():
    r = _record()
    assert "true_value" in r and r["true_value"] is None
    assert "absolute_error" in r and r["absolute_error"] is None


def test_json_roundtrip_preserves_nulls():
    r = _record()
    back = json.loads(json.dumps(r))
    assert back["true_value"] is None
    assert back["absolute_error"] is None
    assert back["failure_reason"] is None
    assert back["status"] == "success"


def test_mission_report_aggregation():
    ok = _record(asset_id="a1")
    bad = _record(asset_id="a2", confidence=0.4, failure_reason="nav_failed",
                  estimated_value=None)
    report = build_mission_report([ok, bad], num_assets=5,
                                  mission_time_s=100.0, timestamp_iso=utc_now_iso())
    assert report["num_assets"] == 5
    assert report["num_results"] == 2
    assert report["success_count"] == 1
    assert report["schema_version"] == SCHEMA_VERSION


def test_failed_record_nav_reason():
    r = _record(confidence=None, confidence_log=[], estimated_value=None,
                failure_reason="nav_failed")
    assert r["failure_reason"] == "nav_failed"


def test_failed_record_precision_reason():
    r = _record(confidence=None, confidence_log=[], estimated_value=None,
                failure_reason="precision_failed")
    assert r["failure_reason"] == "precision_failed"


def test_confidence_log_last_reading_wins():
    log = update_confidence_log(["v3"], [], 0.55)
    log = update_confidence_log(["v3"], log, 0.90)  # reader retry, same attempt
    assert log == [0.90]


def test_confidence_log_appends_for_new_attempt():
    log = update_confidence_log(["v3", "v5"], [0.90], 0.62)
    assert log == [0.90, 0.62]