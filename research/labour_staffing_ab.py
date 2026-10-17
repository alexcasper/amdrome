#!/usr/bin/env python3
"""Labour-coupling before/after probe (bead amdrome-svf).

Runs paired episodes for a small agent panel against the engine tree this
file lives in, so the SAME script measures a pre-fix and a post-fix copy:

  blind            run-to-failure, default staffing (even spread)
  reactive         agents/reactive.py (CUSUM PM + bidding + staffing counts)
  reactive_noasg   reactive with its 'assign' action stripped
  unstaff_exploit  blind + every present worker piled onto 'pack' (5 of 6
                   stations unstaffed) — profitable only if understaffing
                   is rewarded
  assistant        demo OperatorAssistant() product default

Prints per-agent means and paired edges (mean diff, d_z, win%) for the
skill-dominance comparisons: reactive-blind, reactive-reactive_noasg (the
labour decision's own edge), unstaff_exploit-blind.

  python3 research/labour_staffing_ab.py --seed-base 960000 --episodes 1000
"""

import argparse
import importlib.util
import json
import math
import os
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, os.path.join(ROOT, "simulator", "src"))
sys.path.insert(0, ROOT)

from amdrome_sim import Engine  # noqa: E402

KEYS = ("net_profit", "completed_clean", "completed_defective",
        "unplanned_downtime", "breakdowns")


def _load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class FnAgent:
    def __init__(self, fn):
        self.fn = fn

    def act(self, obs):
        return self.fn(obs)


def make(name, mods):
    if name == "blind":
        return FnAgent(mods["blind"].act)
    if name == "reactive":
        return mods["reactive"].Agent()
    if name == "reactive_noasg":
        r = mods["reactive"].Agent()

        def act(obs):
            out = r.act(obs) or {}
            out.pop("assign", None)
            return out
        return FnAgent(act)
    if name == "unstaff_exploit":
        def act(obs):
            out = mods["blind"].act(obs)
            present = (obs.get("roster") or {}).get("present", 0)
            if present:
                out["assign"] = {"pack": present}
            return out
        return FnAgent(act)
    if name == "assistant":
        from demo.assistant import OperatorAssistant
        return OperatorAssistant(autonomous=True)
    raise SystemExit(name)


def paired(a, b):
    d = [x - y for x, y in zip(a, b)]
    n = len(d)
    m = sum(d) / n
    sd = math.sqrt(sum((x - m) ** 2 for x in d) / (n - 1)) or 1e-9
    return {"mean": round(m, 2), "dz": round(m / sd, 3),
            "z": round(m / (sd / math.sqrt(n)), 1),
            "win_pct": round(100 * sum(1 for x in d if x > 0) / n, 1)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed-base", type=int, default=960000)
    ap.add_argument("--episodes", type=int, default=1000)
    ap.add_argument("--agents", default="blind,reactive,reactive_noasg,"
                    "unstaff_exploit,assistant")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    mods = {"blind": _load(os.path.join(ROOT, "agents", "blind.py"), "b_"),
            "reactive": _load(os.path.join(ROOT, "agents", "reactive.py"),
                              "r_")}
    names = args.agents.split(",")
    res = {n: {k: [] for k in KEYS} for n in names}
    for i in range(args.episodes):
        for n in names:
            r = Engine(args.seed_base + i, agent=make(n, mods)).run()
            for k in KEYS:
                res[n][k].append(r[k])
    out = {"seed_base": args.seed_base, "episodes": args.episodes,
           "per_agent": {n: {k: round(sum(v) / len(v), 3)
                             for k, v in d.items()} for n, d in res.items()},
           "paired_net": {}}
    for a, b in (("reactive", "blind"), ("reactive", "reactive_noasg"),
                 ("unstaff_exploit", "blind"), ("assistant", "blind")):
        if a in res and b in res:
            out["paired_net"][f"{a}-{b}"] = paired(res[a]["net_profit"],
                                                   res[b]["net_profit"])
    s = json.dumps(out, indent=1)
    print(s)
    if args.out:
        with open(args.out, "w") as f:
            f.write(s + "\n")


if __name__ == "__main__":
    main()
