#!/usr/bin/env python3
"""amdrome layout-mechanic prototype (bead amdrome-is5, DESIGN.md §1 + §7).

Measures outcome variance vs decision sensitivity for the LAYOUT mechanic
only: same flow/wear dynamics, different floor placements.

Stateless CLI (DESIGN §8): inputs on argv, one JSON object per episode on
stdout. Pure stdlib — runs on any fleet host with python3, no numpy.

Usage:
  proto_layout.py --policy compact|scattered|clustered --seed N --episodes N
                  [--ticks 336]
"""

import argparse
import hashlib
import json
import math
import random
import sys

# ---------------------------------------------------------------- world spec

GRID_W, GRID_H = 12, 8
ROUTE = ["cut", "form", "weld", "paint", "inspect", "pack"]  # station types
BUFFER_CAP = 4          # jobs per buffer (1-cell kanban card stack)
T_UNIT = 1.0            # transport ticks per manhattan cell
PROC_NOMINAL = 7        # nominal processing ticks per op
SIGMA_PROC = 0.15       # lognormal cycle-time noise
DRIFT_SLOPE = 0.004     # cycle-time inflation per unit of wear
WEAR_PER_OP = 0.01      # (unused placeholder; wear_rate drawn per episode)
TICKS = 336             # one production week (7 shifts x 48)

# hyperprior ranges — drawn once per episode from the *scenario* generator
# (DESIGN §6: the primary anti-tape lever)
HYPER = {
    "lam": (0.05, 0.12),        # job arrivals per tick (Poisson thinning)
    "proc_scale": (0.85, 1.15), # episode-wide processing speed
    "wear_rate": (0.006, 0.016),
    "t_noise": (0.0, 0.10),     # transport time noise fraction
}


def gen_seed(*parts):
    """Deterministic integer seed from parts.

    NEVER seed random.Random with tuples/strings directly: str hashing is
    salted per process (PYTHONHASHSEED), which breaks replay determinism.
    """
    digest = hashlib.sha256("|".join(str(p) for p in parts).encode()).digest()
    return int.from_bytes(digest[:8], "big")


# ------------------------------------------------------------------ placement

def place_compact(rng):
    """Straight line along row 3: inbuf cut b form b weld b paint b insp b pack."""
    ents, x = [], 0
    ents.append(("inbuf", (x, 3))); x += 1
    for i, st in enumerate(ROUTE):
        ents.append((st, (x, 3))); x += 1
        if i < len(ROUTE) - 1:
            ents.append(("buffer", (x, 3))); x += 1
    return ents


def place_scattered(rng):
    """Uniform random distinct cells — the 'bad layout' extreme."""
    cells = [(x, y) for x in range(GRID_W) for y in range(GRID_H)]
    rng.shuffle(cells)
    n = len(ROUTE) * 2  # inbuf + 6 stations + 5 buffers
    picked = cells[:n]
    ents = [("inbuf", picked[0])]
    for i, st in enumerate(ROUTE):
        ents.append((st, picked[1 + 2 * i]))
        if i < len(ROUTE) - 1:
            ents.append(("buffer", picked[2 + 2 * i]))
    return ents


def place_clustered(rng):
    """All entities inside a random 4x4 region — medium quality."""
    x0 = rng.randrange(0, GRID_W - 4)
    y0 = rng.randrange(0, GRID_H - 4)
    cells = [(x0 + dx, y0 + dy) for dx in range(4) for dy in range(4)]
    rng.shuffle(cells)
    n = len(ROUTE) * 2
    picked = cells[:n]
    ents = [("inbuf", picked[0])]
    for i, st in enumerate(ROUTE):
        ents.append((st, picked[1 + 2 * i]))
        if i < len(ROUTE) - 1:
            ents.append(("buffer", picked[2 + 2 * i]))
    return ents


POLICIES = {"compact": place_compact, "scattered": place_scattered,
            "clustered": place_clustered}


