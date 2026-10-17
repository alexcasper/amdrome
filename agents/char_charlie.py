"""CHARACTER: Checklist Charlie — by-the-book, deaf to every signal.

Strategy: fixed rotation regardless of state. PM every station every
N ticks whether it needs it or not; inspection mode is always FULL (the
book demands it); probes rotate round-robin regardless of drift; bids go
out at exactly face value on every contract (the book's price); buffer
caps stay at the standard even spread.

Failure mode (the one thing Charlie can't do): ADAPT. He services
healthy machines (waste), walks away from any contract above his 90%-of-
face book price (forfeits good deals whenever the market moves), and
never reacts to wear asymmetry, spot dips, or alarms. Deterministic:
pure function of the observation, no randomness.
"""


PM_EVERY = 40          # the book says: service every shift, no exceptions
PROBE_EVERY = 4        # the book says: sample each station every 4th tick


class Agent:
    def __init__(self, knobs=None):
        self.k = knobs or {}

    def act(self, obs):
        kinds = sorted(obs["cards"])          # config-agnostic station set
        out = {"bids": {}, "probes": [], "inspect_mode": "full"}
        for c in obs["open_contracts"]:
            # the book says: never commit above 90% of face value
            out["bids"][c["id"]] = round(c["unit_price"] * 0.90, 2)
        if kinds and obs["t"] % PM_EVERY == 0 and obs["t"] > 0:
            out["pm"] = kinds                 # every station, every time
        if kinds and obs["t"] % PROBE_EVERY == 0:
            out["probes"] = [kinds[(obs["t"] // PROBE_EVERY) % len(kinds)]]
        if obs["t"] % 48 == 0 and obs["t"] > 0:
            out["caps"] = [3] * 6               # the standard spread
        return out


def act(obs):
    return Agent().act(obs)
