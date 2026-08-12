"""Test dataset generator produces correct output structure and values."""
import os, sys, subprocess, tempfile, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "siminspect_gauge_vision"))
from generate_dataset import draw_gauge, generate

def test_draw_gauge_shape():
    img = draw_gauge(0, 0, 100, "psi")
    assert img.shape == (320, 320, 3)
    assert img.min() >= 0 and img.max() <= 255

def test_generate_small(tmp_path):
    d = str(tmp_path)
    generate(d, 10, "train")
    assert len(os.listdir(os.path.join(d, "train", "images"))) == 10
import csv
def test_labels_match_images(tmp_path):
    d = str(tmp_path)
    generate(d, 5, "test")
    imgs = set(os.listdir(os.path.join(d, "test", "images")))
    with open(os.path.join(d, "test", "labels.csv")) as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 5
    for r in rows:
        assert r["image_id"] + ".png" in imgs
