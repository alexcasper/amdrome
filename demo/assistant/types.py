"""Data structures for the Operator Assistant (bead amdrome-a3j, SPEC_DEMO_PRODUCT.md)."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class Severity(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


class ActionType(str, Enum):
    TRIGGER_PM = "TRIGGER_PM"
    ALLOCATE_PROBE = "ALLOCATE_PROBE"
    ADJUST_INSPECTION = "ADJUST_INSPECTION"
    REBALANCE_BUFFERS = "REBALANCE_BUFFERS"
    SUBMIT_BID = "SUBMIT_BID"


@dataclass
class Alert:
    tick: int
    station: Optional[str]
    severity: Severity
    code: str
    message: str
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Recommendation:
    priority: int                   # 1 (urgent) to 5 (opportunistic)
    action_type: ActionType
    target: Optional[str]           # station kind, contract id, etc.
    rationale: str
    expected_savings: float         # estimated net financial impact in $
    payload: Dict[str, Any]         # action format matching engine contract


@dataclass
class StationHealth:
    kind: str
    state: str
    ops_seen: int
    queue_before: int
    cusum: float
    estimated_wear: float           # [0.0, 1.0]
    hazard_rate: float              # per-tick failure probability
    rul_ticks: Optional[int]        # estimated remaining useful life in ticks
    prob_failure_30t: float         # probability of breakdown in next 30 ticks
    status: str                     # "HEALTHY", "DRIFTING", "CRITICAL", "OFFLINE"


@dataclass
class AssistantReport:
    tick: int
    wip: int
    spot_price: float
    probes_left: int
    health: Dict[str, StationHealth]
    active_alerts: List[Alert]
    ranked_recommendations: List[Recommendation]
    suggested_actions: Dict[str, Any]
