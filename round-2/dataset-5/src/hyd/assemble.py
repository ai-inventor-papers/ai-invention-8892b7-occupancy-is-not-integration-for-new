#!/usr/bin/env python3
"""Steps 5 (post-processing), 6b, 7, 8: assemble D1-D5 + documentation from the frozen frame, the retrieval
state (retrieval/*.json) and the local work store. Applies the u-order PREFIX rule.

Outputs: data_out.json (+ full/mini/preview), works/works_part_XX.parquet, concept_work.parquet,
context/{subfield_year_totals.json, venue_habitat.json, quality_report.json, quality_report.md},
keywords_dict.json, pending_hydration.json, logs/assemble_summary.json"""
import asyncio
import glob
import hashlib
import math
import random
import re
from collections import Counter, defaultdict
from datetime import date

import numpy as np
import orjson
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from loguru import logger

from common import ROOT, fold, setup_logging, verify_regex
from hydrate_lib import Store
from llm_utils import LLM, BudgetStop

RET = ROOT / "retrieval"
YEARS = list(range(2000, 2025))
MEGA = {"plos one", "scientific reports", "ieee access", "heliyon", "peerj", "cureus", "medicine",
        "sage open", "f1000research", "royal society open science", "aip advances", "applied sciences",
        "sustainability", "international journal of environmental research and public health", "molecules",
        "sensors", "nature communications", "science advances", "plos computational biology",
        "journal of physics conference series", "iop conference series materials science and engineering"}
SENSE_SYS = ("You judge word senses. For each numbered item you get a phrase and paper titles from ONE year that "
             "use it. Decide whether the titles use the phrase in one technical sense. Return ONLY a JSON array of "
             "{\"i\": <item number>, \"dominant_share\": <0..1 share of titles using the dominant sense>}.")


def f_band(F: int) -> str:
    return "2005-07" if F <= 2007 else ("2008-11" if F <= 2011 else "2012-16")


def norm_title(t: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (t or "").lower()).strip()


async def sense_check(items: list[dict]) -> dict:
    cache_p = ROOT / "screen" / "sense_check.jsonl"
    cache = {}
    if cache_p.exists():
        for line in cache_p.read_text().splitlines():
            r = orjson.loads(line)
            cache[r["concept_id"]] = r
    todo = [x for x in items if x["concept_id"] not in cache and x["titles"]]
    llm = LLM(ROOT / "screen" / "llm_cost_sense.json")

    async def one(b):
        txt = "\n\n".join(f"ITEM {k}: phrase = \"{x['phrase']}\"\n" + "\n".join(f"- {t}" for t in x["titles"])
                          for k, x in enumerate(b))
        res = await llm.json_call(SENSE_SYS, txt, max_tokens=800)
        byi = {int(r.get("i", -1)): r for r in res if isinstance(r, dict)} if isinstance(res, list) else {}
        return [{"concept_id": x["concept_id"],
                 "dominant_share": float(byi[k].get("dominant_share", 1.0)) if k in byi else None}
                for k, x in enumerate(b)]

    batches = [todo[i:i + 8] for i in range(0, len(todo), 8)]
    res = await asyncio.gather(*[one(b) for b in batches], return_exceptions=True)
    with cache_p.open("ab") as f:
        for r in res:
            if isinstance(r, BaseException):
                logger.warning(f"sense batch failed: {r}")
                continue
            for x in r:
                cache[x["concept_id"]] = x
                f.write(orjson.dumps(x) + b"\n")
    logger.info(f"sense check LLM cost ${llm.cost:.4f}")
    return cache


