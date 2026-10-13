# amdrome Simulation API & Environment Specification (v1.0)

**Document Type:** API Specification, `kaggle_environments` Schema & Gym Interface  
**Lineage:** Building on GLM's `DESIGN.md` §1, §3, §8 and `kaggriculture` submission standards  
**Parent Bead:** amdrome-is5 (Engine core)  
**Deliverable Targets:** Single-file agent compatibility, Gymnasium / PettingZoo RL interface, headless stateless runner CLI  

---

## 1. Dual Interface Architecture

To satisfy both the **Kaggle Challenge** format and the **Reinforcement Learning (SB3)** training pipeline, `amdrome` implements a strict dual-interface pattern:

```
                  ┌──────────────────────────────────────────────┐
                  │             amdrome Simulation Core          │
                  │  (Pure Python + NumPy, Pure Determinism)     │
                  └──────────────────────┬───────────────────────┘
                                         │
                 ┌───────────────────────┴───────────────────────┐
                 ▼                                               ▼
   ┌───────────────────────────┐                   ┌───────────────────────────┐
   │ kaggle_environments Shell │                   │  Gymnasium / PettingZoo   │
   │                           │                   │                           │
   │ • Single-file python agent│                   │ • Vectorized environments │
   │ • JSON obs/act protocol   │                   │ • Tensor obs / action Box │
   │ • Per-turn timeout & bank │                   │ • SB3 MaskablePPO support │
   │ • Replay JSON / HTML tape │                   │ • Fast local/fleet train  │
   └───────────────────────────┘                   └───────────────────────────┘
```

Both interfaces wrap the identical underlying simulation engine without duplicating physics or state transitions.

---

## 2. `kaggle_environments` Protocol Specification

### 2.1 Agent Signature
An agent submitted to the competition is a single self-contained Python file exposing a callable function:

```python
def agent(observation, configuration) -> dict:
    """Agent entrypoint called at each simulation tick.
    
    Args:
        observation: AttributeDict containing visible kanban observations.
        configuration: AttributeDict containing static episode parameters.
        
    Returns:
        dict: Valid action dictionary for this tick.
    """
    ...
```

### 2.2 Configuration Schema (`configuration`)
Static parameters passed to the agent on tick 0:

| Field | Type | Description |
| :--- | :---: | :--- |
| `episode_ticks` | `int` | Total duration of the episode (default: `336`). |
| `grid_width` | `int` | Factory floor width (default: `12`). |
| `grid_height` | `int` | Factory floor height (default: `8`). |
| `num_players` | `int` | Number of competing factories in the market (`1` to `4`). |
| `player_index` | `int` | Zero-indexed ID of the current agent (`0` to `num_players - 1`). |
| `act_timeout` | `float` | Per-step timeout in seconds (default: `0.25`). |
| `run_timeout` | `float` | Episode-wide emergency timeout bank (default: `60.0`). |
| `spc_budget_per_shift` | `int` | Allocation of SPC sample probes per 48 ticks (default: `8`). |
| `routes` | `list[str]` | Standard manufacturing sequence: `["cut", "form", "weld", "paint", "inspect", "pack"]`. |

---

### 2.3 Observation Schema (`observation`)
The observation represents the **Kanban Epistemic Layer** at tick $t$. It exposes *only* the authorized monitoring data:

