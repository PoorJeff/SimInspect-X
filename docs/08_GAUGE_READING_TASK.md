# Gauge Reading Task

## Why analog gauges

They provide a compact industrial vision problem with exact numeric ground truth:
- detect gauge;
- rectify perspective;
- identify centre / scale;
- estimate pointer angle;
- convert angle to physical value.

## Core implementation path

### Stage 1 — deterministic synthetic dataset
Generate gauge images in Python:
- pointer angle;
- scale;
- blur;
- lighting;
- perspective distortion;
- partial occlusion;
- image noise.

Keep exact label.

### Stage 2 — Gazebo asset integration
Use fixed / generated gauge-face textures on several plant assets.
The robot camera observes them from different poses.

### Stage 3 — reader
Baseline:
- detect/crop ROI;
- perspective correction;
- circle/face localisation;
- line/pointer estimation;
- angle-to-value conversion.

A learned detector may later replace only the detection stage if useful.

## Output

```text
asset_id
estimated_value
unit
confidence
target_pixel_area
view_angle_proxy
timestamp
```

## Confidence

Start with an interpretable confidence proxy using:
- successful detection;
- pointer-line strength;
- target pixel size;
- perspective/angle;
- consistency across several frames.

Do not call it statistically calibrated probability unless calibration is actually performed.

## Metrics
- MAE;
- RMSE;
- percentage within tolerance;
- failure-to-read rate;
- confidence vs actual error relationship.
