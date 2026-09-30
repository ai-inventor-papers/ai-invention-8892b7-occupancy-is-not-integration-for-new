"""STAGE 0: freeze the D2 SPEC before any outcome is computed (results/d2_prereg.json + sha256 + UTC timestamp)."""
from __future__ import annotations

import datetime as dt
import json

from loguru import logger

from config import LOGS, RESULTS, SPEC, spec_hash


def freeze() -> str:
    p = RESULTS / "d2_prereg.json"
    h = spec_hash()
    if p.exists():
        old = json.loads(p.read_text())
        if old["sha256"] != h:
            raise RuntimeError("SPEC changed after the freeze: log the change in results/deviations.md and re-freeze "
                               "explicitly (delete results/d2_prereg.json) if it is intended")
        logger.info(f"prereg already frozen: {h}")
        return h
    ts = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    p.write_text(json.dumps({"spec": SPEC, "sha256": h, "frozen_utc": ts,
                             "note": "sha256 = sha256(json.dumps(spec, sort_keys=True)); frozen before stage 6 "
                                     "(outcomes) ran for the first time"}, indent=1))
    with open(LOGS / "prereg_freeze.log", "a") as f:
        f.write(f"{h} {ts}\n")
    logger.info(f"prereg frozen {h} at {ts}")
    return h
