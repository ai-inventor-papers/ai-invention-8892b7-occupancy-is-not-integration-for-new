"""Step 4: per-(concept, year) indicators with the vendored stage_indicators.concept_indicators, plus the new
openness columns, the R1a turnover-residualised closure and the sealed held-out pass.

Outputs
  work/indicators_{repro_code,repro_data}.parquet                     reproduction modes
  results/indicators/concept_year_indicators_hydrated.parquet         active (screen + reference) rows, all columns
  results/indicators/r1a_betas.json                                   screen R1a / _res betas (label-free fit)
  sealed/concept_year_indicators_heldout_le2015.parquet (+ .sha256)   held-out rows, years <= 2015, screen betas
"""
from __future__ import annotations

import argparse
import json
import math
import multiprocessing as mp
import time
from concurrent.futures import ProcessPoolExecutor, as_completed

import numpy as np
import pandas as pd
from loguru import logger

import common as K

NEW_COLS = ["top_AS", "top_AS_prev", "closure_persist", "persist_n", "persist_overlap", "n_ego", "constraint", "effsize",
            "efficiency", "cdeg_diag", "xc_obs", "xc_exp", "xc_excess", "xc_n", "xc_merges", "n_all", "n_tags_frame"]
LABEL_LIKE = {"E", "E_up", "E_alt", "E_cg", "E3", "onset", "group", "futE", "label_col", "uptake_mean5", "pct_gain5"}
VENDOR_RES_COLS = ["accretion_shift_rar", "closure", "P_rar", "accretion_shift_raw", "closure_raw", "P_raw", "sne_share_rar",
                   "beta_sim_rar", "wmz", "btw_pct", "H", "RS", "subfield_count", "new_relation_rate", "neigh_growth",
                   "novelty", "strength_growth", "pct", "H_rar"]
NEW_RES_COLS = ["constraint", "xc_excess", "closure_persist", "cdeg_diag", "effsize", "efficiency", "xc_obs"]


def load_D() -> tuple[np.ndarray, dict]:
    rs = pd.read_parquet(K.EXP3 / "results" / "concept_subfield" / "rs_distance.parquet")
    subs = np.sort(rs.subfield_i.unique())
    sidx = {int(s): i for i, s in enumerate(subs)}
    D = rs.pivot(index="subfield_i", columns="subfield_j", values="d").loc[subs, subs].values.astype(float)
    assert D.shape == (len(subs), len(subs)) and np.allclose(D, D.T)
    return D, sidx


def pid_map() -> dict:
    pers = pd.read_parquet(K.EXP3 / "work" / "communities" / "persistent_ids.parquet")
    return {(int(a), int(b)): int(c) for a, b, c in zip(pers.year, pers.comm, pers.pid)}


def _worker(args):
    import stage_indicators as SI
    cid, F, papers, pm, pmap, totals, D, sidx, max_year = args
    rows, _ = SI.concept_indicators(cid, F, papers, pm, pmap, totals, D, sidx, max_year=max_year)
    return rows


def mode_config(mode: str) -> dict:
    if mode == "repro_code":
        return dict(pool=pd.read_parquet(K.EXP3 / "work" / "pool.parquet"), cp=K.EXP3 / "work" / "cp.parquet",
                    pm_dir=K.WORK / "attach" / "repro_code", pm_fmt="pool_metrics_v3_y{y}.parquet",
                    totals=K.EXP3 / "work" / "totals.json", max_year=None)
    if mode == "repro_data":
        return dict(pool=pd.read_parquet(K.EXP3 / "work" / "pool.parquet"), cp=K.WORK / "cp_active.parquet",
                    pm_dir=K.WORK / "attach" / "repro_data", pm_fmt="pool_metrics_v3_y{y}.parquet",
                    totals=K.WORK / "totals.json", max_year=None)
    if mode == "full":
        return dict(pool=pd.read_parquet(K.WORK / "pool_active.parquet"), cp=K.WORK / "cp_active.parquet",
                    pm_dir=K.WORK / "attach" / "full", pm_fmt="pool_metrics_v3_y{y}.parquet",
                    totals=K.WORK / "totals.json", max_year=None)
    if mode == "sealed":
        return dict(pool=pd.read_parquet(K.WORK / "pool_heldout.parquet"), cp=K.SEALED / "cp_heldout.parquet",
                    pm_dir=K.SEALED / "attach", pm_fmt="pool_metrics_heldout_y{y}.parquet",
                    totals=K.WORK / "totals.json", max_year=K.SPEC3["sealed_max_year"])
    raise ValueError(mode)


