"""Model helpers shared by the models, power and held-out confirmation stages (numpy only, deterministic)."""
from __future__ import annotations

import math

import numpy as np
import pandas as pd
from scipy import stats

NUM_BASE = ["H_W1", "n_active_W1", "log_vol_W1", "momentum", "GEB", "burst_state", "rafols_coh_f", "coh_missing",
            "P_rar_f", "P_rar_missing"]
CATS = ["origin_group", "F_band", "route", "t"]
TURNOVER = ["new_relation_rate", "novelty", "beta_sim_rar_f", "beta_sim_missing"]


def design(d: pd.DataFrame, lead: list[str], num: list[str] = NUM_BASE, cats: list[str] = CATS,
           levels: dict | None = None) -> tuple[np.ndarray, list[str], dict]:
    """[const, lead..., num..., drop-first dummies]; lead columns sit at positions 1..len(lead).

    `levels` (from a previous call) freezes dummy coding, e.g. for held-out rows.
    """
    cols = [np.ones(len(d))]
    names = ["const"]
    for c in lead + num:
        cols.append(d[c].astype(float).values)
        names.append(c)
    lv_out = {}
    for c in cats:
        vals = d[c].astype(str).values
        lv = levels[c] if levels is not None else sorted(set(vals))
        lv_out[c] = lv
        for v in lv[1:]:
            cols.append((vals == v).astype(float))
            names.append(f"{c}={v}")
    X = np.column_stack(cols)
    if levels is None:  # drop constant dummy / numeric columns (never const or lead)
        keep = [i for i in range(X.shape[1]) if i <= len(lead) or np.ptp(X[:, i]) > 0]
        X = X[:, keep]
        names = [names[i] for i in keep]
    return X, names, lv_out


def ols(X: np.ndarray, y: np.ndarray) -> np.ndarray:
    return np.linalg.lstsq(X, y, rcond=None)[0]


def cr1(X: np.ndarray, y: np.ndarray, g: np.ndarray, beta: np.ndarray | None = None) -> tuple[np.ndarray, np.ndarray]:
    """Coefficients and CR1 cluster-robust SEs (Stata small-sample factor)."""
    beta = ols(X, y) if beta is None else beta
    u = y - X @ beta
    n, k = X.shape
    XtXi = np.linalg.pinv(X.T @ X)
    uniq, inv = np.unique(g, return_inverse=True)
    G = len(uniq)
    S = np.zeros((G, k))
    np.add.at(S, inv, X * u[:, None])
    meat = S.T @ S
    V = XtXi @ meat @ XtXi * (G / (G - 1)) * ((n - 1) / max(n - k, 1))
    return beta, np.sqrt(np.clip(np.diag(V), 0, None))


def blocks_of(g: np.ndarray) -> list[np.ndarray]:
    uniq, inv = np.unique(g, return_inverse=True)
    order = np.argsort(inv, kind="stable")
    cuts = np.cumsum(np.bincount(inv))[:-1]
    return np.split(order, cuts)


def cluster_boot(X: np.ndarray, y: np.ndarray, g: np.ndarray, B: int, seed: int, j: int | list = 1) -> np.ndarray:
    blocks = blocks_of(g)
    G = len(blocks)
    rng = np.random.default_rng(seed)
    jj = np.atleast_1d(j)
    out = np.empty((B, len(jj)))
    for b in range(B):
        idx = np.concatenate([blocks[k] for k in rng.integers(0, G, G)])
        out[b] = ols(X[idx], y[idx])[jj]
    return out[:, 0] if np.ndim(j) == 0 else out


def boot_summary(est: float, draws: np.ndarray) -> dict:
    B = len(draws)
    lo, hi = np.percentile(draws, [2.5, 97.5])
    n_le, n_ge = int(np.sum(draws <= 0)), int(np.sum(draws >= 0))
    p = min(1.0, 2 * min((n_le + 1) / (B + 1), (n_ge + 1) / (B + 1)))
    return dict(coef=float(est), ci_lo=float(lo), ci_hi=float(hi), p_boot=float(p), boot_sd=float(np.std(draws, ddof=1)))


def r2(y: np.ndarray, p: np.ndarray) -> float:
    sst = float(np.sum((y - y.mean()) ** 2))
    return float(1 - np.sum((y - p) ** 2) / sst) if sst > 0 else math.nan


def fold_assign(g: np.ndarray, k: int, seed: int) -> np.ndarray:
    """Concepts shuffled (seeded) then dealt round-robin into k folds (grouped K-fold with shuffled group order)."""
    uniq = np.unique(g)
    perm = np.random.default_rng(seed).permutation(uniq)
    f_of = {c: i % k for i, c in enumerate(perm)}
    return np.array([f_of[c] for c in g])


def grouped_cv(Xb: np.ndarray, Xf: np.ndarray | None, y: np.ndarray, g: np.ndarray, reps: int = 20, k: int = 5,
               xf_fn=None) -> tuple[np.ndarray, np.ndarray]:
    """OOF predictions (averaged over repeats) for BASE and FULL; xf_fn(train_mask) -> FULL design (fold-internal)."""
    n = len(y)
    pb, pf = np.zeros((reps, n)), np.zeros((reps, n))
    for r in range(reps):
        f = fold_assign(g, k, r)
        for i in range(k):
            tr, te = f != i, f == i
            pb[r, te] = Xb[te] @ ols(Xb[tr], y[tr])
            XF = xf_fn(tr) if xf_fn is not None else Xf
            pf[r, te] = XF[te] @ ols(XF[tr], y[tr])
    return pb.mean(0), pf.mean(0)


def delta_r2_boot(y: np.ndarray, pb: np.ndarray, pf: np.ndarray, g: np.ndarray, B: int, seed: int) -> dict:
    blocks = blocks_of(g)
    G = len(blocks)
    rng = np.random.default_rng(seed)
    d = np.empty(B)
    for b in range(B):
        idx = np.concatenate([blocks[k] for k in rng.integers(0, G, G)])
        d[b] = r2(y[idx], pf[idx]) - r2(y[idx], pb[idx])
    lo, hi = np.percentile(d, [2.5, 97.5])
    return dict(r2_base=r2(y, pb), r2_full=r2(y, pf), delta_r2=r2(y, pf) - r2(y, pb), ci_lo=float(lo), ci_hi=float(hi))


def t_p_two_sided(coef: float, se: float, df: int) -> float:
    if not (np.isfinite(se) and se > 0):
        return math.nan
    return float(2 * stats.t.sf(abs(coef / se), df))
