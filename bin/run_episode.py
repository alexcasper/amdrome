#!/usr/bin/env python3
"""Stateless episode runner — fleet-portable (pure stdlib).

Usage:
  python3 bin/run_episode.py --seed 1 --episodes 10 [--layout compact]
Outputs one JSON result per episode on stdout (JSONL).
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "simulator", "src"))

from amdrome_sim import Engine, NullAgent  # noqa: E402


class SimpleAgent(NullAgent):
    """Cheap adaptive agent: bids near face value, probes round-robin."""

    def act(self, obs):
        acts = {"bids": {}, "probes": []}
        for c in obs["open_contracts"]:
            acts["bids"][c["id"]] = round(c["unit_price"] * 1.05, 2)
        if obs["t"] % 24 == 0:
            acts["probes"] = ["form"]
        return acts


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--episodes", type=int, default=1)
    ap.add_argument("--layout", default="compact",
                    choices=["compact", "scattered"])
    args = ap.parse_args()
    for e in range(args.episodes):
        eng = Engine(args.seed + e, agent=SimpleAgent(),
                     layout=args.layout)
        eng.run()
        print(json.dumps(eng.result()))
    print(f"[run_episode] {args.layout} x{args.episodes} done",
          file=sys.stderr)


if __name__ == "__main__":
    main()
