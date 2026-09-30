"""Fast conditional logit (any number of controls per stratum) with model-based and concept-cluster-robust SEs,
a concept-cluster bootstrap driver and small helpers. Validated against statsmodels ConditionalLogit in eval.py."""
from __future__ import annotations

import numpy as np
from scipy import stats


def clogit(y: np.ndarray, X: np.ndarray, strata: np.ndarray, cluster: np.ndarray | None = None,
           maxit: int = 50, tol: float = 1e-10) -> dict:
    """Conditional logistic regression. y: 0/1 case flag (one case per stratum), X: n x k, strata: int ids."""
    X = np.asarray(X, float)
    if X.ndim == 1:
        X = X[:, None]
    _, s = np.unique(strata, return_inverse=True)
    ns = s.max() + 1
    k = X.shape[1]
    beta = np.zeros(k)
    ll_old = -np.inf
    conv = False
    for it in range(maxit):
        eta = X @ beta
        # stabilise per stratum
        mx = np.full(ns, -np.inf)
        np.maximum.at(mx, s, eta)
        ex = np.exp(eta - mx[s])
        den = np.bincount(s, weights=ex, minlength=ns)
        p = ex / den[s]
        ll = float(np.sum(eta[y == 1] - mx[s[y == 1]] - np.log(den[s[y == 1]])))
        xbar = np.zeros((ns, k))
        np.add.at(xbar, s, p[:, None] * X)
        casex = np.zeros((ns, k))
        np.add.at(casex, s[y == 1], X[y == 1])
        grad = (casex - xbar).sum(0)
        dev = X - xbar[s]
        H = (dev * p[:, None]).T @ dev
        try:
            step = np.linalg.solve(H + 1e-10 * np.eye(k), grad)
        except np.linalg.LinAlgError:
            break
        beta = beta + step
        if abs(ll - ll_old) < tol and np.max(np.abs(step)) < 1e-7:
            conv = True
            break
        ll_old = ll
    eta = X @ beta
    mx = np.full(ns, -np.inf)
    np.maximum.at(mx, s, eta)
    ex = np.exp(eta - mx[s])
    den = np.bincount(s, weights=ex, minlength=ns)
    p = ex / den[s]
    xbar = np.zeros((ns, k))
    np.add.at(xbar, s, p[:, None] * X)
    dev = X - xbar[s]
    H = (dev * p[:, None]).T @ dev
    try:
        Hi = np.linalg.inv(H)
    except np.linalg.LinAlgError:
        Hi = np.full((k, k), np.nan)
    se = np.sqrt(np.clip(np.diag(Hi), 0, None))
    out = {"beta": beta, "se": se, "converged": conv, "n_strata": int(ns), "n": int(len(y))}
    if cluster is not None:
        casex = np.zeros((ns, k))
        np.add.at(casex, s[y == 1], X[y == 1])
        score_s = casex - xbar  # per-stratum score
        cl_s = np.zeros(ns, dtype=np.int64)
        _, cl = np.unique(cluster, return_inverse=True)
        cl_s[s] = cl
        G = cl.max() + 1
        S = np.zeros((G, k))
        np.add.at(S, cl_s, score_s)
        V = G / (G - 1) * Hi @ (S.T @ S) @ Hi if G > 1 else Hi
        out["se_crv"] = np.sqrt(np.clip(np.diag(V), 0, None))
        out["G"] = int(G)
    return out


def boot_indices(cluster_of_row: np.ndarray, rng: np.random.Generator) -> tuple[np.ndarray, np.ndarray]:
    """Concept-cluster bootstrap: returns row indices and a replicate-cluster id per row (duplicates distinct)."""
    uc, inv = np.unique(cluster_of_row, return_inverse=True)
    rows_by = [np.flatnonzero(inv == i) for i in range(len(uc))]
    draw = rng.integers(0, len(uc), len(uc))
    idx = np.concatenate([rows_by[j] for j in draw])
    rep = np.concatenate([np.full(len(rows_by[j]), t) for t, j in enumerate(draw)])
    return idx, rep


def pct_ci(x: np.ndarray, alpha: float = 0.05) -> list[float]:
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    if len(x) < 10:
        return [float("nan"), float("nan")]
    return [float(np.quantile(x, alpha / 2)), float(np.quantile(x, 1 - alpha / 2))]


def boot_p(x: np.ndarray, null: float = 0.0) -> float:
    """Two-sided bootstrap p: 2 x min share of replicates on either side of the null (floored at 1/(B+1))."""
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    if len(x) == 0:
        return float("nan")
    p = 2 * min((x <= null).mean(), (x >= null).mean())
    return float(max(min(p, 1.0), 1 / (len(x) + 1)))


def wald_p(b: float, se: float) -> float:
    return float(2 * stats.norm.sf(abs(b / se))) if se and np.isfinite(se) and se > 0 else float("nan")


def smd(a: np.ndarray, b: np.ndarray) -> float:
    a, b = np.asarray(a, float), np.asarray(b, float)
    a, b = a[np.isfinite(a)], b[np.isfinite(b)]
    sd = np.sqrt((a.var(ddof=1) + b.var(ddof=1)) / 2)
    return float((a.mean() - b.mean()) / sd) if sd > 0 else 0.0


def kappa(a: np.ndarray, b: np.ndarray) -> float:
    a, b = np.asarray(a, int), np.asarray(b, int)
    po = (a == b).mean()
    pe = a.mean() * b.mean() + (1 - a.mean()) * (1 - b.mean())
    return float((po - pe) / (1 - pe)) if pe < 1 else float("nan")
