# A/B claim verification — operator assistant vs blind (2026-10-17)

Bead: amdrome-bqm. Author: Agravain (ops_amdrome). Verification ran on Explorer
HPC (slurm `short`, Python 3.13.5). t3, dusk and albion had been offline on
tailscale for 20h+, and dawn runs no sweeps.

## Verdict

| headline claim (README / COMPREHENSIVE_PLAN / SPEC §4.2) | shipped assistant (default config) | assistant with condition-based PM (`cbm_threshold=0.40, full_inspection=True`) |
|---|---|---|
| ">70% downtime reduction" | **NOT SUPPORTED**: unplanned downtime −19.7% [18.4, 21.0] | **SUPPORTED for unplanned downtime**: −88.2% [87.3, 89.0]. Total station downtime incl. PM is **+24%** |
| ">90% defect-escape reduction" | **NOT SUPPORTED**: −81.8% [79.2, 84.2] | ~−92%: 91.8% [89.9, 93.5]. The CI lower bound touches 90%, and the whole effect comes from a costless inspection knob (see §3) |

Figures are from the held-out set: 2000 paired episodes, seeds 900000–901999.
These seeds were never used for tuning, and the test was pre-registered in a bead
comment before the run. Each figure is the relative reduction 1 − mean(A)/mean(B)
with a paired seed-bootstrap 95% CI.

The SPEC_DEMO_PRODUCT §4.2 "scorecard" had no measurement behind it: −74.3%
downtime, −94.7% escapes, `p<0.0001`, `d_z=3.12`. They were targets written as if
they were results, and every number in that table was invented. They have been
relabelled and replaced with the measured numbers below.

### Quotable statements (true on held-out data; quote the config with them)

- With condition-based PM from cycle-time trends, the assistant cut **unplanned
  breakdown downtime by 88%** (95% CI 87–89%) and **breakdowns by 89%** (3.76 → 0.43
  per episode) against a run-to-failure baseline. That is 2000 paired simulated
  weeks. The cost is about 12 planned 8-tick PM stops per week. Total station
  downtime goes **up 24%**, but the line ships **18% more clean units** (20.2 →
  23.9) and profit rises by **$5,471 per episode** (CI $5,327–5,603; the assistant
  wins 96% of episodes).
- **Customer defect escapes fall ~92%** (0.52 → 0.04 units per episode, CI 90–94%).
  This comes from holding 100% inspection, which the engine charges nothing for.
- The shipped default assistant (legacy CUSUM/RUL PM, capped at 2 PMs per
  episode) cuts unplanned downtime by **20%** and escapes by **82%**, and adds
  **+$1,495 per episode**.

Do not say: ">70% downtime reduction" without the word *unplanned* and the PM
trade-off; ">90% escapes" as a strict bound; or anything about "on-time delivery
94%" or "+$10,440/week". Those were never measured.

## 1. Measured numbers (held-out, n=2000, ref = blind)

| arm | unplanned DT/ep | rel. red. [95% CI] | Δ total DT incl. PM | breakdowns/ep | escapes/ep | escape red. [95% CI] | clean units | Δ net $/ep | PM/ep |
|---|---|---|---|---|---|---|---|---|---|
| blind (ref) | 82.2 | — | 82.2 | 3.76 | 0.52 | — | 20.2 | — | 0 |
| blind_full | 82.3 | −0.1% | +0.1% | 3.75 | 0.04 | 91.4% [89.5, 93.1] | 20.3 | +373 | 0 |
| **asst (shipped default)** | 66.0 | **19.7% [18.4, 21.0]** | −0.9% | 3.03 | 0.10 | **81.8% [79.2, 84.2]** | 21.0 | +1495 | 1.9 |
| asst_full | 66.2 | 19.5% | −0.8% | 3.04 | 0.04 | 92.0% [90.1, 93.6] | 21.1 | +1523 | 1.9 |
| asst_nocap (PM caps removed) | 54.0 | 34.4% | +28.2% | 2.41 | 0.10 | 80.8% | 21.2 | +2173 | 6.6 |
| **prod_cbm40 (proposed)** | 9.7 | **88.2% [87.3, 89.0]** | **+24.0%** | 0.43 | 0.04 | **91.8% [89.9, 93.5]** | 23.9 | **+5471** | 11.8 |
| prod_cbm45 | 14.0 | 83.0% [82.0, 84.1] | +13.6% | 0.62 | 0.04 | 91.9% | 23.7 | +5262 | 10.1 |
| prod_cbm50 | 19.3 | 76.5% [75.4, 77.7] | +5.9% | 0.86 | 0.04 | 92.2% | 23.4 | +4927 | 8.6 |
| asst_ops12 (PM every 12 ops) | 9.5 | 88.5% | +47.1% | 0.42 | 0.04 | 92.8% | 24.2 | +5318 | 14.2 |
| asst_ops16 | 24.4 | 70.3% | +32.8% | 1.09 | 0.04 | 92.2% | 23.2 | +4395 | 10.8 |
| *oracle_w35 (CEILING, reads true wear)* | 5.5 | 93.3% | +7.9% | 0.24 | 0.04 | 92.7% | 24.4 | +5928 | 10.6 |
| *oracle_w45 (CEILING)* | 11.8 | 85.7% | **−16.8%** | 0.53 | 0.04 | 92.5% | 24.1 | +5679 | 7.3 |

