#!/usr/bin/env python3
"""Independent re-derivation of the headline numbers through separate code paths.

(1) the 3 primary closure_res coefficients: statsmodels formula API (C() dummies) vs the pipeline's numpy lstsq
    -> must agree to 1e-8; (2) Y1r for 20 random rows by a plain-Python loop (own Shannon, own sampling loop with
    the same seed stream) vs results/d1/outcomes_ct.parquet -> must agree to 1e-6;
(3) every headline number in results_summary.json is re-read from the result files it came from.
Writes results/audit_rederive.json and exits non-zero on any mismatch.
"""
from __future__ import annotations

import json
import math
import os
import sys
from pathlib import Path

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_v, "1")
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import statsmodels.formula.api as smf  # noqa: E402
from loguru import logger  # noqa: E402

import common as K  # noqa: E402
import lib_metrics as lm  # noqa: E402

NUM = ["H_W1", "n_active_W1", "log_vol_W1", "momentum", "GEB", "burst_state", "rafols_coh_f", "coh_missing", "P_rar_f",
       "P_rar_missing"]


def plain_shannon(xs) -> float:
    counts: dict = {}
    for x in xs:
        counts[x] = counts.get(x, 0) + 1
    n = sum(counts.values())
    return -sum((c / n) * math.log(c / n) for c in counts.values())


def main() -> None:
    K.setup_logging("audit_rederive")
    out = dict(coefficients=[], y1r=[], summary_checks=[])
    ok = True
    panel = pd.read_parquet(ROOT / "results" / "d1" / "panel_ct.parquet")
    prim = pd.read_csv(ROOT / "results" / "d1" / "coef_table_primary.csv")
    d = panel[panel.in_MAIN].copy()
    d["t_s"] = d.t.astype(str)
    for y in ["Y1r", "Y2", "log1p_Y3"]:
        m = d.dropna(subset=[y, "closure_res_z"] + NUM)
        f = f"{y} ~ closure_res_z + " + " + ".join(NUM) + " + C(origin_group) + C(F_band) + C(route) + C(t_s)"
        fit = smf.ols(f, data=m).fit(cov_type="cluster", cov_kwds={"groups": pd.factorize(m.concept_id)[0]})
        b_sm = float(fit.params["closure_res_z"])
        # shuffled-outcome control: the same cluster-robust test on permuted Y must reject at ~5%, not more
        rng = np.random.default_rng(123)
        rej = 0
        for _ in range(200):
            ms = m.assign(**{y: rng.permutation(m[y].values)})
            ps = smf.ols(f, data=ms).fit(cov_type="cluster", cov_kwds={"groups": pd.factorize(ms.concept_id)[0]}).pvalues["closure_res_z"]
            rej += int(ps < 0.05)
        out.setdefault("shuffled_outcome_control", []).append(dict(outcome=y, real_p_cluster=float(fit.pvalues["closure_res_z"]),
                                                                   shuffled_rejection_rate=rej / 200))
        ok &= rej / 200 <= 0.10
        b_pipe = float(prim[(prim.openness == "closure_res_z") & (prim.outcome == y)].coef.iloc[0])
        good = abs(b_sm - b_pipe) < 1e-8
        ok &= good
        out["coefficients"].append(dict(outcome=y, statsmodels=b_sm, pipeline=b_pipe, abs_diff=abs(b_sm - b_pipe), match=good))
    # mediation indirect effect (Y3) by statsmodels formulas: a (M on X) times b (Y on X + M)
    med = json.loads((ROOT / "results" / "d1" / "mediation.json").read_text())["closure_res_z"]["per_outcome"]["log1p_Y3"]
    mm = d.dropna(subset=["log1p_Y3", "closure_res_z", "M_W2"] + NUM)
    rhs = " + ".join(NUM) + " + C(origin_group) + C(F_band) + C(route) + C(t_s)"
    a = smf.ols("M_W2 ~ closure_res_z + " + rhs, data=mm).fit().params["closure_res_z"]
    b = smf.ols("log1p_Y3 ~ closure_res_z + M_W2 + " + rhs, data=mm).fit().params["M_W2"]
    good = abs(a * b - med["indirect_ab"]["est"]) < 1e-8
    ok &= good
    out["mediation_indirect_Y3"] = dict(statsmodels=float(a * b), pipeline=med["indirect_ab"]["est"], match=good)
    # Y1r by a plain loop
    O = pd.read_parquet(ROOT / "results" / "d1" / "outcomes_ct.parquet")
    cp = pd.read_parquet(K.WORK / "cp.parquet", columns=["concept_id", "year", "subfield"])
    rows = O[O.Y1r.notna()].sample(20, random_state=7)
    for r in rows.itertuples(index=False):
        g = cp[(cp.concept_id == r.concept_id) & (cp.subfield >= 0)]
        s1 = g.subfield.values[((g.year >= r.t - 5) & (g.year <= r.t)).values]
        s2 = g.subfield.values[((g.year >= r.t + 1) & (g.year <= r.t + 5)).values]
        n = min(len(s1), len(s2))
        rng = np.random.default_rng(lm.stable_seed(r.concept_id, r.t, "Y1r"))
        acc = 0.0
        for _ in range(200):
            i2 = rng.choice(len(s2), n, replace=False)
            i1 = rng.choice(len(s1), n, replace=False)
            acc += plain_shannon([s2[i] for i in i2]) - plain_shannon([s1[i] for i in i1])
        v = acc / 200
        good = abs(v - r.Y1r) < 1e-6
        ok &= good
        out["y1r"].append(dict(concept_id=r.concept_id, t=int(r.t), loop=v, pipeline=float(r.Y1r), match=good))
    # headline numbers in results_summary.json vs source files
    summ = json.loads((ROOT / "results_summary.json").read_text())
    ver = json.loads((ROOT / "results" / "d1" / "verdict.json").read_text())
    rep = json.loads((ROOT / "results" / "reproduction" / "reproduction_check.json").read_text())
    for name, a, b in [("verdict", summ["verdict"], ver["verdict"]),
                       ("r_closure_hydrated", summ["reproduction"]["r_closure_hydrated"], rep["r_closure_ds5"])]:
        good = a == b
        ok &= good
        out["summary_checks"].append(dict(item=name, summary=a, source=b, match=good))
    for rec in summ["primary_estimates"]:
        src = prim[(prim.openness == rec["openness"]) & (prim.outcome == rec["outcome"])].iloc[0]
        good = abs(rec["coef"] - src.coef) < 1e-12
        ok &= good
        out["summary_checks"].append(dict(item=f"coef {rec['openness']} {rec['outcome']}", match=good))
    out["all_match"] = bool(ok)
    K.write_json(ROOT / "results" / "audit_rederive.json", out)
    logger.info(f"audit: all_match={ok}")
    if not ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
