"""Leakage test (vendored pattern): for 5 random screen concept-years, recompute every new attachment column and the
vendored indicator columns with every c-paper after t removed; all must be identical to the stored values."""
from __future__ import annotations

import math

import numpy as np
import pandas as pd
from loguru import logger

import common as K

NEW = ["closure", "closure_persist", "persist_n", "n_ego", "constraint", "effsize", "efficiency", "cdeg_diag", "xc_obs",
       "xc_exp", "xc_excess", "wmz", "P_rar", "strength"]
VEND = ["log_vol3", "growth1", "growth3", "burst_state", "yrs_since_burst", "new_relation_rate", "novelty", "neigh_growth",
        "beta_sim_rar", "beta_sim_raw", "H", "RS", "subfield_count", "strength_growth", "closure_slope", "P_slope"]


def main(n: int = 5) -> dict:
    import stage_indicators as SI
    from attach import Snap, concept_block, light_graph
    from indicators3 import load_D, pid_map
    import json
    lab = pd.read_parquet(K.RES / "labels" / "labels_screen.parquet")
    ind = pd.read_parquet(K.RES / "indicators" / "concept_year_indicators_hydrated.parquet")
    cp = pd.read_parquet(K.WORK / "cp_active.parquet")
    pool = pd.read_parquet(K.WORK / "pool_active.parquet").set_index("concept_id")
    pm_dir = K.WORK / "attach" / "full"
    rng = np.random.default_rng(123)
    picks = lab.iloc[rng.choice(len(lab), size=n, replace=False)]
    D, sidx = load_D()
    pmap = pid_map()
    totals = json.loads((K.WORK / "totals.json").read_text())
    cases = []
    for r in picks.itertuples():
        c, t = r.concept_id, int(r.t)
        trunc = cp[(cp.concept_id == c) & (cp.year <= t)]
        g = Snap(t)
        sub = trunc[trunc.year >= t - 2]
        prv = trunc[(trunc.year >= t - 3) & (trunc.year <= t - 1)]  # the y-1 window (y-3..y-1)
        row, _ = concept_block(c, sub, g, t, light_graph(t - 1), prv)
        stored = ind[(ind.concept_id == c) & (ind.year == t)].iloc[0]
        bad = []
        for f in NEW:
            a, b = float(row[f]), float(stored[f])
            if not ((np.isnan(a) and np.isnan(b)) or math.isclose(a, b, rel_tol=1e-9, abs_tol=1e-12)):
                bad.append((f, a, b))
        pm = pd.concat([pd.read_parquet(pm_dir / f"pool_metrics_v3_y{y}.parquet") for y in range(2000, t + 1)])
        rows, _ = SI.concept_indicators(c, float(pool.loc[c, "F"]), trunc, pm[pm.concept_id == c], pmap, totals, D, sidx, max_year=t)
        tr = pd.DataFrame(rows).set_index("year").loc[t]
        for f in VEND:
            a, b = float(tr[f]), float(stored[f])
            if not ((np.isnan(a) and np.isnan(b)) or math.isclose(a, b, rel_tol=1e-6, abs_tol=1e-9)):
                bad.append((f, a, b))
        cases.append(dict(concept_id=c, t=t, n_features=len(NEW) + len(VEND), mismatches=bad))
        if bad:
            raise AssertionError(f"LEAKAGE at ({c},{t}): {bad[:5]}")
    out = dict(passed=True, cases=cases, note="closure_resT / _res use betas fitted on the pooled screen panel (label-free; "
               "coefficient look-ahead declared); prediction refits R1a inside training folds")
    K.write_json(K.RES / "leakage_test.json", out)
    logger.info(f"leakage test passed on {len(cases)} concept-years x {len(NEW) + len(VEND)} features")
    return out


if __name__ == "__main__":
    K.setup_logging("leakage")
    main()
