"""STEP 5: the four medoid-selected cases with subfield shares, ego position and their D2 host entries."""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from base import E7, E8, RES, write_json

ENTRY_COLS = ["d", "e", "n_entry_papers", "n_partners_distinct", "A_cont", "A0_cont", "CT", "RD", "Y_strict", "Y_all", "EST_bin", "kw5"]


def sub_shares(sy: dict, year: int, top: int = 6) -> dict:
    yrs = sy["years"]
    if year not in yrs:
        return {}
    i = yrs.index(year)
    lo = max(0, i - 2)
    cnt = {r["name"]: sum(r["counts"][lo:i + 1]) for r in sy["rows"]}
    tot = sum(cnt.values())
    if tot == 0:
        return dict(n_papers_3y=0)
    s = sorted(cnt.items(), key=lambda kv: -kv[1])
    out = {k: v / tot for k, v in s[:top] if v > 0}
    out["_other"] = sum(v for k, v in s[top:]) / tot
    out["n_papers_3y"] = tot
    return out


def run() -> dict:
    from roles import ga_class
    sel = json.loads((E8 / "results/cases_selection.json").read_text())
    ind = pd.read_parquet(E8 / "results/indicators/concept_year_indicators_hyd.parquet")
    ev = pd.read_parquet(E7 / "results/screen_events_with_outcomes.parquet")
    gl = pd.read_parquet(E7 / "results/graft_labels_screen.parquet")[["concept_id", "d", "e", "anchored"]]
    ev = ev.merge(gl, on=["concept_id", "d", "e"], how="left")
    from base import LOOP
    tx = json.loads((LOOP / "iter_2/gen_art/gen_art_dataset_5/hyd/taxonomy.json").read_text())
    sub_names = {int(k): v for k, v in tx["subfields"].items()}
    samp = pd.read_parquet(RES / "rooting_screen_sample.parquet", columns=["concept_id", "d", "e"])
    samp_keys = set(zip(samp.concept_id, samp.d.astype(int), samp.e.astype(int)))
    out, rows = {}, []
    for c in sel["cases"]:
        cid = c["concept_id"]
        cj = json.loads((E8 / "cases" / f"{cid}.json").read_text())
        tps = [int(t) for t in cj["time_points"]]
        g = ind[ind.concept_id == cid].set_index("year")
        pos = {}
        for t in tps:
            if t in g.index:
                r = g.loc[t]
                P = r.P_rar if np.isfinite(r.P_rar) else r.P_raw
                pos[str(t)] = dict(strength_pct_alt=float(r.pct_alt), P=float(P) if np.isfinite(P) else None, wmz=float(r.wmz) if np.isfinite(r.wmz) else None,
                                   GA_class=ga_class(float(r.wmz), float(P)), betweenness_pct=float(r.btw_pct) if np.isfinite(r.btw_pct) else None,
                                   H_rar=float(r.H_rar) if np.isfinite(r.H_rar) else None, active_subfields_3y=int(r.active_subfields_3y))
        e = ev[(ev.concept_id == cid) & (ev.arm == "main")].sort_values(["e", "d"]).copy()
        e["host_subfield"] = e.d.map(lambda x: sub_names.get(int(x), str(int(x))))
        e["in_coprimary_sample"] = [(cid, int(d), int(y)) in samp_keys for d, y in zip(e.d, e.e)]  # exact D2 co-primary sample rows
        e["graft_label"] = np.where(e.anchored.isna(), "unlabelled", np.where(e.anchored.fillna(False).astype(bool), "anchored", "not_anchored"))
        tab = e[["host_subfield"] + ENTRY_COLS + ["in_coprimary_sample", "graft_label"]]
        cp = e[e.in_coprimary_sample]
        rooted, unrooted = cp[cp.EST_bin == 1], cp[cp.EST_bin == 0]
        cmp = dict(n_rooted=len(rooted), n_unrooted=len(unrooted),
                   A_cont_rooted_mean=float(rooted.A_cont.mean()) if len(rooted) else None,
                   A_cont_unrooted_mean=float(unrooted.A_cont.mean()) if len(unrooted) else None)
        cmp["diff"] = (cmp["A_cont_rooted_mean"] - cmp["A_cont_unrooted_mean"]) if (len(rooted) and len(unrooted)) else None
        cmp["rooted_higher"] = (cmp["diff"] > 0) if cmp["diff"] is not None else None
        rec = dict(concept_id=cid, phrase=cj["phrase"], rule=c["rule"], cluster=cj["cluster"], origin=cj["origin_group"], F=int(cj["F"]),
                   origin_subfield=cj["origin_subfield"], E_up_group=cj["E_up_group"], leadlag=cj["leadlag"], time_points=tps,
                   role_path=[dict(year=p["year"], role=p["role"], robust=p["robust"]) for p in cj["alluvial_path"]],
                   subfield_shares={str(t): sub_shares(cj["subfield_year"], t) for t in tps}, ego_position=pos,
                   n_host_entries=len(e), n_coprimary=len(cp), EST_rate=float(cp.EST_bin.mean()) if len(cp) else None,
                   mean_A_cont=float(cp.A_cont.mean()) if len(cp) else None, mean_CT=float(cp.CT.mean()) if len(cp) else None,
                   rooted_vs_unrooted=cmp, entries=tab.to_dict("records"),
                   partner_lists=("DROPPED: exp_7 partner lists need its prepared corpus cache (results/cache/prepared.pkl), which was removed "
                                  "under that artifact's manifest; rebuilding it would write inside a read-only dependency. Stored entry values "
                                  "(A_cont independently re-derived in exp_7 audit_rederive.py) are reported instead."))
        out[cid] = rec
        for r in tab.to_dict("records"):
            rows.append(dict(concept_id=cid, phrase=cj["phrase"], cluster=cj["cluster"], **r))
    pd.DataFrame(rows).to_csv(RES / "case_entries.csv", index=False)
    write_json(RES / "cases_rooting.json", out)
    return out