def raw_indicators(mode: str, workers: int, ids: list | None = None) -> pd.DataFrame:
    cfg = mode_config(mode)
    pool = cfg["pool"]
    if ids is not None:
        pool = pool[pool.concept_id.isin(set(ids))]
    years = range(2000, (cfg["max_year"] or 2024) + 1)
    pm = pd.concat([pd.read_parquet(cfg["pm_dir"] / cfg["pm_fmt"].format(y=y)) for y in years], ignore_index=True)
    cp = pd.read_parquet(cfg["cp"], columns=["concept_id", "year", "type", "subfield", "tags"])
    totals = json.loads(cfg["totals"].read_text())
    D, sidx = load_D()
    pmap = pid_map()
    tasks = []
    for r in pool.itertuples(index=False):
        F = float(r.F) if r.F is not None and r.F == r.F else None
        tasks.append((r.concept_id, F, cp[cp.concept_id == r.concept_id], pm[pm.concept_id == r.concept_id], pmap, totals,
                      D, sidx, cfg["max_year"]))
    rows = []
    t0 = time.time()
    with ProcessPoolExecutor(max_workers=workers, mp_context=mp.get_context("spawn")) as ex:
        futs = [ex.submit(_worker, t) for t in tasks]
        for i, f in enumerate(as_completed(futs)):
            rows.extend(f.result())
            if i % 50 == 0:
                logger.info(f"[{mode}] indicators {i + 1}/{len(tasks)} ({time.time() - t0:.0f}s)")
    df = pd.DataFrame(rows)
    keep = ["concept_id", "fold", "F", "F_band", "origin_group", "sense_check_fail"]
    extra = [c for c in ("route", "hydration_batch", "old_new", "MAIN", "STRICT", "SENS") if c in pool.columns]
    df = df.merge(pool[keep + extra], on="concept_id", how="left")
    # new openness columns from the attachment
    newc = pm[["concept_id", "year"] + [c for c in NEW_COLS if c in pm.columns]]
    df = df.merge(newc, on=["concept_id", "year"], how="left")
    return df


def alt_pct(df: pd.DataFrame) -> pd.Series:
    """Vendored ALT percentile among pool nodes with frame papers in the snapshot."""
    def f(g: pd.DataFrame) -> pd.Series:
        act = g.n_frame > 0
        ranks = g.loc[act, "strength"].rank(pct=True, method="average") * 100
        out = pd.Series(0.0, index=g.index)
        out[act] = ranks
        return out
    return df.groupby("year", group_keys=False)[["n_frame", "strength"]].apply(f)


def add_lags(df: pd.DataFrame) -> pd.DataFrame:
    df = df.sort_values(["concept_id", "year"]).reset_index(drop=True)
    for col, out in (("wmz", "d_wmz"), ("closure", "d_closure"), ("constraint", "d_constraint")):
        prev = df.groupby("concept_id")[[col, "year"]].shift(1)
        ok = prev.year == df.year - 1
        df[out] = np.where(ok, df[col] - prev[col], np.nan)
    return df


# ----------------------------------------------------------------------------- R1a (label-free)
def _design(df: pd.DataFrame, covs: list[str], means: dict, fill: bool) -> tuple[np.ndarray, list[str]]:
    cols, names = [np.ones(len(df))], ["const"]
    for c in covs:
        x = df[c].astype(float).values
        if fill:
            na = ~np.isfinite(x)
            cols.append(np.where(na, means[c], x))
            names.append(c)
            if means.get(f"{c}__has_na"):
                cols.append(na.astype(float))
                names.append(f"{c}_isNA")
        else:
            cols.append(x)
            names.append(c)
    return np.column_stack(cols), names


