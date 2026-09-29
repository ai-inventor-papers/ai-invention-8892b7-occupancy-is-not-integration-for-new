"""STAGE 3: load the 191 MeSH concepts and their works into the exp_7 G structure, plus the co-word substrate.

No outcomes are computed here. Rules (frozen into mesh_spec.json later):
  c-paper set    primary: rows with verified_text_match == True; union (incl. MeSH-indexed-only / unverified) kept for S12
  dedup          (concept, work_id); then (concept, normalised DOI): keep earliest year, then min work_id
  sub(w)         primary_topic.subfield_id (-1 if missing). Deviation D-M1: MeSH works carry no topic score, so
                 there is no known-sub topic_score >= 0.05 filter (harmonisation row h2 measures its effect on main)
  partners(w)    {legacy concept c: level >= 1, score >= 0.3} U {kwmap[k]: keyword slug -> legacy concept by exact
                 display name, level >= 1} (dataset_5 node rule at the MeSH 0.3 tagging floor; h1 on main)
  own nodes      legacy concepts whose display name equals (casefolded) the preferred term or any surface form or
                 acronym of the MeSH concept -> dropped from that concept's partners
  origin         the dataset's origin_subfield (frozen); agreement with the modal subfield of verified F..F+2 papers
                 is reported
  overlap        MeSH concepts whose casefolded surface forms collide with a main-pool phrase are dropped (reported)
"""
from __future__ import annotations

import gzip
import pickle
import re
from collections import Counter, defaultdict
from itertools import combinations

import numpy as np
import orjson
import pandas as pd
from loguru import logger

import common
from common import CACHE, D5, MESH, RESULTS, dump

PREP = CACHE / "mesh_prepared.pkl"


def _j(v):
    return orjson.loads(v) if isinstance(v, (str, bytes)) else v


def load_concepts() -> pd.DataFrame:
    d = orjson.loads((MESH / "data_out.json").read_bytes())
    rows = []
    for r in d:
        inp, out, md = _j(r["input"]), _j(r["output"]), _j(r["metadata"])
        rows.append({"concept_id": inp["concept_id"], "descriptor_ui": inp["descriptor_ui"],
                     "preferred_term": inp["preferred_term"], "surface_forms": list(inp.get("surface_forms") or []),
                     "acronyms": list(inp.get("acronyms") or []), "F": int(inp["F"]),
                     "origin": int(inp["origin_subfield"]) if inp.get("origin_subfield") is not None else -999,
                     "origin_field": int(inp["origin_field"]) if inp.get("origin_field") is not None else -999,
                     "tree_branch": inp.get("tree_branch_primary"), "mesh_year": inp.get("mesh_year_established"),
                     "retrieval_complete": bool(md["retrieval_complete"]), "rule_parity": bool(md["rule_parity"]),
                     "final_rule_basis": out.get("final_rule_basis"), "branch_group": md.get("branch_group"),
                     "volume_tercile": md.get("volume_tercile")})
    df = pd.DataFrame(rows)
    logger.info(f"MeSH concepts: {len(df)}; retrieval_complete {int(df.retrieval_complete.sum())}; "
                f"rule_parity {int(df.rule_parity.sum())}")
    return df


def legacy_maps() -> tuple[dict[str, int], dict[int, int], dict[str, list[int]]]:
    con = pd.read_parquet(D5 / "deps" / "gen_art_dataset_2" / "concepts.parquet",
                          columns=["concept_id", "display_name", "level"])
    kw = pd.read_parquet(D5 / "deps" / "gen_art_dataset_2" / "keywords.parquet", columns=["keyword_slug", "display_name"])
    name2c: dict[str, int] = {}
    for cid, n in zip(con.concept_id, con.display_name):
        name2c.setdefault(n, int(cid[1:]))
    slug2c = {s: name2c[n] for s, n in zip(kw.keyword_slug, kw.display_name) if n in name2c}
    level = {int(c[1:]): int(lv) for c, lv in zip(con.concept_id, con.level)}
    fold2c: dict[str, list[int]] = defaultdict(list)
    for cid, n in zip(con.concept_id, con.display_name):
        if isinstance(n, str):
            fold2c[n.casefold().strip()].append(int(cid[1:]))
    logger.info(f"legacy concepts {len(con)}; keyword slugs mapped {len(slug2c)}/{len(kw)}")
    return slug2c, level, dict(fold2c)


