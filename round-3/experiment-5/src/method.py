#!/usr/bin/env python3
"""Is openness before take-off brokerage or churn? RQ1 deepen (iteration 3), $0, CPU only.

Pipeline (each step is a module in src/; this script orchestrates them in the pre-declared order):
  0  setup       vendor exp_3 code byte-identical, hash, write prereg_v3.json BEFORE any label
  1  population  frozen replacement rule -> MAIN / STRICT / SENS; folds (sha1 rule == ds5), old/new
  2  prep3       dataset_5 c-papers (active + sealed held-out), totals, data-change check vs exp_3
  3  attach      re-attach concepts to the exp_3 snapshots (modes repro_code, repro_data, full) + R1b / R1c metrics
  4  indicators  vendored concept_indicators + new columns + R1a (label-free) ; repro gate ; sealed held-out pass
  5  labels3     E_up / E_alt / E on the screen fold only (held-out ids loaded into the vendored guard)
  -  leakage     new + vendored features recomputed with data after t removed
  6  event3      matched event study grid, primary family (Holm), sensitivities, panels, R1a correlations, R1d
  7  verdict     mechanical BROKERAGE / TURNOVER / MIXED
  8  power       held-out MDE (event study vs pooled panel) -> held-out primary estimator
  9  predict3    grouped-CV delta-AUC, reported not claimed
  10 figs, audit, exports, confirm self-test, freeze (heldout_spec.json, last: it hashes all code)

Usage:
  uv run method.py              # full pipeline (~10 min on 4 CPUs)
  uv run method.py --from 5     # rerun from the labels step (inputs from earlier steps must exist)
"""
from __future__ import annotations

import os

os.environ.setdefault("OMP_NUM_THREADS", "1")

import argparse  # noqa: E402
import subprocess  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402
from pathlib import Path  # noqa: E402

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))
import common as K  # noqa: E402
from loguru import logger  # noqa: E402


def sub(args: list[str]) -> None:
    """Run a step as a subprocess (keeps the parent free of large objects; spawn pools inside)."""
    t0 = time.time()
    r = subprocess.run([sys.executable] + args, cwd=ROOT)
    if r.returncode != 0:
        raise RuntimeError(f"step {' '.join(args)} failed with code {r.returncode}")
    logger.info(f"step {' '.join(args)} done in {time.time() - t0:.0f}s")


@logger.catch(reraise=True)
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--from", dest="start", type=int, default=0)
    ap.add_argument("--workers", type=int, default=min(4, K.detect_cpus()))
    a = ap.parse_args()
    K.setup_logging("method")
    K.set_ram_limit(26)
    t0 = time.time()
    w = str(a.workers)
    steps = [
        (0, ["src/setup.py"]),
        (1, ["src/population.py"]),
        (2, ["src/prep3.py"]),
        (3, ["src/attach.py", "--modes", "full", "repro_code", "repro_data", "--workers", w]),
        (4, ["src/indicators3.py", "--modes", "repro_code", "repro_data", "full", "--workers", w]),
        (4, ["src/repro.py"]),
        (4, ["src/attach.py", "--modes", "sealed", "--years"] + [str(y) for y in range(2000, K.SPEC3["sealed_max_year"] + 1)]
         + ["--workers", w]),
        (4, ["src/indicators3.py", "--modes", "sealed", "--workers", w]),
        (5, ["src/labels3.py"]),
        (5, ["src/leakage.py"]),
        (6, ["src/event3.py"]),
        (7, ["src/verdict.py"]),
        (8, ["src/power.py"]),
        (9, ["src/predict3.py"]),
        (10, ["src/figs.py"]),
        (10, ["src/audit.py"]),
        (10, ["confirm_heldout.py", "--self-test-on-screen"]),
        (10, ["src/exports.py"]),
        (10, ["src/freeze.py"]),
    ]
    for k, args in steps:
        if k >= a.start:
            sub(args)
    logger.info(f"pipeline done in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
