# amdrome Simulation Mechanics Specification (v1.0)

**Document Type:** Formal Mechanics Specification & Mathematical Model  
**Lineage:** Building on GLM's `DESIGN.md` v0 and lessons from `kaggriculture` (farm)  
**Parent Bead:** amdrome-is5 (Engine core)  
**Target Architecture:** Pure Python + NumPy core, Gym/Gymnasium environment, `kaggle_environments` episode runner  

---

## 1. System Philosophy & Stock-Flow Foundation

The `amdrome` simulation models a discrete manufacturing plant operating under principles of system dynamics (Sterman, *Business Dynamics*). The core premise is that factory performance is governed by coupled stock-and-flow feedback loops:

1. **Material Stocks and Flows:** Jobs flow through processing stations and buffer inventories. Bottlenecks shift dynamically based on layout distance, station speeds, blocking, and starvation.
2. **Physical Degradation:** Stations wear down with operational throughput, causing continuous **performance drift** (cycle time dilation) and a convex **breakdown hazard** (unplanned downtime).
3. **Quality & Defect Cascades:** Latent defects are injected stochastically based on wear and worker fatigue. Without timely inspection, defects flow downstream, consuming upstream capacity and culminating in catastrophic customer escapes.
4. **Information Delays (The Kanban Epistemic Boundary):** Operators do not observe ground-truth system states (e.g., true wear, exact defect states, full inventory queues). They observe delayed, noisy, aggregated signals (kanban cards, SPC samples, andon alerts).
5. **Economic Exchange:** Factories operate within a shared, volatile marketplace where they procure raw inputs and compete for customer delivery contracts.

```
       [Raw Inputs]
            │
            ▼ (Flow: Job Release)
     ┌─────────────┐
     │ Inbuf Stock │
     └──────┬──────┘
            │
    ┌───────▼──────────────────────────┐
    │  Processing Stations (1..K)      │◄─── [Labour & Tech Roster]
    │  • Hidden Wear: w_i(t)           │
    │  • Cycle Drift: T_proc(w)        │
    │  • Defect Gen:  P_defect(w, skill│
    └───────┬──────────────────────────┘
            │
     ┌──────▼──────┐
     │ Inspect Stn │───── (Rework / Scrap)
     └──────┬──────┘
            │ (Escaped Defects vs Clean Goods)
            ▼
     ┌─────────────┐
     │ Finished Q  │ ────► [Customer Delivery & Contract Settlement]
     └─────────────┘
```

---

## 2. World Model & Topology

### 2.1 Spatiotemporal Scale
* **Time Ticks ($t$):** Discrete simulation steps.
  * 1 shift = 48 ticks.
  * 1 day = 3 shifts = 144 ticks.
  * 1 production week (standard episode) = 7 shifts = 336 ticks (or 1 full week = 1,008 ticks in long-form matches; default standard episode is 336 ticks).
  * 1 tick $\approx$ 10 simulation minutes.
* **Floor Grid ($G$):**
  * Dimension: $W \times H = 12 \times 8$ cells (96 discrete spatial locations).
  * Cell Coordinates: $(x, y) \in [0, 11] \times [0, 7]$.
  * Footprint:
    * Standard Processing Station: 1 cell (or multi-cell footprint 2x1 for heavy machinery).
    * Buffer: 1 cell.
    * Walkways/Transit: Implicit grid traversal over open cells.

### 2.2 Station Typology
The standard manufacturing process follows a 6-stage routing:
$$R = [\text{cut}, \text{form}, \text{weld}, \text{paint}, \text{inspect}, \text{pack}]$$

