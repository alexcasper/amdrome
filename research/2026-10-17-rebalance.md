# Economy rebalance: characters to break-even — 2026-10-17

Alex's balance pass (2026-10-17). **All pre-rebalance dollar figures in
the repo are superseded** — every table below is the rebalanced economy.
Method: economy knobs only (agents untouched), price-side preferred.
Sweeps on Explorer HPC (login node kills non-slurm compute).

## Economy diff

| knob | before | after |
|---|---|---|
| CONTRACT_PRICE | (360, 540) | **(560, 740)** |
| rival_bid_mu hyperprior | (0.85, 1.05) | **(0.80, 0.98)** |
| BREAKDOWN_COST | 1200 | **1400** |

Rationale: prices up = revenue opportunity (disciplined play pays);
softer rival pool lets shade-bidders (Charlie/Chen 0.90×) win their share
(compresses the discipline gap to fit the target bands); breakdown cost
+200 sharpens the negligence gradient (~$1.1k/ep extra for
non-maintainers). Four sweep rounds (16 combos) → c200_mu98_b1400.

## Before / after — character agents (blind + 5, same protocol)

| agent | before | after (100 eps, seeds 910000+) | target |
|---|---|---|---|
| blind | −4 458 | −2 057 | — |
| Checklist Charlie | −3 317 | **−92** | ~0 ±500 ✓ |
| Max Milliard | −2 958 | **+25** | ~0 ±500 ✓ |
| Panic Pete | −5 153 | −2 869 | −1.5..−2.5k (≈, 370 past) |
| Cheapskate Chen | −5 594 | −3 518 | −1.5..−2.5k (past — dual flaw stacks: lost bids + escapes) |
| reactive | −2 239 | +600 | ceiling above chars ✓ |
| random baseline | −5 972 | −2 827 | floor ✓ |

Ladder ordering preserved and monotone on the discipline axis:
random < {pete, chen} < blind < {charlie, milliard} < reactive.
Data: research/data/character_scores.jsonl.

## Assistant re-verification — held-out 2000-seed protocol (seeds 920000+, 1000 paired/arm)

| arm | net/ep | unplanned dt (ticks) | escapes/ep | breakdowns | edge vs blind |
|---|---|---|---|---|---|
| blind | −2 274 | 84.0 | 0.52 | 3.83 | — |
| assistant default (cbm 0.50) | −526 | 68.3 | 0.10 | 3.12 | +1 748 |
| **assistant CBM-40 (shipped config)** | **+4 472** | **10.4 (−88%)** | **0.03 (−94%)** | 0.46 | **+6 746** |
| assistant CBM-50 | +3 751 | 20.8 (−75%) | 0.05 | 0.92 | +6 025 |

The CBM assistant keeps a CLEAR margin above every character (+4.4k vs
Charlie's −92). **Action item**: the *default* assistant config (cbm
0.50, −526) now sits BELOW Charlie under the new economy — the shipped
default should flip to cbm 0.40 (strongest under both economies once
prices rose); handed to the demo lane with this data.

## Gates re-validated post-rebalance

- Anti-tape: tape win% full 3.0 / bids 1.0 / ops 3.0 — PASS (strongest
  yet; the wider contract prices punish bid-tapes harder).
- Determinism/golden: re-pinned (v7), 16/16 tests green.
