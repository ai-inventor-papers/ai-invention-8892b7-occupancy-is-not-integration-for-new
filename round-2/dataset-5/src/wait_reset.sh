#!/usr/bin/env bash
# wait until just after the 00:00 UTC credit reset, then run the batch-equivalence check (2 credits)
cd "$(dirname "$0")"
target=$(date -u -d "tomorrow 00:00:40" +%s); [ "$(date -u +%H)" = "00" ] && target=$(date -u +%s)
while [ "$(date -u +%s)" -lt "$target" ]; do sleep 20; done
AII_STEP=p1_batch_equivalence AII_ARTIFACT_CAP=20 .venv/bin/python batch_equivalence.py
