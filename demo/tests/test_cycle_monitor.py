"""CycleMonitor: wear-rate inference from the per-op cycle-time stream."""

import math
import os
import random
import sys
import unittest

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
sys.path.insert(0, ROOT)

from demo.assistant.cycle_monitor import CycleMonitor  # noqa: E402


def synthetic_stream(rate, scale=1.0, n_ops=30, seed=1):
    """Yield obs dicts for one station whose cycle time follows the engine
    model 7*scale*lognormal(0.15)*(1+0.35*wear), wear += rate per op."""
    rng = random.Random(seed)
    t, wear, ops = 0, 0.0, 0
    for _ in range(n_ops):
        dur = max(1, round(7 * scale * math.exp(rng.gauss(0, 0.15))
                           * (1 + 0.35 * wear)))
        # engine-visible pattern: dur-1 ticks 'proc', then op counter +1
        for _ in range(dur - 1):
            yield {"t": t, "cards": {"weld": {"state": "proc", "ops_seen": ops}},
                   "roster": {"assigned_counts": {"weld": 1}}}
            t += 1
        ops += 1
        wear += rate
        yield {"t": t, "cards": {"weld": {"state": "idle", "ops_seen": ops}},
               "roster": {"assigned_counts": {"weld": 1}}}
        t += 1


class TestCycleMonitor(unittest.TestCase):
    def test_rate_tracks_truth(self):
        # Single station, 30 ops: intercept and slope come from one stream,
        # so the r prior (mean 0.0276) shrinks estimates noticeably. Assert
        # the estimator separates slow from fast wear and stays within 2x.
        means = []
        for true_r in (0.015, 0.045):
            ests = []
            for seed in range(8):
                cm = CycleMonitor(wear_threshold=2.0)
                for obs in synthetic_stream(true_r, seed=seed):
                    cm.update(obs)
                ests.append(cm.rate("weld"))
            m = sum(ests) / len(ests)
            means.append(m)
            self.assertTrue(0.5 * true_r < m < 2.0 * true_r,
                            f"mean est {m:.4f} at r={true_r}")
        self.assertGreater(means[1], 1.5 * means[0])

    def test_requests_pm_at_threshold_and_resets(self):
        cm = CycleMonitor(wear_threshold=0.4)
        fired = False
        for obs in synthetic_stream(0.05, n_ops=20, seed=3):
            cm.update(obs)
            if cm.pm_requests(obs):
                fired = True
                break
        self.assertTrue(fired)
        # PM cycle: state pm then idle -> wear estimate resets near zero
        t = obs["t"]
        ops = obs["cards"]["weld"]["ops_seen"]
        for st in ("pm", "idle"):
            t += 1
            cm.update({"t": t, "cards": {"weld": {"state": st, "ops_seen": ops}}})
        self.assertLess(cm.wear("weld"), 0.1)


if __name__ == "__main__":
    unittest.main()
