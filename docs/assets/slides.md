# AMDrome — slides (paste into the submission tool / present directly)

1. **The problem.** Industrial AI agents need a benchmark where running a
   factory badly is easy and running it well is measurable — not a demo
   dataset, a live economy.
2. **What AMDrome is.** A seed-reproducible discrete-event factory
   simulator: 6-station line, wear-driven breakdowns with a hazard cliff,
   defects + inspection, labour roster, spot inputs and sealed-bid
   contracts. Pure Python, zero dependencies; Gym + kaggle-style runners.
3. **Partial observability.** Agents see only the kanban card stream —
   station cards, budgeted SPC samples, pull signals, alarms. Machine
   wear is never shown; you must infer it. (Show viz: floor, andon, wear
   gauges, KPI ticker.)
4. **Anti-tape by design.** Every episode draws scenario parameters from
   a hyperprior. Measured: memorised action tapes lose to a mediocre
   reactive agent 97% of the time. Policy skill, not memorisation, wins.
5. **Four live decision surfaces.** Monitoring/PM, market bidding,
   procurement, labour assignment (+ layout moves). Grid size is a
   measured lever: policy share of cycle-time variance 47%→77% from 8×6
   to 16×12 floors.
6. **The product: operator assistant.** CUSUM drift detection +
   condition-based PM from cycle-time trends. Held-out paired A/B, 2000
   episodes: unplanned downtime −73.6% [72.4, 74.8], total downtime
   ~flat, escapes −91% (marked: rides on free 100% inspection —
   disclosed open issue), +$6.6k/episode.
7. **Honest engineering.** Claims were independently re-verified; two
   inverted-sign bugs found and fixed with regression tests (understaffed
   stations ran faster; low skill cut defects). Character-agent opponent
   ladder is economy-bracketed: disciplined personas break even,
   negligent ones lose.
8. **Runs on AMD.** RL policy training (SB3 MaskablePPO) executes on AMD
   Radeon 9700 XT via ROCm — see docs/assets/amd-rocm-run.log. The
   benchmark is vendor-neutral: any stack can train against it.
