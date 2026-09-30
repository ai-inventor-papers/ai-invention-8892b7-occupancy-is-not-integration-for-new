"""Per-concept edge computation shared by Gate A (no bootstrap) and the viability layer (bootstrap).

Workers are spawned with the prepared cache loaded once per process (initializer).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from common import B as B_DEFAULT
from common import SEED, h32
from labels import bootstrap_edge
from leakage import w1_view
from lineage import canonical_main, canonical_w1, edge_vectors, momentum, parentage, point_estimates, w1_counts, yearly_counts

_G: dict = {}
REF_YEARS = list(range(2008, 2020))


def init_worker(payload: dict) -> None:
    import io_load
    d = io_load.prepare()
    _G.update(d)
    _G.update(payload)


def focal_years(F: int) -> list[int]:
    return [t for t in range(F + 3, F + 9) if t <= 2019]


def _mom(view, d, t, totals) -> tuple[float, float, float]:
    cnt = yearly_counts(view, d, t)
    yrs = np.arange(t - 5, t + 1)
    tot = np.array([totals.get((int(d), int(y)), 0) for y in yrs], float)
    return momentum(cnt, tot, yrs)


def modal_sub_2000_2004(papers: pd.DataFrame) -> int | None:
    s = papers["sub"][(papers.year >= 2000) & (papers.year <= 2004) & (papers["sub"] >= 0)]
    return int(s.value_counts().idxmax()) if len(s) else None


def reference_concept(cid: str, cdata: dict, totals: dict) -> list[dict]:
    """rho_r(d,t) for every (d,t) with >= 10 W1 d-papers, t = 2008..2019, origin NOT excluded; Gate-A ref stats."""
    papers = cdata["papers"]
    canon = canonical_main(papers, None)
    modal = modal_sub_2000_2004(papers)
    rows = []
    for t in REF_YEARS:
        view = w1_view(cdata, t)
        par = parentage(view, canon, t)
        cnt = w1_counts(view, t)
        for d, nw in cnt.items():
            if nw < 10:
                continue
            ev = edge_vectors(view, par, int(d), t)
            pe = point_estimates(ev)
            sl, lo, hi = _mom(view, int(d), t, totals)
            rows.append({"ref_id": cid, "d": int(d), "t": t, "n_w1": ev.n_w1, "n_children": ev.n_children,
                         "n_parents": ev.n_parents, "rho": pe["rho"], "m": pe["m"], "slope": sl,
                         "is_modal": modal is not None and int(d) == modal, "modal_sub": modal, **ev.stats})
    return rows


def main_concept(cid: str, *, boot: bool, B: int | None = None, rho0: dict | None = None,
                 rho0_boot: dict | None = None, canon_w1: bool = True, data: dict | None = None) -> dict:
    """All edges (c, d, t) for a main concept. rho0: variant -> {(d,t): value}; rho0_boot: {(d,t): ndarray(B)}."""
    G = data if data is not None else _G
    B = B or B_DEFAULT
    meta = G["concepts"].set_index("concept_id").loc[cid]
    cdata = G["per"][cid]
    totals = G["totals"]
    F, o = int(meta.F), (int(meta.origin_sub) if pd.notna(meta.origin_sub) else -999)
    papers = cdata["papers"]
    canon = canonical_main(papers, F)
    rows, ct = [], []
    for t in focal_years(F):
        view = w1_view(cdata, t)
        par = parentage(view, canon, t)
        cnt = w1_counts(view, t)
        ct.append({"concept_id": cid, "t": t, "counts": {int(k): int(v) for k, v in cnt.items()}})
        par_w1 = None
        for d, nw in cnt.items():
            d = int(d)
            if nw < 10:
                continue
            ev = edge_vectors(view, par, d, t)
            pe = point_estimates(ev)
            sl, slo, shi = _mom(view, d, t, totals)
            row = {"concept_id": cid, "t": t, "age": t - F, "d": d, "role": "origin" if d == o else "host",
                   "n_w1": ev.n_w1, "n_children": ev.n_children, "n_parents": ev.n_parents, "eligible": True,
                   "rho": pe["rho"], "m": pe["m"], "mom": sl, "mom_lo": slo, "mom_hi": shi,
                   "t_max_used": int(view.papers.year.max()) if len(view.papers) else None, **ev.stats}
            testable = (d != o) and ev.n_parents >= 1 and ev.n_children >= 5 and ev.stats["n_traced"] >= 1
            if boot and testable:
                rng = np.random.default_rng([SEED, h32(cid), t, d])
                r0 = {k: v.get((d, t), np.nan) for k, v in (rho0 or {}).items()}
                if rho0_boot is not None:
                    r0["refboot"] = rho0_boot.get((d, t), np.full(B, np.nan))
                row.update(bootstrap_edge(ev, rng, B, r0))
                if canon_w1:
                    if par_w1 is None:
                        par_w1 = parentage(view, canonical_w1(view, F, t), t)
                    ev2 = edge_vectors(view, par_w1, d, t)
                    row["n_parents_cw1"], row["n_children_cw1"] = ev2.n_parents, ev2.n_children
                    row["n_traced_cw1"] = ev2.stats["n_traced"]
                    row["rho_cw1"] = point_estimates(ev2)["rho"]
                    if ev2.n_parents >= 1 and ev2.stats["n_traced"] >= 1:
                        rng2 = np.random.default_rng([SEED, h32(cid), t, d, 1])
                        o2 = bootstrap_edge(ev2, rng2, B, {"main": r0.get("main", np.nan)})
                        row["p_greater_cw1"], row["p_less_cw1"] = o2["p_greater_main"], o2["p_less_main"]
                        row["m_lo_cw1"] = o2["m_lo"]
            rows.append(row)
    return {"rows": rows, "ct": ct}


def run_main_task(args: tuple) -> dict:
    cid, kw = args
    return main_concept(cid, **kw)


def run_ref_task(cid: str) -> list[dict]:
    return reference_concept(cid, _G["per"][cid], _G["totals"])