def venue_table(source_ids: set[int], tax: dict) -> dict[int, dict]:
    fs = glob.glob(str(ROOT / "snapshot_entities/sources/**/*.parquet"), recursive=True)
    topic_sf = {k: v["subfield"] for k, v in tax["topics"].items()}
    out = {}
    for f in fs:
        t = pq.read_table(f, columns=["id", "issn_l", "display_name", "type", "host_organization_name",
                                      "works_count", "topics", "counts_by_year"]).to_pandas()
        t["sid"] = t["id"].str.rsplit("/S", n=1).str[-1].astype("int64")
        t = t[t["sid"].isin(source_ids)]
        for r in t.itertuples():
            sfc = Counter()
            topics = r.topics if r.topics is not None else []
            for tp in topics:
                tid = (tp.get("id") or "").rsplit("/", 1)[-1]
                if tid in topic_sf:
                    sfc[topic_sf[tid]] += int(tp.get("count") or 0)
            tot = sum(sfc.values())
            dom, domc = (sfc.most_common(1)[0] if sfc else (None, 0))
            share = domc / tot if tot else 0.0
            cby = r.counts_by_year if r.counts_by_year is not None else []
            yr_counts = [int(c.get("works_count") or 0) for c in cby]
            per_year = max(yr_counts) if yr_counts else 0
            name = (r.display_name or "").lower().replace("&", "and")
            name = re.sub(r"[^a-z ]", " ", name)
            name = re.sub(r"\s+", " ", name).strip()
            mega = name in MEGA or (share < 0.40 and per_year > 3000)
            if r.type not in ("journal", "conference"):
                reason = f"type_{r.type}"
            elif mega:
                reason = "megajournal"
            elif share <= 0.40:
                reason = "dominant_share_le_0.40"
            else:
                reason = None
            out[int(r.sid)] = {"source_id": int(r.sid), "issn_l": r.issn_l, "display_name": r.display_name,
                               "type": r.type, "host_org": r.host_organization_name, "works_count": int(r.works_count or 0),
                               "max_works_per_year": per_year,
                               "subfield_shares": {str(k): round(v / tot, 4) for k, v in sfc.most_common(10)} if tot else {},
                               "dominant_subfield": dom, "dominant_share": round(share, 4), "megajournal": bool(mega),
                               "covered": reason is None, "uncovered_reason": reason}
    return out


