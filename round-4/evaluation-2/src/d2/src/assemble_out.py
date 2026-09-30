"""STAGE 12: grouped-by-concept out-of-sample check (descriptive, not the inferential test) and method_out.json.

Screen MAIN kw5 events are split into 5 folds by int(sha1(concept_id), 16) % 5. On 4 folds we fit a Poisson GLM with
e and d one-hot FE (unseen levels -> reference level, i.e. the mean FE), concept-level covariates instead of a concept FE,
and exposure n_entry_papers (rate model with sample weights = exposure, equivalent to an offset). M0 = controls only;
M1 = M0 + A_cont + CT. We predict Y_strict for the held-back fold.
"""
from __future__ import annotations

import hashlib
import json

import numpy as np
import orjson
import pandas as pd
from loguru import logger
from scipy import stats
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import PoissonRegressor
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

import models
from config import SEED, WS

NUM0 = models.EVENT_CONTROLS + models.SECONDARY_EXTRA + ["route_A_f"]
NUM1 = NUM0 + ["A_cont", "CT"]


def _model(num: list[str]):
    ct = ColumnTransformer([("num", StandardScaler(), num),
                            ("fe", OneHotEncoder(handle_unknown="ignore"), ["e_s", "d_s"])])
    return make_pipeline(ct, PoissonRegressor(alpha=1e-4, max_iter=3000))


def poisson_dev(y: np.ndarray, mu: np.ndarray) -> np.ndarray:
    return 2 * (np.where(y > 0, y * np.log(np.where(y > 0, y, 1) / mu), 0) - (y - mu))


def oos(s: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    s = s.copy()
    s["route_A_f"] = s.route_A.astype(float)
    s["e_s"], s["d_s"] = s.e.astype(str), s.d.astype(str)
    s["k"] = [int(hashlib.sha1(c.encode()).hexdigest(), 16) % 5 for c in s.concept_id]
    s["rate"] = s.Y_strict / s.n_entry_papers
    s["mu0"], s["mu1"] = np.nan, np.nan
    for k in range(5):
        tr, te = s.k != k, s.k == k
        for name, num in (("mu0", NUM0), ("mu1", NUM1)):
            m = _model(num)
            m.fit(s.loc[tr], s.loc[tr, "rate"], poissonregressor__sample_weight=s.loc[tr, "n_entry_papers"])
            s.loc[te, name] = m.predict(s.loc[te]) * s.loc[te, "n_entry_papers"]
    y = s.Y_strict.to_numpy(float)
    d0, d1 = poisson_dev(y, s.mu0.to_numpy()), poisson_dev(y, s.mu1.to_numpy())
    rng = np.random.default_rng(SEED)
    cids = s.concept_id.to_numpy()
    uc = np.unique(cids)
    grp = {c: np.flatnonzero(cids == c) for c in uc}
    diffs = []
    for _ in range(1000):
        ix = np.concatenate([grp[c] for c in rng.choice(uc, len(uc))])
        diffs.append(d1[ix].mean() - d0[ix].mean())
    res = {"n_events": int(len(s)), "n_concepts": int(len(uc)),
           "mean_deviance_M0": float(d0.mean()), "mean_deviance_M1": float(d1.mean()),
           "deviance_diff_M1_minus_M0": float(d1.mean() - d0.mean()),
           "deviance_diff_ci95_concept_bootstrap": [float(np.quantile(diffs, .025)), float(np.quantile(diffs, .975))],
           "spearman_M0": float(stats.spearmanr(s.mu0, y).statistic),
           "spearman_M1": float(stats.spearmanr(s.mu1, y).statistic),
           "note": "grouped-by-concept 5-fold out-of-fold predictions; descriptive predictive check, not the "
                   "inferential test (concept x e FE cannot be used for unseen concepts)"}
    return s, res


def method_out(s: pd.DataFrame, labels: pd.DataFrame, oos_res: dict, summary_meta: dict) -> dict:
    s = s.join(labels[["anchored"]], how="left")
    feats = ["A_cont", "A", "A_t03", "CT", "CT_any", "graft_t03", "native_companion_t03", "package_t03",
             "third_party_t03", "unknown_share", "cov", "A0_cont", "A_cont_ex", "prox_od", "RD", "log_n_partner_tags",
             "demic", "mean_topic_score", "boundary_share", "abstract_share", "mom_d", "log_centrality", "log_W1",
             "n_entry_papers", "n_partners_distinct"]
    ex = []
    for r in s.itertuples():
        inp = {"concept_id": r.concept_id, "o": int(r.o), "d": int(r.d), "e": int(r.e),
               **{f: (None if pd.isna(getattr(r, f)) else round(float(getattr(r, f)), 6)) for f in feats}}
        ex.append({"input": orjson.dumps(inp).decode(), "output": str(int(r.Y_strict)),
                   "predict_baseline": str(round(float(r.mu0), 4)), "predict_method": str(round(float(r.mu1), 4)),
                   "metadata_concept_id": r.concept_id, "metadata_fold": "screen",
                   "metadata_oos_fold": int(r.k), "metadata_population": "MAIN" + ("+STRICT" if r.STRICT else ""),
                   "metadata_route": r.route, "metadata_label_anchored": bool(r.anchored) if pd.notna(r.anchored) else None,
                   "metadata_Y_all": int(r.Y_all), "metadata_Y_lenient": int(r.Y_lenient),
                   "metadata_EST_bin": int(r.EST_bin), "metadata_field_group": r.field_group})
    out = {"metadata": {"method_name": "D2 host-entry anchoring vs co-transfer (PPML, grafting test)",
                        "description": "One example per screen MAIN kw5 host-entry event (concept c enters non-origin "
                                       "subfield d in year e). input = W1 features; output = Y_strict (W2 host papers "
                                       "by author-disjoint newcomers). predict_baseline = out-of-fold mean from the "
                                       "controls-only Poisson model (M0); predict_method = M0 + anchoring A_cont + "
                                       "co-transfer CT (M1).",
                        "oos": oos_res, **summary_meta},
           "datasets": [{"dataset": "d2_host_entry_events_screen", "examples": ex}]}
    (WS / "method_out.json").write_bytes(orjson.dumps(out, option=orjson.OPT_INDENT_2))
    logger.info(f"method_out.json: {len(ex)} examples")
    return out


def run(df: pd.DataFrame, labels: pd.DataFrame, summary_meta: dict) -> dict:
    s = models.primary_sample(df)
    s.index = df[(df.arm == "main") & (df.fold == "screen") & df.kw5 & df.MAIN].dropna(
        subset=["A_cont", "CT"] + models.EVENT_CONTROLS + models.SECONDARY_EXTRA).index
    so, res = oos(s)
    method_out(so, labels, res, summary_meta)
    from config import RESULTS
    (RESULTS / "oos_check.json").write_text(json.dumps(res, indent=1))
    logger.info(f"oos: {res}")
    return res
