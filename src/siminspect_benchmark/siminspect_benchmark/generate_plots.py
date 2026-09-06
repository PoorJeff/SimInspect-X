#!/usr/bin/env python3
"""Generate analysis plots from the summary JSON (P9-T04).

Headless (Agg). Every figure is regenerated from raw-derived summaries
(docs/16). Missing data -> warn and skip, never invent.
"""
import argparse
import json
import os
import warnings

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402


def make_plots(summary, outdir):
    """Create the four standard figures; returns the list of file names."""
    made = []
    os.makedirs(outdir, exist_ok=True)

    def path(name):
        return os.path.join(outdir, name)

    def skip(name):
        warnings.warn(f"skip {name}: insufficient data")

    # 1) E4 trade-off: delta_distance vs delta_success per method
    trade = summary.get("e4_tradeoff", {})
    pts = {}
    for m, v in trade.items():
        if isinstance(v, dict) and v.get("delta_success") is not None \
                and v.get("delta_distance") is not None:
            pts[m] = (v["delta_success"], v["delta_distance"])
    if pts:
        fig, ax = plt.subplots()
        ax.scatter([p[0] for p in pts.values()], [p[1] for p in pts.values()])
        for m, (x, y) in pts.items():
            ax.annotate(m, (x, y))
        ax.set_xlabel("delta success rate (vs B0)")
        ax.set_ylabel("delta distance m (vs B0)")
        ax.set_title("E4 viewpoint policy trade-off")
        fig.savefig(path("e4_tradeoff.png"))
        plt.close(fig)
        made.append("e4_tradeoff.png")
    else:
        skip("e4_tradeoff")

    # 2) success rate comparison per method
    rates = {}
    for exp, es in summary.get("experiments", {}).items():
        for method, ms in es.get("methods", {}).items():
            if ms.get("success_rate") is not None:
                rates[f"{exp}/{method}"] = ms["success_rate"]
    if rates:
        fig, ax = plt.subplots()
        ax.bar(list(rates.keys()), list(rates.values()))
        ax.set_ylabel("success rate")
        ax.set_title("Method success rates")
        plt.xticks(rotation=45, ha="right")
        fig.tight_layout()
        fig.savefig(path("method_comparison.png"))
        plt.close(fig)
        made.append("method_comparison.png")
    else:
        skip("method_comparison")

    # 3) ablation delta vs P2 baseline
    e4 = summary.get("experiments", {}).get("E4", {}).get("methods", {})
    p2_rate = (e4.get("P2") or {}).get("success_rate")
    ab_delta = {}
    for m in ("P2_A1", "P2_A2", "P2_A3", "P2_A4"):
        ms = e4.get(m)
        if ms and ms.get("success_rate") is not None and p2_rate is not None:
            ab_delta[m.replace("P2_", "A")] = ms["success_rate"] - p2_rate
    if ab_delta:
        fig, ax = plt.subplots()
        ax.bar(list(ab_delta.keys()), list(ab_delta.values()))
        ax.set_ylabel("delta success rate (vs P2)")
        ax.set_title("Ablations A1-A4 vs P2")
        fig.savefig(path("ablation_delta.png"))
        plt.close(fig)
        made.append("ablation_delta.png")
    else:
        skip("ablation_delta")

    # 4) E5 PID vs MPC metric bars
    e5 = summary.get("experiments", {}).get("E5", {}).get("methods", {})
    keys = ("final_position_error", "effort_abs", "settling_time_s",
            "constraint_violations")
    pid = e5.get("PID") or {}
    mpc = e5.get("MPC") or {}
    pairs = {}
    for k in keys:
        a = pid.get("metrics", {}).get(k)
        b = mpc.get("metrics", {}).get(k)
        if a is not None and b is not None:
            pairs[k] = (a, b)
    if pairs:
        fig, ax = plt.subplots()
        x = np.arange(len(pairs))
        w = 0.35
        ax.bar(x - w / 2, [v[0] for v in pairs.values()], w, label="PID")
        ax.bar(x + w / 2, [v[1] for v in pairs.values()], w, label="MPC")
        ax.set_xticks(x)
        ax.set_xticklabels(list(pairs.keys()), rotation=15)
        ax.legend()
        ax.set_title("E5 PID vs MPC")
        fig.tight_layout()
        fig.savefig(path("e5_pid_mpc.png"))
        plt.close(fig)
        made.append("e5_pid_mpc.png")
    else:
        skip("e5_pid_mpc")

    return made


def main():
    ap = argparse.ArgumentParser(description="Generate plots (P9-T04)")
    ap.add_argument("--summary", default="results/analysis_summary.json")
    ap.add_argument("--outdir", default="results/plots")
    args = ap.parse_args()

    with open(args.summary, encoding="utf-8") as f:
        summary = json.load(f)
    made = make_plots(summary, args.outdir)
    for name in made:
        print(f"wrote {os.path.join(args.outdir, name)}")
    if not made:
        print("No plots generated (insufficient data).")


if __name__ == "__main__":
    main()