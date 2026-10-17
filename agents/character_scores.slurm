#!/bin/bash
# Character score table (Explorer HPC). Stage first:
#   tar czf - simulator agents | ssh exp 'mkdir -p ~/amdrome && cd ~/amdrome && tar xzf -'
# Submit: mkdir -p chars && sbatch agents/character_scores.slurm
#SBATCH -p short
#SBATCH -J charscores
#SBATCH -c 1
#SBATCH --mem=2G
#SBATCH -t 00:30:00
#SBATCH -o chars/%x.log
module load python/3.13.5 2>/dev/null || true
cd ~/amdrome
python3 agents/character_scores.py 910000 100 > chars/scores.jsonl
