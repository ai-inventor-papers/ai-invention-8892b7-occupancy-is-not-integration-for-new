"""Stage 7: rolling-origin prediction of emergence (E), subfield-count gain and centrality gain.

Features use data <= t only. Baselines (frequency/burst, degree/centrality growth, entropy growth) and the
precursor-augmented FULL model share model class, training rows and regularisation.
Primary: L2 logistic (C=1, balanced); secondary: HistGradientBoosting. Concept-bootstrap CIs for delta-AUC / delta-R2.
"""
from __future__ import annotations

import warnings

import numpy as np
import pandas as pd
from loguru import logger
from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import average_precision_score, r2_score, roc_auc_score
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

import config as C

S = C.SPEC
warnings.filterwarnings("ignore", category=UserWarning)

BASE_A = ["log_vol3", "growth1", "growth3", "burst_state", "yrs_since_burst"]
BASE_B = ["log_strength", "strength_growth", "PA", "btw_pct", "btw_change", "pct"]
BASE_C = ["subfield_count", "H", "RS", "subfield_count_growth3", "H_growth3", "RS_growth3"]
EXTRA = ["age", "band_2005_07", "band_2008_11", "og_F31", "og_F17", "og_D3"]
PREC = ["accretion_shift_rar", "sne_share_rar", "beta_sim_rar", "closure", "closure_slope", "P_rar", "P_slope", "wmz"]
FEATURE_SETS = {"A_freq_burst": BASE_A, "B_degree_centrality": BASE_B, "C_entropy": BASE_C,
                "BASELINE": BASE_A + BASE_B + BASE_C + EXTRA, "PREC_only": PREC + EXTRA,
                "FULL": BASE_A + BASE_B + BASE_C + EXTRA + PREC}


def build_rows(lab: pd.DataFrame, ind: pd.DataFrame) -> pd.DataFrame:
    x = ind.copy()
    x["log_strength"] = np.log1p(x.strength.fillna(0))
    d = lab.merge(x.drop(columns=["age", "F", "F_band", "origin_group", "sense_check_fail", "fold"], errors="ignore"),
                  left_on=["concept_id", "t"], right_on=["concept_id", "year"], how="left")
    d["band_2005_07"] = (d.F_band == "2005-07").astype(float)
    d["band_2008_11"] = (d.F_band == "2008-11").astype(float)
    for k in ("F31", "F17", "D3"):
        d[f"og_{k}"] = d.origin_group.str.startswith(k).astype(float)
    return d


def _prep(train: pd.DataFrame, test: pd.DataFrame, feats: list[str]) -> tuple[np.ndarray, np.ndarray]:
    Xtr = train[feats].astype(float).copy()
    Xte = test[feats].astype(float).copy()
    med = Xtr.median()
    miss_cols = [f for f in feats if Xtr[f].isna().any() or Xte[f].isna().any()]
    for f in miss_cols:
        Xtr[f"{f}_na"] = Xtr[f].isna().astype(float)
        Xte[f"{f}_na"] = Xte[f].isna().astype(float)
    Xtr = Xtr.fillna(med).fillna(0.0)
    Xte = Xte.fillna(med).fillna(0.0)
    return Xtr.values, Xte.values


def _clf(kind: str):
    if kind == "logit":
        return make_pipeline(StandardScaler(), LogisticRegression(C=1.0, class_weight="balanced", max_iter=5000))
    return HistGradientBoostingClassifier(max_depth=3, learning_rate=0.05, max_iter=200, min_samples_leaf=10, random_state=0)


def _reg(kind: str):
    if kind == "logit":
        return make_pipeline(StandardScaler(), Ridge(alpha=1.0))
    return HistGradientBoostingRegressor(max_depth=3, learning_rate=0.05, max_iter=200, min_samples_leaf=10, random_state=0)


def rolling(d: pd.DataFrame, target: str, origins: list[int], horizon: int, task: str = "clf") -> tuple[pd.DataFrame, list]:
    preds, olog = [], []
    for T in origins:
        tr = d[(d.t <= T - horizon) & d[target].notna()]
        te = d[(d.t == T) & d[target].notna()]
        npos = int(tr[target].sum()) if task == "clf" else -1
        ok = len(tr) >= S["min_train_rows"] and len(te) > 0 and (task != "clf" or (npos >= S["min_train_pos"] and tr[target].nunique() == 2))
        olog.append(dict(T=T, n_train=len(tr), n_train_pos=npos, n_test=len(te),
                         n_test_pos=int(te[target].sum()) if task == "clf" else -1, used=bool(ok)))
        if not ok:
            logger.info(f"[{target} h={horizon}] origin {T} skipped (train {len(tr)}, pos {npos}, test {len(te)})")
            continue
        for kind in ("logit", "hgb"):
            for fs, feats in FEATURE_SETS.items():
                Xtr, Xte = _prep(tr, te, feats)
                if task == "clf":
                    mdl = _clf(kind).fit(Xtr, tr[target].astype(int).values)
                    sc = mdl.predict_proba(Xte)[:, 1]
                else:
                    mdl = _reg(kind).fit(Xtr, tr[target].astype(float).values)
                    sc = mdl.predict(Xte)
                preds.append(pd.DataFrame(dict(concept_id=te.concept_id.values, t=te.t.values, T=T, model=kind,
                                               featureset=fs, y_true=te[target].values, y_score=sc, target=target,
                                               horizon=horizon)))
    return (pd.concat(preds, ignore_index=True) if preds else pd.DataFrame()), olog


