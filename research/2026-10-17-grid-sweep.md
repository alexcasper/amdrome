# Grid-size sweep: 8x6 / 12x8 / 16x12 — balance data for factory expansion — 2026-10-17

Alex's grid-sweep order (supersedes the plain 16x12 switch): grid is now a
config parameter (`Engine(grid_w, grid_h)`, proto `--grid W H`); this sweep
is the balance data that prices expansion wings (follow-up design).

Host: Explorer HPC. Data: `research/data/gridsweep/*.jsonl`
(3 sizes × 3 policies × 400 paired seeds, compact/clustered/scattered).
Engine timing: 60 eps/point with the full reactive agent.

## Per-size table

| size | policy share of cycle variance | scenario (seed) | residual | compact−scattered d_z (cycle) | throughput edge (units/ep) | engine ms/ep |
|---|---|---|---|---|---|---|
| 8×6 (48 cells) | 47.1% | 37.8% | 15.0% | −2.49 | +1.4 | 39.5 / 41.3 |
| 12×8 (96) | 63.9% | 24.1% | 12.0% | −2.89 | +2.5 | 40.0 / 40.3 |
| 16×12 (192) | 76.7% | 13.9% | 9.4% | −3.35 | +3.4 | 40.0 / 41.4 |

(compact/scattered columns of the timing pair.)

## Findings

1. **No skill-gap collapse at either extreme.** The compact-vs-scattered
   gap *grows* with floor size (d_z 2.49 → 3.35; throughput edge +1.4 →
   +3.4 units/ep): a bigger floor is more room to be bad. At 8×6 the gap
   persists because scattered mean hop distance (~5–6) still dwarfs the
   compact snake (~1).
2. **Regime: transport dominates at every size; blocking never binds**
   (blocked_ticks = 0 everywhere). Even 8×6 is not "cramped" for a single
   12-entity line — true crampedness requires v1 multi-cell footprints or
   simultaneous lines occupying the floor.
3. **Compact is size-invariant by construction** (snake walk keeps hop
   adjacency ≈1 at any size) — identical numbers across all three sizes.
   The size lever acts ONLY on how costly bad layouts are.
4. **Runtime is flat ~40 ms/ep across sizes** (obs construction dominates,
   not grid geometry) — well under the 1 s/episode budget; grid size is
   computationally free. Proto stays sub-ms.
5. **Anti-tape trade-off**: bigger floors raise the policy share (64→77%)
   but shrink scenario variance (24→14%) — the anti-tape lever weakens as
   layout dominates. 12×8 keeps the balance that the original measurement
   (53–64% policy share, 12×8-era) established.

## Default grid: 12×8

12×8 is the balanced point (policy 64% / scenario 24% / noise 12%), keeps
every historical figure quotable without annotation, and preserves the
anti-tape variance share. 16×12 is the recommended CHALLENGE tier
(maximum layout skill share, headroom for multi-line), reachable through
the expansion mechanic rather than the default.

## Wing-pricing implications (for the expansion design, DESIGN.md §10)

With a single line, **extra cells have ~zero direct value** (compact is
size-invariant) — wings are options whose payoff materializes with
product-mix multi-lines, station duplication, and multi-cell footprints.
Consequences: (a) v1 wing prices must be LOW or expansion is never
rational; (b) the honest price curve keys off what the wing UNLOCKS
(line count, long-route products), not raw variance numbers; (c) the
anti-tape counterweight (scenario share falls with size) argues for
pricing wings from a hyperprior so expansion timing is scenario-dependent.
