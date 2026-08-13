#!/usr/bin/env python3
"""Render the system architecture diagram (P10-T03).

Headless matplotlib (Agg). This script is the source of truth for
architecture.png / architecture.svg; the structure follows
docs/03_SYSTEM_ARCHITECTURE.md and docs/06_ROS_TF_CONTRACT.md.
"""
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

HERE = os.path.dirname(os.path.abspath(__file__))

# 8-layer pipeline, top -> bottom: (title, detail)
LAYERS = [
    ("Gazebo Sensors", "LiDAR / IMU / RGB camera / wheel odometry"),
    ("State Estimation", "EKF (robot_localization) + SLAM Toolbox"),
    ("Navigation", "Nav2: Navfn global + MPPI local, recovery"),
    ("Viewpoint Planning",
     "candidate generation + quality scoring\nB0 / B1 / P1 / P2 selectors"),
    ("Precision Control", "handoff + PID | constrained MPC (OSQP)"),
    ("Gauge Vision", "detect -> rectify -> read -> confidence proxy"),
    ("Mission Executive",
     "multi-asset SM, bounded retries,\nreport v1.0, ordering"),
    ("Benchmark / Firewall",
     "fault injection F00-F11, seeds,\nground truth isolated"),
]

TF_CHAIN = ["map", "odom", "base_link"]
TF_LEAVES = ["laser_link", "imu_link", "camera_link"]


def main():
    fig, ax = plt.subplots(figsize=(14, 9))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis("off")
    ax.text(50, 98, "SimInspect-X System Architecture", ha="center",
            fontsize=15, fontweight="bold")

    # ---- left: 8-layer pipeline ----
    x0, x1 = 5, 44
    top, h, gap = 92, 10, 1.6
    cx = (x0 + x1) / 2
    bottoms = []
    for i, (title, detail) in enumerate(LAYERS):
        y_top = top - i * (h + gap)
        y_bot = y_top - h
        box = FancyBboxPatch((x0, y_bot), x1 - x0, h,
                             boxstyle="round,pad=0.4",
                             facecolor="#eef3fa", edgecolor="#2b5b8a",
                             linewidth=1.2)
        ax.add_patch(box)
        ax.text(cx, y_bot + h * 0.68, title, ha="center", va="center",
                fontsize=11, fontweight="bold")
        ax.text(cx, y_bot + h * 0.26, detail, ha="center", va="center",
                fontsize=8)
        bottoms.append(y_bot)
    for i in range(len(LAYERS) - 1):
        y_from = bottoms[i]
        y_to = top - (i + 1) * (h + gap)
        ax.annotate("", xy=(cx, y_to), xytext=(cx, y_from),
                    arrowprops=dict(arrowstyle="->", color="#2b5b8a",
                                    lw=1.4))

    # ---- right top: TF tree ----
    tf_x = 62
    chain_ys = {"map": 92, "odom": 82, "base_link": 72}
    leaf_ys = {"laser_link": 66, "imu_link": 60, "camera_link": 54}
    for name, y in chain_ys.items():
        ax.add_patch(FancyBboxPatch((tf_x - 8, y - 3), 16, 6,
                                    boxstyle="round,pad=0.3",
                                    facecolor="#f5f0e6",
                                    edgecolor="#8a6d2b", linewidth=1.0))
        ax.text(tf_x, y, name, ha="center", va="center", fontsize=9)
    ax.annotate("", xy=(tf_x, chain_ys["odom"] + 3),
                xytext=(tf_x, chain_ys["map"] - 3),
                arrowprops=dict(arrowstyle="->", color="#8a6d2b"))
    ax.annotate("", xy=(tf_x, chain_ys["base_link"] + 3),
                xytext=(tf_x, chain_ys["odom"] - 3),
                arrowprops=dict(arrowstyle="->", color="#8a6d2b"))
    for name, y in leaf_ys.items():
        ax.add_patch(FancyBboxPatch((tf_x - 8, y - 2.5), 16, 5,
                                    boxstyle="round,pad=0.3",
                                    facecolor="#fdf6ee",
                                    edgecolor="#8a6d2b", linewidth=0.9))
        ax.text(tf_x, y, name, ha="center", va="center", fontsize=8)
        ax.annotate("", xy=(tf_x - 8, y), xytext=(tf_x - 3,
                    chain_ys["base_link"] - 1.5),
                    arrowprops=dict(arrowstyle="->", color="#8a6d2b",
                                    lw=0.9))
    ax.text(tf_x, 40, "TF tree\n(docs/06)", ha="center", va="center",
            fontsize=9, style="italic")

    # ---- right bottom: ground-truth firewall ----
    fx0, fy0, fx1, fy1 = 55, 6, 92, 26
    ax.add_patch(FancyBboxPatch((fx0, fy0), fx1 - fx0, fy1 - fy0,
                                boxstyle="round,pad=0.5",
                                facecolor="#fdeeee", edgecolor="#c0392b",
                                linestyle="--", linewidth=1.6))
    ax.text((fx0 + fx1) / 2, fy0 + 15,
            "/benchmark_ground_truth/*", ha="center", va="center",
            fontsize=11, fontweight="bold", color="#c0392b")
    ax.text((fx0 + fx1) / 2, fy0 + 7,
            "benchmark-only\n(L1 build gate + L2 rosgraph watchdog,\ndocs/06)",
            ha="center", va="center", fontsize=8.5, color="#7b241c")

    out_png = os.path.join(HERE, "architecture.png")
    out_svg = os.path.join(HERE, "architecture.svg")
    fig.savefig(out_png, dpi=150, bbox_inches="tight")
    fig.savefig(out_svg, bbox_inches="tight")
    plt.close(fig)
    print("wrote", out_png)
    print("wrote", out_svg)


if __name__ == "__main__":
    main()