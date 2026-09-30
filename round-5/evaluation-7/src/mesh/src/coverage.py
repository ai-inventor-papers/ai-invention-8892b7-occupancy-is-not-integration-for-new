"""STAGE 4: PubMed host-coverage rule (declared before any MeSH event is counted) + truncation audit.

178/191 MeSH concepts have only PubMed-indexed works retrieved, so an entry into a subfield that PubMed barely
covers is unobservable. Rule: pm_share[d, block] = n(has_pmid, d, block) / n(all, d, block) from OpenAlex group_by
over the whole index; covered(d, e) = pm_share[d, block(e)] >= 0.50 (sensitivity 0.30 / 0.70). Blocks are the
ENTRY periods 2005-2009, 2010-2014, 2015-2019. group_by returns at most 200 groups and there are 252 subfields, so
each (block, frame) call is split by OpenAlex domain (4 domains x 2 frames x 3 blocks = 24 list calls, deviation
D-M4 of the planned 6). $0 fallback: covered = subfields in domains 1 (Life Sciences) and 4 (Health Sciences).
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
from loguru import logger

import common
from common import CACHE, RESULTS, CreditStop, OpenAlex, dump

ENTRY_BLOCKS = ["2005-2009", "2010-2014", "2015-2019"]
THRESH = 0.50
SENS = [0.30, 0.70]
RAW = CACHE / "coverage_groupby.json"


def entry_block(e: int) -> str:
    return "2005-2009" if e < 2010 else ("2010-2014" if e < 2015 else "2015-2019")


def parse_groups(d: dict) -> dict[int, int]:
    out = {}
    for g in d.get("group_by", []):
        k = str(g["key"]).rstrip("/").split("/")[-1]
        if k.isdigit():
            out[int(k)] = int(g["count"])
    return out


def fetch() -> dict:
    if RAW.exists():
        return json.loads(RAW.read_text())
    oa = OpenAlex("coverage")
    raw = {}
    for blk in ENTRY_BLOCKS:
        for frame, extra in (("pm", ",has_pmid:true"), ("all", "")):
            for dom in (1, 2, 3, 4):
                d = oa.get("/works", {"filter": f"publication_year:{blk},primary_topic.domain.id:{dom}{extra}",
                                      "group_by": "primary_topic.subfield.id", "per_page": 200},
                           tag=f"coverage {blk} {frame} domain {dom}")
                g = parse_groups(d)
                if len(d.get("group_by", [])) >= 200:
                    logger.warning(f"{blk} {frame} {dom}: 200 groups returned (possible truncation)")
                raw[f"{blk}|{frame}|{dom}"] = {str(k): v for k, v in g.items()}
    RAW.write_text(json.dumps(raw))
    logger.info(f"coverage calls {oa.calls}, credits {oa.credits}, remaining {oa.remaining}")
    return raw


def rule(tax: dict) -> tuple[dict, str]:
    """Returns ({(d, block): pm_share}, source)."""
    try:
        raw = fetch()
        pm = {}
        for blk in ENTRY_BLOCKS:
            npm, nall = {}, {}
            for dom in (1, 2, 3, 4):
                npm.update({int(k): v for k, v in raw[f"{blk}|pm|{dom}"].items()})
                nall.update({int(k): v for k, v in raw[f"{blk}|all|{dom}"].items()})
            for d in tax["sub_field"]:
                pm[(int(d), blk)] = npm.get(d, 0) / nall[d] if nall.get(d, 0) > 0 else 0.0
        return pm, "openalex_groupby"
    except (CreditStop, RuntimeError) as ex:
        logger.warning(f"coverage fetch failed ({ex!r}); $0 domain fallback (Life + Health Sciences)")
        pm = {}
        for d, f in tax["sub_field"].items():
            dom = tax["field_domain"][f]
            for blk in ENTRY_BLOCKS:
                pm[(int(d), blk)] = 1.0 if dom in (1, 4) else 0.0
        return pm, "domain_fallback"


def covered(pm: dict, d: int, e: int, thr: float = THRESH) -> bool:
    return pm.get((int(d), entry_block(int(e))), 0.0) >= thr


def truncation_audit(G: dict, pm: dict) -> dict:
    """13 retrieval_complete concepts: entry year from ALL verified works vs from PMID-only verified works."""
    con = G["concepts"]
    W = G["W"]
    rows = []
    for c in con[con.retrieval_complete].itertuples():
        r, y = G["links"][c.concept_id]
        sub = W["sub"][r]
        pmm = W["has_pmid"][r]
        m = (sub >= 0) & (sub != c.origin)
        for d in np.unique(sub[m]):
            sel = m & (sub == d)
            e_all = int(y[sel].min())
            if not (c.F <= e_all <= 2019):
                continue
            selp = sel & pmm
            e_pm = int(y[selp].min()) if selp.any() else None
            rows.append({"concept_id": c.concept_id, "d": int(d), "e_all": e_all, "e_pmid": e_pm,
                         "covered": covered(pm, d, e_all), "identical": e_pm == e_all,
                         "missing_in_pmid": e_pm is None})
    df = pd.DataFrame(rows)
    out = {"n_concepts": int(con.retrieval_complete.sum()), "n_entries": int(len(df))}
    for k, g in df.groupby("covered"):
        out["covered" if k else "uncovered"] = {"n": int(len(g)), "share_identical_e": float(g.identical.mean()),
                                                 "share_entry_missing_in_pmid_only": float(g.missing_in_pmid.mean())}
    out["all"] = {"share_identical_e": float(df.identical.mean()) if len(df) else None}
    df.to_csv(RESULTS / "truncation_audit_rows.csv", index=False)
    return out


def run(mini: bool = False) -> dict:
    import load_mesh
    G = load_mesh.prepare()
    pm, src = rule(G["tax"])
    tax = G["tax"]
    tab = []
    for (d, blk), v in sorted(pm.items()):
        f = tax["sub_field"].get(d, -1)
        tab.append({"d": d, "block": blk, "pm_share": v, "covered": v >= THRESH, "field": f,
                    "domain": tax["field_domain"].get(f, -1), "sub_name": tax["sub_name"].get(d)})
    t = pd.DataFrame(tab)
    t.to_csv(RESULTS / "host_coverage_table.csv", index=False)
    out = {"source": src, "threshold": THRESH, "sensitivity": SENS,
           "rule": "covered(d, e) = pm_share[d, entry block of e] >= 0.50; pm_share = has_pmid / all works with "
                   "primary subfield d in the block (OpenAlex group_by, whole index)",
           "n_covered_by_block": {b: int(g.covered.sum()) for b, g in t.groupby("block")},
           "n_covered_by_block_domain": {f"{b}|{dm}": int(g.covered.sum()) for (b, dm), g in t.groupby(["block", "domain"])},
           "n_covered_at_0.30": {b: int((g.pm_share >= 0.3).sum()) for b, g in t.groupby("block")},
           "n_covered_at_0.70": {b: int((g.pm_share >= 0.7).sum()) for b, g in t.groupby("block")},
           "pm_share": {f"{d}|{b}": v for (d, b), v in pm.items()}}
    dump(RESULTS / "host_coverage.json", out)
    ta = truncation_audit(G, pm)
    dump(RESULTS / "truncation_audit.json", ta)
    logger.info(f"coverage: {src}; covered per block {out['n_covered_by_block']}; truncation audit {ta}")
    return out


def load_rule() -> dict:
    d = json.loads((RESULTS / "host_coverage.json").read_text())
    return {(int(k.split("|")[0]), k.split("|")[1]): v for k, v in d["pm_share"].items()}
