#!/usr/bin/env python3
"""STAGE 2: per concept-year indicators with the VENDORED iteration-2 stage_indicators.concept_indicators, plus the
diffusion channels this experiment adds (active-subfield counts, cumulative reach, rarefied Rao-Stirling / richness).

Reproduction gate: on the 123 iteration-2 screen concepts every downstream column is compared with
X3/results/indicators/concept_year_indicators.parquet (results/reproduction_check.json); closure r >= 0.99 required.
Output: results/indicators/concept_year_indicators_hyd.parquet.
"""
from __future__ import annotations

import json
import math
import multiprocessing as mp
import time
from concurrent.futures import ProcessPoolExecutor, as_completed

import numpy as np
import pandas as pd
from loguru import logger

from common import HELDOUT, RES, WORK, X3, YEARS, C, setup_logging, write_json

IND = RES / "indicators"
IND.mkdir(parents=True, exist_ok=True)


def load_rs() -> tuple[np.ndarray, dict]:
    """Fixed pre-period Rao-Stirling distance from iteration 2 (NOT rebuilt)."""
    d = pd.read_parquet(X3 / "results" / "concept_subfield" / "rs_distance.parquet")
    subs = np.sort(d.subfield_i.unique())
    sidx = {int(s): i for i, s in enumerate(subs)}
    D = np.zeros((len(subs), len(subs)))
    D[[sidx[int(a)] for a in d.subfield_i], [sidx[int(b)] for b in d.subfield_j]] = d.d.values.astype(float)
    return D, sidx


def extra_channels(cid: str, papers: pd.DataFrame, years: list[int], D: np.ndarray, sidx: dict) -> list[dict]:
    """Added diffusion channels; each uses data <= y only."""
    import lib_metrics as lm
    m, draws = C.SPEC["rarefy_m"], C.SPEC["rarefy_draws"]
    kn = papers[papers.subfield >= 0]
    out, seen, cum = [], set(), 0
    vol_y = papers.groupby("year").size().to_dict()
    for y in range(2000, max(years) + 1):
        cum += vol_y.get(y, 0)
        ky = kn[kn.year == y]
        seen |= set(ky.subfield.tolist())
        if y not in years:
            continue
        wp = kn[(kn.year >= y - 2) & (kn.year <= y)]
        vc = wp.subfield.value_counts()
        subs_arr = wp.subfield.values
        dr = lm.rarefied_draws(len(subs_arr), m, draws, lm.stable_seed(cid, y, "RS"))
        rs_r, rich_r = np.nan, np.nan
        if dr:
            rsv, rch = [], []
            for d in dr:
                sc = pd.Series(subs_arr[d]).value_counts().to_dict()
                rsv.append(lm.rao_stirling(sc, dist_matrix=D, index=sidx))
                rch.append(len(sc))
            rs_r, rich_r = float(np.nanmean(rsv)) if np.isfinite(rsv).any() else np.nan, float(np.mean(rch))
        out.append(dict(concept_id=cid, year=y, active_subfields_3y=int((vc >= 2).sum()),
                        active_subfields_1y=int(ky.subfield.nunique()), cum_subfields=len(seen), cum_vol=cum,
                        RS_rar=rs_r, richness_rar=rich_r))
    return out


def _worker(args: tuple) -> tuple[list, list, list]:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "vendor"))
    import stage_indicators as SI
    cid, F, papers, pm, pid_map, totals, D, sidx = args
    rows, bip = SI.concept_indicators(cid, F, papers, pm, pid_map, totals, D, sidx)
    years = sorted({int(r["year"]) for r in rows})
    ex = extra_channels(cid, papers, years, D, sidx) if years else []
    return rows, bip, ex


def pct_rank_rows(df: pd.DataFrame, mask: pd.Series) -> pd.Series:
    """Iteration-2 ALT percentile: rank of strength among the masked rows with frame papers, per year."""
    out = pd.Series(np.nan, index=df.index)
    sub = df[mask]
    for _, g in sub.groupby("year"):
        act = g.n_frame > 0
        out.loc[g.index] = 0.0
        out.loc[g.index[act]] = g.loc[act, "strength"].rank(pct=True, method="average") * 100
    return out


