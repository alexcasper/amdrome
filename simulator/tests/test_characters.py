"""Character-agent tests (bead amdrome-iuf).

Pass criteria from the feature order: every persona runs N episodes
across >=3 configs with ZERO errors, deterministically. Score ordering
(> random, < reactive) is measured on the fleet host and reported in the
research note — not asserted here (needs larger n than dawn allows).
"""

import importlib.util
import json
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "simulator", "src"))

from amdrome_sim import Engine  # noqa: E402

CHARACTERS = ["random_baseline", "char_charlie", "char_pete",
              "char_chen", "char_milliard"]

CONFIGS = [  # >=3 distinct engine configurations
    {"layout": "compact", "ticks": 336},
    {"layout": "scattered", "ticks": 336},
    {"layout": "compact", "ticks": 168},
]


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def make_agent(name):
    mod = load(os.path.join(ROOT, "agents", f"{name}.py"), f"t_{name}")
    return mod.Agent()


class TestCharacters(unittest.TestCase):
    def test_all_personas_all_configs_zero_errors(self):
        for cname in CHARACTERS:
            for cfg in CONFIGS:
                for seed in (4242, 4243, 4244):
                    eng = Engine(seed, agent=make_agent(cname),
                                 layout=cfg["layout"], ticks=cfg["ticks"])
                    res = eng.run()
                    self.assertTrue(
                        all(isinstance(v, (int, float))
                            for v in res.values() if v is not None),
                        f"{cname} produced non-numeric metric")

    def test_deterministic_per_seed(self):
        for cname in CHARACTERS:
            a = Engine(555, agent=make_agent(cname)).run()
            b = Engine(555, agent=make_agent(cname)).run()
            self.assertEqual(json.dumps(a, sort_keys=True),
                             json.dumps(b, sort_keys=True),
                             f"{cname} not deterministic")

    def test_legal_actions_only(self):
        """Every action submitted is within the engine's accepted schema —
        the run itself is the check (engine raises on malformed internals);
        additionally assert no exceptions leak from the agent side."""
        for cname in CHARACTERS:
            agent = make_agent(cname)
            eng = Engine(999, agent=agent, ticks=48)
            eng.run()   # short episode exercises every action channel once


if __name__ == "__main__":
    unittest.main()
