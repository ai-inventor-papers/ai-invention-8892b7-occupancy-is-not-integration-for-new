#!/usr/bin/env python3
"""S8: outcome-blind, pre-registered subsample of eligible pool phrases; download all their works.

Step 1 (selection) reads ONLY data_out/pool_early.json (never the sealed outcome file) and writes
subsample/selection_protocol.json with the stratification, seed and a random priority order.
Step 2 (budgeting only) reads total counts from the sealed file to estimate API calls per phrase,
and takes phrases in the pre-registered order until the budget or 150 phrases is reached.
Step 3 downloads works (cursor paging, per_page=200) with filter title_and_abstract.search.exact,
1990-2024; phrases with <50 total works are OR-batched (<=10 per query) and assigned locally by
exact surface match. Abstract text is used for exact_surface_in_text and then dropped.

Usage: python s8_works.py [--budget-credits N] [--max-phrases 150] [--resume]
"""
from __future__ import annotations

import argparse
import asyncio
import json
import random
import re
import sys
from collections import defaultdict
from pathlib import Path

from loguru import logger

sys.path.insert(0, str(Path(__file__).resolve().parent))
from oa_client import OAClient, BudgetExhausted, ROOT  # noqa: E402
from s1_fetch_corpus import rebuild_abstract  # noqa: E402

logger.remove()
logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
logger.add(ROOT / "logs" / "s8_works.log", rotation="30 MB", level="DEBUG")
SEED = 20260929
SELECT = ("id,doi,display_name,publication_year,publication_date,primary_topic,primary_location,"
          "referenced_works,authorships,keywords,abstract_inverted_index")
SUB = ROOT / "subsample"
SUB.mkdir(exist_ok=True)


def tercile(x: int, cuts: list[int]) -> str:
    return "T1" if x <= cuts[0] else "T2" if x <= cuts[1] else "T3"


def n_band(n: int) -> str:
    return "20-50" if n <= 50 else "51-120" if n <= 120 else "121-300"


