#!/usr/bin/env python3
"""Stages 3-4: concept-subfield bipartite + per-(concept, year) temporal network indicators.

Every indicator at year y uses data <= y only (the Kleinberg burst state is recomputed on the series truncated at y).
Precursors are given in raw form, rarefied form (m = 10 c-papers, 50 draws) and residualised on log volume + age.
Outputs: results/indicators/concept_year_indicators.parquet (+ csv), results/concept_subfield/edges.parquet,
results/concept_subfield/rs_distance.parquet, results/indicators/README.md (data dictionary).
"""
from __future__ import annotations

import json
import math
import multiprocessing as mp
import time
from concurrent.futures import ProcessPoolExecutor, as_completed

import numpy as np
import pandas as pd
import scipy.sparse as sp
from loguru import logger

import config as C
import lib_metrics as lm

SNAP = C.WORK / "snapshots"
IND = C.OUT / "indicators"
CSB = C.OUT / "concept_subfield"
IND.mkdir(parents=True, exist_ok=True)
CSB.mkdir(parents=True, exist_ok=True)

PM_COLS = ["strength", "pct", "pct_bg_only", "closure", "closure_obs", "closure_nK", "P_raw", "P_rar", "P_rar_m5", "wmz",
           "btw", "btw_pct", "cross_comm_flag", "plural_comm_raw", "n_comm_touched", "n_frame", "n_comm_10pct_frame"]


def build_rs_distance() -> tuple[np.ndarray, dict]:
    """Fixed pre-period (2000-2004) Rao-Stirling distance: 1 - cosine of subfield concept-profile vectors."""
    bg = pd.read_parquet(C.WORK / "bg.parquet", columns=["year", "w_year", "tags", "subfield_id", "low_conf_topic"])
    bg = bg[(bg.year <= 2004) & (~bg.low_conf_topic)]
    subs = np.sort(bg.subfield_id.unique())
    sidx = {int(s): i for i, s in enumerate(subs)}
    lens = bg.tags.map(len).values
    flat = np.concatenate(list(bg.tags.values))
    nodes, col = np.unique(flat, return_inverse=True)
    row = np.repeat(np.array([sidx[int(s)] for s in bg.subfield_id.values]), lens)
    w = np.repeat(bg.w_year.values, lens)
    M = sp.csr_matrix((w, (row, col)), shape=(len(subs), len(nodes)))
    norms = np.sqrt(np.asarray(M.multiply(M).sum(axis=1)).ravel())
    norms[norms == 0] = 1.0
    Mn = sp.diags(1.0 / norms) @ M
    cos = (Mn @ Mn.T).toarray()
    D = np.clip(1.0 - cos, 0.0, 1.0)
    np.fill_diagonal(D, 0.0)
    ii, jj = np.meshgrid(subs, subs, indexing="ij")
    pd.DataFrame(dict(subfield_i=ii.ravel(), subfield_j=jj.ravel(), d=D.ravel().astype(np.float32))).to_parquet(
        CSB / "rs_distance.parquet", index=False)
    logger.info(f"RS distance matrix {D.shape}, mean d {D[np.triu_indices(len(subs), 1)].mean():.3f}")
    return D, sidx


def _union(tag_lists) -> set:
    out: set = set()
    for t in tag_lists:
        out.update(t.tolist())
    return out


def _slope3(vals: dict, y: int) -> float:
    xs = [yy for yy in (y - 2, y - 1, y) if yy in vals]
    return lm.ols_slope(xs, [vals[yy] for yy in xs])


