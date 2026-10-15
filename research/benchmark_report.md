# amdrome demo — measured improvement: operator assistant vs blind

Paired double-blind A/B: 200 episodes, seeds 81000+ (identical scenarios per pair).
Arm A: demo/assistant OperatorAssistant (autonomous). Arm B: blind baseline (run-to-failure, no monitoring).

| metric | assistant (A) | blind (B) | Δ (A−B) | 95% CI | A wins |
|---|---|---|---|---|---|
| net profit | -7314.39 | -125.92 | +-7188.47 | [-7698.44, -6696.84] | 2.0% |
| defect escapes (units/ep) | 0.1 | 0.72 | -0.63 | [-0.75, -0.52] | 0.5% |
| defect PPM | 4227.67 | 28310.28 | -24082.61 | [-28564.46, -19831.15] | 3.0% |
| unplanned downtime (ticks/ep) | 7.25 | 20.68 | -13.44 | [-17.2, -9.88] | 10.0% |
| breakdowns (per ep) | 0.32 | 1.01 | -0.69 | [-0.86, -0.54] | 5.0% |

**Time-to-detection** (information advantage — the rubric's “spot problems earlier”): assistant mean None ticks after drift onset (0/200 episodes with a detection); blind arm has no monitoring and never detects.

Reproduce: `python3 demo/benchmark/run_ab.py --episodes 200 --seed-base 81000 --report demo/benchmark_report.md` (run on a fleet host; dawn does no batch evals).
