from pathlib import Path
import sys

import pytest
import yaml


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src" / "siminspect_bringup"))

from siminspect_bringup.demo_config import DemoConfig, load_demo_config


CONFIG = ROOT / "config" / "demo_config.yaml"


def write_config(tmp_path, **changes):
    data = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    data.update(changes)
    path = tmp_path / "demo_config.yaml"
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    return path


def test_loads_the_repository_demo_config_as_an_immutable_contract():
    config = load_demo_config(CONFIG)

    assert isinstance(config, DemoConfig)
    assert config.world == ROOT / "src" / "siminspect_sim" / "worlds" / "plant.sdf"
    assert config.mission_assets == (
        "gauge_pipe_01", "gauge_pipe_02", "gauge_pump_01",
        "gauge_tank_01", "gauge_tank_02", "gauge_valve_01",
    )
    assert config.method == "B0"
    assert config.seed == 21
    with pytest.raises((AttributeError, TypeError)):
        config.seed = 22


@pytest.mark.parametrize("field, value", [
    ("method", "P1"),
    ("scenario", "F01"),
    ("controller", "pd"),
    ("ordering", "shortest"),
])
def test_rejects_unknown_enum_values(tmp_path, field, value):
    with pytest.raises(ValueError, match=field):
        load_demo_config(write_config(tmp_path, **{field: value}))


@pytest.mark.parametrize("seed", [0, 11, 20, 26])
def test_rejects_seeds_outside_development_and_final_pools(tmp_path, seed):
    with pytest.raises(ValueError, match="seed"):
        load_demo_config(write_config(tmp_path, seed=seed))


def test_accepts_final_evaluation_pool_seed(tmp_path):
    assert load_demo_config(write_config(tmp_path, seed=10)).seed == 10


@pytest.mark.parametrize("assets", [
    ["gauge_pipe_01", "gauge_pipe_02", "gauge_pump_01", "gauge_tank_01"],
    ["gauge_pipe_01"] * 6,
])
def test_rejects_insufficient_or_duplicate_mission_assets(tmp_path, assets):
    with pytest.raises(ValueError, match="mission_assets"):
        load_demo_config(write_config(tmp_path, mission_assets=assets))


def test_rejects_unknown_keys_and_missing_world(tmp_path):
    with pytest.raises(ValueError, match="unknown"):
        load_demo_config(write_config(tmp_path, unexpected=True))
    with pytest.raises(ValueError, match="world"):
        load_demo_config(write_config(tmp_path, world="src/nope.sdf"))
