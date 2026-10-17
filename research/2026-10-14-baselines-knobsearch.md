# Scripted baselines + knob-search: results & structural findings — 2026-10-13/14

Bead: amdrome-6k2. Hosts: all sweeps/evals on **t3** (dawn: code only).
Artifacts: `agents/{blind,lean,reactive}.py`, `rl/tune_knobs.py`
(random-search harness, coarse/refine stages), data in
`research/data/knobs_coarse*.jsonl`, `final_6k2*.json`, `gate2_engine_v2.jsonl`.

## Final baseline numbers (200 paired episodes, seeds 70000+)

| agent | net_profit | defect PPM | breakdowns | PMs/ep | downtime ticks | rejected |
|---|---|---|---|---|---|---|
| blind | −375 | 22 811 | 1.27 | 0 | 25.5 | 3.52 |
| lean | −1149 | 25 945 | 0.81 | 6.0 | 16.6 | 3.88 |
| reactive (tuned v1) | **−133** | **8 179** | 1.24 | 0.05 | 25.5 | 2.76 |

Paired vs blind: reactive **+242 ± 1073** (p=0.0014, episode-level win
29.5% — bimodal); lean −773 (over-PMs: 6 blind PMs × $250 + offline time
costs more than the 0.5 breakdowns they prevent). Match-level (mean of 5
episodes): reactive d_z=0.63, win 75%, p=7e-5.

## d_z > 2.0 status: NOT REACHED — structural, documented for u2b

Best of 3 knob-search iterations (120 configs × 40 paired eps): episode
d_z ceiling ≈ 0.35 for net_profit. Causes, in order of impact:

1. **Irreducible breakdown noise** (partially fixed): H0 baseline hazard
   produced ~0.9 unpreventable breakdowns/ep ($1900 noise floor). Lowered
   H0 0.0005→0.0001 and raised the wear cliff BETA 0.15→0.30 so
   breakdowns are now wear-driven and preventable in principle.
2. **PM was un-executable under load** (fixed): PM required an idle
   station; near-saturation stations never idle → detection worked, PM
   never fired (0.55 PMs/ep vs 4 detections). Engine now honors a PM
   REQUEST by reserving the station at its next op completion
   (planned-maintenance window) — the monitoring skill is now exercisable.
3. **Bimodal scenario interaction** (open): hot-wear seeds reward early PM
   (+$2400), cool-wear seeds punish any PM (−$250+offline). A static knob
   set can't win both tails — needs scenario-adaptive policy (κ inference
   from CUSUM slope, or RL). This is the concrete u2b/x4i target.
4. Ops-count PM rule (PM at N ops + low CUSUM) explored and rejected for
   v1 defaults: over-PMs catastrophically when κ is low (−$16k/ep at
   pm_ops=16).

Agent bugs found & fixed: PM latch never cleared (once alarmed, the agent
re-requested PM forever — 37 PMs/ep); now clears when the card shows
pm/broken.

## Score-skill mapping (for demo benchmarks)

- Quality: reactive cuts defect PPM 2.8× vs blind (22 811 → 8 179) —
  significant and large; the demo A/B (g9c) should lead with
  time-to-detection + PPM + downtime, not net alone.
- Downtime: lean cuts downtime ticks 35% but at negative net — the
  "wasteful maintenance" story for the demo.
- Net: modest, significant edge for reactive (p=0.0014); match-level
  scoring (mean of ≥5 episodes) recommended for challenge verdicts.

## Re-validation after engine changes (hazard + PM reservation)

- Anti-tape gate 2 (gn6) re-run on t3 with reactive as taped policy:
  tape win% full 4.5 / bids 3.0 / ops 3.5 — **PASS, stronger than before**.
- Determinism/golden/invariant suite: 11/11 green (golden re-pinned v3
  after the PM-reservation mechanic).