def r1a_fit(df: pd.DataFrame, fit_mask: np.ndarray, covs: list[str], fill: bool, target: str = "closure") -> dict:
    """OLS of `target` on the turnover covariates; fitted on screen concept-years only. NO label columns allowed."""
    bad = LABEL_LIKE & set(df.columns)
    assert not bad, f"label columns in R1a scope: {bad}"
    fm = fit_mask & np.isfinite(df[target].astype(float).values)
    means = {}
    for c in covs:
        x = df.loc[fm, c].astype(float)
        means[c] = float(x.mean())
        means[f"{c}__has_na"] = bool(x.isna().any()) if fill else False
    X, names = _design(df, covs, means, fill)
    ok = fm & np.isfinite(X).all(1)
    beta, *_ = np.linalg.lstsq(X[ok], df[target].astype(float).values[ok], rcond=None)
    return dict(beta=beta.tolist(), names=names, means=means, n_fit=int(ok.sum()), covs=covs, fill=fill, target=target)


def r1a_apply(df: pd.DataFrame, fit: dict) -> np.ndarray:
    X, names = _design(df, fit["covs"], fit["means"], fit["fill"])
    assert names == fit["names"]
    y = df[fit["target"]].astype(float).values
    out = np.full(len(df), np.nan)
    ok = np.isfinite(y) & np.isfinite(X).all(1)
    out[ok] = y[ok] - X[ok] @ np.asarray(fit["beta"])
    return out


def r1a_all(df: pd.DataFrame, fit_mask: np.ndarray, fits: dict | None = None) -> tuple[pd.DataFrame, dict]:
    covs = K.SPEC3["r1a_covariates"]
    covs_raw = [c if c != "beta_sim_rar" else "beta_sim_raw" for c in covs]
    if fits is None:
        fits = dict(closure_resT=r1a_fit(df, fit_mask, covs, True),
                    closure_resT_cc=r1a_fit(df, fit_mask, covs, False),
                    closure_resT_raw=r1a_fit(df, fit_mask, covs_raw, True))
    for k, f in fits.items():
        df[k] = r1a_apply(df, f)
    return df, fits


# ----------------------------------------------------------------------------- vendor-formula _res with exportable betas
def res_fit(df: pd.DataFrame, cols: list[str], fit_mask: np.ndarray) -> dict:
    X = np.column_stack([np.ones(len(df)), np.log1p(df.vol), np.log1p(df.vol3), df.age.fillna(0)])
    out = {}
    for col in cols:
        y = df[col].values.astype(float)
        ok = np.isfinite(y) & fit_mask & np.isfinite(X).all(1)
        if ok.sum() > 10:
            out[col] = np.linalg.lstsq(X[ok], y[ok], rcond=None)[0].tolist()
    return out


def res_apply(df: pd.DataFrame, betas: dict) -> pd.DataFrame:
    X = np.column_stack([np.ones(len(df)), np.log1p(df.vol), np.log1p(df.vol3), df.age.fillna(0)])
    for col, b in betas.items():
        y = df[col].values.astype(float)
        out = np.full(len(df), np.nan)
        fin = np.isfinite(y)
        out[fin] = y[fin] - X[fin] @ np.asarray(b)
        df[f"{col}_res"] = out
    return df


def screen_fit_mask(df: pd.DataFrame) -> np.ndarray:
    return ((df.fold == "screen") & (df.age >= -2)).values


def run_repro(mode: str, workers: int) -> pd.DataFrame:
    import stage_indicators as SI
    df = raw_indicators(mode, workers)
    df["pct_alt"] = alt_pct(df)
    df = SI.residualise(df, VENDOR_RES_COLS, df.fold == "screen")
    df = add_lags(df)
    df = df.sort_values(["concept_id", "year"]).reset_index(drop=True)
    df.to_parquet(K.WORK / f"indicators_{mode}.parquet", index=False)
    logger.info(f"[{mode}] {len(df)} rows, {df.concept_id.nunique()} concepts")
    return df