| Station Kind | Footprint | Base Proc Time ($T_0$) | Wear Sensitivity ($\kappa$) | Base Defect Rate ($p_0$) | Description |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **`cut`** | 1 cell | 6 ticks | Medium ($0.012$) | $0.010$ | Raw sheet/stock cutting; saw/laser tooling |
| **`form`** | 1 cell | 7 ticks | High ($0.015$) | $0.015$ | Stamping / bending presses; alignment sensitive |
| **`weld`** | 1 cell | 8 ticks | High ($0.018$) | $0.025$ | Robotic/manual welding; high thermal stress |
| **`paint`** | 1 cell | 9 ticks | Low ($0.008$) | $0.020$ | Surface coating / baking; nozzle clogging |
| **`inspect`** | 1 cell | 5 ticks | Negligible ($0.002$) | $0.000$ | Quality verification; SPC / visual / ultrasonic |
| **`pack`** | 1 cell | 4 ticks | Negligible ($0.003$) | $0.002$ | Final packaging and palletizing |
| **`buffer`** | 1 cell | 0 ticks | None ($0.000$) | $0.000$ | Kanban staging buffer with capacity $C_{buf} = 4$ |

### 2.3 Spatial Transport Physics
Movement of material between station $A$ at $(x_A, y_A)$ and downstream buffer/station $B$ at $(x_B, y_B)$ incurs transit time:
$$d(A, B) = |x_A - x_B| + |y_A - y_B| \quad \text{(Manhattan Distance)}$$
$$T_{\text{trans}}(A, B) = \max\left(1, \left\lfloor d(A, B) \cdot v_{\text{trans}} \cdot (1 + \epsilon_{\text{noise}}) \right\rceil\right)$$
where:
* $v_{\text{trans}} = 1.0$ tick per Manhattan cell.
* $\epsilon_{\text{noise}} \sim \text{Uniform}(-\eta_{\text{trans}}, \eta_{\text{trans}})$, drawn per transit dispatch.
* Jobs in transit do not occupy floor cells, representing internal overhead conveyors or dedicated cart paths.

### 2.4 Queuing, Blocking, and Starvation
Let station $s$ have upstream buffer $B_{in}(s)$ and downstream buffer $B_{out}(s)$:
1. **Starvation:** Station $s$ is starved at tick $t$ if $s$ is idle and $B_{in}(s)$ has queue length $|Q(B_{in})| = 0$.
2. **Processing:** When idle and $|Q(B_{in})| > 0$, station $s$ pops the head job $j$, advances job state to `processing`, and schedules duration $T_{\text{proc}}$.
3. **Blocking (Type 1 Kanban Blocking):** When station $s$ completes job $j$, it cannot release $j$ unless $|Q(B_{out})| < C_{buf}$.
   * If downstream buffer is full ($|Q(B_{out})| = C_{buf}$), station $s$ enters **`blocked`** state.
   * While blocked, station $s$ cannot accept new incoming jobs, propagating upstream congestion.
   * Measured empirical rule: In line-saturation regimes ($\lambda \ge 0.10$), downstream buffer blocking is the direct mechanism that translates poor physical layouts into lost factory throughput.

---

## 3. Physical Degradation & Failure Mechanics

Every mechanical processing station $s$ maintains a hidden, continuous wear state $w_s(t) \in [0.0, 1.0]$.

### 3.1 Wear Accumulation
Wear accumulates from physical operation:
$$w_s(t + 1) = \min\left(1.0, w_s(t) + \Delta w_s(t)\right)$$
$$\Delta w_s(t) = \begin{cases}
\kappa_s \cdot \omega_{\text{episode}} \cdot (1 + \xi_{\text{op}}) & \text{if station } s \text{ is processing at tick } t \\
0 & \text{if idle, starved, or blocked}
\end{cases}$$
where:
* $\kappa_s$: station-class base wear coefficient.
* $\omega_{\text{episode}} \sim \text{Hyperprior}(\text{wear\_rate})$: scenario-wide wear multiplier.
* $\xi_{\text{op}} \sim \mathcal{N}(0, 0.05)$: per-tick operational jitter.

