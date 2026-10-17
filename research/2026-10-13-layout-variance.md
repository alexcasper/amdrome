# Layout mechanic: variance vs sensitivity (measured) — 2026-10-13

Bead: amdrome-is5 (design-iteration loop, step 2). All numbers from paired
sweeps on **dusk** (fleet host; 1200 episodes/sweep ≈ 0.7 s CPU).

- Prototype: `simulator/proto_layout.py` (pure stdlib, stateless CLI, JSONL out)
- Analysis: `research/layout_variance_analysis.py [datadir]`
- Data: `research/data/` (baseline λ∈[0.05,0.12]) and `research/data/hot/`
  (near-saturation λ∈[0.10,0.16]), 400 paired seeds × 3 policies.

Policies: `compact` (straight line, hop distance ~1–2), `clustered`
(random within a 4×4 region), `scattered` (uniform random on 12×8 — mean
hop distance ~7–8). Hyperprior (λ, proc scale, wear rate, transport noise)
is **paired across policies by seed**.

## Findings (baseline → hot regime)

| metric | policy share of variance (cycle_mean) | compact−scattered d_z | n95 (episodes to 95% verdict) |
|---|---|---|---|
| cycle_mean | 64% → 53% | −2.89 → −2.37 | 1 → 1 |
| wip_mean   | —                       | −1.06 → −1.28 | 4 → 3 |
| completed  | —                       | +0.42 → +0.68 | 22 → 9 |

(compact−clustered on completed remains weak: d_z 0.17 → 0.24, n95 130 → 69.)

1. **Layout skill dominates noise on cycle time**: policy explains 53–64%
   of cycle_mean variance; scenario seed 24–32%; residual ~12–15%. Exactly
   the anti-tape profile (real cross-episode variance, decision-dominated
   outcome). Paired verdicts between far-apart layouts need ~1–9 episodes —
   far under the 200-episode budget (DESIGN §7 gate 3 on track).
2. **Throughput is only weakly layout-coupled** in this prototype. Cause:
   transport delays inflate cycle time/WIP but don't consume station
   capacity — blocking almost never binds (buffers absorb). Moving λ toward
   saturation (hot regime) improves it (win rate 61%→76%, n95 22→9) but
   adjacent-quality layouts stay hard to separate on throughput alone.
3. **Runtime budget (gate 4)**: ~0.6 ms/episode/336 ticks on dusk → an
   8-factory × 50-episode league match ≈ 0.2 s single-core. No risk.
4. **Determinism gotcha (now a design rule)**: seeding `random.Random` with
   tuples/strings uses salted `hash()` — NOT replay-stable across processes.
   All generator seeds go through `gen_seed()` = sha256 → int.

## Design implications (feeding DESIGN.md v1)

- **Score must weight cycle time / WIP (or cost/unit with time cost), not
  throughput alone** — else layout skill is under-rewarded relative to
  capacity decisions.
- **AGV/forklift pool question (DESIGN §9)**: answered. A *small shared*
  transport pool is what couples layout to throughput (bad layouts consume
  more AGV-seconds, blocking stations). Without it, cut is fine for v1 if
  the score weights cycle/WIP. Recommend: cut AGVs from v1, revisit if
  throughput separation between adjacent layouts matters.
- λ hyperprior should sit near saturation (arrival rate ≈ 85–95% of line
  capacity) so capacity decisions matter; hyperprior width stays wide for
  anti-tape variance.

## Next (design loop continues)

- Prototype mechanic 2: degradation/monitoring (SPC drift detection latency
  vs sample budget) — the kanban skill surface and the demo's foundation.
- Then anti-tape acceptance test (tape agent vs mediocre reactive) once
  there is a policy worth taping.