def concept_indicators(cid: str, F: float | None, papers: pd.DataFrame, pm: pd.DataFrame, pid_map: dict,
                       totals: dict, D: np.ndarray, sidx: dict, max_year: int | None = None) -> tuple[list, list]:
    """All indicators for one concept. `papers` = its c-papers (all types); `pm` = its pool_metrics rows by year.

    If max_year is given, data after max_year are dropped first (used by the leakage test).
    """
    S = C.SPEC
    if max_year is not None:
        papers = papers[papers.year <= max_year]
        pm = pm[pm.year <= max_year]
    y_first = 2000 if (F is None or (isinstance(F, float) and math.isnan(F))) else max(2000, int(F) - 2)
    y_last = 2024 if max_year is None else min(2024, max_year)
    years_all = list(range(2000, y_last + 1))
    by_year = {y: papers[papers.year == y] for y in years_all}
    vol = {y: len(by_year[y]) for y in years_all}
    tags_y = {y: list(by_year[y].tags.values) for y in years_all}
    N = {y: _union(tags_y[y]) for y in years_all}
    pmd = {int(r.year): r for r in pm.itertuples(index=False)}
    rs = S["rarefy_m"]
    rows, bip = [], []
    seen_before: set = set()
    dser = [totals[str(y)]["all_science"] for y in years_all]
    rser = [vol[y] for y in years_all]
    cache: dict = {}
    for y in years_all:
        if y < y_first:
            seen_before |= N[y]
            continue
        r: dict = dict(concept_id=cid, year=y, age=(y - int(F)) if F is not None and not (isinstance(F, float) and math.isnan(F)) else np.nan)
        win = [yy for yy in (y - 2, y - 1, y) if yy >= 2000]
        vol3 = sum(vol[yy] for yy in win)
        r.update(vol=vol[y], vol3=vol3, log_vol3=math.log1p(vol3))
        r["growth1"] = math.log((vol[y] + 1) / (vol.get(y - 1, 0) + 1))
        vol3_prev3 = sum(vol.get(yy, 0) for yy in (y - 5, y - 4, y - 3))
        r["growth3"] = math.log((vol3 + 1) / (vol3_prev3 + 1))
        st, ys = lm.kleinberg_at(years_all, rser, dser, y, **S["kleinberg"])
        r["burst_state"] = st
        r["yrs_since_burst"] = ys if np.isfinite(ys) else 30.0
        # neighbourhoods
        N3 = set().union(*[N[yy] for yy in win])
        win_prev = [yy for yy in (y - 3, y - 2, y - 1) if yy >= 2000]
        N3p = set().union(*[N[yy] for yy in win_prev]) if win_prev else set()
        new = N3 - N3p
        r["n_neigh3"] = len(N3)
        r["new_relation_rate"] = len(new) / len(N3) if N3 else np.nan
        r["new_rel_per_paper"] = len(new) / vol[y] if vol[y] else np.nan
        r["neigh_growth"] = math.log((len(N3) + 1) / (len(N3p) + 1))
        r["novelty"] = len(N[y] - seen_before) / len(N[y]) if N[y] else np.nan
        seen_before |= N[y]
        # Baselga raw
        prev = N.get(y - 1, set())
        sor, sim, sne = lm.baselga(prev, N[y]) if (prev or N[y]) and vol.get(y - 1, 0) > 0 and vol[y] > 0 else (np.nan,) * 3
        r.update(beta_sor_raw=sor, beta_sim_raw=sim, beta_sne_raw=sne, sne_share_raw=lm.sne_share(sor, sne))
        # Baselga rarefied (m=10 primary, m=5 sensitivity)
        for m, suf in ((rs, "rar"), (S["rarefy_m_sensitivity"], "rar5")):
            vals = []
            if y - 1 >= 2000 and vol[y - 1] >= m and vol[y] >= m:
                d1 = lm.rarefied_draws(vol[y - 1], m, S["rarefy_draws"], lm.stable_seed(cid, y - 1, "B", m, "a"))
                d2 = lm.rarefied_draws(vol[y], m, S["rarefy_draws"], lm.stable_seed(cid, y, "B", m, "b"))
                tp, tc = tags_y[y - 1], tags_y[y]
                for a, b in zip(d1, d2):
                    vals.append(lm.baselga(_union([tp[i] for i in a]), _union([tc[i] for i in b])))
            if vals:
                arr = np.array(vals, dtype=float)
                msor, msim, msne = np.nanmean(arr, axis=0)
                r.update({f"beta_sor_{suf}": msor, f"beta_sim_{suf}": msim, f"beta_sne_{suf}": msne,
                          f"sne_share_{suf}": lm.sne_share(msor, msne)})
            else:
                r.update({f"beta_sor_{suf}": np.nan, f"beta_sim_{suf}": np.nan, f"beta_sne_{suf}": np.nan,
                          f"sne_share_{suf}": np.nan})
        cache[y] = r
        # snapshot metrics
        p = pmd.get(y)
        for k in PM_COLS:
            r[k] = getattr(p, k) if p is not None else np.nan
        r["cross_comm_flag"] = bool(r["cross_comm_flag"]) if p is not None and r["cross_comm_flag"] == r["cross_comm_flag"] else False
        pc = int(r["plural_comm_raw"]) if p is not None and np.isfinite(r["plural_comm_raw"]) else -1
        r["comm_pid"] = pid_map.get((y, pc), -1) if pc >= 0 else -1
        r["closure_raw"] = math.log1p(r["closure_obs"]) if np.isfinite(r["closure_obs"]) else np.nan
        # disciplinary (3-yr window, all types, known subfield)
        wp = papers[(papers.year >= y - 2) & (papers.year <= y) & (papers.subfield >= 0)]
        sc = wp.subfield.value_counts().to_dict()
        r["subfield_count"] = len(sc)
        r["H"] = lm.shannon(sc.values()) if sc else np.nan
        r["RS"] = lm.rao_stirling(sc, dist_matrix=D, index=sidx) if sc else np.nan
        subs_arr = wp.subfield.values
        dr = lm.rarefied_draws(len(subs_arr), rs, S["rarefy_draws"], lm.stable_seed(cid, y, "H"))
        r["H_rar"] = float(np.nanmean([lm.shannon(pd.Series(subs_arr[d]).value_counts().values) for d in dr])) if dr else np.nan
        # yearly concept-subfield bipartite (all types, incl. unknown as -1 kept out of incidence)
        yp = by_year[y]
        for d_, n in yp.subfield.value_counts().items():
            den = totals[str(y)]["subfield"].get(str(int(d_))) if d_ >= 0 else None
            bip.append(dict(concept_id=cid, year=y, subfield=int(d_), n=int(n),
                            inc_per_1e4=(1e4 * n / den) if den else np.nan))
        rows.append(r)
    # derived temporal differences / slopes (all use <= y)
    df = pd.DataFrame(rows)
    if df.empty:
        return [], bip
    df = df.sort_values("year").reset_index(drop=True)
    byy = df.set_index("year")
    def lag(col: str, k: int) -> pd.Series:
        return df.year.map(lambda yy: byy[col].get(yy - k, np.nan))
    df["strength_growth"] = np.log((df.strength.fillna(0) + 1) / (lag("strength", 1).fillna(0) + 1))
    df["PA"] = np.log(df.strength.fillna(0) + 1) + df.strength_growth
    df["btw_change"] = df.btw_pct - lag("btw_pct", 1)
    df["pct_change1"] = df.pct - lag("pct", 1)
    pid_prev = lag("comm_pid", 1)
    df["comm_change"] = np.where((df.comm_pid >= 0) & (pid_prev >= 0), (df.comm_pid != pid_prev).astype(float), np.nan)
    for col in ("subfield_count", "H", "RS", "H_rar"):
        df[f"{col}_growth3"] = df[col] - lag(col, 3)
    for col, out in (("closure", "closure_slope"), ("P_rar", "P_slope"), ("sne_share_rar", "sne_slope_rar"),
                     ("beta_sim_rar", "sim_slope_rar"), ("sne_share_raw", "sne_slope_raw"), ("beta_sim_raw", "sim_slope_raw"),
                     ("sne_share_rar5", "sne_slope_rar5"), ("beta_sim_rar5", "sim_slope_rar5"), ("P_raw", "P_raw_slope")):
        vals = dict(zip(df.year, df[col]))
        df[out] = [_slope3({k: v for k, v in vals.items() if np.isfinite(v)}, yy) for yy in df.year]
    df["accretion_shift_rar"] = df.sne_slope_rar - df.sim_slope_rar
    df["accretion_shift_raw"] = df.sne_slope_raw - df.sim_slope_raw
    df["accretion_shift_rar5"] = df.sne_slope_rar5 - df.sim_slope_rar5
    return df.to_dict("records"), bip