### 3.2 Performance Drift (Continuous Degradation)
Wear does not simply cause sudden failures; it causes **gradual cycle-time inflation (drift)**:
$$T_{\text{proc}}(s, j) = \max\left(1, \left\lfloor T_{0}(s) \cdot \mu_{\text{proc}} \cdot e^{\zeta} \cdot \left(1 + \delta_{\text{drift}} \cdot w_s(t)\right) \cdot \Phi_{\text{worker}}(s) \right\rceil\right)$$
where:
* $T_0(s)$: nominal baseline duration.
* $\mu_{\text{proc}} \sim \text{Hyperprior}(\text{proc\_scale})$: episode-wide manufacturing speed.
* $\zeta \sim \mathcal{N}(0, \sigma_{\text{proc}}^2)$ with $\sigma_{\text{proc}} = 0.12$: lognormal duration variance.
* $\delta_{\text{drift}} = 0.35$: drift slope (at $w=1.0$, nominal duration is $+35\%$ slower).
* $\Phi_{\text{worker}}(s)$: worker skill and fatigue modifier (see §5).

### 3.3 Catastrophic Breakdown Hazard (Weibull Model)
The hazard rate $h(w)$ represents the instantaneous probability of a mechanical breakdown during active processing:
$$h(w_s) = h_0 + \beta_{\text{wear}} \cdot (w_s)^\gamma$$
* $h_0 = 0.0005$: baseline infant-mortality / random fault rate.
* $\beta_{\text{wear}} = 0.045$: wear-dependent hazard multiplier.
* $\gamma = 3.0$: convexity exponent (representing accelerated mechanical wear-out).

```
Hazard h(w)
   │                                   * (w=1.0, h ≈ 0.0455)
   │                                  *
   │                                 *
   │                                *
   │                               *
   │                             **
   │                       ******
   │ **********************
   └─────────────────────────────────────► Wear w
   0.0                    0.5         1.0
```

At each processing tick, a breakdown occurs if $U \sim \text{Uniform}(0, 1) < h(w_s)$.

### 3.4 Maintenance Physics
The player has two distinct maintenance pathways:
1. **Preventive Maintenance (PM):**
   * Triggered proactively by the player.
   * Can only be executed when the station is idle or after current job finishes.
   * Duration: $T_{PM} = 12$ ticks.
   * Cost: $\$250$ in parts/supplies + requires 1 Maintenance Technician for duration.
   * Effect: Resets wear: $w_s \leftarrow \max(0.0, w_s \cdot 0.10)$ (retains 10% residual age).
2. **Corrective Maintenance (Breakdown Repair):**
   * Triggered automatically upon breakdown.
   * Station enters `broken` state immediately; current job is ruined (scrapped).
   * Duration: $T_{\text{repair}} \sim \max(16, \lfloor \text{Lognormal}(3.2, 0.4) \rfloor)$ ticks (mean $\approx 28$ ticks, heavy tail up to 60 ticks).
   * Cost: $\$1,200$ emergency overhaul cost + requires 1 Maintenance Technician for duration.
   * Effect: Station offline; upon completion, $w_s \leftarrow 0.15$.

---

## 4. Quality Architecture & Inspection Filtering

### 4.1 Defect Injection
At each processing station $s \in \{\text{cut}, \text{form}, \text{weld}, \text{paint}, \text{pack}\}$, an operation on job $j$ has probability $P_{\text{defect}}$ of introducing a latent defect:
$$P_{\text{defect}}(s) = 1 - \exp\left(-\left(p_{0}(s) + \alpha_w \cdot (w_s)^2 + \alpha_{\text{fatigue}} \cdot F_{\text{worker}} - \alpha_{\text{skill}} \cdot S_{\text{worker}, s}\right)\right)$$
* Defects are binary attributes attached to job parts: $j.\text{defects}[s] \in \{0, 1\}$.
* Total defects on job: $D(j) = \sum_s j.\text{defects}[s]$.
* Defective jobs proceed through downstream stations normally unless intercepted at the **`inspect`** station.

### 4.2 Inspection Station Modes
The player controls the operational policy at `inspect`:

