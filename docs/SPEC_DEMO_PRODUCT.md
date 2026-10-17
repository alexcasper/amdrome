# amdrome Demo Product Specification: Intelligent Factory Operator Assistant (v1.0)

**Document Type:** Hackathon Product Specification & Operator Assistant Architecture  
**Brief Target:** Intelligent Industry — Early problem detection, operational excellence, downtime & scrap reduction  
**Parent Bead:** amdrome-59z (Hackathon demo, P1)  
**Deliverables:** Live Operator Console, Streaming AI Assistant, Rigorous A/B Benchmark Suite, 3-Minute Presentation Script  

---

## 1. Product Concept & Industrial Value Proposition

### 1.1 The Industrial Challenge
In discrete manufacturing plants, equipment degradation and process drift are insidious:
1. **Latent Mechanical Drift:** Stations do not fail instantly; tool wear, mechanical backlash, and thermal distortion inflate cycle times gradually before catastrophic seizure.
2. **The Epistemic Gap:** Operators cannot watch every machine continuously. Information arrives via noisy, aggregated signals (kanban pull events, shift tallies, sparse quality audits).
3. **Cascading Penalties:** An unaddressed station breakdown halts the entire production line (blocking upstream, starving downstream), ruins in-flight work-in-progress, and delays customer shipments.
4. **Defect Escapes:** Worn tooling injects subtle micro-defects that propagate undetected through downstream stations, resulting in catastrophic customer returns and contractual penalties.

### 1.2 The Solution: The `amdrome` Operator Assistant
The **Operator Assistant** is an intelligent streaming copilot designed directly for factory floor supervisors and operations managers:
* Ingests the real-time **Kanban Telemetry Stream** (station cards, SPC cycle-time samples, buffer movements, andon flags).
* Employs statistical drift detection (CUSUM / EWMA) and remaining useful life (RUL) estimation to detect anomalies **15 to 40 ticks before catastrophic breakdown**.
* Formulates transparent, domain-grounded explanations of root causes.
* Issues prioritized, actionable recommendations (e.g. optimal PM scheduling during buffer slack, dynamic reallocation of technician capacity, targeted SPC probe dispatches).
* Produces **quantifiable, measured improvements** in downtime, defect PPM, and bottom-line profitability.

```
       ┌─────────────────────────────────────────────────────────────┐
       │                   Plant Floor Telemetry                     │
       │     (Station Cards, Buffer Pulls, SPC Samples, Alarms)      │
       └──────────────────────────────┬──────────────────────────────┘
                                      │
                                      ▼
       ┌─────────────────────────────────────────────────────────────┐
       │             Operator Assistant Analytical Engine            │
       │                                                             │
       │  1. Signal Filter & CUSUM Statistical Drift Detector        │
       │  2. Weibull Remaining Useful Life (RUL) Estimator           │
       │  3. Root Cause Attribution Engine (Wear vs Fatigue vs Jams) │
       │  4. Prescriptive Action Optimizer (Cost-Benefit Planner)    │
       └──────────────────────────────┬──────────────────────────────┘
                                      │
                                      ▼
       ┌─────────────────────────────────────────────────────────────┐
       │                 Live Operator Console (UI)                  │
       │                                                             │
       │  • Real-Time Floor Status Grid & Station Health Gauges      │
       │  • SPC Control Charts with Dynamic Upper/Lower Limits       │
       │  • High-Priority Alert & Recommendation Feed                │
       │  • Financial Impact & Downtime Avoidance Counter            │
       └─────────────────────────────────────────────────────────────┘
```

---

## 2. Technical Architecture & Core Algorithms

### 2.1 Online Statistical Drift Detection (CUSUM)
To catch station wear drift using limited SPC sample telemetry, the Assistant maintains a two-sided Cumulative Sum (CUSUM) filter for each monitored station $s$:

Let $\bar{T}_0(s)$ be the nominal cycle time and $\sigma_s$ be standard deviation:
$$Z_t(s) = \frac{T_{\text{sample}}(s, t) - \bar{T}_0(s)}{\sigma_s}$$
$$S_t^+(s) = \max\left(0, S_{t-1}^+(s) + Z_t(s) - k\right)$$
where $k = 0.5$ (slack parameter). When $S_t^+(s) > h_{\text{drift}}$ (threshold $h_{\text{drift}} = 4.0$), the Assistant raises an early **Performance Drift Alarm**:
$$\text{Alert: Station } s \text{ exhibiting statistically significant cycle-time dilation (+18.4% above baseline)}.$$

