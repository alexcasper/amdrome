#!/usr/bin/env python3
"""amdrome degradation & monitoring prototype (bead amdrome-96z / amdrome-is5).

Measures outcome variance vs decision sensitivity for DEGRADATION,
KANBAN MONITORING (SPC CUSUM), and PREVENTIVE MAINTENANCE.
Includes drift-detection latency measurement across sample budgets (B=4, 8, 16).

Stateless CLI (DESIGN §8): inputs on argv, one JSON object per episode on stdout.
Pure stdlib — runs on any fleet host with python3, no external dependencies.

Usage:
  proto_degradation.py --policy run_to_failure|periodic_pm|spc_reactive
                       --seed N --episodes N [--ticks 336] [--sample-budget 4|8|16]
"""

import argparse
import hashlib
import json
import math
import random
import sys

# ---------------------------------------------------------------- world spec

GRID_W, GRID_H = 12, 8
ROUTE = ["cut", "form", "weld", "paint", "inspect", "pack"]
BUFFER_CAP = 4          # jobs per buffer
T_UNIT = 1.0            # transport ticks per manhattan cell
PROC_NOMINAL = 7        # nominal processing ticks per op
SIGMA_PROC = 0.15       # lognormal cycle-time noise
DRIFT_SLOPE = 0.35      # cycle-time inflation at w=1.0 (+35%)
TICKS = 336             # one production week (7 shifts x 48)

# Economic parameters ($)
REV_PER_UNIT = 350.0    # revenue per clean delivered unit
COST_PM = 250.0         # preventive maintenance cost
COST_BREAKDOWN = 1200.0 # catastrophic emergency overhaul cost
COST_SCRAP = 300.0      # scrapped in-process workpiece write-off
PENALTY_ESCAPE = 850.0  # customer escape penalty per defective unit shipped
DOWNTIME_COST_TICK = 5.0# line idling cost per tick of unplanned downtime

# Failure & Wear Physics
H0_HAZARD = 0.0005      # baseline hazard per tick
BETA_WEAR = 0.045       # wear-dependent hazard multiplier (Weibull convex)
GAMMA_EXP = 3.0         # convexity exponent
PM_DURATION = 12        # ticks required for PM
DRIFT_ONSET_WEAR = 0.35 # wear threshold defining start of detectable drift

# Hyperpriors (drawn once per episode from scenario generator)
HYPER = {
    "lam": (0.08, 0.14),        # arrival rate (near saturation)
    "proc_scale": (0.85, 1.15), # episode processing speed
    "wear_rate": (0.008, 0.020),# wear accumulated per finished job
    "p_defect_base": (0.005, 0.020),
}


def gen_seed(*parts):
    """Deterministic integer seed from string/tuple components via sha256."""
    digest = hashlib.sha256("|".join(str(p) for p in parts).encode()).digest()
    return int.from_bytes(digest[:8], "big")


# ------------------------------------------------------------------ topology

def place_compact():
    """Straight line along row 3: inbuf cut b form b weld b paint b insp b pack."""
    ents, x = [], 0
    ents.append(("inbuf", (x, 3))); x += 1
    for i, st in enumerate(ROUTE):
        ents.append((st, (x, 3))); x += 1
        if i < len(ROUTE) - 1:
            ents.append(("buffer", (x, 3))); x += 1
    return ents


