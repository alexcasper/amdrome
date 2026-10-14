#!/usr/bin/env python3
"""Knob-search over the reactive baseline (bead amdrome-6k2 / x4i pre-work).

Random search over the reactive agent's knob space, evaluated head-to-head
vs blind on paired seeds. Pure stdlib, stateless — run on fleet hosts:

  python3 rl/tune_knobs.py --configs 40 --episodes 40 --seed 41000

Output: JSONL rows {config_id, knobs, mean_net, mean_edge_vs_blind, dz}
one per config, plus a final summary with the best config.

Stages: --stage coarse (wide ranges) / --stage refine (around --center,
passed as JSON from the coarse best).
"""

import argparse
import importlib.util
import json
import math
import os
import random
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, os.path.join(ROOT, "simulator", "src"))
sys.path.insert(0, os.path.join(ROOT, "agents"))

from amdrome_sim import Engine  # noqa: E402

SPACE_COARSE = {
    "pm_cusum": (1.2, 4.5),
    "pm_ops": (8, 30),
    "pm_ops_cusum": (0.3, 2.0),
    "pm_floor_ticks": (48, 240),
    "probe_top_k": (1, 3),
    "margin_hi": (40, 140),
    "shade_lo": (0.86, 0.94),
    "shade_hi": (0.96, 1.02),
    "inspect_full_after": (0, 240),
    "caps_hot_wip": (4, 12),
}


def sample(rng, space):
    k = {}
    for key, (lo, hi) in space.items():
        if key in ("probe_top_k",):
            k[key] = rng.randrange(lo, hi + 1)
        else:
            k[key] = round(rng.uniform(lo, hi), 3)
    return k


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def evaluate(knobs, base_seed, n, agent_cls, blind):
    diffs, nets = [], []
    for i in range(n):
        seed = base_seed + i
        ra = Engine(seed, agent=agent_cls(knobs)).run()["net_profit"]
        rb = Engine(seed, agent=blind).run()["net_profit"]
        nets.append(ra)
        diffs.append(ra - rb)
    dm = sum(diffs) / n
    ds = math.sqrt(sum((d - dm) ** 2 for d in diffs) / (n - 1))
    return {"mean_net": round(sum(nets) / n, 2),
            "mean_edge": round(dm, 2),
            "dz": round(dm / ds, 3) if ds else 99.0,
            "win_pct": round(100 * sum(1 for d in diffs if d > 0) / n, 1)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--configs", type=int, default=40)
    ap.add_argument("--episodes", type=int, default=40)
    ap.add_argument("--seed", type=int, default=41000)
    ap.add_argument("--stage", choices=["coarse", "refine"],
                    default="coarse")
    ap.add_argument("--center", type=str, default=None,
                    help="JSON knobs to refine around (coarse best)")
    args = ap.parse_args()

    reactive = load(os.path.join(ROOT, "agents", "reactive.py"),
                    "reactive_mod")
    blind = load(os.path.join(ROOT, "agents", "blind.py"), "blind_mod")
    rng = random.Random(args.seed)

    space = dict(SPACE_COARSE)
    if args.stage == "refine" and args.center:
        c = json.loads(args.center)
        space = {k: (max(SPACE_COARSE[k][0], v - (SPACE_COARSE[k][1]
                                                  - SPACE_COARSE[k][0]) * 0.15),
                   min(SPACE_COARSE[k][1], v + (SPACE_COARSE[k][1]
                                                - SPACE_COARSE[k][0]) * 0.15))
                 for k, v in c.items()}

    best = None
    for ci in range(args.configs):
        knobs = sample(rng, space)
        ev = evaluate(knobs, args.seed, args.episodes,
                      reactive.Agent, blind)
        row = {"config_id": ci, "knobs": knobs}
        row.update(ev)
        print(json.dumps(row))
        if best is None or ev["mean_edge"] > best["mean_edge"]:
            best = row
    print(json.dumps({"summary": True, "stage": args.stage,
                      "episodes_per_config": args.episodes,
                      "best": best}))
    print(f"[tune_knobs] best config {best['config_id']}: "
          f"edge {best['mean_edge']} d_z {best['dz']}", file=sys.stderr)


if __name__ == "__main__":
    main()
