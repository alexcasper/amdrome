"""Reactive baseline: dynamic SPC + CUSUM-driven PM + margin-aware bidding.

Single-file agent submission. Knobs are class-level so the knob-search
harness (rl/tune_knobs.py) can override them; defaults are the tuned v1
set (see research/ knob-search note).
"""

KNOBS = {
    # tuned v1 (knob-search coarse, t3, 2026-10-13): conservative-PM corner
    "pm_cusum": 4.44,      # PM trigger on CUSUM alarm
    "pm_ops": 40,          # ops-based early PM (off in v1: 40 ops unreachable
                           # pre-reset; kept for knob-search/RL)
    "pm_ops_cusum": 1.9,
    "pm_floor_ticks": 184, # don't PM before this tick (avoid noise PMs)
    "probe_top_k": 2,      # SPC probes per tick on busiest stations
    "margin_lo": 30,       # below this margin: shade hard
    "margin_hi": 80,       # above this: bid face
    "shade_lo": 0.90,
    "shade_hi": 1.00,
    "inspect_full_after": 144,   # full inspection from tick
    "caps_hot_wip": 8,     # entry-heavy when WIP exceeds this
}


class Agent:
    def __init__(self, knobs=None):
        self.k = dict(KNOBS)
        if knobs:
            self.k.update(knobs)
        self.pm_wanted = set()   # latch: request until station enters PM

    def act(self, obs):
        k = self.k
        out = {"bids": {}, "probes": [], "pm": []}
        spot = obs["spot_price"]
        for c in obs["open_contracts"]:
            margin = c["unit_price"] - spot
            if margin > k["margin_hi"]:
                shade = k["shade_hi"]
            elif margin > k["margin_lo"]:
                shade = (k["shade_lo"] + k["shade_hi"]) / 2.0
            else:
                shade = k["shade_lo"]
            out["bids"][c["id"]] = round(c["unit_price"] * shade, 2)

        cards = sorted(obs["cards"].items(),
                       key=lambda kv: (-kv[1]["queue_before"], kv[0]))
        for kind, card in cards[:k["probe_top_k"]]:
            if card["state"] == "proc":
                out["probes"].append(kind)

        if obs["t"] > k["pm_floor_ticks"]:
            for kind, c in obs["cusum"].items():
                ops = obs["cards"][kind]["ops_seen"]
                if c > k["pm_cusum"] or (
                        ops >= k["pm_ops"] and c > k["pm_ops_cusum"]):
                    self.pm_wanted.add(kind)
        # latch: keep requesting until the station actually enters PM/repair
        for kind, card in obs["cards"].items():
            if card["state"] in ("pm", "broken"):
                self.pm_wanted.discard(kind)
        out["pm"] = sorted(self.pm_wanted)

        if obs["t"] % 48 == 0 and obs["t"] > 0:
            out["caps"] = ([8, 3, 2, 2, 2, 1]
                           if obs["wip"] > k["caps_hot_wip"]
                           else [3, 3, 3, 3, 3, 3])
            out["inspect_mode"] = ("full"
                                   if obs["t"] >= k["inspect_full_after"]
                                   else "sample")
        return out


def act(obs):
    return Agent().act(obs)
