# amdrome demo — measured improvement: operator assistant vs blind

Paired double-blind A/B: 200 episodes, seeds 81000+ (identical scenarios per pair).
Arm A: demo/assistant OperatorAssistant (autonomous, legacy PM). 
Arm B: blind baseline (run-to-failure, no monitoring).

| metric | assistant (A) | blind (B) | Δ (A−B) | 95% CI | A wins |
|---|---|---|---|---|---|
| net profit | -2734.67 | -4097.17 | +1362.51 | [1091.1, 1632.0] | 75.0% |
| defect escapes (units/ep) | 0.1 | 0.57 | -0.47 | [-0.58, -0.37] | 36.5% |
| defect PPM | 4612.63 | 28241.87 | -23629.24 | [-29016.35, -18450.35] | 40.0% |
| unplanned downtime (ticks/ep) | 63.48 | 77.52 | -14.03 | [-18.05, -10.15] | 66.0% |
| breakdowns (per ep) | 2.88 | 3.52 | -0.63 | [-0.79, -0.48] | 56.5% |

**Time-to-detection** (information advantage — the rubric's “spot problems earlier”): assistant mean 80.39 ticks after drift onset (186/200 episodes with a detection); blind arm has no monitoring and never detects.

Reproduce: `python3 demo/benchmark/run_ab.py --episodes 200 --seed-base 81000 --report demo/benchmark_report.md` (run on a fleet host; dawn does no batch evals).
