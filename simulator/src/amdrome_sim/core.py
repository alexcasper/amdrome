"""Core: episode container + deterministic tick transition coordinator.

Episode API (v1, frozen field names; p2a wraps this for gym/kaggle):

  Engine(seed, agent, layout="compact", ticks=336).run() -> result dict

Agent protocol: `agent.act(obs) -> actions` where actions may contain
  {"bids": {contract_id: price},            # any tick while contract open
   "pm": [station_kind, ...],               # any tick; starts PM when idle
   "probes": [station_kind, ...],           # any tick; SPC budget/shift
   "inspect_mode": "skip|sample|full",      # shift boundaries
   "caps": [c_inbuf, b1..b5]}               # shift boundaries; total 18

The agent receives ONLY the kanban observation (partial observability).
Everything stochastic flows through the RngBank; same seed + same
deterministic agent => bit-identical replay (verified by golden tests).
"""

import hashlib
import json
import math
import random

from . import degradation, floor, kanban as kanban_mod, labour, market, quality
from .rng import RngBank, draw_hyperprior
from .stations import Line, T_UNIT, BUFFER_CAP_DEFAULT

TICKS = 336
SHIFT = 48
BUFFER_TOTAL = 18
DOWNTIME_COST_TICK = 5.0
INPUT_UNITS_PER_JOB = 1.0


class NullAgent:
    """Minimal baseline: never bids, never PMs, even buffers, sample mode."""

    def act(self, obs):
        return {}


