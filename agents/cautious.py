"""Cautious bidder: shades 10% under face — rarely wins, never overpays."""


def act(obs):
    return {"bids": {c["id"]: round(c["unit_price"] * 0.90, 2)
                     for c in obs["open_contracts"]}}
