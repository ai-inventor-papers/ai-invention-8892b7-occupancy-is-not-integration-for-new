#!/usr/bin/env python3
"""RQ2-D1 screen test: does neighbourhood openness at t predict W2 = [t+1, t+5] disciplinary breadth gain?

Orchestrates the stages (all writes stay inside this repository):
  vendor      run the vendored iteration-2 unit tests + this repo's tests
  population  frozen MAIN/STRICT/SENSITIVITY population after the frozen replacement rule; sealed held-out ids
  prep        c-papers of all 426 concepts from the hydrated corpus; author index; denominators
  attach      attach pool concepts to exp_3's 25 prebuilt snapshots + ego-network openness (+ DS1 code-equality run)
  indicators  vendored per-(concept, year) indicators, reproduction gate vs exp_3, E_up labels
  openness    closure_res (R1a residualisation), constraint, effective size, xcomm; sealed held-out W1 file
  features    W1 baselines at t (level, volume, momentum, growing-edge breadth, burst, coherence, ...)
  outcomes    W2 outcomes Y1, Y1r, Y1r20, Y2, Y3, Y3b and the mediator (screen only, guarded)
  models      OLS + cluster bootstrap, grouped CV delta-R2, E_up subset, robustness grid, mediation, sanity checks
  power       MDE simulation at held-out size
  freeze      heldout_spec.json + sha256 + freeze log
  outputs     method_out.json, figures, results_summary.json
Usage: method.py --stage all | --stage prep attach ... [--mini]
"""
from __future__ import annotations

import argparse
import os
import sys

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_v, "1")  # small dense solves: BLAS threading is ~1000x slower here
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
if "--mini" in sys.argv:
    os.environ["AII_MINI"] = "1"

from loguru import logger  # noqa: E402

import common as K  # noqa: E402

STAGES = ["vendor", "population", "prep", "attach", "indicators", "openness", "features", "outcomes", "models",
          "power", "freeze", "outputs"]


def stage_vendor() -> None:
    import subprocess
    r = subprocess.run([sys.executable, "-m", "pytest", "-q", "vendor/tests", "tests"], cwd=K.WS,
                       capture_output=True, text=True)
    (K.LOGS / "pytest.log").write_text(r.stdout + r.stderr)
    logger.info(r.stdout.strip().splitlines()[-1] if r.stdout.strip() else r.stderr[-500:])
    if r.returncode != 0:
        raise RuntimeError("unit tests failed; see logs/pytest.log")


@logger.catch(reraise=True)
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", nargs="+", default=["all"])
    ap.add_argument("--mini", action="store_true", help="first 20 screen concepts (smoke run)")
    ap.add_argument("--workers", type=int, default=min(4, K.detect_cpus()))
    ap.add_argument("--boot", type=int, default=2000)
    a = ap.parse_args()
    K.setup_logging("method")
    K.set_ram_limit(24)
    stages = STAGES if "all" in a.stage else a.stage
    K.load_sealed_ids()
    for st in stages:
        t0 = time.time()
        logger.info(f"=== stage {st} ===")
        if st == "vendor":
            stage_vendor()
        elif st == "population":
            import population
            population.run()
        elif st == "prep":
            import prep
            prep.run()
        elif st == "attach":
            import attach
            attach.run(workers=a.workers)
            attach.run(cp_path=K.EXP3_CP, out_dir=K.WORK / "pool_metrics_ds1",
                       concept_ids=sorted(__import__("pandas").read_parquet(K.EXP3_POOL).concept_id), workers=a.workers)
        elif st == "indicators":
            import indicators
            indicators.run(workers=a.workers)
        elif st == "openness":
            import openness
            openness.run()
        elif st == "features":
            import features
            features.run(mini=a.mini)
        elif st == "outcomes":
            import outcomes
            outcomes.run(mini=a.mini)
        elif st == "models":
            import models
            models.run(boot=a.boot, mini=a.mini)
        elif st == "power":
            import power
            power.run(mini=a.mini)
        elif st == "freeze":
            import freeze
            freeze.run()
        elif st == "outputs":
            import outputs
            outputs.run()
        else:
            raise ValueError(st)
        logger.info(f"=== stage {st} done in {time.time() - t0:.1f}s (guard calls so far {K.GUARD_CALLS['n']}) ===")


if __name__ == "__main__":
    main()
