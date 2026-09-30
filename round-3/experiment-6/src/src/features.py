"""Step 6: W1 baselines at t (data in [t-5, t] only) for screen unit rows, plus sealed W1 rows for held-out concepts.

Unit rows: concepts of the main arm, t in [F+3, F+8], t <= 2015.
"""
from __future__ import annotations

import json
import math

import numpy as np
import pandas as pd
from loguru import logger

import common as K
from common import AGES, MINI_N, OUT, SEALED, T_MAX_SCREEN, WORK

import lib_metrics as lm
from indicators import load_rs

FDIR = OUT / "d1"


def rs_value(counts: dict, D: np.ndarray, sidx: dict) -> float:
    return lm.rao_stirling(counts, dist_matrix=D, index=sidx) if counts else math.nan


def ols_slope_se(x: np.ndarray, y: np.ndarray) -> tuple[float, float]:
    x = np.asarray(x, float)
    y = np.asarray(y, float)
    n = len(x)
    xc = x - x.mean()
    sxx = float(np.sum(xc ** 2))
    b = float(np.sum(xc * (y - y.mean())) / sxx)
    resid = y - (y.mean() + b * xc)
    se = math.sqrt(float(np.sum(resid ** 2)) / (n - 2) / sxx) if n > 2 else math.nan
    return b, se


def growing_edge(years: np.ndarray, subs: np.ndarray, t: int) -> tuple[float, int]:
    """Shannon over W1 counts of subfields whose yearly log(n+1) slope over [t-5, t] is significantly > 0."""
    m = (years >= t - 5) & (years <= t) & (subs >= 0)
    if not m.any():
        return 0.0, 0
    yy = np.arange(t - 5, t + 1)
    grow_counts = []
    for d in np.unique(subs[m]):
        md = m & (subs == d)
        n_y = np.array([np.sum(years[md] == y) for y in yy], dtype=float)
        b, se = ols_slope_se(yy, np.log(n_y + 1))
        if np.isfinite(se) and b - 1.645 * se > 0:
            grow_counts.append(n_y.sum())
    if not grow_counts:
        return 0.0, 0
    return (lm.shannon(grow_counts) if len(grow_counts) > 1 else 0.0), len(grow_counts)


def rafols_coherence(cid_papers: pd.DataFrame, t: int, D: np.ndarray, sidx: dict) -> tuple[float, int]:
    """Within-concept citation coherence (Rafols 2014): distance-weighted observed flows over the Rao-Stirling
    expectation. Flows = refs from W1 c-papers (known subfield) to c-papers of the same concept published <= t."""
    w1 = cid_papers[(cid_papers.year >= t - 5) & (cid_papers.year <= t) & (cid_papers.subfield >= 0)]
    upto = cid_papers[(cid_papers.year <= t) & (cid_papers.subfield >= 0)]
    sub_of = dict(zip(upto.work_id.values, upto.subfield.values))
    flows = []
    for s_i, refs in zip(w1.subfield.values, w1.refs.values):
        if refs is None:
            continue
        for q in refs:
            s_j = sub_of.get(int(q))
            if s_j is not None and int(s_i) in sidx and int(s_j) in sidx:
                flows.append((sidx[int(s_i)], sidx[int(s_j)]))
    n = len(flows)
    counts = w1.subfield.value_counts().to_dict()
    rs = rs_value(counts, D, sidx)
    if n < 10 or not np.isfinite(rs) or rs <= 0:
        return math.nan, n
    f = np.array(flows)
    num = float(np.sum(D[f[:, 0], f[:, 1]])) / n   # sum_{i != j} d_ij I_ij (d_ii = 0)
    return num / rs, n


def unit_rows(pool: pd.DataFrame, fold: str) -> pd.DataFrame:
    p = pool[(pool.fold == fold) & (pool.arm == "main")]
    rows = []
    for r in p.itertuples(index=False):
        for t in range(int(r.F) + AGES[0], int(r.F) + AGES[1] + 1):
            if t <= T_MAX_SCREEN:
                rows.append(dict(concept_id=r.concept_id, t=t))
    return pd.DataFrame(rows)


