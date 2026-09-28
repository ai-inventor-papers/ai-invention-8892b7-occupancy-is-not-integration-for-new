#!/usr/bin/env python3
"""Budget-route (b) of the plan: batched list lookups filter=ids.pmid:p1|...|p100 (1 credit per 100 works,
measured) for PubMed-route PMIDs, walking the working list from the END of the rank order while the free
singleton fetcher (s04_retrieve.py pubmed) walks from the front. Needed because the key-wide 30 req/s
rate limit, shared with sibling runs, held free singletons to ~13 req/s.

usage: s04c_pmid_list_batches.py <credit_cap>
Writes temp/oa_cache/pmid_works_list.jsonl (same record format as the singleton cache; PMIDs requested but
not returned are recorded with status 404).
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
from s04_retrieve import cached_pmids  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
TEMP = ROOT / "temp"
OUT = TEMP / "oa_cache" / "pmid_works_list.jsonl"
logger.remove()
logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
logger.add(ROOT / "logs" / "s04c_list.log", rotation="30 MB", level="DEBUG")


async def amain(cap: int) -> None:
    wl = sorted(json.loads((TEMP / "working_list.json").read_text()), key=lambda r: -r["sample_rank"])
    tiab = json.loads((TEMP / "pubmed_tiab_pmids.json").read_text())
    nc = json.loads((TEMP / "nonpubmed_counts.json").read_text())
    have = cached_pmids()
    want: list[int] = []
    for r in wl:
        if nc.get(r["descriptor_ui"], {}).get("total", 0) > 8000:
            continue  # fails the total cap on non-PubMed works alone
        want.extend(p for p in tiab[r["descriptor_ui"]] if p not in have)
    want = list(dict.fromkeys(want))
    start = oa.ledger_total()
    n_batches = min(len(want) // 100 + 1, cap)
    logger.info(f"{len(want)} PMIDs not cached; fetching up to {n_batches} batches (cap {cap} credits); ledger {start}")
    batches = [want[i:i + 100] for i in range(0, len(want), 100)][:n_batches]
    fh = OUT.open("a")
    async with aiohttp.ClientSession() as sess:
        client = oa.OA(sess, rps=6, conc=4)

        async def one(b: list[int]) -> None:
            if client.budget_exhausted or oa.ledger_total() - start >= cap or not client.can_spend(1):
                return
            st, js = await client.get("/works", {"filter": "ids.pmid:" + "|".join(map(str, b)), "per_page": 100,
                                                 "select": oa.SELECT}, paid_kind="list")
            if st != 200:
                logger.warning(f"batch failed status {st}")
                return
            got = set()
            for w in js["results"]:
                c = oa.compact(w)
                t, a = oa.texts(w)
                if c["pmid"] in b:
                    got.add(c["pmid"])
                    fh.write(json.dumps({"pmid": c["pmid"], "status": 200, "w": c, "t": t, "a": a}) + "\n")
            for p in set(b) - got:
                fh.write(json.dumps({"pmid": p, "status": 404}) + "\n")

        for i in range(0, len(batches), 40):
            await asyncio.gather(*(one(b) for b in batches[i:i + 40]))
            fh.flush()
            logger.info(f"{min(i + 40, len(batches))}/{len(batches)} batches; artifact ledger {oa.ledger_total()}")
            if client.budget_exhausted or oa.ledger_total() - start >= cap:
                break
    fh.close()
    logger.info(f"done; artifact ledger {oa.ledger_total()}")


if __name__ == "__main__":
    logger.catch(reraise=True)(lambda: asyncio.run(amain(int(sys.argv[1]))))()
