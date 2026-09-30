#!/usr/bin/env python3
"""Step 9: route calibration against the main corpus's plain OpenAlex query.

usage: s06_calibrate.py fetch    (paid, ~150 credits) pick 10 working-list concepts from the top sample ranks spread over
                                 branch groups; run the plain query title_and_abstract.search:(forms) over ALL works,
                                 2000-2024, group_by=publication_year; for the 3 smallest also page all work ids.
                                 -> temp/calib_plain.json, temp/calibration_members.json
       s06_calibrate.py compare  (local) compare with this artifact's union route -> route_calibration.json
The plain query is fetched early (before retrieval) only because the shared key's credits were draining;
the comparison itself uses the finished works parts.
"""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

import aiohttp
from loguru import logger

sys.path.insert(0, str(Path(__file__).resolve().parent))
import oa  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
TEMP = ROOT / "temp"
logger.remove()
logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
logger.add(ROOT / "logs" / "s06_calibrate.log", rotation="30 MB", level="DEBUG")
YEARS = [str(y) for y in range(2000, 2025)]
N_CAL, N_JACC, TOP_RANKS = 10, 3, 60


def or_expr(forms: list[str]) -> str:
    fs = []
    for f in forms:
        f = f.replace('"', "").replace(",", " ").strip()
        if f and f.lower() not in {x.lower() for x in fs}:
            fs.append(f)
    return " OR ".join(f'"{f}"' for f in fs)


def pick(wl: list[dict]) -> list[dict]:
    top = sorted([r for r in wl if r["sample_rank"] <= TOP_RANKS], key=lambda r: r["sample_rank"])
    by_g: dict[str, list[dict]] = {}
    for r in top:
        by_g.setdefault(r["branch_group"], []).append(r)
    out = []
    while len(out) < min(N_CAL, len(top)):
        for g in sorted(by_g):
            if by_g[g] and len(out) < N_CAL:
                out.append(by_g[g].pop(0))
    return out


