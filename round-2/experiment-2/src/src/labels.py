"""Paper-cluster bootstrap, BH families, four states, n_min rule."""
from __future__ import annotations

import numpy as np
import pandas as pd
from statsmodels.stats.multitest import multipletests

from lineage import EdgeVec

Q_BH = 0.10
M_SINK = 0.5
NMIN_BINS = [5, 10, 15, 20, 30]
WIDTH_MAX = 0.7


def boot_counts(rng: np.random.Generator, n: int, B: int) -> np.ndarray:
    """B x n multinomial(n, 1/n) counts via bincount of uniform index draws (identical distribution)."""
    idx = rng.integers(0, n, size=(B, n), dtype=np.int64)
    idx += (np.arange(B, dtype=np.int64) * n)[:, None]
    return np.bincount(idx.ravel(), minlength=B * n).reshape(B, n).astype(np.float64)


def bootstrap_edge(ev: EdgeVec, rng: np.random.Generator, B: int, rho0: dict[str, object]) -> dict:
    """rho0: variant name -> float (fixed benchmark) or ndarray (B,) (REF_BOOT). Returns CIs and p-values."""
    n = len(ev.units)
    V = np.stack([ev.a, ev.b, ev.imp, ev.tr], axis=1)
    S = np.zeros((B, 4))
    chunk = max(1, int(2e7 // max(n, 1)))
    for s0 in range(0, B, chunk):
        bb = min(chunk, B - s0)
        S[s0:s0 + bb] = boot_counts(rng, n, bb) @ V
    sa, sb, si, st = S.T
    with np.errstate(divide="ignore", invalid="ignore"):
        rs = np.where(sb > 0, sa / sb, np.nan)
        ms = np.where(st > 0, si / st, np.nan)
        lr = np.where(sb > 0, np.where(sa > 0, np.log(sa / sb), np.log((sa + 0.5) / (sb + 0.5))), np.nan)
    out = {"nan_share": float(np.isnan(rs).mean())}
    ok = ~np.isnan(rs)
    if ok.sum() >= 10:
        out["rho_lo"], out["rho_hi"] = (float(x) for x in np.percentile(rs[ok], [5, 95]))
        l5, l95 = np.percentile(lr[ok], [5, 95])
        out["log_ci_width"] = float(l95 - l5)
    else:
        out["rho_lo"] = out["rho_hi"] = out["log_ci_width"] = np.nan
    okm = ~np.isnan(ms)
    if okm.sum() >= 10:
        out["m_lo"], out["m_hi"] = (float(x) for x in np.percentile(ms[okm], [5, 95]))
    else:
        out["m_lo"] = out["m_hi"] = np.nan
    for name, r0 in rho0.items():
        r0a = np.asarray(r0, float)
        if np.all(np.isnan(r0a)):
            out[f"p_greater_{name}"] = out[f"p_less_{name}"] = 1.0
            out[f"rt_lo_{name}"] = out[f"rt_hi_{name}"] = np.nan
            continue
        with np.errstate(divide="ignore", invalid="ignore"):
            rt = rs / r0a
        bad = np.isnan(rt)
        out[f"p_greater_{name}"] = float((1 + np.sum(bad | (rt <= 1))) / (B + 1))
        out[f"p_less_{name}"] = float((1 + np.sum(bad | (rt >= 1))) / (B + 1))
        if (~bad).sum() >= 10:
            out[f"rt_lo_{name}"], out[f"rt_hi_{name}"] = (float(x) for x in np.percentile(rt[~bad], [5, 95]))
        else:
            out[f"rt_lo_{name}"] = out[f"rt_hi_{name}"] = np.nan
    return out


def bh_reject(p: np.ndarray, q: float = Q_BH) -> np.ndarray:
    if len(p) == 0:
        return np.zeros(0, bool)
    return multipletests(p, alpha=q, method="fdr_bh")[0]


def bh_qvalues(p: np.ndarray) -> np.ndarray:
    if len(p) == 0:
        return np.zeros(0)
    return multipletests(p, alpha=Q_BH, method="fdr_bh")[1]


def state_of(rej_g: bool, rej_l: bool, m_lo: float) -> str:
    if rej_g and not rej_l:
        return "SOURCE"
    if rej_l and not rej_g:
        return "SINK" if (m_lo is not None and not np.isnan(m_lo) and m_lo > M_SINK) else "FADING"
    return "UNDETERMINED"


def assign_states(df: pd.DataFrame, n_min: int, pg: str, pl: str, col: str) -> pd.DataFrame:
    """BH per (concept, t) family among tested edges; writes df[col] (state) and q-values for this variant."""
    tested = ((df.n_children >= n_min) & (df.n_parents >= 1) & (df.n_traced >= 1) & df.eligible).to_numpy()
    st = np.array(["UNDETERMINED"] * len(df), dtype=object)
    qg = np.full(len(df), np.nan)
    ql = np.full(len(df), np.nan)
    sub = df[tested]
    for _, g in sub.groupby(["concept_id", "t"]).groups.items():
        ii = df.index.get_indexer(g)
        p1 = df[pg].to_numpy()[ii]
        p2 = df[pl].to_numpy()[ii]
        r1, r2 = bh_reject(p1), bh_reject(p2)
        qg[ii], ql[ii] = bh_qvalues(p1), bh_qvalues(p2)
        mlo = df["m_lo"].to_numpy()[ii]
        for k, i in enumerate(ii):
            st[i] = state_of(bool(r1[k]), bool(r2[k]), mlo[k])
    df[col] = st
    return df.assign(**{f"{col}__q_greater": qg, f"{col}__q_less": ql, f"{col}__tested": tested})


def reason_code(row: pd.Series, n_min: int) -> str:
    if not row.eligible:
        return "ineligible_lt10_w1"
    if row.n_parents < 1:
        return "no_cohort_parents"
    if row.n_children < n_min:
        return "below_nmin"
    if row.n_traced < 1:
        return "no_traced_children"
    return "tested"


def nmin_rule(df: pd.DataFrame) -> dict:
    e = df[df.eligible & (df.n_children >= 5) & df.log_ci_width.notna()]
    edges = NMIN_BINS + [np.inf]
    rows = []
    for lo, hi in zip(edges[:-1], edges[1:]):
        s = e[(e.n_children >= lo) & (e.n_children < hi)].log_ci_width
        rows.append({"bin_lo": lo, "bin_hi": None if np.isinf(hi) else hi, "n_edges": int(len(s)),
                     "median_width": float(s.median()) if len(s) else None})
    ok = [r["median_width"] is not None and r["median_width"] <= WIDTH_MAX for r in rows]
    n_rule, flagged = None, False
    for i, r in enumerate(rows):
        if all(ok[i:]) and rows[i]["n_edges"] > 0:
            n_rule = r["bin_lo"]
            break
    if n_rule is None:
        n_rule, flagged = 30, True
    return {"bins": rows, "n_min_rule": int(n_rule), "rule_not_met_flag": flagged, "n_min_main": int(max(10, n_rule))}
