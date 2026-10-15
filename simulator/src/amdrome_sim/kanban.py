"""Kanban: partial-observability layer — the agent's only window.

The agent never sees ground truth (true wear, defect status, remaining
ticks). It sees: coarse station cards, budgeted SPC cycle-time samples,
buffer pull counts, inspection results, and its own threshold alarms.
Monitoring capacity is limited (SPC_BUDGET probes/shift) and is itself
an evaluated skill.
"""

import math

SPC_BUDGET = 8          # probes per 48-tick shift
CARD_EVERY = 8          # station-card refresh interval (ticks)
CUSUM_DRIFT_K = 0.4     # CUSUM slack
CUSUM_ALARM = 3.2      # detection threshold
MEAS_NOISE = 0.4


class KanbanView:
    """Accumulates observations and masks state for the agent."""

    def __init__(self, line, proc_scale):
        self.line = line
        self.proc_scale = proc_scale
        self.probes_left = SPC_BUDGET
        self.cusum = {s.kind: 0.0 for s in line.stations}
        self.last_sampled = {s.kind: -1 for s in line.stations}
        self.spent = 0
        self.false_alarms = 0
        self.detections = 0
        self.detect_latencies = []

    def new_shift(self):
        self.probes_left = SPC_BUDGET

    def probe(self, station, t, drift_onset_tick, rng):
        """One SPC probe: noisy cycle-time measurement -> CUSUM update."""
        if self.probes_left <= 0 or station.last_proc_actual is None:
            return None
        self.probes_left -= 1
        self.spent += 1
        self.last_sampled[station.kind] = t
        meas = station.last_proc_actual + rng.gauss(0, MEAS_NOISE)
        z = (meas - 7.0 * self.proc_scale) / (7.0 * 0.15)
        self.cusum[station.kind] = max(0.0, self.cusum[station.kind]
                                       + z - CUSUM_DRIFT_K)
        if self.cusum[station.kind] > CUSUM_ALARM:
            if drift_onset_tick is not None:
                self.detections += 1
                self.detect_latencies.append(t - drift_onset_tick)
            else:
                self.false_alarms += 1
            self.cusum[station.kind] = 0.0
            return True
        return None

    def station_card(self, s):
        """Coarse card: state + queue. NEVER exposes wear or job internals."""
        return {
            "kind": s.kind,
            "state": s.state,
            "ops_seen": s.ops_done,
        }

    def observe(self, t, line, wip, spot_price, open_contracts, results,
                input_stock=0):
        """Full observation dict — everything the agent is allowed to see."""
        cards = {}
        for s in line.stations:
            cards[s.kind] = {
                "state": s.state,
                "ops_seen": s.ops_done,
                "queue_before": len(line.buf_before[s].queue),
            }
        return {
            "t": t,
            "wip": wip,
            "spot_price": round(spot_price, 2),
            "input_stock": input_stock,
            "spc_probes_left": self.probes_left,
            "cusum": {k: round(v, 3) for k, v in self.cusum.items()},
            "cards": cards,
            "open_contracts": [
                {"id": c.id, "size": c.size, "unit_price": c.unit_price,
                 "deadline": c.deadline, "close_tick": c.close_tick}
                for c in open_contracts],
            "results": results,     # completed/scrapped/settled last tick
        }
