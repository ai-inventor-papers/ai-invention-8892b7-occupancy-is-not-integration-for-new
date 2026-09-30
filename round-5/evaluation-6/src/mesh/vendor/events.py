"""STAGES 3a + 4: host-entry events.

3a reproduces iteration-2 gen_art_experiment_2 graft_fallback() (iteration-1 main concepts, keyword_idx proxy) row by row.
4  builds every entry of a pool concept into a non-origin subfield on the hydrated 426-concept pool:
   main arm      e(c, d) = first year with a d-paper (known sub: topic_score >= 0.05), kept iff F <= e <= 2019
   reference arm kept iff 2005 <= e <= 2019 (no d-paper in 2000-2004); used ONLY for benchmarks
"""
from __future__ import annotations

import json

import numpy as np
import orjson
import pandas as pd
from loguru import logger

from config import D1, E2, RESULTS


def partners_of(G: dict, rows: np.ndarray, drop: int | None) -> list[np.ndarray]:
    ptr, idx = G["P"]
    out = []
    for r in rows:
        a = idx[ptr[r]:ptr[r + 1]]
        out.append(a[a != drop] if drop is not None else a)
    return out


def reproduce_iter1(G: dict) -> dict:
    """Row-level reproduction of graft_fallback_events.csv (2,347 / 2,154 / 2,000)."""
    ds1 = orjson.loads((D1 / "data_out.json").read_bytes())
    con = []
    for ds in ds1["datasets"]:
        if ds["dataset"] != "concept_pool_2005_2016":
            continue
        for e in ds["examples"]:
            if e["metadata_arm"] != "main":
                continue
            inp = orjson.loads(e["input"])
            con.append((e["metadata_concept_id"], e["metadata_fold"], int(inp["F"]),
                        (inp.get("origin_subfield") or {}).get("id")))
    W = G["W"]
    kptr, kidx = G["KW"]
    rows = []
    for cid, fold, F, o in con:
        r, y = G["links"][cid]
        sub = W["sub_raw"][r]
        o = int(o) if o is not None else -999
        m = (sub >= 0) & (sub != o)
        for d in np.unique(sub[m]):
            sel = m & (sub == d)
            e = int(y[sel].min())
            if e > 2019:
                continue
            er = r[sel & (y == e)]
            nk = len(set(np.concatenate([kidx[kptr[i]:kptr[i + 1]] for i in er]).tolist()))
            rows.append({"concept_id": cid, "d": int(d), "e": e, "fold": fold, "n_kw": nk, "anchored_proxy": nk >= 5,
                         "e_ge_F": e >= F})
    df = pd.DataFrame(rows)
    tgt = pd.read_csv(E2 / "results" / "gate_a" / "graft_fallback_events.csv")
    key = ["concept_id", "d", "e", "n_kw"]
    a = df[key].sort_values(key).reset_index(drop=True)
    b = tgt[key].sort_values(key).reset_index(drop=True)
    row_equal = len(a) == len(b) and bool((a.to_numpy() == b.to_numpy()).all())
    mg = a.merge(b, on=key, how="outer", indicator=True)
    res = {"n_concepts_iter1_main": len(con), "n_events_all": int(len(df)), "n_events_kw5": int(df.anchored_proxy.sum()),
           "n_events_kw5_e_ge_F": int((df.anchored_proxy & df.e_ge_F).sum()),
           "kw5_by_fold": {f: int(g.anchored_proxy.sum()) for f, g in df.groupby("fold")},
           "expected": {"n_events_all": 2347, "n_events_kw5": 2154, "n_events_kw5_e_ge_F": 2000,
                        "kw5_by_fold": {"screen": 1285, "heldout_concept": 869}},
           "row_level_equal": row_equal, "rows_only_here": int((mg._merge == "left_only").sum()),
           "rows_only_target": int((mg._merge == "right_only").sum())}
    res["pass"] = bool(row_equal and res["n_events_all"] == 2347 and res["n_events_kw5"] == 2154
                       and res["n_events_kw5_e_ge_F"] == 2000)
    (RESULTS / "repro_events_iter1.json").write_text(json.dumps(res, indent=1))
    logger.info(f"3a reproduction: {res}")
    return res


def build_events(G: dict, pop: dict) -> pd.DataFrame:
    W = G["W"]
    con = G["concepts"].set_index("concept_id")
    per = pd.DataFrame(pop["per_concept"]).set_index("concept_id")
    rows, n_pre_F = [], 0
    for cid, c in con.iterrows():
        r, y = G["links"][cid]
        sub = W["sub"][r]
        o = int(c.origin) if pd.notna(c.origin) else -999
        m = (sub >= 0) & (sub != o)
        main = c.arm == "main"
        for d in np.unique(sub[m]):
            sel = m & (sub == d)
            e = int(y[sel].min())
            if main:
                if e < int(c.F):
                    n_pre_F += 1
                    continue
                if e > 2019:
                    continue
            elif not (2005 <= e <= 2019):
                continue
            er = r[sel & (y == e)]
            own = int(c.own_node) if pd.notna(c.own_node) else None
            parts = partners_of(G, er, own)
            tags = int(sum(len(p) for p in parts))
            distinct = len(set(np.concatenate(parts).tolist())) if tags else 0
            rows.append({"concept_id": cid, "arm": c.arm, "fold": per.at[cid, "fold"], "d": int(d), "e": e,
                         "o": o, "F": int(c.F) if main else None, "n_entry_papers": int(len(er)),
                         "n_partners_distinct": distinct, "n_partner_tags": tags, "kw5": distinct >= 5,
                         "n_kw": int(len(set(np.concatenate([G["KW"][1][G["KW"][0][i]:G["KW"][0][i + 1]]
                                                               for i in er]).tolist()))),
                         "route": c.route, "route_A": str(c.route).startswith("A"),
                         "MAIN": bool(per.at[cid, "MAIN"]), "STRICT": bool(per.at[cid, "STRICT"]),
                         "REFERENCE_ACCEPTED": bool(per.at[cid, "REFERENCE_ACCEPTED"]),
                         "SENSITIVITY": bool(per.at[cid, "SENSITIVITY"])})
    ev = pd.DataFrame(rows)
    ev.to_parquet(RESULTS / "events_all.parquet", index=False)
    tab = (ev.assign(pop=np.where(ev.MAIN, "MAIN", np.where(ev.arm == "reference", "REF", "nonMAIN")))
           .groupby(["arm", "fold", "pop", "kw5"]).size().reset_index(name="n"))
    tab.to_csv(RESULTS / "events_counts.csv", index=False)
    mainm = ev[(ev.arm == "main") & ev.MAIN & ev.kw5]
    summ = {"n_events_all": int(len(ev)), "main_arm": int((ev.arm == "main").sum()),
            "main_arm_kw5": int(((ev.arm == "main") & ev.kw5).sum()), "reference_arm": int((ev.arm == "reference").sum()),
            "excluded_pre_F_entries": n_pre_F,
            "MAIN_kw5_by_fold": {f: {"events": int(len(g)), "concepts": int(g.concept_id.nunique())}
                                 for f, g in mainm.groupby("fold")},
            "SENSITIVITY_kw5_by_fold": {f: int(len(g)) for f, g in ev[(ev.arm == "main") & ev.kw5].groupby("fold")},
            "screen_share_main_arm_kw5": float((ev[(ev.arm == "main") & ev.kw5].fold == "screen").mean())}
    (RESULTS / "events_summary.json").write_text(json.dumps(summ, indent=1))
    logger.info(f"events: {summ}")
    return ev
