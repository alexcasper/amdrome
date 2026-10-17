"""Remaining Useful Life (RUL) & Weibull hazard forecasting (SPEC_DEMO_PRODUCT.md §2.2)."""

import math
from typing import Dict, Tuple
from .types import StationHealth

# Physics parameters matching amdrome_sim.degradation
H0_HAZARD = 0.0005
BETA_WEAR = 0.15
GAMMA_EXP = 6.0
DRIFT_SLOPE = 0.35      # cycle time inflation at w=1.0 (+35%)
EST_WEAR_PER_OP = 0.012 # typical wear rate per operation


class RULEstimator:
    """Infers hidden mechanical wear and calculates Remaining Useful Life (RUL)."""

    def __init__(self):
        self.wear_estimates = {}        # station -> float in [0.0, 1.0]
        self.last_ops_seen = {}         # station -> int
        self.last_state = {}            # station -> str
        self.last_pm_tick = {}          # station -> tick of last PM or overhaul

    def estimate_health(self, t: int, cards: Dict[str, Dict],
                        cusum_scores: Dict[str, float]) -> Dict[str, StationHealth]:
        """Calculates current wear, hazard rate, RUL, and failure probability for all stations."""
        health_map = {}

        for kind, card in cards.items():
            state = card.get("state", "idle")
            ops = card.get("ops_seen", 0)
            queue_before = card.get("queue_before", 0)
            cusum = cusum_scores.get(kind, 0.0)

            # Track state transitions for wear reset
            prev_state = self.last_state.get(kind, state)
            prev_ops = self.last_ops_seen.get(kind, ops)
            delta_ops = max(0, ops - prev_ops)

            curr_wear = self.wear_estimates.get(kind, 0.0)

            if prev_state == "pm" and state == "idle":
                # PM completed: 92% wear reduction
                curr_wear *= 0.08
                self.last_pm_tick[kind] = t
            elif prev_state == "broken" and state == "idle":
                # Overhaul completed: reset to 0.15
                curr_wear = 0.15
                self.last_pm_tick[kind] = t
            elif state in ("pm", "broken"):
                self.last_pm_tick[kind] = t
            else:
                # Accumulate wear from ops
                curr_wear += delta_ops * EST_WEAR_PER_OP

                # Blend with CUSUM drift signal if positive, but avoid stale CUSUM post-PM
                ticks_since_pm = t - self.last_pm_tick.get(kind, -999)
                if cusum > 1.0 and ticks_since_pm > 35:
                    # Invert drift: CUSUM reflects accumulated cycle inflation
                    inferred_from_drift = min(1.0, (cusum / 3.5) * 0.75)
                    curr_wear = max(curr_wear, inferred_from_drift)

            curr_wear = min(1.0, max(0.0, curr_wear))
            self.wear_estimates[kind] = curr_wear
            self.last_ops_seen[kind] = ops
            self.last_state[kind] = state

            # Weibull hazard calculation: h(w) = h0 + beta * w^gamma
            h = H0_HAZARD + BETA_WEAR * (curr_wear ** GAMMA_EXP)

            # 30-tick breakdown probability: P = 1 - exp(-30 * h)
            prob_30t = 1.0 - math.exp(-30.0 * h)

            # Expected Remaining Useful Life in ticks: RUL = 1 / h
            if h > 0.002:
                rul_ticks = max(1, round(1.0 / h))
            else:
                rul_ticks = None        # safe / negligible hazard

            # Determine categorical health status
            if state in ("broken", "pm"):
                status = "OFFLINE"
            elif prob_30t >= 0.35 or (rul_ticks is not None and rul_ticks <= 30):
                status = "CRITICAL"
            elif prob_30t >= 0.10 or cusum >= 1.8:
                status = "DRIFTING"
            else:
                status = "HEALTHY"

            health_map[kind] = StationHealth(
                kind=kind,
                state=state,
                ops_seen=ops,
                queue_before=queue_before,
                cusum=cusum,
                estimated_wear=round(curr_wear, 3),
                hazard_rate=round(h, 6),
                rul_ticks=rul_ticks,
                prob_failure_30t=round(prob_30t, 4),
                status=status
            )

        return health_map