async def fetch() -> None:
    wl = json.loads((TEMP / "working_list.json").read_text())
    cal = pick(wl)
    logger.info(f"calibration concepts: {[(r['sample_rank'], r['preferred_term']) for r in cal]}")
    out = []
    async with aiohttp.ClientSession() as sess:
        client = oa.OA(sess, rps=4, conc=2)
        for r in cal:
            filt = f"title_and_abstract.search:({or_expr(r['surface_forms'])}),publication_year:2000-2024"
            if not client.can_spend(10):
                logger.warning("artifact credit ceiling reached")
                break
            st, js = await client.get("/works", {"filter": filt, "group_by": "publication_year"}, paid_kind="group_by")
            if st != 200:
                logger.error(f"group_by failed {r['descriptor_ui']}: {st}")
                continue
            plain = {str(g["key"]): g["count"] for g in js["group_by"]}
            out.append({"descriptor_ui": r["descriptor_ui"], "concept_id": r["concept_id"], "preferred_term": r["preferred_term"],
                        "sample_rank": r["sample_rank"], "query_filter": filt, "plain_per_year": plain,
                        "total_plain": sum(plain.get(y, 0) for y in YEARS)})
            logger.info(f"{r['preferred_term']}: plain total {out[-1]['total_plain']}")
        for c in sorted([c for c in out if c["total_plain"] > 0], key=lambda c: c["total_plain"])[:N_JACC]:
            pages = -(-c["total_plain"] // 200)
            if pages > 6 or not client.can_spend(pages * 10):
                logger.warning(f"skip id paging for {c['preferred_term']} ({pages} pages)")
                continue
            ids, cursor = {}, "*"
            while cursor:
                st, js = await client.get("/works", {"filter": c["query_filter"], "select": "id,ids,publication_year",
                                                     "per_page": 200, "cursor": cursor}, paid_kind="search")
                if st != 200 or not js["results"]:
                    break
                for w in js["results"]:
                    ids[oa._int_id(w["id"])] = bool((w.get("ids") or {}).get("pmid"))
                cursor = js["meta"].get("next_cursor")
            c["plain_ids"] = {str(k): v for k, v in ids.items()}
            logger.info(f"paged {len(ids)} plain ids for {c['preferred_term']}")
    (TEMP / "calib_plain.json").write_text(json.dumps(out))
    (TEMP / "calibration_members.json").write_text(json.dumps([c["descriptor_ui"] for c in out]))
    logger.info(f"calibration fetch done; artifact ledger total {oa.ledger_total()}")


def compare() -> None:
    """Union route rebuilt from the retrieval caches for every calibration concept (accepted or not)."""
    import s05_finalize as fin
    cal = json.loads((TEMP / "calib_plain.json").read_text())
    final_ids = {c["input"]["descriptor_ui"] for c in json.loads((ROOT / "data_out.json").read_text())}
    wl = {r["descriptor_ui"]: r for r in json.loads((TEMP / "working_list.json").read_text())}
    tiab = json.loads((TEMP / "pubmed_tiab_pmids.json").read_text())
    idx = json.loads((TEMP / "mesh_indexed.json").read_text())
    pm = fin.load_pm_cache()
    rem, rstate = fin.load_remainder()
    rows = []
    for c in cal:
        u = c["descriptor_ui"]
        cc = fin.build_concept(wl[u], tiab[u], idx[u], pm, rem.get(u, []), u in rstate["done"])
        union = [x for x in cc["rows"] if x["match_route"] in fin.UNION_ROUTES and x["verified_text_match"]]
        allr = [x for x in cc["rows"] if x["match_route"] != "mesh_indexed_only"]
        uy = {str(y): cc["yearly"][y] for y in fin.YEARS}
        row = {k: c[k] for k in ("concept_id", "preferred_term", "sample_rank", "query_filter", "total_plain")}
        row.update({"in_final_population": u in final_ids, "retrieval_complete": u in rstate["done"],
                    "per_year": {y: {"plain_openalex": c["plain_per_year"].get(y, 0), "union_verified": uy[y]} for y in YEARS},
                    "total_union_verified": sum(uy.values())})
        row["ratio_union_to_plain"] = round(row["total_union_verified"] / c["total_plain"], 4) if c["total_plain"] else None
        row["F_plain"] = next((int(y) for y in YEARS if c["plain_per_year"].get(y, 0) >= 5), None)
        row["F_union"] = cc["F"]
        if "plain_ids" in c:
            ids = {int(k): v for k, v in c["plain_ids"].items()}
            P, V, A = set(ids), {x["work_id"] for x in union}, {x["work_id"] for x in allr}
            only = P - A
            row["work_overlap"] = {
                "n_plain": len(P), "n_union_verified": len(V), "n_union_retrieved": len(A),
                "jaccard_plain_vs_union_verified": round(len(P & V) / len(P | V), 4) if P | V else None,
                "jaccard_plain_vs_union_retrieved": round(len(P & A) / len(P | A), 4) if P | A else None,
                "n_plain_only": len(only), "n_plain_only_with_pmid": sum(1 for w in only if ids[w]),
                "n_union_verified_only": len(V - P)}
        rows.append(row)
    ratios = sorted(r["ratio_union_to_plain"] for r in rows if r.get("ratio_union_to_plain"))
    summ = {"n_calibration_concepts": len(rows), "n_in_final_population": sum(1 for r in rows if r.get("in_final_population")),
            "ratio_union_to_plain_median": ratios[len(ratios) // 2] if ratios else None,
            "ratio_union_to_plain_min": ratios[0] if ratios else None, "ratio_union_to_plain_max": ratios[-1] if ratios else None,
            "F_agreement": sum(1 for r in rows if r.get("F_union") is not None and r.get("F_union") == r.get("F_plain")),
            "F_within_1y": sum(1 for r in rows if r.get("F_union") is not None and r.get("F_plain") is not None and abs(r["F_union"] - r["F_plain"]) <= 1),
            "artifact_openalex_credits_spent_total": oa.ledger_total()}
    (ROOT / "route_calibration.json").write_text(json.dumps({
        "description": "Union route (PubMed [tiab] -> free OpenAlex singletons, plus OpenAlex has_pmid:false title_and_abstract.search; "
                       "all locally verified) versus the main corpus's plain OpenAlex title_and_abstract.search over all works, 2000-2024.",
        "summary": summ, "concepts": rows}, indent=1))
    logger.info(f"calibration summary {summ}")


if __name__ == "__main__":
    mode = sys.argv[1]
    logger.catch(reraise=True)(lambda: asyncio.run(fetch()) if mode == "fetch" else compare())()
