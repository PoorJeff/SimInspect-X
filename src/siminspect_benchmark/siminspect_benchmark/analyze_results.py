#!/usr/bin/env python3
"""Consolidated analysis over experiments/raw (P9-T04).

Walks experiments/raw/<experiment>/<commit>/<method>/<scenario>/seed_XXXX.json
(docs/16 layout), computes per-experiment statistics and writes
results/analysis_summary.json. Missing metrics are reported honestly.
"""
import argparse
import json
import os
import re

try:
    from siminspect_benchmark.analysis_core import group_trials, build_summary
except ImportError:
    from analysis_core import group_trials, build_summary

_EXPERIMENT_RE = re.compile(r"^E[1-6]_[a-z0-9_]+$")


def collect_records(root):
    """Collect all trial JSONs under the docs/16 raw directory layout."""
    records = []
    if not os.path.isdir(root):
        return records
    for exp_dir in sorted(os.listdir(root)):
        exp_path = os.path.join(root, exp_dir)
        if not os.path.isdir(exp_path) or not _EXPERIMENT_RE.match(exp_dir):
            continue
        for commit in sorted(os.listdir(exp_path)):
            commit_path = os.path.join(exp_path, commit)
            if not os.path.isdir(commit_path):
                continue
            for method in sorted(os.listdir(commit_path)):
                method_path = os.path.join(commit_path, method)
                if not os.path.isdir(method_path):
                    continue
                for scenario in sorted(os.listdir(method_path)):
                    scen_path = os.path.join(method_path, scenario)
                    if not os.path.isdir(scen_path):
                        continue
                    for fname in sorted(os.listdir(scen_path)):
                        if not fname.endswith(".json"):
                            continue
                        with open(os.path.join(scen_path, fname),
                                  encoding="utf-8") as f:
                            rec = json.load(f)
                        rec.setdefault("experiment",
                                       exp_dir.split("_")[0])  # E4_viewpoint_policy -> E4
                        rec.setdefault("method", method)
                        rec.setdefault("scenario", scenario)
                        records.append(rec)
    return records


def main():
    ap = argparse.ArgumentParser(description="Consolidated analysis (P9-T04)")
    ap.add_argument("--root", default="experiments/raw")
    ap.add_argument("--output", default="results/analysis_summary.json")
    args = ap.parse_args()

    records = collect_records(args.root)
    print(f"Collected {len(records)} trial records from {args.root}")
    if not records:
        summary = {"alpha": 0.05, "experiments": {}, "e4_tradeoff": {},
                   "hypothesis_tests": {}, "n_records": 0}
    else:
        summary = build_summary(group_trials(records))
        summary["n_records"] = len(records)
        for exp, es in summary["experiments"].items():
            print(f"{exp}: methods={list(es['methods'].keys())}")
        for hid, t in summary["hypothesis_tests"].items():
            if t.get("insufficient_pairs"):
                print(f"{hid}: insufficient_pairs (n={t.get('n')})")
            else:
                print(f"{hid}: n={t.get('n')} p={t.get('p_value')} "
                      f"significant={t.get('significant')}")

    out_dir = os.path.dirname(args.output) or "."
    os.makedirs(out_dir, exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    print(f"Summary written to {args.output}")


if __name__ == "__main__":
    main()