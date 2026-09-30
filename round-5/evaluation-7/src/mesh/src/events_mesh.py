"""STAGE 5: MeSH host-entry events (W1 only: nothing after the entry year is read except G1's [t, t+1] window).

  entry     for c (not colliding with a main-pool phrase) and d != o(c) with a verified d-paper:
            e = first year with a d-paper; keep iff F <= e <= 2019
  kw5       >= 5 distinct partner nodes over the entry-year d-papers (own nodes dropped); kw3 for the F6 widening
  covered   PubMed coverage rule of stage 4 at 0.50 (0.30 / 0.70 sensitivity)
  MESH_MAIN kw5 & covered(0.50), unless the pre-declared F6 widening fires (decided on W1 design counts only):
            design G = concepts with >= 2 sample events (the concept FE singleton rule), N = events in them;
            if G < 50 or N < 300: (a) kw5 -> kw3; then (b) coverage 0.50 -> 0.30; stop at the first with G >= 50
            (and N >= 300); if none, UNDERPOWERED-BY-DESIGN.
  G1        e1 = first t >= e such that [t, t+1] holds >= 2 d-papers of c including two author-disjoint papers;
            keep t <= 2018 (W2 for G1 = [t+2, t+6])
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
from loguru import logger

import common
from common import RESULTS, dump
from coverage import covered, load_rule

WIDEN = [("declared", "kw5", 0.50), ("F6a", "kw3", 0.50), ("F6b", "kw3", 0.30)]


def mini_concepts(G: dict) -> list[str]:
    con = G["concepts"]
    top = con.sort_values("n_verified_links", ascending=False).concept_id.head(5).tolist()
    rest = con[~con.concept_id.isin(top)].concept_id.tolist()
    rng = np.random.default_rng(42)
    return top + sorted(rng.choice(rest, 5, replace=False).tolist())


def entry_partners(G: dict, rows: np.ndarray, own: set) -> list[np.ndarray]:
    ptr, idx = G["P"]
    out = []
    for r in rows:
        a = idx[ptr[r]:ptr[r + 1]]
        out.append(a[~np.isin(a, list(own))] if own else a)
    return out


def g1_time(G: dict, r: np.ndarray, y: np.ndarray, sub: np.ndarray, d: int, e: int) -> int | None:
    AUp, AUi = G["AU"]
    for t in range(e, 2019):
        rows = r[(sub == d) & (y >= t) & (y <= t + 1)]
        if len(rows) < 2:
            continue
        sets = [set(AUi[AUp[k]:AUp[k + 1]].tolist()) for k in rows]
        sets = [s for s in sets if s]
        for i in range(len(sets)):
            if any(not (sets[i] & sets[j]) for j in range(i + 1, len(sets))):
                return t
    return None


def build(G: dict, pm: dict, concepts: list[str] | None = None) -> tuple[pd.DataFrame, dict]:
    W = G["W"]
    tax = G["tax"]
    con = G["concepts"].set_index("concept_id")
    if concepts is not None:
        con = con.loc[concepts]
    rows, n_pre_F, n_late, n_overlap = [], 0, 0, 0
    for cid, c in con.iterrows():
        if c.overlap_main:
            n_overlap += 1
            continue
        r, y = G["links"][cid]
        sub = W["sub"][r]
        o = int(c.origin)
        own = set(c.own_nodes)
        m = (sub >= 0) & (sub != o)
        for d in np.unique(sub[m]):
            sel = m & (sub == d)
            e = int(y[sel].min())
            if e < int(c.F):
                n_pre_F += 1
                continue
            if e > 2019:
                n_late += 1
                continue
            er = r[sel & (y == e)]
            parts = entry_partners(G, er, own)
            tags = int(sum(len(p) for p in parts))
            distinct = len(set(np.concatenate(parts).tolist())) if tags else 0
            t1 = g1_time(G, r, y, sub, int(d), e)
            f_d = tax["sub_field"].get(int(d), -1)
            rows.append({"concept_id": cid, "d": int(d), "e": e, "o": o, "F": int(c.F),
                         "n_entry_papers": int(len(er)), "n_partner_tags": tags, "n_partners_distinct": distinct,
                         "kw5": distinct >= 5, "kw3": distinct >= 3,
                         "covered50": covered(pm, d, e, 0.50), "covered30": covered(pm, d, e, 0.30),
                         "covered70": covered(pm, d, e, 0.70),
                         "pm_share": pm.get((int(d), "2005-2009" if e < 2010 else ("2010-2014" if e < 2015 else "2015-2019"))),
                         "field_d": f_d, "domain_d": tax["field_domain"].get(f_d, -1),
                         "retrieval_complete": bool(c.retrieval_complete), "rule_parity": bool(c.rule_parity),
                         "g1_t": t1})
    ev = pd.DataFrame(rows)
    info = {"n_concepts_considered": int(len(con)), "overlap_dropped_concepts": n_overlap,
            "entries_pre_F_excluded": n_pre_F, "entries_e_gt_2019_excluded": n_late}
    return ev, info


def design(ev: pd.DataFrame, kw: str, thr: float) -> dict:
    s = ev[ev[kw] & ev[f"covered{int(thr * 100)}"]]
    vc = s.concept_id.value_counts()
    keepc = vc[vc >= 2].index
    return {"events": int(len(s)), "concepts": int(s.concept_id.nunique()),
            "design_G_non_singleton": int(len(keepc)), "design_N_non_singleton": int(s.concept_id.isin(keepc).sum())}


def run(mini: bool = False) -> dict:
    import load_mesh
    G = load_mesh.prepare()
    pm = load_rule()
    out_dir = RESULTS / "mini" if mini else RESULTS
    out_dir.mkdir(exist_ok=True)
    ev, info = build(G, pm, mini_concepts(G) if mini else None)
    steps, chosen = [], None
    for name, kw, thr in WIDEN:
        dsg = design(ev, kw, thr)
        dsg.update({"step": name, "kw": kw, "coverage_threshold": thr})
        steps.append(dsg)
        if dsg["design_G_non_singleton"] >= 50 and dsg["design_N_non_singleton"] >= 300:
            chosen = dsg
            break
    underpowered_by_design = chosen is None
    if chosen is None:
        chosen = steps[-1]
    kwc, thr = chosen["kw"], chosen["coverage_threshold"]
    ev["MESH_MAIN"] = ev[kwc] & ev[f"covered{int(thr * 100)}"]
    ev["event_id"] = np.arange(len(ev))
    ev.to_parquet(out_dir / "events_mesh.parquet", index=False)
    mm = ev[ev.MESH_MAIN]
    by_field = (ev[ev[kwc]].assign(kept=lambda x: x[f"covered{int(thr * 100)}"])
                .groupby(["domain_d", "field_d", "kept"]).size().unstack(fill_value=0).reset_index())
    by_field["field_name"] = by_field.field_d.map(G["tax"]["field_name"])
    by_field.to_csv(out_dir / "entry_counts_by_host_field.csv", index=False)
    summ = {**info, "n_entries_all": int(len(ev)), "kw5": int(ev.kw5.sum()), "kw3": int(ev.kw3.sum()),
            "covered50": int(ev.covered50.sum()), "covered30": int(ev.covered30.sum()),
            "kw5_and_covered50": int((ev.kw5 & ev.covered50).sum()),
            "removed_by_coverage_among_kw": {"n": int((ev[kwc] & ~ev[f"covered{int(thr * 100)}"]).sum()),
                                             "share": float((~ev[ev[kwc]][f"covered{int(thr * 100)}"]).mean())},
            "widening_steps": steps, "chosen": chosen, "underpowered_by_design": underpowered_by_design,
            "MESH_MAIN": {"events": int(len(mm)), "concepts": int(mm.concept_id.nunique()),
                          "by_host_domain": {int(k): int(v) for k, v in mm.domain_d.value_counts().items()},
                          "n_entry_papers_eq_1_share": float((mm.n_entry_papers == 1).mean()),
                          "median_partners_distinct": float(mm.n_partners_distinct.median()),
                          "tags_per_entry_paper_mean": float((mm.n_partner_tags / mm.n_entry_papers).mean())},
            "G1": {"events_with_t": int(mm.g1_t.notna().sum()), "concepts": int(mm[mm.g1_t.notna()].concept_id.nunique())},
            "per_concept_MESH_MAIN": {k: int(v) for k, v in mm.concept_id.value_counts().items()}}
    dump(out_dir / "events_mesh_summary.json", summ)
    logger.info(f"events: { {k: v for k, v in summ.items() if k != 'per_concept_MESH_MAIN'} }")
    return summ


def load_events(mini: bool = False) -> pd.DataFrame:
    return pd.read_parquet((RESULTS / "mini" if mini else RESULTS) / "events_mesh.parquet")
