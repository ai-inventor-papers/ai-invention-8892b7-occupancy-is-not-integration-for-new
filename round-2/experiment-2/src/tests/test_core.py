"""T0 unit tests: toy lineage, BH, bootstrap coverage, state truth table."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from statsmodels.stats.multitest import multipletests

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from labels import bh_reject, bootstrap_edge, state_of  # noqa: E402
from leakage import w1_view  # noqa: E402
from lineage import EdgeVec, canonical_main, edge_vectors, parentage, point_estimates  # noqa: E402


def toy():
    rows = [(2010, 1702, 100), (2011, 2208, 90), (2012, 1702, 80), (2012, 1702, 70), (2012, 1702, 60),
            (2012, 2208, 1), (2013, 2208, 1), (2014, 2208, 0), (2015, 2208, 0), (2015, 1702, 0), (2016, 2208, 0)]
    p = pd.DataFrame(rows, columns=["year", "sub", "cbc"])
    p["work_id"] = np.arange(100, 100 + len(p))
    p["field"] = p["sub"] // 100
    p["n_refs"] = [0, 0, 0, 0, 0, 0, 0, 2, 1, 1, 2]
    p["n_kw"] = 0
    p["lenient_excl_F"] = False
    cites = np.array([[7, 5], [7, 6], [8, 1], [9, 6], [10, 9], [10, 6]], np.int32)
    return {"papers": p, "cites": cites}


def test_toy_lineage():
    c = toy()
    canon = canonical_main(c["papers"], 2010)
    assert canon == {100, 101, 102, 103, 104}
    v = w1_view(c, 2016)
    par = parentage(v, canon, 2016)
    ev = edge_vectors(v, par, 2208, 2016)
    assert ev.n_parents == 2 and ev.n_children == 5
    w6_10 = np.exp(-1.5) / (np.exp(-0.5) + np.exp(-1.5))
    pe = point_estimates(ev)
    assert abs(pe["rho"] - (1 + w6_10) / 2) < 1e-9
    assert abs(pe["m"] - (1 - w6_10) / 2) < 1e-9
    assert abs(ev.stats["untraced_share"] - 3 / 5) < 1e-9
    assert abs(ev.stats["background_only_share"] - 1 / 5) < 1e-9
    assert abs(ev.stats["within_host_share"] - 2 / 5) < 1e-9
    # weights of child 7: exp(-1) and exp(-0.5) normalised
    sel = par.ch == 7
    ws = dict(zip(par.pa[sel], par.w[sel]))
    z = np.exp(-1) + np.exp(-0.5)
    assert abs(ws[5] - np.exp(-1) / z) < 1e-9 and abs(ws[6] - np.exp(-0.5) / z) < 1e-9


def test_bh_matches_statsmodels():
    rng = np.random.default_rng(0)
    for _ in range(50):
        p = rng.uniform(size=rng.integers(1, 30)) ** 2
        assert np.array_equal(bh_reject(p), multipletests(p, alpha=0.10, method="fdr_bh")[0])


def test_bootstrap_coverage():
    rng = np.random.default_rng(1)
    hits = 0
    R = 300
    for i in range(R):
        n = 200
        b = (rng.uniform(size=n) < 0.5).astype(float)
        a = rng.poisson(0.8, size=n).astype(float) * (1 - b)  # children carry a, truth rho = 0.8*0.5/0.5
        ev = EdgeVec(units=np.arange(n), a=a, b=b, imp=np.zeros(n), tr=(a > 0).astype(float),
                     n_parents=int(b.sum()), n_children=n, n_w1=n, stats={})
        o = bootstrap_edge(ev, np.random.default_rng(i), 1000, {"main": 1.0})
        hits += o["rho_lo"] <= 0.8 <= o["rho_hi"]
    cov = hits / R
    assert 0.85 <= cov <= 0.95, cov


@pytest.mark.parametrize("g,l,mlo,exp", [(True, False, 0.9, "SOURCE"), (False, True, 0.6, "SINK"),
                                         (False, True, 0.4, "FADING"), (False, True, np.nan, "FADING"),
                                         (False, False, 0.9, "UNDETERMINED"), (True, True, 0.9, "UNDETERMINED")])
def test_states(g, l, mlo, exp):
    assert state_of(g, l, mlo) == exp
