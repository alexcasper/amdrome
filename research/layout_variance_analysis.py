#!/usr/bin/env python3
"""Paired variance/sensitivity analysis for the layout-mechanic prototype.

Reads research/data/{compact,clustered,scattered}.jsonl (paired by seed),
reports per-policy outcome stats, paired effect sizes, win rates, and the
episode count needed for a 95%-confidence verdict — the skill/noise
measurement called for by DESIGN.md §7 (gates 2-3 inputs).
"""

import json
import math
import sys
from pathlib import Path

DATA = Path(sys.argv[1] if len(sys.argv) > 1
            else Path(__file__).resolve().parent / "data")
POLICIES = ["compact", "clustered", "scattered"]
METRICS = ["completed", "cycle_mean", "wip_mean"]


def load(policy):
    recs = {}
    for line in (DATA / f"{policy}.jsonl").read_text().splitlines():
        r = json.loads(line)
        recs[r["seed"]] = r
    return recs


def mean(xs):
    return sum(xs) / len(xs)


def stdev(xs):
    m = mean(xs)
    return math.sqrt(sum((x - m) ** 2 for x in xs) / (len(xs) - 1))


def tinv975(df):
    """Rough two-sided 97.5% t quantile (normal approx w/ small-sample bump)."""
    return 1.96 if df >= 100 else {9: 2.26, 19: 2.09, 29: 2.04, 49: 2.01,
                                   99: 1.98}.get(min(df // 10 * 10, 99), 2.0)


def main():
    data = {p: load(p) for p in POLICIES}
    seeds = sorted(set.intersection(*(set(d) for d in data.values())))
    n = len(seeds)
    print(f"paired seeds: {n}\n")

    print(f"{'metric':<12}" + "".join(f"{p:>22}" for p in POLICIES))
    print(f"{'':<12}" + "".join(f"{'mean ± sd (min,max)':>22}" for _ in POLICIES))
    for m in METRICS:
        row = f"{m:<12}"
        for p in POLICIES:
            xs = [data[p][s][m] for s in seeds if data[p][s][m] is not None]
            row += f"{mean(xs):>10.2f} ±{stdev(xs):<5.2f}({min(xs):.0f},{max(xs):.0f})"
        print(row)

    print(f"\n{'pair':<24}{'metric':<12}{'Δmean':>8}{'sd(Δ)':>8}"
          f"{'95% CI':>20}{'win%':>7}{'d_z':>7}{'n95':>7}")
    for a, b in [("compact", "scattered"), ("compact", "clustered"),
                 ("clustered", "scattered")]:
        for m in METRICS:
            diffs = [data[a][s][m] - data[b][s][m] for s in seeds
                     if data[a][s][m] is not None and data[b][s][m] is not None]
            dm, ds = mean(diffs), stdev(diffs)
            t = tinv975(len(diffs) - 1)
            ci = (dm - t * ds / math.sqrt(len(diffs)),
                  dm + t * ds / math.sqrt(len(diffs)))
            wins = sum(1 for d in diffs if d > 0) / len(diffs) * 100
            dz = dm / ds if ds else float("inf")
            n95 = math.ceil((1.96 * ds / abs(dm)) ** 2) if dm else 9999
            better = "higher" if m == "completed" else "lower"
            print(f"{a+' - '+b:<24}{m:<12}{dm:>8.2f}{ds:>8.2f}"
                  f"  [{ci[0]:7.2f},{ci[1]:7.2f}]{wins:>6.1f}{dz:>7.2f}{n95:>7}")

    # variance decomposition for cycle_mean (the layout-sensitive KPI)
    m = "cycle_mean"
    grand = mean([data[p][s][m] for p in POLICIES for s in seeds])
    ss_policy = n * sum((mean([data[p][s][m] for s in seeds]) - grand) ** 2
                        for p in POLICIES)
    ss_seed = sum((mean([data[p][s][m] for p in POLICIES]) - grand) ** 2
                  for s in seeds) * len(POLICIES)
    ss_res = sum((data[p][s][m] - grand) ** 2 for p in POLICIES
                 for s in seeds) - ss_policy - ss_seed
    tot = ss_policy + ss_seed + ss_res
    print(f"\ncycle_mean variance decomposition (2-way, policy x seed):")
    print(f"  policy (skill)      {ss_policy / tot:6.1%}")
    print(f"  seed (scenario)     {ss_seed / tot:6.1%}")
    print(f"  residual (noise)    {ss_res / tot:6.1%}")

    # throughput check: is completed too bottleneck-dominated?
    m = "completed"
    for p in POLICIES:
        xs = [data[p][s][m] for s in seeds]
        print(f"completed {p:<10} mean {mean(xs):6.2f}  sd {stdev(xs):5.2f}  "
              f"cv {stdev(xs) / mean(xs):.3f}")


if __name__ == "__main__":
    main()
