# amdrome

**Intelligent Industry Factory Simulation Engine & Autonomous Agent Benchmark**

`amdrome` is a discrete-event manufacturing simulation engine designed as both an open benchmark for reinforcement learning in the lineage of Kaggle simulation environments (`kaggriculture`), and the core asset for an **Intelligent Industry** hackathon demonstration.

---

## Deliverables & Architecture

1. **The Simulation Engine (`amdrome_sim`)**
   * Pure Python + NumPy discrete-event simulation core based on system dynamics (Sterman, *Business Dynamics*).
   * Dual interface: `kaggle_environments` compatible episode runner (JSON observation/action protocol) and Gymnasium / PettingZoo vector environments for RL.
   * Built from the ground up with an **anti-tape design guarantee**: hierarchical Bayesian hyperpriors and partial observability prevent trajectory memorization while preserving seed-level determinism.

2. **The Sample Agent Ecosystem (`agents/` & `rl/`)**
   * Readable scripted baselines: Blind Run-to-Failure, Lean Kanban Pull, and Adaptive Reactive Heuristics.
   * Parameter tuning pipeline using Bayesian search (Optuna / GEPA).
   * Stable-Baselines3 (MaskablePPO) training pipeline designed for fleet execution.

3. **The Intelligent Industry Demo Product (`demo/`)**
   * Live streaming **Operator Assistant** running over the kanban observation stream.
   * Statistical CUSUM drift detection and Weibull Remaining Useful Life (RUL) estimation.
   * Interactive Rich terminal operator console with real-time floor topology, andon boards, and prescriptive recommendations.
   * Automated paired A/B evaluation suite (`demo/benchmark/`), independently verified on 2000 held-out seeds (research/2026-10-17-ab-verification.md): with condition-based PM (`cbm_threshold=0.40`, `full_inspection=True`) the assistant cuts **unplanned** breakdown downtime 88% (95% CI 87–89%; total downtime incl. planned PM +24%) and defect escapes ~92% (CI 90–94%), +\$5.5k net/episode. The default (legacy-PM) assistant: −20% unplanned downtime, −82% escapes.

---

## Documentation Suite

Detailed architecture, mathematical models, API contracts, and roadmap specifications:

* 📄 **[Master Comprehensive Plan](file:///mnt/d/ops/amdrome/docs/COMPREHENSIVE_PLAN.md):** Overall system blueprint, strategic lessons from kaggriculture, acceptance gates, and delivery plan.
* 📐 **[Simulation Mechanics Specification](file:///mnt/d/ops/amdrome/docs/SPEC_MECHANICS.md):** Mathematical models of world topology, stock-flow queues, wear degradation, defect cascades, labour fatigue, market bidding, and two-tier RNG inventory.
* 🔌 **[API & Environment Specification](file:///mnt/d/ops/amdrome/docs/SPEC_API_ENV.md):** `kaggle_environments` JSON schema, Gymnasium `FactoryGymEnv` interface, PettingZoo multi-agent interface, and headless runner CLI (`bin/run_match.py`).
* 🖥️ **[Demo Product Specification](file:///mnt/d/ops/amdrome/docs/SPEC_DEMO_PRODUCT.md):** Operator Assistant analytical architecture, terminal UI layout, paired A/B benchmark methodology, and 3-minute pitch script.
* 🗺️ **[Roadmap & Beads Breakdown](file:///mnt/d/ops/amdrome/docs/ROADMAP_AND_BEADS.md):** Phased project roadmap, Beads task hierarchy, and fleet infrastructure execution protocol.
* 📜 **[Project Charter](file:///mnt/d/ops/amdrome/CHARTER.md):** Ratified charter, hackathon brief, and anti-tape design goals.
* 🛠️ **[Design v0 Workbench](file:///mnt/d/ops/amdrome/DESIGN.md):** Working design document and initial layout prototype findings.

---

## Fleet Execution Protocol (Hard Constraint)

* **Dawn (Local Host):** Orchestration, code editing, git versioning, beads management, fast test execution (<10s). Dawn does **no heavy simulation or sweep runs**.
* **Fleet Hosts (`dusk`, `albion`, `midknight`):** Headless episode execution, parameter sweeps, and RL training dispatched via stateless CLI runners over SSH.
