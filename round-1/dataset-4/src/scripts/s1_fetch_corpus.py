#!/usr/bin/env python3
"""S1: stratified (field x year) OpenAlex background corpus + pre-period screen.

Main corpus: 26 fields x 2003-2016; prescreen: 26 fields x 1995-2004.
One seeded sample=150 call per stratum (per_page=150), plus one group_by call per
year for stratum sizes N and one has_abstract group_by per year for coverage.
Output: raw/corpus_works/corpus_works_part_NNN.jsonl (one compact work per line, <=80 MB parts), raw/strata.json.
Re-running reads everything from the on-disk cache (resumable).
"""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

from loguru import logger

sys.path.insert(0, str(Path(__file__).resolve().parent))
from oa_client import OAClient, BudgetExhausted, ROOT  # noqa: E402
from rawio import write_corpus_works  # noqa: E402

logger.remove()
logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
logger.add(ROOT / "logs" / "s1_corpus.log", rotation="30 MB", level="DEBUG")

FIELDS = list(range(11, 37))  # 26 OpenAlex fields
MAIN_YEARS = list(range(2003, 2017))
PRE_YEARS = list(range(1995, 2005))
SAMPLE = 150
BASE_FILTER = "has_abstract:true,language:en,type:article|review"
SELECT = ("id,doi,display_name,publication_year,publication_date,primary_topic,primary_location,"
          "keywords,concepts,abstract_inverted_index,referenced_works_count,authorships")


def seed_for(field: int, year: int, corpus: str) -> int:
    return (field * 10000 + year) * (1 if corpus == "main" else 7) % 1000003


def rebuild_abstract(inv: dict | None) -> str:
    if not inv:
        return ""
    pos: list[tuple[int, str]] = []
    for w, idxs in inv.items():
        for i in idxs:
            pos.append((i, w))
    pos.sort()
    return " ".join(w for _, w in pos)


def compact(w: dict, corpus: str, field: int, year: int) -> dict:
    pt = w.get("primary_topic") or {}
    loc = (w.get("primary_location") or {}).get("source") or {}
    return {
        "id": w["id"].rsplit("/", 1)[-1],
        "doi": w.get("doi"),
        "title": w.get("display_name") or "",
        "abstract": rebuild_abstract(w.get("abstract_inverted_index")),
        "year": w.get("publication_year"),
        "date": w.get("publication_date"),
        "field_id": field,
        "field": (pt.get("field") or {}).get("display_name"),
        "subfield_id": ((pt.get("subfield") or {}).get("id") or "").rsplit("/", 1)[-1],
        "subfield": (pt.get("subfield") or {}).get("display_name"),
        "domain": (pt.get("domain") or {}).get("display_name"),
        "topic_id": (pt.get("id") or "").rsplit("/", 1)[-1],
        "topic": pt.get("display_name"),
        "venue_id": (loc.get("id") or "").rsplit("/", 1)[-1] or None,
        "venue_type": loc.get("type"),
        "keywords": [k.get("display_name") for k in (w.get("keywords") or [])],
        "concepts": [c.get("display_name") for c in (w.get("concepts") or []) if (c.get("score") or 0) >= 0.3][:10],
        "referenced_works_count": w.get("referenced_works_count"),
        "author_ids": [((a.get("author") or {}).get("id") or "").rsplit("/", 1)[-1] for a in (w.get("authorships") or [])][:50],
        "institution_ids": sorted({(i.get("id") or "").rsplit("/", 1)[-1] for a in (w.get("authorships") or [])
                                   for i in (a.get("institutions") or []) if i.get("id")})[:50],
        "corpus": corpus,
        "stratum_field": field,
        "stratum_year": year,
    }


async def main() -> None:
    strata_out = ROOT / "raw" / "strata.json"
    async with OAClient(artifact_cap_credits=6000) as oa:
        years = sorted(set(MAIN_YEARS) | set(PRE_YEARS))
        # stratum sizes and abstract coverage per year
        size_tasks = [oa.get("/works", {"filter": f"{BASE_FILTER},publication_year:{y}",
                                        "group_by": "primary_topic.field.id"}) for y in years]
        cov_tasks = [oa.get("/works", {"filter": f"language:en,type:article|review,publication_year:{y}",
                                       "group_by": "has_abstract"}) for y in years]
        sizes = await asyncio.gather(*size_tasks)
        covs = await asyncio.gather(*cov_tasks)
        N: dict[str, int] = {}
        for y, r in zip(years, sizes):
            for g in r.get("group_by", []):
                fid = str(g["key"]).rsplit("/", 1)[-1]
                N[f"{fid}_{y}"] = g["count"]
        coverage = {}
        for y, r in zip(years, covs):
            d = {str(g["key_display_name"]).lower(): g["count"] for g in r.get("group_by", [])}
            tot = sum(d.values())
            coverage[y] = {"with_abstract": d.get("true", 0), "total": tot,
                           "share": round(d.get("true", 0) / tot, 4) if tot else None}
        logger.info(f"stratum sizes for {len(N)} field-years; coverage {coverage.get(2010)}")

        jobs = [(f, y, "main") for y in MAIN_YEARS for f in FIELDS] + [(f, y, "prescreen") for y in PRE_YEARS for f in FIELDS]

        async def fetch(f: int, y: int, c: str):
            params = {"filter": f"primary_topic.field.id:{f},publication_year:{y},{BASE_FILTER}",
                      "sample": SAMPLE, "seed": seed_for(f, y, c), "per_page": SAMPLE, "select": SELECT}
            try:
                return f, y, c, await oa.get("/works", params)
            except BudgetExhausted as e:
                logger.error(f"budget stop at {f},{y},{c}: {e}")
                return f, y, c, None

        results = await asyncio.gather(*[fetch(*j) for j in jobs])
        seen: set[str] = set()
        strata = []
        rows: list[dict] = []
        for f, y, c, r in results:
            got = 0
            if r is not None:
                for w in r.get("results", []):
                    cw = compact(w, c, f, y)
                    key = f"{cw['id']}_{c}"
                    if key in seen:
                        continue
                    seen.add(key)
                    got += 1
                    rows.append(cw)
            n = N.get(f"{f}_{y}", 0)
            strata.append({"field_id": f, "year": y, "corpus": c, "N_stratum": n, "n_sampled": got,
                           "design_weight": round(n / got, 3) if got else None,
                           "sampling_rate": round(got / n, 6) if n else None,
                           "seed": seed_for(f, y, c), "fetched": r is not None})
        n_rows = write_corpus_works(iter(rows))
        # The has_abstract group_by returns an empty 'false' bucket (coverage looks like 1.0), so the real
        # abstract coverage is computed by scripts/s1b_coverage.py; keep its keys if already present.
        prev = json.loads(strata_out.read_text()) if strata_out.exists() else {}
        out = {"strata": strata, "abstract_coverage_by_year": coverage,
               "sample_per_stratum": SAMPLE, "base_filter": BASE_FILTER}
        if "abstract_coverage_note" in prev:
            out["abstract_coverage_by_year"] = prev["abstract_coverage_by_year"]
            out["abstract_coverage_note"] = prev["abstract_coverage_note"]
        strata_out.write_text(json.dumps(out, indent=1))
        logger.info(f"wrote {n_rows} works; paid calls {oa.paid_calls}, cache hits {oa.cache_hits}, "
                    f"credits spent total {oa.credits_spent}, key remaining {oa.remaining}")


if __name__ == "__main__":
    asyncio.run(main())
