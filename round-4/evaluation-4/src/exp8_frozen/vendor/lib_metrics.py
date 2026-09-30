#!/usr/bin/env python3
"""Pure metric functions for the RQ1 temporal co-word network study.

Every function here is side-effect free and unit-tested in tests/test_metrics.py:
association strength, Baselga beta-diversity partition, participation coefficient,
within-module z, Chung-Lu closure log-ratio, Kleinberg two-state burst detection
(Viterbi, evaluated on a truncated series so it never sees the future), Shannon and
Rao-Stirling diversity, rarefaction helpers and OLS slopes.
"""
from __future__ import annotations

import hashlib
import math
from collections.abc import Iterable, Sequence

import numpy as np


# ----------------------------------------------------------------------------- seeds
def stable_seed(*parts: object) -> int:
    """Deterministic 32-bit seed from arbitrary parts (independent of PYTHONHASHSEED)."""
    h = hashlib.sha1("|".join(map(str, parts)).encode()).hexdigest()
    return int(h[:8], 16)


# ----------------------------------------------------------------------------- association strength
def association_strength(c_ij: np.ndarray | float, w_i: np.ndarray | float, w_j: np.ndarray | float,
                         w_tot: float) -> np.ndarray | float:
    """van Eck & Waltman (2009) association strength AS_ij = c_ij * W_tot / (W_i * W_j)."""
    return np.asarray(c_ij, dtype=float) * w_tot / (np.asarray(w_i, dtype=float) * np.asarray(w_j, dtype=float))


# ----------------------------------------------------------------------------- Baselga
def baselga(prev: set, cur: set) -> tuple[float, float, float]:
    """Baselga (2010) Sorensen partition between two sets.

    Returns (beta_sor, beta_sim, beta_sne). NaN if both sets are empty.
    beta_sor = (b+c)/(2a+b+c); beta_sim = min(b,c)/(a+min(b,c)); beta_sne = beta_sor - beta_sim.
    """
    a = len(prev & cur)
    b = len(prev - cur)
    c = len(cur - prev)
    den = 2 * a + b + c
    if den == 0:
        return (math.nan, math.nan, math.nan)
    sor = (b + c) / den
    mn = min(b, c)
    sim = mn / (a + mn) if (a + mn) > 0 else 0.0
    return (sor, sim, sor - sim)


def sne_share(sor: float, sne: float) -> float:
    """Share of Sorensen dissimilarity due to nestedness (accretion); NaN when sor == 0 or NaN."""
    if not np.isfinite(sor) or sor <= 0:
        return math.nan
    return sne / sor


# ----------------------------------------------------------------------------- participation / roles
def participation(weights_by_comm: dict) -> float:
    """Guimera-Amaral participation P = 1 - sum_s (k_s / k)^2. NaN if total weight is 0."""
    vals = np.array([v for v in weights_by_comm.values() if v > 0], dtype=float)
    tot = vals.sum()
    if tot <= 0:
        return math.nan
    return float(1.0 - np.sum((vals / tot) ** 2))


def within_module_z(k_own: float, peer_k_own: np.ndarray) -> float:
    """Within-module degree z-score of a node against the within-module strengths of its community peers."""
    peer_k_own = np.asarray(peer_k_own, dtype=float)
    if peer_k_own.size < 3:
        return math.nan
    sd = peer_k_own.std(ddof=1)
    if sd <= 0:
        return math.nan
    return float((k_own - peer_k_own.mean()) / sd)


# ----------------------------------------------------------------------------- closure
def closure_log_ratio(obs: float, exp: float, eps: float) -> float:
    """log((obs+eps)/(exp+eps)): observed neighbourhood tie weight over the Chung-Lu expectation."""
    return float(np.log((obs + eps) / (exp + eps)))


def chung_lu_expected(strengths: np.ndarray, total_strength: float) -> float:
    """Sum over unordered pairs of s_i s_j / S, where S = sum of all strengths (= 2 * total edge weight)."""
    s = np.asarray(strengths, dtype=float)
    if s.size < 2 or total_strength <= 0:
        return math.nan
    return float(((s.sum() ** 2 - np.sum(s ** 2)) / 2.0) / total_strength)


# ----------------------------------------------------------------------------- diversity
def shannon(counts: Iterable[float]) -> float:
    c = np.array([x for x in counts if x > 0], dtype=float)
    if c.size == 0:
        return math.nan
    p = c / c.sum()
    return float(-np.sum(p * np.log(p)))


def rao_stirling(counts_by_cat: dict, dist: dict[tuple, float] | None = None,
                 dist_matrix: np.ndarray | None = None, index: dict | None = None) -> float:
    """Rao-Stirling diversity sum_{i != j} d_ij p_i p_j over categories with positive counts.

    Either `dist` (dict keyed by (i, j)) or `dist_matrix` + `index` (category -> row) must be given.
    Categories missing from the distance matrix are dropped.
    """
    cats = [k for k, v in counts_by_cat.items() if v > 0 and (index is None or k in index)]
    if not cats:
        return math.nan
    v = np.array([counts_by_cat[k] for k in cats], dtype=float)
    p = v / v.sum()
    if dist_matrix is not None and index is not None:
        idx = np.array([index[k] for k in cats])
        d = dist_matrix[np.ix_(idx, idx)]
    else:
        d = np.array([[0.0 if a == b else dist[(a, b)] for b in cats] for a in cats])
    return float(p @ d @ p)