def run_full(workers: int) -> pd.DataFrame:
    import stage_indicators as SI
    df = raw_indicators("full", workers)
    df["pct_alt"] = alt_pct(df)
    df = SI.residualise(df, VENDOR_RES_COLS, df.fold == "screen")
    # vendor-formula betas (exported, applied to sealed rows); check identity with the vendored residualise
    betas = res_fit(df, VENDOR_RES_COLS + NEW_RES_COLS, (df.fold == "screen").values)
    chk = res_apply(df.copy(), {k: betas[k] for k in VENDOR_RES_COLS if k in betas})
    for c in VENDOR_RES_COLS:
        a, b = df[f"{c}_res"].values, chk[f"{c}_res"].values
        assert np.allclose(a[np.isfinite(a)], b[np.isfinite(a)], atol=1e-9), c
    df = res_apply(df, {k: betas[k] for k in NEW_RES_COLS if k in betas})
    df = add_lags(df)
    df, fits = r1a_all(df, screen_fit_mask(df))
    df = df.sort_values(["concept_id", "year"]).reset_index(drop=True)
    (K.RES / "indicators").mkdir(parents=True, exist_ok=True)
    df.to_parquet(K.RES / "indicators" / "concept_year_indicators_hydrated.parquet", index=False)
    K.write_json(K.RES / "indicators" / "r1a_betas.json", dict(r1a=fits, res_betas=betas,
                 res_formula="col ~ 1 + log1p(vol) + log1p(vol3) + age.fillna(0), fit on fold == screen (vendored)",
                 r1a_formula="closure ~ 1 + covariates (+ NA dummies), fit on screen concept-years with age >= -2"))
    na = {c: float(df.loc[(df.fold == "screen") & (df.age >= 0) & (df.year <= 2015), c].isna().mean())
          for c in ("closure", "closure_persist", "constraint", "xc_excess", "closure_resT", "closure_resT_cc", "beta_sim_rar", "H")}
    K.write_json(K.RES / "indicators" / "indicator_summary_v3.json",
                 dict(n_rows=len(df), n_concepts=int(df.concept_id.nunique()), na_share_screen_age_ge0_le2015=na,
                      r1a_n_fit={k: v["n_fit"] for k, v in fits.items()},
                      r1a_beta={k: dict(zip(v["names"], v["beta"])) for k, v in fits.items()}))
    logger.info(f"[full] {len(df)} rows; R1a n_fit {fits['closure_resT']['n_fit']}; NA shares {na}")
    return df


def run_sealed(workers: int) -> dict:
    """Held-out indicators, years <= 2015, with SCREEN betas. No value is logged."""
    import stage_indicators as SI  # noqa: F401
    df = raw_indicators("sealed", workers)
    # ALT percentile: insertion rank against the active pool distribution of the same year (never re-ranked)
    act = pd.read_parquet(K.RES / "indicators" / "concept_year_indicators_hydrated.parquet",
                          columns=["year", "n_frame", "strength"])
    pa = []
    for y, s, n in zip(df.year, df.strength, df.n_frame):
        a = np.sort(act.loc[(act.year == y) & (act.n_frame > 0), "strength"].values)
        if n > 0 and len(a):
            lo, hi = np.searchsorted(a, s, "left"), np.searchsorted(a, s, "right")
            pa.append(100.0 * (lo + 0.5 * (hi - lo) + 0.5) / (len(a) + 1))
        else:
            pa.append(0.0)
    df["pct_alt"] = pa
    rb = json.loads((K.RES / "indicators" / "r1a_betas.json").read_text())
    df = res_apply(df, rb["res_betas"])
    df = add_lags(df)
    df, _ = r1a_all(df, np.zeros(len(df), bool), fits=rb["r1a"])
    assert df.year.max() <= K.SPEC3["sealed_max_year"]
    df = df.sort_values(["concept_id", "year"]).reset_index(drop=True)
    p = K.SEALED / "concept_year_indicators_heldout_le2015.parquet"
    df.to_parquet(p, index=False)
    h = K.sha256_file(p)
    (K.SEALED / "concept_year_indicators_heldout_le2015.sha256").write_text(h + "\n")
    logger.info(f"[sealed] held-out indicators written: {len(df)} rows, {df.concept_id.nunique()} concepts (no values logged)")
    return dict(rows=len(df), concepts=int(df.concept_id.nunique()), sha256=h)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--modes", nargs="+", default=["repro_code", "repro_data", "full"])
    ap.add_argument("--workers", type=int, default=min(4, K.detect_cpus()))
    a = ap.parse_args()
    K.setup_logging("indicators3")
    K.set_ram_limit(26)
    for m in a.modes:
        t0 = time.time()
        if m in ("repro_code", "repro_data"):
            run_repro(m, a.workers)
        elif m == "full":
            run_full(a.workers)
        elif m == "sealed":
            run_sealed(a.workers)
        logger.info(f"indicators {m} done in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