class Engine:
    def __init__(self, seed, agent=None, layout="compact", ticks=TICKS,
                 shared_flow=True, rival_mu=None):
        self.seed = seed
        self.agent = agent or NullAgent()
        self.ticks = ticks
        self.bank = RngBank(seed, policy=layout, shared_flow=shared_flow)
        self.h = draw_hyperprior(self.bank.hyper)
        if rival_mu is not None:      # opponent-pool draw (league play)
            self.h["rival_bid_mu"] = rival_mu
        self.rng = self.bank.flow
        self.agent_rng = self.bank.agents
        self.probe_rng = random.Random(
            int.from_bytes(hashlib.sha256(
                f"{seed}|probes".encode()).digest()[:8], "big"))

        if layout == "compact":
            ents = floor.compact_layout()
        else:
            ents = floor.scattered_layout(self.bank.layout)
        floor.validate(ents)
        self.line = Line(ents, buffer_total=BUFFER_TOTAL)
        self.line.set_caps([3] * 6)

        self.roster = labour.Roster(self.bank.layout)
        self.spot = market.SpotMarket(self.h["spot_p0"], self.h["spot_sigma"],
                                      self.h["spot_jump"], self.rng)
        self.view = kanban_mod.KanbanView(self.line, self.h["proc_scale"])

        self.jobs = {}
        self.next_jid = 0
        self.next_cid = 0
        self.open_contracts = []       # awaiting close
        self.won = {}                  # id -> {contract, filled_clean, ...}
        self.settled = []
        self.inspect_mode = "sample"

        # counters
        self.completed_clean = 0
        self.completed_defective = 0
        self.scrapped = 0
        self.reworked = 0
        self.breakdowns = 0
        self.pm_count = 0
        self.rejected = 0
        self.unplanned_downtime = 0
        self.planned_downtime = 0
        self.input_cost = 0.0
        self.pm_cost = 0.0
        self.breakdown_cost = 0.0
        self.scrap_cost = 0.0
        self.contract_money = 0.0
        self.delivered = []            # (tick, clean?, contract_id)
        self.drift_onset = {}

        self.actions_taken = 0
        self.results_log = []

    # ------------------------------------------------------------ helpers

    def _wip(self):
        return len(self.jobs)

    def state_hash(self):
        """Canonical hash over all ground-truth state (golden tests)."""
        st = {
            "t": getattr(self, "t", -1),
            "jobs": sorted((j["id"], j["state"], j.get("dest_kind", ""),
                            j.get("travel", 0), int(j["has_defect"]))
                           for j in self.jobs.values()),
            "stations": [(s.kind, s.state, round(s.wear, 6), s.ops_done,
                          s.remaining) for s in self.line.stations],
            "queues": [len(b.queue) for b in self.line.buffers],
            "caps": [b.cap for b in self.line.buffers],
            "money": [round(x, 4) for x in (self.input_cost, self.pm_cost,
                                            self.breakdown_cost,
                                            self.scrap_cost,
                                            self.contract_money)],
            "counts": [self.completed_clean, self.completed_defective,
                       self.scrapped, self.breakdowns, self.pm_count,
                       self.rejected, self.unplanned_downtime],
            "spot": round(self.spot.p, 4),
            "contracts": sorted(c.id for c in self.open_contracts),
            "won": sorted((i, v["filled_clean"], v["filled_def"])
                          for i, v in self.won.items()),
        }
        blob = json.dumps(st, sort_keys=True).encode()
        return hashlib.sha256(blob).hexdigest()

    # ------------------------------------------------------------ main loop

    def run(self):
        for t in range(self.ticks):
            self.t = t
            self._tick(t)
        # settle everything still open at episode end
        for cid in list(self.won):
            self._settle(cid, self.ticks)
        return self.result()

    def _tick(self, t):
        results = []
        shift_boundary = (t % SHIFT == 0 and t > 0)

        # 1. shift boundary: roster + SPC budget refresh
        if shift_boundary:
            self.roster.roll_shift(self.rng)
            self.view.new_shift()

        # 2. spot market
        self.spot.tick()

        # 3. contract arrivals (engine-scoped IDs — replay determinism)
        newc, self.next_cid = market.spawn_contracts(
            t, self.h["contract_rate"], self.agent_rng, self.ticks,
            self.next_cid)
        for c in newc:
            c.close_tick = t + market.BID_WINDOW
            c.opened = t
            self.open_contracts.append(c)

        # 4. agent decision (the ONLY information channel: kanban obs)
        obs = self.view.observe(t, self.line, self._wip(), self.spot.p,
                                self.open_contracts, self.results_log)
        self.results_log = []
        actions = self.agent.act(obs) or {}
        self.actions_taken += sum(len(v) if isinstance(v, (list, dict))
                                  else 1 for v in actions.values())

        # 5. apply agent actions
        if shift_boundary and "caps" in actions:
            try:
                self.line.set_caps([int(c) for c in actions["caps"]])
            except AssertionError:
                pass                      # invalid total: ignored
        if "inspect_mode" in actions \
                and actions["inspect_mode"] in quality.CATCH_PROB:
            self.inspect_mode = actions["inspect_mode"]
        for kind in actions.get("probes", [])[:kanban_mod.SPC_BUDGET]:
            s = self._station(kind)
            if s is not None and s.state == "proc":
                self.view.probe(s, t, self.drift_onset.get(s.kind),
                                self.probe_rng)
        for kind in actions.get("pm", []):
            s = self._station(kind)
            if (s is not None and s.state == "idle" and s.job is None
                    and s.downtime_rem <= 0):
                degradation.start_pm(s)
                self.pm_count += 1
                self.pm_cost += degradation.PM_COST

        # 6. arrivals
        if self.rng.random() < self.h["lam"]:
            if len(self.line.inbuf.queue) < self.line.inbuf.cap:
                self.input_cost += self.spot.p * INPUT_UNITS_PER_JOB
                j = {"id": self.next_jid, "state": "wait",
                     "dest": self.line.inbuf, "born": t,
                     "has_defect": False, "reworks": 0}
                self.line.inbuf.queue.append(j)
                self.jobs[self.next_jid] = j
                self.next_jid += 1
            else:
                self.rejected += 1

        # 7. drift onset tracking (ground truth)
        for s in self.line.stations:
            if s.wear >= degradation.DRIFT_ONSET_WEAR \
                    and s.kind not in self.drift_onset:
                self.drift_onset[s.kind] = t

        # 8. maintenance countdowns
        for s in self.line.stations:
            if s.downtime_rem > 0:
                s.downtime_rem -= 1
                if s.state == "pm":
                    self.planned_downtime += 1
                else:
                    self.unplanned_downtime += 1
                if s.downtime_rem <= 0:
                    if s.state == "pm":
                        degradation.complete_pm(s)
                    else:
                        degradation.complete_repair(s)
                    s.job = None

        # 9. station admission
        staffing = self.roster.staffing_multiplier()
        for s in self.line.stations:
            if s.state == "idle" and s.job is None:
                up = self.line.buf_before[s]
                if up.queue:
                    j = up.queue.pop(0)
                    s.job = j
                    s.state = "proc"
                    s.remaining = max(1, round(
                        s.proc_time(self.h["proc_scale"], 0, self.rng)
                        / staffing))
                    j["state"] = "proc"

        # 10. processing, hazard, op completion
        for s in self.line.stations:
            if s.state != "proc" or s.job is None:
                continue
            repair = degradation.maybe_breakdown(s, self.rng)
            if repair:
                self.breakdowns += 1
                self.breakdown_cost += degradation.BREAKDOWN_COST
                s.state = "broken"
                s.downtime_rem = repair
                if s.job is not None:
                    self.scrapped += 1
                    self.scrap_cost += quality.SCRAP_COST
                    del self.jobs[s.job["id"]]
                    s.job = None
                continue
            s.remaining -= 1
            if s.remaining > 0:
                continue
            j = s.job
            degradation.apply_wear(s, self.h["wear_rate"])
            if s.kind in ("cut", "form", "weld", "paint"):
                quality.inject(j, s, self.h["p_defect_base"], self.rng)
            self._release(s, j, t, results)

        # 11. transit arrivals
        arrived = [jid for jid, j in self.jobs.items()
                   if j["state"] == "transit"]
        for jid in arrived:
            j = self.jobs[jid]
            j["travel"] -= 1
            if j["travel"] <= 0:
                j["state"] = "wait"
                j["dest"].queue.append(j)

        # 11b. unblock stations whose downstream buffer opened up
        for s in self.line.stations:
            if s.state == "blocked" and s.job is not None:
                down = self.line.buf_after.get(s)
                if down is not None and len(down.queue) < down.cap:
                    j = s.job
                    s.job = None
                    s.state = "idle"
                    dist = floor.manhattan(s.pos, down.pos)
                    tt = max(1, round(dist * T_UNIT
                                      * (1 + self.rng.uniform(
                                          -self.h["t_noise"],
                                          self.h["t_noise"]))))
                    j["state"] = "transit"
                    j["dest"] = down
                    j["travel"] = tt

        # 12. contract close: resolve sealed bids
        for c in [c for c in self.open_contracts if t >= c.close_tick]:
            self.open_contracts.remove(c)
            bid = actions.get("bids", {}).get(c.id)
            if bid is not None and bid > 0:
                won, rival = market.resolve_bid(
                    c, float(bid), self.h["rival_bid_mu"], self.agent_rng)
                if won:
                    self.won[c.id] = {"contract": c, "filled_clean": 0,
                                      "filled_def": 0, "my_bid": float(bid)}
                    results.append({"event": "won_contract",
                                    "id": c.id, "bid": round(float(bid), 2)})

        # 13. delivery to oldest unfulfilled won contract
        for ev in [e for e in results if e["event"] == "completed"]:
            self._deliver(ev, t)

        # 14. settle contracts past deadline
        for cid in [cid for cid, v in self.won.items()
                    if t >= v["contract"].deadline
                    or v["filled_clean"] + v["filled_def"]
                    >= v["contract"].size]:
            self._settle(cid, t)

        self.results_log = results

    # ------------------------------------------------------------ pieces

    def _station(self, kind):
        for s in self.line.stations:
            if s.kind == kind:
                return s
        return None

    def _release(self, s, j, t, results):
        """Op done at station s: inspect/rework/transit/complete."""
        s.job = None
        s.state = "idle"
        if s.kind == "inspect":
            caught = quality.inspect(j, self.inspect_mode, self.rng)
            if caught:
                self.reworked += 1
                j["has_defect"] = False
                j["reworks"] += 1
                # rework: back to the front of the line
                j["state"] = "wait"
                j["dest"] = self.line.inbuf
                self.line.inbuf.queue.append(j)
                return
        if s.kind == "pack":
            self._complete(j, t, results)
            return
        down = self.line.buf_after[s]
        if len(down.queue) < down.cap:
            dist = floor.manhattan(s.pos, down.pos)
            tt = max(1, round(dist * T_UNIT
                              * (1 + self.rng.uniform(
                                  -self.h["t_noise"], self.h["t_noise"]))))
            j["state"] = "transit"
            j["dest"] = down
            j["dest_kind"] = down.kind
            j["travel"] = tt
        else:
            s.job = j                    # blocked: hold on station
            s.state = "blocked"

    def _complete(self, j, t, results):
        del self.jobs[j["id"]]
        if j["has_defect"]:
            self.completed_defective += 1
        else:
            self.completed_clean += 1
        results.append({"event": "completed", "defect": j["has_defect"],
                        "id": j["id"]})

    def _deliver(self, ev, t):
        for cid, v in self.won.items():       # FIFO: oldest first
            need = v["contract"].size - v["filled_clean"] - v["filled_def"]
            if need > 0:
                if ev["defect"]:
                    v["filled_def"] += 1
                else:
                    v["filled_clean"] += 1
                return

    def _settle(self, cid, t):
        v = self.won.pop(cid)
        c = v["contract"]
        money = market.settle(c, v["filled_clean"], v["filled_def"], t)
        # bidding economics: factory pays its own bid price per unit won
        money -= v["my_bid"] * (v["filled_clean"] + v["filled_def"]) \
            - c.unit_price * (v["filled_clean"] + v["filled_def"])
        self.contract_money += money
        self.settled.append({"id": cid, "money": money,
                             "clean": v["filled_clean"],
                             "def": v["filled_def"]})

    def result(self):
        net = (self.contract_money - self.input_cost - self.pm_cost
               - self.breakdown_cost - self.scrap_cost
               - self.unplanned_downtime * DOWNTIME_COST_TICK)
        delivered = self.completed_clean + self.completed_defective
        ontime = sum(1 for s in self.settled if s["money"] > 0) \
            / max(1, len(self.settled))
        ppm = (self.completed_defective / max(1, delivered)) * 1e6
        return {
            "seed": self.seed, "ticks": self.ticks,
            "net_profit": round(net, 2),
            "revenue": round(self.contract_money, 2),
            "completed_clean": self.completed_clean,
            "completed_defective": self.completed_defective,
            "scrapped": self.scrapped, "reworked": self.reworked,
            "breakdowns": self.breakdowns, "pm_count": self.pm_count,
            "rejected": self.rejected,
            "unplanned_downtime": self.unplanned_downtime,
            "contracts_won": len(self.settled),
            "ontime_frac": round(ontime, 3),
            "defect_ppm": round(ppm, 1),
            "downtime_frac": round(self.unplanned_downtime / self.ticks, 3),
            "actions_taken": self.actions_taken,
            "spc_probes": self.view.spent,
            "detections": self.view.detections,
            "mean_detection_latency": (
                round(sum(self.view.detect_latencies)
                      / len(self.view.detect_latencies), 2)
                if self.view.detect_latencies else None),
            "false_alarms": self.view.false_alarms,
        }
