# Engine-level acceptance gates: verdict — 2026-10-13

Bead: amdrome-gn6 (spun out of amdrome-3zh). Host: **t3** (ARM, py3.10);
harness `bin/run_anti_tape.py` + `bin/run_match.py`; data:
`research/data/gate2_engine.jsonl`, `skill_engine.jsonl`, `skill_engine2.jsonl`.

Engine at test time: amdrome_sim v0.1 + spot sales (uncontracted units sell
at 0.75×spot; defective spot units −$400) — added after the first smoke
showed a **win-by-not-playing pathology**: without a spot floor, ~half of
production was stranded (no contract to deliver into), so zero-bidding
tapes beat the reactive baseline 67%. Charter's market spec (contracts +
spot sales) fixes the incentive; after the fix, agents cluster around
breakeven and bidding pays (league: eager +518, blind +14, shrewd −179
mean over 10 ep).

## Gate 2 (anti-tape) — PASS

Tape = full recorded action stream of shrewd under seed 7 (336 ticks),
replayed under 200 fresh scenario draws vs mediocre reactive (shrewd).
Bids are mapped by ORDINAL onto the fresh contract draws (memorized
absolute prices land on different face values); pm/probes/caps replayed
verbatim.

| tape variant | win% vs mediocre (n=200) | verdict (<30%) |
|---|---|---|
| full action stream | **9.0** | PASS |
| bids only | **13.0** | PASS |
| ops only (pm/probes/caps) | **7.5** | PASS |

The market surface does what the prototype couldn't (cf.
research/2026-10-13-acceptance-gates.md: prototype tapes won 93%/tied
50%): replayed bid prices overpay or lose contracts under fresh price
draws — symmetric penalties, as designed.

## Gate 3 (skill dominance) at engine level

| pair | n | Δmean ± sd | d_z | z | p | win% |
|---|---|---|---|---|---|---|
| eager − cautious | 200 | +1671.7 ± 2305.8 | 0.73 | 10.3 | 1.2e-24 | 74.0 |
| shrewd − cautious | 200 | +538.0 ± 2750.5 | 0.20 | 2.8 | 5.7e-03 | 54.0 |

**PASS at DESIGN §7's criterion** (scripted-good beats scripted-bad with
≥95% confidence at ≤200 episodes: p=1e-24). The roadmap's tightened
d_z>2.0 composite form is NOT met — d_z measures the *quality gap of the
agents*, and the current pool is deliberately untuned (shrewd's
monitoring heuristics cost it variance). That check is re-scoped to
amdrome-6k2/u2b (tuned baselines + knob-search/RL), where it belongs;
the engine provides fair, discriminating pairing (74% win, clean
separation at p=1e-24).

## Engine changes this bead

- market.py: SPOT_SELL_FRAC/SPOT_DEFECT_PENALTY (charter spot-sales lane)
- core.py: spot fallback in _deliver, spot_units counter in results
- golden hash re-pinned (cd489b39…); full test suite green
