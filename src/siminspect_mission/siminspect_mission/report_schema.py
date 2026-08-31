#!/usr/bin/env python3
"""Inspection report schema (P8-T02).

Pure Python, no ROS imports: unit-testable on any host (D-007 pattern).

Firewall contract (docs/11):
- `true_value` and `absolute_error` are always exported as literal `null`.
- The benchmark layer may fill them after the mission, keyed by asset_id.
  Production mission code must never read or fill them.
"""
from datetime import datetime, timezone

SCHEMA_VERSION = "1.1"
VALID_CONFIDENCE = 0.80
FAILURE_REASONS = ("nav_failed", "low_confidence", "timeout", "precision_failed")


def utc_now_iso():
    """Current UTC time as an ISO-8601 string."""
    return datetime.now(timezone.utc).isoformat()


def update_confidence_log(viewpoints, confidence_log, confidence):
    """Record a reading confidence for the current viewpoint attempt.

    Reader retries produce several readings for the same attempt; the last
    reading wins (it is the one that passed validation). A new viewpoint
    attempt (viewpoints grew) gets a fresh entry.
    """
    if len(confidence_log) < len(viewpoints):
        confidence_log.append(confidence)
    else:
        confidence_log[-1] = confidence
    return confidence_log


def build_viewpoint_attempts_detail(viewpoints, confidence_log):
    """Per-attempt viewpoint detail.

    viewpoints: list of viewpoint strings, one per attempt, in order.
    confidence_log: list of confidence floats, one per reading received.
    Attempts without a reading get confidence None.
    """
    return [
        {
            "attempt": idx + 1,
            "viewpoint": vp,
            "confidence": confidence_log[idx] if idx < len(confidence_log) else None,
        }
        for idx, vp in enumerate(viewpoints)
    ]


def build_result_record(asset_id, attempts, viewpoints, confidence_log,
                        estimated_value, confidence, navigation_time_s,
                        inspection_time_s, failure_reason):
    """Build one per-asset result record (schema v1.1)."""
    if failure_reason is not None and failure_reason not in FAILURE_REASONS:
        raise ValueError(f"Unknown failure_reason: {failure_reason}")
    success = (confidence is not None
               and confidence >= VALID_CONFIDENCE
               and failure_reason is None)
    return {
        "asset_id": asset_id,
        "attempts": attempts,
        "selected_viewpoints": list(viewpoints),
        "viewpoint_attempts_detail": build_viewpoint_attempts_detail(
            viewpoints, confidence_log),
        "estimated_value": estimated_value,
        "confidence": confidence if confidence is not None else 0.0,
        "navigation_time_s": round(navigation_time_s, 2),
        "inspection_time_s": round(inspection_time_s, 2),
        "status": "success" if success else "failed",
        "failure_reason": failure_reason,
        # Benchmark-only placeholders: never read or filled by mission code.
        "true_value": None,
        "absolute_error": None,
    }


def build_mission_report(results, num_assets, mission_time_s, timestamp_iso,
                         run_id="", expected_asset_ids=(), return_home=None):
    """Build the top-level mission report (schema v1.1)."""
    if return_home is None:
        return_home = {
            "status": "pending",
            "final_distance_m": None,
            "failure_reason": None,
        }
    return {
        "schema_version": SCHEMA_VERSION,
        "run_id": run_id,
        "mission_timestamp": timestamp_iso,
        "mission_time_s": round(mission_time_s, 2),
        "expected_asset_ids": list(expected_asset_ids),
        "num_assets": num_assets,
        "num_results": len(results),
        "success_count": sum(1 for r in results if r.get("status") == "success"),
        "return_home": dict(return_home),
        "results": results,
    }