| Mode | Coverage | Duration per Job | Unit Cost | Detection Sensitivity ($P_D$) | False Alarm Rate ($P_{FA}$) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **`skip`** | 0% | 0 ticks | $\$0$ | $0.00$ | $0.00$ |
| **`sample`** | 20% (every 5th job) | 4 ticks | $\$15$ | $0.85$ (on sampled) | $0.01$ |
| **`full`** | 100% (all jobs) | 8 ticks | $\$45$ | $0.98$ | $0.02$ |

### 4.3 Disposition Logic (Rework vs Scrap)
When a defect is detected on job $j$:
* If $D(j) = 1$ and defect originated at $\{\text{weld}, \text{paint}\}$: Job is sent to **Rework Loop** (re-enters line at that station buffer; costs $\$100$ and $T_{\text{rework}}$ ticks).
* If $D(j) \ge 2$ or defect originated at $\{\text{cut}, \text{form}\}$: Job is condemned as **Scrap** (materials lost, written off at $\$300$ penalty).

### 4.4 Customer Escape Penalty
If a defective job passes `pack` without detection and is delivered to fulfill a contract:
* Escape cost: $\$850$ per escaped defective unit.
* Contract Quality SLA: If batch defect rate exceeds contract threshold (e.g., $> 200$ PPM), severe contract cancellation penalty ($-\$5,000$) is assessed.

---

## 5. Labour Roster & Human Dynamics

### 5.1 Roster Specification
A factory employs a fixed roster of:
* $N_{\text{prod}} = 10$ Production Workers: $\{W_1, \dots, W_{10}\}$.
* $N_{\text{tech}} = 2$ Maintenance Technicians: $\{M_1, M_2\}$.

### 5.2 Worker State Vector
Each production worker $W_i$ has:
* **Skill Vector:** $\mathbf{S}_i \in [0.1, 1.0]^6$, rating proficiency across the 6 station types.
* **Fatigue Level:** $F_i(t) \in [0.0, 1.0]$.
* **Shift Assignment:** Shift 1 (morning), Shift 2 (evening), Shift 3 (night), or Off.
* **Current Allocation:** Assigned to station $s$ or Idle/Resting.

### 5.3 Fatigue Dynamics
During an active shift where worker $W_i$ is assigned to an operating station:
$$F_i(t + 1) = \min\left(1.0, F_i(t) + \Delta F_{\text{work}}\right), \quad \Delta F_{\text{work}} = 0.004 \text{ / tick}$$
During rest shifts or when unassigned:
$$F_i(t + 1) = \max\left(0.0, F_i(t) - \Delta F_{\text{rest}}\right), \quad \Delta F_{\text{rest}} = 0.008 \text{ / tick}$$

**Fatigue Penalties:**
* Effective Station Speed: $\Phi_{\text{worker}}(s) = 1.0 + 0.30 \cdot F_i(t) - 0.20 \cdot (\mathbf{S}_{i, s} - 0.5)$.
* Defect Generation Modifier: scales up defect injection by up to $+60\%$ at $F_i = 1.0$.

### 5.4 Technician Contention
Technicians $\{M_1, M_2\}$ handle both PM and emergency repairs.
* If 2 stations are undergoing PM and a 3rd station breaks down, the breakdown cannot begin repairs until a tech is freed.
* This creates a critical operational tradeoff: over-scheduling PM consumes technician capacity and risks leaving breakdowns unserviced.

---

## 6. Shared Market & Procurement Engine

Factories in `amdrome` do not exist in a vacuum; they compete in a shared market environment (1 to 4 factories in multi-play).

### 6.1 Raw Material Input Procurement
* Jobs require 1 unit of raw stock to release into the entry buffer.
* **Spot Material Price ($P_{\text{raw}}(t)$):** Follows an Ornstein-Uhlenbeck jump-diffusion process:
  $$dP_t = \theta (\mu_{\text{raw}} - P_t)dt + \sigma_{\text{raw}} dW_t + J_t dq_t$$
  * Mean reversion speed: $\theta = 0.05$.
  * Long-term mean: $\mu_{\text{raw}} = \$120 / \text{unit}$.
  * Volatility: $\sigma_{\text{raw}} = \$15$.
  * Jumps $J_t \sim \text{Lognormal}(3.0, 0.5)$ with arrival intensity $\lambda_{\text{jump}} = 0.02$ / tick (supply chain disruptions).
