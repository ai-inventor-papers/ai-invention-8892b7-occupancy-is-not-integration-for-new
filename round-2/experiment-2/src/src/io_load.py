"""Loaders for the iteration-1 dataset artifact (DS1). No network calls.

prepare() builds, once, a per-concept structure:
  papers  : DataFrame (dedup'ed c-papers) work_id, year, sub, field, n_refs, cbc, n_kw, lenient_excl_F
  cites   : int32 array (n, 2) of (child_idx, parent_idx) for every in-cset citation child -> parent, parent != child
            (no year / canonical filter; lineage.py applies those)
and a no-dedup link-level table used for the lenient loader check (assemble.py lines 353-403).
"""
from __future__ import annotations

import gc
import pickle
from collections import Counter

import numpy as np
import orjson
import pandas as pd
import pyarrow.parquet as pq
from loguru import logger

from common import DS1, RESULTS, f_band

CACHE = RESULTS / "cache" / "prepared.pkl"


def load_concepts() -> pd.DataFrame:
    d = orjson.loads((DS1 / "data_out.json").read_bytes())
    rows = []
    for ds in d["datasets"]:
        if ds["dataset"] != "concept_pool_2005_2016":
            continue
        for e in ds["examples"]:
            inp = orjson.loads(e["input"])
            out = orjson.loads(e["output"])
            main = e["metadata_arm"] == "main"
            rows.append({
                "concept_id": e["metadata_concept_id"], "phrase": e["metadata_phrase"], "arm": e["metadata_arm"],
                "fold": e["metadata_fold"], "route": e["metadata_retrieval_route"],
                "flags": list(e.get("metadata_flags") or []),
                "sense_share": e.get("metadata_sense_dominant_share"),
                "sense_check_fail": "sense_check_fail" in (e.get("metadata_flags") or []),
                "F": inp.get("F") if main else None, "V": inp.get("early_volume_V") if main else None,
                "F_band": e.get("metadata_F_band"), "volume_tercile": e.get("metadata_volume_tercile"),
                "origin_sub": (inp.get("origin_subfield") or {}).get("id") if main else None,
                "origin_field": (inp.get("origin_field") or {}).get("id") if main else None,
                "stratum": e.get("metadata_stratum"),
                "focal_screen": e.get("metadata_focal_years_screen") or [],
                "focal_heldout": e.get("metadata_focal_years_heldout") or [],
                "match_mix": e.get("metadata_match_evidence_mix"), "n_works_d1": out.get("n_works"),
            })
    df = pd.DataFrame(rows)
    logger.info(f"D1 concepts: {len(df)} ({(df.arm == 'main').sum()} main, {(df.arm == 'reference').sum()} reference)")
    return df


def load_taxonomy() -> dict:
    tx = orjson.loads((DS1 / "taxonomy.json").read_bytes())
    sub_field = {int(k): int(v) for k, v in tx["subfield_field"].items()}
    field_domain = {int(k): int(v) for k, v in tx["field_domain"].items()}
    return {"sub_field": sub_field, "field_domain": field_domain, "subfields": tx["subfields"], "fields": tx["fields"]}


def load_totals(variant: str = "all_types") -> dict[tuple[int, int], int]:
    s = orjson.loads((DS1 / "context" / "subfield_year_totals.json").read_bytes())
    out = {}
    for y, v in s["variants"][variant].items():
        for sf, n in v["subfield"].items():
            out[(int(sf), int(y))] = int(n)
    return out


def load_works(cols: list[str]) -> pd.DataFrame:
    parts = sorted((DS1 / "works").glob("works_part_*.parquet"))
    dfs = [pq.read_table(p, columns=cols).to_pandas() for p in parts]
    w = pd.concat(dfs, ignore_index=True)
    logger.info(f"works: {len(w)} rows, cols={cols}")
    return w


def load_links() -> pd.DataFrame:
    cw = pd.read_parquet(DS1 / "concept_work.parquet")
    logger.info(f"concept_work links: {len(cw)}")
    return cw


def within_concept_cites(links: pd.DataFrame, works: pd.DataFrame) -> pd.DataFrame:
    """(concept_id, child, parent) for every citation where child and parent are both linked to the concept."""
    ref = works[["work_id", "refs_in_corpus"]].explode("refs_in_corpus").dropna()
    ref = ref.rename(columns={"work_id": "child", "refs_in_corpus": "parent"})
    ref["parent"] = ref["parent"].astype(np.int64)
    ref["child"] = ref["child"].astype(np.int64)
    lk = links[["concept_id", "work_id"]]
    m = lk.rename(columns={"work_id": "child"}).merge(ref, on="child", how="inner")
    m = m.merge(lk.rename(columns={"work_id": "parent"}), on=["concept_id", "parent"], how="inner")
    m = m[m.child != m.parent].drop_duplicates()
    logger.info(f"within-concept citations (no dedup): {len(m)}")
    return m