def manhattan(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


# ----------------------------------------------------------------- node & job

class StationNode:
    __slots__ = ("kind", "pos", "job", "remaining", "wear", "state",
                 "downtime_rem", "last_proc_actual", "cusum", "samples_seen",
                 "drift_onset_tick", "detected", "last_sampled_tick")

    def __init__(self, kind, pos):
        self.kind = kind
        self.pos = pos
        self.job = None
        self.remaining = 0
        self.wear = 0.0
        self.state = "idle"       # idle, proc, blocked, pm, broken
        self.downtime_rem = 0
        self.last_proc_actual = PROC_NOMINAL
        self.cusum = 0.0
        self.samples_seen = 0
        self.drift_onset_tick = None
        self.detected = False
        self.last_sampled_tick = -999


class BufferNode:
    __slots__ = ("kind", "pos", "queue")

    def __init__(self, kind, pos):
        self.kind = kind
        self.pos = pos
        self.queue = []


# ----------------------------------------------------------------- simulation

def run_episode(policy, seed, ticks=TICKS, sample_budget=8):
    """One paired episode testing degradation, wear drift, and PM policies."""
    scen = random.Random(gen_seed(seed, "hyper"))
    rng = random.Random(gen_seed(seed, policy, "flow"))

    lam = scen.uniform(*HYPER["lam"])
    proc_scale = scen.uniform(*HYPER["proc_scale"])
    wear_rate = scen.uniform(*HYPER["wear_rate"])
    p_defect_base = scen.uniform(*HYPER["p_defect_base"])

    ents = place_compact()
    inbuf = BufferNode(ents[0][0], ents[0][1])
    nodes = [inbuf]
    station_map = {}

    for k, p in ents[1:]:
        if k == "buffer":
            nodes.append(BufferNode(k, p))
        else:
            st = StationNode(k, p)
            nodes.append(st)
            station_map[k] = st

    st_nodes = [n for n in nodes if isinstance(n, StationNode)]
    buf_before = {}
    buf_after = {}
    for i, n in enumerate(nodes):
        if isinstance(n, StationNode):
            buf_before[n] = nodes[i - 1]
            if n.kind != "pack":
                buf_after[n] = nodes[i + 1]

    jobs = {}
    next_jid = 0
    completed_clean = 0
    completed_defective = 0
    scrapped_jobs = 0
    breakdowns_count = 0
    pm_count = 0
    unplanned_downtime = 0
    planned_downtime = 0
    spc_probes_spent = 0
    shift_probes_remaining = sample_budget
    cycle_times = []

    # Detection latency tracking
    detection_latencies = []
    detections_count = 0
    missed_detections = 0
    false_alarms = 0

    # Policy state tracking
    ticks_since_pm = {s.kind: 0 for s in st_nodes}

    for t in range(ticks):
        # Shift rollover every 48 ticks: reset telemetry probe budget
        if t % 48 == 0:
            shift_probes_remaining = sample_budget

        # 1. Job arrivals
        if rng.random() < lam:
            if len(inbuf.queue) < BUFFER_CAP:
                j = {
                    "id": next_jid, "state": "wait", "dest": inbuf,
                    "born": t, "has_defect": False
                }
                inbuf.queue.append(j)
                jobs[next_jid] = j
                next_jid += 1

        # Track drift onset
        for s in st_nodes:
            if s.wear >= DRIFT_ONSET_WEAR and s.drift_onset_tick is None:
                s.drift_onset_tick = t
                s.detected = False

        # 2. Operator / Policy decision phase
        if policy == "run_to_failure":
            pass  # never schedules PM; only fixes hard breakdowns
        elif policy == "periodic_pm":
            for s in st_nodes:
                if s.kind in ("form", "weld") and s.state in ("idle", "proc") and s.downtime_rem <= 0:
                    ticks_since_pm[s.kind] += 1
                    if ticks_since_pm[s.kind] >= 90 and s.job is None:
                        s.state = "pm"
                        s.downtime_rem = PM_DURATION
                        ticks_since_pm[s.kind] = 0
                        pm_count += 1
        elif policy.startswith("spc_reactive"):
            # Sort candidate stations by time since last sample (round-robin / risk prioritization)
            candidates = [s for s in st_nodes if s.kind in ("form", "weld", "cut") and s.state == "proc"]
            candidates.sort(key=lambda s: s.last_sampled_tick)

            for s in candidates:
                if shift_probes_remaining > 0:
                    # probe cycle time with sensor noise
                    meas = s.last_proc_actual + rng.gauss(0, 0.4)
                    spc_probes_spent += 1
                    shift_probes_remaining -= 1
                    s.samples_seen += 1
                    s.last_sampled_tick = t

                    # CUSUM drift update: standard score against nominal
                    z = (meas - PROC_NOMINAL * proc_scale) / (PROC_NOMINAL * SIGMA_PROC)
                    s.cusum = max(0.0, s.cusum + z - 0.4)

                    # Check detection threshold
                    if s.cusum > 3.2:
                        if not s.detected:
                            detections_count += 1
                            s.detected = True
                            if s.drift_onset_tick is not None:
                                detection_latencies.append(t - s.drift_onset_tick)
                            else:
                                false_alarms += 1

                        # If buffer cushion exists, schedule PM
                        down_buf = buf_after.get(s)
                        if (down_buf is None or len(down_buf.queue) >= 1) and s.state == "proc" and s.remaining <= 1:
                            s.state = "pm"
                            s.downtime_rem = PM_DURATION
                            s.cusum = 0.0
                            pm_count += 1

        # 3. Station maintenance & breakdown recovery
        for s in st_nodes:
            if s.downtime_rem > 0:
                s.downtime_rem -= 1
                if s.state == "pm":
                    planned_downtime += 1
                elif s.state == "broken":
                    unplanned_downtime += 1

                if s.downtime_rem <= 0:
                    if s.state == "pm":
                        s.wear = max(0.0, s.wear * 0.08)  # 92% wear reset
                    elif s.state == "broken":
                        s.wear = 0.15                     # overhaul reset
                    s.state = "idle"
                    s.drift_onset_tick = None
                    s.detected = False
                    s.cusum = 0.0

        # 4. Station admission
        for s in st_nodes:
            if s.state == "idle" and s.job is None and buf_before[s].queue:
                j = buf_before[s].queue.pop(0)
                s.job = j
                s.state = "proc"
                base = PROC_NOMINAL * proc_scale
                dur = max(1, round(
                    base * math.exp(rng.gauss(0, SIGMA_PROC))
                    * (1.0 + DRIFT_SLOPE * s.wear)
                ))
                s.remaining = dur
                s.last_proc_actual = dur
                j["state"] = "proc"

        # 5. Station processing & breakdown hazard check
        for s in st_nodes:
            if s.state == "proc" and s.job is not None:
                # Hazard check: Weibull breakdown
                hazard = H0_HAZARD + BETA_WEAR * (s.wear ** GAMMA_EXP)
                if rng.random() < hazard:
                    # Breakdown occurs!
                    breakdowns_count += 1
                    if s.drift_onset_tick is not None and not s.detected:
                        missed_detections += 1

                    s.state = "broken"
                    repair_time = max(16, round(math.exp(rng.gauss(3.1, 0.35))))
                    s.downtime_rem = repair_time
                    scrapped_jobs += 1
                    del jobs[s.job["id"]]
                    s.job = None
                    s.remaining = 0
                    continue

                s.remaining -= 1
                if s.remaining <= 0:
                    # Operation completed
                    j = s.job
                    s.wear = min(1.0, s.wear + wear_rate)

                    # Defect injection
                    p_def = min(0.40, p_defect_base + 0.08 * (s.wear ** 2))
                    if rng.random() < p_def:
                        j["has_defect"] = True

                    # Inspection station handling
                    if s.kind == "inspect":
                        # sample mode (20%)
                        if rng.random() < 0.20:
                            if j["has_defect"] and rng.random() < 0.85:
                                scrapped_jobs += 1
                                del jobs[j["id"]]
                                s.job = None
                                s.state = "idle"
                                continue

                    # Advance downstream
                    if s.kind == "pack":
                        if j["has_defect"]:
                            completed_defective += 1
                        else:
                            completed_clean += 1
                        cycle_times.append(t - j["born"])
                        del jobs[j["id"]]
                        s.job = None
                        s.state = "idle"
                    else:
                        down = buf_after[s]
                        if len(down.queue) < BUFFER_CAP:
                            dist = manhattan(s.pos, down.pos)
                            tt = max(1, round(dist * T_UNIT))
                            j["state"] = "transit"
                            j["dest"] = down
                            j["travel"] = tt
                            s.job = None
                            s.state = "idle"
                        else:
                            s.state = "blocked"

        # 6. Transit arrivals
        arrivals = [jid for jid, j in jobs.items() if j["state"] == "transit"]
        for jid in arrivals:
            j = jobs[jid]
            j["travel"] -= 1
            if j["travel"] <= 0:
                j["state"] = "wait"
                j["dest"].queue.append(j)

        # 7. Unblock stations if downstream opened
        for s in st_nodes:
            if s.state == "blocked" and s.job is not None:
                down = buf_after.get(s)
                if down and len(down.queue) < BUFFER_CAP:
                    j = s.job
                    dist = manhattan(s.pos, down.pos)
                    tt = max(1, round(dist * T_UNIT))
                    j["state"] = "transit"
                    j["dest"] = down
                    j["travel"] = tt
                    s.job = None
                    s.state = "idle"

    # Compute financial score
    revenue = completed_clean * REV_PER_UNIT
    cost_pm_total = pm_count * COST_PM
    cost_breakdown_total = breakdowns_count * COST_BREAKDOWN
    cost_scrap_total = scrapped_jobs * COST_SCRAP
    cost_escapes_total = completed_defective * PENALTY_ESCAPE
    cost_downtime_total = unplanned_downtime * DOWNTIME_COST_TICK

    net_profit = (revenue
                  - cost_pm_total
                  - cost_breakdown_total
                  - cost_scrap_total
                  - cost_escapes_total
                  - cost_downtime_total)

    mean_latency = (round(sum(detection_latencies) / len(detection_latencies), 2)
                    if detection_latencies else None)

    return {
        "policy": policy,
        "sample_budget": sample_budget,
        "seed": seed,
        "ticks": ticks,
        "completed_clean": completed_clean,
        "completed_defective": completed_defective,
        "scrapped_jobs": scrapped_jobs,
        "breakdowns_count": breakdowns_count,
        "pm_count": pm_count,
        "unplanned_downtime": unplanned_downtime,
        "planned_downtime": planned_downtime,
        "spc_probes_spent": spc_probes_spent,
        "revenue": round(revenue, 2),
        "net_profit": round(net_profit, 2),
        "cycle_mean": round(sum(cycle_times) / len(cycle_times), 2) if cycle_times else None,
        "detections_count": detections_count,
        "missed_detections": missed_detections,
        "false_alarms": false_alarms,
        "mean_detection_latency": mean_latency,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--policy", required=True)
    ap.add_argument("--sample-budget", type=int, default=8,
                    help="SPC sample budget per 48-tick shift")
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--episodes", type=int, default=1)
    ap.add_argument("--ticks", type=int, default=TICKS)
    args = ap.parse_args()

    for e in range(args.episodes):
        rec = run_episode(args.policy, args.seed + e, args.ticks,
                          sample_budget=args.sample_budget)
        print(json.dumps(rec))
    print(f"[proto_degradation] {args.policy} (budget={args.sample_budget}) x{args.episodes} done",
          file=sys.stderr)


if __name__ == "__main__":
    main()
