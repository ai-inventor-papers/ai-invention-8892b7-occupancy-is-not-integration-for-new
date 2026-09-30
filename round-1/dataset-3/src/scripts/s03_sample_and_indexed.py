#!/usr/bin/env python3
"""Step 6: outcome-blind stratified sample of pre-screen passers (seed 20260928), plus the
PubMed [MeSH Terms:noexp] indexed PMID sets (and their publication years) for the working list.

Strata: branch group x early-volume tercile (PubMed count F..F+2) x establishment period.
Allocation: proportional, floor 8 per branch group, D-branch capped at 35% of the working list.
Outputs: temp/working_list.json, temp/mesh_indexed.json, temp/flow_step6.json
"""
from __future__ import annotations

import asyncio
import json
import math
import random
import resource
import sys
from collections import Counter, defaultdict
from pathlib import Path

import aiohttp
import numpy as np
from loguru import logger

sys.path.insert(0, str(Path(__file__).resolve().parent))
from eutils import EUtils  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
TEMP = ROOT / "temp"
logger.remove()
logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
logger.add(ROOT / "logs" / "s03_sample.log", rotation="30 MB", level="DEBUG")
resource.setrlimit(resource.RLIMIT_AS, (8 * 1024**3, 8 * 1024**3))

SEED = 20260928
WORKING_N = 10_000   # all passers when there are fewer than ~260 + margin (283 in this run)
FLOOR = 8
D_CAP = 0.35
IDX_YEARS = list(range(2000, 2025))


def branch_group(b: str) -> str:
    return {"A": "A+B", "B": "A+B", "C": "C", "D": "D", "E": "E", "G": "G"}.get(b, "F+H-N")


def largest_remainder(weights: dict, total: int, caps: dict | None = None) -> dict:
    """Proportional integer allocation of `total` over keys by weight, respecting per-key caps."""
    caps = caps or {k: math.inf for k in weights}
    alloc = {k: 0 for k in weights}
    remaining = total
    while remaining > 0:
        active = [k for k in sorted(weights) if weights[k] > 0 and alloc[k] < caps[k]]
        if not active:
            break
        wsum = sum(weights[k] for k in active)
        raw = {k: remaining * weights[k] / wsum for k in active}
        add = {k: min(int(raw[k]), caps[k] - alloc[k]) for k in active}
        if sum(add.values()) == 0:
            for k in sorted(active, key=lambda k: raw[k] - int(raw[k]), reverse=True)[:remaining]:
                alloc[k] += 1
        else:
            for k, v in add.items():
                alloc[k] += v
        remaining = total - sum(alloc.values())
    return alloc


async def indexed_sets(rows: list[dict]) -> dict:
    out: dict[str, dict] = {}
    async with aiohttp.ClientSession(headers={"User-Agent": "aii_mesh_pop/1.0"}) as sess:
        eu = EUtils(sess)

        async def one(r: dict) -> None:
            term = f'"{r["preferred_term"]}"[MeSH Terms:noexp]'
            res = await eu.esearch(term, retmax=10000)
            out[r["descriptor_ui"]] = {"term": term, "count": int(res["count"]),
                                       "pmids": [int(x) for x in res.get("idlist", [])],
                                       "translation": res.get("querytranslation", "")[:300]}
        await asyncio.gather(*(one(r) for r in rows))
        logger.info(f"indexed sets fetched: {len(out)}; calls {eu.n_calls}")
        # yearly counts of indexed PMIDs via chunk x year intersections
        chunks, cur, s = [], [], 0
        for r in rows:
            t = min(out[r["descriptor_ui"]]["count"], 9999)
            if cur and s + t > 9000:
                chunks.append(cur)
                cur, s = [], 0
            cur.append(r)
            s += t
        if cur:
            chunks.append(cur)
        year_sets: dict[tuple[int, int], set[int]] = {}

        async def yq(ci: int, y: int) -> None:
            q = " OR ".join(out[r["descriptor_ui"]]["term"] for r in chunks[ci])
            res = await eu.esearch(f"({q}) AND {y}[dp]", retmax=10000)
            year_sets[(ci, y)] = {int(x) for x in res.get("idlist", [])}
        jobs = [(ci, y) for ci in range(len(chunks)) for y in IDX_YEARS]
        logger.info(f"indexed yearly: {len(chunks)} chunks x {len(IDX_YEARS)} years = {len(jobs)} calls")
        for i in range(0, len(jobs), 150):
            await asyncio.gather(*(yq(ci, y) for ci, y in jobs[i:i + 150]))
        for ci, ch in enumerate(chunks):
            for r in ch:
                ids = set(out[r["descriptor_ui"]]["pmids"])
                pm_year = {}
                for y in IDX_YEARS:
                    for p in ids & year_sets[(ci, y)]:
                        pm_year[p] = y
                out[r["descriptor_ui"]]["pmid_year"] = {str(p): y for p, y in pm_year.items()}
                out[r["descriptor_ui"]]["yearly"] = {str(y): sum(1 for v in pm_year.values() if v == y) for y in IDX_YEARS}
        logger.info(f"E-utilities calls total {eu.n_calls}, retries {eu.n_retries}")
    return out


