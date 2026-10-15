"""Prescriptive Recommendation Engine & Root-Cause Attribution (SPEC_DEMO_PRODUCT.md §2.3)."""

from typing import Any, Dict, List
from .types import ActionType, Recommendation, StationHealth

PM_COST = 250.0
BREAKDOWN_COST = 1200.0
SCRAP_COST = 300.0
DOWNTIME_TICK_COST = 5.0
AVOIDED_OVERHAUL_SAVINGS = BREAKDOWN_COST + SCRAP_COST + (24 * DOWNTIME_TICK_COST) - PM_COST  # ~$1,370


class Recommender:
    """Evaluates plant telemetry and generates ranked, high-ROI prescriptive actions."""

    def __init__(self, pm_floor_ticks: int = 160, pm_cooldown_ticks: int = 60, pm_cusum_thresh: float = 3.5):
        self.pm_floor_ticks = pm_floor_ticks
        self.pm_cooldown_ticks = pm_cooldown_ticks
        self.pm_cusum_thresh = pm_cusum_thresh
        self.pm_wanted = set()          # latch: request until station enters PM
        self.last_pm_tick = {}          # station -> tick of last PM entry
        self.pm_completed_count = {}    # station -> count of PMs initiated

    def generate_recommendations(self, t: int, health_map: Dict[str, StationHealth],
                                 open_contracts: List[Dict], spot_price: float,
                                 probes_left: int, probe_candidates: List[str]) -> List[Recommendation]:
        recs = []

        # 1. PM Latch Update: unlatch stations that entered PM or repair
        for kind, h in health_map.items():
            if kind in self.pm_wanted and h.state in ("pm", "broken"):
                self.pm_wanted.discard(kind)
                self.last_pm_tick[kind] = t
                self.pm_completed_count[kind] = self.pm_completed_count.get(kind, 0) + 1

        # 2. PM Evaluation: add candidates to pm_wanted if qualified
        for kind, h in health_map.items():
            if kind in self.pm_wanted or h.state in ("pm", "broken"):
                continue
            if self.pm_completed_count.get(kind, 0) >= 1:
                continue
            if (t - self.last_pm_tick.get(kind, -999)) < self.pm_cooldown_ticks:
                continue
            if sum(self.pm_completed_count.values()) >= 2:
                continue

            # Qualifying criteria:
            # - Severe wear hazard (wear >= 0.75 or 30t breakdown prob >= 50%)
            # - Sustained post-floor CUSUM/wear drift (t >= pm_floor_ticks and wear >= 0.60 and cusum >= 3.5 or cusum >= 4.0)
            severe_wear = (h.estimated_wear >= 0.75 or h.prob_failure_30t >= 0.50)
            sustained_drift = (t >= self.pm_floor_ticks and (
                (h.estimated_wear >= 0.60 and (h.cusum >= self.pm_cusum_thresh or h.prob_failure_30t >= 0.35))
                or h.cusum >= 4.0
            ))

            if severe_wear or sustained_drift:
                self.pm_wanted.add(kind)

        # 3. Emit PM Recommendations (Highest Priority)
        for kind in sorted(self.pm_wanted):
            h = health_map[kind]
            rul_desc = f"{h.rul_ticks} ticks" if h.rul_ticks is not None else "imminent"
            recs.append(Recommendation(
                priority=1,
                action_type=ActionType.TRIGGER_PM,
                target=kind,
                rationale=(f"Station {kind.upper()} wear estimated at {h.estimated_wear:.1%}. "
                           f"Weibull failure probability is {h.prob_failure_30t:.1%} in next 30t "
                           f"(RUL ~ {rul_desc}). Proactive PM averts catastrophic seizure, "
                           f"in-process scrap write-off, and ~28 ticks of unplanned downtime."),
                expected_savings=round(AVOIDED_OVERHAUL_SAVINGS, 2),
                payload={"pm": sorted(self.pm_wanted)}
            ))

        # 4. SPC Probe Allocation Recommendations
        if probes_left > 0 and probe_candidates:
            recs.append(Recommendation(
                priority=2,
                action_type=ActionType.ALLOCATE_PROBE,
                target=probe_candidates[0],
                rationale=(f"Telemetry budget remaining ({probes_left} probes). Allocating probe to "
                           f"station {probe_candidates[0].upper()} to confirm cycle-time variance."),
                expected_savings=150.0,
                payload={"probes": probe_candidates}
            ))

        # 5. Quality & Inspection Mode Rebalancing
        critical_wear_count = sum(1 for h in health_map.values() if h.estimated_wear >= 0.55)
        if critical_wear_count >= 1 or t >= 144:
            recs.append(Recommendation(
                priority=3,
                action_type=ActionType.ADJUST_INSPECTION,
                target="inspect",
                rationale=(f"Elevated wear detected or late shift (t={t}). Defect injection probability "
                           f"is elevated. Recommend escalating inspection mode to 'full' (100% gate) "
                           f"to prevent customer escape penalties ($850/unit)."),
                expected_savings=850.0,
                payload={"inspect_mode": "full"}
            ))

        # 6. Market Contract Bidding (margin-aware bidding matching anti-tape backbone)
        for c in open_contracts:
            margin = c["unit_price"] - spot_price
            if margin > 80.0:
                shade = 1.00
            elif margin > 30.0:
                shade = 0.95
            else:
                shade = 0.90
            bid_price = round(c["unit_price"] * shade, 2)
            recs.append(Recommendation(
                priority=4,
                action_type=ActionType.SUBMIT_BID,
                target=str(c["id"]),
                rationale=(f"Contract #{c['id']} ({c['size']} units @ max ${c['unit_price']}) "
                           f"offers ${margin:.2f}/unit margin over spot raw price (${spot_price:.2f}). "
                           f"Bidding ${bid_price:.2f} ({shade:.0%} face value)."),
                expected_savings=round((bid_price - spot_price) * c["size"], 2),
                payload={"bids": {c["id"]: bid_price}}
            ))

        # 7. Buffer Capacity Dynamic Rebalancing (shift boundary)
        if t % 48 == 0 and t > 0:
            total_wip = sum(h.queue_before for h in health_map.values())
            caps = [8, 3, 2, 2, 2, 1] if total_wip > 8 else [3, 3, 3, 3, 3, 3]
            recs.append(Recommendation(
                priority=5,
                action_type=ActionType.REBALANCE_BUFFERS,
                target="buffers",
                rationale=f"Shift boundary at tick {t}. Rebalancing buffer slots to {caps} (WIP={total_wip}).",
                expected_savings=100.0,
                payload={"caps": caps}
            ))

        # Sort by priority ascending (1 = highest urgency)
        recs.sort(key=lambda r: (r.priority, -r.expected_savings))
        return recs
