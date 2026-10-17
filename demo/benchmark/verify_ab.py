#!/usr/bin/env python3
"""Independent A/B verification runner (bead: A/B claim verification).

Deliberately does NOT reuse run_ab.py: arms are re-declared here, every
episode is run from a fresh Engine, and extra ground-truth instrumentation
is captured so headline claims can be audited, not just restated.

Per (seed, arm) it emits one JSON row with the engine result plus:
  planned_downtime      PM/relocation ticks (engine counts them separately;
                        a policy can trade unplanned for planned downtime)
  total_downtime        unplanned + planned
  bd_wear               true wear of the station at each breakdown
  bd_h0_share           expected count of breakdowns attributable to the
                        wear-independent hazard floor H0 (sum H0/hazard(w)):
                        the irreducible breakdown share no policy can avoid
  defects_injected      defective units created (pre-inspection)

Arms (LEGIT = observation-only; CEIL = ground-truth oracle, an upper bound
on what ANY policy could achieve in this engine — never a product claim):
  blind             agents/blind.py (run-to-failure, sample inspection)
  blind_full        blind + inspect_mode=full every tick       (LEGIT)
  asst              LEGACY assistant (cbm_threshold=None, adaptive inspection;
                    the pre-2026-10-17 shipped default)          (LEGIT)
  asst_full         asst + full inspection from t=0            (LEGIT)
  asst_nocap        asst with PM budget caps removed           (LEGIT)
  asst_nocap_full   both                                       (LEGIT)
  asst_ops<K>       asst_nocap_full + PM every K ops/station   (LEGIT)
  oracle_w<NN>      asst bids + PM when TRUE wear >= 0.NN + full (CEIL)

Usage (never on dawn — fleet / Explorer slurm only):
  python3 demo/benchmark/verify_ab.py --seed-base 500000 --episodes 1000 \
      --shard 0 --nshards 10 --arms blind,asst,... --out shard0.jsonl
  python3 demo/benchmark/verify_ab.py --replay-check 20 --seed-base 500000
"""

import argparse
import importlib.util
import json
import os
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
sys.path.insert(0, os.path.join(ROOT, "simulator", "src"))
sys.path.insert(0, ROOT)

from amdrome_sim import Engine  # noqa: E402
from amdrome_sim import degradation  # noqa: E402

from demo.assistant import OperatorAssistant, Recommender  # noqa: E402
from demo.assistant.cycle_monitor import CycleMonitor  # noqa: E402

# harness arms are defined relative to the LEGACY assistant so arm names keep
# their meaning across the 2026-10-17 default flip (prod_* = product path)
LEGACY = {"cbm_threshold": None, "full_inspection": False}

DEFAULT_ARMS = ("blind,blind_full,asst,asst_full,asst_nocap,asst_nocap_full,"
                "asst_ops8,asst_ops12,asst_ops16,oracle_w35,oracle_w45")


# ------------------------------------------------------------ instrumentation

class BreakdownTap:
    """Wraps degradation.maybe_breakdown (behaviour-preserving) to record
    the true wear at every breakdown. Engine calls it via the module
    attribute, so patching the module function is sufficient."""

    def __init__(self):
        self._orig = degradation.maybe_breakdown
        self.wears = []

    def __enter__(self):
        orig = self._orig
        wears = self.wears

        def tapped(station, rng):
            r = orig(station, rng)
            if r:
                wears.append(station.wear)
            return r

        degradation.maybe_breakdown = tapped
        return self

    def __exit__(self, *exc):
        degradation.maybe_breakdown = self._orig


def h0_share(wears):
    return sum(degradation.H0_HAZARD / degradation.hazard(w) for w in wears)


# ------------------------------------------------------------ arms

