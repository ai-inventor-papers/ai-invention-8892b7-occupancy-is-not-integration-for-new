#!/usr/bin/env python3
"""Independent re-derivation of the D3 primary statistic (no d3core code): X and Y rebuilt from the raw parquet files
with plain loops, partial Spearman via statsmodels OLS residuals, and a pingouin-free closed-form check against
the analytic partial correlation from the inverse correlation matrix. Writes results/d3/audit_d3.json."""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats

WS = Path(__file__).resolve().parent
LOOP = WS.parents[2]
E6 = LOOP / "round-3" / "." / "gen_art_experiment_6"
E7 = LOOP / "round-3" / "." / "gen_art_experiment_7"


def rebuild(fold: str) -> pd.DataFrame:
    pop = pd.read_parquet(WS / "deps_run" / "exp5" / "work" / "population.parquet")
    pop = pop[(pop.arm == "main") & (pop.fold == fold) & pop.MAIN]
    F = dict(zip(pop.concept_id, pop.F))
    o = pd.read_parquet(E6 / ("results/openness/openness_ct.parquet" if fold == "screen" else "sealed/openness_ct_heldout.parquet"))
    ev = pd.read_parquet(E7 / ("results/features_screen.parquet" if fold == "screen" else "sealed/heldout_features.parquet"))
    X, Y, N = {}, {}, {}
    for c, t, v in zip(o.concept_id, o.t, o.closure):
        if c in F and 3 <= t - F[c] <= 5 and t <= 2015 and v == v:
            X.setdefault(c, []).append(v)
    for c, arm, kw5, e, a in zip(ev.concept_id, ev.arm, ev.kw5, ev.e, ev.A_cont):
        if c in F and arm == "main" and kw5 and e >= F[c] + 6 and a == a:
            Y.setdefault(c, []).append(a)
    rows = [dict(concept_id=c, X=float(np.mean(X[c])), Y=float(np.mean(Y[c])), n_events=len(Y[c])) for c in F if c in X and c in Y]
    d = pd.DataFrame(rows)
    mine = pd.read_csv(WS / "results" / "d3" / f"d3_concepts_{fold}.csv").set_index("concept_id")
    d["log_vol_early"] = d.concept_id.map(mine.log_vol_early)
    d["origin5"] = d.concept_id.map(mine.origin5)
    d["X_mine"], d["Y_mine"] = d.concept_id.map(mine.X), d.concept_id.map(mine.Y)
    return d


def partial(d: pd.DataFrame) -> tuple[float, float]:
    g = d.origin5.copy()
    vc = g.value_counts()
    g[g.isin([k for k, v in vc.items() if v < 5])] = "Other"
    vc = g.value_counts()
    if "Other" in vc and vc["Other"] < 5:
        g[g == "Other"] = vc.index[0]
    Z = pd.get_dummies(g, drop_first=False).astype(float)
    Z = Z.drop(columns=[g.value_counts().index[0]])
    Z["rv"] = stats.rankdata(d.log_vol_early)
    Z["ln"] = np.log(d.n_events)
    Z = sm.add_constant(Z)
    rx = sm.OLS(stats.rankdata(d.X), Z).fit().resid
    ry = sm.OLS(stats.rankdata(d.Y), Z).fit().resid
    r1 = float(np.corrcoef(rx, ry)[0, 1])
    # analytic partial correlation via the precision matrix of [rankX, rankY, Z(no const)]
    M = np.column_stack([stats.rankdata(d.X), stats.rankdata(d.Y), Z.drop(columns="const").values])
    P = np.linalg.pinv(np.corrcoef(M, rowvar=False))
    r2 = float(-P[0, 1] / math.sqrt(P[0, 0] * P[1, 1]))
    return r1, r2


def main() -> None:
    res = json.loads((WS / "results" / "d3" / "d3_results.json").read_text())
    out = {}
    for fold in ("screen", "heldout"):
        d = rebuild(fold)
        r_ols, r_prec = partial(d)
        out[fold] = dict(n=len(d), n_reported=res["primary"][fold]["n"],
                         max_abs_dX=float((d.X - d.X_mine).abs().max()), max_abs_dY=float((d.Y - d.Y_mine).abs().max()),
                         partial_rho_ols=r_ols, partial_rho_precision=r_prec, partial_rho_reported=res["primary"][fold]["partial_rho"],
                         abs_diff=abs(r_ols - res["primary"][fold]["partial_rho"]),
                         raw_rho=float(stats.spearmanr(d.X, d.Y).statistic), raw_rho_reported=res["primary"][fold]["raw_rho"])
        out[fold]["pass"] = bool(out[fold]["n"] == out[fold]["n_reported"] and out[fold]["abs_diff"] < 1e-9
                                 and out[fold]["max_abs_dX"] < 1e-12 and out[fold]["max_abs_dY"] < 1e-12)
    (WS / "results" / "d3" / "audit_d3.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
