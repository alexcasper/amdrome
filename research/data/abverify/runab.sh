#!/bin/bash
module load python/3.13.5
cd ~/amdrome
python3 demo/benchmark/run_ab.py --episodes 200 --seed-base 81000 --report abv/report_legacy_81000.md > abv/runab_legacy_81000.jsonl
python3 demo/benchmark/run_ab.py --episodes 2000 --seed-base 900000 --cbm 0.40 --full-inspection --report abv/report_cbm40_900000.md > abv/runab_cbm40_900000.jsonl
