#!/usr/bin/env python3
"""Paired variance/sensitivity analysis for the degradation-mechanic prototype.

Reads research/data/degradation/{run_to_failure,periodic_pm,spc_reactive}.jsonl
(paired by seed), reports per-policy outcome stats, paired effect sizes,
win rates, and episode counts needed for 95% confidence verdicts.
"""

import json
import math
import sys
from pathlib import Path

DATA = Path(sys.argv[1] if len(sys.argv) > 1
            else Path(__file__).resolve().parent / "data" / "degradation")
POLICIES = ["run_to_failure", "periodic_pm", "spc_reactive"]
METRICS = ["net_profit", "unplanned_downtime", "breakdowns_count", "completed_clean"]


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
    return sum(xs) / len(xs) if xs else 0.0


def stdev(xs):
    if len(xs) < 2:
        return 0.0
    m = mean(xs)
    return math.sqrt(sum((x - m) ** 2 for x in xs) / (len(xs) - 1))


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

    print(f"{'Metric':<20}" + "".join(f"{p:>24}" for p in valid_policies))
    print(f"{'':<20}" + "".join(f"{'mean ± sd (min,max)':>24}" for _ in valid_policies))
    for m in METRICS:
        row = f"{m:<20}"
        for p in valid_policies:
            xs = [data[p][s][m] for s in seeds if data[p][s][m] is not None]
            if xs:
                row += f"{mean(xs):>12.2f} ±{stdev(xs):<5.2f}({min(xs):.0f},{max(xs):.0f})"
            else:
                row += f"{'N/A':>24}"
        print(row)

    print(f"\n{'Comparison':<32}{'Metric':<20}{'Δmean':>8}{'sd(Δ)':>8}"
          f"{'95% CI':>20}{'win%':>7}{'d_z':>7}{'n95':>7}")
    pairs = [("spc_reactive", "run_to_failure"),
             ("periodic_pm", "run_to_failure"),
             ("spc_reactive", "periodic_pm")]

    for a, b in pairs:
        if a not in valid_policies or b not in valid_policies:
            continue
        for m in METRICS:
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
            print(f"{a+' vs '+b:<32}{m:<20}{dm:>8.2f}{ds:>8.2f}"
                  f"  [{ci[0]:7.1f},{ci[1]:7.1f}]{wins:>6.1f}{dz:>7.2f}{n95:>7}")


if __name__ == "__main__":
    main()