def norm_doi(d) -> str | None:
    if not d:
        return None
    d = str(d).lower().strip()
    d = re.sub(r"^https?://(dx\.)?doi\.org/", "", d)
    return d or None


def read_rows() -> list[dict]:
    rows = []
    for p in sorted((MESH / "works").glob("works_part_*.jsonl.gz")):
        with gzip.open(p, "rb") as f:
            for line in f:
                if line.strip():
                    rows.append(orjson.loads(line))
    logger.info(f"MeSH (concept, work) rows: {len(rows)}")
    return rows


def main_pool_phrases() -> set[str]:
    d = orjson.loads((D5 / "hyd" / "data_out.json").read_bytes())
    out = set()
    for ds in d["datasets"]:
        if ds["dataset"] != "concept_pool_2005_2016":
            continue
        for e in ds["examples"]:
            out.add(str(e["metadata_phrase"]).casefold().strip())
            inp = orjson.loads(e["input"])
            for s in inp.get("surface_forms") or []:
                out.add(str(s).casefold().strip())
    return out


def prepare(force: bool = False) -> dict:
    if PREP.exists() and not force:
        return pickle.loads(PREP.read_bytes())
    concepts = load_concepts()
    slug2c, level, fold2c = legacy_maps()
    rows = read_rows()
    # ---- unique works
    works: dict[int, dict] = {}
    for r in rows:
        wid = int(r["work_id"])
        if wid not in works:
            works[wid] = r
    wids = np.array(sorted(works), np.int64)
    n = len(wids)
    row_of = {w: i for i, w in enumerate(wids.tolist())}
    year = np.zeros(n, np.int32)
    sub_raw = np.full(n, -1, np.int32)
    has_abs = np.zeros(n, bool)
    has_pmid = np.zeros(n, bool)
    plist, alist, n_lvl0, n_kw_mapped, n_tags_raw = [], [], 0, 0, 0
    for i, w in enumerate(wids.tolist()):
        r = works[w]
        year[i] = int(r.get("publication_year") or 0)
        pt = r.get("primary_topic") or {}
        if pt.get("subfield_id") is not None:
            sub_raw[i] = int(pt["subfield_id"])
        has_abs[i] = bool(r.get("has_abstract"))
        has_pmid[i] = r.get("pmid") is not None
        s = set()
        for c in r.get("concepts") or []:
            if c.get("score", 0) >= 0.3:
                s.add(int(c["id"]))
                n_tags_raw += 1
        for k in r.get("keywords") or []:
            x = slug2c.get(k.get("id"))
            if x is not None:
                s.add(int(x))
                n_kw_mapped += 1
        keep = []
        for x in s:
            if level.get(x) == 0:
                n_lvl0 += 1
                continue
            keep.append(x)
        plist.append(sorted(keep))
        alist.append([int(a["author_id"]) for a in (r.get("authorships") or []) if a.get("author_id") is not None])
    from io_load import _csr  # vendored
    P = _csr(plist)
    au_ptr, au_raw = _csr(alist)
    uniq, au_idx = np.unique(au_raw, return_inverse=True)
    AU = (au_ptr, au_idx.astype(np.int64))
    logger.info(f"unique works {n}; partner tags {len(P[1])} (level-0 dropped {n_lvl0}; keyword-mapped {n_kw_mapped}); "
                f"authors {len(uniq)}; works without subfield {int((sub_raw < 0).sum())}")
    # ---- links (primary = verified) with dedup
    lk = pd.DataFrame({"concept_id": [r["concept_id"] for r in rows], "work_id": [int(r["work_id"]) for r in rows],
                       "verified": [bool(r.get("verified_text_match")) for r in rows],
                       "match_route": [r.get("match_route") for r in rows],
                       "doi": [norm_doi(r.get("doi")) for r in rows]})
    lk["year"] = year[np.array([row_of[w] for w in lk.work_id])]
    n_rows = len(lk)
    lk = lk.sort_values(["concept_id", "work_id", "verified"], ascending=[True, True, False])
    lk = lk.drop_duplicates(["concept_id", "work_id"], keep="first")
    n_after_wid = len(lk)
    lk = lk.sort_values(["concept_id", "year", "work_id"])
    has_doi = lk.doi.notna()
    dd = lk[has_doi].duplicated(["concept_id", "doi"], keep="first")
    drop_idx = lk[has_doi][dd].index
    lk = lk.drop(index=drop_idx)
    dedup = {"rows": n_rows, "after_concept_work_dedup": n_after_wid, "doi_duplicates_dropped": int(len(drop_idx)),
             "after_doi_dedup": int(len(lk)), "verified_links": int(lk.verified.sum())}
    lk["row"] = lk.work_id.map(row_of).astype(np.int64)
    lk = lk[lk.year > 0]
    links, links_union = {}, {}
    for cid, g in lk.groupby("concept_id"):
        gv = g[g.verified]
        links[cid] = (gv.row.to_numpy(np.int64), gv.year.to_numpy(np.int32))
        links_union[cid] = (g.row.to_numpy(np.int64), g.year.to_numpy(np.int32))
    # ---- own nodes, overlap, origin check
    main_phr = main_pool_phrases()
    own, overlap = {}, []
    for c in concepts.itertuples():
        forms = {c.preferred_term, *c.surface_forms, *c.acronyms}
        forms = {str(f).casefold().strip() for f in forms if f}
        ids = sorted({x for f in forms for x in fold2c.get(f, [])})
        own[c.concept_id] = ids
        if forms & main_phr:
            overlap.append({"concept_id": c.concept_id, "forms": sorted(forms & main_phr)})
    concepts["own_nodes"] = concepts.concept_id.map(lambda x: own.get(x, []))
    concepts["overlap_main"] = concepts.concept_id.isin({o["concept_id"] for o in overlap})
    concepts["n_verified_links"] = concepts.concept_id.map(lambda x: len(links.get(x, ([], []))[0]))
    agree, oc = 0, []
    for c in concepts.itertuples():
        r, y = links.get(c.concept_id, (np.zeros(0, np.int64), np.zeros(0, np.int32)))
        sel = r[(y >= c.F) & (y <= c.F + 2)]
        cnt = Counter(int(s) for s in sub_raw[sel] if s >= 0)
        mod = cnt.most_common(1)[0][0] if cnt else None
        agree += int(mod == c.origin)
        oc.append({"concept_id": c.concept_id, "origin": c.origin, "modal_F_F2": mod})
    tx = orjson.loads((D5 / "hyd" / "taxonomy.json").read_bytes())
    tax = {"sub_field": {int(k): int(v) for k, v in tx["subfield_field"].items()},
           "field_domain": {int(k): int(v) for k, v in tx["field_domain"].items()},
           "sub_name": {int(k): v for k, v in tx["subfields"].items()},
           "field_name": {int(k): v for k, v in tx["fields"].items()}}
    s_tot = orjson.loads((D5 / "hyd" / "context" / "subfield_year_totals.json").read_bytes())
    totals = {(int(sf), int(y)): int(v) for y, vv in s_tot["variants"]["all_types"].items()
              for sf, v in vv["subfield"].items()}
    W = {"work_id": wids, "year": year, "sub_raw": sub_raw, "sub": sub_raw.copy(),
         "topic_score": np.full(n, np.nan, np.float32), "has_abstract": has_abs, "has_pmid": has_pmid}
    G = {"W": W, "P": P, "AU": AU, "n_authors": int(len(uniq)), "T3": (np.zeros(n + 1, np.int64), np.zeros(0, np.int64)),
         "concepts": concepts, "links": links, "links_union": links_union, "tax": tax, "totals": totals,
         "level": level, "dedup": dedup,
         "origin_check": {"n": len(concepts), "agree": agree, "share": agree / len(concepts), "per_concept": oc},
         "overlap": overlap}
    PREP.write_bytes(pickle.dumps(G, protocol=5))
    return G


