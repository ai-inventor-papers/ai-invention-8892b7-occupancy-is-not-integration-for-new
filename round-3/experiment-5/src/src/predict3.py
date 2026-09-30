"""Step 9: prediction of E_up from features <= t, REPORTED NOT CLAIMED.

Rows: screen MAIN eligible concept-years, t in 2008-2015, ages 3-8. Grouped (by concept) stratified 5-fold CV x 5 seeds;
vendored L2 logistic (StandardScaler + LogisticRegression C=1, balanced) and vendored median-fill + NA-dummy prep.
BASE = vendored BASELINE (frequency/burst + degree/centrality + entropy families + band/origin/age).
FULL = BASE + closure_resT + constraint; closure_resT is RE-FIT inside each training fold (training concepts' indicator
rows only) and applied to the test fold. FULL_R1bc = BASE + closure_persist + xc_excess (secondary).
Delta-AUC on seed-averaged out-of-fold scores with a concept-bootstrap CI; 20 label shuffles as a control.
"""
from __future__ import annotations

import json
import warnings

import numpy as np
import pandas as pd
from loguru import logger
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedGroupKFold

import common as K

warnings.filterwarnings("ignore")


def build(lab: pd.DataFrame, ind: pd.DataFrame) -> pd.DataFrame:
    import analysis_predict as AP
    cfg = K.SPEC3["prediction"]
    l = lab[lab.MAIN.astype(bool) & (lab.t >= cfg["t_range"][0]) & (lab.t <= cfg["t_range"][1]) &
            (lab.age >= cfg["ages"][0]) & (lab.age <= cfg["ages"][1])].copy()
    keep = ["concept_id", "t", "age", "F", "F_band", "origin_group", "E_up", "old_new", "route", "group_E_up", "onset_E_up"]
    d = AP.build_rows(l[keep], ind.drop(columns=["closure_resT", "closure_resT_cc", "closure_resT_raw", "route", "old_new",
                                                  "hydration_batch", "MAIN", "STRICT", "SENS"], errors="ignore"))
    return d.sort_values(["concept_id", "t"]).reset_index(drop=True)


def fold_r1a(ind: pd.DataFrame, train_concepts: set, d: pd.DataFrame) -> np.ndarray:
    """R1a OLS refit on the training concepts' screen indicator rows (age >= -2), applied to the prediction rows."""
    from indicators3 import r1a_apply, r1a_fit
    sub = ind[ind.concept_id.isin(train_concepts)].reset_index(drop=True)
    fit = r1a_fit(sub.drop(columns=[c for c in ("E", "E_up") if c in sub.columns]),
                  ((sub.fold == "screen") & (sub.age >= -2)).values, K.SPEC3["r1a_covariates"], True)
    x = d[["closure"] + K.SPEC3["r1a_covariates"]].copy()
    return r1a_apply(x, fit)


def cv_scores(d: pd.DataFrame, ind: pd.DataFrame, feats: dict, y: np.ndarray, seed: int) -> dict:
    import analysis_predict as AP
    cfg = K.SPEC3["prediction"]
    groups = d.concept_id.values
    out = {k: np.full(len(d), np.nan) for k in feats}
    skf = StratifiedGroupKFold(n_splits=cfg["folds"], shuffle=True, random_state=seed)
    for tr, te in skf.split(d, y, groups):
        dd = d.copy()
        need_r1a = any("closure_resT" in f for f in feats.values())
        if need_r1a:
            dd["closure_resT"] = fold_r1a(ind, set(d.concept_id.values[tr]), d)
        for name, fs in feats.items():
            if len(np.unique(y[tr])) < 2:
                continue
            Xtr, Xte = AP._prep(dd.iloc[tr], dd.iloc[te], fs)
            clf = AP._clf("logit")
            clf.fit(Xtr, y[tr])
            out[name][te] = clf.predict_proba(Xte)[:, 1]
    return out


def boot_delta(y: np.ndarray, a: np.ndarray, b: np.ndarray, groups: np.ndarray, B: int, seed: int) -> list:
    uc = np.unique(groups)
    rows_by = {c: np.where(groups == c)[0] for c in uc}
    rng = np.random.default_rng(seed)
    out = []
    for _ in range(B):
        ii = np.concatenate([rows_by[c] for c in rng.choice(uc, len(uc), replace=True)])
        if len(np.unique(y[ii])) < 2:
            continue
        out.append(roc_auc_score(y[ii], b[ii]) - roc_auc_score(y[ii], a[ii]))
    return np.percentile(out, [2.5, 97.5]).tolist()


