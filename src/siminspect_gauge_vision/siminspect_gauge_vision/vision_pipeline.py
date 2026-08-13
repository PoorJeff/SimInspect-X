#!/usr/bin/env python3
"""Pure vision pipeline: detector -> reader -> confidence (P10-T01).

No ROS imports (D-007): unit-testable on any host.
Closes the P5 wiring debt — the three P5 modules were library-only.
"""
try:
    from siminspect_gauge_vision.gauge_detector import GaugeDetector
    from siminspect_gauge_vision.gauge_reader import GaugeReader
    from siminspect_gauge_vision.confidence_estimator import (
        ConfidenceEstimator)
except ImportError:
    from gauge_detector import GaugeDetector
    from gauge_reader import GaugeReader
    from confidence_estimator import ConfidenceEstimator


def run_pipeline(img_bgr, detector=None, reader=None, estimator=None,
                 asset_id=""):
    """Run the full gauge vision chain on a BGR image.

    Returns a dict with the GaugeReading field values. The node layer
    (gauge_vision_node.py) only maps these into the ROS message.
    """
    det = detector or GaugeDetector()
    rd = reader or GaugeReader()
    est = estimator or ConfidenceEstimator()
    roi, (cx, cy), r, ok = det.detect(img_bgr)
    value, pointer_conf = rd.read(roi, cx, cy, r)
    # axis_ratio/consistency have no signal sources yet: neutral defaults.
    confidence = est.estimate(ok, pointer_conf, r, img_bgr.shape[0], 1.0, 1.0)
    return {
        "asset_id": asset_id,
        "estimated_value": value,
        "unit": rd.unit,
        "confidence": confidence,
        "target_pixel_area": float(r * r),
        "view_angle_proxy": 1.0 if ok else 0.0,
    }