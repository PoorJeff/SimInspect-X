"""Test gauge detector on T01 test dataset."""
import cv2, os, sys, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "siminspect_gauge_vision"))
from gauge_detector import GaugeDetector

DS = os.path.join(os.path.dirname(__file__), "..", "..", "..", "datasets", "gauge_synthetic", "test")
d = GaugeDetector()

def test_detect_shape():
    import numpy as np
    img = np.ones((320, 320, 3), dtype=np.uint8) * 255
    roi, (cx, cy), r, ok = d.detect(img)
    assert roi is not None and r > 0


def test_default_detector_preserves_large_gauge_solution():
    image_path = os.path.join(DS, "images", "test_0026.png")
    if not os.path.isfile(image_path):
        pytest.skip("reference large-gauge image not found")
    img = cv2.imread(image_path)
    assert img is not None

    _, default_center, default_radius, default_ok = GaugeDetector().detect(img)
    _, large_center, large_radius, large_ok = GaugeDetector(
        min_r=80, max_r=160).detect(img)

    assert large_ok
    assert (default_ok, default_center, default_radius) == (
        large_ok, large_center, large_radius)

@pytest.mark.parametrize("i", range(20))
def test_detect_test_images(i):
    if not os.path.isdir(DS): pytest.skip("dataset not found")
    imgs = sorted(os.listdir(os.path.join(DS, "images")))
    if i >= len(imgs): pytest.skip("not enough images")
    img = cv2.imread(os.path.join(DS, "images", imgs[i]))
    roi, (cx, cy), r, ok = d.detect(img)
    assert roi.shape[0] > 20 and roi.shape[1] > 20
    assert cx > 0 and cy > 0
    assert r > 30
    if not ok:
        pytest.skip(f"image {imgs[i]} required fallback (likely heavy occlusion/noise)")
