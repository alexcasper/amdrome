"""CHARACTER: Max Milliard — if some is good, everything is better.

Strategy: maximum everything. PM every station every 40 ticks AND on any
CUSUM tick above 1.0 (can't be too careful); probes on up to three
stations every tick (spend the whole SPC budget); inspection permanently
FULL; staffing piles workers on stations (2 per station where the roster
allows — headcount is a strength); bids go out at 1.02x face (we do NOT
lose contracts); entry buffer maxed because throughput is king.

Failure mode (the one thing Max can't do): STOP. PM spend, overpaid bids
and offline servicing mount into fixed costs that eat the margin: the
plant is reliable and clean and barely profitable. Deterministic: pure
function of the observation.
"""

PM_EVERY = 40


class Agent:
    def __init__(self, knobs=None):
        self.k = knobs or {}

    def act(self, obs):
        kinds = sorted(obs["cards"])
        out = {"bids": {}, "probes": [], "inspect_mode": "full"}
        for c in obs["open_contracts"]:
            out["bids"][c["id"]] = round(c["unit_price"] * 1.02, 2)
        # spend the entire SPC budget, every tick, on the busiest stations
        busy = sorted(kinds, key=lambda k: -obs["cards"][k]["queue_before"])
        out["probes"] = [k for k in busy[:3]
                         if obs["cards"][k]["state"] == "proc"]
        pm = []
        if kinds and obs["t"] % PM_EVERY == 0 and obs["t"] > 0:
            pm = list(kinds)
        pm += [k for k, c in obs["cusum"].items() if c > 1.0]
        if pm:
            out["pm"] = sorted(set(pm))
        # max staffing: double-staff from the roster of present workers
        roster = obs.get("roster") or {}
        present = roster.get("present")
        if present and kinds and obs["t"] % 48 == 0 and obs["t"] > 0:
            per = max(1, present // max(1, len(kinds)))
            counts = {}
            left = present
            for k in kinds:
                take = min(per, left)
                counts[k] = take
                left -= take
            i = 0
            while left > 0 and kinds:
                counts[kinds[i % len(kinds)]] += 1
                left -= 1
                i += 1
            out["assign"] = counts
            out["caps"] = [8, 3, 2, 2, 2, 1]   # entry maxed: throughput!
        return out


def act(obs):
    return Agent().act(obs)