def reproduction_check(df: pd.DataFrame, pool: pd.DataFrame) -> dict:
    x3 = pd.read_parquet(X3 / "results" / "indicators" / "concept_year_indicators.parquet")
    x3 = x3[x3.fold == "screen"]
    old = set(x3.concept_id)
    m = df[df.concept_id.isin(old)].merge(x3, on=["concept_id", "year"], suffixes=("", "_x3"))
    pairs = {c: c for c in ["strength", "closure", "P_raw", "P_rar", "wmz", "btw_pct", "comm_pid", "H", "H_rar", "RS",
                            "subfield_count", "strength_growth", "neigh_growth", "beta_sim_rar", "vol", "pct"]}
    pairs.update({"pct_alt_iter2": "pct_alt", "pct_iter2": "pct"})
    rep = dict(n_concepts=int(m.concept_id.nunique()), n_rows=len(m), n_rows_x3=int(len(x3)), columns={})
    for mine, theirs in pairs.items():
        a, b = m[mine].astype(float).values, m[f"{theirs}_x3"].astype(float).values
        ok = np.isfinite(a) & np.isfinite(b)
        rep["columns"][f"{mine}~{theirs}"] = dict(
            n=int(ok.sum()), pearson_r=float(np.corrcoef(a[ok], b[ok])[0, 1]) if ok.sum() > 2 and np.std(a[ok]) > 0 else None,
            max_abs_diff=float(np.max(np.abs(a[ok] - b[ok]))) if ok.sum() else None,
            share_equal=float(np.mean(np.isclose(a[ok], b[ok], rtol=1e-6, atol=1e-9))) if ok.sum() else None,
            nan_pattern_mismatch=int((np.isfinite(a) != np.isfinite(b)).sum()))
    # concepts whose c-paper set differs between iteration 2 (dataset_1) and the hydrated corpus (dataset_5)
    cp_old = pd.read_parquet(X3 / "work" / "cp.parquet", columns=["concept_id", "work_id"])
    cp_new = pd.read_parquet(WORK / "cp_hyd.parquet", columns=["concept_id", "work_id"])
    jac = {}
    for c in sorted(old):
        a, b = set(cp_old.work_id[cp_old.concept_id == c]), set(cp_new.work_id[cp_new.concept_id == c])
        jac[c] = len(a & b) / max(1, len(a | b))
    rep["work_set_jaccard"] = dict(min=float(min(jac.values())), share_equal=float(np.mean([v == 1.0 for v in jac.values()])),
                                   n_below_0_98=int(sum(v < 0.98 for v in jac.values())))
    r_cl = rep["columns"]["closure~closure"]["pearson_r"]
    rep["gate"] = dict(rule="closure pearson r >= 0.99 on the 123 iteration-2 screen concepts", closure_r=r_cl,
                       passed=bool(r_cl is not None and r_cl >= 0.99))
    return rep


@logger.catch(reraise=True)
def main(workers: int = 4) -> None:
    setup_logging("indicators")
    C.set_ram_limit(24)
    t0 = time.time()
    D, sidx = load_rs()
    pool = pd.read_parquet(WORK / "pool_active.parquet")
    C.assert_not_sealed(pool.concept_id)
    cp = pd.read_parquet(WORK / "cp_hyd.parquet", columns=["concept_id", "year", "type", "subfield", "tags"])
    pm = pd.concat([pd.read_parquet(WORK / "attach" / f"pool_metrics_y{y}.parquet") for y in YEARS], ignore_index=True)
    pers = pd.read_parquet(X3 / "work" / "communities" / "persistent_ids.parquet")
    pid_map = {(int(a), int(b)): int(c) for a, b, c in zip(pers.year, pers.comm, pers.pid)}
    totals = json.loads((WORK / "totals.json").read_text())
    cp_by = {c: g for c, g in cp.groupby("concept_id")}
    pm_by = {c: g for c, g in pm.groupby("concept_id")}
    tasks = []
    for r in pool.itertuples(index=False):
        F = float(r.F) if r.F is not None and r.F == r.F else None
        tasks.append((r.concept_id, F, cp_by.get(r.concept_id, cp.iloc[:0]), pm_by.get(r.concept_id, pm.iloc[:0]),
                      pid_map, totals, D, sidx))
    rows, bip, extra = [], [], []
    with ProcessPoolExecutor(max_workers=workers, mp_context=mp.get_context("spawn")) as ex:
        futs = {ex.submit(_worker, t): t[0] for t in tasks}
        for i, f in enumerate(as_completed(futs)):
            a, b, e = f.result()
            rows.extend(a)
            bip.extend(b)
            extra.extend(e)
            if i % 50 == 0:
                logger.info(f"indicators {i + 1}/{len(tasks)} ({time.time() - t0:.0f}s)")
    df = pd.DataFrame(rows).merge(pd.DataFrame(extra), on=["concept_id", "year"], how="left")
    keep_pm = pm[["concept_id", "year", "pct_alt", "pct_iter2", "cw_all_json", "cw_frame_json", "n_all"]]
    df = df.merge(keep_pm, on=["concept_id", "year"], how="left")
    df = df.merge(pool[["concept_id", "fold", "arm", "F", "F_band", "origin_group", "origin_subfield_id", "route",
                        "sense_check_fail", "MAIN", "STRICT", "iter2_active"]], on="concept_id", how="left")
    df["pct_alt_iter2"] = pct_rank_rows(df, df.iter2_active)
    df = df.sort_values(["concept_id", "year"]).reset_index(drop=True)
    df.to_parquet(IND / "concept_year_indicators_hyd.parquet", index=False)
    pd.DataFrame(bip).to_parquet(IND / "concept_subfield_edges_hyd.parquet", index=False)
    if HELDOUT:
        logger.info(f"held-out indicators: {len(df)} rows, {df.concept_id.nunique()} concepts (no reproduction gate)")
        return
    rep = reproduction_check(df, pool)
    write_json(RES / "reproduction_check.json", rep)
    logger.info(f"indicators: {len(df)} rows, {df.concept_id.nunique()} concepts in {time.time() - t0:.0f}s; "
                f"gate {rep['gate']}")
    if not rep["gate"]["passed"]:
        raise RuntimeError(f"REPRODUCTION GATE FAILED: {rep['gate']}")


if __name__ == "__main__":
    main()