How to read the columns:

- "Unplanned downtime" is the engine's `unplanned_downtime`: station-ticks spent
  under breakdown repair. It is not line-stop time.
- Planned PM and relocation ticks are not in the engine result. The harness reads
  `Engine.planned_downtime` to fill the "total DT" column.
- About 0.12 of the blind arm's 3.76 breakdowns per episode come from the
  wear-independent H0 hazard floor. This was measured with a behaviour-preserving
  tap on `degradation.maybe_breakdown`. It puts the breakdown-reduction ceiling at
  roughly 97%.
- The tuning set (seeds 500000–501999, `research/data/abverify/main.md` and
  `cbm.md`) agrees with the held-out set to within about 0.5 pp on every arm.

## 2. Where the downtime gap came from

1. **Hard PM budget in the recommender.** `Recommender` allowed at most one PM per
   station and two per episode (`pm_completed_count >= 1`, `sum >= 2`). The
   assistant averaged 1.9 PMs per episode while blind had 3.8 breakdowns. That cap
   alone limits it to about −20%. Removing the caps (`asst_nocap`) only reaches
   −34%, because the trigger itself is weak.
2. **Slow, mis-calibrated detection.**
   - `rul_estimator.py` still uses pre-calibration physics: `BETA_WEAR=0.15`
     (the engine uses 0.30), `H0=0.0005` (engine 0.0001), and one fixed
     `EST_WEAR_PER_OP=0.012`. Real per-station wear per op is 0.007–0.061: the
     hyperprior 0.014–0.034 times a station multiplier of 0.5–1.8.
   - SPC-probe CUSUM confirms drift a mean of about 80–88 ticks after onset, in a
     336-tick episode. By then the hazard cliff (0.3·w⁶) has often already fired.
3. **Fix: condition-based PM from free cycle-time telemetry.**
   - The obs stream shows each station's `state` every tick plus its `ops_seen`
     counter. Counting `proc` ticks between counter increments therefore gives the
     realised cycle time of every operation, with no probe budget spent.
   - `demo/assistant/cycle_monitor.py` fits log(cycle) = a + log(1 + 0.35·(w0 +
     r_s·n)) with these parts:
     - one intercept shared by all stations (proc_scale);
     - a per-station wear rate r_s, with Normal priors;
     - a staffing correction;
     - w0 reset to 0.08·w after a PM and to 0.15 after a repair.
   - It requests PM when the estimated wear reaches W.
   - A first version estimated the intercept from first ops only. That biased every
     slope low (relative error 43%). Fitting intercept and slopes jointly fixed it,
     and lifted unplanned-downtime reduction from 80% to 88% at W=0.40.
   - It never reads ground truth. The `prod_cbm*` arms run the product code path,
     and their state hashes match the harness-wrapper arm `asst_cbm*` exactly.
4. **The trade-off and the remaining headroom.**
   - Every observation-only policy that gets past 70% unplanned reduction
     increases total station downtime. PM stops are 8 ticks each, and an early PM
     wastes wear life.
   - The ground-truth oracle at W=0.45 cuts both (−86% unplanned, −17% total). So
     better wear estimation is still worth something: the CycleMonitor's
     end-of-episode rate error is still about 40% after PMs keep n small.
   - W=0.50 is the most balanced option on the verified frontier: −76.5% unplanned,
     +5.9% total, +$4,927 per episode.
   - W=0.40 has net profit within noise of the best (0.30–0.40 is flat), so it was
     chosen on the tuning set. A plain ops-count schedule (`asst_ops12`) gives the
     same unplanned reduction but much more PM: +47% total downtime.

## 3. Where the escape number comes from

- Escapes depend almost entirely on `inspect_mode`. Catch probability is 0.97 for
  `full` and 0.65 for `sample`, and **`full` costs nothing**: same inspect time,
  no fee. The only cost is rework capacity.
- Blind plus full inspection, with no other intelligence (`blind_full`), already
  gets −91.4%.
- The shipped assistant only escalates to full inspection at t≥144 or when
  estimated wear is ≥0.55, which is why it gets −82%.
- Absolute numbers are tiny: 0.52 escapes per episode at baseline. Most episodes
  tie at 0, so the escape "win %" (~40%) is not a useful statistic.
