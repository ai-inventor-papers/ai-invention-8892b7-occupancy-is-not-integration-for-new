#!/usr/bin/env python3
"""Entry point: K1 (which margin) / K3 (field boundary) / INFERENCE FIX evaluation of the confirmed D2 effect.

Run order (each stage is a separate script so a broken stage is reported as NOT RUN without touching the others):
  1. k/k_freeze.py        gates R0a-R0e -> results/gates.json; MDE simulations; k13_spec.json + sha256 (FREEZE)
                          skipped when results/k13_spec.json already exists (re-freezing would change the hash);
                          pass --refreeze to rebuild it (the new hash is appended to logs/freeze_log.txt)
  2. k/k_run.py --synthetic   smoke test on an NB2 synthetic outcome -> results/smoke/
  3. k/k_run.py           K1, K3, INFERENCE on the real outcome (asserts the spec hash first)
  4. audit/audit_k.py     independent pyfixest re-derivation -> audit/audit_k.json
  5. k/report.py          verdicts (results/k13_summary.json), figures/, record_of_numbers.csv, eval_out.json
  6. audit/audit_placebo.py   raw-file re-derivation of IVW rows / held-out p + placebo checks
Usage: uv run eval.py [--stages freeze,smoke,run,audit,report] [--refreeze]
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

from loguru import logger

WS = Path(__file__).resolve().parent
(WS / "logs").mkdir(exist_ok=True)
logger.remove()
logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
logger.add(WS / "logs" / "eval.log", rotation="30 MB", level="DEBUG")

STAGES = {"freeze": ["k/k_freeze.py", "--reps", "300"], "smoke": ["k/k_run.py", "--synthetic"],
          "run": ["k/k_run.py", "--stage", "all"], "audit": ["audit/audit_k.py"], "report": ["k/report.py"],
          "placebo": ["audit/audit_placebo.py"]}


def run(stage: str) -> int:
    t0 = time.time()
    env = dict(os.environ)
    env.setdefault("AII_DEPS_ROOT", str(WS.parents[2]))
    p = subprocess.run([sys.executable, *STAGES[stage]], cwd=WS, env=env)
    logger.info(f"stage {stage}: exit {p.returncode} in {time.time() - t0:.0f}s")
    return p.returncode


@logger.catch(reraise=True)
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stages", default="freeze,smoke,run,audit,report,placebo")
    ap.add_argument("--refreeze", action="store_true")
    a = ap.parse_args()
    for st in a.stages.split(","):
        if st == "freeze" and (WS / "results" / "k13_spec.json").exists() and not a.refreeze:
            logger.info("spec already frozen: skipping freeze (use --refreeze to rebuild)")
            continue
        rc = run(st)
        if rc != 0:
            logger.error(f"stage {st} failed with exit code {rc}")
            if st in ("freeze",):
                raise SystemExit(rc)


if __name__ == "__main__":
    main()
