"""Step 5: openness features at t (W1 only) and the pre-outcome row-count decision.

closure_res (PRIMARY, R1a): OLS residual of the top-20 Chung-Lu closure log-ratio on
  1 + new_relation_rate + novelty + beta_sim_rar + log_vol3 + age + H_W1,
fit once on ALL screen concept-years with age 3..8, year <= 2015 and finite regressors (label-blind; the fit rows
do not depend on the population filter, so every population in the robustness grid shares one residualisation).
The frozen coefficients are stored for iteration 4, which applies them to the held-out rows.
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
from loguru import logger

import common as K
from common import AGES, OUT, SEALED, T_MAX_SCREEN, WORK

import lib_metrics as lm

ODIR = OUT / "openness"
R1A = ["new_relation_rate", "novelty", "beta_sim_rar", "log_vol3", "age"]
OPEN_VARS = ["closure_res", "closure_res_imp", "closure_res_H3", "closure_unres", "closure_res_w1mean", "constraint",
             "esize_norm", "xcomm_exc"]


def h_w1_table(cp: pd.DataFrame, keys: pd.DataFrame) -> pd.Series:
    """Paper-weighted Shannon over known subfields of c-papers in [t-5, t] for each (concept_id, year) in keys."""
    known = cp[cp.subfield >= 0]
    g = {c: (s.year.values, s.subfield.values) for c, s in known.groupby("concept_id")}
    out = []
    for c, t in zip(keys.concept_id, keys.year):
        yrs, sub = g.get(c, (np.zeros(0), np.zeros(0)))
        m = (yrs >= t - 5) & (yrs <= t)
        out.append(lm.shannon(np.unique(sub[m], return_counts=True)[1]) if m.any() else np.nan)
    return pd.Series(out, index=keys.index)


def fit_r1a(df: pd.DataFrame, fit_mask: np.ndarray, hcol: str, impute: bool = False) -> tuple[np.ndarray, dict]:
    d = df.copy()
    cols = R1A + [hcol]
    info: dict = dict(regressors=["const"] + cols, H_column=hcol, imputed=impute)
    if impute:
        med = float(d.loc[fit_mask & d.beta_sim_rar.notna(), "beta_sim_rar"].median())
        d["beta_sim_missing"] = d.beta_sim_rar.isna().astype(float)
        d["beta_sim_rar"] = d.beta_sim_rar.fillna(med)
        cols = cols + ["beta_sim_missing"]
        info.update(regressors=["const"] + cols, beta_sim_median=med)
    X = np.column_stack([np.ones(len(d))] + [d[c].astype(float).values for c in cols])
    y = d.closure.astype(float).values
    ok = fit_mask & np.isfinite(X).all(1) & np.isfinite(y)
    beta, *_ = np.linalg.lstsq(X[ok], y[ok], rcond=None)
    fin = np.isfinite(X).all(1) & np.isfinite(y)
    res = np.full(len(d), np.nan)
    res[fin] = y[fin] - X[fin] @ beta
    r2 = 1 - np.sum(res[ok] ** 2) / np.sum((y[ok] - y[ok].mean()) ** 2)
    info.update(beta=dict(zip(info["regressors"], beta.tolist())), n_fit_rows=int(ok.sum()),
                n_fit_concepts=int(d.loc[ok, "concept_id"].nunique()), r2=float(r2),
                mean_resid_fit_rows=float(res[ok].mean()))
    return res, info


def apply_r1a(df: pd.DataFrame, info: dict) -> np.ndarray:
    """Apply frozen R1a coefficients (iteration 4 uses this on held-out rows)."""
    d = df.copy()
    if info.get("imputed"):
        d["beta_sim_missing"] = d.beta_sim_rar.isna().astype(float)
        d["beta_sim_rar"] = d.beta_sim_rar.fillna(info["beta_sim_median"])
    regs = info["regressors"]
    X = np.column_stack([np.ones(len(d))] + [d[c].astype(float).values for c in regs[1:]])
    b = np.array([info["beta"][r] for r in regs])
    y = d.closure.astype(float).values
    out = np.full(len(d), np.nan)
    fin = np.isfinite(X).all(1) & np.isfinite(y)
    out[fin] = y[fin] - X[fin] @ b
    return out


def run() -> None:
    ODIR.mkdir(parents=True, exist_ok=True)
    heldout = K.load_sealed_ids()
    ind = pd.read_parquet(OUT / "indicators" / "concept_year_indicators_hyd.parquet")
    cp = pd.read_parquet(WORK / "cp.parquet", columns=["concept_id", "year", "subfield"])
    ind = ind[ind.fold != "reference"].copy()   # reference arm is never an analysis unit here
    ind["H_W1"] = h_w1_table(cp, ind)
    fit_mask = ((ind.fold == "screen") & ind.age.between(*AGES) & (ind.year <= T_MAX_SCREEN)).values
    ind["closure_res"], info = fit_r1a(ind, fit_mask, "H_W1")
    ind["closure_res_H3"], info_h3 = fit_r1a(ind, fit_mask, "H")
    ind["closure_res_imp"], info_imp = fit_r1a(ind, fit_mask, "H_W1", impute=True)
    assert np.allclose(apply_r1a(ind, info), ind.closure_res.values, equal_nan=True)
    ind["closure_unres"] = ind.closure
    ind = ind.sort_values(["concept_id", "year"]).reset_index(drop=True)
    ind["closure_res_w1mean"] = ind.groupby("concept_id").closure_res.transform(lambda s: s.rolling(3, min_periods=1).mean())
    elig = fit_mask  # screen, age 3..8, t <= 2015 (the unit rows of the D1 models)
    elig = ((ind.fold == "screen") & ind.age.between(*AGES) & (ind.year <= T_MAX_SCREEN)).values
    scal = {}
    for v in OPEN_VARS:
        x = ind.loc[elig, v].astype(float)
        mu, sd = float(x.mean()), float(x.std(ddof=1))
        scal[v] = dict(mean=mu, sd=sd, n=int(x.notna().sum()))
        ind[f"{v}_z"] = (ind[v] - mu) / sd
    K.write_json(ODIR / "r1a_fit.json", dict(primary=info, H3_variant=info_h3, imputed_variant=info_imp,
                                              z_scaling=scal, fit_rows_rule="fold==screen & age in [3,8] & year<=2015 & finite"))
    logger.info(f"R1a fit: n={info['n_fit_rows']} rows / {info['n_fit_concepts']} concepts, R2={info['r2']:.3f}; "
                f"beta={ {k: round(v, 3) for k, v in info['beta'].items()} }")
    cols = ["concept_id", "year", "fold", "in_MAIN", "in_STRICT", "age", "closure", "closure_res", "closure_res_H3",
            "closure_res_imp", "closure_res_w1mean", "closure_unres", "constraint", "esize", "esize_norm", "xcomm_exc",
            "xcomm_obs", "ego_deg", "H_W1"] + [f"{v}_z" for v in OPEN_VARS]
    out = ind[ind.fold == "screen"][cols].rename(columns={"year": "t"})
    out.to_parquet(ODIR / "openness_ct.parquet", index=False)
    ho = ind[ind.concept_id.isin(heldout)][cols].rename(columns={"year": "t"})
    assert ho.t.max() <= T_MAX_SCREEN
    ho.to_parquet(SEALED / "openness_ct_heldout.parquet", index=False)
    (SEALED / "openness_ct_heldout.sha256").write_text(K.sha256_file(SEALED / "openness_ct_heldout.parquet") + "\n")
    ind.to_parquet(WORK / "indicators_open.parquet", index=False)

    # ---- F3 decision BEFORE any outcome is computed
    m = elig & ind.in_MAIN.values
    cc = m & ind.closure_res.notna().values
    n_rows, n_con = int(cc.sum()), int(ind.loc[cc, "concept_id"].nunique())
    f3 = bool(n_con < 150 or n_rows < 500)
    dec = dict(created_before_outcomes=True, main_screen_eligible_rows=int(m.sum()),
               main_screen_eligible_concepts=int(ind.loc[m, "concept_id"].nunique()),
               closure_res_complete_rows=n_rows, closure_res_complete_concepts=n_con,
               closure_res_imp_complete_rows=int((m & ind.closure_res_imp.notna().values).sum()),
               F3_rule="if complete-case closure_res leaves < 150 screen MAIN concepts or < 500 rows -> closure_res_imp co-primary",
               F3_triggered=f3,
               coprimary_rule=("D1_SUPPORTED_SCREEN requires the pre-declared rule to hold for closure_res AND for "
                               "closure_res_imp on the same outcome (conservative conjunction; no forking)") if f3 else None)
    K.write_json(OUT / "d1" / "rowcount_decision.json", dec)
    logger.info(f"row-count decision: {dec}")
