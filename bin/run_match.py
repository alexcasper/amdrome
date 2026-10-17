#!/usr/bin/env python3
"""Stateless league-match runner — fleet-portable (pure stdlib).

Inputs: agent files (single-file submissions exposing act(obs) or an
`Agent` class) + seed block. Outputs: one JSON row per episode on stdout,
then a summary JSON object on the last line (tagged "summary": true).

League design (charter: no canonical opponent): each agent plays the same
seeded episode set; per episode the rival bid strength is drawn from an
opponent POOL (uniform over the pool's mu values), seeded by
(match_seed, episode, agent) — so opponents vary and cannot be taped.

Usage:
  python3 bin/run_match.py --agents agents/blind.py agents/shrewd.py \
      --seed 99000 --episodes 50 [--threads 8] [--layout compact]

Works on any host with python3 >= 3.10; no network, no shared state.
"""

import argparse
import importlib.util
import json
import os
import sys
from concurrent.futures import ProcessPoolExecutor

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "simulator", "src"))

from amdrome_sim import Engine  # noqa: E402

# opponent pool: rival bid-strength mus agents are drawn against
OPPONENT_POOL = [0.85, 0.92, 0.98, 1.02, 1.05]


def load_agent(path):
    """Load a single-file agent submission: module-level act(obs) or Agent."""
    name = os.path.splitext(os.path.basename(path))[0]
    spec = importlib.util.spec_from_file_location(f"agent_{name}", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    if hasattr(mod, "Agent"):
        return mod.Agent()
    if hasattr(mod, "act"):
        return mod          # module itself is the callable surface
    raise ValueError(f"{path}: no act(obs) or Agent class found")


def _pool_seed(match_seed, episode, agent_name):
    import hashlib
    blob = f"{match_seed}|{episode}|{agent_name}|pool".encode()
    return int.from_bytes(hashlib.sha256(blob).digest()[:8], "big")


def run_one(args):
    agent_path, agent_name, seed, episode, layout, match_seed = args
    import random
    mu = OPPONENT_POOL[random.Random(
        _pool_seed(match_seed, episode, agent_name)).randrange(
            len(OPPONENT_POOL))]
    agent = load_agent(agent_path)
    eng = Engine(seed + episode, agent=agent, layout=layout,
                 rival_mu=mu)
    eng.run()
    r = eng.result()
    r.update({"agent": agent_name, "episode": episode, "rival_mu": mu})
    return r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--agents", nargs="+", required=True)
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--episodes", type=int, default=50)
    ap.add_argument("--layout", default="compact")
    ap.add_argument("--threads", type=int, default=1)
    args = ap.parse_args()

    jobs = []
    names = []
    for path in args.agents:
        name = os.path.splitext(os.path.basename(path))[0]
        names.append(name)
        load_agent(path)                      # fail fast on bad submissions
        for e in range(args.episodes):
            jobs.append((os.path.abspath(path), name, args.seed, e,
                         args.layout, args.seed))

    if args.threads > 1:
        with ProcessPoolExecutor(max_workers=args.threads) as ex:
            results = list(ex.map(run_one, jobs))
    else:
        results = [run_one(j) for j in jobs]

    for r in results:
        print(json.dumps(r))

    # summary
    summary = {"summary": True, "episodes_per_agent": args.episodes,
               "seed": args.seed, "agents": {}}
    for name in names:
        rs = [r for r in results if r["agent"] == name]
        profits = sorted(r["net_profit"] for r in rs)
        summary["agents"][name] = {
            "mean_net": round(sum(profits) / len(profits), 2),
            "median_net": profits[len(profits) // 2],
            "win_vs_pool_pct": round(100 * sum(
                1 for r in rs if r["net_profit"] > 0) / len(rs), 1),
            "mean_clean": round(sum(r["completed_clean"] for r in rs)
                                / len(rs), 2),
            "mean_breakdowns": round(sum(r["breakdowns"] for r in rs)
                                     / len(rs), 2),
            "ontime": round(sum(r["ontime_frac"] for r in rs) / len(rs), 3),
            "ppm": round(sum(r["defect_ppm"] for r in rs) / len(rs), 1),
        }
    print(json.dumps(summary))


if __name__ == "__main__":
    main()
