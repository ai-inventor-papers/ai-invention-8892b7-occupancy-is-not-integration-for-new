"""Step 4: vendored per-(concept, year) indicators on the hydrated corpus, the reproduction gate, E_up labels.

Held-out concepts get indicators with data <= 2015 only (max_year, the vendored leakage switch).
Reproduction: (i) DS5 inputs vs exp_3's published indicators on the 123 iteration-1 screen concepts x 2000..2019;
(ii) code equality: the same code on exp_3's DS1-derived c-papers must give r >= 0.999.
"""
from __future__ import annotations

import json
import math
import multiprocessing as mp
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import numpy as np
import pandas as pd
from loguru import logger

import common as K
from common import OUT, RSD, SPEC, T_MAX_SCREEN, WORK

IND = OUT / "indicators"
REP = OUT / "reproduction"
REP_COLS = ["closure", "closure_obs", "closure_nK", "P_raw", "P_rar", "wmz", "new_relation_rate", "novelty", "beta_sim_rar",
            "n_neigh3", "vol", "vol3", "log_vol3", "H", "H_rar", "RS", "subfield_count", "burst_state", "strength", "growth3"]


def load_rs() -> tuple[np.ndarray, dict]:
    r = pd.read_parquet(RSD)
    subs = np.sort(r.subfield_i.unique())
    sidx = {int(s): i for i, s in enumerate(subs)}
    D = np.zeros((len(subs), len(subs)))
    D[[sidx[int(a)] for a in r.subfield_i], [sidx[int(b)] for b in r.subfield_j]] = r.d.values.astype(np.float64)
    return D, sidx


def _worker(args: tuple) -> list:
    import stage_indicators as si
    cid, F, papers, pm, pid_map, totals, D, sidx, max_year = args
    rows, _ = si.concept_indicators(cid, F, papers, pm, pid_map, totals, D, sidx, max_year=max_year)
    return rows


def compute(pool: pd.DataFrame, cp_path: Path, pm_dir: Path, heldout: set, workers: int) -> pd.DataFrame:
    cp = pd.read_parquet(cp_path, columns=["concept_id", "year", "type", "subfield", "tags"])
    pm = pd.concat([pd.read_parquet(pm_dir / f"pool_metrics_y{y}.parquet") for y in SPEC["years"]], ignore_index=True)
    pers = pd.read_parquet(K.COMM / "persistent_ids.parquet")
    pid_map = {(int(a), int(b)): int(c) for a, b, c in zip(pers.year, pers.comm, pers.pid)}
    totals = json.loads((WORK / "totals.json").read_text())
    D, sidx = load_rs()
    cpg = dict(tuple(cp.groupby("concept_id")))
    pmg = dict(tuple(pm.groupby("concept_id")))
    tasks = []
    for r in pool.itertuples(index=False):
        F = float(r.F) if r.F is not None and r.F == r.F else None
        tasks.append((r.concept_id, F, cpg.get(r.concept_id, cp.iloc[0:0]), pmg.get(r.concept_id, pm.iloc[0:0]),
                      pid_map, totals, D, sidx, T_MAX_SCREEN if r.concept_id in heldout else None))
    rows, t0 = [], time.time()
    with ProcessPoolExecutor(max_workers=workers, mp_context=mp.get_context("spawn")) as ex:
        futs = {ex.submit(_worker, t): t[0] for t in tasks}
        for i, f in enumerate(as_completed(futs)):
            rows.extend(f.result())
            if i % 50 == 0:
                logger.info(f"indicators {i + 1}/{len(tasks)} ({time.time() - t0:.0f}s)")
    df = pd.DataFrame(rows)

    def alt_pct(g: pd.DataFrame) -> pd.Series:
        act = g.n_frame > 0
        out = pd.Series(0.0, index=g.index)
        out[act] = g.loc[act, "strength"].rank(pct=True, method="average") * 100
        return out
    df["pct_alt"] = df.groupby("year", group_keys=False)[["n_frame", "strength"]].apply(alt_pct)
    return df.sort_values(["concept_id", "year"]).reset_index(drop=True)