def manhattan(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


# ----------------------------------------------------------------- simulation

class Node:
    __slots__ = ("kind", "pos", "queue", "job", "remaining", "wear")

    def __init__(self, kind, pos):
        self.kind = kind
        self.pos = pos
        self.queue = []       # waiting jobs (buffers only)
        self.job = None       # in-process job (stations only)
        self.remaining = 0
        self.wear = 0.0


def run_episode(policy, seed, ticks=TICKS, lam_range=None):
    """One episode. Three generators (DESIGN §6):
    - scenario hyperprior: shared across policies for a given seed (paired)
    - layout: policy-specific (scattered placement varies)
    - flow: per (seed, policy) episode randomness
    """
    lam_lo, lam_hi = lam_range or HYPER["lam"]
    scen = random.Random(gen_seed(seed, "hyper"))
    lay = random.Random(gen_seed(seed, policy, "layout"))
    rng = random.Random(gen_seed(seed, policy, "flow"))

    lam = scen.uniform(lam_lo, lam_hi)
    proc_scale = scen.uniform(*HYPER["proc_scale"])
    wear_rate = scen.uniform(*HYPER["wear_rate"])
    t_noise = scen.uniform(*HYPER["t_noise"])

    ents = POLICIES[policy](lay)
    nodes = [Node(k, p) for k, p in ents]
    inbuf = nodes[0]
    station_nodes = [n for n in nodes if n.kind in ROUTE]
    buf_after, buf_before = {}, {}
    for i, n in enumerate(nodes):
        if n.kind in ROUTE:
            if n.kind != "pack":            # pack has no downstream buffer
                buf_after[n] = nodes[i + 1]
            buf_before[n] = nodes[i - 1]

    jobs = {}               # jid -> job dict (WIP in system)
    next_jid = 0
    completed, cycle_times, wip_sum, rejected = 0, [], 0, 0
    transport_ticks = 0
    blocked_ticks = 0

    for t in range(ticks):
        # arrivals (Poisson thinning)
        if rng.random() < lam:
            if len(inbuf.queue) < BUFFER_CAP:
                j = {"id": next_jid, "state": "wait", "dest": inbuf,
                     "born": t}
                inbuf.queue.append(j)
                jobs[next_jid] = j
                next_jid += 1
            else:
                rejected += 1

        # station admission (fixed order = deterministic)
        for s in station_nodes:
            if s.job is None and buf_before[s].queue:
                j = buf_before[s].queue.pop(0)
                s.job = j
                base = PROC_NOMINAL * proc_scale
                s.remaining = max(1, round(
                    base * math.exp(rng.gauss(0, SIGMA_PROC))
                    * (1 + DRIFT_SLOPE * s.wear)))
                j["state"] = "proc"

        # advance processing; release only if downstream buffer has space
        # (classic blocking — bad layouts pile WIP onto stations)
        for s in station_nodes:
            if s.job is not None:
                s.remaining -= 1
                if s.remaining <= 0:
                    j = s.job
                    s.wear = min(1.0, s.wear + wear_rate)
                    if s.kind == "pack":
                        completed += 1
                        cycle_times.append(t - j["born"])
                        del jobs[j["id"]]
                        s.job = None
                    else:
                        down = buf_after[s]
                        if len(down.queue) < BUFFER_CAP:
                            dist = manhattan(s.pos, down.pos)
                            tt = max(1, round(dist * T_UNIT *
                                      (1 + rng.uniform(-t_noise, t_noise))))
                            j["state"] = "transit"
                            j["dest"] = down
                            j["travel"] = tt
                            s.job = None
                        else:
                            blocked_ticks += 1  # held on station, blocked

        # transit arrival
        arrivals = [jid for jid, j in jobs.items()
                    if j["state"] == "transit"]
        for jid in arrivals:
            j = jobs[jid]
            j["travel"] -= 1
            transport_ticks += 1
            if j["travel"] <= 0:
                j["state"] = "wait"
                j["dest"].queue.append(j)

        wip_sum += len(jobs)

    wear_final = [round(s.wear, 4) for s in station_nodes]
    return {
        "policy": policy, "seed": seed, "ticks": ticks,
        "lam": round(lam, 5), "proc_scale": round(proc_scale, 4),
        "wear_rate": round(wear_rate, 5), "t_noise": round(t_noise, 4),
        "completed": completed,
        "rejected": rejected,
        "cycle_mean": (round(sum(cycle_times) / len(cycle_times), 2)
                       if cycle_times else None),
        "wip_mean": round(wip_sum / ticks, 3),
        "blocked_ticks": blocked_ticks,
        "wear_final": wear_final,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--policy", required=True, choices=sorted(POLICIES))
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--episodes", type=int, default=1)
    ap.add_argument("--ticks", type=int, default=TICKS)
    ap.add_argument("--lam-range", type=float, nargs=2, metavar=("LO", "HI"),
                    default=None, help="override arrival-rate hyperprior")
    args = ap.parse_args()

    for e in range(args.episodes):
        rec = run_episode(args.policy, args.seed + e, args.ticks,
                          lam_range=tuple(args.lam_range)
                          if args.lam_range else None)
        print(json.dumps(rec))
    print(f"[proto_layout] {args.policy} x{args.episodes} done",
          file=sys.stderr)


if __name__ == "__main__":
    main()