def _metric(y, s, task):
    if task == "clf":
        if len(np.unique(y)) < 2:
            return np.nan
        return roc_auc_score(y, s)
    if len(y) < 3:
        return np.nan
    return r2_score(y, s)


def evaluate(p: pd.DataFrame, task: str, B: int, seed: int = 0) -> dict:
    """Pooled metrics per model x featureset and concept-bootstrap CI of FULL - BASELINE."""
    out: dict = {}
    if p.empty:
        return out
    for kind, g in p.groupby("model"):
        piv = g.pivot_table(index=["concept_id", "t", "T"], columns="featureset", values="y_score")
        yt = g.drop_duplicates(["concept_id", "t", "T"]).set_index(["concept_id", "t", "T"]).y_true.reindex(piv.index)
        y = yt.values.astype(float)
        res = {}
        for fs in piv.columns:
            res[fs] = dict(metric=_metric(y, piv[fs].values, task),
                           ap=float(average_precision_score(y, piv[fs].values)) if task == "clf" and len(np.unique(y)) == 2 else None)
        per_origin = {}
        for T in sorted(set(piv.index.get_level_values("T"))):
            msk = piv.index.get_level_values("T") == T
            per_origin[str(T)] = dict(n=int(msk.sum()), n_pos=int(y[msk].sum()) if task == "clf" else None,
                                      BASELINE=_metric(y[msk], piv.loc[msk, "BASELINE"].values, task),
                                      FULL=_metric(y[msk], piv.loc[msk, "FULL"].values, task))
        concepts = piv.index.get_level_values("concept_id").values
        uc = np.unique(concepts)
        rows_by = {c: np.where(concepts == c)[0] for c in uc}
        rng = np.random.default_rng(seed)
        deltas = {"FULL_vs_BASELINE": [], "PREC_only_vs_BASELINE": []}
        for _ in range(B):
            pick = rng.choice(uc, len(uc), replace=True)
            ii = np.concatenate([rows_by[c] for c in pick])
            yb = y[ii]
            if task == "clf" and len(np.unique(yb)) < 2:
                continue
            base = _metric(yb, piv["BASELINE"].values[ii], task)
            deltas["FULL_vs_BASELINE"].append(_metric(yb, piv["FULL"].values[ii], task) - base)
            deltas["PREC_only_vs_BASELINE"].append(_metric(yb, piv["PREC_only"].values[ii], task) - base)
        dres = {}
        for k, v in deltas.items():
            v = np.array(v, dtype=float)
            v = v[np.isfinite(v)]
            a, b = k.split("_vs_")
            point = res[a]["metric"] - res[b]["metric"] if np.isfinite(res[a]["metric"]) and np.isfinite(res[b]["metric"]) else np.nan
            dres[k] = dict(delta=point, ci=np.percentile(v, [2.5, 97.5]).tolist() if len(v) > 20 else [np.nan, np.nan],
                           n_boot=len(v))
        out[kind] = dict(pooled=res, per_origin=per_origin, deltas=dres, n_test_rows=int(len(y)),
                         n_test_pos=int(y.sum()) if task == "clf" else None, n_concepts=int(len(uc)))
    return out


def grouped_cv(d: pd.DataFrame, target: str) -> dict:
    """Non-temporal sanity check: 5-fold GroupKFold by concept (features <= t still)."""
    dd = d[d[target].notna()]
    if dd[target].nunique() < 2:
        return {}
    gkf = GroupKFold(n_splits=5)
    scores = {fs: np.zeros(len(dd)) for fs in ("BASELINE", "FULL")}
    for tr_i, te_i in gkf.split(dd, groups=dd.concept_id):
        tr, te = dd.iloc[tr_i], dd.iloc[te_i]
        for fs in scores:
            Xtr, Xte = _prep(tr, te, FEATURE_SETS[fs])
            if tr[target].nunique() < 2:
                scores[fs][te_i] = 0.5
                continue
            scores[fs][te_i] = _clf("logit").fit(Xtr, tr[target].astype(int)).predict_proba(Xte)[:, 1]
    y = dd[target].astype(int).values
    return {fs: float(roc_auc_score(y, s)) for fs, s in scores.items()} | {"n": len(dd), "n_pos": int(y.sum())}


