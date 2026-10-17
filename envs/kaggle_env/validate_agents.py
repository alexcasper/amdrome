#!/usr/bin/env python3
"""Validate agent submissions against the kaggle_env contract.

Checks each file: loads as a module, exposes act(obs) or Agent, and runs
one short episode (48 ticks, single factory — unit-test scale, dawn-safe)
against a synthetic obs sequence producing only contract-valid actions.

Usage: python3 envs/kaggle_env/validate_agents.py agents/*.py
"""

import json
import os
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
sys.path.insert(0, os.path.join(ROOT, "simulator", "src"))

from amdrome_sim import Engine  # noqa: E402

sys.path.insert(0, os.path.join(ROOT, "bin"))
from run_match import load_agent  # noqa: E402

VALID_MODES = ("skip", "sample", "full")
STATION_KINDS = ("cut", "form", "weld", "paint", "inspect", "pack")


def validate(path):
    errs = []
    try:
        agent = load_agent(path)
    except Exception as e:
        return [f"load failed: {e}"]

    class Checker:
        def act(self, obs):
            try:
                acts = agent.act(obs) or {}
            except Exception as e:
                errs.append(f"agent raised: {e!r}")
                return {}
            if not isinstance(acts, dict):
                errs.append("actions must be a dict")
                return {}
            for cid, bid in acts.get("bids", {}).items():
                if not isinstance(bid, (int, float)) or bid <= 0:
                    errs.append(f"bad bid {bid!r} for {cid}")
            for k in acts.get("probes", []):
                if k not in STATION_KINDS:
                    errs.append(f"bad probe target {k!r}")
            for k in acts.get("pm", []):
                if k not in STATION_KINDS:
                    errs.append(f"bad pm target {k!r}")
            if "inspect_mode" in acts \
                    and acts["inspect_mode"] not in VALID_MODES:
                errs.append(f"bad inspect_mode {acts['inspect_mode']!r}")
            if "caps" in acts:
                caps = acts["caps"]
                if not (isinstance(caps, list) and len(caps) == 6
                        and all(isinstance(c, int) and c >= 0 for c in caps)):
                    errs.append("caps must be 6 non-negative ints")
                elif sum(caps) != 18:
                    errs.append(f"caps must total 18, got {sum(caps)}")
            return acts

    eng = Engine(1, agent=Checker(), ticks=48)   # dawn-safe unit scale
    try:
        eng.run()
    except Exception as e:
        errs.append(f"engine error during episode: {e!r}")
    return errs


def main():
    failures = 0
    for path in sys.argv[1:]:
        errs = validate(path)
        status = "OK" if not errs else "FAIL"
        print(f"{status}  {path}")
        for e in errs:
            print(f"      - {e}")
        failures += bool(errs)
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
