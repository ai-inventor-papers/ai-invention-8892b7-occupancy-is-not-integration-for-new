#!/usr/bin/env python3
"""STEP 0e: minimum detectable effects, written BEFORE any held-out/MeSH outcome is read."""
import json
import os, math, sys
from pathlib import Path
import numpy as np, pandas as pd
from statsmodels.stats.power import GofChisquarePower
from loguru import logger
WS = Path(__file__).resolve().parents[1]
LOOP = Path(os.environ.get("AII_LOOP_ROOT", WS.parents[2])).resolve()  # dependency artifacts: <LOOP>/iter_N/gen_art/<artifact>
E8 = WS / "exp8_frozen"; E7 = LOOP / "round-3/experiment-7/src"
logger.remove(); logger.add(sys.stdout, level="INFO")

def wilson_hw(p, n, z=1.959964):
    den = 1 + z*z/n
    return z*math.sqrt(p*(1-p)/n + z*z/(4*n*n))/den

@logger.catch(reraise=True)
def main():
    spec = json.loads((E8/"sealed/heldout_spec.json").read_text())
    sc = spec["screen_reference"]["E1_cluster_shares"]
    n_sc = sum(v["n"] for v in sc.values())
    out = {"note": "computed before any held-out or MeSH outcome was read", "screen_n": n_sc,
           "heldout_n_ids_spec": 119, "heldout_n_main_expected": 100}
    out["wilson_halfwidth"] = {k: {str(n): wilson_hw(v["share"], n) for n in (100, 119, 191, 302)} for k, v in sc.items()}
    gp = GofChisquarePower()
    out["chi2_mde_w_80pct"] = {f"df{df}": {str(n): float(gp.solve_power(effect_size=None, nobs=n, alpha=0.05, power=0.8, n_bins=df+1))
                                for n in (100, 191, 202, 302)} for df in (1, 2, 3, 4, 5)}
    out["chi2_mde_note"] = "Cramer's V = w/sqrt(min(r,c)-1); with 2 types V = w. Screen origin V=0.28 is below the held-out-only MDE at df>=2."
    n_both_screen, n_screen_ll = 16, 202
    exp_nb = n_both_screen / n_screen_ll * 100
    out["leadlag"] = {"expected_n_both_heldout": exp_nb, "wilson_halfwidth_at_0.94": wilson_hw(0.94, max(1, round(exp_nb))),
                      "expected_n_both_pooled": n_both_screen + exp_nb}
    # A_cont type-gap MDE: concept-cluster simulation from the screen A_cont variance
    ev = pd.read_parquet(E7/"results/screen_events_with_outcomes.parquet")
    ev = ev[ev.MAIN & (ev.n_partners_distinct >= 5)].dropna(subset=["A_cont"])
    sd = ev.A_cont.std()
    cm = ev.groupby("concept_id").A_cont.agg(["mean", "size"])
    rng = np.random.default_rng(0)
    res = {}
    for n_c in (93, 100):
        for delta_sd in (0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.8):
            rej = 0
            for _ in range(500):
                idx = rng.integers(0, len(cm), n_c)
                m = cm["mean"].to_numpy()[idx].copy()
                broad = rng.random(n_c) < 0.33
                m[broad] += delta_sd * sd
                a, b = m[broad], m[~broad]
                if len(a) < 2 or len(b) < 2: continue
                se = math.sqrt(a.var(ddof=1)/len(a) + b.var(ddof=1)/len(b))
                rej += abs((a.mean()-b.mean())/se) > 1.96
            res[f"n{n_c}_d{delta_sd}"] = rej/500
        mde = next((d for d in (0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.8) if res[f"n{n_c}_d{d}"] >= 0.8), None)
        res[f"MDE_sd_n{n_c}"] = mde
    out["Acont_typegap_sim"] = {"entry_sd_Acont": sd, "concept_mean_sd": float(cm["mean"].std()), "power": res,
                                "method": "500 draws per cell; resample screen concept means, 33% labelled BROAD, shift by delta*SD; Welch z test on concept means"}
    (WS/"results/power_mde.json").write_text(json.dumps(out, indent=1))
    logger.info(json.dumps(out)[:1500])
main()