* Lead Time: Raw orders arrive after $L_{\text{raw}} \sim \text{Uniform}(8, 20)$ ticks. Factories must maintain raw stock inventory or risk starvation.

### 6.2 Customer Order Contracts
At stochastic intervals $t_{\text{order}} \sim \text{Poisson}(\lambda_{\text{order}})$, customer contracts are posted to the public exchange:
$$\mathcal{C}_k = \{ \text{Volume } V_k, \text{Deadline } D_k, \text{Max Price } \bar{P}_k, \text{SLA Quality PPM}_k, \text{Late Penalty Rate } \Pi_k \}$$
* **Contract Allocation:** First-price sealed-bid auction. Each participating factory submits bid $(p_k^{\text{bid}} \le \bar{P}_k)$.
* Lowest qualifying bidder wins the contract.
* Fulfillment: Completed jobs flowing out of `pack` are allocated to active contracts.
* Revenue: $V_k \times p_k^{\text{bid}}$ awarded upon on-time, conforming delivery.
* Late Penalty: $-\Pi_k \times (t_{\text{delivery}} - D_k)$ assessed per tick overdue.

---

## 7. The Kanban Observation Layer (Epistemic Boundaries)

In accordance with the **anti-tape design imperative**, full ground-truth state is strictly inaccessible to agents. Information is mediated through the **Kanban Telemetry Interface**.

### 7.1 Observation Channels

```
True State (Hidden)                      Observation Stream (Visible)
┌─────────────────────────┐              ┌─────────────────────────┐
│ • True Wear w_i         │              │ • Station Card Status   │
│ • True Latent Defects   │  Filters &   │ • SPC Cycle-Time Sample │
│ • Exact Queue Contents  │ ──────────►  │ • Buffer Card Count     │
│ • Station Remaining Ticks│ Subsampling │ • Defect Count at Insp  │
│ • Worker True Fatigue   │              │ • Andon Alarm Events    │
└─────────────────────────┘              └─────────────────────────┘
```

1. **Station Cards (Periodic Broadcast, every $K_{\text{card}} = 6$ ticks):**
   * Coarse status: `IDLE`, `PROCESSING`, `BLOCKED`, `BROKEN`, `MAINTENANCE`.
   * Current queue depth of attached buffers.
   * Cumulative completed units since shift start.
2. **Buffer Pull Signals (Event Stream):**
   * Dispatched whenever a kanban card is pulled from a downstream buffer to release an upstream job.
3. **Statistical Process Control (SPC) Samples (Budget-Constrained):**
   * Cycle-time measurement and dimensional tolerance data.
   * **Telemetry Budget:** The agent is allocated $B_{\text{spc}} = 8$ sample probes per shift.
   * The agent must explicitly allocate probes: `ACTION: sample_station(station_id)`.
   * Probing returns: $T_{\text{sample}} = T_{\text{actual}} + \epsilon_{\text{sensor}}$, where $\epsilon_{\text{sensor}} \sim \mathcal{N}(0, 0.4)$.
4. **Inspection Batch Reports:**
   * Received only when a batch passes `inspect` (reports detected defects and scrap rate).
5. **Configurable Andon Alarms:**
   * Player sets alert triggers (e.g., "Alert if station cycle time $> 10$ ticks" or "Alert if buffer queue $> 3$ for 12 ticks").
   * Subject to sensor noise and false positive rate $\alpha_{\text{alarm}} \approx 0.05$.

---

## 8. Complete RNG Inventory & Anti-Tape Architecture

To guarantee the **anti-tape property** while preserving **100% reproducible determinism**, the simulation enforces a two-tier generator hierarchy.