def _worker(args: tuple) -> tuple[list, list]:
    cid, F, papers, pm, pid_map, totals, D, sidx = args
    return concept_indicators(cid, F, papers, pm, pid_map, totals, D, sidx)


def load_inputs() -> dict:
    pool = pd.read_parquet(C.WORK / "pool.parquet")
    cp = pd.read_parquet(C.WORK / "cp.parquet", columns=["concept_id", "year", "type", "subfield", "tags"])
    pm = pd.concat([pd.read_parquet(SNAP / f"pool_metrics_y{y}.parquet") for y in C.SPEC["years"]], ignore_index=True)
    pers = pd.read_parquet(C.WORK / "communities" / "persistent_ids.parquet")
    pid_map = {(int(a), int(b)): int(c) for a, b, c in zip(pers.year, pers.comm, pers.pid)}
    totals = json.loads((C.WORK / "totals.json").read_text())
    return dict(pool=pool, cp=cp, pm=pm, pid_map=pid_map, totals=totals)


def residualise(df: pd.DataFrame, cols: list[str], fit_mask: pd.Series) -> pd.DataFrame:
    """OLS residual of each indicator on log1p(vol) + log1p(vol3) + age, fitted on screen concept-years."""
    X = np.column_stack([np.ones(len(df)), np.log1p(df.vol), np.log1p(df.vol3), df.age.fillna(0)])
    for col in cols:
        y = df[col].values.astype(float)
        ok = np.isfinite(y) & fit_mask.values & np.isfinite(X).all(1)
        out = np.full(len(df), np.nan)
        if ok.sum() > 10:
            beta, *_ = np.linalg.lstsq(X[ok], y[ok], rcond=None)
            fin = np.isfinite(y)
            out[fin] = y[fin] - X[fin] @ beta
        df[f"{col}_res"] = out
    return df


