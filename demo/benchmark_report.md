# amdrome demo — measured improvement: operator assistant vs blind

Paired double-blind A/B: 2000 episodes, seeds 900000+ (identical scenarios per pair).
Arm A: demo/assistant OperatorAssistant (autonomous, cbm 0.4, full-inspection). 
Arm B: blind baseline (run-to-failure, no monitoring).

| metric | assistant (A) | blind (B) | Δ (A−B) | 95% CI | A wins |
|---|---|---|---|---|---|
| net profit | 999.76 | -4470.87 | +5470.63 | [5327.22, 5602.54] | 96.4% |
| defect escapes (units/ep) | 0.04 | 0.52 | -0.48 | [-0.51, -0.45] | 39.0% |
| defect PPM | 1787.89 | 25234.8 | -23446.91 | [-25094.14, -21828.56] | 40.3% |
| unplanned downtime (ticks/ep) | 9.72 | 82.22 | -72.51 | [-74.28, -70.72] | 95.5% |
| breakdowns (per ep) | 0.43 | 3.76 | -3.33 | [-3.4, -3.25] | 95.5% |

**Time-to-detection** (information advantage — the rubric's “spot problems earlier”): assistant mean 87.69 ticks after drift onset (1388/2000 episodes with a detection); blind arm has no monitoring and never detects.

Reproduce: `python3 demo/benchmark/run_ab.py --episodes 2000 --seed-base 900000 --cbm 0.4 --full-inspection --report demo/benchmark_report.md` (run on a fleet host; dawn does no batch evals).

Default assistant (legacy PM, no `--cbm`), seeds 81000+, 200 eps: unplanned downtime −18.1%, escapes −82.6%, net +$1,363/ep (`research/data/abverify/report_legacy_81000.md`). Total downtime incl. planned PM and the claim verdict: `research/2026-10-17-ab-verification.md`.
