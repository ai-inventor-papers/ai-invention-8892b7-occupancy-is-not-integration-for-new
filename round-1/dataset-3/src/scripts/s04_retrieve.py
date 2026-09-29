#!/usr/bin/env python3
"""Step 7: retrieval for the working list, in sample_rank order.

usage: s04_retrieve.py pubmed [max_rank]      free singleton lookups /works/pmid:X for all [tiab] PMIDs
       s04_retrieve.py remainder [max_rank]   paid OR-batched title_and_abstract.search restricted to has_pmid:false
       s04_retrieve.py meshonly [max_rank]    free singleton lookups for MeSH-indexed-only PMIDs (time permitting)

All results are cached as JSONL under temp/oa_cache/ (compact record + normalised title/abstract text used
only for local verification; the text is dropped at packaging). Re-running resumes from the cache.
"""
from __future__ import annotations

import asyncio
import json
import os
import resource
import sys
import time
from pathlib import Path
from urllib.parse import quote

import aiohttp
from loguru import logger

sys.path.insert(0, str(Path(__file__).resolve().parent))
import oa  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
TEMP = ROOT / "temp"
CACHE = TEMP / "oa_cache"
CACHE.mkdir(parents=True, exist_ok=True)
logger.remove()
logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
logger.add(ROOT / "logs" / "s04_retrieve.log", rotation="30 MB", level="DEBUG")
resource.setrlimit(resource.RLIMIT_AS, (16 * 1024**3, 16 * 1024**3))

PM_CACHE = CACHE / "pmid_works.jsonl"
REM_CACHE = CACHE / "remainder_pages.jsonl"
REM_STATE = CACHE / "remainder_state.json"
URL_BUDGET = 3300          # chars of the (encoded) search expression per OR batch
CALIB_RESERVE = 0 if (TEMP / "calib_plain.json").exists() else 260   # credits kept back for step 9 calibration
PER_PAGE = 200
SPLIT_SEEN: dict = {}


def load_working(max_rank: int | None) -> list[dict]:
    wl = json.loads((TEMP / "working_list.json").read_text())
    wl.sort(key=lambda r: r["sample_rank"])
    return [r for r in wl if max_rank is None or r["sample_rank"] <= max_rank]


def cached_pmids() -> set[int]:
    s = set()
    for f in (PM_CACHE, CACHE / "pmid_works_list.jsonl"):
        if f.exists():
            with f.open() as fh:
                for line in fh:
                    try:
                        s.add(json.loads(line)["pmid"])
                    except json.JSONDecodeError:
                        continue
    return s


async def run_pubmed(max_rank: int | None, which: str) -> None:
    wl = load_working(max_rank)
    tiab = json.loads((TEMP / "pubmed_tiab_pmids.json").read_text())
    nc = json.loads((TEMP / "nonpubmed_counts.json").read_text()) if (TEMP / "nonpubmed_counts.json").exists() else {}
    capfail = {u for u, v in nc.items() if v["total"] > 8000}   # fail the total cap on non-PubMed works alone
    wl = [r for r in wl if r["descriptor_ui"] not in capfail]
    if which == "pubmed":
        want = [p for r in wl for p in tiab[r["descriptor_ui"]]]
    else:
        idx = json.loads((TEMP / "mesh_indexed.json").read_text())
        want = [p for r in wl for p in idx[r["descriptor_ui"]]["pmids"] if p not in set(tiab[r["descriptor_ui"]])]
    done = cached_pmids()
    todo = list(dict.fromkeys(p for p in want if p not in done))
    logger.info(f"[{which}] {len(wl)} concepts, {len(set(want))} unique PMIDs, {len(todo)} to fetch")
    t0 = time.time()
    async with aiohttp.ClientSession(headers={"User-Agent": "aii_mesh_pop/1.0"}) as sess:
        client = oa.OA(sess, rps=float(os.environ.get("AII_SINGLETON_RPS", "18")), conc=24)
        fh = PM_CACHE.open("a")

        async def one(p: int) -> None:
            st, w = await client.get(f"/works/pmid:{p}", {"select": oa.SELECT})
            rec = {"pmid": p, "status": st}
            if st == 200 and w:
                t, a = oa.texts(w)
                rec.update({"w": oa.compact(w), "t": t, "a": a})
            fh.write(json.dumps(rec) + "\n")

        B = 1500
        for i in range(0, len(todo), B):
            await asyncio.gather(*(one(p) for p in todo[i:i + B]))
            fh.flush()
            el = time.time() - t0
            logger.info(f"[{which}] {min(i + B, len(todo))}/{len(todo)} in {el:.0f}s ({min(i + B, len(todo)) / el:.1f}/s)")
        fh.close()


