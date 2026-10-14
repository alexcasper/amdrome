"""Operator Assistant: Intelligent streaming copilot over the kanban observation stream.

Bead: amdrome-a3j (SPEC_DEMO_PRODUCT.md)
"""

from typing import Any, Dict, List
from .drift_detector import DriftDetector
from .recommender import Recommender
from .rul_estimator import RULEstimator
from .types import Alert, AssistantReport, Recommendation, Severity, StationHealth


class OperatorAssistant:
    """Consumes the engine's partial-observability kanban stream and emits ranked alerts and recommendations."""

    def __init__(self, autonomous: bool = False):
        self.autonomous = autonomous
        self.detector = DriftDetector()
        self.rul = RULEstimator()
        self.recommender = Recommender()

        # Telemetry logs & metrics
        self.reports_history = []
        self.all_alerts = []
        self.total_pm_actions = 0
        self.total_probes_dispatched = 0
        self.total_savings_accumulated = 0.0

    def process_tick(self, obs: Dict[str, Any]) -> AssistantReport:
        """Processes one tick of the kanban observation stream and returns an analytical report."""
        t = obs["t"]
        wip = obs.get("wip", 0)
        spot_price = obs.get("spot_price", 100.0)
        probes_left = obs.get("spc_probes_left", 0)
        cusum_scores = obs.get("cusum", {})
        cards = obs.get("cards", {})
        open_contracts = obs.get("open_contracts", [])

        # 1. Update CUSUM drift detection
        drift_alerts = self.detector.update(t, cusum_scores, cards)

        # 2. Update health & RUL estimation
        health_map = self.rul.estimate_health(t, cards, cusum_scores)

        # 3. Formulate additional alerts from health map
        active_alerts: List[Alert] = list(drift_alerts)
        for kind, h in health_map.items():
            if h.status == "CRITICAL" and h.state != "broken" and h.state != "pm":
                active_alerts.append(Alert(
                    tick=t,
                    station=kind,
                    severity=Severity.CRITICAL,
                    code="IMMINENT_BREAKDOWN_HAZARD",
                    message=(f"Station {kind.upper()} hazard cliff reached! Estimated wear: {h.estimated_wear:.1%}. "
                             f"RUL: {h.rul_ticks} ticks. Failure probability: {h.prob_failure_30t:.1%} in next 30t."),
                    context={"wear": h.estimated_wear, "rul": h.rul_ticks, "prob": h.prob_failure_30t}
                ))

        # Check for buffer bottlenecks
        for kind, card in cards.items():
            q = card.get("queue_before", 0)
            if q >= 4:
                active_alerts.append(Alert(
                    tick=t,
                    station=kind,
                    severity=Severity.WARNING,
                    code="UPSTREAM_BUFFER_SATURATION",
                    message=f"Buffer preceding {kind.upper()} is saturated (queue={q}/4). Upstream stations risk blocking.",
                    context={"queue": q}
                ))

        # 4. Determine probe dispatch recommendations
        probe_candidates = self.detector.recommend_probes(t, cards, probes_left, cusum_scores)

        # 5. Prescriptive recommendations
        recommendations = self.recommender.generate_recommendations(
            t, health_map, open_contracts, spot_price, probes_left, probe_candidates
        )

        # 6. Synthesize combined suggested actions for engine
        suggested_actions: Dict[str, Any] = {}
        for rec in recommendations:
            for k, v in rec.payload.items():
                if k not in suggested_actions:
                    suggested_actions[k] = v
                elif isinstance(v, list) and isinstance(suggested_actions[k], list):
                    # Combine unique items
                    for item in v:
                        if item not in suggested_actions[k]:
                            suggested_actions[k].append(item)
                elif isinstance(v, dict) and isinstance(suggested_actions[k], dict):
                    suggested_actions[k].update(v)

        report = AssistantReport(
            tick=t,
            wip=wip,
            spot_price=spot_price,
            probes_left=probes_left,
            health=health_map,
            active_alerts=active_alerts,
            ranked_recommendations=recommendations,
            suggested_actions=suggested_actions
        )

        self.reports_history.append(report)
        self.all_alerts.extend(active_alerts)
        if "pm" in suggested_actions:
            self.total_pm_actions += len(suggested_actions["pm"])
        if "probes" in suggested_actions:
            self.total_probes_dispatched += len(suggested_actions["probes"])

        return report

    def act(self, obs: Dict[str, Any]) -> Dict[str, Any]:
        """Engine agent interface: acts autonomously or provides operator guidance."""
        report = self.process_tick(obs)
        if self.autonomous:
            return report.suggested_actions
        return {}

    def get_summary(self) -> Dict[str, Any]:
        """Returns cumulative diagnostic summary over all observed ticks."""
        latencies = self.detector.latencies
        mean_lat = round(sum(latencies) / len(latencies), 2) if latencies else None

        alerts_by_sev = {
            "CRITICAL": sum(1 for a in self.all_alerts if a.severity == Severity.CRITICAL),
            "WARNING": sum(1 for a in self.all_alerts if a.severity == Severity.WARNING),
            "INFO": sum(1 for a in self.all_alerts if a.severity == Severity.INFO),
        }

        return {
            "total_ticks_processed": len(self.reports_history),
            "total_alerts": len(self.all_alerts),
            "alerts_by_severity": alerts_by_sev,
            "confirmed_drift_detections": len(latencies),
            "mean_detection_latency_ticks": mean_lat,
            "total_pm_recommended": self.total_pm_actions,
            "total_probes_recommended": self.total_probes_dispatched,
        }
