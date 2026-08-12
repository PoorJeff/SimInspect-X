#!/usr/bin/env python3
"""Plot PID vs MPC comparison from precision_benchmark results JSON."""
import json, sys, os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def load_results(path):
    with open(path) as f:
        return json.load(f)


def plot_comparison(data, out_dir="."):
    summary = data["summary"]
    conditions = list(summary.keys())
    methods = data["methods"]
    n_cond = len(conditions)
    x = np.arange(n_cond)
    width = 0.35

    # ---- Figure 1: Bar chart — final errors + settling time ----
    fig, axes = plt.subplots(1, 3, figsize=(16, 5))

    for m_idx, method in enumerate(methods):
        pos = [summary[c][method]["mean_final_pos_err"] for c in conditions]
        yaw = [summary[c][method]["mean_final_yaw_err"] for c in conditions]
        settle = [summary[c][method]["mean_settling_s"] for c in conditions]
        offset = width * (m_idx - 0.5)
        axes[0].bar(x + offset, pos, width, label=method.upper())
        axes[1].bar(x + offset, yaw, width, label=method.upper())
        axes[2].bar(x + offset, settle, width, label=method.upper())

    axes[0].set_title("Final Position Error [m]")
    axes[1].set_title("Final Yaw Error [rad]")
    axes[2].set_title("Settling Time [s]")
    for ax in axes:
        ax.set_xticks(x)
        ax.set_xticklabels([c.replace("E5_", "") for c in conditions], rotation=30, ha="right")
        ax.legend()
        ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(out_dir, "precision_errors.png"), dpi=150)
    plt.close(fig)

    # ---- Figure 2: Bar chart — control effort ----
    fig, axes = plt.subplots(1, 3, figsize=(16, 5))

    for m_idx, method in enumerate(methods):
        abs_eff = [summary[c][method]["mean_effort_abs"] for c in conditions]
        sq_eff = [summary[c][method]["mean_effort_sq"] for c in conditions]
        viol = [summary[c][method]["mean_violations"] for c in conditions]
        offset = width * (m_idx - 0.5)
        axes[0].bar(x + offset, abs_eff, width, label=method.upper())
        axes[1].bar(x + offset, sq_eff, width, label=method.upper())
        axes[2].bar(x + offset, viol, width, label=method.upper())

    axes[0].set_title("Control Effort (abs)")
    axes[1].set_title("Control Effort (sq)")
    axes[2].set_title("Constraint Violations")
    for ax in axes:
        ax.set_xticks(x)
        ax.set_xticklabels([c.replace("E5_", "") for c in conditions], rotation=30, ha="right")
        ax.legend()
        ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(out_dir, "precision_effort.png"), dpi=150)
    plt.close(fig)

    # ---- Figure 3: Scatter — settling time vs effort ----
    fig, ax = plt.subplots(figsize=(8, 6))
    colors = {"pid": "#2196F3", "mpc": "#FF5722"}
    for method in methods:
        pts = []
        for c in conditions:
            s = summary[c][method]
            pts.append((s["mean_settling_s"], s["mean_effort_abs"]))
        xs, ys = zip(*pts)
        ax.scatter(xs, ys, c=colors[method], label=method.upper(), s=80)
        for i, c in enumerate(conditions):
            ax.annotate(c.replace("E5_", ""), (xs[i], ys[i]),
                        textcoords="offset points", xytext=(5, 5), fontsize=8)
    ax.set_xlabel("Settling Time [s]")
    ax.set_ylabel("Control Effort (abs)")
    ax.set_title("PID vs MPC: Efficiency Trade-off")
    ax.legend()
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(out_dir, "precision_scatter.png"), dpi=150)
    plt.close(fig)

    print(f"Plots saved to {out_dir}/")


def main():
    if len(sys.argv) < 2:
        path = os.path.join("results", "precision_results.json")
    else:
        path = sys.argv[1]
    out = os.path.dirname(path) or "."
    data = load_results(path)
    plot_comparison(data, out)


if __name__ == "__main__":
    main()