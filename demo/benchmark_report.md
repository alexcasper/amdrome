# amdrome demo — measured improvement: operator assistant vs blind

Paired double-blind A/B: 200 episodes, seeds 81000+ (identical scenarios per pair).
Arm A: demo/assistant OperatorAssistant (autonomous). Arm B: blind baseline (run-to-failure, no monitoring).

| metric | assistant (A) | blind (B) | Δ (A−B) | 95% CI | A wins |
|---|---|---|---|---|---|
| net profit | 265.29 | -125.92 | +391.21 | [158.34, 626.2] | 52.0% |
| defect escapes (units/ep) | 0.14 | 0.72 | -0.59 | [-0.7, -0.48] | 45.0% |
| defect PPM | 5390.02 | 28310.28 | -22920.26 | [-27070.55, -19001.82] | 47.0% |
| unplanned downtime (ticks/ep) | 14.96 | 20.68 | -5.71 | [-8.73, -2.83] | 32.0% |
| breakdowns (per ep) | 0.73 | 1.01 | -0.28 | [-0.41, -0.15] | 29.5% |

**Time-to-detection** (information advantage — the rubric's “spot problems earlier”): assistant mean 45.01 ticks after drift onset (100/200 episodes with a detection); blind arm has no monitoring and never detects.

Reproduce: `python3 demo/benchmark/run_ab.py --episodes 200 --seed-base 81000 --report demo/benchmark_report.md` (run on a fleet host; dawn does no batch evals).
