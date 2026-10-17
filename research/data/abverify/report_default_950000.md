# amdrome demo — measured improvement: operator assistant vs blind

Paired double-blind A/B: 200 episodes, seeds 950000+ (identical scenarios per pair).
Arm A: demo/assistant OperatorAssistant (autonomous, cbm 0.5). 
Arm B: blind baseline (run-to-failure, no monitoring).

| metric | assistant (A) | blind (B) | Δ (A−B) | 95% CI | A wins |
|---|---|---|---|---|---|
| net profit | 3487.43 | -2048.47 | +5535.9 | [5026.24, 6052.6] | 94.5% |
| defect escapes (units/ep) | 0.03 | 0.54 | -0.51 | [-0.61, -0.4] | 38.0% |
| defect PPM | 1134.47 | 25170.89 | -24036.42 | [-29163.91, -19235.5] | 40.5% |
| unplanned downtime (ticks/ep) | 19.24 | 78.97 | -59.73 | [-65.38, -54.02] | 93.0% |
| breakdowns (per ep) | 0.88 | 3.62 | -2.75 | [-3.0, -2.5] | 90.5% |

**Time-to-detection** (information advantage — the rubric's “spot problems earlier”): assistant mean 82.61 ticks after drift onset (157/200 episodes with a detection); blind arm has no monitoring and never detects.

Reproduce: `python3 demo/benchmark/run_ab.py --episodes 200 --seed-base 950000 --cbm 0.5 --report <out.md>` (run on a fleet host; dawn does no batch evals).