```json
{
  "step": 42,
  "shift_index": 0,
  "tick_in_shift": 42,
  "remaining_overage_time": 59.82,
  "cash": 24500.0,
  "raw_stock_inventory": 18,
  "telemetry_budget_remaining": 3,
  
  "stations": [
    {
      "id": "st_cut_0",
      "kind": "cut",
      "pos": [0, 3],
      "state": "PROCESSING",
      "queue_depth": 2,
      "completed_units": 14,
      "has_sensor": true,
      "andon_active": false
    },
    {
      "id": "st_weld_0",
      "kind": "weld",
      "pos": [4, 3],
      "state": "BLOCKED",
      "queue_depth": 4,
      "completed_units": 11,
      "has_sensor": false,
      "andon_active": true
    }
  ],
  
  "buffers": [
    {
      "id": "buf_in",
      "pos": [0, 2],
      "count": 3,
      "capacity": 4
    },
    {
      "id": "buf_cut_weld",
      "pos": [2, 3],
      "count": 4,
      "capacity": 4
    }
  ],
  
  "workers": [
    {
      "id": "w_0",
      "assigned_station": "st_cut_0",
      "shift": 0,
      "fatigue_coarse": "LOW"
    },
    {
      "id": "w_1",
      "assigned_station": "st_weld_0",
      "shift": 0,
      "fatigue_coarse": "HIGH"
    }
  ],
  
  "technicians": [
    {
      "id": "tech_0",
      "state": "IDLE",
      "target_station": null,
      "ticks_remaining": 0
    },
    {
      "id": "tech_1",
      "state": "REPAIR",
      "target_station": "st_form_0",
      "ticks_remaining": 14
    }
  ],
  
  "spc_samples": [
    {
      "station_id": "st_cut_0",
      "tick": 41,
      "measured_cycle_time": 7.2,
      "sigma_tolerance": 0.14
    }
  ],
  
  "inspection_reports": [
    {
      "tick": 38,
      "inspected_count": 5,
      "defects_detected": 1,
      "reworked": 1,
      "scrapped": 0
    }
  ],
  
  "active_alarms": [
    {
      "station_id": "st_weld_0",
      "type": "BUFFER_SATURATION",
      "raised_tick": 36
    }
  ],
  
  "market": {
    "spot_raw_price": 128.50,
    "lead_time_ticks": 12,
    "available_contracts": [
      {
        "id": "contract_101",
        "volume": 20,
        "max_bid_price": 280.0,
        "deadline_tick": 180,
        "quality_sla_ppm": 250,
        "late_penalty_rate": 15.0
      }
    ],
    "won_contracts": [
      {
        "id": "contract_098",
        "agreed_price": 265.0,
        "total_volume": 15,
        "delivered_volume": 9,
        "deadline_tick": 120
      }
    ]
  }
}
```

---

### 2.4 Action Schema (`action`)
The agent returns a dictionary containing decisions to execute during the current tick. All fields are optional:

```json
{
  "buy_raw": 10,
  "bids": {
    "contract_101": 255.0
  },
  "spc_probes": [
    "st_weld_0"
  ],
  "maintenance": [
    {
      "tech_id": "tech_0",
      "station_id": "st_cut_0",
      "type": "PM"
    }
  ],
  "worker_assignments": [
    {
      "worker_id": "w_2",
      "station_id": "st_weld_0"
    }
  ],
  "inspection_mode": "sample",
  "relocate_stations": [
    {
      "station_id": "st_weld_0",
      "new_pos": [4, 4]
    }
  ],
  "alarm_configs": [
    {
      "station_id": "st_cut_0",
      "metric": "CYCLE_TIME",
      "threshold": 9.0
    }
  ]
}
```

#### Validation & Graceful Fallbacks:
* **Overspending:** If `buy_raw * spot_price > cash`, the order is automatically truncated to `floor(cash / spot_price)`.
* **Budget Exceeded:** If more `spc_probes` are requested than `telemetry_budget_remaining`, only the first $B$ probes are evaluated; remainder are discarded.
* **Conflicting Orders:** If two technicians are assigned to the same station, the first assignment takes precedence.
* **Invalid Station/Coordinates:** Invalid move coordinates or assignments are discarded with a structured warning written to the match error log, preserving simulation continuity.

---

## 3. Gymnasium Single-Agent Interface (`FactoryGymEnv`)

For RL experimentation and baseline training with Stable-Baselines3 (SB3), `amdrome` provides a standard `gymnasium.Env` implementation.

### 3.1 Observation Space
To support standard neural network architectures (MLP / CNN), `FactoryGymEnv` supports both:
1. `Dict` observation space mirroring the structured kanban telemetry.
2. Flattened 1D vector observation $\mathbf{o}_t \in \mathbb{R}^{D}$ ($D = 128$), including:
   * Normalized cash balance: $\tanh(\text{cash} / 50000)$.
   * Station status one-hot encodings and coarse queue sizes.
   * Recent SPC cycle-time moving averages and drift estimates.
   * Active alarm indicator bits.
   * Spot price and inventory levels.

### 3.2 Action Space
To accommodate discrete RL algorithms (PPO, MaskablePPO, DQN), `FactoryGymEnv` structures actions as a **`MultiDiscrete`** or hierarchical discrete action tuple:

