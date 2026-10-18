# Video plan (3 minutes)

- **0:00–0:30 — the floor.** Screen-capture of the episode visualizer
  (http://dawn.saiga-beaufort.ts.net:9122): play an episode at 16×,
  scrub to a breakdown, point out the andon badge, wear gauges filling,
  buffer bars, KPI ticker.
- **0:30–1:20 — the operator assistant.** Terminal console (demo/console):
  alerts stream in as drift develops; assistant ranks them, recommends a
  PM before the hazard cliff; the breakdown never happens. Contrast with
  the blind run.
- **1:20–2:10 — the measured table.** Static slides (docs/assets/slides.md
  beats 4–7): anti-tape numbers, the held-out A/B result with CIs, the
  character ladder.
- **2:10–3:00 — runs on AMD + stack.** The ROCm training log tail
  scrolling, one breath on the architecture (pure-python engine, Gym
  wrapper, SB3 PPO), close on the repo URL.

Recording: OBS or `wf-recorder` over the viz + console; the visualizer is
already running on dawn port 9122.
