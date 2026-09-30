"""Main-pool-aligned indicators (sibling iteration-2 main-pool RQ1 run, gen_art_experiment_3).

The main-pool run was found at run time (see prereg_spec.json -> main_pool_alignment). Its pre-named precursors are
accretion_shift_rar, closure and P_rar, and it labels E / E_alt / E_up. This module recomputes those columns for
the MeSH focal concepts with the main pool's own metric functions (vendored read-only copy of its lib_metrics.py,
sha256 recorded) and its constants (spec.json): year-y neighbour sets, rarefaction m=10 with 50 draws and
stable_seed(cid, y, ...), 3-year OLS slopes, top-20 association-strength closure against the weighted Chung-Lu
expectation with eps = min edge weight and >= 5 neighbours, frame-type papers for closure, all types for
participation and Baselga. Communities and background weights come from THIS artifact's snapshots.
Outcome-blind: every value at (c, y) uses works with year <= y and snapshot y only."""

from __future__ import annotations

import math
from collections import Counter

import numpy as np
import pandas as pd
import scipy.sparse as sp
from loguru import logger

import load
from vendor import mainpool_lib_metrics as lm

MP = {"rarefy_m": 10, "rarefy_m_sensitivity": 5, "rarefy_draws": 50, "topk_closure": 20, "closure_min_neighbours": 5,
      "frame_types": {"article", "review", "preprint", "book-chapter"}}
SNAP = load.RESULTS / "snapshots"


def _union(tag_lists) -> set:
    out: set = set()
    for t in tag_lists:
        out.update(t)
    return out


def _slope3(vals: dict, y: int) -> float:
    xs = [yy for yy in (y - 2, y - 1, y) if yy in vals]
    return lm.ols_slope(xs, [vals[yy] for yy in xs])


def _comm_weights(tag_counts: dict, idx: dict, memb: np.ndarray) -> dict:
    out: Counter = Counter()
    for j, x in tag_counts.items():
        p = idx.get(j)
        if p is not None and memb[p] >= 0:
            out[int(memb[p])] += x
    return dict(out)


def _count(tag_lists) -> dict:
    c: Counter = Counter()
    for t in tag_lists:
        c.update(t)
    return dict(c)


def snapshot_metrics(concept_ids: list[str], years: list[int], works: pd.DataFrame, twins: dict) -> pd.DataFrame:
    """Per (c, y): main-pool closure, P_raw, P_rar, P_rar_m5 from snapshot y and the window works."""
    rows = []
    for y in years:
        nd = pd.read_parquet(SNAP / f"nodes_{y}.parquet")
        ed = pd.read_parquet(SNAP / f"edges_{y}.parquet")
        tags = nd.tag.to_numpy()
        idx = {int(t): i for i, t in enumerate(tags)}
        memb = nd.comm_local.to_numpy()
        W = nd.W_i.to_numpy(dtype=float)
        ii = ed.i.map(idx).to_numpy()
        jj = ed.j.map(idx).to_numpy()
        c = ed.W_ij.to_numpy(dtype=float)
        n = len(tags)
        Cw = sp.csr_matrix((np.r_[c, c], (np.r_[ii, jj], np.r_[jj, ii])), shape=(n, n))
        s = np.asarray(Cw.sum(axis=1)).ravel()
        S_total = float(s.sum())
        eps = float(c.min()) if len(c) else 1.0
        win = works[(works.year >= y - 2) & (works.year <= y)]
        for cid, g in win.groupby("concept_id"):
            tw = set(twins.get(cid, []))
            tl = [[t for t in ts if t not in tw] for ts in g.tags]
            fr = [[t for t in ts if t not in tw] for ts, wt in zip(g.tags, g.wtype) if wt in MP["frame_types"]]
            x_frame, x_all = _count(fr), _count(tl)
            r = {"concept_id": cid, "year": y, "n_frame": len(fr), "n_all": len(tl)}
            js = np.array([idx[j] for j in x_frame if j in idx], dtype=np.int64)
            closure = obs = exp = np.nan
            nK = 0
            if len(fr) and len(js):
                xs = np.array([x_frame[int(tags[p])] for p in js], dtype=float)
                AS_c = xs / (len(fr) * W[js])  # Wtot is a constant factor: ranking-invariant
                K = js[np.argsort(-AS_c, kind="stable")[: MP["topk_closure"]]]
                nK = len(K)
                if nK >= MP["closure_min_neighbours"]:
                    obs = float(Cw[K][:, K].sum() / 2.0)
                    exp = lm.chung_lu_expected(s[K], S_total)
                    closure = lm.closure_log_ratio(obs, exp, eps)
            r.update({"closure": closure, "closure_mp_obs": obs, "closure_mp_exp": exp, "closure_nK": nK,
                      "P_raw": lm.participation(_comm_weights(x_all, idx, memb))})
            for m, suf, key in ((MP["rarefy_m"], "P_rar", "P"), (MP["rarefy_m_sensitivity"], "P_rar_m5", "P5")):
                ds = lm.rarefied_draws(len(tl), m, MP["rarefy_draws"], lm.stable_seed(cid, y, key))
                if ds:
                    v = np.array([lm.participation(_comm_weights(_count([tl[i] for i in d]), idx, memb)) for d in ds])
                    r[suf] = float(np.nanmean(v)) if np.isfinite(v).any() else np.nan
                else:
                    r[suf] = np.nan
            rows.append(r)
        logger.debug(f"main-pool snapshot metrics {y}: {win.concept_id.nunique()} concepts")
    return pd.DataFrame(rows)


