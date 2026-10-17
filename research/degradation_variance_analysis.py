#!/usr/bin/env python3
"""Paired variance/sensitivity analysis for the degradation-mechanic prototype.

Reads research/data/degradation/*.jsonl (paired by seed), reports per-policy
outcome stats, paired effect sizes, win rates, detection latency curves,
and episode counts needed for 95% confidence verdicts (DESIGN §7 gates 2-3).
"""

import json
import math
import sys
from pathlib import Path

DATA = Path(sys.argv[1] if len(sys.argv) > 1
            else Path(__file__).resolve().parent / "data" / "degradation")
POLICIES = [
    "run_to_failure",
    "periodic_pm",
    "spc_reactive_b4",
    "spc_reactive_b8",
    "spc_reactive_b16",
]
METRICS = [
    "net_profit",
    "unplanned_downtime",
    "breakdowns_count",
    "completed_clean",
    "mean_detection_latency",
    "missed_detections",
    "pm_count",
]


def load(policy):
    p = DATA / f"{policy}.jsonl"
    if not p.exists():
        return {}
    recs = {}
    for line in p.read_text().splitlines():
        if line.strip():
            r = json.loads(line)
            recs[r["seed"]] = r
    return recs


def mean(xs):
    valid = [x for x in xs if x is not None]
    return sum(valid) / len(valid) if valid else 0.0


def stdev(xs):
    valid = [x for x in xs if x is not None]
    if len(valid) < 2:
        return 0.0
    m = mean(valid)
    return math.sqrt(sum((x - m) ** 2 for x in valid) / (len(valid) - 1))


def tinv975(df):
    return 1.96 if df >= 100 else {9: 2.26, 19: 2.09, 29: 2.04, 49: 2.01,
                                   99: 1.98}.get(min(df // 10 * 10, 99), 2.0)


def main():
    data = {p: load(p) for p in POLICIES}
    valid_policies = [p for p in POLICIES if data[p]]
    if len(valid_policies) < 2:
        print(f"[degradation_analysis] Need at least 2 policy datasets in {DATA}")
        return

    seeds = sorted(set.intersection(*(set(data[p]) for p in valid_policies)))
    n = len(seeds)
    print(f"Paired seeds: {n}\n")

    # Table 1: Per-policy summary
    print(f"{'Metric':<24}" + "".join(f"{p:>20}" for p in valid_policies))
    print(f"{'':<24}" + "".join(f"{'mean ± sd (min,max)':>20}" for _ in valid_policies))
    for m in METRICS:
        row = f"{m:<24}"
        for p in valid_policies:
            xs = [data[p][s][m] for s in seeds if data[p][s][m] is not None]
            if xs:
                row += f"{mean(xs):>10.1f} ±{stdev(xs):<4.1f}({min(xs):.0f},{max(xs):.0f})"
            else:
                row += f"{'N/A':>20}"
        print(row)

    # Table 2: Paired Comparisons against Run-to-Failure baseline
    print(f"\n{'Comparison vs Baseline':<32}{'Metric':<20}{'Δmean':>8}{'sd(Δ)':>8}"
          f"{'95% CI':>20}{'win%':>7}{'d_z':>7}{'n95':>7}")
    
    comparisons = [
        ("spc_reactive_b16", "run_to_failure"),
        ("spc_reactive_b8", "run_to_failure"),
        ("spc_reactive_b4", "run_to_failure"),
        ("spc_reactive_b8", "periodic_pm"),
        ("periodic_pm", "run_to_failure"),
    ]

    eval_metrics = ["net_profit", "unplanned_downtime", "breakdowns_count", "completed_clean"]

    for a, b in comparisons:
        if a not in valid_policies or b not in valid_policies:
            continue
        for m in eval_metrics:
            diffs = [data[a][s][m] - data[b][s][m] for s in seeds
                     if data[a][s][m] is not None and data[b][s][m] is not None]
            if not diffs:
                continue
            dm, ds = mean(diffs), stdev(diffs)
            df = len(diffs) - 1
            t = tinv975(df) if df > 0 else 2.0
            ci = (dm - t * ds / math.sqrt(len(diffs)),
                  dm + t * ds / math.sqrt(len(diffs))) if df > 0 else (dm, dm)
            better_positive = (m in ("net_profit", "completed_clean"))
            wins = (sum(1 for d in diffs if d > 0) if better_positive else sum(1 for d in diffs if d < 0)) / len(diffs) * 100
            dz = dm / ds if ds > 1e-9 else float("inf")
            n95 = math.ceil((1.96 * ds / abs(dm)) ** 2) if abs(dm) > 1e-9 and ds > 0 else 1
            print(f"{a+' vs '+b:<32}{m:<20}{dm:>8.1f}{ds:>8.1f}"
                  f"  [{ci[0]:7.1f},{ci[1]:7.1f}]{wins:>6.1f}{dz:>7.2f}{n95:>7}")

    # Table 3: Detection Latency vs Monitoring Budget Curve
    print("\nCUSUM Drift Detection Latency vs Sample Budget Curve:")
    print(f"{'Budget (probes/shift)':<24}{'Mean Latency (ticks)':<24}{'Missed Detections / Ep':<24}{'Net Profit ($)':<20}")
    for b_str in ["spc_reactive_b4", "spc_reactive_b8", "spc_reactive_b16"]:
        if b_str in valid_policies:
            latencies = [data[b_str][s]["mean_detection_latency"] for s in seeds if data[b_str][s]["mean_detection_latency"] is not None]
            missed = [data[b_str][s]["missed_detections"] for s in seeds]
            profit = [data[b_str][s]["net_profit"] for s in seeds]
            b_val = b_str.split("_b")[-1]
            print(f"  B = {b_val:<20} {mean(latencies):>8.1f} ± {stdev(latencies):<6.1f} {mean(missed):>12.2f} {mean(profit):>18.1f}")

    # Table 4: Variance Decomposition on Net Profit (Skill vs Scenario vs Residual)
    print("\nNet Profit Variance Decomposition (3-way: Policy x Scenario Seed):")
    core_pols = ["spc_reactive_b8", "run_to_failure", "periodic_pm"]
    if all(p in valid_policies for p in core_pols):
        m = "net_profit"
        grand = mean([data[p][s][m] for p in core_pols for s in seeds])
        ss_policy = len(seeds) * sum((mean([data[p][s][m] for s in seeds]) - grand) ** 2 for p in core_pols)
        ss_seed = sum((mean([data[p][s][m] for p in core_pols]) - grand) ** 2 for s in seeds) * len(core_pols)
        ss_res = sum((data[p][s][m] - grand) ** 2 for p in core_pols for s in seeds) - ss_policy - ss_seed
        tot = ss_policy + ss_seed + ss_res
        print(f"  Policy (Skill):   {ss_policy / tot:6.1%}")
        print(f"  Seed (Scenario):  {ss_seed / tot:6.1%}")
        print(f"  Residual (Noise): {ss_res / tot:6.1%}")


if __name__ == "__main__":
    main()
