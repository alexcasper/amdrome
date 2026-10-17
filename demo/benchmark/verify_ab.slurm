#!/bin/bash
# Sharded verify_ab.py sweep (Explorer HPC; any slurm cluster with python3).
# Stage first:  tar czf - simulator agents demo bin envs | ssh exp 'mkdir -p ~/amdrome && cd ~/amdrome && tar xzf -'
# Submit:       export ARMS=blind,asst,prod_cbm40 SEEDBASE=900000 EPS=2000 TAG=heldout
#               mkdir -p abv && sbatch --export=ALL demo/benchmark/verify_ab.slurm
# (sbatch --export=VAR=a,b splits on commas — export ARMS in the shell instead.)
#SBATCH -p short
#SBATCH -J abverify
#SBATCH -c 1
#SBATCH --mem=2G
#SBATCH -t 01:00:00
#SBATCH --array=0-9
#SBATCH -o abv/%x-%A_%a.log
module load python/3.13.5 2>/dev/null || true
cd ~/amdrome
python3 demo/benchmark/verify_ab.py --seed-base "$SEEDBASE" --episodes "$EPS" \
    --shard "$SLURM_ARRAY_TASK_ID" --nshards 10 --arms "$ARMS" \
    --out "abv/${TAG}_${SLURM_ARRAY_TASK_ID}.jsonl"