def or_expr(forms: list[str]) -> str:
    fs = []
    for f in forms:
        f = f.replace('"', "").replace(",", " ").strip()
        if f and f.lower() not in {x.lower() for x in fs}:
            fs.append(f)
    return " OR ".join(f'"{f}"' for f in fs)


async def run_remainder(max_rank: int | None) -> None:
    wl = load_working(max_rank)
    state = json.loads(REM_STATE.read_text()) if REM_STATE.exists() else {"done": [], "skipped_budget": [], "batches": []}
    done = set(state["done"])
    # skip concepts whose PubMed-route verified counts already fail irrecoverably
    # (adding works can only make F earlier and totals larger)
    pre_fail = set(json.loads((TEMP / "pubmed_route_fail.json").read_text())) if (TEMP / "pubmed_route_fail.json").exists() else set()
    todo = [r for r in wl if r["descriptor_ui"] not in done and r["descriptor_ui"] not in pre_fail]
    # exact non-PubMed counts from s04b (group_by, 1 credit each): skip concepts whose non-PubMed count alone
    # exceeds the 8,000 cap (they fail the final rule regardless), mark zero-count concepts complete without paging
    nc = json.loads((TEMP / "nonpubmed_counts.json").read_text()) if (TEMP / "nonpubmed_counts.json").exists() else {}
    state.setdefault("skipped_cap", [])
    for r in list(todo):
        u = r["descriptor_ui"]
        if u in nc and nc[u]["total"] > 8000:
            if u not in state["skipped_cap"]:
                state["skipped_cap"].append(u)
            todo.remove(r)
        elif u in nc and nc[u]["total"] == 0:
            state["done"].append(u)
            todo.remove(r)
    REM_STATE.write_text(json.dumps(state))
    logger.info(f"[remainder] {len(todo)} concepts to cover; {len(pre_fail)} skipped as irrecoverable; spent so far {oa.ledger_total()} / stop {oa.STOP_AT}")
    batches, cur, clen, ccount = [], [], 0, 0
    for r in todo:
        e = or_expr(r["surface_forms"])
        L = len(quote(e))
        cnt = nc.get(r["descriptor_ui"], {}).get("total", 0)
        if cur and (clen + L + 10 > URL_BUDGET or ccount + cnt > 2000):
            batches.append(cur)
            cur, clen, ccount = [], 0, 0
        cur.append(r)
        clen += L + 10
        ccount += cnt
    if cur:
        batches.append(cur)
    logger.info(f"[remainder] {len(batches)} OR batches")
    async with aiohttp.ClientSession(headers={"User-Agent": "aii_mesh_pop/1.0"}) as sess:
        client = oa.OA(sess, rps=5, conc=2)
        fh = REM_CACHE.open("a")
        for bi, batch in enumerate(batches):
            expr = " OR ".join(f"({or_expr(r['surface_forms'])})" for r in batch)
            filt = f"title_and_abstract.search:({expr}),has_pmid:false,publication_year:2000-2024"
            if not client.can_spend(10 + CALIB_RESERVE):
                logger.warning("[remainder] budget ceiling reached; stopping")
                break
            known = sum(nc.get(r["descriptor_ui"], {}).get("total", 0) for r in batch)
            proj = -(-known // PER_PAGE) * 10
            if nc and client.spent + max(proj, 10) + CALIB_RESERVE > oa.STOP_AT:
                if len(batch) > 1:
                    half = len(batch) // 2
                    batches.insert(bi + 1, batch[:half])
                    batches.insert(bi + 2, batch[half:])
                    logger.info(f"[remainder] batch {bi} projected {proj} credits exceeds budget; splitting (no probe)")
                    continue
                logger.warning(f"[remainder] next concept in rank order ({batch[0]['descriptor_ui']}, ~{proj} credits) "
                               f"does not fit the remaining budget; stopping in rank order")
                state["skipped_budget"].append(batch[0]["descriptor_ui"])
                REM_STATE.write_text(json.dumps(state))
                break
            st, js = await client.get("/works", {"filter": filt, "select": oa.SELECT, "per_page": PER_PAGE,
                                                 "cursor": "*"}, paid_kind="search")
            if st != 200:
                logger.error(f"[remainder] batch {bi} failed status {st}; stopping")
                break
            count = js["meta"]["count"]
            pages = -(-count // PER_PAGE)
            cost = pages * 10
            logger.info(f"[remainder] batch {bi}: {len(batch)} concepts, {count} works, {pages} pages, projected {cost} credits; spent {client.spent}")
            if client.spent + cost - 10 + CALIB_RESERVE > oa.STOP_AT:
                if len(batch) > 1 and not SPLIT_SEEN.get(bi):
                    # try again later with smaller batches: record nothing, split this batch
                    logger.warning(f"[remainder] batch {bi} too expensive for remaining budget; splitting")
                    half = len(batch) // 2
                    batches.insert(bi + 1, batch[:half])
                    batches.insert(bi + 2, batch[half:])
                    continue
                logger.warning(f"[remainder] concept {batch[0]['descriptor_ui']} too expensive ({cost}); stopping in rank order")
                state["skipped_budget"].append(batch[0]["descriptor_ui"])
                REM_STATE.write_text(json.dumps(state))
                break
            results = list(js["results"])
            cursor = js["meta"].get("next_cursor")
            while cursor and len(results) < count:
                st, js = await client.get("/works", {"filter": filt, "select": oa.SELECT, "per_page": PER_PAGE,
                                                     "cursor": cursor}, paid_kind="search")
                if st != 200:
                    logger.error(f"[remainder] paging failed in batch {bi}; batch left incomplete")
                    results = None
                    break
                if not js["results"]:
                    break
                results.extend(js["results"])
                cursor = js["meta"].get("next_cursor")
            if results is None:
                break
            uis = [r["descriptor_ui"] for r in batch]
            for w in results:
                t, a = oa.texts(w)
                fh.write(json.dumps({"batch": bi, "uis": uis, "w": oa.compact(w), "t": t, "a": a}) + "\n")
            fh.flush()
            state["done"].extend(uis)
            state["batches"].append({"batch": bi, "uis": uis, "count": count, "retrieved": len(results)})
            REM_STATE.write_text(json.dumps(state))
            logger.info(f"[remainder] batch {bi} stored {len(results)} works; spent {client.spent}")
        fh.close()
    logger.info(f"[remainder] finished; ledger total {oa.ledger_total()}")


def main() -> None:
    mode = sys.argv[1]
    max_rank = int(sys.argv[2]) if len(sys.argv) > 2 else None
    if mode in ("pubmed", "meshonly"):
        asyncio.run(run_pubmed(max_rank, mode))
    elif mode == "remainder":
        asyncio.run(run_remainder(max_rank))
    else:
        raise SystemExit(f"unknown mode {mode}")


if __name__ == "__main__":
    logger.catch(reraise=True)(main)()
