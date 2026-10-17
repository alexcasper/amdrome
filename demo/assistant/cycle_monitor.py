"""Condition-based PM from free cycle-time telemetry (bead amdrome-bqm).

The kanban stream exposes every station's state each tick plus its
completed-op counter. Counting `proc` ticks between op-counter increments
yields the realised cycle time of EVERY operation — no SPC probe budget
needed. The engine inflates cycle time by (1 + 0.35 * wear), and wear grows
by a fixed (unknown, per-station) amount per finished op, so a per-station
regression of log(cycle) on ops-since-reset recovers that wear rate. The
monitor then requests PM when the estimated wear reaches a threshold.

Pure observation-side inference: no ground truth is read.
"""

import math

DRIFT_SLOPE = 0.35          # cycle inflation at wear=1.0 (engine contract)
PM_RESIDUAL = 0.08          # wear kept after PM
REPAIR_RESET = 0.15         # wear after breakdown overhaul
R_PRIOR = 0.0276            # prior mean wear/op (hyperprior x station mult)
R_PRIOR_SD = 0.012
LOGD_SD = 0.16              # per-op log cycle noise (lognormal 0.15 + rounding)
STAFF_MULT = {0: 1.3, 1: 1.0}   # engine divides proc time by this; >=2: 0.9


def _staff_mult(n):
    return STAFF_MULT.get(n, 0.9)


class CycleMonitor:
    def __init__(self, wear_threshold=0.40):
        self.w_thr = wear_threshold
        self.prev_ops = {}
        self.prev_state = {}
        self.proc_ticks = {}
        self.valid = {}
        self.n_since = {}          # ops since last reset
        self.w0 = {}               # estimated wear at last reset
        self.w_pre_pm = {}         # wear estimate when PM started
        self.base_obs = []         # log cycle samples at near-zero wear
        self.sxx = {}              # sum n^2   (per station)
        self.sxy = {}              # sum n*(y - w0)
        self.samples = 0

    # ---------------------------------------------------------- estimation
    def _intercept(self):
        if not self.base_obs:
            return None
        return sum(self.base_obs) / len(self.base_obs)

    def rate(self, kind):
        """Posterior-mean wear per op (normal prior, weighted LS)."""
        pw = 1.0 / R_PRIOR_SD ** 2
        lw = 1.0 / (LOGD_SD / DRIFT_SLOPE) ** 2
        sxx = self.sxx.get(kind, 0.0)
        sxy = self.sxy.get(kind, 0.0)
        return max(0.002, (R_PRIOR * pw + sxy * lw) / (pw + sxx * lw))

    def wear(self, kind):
        return self.w0.get(kind, 0.0) + self.rate(kind) * self.n_since.get(kind, 0)

    def _record(self, kind, dur, staff_n):
        d = max(1.0, dur * _staff_mult(staff_n))
        y = math.log(d)
        n = self.n_since.get(kind, 0)
        w0 = self.w0.get(kind, 0.0)
        if n <= 1 and w0 < 0.05:
            self.base_obs.append(y)
        a = self._intercept()
        if a is not None and n >= 1:
            # y - a ~= DRIFT_SLOPE * (w0 + r n)
            yw = (y - a) / DRIFT_SLOPE - w0
            self.sxx[kind] = self.sxx.get(kind, 0.0) + n * n
            self.sxy[kind] = self.sxy.get(kind, 0.0) + n * yw
            self.samples += 1

    # ---------------------------------------------------------- stream
    def update(self, obs):
        counts = (obs.get("roster") or {}).get("assigned_counts", {})
        for kind, card in obs["cards"].items():
            st, ops = card["state"], card["ops_seen"]
            prev_st = self.prev_state.get(kind)
            prev_ops = self.prev_ops.get(kind, ops)
            if ops > prev_ops:
                if self.valid.get(kind) and self.proc_ticks.get(kind, 0) > 0:
                    self._record(kind, self.proc_ticks[kind] + 1,
                                 counts.get(kind, 1))
                self.n_since[kind] = self.n_since.get(kind, 0) + (ops - prev_ops)
                self.proc_ticks[kind] = 0
                self.valid[kind] = True
            if prev_st not in ("pm", "broken") and st in ("pm", "broken"):
                self.w_pre_pm[kind] = self.wear(kind)
            if prev_st in ("pm", "broken") and st not in ("pm", "broken"):
                self.w0[kind] = (PM_RESIDUAL * self.w_pre_pm.get(kind, 0.0)
                                 if prev_st == "pm" else REPAIR_RESET)
                self.n_since[kind] = 0
            if st == "proc":
                self.proc_ticks[kind] = self.proc_ticks.get(kind, 0) + 1
            elif st in ("broken", "pm", "moving"):
                self.valid[kind] = False      # interrupted op: discard
                self.proc_ticks[kind] = 0
            self.prev_state[kind] = st
            self.prev_ops[kind] = ops

    def pm_requests(self, obs):
        out = []
        for kind, card in obs["cards"].items():
            if card["state"] in ("pm", "broken", "moving"):
                continue
            nxt = self.w0.get(kind, 0.0) + self.rate(kind) * (
                self.n_since.get(kind, 0) + 1)
            if nxt >= self.w_thr:
                out.append(kind)
        return out
