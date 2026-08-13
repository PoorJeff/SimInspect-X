"""Pure-logic tests for the vision pipeline chain (P10-T01).

No ROS imports; imports vision_pipeline only.
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "siminspect_gauge_vision"))

from vision_pipeline import run_pipeline  # noqa: E402


def test_pipeline_blank_image_deterministic():
    img = np.zeros((480, 640, 3), dtype=np.uint8)
    out = run_pipeline(img, asset_id="gauge_pump_01")
    assert out["asset_id"] == "gauge_pump_01"
    assert out["estimated_value"] == 50.0     # mid-scale fallback on blank
    assert 0.0 <= out["confidence"] < 0.1     # no detection -> low confidence
    assert out["unit"] == "psi"
    assert out["target_pixel_area"] > 0.0
    assert out["view_angle_proxy"] == 0.0     # fallback detection not ok


def test_pipeline_synthetic_image_bounds():
    import cv2
    img = np.zeros((480, 640, 3), dtype=np.uint8)
    cv2.circle(img, (320, 240), 120, (255, 255, 255), 3)
    out = run_pipeline(img, asset_id="a2")
    assert out["asset_id"] == "a2"
    assert 0.0 <= out["estimated_value"] <= 100.0
    assert 0.0 <= out["confidence"] <= 1.0
    assert out["target_pixel_area"] > 0.0