def substrate(G: dict) -> dict:
    """Yearly legacy-concept co-occurrence among verified MeSH c-papers (association strength w / (k_i k_j))."""
    rows = np.unique(np.concatenate([r for r, _ in G["links"].values()]))
    ptr, idx_raw = G["P"]
    nodes_u, idx = np.unique(idx_raw, return_inverse=True)   # dense node index (legacy ids exceed 2^31)
    yrs = G["W"]["year"][rows]
    out, ny = [], []
    for yv in range(2000, 2025):
        rr = rows[yrs == yv]
        if not len(rr):
            continue
        pairs, occ = [], Counter()
        for r in rr:
            a = idx[ptr[r]:ptr[r + 1]]
            occ.update(a.tolist())
            if len(a) > 1:
                pairs.extend(i * (1 << 32) + j for i, j in combinations(sorted(a.tolist()), 2))
        if pairs:
            u, w = np.unique(np.asarray(pairs, np.int64), return_counts=True)
            i, j = u >> 32, u & ((1 << 32) - 1)
            ki = np.array([occ[x] for x in i.tolist()], float)
            kj = np.array([occ[x] for x in j.tolist()], float)
            out.append(pd.DataFrame({"year": yv, "i": nodes_u[i], "j": nodes_u[j], "w": w, "as": w / (ki * kj)}))
        deg = Counter()
        if pairs:
            for x in np.concatenate([i, j]).tolist():
                deg[x] += 1
        ny.append(pd.DataFrame({"year": yv, "node": nodes_u[np.array(list(occ.keys()), np.int64)], "n_papers": list(occ.values()),
                                "degree": [deg.get(x, 0) for x in occ.keys()]}))
    cw = pd.concat(out, ignore_index=True)
    nd = pd.concat(ny, ignore_index=True)
    cw.to_parquet(RESULTS / "substrate" / "mesh_coword.parquet", index=False)
    nd.to_parquet(RESULTS / "substrate" / "node_year.parquet", index=False)
    return {"n_pair_year_rows": int(len(cw)), "n_node_year_rows": int(len(nd)), "n_nodes": int(nd.node.nunique()),
            "papers": int(len(rows))}


