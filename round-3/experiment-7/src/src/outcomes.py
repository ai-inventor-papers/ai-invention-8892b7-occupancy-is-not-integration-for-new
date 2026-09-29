"""STAGE 6: W2 outcomes (screen fold only; every call is guarded by assert_not_sealed).

Prior set Pset(c, e) = authors of any c-paper in [e-5, e] UNION their co-authors on ANY corpus work (all 463k)
published in [e-5, e]. W2 = [e+1, e+5].
  Y_strict  W2 d-papers of c with no author in Pset (papers without author ids are excluded and counted)
  Y_lenient W2 d-papers of c with >= 1 author not in Pset
  Y_all     all W2 d-papers of c
  EST_bin   Y_strict >= 3 AND d-papers present in >= 3 of the 5 W2 years
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from loguru import logger
from scipy import sparse

import config
from config import assert_not_sealed


class CoauthorIndex:
    """works x authors CSR restricted per 6-year window [e-5, e]; built lazily and cached per e."""

    def __init__(self, G: dict):
        ptr, idx = G["AU"]
        n = len(ptr) - 1
        self.M = sparse.csr_matrix((np.ones(len(idx), np.int8), idx, ptr), shape=(n, G["n_authors"]))
        self.year = G["W"]["year"]
        self.cache: dict[int, sparse.csr_matrix] = {}

    def window(self, e: int) -> sparse.csr_matrix:
        if e not in self.cache:
            rows = np.flatnonzero((self.year >= e - 5) & (self.year <= e))
            self.cache[e] = self.M[rows]
        return self.cache[e]

    def prior_set(self, authors: np.ndarray, e: int) -> np.ndarray:
        """Boolean mask over authors: seeds plus co-authors on any corpus work in [e-5, e]."""
        Mw = self.window(e)
        v = np.zeros(self.M.shape[1], np.int8)
        v[authors] = 1
        hit = np.flatnonzero(Mw @ v)
        mask = np.zeros(self.M.shape[1], bool)
        mask[authors] = True
        if len(hit):
            mask[np.unique(Mw[hit].indices)] = True
        return mask


def compute_Y(G: dict, events: pd.DataFrame, cai: CoauthorIndex | None = None, direct_only: bool = False) -> pd.DataFrame:
    """Outcomes for the given events. Raises for any sealed (held-out) concept."""
    assert_not_sealed(events.concept_id.unique())
    W = G["W"]
    AUp, AUi = G["AU"]
    cai = cai or CoauthorIndex(G)
    out = []
    for cid, g in events.groupby("concept_id"):
        assert_not_sealed([cid])
        r, y = G["links"][cid]
        sub = W["sub"][r]
        pset_cache: dict[int, np.ndarray] = {}
        for ev in g.itertuples():
            d, e = int(ev.d), int(ev.e)
            if e not in pset_cache:
                seeds = np.unique(np.concatenate([AUi[AUp[k]:AUp[k + 1]] for k in r[(y >= e - 5) & (y <= e)]]
                                                 or [np.zeros(0, np.int64)]))
                if direct_only:
                    m = np.zeros(G["n_authors"], bool)
                    m[seeds] = True
                    pset_cache[e] = m
                else:
                    pset_cache[e] = cai.prior_set(seeds, e)
            ps = pset_cache[e]
            w2 = (sub == d) & (y >= e + 1) & (y <= e + 5)
            strict = lenient = noauth = 0
            by_year = {k: 0 for k in range(1, 6)}
            for k, yy in zip(r[w2], y[w2]):
                a = AUi[AUp[k]:AUp[k + 1]]
                if len(a) == 0:
                    noauth += 1
                    continue
                inp = ps[a]
                if not inp.any():
                    strict += 1
                    by_year[int(yy) - e] += 1
                if not inp.all():
                    lenient += 1
            yrs_present = len(set((y[w2] - e).tolist()))
            out.append({"index": ev.Index, "Y_strict": strict, "Y_lenient": lenient, "Y_all": int(w2.sum()),
                        "n_w2_noauthor": noauth, "w2_years_present": yrs_present,
                        "EST_bin": int(strict >= 3 and yrs_present >= 3),
                        "present_e5": int(((sub == d) & (y == e + 5)).any()),
                        "present_e45": int(((sub == d) & (y >= e + 4) & (y <= e + 5)).any()),
                        **{f"Y_strict_t{k}": v for k, v in by_year.items()},
                        "pset_size": int(ps.sum())})
    res = pd.DataFrame(out).set_index("index")
    logger.info(f"outcomes: {len(res)} events; Y_strict zero share {float((res.Y_strict == 0).mean()):.3f}")
    return res


def compute_Y_shifted(G: dict, events: pd.DataFrame, cai: CoauthorIndex, shift: int = 1) -> pd.Series:
    """Y_strict over W2 shifted by `shift` years ([e+1+shift, e+5+shift]), Pset window unchanged (robustness)."""
    assert_not_sealed(events.concept_id.unique())
    W = G["W"]
    AUp, AUi = G["AU"]
    vals = {}
    for cid, g in events.groupby("concept_id"):
        r, y = G["links"][cid]
        sub = W["sub"][r]
        for ev in g.itertuples():
            d, e = int(ev.d), int(ev.e)
            seeds = np.unique(np.concatenate([AUi[AUp[k]:AUp[k + 1]] for k in r[(y >= e - 5) & (y <= e + shift)]]
                                             or [np.zeros(0, np.int64)]))
            ps = cai.prior_set(seeds, e + shift)
            w2 = (sub == d) & (y >= e + 1 + shift) & (y <= e + 5 + shift)
            s = 0
            for k in r[w2]:
                a = AUi[AUp[k]:AUp[k + 1]]
                if len(a) and not ps[a].any():
                    s += 1
            vals[ev.Index] = s
    return pd.Series(vals)


__all__ = ["compute_Y", "compute_Y_shifted", "CoauthorIndex", "config"]
