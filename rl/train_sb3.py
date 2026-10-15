#!/usr/bin/env python3
"""SB3 training entrypoint (bead amdrome-x4i).

MaskablePPO over the FactoryGymEnv wrapper. Designed for FLEET/GPU hosts
(env_cteach profile) — NOT dawn. The wrapper's action masking is implicit
(no illegal-action penalty; the engine ignores invalid actions), so
standard PPO also works; MaskablePPO is kept for the discrete bundle.

Usage (on a host with the RL venv — see fleet-batch-compute skill):
  python3 rl/train_sb3.py --steps 100000 --run-name ppo_v1 \
      --out rl/runs/ppo_v1.zip

Env deps (install on the training host, never dawn):
  uv pip install gymnasium sb3-contrib torch numpy  # torch cpu is enough
"""

import argparse
import os
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, os.path.join(ROOT, "simulator", "src"))
sys.path.insert(0, os.path.join(ROOT, "envs", "gym_env"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--steps", type=int, default=100_000)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--run-name", default="ppo_v1")
    ap.add_argument("--out", default=None)
    ap.add_argument("--algo", choices=["ppo", "maskable-ppo"],
                    default="maskable-ppo")
    args = ap.parse_args()

    from stable_baselines3 import PPO
    if args.algo == "maskable-ppo":
        from sb3_contrib import MaskablePPO as Algo
    else:
        Algo = PPO

    from factory_gym import FactoryGymEnv

    env = FactoryGymEnv(seed=args.seed)
    model = Algo("MlpPolicy", env, verbose=1, seed=args.seed,
                 n_steps=2048, batch_size=512, gamma=0.995,
                 learning_rate=3e-4, tensorboard_log=None)
    model.learn(total_timesteps=args.steps, progress_bar=False)

    out = args.out or os.path.join(
        ROOT, "rl", "runs", f"{args.run_name}_{args.steps}.zip")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    model.save(out)
    print(f"[train_sb3] saved {out}")

    # quick post-train probe: 3 greedy episodes
    import numpy as np
    rewards = []
    for ep in range(3):
        obs, _ = env.reset(seed=args.seed + 1000 + ep)
        done, total = False, 0.0
        while not done:
            action, _ = model.predict(obs, deterministic=True)
            obs, r, done, _, _ = env.step(action)
            total += r
        rewards.append(round(total, 2))
    print(f"[train_sb3] greedy episode rewards: {rewards}")


if __name__ == "__main__":
    main()
