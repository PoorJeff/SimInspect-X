"""Verify confidence correlates with error."""
import csv, cv2, math, os, sys, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "siminspect_gauge_vision"))
from gauge_detector import GaugeDetector
from gauge_reader import GaugeReader
from confidence_estimator import ConfidenceEstimator
DS = os.path.join(os.path.dirname(__file__),"..","..","..","datasets","gauge_synthetic","test")
det = GaugeDetector(); rdr = GaugeReader(); ce = ConfidenceEstimator()

def get_fs(u, tv):
    if u == "psi": return 160 if tv > 100 else 100
    if u == "kPa": return 200
    return 60

def test_confidence_correlation():
    if not os.path.isdir(DS): pytest.skip("no dataset")
    with open(os.path.join(DS, "labels.csv")) as f:
        rows = list(csv.DictReader(f))
    img_dir = os.path.join(DS, "images"); pairs = []
    for r in rows:
        img = cv2.imread(os.path.join(img_dir, r["image_id"] + ".png"))
        roi, (cx, cy), rad, ok = det.detect(img)
        if not ok: pairs.append((0.05, 1.0)); continue
        true_val = float(r["value"]); fs = get_fs(r["unit"], true_val)
        rdr.min = 0; rdr.max = fs
        est, rc = rdr.read(roi, cx, cy, rad)
        c = ce.estimate(ok, rc, rad, max(roi.shape[0], roi.shape[1]), 1.0, max(0.2, rc))
        pairs.append((c, abs(est - true_val) / fs))
    pairs.sort(key=lambda x: x[0])
    n = len(pairs); low = pairs[:n//2]; high = pairs[n//2:]
    low_mae = sum(e for _, e in low) / len(low)
    high_mae = sum(e for _, e in high) / len(high)
    print(f"Low MAE: {low_mae:.4f}, High MAE: {high_mae:.4f}")
    assert high_mae < low_mae, "High-conf should have lower error"
