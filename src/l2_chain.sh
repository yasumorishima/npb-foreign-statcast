#!/bin/bash
# Waits for the league-wide fetch, then runs the frozen Layer 2 pipeline once. Stops at the first failing gate.
set -e
cd ~/claude-scratch/npbmlb
until tail -1 fetch_lg.log | grep -q "^done"; do sleep 300; done
for s in 2024 2025; do nice .venv/bin/python l2_agg.py $s; done
nice .venv/bin/python l2_delta.py
nice .venv/bin/python l2_pred26.py
chmod a-w l2/pred26L2_bat.csv l2/pred26L2_pit.csv l2/coefL2.csv l2/relk.csv l2/delta.csv l2_pred26.py l2_agg.py l2_delta.py
echo CHAIN_OK $(TZ=Asia/Tokyo date "+%F %T")
