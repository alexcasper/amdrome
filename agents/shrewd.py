"""Shrewd baseline (single-file agent submission).

Adaptive capacity + monitoring policy:
- bids conditioned on spot price vs contract price (margin-aware)
- spends full SPC budget on the busiest stations
- PM when CUSUM drift accumulates
- reallocates buffers toward the entry as demand materializes
"""


def act(obs):
    out = {"bids": {}, "probes": [], "pm": []}
    spot = obs["spot_price"]
    for c in obs["open_contracts"]:
        # input cost per unit ~ spot; bid only with margin, shade by price
        margin = c["unit_price"] - spot
        if margin > 60:
            bid = c["unit_price"] * 1.00
        elif margin > 20:
            bid = c["unit_price"] * 0.96
        else:
            bid = c["unit_price"] * 0.90
        out["bids"][c["id"]] = round(bid, 2)

    cards = sorted(obs["cards"].items(),
                   key=lambda kv: (-kv[1]["queue_before"], kv[0]))
    for kind, card in cards[:3]:
        if card["state"] == "proc":
            out["probes"].append(kind)

    for kind, c in obs["cusum"].items():
        if c > 1.8:
            out["pm"].append(kind)

    if obs["t"] % 48 == 0 and obs["t"] > 0:
        # demand high -> protect entry buffer; else spread
        lam_h = obs["wip"] / max(1, obs["t"])
        if lam_h > 0.03:
            out["caps"] = [8, 3, 2, 2, 2, 1]
        else:
            out["caps"] = [3, 3, 3, 3, 3, 3]
        out["inspect_mode"] = "full" if obs["t"] > 200 else "sample"
    return out
