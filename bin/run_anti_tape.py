#!/usr/bin/env python3
"""Engine-level anti-tape gate (bead amdrome-gn6, DESIGN.md §7 gate 2).

Records a strong policy's full action stream under tape-seed S0, then
replays it under FRESH scenario draws vs a mediocre reactive agent.
Pass: every tape variant's win rate < 30% over >= 100 paired episodes.

Tape variants:
  full  — all recorded actions; bids mapped by ORDINAL onto the currently
          open contracts (memorized absolute prices land on different
          face values — the honest anti-tape mechanism), pm/probes/caps
          replayed verbatim
  bids  — only the bid stream (market surface only)
  ops   — only pm/probes/caps (physical surface only)

Stateless CLI, pure stdlib — run on fleet hosts:
  python3 bin/run_anti_tape.py --strong agents/shrewd.py \
      --mediocre agents/shrewd.py --tape-seed 7 --seed-base 2001 \
      --episodes 200
"""

import argparse
import json
import os
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, os.path.join(ROOT, "simulator", "src"))
sys.path.insert(0, os.path.join(ROOT, "bin"))

from amdrome_sim import Engine  # noqa: E402
from run_match import load_agent  # noqa: E402


class Recorder:
    """Wraps an agent, recording its action stream per tick."""

    def __init__(self, agent):
        self.agent = agent
        self.log = []

    def act(self, obs):
        acts = self.agent.act(obs) or {}
        self.log.append(acts)
        return acts


class TapeAgent:
    """Replays recorded actions; bids mapped by ordinal position."""

    def __init__(self, log, variant="full"):
        self.log = log
        self.variant = variant

    def act(self, obs):
        t = obs["t"]
        rec = self.log[t] if t < len(self.log) else {}
        out = {}
        if self.variant in ("full", "bids") and rec.get("bids"):
            open_sorted = sorted(obs["open_contracts"], key=lambda c: c["id"])
            prices = list(rec["bids"].values())
            out["bids"] = {c["id"]: prices[i] for i, c in
                           enumerate(open_sorted) if i < len(prices)}
        if self.variant in ("full", "ops"):
            for k in ("probes", "pm", "caps", "inspect_mode"):
                if k in rec:
                    out[k] = rec[k]
        return out


def play(seed, agent, tape_seed_log, variant, rival_mu=None):
    if variant is None:                      # live agent episode
        eng = Engine(seed, agent=agent, rival_mu=rival_mu)
    else:
        eng = Engine(seed, agent=TapeAgent(tape_seed_log, variant),
                     rival_mu=rival_mu)
    eng.run()
    return eng.result()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--strong", required=True, help="agent file to record")
    ap.add_argument("--mediocre", required=True, help="reactive baseline")
    ap.add_argument("--tape-seed", type=int, default=7)
    ap.add_argument("--seed-base", type=int, default=2001)
    ap.add_argument("--episodes", type=int, default=200)
    ap.add_argument("--rival-mu", type=float, default=None)
    args = ap.parse_args()

    strong = load_agent(args.strong)
    mediocre = load_agent(args.mediocre)

    rec_engine = Engine(args.tape_seed, agent=Recorder(strong),
                        rival_mu=args.rival_mu)
    rec_engine.run()
    tape_log = rec_engine.agent.log
    print(f"# recorded {len(tape_log)} ticks from {args.strong} "
          f"seed {args.tape_seed} "
          f"(net {rec_engine.result()['net_profit']})", file=sys.stderr)

    verdicts = {}
    for variant in ("full", "bids", "ops"):
        wins = 0
        n = args.episodes
        for i in range(n):
            seed = args.seed_base + i
            rt = play(seed, None, tape_log, variant, args.rival_mu)
            rm = play(seed, mediocre, None, None, args.rival_mu)
            print(json.dumps({
                "variant": variant, "seed": seed,
                "tape_net": rt["net_profit"], "mediocre_net": rm["net_profit"],
                "tape_contracts": rt["contracts_won"],
                "tape_clean": rt["completed_clean"],
                "tape_breakdowns": rt["breakdowns"]}))
            if rt["net_profit"] > rm["net_profit"]:
                wins += 1
        wr = round(100 * wins / n, 1)
        verdicts[variant] = wr
        print(f"[gate2:{variant}] tape win% = {wr} "
              f"-> {'PASS' if wr < 30 else 'FAIL'}", file=sys.stderr)
    print(json.dumps({"summary": True, "gate": "anti_tape_engine",
                      "tape_seed": args.tape_seed,
                      "episodes": args.episodes,
                      "tape_win_pct": verdicts,
                      "overall": "PASS" if all(v < 30 for v in
                                               verdicts.values()) else "FAIL"}))


if __name__ == "__main__":
    main()
