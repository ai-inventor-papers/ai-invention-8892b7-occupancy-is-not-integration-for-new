"""Pure turnover-proof openness metrics (iteration 3): Burt ego brokerage and the cross-community pair excess.

All functions are side-effect free and unit-tested against networkx (tests/test_openness.py).

Ego network of a pool concept c (weighted, undirected):
  nodes = c + its frame-type neighbours js (all tags with association strength AS_c > 0),
  tie c-j weight = AS_c[j] (lift of j among c's frame papers),
  tie q-j weight = AS_qj of the background snapshot (all edges, not only kept ones).
Burt (1992) constraint and effective size use exactly the networkx weighted formulas
(normalized mutual weight with norm = sum for p, norm = max for the redundancy m).
"""
from __future__ import annotations

import math

import numpy as np
import scipy.sparse as sp


def ego_brokerage(w_c: np.ndarray, A: sp.spmatrix | np.ndarray) -> dict:
    """Burt constraint, effective size and efficiency of ego c.

    w_c : (n,) positive tie weights from c to each neighbour.
    A   : (n, n) symmetric non-negative neighbour-neighbour tie weights with zero diagonal.
    constraint = sum_j (p_cj + sum_q p_cq p_qj)^2, p_uv = w_uv / sum_x w_ux over u's ego-network neighbours.
    effsize    = sum_q (1 - sum_w p_cw m_qw), m_qw = w_qw / max_x w_qx over q's ego-network neighbours (incl. c).
    """
    w_c = np.asarray(w_c, dtype=float)
    n = len(w_c)
    if n == 0 or w_c.sum() <= 0:
        return dict(n_ego=n, constraint=math.nan, effsize=math.nan, efficiency=math.nan, cdeg_diag=math.nan)
    A = sp.csr_matrix(A, dtype=float)
    A.setdiag(0)
    A.eliminate_zeros()
    p_c = w_c / w_c.sum()
    rowsum = np.asarray(A.sum(axis=1)).ravel()
    tot_q = rowsum + w_c                      # q's strength inside the ego network (incl. its tie to c)
    P = sp.diags(1.0 / tot_q) @ A             # p_qj
    indirect = np.asarray(P.T @ p_c).ravel()  # (p_c @ P)[j] = sum_q p_cq p_qj
    constraint = float(np.sum((p_c + indirect) ** 2))
    # redundancy with max-normalised mutual weight
    rowmax = A.max(axis=1).toarray().ravel() if A.nnz else np.zeros(n)
    maxq = np.maximum(rowmax, w_c)
    red = np.asarray(A @ p_c).ravel() / maxq  # sum_w p_cw * A_qw / max_q
    effsize = float(np.sum(1.0 - red))
    return dict(n_ego=n, constraint=constraint, effsize=effsize, efficiency=effsize / n,
                cdeg_diag=float(math.log(n * constraint)) if constraint > 0 else math.nan)


def strength_decile_bins(s_kept: np.ndarray, n_bins: int = 10) -> tuple[np.ndarray, np.ndarray]:
    """Decile edges of kept-node strengths and the decile index of every kept node (fixed per snapshot)."""
    s_kept = np.asarray(s_kept, dtype=float)
    edges = np.quantile(s_kept, np.linspace(0, 1, n_bins + 1))
    edges[0], edges[-1] = -np.inf, np.inf
    b = np.clip(np.searchsorted(edges, s_kept, side="right") - 1, 0, n_bins - 1)
    return edges, b


def cross_share(memb: np.ndarray) -> float:
    """Share of unordered pairs whose community labels differ."""
    memb = np.asarray(memb)
    n = len(memb)
    if n < 2:
        return math.nan
    _, cnt = np.unique(memb, return_counts=True)
    same = float(np.sum(cnt * (cnt - 1) / 2.0))
    tot = n * (n - 1) / 2.0
    return 1.0 - same / tot


def xc_null(member_bins: np.ndarray, bin_pools: list[np.ndarray], pool_memb: list[np.ndarray], draws: int,
            seed: int) -> tuple[float, int]:
    """Strength-decile-matched null of the cross-community pair share.

    member_bins : decile of each member of K.
    bin_pools   : per decile, the array of kept background node positions (candidates).
    pool_memb   : per decile, the community of each candidate.
    For each draw, every member of K is replaced by a distinct kept node of the same decile (without replacement
    within a draw). If a decile holds fewer candidates than needed, the adjacent deciles are merged (F6) and the
    number of merges is returned.
    """
    rng = np.random.default_rng(seed)
    nb = len(bin_pools)
    need = np.bincount(member_bins, minlength=nb)
    # merged groups: extend a short decile with its neighbours until it has enough candidates
    groups = {}
    merges = 0
    for b in np.where(need > 0)[0]:
        lo = hi = int(b)
        while sum(len(bin_pools[k]) for k in range(lo, hi + 1)) < need[b] and (lo > 0 or hi < nb - 1):
            lo, hi = max(0, lo - 1), min(nb - 1, hi + 1)
            merges += 1
        groups[int(b)] = np.concatenate([pool_memb[k] for k in range(lo, hi + 1)])
    vals = np.empty(draws)
    for d in range(draws):
        mm = []
        for b in np.where(need > 0)[0]:
            cand = groups[int(b)]
            k = min(int(need[b]), len(cand))
            mm.append(cand[rng.choice(len(cand), size=k, replace=False)])
        vals[d] = cross_share(np.concatenate(mm))
    return float(np.nanmean(vals)), merges
