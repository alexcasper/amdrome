"""Blind baseline (single-file agent submission).

Run-to-failure: fixed bids at face value, no monitoring, no PM.
This is the floor the operator-assistant demo must beat.
"""


def act(obs):
    out = {"bids": {}}
    for c in obs["open_contracts"]:
        out["bids"][c["id"]] = c["unit_price"]
    return out