def lenient_flags(concepts: pd.DataFrame, links: pd.DataFrame, cites: pd.DataFrame, works: pd.DataFrame) -> pd.DataFrame:
    """Exact re-implementation of assemble.py lines 360-377 at link level (no dedup)."""
    lk = links[["concept_id", "work_id", "year", "match_evidence", "dup_group"]].copy()
    F = concepts.set_index("concept_id")["F"]
    osub = concepts.set_index("concept_id")["origin_sub"]
    arm = concepts.set_index("concept_id")["arm"]
    y = lk.set_index(["concept_id", "work_id"])["year"]
    c = cites.copy()
    c["cy"] = y.reindex(pd.MultiIndex.from_arrays([c.concept_id, c.child])).to_numpy()
    c["py"] = y.reindex(pd.MultiIndex.from_arrays([c.concept_id, c.parent])).to_numpy()
    c = c[c.py < c.cy]
    c["F"] = c.concept_id.map(F)
    any_par = set(zip(c.concept_id, c.child))
    exf = c[c.F.isna() | (c.py != c.F)]
    exf_par = set(zip(exf.concept_id, exf.child))
    key = list(zip(lk.concept_id, lk.work_id))
    lk["traced_any"] = [k in any_par for k in key]
    lk["traced_excl_F"] = [k in exf_par for k in key]
    ws = works.set_index("work_id")
    lk["sub"] = ws["subfield_id"].reindex(lk.work_id).to_numpy()
    lk["n_refs"] = ws["n_refs"].reindex(lk.work_id).to_numpy()
    lk["arm"] = lk.concept_id.map(arm)
    o = lk.concept_id.map(osub)
    lk["outside_origin"] = o.notna() & lk["sub"].notna() & (lk["sub"] != o)
    return lk


def dedup(links: pd.DataFrame) -> pd.DataFrame:
    """Within (concept, dup_group) keep earliest year, then max n_refs, then min work_id."""
    lk = links.copy()
    g = lk.dup_group
    lk["_grp"] = np.where(g.isna(), "w" + lk.work_id.astype(str), "g" + g.fillna(-1).astype(int).astype(str))
    lk = lk.sort_values(["concept_id", "_grp", "year", "n_refs", "work_id"], ascending=[True, True, True, False, True])
    kept = lk.drop_duplicates(["concept_id", "_grp"], keep="first").drop(columns="_grp")
    logger.info(f"dedup: {len(links)} links -> {len(kept)} kept")
    return kept


def prepare(force: bool = False) -> dict:
    if CACHE.exists() and not force:
        return pickle.loads(CACHE.read_bytes())
    concepts = load_concepts()
    tax = load_taxonomy()
    links = load_links()
    works = load_works(["work_id", "publication_year", "subfield_id", "field_id", "n_refs", "refs_in_corpus",
                        "cited_by_count", "keyword_idx", "type"])
    works = works[works.work_id.isin(set(links.work_id))].reset_index(drop=True)
    works["n_kw"] = works.keyword_idx.map(len)
    kw_of = dict(zip(works.work_id, works.keyword_idx))
    cites = within_concept_cites(links, works)
    lk = lenient_flags(concepts, links, cites, works)
    wsub = works.set_index("work_id")
    lk["field"] = wsub["field_id"].reindex(lk.work_id).to_numpy()
    lk["cbc"] = wsub["cited_by_count"].reindex(lk.work_id).to_numpy()
    lk["n_kw"] = wsub["n_kw"].reindex(lk.work_id).to_numpy()
    lk["pub_year"] = wsub["publication_year"].reindex(lk.work_id).to_numpy()
    kept = dedup(lk)
    per = {}
    cites_g = {k: v for k, v in cites.groupby("concept_id")}
    for cid, p in kept.groupby("concept_id"):
        p = p.sort_values(["year", "work_id"]).reset_index(drop=True)
        papers = pd.DataFrame({
            "work_id": p.work_id.to_numpy(np.int64), "year": p.year.to_numpy(np.int32),
            "sub": p["sub"].fillna(-1).to_numpy(np.int32), "field": p["field"].fillna(-1).to_numpy(np.int32),
            "n_refs": p.n_refs.fillna(0).to_numpy(np.int32), "cbc": p.cbc.fillna(0).to_numpy(np.int64),
            "n_kw": p.n_kw.fillna(0).to_numpy(np.int32), "lenient_excl_F": p.traced_excl_F.to_numpy(bool)})
        idx = {w: i for i, w in enumerate(papers.work_id)}
        cc = cites_g.get(cid)
        if cc is not None and len(cc):
            ch = cc.child.map(idx)
            pa = cc.parent.map(idx)
            ok = ch.notna() & pa.notna()
            arr = np.stack([ch[ok].to_numpy(np.int32), pa[ok].to_numpy(np.int32)], axis=1) if ok.any() else np.zeros((0, 2), np.int32)
        else:
            arr = np.zeros((0, 2), np.int32)
        per[cid] = {"papers": papers, "cites": arr}
    del cites_g
    gc.collect()
    # keyword sets per concept-work for the graft-fallback proxy (only needed for entry-year d-papers; stored compactly)
    kw = {cid: [kw_of.get(w, np.zeros(0, np.int32)) for w in per[cid]["papers"].work_id] for cid in per}
    out = {"concepts": concepts, "tax": tax, "links_lenient": lk.drop(columns=["field", "cbc", "n_kw"]),
           "per": per, "kw": kw, "year_check": {
               "link_year_eq_pub_year_share": float((lk.year == lk.pub_year).mean())}}
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_bytes(pickle.dumps(out, protocol=5))
    logger.info(f"prepared cache written ({CACHE.stat().st_size / 1e6:.1f} MB); concepts with papers: {len(per)}")
    return out


def cite_counter(x) -> Counter:  # small helper used in audit
    return Counter(x)