def turnover(cid: str, F: int, g: pd.DataFrame, twins: dict, years: list[int]) -> list[dict]:
    """Main-pool Baselga raw / rarefied on year-y neighbour sets and the 3-year-slope accretion shift."""
    tw = set(twins.get(cid, []))
    by = {y: [[t for t in ts if t not in tw] for ts in g.loc[g.year == y, "tags"]] for y in years}
    vol = {y: len(by[y]) for y in years}
    N = {y: _union(by[y]) for y in years}
    y_first = max(2000, F - 2)
    rows = []
    for y in years:
        if y < y_first:
            continue
        r = {"concept_id": cid, "year": y}
        prev = N.get(y - 1, set())
        if (prev or N[y]) and vol.get(y - 1, 0) > 0 and vol[y] > 0:
            sor, sim, sne = lm.baselga(prev, N[y])
        else:
            sor = sim = sne = np.nan
        r.update(beta_sor_raw=sor, beta_sim_raw=sim, beta_sne_raw=sne, sne_share_raw=lm.sne_share(sor, sne))
        for m, suf in ((MP["rarefy_m"], "rar"), (MP["rarefy_m_sensitivity"], "rar5")):
            vals = []
            if y - 1 >= years[0] and vol[y - 1] >= m and vol[y] >= m:
                d1 = lm.rarefied_draws(vol[y - 1], m, MP["rarefy_draws"], lm.stable_seed(cid, y - 1, "B", m, "a"))
                d2 = lm.rarefied_draws(vol[y], m, MP["rarefy_draws"], lm.stable_seed(cid, y, "B", m, "b"))
                for a, b in zip(d1, d2):
                    vals.append(lm.baselga(_union([by[y - 1][i] for i in a]), _union([by[y][i] for i in b])))
            if vals:
                msor, msim, msne = np.nanmean(np.array(vals, dtype=float), axis=0)
                r.update({f"beta_sor_{suf}": msor, f"beta_sim_{suf}": msim, f"beta_sne_{suf}": msne,
                          f"sne_share_{suf}": lm.sne_share(msor, msne)})
            else:
                r.update({f"beta_sor_{suf}": np.nan, f"beta_sim_{suf}": np.nan, f"beta_sne_{suf}": np.nan,
                          f"sne_share_{suf}": np.nan})
        rows.append(r)
    df = pd.DataFrame(rows)
    for col, out in (("sne_share_rar", "sne_slope_rar"), ("beta_sim_rar", "sim_slope_rar"),
                     ("sne_share_raw", "sne_slope_raw"), ("beta_sim_raw", "sim_slope_raw"),
                     ("sne_share_rar5", "sne_slope_rar5"), ("beta_sim_rar5", "sim_slope_rar5")):
        vals = {yy: v for yy, v in zip(df.year, df[col]) if np.isfinite(v)}
        df[out] = [_slope3(vals, yy) for yy in df.year]
    df["accretion_shift_rar"] = df.sne_slope_rar - df.sim_slope_rar
    df["accretion_shift_raw"] = df.sne_slope_raw - df.sim_slope_raw
    df["accretion_shift_rar5"] = df.sne_slope_rar5 - df.sim_slope_rar5
    return df.to_dict("records")


