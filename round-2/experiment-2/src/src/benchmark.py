"""Replacement benchmark rho0(d,t) from stationary reference cells via the pre-declared pooling hierarchy."""
from __future__ import annotations

import numpy as np
import pandas as pd

SLOPE_MAX = 0.05
MIN_W1 = 30
MIN_CELLS = 3


def stationary_cells(refs: pd.DataFrame) -> tuple[pd.DataFrame, str]:
    c = refs[(refs.n_w1 >= MIN_W1) & (refs.slope.abs() < SLOPE_MAX) & refs.rho.notna() & (refs.n_parents >= 1)]
    if len(c):
        return c.copy(), "stationary"
    c = refs[(refs.n_w1 >= MIN_W1) & refs.is_modal & refs.rho.notna() & (refs.n_parents >= 1)]  # F2(b)
    if len(c):
        return c.copy(), "relaxed_modal_any_slope"
    return refs[(refs.n_w1 >= MIN_W1) & refs.rho.notna() & (refs.n_parents >= 1)].copy(), "relaxed_any"


def _med(v: np.ndarray) -> float:
    return float(np.median(v)) if len(v) >= MIN_CELLS else np.nan


def rho0_table(cells: pd.DataFrame, needed: list[tuple[int, int]], field_of: dict[int, int],
               l3_window: tuple[int, int] = (-2, 2)) -> dict[tuple[int, int], tuple[float, str, int]]:
    """(d,t) -> (rho0, level, n_cells). Levels L1..L5; a level is skipped if its median <= 0 or n < 3."""
    c = cells.assign(f=cells.d.map(lambda x: field_of.get(int(x), -1)))
    rho = c.rho.to_numpy()
    by_dt = {k: rho[v] for k, v in c.groupby(["d", "t"]).indices.items()}
    by_ft = {k: rho[v] for k, v in c.groupby(["f", "t"]).indices.items()}
    by_t = {k: rho[v] for k, v in c.groupby("t").indices.items()}
    allv = rho
    fs = c.f.to_numpy()
    ts = c.t.to_numpy()
    cache_l3: dict = {}
    out = {}
    for d, t in needed:
        f = field_of.get(int(d), -1)
        cand = []
        v1 = by_dt.get((d, t), np.zeros(0))
        cand.append(("L1", v1))
        cand.append(("L2", by_ft.get((f, t), np.zeros(0))))
        key = (f, t)
        if key not in cache_l3:
            sel = (fs == f) & (ts >= t + l3_window[0]) & (ts <= t + l3_window[1])
            cache_l3[key] = rho[sel]
        cand.append(("L3", cache_l3[key]))
        cand.append(("L4", by_t.get(t, np.zeros(0))))
        cand.append(("L5", allv))
        res = (np.nan, "none", 0)
        for lev, v in cand:
            m = _med(v)
            if not np.isnan(m) and m > 0:
                res = (m, lev, int(len(v)))
                break
        out[(d, t)] = res
    return out


def eb_table(cells: pd.DataFrame, needed: list[tuple[int, int]], field_of: dict[int, int],
             fallback: dict) -> dict[tuple[int, int], float]:
    """EB: cell mean of log rho_r (positive values) shrunk toward the field mean with MoM tau^2."""
    c = cells[cells.rho > 0].assign(f=cells.d.map(lambda x: field_of.get(int(x), -1)), x=lambda z: np.log(z.rho))
    g = c.groupby(["d", "t"]).x.agg(["mean", "var", "count"]).reset_index()
    s2_pool = float(np.nanmean(g["var"])) if g["var"].notna().any() else float(c.x.var())
    g["f"] = g.d.map(lambda x: field_of.get(int(x), -1))
    out = {}
    fstat = {}
    for f, gg in g.groupby("f"):
        if len(gg) >= 2:
            mu = float(gg["mean"].mean())
            tau2 = max(0.0, float(gg["mean"].var()) - float(np.mean(s2_pool / gg["count"])))
            fstat[f] = (mu, tau2)
    gi = g.set_index(["d", "t"])
    for d, t in needed:
        f = field_of.get(int(d), -1)
        if (d, t) in gi.index and f in fstat:
            r = gi.loc[(d, t)]
            mu, tau2 = fstat[f]
            wgt = tau2 / (tau2 + s2_pool / r["count"]) if (tau2 + s2_pool / r["count"]) > 0 else 0.0
            out[(d, t)] = float(np.exp(mu + wgt * (r["mean"] - mu)))
        else:
            out[(d, t)] = fallback[(d, t)][0]
    return out


def refboot_table(cells: pd.DataFrame, needed: list[tuple[int, int]], field_of: dict[int, int], B: int,
                  seed: int) -> dict[tuple[int, int], np.ndarray]:
    """REF_BOOT: resample reference concepts with replacement in each rep and recompute the hierarchy."""
    rng = np.random.default_rng([seed, 99])
    refs = np.array(sorted(cells.ref_id.unique()))
    out = {k: np.full(B, np.nan) for k in needed}
    by_ref = {r: g for r, g in cells.groupby("ref_id")}
    for b in range(B):
        draw = rng.choice(refs, size=len(refs), replace=True)
        cb = pd.concat([by_ref[r] for r in draw], ignore_index=True)
        tb = rho0_table(cb, needed, field_of)
        for k, v in tb.items():
            out[k][b] = v[0]
    return out
