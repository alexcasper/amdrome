#!/usr/bin/env python3
"""Analyze verify_ab.py shards: paired relative reductions vs a reference arm.

Relative reduction = 1 - mean(arm)/mean(ref), with a paired seed-bootstrap
95% CI (resample seeds, recompute the ratio of means). This is the quantity
a ">70% downtime reduction" claim asserts; mean-of-per-episode-ratios is
not used (undefined when ref=0 and dominated by small denominators).

  python3 demo/benchmark/verify_analyze.py research/data/abverify/*.jsonl \
      --ref blind [--md out.md]
"""

import argparse
import json
import random
from collections import defaultdict

METRICS = [
    ("unplanned_downtime", "unplanned downtime (ticks)", "down"),
    ("total_downtime", "total downtime incl. PM (ticks)", "down"),
    ("breakdowns", "breakdowns", "down"),
    ("completed_defective", "defect escapes (units)", "down"),
    ("defect_ppm", "defect PPM", "down"),
    ("net_profit", "net profit ($)", "up"),
    ("completed_clean", "clean units shipped", "up"),
]
B = 2000


def load(paths):
    rows = defaultdict(dict)          # seed -> arm -> row
    for p in paths:
        with open(p) as f:
            for line in f:
                line = line.strip()
                if not line or not line.startswith("{"):
                    continue
                r = json.loads(line)
                if "arm" in r:
                    rows[r["seed"]][r["arm"]] = r
    return rows


def mean(xs):
    return sum(xs) / len(xs) if xs else float("nan")


def rel_ci(a, b, rng):
    n = len(a)
    vals = []
    for _ in range(B):
        idx = [rng.randrange(n) for _ in range(n)]
        mb = mean([b[i] for i in idx])
        ma = mean([a[i] for i in idx])
        vals.append(1 - ma / mb if mb else 0.0)
    vals.sort()
    return vals[int(0.025 * B)], vals[int(0.975 * B) - 1]


def analyze(rows, ref):
    arms = sorted({a for d in rows.values() for a in d})
    out = {}
    for arm in arms:
        if arm == ref:
            continue
        seeds = sorted(s for s, d in rows.items() if arm in d and ref in d)
        if not seeds:
            continue
        rng = random.Random(777)
        res = {"n": len(seeds)}
        for key, _, direction in METRICS:
            a = [rows[s][arm][key] for s in seeds]
            b = [rows[s][ref][key] for s in seeds]
            ma, mb = mean(a), mean(b)
            lo, hi = rel_ci(a, b, rng)
            d = [x - y for x, y in zip(a, b)]
            res[key] = {"arm": round(ma, 2), "ref": round(mb, 2),
                        "delta": round(ma - mb, 2),
                        "rel_red": round(1 - ma / mb, 4) if mb else None,
                        "rel_ci": [round(lo, 4), round(hi, 4)],
                        "win": round(mean([
                            1.0 if (x < 0 if direction == "down" else x > 0)
                            else 0.0 for x in d]), 3)}
        h0 = [rows[s][arm]["bd_h0_share"] for s in seeds]
        res["h0_breakdowns"] = round(mean(h0), 3)
        res["planned_downtime"] = round(
            mean([rows[s][arm]["planned_downtime"] for s in seeds]), 2)
        res["pm_count"] = round(mean([rows[s][arm]["pm_count"]
                                      for s in seeds]), 2)
        out[arm] = res
    refseeds = sorted(s for s, d in rows.items() if ref in d)
    out["_ref"] = {
        "arm": ref, "n": len(refseeds),
        "h0_breakdowns": round(mean([rows[s][ref]["bd_h0_share"]
                                     for s in refseeds]), 3),
        "breakdowns": round(mean([rows[s][ref]["breakdowns"]
                                  for s in refseeds]), 3),
    }
    return out


def to_md(out, ref):
    lines = [f"Reference arm: `{ref}` (n={out['_ref']['n']} seeds; "
             f"{out['_ref']['breakdowns']} breakdowns/ep, of which "
             f"{out['_ref']['h0_breakdowns']} expected from the "
             f"wear-independent H0 floor).", "",
             "| arm | n | unplanned DT red. [95% CI] | total DT red. | "
             "breakdowns red. | escapes red. [95% CI] | Δ net $/ep | "
             "PM/ep |",
             "|---|---|---|---|---|---|---|---|"]
    for arm, r in out.items():
        if arm.startswith("_"):
            continue

        def pct(k, ci=False):
            m = r[k]
            if m["rel_red"] is None:
                return "n/a"
            s = f"{100 * m['rel_red']:.1f}%"
            if ci:
                s += (f" [{100 * m['rel_ci'][0]:.1f}, "
                      f"{100 * m['rel_ci'][1]:.1f}]")
            return s
        lines.append(
            f"| {arm} | {r['n']} | {pct('unplanned_downtime', True)} | "
            f"{pct('total_downtime')} | {pct('breakdowns')} | "
            f"{pct('completed_defective', True)} | "
            f"{r['net_profit']['delta']:+.0f} | {r['pm_count']} |")
    return "\n".join(lines) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("paths", nargs="+")
    ap.add_argument("--ref", default="blind")
    ap.add_argument("--md", default=None)
    ap.add_argument("--json", default=None)
    args = ap.parse_args()
    rows = load(args.paths)
    out = analyze(rows, args.ref)
    md = to_md(out, args.ref)
    print(md)
    if args.md:
        with open(args.md, "w") as f:
            f.write(md)
    if args.json:
        with open(args.json, "w") as f:
            json.dump(out, f, indent=1)


if __name__ == "__main__":
    main()
