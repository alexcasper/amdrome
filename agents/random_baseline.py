"""Random baseline agent — uniform legal actions, seeded deterministically.

Used as the floor for character-agent tests (chars must beat this).
Seed derives from the first observation (deterministic per episode).
"""

import random


class Agent:
    def __init__(self, seed=None):
        self.rng = None
        self._seed = seed

    def act(self, obs):
        if self.rng is None:
            blob = f"{sorted(obs['cards'].keys())}|{obs['t']}"
            if self._seed is not None:
                blob += f"|{self._seed}"
            import hashlib
            digest = hashlib.sha256(blob.encode()).digest()
            self.rng = random.Random(int.from_bytes(digest[:8], "big"))
        rng = self.rng
        out = {"bids": {}, "probes": []}
        kinds = sorted(obs["cards"])
        for c in obs["open_contracts"]:
            out["bids"][c["id"]] = round(
                c["unit_price"] * rng.uniform(0.85, 1.05), 2)
        if kinds and rng.random() < 0.3:
            out["probes"] = [rng.choice(kinds)]
        if rng.random() < 0.05 and kinds:
            out["pm"] = [rng.choice(kinds)]
        if rng.random() < 0.08:
            out["buy_input"] = rng.randrange(1, 10)
        if obs["t"] % 48 == 0 and obs["t"] > 0:
            if rng.random() < 0.5:
                out["caps"] = [3] * 6
            else:
                out["caps"] = [8, 3, 2, 2, 2, 1]
        return out


def act(obs):
    return Agent().act(obs)
