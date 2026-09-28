#!/usr/bin/env python3
"""Per-concept yearly counts of NON-PubMed OpenAlex works (has_pmid:false, 2000-2024) via
title_and_abstract.search + group_by=publication_year. group_by calls are list-priced (1 credit each,
measured from X-RateLimit-Credits-Used), so this sizes the paid remainder for every working-list concept
before any paging, and gives a count-level fallback for concepts whose works cannot all be paged.
Output: temp/nonpubmed_counts.json
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
from s06_calibrate import or_expr  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
TEMP = ROOT / "temp"
logger.remove()
logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
logger.add(ROOT / "logs" / "s04b_counts.log", rotation="30 MB", level="DEBUG")


async def amain() -> None:
    wl = sorted(json.loads((TEMP / "working_list.json").read_text()), key=lambda r: r["sample_rank"])
    outp = TEMP / "nonpubmed_counts.json"
    out = json.loads(outp.read_text()) if outp.exists() else {}
    todo = [r for r in wl if r["descriptor_ui"] not in out]
    async with aiohttp.ClientSession() as sess:
        client = oa.OA(sess, rps=4, conc=3)

        async def one(r: dict) -> None:
            if not client.can_spend(2):
                return
            filt = f"title_and_abstract.search:({or_expr(r['surface_forms'])}),has_pmid:false,publication_year:2000-2024"
            st, js = await client.get("/works", {"filter": filt, "group_by": "publication_year"}, paid_kind="group_by")
            if st == 200:
                yc = {str(g["key"]): g["count"] for g in js["group_by"]}
                out[r["descriptor_ui"]] = {"filter": filt, "yearly": yc, "total": sum(yc.values())}
        for i in range(0, len(todo), 3):   # rank order; budget checked before every group of 3 calls
            if client.budget_exhausted or not client.can_spend(3):
                logger.warning(f"credit ceiling / key budget reached after {i} of {len(todo)} concepts")
                break
            await asyncio.gather(*(one(r) for r in todo[i:i + 3]))
    outp.write_text(json.dumps(out))
    tot = sorted(((v["total"], u) for u, v in out.items()), reverse=True)
    logger.info(f"counted {len(out)} concepts; sum non-PubMed works {sum(t for t, _ in tot)}; top: {tot[:12]}; ledger {oa.ledger_total()}")


if __name__ == "__main__":
    logger.catch(reraise=True)(lambda: asyncio.run(amain()))()