def _load_blind():
    path = os.path.join(ROOT, "agents", "blind.py")
    spec = importlib.util.spec_from_file_location("blind_verify", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class BlindFull:
    def __init__(self, blind):
        self.blind = blind

    def act(self, obs):
        out = self.blind.act(obs)
        out["inspect_mode"] = "full"
        return out


class AssistantVariant:
    """Shipped assistant + observation-only overrides."""

    def __init__(self, nocap=False, full=False, pm_every_ops=None):
        self.a = OperatorAssistant(autonomous=True, **LEGACY)
        if nocap:
            self.a.recommender = Recommender(max_pm_per_station=None,
                                             max_pm_total=None)
        self.full = full
        self.k = pm_every_ops
        self.base_ops = {}
        self.prev_state = {}

    def act(self, obs):
        out = dict(self.a.act(obs) or {})
        if self.full:
            out["inspect_mode"] = "full"
        if self.k:
            pm = set(out.get("pm", []))
            for kind, card in obs["cards"].items():
                st, ops = card["state"], card["ops_seen"]
                prev = self.prev_state.get(kind)
                if prev in ("pm", "broken") and st not in ("pm", "broken"):
                    self.base_ops[kind] = ops          # wear just reset
                self.prev_state[kind] = st
                if st in ("pm", "broken"):
                    continue
                if ops - self.base_ops.get(kind, 0) >= self.k:
                    pm.add(kind)
            if pm:
                out["pm"] = sorted(pm)
        return out


class CBMVariant:
    """Shipped assistant + full inspection + condition-based PM from the
    free per-op cycle-time stream (demo/assistant/cycle_monitor.py)."""

    def __init__(self, w):
        self.a = OperatorAssistant(autonomous=True, **LEGACY)
        self.cm = CycleMonitor(wear_threshold=w)

    def act(self, obs):
        out = dict(self.a.act(obs) or {})
        out["inspect_mode"] = "full"
        self.cm.update(obs)
        pm = set(out.get("pm", [])) | set(self.cm.pm_requests(obs))
        if pm:
            out["pm"] = sorted(pm)
        return out


class Oracle:
    """CEILING ONLY: reads ground-truth wear via the engine handle."""

    def __init__(self, w):
        self.w = w
        self.a = OperatorAssistant(autonomous=True, **LEGACY)   # bids/probes/caps
        self.engine = None

    def act(self, obs):
        out = dict(self.a.act(obs) or {})
        out["inspect_mode"] = "full"
        out["pm"] = [s.kind for s in self.engine.line.stations
                     if s.wear >= self.w and s.state not in ("pm", "broken")]
        return out


def make_arm(name, blind):
    if name == "blind":
        return blind
    if name == "blind_full":
        return BlindFull(blind)
    if name == "asst":
        return AssistantVariant()
    if name == "asst_full":
        return AssistantVariant(full=True)
    if name == "asst_nocap":
        return AssistantVariant(nocap=True)
    if name == "asst_nocap_full":
        return AssistantVariant(nocap=True, full=True)
    if name.startswith("asst_ops"):
        return AssistantVariant(nocap=True, full=True,
                                pm_every_ops=int(name[len("asst_ops"):]))
    if name == "prod_default":              # whatever OperatorAssistant() ships
        return OperatorAssistant(autonomous=True)
    if name.startswith("prod_cbm"):          # product code path, as shipped
        return OperatorAssistant(autonomous=True, full_inspection=True,
                                 cbm_threshold=int(name[len("prod_cbm"):]) / 100.0)
    if name.startswith("asst_cbm"):
        return CBMVariant(int(name[len("asst_cbm"):]) / 100.0)
    if name.startswith("oracle_w"):
        return Oracle(int(name[len("oracle_w"):]) / 100.0)
    raise SystemExit(f"unknown arm {name}")


# ------------------------------------------------------------ run

def run_one(seed, arm_name, blind):
    agent = make_arm(arm_name, blind)
    e = Engine(seed, agent=agent)
    if isinstance(agent, Oracle):
        agent.engine = e
    with BreakdownTap() as tap:
        r = e.run()
    r = dict(r)
    r.update({
        "arm": arm_name,
        "planned_downtime": e.planned_downtime,
        "total_downtime": e.unplanned_downtime + e.planned_downtime,
        "bd_wear": [round(w, 3) for w in tap.wears],
        "bd_h0_share": round(h0_share(tap.wears), 4),
        "defects_injected": e.completed_defective + e.reworked
        + sum(1 for j in e.jobs.values() if j["has_defect"]),
        "state_hash": e.state_hash(),
    })
    if isinstance(agent, CBMVariant):     # estimator audit (truth vs est.)
        errs = []
        for s in e.line.stations:
            true_r = e.h["wear_rate"] * e.wear_mult[s.kind]
            errs.append(abs(agent.cm.rate(s.kind) - true_r) / true_r)
        r["cbm_rate_relerr"] = round(sum(errs) / len(errs), 4)
    return r


def replay_check(seed_base, n, arms, blind):
    bad = 0
    for i in range(n):
        for a in arms:
            r1 = run_one(seed_base + i, a, blind)
            r2 = run_one(seed_base + i, a, blind)
            if r1 != r2:
                bad += 1
                print(f"[replay] MISMATCH seed={seed_base + i} arm={a}",
                      file=sys.stderr)
    print(json.dumps({"replay_check": True, "pairs": n * len(arms),
                      "mismatches": bad}))
    return bad


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed-base", type=int, default=500000)
    ap.add_argument("--episodes", type=int, default=1000)
    ap.add_argument("--shard", type=int, default=0)
    ap.add_argument("--nshards", type=int, default=1)
    ap.add_argument("--arms", default=DEFAULT_ARMS)
    ap.add_argument("--out", default=None)
    ap.add_argument("--replay-check", type=int, default=0,
                    help="re-run N seeds per arm twice; assert identical")
    args = ap.parse_args()

    blind = _load_blind()
    arms = [a for a in args.arms.split(",") if a]
    if args.replay_check:
        sys.exit(1 if replay_check(args.seed_base, args.replay_check,
                                   arms, blind) else 0)

    out = open(args.out, "w") if args.out else sys.stdout
    seeds = [args.seed_base + i for i in range(args.episodes)
             if i % args.nshards == args.shard]
    for k, seed in enumerate(seeds):
        for a in arms:
            out.write(json.dumps(run_one(seed, a, blind)) + "\n")
        out.flush()
        if k % 20 == 0:
            print(f"[verify] shard {args.shard} {k}/{len(seeds)}",
                  file=sys.stderr)
    if out is not sys.stdout:
        out.close()


if __name__ == "__main__":
    main()
