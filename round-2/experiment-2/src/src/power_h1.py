"""STEP 6a/6b: unit counts + projection, and simulation MDE for H1 (delta-AUC and delta-R2) BEFORE any outcome.

Only W1 features, labels and origin covariates are used; host W2 incidence is never computed.
"""
from __future__ import annotations

import json
import multiprocessing as mp
import time
import warnings
from concurrent.futures import ProcessPoolExecutor, as_completed

import numpy as np
import orjson
import pandas as pd
import statsmodels.api as sm
from loguru import logger
from scipy.optimize import brentq
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.model_selection import GroupKFold
from sklearn.preprocessing import StandardScaler

import io_load
from common import DS1, RESULTS, SEED, detect_cpus, f_band

OUT = RESULTS / "power"
BASE = ["H", "n_active", "growing_breadth", "mean_host_mom", "log_w1_volume"]
S = ["S_source_breadth", "S_sink_share"]
GAMMAS = [0.0, 0.1, 0.2, 0.35, 0.5, 0.75, 1.0, 1.5]
NMINS = [5, 10, 20, None]  # None = main n_min
PREV = 0.35
N_SIMS = 200
B_BOOT = 1000


# ---------------------------------------------------------------- 6a projection
def focal_count(F: int) -> int:
    return len([t for t in range(F + 3, F + 9) if t <= 2019])


def projection(n_min_list: list, e: pd.DataFrame, con: pd.DataFrame) -> dict:
    main = con[con.arm == "main"].copy()
    main["n_focal"] = main.F.astype(int).map(focal_count)
    grp = main.set_index("concept_id").stratum.str.split("|").str[0]
    main["ogroup"] = main.concept_id.map(grp).fillna("NA")
    frame = orjson.loads((DS1 / "sample_frame_frozen.json").read_bytes())
    pend = orjson.loads((DS1 / "pending_hydration.json").read_bytes())["pending"]
    pend_main = [p["concept_id"] for p in pend if p["arm"] == "main"]
    elig = {x["concept_id"]: x for x in frame["eligible"]}
    pm = pd.DataFrame([{"concept_id": c, "V": elig[c]["V"], "F": elig[c]["F"]} for c in pend_main if c in elig])
    pm["F_band"] = pm.F.map(f_band)
    pm["n_focal"] = pm.F.map(focal_count)
    res = {"n_pending_main": int(len(pm)), "pending_main_listed": len(pend_main)}
    rng = np.random.default_rng([SEED, 61])
    for nm in n_min_list:
        nmv = int(e.n_min_main.iloc[0]) if nm is None else nm
        t = e[(e.n_children >= nmv) & (e.n_parents >= 1) & (e.n_traced >= 1)]
        cnt = t.groupby("concept_id").size()
        main["y"] = main.concept_id.map(cnt).fillna(0).astype(int)
        realised = int((main.y > 0).sum())
        out = {"realised_N_c": realised, "realised_tested_edges": int(main.y.sum())}
        for label, formula_cols, data in [("with_origin", True, main), ("no_origin", False, main)]:
            X = pd.get_dummies(data[["F_band"] + (["ogroup"] if formula_cols else [])], drop_first=True).astype(float)
            X["logV"] = np.log(data.V.astype(float))
            X = sm.add_constant(X)
            try:
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    mod = sm.NegativeBinomial(data.y.to_numpy(), X, offset=np.log(data.n_focal.to_numpy())).fit(disp=0, maxiter=200)
                out[f"nb_{label}_params"] = {k: float(v) for k, v in mod.params.items()}
                out[f"nb_{label}_converged"] = bool(mod.mle_retvals.get("converged", True))
                if not formula_cols:
                    Xp = pd.get_dummies(pm[["F_band"]], drop_first=True).astype(float)
                    Xp = Xp.reindex(columns=[c for c in X.columns if c not in ("const", "logV")], fill_value=0.0)
                    Xp["logV"] = np.log(pm.V.astype(float))
                    Xp = sm.add_constant(Xp, has_constant="add")[X.columns]
                    draws = rng.multivariate_normal(mod.params.to_numpy(), mod.cov_params().to_numpy(), size=2000)
                    tot = []
                    for dr in draws:
                        beta, alpha = dr[:-1], max(dr[-1], 1e-6)
                        mu = np.exp(Xp.to_numpy() @ beta + np.log(pm.n_focal.to_numpy()))
                        p0 = (1 + alpha * mu) ** (-1 / alpha)
                        tot.append(rng.binomial(1, 1 - p0).sum())
                    beta, alpha = mod.params.to_numpy()[:-1], max(mod.params.to_numpy()[-1], 1e-6)
                    mu = np.exp(Xp.to_numpy() @ beta + np.log(pm.n_focal.to_numpy()))
                    exp_new = float((1 - (1 + alpha * mu) ** (-1 / alpha)).sum())
                    out["projected_N_c"] = round(realised + exp_new, 1)
                    out["projected_N_c_90"] = [float(realised + np.percentile(tot, 5)), float(realised + np.percentile(tot, 95))]
            except (np.linalg.LinAlgError, ValueError) as ex:
                logger.error(f"NB projection failed ({label}, n_min={nmv}): {ex}")
                out[f"nb_{label}_error"] = str(ex)
        if "projected_N_c" not in out:  # fallback: realised rate among included concepts
            rate = realised / len(main)
            out["projected_N_c"] = round(realised + rate * len(pm), 1)
            out["projection_fallback"] = "empirical rate"
        res[f"n_min_{nmv}"] = out
    return res


