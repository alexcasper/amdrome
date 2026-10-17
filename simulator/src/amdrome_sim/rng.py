"""Deterministic RNG utilities — the engine's only source of randomness.

Rule (DESIGN.md §6): never seed random.Random with tuples/strings directly
(PYTHONHASHSEED salt breaks replay); always sha256 -> int via gen_seed.
"""

import hashlib
import random


def gen_seed(*parts) -> int:
    digest = hashlib.sha256("|".join(str(p) for p in parts).encode()).digest()
    return int.from_bytes(digest[:8], "big")


class RngBank:
    """Named generator bank for one episode.

    Streams (draw order fixed; hyperprior separate so a scenario can be
    logged without replaying the episode):
      hyper  — scenario hyperprior parameters (shared per seed across
               policies for paired comparisons)
      flow   — per-episode dynamics (arrivals, processing, defects...)
      layout — policy-specific placement draws (scatter layouts)
      agents — opponent/market draws (bid competition, absence bursts)
    """

    def __init__(self, seed, policy="default", shared_flow=True):
        self.hyper = random.Random(gen_seed(seed, "hyper"))
        self.layout = random.Random(gen_seed(seed, policy, "layout"))
        if shared_flow:
            self.flow = random.Random(gen_seed(seed, "flow"))
        else:
            self.flow = random.Random(gen_seed(seed, policy, "flow"))
        self.agents = random.Random(gen_seed(seed, "agents"))


# Hyperprior ranges (anti-tape lever #1: episodes differ in these params)
HYPERPRIOR = {
    "lam": (0.08, 0.14),          # job arrivals/tick (near saturation)
    "proc_scale": (0.85, 1.15),
    "wear_rate": (0.014, 0.034),# wear per finished job (calibrated: hot
                         # regime makes prevention economically pivotal)
    "p_defect_base": (0.005, 0.020),
    "t_noise": (0.0, 0.10),       # transport noise fraction
    "spot_p0": (80.0, 120.0),     # input spot price anchor
    "spot_sigma": (0.02, 0.05),   # OU volatility
    "spot_jump": (0.004, 0.02),   # jump probability/tick
    "contract_rate": (0.008, 0.025),  # contract arrivals/tick
    "rival_bid_mu": (0.80, 0.98),    # REBALANCED 2026-10-17 (was 0.85-1.05):
                         # softer rival pool so shade-bidders win their share
}


def draw_hyperprior(rng) -> dict:
    return {k: rng.uniform(*v) for k, v in HYPERPRIOR.items()}