MP_COLS = ["closure", "closure_mp_obs", "closure_mp_exp", "closure_nK", "P_raw", "P_rar", "P_rar_m5", "n_frame", "n_all",
           "beta_sor_raw", "beta_sim_raw", "beta_sne_raw", "sne_share_raw", "beta_sim_rar", "beta_sne_rar",
           "sne_share_rar", "beta_sim_rar5", "sne_share_rar5", "accretion_shift_rar", "accretion_shift_raw",
           "accretion_shift_rar5"]
MP_RES = ["accretion_shift_rar", "closure", "P_rar", "accretion_shift_raw", "P_raw", "sne_share_rar", "beta_sim_rar"]


def add_mainpool_columns(df: pd.DataFrame, concepts: pd.DataFrame, years: list[int]) -> tuple[pd.DataFrame, dict]:
    import json
    twins = json.loads((load.INTER / "twins.json").read_text())
    works = pd.read_parquet(load.INTER / "mesh_works.parquet")
    works = works[works.primary & works.concept_id.isin(concepts.concept_id)].drop_duplicates(["concept_id", "work_id"])
    works = works[works.year.isin(years)]
    snap = snapshot_metrics(concepts.concept_id.tolist(), years, works, twins)
    trows = []
    for c in concepts.itertuples(index=False):
        trows.extend(turnover(c.concept_id, int(c.F), works[works.concept_id == c.concept_id], twins, years))
    turn = pd.DataFrame(trows)
    out = df.merge(snap, on=["concept_id", "year"], how="left").merge(
        turn[["concept_id", "year"] + [k for k in MP_COLS if k in turn.columns]], on=["concept_id", "year"], how="left")
    # main-pool matching volume: 3-year trailing all-type c-paper count
    out = out.sort_values(["concept_id", "year"]).reset_index(drop=True)
    out["vol"] = out.V_tm
    out["vol3"] = out.groupby("concept_id").V_tm.transform(lambda s: s.rolling(3, min_periods=1).sum())
    out["log_vol3"] = np.log1p(out.vol3)
    # residualised on log volume + age (main pool: fitted on its screen panel; here: all MeSH concept-years)
    fit = {}
    for col in MP_RES:
        m = out[col].notna() & out.age.notna() & (out.vol3 > 0)
        if m.sum() < 20:
            out[f"{col}_res"] = np.nan
            continue
        X = np.c_[np.ones(m.sum()), out.loc[m, "log_vol3"], out.loc[m, "age"]]
        beta, *_ = np.linalg.lstsq(X, out.loc[m, col].to_numpy(dtype=float), rcond=None)
        out[f"{col}_res"] = np.where(m, out[col] - (beta[0] + beta[1] * out.log_vol3 + beta[2] * out.age), np.nan)
        fit[col] = {"coef": [float(b) for b in beta], "n": int(m.sum())}
    na = {c: float(out.loc[out.W_c > 0, c].isna().mean()) for c in ("accretion_shift_rar", "closure", "P_rar")}
    logger.info(f"main-pool aligned columns added; NA share among networked concept-years: {na}")
    return out, {"res_fit": fit, "na_share_networked": na}
