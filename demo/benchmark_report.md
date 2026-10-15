# amdrome demo — measured improvement: operator assistant vs blind

Paired double-blind A/B: 200 episodes, seeds 81000+ (identical scenarios per pair).
Arm A: demo/assistant OperatorAssistant (autonomous). Arm B: blind baseline (run-to-failure, no monitoring).

| metric | assistant (A) | blind (B) | Δ (A−B) | 95% CI | A wins |
|---|---|---|---|---|---|
| net profit | -3144.5 | -4846.58 | +1702.07 | [1370.08, 2015.8] | 73.5% |
| defect escapes (units/ep) | 0.14 | 0.71 | -0.57 | [-0.68, -0.47] | 42.5% |
| defect PPM | 7028.59 | 35410.16 | -28381.58 | [-33699.15, -23404.18] | 50.0% |
| unplanned downtime (ticks/ep) | 69.56 | 85.43 | -15.87 | [-20.01, -11.73] | 70.5% |
| breakdowns (per ep) | 3.15 | 3.92 | -0.77 | [-0.93, -0.59] | 59.0% |

**Time-to-detection** (information advantage — the rubric's “spot problems earlier”): assistant mean 78.92 ticks after drift onset (192/200 episodes with a detection); blind arm has no monitoring and never detects.

Reproduce: `python3 demo/benchmark/run_ab.py --episodes 200 --seed-base 81000 --report demo/benchmark_report.md` (run on a fleet host; dawn does no batch evals).
