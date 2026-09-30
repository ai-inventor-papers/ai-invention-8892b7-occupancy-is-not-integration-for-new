#!/usr/bin/env python3
"""RQ2 experiment orchestrator: how new concepts spread - diffusion types, community roles, expansion/diffusion timing.

Stages (src/*.py): prep -> attach -> indicators (reproduction gate) -> labels -> leiden_seeds -> typology (+ baselines) ->
roles -> leadlag -> patterns -> validation -> cases (+ figures) -> method_out (method_out.json, results_summary.json) ->
freeze (sealed/heldout_spec.json; LAST).

Usage:
  uv run method.py                 # all stages
  uv run method.py --stage typology roles
  uv run method.py --mini          # smoke test: 10 old + 10 new screen concepts, attach 2005-2012, compare with iteration 2
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ORDER = ["prep", "attach", "indicators", "labels", "leiden_seeds", "typology", "roles", "leadlag", "patterns", "validation",
         "cases", "method_out", "freeze"]


def run(stage: str, env: dict | None = None) -> float:
    t0 = time.time()
    r = subprocess.run([sys.executable, str(ROOT / "src" / f"{stage}.py")], cwd=ROOT / "src", env=env or os.environ.copy())
    if r.returncode != 0:
        raise SystemExit(f"stage {stage} failed (exit {r.returncode})")
    return time.time() - t0


def mini() -> None:
    env = dict(os.environ, AII_MINI="1")
    run("prep", env)
    code = ("import sys; sys.argv=['x']; import attach; attach.main(workers=4, years=list(range(2005, 2013)));"
            "import pandas as pd, numpy as np, json; from common import X3, WORK, RES, write_json;"
            "rows=[];\n"
            "for y in range(2005, 2013):\n"
            "  a=pd.read_parquet(WORK/'attach'/f'pool_metrics_y{y}.parquet'); b=pd.read_parquet(X3/'work'/'snapshots'/f'pool_metrics_y{y}.parquet')\n"
            "  m=a.merge(b,on='concept_id',suffixes=('','_x3'))\n"
            "  for c in ['strength','closure','wmz','P_raw','n_all']:\n"
            "    x=m[c].astype(float); z=m[c+'_x3'].astype(float); ok=np.isfinite(x)&np.isfinite(z)\n"
            "    rows.append(dict(year=y,col=c,n=int(ok.sum()),share_equal=float(np.mean(np.isclose(x[ok],z[ok],rtol=1e-6))) if ok.sum() else None))\n"
            "write_json(RES/'mini_comparison.json', rows); print(pd.DataFrame(rows).groupby('col').share_equal.mean())")
    t0 = time.time()
    r = subprocess.run([sys.executable, "-c", code], cwd=ROOT / "src", env=env)
    print(f"mini attach+compare exit {r.returncode} in {time.time() - t0:.0f}s")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", nargs="*", default=None)
    ap.add_argument("--mini", action="store_true")
    a = ap.parse_args()
    if a.mini:
        mini()
        return
    for st in a.stage or ORDER:
        secs = run(st)
        print(f"stage {st} done in {secs:.0f}s", flush=True)


if __name__ == "__main__":
    main()
