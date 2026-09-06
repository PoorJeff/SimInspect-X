import os
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "siminspect_benchmark"))

from fault_image_relay import FaultImageRelay  # noqa: E402


def test_f00_is_byte_identical():
    frame = np.arange(64 * 64 * 3, dtype=np.uint8).reshape((64, 64, 3))
    out = FaultImageRelay("F00").transform(frame)
    assert np.array_equal(out, frame)


def test_f07_applies_deterministic_gaussian_blur_sigma_three():
    frame = np.zeros((64, 64, 3), dtype=np.uint8)
    frame[16:48, 16:48] = 255
    relay = FaultImageRelay("F07")
    out = relay.transform(frame)
    expected = cv2.GaussianBlur(frame, (0, 0), sigmaX=3.0)
    assert np.array_equal(out, expected)
    assert not np.array_equal(out, frame)
    assert relay.frames_modified == 1


def test_unsupported_scenario_is_rejected():
    try:
        FaultImageRelay("F06")
    except ValueError as exc:
        assert "F00" in str(exc) and "F07" in str(exc)
    else:
        raise AssertionError("only F00 and F07 are image relay scenarios")
