"""Degradation: wear accumulation, cycle drift, hazard cliff, PM/repair.

Prototype-validated (research/2026-10-13-degradation-variance.md): drift
must be SPC-detectable before the hazard cliff; PM timing is pivotal when
wear-rate hyperprior is wide.
"""

import math

H0_HAZARD = 0.0005
BETA_WEAR = 0.15       # cliff multiplier
GAMMA_EXP = 6.0
PM_DURATION = 8        # ticks
PM_COST = 250.0
BREAKDOWN_COST = 1200.0
REPAIR_LOGN_MU = 3.1   # lognormal repair time
REPAIR_LOGN_SIG = 0.35
DRIFT_ONSET_WEAR = 0.35


def hazard(wear):
    return H0_HAZARD + BETA_WEAR * (wear ** GAMMA_EXP)


def maybe_breakdown(station, rng):
    """Returns repair_time if the station breaks down this tick, else 0."""
    if rng.random() < hazard(station.wear):
        return max(16, round(math.exp(rng.gauss(REPAIR_LOGN_MU,
                                                REPAIR_LOGN_SIG))))
    return 0


def apply_wear(station, wear_rate):
    station.wear = min(1.0, station.wear + wear_rate)
    station.ops_done += 1


def start_pm(station):
    station.state = "pm"
    station.downtime_rem = PM_DURATION


def complete_pm(station):
    station.wear *= 0.08            # 92% reset
    station.state = "idle"


def complete_repair(station):
    station.wear = 0.15             # overhaul reset
    station.state = "idle"
