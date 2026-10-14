"""Statistical drift detection and probe budgeting (CUSUM, SPEC_DEMO_PRODUCT.md §2.1)."""

from typing import Dict, List, Optional
from .types import Alert, Severity

CUSUM_WARNING = 1.8      # Early warning threshold
CUSUM_ALARM = 3.0        # Statistical drift confirmation threshold


class DriftDetector:
    """Monitors CUSUM drift and strategically allocates SPC sample probes."""

    def __init__(self):
        self.last_probed = {}           # station -> tick
        self.drift_onset_tick = {}      # station -> tick when drift first noted
        self.drift_detected_tick = {}   # station -> tick when alarm confirmed
        self.confirmed_drift = set()
        self.latencies = []

    def update(self, t: int, cusum_scores: Dict[str, float],
               cards: Dict[str, Dict]) -> List[Alert]:
        """Update drift tracking from observation and return any drift alerts."""
        alerts = []

        for kind, score in cusum_scores.items():
            card = cards.get(kind, {})
            state = card.get("state", "idle")

            # Check for drift onset
            if score >= CUSUM_WARNING and kind not in self.drift_onset_tick:
                self.drift_onset_tick[kind] = t

            # Check for confirmed drift breach
            if score >= CUSUM_ALARM:
                if kind not in self.confirmed_drift:
                    self.confirmed_drift.add(kind)
                    self.drift_detected_tick[kind] = t
                    onset = self.drift_onset_tick.get(kind, t)
                    latency = max(0, t - onset)
                    self.latencies.append(latency)

                    alerts.append(Alert(
                        tick=t,
                        station=kind,
                        severity=Severity.CRITICAL,
                        code="CONFIRMED_CYCLE_DRIFT",
                        message=(f"Station {kind.upper()} confirmed statistically significant "
                                 f"cycle-time drift (CUSUM={score:.2f} > {CUSUM_ALARM}). "
                                 f"Detection latency: {latency} ticks."),
                        context={"cusum": score, "latency": latency, "state": state}
                    ))
            elif score >= CUSUM_WARNING:
                alerts.append(Alert(
                    tick=t,
                    station=kind,
                    severity=Severity.WARNING,
                    code="ELEVATED_CYCLE_VARIANCE",
                    message=(f"Station {kind.upper()} exhibiting early cycle-time dilation "
                             f"(CUSUM={score:.2f}). Additional sampling advised."),
                    context={"cusum": score, "state": state}
                ))

            # If station has entered PM or overhaul, clear drift flags
            if state in ("pm", "broken"):
                self.confirmed_drift.discard(kind)
                self.drift_onset_tick.pop(kind, None)
                self.drift_detected_tick.pop(kind, None)

        return alerts

    def recommend_probes(self, t: int, cards: Dict[str, Dict],
                         probes_left: int, cusum_scores: Dict[str, float]) -> List[str]:
        """Prioritizes station probe dispatches within remaining shift budget."""
        if probes_left <= 0:
            return []

        # Only active processing stations can be probed
        candidates = [k for k, v in cards.items() if v.get("state") == "proc"]
        if not candidates:
            return []

        def probe_priority(kind: str) -> float:
            score = 0.0
            # Higher score if already drifting to confirm or track recovery
            score += cusum_scores.get(kind, 0.0) * 2.0
            # Higher score if not probed recently
            ticks_since = t - self.last_probed.get(kind, -100)
            score += min(ticks_since * 0.1, 5.0)
            # High-impact stations (weld, form, paint)
            if kind in ("weld", "form", "paint"):
                score += 2.0
            return score

        candidates.sort(key=probe_priority, reverse=True)
        recommended = candidates[:probes_left]

        for k in recommended:
            self.last_probed[k] = t

        return recommended