def main() -> tuple[dict, pd.DataFrame]:
    import analysis_predict as AP
    from labels3 import guard
    guard()
    cfg = K.SPEC3["prediction"]
    ind = pd.read_parquet(K.RES / "indicators" / "concept_year_indicators_hydrated.parquet")
    lab = pd.read_parquet(K.RES / "labels" / "labels_screen.parquet")
    d = build(lab, ind)
    y = d.E_up.astype(int).values
    base = AP.FEATURE_SETS["BASELINE"]
    feats = dict(BASE=base, FULL=base + ["closure_resT", "constraint"], FULL_R1bc=base + ["closure_persist", "xc_excess"],
                 A_freq_burst=AP.FEATURE_SETS["A_freq_burst"], OPEN_only=["closure_resT", "constraint", "closure_persist",
                                                                         "xc_excess"] + AP.EXTRA)
    per_seed = [cv_scores(d, ind, feats, y, s) for s in cfg["seeds"]]
    avg = {k: np.nanmean(np.vstack([p[k] for p in per_seed]), axis=0) for k in feats}
    groups = d.concept_id.values
    res = dict(n_rows=len(d), n_pos=int(y.sum()), n_concepts=int(d.concept_id.nunique()),
               auc={k: float(roc_auc_score(y, v)) for k, v in avg.items()},
               auc_per_seed={k: [float(roc_auc_score(y, p[k])) for p in per_seed] for k in feats})
    res["delta_FULL_vs_BASE"] = dict(delta=res["auc"]["FULL"] - res["auc"]["BASE"],
                                     ci=boot_delta(y, avg["BASE"], avg["FULL"], groups, cfg["boot"], 31))
    res["delta_FULL_R1bc_vs_BASE"] = dict(delta=res["auc"]["FULL_R1bc"] - res["auc"]["BASE"],
                                          ci=boot_delta(y, avg["BASE"], avg["FULL_R1bc"], groups, cfg["boot"], 32))
    # label-shuffle control (permute labels across concepts, keep each concept's label vector)
    rng = np.random.default_rng(K.SPEC3["seeds"]["cv"])
    sh = []
    uc = d.concept_id.unique()
    for i in range(cfg["shuffles"]):
        perm = dict(zip(uc, rng.permutation(uc)))
        # each concept takes the label sequence of another concept (aligned by rank of t; padded with 0)
        ys = np.zeros(len(d), int)
        byc = {c: y[d.concept_id.values == c] for c in uc}
        for c in uc:
            idx = np.where(d.concept_id.values == c)[0]
            src = byc[perm[c]]
            ys[idx] = np.resize(src, len(idx)) if len(src) else 0
        if len(np.unique(ys)) < 2:
            continue
        s = cv_scores(d, ind, dict(BASE=base, FULL=feats["FULL"]), ys, 100 + i)
        sh.append(roc_auc_score(ys, s["FULL"]) - roc_auc_score(ys, s["BASE"]))
    res["label_shuffle"] = dict(n=len(sh), mean_delta=float(np.mean(sh)), sd_delta=float(np.std(sh)), deltas=sh)
    res["note"] = ("REPORTED, NOT CLAIMED. E_up is a post-hoc label; grouped CV (not rolling-origin); residualisation refit "
                   "inside training folds (training concepts only).")
    preds = d[["concept_id", "t", "age", "E_up", "old_new", "route", "group_E_up", "onset_E_up"]].copy()
    for k, v in avg.items():
        preds[f"score_{k}"] = v
    (K.RES / "prediction").mkdir(parents=True, exist_ok=True)
    preds.to_parquet(K.RES / "prediction" / "predictions.parquet", index=False)
    K.write_json(K.RES / "prediction.json", res)
    logger.info(f"prediction: AUC {res['auc']}; dFULL {res['delta_FULL_vs_BASE']}; shuffle {res['label_shuffle']['mean_delta']:.3f}")
    return res, d.assign(**{f"score_{k}": v for k, v in avg.items()})


if __name__ == "__main__":
    K.setup_logging("predict3")
    main()