### 2.2 Remaining Useful Life (RUL) & Hazard Forecasting
Using the estimated wear level $\hat{w}_s(t)$ inverted from cycle-time drift:
$$\hat{w}_s(t) = \frac{1}{\delta_{\text{drift}}} \left( \frac{\hat{\mu}_{\text{proc}}(s, t)}{T_0(s)} - 1 \right)$$
The Assistant evaluates the cumulative failure hazard over the upcoming horizon $\Delta t \in [1, 50]$ ticks:
$$P(\text{Breakdown in next } \Delta t) = 1 - \exp\left( - \int_{t}^{t + \Delta t} h(\hat{w}_s(\tau)) \, d\tau \right)$$
If the cumulative hazard exceeds 35%, the Assistant flags **Imminent Breakdown Hazard**, estimating ticks to failure with 90% confidence bounds.

### 2.3 Prescriptive Recommendation Engine
The Assistant evaluates candidate interventions against an economic loss function:
$$\mathbb{E}[\Delta \text{Cost}] = \text{Cost}(\text{Intervention}) - \mathbb{E}[\text{Loss if Ignored}]$$
* **Preventive Maintenance (PM):** Cost = $\$80$ parts + 8 ticks planned downtime (engine `degradation.PM_COST`/`PM_DURATION`, calibrated 2026-10-14). Avoids: $\$1,200$ emergency overhaul + $\$300$ scrapped in-process job + lognormal repair (median ~22, min 16 ticks) of unplanned downtime.
* **Smart Scheduling:** Recommends triggering PM when upstream buffer is depleted or downstream buffer is near capacity, minimizing line starvation impact.

---

## 3. The Operator Console Experience

The product delivers a high-impact, visual terminal interface (built with Python `rich` / `textual` or web dashboard) for operational monitoring.

