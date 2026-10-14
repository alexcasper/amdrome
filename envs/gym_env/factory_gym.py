"""Gymnasium wrapper over the amdrome core engine (optional dependency).

Import fails with a clear message if gymnasium is absent — the engine and
league runner are stdlib-only; this wrapper is for RL training (SB3) on
fleet hosts that install extras. Smoke-tested on hosts with gymnasium
(bead amdrome-x4i); the core engine carries its own determinism tests.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "..", "simulator", "src"))

BID_SHADES = [0.88, 0.92, 0.96, 1.00, 1.04]
CAPS_PRESETS = [[3, 3, 3, 3, 3, 3], [8, 3, 2, 2, 2, 1], [2, 4, 4, 4, 2, 2]]


class _RlAgent:
    """Bridges discrete RL actions (set per step) to engine action dicts."""

    def __init__(self):
        self.actions = {}

    def act(self, obs):
        a = self.actions
        self.actions = {}            # one-shot; env sets before each tick
        return a


class FactoryGymEnv:
    """gymnasium.Env-shaped wrapper (duck-typed)."""

    def __init__(self, seed=0, layout="compact"):
        try:
            import gymnasium as gym
        except ImportError as e:
            raise ImportError(
                "gymnasium not installed — RL wrappers need it "
                "(uv pip install gymnasium on the training host)") from e
        from amdrome_sim import Engine
        self._Engine = Engine
        self.gym = gym
        self.seed = seed
        self.layout = layout
        self.action_space = gym.spaces.MultiDiscrete([5, 6, 2, 3])
        self.observation_space = gym.spaces.Box(
            low=0.0, high=1e6, shape=(64,), dtype=float)
        self._rl_agent = _RlAgent()
        self._e = None
        self._t = -1

    def _flatten(self, obs):
        v = [float(obs["t"]), float(obs["wip"]), float(obs["spot_price"]),
             float(obs["spc_probes_left"])]
        for kind in sorted(obs["cards"]):
            c = obs["cards"][kind]
            v += [float(c["queue_before"]),
                  1.0 if c["state"] == "proc" else 0.0]
        for kind in sorted(obs["cusum"]):
            v.append(float(obs["cusum"][kind]))
        v += [0.0] * (64 - len(v))
        return v[:64]

    def _obs(self):
        e = self._e
        return e.view.observe(max(0, self._t), e.line, len(e.jobs),
                              e.spot.p, e.open_contracts, e.results_log)

    def reset(self, *, seed=None, options=None):
        self._e = self._Engine(seed if seed is not None else self.seed,
                               agent=self._rl_agent, layout=self.layout)
        self._t = 0
        self._e.t = 0
        return self._flatten(self._obs()), {}

    def step(self, action):
        e = self._e
        obs = self._obs()
        shade, probe_slot, pm_flag, caps_slot = [int(a) for a in action]
        acts = {"bids": {c["id"]: round(c["unit_price"] * BID_SHADES[shade],
                                        2) for c in obs["open_contracts"]}}
        kinds = sorted(obs["cards"])
        if probe_slot < len(kinds):
            acts["probes"] = [kinds[probe_slot]]
        if pm_flag:
            acts["pm"] = [max(obs["cusum"], key=obs["cusum"].get)]
        if (self._t + 1) % 48 == 0:
            acts["caps"] = CAPS_PRESETS[caps_slot]
        self._rl_agent.actions = acts

        self._t += 1
        e.t = self._t
        e._tick(self._t)
        done = self._t >= e.ticks - 1
        reward = 0.0
        if done:
            for cid in list(e.won):
                e._settle(cid, e.ticks)
            reward = e.result()["net_profit"]
        return self._flatten(self._obs()), reward, done, False, {}
