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

    def generate_recommendations(self, t: int, health_map: Dict[str, StationHealth],
                                 open_contracts: List[Dict], spot_price: float,
                                 probes_left: int, probe_candidates: List[str]) -> List[Recommendation]:
        recs = []

        # 1. PM Recommendations (Highest Priority)
        for kind, h in health_map.items():
            if h.status == "CRITICAL" and h.state != "broken" and h.state != "pm":
                # Severe wear hazard detected: recommend immediate PM
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
                    payload={"pm": [kind]}
                ))
            elif h.status == "DRIFTING" and h.state == "idle" and h.queue_before == 0:
                # Opportunistic PM during line starvation
                recs.append(Recommendation(
                    priority=2,
                    action_type=ActionType.TRIGGER_PM,
                    target=kind,
                    rationale=(f"Station {kind.upper()} is currently starved (queue=0) with "
                               f"mild drift (wear ~ {h.estimated_wear:.1%}). Scheduling PM now "
                               f"incurs zero operational disruption to active throughput."),
                    expected_savings=round(AVOIDED_OVERHAUL_SAVINGS * 0.75, 2),
                    payload={"pm": [kind]}
                ))

        # 2. SPC Probe Allocation Recommendations
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

        # 3. Quality & Inspection Mode Rebalancing
        critical_wear_count = sum(1 for h in health_map.values() if h.estimated_wear >= 0.55)
        if critical_wear_count >= 1:
            recs.append(Recommendation(
                priority=3,
                action_type=ActionType.ADJUST_INSPECTION,
                target="inspect",
                rationale=(f"{critical_wear_count} upstream stations exhibit elevated wear (>55%). "
                           f"Defect injection probability is elevated. Recommend escalating inspection "
                           f"mode to 'full' (100% gate) to prevent customer escape penalties ($850/unit)."),
                expected_savings=850.0,
                payload={"inspect_mode": "full"}
            ))

        # 4. Market Contract Bidding
        for c in open_contracts:
            # Bid if contract offers comfortable margin above spot raw materials
            min_margin = spot_price * 1.5
            if c["unit_price"] >= min_margin:
                # Competitive bid slightly under max price to win auction
                bid_price = round(c["unit_price"] * 0.92, 2)
                recs.append(Recommendation(
                    priority=4,
                    action_type=ActionType.SUBMIT_BID,
                    target=str(c["id"]),
                    rationale=(f"Contract #{c['id']} ({c['size']} units @ max ${c['unit_price']}) "
                               f"provides profitable spread above spot raw price (${spot_price:.2f}). "
                               f"Recommend sealed bid at ${bid_price:.2f}."),
                    expected_savings=round((bid_price - spot_price) * c["size"], 2),
                    payload={"bids": {c["id"]: bid_price}}
                ))

        # Sort by priority ascending (1 = highest urgency)
        recs.sort(key=lambda r: (r.priority, -r.expected_savings))
        return recs
