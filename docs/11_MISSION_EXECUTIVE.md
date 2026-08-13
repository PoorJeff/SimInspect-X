# Mission Executive

## State machine

```text
IDLE
 -> LOAD_MISSION
 -> SELECT_ASSET
 -> SELECT_VIEWPOINT
 -> NAVIGATE
 -> PRECISION_APPROACH
 -> INSPECT
 -> VALIDATE
      -> success -> RECORD
      -> low confidence -> RESELECT_VIEWPOINT
      -> repeated failure -> MARK_FAILED
 -> NEXT_ASSET
 -> RETURN_HOME
 -> EXPORT_REPORT
 -> DONE
```

## Bounded retries
No infinite loops.

Per asset:
- navigation retries: 2;
- viewpoint attempts: 3;
- camera/reader retries per viewpoint: small fixed number.

## Asset ordering

The mission node declares a ROS parameter `ordering` (default `list`):

- `list` — assets are visited in declaration order (the default,
  preserving the original behaviour).
- `greedy` — nearest-neighbour heuristic: from the current robot pose,
  repeatedly visit the closest unvisited asset. The asset gauge pose is
  used as a proxy for the visit point (viewpoints lie near the asset).
  Deterministic (stable ties); not guaranteed globally optimal.

## Result record

Top-level report (schema v1.0):

```json
{
  "schema_version": "1.0",
  "mission_timestamp": "2026-08-13T01:30:00+00:00",
  "mission_time_s": 612.4,
  "num_assets": 5,
  "num_results": 5,
  "success_count": 4,
  "results": [
    {
      "asset_id": "gauge_pump_01",
      "attempts": 2,
      "selected_viewpoints": ["v3", "v5"],
      "viewpoint_attempts_detail": [
        {"attempt": 1, "viewpoint": "v3", "confidence": 0.61},
        {"attempt": 2, "viewpoint": "v5", "confidence": 0.87}
      ],
      "estimated_value": 42.1,
      "confidence": 0.87,
      "navigation_time_s": 12.3,
      "inspection_time_s": 4.1,
      "status": "success",
      "failure_reason": null,
      "true_value": null,
      "absolute_error": null
    }
  ]
}
```

### failure_reason enum

| Value | Meaning |
|---|---|
| nav_failed | Nav2 goal rejected/unavailable, or nav retries exhausted |
| precision_failed | PrecisionApproach failed or handoff retry signal |
| low_confidence | reader retries exhausted below the 0.80 threshold |
| timeout | reserved: no timeout signal source in the current action interface |

`failure_reason` is `null` for successful records. Failed assets are always
recorded: nav/approach/reader exhaustion transitions to RECORD (P8-T02
boundary decision, approved).

### Benchmark firewall

`true_value` and `absolute_error` are exported as literal `null` by mission
code. The benchmark layer may append true value and absolute error after the
mission, keyed by `asset_id`. Production mission code must not know the hidden
true value and must never read or fill these fields.
