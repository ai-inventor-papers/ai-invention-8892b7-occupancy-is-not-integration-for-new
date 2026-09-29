"""Step 7: W2 = [t+1, t+5] disciplinary breadth outcomes (screen only; every outcome function is guarded).

Y1   = H(W2) - H(W1)                               (paper-weighted Shannon over known primary-topic subfields)
Y1r  = mean over 200 paired draws of H(sub_W2) - H(sub_W1) at n* = min(n_W1, n_W2) (n* >= floor, default 20)
Y1r20= the same at fixed n = 20 (coverage-standardised sensitivity)
Y2   = RS(W2) - RS(W1)                             (fixed 2000-04 Rao-Stirling distance)
Y3   = # subfields not active in W1 (< 2 W1 papers) reached by >= 1 author-disjoint NEWCOMER W2 paper
Y3b  = the same with >= 2 newcomer papers
M_W2 = mean xcomm_exc over y in [t+1, t+5]         (mediator; post-t, descriptive only)
W1 = [t-5, t]. A newcomer paper has >= 1 author id and no author among the W1 authors of the concept or their
co-authors on any corpus work published in [t-5, t] (co-authorship is within the hydrated corpus only).
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd
import scipy.sparse as sp
from loguru import logger

import common as K
from common import OUT, WORK, outcome_fn

import lib_metrics as lm
from indicators import load_rs

FDIR = OUT / "d1"
N_DRAWS = 200


class AuthorIndex:
    """works x authors incidence, sliced per 6-year window [t-5, t]."""

    def __init__(self) -> None:
        a = pd.read_parquet(WORK / "authors.parquet")
        lens = a.author_ids.map(lambda x: 0 if x is None else len(x)).values
        flat = np.concatenate([np.asarray(x, dtype=np.int64) for x in a.author_ids.values if x is not None and len(x)])
        self.auth_ids, col = np.unique(flat, return_inverse=True)
        row = np.repeat(np.arange(len(a)), lens)
        self.X = sp.csr_matrix((np.ones(len(flat), dtype=np.int8), (row, col)), shape=(len(a), len(self.auth_ids)))
        self.X.sum_duplicates()
        self.year = a.year.values
        self.row_of = dict(zip(a.work_id.values, range(len(a))))
        self._win: dict = {}
        logger.info(f"author index: {len(a)} works, {len(self.auth_ids)} authors, nnz {self.X.nnz}")

    def window(self, t: int):
        if t not in self._win:
            m = (self.year >= t - 5) & (self.year <= t)
            Xw = self.X[np.where(m)[0]]
            self._win[t] = (Xw.tocsr(), Xw.tocsc())
        return self._win[t]

    def cols(self, work_ids) -> np.ndarray:
        rows = [self.row_of[w] for w in work_ids if w in self.row_of]
        if not rows:
            return np.zeros(0, dtype=np.int64)
        return np.unique(self.X[rows].indices)

    def known_set(self, w1_work_ids, t: int) -> np.ndarray:
        """Boolean mask over authors: W1 authors of the concept plus all their co-authors on works in [t-5, t]."""
        mask = np.zeros(len(self.auth_ids), dtype=bool)
        a1 = self.cols(w1_work_ids)
        if a1.size == 0:
            return mask
        Xr, Xc = self.window(t)
        touched = np.unique(Xc[:, a1].tocoo().row)
        mask[a1] = True
        if touched.size:
            mask[np.unique(Xr[touched].indices)] = True
        return mask


def shannon_codes(x: np.ndarray) -> float:
    return lm.shannon(np.unique(x, return_counts=True)[1]) if x.size else math.nan


def rarefied_delta(s1: np.ndarray, s2: np.ndarray, n: int, seed: int, draws: int = N_DRAWS) -> float:
    if len(s1) < n or len(s2) < n or n < 2:
        return math.nan
    rng = np.random.default_rng(seed)
    v = [shannon_codes(s2[rng.choice(len(s2), n, replace=False)]) - shannon_codes(s1[rng.choice(len(s1), n, replace=False)])
         for _ in range(draws)]
    return float(np.mean(v))


@outcome_fn
def w2_counts(cid: str, t: int, g: pd.DataFrame) -> dict:
    """Window sizes only (volume, not breadth) - used for the F4 floor decision before any outcome is computed."""
    k = g[g.subfield >= 0]
    n1 = int(((k.year >= t - 5) & (k.year <= t)).sum())
    n2 = int(((k.year >= t + 1) & (k.year <= t + 5)).sum())
    return dict(n_W1k=n1, n_W2k=n2, n_star=min(n1, n2))


@outcome_fn
def breadth_outcomes(cid: str, t: int, g: pd.DataFrame, D: np.ndarray, sidx: dict, floor: int) -> dict:
    k = g[g.subfield >= 0]
    s1 = k.subfield.values[((k.year >= t - 5) & (k.year <= t)).values]
    s2 = k.subfield.values[((k.year >= t + 1) & (k.year <= t + 5)).values]
    n_star = min(len(s1), len(s2))
    c1 = dict(zip(*np.unique(s1, return_counts=True)))
    c2 = dict(zip(*np.unique(s2, return_counts=True)))
    rs1 = lm.rao_stirling({int(a): b for a, b in c1.items()}, dist_matrix=D, index=sidx) if c1 else math.nan
    rs2 = lm.rao_stirling({int(a): b for a, b in c2.items()}, dist_matrix=D, index=sidx) if c2 else math.nan
    H1, H2 = shannon_codes(s1), shannon_codes(s2)
    Y1r = rarefied_delta(s1, s2, n_star, lm.stable_seed(cid, t, "Y1r")) if n_star >= floor else math.nan
    Y1r_fixed = rarefied_delta(s1, s2, floor, lm.stable_seed(cid, t, "Y1rfix"))
    return dict(n_W2=len(s2), H_W2=H2, RS_W2=rs2, Y1=H2 - H1 if len(s1) and len(s2) else math.nan,
                Y1r=Y1r, Y1r_fixed=Y1r_fixed, Y2=rs2 - rs1 if np.isfinite(rs1) and np.isfinite(rs2) else math.nan)


@outcome_fn
def newcomer_outcome(cid: str, t: int, g: pd.DataFrame, AI: AuthorIndex) -> dict:
    w1 = g[(g.year >= t - 5) & (g.year <= t)]
    w2 = g[(g.year >= t + 1) & (g.year <= t + 5)]
    known = AI.known_set(w1.work_id.values, t)
    w1c = w1[w1.subfield >= 0].subfield.value_counts()
    active = set(w1c[w1c >= 2].index.astype(int))
    n_missing = 0
    new_by_sub: dict = {}
    n_newcomer = 0
    for wid, sub in zip(w2.work_id.values, w2.subfield.values):
        r = AI.row_of.get(wid)
        cols = AI.X[r].indices if r is not None else np.zeros(0, dtype=np.int64)
        if cols.size == 0:
            n_missing += 1
            continue
        if not known[cols].any():
            n_newcomer += 1
            if sub >= 0:
                new_by_sub[int(sub)] = new_by_sub.get(int(sub), 0) + 1
    Y3 = sum(1 for d, n in new_by_sub.items() if d not in active and n >= 1)
    Y3b = sum(1 for d, n in new_by_sub.items() if d not in active and n >= 2)
    return dict(Y3=Y3, Y3b=Y3b, n_newcomer_W2=n_newcomer, share_W2_missing_authors=(n_missing / len(w2)) if len(w2) else math.nan,
                n_known_authors=int(known.sum()))


@outcome_fn
def mediator(cid: str, t: int, xc: dict) -> float:
    v = [xc.get((cid, y), np.nan) for y in range(t + 1, t + 6)]
    v = [x for x in v if np.isfinite(x)]
    return float(np.mean(v)) if v else math.nan


def run(mini: bool = False) -> None:
    K.load_sealed_ids()
    F = pd.read_parquet(FDIR / "features_ct.parquet")
    cp = pd.read_parquet(WORK / "cp.parquet", columns=["concept_id", "work_id", "year", "subfield"])
    cp = cp[cp.concept_id.isin(set(F.concept_id))]
    groups = dict(tuple(cp.groupby("concept_id")))
    # ---- F4: floor decision from window sizes only
    cnt = pd.DataFrame([dict(concept_id=c, t=t, **w2_counts(c, t, groups[c])) for c, t in zip(F.concept_id, F.t)])
    main_rows = F.in_MAIN.values
    share_lt20 = float((cnt.n_star[main_rows] < 20).mean())
    floor = 10 if share_lt20 > 0.40 else 20
    dec_path = FDIR / "rowcount_decision.json"
    import json
    dec = json.loads(dec_path.read_text()) if dec_path.exists() else {}
    dec.update(F4_rule="if n* < 20 in > 40% of MAIN rows -> Y1r floor 10 and Y1r20 -> Y1r10",
               F4_share_nstar_lt20=share_lt20, F4_triggered=bool(floor == 10), Y1r_floor=floor)
    K.write_json(dec_path, dec)
    logger.info(f"F4: share n*<20 among MAIN rows = {share_lt20:.3f} -> floor {floor}")
    D, sidx = load_rs()
    AI = AuthorIndex()
    ind = pd.read_parquet(WORK / "indicators_open.parquet", columns=["concept_id", "year", "xcomm_exc", "vol"])
    xc = {(c, int(y)): v for c, y, v in zip(ind.concept_id, ind.year, ind.xcomm_exc)}
    vol = {(c, int(y)): v for c, y, v in zip(ind.concept_id, ind.year, ind.vol)}
    rows = []
    for i, (c, t) in enumerate(zip(F.concept_id, F.t)):
        g = groups[c]
        r = dict(concept_id=c, t=int(t))
        r.update(breadth_outcomes(c, t, g, D, sidx, floor))
        r.update(newcomer_outcome(c, t, g, AI))
        r["M_W2"] = mediator(c, t, xc)
        r["log_vol_W2"] = math.log1p(sum(vol.get((c, y), 0) for y in range(t + 1, t + 6)))  # leaky-feature check only
        rows.append(r)
        if i % 100 == 0:
            logger.info(f"outcomes {i + 1}/{len(F)}")
    O = pd.DataFrame(rows).merge(cnt, on=["concept_id", "t"])
    O = O.rename(columns={"Y1r_fixed": f"Y1r{floor}"})
    O["log1p_Y3"] = np.log1p(O.Y3)
    O["any_new"] = (O.Y3 > 0).astype(int)
    O.to_parquet(FDIR / "outcomes_ct.parquet", index=False)
    m = O.merge(F[["concept_id", "t", "in_MAIN"]], on=["concept_id", "t"])
    mm = m[m.in_MAIN]
    summ = dict(n_rows=len(O), Y1r_finite_share_main=float(mm.Y1r.notna().mean()),
                Y3_zero_share_main=float((mm.Y3 == 0).mean()),
                W2_missing_author_share_main=float(np.nanmean(mm.share_W2_missing_authors)),
                describe={c: mm[c].describe().to_dict() for c in ("Y1", "Y1r", f"Y1r{floor}", "Y2", "Y3", "Y3b", "M_W2")},
                guard_calls=K.GUARD_CALLS["n"])
    K.write_json(FDIR / "outcomes_summary.json", summ)
    logger.info(f"outcomes: {summ['n_rows']} rows; Y1r finite (MAIN) {summ['Y1r_finite_share_main']:.2f}; "
                f"Y3 zeros {summ['Y3_zero_share_main']:.2f}; missing authors {summ['W2_missing_author_share_main']:.3f}")
