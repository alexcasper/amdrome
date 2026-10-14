"""Market: spot input prices (OU + jumps), stochastic contracts, sealed-bid
auction, delivery deadlines with penalties.

This is the anti-tape backbone (research/2026-10-13-acceptance-gates.md):
bidding under volatile prices = symmetric penalties, high decision density.
"""

import math

LATE_PENALTY_PER_TICK = 15.0
BID_WINDOW = 8           # ticks a contract stays open for bids
SPOT_SELL_FRAC = 0.75     # uncontracted units sell on the spot market
SPOT_DEFECT_PENALTY = 400.0


class SpotMarket:
    """Mean-reverting price with jumps; price-taker factories."""

    def __init__(self, p0, sigma, jump_p, rng):
        self.p = p0
        self.anchor = p0
        self.sigma = sigma
        self.jump_p = jump_p
        self.rng = rng
        self.history = [p0]

    def tick(self):
        ou = 0.05 * (self.anchor - self.p) + self.rng.gauss(0, self.sigma * 40)
        self.p = max(20.0, self.p + ou)
        if self.rng.random() < self.jump_p:
            self.p = max(20.0, self.p * self.rng.uniform(0.80, 1.25))
        self.history.append(round(self.p, 2))
        return self.p


class Contract:
    def __init__(self, cid, size, unit_price, deadline, penalty_ppm,
                 quality_floor):
        self.id = cid
        self.size = size                # units to deliver
        self.unit_price = unit_price    # $/unit if won
        self.deadline = deadline        # tick
        self.penalty_ppm = penalty_ppm  # $ per escaped defect unit
        self.quality_floor = quality_floor  # max PPM fraction accepted

    def __repr__(self):
        return (f"Contract({self.id}, n={self.size}, p={self.unit_price}, "
                f"d={self.deadline})")


def spawn_contracts(t, rate, rng, ticks, next_cid):
    """Poisson-thinned contract arrivals; returns (list, updated next_cid).

    IDs are caller-scoped: NEVER class-level counters (cross-engine global
    state breaks same-seed replay determinism within one process).
    """
    out = []
    if rng.random() < rate:
        size = 1 + rng.randrange(1, 5)
        price = round(rng.uniform(300, 480), 2)
        deadline = min(ticks - 1, t + rng.randrange(120, 300))
        penalty = round(rng.uniform(400, 1200), 2)
        qfloor = round(rng.uniform(0.01, 0.05), 4)
        out.append(Contract(next_cid, size, price, deadline, penalty, qfloor))
        next_cid += 1
    return out, next_cid


def resolve_bid(contract, my_bid, rival_bid_mu, rng):
    """Sealed first-price vs one drawn rival. Returns True if factory wins.

    rival bid = contract.unit_price * mu * lognoise — under-drawing the
    rival's price when the scenario moved is the symmetric anti-tape
    penalty: bid too high (memorized) and you overpay; too low and the
    rival takes the contract.
    """
    rival = contract.unit_price * rival_bid_mu \
        * math.exp(rng.gauss(0, 0.08))
    return my_bid >= rival, round(rival, 2)


def settle(contract, delivered_clean, delivered_defective, delivered_at):
    """Revenue and penalties at settlement (deadline or contract clear)."""
    revenue = delivered_clean * contract.unit_price
    late_ticks = max(0, delivered_at - contract.deadline)
    late_cost = late_ticks * LATE_PENALTY_PER_TICK * contract.size / 4.0
    escape_cost = delivered_defective * contract.penalty_ppm
    return round(revenue - late_cost - escape_cost, 2)
