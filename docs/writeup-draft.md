# amdrome — project writeup (draft, 2026-10-18)

Status: working engine, demo verified, economy balance in progress.
Repo: /mnt/d/ops/amdrome (HEAD d560091). Charter: draft v2, proposed —
alex's sign-off pending (CHARTER.md).

## What it is

amdrome is a discrete-event factory simulation engine with three deliverables
(README.md, CHARTER.md):

1. The engine (`simulator/`, `amdrome_sim`): pure Python + NumPy, six-station
   production line (cut, form, weld, paint, inspect, pack), wear-driven
   degradation, defect injection with inspection and rework, labour roster
   with staffing and skill effects, spot input market and sealed-bid
   contracts. Dual interface: `kaggle_environments`-compatible episode runner
   plus Gymnasium/PettingZoo. Grid size is a config parameter
   (`Engine(grid_w, grid_h)`), default 12x8.
2. The agent ecosystem (`agents/`, `rl/`): scripted baselines (blind
   run-to-failure, reactive CUSUM/PM ceiling), four character agents with
   documented personas, SB3 MaskablePPO training harness (in progress,
   amdrome-x4i).
3. The demo product (`demo/`): an operator assistant over the kanban
   observation stream, with CUSUM drift detection, Weibull RUL estimation,
   and a paired A/B benchmark suite.

The design goal that shapes everything: anti-tape. Episodes draw scenarios
from hyperpriors under partial observability, so memorized action tapes lose
to mediocre reactive play. The engine-level gate passes (tape win rate
3.0/1.0/3.0% full/bids/ops after rebalance — research/2026-10-17-rebalance.md).

## Why it exists

Two reasons (CHARTER.md). First, a Kaggle-style challenge asset in the lineage
of the farm repo's Kaggriculture work, but with original discrete-manufacturing
mechanics — there is no upstream factory engine to wrap, so seed determinism,
golden states, and replay tests replace a parity suite. Second, the
Intelligent Industry hackathon: the assistant demo is the application, the
engine is the asset.

## Results

### Operator assistant vs blind — current engine, held-out

Pre-registered A/B, 2000 paired held-out episodes (seeds 900000+, never used
for tuning), on the current engine after the labour fixes (d9a7ed8)
(research/2026-10-17-ab-verification.md):

| metric | result |
|---|---|
| Unplanned breakdown downtime | −73.6% (95% CI 72.4–74.8) |
| Total downtime incl. planned PM | +1.6% (roughly flat) |
| Customer defect escapes | −91.4% (CI 89.9–92.8), hpm-dependent |
| Net profit vs blind | +$6,612/episode |

The escape reduction depends on 100% inspection being free in the engine —
that is an open design issue (amdrome-hpm), disclosed rather than hidden. The
pre-rebalance held-out dollar figure (+$5,471/ep, cbm 0.40, 96% win) is
superseded; all prior dollar figures died with the 2026-10-17 rebalance.

An earlier spec scorecard (SPEC_DEMO_PRODUCT §4.2) claimed −74.3% downtime
and −94.7% escapes with no measurement behind it — targets written as
results. Independent verification caught this, and every number was replaced
with measured ones (research/2026-10-17-ab-verification.md).

### Labour coupling: both signs were inverted

Independent review found two engine bugs, both fixed with regression tests
that fail on the old code (research/2026-10-17-labour-svf.md):

- 8ed7aff: the staffing multiplier divided processing time instead of
  multiplying — an unstaffed station ran 23% faster, double-staffed ran 11%
  slower.
- d9a7ed8: worker skill inverted the defect modifier — skill 0.7 gave 0.85x
  the defects, making weak workers better. Now skill 0.7 gives 1.15x.

After both fixes, the skilled reactive agent's lead over blind grew
(d_z 0.77 -> 0.87, win 77% -> 81%, n=1000 paired seeds 960000+) and the
anti-tape gate still passes. The labour decision itself remains worth almost
nothing (+$175, z 2.1): `assign` takes counts only, so an agent cannot place
a specific worker — a design gap, not a bug.

### Grid sweep: floor size prices bad layouts

400 paired seeds per size (research/2026-10-17-grid-sweep.md):

| size | policy share of cycle variance | scenario share | compact-scattered d_z | throughput edge | engine ms/ep |
|---|---|---|---|---|---|
| 8x6 (48 cells) | 47.1% | 37.8% | 2.49 | +1.4 units/ep | ~40 |
| 12x8 (default) | 63.9% | 24.1% | 2.89 | +2.5 units/ep | ~40 |
| 16x12 | 76.7% | 13.9% | 3.35 | +3.4 units/ep | ~40 |

Transport dominates at every size; blocking never binds (blocked_ticks = 0).
A bigger floor does not get cramped — it makes bad layouts cost more. Runtime
is flat across sizes.

### Character-agent economics — balance pass in progress

Target: disciplined personas break even, negligent ones lose. Not there yet.
Alex's rebalance pass is underway (research/2026-10-17-rebalance.md,
economy knobs only, agents untouched). Full post-rebalance ladder:

random −5,972 < Chen −5,594 ≈ Pete −5,153 < blind −4,458 < Charlie −3,317 <
Milliard −2,958 < reactive −2,239 (net $/ep).

The coordinator's latest 40-episode snapshot (seed 4242,
docs/hackathon-submission.md) — every character still loses money:
blind −4,396, Charlie −2,862, Milliard −3,073, Pete −5,220, Chen −5,498.
Ladder ordering is monotone on the discipline axis and preserved across both
economy versions. Absolute dollar figures are provisional until the balance
pass lands.

## Limitations / open work

- Economy balance: in progress (alex). Numbers above are provisional in
  absolute dollars.
- Inspection is free in the engine (amdrome-hpm) — the escape-reduction
  claim inherits that hole; the escape effect comes from a costless knob.
- RL harness (amdrome-x4i) in progress; the adaptive ceiling needs it —
  reactive is under-tuned for the current economics
  (research/2026-10-17-character-roster.md).
- Labour assignment is count-only; per-worker placement is a design gap.
- Product mix (multi-product routes) is specified but not in the engine
  (docs/SPEC_PRODUCT_MIX.md).
- Charter not ratified; grid default 12x8 is a coordinator decision, 16x12
  challenge tier still a design option.

## How it was built

Multi-agent LLM team in parallel herdr panes (GLM coordinator + Claude and
Gemini workers), work tracked as beads, commits per feature. Verification ran
on Explorer HPC (dawn does no sweeps; slurm `short`).

## Sources

- research/2026-10-17-ab-verification.md — A/B verification, held-out tables
- research/2026-10-17-labour-svf.md — both sign bugs, before/after, d_z
- research/2026-10-17-grid-sweep.md — grid sweep table
- research/2026-10-17-rebalance.md — economy diff, post-rebalance ladder
- research/2026-10-17-character-roster.md — personas, ladder-tuning findings
- docs/hackathon-submission.md — in-progress balance snapshot (seed 4242)
- commits 8ed7aff, d9a7ed8 — the fixes; golden v8/v9
- README.md, CHARTER.md, DESIGN.md, docs/SPEC_*.md
