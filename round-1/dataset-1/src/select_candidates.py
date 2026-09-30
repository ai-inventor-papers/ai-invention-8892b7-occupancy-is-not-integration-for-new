#!/usr/bin/env python3
"""Step 1 (cont.): walk the seeded random order of the cleaned vocabulary, run the strictly LINGUISTIC LLM
genericity screen in batches of 60, and emit candidates until quotas are met (no arm > 60%).
Also emits a reference-arm candidate list: stop-list-passing phrases the tag pre-filter flagged as pre-existing
(random order, same seed).

Usage: python select_candidates.py <n_main> <n_ref>"""
import asyncio
import sys

import orjson
import pandas as pd
from loguru import logger

from common import ROOT, setup_logging, surface_forms
from llm_utils import LLM, BudgetStop

SYSTEM = ("You are a terminology annotator. For each English phrase decide, purely linguistically: "
          "is_specific_technical_term = true if the phrase names a specific technical/scientific notion, method, "
          "material, entity class or phenomenon (not a generic everyday or broad academic expression); "
          "has_multiple_unrelated_senses = true if the exact phrase is commonly used with two or more unrelated "
          "meanings; is_named_entity = true if it is a person, place, country, organisation, product brand or "
          "journal name. Return ONLY a JSON array of objects {\"phrase\",\"is_specific_technical_term\","
          "\"has_multiple_unrelated_senses\",\"is_named_entity\"}, one per input phrase, same order.")
ARMS = ["openalex_keyword", "legacy_concept", "mesh_new_descriptor"]


async def screen_batch(llm: LLM, phrases: list[str]) -> dict[str, dict]:
    res = await llm.json_call(SYSTEM, "\n".join(phrases))
    out = {}
    if isinstance(res, list):
        for r in res:
            if isinstance(r, dict) and "phrase" in r:
                out[str(r["phrase"]).strip().lower()] = r
    return out


async def run(n_main: int, n_ref: int) -> None:
    df = pd.read_parquet(ROOT / "vocab" / "vocab_clean.parquet")
    main_pool = df[df.stop_reason.isna() & df.prefilter_reason.isna()].sort_values("rand_order")
    ref_pool = df[df.stop_reason.isna() & df.prefilter_reason.notna()].sort_values("rand_order")
    llm = LLM(ROOT / "vocab" / "llm_cost.json")
    cache_p = ROOT / "vocab" / "llm_genericity.jsonl"
    cache = {}
    if cache_p.exists():
        for line in cache_p.read_text().splitlines():
            r = orjson.loads(line)
            cache[r["phrase"]] = r

    async def ensure(phrases: list[str]) -> None:
        need = [p for p in phrases if p not in cache]
        batches = [need[i:i + 60] for i in range(0, len(need), 60)]
        results = await asyncio.gather(*[screen_batch(llm, b) for b in batches], return_exceptions=True)
        with cache_p.open("ab") as f:
            for b, res in zip(batches, results):
                if isinstance(res, BaseException):
                    logger.warning(f"batch failed: {res}")
                    continue
                for p in b:
                    r = res.get(p)
                    rec = {"phrase": p, "llm_screen": r is not None,
                           "is_specific": bool(r.get("is_specific_technical_term", True)) if r else True,
                           "multi_sense": bool(r.get("has_multiple_unrelated_senses", False)) if r else False,
                           "named_entity": bool(r.get("is_named_entity", False)) if r else False}
                    cache[p] = rec
                    f.write(orjson.dumps(rec) + b"\n")

    def pick(pool: pd.DataFrame, n: int, arm_cap: float | None) -> list[dict]:
        chosen, arm_counts = [], {a: 0 for a in ARMS}
        for _, r in pool.iterrows():
            g = cache.get(r.phrase)
            if g is None or not g["is_specific"] or g["named_entity"]:
                continue
            arms = list(r.vocab_arms)
            prim = "mesh_new_descriptor" if "mesh_new_descriptor" in arms else arms[0]
            if arm_cap is not None and arm_counts[prim] + 1 > arm_cap * n:
                continue
            arm_counts[prim] += 1
            forms = set(surface_forms(r.phrase))
            chosen.append({"concept_id": r.concept_id, "phrase": r.phrase, "surface_forms": sorted(forms),
                           "acronyms": list(r.acronyms), "vocab_arms": arms, "primary_arm": prim,
                           "links": orjson.loads(r.links), "labels": list(r.labels),
                           "pre2005_tag_counts": orjson.loads(r.pre2005_tag_counts),
                           "llm_screen": g["llm_screen"], "multi_sense_flag": g["multi_sense"],
                           "rand_order": int(r.rand_order)})
            if len(chosen) >= n:
                break
        return chosen

    # screen in growing chunks of the random order until quotas can be filled
    step = 600
    k = 0
    main_sel: list[dict] = []
    try:
        while True:
            k += step
            await ensure(list(main_pool.phrase.iloc[:k]))
            main_sel = pick(main_pool.iloc[:k], n_main, 0.6)
            logger.info(f"walked {k}: {len(main_sel)} main candidates; llm cost ${llm.cost:.4f}")
            if len(main_sel) >= n_main or k >= len(main_pool):
                break
        await ensure(list(ref_pool.phrase.iloc[: int(n_ref * 1.6)]))
    except BudgetStop as e:
        logger.warning(f"OpenRouter budget stop - deterministic stop-list only for the rest: {e}")
    ref_sel = pick(ref_pool.iloc[: int(n_ref * 1.6)], n_ref, None)
    for fn, sel in [("candidates_main.jsonl", main_sel), ("candidates_ref.jsonl", ref_sel)]:
        (ROOT / "vocab" / fn).write_bytes(b"".join(orjson.dumps(x) + b"\n" for x in sel))
    shares = pd.Series([x["primary_arm"] for x in main_sel]).value_counts().to_dict()
    logger.info(f"main={len(main_sel)} arm shares={shares} ref={len(ref_sel)} llm_cost=${llm.cost:.4f}")


@logger.catch(reraise=True)
def main() -> None:
    setup_logging("select_candidates")
    asyncio.run(run(int(sys.argv[1]), int(sys.argv[2])))


if __name__ == "__main__":
    main()
