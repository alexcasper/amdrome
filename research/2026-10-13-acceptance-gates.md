# Acceptance gates at prototype scope: measured verdict — 2026-10-13

Bead: amdrome-3zh (Phase0 anti-tape + skill-dominance gates). Host: **t3**
(8c ARM, Python 3.10) — all sweeps off-dawn; dusk flapping / albion offline
at run time. Harness: `simulator/proto_gates.py` (pure stdlib, stateless
CLI); data: `research/data/gates_final.jsonl` (+ gates_results/gates_pm2/
gates_pm3 iteration history). 400 paired seeds per anti-tape surface,
200 per skill pair; common-random-numbers pairing (shared arrival stream
per seed across policies).

Economic score (layout surface): `40·completed − 30·rejected − 3·wip_mean
− 1.0·cycle_mean`; degradation surface uses the prototype's net profit.
Scenario hyperprior widened for the gates: λ ∈ U[0.08, 0.17] (line capacity
≈ 0.10–0.14), so both starvation and congestion regimes occur.

## Results

| gate | comparison | n | Δmean ± sd | d_z | z | p | win% | verdict |
|---|---|---|---|---|---|---|---|---|
| skill_good_bad | good − bad | 200 | +220.9 ± 186.4 | 1.19 | 16.8 | 5e-63 | 85.5% | **PASS** (DESIGN §7 gate 3: ≥95% conf at ≤200 ep) |
| skill_good_med | good − mediocre | 200 | +91.9 ± 118.3 | 0.78 | 11.0 | 5e-28 | 55.5% | **PASS** |
| anti_tape (capacity) | tape vs mediocre | 400 | −81.4 ± 105.6 | −0.77 | −15.4 | 1e-53 | tape 93.0% | **FAIL** |
| anti_tape_pm (PM timing) | tape_pm vs spc_reactive | 400 | +63.0 ± 3790 | 0.02 | 0.3 | 0.74 | tape 49.8% | **FAIL** |

Agents: good = compact layout + per-shift adaptive buffer allocation
(λ̂ from cumulative kanban pull count, 6 decisions/episode); mediocre =
compact + fixed even allocation; bad = scattered + fixed; tape = replays
good's per-shift allocation sequence recorded under seed 7; tape_pm =
replays spc_reactive's PM schedule recorded under seed 7.

Three lever-revision iterations on the PM surface (wear-rate hyperprior
2.5×→5× spread, hazard cliff BETA 0.045→0.15 / GAMMA 3→6, PM trigger
loosened, PM duration 12→8) moved tape win 48%→52%→50% — plateau, stopped
after 3 attempts.

## Why gate 2 fails at prototype scope (causal, not incidental)

1. **Asymmetric-risk surfaces don't punish tapes.** On the capacity
   surface a stale hot-λ allocation (big inbuf, small downstream) is
   merely wasteful on cool scenarios and excellent on hot ones — never
   actively harmful. A tape of a good policy therefore *beats* the fixed
   mediocre agent (93%). Tapes are only punished when wrong decisions are
   harmful, not when they are wasteful.
2. **Decision density is too low.** 6 reallocation ticks per episode, and
   effectively 1–2 PM events per episode (CUSUM detection rarely converts
   to PM under this prototype's trigger path). With ~10 scenario-coupled
   decisions, a tape has few opportunities to be wrong; mistiming one PM
   is worth ~$250–1500 against a per-episode breakdown-noise floor of
   σ ≈ $3800.
3. **No adversarial/commons surface exists yet.** The designed anti-tape
   backbone — the shared market (bidding against volatile prices, penalty
   contracts) — is absent from both prototypes. There, replaying S0's bid
   prices under a different price draw loses money *symmetrically*
   (overpay when prices dropped; lose contracts when they rose), every
   contract round.

## Design requirements carried into the engine (p1a/p2a)

- Anti-tape gate 2 must be re-run **at engine level with the shared market
  live** (new bead; blocked by p2a). Prototype verdict: gate 2 is not
  passable — by construction, not by tuning — on layout/capacity/PM-only
  surfaces.
- v1 episodes need **≥50 scenario-coupled decision points** (per-shift
  allocation + every contract round + PM plan), each with symmetric
  penalties.
- Keep the hyperprior draw as primary lever (validated: λ spread 2× makes
  capacity decisions pivotal), but pair it with observability limits so
  tapes encode wrong beliefs (partial observability already specced).
- Paired comparisons should use common random numbers (shared flow stream
  per seed): cut paired σ ~35% vs policy-specific streams here.
- Skill gate at composite economic score reached d_z=1.19 (85.5% wins)
  even with near-saturated λ; cycle_mean alone reaches d_z≈2.4 (layout
  sweep). Engine scoring should let delivered-profit + cycle/WIP compose
  to d_z>2 (expected: breakdown/defect variance shrinks once PM is
  controllable at engine level).

## Verdict

- Gate 3 (skill dominance): **PASS** at DESIGN §7's criterion (≥95%
  confidence at ≤200 paired episodes; measured z=16.8). The roadmap's
  tightened d_z>2.0 form is not met on the composite score at prototype
  scope — re-verify at engine level alongside gate 2.
- Gate 2 (anti-tape): **FAIL at prototype scope — deferred to engine-level
  re-run** with the shared market live (design requirements above).
- API freeze: findings ADD a freeze requirement (market surface mandatory
  in v1 scoring; ≥50 scenario-coupled decisions/episode) rather than
  block it.