def shuffle_test(d: pd.DataFrame, target: str, origins: list[int], horizon: int, n: int = 20) -> dict:
    """Label shuffles within F-band across concepts -> delta-AUC should be ~0."""
    rng = np.random.default_rng(3)
    deltas = []
    for i in range(n):
        dd = d.copy()
        # shuffle concept-level label vectors within band (keeps within-concept structure but breaks feature link)
        dd[target] = dd.groupby("F_band")[target].transform(lambda s: rng.permutation(s.values))
        preds = []
        for T in origins:
            tr = dd[(dd.t <= T - horizon) & dd[target].notna()]
            te = dd[(dd.t == T) & dd[target].notna()]
            if len(tr) < S["min_train_rows"] or tr[target].sum() < S["min_train_pos"] or te.empty:
                continue
            for fs in ("BASELINE", "FULL"):
                Xtr, Xte = _prep(tr, te, FEATURE_SETS[fs])
                sc = _clf("logit").fit(Xtr, tr[target].astype(int)).predict_proba(Xte)[:, 1]
                preds.append(pd.DataFrame(dict(k=np.arange(len(te)), T=T, fs=fs, y=te[target].values, s=sc)))
        if not preds:
            continue
        p = pd.concat(preds)
        b = p[p.fs == "BASELINE"]
        f = p[p.fs == "FULL"]
        if b.y.nunique() < 2:
            continue
        deltas.append(roc_auc_score(f.y, f.s) - roc_auc_score(b.y, b.s))
    deltas = np.array(deltas)
    return dict(n=len(deltas), mean_delta=float(deltas.mean()) if len(deltas) else np.nan,
                sd_delta=float(deltas.std(ddof=1)) if len(deltas) > 1 else np.nan)


def run_prediction(lab: pd.DataFrame, ind: pd.DataFrame) -> tuple[dict, pd.DataFrame]:
    """Primary E (h=5), E3 (h=3), and the secondary labels E_alt (pre-declared pool-only percentile) and E_up (uptake only)."""
    B = S["bootstrap"]
    d = build_rows(lab, ind)
    out: dict = dict(feature_sets=FEATURE_SETS, n_rows=len(d),
                     n_pos={t: int(d[t].sum()) for t in ("E", "E3", "E_alt", "E_up")})
    allp = []
    designs = (("E", 5, S["test_origins"]), ("E3", 3, S["h3_test_origins"]), ("E_alt", 5, S["test_origins"]),
               ("E_up", 5, S["test_origins"]))
    used = {}
    for tgt, hz, org in designs:
        key = f"{tgt}_h{hz}"
        p, olog = rolling(d, tgt, org, hz)
        out[key] = dict(target=tgt, horizon=hz, origins=olog, eval=evaluate(p, "clf", B))
        used[key] = sum(o["used"] for o in olog)
        allp.append(p)
    if used["E_h5"] >= 2:
        out["headline"] = "E_h5"
    elif used["E3_h3"] >= 2:
        out["headline"] = "E3_h3"
    elif used["E_h5"] >= 1:
        out["headline"] = "E_h5"
    else:
        out["headline"] = None
    out["headline_note"] = ("primary E: fewer than 2 usable rolling origins -> read as a single-origin pilot"
                            if out["headline"] == "E_h5" and used["E_h5"] < 2 else "")
    out["secondary_headline"] = "E_alt_h5"
    out["origins_used"] = used
    for tgt in ("subfield_gain", "cent_gain"):
        pr, ol = rolling(d, tgt, S["test_origins"], 5, task="reg")
        out[f"{tgt}_reg"] = dict(origins=ol, eval=evaluate(pr, "reg", B))
        allp.append(pr)
    # secondary population: drop sense_check_fail (on the primary headline and on E_alt)
    ds = d[~d.sense_check_fail]
    for key in {out["headline"], "E_alt_h5"} - {None}:
        tgt, hz = out[key]["target"], out[key]["horizon"]
        org = S["test_origins"] if hz == 5 else S["h3_test_origins"]
        ps, ols = rolling(ds, tgt, org, hz)
        out[f"secondary_drop_sense_fail_{key}"] = dict(origins=ols, eval=evaluate(ps, "clf", B))
    out["grouped_cv_sanity"] = {t: grouped_cv(d, t) for t in ("E", "E3", "E_alt", "E_up")}
    out["shuffle_test"] = {}
    for key in {out["headline"], "E_alt_h5"} - {None}:
        tgt, hz = out[key]["target"], out[key]["horizon"]
        org = S["test_origins"] if hz == 5 else S["h3_test_origins"]
        out["shuffle_test"][key] = shuffle_test(d, tgt, org, hz)
    for key in (out["headline"], "E_alt_h5", "E_up_h5"):
        if key:
            logger.info(f"prediction {key}: {out[key]['eval'].get('logit', {}).get('deltas')}")
    preds = pd.concat([x for x in allp if not x.empty], ignore_index=True) if any(not x.empty for x in allp) else pd.DataFrame()
    return out, preds
