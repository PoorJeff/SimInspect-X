#!/usr/bin/env python3
"""Consolidated analysis core (P9-T04).

Pure Python, no ROS imports: unit-testable on any host (D-007 pattern).
Uses numpy/scipy for statistics (declared in package.xml).

Honesty contract (docs/16): every figure must be regenerated from raw trial
files. Metrics absent from the records are reported as None (JSON null) /
"insufficient_data" and never invented.
"""
import numpy as np
from scipy import stats

ALPHA = 0.05
TOLERANCE_FRACTION = 0.05  # docs/13: within-tolerance = |err| <= 5% full-scale


def group_trials(records):
    """Group records by (experiment, method, scenario)."""
    groups = {}
    for rec in records:
        exp = rec.get("experiment", "unknown")
        method = rec.get("method", "unknown")
        scenario = rec.get("scenario", "unknown")
        groups.setdefault(exp, {}).setdefault(method, {}).setdefault(
            scenario, []).append(rec)
    return groups


def success_rate(records):
    """Fraction of records with result completed/success; None if empty."""
    if not records:
        return None
    n_ok = sum(1 for r in records
               if r.get("result") in ("completed", "success"))
    return n_ok / len(records)


def mae_rmse_median(errors):
    """docs/13: MAE, RMSE and median absolute error; None if no data."""
    if not errors:
        return None
    e = np.asarray(errors, dtype=float)
    return {
        "mae": float(np.mean(np.abs(e))),
        "rmse": float(np.sqrt(np.mean(e ** 2))),
        "median": float(np.median(np.abs(e))),
    }


def within_tolerance_rate(errors, full_scale_range):
    """docs/13: fraction of |err| <= 5% of full-scale range."""
    if not errors or full_scale_range is None:
        return None
    tol = TOLERANCE_FRACTION * full_scale_range
    e = np.asarray(errors, dtype=float)
    return float(np.mean(np.abs(e) <= tol))


def mean_of(records, metric_key, sub="metrics"):
    """Mean of a numeric metric across records; None if any value missing."""
    vals = []
    for r in records:
        v = (r.get(sub) or {}).get(metric_key)
        if v is None:
            return None
        vals.append(float(v))
    return float(np.mean(vals)) if vals else None


def extra_distance(base_records, method_records):
    """docs/13: mean extra path length of method vs baseline; None if missing."""
    b = mean_of(base_records, "path_length_m")
    m = mean_of(method_records, "path_length_m")
    if b is None or m is None:
        return None
    return m - b


def paired_test(pairs_a, pairs_b, alpha=ALPHA):
    """Paired t-test (scipy ttest_rel) with Wilcoxon alternative.

    Requires >= 3 paired samples for the t-test (statistical honesty);
    fewer pairs -> insufficient_pairs and no significance claim.
    """
    a = [float(x) for x in pairs_a if x is not None]
    b = [float(x) for x in pairs_b if x is not None]
    n = min(len(a), len(b))
    if n < 3:
        return {"insufficient_pairs": True, "n": n,
                "alpha": alpha, "significant": None}
    a, b = a[:n], b[:n]
    t_stat, p = stats.ttest_rel(a, b)
    if not np.isfinite(p):
        # zero-variance / identical pairs: no meaningful test result
        return {"n": n, "alpha": alpha, "insufficient_pairs": False,
                "t_statistic": None, "p_value": None,
                "significant": None, "wilcoxon_statistic": None,
                "wilcoxon_p": None}
    try:
        w_stat, w_p = stats.wilcoxon(a, b)
    except ValueError:
        w_stat, w_p = None, None
    return {
        "n": n,
        "alpha": alpha,
        "t_statistic": float(t_stat),
        "p_value": float(p),
        "significant": bool(p < alpha),
        "wilcoxon_statistic": float(w_stat) if w_stat is not None else None,
        "wilcoxon_p": float(w_p) if w_p is not None else None,
    }


def paired_values(grouped, exp, method_a, method_b, metric_key, sub="metrics"):
    """Per-(scenario, seed) paired metric values across two methods."""
    exp_g = grouped.get(exp, {})
    a_scen = exp_g.get(method_a, {})
    b_scen = exp_g.get(method_b, {})
    a_vals, b_vals = [], []
    for scen in sorted(set(a_scen) & set(b_scen)):
        a_by_seed = {r.get("seed"): (r.get(sub) or {}).get(metric_key)
                     for r in a_scen[scen]}
        b_by_seed = {r.get("seed"): (r.get(sub) or {}).get(metric_key)
                     for r in b_scen[scen]}
        for seed in sorted(set(a_by_seed) & set(b_by_seed)):
            av, bv = a_by_seed[seed], b_by_seed[seed]
            if av is not None and bv is not None:
                a_vals.append(float(av))
                b_vals.append(float(bv))
    return a_vals, b_vals


def build_summary(grouped):
    """Per-experiment summary tables + E4 trade-off + H1/H4 paired tests.

    Missing metrics are reported as None (JSON null); empty groups get
    status "insufficient_data". No values are ever invented.
    """
    summary = {"alpha": ALPHA, "experiments": {}}
    scalar_keys = ("final_position_error", "final_yaw_error", "effort_abs",
                   "effort_sq", "settling_time_s", "constraint_violations",
                   "path_length_m", "extra_path_m", "gauge_mae",
                   "valid_read_rate", "recovery_count")

    for exp in sorted(grouped):
        exp_summary = {"methods": {}}
        for method in sorted(grouped[exp]):
            recs = [r for sc in grouped[exp][method].values() for r in sc]
            msum = {
                "n": len(recs),
                "success_rate": success_rate(recs),
                "metrics": {k: mean_of(recs, k) for k in scalar_keys},
            }
            if not recs:
                msum["status"] = "insufficient_data"
            exp_summary["methods"][method] = msum
        summary["experiments"][exp] = exp_summary

    # E4 trade-off vs B0 (docs/13: extra distance vs success gain)
    summary["e4_tradeoff"] = {}
    e4 = summary["experiments"].get("E4", {}).get("methods", {})
    b0_rate = (e4.get("B0") or {}).get("success_rate")
    b0_dist = (e4.get("B0") or {}).get("metrics", {}).get("path_length_m")
    for m in ("P1", "P2"):
        mm = e4.get(m)
        if not mm:
            summary["e4_tradeoff"][m] = "insufficient_data"
            continue
        rate = mm.get("success_rate")
        dist = mm.get("metrics", {}).get("path_length_m")
        summary["e4_tradeoff"][m] = {
            "delta_success": (rate - b0_rate)
            if (rate is not None and b0_rate is not None) else None,
            "delta_distance": (dist - b0_dist)
            if (dist is not None and b0_dist is not None) else None,
        }

    # H1 (docs/01: unadjusted p-values) + H4 paired tests
    tests = {}
    for hid, (exp, ma, mb, key, alpha) in {
        # docs/01: H1 reports unadjusted p-values (alpha 0.05);
        # H4 Tier-1 uses Bonferroni correction (4 conditions -> 0.0125).
        "H1_B0_vs_P1": ("E4", "B0", "P1", "valid_read_rate", ALPHA),
        "H1_B0_vs_P2": ("E4", "B0", "P2", "valid_read_rate", ALPHA),
        "H4_PID_vs_MPC_pos": ("E5", "PID", "MPC",
                               "final_position_error", 0.0125),
    }.items():
        a, b = paired_values(grouped, exp, ma, mb, key)
        tests[hid] = paired_test(a, b, alpha=alpha)
    summary["hypothesis_tests"] = tests

    return summary