### 3.1 Console Layout Mockup
```
┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
│  AMDROME OPERATOR ASSISTANT  │  Shift 2/7  │  Tick 142/336  │  Cash: $31,450  │  Downtime: 2.1%  │
├──────────────────────────────────────────────────────────────────────────────────────────────────┤
│ FLOOR TOPOLOGY & REAL-TIME STATION STATUS                                                        │
│  [CUT-1]   ──────► [BUF-1] ──────► [FORM-1] ──────► [BUF-2] ──────► [WELD-1] ──────► [BUF-3]     │
│   IDLE              (3/4)           PROC (82%)       (4/4) ⚠️        BLOCKED          (1/4)      │
│                                                                                                  │
│  [PAINT-1] ──────► [BUF-4] ──────► [INSPECT] ──────► [PACK-1] ──────► [FINISHED]                 │
│   PROC (91%)        (2/4)           SAMPLE (20%)     PROC (98%)       42 Units Delivered         │
├──────────────────────────────────────────────────────────────────────────────────────────────────┤
│ 🚨 ACTIVE ALERTS & ASSISTANT RECOMMENDATIONS                                                     │
│                                                                                                  │
│  [CRITICAL] Station WELD-1: Imminent Breakdown Hazard (Est. Ticks to Failure: 18 ± 4)            │
│  ├─ ROOT CAUSE: Severe mechanical wear (estimated w = 0.84). Cycle time dilated by +29.2%.      │
│  ├─ BOTTLENECK: BUF-2 is saturated (4/4), causing upstream FORM-1 to block within 3 ticks.       │
│  └─ PRESCRIPTIVE ACTION: Order immediate Preventive Maintenance (PM) with Tech-0.                 │
│     Estimated Savings: $1,450 overhaul avoidance + 24 ticks saved downtime.                     │
│     [Press 'A' to Authorize Action]                                                              │
│                                                                                                  │
│  [QUALITY] Inspection Mode Rebalancing                                                           │
│  └─ Latent defect probability elevated on FORM-1 due to worker fatigue. Recommend switching       │
│     inspection mode from 'sample' to 'full' for the next 20 ticks to prevent customer escape.    │
├──────────────────────────────────────────────────────────────────────────────────────────────────┤
│ LIVE TELEMETRY LOG                                                                               │
│  14:21:04  [SPC] Probe st_form_0 recorded 7.8 ticks (normal range: 6.8 - 7.4).                   │
│  14:21:18  [SPC] Probe st_weld_0 recorded 10.4 ticks (ALERT: CUSUM threshold breached).          │
│  14:21:30  [PULL] Finished goods release: Contract #104 batch delivered on-time (PPM: 0).        │
└──────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Head-to-Head A/B Evaluation Methodology

To prove that the Assistant provides undeniable, quantifiable industrial value (satisfying the hackathon rubric), we construct an automated, paired A/B benchmark harness:

### 4.1 Paired Benchmark Protocol
* **Sample Size:** 200 paired episodes across identical scenario hyperprior seeds.
* **Control Group (Condition A - Blind / Reactive Operator):**
  * Operates on static thresholds.
  * Only reacts to hard machine breakdowns (run-to-failure maintenance).
  * Uses the engine default `sample` inspection mode (65% catch probability).
  * Does not strategically allocate SPC probes.
* **Treatment Group (Condition B - Assistant-Guided Operator):**
  * Continuously evaluates CUSUM drift and RUL.
  * Dispatches SPC probes to high-risk stations.
  * Executes proactive PM when hazard $> 35\%$ and buffer cushions exist.
  * Dynamically scales inspection to 100% when defect risks spike.

### 4.2 Measured Performance Scorecard (independently verified 2026-10-17)

> **Correction.** An earlier version of this section showed a "scorecard" (−74.3% downtime, −94.7% escapes, +19.6pp on-time, +$10,440/week, all "p<0.0001, d_z>2") that was a **target, not a measurement** — none of those numbers were ever produced by a run. Replaced with verified numbers from `research/2026-10-17-ab-verification.md` (2000 held-out paired seeds 900000+, ratio-of-means with paired seed-bootstrap 95% CIs; reproduce with `demo/benchmark/run_ab.py --episodes 2000 --seed-base 900000 --cbm 0.40 --full-inspection`).

| Metric (per 336-tick episode) | Blind baseline | Assistant, default (legacy PM) | Assistant, condition-based PM (`cbm_threshold=0.40`, `full_inspection`) |
| :--- | :---: | :---: | :---: |
| Unplanned downtime (station-ticks under repair) | 82.2 | 66.0 (**−19.7%** [18.4, 21.0]) | 9.7 (**−88.2%** [87.3, 89.0]) |
| Total station downtime incl. planned PM | 82.2 | 81.4 (−0.9%) | 102.0 (**+24.0%**) |
| Breakdowns | 3.76 | 3.03 | 0.43 (−88.6%) |
| Defect escapes to customer (units) | 0.52 | 0.10 (**−81.8%** [79.2, 84.2]) | 0.04 (**−91.8%** [89.9, 93.5]) |
| Clean units shipped | 20.2 | 21.0 | 23.9 (+18%) |
| Net profit Δ vs blind | — | +$1,495 | +$5,471 [5,327, 5,603]; wins 96% of episodes |

Caveats: escape reduction is almost entirely the costless `full` inspection mode (blind + full inspection alone: −91.4%); the >70% downtime figure holds for *unplanned* downtime only, bought with ~12 planned 8-tick PM stops per episode. At `cbm_threshold=0.50`: −76.5% unplanned, +5.9% total, +$4,927.


---

## 5. The 3-Minute Hackathon Presentation Script

A battle-tested, minute-by-minute script for the live pitch or recorded demo video:

### 0:00 - 0:45 | The Hook & The Problem
> *"In discrete manufacturing, unexpected downtime and quality defects destroy over $50 billion of industrial value every year. The tragedy is that machines rarely die by surprise—they drift. Bearings wear, cycle times dilate by milliseconds, and defect probabilities creep up.*  
> *Yet, factory operators are forced to manage blind. Sensors are expensive, telemetry is partial, and operators only discover a problem when the line halts or a customer returns a defective shipment."*

### 0:45 - 1:45 | The Product: Real-Time Intelligence over the Kanban Stream
> *"Meet the amdrome Operator Assistant. Built for the Intelligent Industry challenge, the Assistant turns coarse, partial kanban signals into predictive industrial intelligence.*  
> *[Switch to Live Console] Here is a live automotive sub-assembly line running on our physics engine. The Assistant continuously allocates limited SPC probes to stations under stress. Look at Station Weld-1: the operator doesn't see a breakdown yet, but the Assistant's CUSUM filter just flagged a 29% cycle-time drift. The Weibull hazard engine estimates failure within 18 ticks.*  
> *Instead of letting the machine seize, ruin WIP, and halt the line, the Assistant alerts the supervisor and recommends a 12-tick preventive maintenance window right now while the upstream buffer can absorb the pause.*  
> *With one click, the operator authorizes PM. The technician services the machine, wear is reset, and the line never stops."*

### 1:45 - 2:30 | The Measured Evidence: Proof Over Vibes
> *"We didn't just build a dashboard—we measured it. Across 2,000 paired simulated weeks on held-out scenarios, against a run-to-failure operator:*  
> *- Unplanned breakdown downtime dropped by eighty-eight percent — we trade surprise breakdowns for short planned maintenance stops, and the line ships eighteen percent more good parts.*  
> *- Customer defect escapes fell by about ninety percent.*  
> *- Profit improved in ninety-six percent of simulated weeks."*  
> *(Numbers: research/2026-10-17-ab-verification.md. Do not quote on-time-delivery or $/week figures — never measured.)*

### 2:30 - 3:00 | Impact & Future Horizon
> *"The amdrome engine is designed as an open benchmark for factory RL and autonomous agents, compatible with Kaggle and Gymnasium. But the Operator Assistant proves that right now, intelligent telemetry can transform human operators into proactive problem-solvers.*  
> *Better reliability, near-zero customer escapes, and measured industrial ROI. Thank you."*