def compare(new: pd.DataFrame, ref: pd.DataFrame, ids: set, years: range) -> pd.DataFrame:
    a = new[new.concept_id.isin(ids) & new.year.isin(years)]
    b = ref[ref.concept_id.isin(ids) & ref.year.isin(years)]
    m = a.merge(b, on=["concept_id", "year"], suffixes=("", "_ref"))
    out = []
    for c in REP_COLS:
        x, y = m[c].astype(float), m[f"{c}_ref"].astype(float)
        both = x.notna() & y.notna()
        na_agree = float(((x.isna()) == (y.isna())).mean())
        xs, ys = x[both], y[both]
        r = float(np.corrcoef(xs, ys)[0, 1]) if both.sum() > 2 and xs.std() > 0 and ys.std() > 0 else math.nan
        rho = float(xs.rank().corr(ys.rank())) if both.sum() > 2 else math.nan
        out.append(dict(column=c, n=int(both.sum()), n_rows=len(m), pearson_r=r, spearman=rho,
                        max_abs_diff=float((xs - ys).abs().max()) if both.any() else math.nan,
                        share_equal_1e6=float(((xs - ys).abs() <= 1e-6 * np.maximum(1, ys.abs())).mean()) if both.any() else math.nan,
                        na_pattern_agreement=na_agree))
    return pd.DataFrame(out)


def leakage_check(df: pd.DataFrame, pool: pd.DataFrame) -> None:
    """Vendored leakage test: 5 random screen (c, y) recomputed with all data after y removed -> identical row."""
    import stage_indicators as si
    cp = pd.read_parquet(WORK / "cp.parquet", columns=["concept_id", "year", "type", "subfield", "tags"])
    pm = pd.concat([pd.read_parquet(WORK / "pool_metrics" / f"pool_metrics_y{y}.parquet") for y in SPEC["years"]])
    pers = pd.read_parquet(K.COMM / "persistent_ids.parquet")
    pid_map = {(int(a), int(b)): int(c) for a, b, c in zip(pers.year, pers.comm, pers.pid)}
    totals = json.loads((WORK / "totals.json").read_text())
    D, sidx = load_rs()
    scr = df[(df.fold == "screen") & (df.year >= 2005) & (df.year <= T_MAX_SCREEN)]
    out = []
    for r in scr.sample(5, random_state=3).itertuples(index=False):
        F = float(pool.set_index("concept_id").loc[r.concept_id, "F"])
        rows, _ = si.concept_indicators(r.concept_id, F, cp[cp.concept_id == r.concept_id], pm[pm.concept_id == r.concept_id],
                                        pid_map, totals, D, sidx, max_year=int(r.year))
        a = [x for x in rows if x["year"] == r.year][0]
        b = df[(df.concept_id == r.concept_id) & (df.year == r.year)].iloc[0]
        diff = [k for k, v in a.items() if k in b.index and not (v == b[k] or (pd.isna(v) and pd.isna(b[k])))]
        out.append(dict(concept_id=r.concept_id, year=int(r.year), identical=not diff, differing=diff))
    K.write_json(REP / "leakage_check.json", out)
    assert all(x["identical"] for x in out), out
    logger.info("leakage check: 5/5 truncated recomputations identical")