$$\mathcal{A} = [a_{\text{procure}}, a_{\text{inspect}}, a_{\text{probe}}, a_{\text{maint}}, a_{\text{bid}}]$$

| Dimension | Meaning | Cardinality | Values |
| :---: | :--- | :---: | :--- |
| **0** | Procurement | 5 | `0`: No order, `1`: Buy 5, `2`: Buy 10, `3`: Buy 20, `4`: Buy 40 |
| **1** | Inspection Mode | 3 | `0`: Skip, `1`: Sample (20%), `2`: Full (100%) |
| **2** | SPC Probe Target | 7 | `0`: None, `1..6`: Probe station $s_1 \dots s_6$ |
| **3** | Maintenance Action | 7 | `0`: None, `1..6`: Order PM on station $s_1 \dots s_6$ |
| **4** | Bid Strategy | 4 | `0`: Do not bid, `1`: Aggressive (cost+10%), `2`: Balanced (cost+25%), `3`: Premium (cost+40%) |

### 3.3 Reward Function
The reward signal directly reflects economic value creation while offering dense learning signals:

$$R_t = \Delta \text{Equity}_t - \text{Penalties}_t$$
$$\Delta \text{Equity}_t = \Delta \text{Cash}_t + \bar{P}_{\text{raw}} \cdot \Delta \text{Inventory}_t$$
$$\text{Penalties}_t = \lambda_{\text{wip}} \cdot \text{WIP}_t + \lambda_{\text{scrap}} \cdot \text{Scrap}_t + \lambda_{\text{down}} \cdot \mathbb{I}(\text{Breakdown}) + \lambda_{\text{escape}} \cdot \text{DefectEscapes}_t$$

* $\lambda_{\text{wip}} = 0.50$: holding cost per job-tick in WIP.
* $\lambda_{\text{scrap}} = 300.0$: scrap cost write-off.
* $\lambda_{\text{down}} = 200.0$: downtime penalty per broken tick.
* $\lambda_{\text{escape}} = 850.0$: customer escape penalty.

---

## 4. Multi-Agent PettingZoo Interface (`FactoryLeagueEnv`)

For multi-factory competition and league evaluation:
* Complies with PettingZoo `ParallelEnv` standard.
* Agents observe their individual factory states while interacting through a shared `MarketEngine`.
* Contracts and spot raw materials are pooled across factories.
* Enables self-play training, population-based training (PBT), and Elo ladder evaluation.

---

## 5. Headless Runner CLI Specification (`bin/run_match.py`)

In accordance with **DESIGN §8 (Portability & Fleet Runner Design)**, heavy match execution is strictly decoupled from the local orchestration environment.

### 5.1 CLI Syntax
```bash
python bin/run_match.py \
    --agents path/to/agent_a.py path/to/agent_b.py \
    --seed 42001 \
    --episodes 50 \
    --ticks 336 \
    --out results.jsonl \
    --tapes-dir tapes/ \
    --threads 8
```

### 5.2 JSONL Output Schema
Each line of `results.jsonl` contains a complete episode record:
```json
{
  "match_id": "match_20261013_42001",
  "episode_index": 0,
  "seed": 42001,
  "ticks": 336,
  "hyper": {
    "lam": 0.114,
    "proc_scale": 1.02,
    "wear_rate": 0.0125,
    "t_noise": 0.04
  },
  "players": [
    {
      "index": 0,
      "agent": "agent_a.py",
      "final_cash": 34820.0,
      "net_profit": 14820.0,
      "completed_units": 48,
      "scrapped_units": 2,
      "escaped_defects": 0,
      "downtime_ticks": 12,
      "mean_wip": 6.84,
      "mean_cycle_time": 28.4,
      "contracts_delivered": 3,
      "contracts_defaulted": 0,
      "score": 14210.0
    }
  ]
}
```

### 5.3 Determinism and Reproducibility Assurance
1. **Zero External Network Calls:** The runner operates completely offline.
2. **Pure File Artifacts:** Inputs are Python scripts and JSON configs; outputs are JSONL and replay tapes.
3. **Reproducibility Guarantee:** Executing `run_match.py` with identical `--seed` and agent files produces byte-identical `results.jsonl` on Linux, macOS, and any Python 3.10+ runtime.
