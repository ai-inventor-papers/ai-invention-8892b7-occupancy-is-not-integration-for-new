"""T1 unit tests: closure on toy graphs, participation, Baselga triple, Kleinberg on a known burst,
Holm, and a hand check of one mini-run focal node's P from its community edge shares."""

import json
import sys

import numpy as np
import pandas as pd
import scipy.sparse as sp

import analysis as A
import features as FT
import network as N


def adj(n, edges):
    e = np.array(edges)
    return sp.csr_matrix((np.ones(2 * len(e)), (np.r_[e[:, 0], e[:, 1]], np.r_[e[:, 1], e[:, 0]])), shape=(n, n))


def test_closure():
    # triangle among T = {0,1,2} plus a sparse periphery: obs = 3 > Chung-Lu expectation -> positive log-ratio
    edges = [(0, 1), (1, 2), (0, 2)] + [(i, i + 1) for i in range(3, 40)]
    Ab = adj(41, edges)
    deg = np.asarray(Ab.sum(1)).ravel()
    obs, exp = N.closure_counts(Ab, np.array([0, 1, 2]), deg, len(edges))
    assert obs == 3 and N.closure_lr(obs, exp) > 0, (obs, exp)
    # star: hub 0 with leaves 1..10; T = leaves -> obs = 0
    edges = [(0, i) for i in range(1, 11)]
    Ab = adj(11, edges)
    deg = np.asarray(Ab.sum(1)).ravel()
    obs, exp = N.closure_counts(Ab, np.arange(1, 11), deg, len(edges))
    assert obs == 0 and N.closure_lr(obs, exp) <= 0, (obs, exp)
    print("closure ok", obs, round(exp, 4))


def test_participation():
    assert abs(N.participation(np.array([1.0, 1.0])) - 0.5) < 1e-12
    assert abs(N.participation(np.array([5.0, 0, 0]))) < 1e-12
    assert abs(N.participation(np.array([2.0, 1.0, 1.0])) - (1 - (0.25 + 0.0625 * 2))) < 1e-12
    print("participation ok")


def test_baselga():
    # hand example: N_prev = {1,2,3,4}, N = {3,4,5,6,7}: a=2, b=3, c=2
    Np, Nc = {1, 2, 3, 4}, {3, 4, 5, 6, 7}
    a, b, c = len(Nc & Np), len(Nc - Np), len(Np - Nc)
    bsor = (b + c) / (2 * a + b + c)
    bsim = min(b, c) / (a + min(b, c))
    assert (a, b, c) == (2, 3, 2)
    assert abs(bsor - 5 / 9) < 1e-12 and abs(bsim - 0.5) < 1e-12
    acc = np.sign(b - c) * (bsor - bsim) / bsor
    assert abs(acc - (5 / 9 - 0.5) / (5 / 9)) < 1e-12
    print("baselga ok", round(bsor, 4), bsim, round(acc, 4))


def test_kleinberg():
    r = np.array([5] * 10 + [25] * 5 + [5] * 5)
    d = np.full(len(r), 1000)
    st, w = FT.kleinberg_batched(r, d, 2.0, 1.0)
    assert st[10:15].all() and not st[:9].any() and not st[16:].any(), st
    assert (w[10:15] > 0).all() and (w[:9] == 0).all()
    print("kleinberg ok", st.tolist())


def test_holm():
    adj_ = A.holm([0.01, 0.04, 0.03])
    assert np.allclose(adj_, [0.03, 0.06, 0.06]), adj_
    print("holm ok", adj_)


def test_focal_p_by_hand(year: int = 2010):
    """Recompute P of one focal node from the saved community labels and its neighbour list."""
    import json as _j
    from pathlib import Path
    snap = Path(__file__).resolve().parent / "results" / "snapshots"
    f = pd.read_parquet(snap / f"focal_{year}.parquet")
    nd = pd.read_parquet(snap / f"nodes_{year}.parquet").set_index("tag")
    twins = _j.loads((Path(__file__).resolve().parent / "results" / "intermediate" / "twins.json").read_text())
    mw = pd.read_parquet(Path(__file__).resolve().parent / "results" / "intermediate" / "mesh_works.parquet")
    r = f[f.k > 0].sort_values("k").iloc[len(f[f.k > 0]) // 2]
    w = mw[mw.primary & (mw.concept_id == r.concept_id) & mw.year.between(year - 2, year)].drop_duplicates("work_id")
    cnt = {}
    for tags in w.tags:
        for t in set(tags):
            if t not in set(twins.get(r.concept_id, [])):
                cnt[t] = cnt.get(t, 0) + 1
    nb = list(r.neighbours)
    assert all(cnt[t] >= 2 for t in nb)
    shares = {}
    for t in nb:
        shares[nd.at[t, "comm_local"]] = shares.get(nd.at[t, "comm_local"], 0) + cnt[t]
    tot = sum(shares.values())
    P = 1 - sum((v / tot) ** 2 for v in shares.values())
    assert abs(P - r.P) < 1e-9, (P, r.P)
    assert abs(tot - r.s) < 1e-9 and int(r.W_c) == len(w)
    print("focal P by hand ok", r.concept_id, round(P, 4), "k", r.k, "s", r.s)


if __name__ == "__main__":
    test_closure()
    test_participation()
    test_baselga()
    test_kleinberg()
    test_holm()
    if len(sys.argv) > 1:
        test_focal_p_by_hand(int(sys.argv[1]))
    print(json.dumps({"tests": "passed"}))
