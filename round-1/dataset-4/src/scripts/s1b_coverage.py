#!/usr/bin/env python3
"""S1b: abstract coverage by year (English article|review), 2 group_by calls; written into raw/strata.json.
(The has_abstract group_by returns a 0 'false' bucket, so coverage is computed as with/without filter counts.)"""
import asyncio, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from oa_client import OAClient, ROOT
async def main():
    async with OAClient() as oa:
        base = "language:en,type:article|review,publication_year:1995-2016"
        tot = await oa.get("/works", {"filter": base, "group_by": "publication_year"})
        ab = await oa.get("/works", {"filter": base + ",has_abstract:true", "group_by": "publication_year"})
    t = {int(g["key"]): g["count"] for g in tot["group_by"]}
    a = {int(g["key"]): g["count"] for g in ab["group_by"]}
    cov = {y: {"with_abstract": a.get(y, 0), "total": t[y], "share": round(a.get(y, 0) / t[y], 4)} for y in sorted(t)}
    p = ROOT / "raw" / "strata.json"
    d = json.loads(p.read_text()); d["abstract_coverage_by_year"] = cov
    d["abstract_coverage_note"] = "share of English article|review works with an abstract in OpenAlex, per publication year"
    p.write_text(json.dumps(d, indent=1)); print(cov)
asyncio.run(main())
