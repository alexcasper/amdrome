# amdrome

**Intelligent Industry Factory Simulation Engine & Autonomous Agent Benchmark**

`amdrome` is a discrete-event manufacturing simulation engine designed as both an open benchmark for reinforcement learning in the lineage of Kaggle simulation environments (`kaggriculture`), and the core asset for an **Intelligent Industry** hackathon demonstration.

---

## Deliverables & Architecture

1. **The Simulation Engine (`amdrome_sim`)**
   * Pure Python + NumPy discrete-event simulation core based on system dynamics (Sterman, *Business Dynamics*).
   * Dual interface: `kaggle_environments` compatible episode runner (JSON observation/action protocol) and Gymnasium / PettingZoo vector environments for RL.
   * Built from the ground up with an **anti-tape design guarantee**: hierarchical Bayesian hyperpriors and partial observability prevent trajectory memorization while preserving seed-level determinism.

2. **The Sample Agent Ecosystem (`agents/` & `rl/`)**
   * Readable scripted baselines: Blind Run-to-Failure, Lean Kanban Pull, and Adaptive Reactive Heuristics.
   * Parameter tuning pipeline using Bayesian search (Optuna / GEPA).
   * Stable-Baselines3 (MaskablePPO) training pipeline designed for fleet execution.

3. **The Intelligent Industry Demo Product (`demo/`)**
   * Live streaming **Operator Assistant** running over the kanban observation stream.
   * Statistical CUSUM drift detection and Weibull Remaining Useful Life (RUL) estimation.
   * Interactive Rich terminal operator console with real-time floor topology, andon boards, and prescriptive recommendations.
   * Automated paired A/B evaluation suite (`demo/benchmark/`), independently verified on 2000 held-out seeds (research/2026-10-17-ab-verification.md): with condition-based PM (`cbm_threshold=0.40`, `full_inspection=True`) the assistant cuts **unplanned** breakdown downtime 88% (95% CI 87–89%; total downtime incl. planned PM +24%) and defect escapes ~92% (CI 90–94%), +\$5.5k net/episode. The default (legacy-PM) assistant: −20% unplanned downtime, −82% escapes.

---

## Game Mechanics

### Current (in the engine today)

**World & layout.** Discrete ticks (episode = one production week, 336 ticks).
Grid floor is config-parameterized (`grid_w/grid_h`; default **12×8** —
challenge tier 16×12, cramped tier 8×6); stations (`cut, form, weld, paint,
inspect, pack` + buffers) occupy 1–4-cell footprints. Jobs are batches with
ordered routes, flowing station→buffer→station with distance-based transport
time. Layout is a real decision: physical moves take the station offline
(cost scales with distance); rebinding a line to an already-placed station
is the cheap move. Measured per grid size (400 paired seeds/point, layout
share of cycle-time variance / scenario share / compact-vs-scattered d_z):

| grid | policy share | scenario share | c−s d_z (cycle) |
|---|---|---|---|
| 8×6 | 47% | 38% | 2.49 |
| 12×8 (default) | 64% | 24% | 2.89 |
| 16×12 | 77% | 14% | 3.35 |

Bigger floors amplify layout skill and shrink scenario variance;
transport dominates at every size (blocking never binds with a single
line). Runtime is flat (~40 ms/episode full engine). Details:
`research/2026-10-17-grid-sweep.md`; factory expansion (buy-a-wing)
design at `DESIGN.md` §10.

**Degradation & failure.** Hidden per-station `wear ∈ [0,1]` driven by usage.
Wear inflates cycle time (gradual drift — the signal SPC monitoring can catch),
raises defect probability, and drives a convex breakdown hazard (infant
mortality + wear-out mix). Breakdowns take stations offline until a tech
repairs them; unplanned downtime propagates into WIP pileups.

**Quality & inspection.** Defects injected per operation (base rate × wear ×
skill); flow downstream to `inspect` stations or escape to the customer (PPM
penalty, contract risk). Inspection modes (skip / sample / full) set the
catch probability — and their economics are a live balance question (see
known issues).

**Labour.** Rostered workers with per-station-type skill vectors, fatigue
accumulation (error/injury multipliers), and random absences. Shared tech pool
contends between preventive maintenance and repairs. Actions: assignment,
cross-training, shift swaps, PM scheduling, worker-affinity matching.