### 8.1 Two-Tier Generator Hierarchy
1. **Tier 1: Scenario Generator (`gen_scenario`)**
   * Seeded by `gen_seed(match_seed, "scenario")`.
   * Draws the episode hyperprior vector $\mathbf{\Theta} \in \mathbb{R}^{12}$.
   * These hyperparameters determine the environmental regime for the episode.
2. **Tier 2: Execution Generators**
   * Flow Generator: `gen_seed(match_seed, episode_id, factory_id, "flow")`.
   * Market Generator: `gen_seed(match_seed, episode_id, "market")`.
   * Labour Generator: `gen_seed(match_seed, episode_id, factory_id, "labour")`.
   * Sensor Generator: `gen_seed(match_seed, episode_id, factory_id, "sensor")`.

### 8.2 Inventory Table

| # | Element | Base Distribution | Hyperprior Distribution | What Skill It Tests | Observed Via |
| :-: | :--- | :--- | :--- | :--- | :--- |
| **1** | Contract Arrivals | $\text{Poisson}(\lambda_{\text{arr}})$ | $\lambda_{\text{arr}} \sim \text{Uniform}(0.08, 0.16)$ | Capacity Planning & Bidding | Market Feed |
| **2** | Spot Input Price | OU-Jump Diffusion | $\mu_{\text{raw}} \sim \text{Uniform}(100, 140)$ | Inventory & Cashflow | Market Feed |
| **3** | Wear Increment | $\text{Beta}(\alpha_w, \beta_w)$ | $\omega_{\text{wear}} \sim \text{Uniform}(0.008, 0.020)$ | Preventive Maintenance | Hidden; SPC Drift |
| **4** | Breakdown Hazard | Convex Weibull | $\beta_{\text{wear}} \sim \text{Uniform}(0.03, 0.06)$ | Redundancy & Buffer Sizing | Andon Alarm / Downtime |
| **5** | Cycle-Time Drift | $\text{Lognormal}(\mu_0(w), \sigma^2)$ | $\mu_{\text{proc}} \sim \text{Uniform}(0.85, 1.15)$ | SPC Sampling Allocation | SPC Samples Only |
| **6** | Defect Injection | $\text{Bernoulli}(p(w, \text{skill}))$ | $p_0 \sim \text{Uniform}(0.005, 0.025)$ | Inspection Mode Economics | Inspect Reports |
| **7** | Inspection Escape | $\text{Binomial}(N, 1 - P_D)$ | Mode-dependent | Quality SLA Risk Management | Customer Warranty Claims |
| **8** | Worker Absence | $\text{Bernoulli}(p_{\text{absent}})$ | $p_{\text{absent}} \sim \text{Uniform}(0.01, 0.08)$ | Cross-Training & Redundancy | Roster Card |
| **9** | Fatigue Rate | Deterministic + Jitter | $\Delta F \sim \text{Uniform}(0.003, 0.006)$ | Shift Rotation Design | Coarse Worker Card |
| **10**| Repair Duration | $\text{Lognormal}(\mu_R, \sigma_R^2)$ | $\mu_R \sim \text{Uniform}(2.8, 3.5)$ | Tech Allocation & Buffer Cushion| Tech Status Card |
| **11**| Transport Delay | $\text{Manhattan} \times (1 + \epsilon)$| $\eta_{\text{trans}} \sim \text{Uniform}(0.0, 0.15)$ | Layout Compactness | WIP Buffer Cards |
| **12**| Market Competitors| Policy Pool Sampling | Uniform from Model Registry | Strategic Bidding & Game Theory| Auction Results Only |

### 8.3 Determinism Rule
All seeds are generated via cryptographically pure integer hashing:
```python
def gen_seed(*parts) -> int:
    digest = hashlib.sha256("|".join(str(p) for p in parts).encode()).digest()
    return int.from_bytes(digest[:8], "big")
```
This completely avoids Python's salted string hash (`PYTHONHASHSEED`), ensuring bit-identical replays across different operating systems, runtimes, and worker processes.
