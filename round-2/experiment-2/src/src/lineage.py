"""Parentage, per-edge vectors (a, b, imp, tr), rho / m point estimates, Gate-A shares, W1 momentum.

All edge-year functions take a W1View (leakage.py) and never see papers dated after t.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy import stats

from leakage import W1View, check_view

TAU = 2.0  # parent-age decay of w_kp


def canonical_main(papers: pd.DataFrame, F: int | None, top: int = 5) -> set[int]:
    """F-year c-papers plus top-5 by 2026 cited_by_count (ties -> lower work_id). The only declared post-t input."""
    s = papers.sort_values(["cbc", "work_id"], ascending=[False, True])
    canon = set(s.work_id.head(top).tolist())
    if F is not None:
        canon |= set(papers.work_id[papers.year == F].tolist())
    return canon


def canonical_w1(view: W1View, F: int | None, t: int, top: int = 5) -> set[int]:
    """CANON_W1 sensitivity: F-year papers + top-5 by in-concept citations received from c-papers with year <= t."""
    check_view(view, t)
    p = view.papers
    cnt = np.bincount(view.cites[:, 1], minlength=len(p)) if len(view.cites) else np.zeros(len(p), int)
    s = pd.DataFrame({"work_id": p.work_id, "n": cnt}).sort_values(["n", "work_id"], ascending=[False, True])
    canon = set(s.work_id.head(top).tolist())
    if F is not None:
        canon |= set(p.work_id[p.year == F].tolist())
    return canon


@dataclass
class Parentage:
    ch: np.ndarray        # child idx per valid cite
    pa: np.ndarray        # parent idx per valid cite
    w: np.ndarray         # normalised weight per valid cite
    traced: np.ndarray    # bool per paper
    bg_only: np.ndarray   # bool per paper: has cset parents (year <= own) but all canonical
    canon: np.ndarray     # bool per paper


def parentage(view: W1View, canon_ids: set[int], t: int) -> Parentage:
    check_view(view, t)
    p = view.papers
    n = len(p)
    yr = p.year.to_numpy()
    canon = p.work_id.isin(canon_ids).to_numpy()
    c = view.cites
    if len(c):
        ch, pa = c[:, 0], c[:, 1]
        base = (pa != ch) & (yr[pa] <= yr[ch])
        ch, pa = ch[base], pa[base]
    else:
        ch = pa = np.zeros(0, np.int64)
    has_any = np.zeros(n, bool)
    has_any[ch] = True
    v = ~canon[pa]
    ch, pa = ch[v], pa[v]
    raw = np.exp(-(yr[ch] - yr[pa]) / TAU)
    tot = np.bincount(ch, weights=raw, minlength=n)
    w = raw / tot[ch] if len(ch) else raw
    traced = np.zeros(n, bool)
    traced[ch] = True
    return Parentage(ch=ch, pa=pa, w=w, traced=traced, bg_only=has_any & ~traced, canon=canon)


@dataclass
class EdgeVec:
    units: np.ndarray     # paper idx of Pd union Kd
    a: np.ndarray
    b: np.ndarray
    imp: np.ndarray
    tr: np.ndarray
    n_parents: int
    n_children: int
    n_w1: int
    stats: dict


def edge_vectors(view: W1View, par: Parentage, d: int, t: int) -> EdgeVec:
    """Vectors for edge (c, d, t) using only W1 papers (years <= t)."""
    check_view(view, t)
    p = view.papers
    yr = p.year.to_numpy()
    sub = p["sub"].to_numpy()
    isd = sub == d
    Pd = isd & ~par.canon & (yr >= t - 5) & (yr <= t - 3)
    Kd = isd & (yr >= t - 4) & (yr <= t)
    n_w1 = int((isd & (yr >= t - 5)).sum())
    n = len(p)
    ch, pa, w = par.ch, par.pa, par.w
    inK = Kd[ch]
    a = np.bincount(ch[inK & Pd[pa]], weights=w[inK & Pd[pa]], minlength=n)
    imp_sel = inK & (sub[pa] != d)
    imp = np.bincount(ch[imp_sel], weights=w[imp_sel], minlength=n)
    tr = (par.traced & Kd).astype(float)
    # Gate-A within-host: child in Kd citing >= 1 non-canonical parent in d with year in [t-5, year_k]
    wh_sel = inK & (sub[pa] == d) & (yr[pa] >= t - 5)
    within = np.zeros(n, bool)
    within[ch[wh_sel]] = True
    units = np.flatnonzero(Pd | Kd)
    nK = int(Kd.sum())
    nrefs = p.n_refs.to_numpy()
    kref = Kd & (nrefs > 0)
    st = {
        "within_host_share": float(within[Kd].mean()) if nK else np.nan,
        "within_host_share_refs": float(within[kref].mean()) if kref.any() else np.nan,
        "n_children_with_refs": int(kref.sum()),
        "lenient_share": float(p.lenient_excl_F.to_numpy()[Kd].mean()) if nK else np.nan,
        "n_traced": int(par.traced[Kd].sum()),
        "untraced_share": float(1 - par.traced[Kd].mean()) if nK else np.nan,
        "background_only_share": float(par.bg_only[Kd].mean()) if nK else np.nan,
        "n_canonical_in_d": int((isd & par.canon).sum()),
    }
    return EdgeVec(units=units, a=a[units], b=Pd[units].astype(float), imp=imp[units], tr=tr[units],
                   n_parents=int(Pd.sum()), n_children=nK, n_w1=n_w1, stats=st)


def point_estimates(ev: EdgeVec) -> dict:
    rho = ev.a.sum() / ev.b.sum() if ev.b.sum() > 0 else np.nan
    m = ev.imp.sum() / ev.tr.sum() if ev.tr.sum() > 0 else np.nan
    return {"rho": float(rho), "m": float(m)}


def momentum(counts: np.ndarray, totals: np.ndarray, years: np.ndarray) -> tuple[float, float, float]:
    """OLS slope of log(1e4*n/T + 1e-3) on year, with 90% CI (t, df = k-2)."""
    ok = totals > 0
    y = np.log(1e4 * counts[ok] / totals[ok] + 1e-3)
    x = years[ok].astype(float)
    if len(x) < 3:
        return np.nan, np.nan, np.nan
    r = stats.linregress(x, y)
    q = stats.t.ppf(0.95, len(x) - 2)
    return float(r.slope), float(r.slope - q * r.stderr), float(r.slope + q * r.stderr)


def w1_counts(view: W1View, t: int) -> pd.Series:
    """W1 (years t-5..t) c-paper counts per subfield (unknown subfield = -1 dropped)."""
    check_view(view, t)
    p = view.papers
    s = p["sub"][(p.year >= t - 5) & (p["sub"] >= 0)]
    return s.value_counts()


def yearly_counts(view: W1View, d: int, t: int) -> np.ndarray:
    check_view(view, t)
    p = view.papers
    yrs = p.year[p["sub"] == d].to_numpy()
    return np.array([(yrs == y).sum() for y in range(t - 5, t + 1)], float)
