#!/usr/bin/env python3
"""A/B benchmark: operator assistant ON vs OFF (bead amdrome-kwo).

Arm A = demo/assistant OperatorAssistant executing autonomously.
Arm B = blind baseline (run-to-failure, no monitoring, face-value bids).
Paired seeds: both arms see identical scenarios (same hyperprior + shared
flow stream) — differences are attributable to the assistant.

Metrics (hackathon-brief rubric): defect escapes / PPM (quality),
unplanned downtime (downtime %), net profit (cost), mean time-to-detection
(assistant arm's own drift detector; blind arm has no monitoring).

Stateless CLI, pure stdlib — run on ARM fleet hosts:
  python3 demo/benchmark/run_ab.py --episodes 200 --seed-base 81000 \
      --report demo/benchmark_report.md
"""

import argparse
import importlib.util
import json
import os
import random
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
sys.path.insert(0, os.path.join(ROOT, "simulator", "src"))
sys.path.insert(0, ROOT)

from amdrome_sim import Engine  # noqa: E402


def load_agent(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def run_pair(seed, arm_a_factory, blind):
    from demo.assistant import OperatorAssistant
    assistant = arm_a_factory()
    ra = Engine(seed, agent=assistant).run()
    summary_a = assistant.get_summary()
    rb = Engine(seed, agent=blind).run()
    return ra, summary_a, rb


BOOTSTRAP_N = 2000


def bootstrap_ci(diffs, alpha=0.05):
    rng = random.Random(12345)
    n = len(diffs)
    means = []
    for _ in range(BOOTSTRAP_N):
        sample = [diffs[rng.randrange(n)] for _ in range(n)]
        means.append(sum(sample) / n)
    means.sort()
    lo = means[int((alpha / 2) * BOOTSTRAP_N)]
    hi = means[int((1 - alpha / 2) * BOOTSTRAP_N) - 1]
    return round(lo, 2), round(hi, 2)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--episodes", type=int, default=200)
    ap.add_argument("--seed-base", type=int, default=81000)
    ap.add_argument("--report", type=str, default=None,
                    help="write markdown improvement table here")
    args = ap.parse_args()

    blind = load_agent(os.path.join(ROOT, "agents", "blind.py"), "blind_ab")

    from demo.assistant import OperatorAssistant
    arm_a_factory = lambda: OperatorAssistant(autonomous=True)  # noqa: E731

    rows = []
    results_a, results_b, summaries_a = [], [], []
    for i in range(args.episodes):
        seed = args.seed_base + i
        ra, sa, rb = run_pair(seed, arm_a_factory, blind)
        results_a.append(ra)
        results_b.append(rb)
        summaries_a.append(sa)
        rows.append(json.dumps({
            "seed": seed,
            "assistant_net": ra["net_profit"], "blind_net": rb["net_profit"],
            "assistant_ppm": ra["defect_ppm"], "blind_ppm": rb["defect_ppm"],
            "assistant_downtime": ra["unplanned_downtime"],
            "blind_downtime": rb["unplanned_downtime"],
            "assistant_escapes": ra["completed_defective"],
            "blind_escapes": rb["completed_defective"],
            "assistant_breakdowns": ra["breakdowns"],
            "blind_breakdowns": rb["breakdowns"],
        }))
        print(rows[-1])

    def deltas(key_a, key_b):
        return [a[key_a] - b[key_b] for a, b in zip(results_a, results_b)]

    metrics = {
        "net_profit": deltas("net_profit", "net_profit"),
        "defect_ppm": deltas("defect_ppm", "defect_ppm"),
        "escapes": deltas("completed_defective", "completed_defective"),
        "unplanned_downtime": deltas("unplanned_downtime",
                                     "unplanned_downtime"),
        "breakdowns": deltas("breakdowns", "breakdowns"),
    }
    summary = {"summary": True, "episodes": args.episodes,
               "seed_base": args.seed_base, "metrics": {}}
    for name, d in metrics.items():
        lo, hi = bootstrap_ci(d)
        mean = sum(d) / len(d)
        is_win = (lambda x: x > 0) if name == "net_profit" else (lambda x: x < 0)
        summary["metrics"][name] = {
            "mean_delta": round(mean, 2), "ci95": [lo, hi],
            "win_pct": round(100 * sum(1 for x in d if is_win(x)) / len(d), 1)}
    # time-to-detection: engine-side (ticks from GROUND-TRUTH drift onset,
    # via the arm's SPC probing); blind arm has no monitoring
    lats = [r["mean_detection_latency"] for r in results_a
            if r["mean_detection_latency"] is not None]
    summary["assistant_time_to_detection_ticks"] = {
        "mean": round(sum(lats) / len(lats), 2) if lats else None,
        "episodes_with_detection": len(lats),
        "blind_arm": "no monitoring (never detects)"}

    print(json.dumps(summary))

    if args.report:
        write_report(args.report, summary, results_a, results_b)
        print(f"[run_ab] report written to {args.report}", file=sys.stderr)


def write_report(path, summary, ra, rb):
    def m(name):
        return summary["metrics"][name]

    def avg(rs, k):
        return round(sum((r[k] or 0) for r in rs) / len(rs), 2)

    ttd = summary["assistant_time_to_detection_ticks"]
    lines = [
        "# amdrome demo — measured improvement: operator assistant vs blind",
        "",
        f"Paired double-blind A/B: {summary['episodes']} episodes, "
        f"seeds {summary['seed_base']}+ (identical scenarios per pair).",
        "Arm A: demo/assistant OperatorAssistant (autonomous). "
        "Arm B: blind baseline (run-to-failure, no monitoring).",
        "",
        "| metric | assistant (A) | blind (B) | Δ (A−B) | 95% CI | A wins |",
        "|---|---|---|---|---|---|",
        f"| net profit | {avg(ra, 'net_profit')} | {avg(rb, 'net_profit')} | "
        f"+{m('net_profit')['mean_delta']} | "
        f"{m('net_profit')['ci95']} | {m('net_profit')['win_pct']}% |",
        f"| defect escapes (units/ep) | {avg(ra, 'completed_defective')} | "
        f"{avg(rb, 'completed_defective')} | "
        f"{m('escapes')['mean_delta']} | {m('escapes')['ci95']} | "
        f"{m('escapes')['win_pct']}% |",
        f"| defect PPM | {avg(ra, 'defect_ppm')} | {avg(rb, 'defect_ppm')} | "
        f"{m('defect_ppm')['mean_delta']} | {m('defect_ppm')['ci95']} | "
        f"{m('defect_ppm')['win_pct']}% |",
        f"| unplanned downtime (ticks/ep) | {avg(ra, 'unplanned_downtime')} | "
        f"{avg(rb, 'unplanned_downtime')} | "
        f"{m('unplanned_downtime')['mean_delta']} | "
        f"{m('unplanned_downtime')['ci95']} | "
        f"{m('unplanned_downtime')['win_pct']}% |",
        f"| breakdowns (per ep) | {avg(ra, 'breakdowns')} | "
        f"{avg(rb, 'breakdowns')} | {m('breakdowns')['mean_delta']} | "
        f"{m('breakdowns')['ci95']} | {m('breakdowns')['win_pct']}% |",
        "",
        "**Time-to-detection** (information advantage — the rubric's "
        "\u201cspot problems earlier\u201d): assistant mean "
        f"{ttd['mean']} ticks after drift onset "
        f"({ttd['episodes_with_detection']}/{len(ra)} episodes with a "
        "detection); blind arm has no monitoring and never detects.",
        "",
        "Reproduce: `python3 demo/benchmark/run_ab.py --episodes 200 "
        "--seed-base %d --report demo/benchmark_report.md` "
        "(run on a fleet host; dawn does no batch evals)."
        % summary["seed_base"],
    ]
    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
