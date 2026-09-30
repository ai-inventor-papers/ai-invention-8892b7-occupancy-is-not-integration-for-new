#!/usr/bin/env python3
"""Step 5: free novelty / early-volume pre-screen via PubMed E-utilities.

A. per descriptor: esearch (forms)[tiab] AND 1995:2024[dp], retmax=10000 -> total + all PMIDs.
   Drop total > 9,999 (above the 8k cap anyway; esearch returns at most 9,999 ids) or total < 15.
B. exact yearly counts without esummary: descriptors are packed into chunks whose summed totals
   stay < 9,999; for every chunk and year 1995..2018 one esearch (OR of chunk queries) AND Y[dp]
   returns that year's PMIDs, intersected locally with each descriptor's PMID set.
C. F = first year >= 1995 with >= 5 papers, all earlier years < 5.
   Pre-screen pass: F in 2005..2016 AND 15 <= count(F..F+2) <= 350 AND total <= 8,000.

Outputs: temp/prescreen.json (per-descriptor counts/flags), temp/pubmed_tiab_pmids.json, temp/flow_step5.json
Resumable: caches step-A results in temp/pm_stepA.jsonl and step-B in temp/pm_stepB.jsonl.
"""
from __future__ import annotations

import asyncio
import json
import resource
import sys
from collections import Counter
from pathlib import Path

import aiohttp
from loguru import logger

sys.path.insert(0, str(Path(__file__).resolve().parent))
from eutils import EUtils  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
TEMP = ROOT / "temp"
logger.remove()
logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
logger.add(ROOT / "logs" / "s02_pubmed.log", rotation="30 MB", level="DEBUG")
resource.setrlimit(resource.RLIMIT_AS, (10 * 1024**3, 10 * 1024**3))

YEARS = list(range(1995, 2019))
CHUNK_BUDGET = 9000
# Conservative prune (documented in provenance.md): PMIDs <= 14,699,652 were entered (EDAT) by 2003-12-31
# (max PMID with EDAT 2003/12/31), so their publication year is <= 2004 except for rare >12-month
# ahead-of-print cases. With dp restricted to 1995..2024, > 40 such papers imply some year 1995-2004
# has >= 5 papers (pigeonhole over 10 years), i.e. F < 2005. We use > 45 as a safety margin.
PMID_EDAT_2003_MAX = 14_699_652
PRUNE_EARLY_N = 45
LIMIT = int(sys.argv[1]) if len(sys.argv) > 1 else None
REFRESHED: set[str] = set()   # descriptors re-queried in step A during this run
import os  # noqa: E402
TAG = os.environ.get("AII_TAG", "")
SUF = f"_{TAG}" if TAG else ""


def tiab_query(forms: list[str]) -> str:
    variants: list[str] = []
    for f in forms:
        for v in {f, f.replace("-", " ")}:
            v = v.replace('"', "").strip()
            if v and v.lower() not in {x.lower() for x in variants}:
                variants.append(v)
    return "(" + " OR ".join(f'"{v}"[tiab]' for v in variants) + ")"


def first_use_year(yc: dict[int, int]) -> int | None:
    for y in YEARS:
        if yc.get(y, 0) >= 5:
            return y
    return None


def load_jsonl(p: Path) -> dict:
    out = {}
    if p.exists():
        for line in p.read_text().splitlines():
            if line.strip():
                d = json.loads(line)
                out[d["key"]] = d
    return out


async def step_a(eu: EUtils, rows: list[dict], cache_p: Path) -> dict:
    done = load_jsonl(cache_p)
    # invalidate cached entries whose query no longer matches the current surface forms
    stale = {r["descriptor_ui"] for r in rows
             if r["descriptor_ui"] in done and done[r["descriptor_ui"]]["query"] != tiab_query(r["surface_forms"])}
    if stale:
        logger.info(f"Step A: {len(stale)} cached queries are stale (surface forms changed): {sorted(stale)}")
        REFRESHED.update(stale)
        for u in stale:
            del done[u]
    todo = [r for r in rows if r["descriptor_ui"] not in done]
    logger.info(f"Step A: {len(done)} cached, {len(todo)} to query")
    fh = cache_p.open("a")

    async def one(r: dict) -> None:
        q = tiab_query(r["surface_forms"])
        res = await eu.esearch(f"{q} AND 1995:2024[dp]", retmax=10000)
        d = {"key": r["descriptor_ui"], "query": q, "total": int(res["count"]),
             "pmids": [int(x) for x in res.get("idlist", [])],
             "warnings": res.get("warninglist", {}), "translation": res.get("querytranslation", "")[:500]}
        done[d["key"]] = d
        fh.write(json.dumps(d) + "\n")

    for i in range(0, len(todo), 200):
        await asyncio.gather(*(one(r) for r in todo[i:i + 200]))
        fh.flush()
        logger.info(f"Step A progress {min(i + 200, len(todo))}/{len(todo)} calls={eu.n_calls} retries={eu.n_retries}")
    fh.close()
    return done