@logger.catch(reraise=True)
def main() -> None:
    setup_logging("assemble")
    frame_bytes = (ROOT / "sample_frame_frozen.json").read_bytes()
    sha = hashlib.sha256(frame_bytes).hexdigest()
    assert sha == (ROOT / "sample_frame_frozen.sha256").read_text().split()[0], "sample frame changed after freeze!"
    frame = orjson.loads(frame_bytes)
    tax = orjson.loads((ROOT / "taxonomy.json").read_bytes())
    sf_field = {int(k): v for k, v in tax["subfield_field"].items()}
    field_domain = {int(k): v for k, v in tax["field_domain"].items()}
    byid = {x["concept_id"]: x for x in frame["eligible"] + frame["reference"]}
    order = frame["hydration_order"]
    states = {}
    for cid in order:
        p = RET / f"{cid}.json"
        states[cid] = orjson.loads(p.read_bytes()) if p.exists() else {}
    prefix = []
    for cid in order:
        if states[cid].get("complete"):
            prefix.append(cid)
        else:
            break
    pending = [cid for cid in order if cid not in set(prefix)]
    logger.info(f"prefix complete: {len(prefix)} / {len(order)}; pending {len(pending)}")
    (ROOT / "pending_hydration.json").write_bytes(orjson.dumps({
        "note": "Concepts after the u-order prefix. Resume with: uv run hydrate.py --resume --deadline-min <m> "
                "(then re-run assemble.py). 'complete_beyond_prefix' concepts are already retrieved but excluded "
                "to keep the included set an exact random prefix.",
        "pending": [{"concept_id": c, "phrase": byid[c]["phrase"], "arm": byid[c].get("arm"),
                     "complete_beyond_prefix": bool(states[c].get("complete"))} for c in pending]},
        option=orjson.OPT_INDENT_2))

    store = Store()
    s2map = {}
    try:
        for c_, w_ in store.con.execute("SELECT corpus_id, wid FROM s2map"):
            s2map[c_] = w_
    except Exception:  # noqa: BLE001 - table absent when no route-B concept ran
        pass
    # recompute c-paper links from ALL discovered candidates with accent-folded verification
    for cid in prefix:
        st = states[cid]
        disc = st["discovery"]
        rx = verify_regex(fold(byid[cid]["phrase"]))
        if disc["route"] == "A_openalex_native":
            cands = list(dict.fromkeys(disc["oa_ids"]))
            nomatch_ev = "oa_index_only"
        else:
            cands = list(dict.fromkeys(s2map.get(h["cid"], -1) for h in disc["s2_hits"] if h.get("cid")))
            cands = [w for w in cands if w and w > 0]
            nomatch_ev = "s2_only"
        recs = store.get_many(cands)
        links = []
        for w in cands:
            r = recs.get(w)
            if r is None or not r["publication_year"] or not (2000 <= r["publication_year"] <= 2024):
                continue
            ev = "oa_title" if rx.search(fold(r["title"])) else ("oa_abstract" if rx.search(fold(r["text"])) else
                                                                 (nomatch_ev if not r["has_abstract"] else None))
            if ev:
                links.append((w, ev, r["publication_year"]))
        st["links"] = links
        st["n_candidates_mapped"] = len(cands)
        st["n_verified"] = len(links)
    all_w = sorted({w for cid in prefix for (w, _, _) in states[cid]["links"]})
    works = store.get_many(all_w)
    logger.info(f"{len(all_w)} unique linked works; {len(works)} in store")
    # s2 corpus ids for route-B works
    rev = {}
    try:
        for c, w in store.con.execute("SELECT corpus_id, wid FROM s2map WHERE wid > 0"):
            rev.setdefault(w, c)
    except Exception:  # noqa: BLE001 - table absent when no route-B concept ran
        pass

    # ---- per-concept processing ----
    cw_rows = []
    concept_rows = []
    sense_items = []
    corpus_set = set(works)
    for cid in prefix:
        c = byid[cid]
        st = states[cid]
        rx = verify_regex(fold(c["phrase"]))
        links = [(w, ev, y) for (w, ev, y) in st["links"] if w in works]
        dup_map = defaultdict(list)
        for w, ev, y in links:
            dup_map[norm_title(works[w]["title"])].append(w)
        dup_group = {}
        gid = 0
        for t, ws in dup_map.items():
            if t and len(ws) > 1:
                gid += 1
                for w in ws:
                    dup_group[w] = gid
        for w, ev, y in links:
            m = rx.search(fold(works[w]["text"]))
            cw_rows.append({"concept_id": cid, "work_id": w,
                            "matched_form": re.sub(r"[\s\-]+", " ", m.group(0).lower()) if m else None,
                            "match_evidence": ev, "year": y, "dup_group": dup_group.get(w)})
        oa_by_year = Counter(y for _, _, y in links)
        c2 = dict(c)
        c2["wlinks"] = links
        c2["oa_counts_by_year"] = {str(y): oa_by_year.get(y, 0) for y in YEARS}
        c2["n_dup_groups"] = gid
        if c.get("arm") == "main":
            F = c["F"]
            early = [w for w, _, y in links if F <= y <= F + 2]
            sfc = Counter(works[w]["subfield_id"] for w in early if works[w].get("subfield_id"))
            fc = Counter(works[w]["field_id"] for w in early if works[w].get("field_id"))
            c2["early_oa_verified_count"] = len(early)
            c2["origin_subfield"] = ({"id": sfc.most_common(1)[0][0], "name": tax["subfields"].get(str(sfc.most_common(1)[0][0])),
                                      "share": round(sfc.most_common(1)[0][1] / sum(sfc.values()), 4)} if sfc else None)
            c2["origin_field"] = ({"id": fc.most_common(1)[0][0], "name": tax["fields"].get(str(fc.most_common(1)[0][0])),
                                   "share": round(fc.most_common(1)[0][1] / sum(fc.values()), 4)} if fc else None)
            titles = [works[w]["title"][:250] for w, _, y in links if y == F and works[w]["title"]]
            random.Random(cid).shuffle(titles)
            sense_items.append({"concept_id": cid, "phrase": c["phrase"], "titles": titles[:20]})
        c2["mix"] = dict(Counter(ev for _, ev, _ in links))
        concept_rows.append(c2)
    sense = asyncio.run(sense_check(sense_items)) if sense_items else {}

    # origin field groups (fields with >= 30 included concepts, else domain, else OTHER)
    main_rows = [c for c in concept_rows if c.get("arm") == "main"]
    fcount = Counter(c["origin_field"]["id"] for c in main_rows if c.get("origin_field"))
    gmap = {}
    for fid, n in fcount.items():
        gmap[fid] = f"F{fid}:{tax['fields'][str(fid)]}" if n >= 30 else f"D{field_domain[fid]}:{tax['domains'][str(field_domain[fid])]}"
    gc = Counter(gmap[c["origin_field"]["id"]] for c in main_rows if c.get("origin_field"))
    for fid in list(gmap):
        if gc[gmap[fid]] < 10 and gmap[fid].startswith("D"):
            gmap[fid] = "OTHER_small"
    # realized inclusion probability per stratum (eligible frame vs included prefix)
    elig_strata = Counter()
    for x in frame["eligible"]:
        elig_strata[f"T{x['volume_tercile']}|{x['F_band']}"] += 1
    incl_strata = Counter(f"T{c['volume_tercile']}|{c['F_band']}" for c in main_rows)

    # ---- D2 works table ----
    kw_ids = sorted({k for w in works.values() for k, _ in w["keywords"]})
    kw_idx = {k: i for i, k in enumerate(kw_ids)}
    (ROOT / "keywords_dict.json").write_bytes(orjson.dumps({"index_to_keyword_id": kw_ids}))
    dup_any = {}
    for r in cw_rows:
        if r["dup_group"] is not None:
            dup_any[r["work_id"]] = r["dup_group"]
    rows = []
    for wid in all_w:
        w = works.get(wid)
        if w is None:
            continue
        refs = w["refs"]
        rows.append({
            "work_id": wid, "doi_present": w["doi_present"], "s2_corpus_id": rev.get(wid),
            "publication_year": w["publication_year"], "publication_date": w["publication_date"],
            "type": w["type"], "language": w["language"], "primary_topic_id": w["primary_topic_id"],
            "topic_score": w["topic_score"], "subfield_id": w["subfield_id"], "field_id": w["field_id"],
            "domain_id": w["domain_id"], "topics_top3": [t for t in w["topics_top3"] if t is not None],
            "source_id": w["source_id"], "source_type": w["source_type"], "n_refs": len(refs), "refs": refs,
            "refs_in_corpus": [r for r in refs if r in corpus_set], "author_ids": w["author_ids"],
            "author_positions": w["author_positions"], "institution_ids": w["institution_ids"],
            "keyword_idx": [kw_idx[k] for k, _ in w["keywords"]], "keyword_scores": [s for _, s in w["keywords"]],
            "concept_ids": [c for c, _ in w["concepts"] if c is not None],
            "concept_scores": [s for c, s in w["concepts"] if c is not None],
            "has_abstract": w["has_abstract"], "abstract_n_tokens": w["abstract_n_tokens"],
            "cited_by_count": w["cited_by_count"], "dup_group": dup_any.get(wid), "retrieved_at": w["retrieved_at"],
            "retrieval_batch": w.get("retrieval_batch", "iter1")})
    schema = pa.schema([
        ("work_id", pa.int64()), ("doi_present", pa.bool_()), ("s2_corpus_id", pa.int64()),
        ("publication_year", pa.int16()), ("publication_date", pa.string()), ("type", pa.string()),
        ("language", pa.string()), ("primary_topic_id", pa.int32()), ("topic_score", pa.float32()),
        ("subfield_id", pa.int16()), ("field_id", pa.int8()), ("domain_id", pa.int8()),
        ("topics_top3", pa.list_(pa.int32())), ("source_id", pa.int64()), ("source_type", pa.string()),
        ("n_refs", pa.int16()), ("refs", pa.list_(pa.int64())), ("refs_in_corpus", pa.list_(pa.int64())),
        ("author_ids", pa.list_(pa.int64())), ("author_positions", pa.list_(pa.string())),
        ("institution_ids", pa.list_(pa.list_(pa.int64()))), ("keyword_idx", pa.list_(pa.int32())),
        ("keyword_scores", pa.list_(pa.float32())), ("concept_ids", pa.list_(pa.int64())),
        ("concept_scores", pa.list_(pa.float32())), ("has_abstract", pa.bool_()),
        ("abstract_n_tokens", pa.int16()), ("cited_by_count", pa.int32()), ("dup_group", pa.int32()),
        ("retrieved_at", pa.string()), ("retrieval_batch", pa.string())])
    (ROOT / "works").mkdir(exist_ok=True)
    for old in (ROOT / "works").glob("works_part_*.parquet"):
        old.unlink()
    part_n = 60_000
    n_parts = 0
    for i in range(0, len(rows), part_n):
        chunk = rows[i:i + part_n]
        for r in chunk:
            r["abstract_n_tokens"] = min(r["abstract_n_tokens"], 32767)
            r["n_refs"] = min(r["n_refs"], 32767)
        tb = pa.Table.from_pylist(chunk, schema=schema)
        pq.write_table(tb, ROOT / "works" / f"works_part_{n_parts:02d}.parquet", compression="zstd")
        n_parts += 1
    logger.info(f"D2: {len(rows)} works in {n_parts} parts")

    # ---- D3 ----
    cw = pd.DataFrame(cw_rows)
    cw.to_parquet(ROOT / "concept_work.parquet", index=False, compression="zstd")

    # ---- D4 ----
    raw = orjson.loads((ROOT / "context" / "subfield_year_totals_raw.json").read_bytes())
    d4 = {"retrieved_at": "2026-09-28", "source": "OpenAlex /works group_by=primary_topic.subfield.id per publication_year",
          "variants": {}, "note": "'unknown' = works without primary_topic. field/domain totals are sums over subfields."}
    for key, sub in raw.items():
        v, y = key.split("|")
        sfd = {k: n for k, n in sub.items() if k.isdigit()}
        fld, dom = Counter(), Counter()
        for k, n in sfd.items():
            f = sf_field.get(int(k))
            if f:
                fld[str(f)] += n
                dom[str(field_domain[f])] += n
        d4["variants"].setdefault(v, {})[y] = {"subfield": sfd, "field": dict(fld), "domain": dict(dom),
                                               "unknown": sub.get("unknown", 0), "total_with_topic": sum(sfd.values())}
    (ROOT / "context" / "subfield_year_totals.json").write_bytes(orjson.dumps(d4))

    # ---- D5 ----
    sids = {r["source_id"] for r in rows if r["source_id"]}
    venues = venue_table(sids, tax)
    cpaper_by_source = Counter(r["source_id"] for r in rows if r["source_id"])
    for s, v in venues.items():
        v["n_cpapers"] = cpaper_by_source.get(s, 0)
    covered = {s for s, v in venues.items() if v["covered"]}
    d5 = {"retrieved_at": "2026-09-28", "source": "OpenAlex S3 snapshot data/parquet/sources (topics counts, all years)",
          "definition": "covered = dominant_share > 0.40 AND type in {journal, conference} AND not megajournal",
          "pre_period_variant": "not computed in this round (credit budget exhausted); see README",
          "n_venues": len(venues), "n_covered": len(covered), "venues": list(venues.values())}
    (ROOT / "context" / "venue_habitat.json").write_bytes(orjson.dumps(d5))

    # ---- quality report ----
    concept_of = defaultdict(list)
    for r in cw_rows:
        concept_of[r["concept_id"]].append(r)
    q_rows = []
    per_concept_q = {}
    for c in concept_rows:
        cid = c["concept_id"]
        ws = sorted(concept_of[cid], key=lambda r: r["year"])
        cset_year = {r["work_id"]: r["year"] for r in ws}
        topcited = set(sorted(cset_year, key=lambda w: -(works[w]["cited_by_count"] or 0))[:5])
        F = c.get("F")
        origin_sf = (c.get("origin_subfield") or {}).get("id")
        cov_venue = [r for r in ws if works[r["work_id"]]["source_id"] in covered]
        for r in ws:
            w = works[r["work_id"]]
            parents = [p for p in w["refs"] if p in cset_year and cset_year[p] < r["year"]]
            q_rows.append({
                "concept_id": cid, "arm": c.get("arm"), "year": r["year"],
                "group": gmap.get((c.get("origin_field") or {}).get("id"), "REFERENCE" if c.get("arm") == "reference" else "NA"),
                "has_refs": w["refs"] != [], "traced_any": bool(parents),
                "traced_excl_F": bool([p for p in parents if F is None or cset_year[p] != F]),
                "traced_excl_F_top5": bool([p for p in parents if (F is None or cset_year[p] != F) and p not in topcited]),
                "outside_origin": origin_sf is not None and w["subfield_id"] is not None and w["subfield_id"] != origin_sf,
                "has_abstract": w["has_abstract"], "author_cov": bool(w["author_ids"]) and all(a != -1 for a in w["author_ids"]),
                "pt_null": w["subfield_id"] is None, "dup": r["dup_group"] is not None, "ev": r["match_evidence"]})
        per_concept_q[cid] = {"covered_venue_share": round(len(cov_venue) / max(len(ws), 1), 4)}
    qdf = pd.DataFrame(q_rows)

    def summarise(df: pd.DataFrame) -> dict:
        host = df[df.outside_origin]
        return {"n_cpapers": int(len(df)), "share_with_refs": round(float(df.has_refs.mean()), 4),
                "traced_share_any": round(float(df.traced_any.mean()), 4),
                "traced_share_excl_F": round(float(df.traced_excl_F.mean()), 4),
                "traced_share_excl_F_top5cited": round(float(df.traced_excl_F_top5.mean()), 4),
                "host_traced_share_excl_F": round(float(host.traced_excl_F.mean()), 4) if len(host) else None,
                "n_host_cpapers": int(len(host)),
                "abstract_share": round(float(df.has_abstract.mean()), 4),
                "author_id_coverage": round(float(df.author_cov.mean()), 4),
                "primary_topic_null_share": round(float(df.pt_null.mean()), 4),
                "dup_group_share": round(float(df.dup.mean()), 4),
                "match_evidence_mix": {k: int(v) for k, v in df.ev.value_counts().items()}}

    qr = {"overall_main": summarise(qdf[qdf.arm == "main"]) if len(qdf) else {},
          "overall_reference": summarise(qdf[qdf.arm == "reference"]) if len(qdf[qdf.arm == "reference"]) else {},
          "gate_A_threshold_marked_not_applied": 0.40,
          "by_group": {g: summarise(d) for g, d in qdf[qdf.arm == "main"].groupby("group")},
          "by_group_year": {f"{g}|{y}": summarise(d) for (g, y), d in qdf[qdf.arm == "main"].groupby(["group", "year"]) if len(d) >= 20},
          "by_year_main": {str(y): summarise(d) for y, d in qdf[qdf.arm == "main"].groupby("year")},
          "notes": ["traced share = share of c-papers citing >= 1 earlier c-paper of the same concept (within the "
                    "retrieved corpus).", "top5cited uses the 2026 cited_by_count snapshot (proxy for canonical parents).",
                    "host = c-papers whose primary_topic subfield differs from the concept's origin subfield."]}
    # mapping rates for route B
    mrates = [(c["concept_id"], states[c["concept_id"]].get("s2_to_oa_mapping_rate")) for c in concept_rows
              if states[c["concept_id"]]["discovery"]["route"] == "B_s2_index"]
    qr["route_counts"] = dict(Counter(states[c["concept_id"]]["discovery"]["route"] for c in concept_rows))
    qr["s2_mapping_rate_mean"] = round(float(np.mean([m for _, m in mrates if m is not None])), 4) if mrates else None
    unm, s2tot = Counter(), Counter()
    for c in concept_rows:
        st = states[c["concept_id"]]
        for y, n in (st.get("s2_unmapped_by_year") or {}).items():
            unm[y] += n
        for y, n in (st.get("s2_counts_by_year") or {}).items():
            s2tot[y] += n
    qr["s2_unmapped_share_by_year"] = {y: round(unm[y] / s2tot[y], 4) for y in sorted(s2tot) if s2tot[y]}
    (ROOT / "context" / "quality_report.json").write_bytes(orjson.dumps(qr, option=orjson.OPT_INDENT_2))
    cols = ["n_cpapers", "share_with_refs", "traced_share_any", "traced_share_excl_F", "traced_share_excl_F_top5cited",
            "host_traced_share_excl_F", "n_host_cpapers", "abstract_share", "author_id_coverage",
            "primary_topic_null_share", "dup_group_share"]
    md = ["# Gate-A data-quality report (descriptive; 0.40 host-traced threshold marked, NOT applied)", "",
          f"Routes: {qr['route_counts']}; mean S2->OpenAlex mapping rate (route B): {qr['s2_mapping_rate_mean']}", "",
          "| group | " + " | ".join(cols) + " |", "|" + "---|" * (len(cols) + 1)]
    rows_md = [("ALL main", qr["overall_main"]), ("REFERENCE arm", qr["overall_reference"])] + list(qr["by_group"].items())
    for g, v in rows_md:
        if v:
            md.append(f"| {g} | " + " | ".join(str(v.get(c)) for c in cols) + " |")
    md += ["", "## By publication year (main arm)", "", "| year | " + " | ".join(cols) + " |", "|" + "---|" * (len(cols) + 1)]
    for y, v in sorted(qr["by_year_main"].items()):
        md.append(f"| {y} | " + " | ".join(str(v.get(c)) for c in cols) + " |")
    md += ["", "Notes:"] + [f"- {n}" for n in qr["notes"]]
    (ROOT / "context" / "quality_report.md").write_text("\n".join(md) + "\n")

    # ---- D1 data_out.json ----
    examples = []
    for c in concept_rows:
        cid = c["concept_id"]
        st = states[cid]
        is_main = c.get("arm") == "main"
        s_share = (sense.get(cid) or {}).get("dominant_share")
        flags = []
        if c.get("burst_start"):
            flags.append("burst_start")
        if s_share is not None and s_share < 0.7:
            flags.append("sense_check_fail")
        n_works = len(c["wlinks"])
        if n_works > 25_000:
            flags.append("large_concept")
        if c["n_dup_groups"]:
            flags.append("dup_groups_present")
        if c.get("multi_sense_flag"):
            flags.append("llm_multi_sense")
        inp = {"concept_id": cid, "phrase": c["phrase"], "surface_forms": c.get("surface_forms", []),
               "acronyms_stored_not_used": c.get("acronyms", []), "vocab_arms": c.get("vocab_arms", []),
               "links": byid[cid].get("links", {})}
        if is_main:
            inp.update({"F": c["F"], "screen_counts_by_year": c["screen_counts_by_year"],
                        "early_volume_V": c["V"], "origin_field": c.get("origin_field"),
                        "origin_subfield": c.get("origin_subfield"), "early_oa_verified_count": c.get("early_oa_verified_count")})
        else:
            inp.update({"screen_counts_by_year_1995_2004": c["screen_counts_by_year"]})
        out = {"oa_counts_by_year": c["oa_counts_by_year"],
               "s2_counts_by_year": {str(y): (st.get("s2_counts_by_year") or {}).get(str(y), 0) for y in YEARS}
               if st["discovery"]["route"] == "B_s2_index" else None,
               "n_works": n_works, "work_ids": sorted(w for w, _, _ in c["wlinks"])}
        mix = c["mix"]
        tot = max(sum(mix.values()), 1)
        ex = {"input": orjson.dumps(inp).decode(), "output": orjson.dumps(out).decode(),
              "metadata_fold": c.get("metadata_fold", "reference"), "metadata_arm": c.get("arm"),
              "metadata_concept_id": cid, "metadata_phrase": c["phrase"],
              "metadata_retrieval_route": st["discovery"]["route"],
              "metadata_s2_to_oa_mapping_rate": st.get("s2_to_oa_mapping_rate"),
              "metadata_match_evidence_mix": {k: round(v / tot, 4) for k, v in mix.items()},
              "metadata_hydration_complete": True, "metadata_flags": flags,
              "metadata_hydration_batch": st.get("hydration_batch", "iter1"),
              "metadata_sense_dominant_share": s_share,
              "metadata_sample_rank_u": c["sample_rank_u"], "metadata_design_selection_prob": c["design_selection_prob"],
              "metadata_covered_venue_share": per_concept_q.get(cid, {}).get("covered_venue_share")}
        if is_main:
            stratum_desc = f"{gmap.get((c.get('origin_field') or {}).get('id'), 'NA')}|T{c['volume_tercile']}|{c['F_band']}"
            sp = f"T{c['volume_tercile']}|{c['F_band']}"
            ex.update({"metadata_stratum": stratum_desc, "metadata_F_band": c["F_band"],
                       "metadata_volume_tercile": c["volume_tercile"],
                       "metadata_realized_inclusion_prob": round(incl_strata[sp] / elig_strata[sp], 4),
                       "metadata_focal_years_all": [t for t in range(c["F"] + 3, min(c["F"] + 8, 2019) + 1)],
                       "metadata_focal_years_screen": c["focal_years_screen"],
                       "metadata_focal_years_heldout": c["focal_years_heldout"],
                       "metadata_vocab_arm_tag": c.get("arm_tag")})
        examples.append(ex)
    data_out = {"metadata": {
        "description": "Outcome-blind pool of scientific concepts first used 2005-2016 (main arm) plus a stationary "
                       "reference arm, with complete OpenAlex work lists 2000-2024. See README.md.",
        "sample_frame_sha256": sha, "retrieved_at": date.today().isoformat(),
        "n_main": sum(1 for e in examples if e["metadata_arm"] == "main"),
        "n_reference": sum(1 for e in examples if e["metadata_arm"] == "reference"),
        "origin_field_group_map": {str(k): v for k, v in gmap.items()}},
        "datasets": [{"dataset": "concept_pool_2005_2016", "examples": examples}]}
    (ROOT / "data_out.json").write_bytes(orjson.dumps(data_out))
    summ = {"prefix_complete": len(prefix), "pending": len(pending),
            "hydration_batch_counts": dict(Counter(e["metadata_hydration_batch"] for e in examples)),
            "retrieval_batch_counts_works": dict(Counter(r["retrieval_batch"] for r in rows)), "n_main": data_out["metadata"]["n_main"],
            "n_reference": data_out["metadata"]["n_reference"], "n_works": len(rows), "n_links": len(cw_rows),
            "fold_counts": dict(Counter(e["metadata_fold"] for e in examples)),
            "route_counts": qr["route_counts"],
            "screen_heldout_focal_nonempty_by_band": {
                b: {"screen": sum(1 for c in main_rows if c["F_band"] == b and c["focal_years_screen"]),
                    "heldout": sum(1 for c in main_rows if c["F_band"] == b and c["focal_years_heldout"])}
                for b in ["2005-07", "2008-11", "2012-16"]},
            "per_group_N": dict(Counter(gmap.get((c.get("origin_field") or {}).get("id"), "NA") for c in main_rows))}
    (ROOT / "logs" / "assemble_summary.json").write_bytes(orjson.dumps(summ, option=orjson.OPT_INDENT_2))
    logger.info(orjson.dumps(summ).decode())


if __name__ == "__main__":
    main()
