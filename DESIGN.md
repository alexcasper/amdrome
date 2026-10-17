# amdrome engine design — v0 draft (iteration target, NOT frozen)

Companion to CHARTER.md. Bead: amdrome-is5. This doc is the design-iteration
workbench: mechanics spec, RNG inventory, API sketch, portability plan. It is
*frozen* only when the anti-tape and skill-dominance tests pass (see
"Acceptance gates").

> **Comprehensive Specification Suite:**  
> The comprehensive architectural plan and formal specifications building on this draft are available in:  
> - [docs/COMPREHENSIVE_PLAN.md](file:///mnt/d/ops/amdrome/docs/COMPREHENSIVE_PLAN.md) — Master System Blueprint & Lessons from Kaggriculture  
> - [docs/SPEC_MECHANICS.md](file:///mnt/d/ops/amdrome/docs/SPEC_MECHANICS.md) — Formal Mathematical Mechanics & 2-Tier RNG Inventory  
> - [docs/SPEC_API_ENV.md](file:///mnt/d/ops/amdrome/docs/SPEC_API_ENV.md) — `kaggle_environments` Schema & Gymnasium / PettingZoo Dual API  
> - [docs/SPEC_DEMO_PRODUCT.md](file:///mnt/d/ops/amdrome/docs/SPEC_DEMO_PRODUCT.md) — Operator Assistant Architecture, CUSUM Drift & A/B Benchmark  
> - [docs/ROADMAP_AND_BEADS.md](file:///mnt/d/ops/amdrome/docs/ROADMAP_AND_BEADS.md) — Phased Roadmap, Beads Breakdown & Fleet Protocol  

Sterman's *Business Dynamics* (RESEARCH/, OCR in flight) is the theory base
for the stock/flow structure: WIP buffers are stocks, production/defect rates
are flows, the kanban layer is the information-feedback path with its own
delays — drift detection latency is literally a delay in an information
feedback loop, which is why monitoring capacity buys measurable KPI gains.

## 1. World model

- **Time**: discrete ticks. Episode = one production week, 336 ticks
  (7 shifts × 48) — subject to the runtime budget test (§7).
- **Floor**: grid, config-parameterized (`grid_w/grid_h`, default **12×8** —
  balanced policy/scenario split; 16×12 is the challenge tier via expansion,
  see research/2026-10-17-grid-sweep.md). Stations occupy footprints
  (1–4 cells — the larger grids are headroom for v1 multi-cell footprints
  and simultaneous lines);
  buffers occupy 1. Moving a station takes it offline for T_move ticks
  (scaled by distance).
- **Stations** (types): `cut, form, weld, paint, inspect, pack` + `buffer`.
  Each has: processing time distribution, footprint, cost, wear rate,
  defect-injection sensitivity, skill requirement.
- **Jobs**: batches with a route (ordered station types). Released at the
  line's entry buffer, flow station→buffer→station; transport time =
  manhattan distance × unit cost; forklift/AGV pool optional (cut if heavy).
- **Lines**: a named route + station bindings. Rebinding a line to a different
  station instance = layout decision, not a physical move, when both are
  already placed (cheap); physical moves are the expensive action.

## 2. Degradation & quality

- Each station has hidden state `wear ∈ [0,1]`, driven up by usage.
- Wear raises: cycle-time multiplier (drift), defect probability, and
  breakdown hazard (hazard convex in wear — infant-mortality + wear-out mix).
- **Drift is gradual**: cycle time inflates e.g. +0.2%/tick of wear — the
  signal a monitoring policy can catch from SPC samples.
- **Breakdown** = hard failure: station offline until a tech repairs
  (duration by severity). Unplanned downtime propagates to WIP pileup.
- Defects: injected per-op with p(base, wear, skill); flow downstream to
  `inspect` (catch prob by inspection mode) or escape to customer (PPM
  penalty, contract risk). Rework loops back to the failed op's station.

## 3. Kanban observation layer (the skill surface)

The agent sees ONLY:
- **Station cards**: per-station status snapshot every K ticks (queue depth,
  utilization, andon state) — coarse.
- **SPC samples**: cycle-time measurements, but only for stations where the
  player allocated a sampling budget (limited samples/shift).
- **Buffer pull signals**: kanban card movement (WIP visible at card
  granularity, not job granularity).
- **Inspection results**: defect counts at inspect stations.
- **Alarms**: threshold events the player configured — with false-positive
  rate so alarm tuning is a real tradeoff.

Monitoring actions: allocate/reallocate sample budget; set alarm thresholds;
add sensor to a station (costly, permanent); order inspection mode
(skip/sample/full). This is where the demo assistant plugs in: it reads the
same kanban stream and recommends allocations.

## 4. Labour

- Roster: N workers with skill vector per station type, shift assignment,
  fatigue accumulator (error/defect multiplier, injury hazard).
- Techs: M maintenance techs shared across the fleet of stations; PM
  (preventive maintenance) vs repair contention.
- Actions: assign worker→station, cross-train (takes shifts), shift swaps
  (fatigue vs coverage), PM scheduling.

## 5. Market (shared, multi-factory)

- Contracts: arrive stochastically (size, price, deadline, quality floor,
  penalty). Bidding: sealed first-price per contract round.
- Spot market: price follows mean-reverting jump process; factories are
  price-takers.
- Inputs: raw stock purchasable at volatile price; lead time + order
  quantity decisions (classic inventory policy surface).
- Score: delivered profit − penalties − scrap − energy, plus KPI league
  points (ontime%, PPM, downtime%).

## 6. RNG inventory (every stochastic element, v0)

| # | Element | Distribution (v0) | What skill it tests | Observed via |
|---|---------|-------------------|---------------------|--------------|
| 1 | Order arrivals | Poisson(λ(t)) by product | capacity planning, bidding | market feed (public) |
| 2 | Spot/input price | mean-reverting jumps (OU+jump) | procurement timing | market feed (public) |
| 3 | Wear increment per op | Beta-ish, heavy tail per station class | PM timing, monitoring | hidden; SPC drift |
| 4 | Breakdown arrival | hazard h(wear), Weibull-ish convex | redundancy, maintenance priority | andon (if sensed) |
| 5 | Cycle time | lognormal around wear-drifted mean | layout, staffing, SPC detection | SPC samples only |
| 6 | Defect injection | Bernoulli p(wear, skill, tooling) | inspection placement, quality | inspect results |
| 7 | Inspection escape | Bernoulli by mode (skip/sample/full) | inspection mode economics | customer returns (lagged) |
| 8 | Worker absence | Bernoulli/day + sickness bursts | cross-training, slack | roster card |
| 9 | Fatigue accumulation | deterministic + noise | shift design | coarse |
| 10 | Repair duration | lognormal by severity | tech allocation | tech card |
| 11 | Transport time | deterministic(distance) + noise | layout (buffer placement) | WIP cards |
| 12 | Contract bid opponents | drawn from policy pool | market strategy | outcomes only |

Design rules: one `numpy.Generator` per episode seeded by (match_seed,
episode_idx); the *parameters* of distributions are themselves drawn once per
episode from a hyperprior (so episodes differ in λ, wear rates, etc. — this is
the primary anti-tape lever); hyperprior draws use a separate generator so a
"scenario" can be logged and replayed without the whole episode.
**Never seed a generator with the hash of a tuple/string** (PYTHONHASHSEED
salting breaks replay determinism across processes) — derive integer seeds
via sha256 (`gen_seed` in `simulator/proto_layout.py`).

### Measured findings (layout mechanic, 2026-10-13, sweeps on dusk)

See `research/2026-10-13-layout-variance.md`. Headlines:

- Layout explains 53–64% of cycle-time variance (scenario 24–32%, noise
  ~12–15%) — skill-dominated with real cross-episode variance, i.e. the
  anti-tape profile. Paired verdicts between distant layouts: 1–9 episodes.
- Throughput is only weakly layout-coupled (transport delays don't consume
  station capacity; blocking rarely binds) → **score must weight cycle
  time/WIP/cost-unit, not throughput alone**; λ hyperprior should sit near
  line saturation (~85–95% capacity).
- AGV pool (§9): CUT from v1 — its only real role would be coupling layout
  to throughput; score-weighting achieves the same skill surface cheaper.
- Runtime: ~0.6 ms/episode on dusk → league match well under budget (gate 4).

### Measured findings (degradation & monitoring mechanic, 2026-10-13, sweeps on t3)

See `research/2026-10-13-degradation-variance.md`. Bead: amdrome-96z. Headlines:

- **Detection-latency vs monitoring budget curve (Sterman information delay):**
  $B=4 \to 8 \to 16$ probes/shift compresses mean CUSUM drift detection latency from
  $32.2 \pm 23.5 \to 25.6 \pm 16.3 \to 22.2 \pm 14.4$ ticks ($-31\%$), and cuts
  missed breakdowns from $0.45 \to 0.24$ per episode ($-47\%$).
- **Downtime reduction:** Reactive SPC maintenance with $B=16$ cuts unplanned downtime
  by $-9.3$ ticks ($31.1$ vs $40.3$, $d_z = -0.22, N95 = 77$) and breakdowns by $-28\%$ ($d_z = -0.27$).
- **Targeted PM vs blind periodic PM:** Reactive SPC PM outperforms fixed periodic PM
  by $+\$470.9$ net profit ($55.2\%$ win rate, $d_z = +0.13, N95 = 246$) because it targets
  interventions only when CUSUM confirms true wear ($0.2$ PMs/ep vs $5.9$ blind PMs).
- **Default telemetry budget:** Set to $B = 8$ probes/shift for v1.0.
- **Runtime budget (gate 4):** 2,000 paired episodes executed in $<6.0$ s on fleet host
  `t3` (~0.7 ms/episode/336 ticks). Dawn compute constraint strictly respected.

## 7. Acceptance gates (before API freeze)

**Measured status (2026-10-13, prototype scope — see
research/2026-10-13-acceptance-gates.md, sweeps on t3):**
- Gate 1 (seed determinism): prototype-level PASS (sha256 gen_seed;
  verified same-seed identical output).
- Gate 2 (anti-tape): **PASS at engine level (2026-10-13)** — tape win%
  9.0/13.0/7.5 (full/bids/ops) vs mediocre reactive over 200 paired
  episodes on t3 (research/2026-10-13-engine-gates.md). The market surface
  (sealed bids + spot-sales floor, added after a win-by-not-playing
  pathology) provides the symmetric penalties the prototypes lacked.
- Gate 3 (skill dominance): **PASS — calibrated 2026-10-14, re-measured
  after the procurement + labour surfaces**: reactive vs blind edge
  +$2032/ep, episode d_z 0.77 (p=2e-27, 77% win, n=200); match-level
  (mean of 5) d_z 1.62, 92.5% win, p=2e-24. The tighter the decision
  surface, the more paired noise — verdict confidence stays extreme
  (z≈10) and match-level scoring (≥5 episodes) remains the recommended
  verdict unit. Calibration history: research/2026-10-14-sim-calibration.md.
- Gate 4 (runtime): PASS (~0.6–0.7 ms/episode on dusk/t3).

1. **Seed determinism**: same seed ⇒ identical state hash at every tick.
2. **Anti-tape**: an agent that replays a recorded action tape from a
   strong-policy episode under a *different* hyperprior draw loses to a
   mediocre reactive agent (median over ≥100 paired episodes).
3. **Skill dominance**: scripted-good beats scripted-bad (layout/labour/
   monitoring variants) with ≥95% confidence at ≤200 episodes/match.
4. **Runtime budget**: full episode in <1s CPU single-factory; league match
   (8 factories × 50 episodes) parallelizes across cores (fleet hosts).

## 8. Portability & runner design (hard constraint: dawn does no heavy runs)

- `amdrome_sim` is pure Python + numpy only. No GPU, no dawn-local daemons.
- `bin/run_match.py`: stateless CLI — inputs: match spec JSON + agent files +
  seed block; outputs: results JSONL + tapes. Runs anywhere (dusk, albion,
   HPC, container). No network, no shared state.
- League harness = a dispatcher (runs on dawn) that ships agent dirs +
  spec to a host over SSH (`ssh dusk '... run_match.py'`), executes under
  `tmux`/`systemd-run`, and pulls back JSONL. Timeout + retry policy built in.
- Design iteration benchmarks (§7 gates 2–4) run through the same runner —
  so from the first week, heavy sweeps execute off-dawn by construction.
- CI-light: pytest unit tests (fast, dawn-safe: seconds) vs gate benchmarks
  (remote-only, invoked explicitly via `bin/run_gates.sh --host dusk`).

## 9. Open design questions (iterate here)

- Episode length & tick granularity (336 too long? sampling aliasing).
- ~~AGV/forklift pool~~ — CUT from v1 (measured 2026-10-13: see §6 findings;
  revisit only if adjacent-layout throughput separation becomes a goal).
- Alarm false-positive mechanics: independent FP process vs threshold on
  noisy observation (latter — cleaner theory, same surface).
- Market v1 scope for the demo: single-factory + exogenous prices, league
  only for the challenge build.
- Scoring weights (throughput vs cycle/WIP/cost-unit) — prototype says
  cycle/WIP must carry weight; exact weights TBD after mechanic-2 prototype.

## 10. Factory expansion (buy-a-wing) — design (2026-10-17, alex order)

Players start with a base plot (**8×6**) and may purchase adjacent
expansion wings (each **+4×6 block**, direction chosen) — modeled on the
farm's buy-a-quadrant mechanic. The floor is the owned region; unowned
cells render dark/blocked in the viz and are invalid move/expand targets.

- **Pricing model: upfront purchase** (not per-episode rent) — one
  decision, clean accounting, mirrors the farm precedent. Wing prices
  drawn from a HYPERPRIOR per episode (anti-tape: expansion timing is
  scenario-dependent).
- **Balance data**: research/2026-10-17-grid-sweep.md — with a single
  line, extra cells have ~zero direct value (compact is size-invariant);
  wings are options on multi-line capacity, station duplication, and
  product-mix long routes. v1 wing prices therefore start LOW and key
  off what the wing unlocks; re-price once product-mix lands.
- **Action**: `expand: {direction}` at episode start or at shift
  boundaries (REALLOC_TICK points). Behind the `factory_expansion`
  config flag (default off) until its own A/B lands: does buying wings
  beat staying small across configs (paired, n≥200)?
- **Interactions**: product-mix (long-route products justify bigger
  floors — SPEC_PRODUCT_MIX.md); labour (more stations need more
  workers/techs); anti-tape (larger owned floors raise layout skill
  share but shrink scenario variance — the hyperprior pricing keeps
  expansion timing non-memorizable).
