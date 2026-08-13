#!/usr/bin/env python3
"""Mission asset ordering heuristics (P8-T04).

Pure Python, no ROS imports: unit-testable on any host (D-007 pattern).

Assumptions:
- The asset gauge pose (map_pose) is used as a proxy for the visit point;
  candidate viewpoints lie near the asset, so the proxy is adequate for
  mission-level ordering.
- Nearest-neighbour greedy is a heuristic: it is deterministic and often
  good, but NOT guaranteed to be globally optimal.
"""
import math

ORDERINGS = ("list", "greedy")


def asset_position(asset):
    """(x, y) of the asset's gauge pose in the map frame."""
    p = asset.map_pose.position
    return (p.x, p.y)


def total_path_length(assets, start_pose):
    """Sum of 2D Euclidean segment lengths start -> a0 -> a1 -> ..."""
    total = 0.0
    cx, cy = start_pose
    for a in assets:
        x, y = asset_position(a)
        total += math.hypot(x - cx, y - cy)
        cx, cy = x, y
    return total


def greedy_nearest_neighbor(assets, start_pose):
    """Order assets by repeatedly visiting the closest unvisited asset.

    Deterministic: strict '<' comparison keeps the original list order
    among equidistant candidates (stable ties).
    """
    remaining = list(assets)
    ordered = []
    cx, cy = start_pose
    while remaining:
        best_idx = 0
        best_d = math.inf
        for i, a in enumerate(remaining):
            x, y = asset_position(a)
            d = math.hypot(x - cx, y - cy)
            if d < best_d:
                best_d = d
                best_idx = i
        picked = remaining.pop(best_idx)
        ordered.append(picked)
        cx, cy = asset_position(picked)
    return ordered


def order_assets(assets, start_pose, strategy):
    """Order assets by strategy.

    'list'   - as given (declaration order); the default behaviour.
    'greedy' - nearest-neighbour from start_pose (heuristic, not optimal).
    """
    if strategy == "greedy":
        return greedy_nearest_neighbor(assets, start_pose)
    return list(assets)