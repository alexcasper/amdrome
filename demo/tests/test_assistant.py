"""Tests for the Operator Assistant (bead amdrome-a3j)."""

import unittest
import sys
from pathlib import Path

# Add simulator and demo to python path
ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "simulator" / "src"))
sys.path.insert(0, str(ROOT))

from amdrome_sim import Engine
from demo.assistant import (
    OperatorAssistant,
    DriftDetector,
    RULEstimator,
    Recommender,
    Severity,
    ActionType
)


class TestOperatorAssistant(unittest.TestCase):

    def setUp(self):
        self.assistant = OperatorAssistant()

    def test_assistant_initialization(self):
        self.assertIsNotNone(self.assistant.detector)
        self.assertIsNotNone(self.assistant.rul)
        self.assertIsNotNone(self.assistant.recommender)
        self.assertEqual(len(self.assistant.reports_history), 0)

    def test_product_defaults(self):
        """Defaults decided on amdrome-bqm: CBM PM at 0.50 + full inspection."""
        self.assertIsNotNone(self.assistant.cbm)
        self.assertEqual(self.assistant.cbm.w_thr, 0.50)
        self.assertTrue(self.assistant.full_inspection)
        legacy = OperatorAssistant(cbm_threshold=None, full_inspection=False)
        self.assertIsNone(legacy.cbm)

    def test_rul_monotonicity(self):
        estimator = RULEstimator()
        cards = {
            "weld": {"state": "proc", "ops_seen": 10, "queue_before": 1},
            "form": {"state": "proc", "ops_seen": 60, "queue_before": 2},
        }
        # Low drift vs high drift
        health_low = estimator.estimate_health(10, cards, {"weld": 0.2, "form": 0.2})
        health_high = estimator.estimate_health(20, cards, {"weld": 0.2, "form": 3.4})

        # Higher CUSUM/wear should result in higher failure probability and lower RUL
        self.assertGreater(health_high["form"].estimated_wear, health_low["weld"].estimated_wear)
        self.assertGreater(health_high["form"].prob_failure_30t, health_low["weld"].prob_failure_30t)
        self.assertEqual(health_high["form"].status, "CRITICAL")

    def test_drift_detector_latency(self):
        detector = DriftDetector()
        cards = {"weld": {"state": "proc"}}
        
        # Tick 10: drift onset
        alerts_onset = detector.update(10, {"weld": 2.0}, cards)
        self.assertEqual(len(alerts_onset), 1)
        self.assertEqual(alerts_onset[0].severity, Severity.WARNING)

        # Tick 25: confirmed drift alarm
        alerts_alarm = detector.update(25, {"weld": 3.5}, cards)
        self.assertEqual(len(alerts_alarm), 1)
        self.assertEqual(alerts_alarm[0].severity, Severity.CRITICAL)
        self.assertEqual(detector.latencies, [15])

    def test_prescriptive_pm_recommendation(self):
        recommender = Recommender()
        estimator = RULEstimator()
        cards = {"weld": {"state": "proc", "ops_seen": 50, "queue_before": 1}}
        health = estimator.estimate_health(50, cards, {"weld": 3.6})
        recs = recommender.generate_recommendations(
            t=50,
            health_map=health,
            open_contracts=[],
            spot_price=120.0,
            probes_left=4,
            probe_candidates=["weld"]
        )

        # Priority 1 recommendation should be PM for weld
        pm_recs = [r for r in recs if r.action_type == ActionType.TRIGGER_PM and r.target == "weld"]
        self.assertEqual(len(pm_recs), 1)
        self.assertEqual(pm_recs[0].priority, 1)
        self.assertGreater(pm_recs[0].expected_savings, 1000.0)

    def test_live_engine_integration(self):
        """Run a full 336-tick episode of amdrome_sim.Engine with the Assistant in advisory mode."""
        assistant = OperatorAssistant(autonomous=False)

        class AdvisoryAgent:
            def act(self, obs):
                report = assistant.process_tick(obs)
                # Ensure report contains valid stations and fields
                assert len(report.health) == 6
                return {"probes": report.suggested_actions.get("probes", [])}

        engine = Engine(seed=42, agent=AdvisoryAgent(), ticks=336)
        res = engine.run()

        self.assertEqual(res["ticks"], 336)
        summary = assistant.get_summary()
        self.assertEqual(summary["total_ticks_processed"], 336)
        self.assertGreater(summary["total_alerts"], 0)

    def test_autonomous_assistant_agent(self):
        """Run an episode with OperatorAssistant acting autonomously as the agent."""
        assistant = OperatorAssistant(autonomous=True)
        engine = Engine(seed=101, agent=assistant, ticks=336)
        res = engine.run()

        self.assertEqual(res["ticks"], 336)
        self.assertGreater(res["actions_taken"], 0)
        # Verify that PM actions were executed proactively
        self.assertGreater(assistant.total_probes_dispatched, 0)


if __name__ == "__main__":
    unittest.main()
