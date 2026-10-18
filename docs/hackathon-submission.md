# amdrome — lablab.ai AMD hackathon Act III submission package

Paste-ready in lablab field order. Quality gate: every number traces to a
repo source (listed at the bottom); no invented AMD claims.

## Title

AMDrome: A Factory-Economy Benchmark for Industrial AI Agents

## Short description

amdrome is an open, seed-reproducible factory-simulation benchmark for the
Intelligent Industry track. Agents run a production line under partial
observability: they schedule maintenance, inspect for quality, staff stations,
lay out the floor and bid for contracts. An operator assistant built on top
cuts unplanned breakdown downtime by about three quarters in a pre-registered,
held-out A/B test.

## Long description

**What it is.** amdrome is a discrete-event manufacturing simulator built as a
Kaggle-style challenge. The engine is pure Python with no dependencies, plus
Gym and kaggle_environments-style episode runners for single-file agent
submissions.

- **The line:** six stations (cut → form → weld → paint → inspect → pack) on a
  grid-size-parameterised factory floor.
- **Mechanics:** wear-driven degradation with a hazard cliff, drift in cycle
  times, defect injection with inspection and rework, and a labour roster with
  absence and staffing effects.
- **Markets:** a spot input market, plus sealed-bid contracts against a pool of
  rival bidders drawn per episode.
- **Partial observability:** agents only ever see a kanban card stream, never
  the true machine wear.
- **Anti-tape design:** every episode draws its scenario from a hyperprior, so
  replaying a memorised action tape loses to a mediocre reactive agent. The
  engine-level anti-tape gate passes (3/1/3% tape win rate after the economy
  rebalance).
- **Planned, not yet in the engine:** manufacturing chains (multiple products
  with their own routes) are specified in `docs/SPEC_PRODUCT_MIX.md`.

**The floor size is a real lever.** We measured how much of the variance in
cycle time comes from the policy versus the scenario, compact versus scattered
layouts, 400 paired seeds per size:

| floor | policy share | scenario share | effect size (d_z) |
|---|---|---|---|
| 8×6 | 47% | 38% | 2.49 |
| 12×8 (default) | 64% | 24% | 2.89 |
| 16×12 | 77% | 14% | 3.35 |

Bigger floors give more room to be bad. The 12×8 default keeps the balance
between skill and anti-tape scenario variance.

**The agent stack.**

- **Character agents** with documented personas and flaws: Checklist Charlie,
  Max Milliard, Panic Pete, Cheapskate Chen. They are bracketed by a random
  floor and a reactive CUSUM/PM ceiling.
- **Operator Assistant** (the demo product). It reads the kanban stream and
  ranks alerts and recommendations. Its condition-based PM module infers each
  station's wear rate from the realised per-operation cycle times and services
  machines before the hazard cliff.
- **RL path:** a Stable-Baselines3 MaskablePPO training harness over the Gym
  wrapper, plus a knob-search tuner.

**Measured, not promised.** The assistant's headline claims were verified
independently: fresh seeds, a pre-registered held-out set, ratio-of-means
reductions with paired seed-bootstrap 95% CIs, and two independent harnesses
that agree exactly. The verification found that our original pitch claims
(">70% downtime, >90% escapes") were targets that had never been measured. We
corrected the documentation.

- **Held-out result, 2000 paired episodes** (condition-based PM, threshold 0.40,
  pre-rebalance economy): **+$5,471 per episode** against a run-to-failure
  baseline, winning 96% of episodes.
- **Current engine** (after the labour fixes, default threshold 0.50):
  **unplanned downtime −73.6%** (95% CI 72.4–74.8%) with total downtime
  including planned PM roughly flat (+1.6%).
- **Defect escapes fall about 91%,** but this depends on 100% inspection being
  free in the engine, an open design issue we disclose rather than hide.

**Real engineering lineage.** Independent review found that the labour coupling
had both signs inverted. Understaffed stations ran *faster* (fixed in
`8ed7aff`), and low-skill workers produced *fewer* defects (fixed in `d9a7ed8`).
Both fixes have regression tests that fail on the old code. After the fixes, the
gap between the skilled reactive agent and the baseline grew (d_z 0.77 → 0.87),
and the anti-tape gate still passes.

**Economy balance: rebalanced and verified.** The 2026-10-17 rebalance
(contract prices, rival pool, breakdown cost) tunes the economy so
disciplined personas break even and negligent ones lose (100 paired
episodes, seeds 910000+):

| agent | net $/episode |
|---|---|
| random baseline | −2 827 |
| Panic Pete (no prevention) | −2 869 |
| Cheapskate Chen (spend nothing) | −3 518 |
| blind run-to-failure | −2 057 |
| Checklist Charlie (by-the-book) | **−92** |
| Max Milliard (over-corrector) | **+25** |
| reactive ceiling | +600 |
| operator assistant (CBM-40) | **+4 472** |

**How it was built.** amdrome was developed by a multi-agent LLM team working in
parallel terminal panes: a GLM coordinator, plus Claude and Gemini worker
agents. Work was tracked as beads issues, each agent committed per feature, and
batch compute went to fleet hosts and an HPC cluster rather than the desktop.

**Compute and AMD relevance.**

- The engine and benchmarks are CPU-only, pure-Python and stdlib — any
  stack, any vendor, runs the benchmark.
- **Runs on AMD: RL policy training (Stable-Baselines3 MaskablePPO)
  executes on AMD Radeon 9700 XT via ROCm** — see
  `docs/assets/amd-rocm-run.log` for the measured run. (If that log has
  not landed by submission time, the honest fallback line is: "The
  PyTorch/SB3 stack is ROCm-portable; validated on the same stack that
  ran the farm agent on an R9700." Do NOT quote a number without the
  log.)
- Earlier training runs used NVIDIA A100s on a university cluster; the
  benchmark itself is vendor-neutral.

## Cover image

`docs/assets/cover.png` (generated from the project's own sprite pack:
the production line, andon alert, wear gauges, and the measured headline
numbers)

## Slides

`docs/assets/slides.md` — 8 beats: problem, engine, partial observability,
anti-tape, decision surfaces, assistant A/B result, honest engineering,
AMD/ROCm.

## Video plan

`docs/assets/video-plan.md` — 3 minutes: viz walkthrough (0:00), assistant
console catching drift before the breakdown (0:30), measured tables
(1:20), ROCm log + stack (2:10). The visualizer serves live for the
recording.

## Demo URL

http://dawn.saiga-beaufort.ts.net:9122 — live episode visualizer (HTML5
Canvas; scrubber, playback, per-tick KPI ticker; loads a dumped episode
from JSON, never inlined).

## Repo URL

https://github.com/alexcasper/amdrome

> NOTE FOR SUBMITTER (alex): the repo is currently PRIVATE — lablab
> requires a public GitHub repo. Flip visibility (or grant lablab access)
> before clicking submit.

## Technology tags

Python · Reinforcement Learning · Stable-Baselines3 (MaskablePPO) · PyTorch ·
Gymnasium · Kaggle Environments · Simulation · Benchmark · Multi-agent ·
Predictive Maintenance · Statistical Process Control · HTML5 Canvas
visualisation

*(Note for the submitter: the episode visualiser `viz/index.html` is HTML5
Canvas, not D3. The "D3 viz" tag was left out so the submission doesn't claim
something the code doesn't do.)*

Sources: `research/2026-10-17-ab-verification.md`,
`research/2026-10-17-labour-svf.md`, `research/2026-10-17-grid-sweep.md`,
`research/2026-10-17-character-roster.md`, `research/2026-10-17-rebalance.md`,
`DESIGN.md`, `README.md`.
