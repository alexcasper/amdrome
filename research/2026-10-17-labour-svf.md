# amdrome-svf — labour coupling had both signs inverted (2026-10-17)

Author: Agravain (ops_amdrome). All runs on Explorer HPC (slurm `short`), with
1000 paired seeds (960000+) per tree. Script: `research/labour_staffing_ab.py`.
Data: `research/data/svf/`.

## The bugs (both fixed, each with a regression test that fails before the fix)

1. **Staffing scaled processing time the wrong way** (`core.py` step 9,
   commit 8ed7aff). The code was `remaining = proc_time / staffing_multiplier`.
   With `UNDERSTAFF_PROC_PENALTY=1.3`, an unstaffed station ran 23% *faster*.
   With `DOUBLE_STAFF_BONUS=0.9`, a double-staffed station ran 11% *slower*.
   The labour docstring says "an unstaffed station runs 30% slower", so the fix
   multiplies instead.
   - Test: `TestLabourCoupling` measures the ratio of the time actually
     allocated at admission to the cycle time before staffing is applied.
   - Before the fix: unstaffed 0.76, double-staffed 1.14 (both tests fail).
   - After: unstaffed ≈1.3, double-staffed <0.97.
2. **Higher worker skill raised defects** (`quality.defect_prob`, commit
   d9a7ed8). The code was `base * (1 - 0.5*(1-skill))`. That gave the unstaffed
   floor skill (0.7) **0.85×** the defects, and made mismatched specialists
   (×0.8 skill) *better*. The fix is `base * (1 + 0.5*(1-skill))`: skill 1.0
   keeps the base rate and skill 0.7 gets 1.15×.
   - Test: `TestSkillDefectCoupling` checks that defect probability decreases
     monotonically as skill rises.

Golden hash re-pinned twice, deliberately (v8, then v9). The CycleMonitor
staffing normalisation was flipped to match (`dur / mult`).

## Before / after (paired, n=1000, seeds 960000+)

| tree | reactive − blind (skill dominance) | reactive − reactive_no_assign (labour decision's own edge) | unstaff_exploit − blind | assistant − blind |
|---|---|---|---|---|
| pre (c5d4f4c) | +$2,181, d_z 0.77, win 77% | +$24, z 0.3 (nil) | −$1,258 (d_z −0.37) | +$5,778, d_z 1.60 |
| staffing fix only (8ed7aff) | +$2,786, d_z 0.86, win 81% | +$271, z 3.2 | **+$1,774** (d_z 0.56) | +$6,409, d_z 1.67 |
| both fixes (d9a7ed8) | **+$2,858, d_z 0.87, win 81%** | +$175, z 2.1 | **+$1,850** (d_z 0.59) | **+$6,526, d_z 1.69** |

Anti-tape gate (`bin/run_anti_tape.py --strong agents/reactive.py --mediocre
agents/shrewd.py`, n=200): PASS both before and after. Tape win rates were
9.5/3.0/9.5% (full/bids/ops) before and 9.0/2.0/8.0% after.

What this shows:

- **Skill dominance gets stronger.** Reactive's lead over blind grows from
  d_z 0.77 to 0.87, and the agent ordering is unchanged. Most of the gain comes
  from the staffing fix: blind's default even spread double-staffs 4 of 6
  stations, and those stations were previously penalised.
- **The labour decision itself is still worth almost nothing** (+$175, z 2.1),
  because of a design gap rather than a sign bug. `assign` takes **counts
  only**: workers are dealt to stations in roster order, so an agent cannot put
  a specialist on its affinity station. Filed as **amdrome-qwv** (proposal:
  accept `{station: [worker_id, ...]}`). The "+~310/ep vs no-assignment" in the
  labour commit message was not reproduced on the pre-fix tree (+$24).
- **The fix exposes a new exploit.** Piling every worker onto `pack` runs five
  stations 1.3× slower. Fewer operations means less wear, fewer breakdowns
  (3.11 vs 4.21) and less downtime, and that saving outweighs about 3 fewer
  clean units. So the exploit beats blind by $1.85k. Under run-to-failure the
  marginal unit loses money. Reactive still beats the exploit by about $1k.
  Filed as **amdrome-48q** (P3, an economics/design call for the coordinator).

## Operator assistant headline on the post-fix engine (held-out seeds 900000+, n=2000)

The held-out set has now been evaluated three times. No knob was tuned on it.

| arm | unplanned DT red. [95% CI] | Δ total DT incl. PM | escapes red. [95% CI] | Δ net $/ep |
|---|---|---|---|---|
| legacy assistant (`--legacy`) | 17.6% [16.2, 18.8] | −1.0% | 81.0% [78.9, 83.0] | +1,897 |
| **product default (cbm 0.50, full inspection)** | **73.6% [72.4, 74.8]** | **+1.6%** | 91.4% [89.9, 92.8] (hpm-dependent) | +6,612 |

Blind now averages 94 ticks of unplanned downtime and 4.26 breakdowns per
episode, up from 82 and 3.76, because its default staffing now speeds lines up
instead of slowing them. The >70% unplanned-downtime claim still holds, with the
CI lower bound at 72.4%. Total downtime is now roughly flat.