# ----------------------------------------------------------------------------- Kleinberg
def kleinberg_states(r: Sequence[float], d: Sequence[float], s: float = 2.0, gamma: float = 1.0) -> np.ndarray:
    """Kleinberg (2002) two-state batched (binomial) burst detection; returns the Viterbi state sequence.

    r_t = relevant counts, d_t = total counts. Base rate p0 = sum r / sum d; burst rate p1 = min(s * p0, 0.9999).
    Upward transition cost gamma * ln(n); downward is free. Callers must pass a series TRUNCATED at the
    evaluation year so the state at the last year never depends on later data.
    """
    r = np.asarray(r, dtype=float)
    d = np.asarray(d, dtype=float)
    n = len(r)
    if n == 0:
        return np.zeros(0, dtype=int)
    if r.sum() <= 0 or d.sum() <= 0:
        return np.zeros(n, dtype=int)
    p0 = r.sum() / d.sum()
    p1 = min(s * p0, 0.9999)
    ps = np.array([p0, p1])
    # cost = -log likelihood (binomial coefficient is common to both states and dropped)
    with np.errstate(divide="ignore", invalid="ignore"):
        cost = -(r[:, None] * np.log(ps[None, :]) + (d - r)[:, None] * np.log1p(-ps[None, :]))
    trans_up = gamma * math.log(max(n, 2))
    best = np.full((n, 2), np.inf)
    back = np.zeros((n, 2), dtype=int)
    best[0, 0] = cost[0, 0]
    best[0, 1] = cost[0, 1] + trans_up
    for t in range(1, n):
        # to state 0: from 0 (free) or from 1 (free)
        if best[t - 1, 0] <= best[t - 1, 1]:
            best[t, 0], back[t, 0] = best[t - 1, 0] + cost[t, 0], 0
        else:
            best[t, 0], back[t, 0] = best[t - 1, 1] + cost[t, 0], 1
        # to state 1: from 0 (pay up) or from 1 (free)
        a0, a1 = best[t - 1, 0] + trans_up, best[t - 1, 1]
        if a0 < a1:
            best[t, 1], back[t, 1] = a0 + cost[t, 1], 0
        else:
            best[t, 1], back[t, 1] = a1 + cost[t, 1], 1
    states = np.zeros(n, dtype=int)
    states[-1] = int(np.argmin(best[-1]))
    for t in range(n - 1, 0, -1):
        states[t - 1] = back[t, states[t]]
    return states


def kleinberg_at(years: Sequence[int], r: Sequence[float], d: Sequence[float], y: int,
                 s: float = 2.0, gamma: float = 1.0) -> tuple[int, float]:
    """Burst state at year y and years since the most recent burst onset, using data <= y only.

    Returns (state_y, years_since_onset) with years_since_onset = NaN when no burst has occurred.
    """
    years = np.asarray(years)
    mask = years <= y
    if mask.sum() == 0:
        return (0, math.nan)
    yy = years[mask]
    st = kleinberg_states(np.asarray(r)[mask], np.asarray(d)[mask], s=s, gamma=gamma)
    onsets = [int(yy[i]) for i in range(len(st)) if st[i] == 1 and (i == 0 or st[i - 1] == 0)]
    return (int(st[-1]), float(y - onsets[-1]) if onsets else math.nan)


# ----------------------------------------------------------------------------- slopes / rarefaction
def ols_slope(x: Sequence[float], y: Sequence[float], min_points: int = 2) -> float:
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    ok = np.isfinite(x) & np.isfinite(y)
    if ok.sum() < min_points:
        return math.nan
    x, y = x[ok], y[ok]
    if np.ptp(x) == 0:
        return math.nan
    return float(np.polyfit(x, y, 1)[0])


def rarefied_draws(n_items: int, m: int, n_draws: int, seed: int) -> list[np.ndarray]:
    """n_draws index samples of size m without replacement from range(n_items); empty list if n_items < m."""
    if n_items < m:
        return []
    rng = np.random.default_rng(seed)
    return [rng.choice(n_items, size=m, replace=False) for _ in range(n_draws)]


def smd(a: Sequence[float], b: Sequence[float]) -> float:
    """Standardised mean difference with pooled SD."""
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    a, b = a[np.isfinite(a)], b[np.isfinite(b)]
    if a.size < 2 or b.size < 2:
        return math.nan
    sd = math.sqrt((a.var(ddof=1) + b.var(ddof=1)) / 2.0)
    if sd == 0:
        return 0.0
    return float((a.mean() - b.mean()) / sd)


def holm(pvals: Sequence[float]) -> list[float]:
    """Holm step-down adjusted p-values (NaN entries passed through)."""
    p = np.asarray(pvals, dtype=float)
    out = np.full_like(p, np.nan)
    ok = np.where(np.isfinite(p))[0]
    order = ok[np.argsort(p[ok])]
    m = len(order)
    running = 0.0
    for rank, idx in enumerate(order):
        adj = min(1.0, (m - rank) * p[idx])
        running = max(running, adj)
        out[idx] = running
    return out.tolist()


def bh(pvals: Sequence[float]) -> list[float]:
    """Benjamini-Hochberg q-values (NaN entries passed through)."""
    p = np.asarray(pvals, dtype=float)
    out = np.full_like(p, np.nan)
    ok = np.where(np.isfinite(p))[0]
    if ok.size == 0:
        return out.tolist()
    order = ok[np.argsort(p[ok])]
    m = len(order)
    q = p[order] * m / np.arange(1, m + 1)
    q = np.minimum.accumulate(q[::-1])[::-1]
    out[order] = np.minimum(q, 1.0)
    return out.tolist()
