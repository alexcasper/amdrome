#!/usr/bin/env python3
"""amdrome acceptance-gate harness (bead amdrome-3zh, DESIGN.md §7 gates 2-3).

Gate 2 (anti-tape), two surfaces:
  a) capacity/layout: TAPE replays the strong policy's PER-SHIFT buffer
     allocation sequence (recorded under tape-seed S0) under fresh scenario
     draws, vs a mediocre fixed-allocation agent. 6 decisions/episode.
  b) degradation/PM: TAPE_PM replays the SPC-reactive policy's PM schedule
     (recorded under S0) in proto_degradation, vs spc_reactive_b8.
  Pass: tape win rate < 30% (>=100 paired episodes) on at least one surface.

Gate 3 (skill dominance): scripted-good (adaptive allocation, compact
layout) vs scripted-bad (fixed even allocation, scattered layout) on
economic score: d_z > 2.0, p < 0.01 at N <= 200 paired episodes; plus
good > mediocre at p < 0.05.

Scenario λ ~ U[0.08, 0.17] (wide hyperprior — the anti-tape lever; line
capacity ≈ 0.10–0.14, so both starvation and congestion regimes occur).

Economic score v1:
    40*completed - 30*rejected - 3*wip_mean - 1.0*cycle_mean

Stateless CLI, pure stdlib — heavy sweeps run on fleet hosts:
  proto_gates.py --gate all --tape-seed 7 --seed-base 1001 --episodes 400
  proto_gates.py --analyze results.jsonl
"""

import argparse
import json
import math
import sys

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from proto_layout import run_episode as run_layout  # noqa: E402

LAM_RANGE = (0.08, 0.17)
WARMUP = [3, 3, 3, 3, 3, 3]
W_UNIT, W_REJECT, W_WIP, W_CYCLE = 40.0, 30.0, 3.0, 1.0


def score(rec):
    return (W_UNIT * rec["completed"] - W_REJECT * rec["rejected"]
            - W_WIP * rec["wip_mean"] - W_CYCLE * (rec["cycle_mean"] or 0.0))


# ------------------------------------------------------------------- agents

def good(t, arr):
    """Adaptive per-shift: λ̂ from cumulative kanban pull count."""
    if t == 0:
        return WARMUP
    lam_h = arr / float(t)
    if lam_h > 0.135:                    # hot: protect entry, starve tail
        return [9, 3, 2, 2, 1, 1]
    if lam_h > 0.105:                    # congested middle band
        return [6, 3, 3, 3, 2, 1]
    return WARMUP                        # cool: even spread


def mediocre(t, arr):
    return WARMUP


def tape_agent(schedule):
    """Replays the S0 per-shift allocation sequence regardless of λ̂."""
    i = [-1]

    def agent(t, arr):
        i[0] += 1
        return WARMUP if i[0] < 0 else list(schedule[min(i[0], len(schedule) - 1)])
    return agent


def record_schedule(tape_seed):
    """Run GOOD under tape_seed; capture its per-shift allocation sequence."""
    sched = []
    outer = sched

    def recorder(t, arr):
        caps = good(t, arr)
        outer.append(list(caps))
        return caps

    run_layout("compact", tape_seed, decide=recorder, lam_range=LAM_RANGE)
    return sched


# --------------------------------------------------------------------- runs

def emit(gate, seed, agent, rec, extra=None):
    row = {"gate": gate, "seed": seed, "agent": agent,
           "score": round(score(rec), 2), "completed": rec["completed"],
           "rejected": rec["rejected"], "cycle_mean": rec["cycle_mean"],
           "wip_mean": rec["wip_mean"], "lam": rec["lam"]}
    if extra:
        row.update(extra)
    print(json.dumps(row))


def run_layout_pair(gate, seed, a, b, sched, name_a, name_b):
    layout_a, dec_a = a if a[0] != "tape" else ("compact", tape_agent(sched))
    layout_b, dec_b = b if b[0] != "tape" else ("compact", tape_agent(sched))
    ra = run_layout(layout_a, seed, decide=dec_a, lam_range=LAM_RANGE,
                    shared_flow=True)
    rb = run_layout(layout_b, seed, decide=dec_b, lam_range=LAM_RANGE,
                    shared_flow=True)
    emit(gate, seed, name_a, ra)
    emit(gate, seed, name_b, rb)


def run_pm_pair(seed, sched_pm, sample_budget=8):
    """Tape-PM vs spc_reactive on the degradation prototype."""
    import proto_degradation as pd
    ra = pd.run_episode("tape_pm", seed, pm_schedule=sched_pm)
    rb = pd.run_episode("spc_reactive", seed, sample_budget=sample_budget)
    for name, r in (("tape_pm", ra), ("mediocre", rb)):
        print(json.dumps({
            "gate": "anti_tape_pm", "seed": seed, "agent": name,
            "score": r["net_profit"], "completed": r["completed_clean"],
            "rejected": r["completed_defective"], "cycle_mean": r["cycle_mean"],
            "wip_mean": None, "lam": None,
            "breakdowns": r["breakdowns_count"], "pm_count": r["pm_count"],
            "unplanned_downtime": r["unplanned_downtime"]}))