@logger.catch(reraise=True)
def main() -> None:
    cands = {r["descriptor_ui"]: r for r in json.loads((TEMP / "candidates.json").read_text())}
    pre = json.loads((TEMP / "prescreen.json").read_text())
    passers = []
    for d in pre:
        if d["prescreen"] != "pass":
            continue
        r = dict(cands[d["descriptor_ui"]])
        r.update({k: d[k] for k in ("total_pubmed_1995_2024", "F_pubmed", "early_pubmed_F_F2", "yearly_pubmed_1995_2018",
                                    "pubmed_query", "quoted_phrase_not_found")})
        r["branch_group"] = branch_group(r["tree_branch_primary"])
        r["period"] = "2006-2010" if r["mesh_year_established"] <= 2010 else "2011-2016"
        passers.append(r)
    logger.info(f"Pre-screen passers: {len(passers)}")
    ev = np.array([r["early_pubmed_F_F2"] for r in passers])
    t1, t2 = np.quantile(ev, [1 / 3, 2 / 3])
    for r in passers:
        r["volume_tercile"] = "T1_low" if r["early_pubmed_F_F2"] <= t1 else ("T2_mid" if r["early_pubmed_F_F2"] <= t2 else "T3_high")
        r["stratum"] = f"{r['branch_group']}|{r['volume_tercile']}|{r['period']}"
    n_work = min(WORKING_N, len(passers))
    gsize = Counter(r["branch_group"] for r in passers)
    # branch-group allocation: floor, D cap, proportional remainder
    floors = {g: min(FLOOR, n) for g, n in gsize.items()}
    caps = {g: (int(D_CAP * n_work) if g == "D" else n) for g, n in gsize.items()}
    caps = {g: min(caps[g], gsize[g]) for g in caps}
    rest = n_work - sum(floors.values())
    extra = largest_remainder({g: max(gsize[g] - floors[g], 0) for g in gsize}, rest,
                              {g: caps[g] - floors[g] for g in gsize})
    g_alloc = {g: floors[g] + extra.get(g, 0) for g in gsize}
    logger.info(f"Branch-group sizes {dict(gsize)} -> allocation {g_alloc}")
    rng = random.Random(SEED)
    selected = []
    strata_info = {}
    for g in sorted(gsize):
        members = [r for r in passers if r["branch_group"] == g]
        ssize = Counter(r["stratum"] for r in members)
        s_alloc = largest_remainder(dict(ssize), g_alloc[g], dict(ssize))
        for s in sorted(ssize):
            pool = sorted([r for r in members if r["stratum"] == s], key=lambda r: r["descriptor_ui"])
            rng.shuffle(pool)
            k = s_alloc.get(s, 0)
            strata_info[s] = {"N": ssize[s], "n": k}
            for r in pool[:k]:
                r["selection_prob"] = round(k / ssize[s], 6)
                selected.append(r)
    keys = {r["descriptor_ui"]: rng.random() for r in selected}
    selected.sort(key=lambda r: keys[r["descriptor_ui"]])
    for i, r in enumerate(selected, 1):
        r["sample_rank"] = i
        r["selection_seed"] = SEED
    logger.info(f"Working list: {len(selected)}; groups {Counter(r['branch_group'] for r in selected)}")
    (TEMP / "working_list.json").write_text(json.dumps(selected, indent=1))
    flow = [{"step": "stratified outcome-blind working list (seed 20260928)", "n": len(selected),
             "passers": len(passers), "tercile_cuts_pubmed_early": [float(t1), float(t2)],
             "branch_group_sizes": dict(gsize), "branch_group_allocation": g_alloc, "strata": strata_info}]
    (TEMP / "flow_step6.json").write_text(json.dumps(flow, indent=1))
    logger.info("working list written; fetching MeSH-indexed PMID sets")
    idx = asyncio.run(indexed_sets(selected))
    (TEMP / "mesh_indexed.json").write_text(json.dumps(idx))


if __name__ == "__main__":
    main()