- Filed **amdrome-hpm** (engine design): inspection mode should carry a cost or a
  time penalty so that it becomes a real decision. The same bead records that the
  per-tick state stream leaks cycle times, which makes the SPC probe budget nearly
  redundant.

## 4. Reproducibility and integrity checks

- **Replay determinism:** 30 seeds × 16 arms were each run twice and compared on
  the full result dict plus `state_hash`. 0 of 480 mismatched
  (`research/data/abverify/replay.json`).
- **Two independent implementations agree:**
  - `demo/benchmark/run_ab.py` and `verify_ab.py` produce identical numbers on
    seeds 81000+ for the legacy config (−18.1% unplanned, −82.6% escapes,
    +1363 per episode).
  - They also match on seeds 900000+ for cbm40 (9.72 vs 82.22 unplanned ticks,
    +5470.63 per episode).
- **Drift vs the committed report:**
  - The committed `demo/benchmark_report.md` (made at 1ef805e, seeds 81000) showed
    −18.6% unplanned and −80% escapes. The primer's −21% / −74% matches neither the
    report nor HEAD.
  - At HEAD (after the procurement, labour and layout commits) the same seeds give
    −18.1% and −82.6%. These are small shifts and none of them changes the verdict.
- **Tuning/held-out discipline:** W was chosen only on seeds 500000+. The held-out
  set was used once.

## 5. Changes made (committed per feature)

| change | where |
|---|---|
| Independent harness: arms, ground-truth oracle ceilings, H0 breakdown tap, planned/total downtime, replay check | `demo/benchmark/verify_ab.py`, `verify_analyze.py`, `verify_ab.slurm` |
| `Recommender(max_pm_per_station, max_pm_total)`; defaults unchanged | `demo/assistant/recommender.py` |
| CycleMonitor (condition-based PM) plus tests | `demo/assistant/cycle_monitor.py`, `demo/tests/test_cycle_monitor.py` |
| `OperatorAssistant(cbm_threshold=None, full_inspection=False)`, **opt-in** (default behaviour unchanged pending a call from the demo owner) | `demo/assistant/assistant.py` |
| `run_ab.py --cbm W --full-inspection`; the report records the config | `demo/benchmark/run_ab.py` |
| Claims corrected | `README.md`, `docs/COMPREHENSIVE_PLAN.md`, `docs/SPEC_DEMO_PRODUCT.md` §2.3/§4/§5, `demo/benchmark_report.md` |
| Data | `research/data/abverify/` (gz jsonl, summaries, reports) |

Beads filed:

- **amdrome-svf** (bug): staffing inverted. `remaining = proc_time /
  staffing_multiplier` with `UNDERSTAFF_PROC_PENALTY=1.3`, so an understaffed
  station runs 23% *faster*.
- **amdrome-hpm** (design): free full inspection, and the cycle-time leak.

**Decision for the demo owner / coordinator:** flip the `OperatorAssistant`
defaults to `cbm_threshold=0.40, full_inspection=True` (or 0.50 if the pitch
should not show total downtime rising). Until that happens, the bare
`OperatorAssistant()` is the −20% / −82% product.

## 6. Commands

```bash
# stage (repo layout preserved) — any slurm host; dawn never runs sweeps
tar czf - --exclude=__pycache__ simulator agents demo bin envs \
  | ssh -o BatchMode=yes exp 'mkdir -p ~/amdrome/abv && cd ~/amdrome && tar xzf -'

# held-out sweep (10 shards); ARMS must be exported, not passed via --export=
ssh exp 'cd ~/amdrome && export ARMS=blind,blind_full,asst,asst_full,asst_nocap,prod_cbm40,prod_cbm45,prod_cbm50,asst_ops12,asst_ops16,oracle_w35,oracle_w45 SEEDBASE=900000 EPS=2000 TAG=heldout && sbatch --export=ALL demo/benchmark/verify_ab.slurm'

# analysis (on a compute node: srun -p short ...)
python3 demo/benchmark/verify_analyze.py abv/heldout_*.jsonl --ref blind --md abv/heldout.md --json abv/heldout_summary.json
python3 demo/benchmark/verify_analyze.py research/data/abverify/heldout.jsonl.gz --ref blind   # from committed data

# replay determinism
python3 demo/benchmark/verify_ab.py --replay-check 30 --seed-base 500000 --arms blind,asst,prod_cbm40

# headline report via the product benchmark (independent code path)
python3 demo/benchmark/run_ab.py --episodes 2000 --seed-base 900000 --cbm 0.40 --full-inspection --report demo/benchmark_report.md
python3 demo/benchmark/run_ab.py --episodes 200  --seed-base 81000  --report research/data/abverify/report_legacy_81000.md
```
