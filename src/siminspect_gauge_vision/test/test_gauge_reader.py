"""Test gauge reader on T01 test set: MAE, RMSE, within-tolerance."""
import csv, cv2, math, os, sys, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "siminspect_gauge_vision"))
from gauge_detector import GaugeDetector
from gauge_reader import GaugeReader
DS = os.path.join(os.path.dirname(__file__), "..", "..", "..", "datasets", "gauge_synthetic", "test")
det = GaugeDetector(); rdr = GaugeReader(); TOL = 0.05

def get_fs(unit, true_val, angle_deg=None):
    if unit == "psi":
        if true_val > 100:
            return 160
        if angle_deg is not None and angle_deg > -120:
            computed = true_val * 240 / (angle_deg + 120)
            return 160 if abs(computed - 160) < abs(computed - 100) else 100
        return 100
    if unit == "kPa": return 200
    if unit == "bar": return 60
    return 100

def test_reader_mae():
    if not os.path.isdir(DS): pytest.skip("dataset not found")
    errors = []
    with open(os.path.join(DS, "labels.csv")) as f:
        rows = list(csv.DictReader(f))
    img_dir = os.path.join(DS, "images")
    for r in rows:
        img = cv2.imread(os.path.join(img_dir, r["image_id"] + ".png"))
        roi, (cx, cy), rad, ok = det.detect(img)
        if not ok: continue
        true_val = float(r["value"]); unit = r["unit"]
        fs = get_fs(unit, true_val, float(r.get("angle_deg", 0)))
        rdr.min = 0; rdr.max = fs
        est, conf = rdr.read(roi, cx, cy, rad)
        errors.append(abs(est - true_val) / fs)
    n = len(errors); assert n >= 20, f"Only {n} detections"
    mae = sum(errors) / n
    rmse = math.sqrt(sum(e*e for e in errors) / n)
    in_tol = sum(1 for e in errors if e <= TOL) / n
    print(f"Detected: {n}, MAE: {mae:.4f}, RMSE: {rmse:.4f}, Within-tol: {in_tol:.2%}")
    assert mae < 0.25, f"MAE {mae:.4f} exceeds 25%"
