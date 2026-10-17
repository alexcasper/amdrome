"""Eager bidder: always bids 4% over face — wins contracts, overpays."""


def act(obs):
    return {"bids": {c["id"]: round(c["unit_price"] * 1.04, 2)
                     for c in obs["open_contracts"]}}
