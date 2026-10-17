"""CHARACTER: Panic Pete — no prevention; reacts only when things break.

Strategy: never schedules PM (prevention is for worriers). The instant
any station card shows "broken" (the andon), Pete PANICS: he dumps a big
input order in (you can never have too much stock after a scare), flips
to full inspection, and fires aggressive 1.04x bids at every open
contract that tick (gotta keep the customer happy NOW). Between panics
he bids face value and does nothing else.

Failure mode (the one thing Pete can't do): PREVENT. Inventory whipsaws
between empty and capped (holding cost + cash tied up), and the plant
still breaks down because nothing is ever maintained. Deterministic:
pure function of the observation.
"""


class Agent:
    def __init__(self, knobs=None):
        self.k = knobs or {}

    def act(self, obs):
        out = {"bids": {}}
        broken = [k for k, c in sorted(obs["cards"].items())
                  if c["state"] == "broken"]
        if broken:
            # PANIC: stock up, inspect everything, win everything
            if obs.get("input_stock", 0) < 8:
                out["buy_input"] = 6
            out["inspect_mode"] = "full"
            for c in obs["open_contracts"]:
                out["bids"][c["id"]] = round(c["unit_price"] * 1.04, 2)
        else:
            for c in obs["open_contracts"]:
                out["bids"][c["id"]] = round(c["unit_price"], 2)
        return out


def act(obs):
    return Agent().act(obs)
