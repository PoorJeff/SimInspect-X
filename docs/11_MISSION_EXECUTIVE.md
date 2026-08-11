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

## Result record

```json
{
  "asset_id": "gauge_pump_01",
  "attempts": 2,
  "selected_viewpoints": ["v3", "v5"],
  "estimated_value": 42.1,
  "confidence": 0.87,
  "navigation_time_s": 12.3,
  "inspection_time_s": 4.1,
  "status": "success"
}
```

The benchmark layer may append true value and absolute error after the mission.
Production mission code must not know the hidden true value.