def run(workers: int = 4) -> None:
    IND.mkdir(parents=True, exist_ok=True)
    REP.mkdir(parents=True, exist_ok=True)
    heldout = K.load_sealed_ids()
    pool = pd.read_parquet(WORK / "pool.parquet")
    df = compute(pool, WORK / "cp.parquet", WORK / "pool_metrics", heldout, workers)
    # xcomm / openness columns from the attach stage (not produced by the vendored code)
    pm = pd.concat([pd.read_parquet(WORK / "pool_metrics" / f"pool_metrics_y{y}.parquet",
                                    columns=["concept_id", "year", "constraint", "esize", "esize_norm", "ego_deg",
                                             "xcomm_obs", "xcomm_null", "xcomm_exc", "xcomm_n_pairs", "closure_exp"])
                    for y in SPEC["years"]], ignore_index=True)
    df = df.merge(pm, on=["concept_id", "year"], how="left")
    assert df[df.concept_id.isin(heldout)].year.max() <= T_MAX_SCREEN
    df = df.merge(pool[["concept_id", "fold", "F", "F_band", "origin_group", "sense_check_fail", "route",
                        "hydration_batch", "in_MAIN", "in_STRICT", "in_SENSITIVITY", "iter1_screen"]],
                  on="concept_id", how="left")
    df.to_parquet(IND / "concept_year_indicators_hyd.parquet", index=False)
    leakage_check(df, pool)
    logger.info(f"indicators: {len(df)} rows, {df.concept_id.nunique()} concepts")

    # ---- reproduction gate
    ref = pd.read_parquet(K.REF_IND)
    old = pd.read_parquet(K.EXP3_POOL)
    ids123 = set(old.loc[old.fold == "screen", "concept_id"])
    rep = compare(df, ref, ids123, range(2000, 2020))
    rep.to_csv(REP / "reproduction_check.csv", index=False)
    # (ii) code equality on exp_3's DS1-derived inputs (145 concepts)
    old_pool = old.assign(F=old.F.astype(float))
    df1 = compute(old_pool, K.EXP3_CP, WORK / "pool_metrics_ds1", set(), workers)
    rep1 = compare(df1, ref, ids123, range(2000, 2020))
    rep1.to_csv(REP / "code_equality_ds1.csv", index=False)
    # (iii) direct pool-metric comparison with exp_3's own attachment (DS1 inputs)
    pmc = []
    for y in SPEC["years"]:
        a = pd.read_parquet(WORK / "pool_metrics_ds1" / f"pool_metrics_y{y}.parquet")
        b = pd.read_parquet(K.SNAP / f"pool_metrics_y{y}.parquet")
        m = a.merge(b, on="concept_id", suffixes=("", "_x3"))
        ok = m[["closure", "closure_x3"]].dropna()
        pmc.append(dict(year=y, n=len(ok), max_abs_diff_closure=float((ok.closure - ok.closure_x3).abs().max()) if len(ok) else None,
                        pct_max_abs_diff=float((m.pct - m.pct_x3).abs().max())))
    # (iv) paper-set drift DS5 vs DS1 for the 123
    c5 = pd.read_parquet(WORK / "cp.parquet", columns=["concept_id", "work_id", "year", "frame"])
    c1 = pd.read_parquet(K.EXP3_CP, columns=["concept_id", "work_id", "year", "frame"])
    c5, c1 = c5[c5.concept_id.isin(ids123)], c1[c1.concept_id.isin(ids123)]
    s5 = set(zip(c5.concept_id, c5.work_id))
    s1 = set(zip(c1.concept_id, c1.work_id))
    per = []
    for cid in sorted(ids123):
        a5 = {w for c, w in s5 if c == cid}
        a1 = {w for c, w in s1 if c == cid}
        if a5 != a1:
            per.append(dict(concept_id=cid, n_ds5=len(a5), n_ds1=len(a1), only_ds5=len(a5 - a1), only_ds1=len(a1 - a5)))
    fr5 = c5[c5.frame].groupby(["concept_id", "year"]).size()
    fr1 = c1[c1.frame].groupby(["concept_id", "year"]).size()
    frc = pd.concat([fr5.rename("ds5"), fr1.rename("ds1")], axis=1).fillna(0)
    gate_r = float(rep.set_index("column").loc["closure", "pearson_r"])
    code_r = float(rep1.set_index("column").loc["closure", "pearson_r"])
    summ = dict(gate_rule="r(closure) >= 0.99 on the 123 iteration-1 screen concepts x 2000..2019 (DS5 inputs vs exp_3)",
                r_closure_ds5=gate_r, gate_passed=bool(gate_r >= 0.99),
                code_equality_rule="r(closure) >= 0.999 with exp_3's DS1-derived c-papers",
                r_closure_ds1=code_r, code_equality_passed=bool(code_r >= 0.999),
                pool_metric_direct=pmc,
                n_concepts_with_changed_paper_sets=len(per), changed_paper_sets=per,
                frame_count_cells=len(frc), frame_count_cells_equal=int((frc.ds5 == frc.ds1).sum()),
                note="betweenness is not recomputed (NaN); strength percentile pct differs by design because the attached "
                     "pool now has 426 concepts (exp_3: 145), so pct is not part of the gate.",
                ds5=rep.to_dict("records"), ds1=rep1.to_dict("records"))
    K.write_json(REP / "reproduction_check.json", summ)
    logger.info(f"REPRODUCTION: r(closure) DS5 {gate_r:.5f} (gate {'PASS' if gate_r >= 0.99 else 'FAIL'}); "
                f"DS1 code equality {code_r:.6f}; changed paper sets {len(per)}")
    if code_r < 0.999:
        raise RuntimeError("code equality failed: attachment bug; outcomes must not run")
    df1.to_parquet(WORK / "indicators_ds1.parquet", index=False)

    # ---- E_up labels (screen only; vendored build_labels)
    import analysis_event as ae
    lp = pool[pool.fold.isin(["screen", "reference"])].copy()
    lp["F"] = lp.F.astype(float)
    lab, info = ae.build_labels(df, lp)
    up = ae.assign_groups(lab, "E_up")
    up.to_parquet(IND / "labels_screen.parquet", index=False)
    on = up.drop_duplicates("concept_id")
    K.write_json(IND / "labels_info.json", dict(info=info, E_up_onsets=int(on.onset.notna().sum()),
                                                  E_up_onset_counts=on.onset.dropna().astype(int).value_counts().sort_index().to_dict()))
    logger.info(f"E_up onsets (screen, 2008..2015): {int(on.onset.notna().sum())}")