async def step_b(eu: EUtils, keep: list[dict], a: dict, cache_p: Path) -> dict[str, dict[int, int]]:
    done = load_jsonl(cache_p)
    # reuse complete cached chunks: a descriptor is covered when a cached chunk containing it has all years
    # and its step-A query is unchanged (the chunk's year-sets are intersected with its own PMID set)
    by_chunk: dict[str, set[int]] = {}
    for k, d in done.items():
        by_chunk.setdefault(k.split("#")[0], set()).add(d["year"])
    keep_ids = {r["descriptor_ui"] for r in keep}
    covered: dict[str, str] = {}
    for ck, yrs in by_chunk.items():
        if set(YEARS) <= yrs:
            for u in ck.split("|"):
                if u in keep_ids and u not in REFRESHED:
                    covered.setdefault(u, ck)
    chunks = sorted({ck for ck in covered.values()})
    chunks = [ck.split("|") for ck in chunks]
    new_keep = [r for r in keep if r["descriptor_ui"] not in covered]
    logger.info(f"Step B: {len(covered)} descriptors covered by {len(chunks)} cached chunks; {len(new_keep)} need new chunks")
    cur, s = [], 0
    for r in sorted(new_keep, key=lambda r: r["descriptor_ui"]):
        t = a[r["descriptor_ui"]]["total"]
        if cur and s + t > CHUNK_BUDGET:
            chunks.append(cur)
            cur, s = [], 0
        cur.append(r["descriptor_ui"])
        s += t
    if cur:
        chunks.append(cur)
    logger.info(f"Step B: {len(keep)} descriptors in {len(chunks)} chunks x {len(YEARS)} years")
    fh = cache_p.open("a")
    jobs = [(ci, y) for ci in range(len(chunks)) for y in YEARS if f"{'|'.join(chunks[ci])}#{y}" not in done]
    logger.info(f"Step B: {len(jobs)} calls remaining")

    async def one(ci: int, y: int) -> None:
        uis = chunks[ci]
        q = " OR ".join(a[u]["query"] for u in uis)
        res = await eu.esearch(f"({q}) AND {y}[dp]", retmax=10000)
        n = int(res["count"])
        if n > 9999:
            logger.error(f"chunk {ci} year {y} count {n} > 9999; counts will be truncated")
        d = {"key": f"{'|'.join(uis)}#{y}", "year": y, "count": n, "pmids": [int(x) for x in res.get("idlist", [])]}
        done[d["key"]] = d
        fh.write(json.dumps(d) + "\n")

    for i in range(0, len(jobs), 150):
        await asyncio.gather(*(one(ci, y) for ci, y in jobs[i:i + 150]))
        fh.flush()
        logger.info(f"Step B progress {min(i + 150, len(jobs))}/{len(jobs)} calls={eu.n_calls} retries={eu.n_retries}")
    fh.close()
    yearly: dict[str, dict[int, int]] = {}
    for uis in chunks:
        per_year = {y: set(done[f"{'|'.join(uis)}#{y}"]["pmids"]) for y in YEARS}
        for u in uis:
            if u not in keep_ids or u in yearly:
                continue
            ids = set(a[u]["pmids"])
            yearly[u] = {y: len(ids & per_year[y]) for y in YEARS}
    return yearly


