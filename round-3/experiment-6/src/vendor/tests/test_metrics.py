"""Unit tests with hand-computable answers for lib_metrics (run: .venv/bin/python -m pytest -q tests)."""
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import lib_metrics as lm  # noqa: E402


def test_baselga_nested():
    sor, sim, sne = lm.baselga({1, 2, 3}, {1, 2, 3, 4, 5})
    assert sim == 0.0
    assert math.isclose(sor, 0.25) and math.isclose(sne, 0.25)
    assert math.isclose(lm.sne_share(sor, sne), 1.0)


def test_baselga_turnover():
    sor, sim, sne = lm.baselga({1, 2}, {3, 4})
    assert sim == 1.0 and sor == 1.0 and sne == 0.0


def test_baselga_empty():
    assert all(math.isnan(v) for v in lm.baselga(set(), set()))


def test_participation():
    assert math.isclose(lm.participation({"a": 3, "b": 3}), 0.5)
    assert lm.participation({"a": 7}) == 0.0
    assert math.isnan(lm.participation({}))


def test_association_strength_hand():
    # c_ij = 4, W_i = 10, W_j = 8, W_tot = 100 -> 4*100/80 = 5
    assert math.isclose(float(lm.association_strength(4, 10, 8, 100)), 5.0)


def test_kleinberg_planted_burst():
    d = np.full(20, 1000.0)
    r = np.full(20, 10.0)
    r[10:14] = 60.0
    st = lm.kleinberg_states(r, d)
    assert st[10:14].all() and not st[:8].any() and not st[16:].any()


def test_kleinberg_truncation_invariance():
    years = np.arange(2000, 2020)
    d = np.full(20, 1000.0)
    r = np.full(20, 10.0)
    r[8:11] = 50.0
    s_trunc, _ = lm.kleinberg_at(years[:11], r[:11], d[:11], 2010)
    r2 = r.copy()
    r2[11:] = 500.0  # wildly different future
    s_full, _ = lm.kleinberg_at(years, r2, d, 2010)
    assert s_trunc == s_full


def test_closure_planted_clique_vs_er():
    rng = np.random.default_rng(0)
    n = 60
    A = (rng.random((n, n)) < 0.1).astype(float)
    A = np.triu(A, 1)
    A = A + A.T
    s = A.sum(1)
    S = s.sum()
    K = np.arange(10)
    obs_er = A[np.ix_(K, K)].sum() / 2
    exp_er = lm.chung_lu_expected(s[K], S)
    er = lm.closure_log_ratio(obs_er, exp_er, 1e-9)
    B = A.copy()
    B[np.ix_(K, K)] = 1.0
    np.fill_diagonal(B, 0)
    sb = B.sum(1)
    clique = lm.closure_log_ratio(B[np.ix_(K, K)].sum() / 2, lm.chung_lu_expected(sb[K], sb.sum()), 1e-9)
    assert clique > 0.5 and clique > er + 0.5
    assert abs(er) < 0.7


def test_rarefaction_reproducible():
    a = lm.rarefied_draws(30, 10, 5, seed=lm.stable_seed("c", 2010))
    b = lm.rarefied_draws(30, 10, 5, seed=lm.stable_seed("c", 2010))
    assert all((x == y).all() for x, y in zip(a, b))
    assert lm.rarefied_draws(5, 10, 5, seed=1) == []


def test_rao_stirling_and_shannon():
    dist = {("a", "b"): 1.0, ("b", "a"): 1.0}
    assert math.isclose(lm.rao_stirling({"a": 1, "b": 1}, dist=dist), 0.5)
    assert math.isclose(lm.shannon([1, 1]), math.log(2))


def test_holm():
    adj = lm.holm([0.01, 0.04, 0.03])
    assert math.isclose(adj[0], 0.03) and math.isclose(adj[2], 0.06) and math.isclose(adj[1], 0.06)


def test_within_module_z():
    assert math.isclose(lm.within_module_z(3.0, np.array([1.0, 2.0, 3.0])), 1.0)


def test_bh():
    q = lm.bh([0.01, 0.04, 0.03, float("nan")])
    assert math.isclose(q[0], 0.03) and math.isclose(q[1], 0.04) and math.isclose(q[2], 0.04) and math.isnan(q[3])
