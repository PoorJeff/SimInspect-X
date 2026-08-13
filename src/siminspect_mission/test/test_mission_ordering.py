"""Test mission asset ordering heuristics (P8-T04).

Pure Python, no ROS imports required.
"""
import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "siminspect_mission"))

from mission_ordering import (  # noqa: E402
    ORDERINGS, asset_position, greedy_nearest_neighbor,
    order_assets, total_path_length,
)


def _asset(aid, x, y):
    return SimpleNamespace(
        id=aid,
        map_pose=SimpleNamespace(position=SimpleNamespace(x=x, y=y)),
    )


def test_orderings_enum():
    assert ORDERINGS == ("list", "greedy")


def test_list_strategy_returns_as_given():
    a = [_asset("a1", 10, 0), _asset("a2", 1, 0), _asset("a3", 9, 0)]
    out = order_assets(a, (0.0, 0.0), "list")
    assert [x.id for x in out] == ["a1", "a2", "a3"]
    assert out[0] is a[0]  # same objects, just re-ordered


def test_greedy_empty_list():
    assert greedy_nearest_neighbor([], (0.0, 0.0)) == []
    assert total_path_length([], (0.0, 0.0)) == 0.0


def test_greedy_single_asset():
    a = [_asset("only", 5, 5)]
    out = greedy_nearest_neighbor(a, (0.0, 0.0))
    assert [x.id for x in out] == ["only"]


def test_greedy_beats_zigzag_list_order():
    """Fixture where declaration order zigzags; greedy must be shorter."""
    assets = [_asset("a1", 10, 0), _asset("a2", 1, 0), _asset("a3", 9, 0)]
    start = (0.0, 0.0)
    list_path = total_path_length(assets, start)
    ordered = greedy_nearest_neighbor(assets, start)
    greedy_path = total_path_length(ordered, start)
    assert [x.id for x in ordered] == ["a2", "a3", "a1"]
    assert greedy_path < list_path


def test_greedy_deterministic_and_stable_ties():
    """Same input twice -> same output; equidistant assets keep list order."""
    a = [_asset("a1", 1, 0), _asset("a2", 0, 1)]  # both at distance 1
    first = greedy_nearest_neighbor(a, (0.0, 0.0))
    second = greedy_nearest_neighbor(a, (0.0, 0.0))
    assert [x.id for x in first] == [x.id for x in second]
    assert [x.id for x in first] == ["a1", "a2"]  # stable tie: original order


def test_total_path_length_arithmetic():
    assets = [_asset("a1", 3, 0), _asset("a2", 3, 4)]
    assert total_path_length(assets, (0.0, 0.0)) == 7.0  # 3 + 4


def test_asset_position():
    assert asset_position(_asset("a1", 4.0, 1.8)) == (4.0, 1.8)