def build(pool: pd.DataFrame, rows: pd.DataFrame, cp_max_year: int | None = None) -> pd.DataFrame:
    cp = pd.read_parquet(WORK / "cp.parquet", columns=["concept_id", "work_id", "year", "subfield", "refs"])
    cp = cp[cp.concept_id.isin(set(rows.concept_id)) & (cp.year <= (cp_max_year or T_MAX_SCREEN))]
    totals = json.loads((WORK / "totals.json").read_text())
    D, sidx = load_rs()
    ind = pd.read_parquet(WORK / "indicators_open.parquet")
    ind = ind[ind.year <= T_MAX_SCREEN]
    pmeta = pool.set_index("concept_id")
    subs_all = np.array(sorted(sidx), dtype=int)
    out = []
    groups = dict(tuple(cp.groupby("concept_id")))
    for cid, t in zip(rows.concept_id, rows.t):
        g = groups.get(cid, cp.iloc[0:0])
        yrs, sub = g.year.values, g.subfield.values
        w1 = (yrs >= t - 5) & (yrs <= t)
        known = w1 & (sub >= 0)
        sc = dict(zip(*np.unique(sub[known], return_counts=True)))
        vol_y = np.array([np.sum(yrs == y) for y in range(t - 5, t + 1)], dtype=float)
        allsci = np.array([totals[str(y)]["all_science"] for y in range(t - 5, t + 1)], dtype=float)
        momentum = lm.ols_slope(np.arange(t - 5, t + 1), np.log((vol_y + 1) / allsci * 1e4))
        geb, n_grow = growing_edge(yrs, sub, t)
        coh, n_flows = rafols_coherence(g, t, D, sidx)
        o = pmeta.loc[cid]
        osub = int(o.origin_subfield_id) if o.origin_subfield_id == o.origin_subfield_id and o.origin_subfield_id is not None else None
        if osub is not None and osub in sidx:
            dd = np.delete(D[sidx[osub]], sidx[osub])
            prox = float(np.mean(1 - dd))
        else:
            prox = math.nan
        out.append(dict(concept_id=cid, t=t, n_W1=int(w1.sum()), n_W1_known=int(known.sum()),
                        H_W1_f=lm.shannon(list(sc.values())) if sc else math.nan,
                        RS_W1=rs_value({int(k): v for k, v in sc.items()}, D, sidx),
                        n_active_W1=int(sum(1 for v in sc.values() if v >= 2)), log_vol_W1=math.log1p(int(w1.sum())),
                        momentum=momentum, GEB=geb, n_growing=n_grow, rafols_coh=coh, n_flows=n_flows,
                        origin_prox=prox))
    F = pd.DataFrame(out)
    keep = ["concept_id", "year", "age", "burst_state", "P_rar", "new_relation_rate", "novelty", "beta_sim_rar",
            "log_vol3", "vol3", "H", "closure", "closure_res", "closure_res_imp", "closure_res_H3", "closure_unres",
            "closure_res_w1mean", "constraint", "esize", "esize_norm", "xcomm_exc", "H_W1"] + \
           [c for c in ind.columns if c.endswith("_z")]
    F = F.merge(ind[keep].rename(columns={"year": "t"}), on=["concept_id", "t"], how="left")
    assert np.allclose(F.H_W1_f.values, F.H_W1.values, equal_nan=True), "H_W1 mismatch between stages"
    F = F.drop(columns=["H_W1_f"])
    F = F.merge(pool[["concept_id", "phrase", "F", "F_band", "origin_group", "route", "hydration_batch", "fold",
                      "in_MAIN", "in_STRICT", "in_SENSITIVITY", "sense_check_fail", "iter1_screen"]],
                on="concept_id", how="left")
    return F


def fill_missing(F: pd.DataFrame, med: dict | None = None) -> tuple[pd.DataFrame, dict]:
    """Median fill + missing dummy for rafols_coh and P_rar (medians from the screen rows; frozen for held-out)."""
    med = med or {c: float(F[c].median()) for c in ("rafols_coh", "P_rar", "origin_prox")}
    F["coh_missing"] = F.rafols_coh.isna().astype(float)
    F["P_rar_missing"] = F.P_rar.isna().astype(float)
    F["prox_missing"] = F.origin_prox.isna().astype(float)
    F["rafols_coh_f"] = F.rafols_coh.fillna(med["rafols_coh"])
    F["P_rar_f"] = F.P_rar.fillna(med["P_rar"])
    F["origin_prox_f"] = F.origin_prox.fillna(med["origin_prox"])
    return F, med


def run(mini: bool = False) -> None:
    FDIR.mkdir(parents=True, exist_ok=True)
    heldout = K.load_sealed_ids()
    pool = pd.read_parquet(WORK / "pool.parquet")
    rows = unit_rows(pool, "screen")
    if mini:
        rows = rows[rows.concept_id.isin(sorted(rows.concept_id.unique())[:MINI_N])]
    for cid, t in zip(rows.concept_id, rows.t):
        K.assert_not_sealed([cid], [t])
    F = build(pool, rows)
    # leakage test: 5 random rows rebuilt from c-papers truncated at t must give identical W1 features
    leak = []
    for r in rows.sample(min(5, len(rows)), random_state=11).itertuples(index=False):
        a = build(pool, pd.DataFrame([dict(concept_id=r.concept_id, t=r.t)]), cp_max_year=int(r.t)).iloc[0]
        b = F[(F.concept_id == r.concept_id) & (F.t == r.t)].iloc[0]
        cols = ["n_W1", "RS_W1", "n_active_W1", "log_vol_W1", "momentum", "GEB", "n_growing", "rafols_coh", "n_flows",
                "origin_prox"]
        same = all((a[c] == b[c]) or (pd.isna(a[c]) and pd.isna(b[c])) for c in cols)
        leak.append(dict(concept_id=r.concept_id, t=int(r.t), identical=bool(same)))
    assert all(x["identical"] for x in leak), leak
    K.write_json(FDIR / "leakage_check_features.json", leak)
    F, med = fill_missing(F)
    F.to_parquet(FDIR / "features_ct.parquet", index=False)
    K.write_json(FDIR / "features_fill_medians.json", med)
    na = {c: float(F[c].isna().mean()) for c in F.columns if F[c].dtype.kind in "fi"}
    logger.info(f"features: {len(F)} rows / {F.concept_id.nunique()} concepts; rows per concept "
                f"{F.groupby('concept_id').size().describe()[['min', 'max']].to_dict()}; NA shares "
                f"{ {k: round(v, 3) for k, v in na.items() if v > 0} }")
    if not mini:
        hrows = unit_rows(pool, "heldout_concept")
        assert set(hrows.concept_id) <= heldout
        H, _ = fill_missing(build(pool, hrows), med)
        H.to_parquet(SEALED / "features_ct_heldout.parquet", index=False)
        (SEALED / "features_ct_heldout.sha256").write_text(K.sha256_file(SEALED / "features_ct_heldout.parquet") + "\n")
        logger.info(f"sealed held-out W1 feature rows: {len(H)} / {H.concept_id.nunique()} concepts")
