# amdrome — charter (draft v2 for alex's sign-off)

**Hackathon brief:** Intelligent Industry — help factories spot problems earlier
and operate better (downtime, quality, safety, resource efficiency).
**Bead:** amdrome-hxx (P1). **Status:** proposed, not yet ratified.

## What amdrome is

A **factory simulation engine** designed as the basis for a **Kaggle-style
challenge**, in the lineage of the farm repo's Kaggriculture work — with
**original mechanics** representing discrete manufacturing. Deliverables:

1. **The engine** — Gym-style core + `kaggle_environments`-compatible episode
   runner (single-file agent submissions, obs/act JSON, per-turn timeout),
   multi-factory shared-market self-play.
2. **A sample agent** — readable, competitive-ish baseline that ships with the
   engine and can be **tuned with reinforcement learning** (SB3 against the
   Gym core, per the farm `market_rl_*` pattern).
3. **The hackathon demo** — an operator-assistant product running on top of the
   engine's observation stream (alerts, explanations, recommendations, measured
   improvement vs blind baseline). The demo is the application; the engine is
   the asset.

Not a Kaggle engine re-implementation: there is no upstream factory engine to
wrap, so we own the rules. No parity suite against an official runner —
seed-determinism, golden states, and replay tests take its place.

## Anti-tape design goal (explicit, drives the whole sim design)

Kaggriculture's lesson: a fully deterministic engine + fixed leaders rewards
**taping** (memorizing trajectories) and lets the meta converge to mirrors.
amdrome is deliberately **less deterministic** so policy quality, not
memorization, dominates:

- **Stochastic environment dynamics**: order arrivals, machine failures,
  worker absence, input prices, and defect occurrences are drawn per-episode
  from seeded distributions — same seed replays identically (fairness,
  debugging), but cross-episode variance is real and large.
- **Partial observability** (kanban monitoring layer): agents never see full
  state; failures start as drift visible only where monitoring capacity was
  spent. Tapes can't encode what the agent couldn't see.
- **No canonical opponent set**: league play draws opponents from a policy
  pool, so there's no fixed leader to tape.
- **Acceptance test**: variance high enough that a tape-replay agent loses to
  a mediocre reactive agent.
- Anti-tape stochasticity must not become pure noise: signal (layout, labour,
  monitoring choices) must still dominate outcomes — the sim needs a measured
  skill/noise ratio, verified during design iteration.

## Core mechanics (the four evaluated skills)

1. **Layout** — a factory floor grid. The player buys and places **processing
   stations** (cut, form, weld, paint, inspect, pack, buffers). A **line** is a
   routing of jobs through stations; stations can be moved (costly, takes
   time), retooled, or duplicated. Transport time is distance-based, so layout
   drives cycle time and WIP.
2. **Labour organisation** — a fixed worker roster (skills, shifts, fatigue).
   Workers assigned to stations/shifts; understaffed stations run slow or
   stall; cross-training trades flexibility against skill; maintenance techs
   compete with production for the same roster.
3. **Monitoring (kanban)** — the player does NOT see full sim state.
   Information arrives via station cards, buffer pull signals, SPC samples,
   inspection results. Limited monitoring capacity (sensors/andon placement,
   inspection frequency). Catching drift earlier is the core skill — and it is
   literally the hackathon brief, which is why the demo product lives here.
4. **Market strategy** — a **shared market** across factories: order contracts
   with deadlines/penalties, spot sales, input procurement with volatile
   prices, capacity bidding.

## Cross-cutting failure & quality model

Stations degrade (wear → drift → breakdown) stochastically; tooling and labour
skill affect defect rates; defects flow downstream unless inspection catches
them (rework/scrap). Energy/material waste accrue from poor scheduling, rework,
idling. KPIs: throughput, on-time delivery, defect PPM, downtime %, cost/unit,
energy/unit, safety incidents.

## Evaluation & scoring

- One "shift" = one episode (target 200–500 ticks).
- League play: factories with different policies in the same market; score =
  delivered-contract profit minus penalties/scrap/energy, plus KPI league
  points (so a profit-rush bot shipping junk doesn't dominate).
- Episode count per match and seed policy are **design levers** for the
  skill/noise ratio (farm lesson: 12 seeds × 8 opponents minimum for stable
  verdicts).

## Architecture (reuse farm patterns)

```
simulator/            Gym-style core (pure python), self-play, league runner
  src/amdrome_sim/    core.py rules.py market.py kanban.py stations.py rng.py
  envs/               kaggle_environments episode runner + OpenEnv shell
  tests/              seed-determinism, golden states, invariants,
                      variance/skill-ratio measurement harness
agents/               sample agent (RL-tunable) + scripted baselines
rl/                   SB3 training entrypoints against the Gym core
research/             verified sim findings (measured, not vibes)
demo/                 hackathon product: operator console + assistant
tapes/                recorded episodes (debug artifacts — NOT a meta weapon)
```

Determinism rule: all randomness through ONE seeded generator per episode;
state transitions pure; same seed ⇒ bit-identical replay.

## Design iteration loop (before build beads are cut)

The sim design needs iteration before freezing the API — alex's explicit call:

1. Write the **design doc** (mechanics spec + RNG inventory: every stochastic
   element, its distribution, and what skill it tests).
2. **Prototype** one mechanic at a time (layout first — most structural);
   measure outcome variance vs decision sensitivity (skill/noise ratio).
3. Run the **anti-tape acceptance test** (tape agent vs mediocre reactive
   agent) and the **skill-dominance test** (good policy beats bad policy at
   episode counts the challenge can afford).
4. Revise distributions/levers until both pass; freeze episode API v1.
5. Then cut build beads for engine, sample agent, RL pipeline, demo.

## Build order (post-freeze beads)

1. Core loop + floor grid + stations + material flow.
2. Degradation/quality model + kanban observation layer.
3. Labour roster + shifts + maintenance.
4. Shared market + contracts + league runner + baselines.
5. Sample agent + RL tuning pipeline (knob-search first, SB3 second).
6. Demo: assistant over the kanban stream; measured A/B vs blind baseline.
7. Polish: metrics pack, 3-minute demo script, measured-improvement table.

## Risks / open questions (for alex)

- Scope vs hackathon clock: engine + sample agent + demo is the full set; if
  tight, ship demo on a reduced factory (no shared market) and keep market as
  the challenge's Phase 2.
- How Kaggle-shaped must v1 be? (kaggle_environments submission format from
  day one, or Gym core first and the kaggle wrapper later?)
- RL sample-efficiency: partial observability + long episodes are hard for
  model-free RL; sample agent may start as scripted-with-tunable-knobs (GEPA /
  random-search over knobs, per farm optimizer pattern) before full RL.
