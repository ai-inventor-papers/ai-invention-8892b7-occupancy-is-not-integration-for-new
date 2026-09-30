"""Unit tests (1)-(3): Burt ego metrics vs networkx, closure_persist identity, cross-community null."""
from __future__ import annotations

import sys
from pathlib import Path

import networkx as nx
import numpy as np
import pytest
import scipy.sparse as sp

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import common  # noqa: E402,F401  (puts vendor/ on sys.path)
import openness as O  # noqa: E402


def _random_ego(rng, n, dens):
    w_c = rng.uniform(0.1, 5.0, n)
    A = np.zeros((n, n))
    for i in range(n):
        for j in range(i + 1, n):
            if rng.random() < dens:
                A[i, j] = A[j, i] = rng.uniform(0.05, 4.0)
    return w_c, A


def _nx_graph(w_c, A):
    G = nx.Graph()
    n = len(w_c)
    G.add_node("c")
    for j in range(n):
        G.add_edge("c", j, weight=float(w_c[j]))
    for i in range(n):
        for j in range(i + 1, n):
            if A[i, j] > 0:
                G.add_edge(i, j, weight=float(A[i, j]))
    return G


@pytest.mark.parametrize("seed", range(50))
def test_ego_vs_networkx(seed):
    rng = np.random.default_rng(seed)
    n = int(rng.integers(5, 61))
    w_c, A = _random_ego(rng, n, float(rng.uniform(0.0, 0.8)))
    G = _nx_graph(w_c, A)
    ref_c = nx.constraint(G, nodes=["c"], weight="weight")["c"]
    ref_e = nx.effective_size(G, nodes=["c"], weight="weight")["c"]
    got = O.ego_brokerage(w_c, sp.csr_matrix(A))
    assert abs(got["constraint"] - ref_c) < 1e-9
    assert abs(got["effsize"] - ref_e) < 1e-9
    assert abs(got["efficiency"] - ref_e / n) < 1e-9


@pytest.mark.parametrize("k", [5, 7, 20])
def test_star_analytic(k):
    got = O.ego_brokerage(np.ones(k), sp.csr_matrix((k, k)))
    assert abs(got["constraint"] - 1.0 / k) < 1e-12
    assert abs(got["effsize"] - k) < 1e-12
    assert abs(got["cdeg_diag"]) < 1e-12


def test_closure_persist_identity():
    """closure on Kp equals the vendored closure when top_AS(y) == top_AS(y-1); NA when overlap < 5."""
    import attach as AT
    rng = np.random.default_rng(3)
    n = 60
    M = sp.random(n, n, density=0.2, random_state=4, data_rvs=lambda k: rng.uniform(1, 5, k))
    Cw = sp.csr_matrix(sp.triu(M, 1) + sp.triu(M, 1).T)
    s = np.asarray(Cw.sum(1)).ravel()
    K = np.arange(20)
    import lib_metrics as lm
    ref = lm.closure_log_ratio(Cw[K][:, K].sum() / 2.0, lm.chung_lu_expected(s[K], s.sum()), 1.0)
    idx = {int(i): int(i) for i in range(n)}
    got = AT.closure_on_ids(list(range(20)), list(range(20)), idx, Cw, s, float(s.sum()), 1.0)
    assert abs(got[0] - ref) < 1e-12 and got[1] == 20
    na = AT.closure_on_ids(list(range(20)), list(range(16, 36)), idx, Cw, s, float(s.sum()), 1.0)
    assert np.isnan(na[0]) and na[1] == 4


def test_xc_null_deterministic_and_zero_excess():
    rng = np.random.default_rng(0)
    n = 2000
    s = rng.lognormal(0, 1, n)
    memb = rng.integers(0, 30, n)
    edges, b = O.strength_decile_bins(s, 10)
    pools = [np.where(b == k)[0] for k in range(10)]
    pmemb = [memb[p] for p in pools]
    K = rng.choice(n, 20, replace=False)
    a = O.xc_null(b[K], pools, pmemb, 50, 123)
    c = O.xc_null(b[K], pools, pmemb, 50, 123)
    assert a == c
    ex = []
    for d in range(200):
        K = rng.choice(n, 20, replace=False)  # a random draw is its own decile-matched null
        ex.append(O.cross_share(memb[K]) - O.xc_null(b[K], pools, pmemb, 50, d)[0])
    assert abs(float(np.mean(ex))) < 0.02


def test_xc_null_merges_short_decile():
    pools = [np.array([0]), np.arange(1, 50), np.arange(50, 100)]
    pm = [np.array([1]), np.arange(1, 50) % 7, np.arange(50, 100) % 7]
    val, merges = O.xc_null(np.array([0, 0, 0, 1, 2]), pools, pm, 10, 1)
    assert merges >= 1 and np.isfinite(val)
