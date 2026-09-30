"""STEP 2: Gate A. Lenient loader check first, then the within-host share per edge and the verdict (applied once)."""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
from loguru import logger

from common import RESULTS

EXPECT = {"main_host": (0.5518, 41861), "by_year": {2010: 0.3174, 2011: 0.3613, 2012: 0.3476, 2013: 0.4130, 2014: 0.5171},
          "ref_any": (0.5311, 92969)}
OUT = RESULTS / "gate_a"


def lenient_check(lk: pd.DataFrame) -> dict:
    m = lk[lk.arm == "main"]
    h = m[m.outside_origin]
    r = lk[lk.arm == "reference"]
    got = {"main_host": (round(float(h.traced_excl_F.mean()), 4), int(len(h))),
           "by_year": {y: round(float(h[h.year == y].traced_excl_F.mean()), 4) for y in EXPECT["by_year"]},
           "ref_any": (round(float(r.traced_any.mean()), 4), int(len(r)))}
    ok = (abs(got["main_host"][0] - EXPECT["main_host"][0]) < 5e-4 and got["main_host"][1] == EXPECT["main_host"][1]
          and all(abs(got["by_year"][y] - v) < 5e-4 for y, v in EXPECT["by_year"].items())
          and abs(got["ref_any"][0] - EXPECT["ref_any"][0]) < 5e-4 and got["ref_any"][1] == EXPECT["ref_any"][1])
    res = {"expected": EXPECT, "reproduced": got, "pass": bool(ok),
           "definition": "assemble.py lines 360-377: no dedup; parents = refs in cset with year < child year; "
                         "traced_excl_F; host = subfield != origin_subfield"}
    if not ok:
        raise RuntimeError(f"LOADER CHECK FAILED: {got}")
    logger.info(f"lenient loader check PASS: {got}")
    return res


def summarise(df: pd.DataFrame, col: str = "within_host_share") -> dict:
    s = df[col].dropna()
    if not len(s):
        return {"n_edges": 0}
    cw = df.groupby("concept_id")[col].mean()
    return {"n_edges": int(len(s)), "n_concepts": int(df.concept_id.nunique()),
            "mean": round(float(s.mean()), 4), "q10": round(float(s.quantile(.1)), 4),
            "q25": round(float(s.quantile(.25)), 4), "median": round(float(s.median()), 4),
            "q75": round(float(s.quantile(.75)), 4), "q90": round(float(s.quantile(.9)), 4),
            "share_ge_040": round(float((s >= 0.40).mean()), 4),
            "concept_weighted_mean": round(float(cw.mean()), 4),
            "concept_weighted_share_ge_040": round(float(df.assign(g=df[col] >= .4).groupby("concept_id").g.mean().mean()), 4)}