def record_pm_schedule(tape_seed):
    import proto_degradation as pd
    rec = pd.run_episode("spc_reactive", tape_seed, sample_budget=8)
    return rec["pm_events"]


# ------------------------------------------------------------------ analyze

def paired_stats(diffs):
    n = len(diffs)
    dm = sum(diffs) / n
    ds = math.sqrt(sum((d - dm) ** 2 for d in diffs) / (n - 1)) or 1e-12
    z = dm / (ds / math.sqrt(n))
    p = math.erfc(abs(z) / math.sqrt(2))
    return {"n": n, "dm": round(dm, 2), "sd": round(ds, 2),
            "dz": round(dm / ds, 3), "z": round(z, 2), "p": p,
            "win": round(100 * sum(1 for d in diffs if d > 0) / n, 1)}


def analyze(path):
    rows = {}
    with open(path) as f:
        for line in f:
            r = json.loads(line)
            rows.setdefault((r["gate"], r["seed"]), {})[r["agent"]] = r
    gates = {}
    for (gate, seed), pair in sorted(rows.items()):
        if len(pair) == 2:
            gates.setdefault(gate, []).append(pair)
    for gate, pairs in gates.items():
        names = sorted(pairs[0])
        a, b = names
        st = paired_stats([p[a]["score"] - p[b]["score"] for p in pairs])
        print(f"[{gate}] {a} - {b}: n={st['n']} Δ={st['dm']}±{st['sd']} "
              f"d_z={st['dz']} z={st['z']} p={st['p']:.2e} {a}win%={st['win']}")
        if gate.startswith("anti_tape"):
            tw = st["win"] if a == "tape" or a == "tape_pm" else 100 - st["win"]
            print(f"    tape win% = {tw} -> {'PASS' if tw < 30 else 'FAIL'} (<30)")
        elif gate == "skill_good_bad":
            ok = st["dz"] > 2.0 and st["p"] < 0.01
            print(f"    -> {'PASS' if ok else 'FAIL'} (d_z>2.0, p<0.01)")
        elif gate == "skill_good_med":
            dm = st["dm"] if a == "good" else -st["dm"]
            ok = dm > 0 and st["p"] < 0.05
            print(f"    -> {'PASS' if ok else 'FAIL'} (good>mediocre, p<0.05)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gate", default="all",
                    choices=["all", "anti_tape", "anti_tape_pm",
                             "skill_good_bad", "skill_good_med"])
    ap.add_argument("--tape-seed", type=int, default=7)
    ap.add_argument("--seed-base", type=int, default=1001)
    ap.add_argument("--episodes", type=int, default=400)
    ap.add_argument("--analyze", metavar="JSONL")
    args = ap.parse_args()

    if args.analyze:
        analyze(args.analyze)
        return

    good_pair = ("compact", good)
    med_pair = ("compact", mediocre)
    bad_pair = ("scattered", mediocre)
    sched = record_schedule(args.tape_seed)
    sched_pm = record_pm_schedule(args.tape_seed)
    print(f"# tape schedule (layout, seed {args.tape_seed}): {sched}",
          file=sys.stderr)
    print(f"# tape PM schedule (seed {args.tape_seed}): {sched_pm}",
          file=sys.stderr)

    base = {"anti_tape": args.seed_base,
            "anti_tape_pm": args.seed_base + 4000,
            "skill_good_bad": args.seed_base + 10000,
            "skill_good_med": args.seed_base + 20000}
    n_by = {"anti_tape": args.episodes, "anti_tape_pm": args.episodes,
            "skill_good_bad": min(args.episodes, 200),
            "skill_good_med": min(args.episodes, 200)}
    runs = {"anti_tape": lambda s: run_layout_pair(
                "anti_tape", s, ("tape", None), med_pair, sched,
                "tape", "mediocre"),
            "anti_tape_pm": lambda s: run_pm_pair(s, sched_pm),
            "skill_good_bad": lambda s: run_layout_pair(
                "skill_good_bad", s, good_pair, bad_pair, sched,
                "good", "bad"),
            "skill_good_med": lambda s: run_layout_pair(
                "skill_good_med", s, good_pair, med_pair, sched,
                "good", "mediocre")}
    todo = list(runs) if args.gate == "all" else [args.gate]
    for gate in todo:
        for i in range(n_by[gate]):
            runs[gate](base[gate] + i)
    print(f"[proto_gates] done ({args.gate})", file=sys.stderr)


if __name__ == "__main__":
    main()