@logger.catch(reraise=True)
def main() -> None:
    C.setup_logging("stage_indicators")
    C.set_ram_limit(24)
    t0 = time.time()
    D, sidx = build_rs_distance()
    inp = load_inputs()
    pool, cp, pm = inp["pool"], inp["cp"], inp["pm"]
    tasks = []
    for r in pool.itertuples(index=False):
        F = float(r.F) if r.F is not None and r.F == r.F else None
        tasks.append((r.concept_id, F, cp[cp.concept_id == r.concept_id], pm[pm.concept_id == r.concept_id],
                      inp["pid_map"], inp["totals"], D, sidx))
    rows, bip = [], []
    with ProcessPoolExecutor(max_workers=min(4, C.detect_cpus()), mp_context=mp.get_context("spawn")) as ex:
        futs = {ex.submit(_worker, t): t[0] for t in tasks}
        for i, f in enumerate(as_completed(futs)):
            a, b = f.result()
            rows.extend(a)
            bip.extend(b)
            if i % 20 == 0:
                logger.info(f"indicators {i+1}/{len(tasks)} ({time.time()-t0:.0f}s)")
    df = pd.DataFrame(rows)
    df = df.merge(pool[["concept_id", "fold", "F", "F_band", "origin_group", "sense_check_fail"]], on="concept_id", how="left")
    # ALT percentile: among pool (screen + reference) nodes with frame papers in the snapshot
    def alt_pct(g: pd.DataFrame) -> pd.Series:
        act = g.n_frame > 0
        ranks = g.loc[act, "strength"].rank(pct=True, method="average") * 100
        out = pd.Series(0.0, index=g.index)
        out[act] = ranks
        return out
    df["pct_alt"] = df.groupby("year", group_keys=False)[["n_frame", "strength"]].apply(alt_pct)
    res_cols = ["accretion_shift_rar", "closure", "P_rar", "accretion_shift_raw", "closure_raw", "P_raw", "sne_share_rar",
                "beta_sim_rar", "wmz", "btw_pct", "H", "RS", "subfield_count", "new_relation_rate", "neigh_growth",
                "novelty", "strength_growth", "pct", "H_rar"]
    df = residualise(df, res_cols, df.fold == "screen")
    df = df.sort_values(["concept_id", "year"]).reset_index(drop=True)
    df.to_parquet(IND / "concept_year_indicators.parquet", index=False)
    df.to_csv(IND / "concept_year_indicators.csv", index=False)
    bipdf = pd.DataFrame(bip)
    bipdf.to_parquet(CSB / "edges.parquet", index=False)
    # volume dependence check (rarefied should be weaker than raw)
    scr = df[df.fold == "screen"]
    chk = {}
    for a, b in (("P_raw", "P_rar"), ("beta_sim_raw", "beta_sim_rar"), ("sne_share_raw", "sne_share_rar"), ("H", "H_rar"),
                 ("accretion_shift_raw", "accretion_shift_rar"), ("closure_raw", "closure")):
        chk[f"{a}_vs_logvol"] = float(scr[[a, "log_vol3"]].corr(method="spearman").iloc[0, 1])
        chk[f"{b}_vs_logvol"] = float(scr[[b, "log_vol3"]].corr(method="spearman").iloc[0, 1])
    na = {c: float(scr.loc[(scr.age >= 0) & (scr.year <= 2015), c].isna().mean()) for c in
          ("beta_sim_rar", "P_rar", "beta_sim_rar5", "P_rar_m5", "closure", "H_rar")}
    summ = dict(n_rows=len(df), n_concepts=int(df.concept_id.nunique()), n_bipartite_rows=len(bipdf),
                volume_spearman=chk, na_share_pre2016_age_ge0=na, secs=round(time.time() - t0, 1))
    (IND / "indicator_summary.json").write_text(json.dumps(summ, indent=1))
    logger.info(f"indicators done: {summ}")


if __name__ == "__main__":
    main()
