#!/usr/bin/env python3
"""S7: yearly OpenAlex counts for pool candidates, eligibility under the early-window anchor rule,
linking, inclusion weights; writes data_out/pool_early.json and data_out/pool_outcomes_SEALED.json.

Counts use filter=title_and_abstract.search.exact:"<surface>" (unstemmed phrase search; the API has
no .no_stem variant). The label-blind audit arm additionally gets the stemmed title_and_abstract.search
count, stored separately, to quantify stemming effects. Billing was verified on one call: list price.

Usage: python s7_counts.py [--max-calls N]
"""
from __future__ import annotations

import argparse
import asyncio
import json
import random
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

from loguru import logger

sys.path.insert(0, str(Path(__file__).resolve().parent))
from oa_client import OAClient, BudgetExhausted, ROOT  # noqa: E402
from linking import Linker, wikidata_lookup  # noqa: E402
from rawio import load_pickle  # noqa: E402

logger.remove()
logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
logger.add(ROOT / "logs" / "s7_counts.log", rotation="30 MB", level="DEBUG")
SEED = 20260928
YEARS = list(range(1980, 2027))
OUT = ROOT / "data_out"
OUT.mkdir(exist_ok=True)


def safe_phrase(s: str) -> str | None:
    s = re.sub(r"[\"(),:;|\[\]{}]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s if len(s) >= 3 and re.search(r"[A-Za-z]{2}", s) else None


def year_vector(resp: dict) -> dict[int, int]:
    v = {}
    for g in resp.get("group_by", []):
        try:
            y = int(g["key"])
        except (ValueError, TypeError):
            continue
        v[y] = g["count"]
    return v


def eligibility(v: dict[int, int], sample_years: list[int]) -> dict:
    F = next((y for y in range(1990, 2027) if v.get(y, 0) >= 3), None)
    if F is None:
        return {"F": None, "eligible": False, "anchor_ok": False, "reason": "never >=3 papers/yr", "tier": "not_eligible"}
    n_early = sum(v.get(y, 0) for y in range(F, F + 3))
    pre = sum(c for y, c in v.items() if y < F)
    reasons = []
    if not (2005 <= F <= 2016):
        reasons.append("F outside 2005-2016")
    if not (20 <= n_early <= 300):
        reasons.append("n_early outside [20,300]")
    if pre > max(2, 0.05 * n_early):
        reasons.append("pre-F papers above novelty threshold")
    anchor_ok = any(F <= y <= F + 2 for y in sample_years)
    base = not reasons
    novel = pre <= max(2, 0.05 * n_early)
    # tiers: strict = plan rule; relaxed_plan = plan fallback (F 2004-2017, n_early <= 500);
    # relaxed_low_volume = exploratory (n_early >= 5), reported because strict yield is ~0.1%.
    # The novelty rule and the anchor rule are never relaxed.
    if base:
        tier = "strict"
    elif novel and 2004 <= F <= 2017 and 20 <= n_early <= 500:
        tier = "relaxed_plan"
    elif novel and 2004 <= F <= 2017 and 5 <= n_early <= 500:
        tier = "relaxed_low_volume"
    else:
        tier = "not_eligible"
    return {"F": F, "n_early": n_early, "pre_F": pre, "eligible_except_anchor": base, "tier": tier,
            "anchor_ok": anchor_ok, "eligible": base and anchor_ok, "reason": "; ".join(reasons) or ("ok" if anchor_ok else "anchor rule failed")}


def inclusion_weight(v: dict[int, int], F: int, field_id: int, rates: dict) -> float | None:
    prod = 1.0
    for y in range(F, F + 3):
        r = rates.get((field_id, y))
        if r is None:
            continue
        prod *= (1 - r) ** v.get(y, 0)
    p = 1 - prod
    return round(1 / p, 3) if p > 0 else None


async def main(max_calls: int) -> None:
    items = json.loads((ROOT / "labelling" / "items.json").read_text())
    AB = json.loads((ROOT / "labelling" / "labels_AB.json").read_text())
    C = load_pickle("candidates")
    meta = load_pickle("docs_meta")["meta"]
    strata = json.loads((ROOT / "raw" / "strata.json").read_text())["strata"]
    rates = {(s["field_id"], s["year"]): s["sampling_rate"] for s in strata if s["corpus"] == "main" and s["sampling_rate"]}
    P = [k for k, v in items.items() if v["track"] == "P"]
    audit = sorted(k for k in P if items[k].get("audit_arm"))
    llm_arm = sorted(k for k in P if not items[k].get("audit_arm") and
                     (AB["A"].get(k, {}).get("label") == "CONCEPT" or AB["B"].get(k, {}).get("label") == "CONCEPT"))
    rng = random.Random(SEED)
    rng.shuffle(llm_arm)
    order = audit + llm_arm
    logger.info(f"pool candidates: audit={len(audit)} LLM-CONCEPT(A or B)={len(llm_arm)}")
    order = order[:max_calls]

    def surface_for(k: str) -> str | None:
        it = items[k]
        # acronyms: the long form (the key itself is the long-form key); otherwise the most frequent surface
        for s in it["surface_forms"] + [k]:
            sp = safe_phrase(s)
            if sp and len(sp.split()) >= 1:
                return sp
        return None

    counts: dict[str, dict] = {}
    async with OAClient(artifact_cap_credits=6000, floor_credits=2500) as oa:
        async def one(k: str):
            s = surface_for(k)
            if not s:
                counts[k] = {"error": "no queryable surface"}
                return
            try:
                r = await oa.get("/works", {"filter": f'title_and_abstract.search.exact:"{s}"', "group_by": "publication_year"})
                v = year_vector(r)
                rec = {"surface_queried": s, "query": "title_and_abstract.search.exact", "vector": v, "retry_flag": False}
                if sum(v.values()) == 0:
                    r2 = await oa.get("/works", {"filter": f"title_and_abstract.search:{s}", "group_by": "publication_year"})
                    rec.update({"vector": year_vector(r2), "query": "title_and_abstract.search (unquoted, stemmed) retry",
                                "retry_flag": True})
                if items[k].get("audit_arm"):
                    r3 = await oa.get("/works", {"filter": f'title_and_abstract.search:"{s}"', "group_by": "publication_year"})
                    rec["vector_stemmed_quoted"] = year_vector(r3)
                counts[k] = rec
            except BudgetExhausted as e:
                counts[k] = {"error": f"budget: {e}"}
            except RuntimeError as e:
                counts[k] = {"error": str(e)[:200]}

        await asyncio.gather(*[one(k) for k in order])
        logger.info(f"counts done: paid={oa.paid_calls} cached={oa.cache_hits} spent_total_credits={oa.credits_spent} key_remaining={oa.remaining}")

    query_date = datetime.now(timezone.utc).date().isoformat()
    linker = Linker()
    rows, sealed = [], {}
    for k in order:
        c = counts.get(k, {})
        if "vector" not in c:
            continue
        v = {int(y): n for y, n in c["vector"].items()}
        docs = C["docs_by_key"][k]
        sample_years = [meta[d]["year"] for d in docs if meta[d]["corpus"] == "main"]
        fld = Counter(meta[d]["field_id"] for d in docs).most_common(1)[0][0]
        el = eligibility(v, sample_years)
        rows.append({"key": k, "counts": c, "el": el, "field_id": fld, "sample_years": sample_years})
        sealed[k] = {"surface_queried": c["surface_queried"], "query": c["query"],
                     "yearly_counts_1980_2026": {y: v.get(y, 0) for y in YEARS},
                     "yearly_counts_stemmed_quoted": ({y: c["vector_stemmed_quoted"].get(str(y), c["vector_stemmed_quoted"].get(y, 0)) for y in YEARS}
                                                      if c.get("vector_stemmed_quoted") else None),
                     "partial_years_right_censored": [2025, 2026], "query_date": query_date}
    # linking (strings only), Wikidata for CONCEPT phrases with no match elsewhere
    links = {r["key"]: linker.link(r["key"], items[r["key"]]["surface_forms"]) for r in rows}
    need_wd = [k for k, l in links.items() if not any(l.values())]
    logger.info(f"Wikidata lookups for {len(need_wd)} unlinked phrases")
    wd = await wikidata_lookup(need_wd)
    pool = []
    for r in rows:
        k, el = r["key"], r["el"]
        it = items[k]
        l = links[k]
        l["wikidata"] = wd.get(k)
        status = ("LINKED_KEYWORD" if l["keyword"] else "LINKED_CONCEPT" if l["concept"] else
                  "LINKED_WIKIDATA" if l["wikidata"] else "LINKED_MESH" if l["mesh"] else "UNLINKED")
        v = {int(y): n for y, n in r["counts"]["vector"].items()}
        F = el.get("F")
        early = {y: v.get(y, 0) for y in range(1980, min(F + 3, 2027))} if F else {}
        pool.append({
            "key": k, "surface_forms": it["surface_forms"], "acronym_short_forms": it.get("acronym_short_forms", []),
            "surface_queried": r["counts"]["surface_queried"], "count_query": r["counts"]["query"],
            "count_retry_flag": r["counts"]["retry_flag"],
            "label_A": AB["A"].get(k, {}).get("label"), "label_B": AB["B"].get(k, {}).get("label"),
            "audit_arm": bool(it.get("audit_arm")), "macro_domain": it["stats"]["macro_domain"],
            "origin_field_id": r["field_id"], "first_sample_year": it["stats"]["first_main_year"],
            "sample_occurrence_years": sorted(r["sample_years"]), "n_sample_occ": it["stats"]["n_occ"],
            "cvalue": it["stats"]["cvalue"],
            "F": F, "counts_up_to_F_plus_2": early, "n_early": el.get("n_early"), "pre_F": el.get("pre_F"),
            "eligible": el["eligible"], "eligible_except_anchor": el.get("eligible_except_anchor", False),
            "anchor_ok": el["anchor_ok"], "eligibility_reason": el["reason"],
            "eligibility_tier": el.get("tier", "not_eligible"),
            "relaxed": el.get("tier") in ("relaxed_plan", "relaxed_low_volume"),
            "inclusion_weight": inclusion_weight(v, F, r["field_id"], rates) if el.get("tier", "not_eligible") != "not_eligible" else None,
            "link_status": status, "links": l, "snippets": it["snippets"],
        })
    (OUT / "pool_early.json").write_text(json.dumps(pool, ensure_ascii=False))
    (OUT / "pool_outcomes_SEALED.json").write_text(json.dumps(sealed))
    n_el = sum(p["eligible"] for p in pool)
    logger.info(f"pool rows {len(pool)}; eligible {n_el} (audit {sum(p['eligible'] and p['audit_arm'] for p in pool)}); "
                f"link status {Counter(p['link_status'] for p in pool)}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-calls", type=int, default=1500)
    a = ap.parse_args()
    asyncio.run(main(a.max_calls))
