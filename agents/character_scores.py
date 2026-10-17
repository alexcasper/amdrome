#!/usr/bin/env python3
"""Character-agent score table (bead amdrome-iuf; fleet host).

Runs every persona + baselines over N paired episodes, prints a JSON
summary row per agent. Assertions live in the analysis (ordering:
random < characters < reactive).
"""

import importlib.util
import json
import os
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, os.path.join(ROOT, "simulator", "src"))

from amdrome_sim import Engine  # noqa: E402

AGENTS = ["random_baseline", "char_charlie", "char_pete", "char_chen",
          "char_milliard", "blind", "reactive"]


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def make_agent(mod):
    if hasattr(mod, "Agent"):
        return mod.Agent()
    return mod          # module-level act(obs) surface


def main():
    base = int(sys.argv[1]) if len(sys.argv) > 1 else 910000
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 100
    for name in AGENTS:
        mod = load(os.path.join(ROOT, "agents", f"{name}.py"), f"s_{name}")
        agent = make_agent(mod)
        nets, pms, brkds, ppm, escapes = [], [], [], [], []
        for i in range(n):
            r = Engine(base + i, agent=agent).run()
            nets.append(r["net_profit"])
            pms.append(r["pm_count"])
            brkds.append(r["breakdowns"])
            ppm.append(r["defect_ppm"])
            escapes.append(r["completed_defective"])
        print(json.dumps({
            "agent": name, "n": n,
            "mean_net": round(sum(nets) / n, 1),
            "mean_pm": round(sum(pms) / n, 2),
            "mean_brkd": round(sum(brkds) / n, 2),
            "mean_ppm": round(sum(ppm) / n, 0),
            "mean_escapes": round(sum(escapes) / n, 2)}))


if __name__ == "__main__":
    main()