@logger.catch(reraise=True)
async def amain() -> None:
    cands = json.loads((TEMP / f"candidates{SUF}.json").read_text())
    rows = [r for r in cands if r["provenance_class"] in ("PRIOR_IMPLICIT", "NO_PRIOR") and r["surface_forms"]]
    if LIMIT:
        rows = rows[:LIMIT]
    logger.info(f"Pre-screening {len(rows)} descriptors")
    flow = []
    async with aiohttp.ClientSession(headers={"User-Agent": "aii_mesh_pop/1.0"}) as sess:
        eu = EUtils(sess)
        a = await step_a(eu, rows, TEMP / "pm_stepA.jsonl")
        flow.append({"step": "PubMed [tiab] esearch done", "n": len(rows)})
        big = [r for r in rows if a[r["descriptor_ui"]]["total"] > 9999]
        small = [r for r in rows if a[r["descriptor_ui"]]["total"] < 15]
        keep = [r for r in rows if 15 <= a[r["descriptor_ui"]]["total"] <= 9999]
        flow.append({"step": "PubMed total 1995-2024 in 15..9,999", "n": len(keep),
                     "dropped_total_gt_9999": len(big), "dropped_total_lt_15": len(small)})
        pruned = {r["descriptor_ui"] for r in keep
                  if sum(1 for p in a[r["descriptor_ui"]]["pmids"] if p <= PMID_EDAT_2003_MAX) > PRUNE_EARLY_N}
        keep = [r for r in keep if r["descriptor_ui"] not in pruned]
        flow.append({"step": f"PMID-date prune: <= {PRUNE_EARLY_N} PMIDs entered by 2003-12-31 (else F < 2005 certain)",
                     "n": len(keep), "dropped": len(pruned)})
        logger.info(f"PMID-date prune dropped {len(pruned)}; {len(keep)} go to exact yearly counts")
        logger.info(f"After totals: keep {len(keep)} (big {len(big)}, small {len(small)})")
        yearly = await step_b(eu, keep, a, TEMP / "pm_stepB.jsonl")
        logger.info(f"E-utilities calls: {eu.n_calls}, retries {eu.n_retries}")

    out = []
    reasons = Counter()
    for r in rows:
        u = r["descriptor_ui"]
        d = {"descriptor_ui": u, "total_pubmed_1995_2024": a[u]["total"], "pubmed_query": a[u]["query"],
             "quoted_phrase_not_found": a[u]["warnings"].get("quotedphrasesnotfound", []) if isinstance(a[u]["warnings"], dict) else []}
        if u in yearly:
            yc = yearly[u]
            F = first_use_year(yc)
            early = sum(yc.get(y, 0) for y in range(F, F + 3)) if F else None
            d.update({"yearly_pubmed_1995_2018": {str(y): c for y, c in yc.items()}, "F_pubmed": F,
                      "early_pubmed_F_F2": early})
            if F is None or not (2005 <= F <= 2016):
                d["prescreen"] = "fail_F_window"
            elif not (15 <= early <= 350):
                d["prescreen"] = "fail_early_volume"
            elif a[u]["total"] > 8000:
                d["prescreen"] = "fail_total_cap"
            else:
                d["prescreen"] = "pass"
        elif a[u]["total"] > 9999 or a[u]["total"] < 15:
            d["prescreen"] = "fail_total_gt_9999" if a[u]["total"] > 9999 else "fail_total_lt_15"
        else:
            d["prescreen"] = "fail_F_window_pmid_prune"
        reasons[d["prescreen"]] += 1
        out.append(d)
    logger.info(f"Pre-screen outcomes: {dict(reasons)}")
    n_f = sum(1 for d in out if "F_pubmed" in d)
    n_fw = sum(1 for d in out if d["prescreen"] not in ("fail_total_gt_9999", "fail_total_lt_15", "fail_F_window", "fail_F_window_pmid_prune"))
    n_ev = sum(1 for d in out if d["prescreen"] in ("pass", "fail_total_cap"))
    flow.append({"step": "F (first year with >=5 PubMed papers, all earlier <5) in 2005..2016", "n": n_fw})
    flow.append({"step": "15 <= PubMed count(F..F+2) <= 350", "n": n_ev})
    flow.append({"step": "PubMed total <= 8,000 (pre-screen pass)", "n": reasons["pass"], "outcomes": dict(reasons),
                 "n_with_yearly": n_f})
    (TEMP / f"prescreen{SUF}.json").write_text(json.dumps(out, indent=1))
    keep_u = {r["descriptor_ui"] for r in rows}
    (TEMP / f"pubmed_tiab_pmids{SUF}.json").write_text(json.dumps({u: a[u]["pmids"] for u in a if u in keep_u}))
    (TEMP / f"flow_step5{SUF}.json").write_text(json.dumps(flow, indent=1))


if __name__ == "__main__":
    asyncio.run(amain())