# ---------------------------------------------------------------- AUC / R2 helpers
def auc(score: np.ndarray, y: np.ndarray) -> float:
    o = np.argsort(score, kind="mergesort")
    ys = y[o]
    neg_below = np.cumsum(1 - ys) - (1 - ys)
    npos, nneg = ys.sum(), len(ys) - ys.sum()
    return float((ys * neg_below).sum() / (npos * nneg)) if npos and nneg else np.nan


def wauc(score: np.ndarray, y: np.ndarray, W: np.ndarray) -> np.ndarray:
    o = np.argsort(score, kind="mergesort")
    ys = y[o]
    Wn = W[:, o] * (1 - ys)
    Wp = W[:, o] * ys
    below = np.cumsum(Wn, axis=1) - Wn
    den = Wp.sum(1) * Wn.sum(1)
    with np.errstate(invalid="ignore", divide="ignore"):
        return (Wp * below).sum(1) / den


def wr2(y: np.ndarray, yhat: np.ndarray, W: np.ndarray) -> np.ndarray:
    sw = W.sum(1)
    ybar = (W * y).sum(1) / sw
    sse = (W * (y - yhat) ** 2).sum(1)
    sst = (W * (y[None, :] - ybar[:, None]) ** 2).sum(1)
    with np.errstate(invalid="ignore", divide="ignore"):
        return 1 - sse / sst


def zs(x: np.ndarray) -> np.ndarray:
    sd = x.std()
    return (x - x.mean()) / sd if sd > 0 else x * 0


