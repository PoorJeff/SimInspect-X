"""Pure-logic tests for the demo configuration (P10-T01)."""
import os
import sys

import yaml

YAML = os.path.join(os.path.dirname(__file__), "..", "..", "..",
                    "config", "demo_config.yaml")


def _load():
    with open(YAML, encoding="utf-8") as f:
        return yaml.safe_load(f)


def test_demo_config_fields():
    d = _load()
    assert d["seed"] == 21 and 21 <= d["seed"] <= 30     # dev pool
    assert d["scenario"] == "F00"
    assert d["ordering"] in ("list", "greedy")
    assert d["timeout_s"] > 0
    assert d["headless"] is True
    assert d["world"].endswith("plant.sdf")


def test_demo_config_assets():
    d = _load()
    assets = d["assets"]
    assert len(assets) >= d["expected_min_assets"] >= 5
    assert len(set(assets)) == len(assets)               # unique ids
    for a in assets:
        assert a.startswith("gauge_")