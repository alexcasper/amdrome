# Simulation calibration: making prevention pay & monitoring matter — 2026-10-14

Bead: amdrome-x4i (simulation refinement). All sweeps on **t3** (ARM fleet).
Scripts: `rl/tune_knobs.py` (refine stage), scratch calibrate/sweep probes;
data: `research/data/knobs_refine*.jsonl`, `final_calib*.json`,
`gate2_v3.jsonl`, `ab_v3.jsonl`.

## Diagnosis chain

1. **Static knob ceiling proven**: refine stage around tuned-v1 gave +25
   edge at p=0.74 (200 paired eps) — noise. Static knobs are done.
2. **Prevention didn't pay**: at PM_COST 250, every PM policy lost money
   (2.17 PMs preventing 0.2 breakdowns: $540 spend vs $300 saved). The
   charter's core skill had negative economic value.
3. **Global wear-rate made monitoring pointless**: with one κ per episode,
   a blind fixed PM schedule (lean, 6 PMs) matched adaptive policies —
   sensing carried no information value.

## Calibration (baked into the engine, golden re-pinned v5)

| change | value | why |
|---|---|---|
| PM_COST | 250 → **80** | prevention must be cheaper than failure |
| wear_rate hyperprior | [0.006,0.024] → **[0.014,0.034]** | hot regime makes PM pivotal |
| CONTRACT_PRICE | (300,480) → **(360,540)** | competent play should be profitable in absolute terms |
| **per-station wear multipliers** | **U(0.5,1.8) per station** (new) | station-asymmetric ageing = the reason the kanban layer exists: scheduled PM services healthy machines while worn ones break |
| reactive: κ-adaptive PM | cum-CUSUM proxy > 3.0, floor 48 | wear-proxy from cumulative SPC drift, resets on PM |

## Results after calibration (200 paired episodes, seeds 94000+)

| agent | net | PPM | breakdowns | downtime ticks |
|---|---|---|---|---|
| blind | −5162 | 35 431 | 4.02 | 88.4 |
| lean (scheduled PM) | −3367 | 24 938 | 2.85 | 61.5 |
| reactive (κ-adaptive) | −2849 | 12 206 | 2.62 | 56.9 |

- **reactive vs blind: edge +2312, d_z 0.82 episode-level (p=2e-31, 79% win);
  match-level (mean of 5) d_z = 2.24, 100% win, p=1e-45 — the d_z>2.0
  target from the roadmap is met at match level.**
- Ordering restored: monitoring (reactive) > blind scheduling (lean) > blind —
  the kanban information layer now has measurable economic value.
- Anti-tape gate 2 re-validated: tape win% 10/3/10 (full/bids/ops) — PASS.
- **A/B demo benchmark (200 eps, regenerated)**: assistant beats blind on
  every rubric metric — net **+$1702/ep** (CI [1370, 2016], 73.5% win),
  PPM −28 382, downtime −15.9 ticks, breakdowns −0.77/ep,
  time-to-detection 78.9 ticks (detections in 192/200 episodes; blind never
  detects). `demo/benchmark_report.md` regenerated.

## Agent bugs found on the way

- κ-adaptive accumulator never reset after PM → permanent PM loop (93
  PMs/ep on hot seeds); now resets when the station card shows "pm".
- knob-search refine crashed on float bounds for integer knobs (probe_top_k);
  0-valued knob defaults silently meaning "always on" — guarded.

## Remaining for x4i

- SB3 entrypoint scaffolded (`rl/train_sb3.py`); training deferred to the
  env_cteach GPU profile per alex (no torch/CUDA on the ARM fleet).
- Episode-level d_z (0.82) below 2.0 — match-level scoring (≥5 episodes)
  is the recommended verdict unit for the challenge (documented in DESIGN).

## Procurement surface (added 2026-10-14, post-calibration)

Charter's "input procurement with volatile prices" is now a decision
surface: `buy_input: n` action, stock cap 32, holding $0.05/unit/tick,
arrivals consume stock before paying spot; `input_stock` visible in obs.
Measured (100 paired eps): the naive buy-low policy's edge is −$16 ± 167
(noise; ~2.5 units bought/ep) — spot volatility [80,120] gives only
~$300/ep theoretical timing value vs episode noise σ≈2900. Surface kept:
decision density (anti-tape gate re-validated PASS 13/6/12% tape win),
RL/expert play may extract the thin edge. Widening spot volatility would
require full re-calibration — deferred.