def composite(df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    """z(BASE_lin), z(resid(S_lin | BASE)) on a feature table."""
    Xb = np.column_stack([zs(df[c].to_numpy(float)) for c in BASE])
    zb = zs(Xb.sum(1))
    sl = zs(np.column_stack([zs(df[c].to_numpy(float)) for c in S]).sum(1))
    Xc = np.column_stack([np.ones(len(df)), Xb])
    coef, *_ = np.linalg.lstsq(Xc, sl, rcond=None)
    return zb, zs(sl - Xc @ coef)


def calib_logit(zb: np.ndarray, zr: np.ndarray, beta: float, gamma: float) -> float:
    eta = beta * zb + gamma * zr
    return brentq(lambda a: (1 / (1 + np.exp(-(a + eta)))).mean() - PREV, -30, 30)


def oracle(df: pd.DataFrame, target_auc: float, rng: np.random.Generator) -> dict:
    """beta for oracle BASE AUC, then the TRUE delta-AUC per gamma on 100k draws (features resampled)."""
    idx = rng.integers(0, len(df), 100_000)
    zb, zr = composite(df)
    zb, zr = zb[idx], zr[idx]
    u = rng.uniform(size=len(zb))

    def auc_for(beta: float) -> float:
        a = calib_logit(zb, zr, beta, 0.0)
        y = (u < 1 / (1 + np.exp(-(a + beta * zb)))).astype(float)
        return auc(zb, y)
    beta = brentq(lambda b: auc_for(b) - target_auc, 0.01, 10)
    true = {}
    for g in GAMMAS:
        a = calib_logit(zb, zr, beta, g)
        eta = beta * zb + g * zr
        y = (u < 1 / (1 + np.exp(-(a + eta)))).astype(float)
        true[g] = auc(eta, y) - auc(zb, y)
    return {"beta": float(beta), "true_delta_auc": true}


def oracle_r2(df: pd.DataFrame, target_r2: float) -> dict:
    zb, zr = composite(df)
    beta = float(np.sqrt(target_r2 / (1 - target_r2)))  # var(beta zb) / (var + 1)
    true = {g: float((beta**2 + g**2) / (beta**2 + g**2 + 1) - beta**2 / (beta**2 + 1)) for g in GAMMAS}
    return {"beta": beta, "true_delta_r2": true}


# ---------------------------------------------------------------- one simulation
def pipeline(X_a: np.ndarray, X_b: np.ndarray, y: np.ndarray, groups: np.ndarray, rng: np.random.Generator,
             binary: bool) -> dict:
    gkf = GroupKFold(n_splits=5)
    pa, pb = np.zeros(len(y)), np.zeros(len(y))
    for tr, te in gkf.split(X_a, y, groups):
        for X, p in ((X_a, pa), (X_b, pb)):
            sc = StandardScaler().fit(X[tr])
            if binary:
                if len(np.unique(y[tr])) < 2:
                    p[te] = y[tr].mean()
                    continue
                m = LogisticRegression(C=1.0, solver="lbfgs", max_iter=500).fit(sc.transform(X[tr]), y[tr])
                p[te] = m.predict_proba(sc.transform(X[te]))[:, 1]
            else:
                m = LinearRegression().fit(sc.transform(X[tr]), y[tr])
                p[te] = m.predict(sc.transform(X[te]))
    ug, inv = np.unique(groups, return_inverse=True)
    draw = rng.integers(0, len(ug), (B_BOOT, len(ug)))
    cnt = np.zeros((B_BOOT, len(ug)))
    np.add.at(cnt, (np.repeat(np.arange(B_BOOT), len(ug)), draw.ravel()), 1)
    W = cnt[:, inv]
    if binary:
        pt = auc(pb, y) - auc(pa, y)
        bd = wauc(pb, y, W) - wauc(pa, y, W)
    else:
        pt = float(wr2(y, pb, np.ones((1, len(y))))[0] - wr2(y, pa, np.ones((1, len(y))))[0])
        bd = wr2(y, pb, W) - wr2(y, pa, W)
    lo = float(np.nanpercentile(bd, 2.5))
    sc = StandardScaler().fit(X_b)
    if binary:
        coef = LogisticRegression(C=1.0, solver="lbfgs", max_iter=500).fit(sc.transform(X_b), y).coef_[0]
    else:
        coef = LinearRegression().fit(sc.transform(X_b), y).coef_
    sign_ok = coef[-2:].sum() > 0
    return {"point": float(pt), "lo": lo, "sign_ok": bool(sign_ok)}


def sim_task(args: dict) -> dict:
    import os
    os.environ.setdefault("OMP_NUM_THREADS", "1")
    df = pd.DataFrame(args["df"])
    rng = np.random.default_rng(args["seed"])
    binary = args["binary"]
    beta, g = args["beta"], args["gamma"]
    target_nc = args["target_nc"]
    res = []
    by_c = {c: np.flatnonzero(df.concept_id.to_numpy() == c) for c in df.concept_id.unique()}
    cids = np.array(list(by_c))
    for s in range(args["n_sims"]):
        if target_nc is None or target_nc <= len(cids):
            rows = np.arange(len(df))
            groups = df.concept_id.to_numpy()
        else:
            pick = rng.choice(cids, size=int(round(target_nc)), replace=True)
            rows = np.concatenate([by_c[c] for c in pick])
            groups = np.concatenate([np.full(len(by_c[c]), i) for i, c in enumerate(pick)])
        d = df.iloc[rows].reset_index(drop=True)
        zb, zr = composite(d)
        eta = beta * zb + g * zr
        if binary:
            a = calib_logit(zb, zr, beta, g)
            y = (rng.uniform(size=len(d)) < 1 / (1 + np.exp(-(a + eta)))).astype(float)
            if y.sum() < 5 or y.sum() > len(y) - 5:
                res.append({"point": np.nan, "lo": np.nan, "sign_ok": False, "success": False})
                continue
        else:
            y = eta + rng.normal(size=len(d))
        Xa = d[BASE].to_numpy(float)
        Xb = d[BASE + S].to_numpy(float)
        r = pipeline(Xa, Xb, y, np.asarray(groups), rng, binary)
        thr = 0.01 if binary else 0.0
        r["success"] = bool(r["lo"] > 0 and r["point"] >= thr and r["sign_ok"]) if not np.isnan(r["lo"]) else False
        res.append(r)
    pts = np.array([r["point"] for r in res], float)
    succ = np.array([r["success"] for r in res])
    return {"key": args["key"], "gamma": g, "power": float(succ.mean()), "mc_se": float(np.sqrt(succ.mean() * (1 - succ.mean()) / len(succ))),
            "mean_point": float(np.nanmean(pts)), "n_sims": len(res), "n_units": int(len(df)) if target_nc is None else None}


def mde(true: dict, power: dict) -> float | str:
    gs = sorted(true)
    xs = [true[g] for g in gs]
    ps = [power[g] for g in gs]
    if ps[0] >= 0.8:
        return float(xs[0])
    for i in range(1, len(gs)):
        if ps[i] >= 0.8 > ps[i - 1]:
            return float(xs[i - 1] + (0.8 - ps[i - 1]) * (xs[i] - xs[i - 1]) / (ps[i] - ps[i - 1]))
    return "> max grid"


def run(n_sims: int = N_SIMS) -> None:
    import p1
    OUT.mkdir(parents=True, exist_ok=True)
    G = io_load.prepare()
    e = pd.read_csv(RESULTS / "viability" / "viability_layer.csv")
    proj = projection(NMINS, e, G["concepts"])
    (OUT / "projection.json").write_text(json.dumps(proj, indent=2, default=float))
    logger.info(f"projection: { {k: (v.get('realised_N_c'), v.get('projected_N_c')) for k, v in proj.items() if isinstance(v, dict)} }")
    n_main = int(e.n_min_main.iloc[0])
    tasks, meta = [], {}
    rng = np.random.default_rng([SEED, 62])
    for nm in NMINS:
        nmv = n_main if nm is None else nm
        f = p1.features(nm)
        f.to_csv(OUT / f"h1_units_nmin{nmv}.csv", index=False)
        pr = proj[f"n_min_{nmv}"]
        designs = {"realised": None, "projected": pr["projected_N_c"], "N150": 150}
        for binary, targets in ((True, [0.70, 0.80]), (False, [0.10, 0.30])):
            for tg in targets:
                orc = oracle(f, tg, rng) if binary else oracle_r2(f, tg)
                for dn, tnc in designs.items():
                    key = f"{'auc' if binary else 'r2'}|nmin{nmv}|{'AUC' if binary else 'R2'}{tg}|{dn}"
                    meta[key] = {"n_min": nmv, "design": dn, "target_N_c": tnc, "realised_units": int(len(f)),
                                 "realised_concepts": int(f.concept_id.nunique()), "base_target": tg, **orc}
                    for g in GAMMAS:
                        tasks.append({"key": key, "gamma": g, "beta": orc["beta"], "binary": binary, "target_nc": tnc,
                                      "df": f[["concept_id"] + BASE + S].to_dict("list"), "n_sims": n_sims if binary else max(1, n_sims // 2),
                                      "seed": [SEED, 63, len(tasks)]})
    logger.info(f"H1 power: {len(tasks)} tasks x {n_sims} sims")
    t0 = time.time()
    out = []
    with ProcessPoolExecutor(max_workers=min(4, detect_cpus()), mp_context=mp.get_context("spawn")) as ex:
        futs = [ex.submit(sim_task, t) for t in tasks]
        for i, fu in enumerate(as_completed(futs)):
            out.append(fu.result())
            if (i + 1) % 24 == 0:
                logger.info(f"H1 power {i + 1}/{len(tasks)} ({time.time() - t0:.0f}s)")
    rows = []
    for key, m in meta.items():
        pw = {r["gamma"]: r for r in out if r["key"] == key}
        true = m.get("true_delta_auc") or m.get("true_delta_r2")
        for g in GAMMAS:
            rows.append({"key": key, "n_min": m["n_min"], "design": m["design"], "target_N_c": m["target_N_c"],
                         "base_target": m["base_target"], "gamma": g, "true_delta": true[g], "power": pw[g]["power"],
                         "mc_se": pw[g]["mc_se"], "mean_point": pw[g]["mean_point"], "outcome": key.split("|")[0]})
        m["power_by_gamma"] = {g: pw[g]["power"] for g in GAMMAS}
        m["MDE"] = mde(true, m["power_by_gamma"])
        m["size_at_gamma0"] = pw[0.0]["power"]
    pd.DataFrame(rows).to_csv(OUT / "h1_power_curves.csv", index=False)
    (OUT / "h1_mde.json").write_text(json.dumps(meta, indent=2, default=float))
    logger.info("H1 MDE: " + "; ".join(f"{k}: {v['MDE']}" for k, v in meta.items()))