def select() -> list[dict]:
    pool = json.loads((ROOT / "data_out" / "pool_early.json").read_text())  # ONLY early information
    tiers = ["strict", "relaxed_plan", "relaxed_low_volume"]
    el = sorted([p for p in pool if p["eligibility_tier"] in tiers and p["anchor_ok"]],
                key=lambda p: (tiers.index(p["eligibility_tier"]), p["key"]))
    Fs = sorted(p["F"] for p in el)
    cuts = [Fs[len(Fs) // 3], Fs[2 * len(Fs) // 3]] if Fs else [2008, 2012]
    rng = random.Random(SEED)
    strata = defaultdict(list)
    for p in el:
        strata[(p["macro_domain"], tercile(p["F"], cuts), n_band(p["n_early"]))].append(p["key"])
    # random priority order, interleaving strata round-robin so any prefix is roughly stratum-balanced
    for v in strata.values():
        rng.shuffle(v)
    keys_s = sorted(strata)
    rng.shuffle(keys_s)
    order = []
    while any(strata[s] for s in keys_s):
        for s in keys_s:
            if strata[s]:
                order.append(strata[s].pop(0))
    # strict-tier phrases first, then relaxed tiers; random order inside each tier
    tier_of = {p["key"]: tiers.index(p["eligibility_tier"]) for p in el}
    order = sorted(order, key=lambda k: tier_of[k])
    proto = {"seed": SEED, "stratification": "macro_domain x F tercile x n_early band [<=50, 51-120, 121+]; tiers strict > relaxed_plan > relaxed_low_volume",
             "F_tercile_cuts": cuts, "n_eligible_anchor_ok": len(el), "priority_order": order,
             "note": "Selection read only pool_early.json. Truncating this random order keeps the sample random."}
    (SUB / "selection_protocol.json").write_text(json.dumps(proto, indent=1))
    return [p for p in el]


def norm_text(s: str) -> str:
    s = s.lower()
    s = re.sub(r"[‐-―−\-/]+", " ", s)
    return re.sub(r"\s+", " ", s)


async def main(budget: int, max_phrases: int) -> None:
    pool = {p["key"]: p for p in select()}
    order = json.loads((SUB / "selection_protocol.json").read_text())["priority_order"]
    sealed = json.loads((ROOT / "data_out" / "pool_outcomes_SEALED.json").read_text())  # budgeting ONLY
    plan, used = [], 0
    for k in order:
        v = sealed[k]["yearly_counts_1980_2026"]
        tot = sum(int(c) for y, c in v.items() if 1990 <= int(y) <= 2024)
        F = pool[k]["F"]
        trunc = tot > 3000
        n_dl = sum(int(c) for y, c in v.items() if 1990 <= int(y) <= min(2024, F + 8)) if trunc else tot
        calls = 0 if tot < 50 else (n_dl // 200 + 1)
        if used + calls + 1 > budget:
            break
        plan.append({"key": k, "total_1990_2024": tot, "truncated": trunc, "calls_est": calls})
        used += calls
        if len(plan) >= max_phrases:
            break
    small = [p for p in plan if p["total_1990_2024"] < 50]
    used += (len(small) + 9) // 10 * 2
    logger.info(f"S8 plan: {len(plan)} phrases, est credits {used} (budget {budget}); OR-batched small={len(small)}")
    (SUB / "download_plan.json").write_text(json.dumps(plan, indent=1))

    works: dict[str, dict] = {}
    assign: dict[str, set] = defaultdict(set)
    status: dict[str, str] = {}
    async with OAClient(artifact_cap_credits=6000, floor_credits=2500) as oa:
        async def pages(filt: str, max_pages: int = 60) -> list[dict] | None:
            out, cursor = [], "*"
            for _ in range(max_pages):
                try:
                    r = await oa.get("/works", {"filter": filt, "per_page": 200, "cursor": cursor, "select": SELECT})
                except BudgetExhausted as e:
                    logger.error(f"budget stop: {e}")
                    return None
                out.extend(r.get("results", []))
                cursor = (r.get("meta") or {}).get("next_cursor")
                if not cursor or not r.get("results"):
                    break
            return out

        async def big(p: dict):
            k = p["key"]
            s = pool[k]["surface_queried"]
            F = pool[k]["F"]
            y1 = min(2024, F + 8) if p["truncated"] else 2024
            res = await pages(f'title_and_abstract.search.exact:"{s}",publication_year:1990-{y1}')
            if res is None:
                status[k] = "budget_stopped"
                return
            for w in res:
                works.setdefault(w["id"], w)
                assign[w["id"]].add(k)
            status[k] = "complete_through_F+8_truncated" if p["truncated"] else "complete"

        async def small_batch(group: list[dict]):
            surf = {pool[p["key"]]["surface_queried"]: p["key"] for p in group}
            ors = "|".join(f'"{s}"' for s in surf)
            res = await pages(f"title_and_abstract.search.exact:{ors},publication_year:1990-2024")
            if res is None:
                for p in group:
                    status[p["key"]] = "budget_stopped"
                return
            for w in res:
                txt = norm_text((w.get("display_name") or "") + " " + rebuild_abstract(w.get("abstract_inverted_index")))
                hit = [k for s, k in surf.items() if norm_text(s) in txt]
                if not hit:  # search matched (e.g. tokenisation differences); keep under every candidate? no: unassigned
                    hit = [k for s, k in surf.items() if all(t in txt for t in norm_text(s).split())]
                for k in hit:
                    works.setdefault(w["id"], w)
                    assign[w["id"]].add(k)
            for p in group:
                status[p["key"]] = "complete_or_batched"

        bigs = [p for p in plan if p["total_1990_2024"] >= 50]
        smalls = [p for p in plan if p["total_1990_2024"] < 50]
        await asyncio.gather(*[big(p) for p in bigs], *[small_batch(smalls[i:i + 10]) for i in range(0, len(smalls), 10)])
        logger.info(f"downloaded {len(works)} works; paid={oa.paid_calls} cached={oa.cache_hits} key_remaining={oa.remaining}")

    rows = []
    prec = defaultdict(lambda: [0, 0])
    for wid, w in works.items():
        abstract = rebuild_abstract(w.get("abstract_inverted_index"))
        txt = norm_text((w.get("display_name") or "") + " " + abstract)
        pt = w.get("primary_topic") or {}
        loc = (w.get("primary_location") or {}).get("source") or {}
        for k in sorted(assign[wid]):
            exact = norm_text(pool[k]["surface_queried"]) in txt
            prec[k][0] += int(exact)
            prec[k][1] += 1
            rows.append({
                "input": w.get("display_name") or "", "output": k,
                "metadata_fold": "heldout_phrase", "metadata_work_id": wid.rsplit("/", 1)[-1], "metadata_doi": w.get("doi"),
                "metadata_publication_year": w.get("publication_year"), "metadata_publication_date": w.get("publication_date"),
                "metadata_field_id": ((pt.get("field") or {}).get("id") or "").rsplit("/", 1)[-1] or None,
                "metadata_field": (pt.get("field") or {}).get("display_name"),
                "metadata_subfield_id": ((pt.get("subfield") or {}).get("id") or "").rsplit("/", 1)[-1] or None,
                "metadata_subfield": (pt.get("subfield") or {}).get("display_name"),
                "metadata_topic_id": (pt.get("id") or "").rsplit("/", 1)[-1] or None,
                "metadata_domain": (pt.get("domain") or {}).get("display_name"),
                "metadata_venue_id": (loc.get("id") or "").rsplit("/", 1)[-1] or None,
                "metadata_referenced_works": [r.rsplit("/", 1)[-1] for r in (w.get("referenced_works") or [])],
                "metadata_author_ids": [((a.get("author") or {}).get("id") or "").rsplit("/", 1)[-1] for a in (w.get("authorships") or [])][:50],
                "metadata_institution_ids": sorted({(i.get("id") or "").rsplit("/", 1)[-1] for a in (w.get("authorships") or [])
                                                     for i in (a.get("institutions") or []) if i.get("id")})[:50],
                "metadata_keywords": [x.get("display_name") for x in (w.get("keywords") or [])],
                "metadata_has_abstract": bool(abstract), "metadata_exact_surface_in_text": exact,
                "metadata_phrase_surface_queried": pool[k]["surface_queried"],
                "metadata_phrase_F": pool[k]["F"],
            })
    per_phrase = {}
    for p in plan:
        k = p["key"]
        a, n = prec.get(k, [0, 0])
        sp = round(a / n, 4) if n else None
        per_phrase[k] = {"n_works": n, "search_precision_exact_surface": sp,
                         "low_precision": bool(sp is not None and sp < 0.7), "truncated": p["truncated"],
                         "status": status.get(k, "not_fetched")}
    (SUB / "heldout_works_rows.json").write_text(json.dumps(rows, ensure_ascii=False))
    (SUB / "per_phrase_download_report.json").write_text(json.dumps(per_phrase, indent=1))
    logger.info(f"rows {len(rows)} for {sum(1 for v in per_phrase.values() if v['n_works'])} phrases")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--budget-credits", type=int, default=1500)
    ap.add_argument("--max-phrases", type=int, default=150)
    ap.add_argument("--resume", action="store_true", help="re-run; everything already fetched comes from cache/openalex")
    a = ap.parse_args()
    asyncio.run(main(a.budget_credits, a.max_phrases))
