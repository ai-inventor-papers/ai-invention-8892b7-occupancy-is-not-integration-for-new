"""Toy checks: rarefied entropy change, newcomer rule, growing-edge breadth."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import scipy.sparse as sp

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import features as FE  # noqa: E402
import outcomes as OC  # noqa: E402


def test_y1r_duplicated_window_is_zero():
    s1 = np.repeat([1, 2, 3, 4], [10, 8, 6, 6])
    s2 = s1.copy()
    v = OC.rarefied_delta(s1, s2, 30, seed=1, draws=50)   # n* = full size -> exact 0
    assert abs(v) < 1e-12
    v2 = OC.rarefied_delta(s1, s2, 20, seed=1, draws=400)
    assert abs(v2) < 0.03


def test_y1r_floor():
    assert np.isnan(OC.rarefied_delta(np.arange(5), np.arange(30), 20, seed=0))


class ToyAI(OC.AuthorIndex):
    def __init__(self, work_authors: dict, years: dict):
        wids = list(work_authors)
        self.auth_ids = np.array(sorted({a for v in work_authors.values() for a in v}))
        col = {a: i for i, a in enumerate(self.auth_ids)}
        rows, cols = [], []
        for r, w in enumerate(wids):
            for a in work_authors[w]:
                rows.append(r)
                cols.append(col[a])
        self.X = sp.csr_matrix((np.ones(len(rows), dtype=np.int8), (rows, cols)), shape=(len(wids), len(self.auth_ids)))
        self.year = np.array([years[w] for w in wids])
        self.row_of = {w: i for i, w in enumerate(wids)}
        self._win = {}


def test_newcomer_rule():
    # W1 (t=2010): work 1 by author A (concept), work 2 by A+B (other concept) -> B is a co-author
    # W2: work 3 by B (known), work 4 by C (newcomer, subfield 7), work 5 by D (newcomer, subfield 1 active in W1)
    wa = {1: [10], 2: [10, 11], 3: [11], 4: [12], 5: [13], 6: []}
    yrs = {1: 2008, 2: 2009, 3: 2012, 4: 2013, 5: 2014, 6: 2012}
    AI = ToyAI(wa, yrs)
    g = pd.DataFrame(dict(work_id=[1, 1, 3, 4, 5, 6], year=[2008, 2008, 2012, 2013, 2014, 2012],
                          subfield=[1, 1, 7, 7, 1, 9]))
    g = g.drop_duplicates("work_id")
    g = pd.concat([g, pd.DataFrame(dict(work_id=[7], year=[2009], subfield=[1]))])
    AI.row_of[7] = AI.row_of[1]
    r = OC.newcomer_outcome.__wrapped__("c_toy", 2010, g, AI)
    assert r["n_newcomer_W2"] == 2          # works 4 and 5
    assert r["Y3"] == 1                      # only subfield 7 is new (subfield 1 has 2 W1 papers)
    assert abs(r["share_W2_missing_authors"] - 1 / 4) < 1e-12


def test_growing_edge_flat_is_zero():
    years = np.repeat(np.arange(2005, 2011), 3)
    subs = np.tile([1, 2, 3], 6)
    assert FE.growing_edge(years, subs, 2010) == (0.0, 0)


def test_growing_edge_detects_growth():
    years = np.concatenate([np.repeat(np.arange(2005, 2011), [1, 2, 4, 8, 16, 32]), np.repeat(np.arange(2005, 2011), 2)])
    subs = np.concatenate([np.full(63, 5), np.full(12, 6)])
    geb, n = FE.growing_edge(years, subs, 2010)
    assert n == 1 and geb == 0.0
