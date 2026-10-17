"""CHARACTER: Cheapskate Chen — every dollar is a dollar too many.

Strategy: minimum sampling (no probes — data costs money), inspection on
SKIP (inspectors are expensive), just-in-time inputs (buys exactly 1 unit
the moment the stock hits zero — no warehouse, no holding cost), and
low-ball bids at 0.85x face (never overpay a rival). Buffer caps pinned
to the minimum viable spread.

Failure mode (the one thing Chen can't do): SPEND WHEN IT PAYS. The 0.85x
bids starve him of contracts (rivals take them), skip inspection ships
defects straight to customers (penalties dwarf the saved inspection), and
JIT inputs mean every arrival pays spot — including the spikes.
Deterministic: pure function of the observation.
"""


class Agent:
    def __init__(self, knobs=None):
        self.k = knobs or {}

    def act(self, obs):
        out = {"bids": {}, "inspect_mode": "sample"}
        for c in obs["open_contracts"]:
            out["bids"][c["id"]] = round(c["unit_price"] * 0.90, 2)
        if obs.get("input_stock", 0) == 0:
            out["buy_input"] = 1                # just-in-time, exactly one
        if obs["t"] % 48 == 0 and obs["t"] > 0:
            out["caps"] = [2, 4, 4, 4, 2, 2]    # cheap spread
        return out


def act(obs):
    return Agent().act(obs)
