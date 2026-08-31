"""Validated configuration for the reproducible SimInspect-X demo."""
from dataclasses import dataclass
from pathlib import Path
from typing import Final

import yaml


_REPOSITORY_ROOT: Final = Path(__file__).resolve().parents[3]
_REQUIRED_KEYS: Final = frozenset({
    "world", "mission_assets", "ordering", "method", "controller", "scenario",
    "seed", "readiness_timeout_s", "mission_timeout_s",
})
_ORDERINGS: Final = frozenset({"list", "greedy"})
_METHODS: Final = frozenset({"B0", "P2"})
_CONTROLLERS: Final = frozenset({"pid", "mpc"})
_SCENARIOS: Final = frozenset({"F00", "F06", "F07"})


@dataclass(frozen=True)
class DemoConfig:
    world: Path
    mission_assets: tuple[str, ...]
    ordering: str
    method: str
    controller: str
    scenario: str
    seed: int
    readiness_timeout_s: float
    mission_timeout_s: float


def _require_choice(data: dict, key: str, choices: frozenset[str]) -> str:
    value = data.get(key)
    if value not in choices:
        raise ValueError(f"{key} must be one of {sorted(choices)}")
    return value


def _positive_number(data: dict, key: str) -> float:
    value = data.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
        raise ValueError(f"{key} must be a positive number")
    return float(value)


def load_demo_config(path: Path) -> DemoConfig:
    """Load a strict, repository-relative demo configuration."""
    with Path(path).open(encoding="utf-8") as stream:
        data = yaml.safe_load(stream)
    if not isinstance(data, dict):
        raise ValueError("demo config must be a mapping")

    unknown = set(data) - _REQUIRED_KEYS
    missing = _REQUIRED_KEYS - set(data)
    if unknown:
        raise ValueError(f"unknown demo config keys: {sorted(unknown)}")
    if missing:
        raise ValueError(f"missing demo config keys: {sorted(missing)}")

    world_value = data["world"]
    if not isinstance(world_value, str) or not world_value:
        raise ValueError("world must be a non-empty repository-relative path")
    world_candidate = Path(world_value)
    if world_candidate.is_absolute():
        raise ValueError("world must be repository-relative")

    assets = data["mission_assets"]
    if (not isinstance(assets, list) or len(assets) < 5 or
            any(not isinstance(asset, str) or not asset for asset in assets) or
            len(set(assets)) != len(assets)):
        raise ValueError("mission_assets must contain at least five unique asset IDs")

    ordering = _require_choice(data, "ordering", _ORDERINGS)
    method = _require_choice(data, "method", _METHODS)
    controller = _require_choice(data, "controller", _CONTROLLERS)
    scenario = _require_choice(data, "scenario", _SCENARIOS)

    seed = data["seed"]
    if isinstance(seed, bool) or not isinstance(seed, int) or not (1 <= seed <= 10 or 21 <= seed <= 25):
        raise ValueError("seed must be in final pool 1-10 or development pool 21-25")

    readiness_timeout_s = _positive_number(data, "readiness_timeout_s")
    mission_timeout_s = _positive_number(data, "mission_timeout_s")

    world = (_REPOSITORY_ROOT / world_candidate).resolve()
    if not world.is_file():
        raise ValueError(f"world does not exist: {world_value}")

    return DemoConfig(
        world=world,
        mission_assets=tuple(assets),
        ordering=ordering,
        method=method,
        controller=controller,
        scenario=scenario,
        seed=seed,
        readiness_timeout_s=readiness_timeout_s,
        mission_timeout_s=mission_timeout_s,
    )
