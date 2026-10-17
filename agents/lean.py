"""Lean baseline: fixed kanban rules (single-file agent submission).

Scheduled PM, even buffers, sample inspection, face-value bids with a
simple margin floor. No monitoring, no adaptation.
"""

PM_EVERY = 96            # scheduled PM interval (2 shifts)
PM_STATIONS = ("form", "weld")


def act(obs):
    out = {"bids": {}, "pm": [], "probes": []}
    for c in obs["open_contracts"]:
        if c["unit_price"] - obs["spot_price"] > 30:
            out["bids"][c["id"]] = round(c["unit_price"] * 1.0, 2)

    if obs["t"] % PM_EVERY == 0 and obs["t"] > 0:
        out["pm"] = list(PM_STATIONS)

    if obs["t"] % 48 == 0 and obs["t"] > 0:
        out["caps"] = [3, 3, 3, 3, 3, 3]
        out["inspect_mode"] = "sample"
    return out
