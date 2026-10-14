"""amdrome_sim — pure-python factory simulation engine (v1 core).

Modules: rng (determinism), floor (grid), stations (line), degradation
(wear/hazard/PM), quality (defects/inspection), labour (roster/techs),
market (spot/contracts/bids), kanban (partial observability), core
(episode coordinator).
"""

from .core import Engine, NullAgent, TICKS, SHIFT  # noqa: F401

__version__ = "0.1.0"