**Monitoring (the skill surface).** The agent sees only the kanban layer:
coarse station cards every K ticks, cycle-time SPC samples *where it allocated
the limited sampling budget*, buffer pull signals at card granularity,
inspection counts, and alarms it configured — with false-positive rates that
make alarm tuning a real tradeoff. Measured: raising the sampling budget from
4→16 probes/shift cuts drift-detection latency 31% and missed breakdowns 47%.

**Market & procurement.** Stochastic contract arrivals (size, price, deadline,
quality floor, penalty) with sealed first-price bidding; mean-reverting jump
spot market; raw inputs at volatile prices with lead times — buy-ahead
inventory policy is a scored decision surface.

**Economics.** Calibrated costs with station-asymmetric wear ("prevention
pays, monitoring matters"). Score = delivered profit − penalties − scrap −
energy, plus KPI league points (ontime%, PPM, downtime%).

**Anti-tape RNG.** Every stochastic element (12-item inventory: arrivals,
prices, wear, breakdowns, cycle times, defects, escapes, absences, fatigue,
repairs, transport, bid opponents) is drawn from per-episode hyperprior
parameters — episodes differ structurally, so trajectory memorization fails
while seed-level determinism holds (sha256-derived seeds, per-episode
generators).

### Planned (spec'd or beaded — not landed)

- **RL training harness** (amdrome-x4i, in progress): knob-search +
  Stable-Baselines3 MaskablePPO fleet runs against the Gym core.
- **RL-tuned sample agent** (amdrome-u2e): readable baseline, tuned by RL.
- **Engine fixes from A/B verification**: understaffing currently *speeds*
  stations up (inverted staffing multiplier, amdrome-svf); full inspection is
  free, dominating the escape metric (amdrome-hpm).
- **Multi-factory shared-market self-play**: bidding opponents drawn from a
  policy pool; league/match runner with the acceptance gates (anti-tape +
  skill-dominance tests) from DESIGN.md §Acceptance.
- **`kaggle_environments` submission runner**: single-file agent submissions,
  per-turn timeout, episode replays.
- **Graphical floor view**: v1 sprite pack committed (`assets/sprites/`,
  9 sprites + regenerable PIL source); animations and an Aseprite-MCP
  authoring pass planned.
- Deliberately cut from v1: AGV/forklift pool (documented in DESIGN.md —
  score-weighting achieves the same skill surface cheaper).

---

## Documentation Suite

Detailed architecture, mathematical models, API contracts, and roadmap specifications:

* 📄 **[Master Comprehensive Plan](file:///mnt/d/ops/amdrome/docs/COMPREHENSIVE_PLAN.md):** Overall system blueprint, strategic lessons from kaggriculture, acceptance gates, and delivery plan.
* 📐 **[Simulation Mechanics Specification](file:///mnt/d/ops/amdrome/docs/SPEC_MECHANICS.md):** Mathematical models of world topology, stock-flow queues, wear degradation, defect cascades, labour fatigue, market bidding, and two-tier RNG inventory.
* 🔌 **[API & Environment Specification](file:///mnt/d/ops/amdrome/docs/SPEC_API_ENV.md):** `kaggle_environments` JSON schema, Gymnasium `FactoryGymEnv` interface, PettingZoo multi-agent interface, and headless runner CLI (`bin/run_match.py`).
* 🖥️ **[Demo Product Specification](file:///mnt/d/ops/amdrome/docs/SPEC_DEMO_PRODUCT.md):** Operator Assistant analytical architecture, terminal UI layout, paired A/B benchmark methodology, and 3-minute pitch script.
* 🗺️ **[Roadmap & Beads Breakdown](file:///mnt/d/ops/amdrome/docs/ROADMAP_AND_BEADS.md):** Phased project roadmap, Beads task hierarchy, and fleet infrastructure execution protocol.
* 📜 **[Project Charter](file:///mnt/d/ops/amdrome/CHARTER.md):** Ratified charter, hackathon brief, and anti-tape design goals.
* 🛠️ **[Design v0 Workbench](file:///mnt/d/ops/amdrome/DESIGN.md):** Working design document and initial layout prototype findings.

---

## Fleet Execution Protocol (Hard Constraint)

* **Dawn (Local Host):** Orchestration, code editing, git versioning, beads management, fast test execution (<10s). Dawn does **no heavy simulation or sweep runs**.
* **Fleet Hosts (`dusk`, `albion`, `midknight`):** Headless episode execution, parameter sweeps, and RL training dispatched via stateless CLI runners over SSH.
