# Character agents: roster, scores, ladder — 2026-10-17

Bead: amdrome-iuf. Scores: Explorer HPC (fleet was dark), seeds 910000+,
n=100 paired episodes, compact layout. Data:
`research/data/character_scores.jsonl`. Tests: `simulator/tests/
test_characters.py` — 5 agents × 3 configs (compact/336, scattered/336,
compact/168) × 3 seeds, zero errors, per-seed deterministic.

## Score table (mean net $/episode; ladder requirement: random < char < reactive)

| agent | net | PMs | breakdowns | PPM | escapes | ladder |
|---|---|---|---|---|---|---|
| random baseline | −5 972 | 15.2 | 1.52 | 18 312 | 0.42 | floor |
| Cheapskate Chen | −5 594 | 0 | 3.46 | 26 969 | 0.55 | ✓ ✓ |
| Panic Pete | −5 153 | 0 | 3.76 | 17 420 | 0.36 | ✓ ✓ |
| blind | −4 458 | 0 | 3.73 | 26 749 | 0.55 | reference |
| Checklist Charlie | −3 317 | 47.9 | 0.17 | 1 328 | 0.03 | ✓ ✓ |
| Max Milliard | −2 958 | 61.4 | 0.13 | 500 | 0.01 | ✓ ✓ |
| reactive (ceiling) | −2 239 | 4.9 | 2.34 | 6 094 | 0.13 | ceiling |

Persona docs (strategy + expected weakness) are in each agent file:
`agents/char_{charlie,pete,chen,milliard}.py`, random floor at
`agents/random_baseline.py`. All are config-agnostic (introspect obs
cards/contracts/roster — no hardcoded routes/counts) and deterministic.

## Two honest findings from the ladder tuning

1. **Charlie initially BEAT reactive (+470 vs −2 239)** with fixed-rotation
   PM: at PM_COST $80 + costless full inspection (the amdrome-hpm hole),
   by-the-book over-service is near-optimal. Fixed persona-side by giving
   Charlie the book's price cap (never bid above 90% of face — ignores
   market conditions, same failure mode: deaf to signal). Charlie's rank
   will drop further once hpm prices inspection; his persona is unchanged.
2. **Reactive is under-tuned for the current economics** — its PM knobs
   were calibrated at PM_COST $250; at $80 the heavier-PM regime pays and
   reactive's κ-adaptive trigger (4.9 PMs/ep) sits below it (threshold
   sweep 3.0→1.5 moved net only −2239→−2058). The adaptive ceiling needs
   the x4i RL run (or a smarter trigger policy), not knob tweaks. The
   ladder is valid for today's engine; re-verify after hpm/x4i.

Pete/Chen tuned up from below-random: Pete panic-buys 6 units (was 16),
Chen bids 0.90× with sample inspection (was 0.85×/skip) — failure modes
unchanged, magnitudes bounded.