def run(mini: bool = False, force: bool = False) -> dict:
    G = prepare(force=force)
    con = G["concepts"]
    W = G["W"]
    rows = np.unique(np.concatenate([r for r, _ in G["links"].values()]))
    tags = np.diff(G["P"][0])[rows]
    summ = {"n_concepts": int(len(con)), "dedup": G["dedup"], "n_unique_works": int(len(W["work_id"])),
            "n_verified_unique_works": int(len(rows)),
            "partner_tags_per_verified_paper": {"mean": float(tags.mean()), "median": float(np.median(tags)),
                                                "p10": float(np.percentile(tags, 10)), "p90": float(np.percentile(tags, 90))},
            "verified_works_with_subfield_share": float((W["sub_raw"][rows] >= 0).mean()),
            "verified_works_with_pmid_share": float(W["has_pmid"][rows].mean()),
            "own_nodes": {"concepts_with_own_node": int((con.own_nodes.str.len() > 0).sum()),
                          "total_own_nodes": int(con.own_nodes.str.len().sum())},
            "overlap_with_main_pool": {"n": len(G["overlap"]), "concepts": G["overlap"]},
            "origin_check": {k: v for k, v in G["origin_check"].items() if k != "per_concept"},
            "retrieval_complete": int(con.retrieval_complete.sum()), "rule_parity": int(con.rule_parity.sum())}
    if not mini:
        summ["substrate"] = substrate(G)
    dump(RESULTS / ("mini" if mini else ".") / "mesh_load_summary.json", summ)
    dump(RESULTS / "origin_check_mesh.json", G["origin_check"])
    logger.info(f"load summary: { {k: v for k, v in summ.items() if k != 'overlap_with_main_pool'} }")
    return summ
