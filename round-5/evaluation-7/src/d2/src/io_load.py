"""STAGE 1: load dataset_5 (hydrated 426-concept corpus) into a compact, cached structure. No network calls.

prepare() returns a dict with
  W        per-work numpy arrays (row-indexed): work_id, year (publication_year), sub_raw (subfield_id or -1),
           sub (subfield if topic_score >= 0.05 else -1), topic_score, has_abstract, n_kw (distinct keyword_idx)
  P        partner CSR (indptr, idx): legacy-concept node ids (int, no 'C'), score >= 0.2, level >= 1; the union of
           concept tags and keyword tags mapped to a legacy concept by exact display name (dataset_5 node rule)
  AU       author CSR (indptr, idx): dense author index
  T3       CSR of the subfields of topics_top3
  concepts DataFrame of the 426 pool concepts (arm, fold, route, F, origin, own linked node, ...)
  links    {concept_id: (rows int64, years int32)} after the iteration-1 dup_group dedup, sorted by (year, work_id)
  prof     {(node, block): (total_known, {sub: count}, truncated)}; totals {(sub, year): n}; sub_field {sub: field}
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

from config import CACHE, D5, E1

PREP = CACHE / "prepared.pkl"
BLOCKS = ["2000-2004", "2005-2009", "2010-2014", "2015-2019"]


def _csr(lists: list) -> tuple[np.ndarray, np.ndarray]:
    lens = np.fromiter((len(x) for x in lists), np.int64, len(lists))
    indptr = np.zeros(len(lists) + 1, np.int64)
    np.cumsum(lens, out=indptr[1:])
    idx = np.concatenate([np.asarray(x, np.int64) for x in lists]) if indptr[-1] else np.zeros(0, np.int64)
    return indptr, idx


def load_concepts() -> pd.DataFrame:
    d = orjson.loads((D5 / "hyd" / "data_out.json").read_bytes())
    cov = orjson.loads((D5 / "outputs" / "nativeness_coverage.json").read_bytes())
    covd = {r["concept_id"]: r for r in cov["concepts"]}
    rows = []
    for ds in d["datasets"]:
        if ds["dataset"] != "concept_pool_2005_2016":
            continue
        for e in ds["examples"]:
            inp = orjson.loads(e["input"])
            main = e["metadata_arm"] == "main"
            own = (inp.get("links") or {}).get("legacy_concept_id")
            cv = covd.get(e["metadata_concept_id"], {})
            rows.append({
                "concept_id": e["metadata_concept_id"], "phrase": e["metadata_phrase"], "arm": e["metadata_arm"],
                "fold_d5": e["metadata_fold"], "route": e["metadata_retrieval_route"],
                "hydration_batch": e["metadata_hydration_batch"],
                "sense_share_d5": e.get("metadata_sense_dominant_share"),
                "F": inp.get("F") if main else None, "F_band": e.get("metadata_F_band"),
                "origin_d1": (inp.get("origin_subfield") or {}).get("id") if main else None,
                "origin": cv.get("origin_subfield"), "covered_weight_share": cv.get("covered_weight_share"),
                "own_node": int(own[1:]) if own else None,
            })
    df = pd.DataFrame(rows)
    logger.info(f"concepts: {len(df)} ({(df.arm == 'main').sum()} main, {(df.arm == 'reference').sum()} reference); "
                f"own linked legacy concept: {df.own_node.notna().sum()}")
    return df


def load_taxonomy() -> dict:
    tx = orjson.loads((D5 / "hyd" / "taxonomy.json").read_bytes())
    return {"sub_field": {int(k): int(v) for k, v in tx["subfield_field"].items()},
            "topic_sub": {int(k[1:]): int(v["subfield"]) for k, v in tx["topics"].items()},
            "sub_name": {int(k): v for k, v in tx["subfields"].items()},
            "field_name": {int(k): v for k, v in tx["fields"].items()}}


def load_totals() -> dict[tuple[int, int], int]:
    s = orjson.loads((D5 / "hyd" / "context" / "subfield_year_totals.json").read_bytes())
    return {(int(sf), int(y)): int(n) for y, v in s["variants"]["all_types"].items() for sf, n in v["subfield"].items()}


def load_profiles() -> dict:
    prof = {}
    for line in (D5 / "p2" / "profiles.jsonl").read_bytes().splitlines():
        if not line.strip():
            continue
        r = orjson.loads(line)
        sc = r["subfield_counts"]
        unk = int(sc.get("unknown", 0))
        counts = {int(k): int(v) for k, v in sc.items() if k != "unknown"}
        trunc = bool(r.get("truncated_top200", False))
        prof[(int(r["node_id"][1:]), r["block"])] = (int(r["total"]) - unk, counts, trunc)
    nodes = {k[0] for k in prof}
    logger.info(f"profiles: {len(prof)} (node, block) over {len(nodes)} nodes")
    return prof


def keyword_map() -> tuple[np.ndarray, dict[int, int]]:
    """keyword_idx -> legacy concept node (int, -1 if no exact display-name match); node -> level."""
    i2k = orjson.loads((D5 / "hyd" / "keywords_dict.json").read_bytes())["index_to_keyword_id"]
    con = pd.read_parquet(D5 / "deps" / "gen_art_dataset_2" / "concepts.parquet",
                          columns=["concept_id", "display_name", "level"])
    kw = pd.read_parquet(D5 / "deps" / "gen_art_dataset_2" / "keywords.parquet", columns=["keyword_slug", "display_name"])
    name2c = {}
    for cid, n in zip(con.concept_id, con.display_name):
        name2c.setdefault(n, int(cid[1:]))
    slug2c = {s: name2c[n] for s, n in zip(kw.keyword_slug, kw.display_name) if n in name2c}
    kmap = np.array([slug2c.get(s, -1) for s in i2k], np.int64)
    level = {int(c[1:]): int(lv) for c, lv in zip(con.concept_id, con.level)}
    logger.info(f"keyword map: {int((kmap >= 0).sum())}/{len(kmap)} keywords map to a legacy concept")
    return kmap, level


def dedup_links(cw: pd.DataFrame, n_refs: pd.Series) -> pd.DataFrame:
    """Iteration-1 rule: within (concept, dup_group) keep earliest year, then max n_refs, then min work_id."""
    lk = cw.copy()
    lk["n_refs"] = n_refs.reindex(lk.work_id).fillna(0).to_numpy()
    g = lk.dup_group
    lk["_grp"] = np.where(g.isna(), "w" + lk.work_id.astype(str), "g" + g.fillna(-1).astype(int).astype(str))
    lk = lk.sort_values(["concept_id", "_grp", "year", "n_refs", "work_id"], ascending=[True, True, True, False, True])
    kept = lk.drop_duplicates(["concept_id", "_grp"], keep="first").drop(columns=["_grp"])
    logger.info(f"dedup: {len(cw)} links -> {len(kept)} kept")
    return kept


def prepare(force: bool = False) -> dict:
    if PREP.exists() and not force:
        return pickle.loads(PREP.read_bytes())
    concepts = load_concepts()
    tax = load_taxonomy()
    kmap, level = keyword_map()
    cols = ["work_id", "publication_year", "subfield_id", "topic_score", "topics_top3", "author_ids", "keyword_idx",
            "concept_ids", "concept_scores", "has_abstract", "n_refs"]
    parts = sorted((D5 / "hyd" / "works").glob("works_part_*.parquet"))
    logger.info(f"works parquet parts: {[p.name for p in parts]}; schema: {pq.ParquetFile(parts[0]).schema_arrow.names}")
    w = pd.concat([pq.read_table(p, columns=cols).to_pandas() for p in parts], ignore_index=True)
    logger.info(f"works: {len(w)} rows")
    n = len(w)
    sub_raw = w.subfield_id.fillna(-1).to_numpy(np.int32)
    ts = w.topic_score.fillna(0).to_numpy(np.float32)
    sub = np.where((sub_raw >= 0) & (ts >= 0.05), sub_raw, -1).astype(np.int32)
    n_kw = np.fromiter((len(set(x)) if x is not None else 0 for x in w.keyword_idx), np.int32, n)
    # partners: dataset_5 node rule (concept tags score >= 0.2 U keyword tags mapped by display name), level >= 1
    plist, n_lvl0, n_nolvl = [], 0, 0
    for ci, cs, ki in zip(w.concept_ids, w.concept_scores, w.keyword_idx):
        s = set()
        if ci is not None:
            s.update(int(c) for c, sc in zip(ci, cs) if sc >= 0.2)
        if ki is not None and len(ki):
            m = kmap[np.asarray(ki, np.int64)]
            s.update(int(x) for x in m[m >= 0])
        keep = []
        for x in s:
            lv = level.get(x)
            if lv == 0:
                n_lvl0 += 1
                continue
            if lv is None:
                n_nolvl += 1
            keep.append(x)
        plist.append(sorted(keep))
    P = _csr(plist)
    del plist
    logger.info(f"partner tags: {len(P[1])} (level-0 dropped {n_lvl0}; unknown level kept {n_nolvl})")
    # authors -> dense index
    alist = [x if x is not None else [] for x in w.author_ids]
    au_ptr, au_raw = _csr(alist)
    uniq, au_idx = np.unique(au_raw, return_inverse=True)
    AU = (au_ptr, au_idx.astype(np.int64))
    del alist, au_raw
    tsub = tax["topic_sub"]
    T3 = _csr([[tsub.get(int(t), -1) for t in x] if x is not None else [] for x in w.topics_top3])
    W = {"work_id": w.work_id.to_numpy(np.int64), "year": w.publication_year.to_numpy(np.int32), "sub_raw": sub_raw,
         "sub": sub, "topic_score": ts, "has_abstract": w.has_abstract.fillna(False).to_numpy(bool), "n_kw": n_kw}
    n_refs = pd.Series(w.n_refs.fillna(0).to_numpy(), index=w.work_id.to_numpy())
    kw_sets = w.keyword_idx  # needed only for the reproduction check (distinct keyword_idx over entry-year papers)
    kw_ptr, kw_idx = _csr([x if x is not None else [] for x in kw_sets])
    del w, kw_sets
    gc.collect()
    cw = pd.read_parquet(D5 / "hyd" / "concept_work.parquet")
    kept = dedup_links(cw, n_refs)
    row_of = pd.Series(np.arange(n), index=W["work_id"])
    kept = kept[kept.work_id.isin(row_of.index)]
    kept["row"] = row_of.reindex(kept.work_id).to_numpy()
    links = {}
    for cid, g in kept.sort_values(["concept_id", "year", "work_id"]).groupby("concept_id"):
        links[cid] = (g.row.to_numpy(np.int64), g.year.to_numpy(np.int32))
    out = {"W": W, "P": P, "AU": AU, "n_authors": int(len(uniq)), "T3": T3, "KW": (kw_ptr, kw_idx),
           "concepts": concepts, "links": links, "prof": load_profiles(), "totals": load_totals(),
           "tax": tax, "level": level,
           "link_year_eq_pub_year_share": float((kept.year.to_numpy() == W["year"][kept.row.to_numpy()]).mean())}
    PREP.write_bytes(pickle.dumps(out, protocol=5))
    logger.info(f"prepared cache: {PREP.stat().st_size / 1e6:.1f} MB; concepts with links {len(links)}; "
                f"authors {len(uniq)}; link-year == pub-year share {out['link_year_eq_pub_year_share']:.4f}")
    return out


def load_population() -> dict:
    return orjson.loads((E1 / "results" / "test_population.json").read_bytes())


def origin_counter_check(G: dict) -> dict:
    """Cross-check dataset_5 origin (nativeness_coverage) against the modal subfield of F..F+2 c-papers."""
    con = G["concepts"].set_index("concept_id")
    W = G["W"]
    agree, n, mism = 0, 0, []
    for cid, c in con[con.arm == "main"].iterrows():
        rows, yrs = G["links"][cid]
        sel = rows[(yrs >= c.F) & (yrs <= c.F + 2)]
        cnt = Counter(int(s) for s in W["sub_raw"][sel] if s >= 0)
        mod = cnt.most_common(1)[0][0] if cnt else None
        n += 1
        if mod == c.origin:
            agree += 1
        else:
            mism.append({"concept_id": cid, "coverage_origin": c.origin, "modal_dedup": mod, "d1_origin": c.origin_d1})
    return {"n": n, "agree": agree, "share": agree / max(n, 1), "mismatches": mism[:30],
            "coverage_vs_d1_agree": int((con[con.arm == "main"].origin == con[con.arm == "main"].origin_d1).sum())}