def gate_a_tables(edges: pd.DataFrame, refs: pd.DataFrame, concepts: pd.DataFrame) -> dict:
    OUT.mkdir(parents=True, exist_ok=True)
    meta = concepts.set_index("concept_id")
    e = edges.copy()
    e["fold"] = e.concept_id.map(meta.fold)
    e["F_band"] = e.concept_id.map(meta.F_band)
    host = e[e.role == "host"]
    orig = e[e.role == "origin"]
    host.to_parquet(OUT / "gate_a_host_edges.parquet", index=False)
    # verdict set: host edge-years with |Kd| >= 10
    vs = host[host.n_children >= 10]
    share = float((vs.within_host_share >= 0.40).mean()) if len(vs) else float("nan")
    verdict_pass = bool(len(vs) and share > 0.5)
    per_year = {int(t): summarise(g) for t, g in vs.groupby("t")}
    per_fold = {f: summarise(g) for f, g in vs.groupby("fold")}
    per_age = {int(a): summarise(g) for a, g in vs.groupby("age")}
    refs = refs.rename(columns={"ref_id": "concept_id"})
    ref_host = refs[~refs.is_modal & (refs.n_children >= 10)]
    ref_modal = refs[refs.is_modal & (refs.n_children >= 10)]
    tabs = []
    for (f, t), g in host.groupby(["fold", "t"]):
        tabs.append({"arm": "main", "fold": f, "t": int(t), "n_edges": len(g), "n_edges_K10": int((g.n_children >= 10).sum()),
                     "lenient_share_mean": g.lenient_share.mean(), "within_host_share_mean": g.within_host_share.mean(),
                     "within_host_share_refs_mean": g.within_host_share_refs.mean(),
                     "share_ge_040_K10": float((g[g.n_children >= 10].within_host_share >= .4).mean()) if (g.n_children >= 10).any() else np.nan})
    for t, g in refs[~refs.is_modal].groupby("t"):
        tabs.append({"arm": "reference", "fold": "reference", "t": int(t), "n_edges": len(g), "n_edges_K10": int((g.n_children >= 10).sum()),
                     "lenient_share_mean": g.lenient_share.mean(), "within_host_share_mean": g.within_host_share.mean(),
                     "within_host_share_refs_mean": g.within_host_share_refs.mean(),
                     "share_ge_040_K10": float((g[g.n_children >= 10].within_host_share >= .4).mean()) if (g.n_children >= 10).any() else np.nan})
    pd.DataFrame(tabs).to_csv(OUT / "gate_a_by_arm_fold_year.csv", index=False)
    subset_share = float((host.within_host_share <= host.lenient_share + 1e-12).mean())
    verdict = {
        "verdict": "PASS" if verdict_pass else "FAIL -> graft fallback supplies H1/H2 labels in iteration 3",
        "share_edges_ge_040": round(share, 4), "n_edges": int(len(vs)), "n_concepts": int(vs.concept_id.nunique()),
        "rule": "PASS iff > 50% of main-arm host edge-years with |Kd| >= 10 have within-host share >= 0.40 (pooled, applied once)",
        "pooled_summary": summarise(vs), "pooled_summary_secondary_denominator": summarise(vs, "within_host_share_refs"),
        "lenient_any_parent_same_edges": summarise(vs, "lenient_share"),
        "per_year_descriptive": per_year, "per_fold_descriptive": per_fold, "per_age_descriptive": per_age,
        "within_origin_contrast": summarise(orig[orig.n_children >= 10]),
        "reference_arm_same_stat": {"host_edges": summarise(ref_host), "modal_subfield_edges": summarise(ref_modal)},
        "share_edges_within_le_lenient": round(subset_share, 4),
        "untraced_share_mean_K10": round(float(vs.untraced_share.mean()), 4) if len(vs) else None,
        "background_only_share_mean_K10": round(float(vs.background_only_share.mean()), 4) if len(vs) else None,
        "status_of_downstream": "labels are DESCRIPTIVE ONLY" if not verdict_pass else "labels usable for H1/H2 screen",
    }
    (OUT / "gate_A_verdict.json").write_text(json.dumps(verdict, indent=2, default=float))
    logger.info(f"GATE A: {verdict['verdict']} share>=0.40 = {share:.4f} over {len(vs)} edges / {verdict['n_concepts']} concepts")
    return verdict


def graft_fallback(G: dict) -> dict:
    """Host entry events (c, d != o, e): e = first year with >= 1 d-paper (e <= 2019); proxy: >= 5 distinct keywords."""
    con = G["concepts"].set_index("concept_id")
    rows = []
    for cid, c in con[con.arm == "main"].iterrows():
        p = G["per"][cid]["papers"]
        kw = G["kw"][cid]
        o = int(c.origin_sub) if pd.notna(c.origin_sub) else -999
        for d, g in p[(p["sub"] >= 0) & (p["sub"] != o)].groupby("sub"):
            e = int(g.year.min())
            if e > 2019:
                continue
            idx = g.index[g.year == e]
            nk = len(set(np.concatenate([np.asarray(kw[i]) for i in idx])) if len(idx) else set())
            rows.append({"concept_id": cid, "d": int(d), "e": e, "fold": c.fold, "n_kw": nk, "anchored_proxy": nk >= 5,
                         "e_ge_F": e >= int(c.F)})
    df = pd.DataFrame(rows)
    df.to_csv(OUT / "graft_fallback_events.csv", index=False)
    res = {"n_events_all": int(len(df)), "n_events_kw5": int(df.anchored_proxy.sum()),
           "n_events_kw5_e_ge_F": int((df.anchored_proxy & df.e_ge_F).sum()),
           "by_fold": {f: {"events": int(len(g)), "kw5": int(g.anchored_proxy.sum()), "concepts": int(g.concept_id.nunique())}
                       for f, g in df.groupby("fold")},
           "note": "keyword_idx co-occurrence is a provisional proxy; the concept-concept network is another artifact"}
    (OUT / "graft_fallback_summary.json").write_text(json.dumps(res, indent=2))
    return res
