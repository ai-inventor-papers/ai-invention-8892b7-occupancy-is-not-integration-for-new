#!/usr/bin/env python3
"""LLM genericity/well-formedness screen (strictly linguistic) of the arXiv-mined arm; writes
vocab/arxiv_candidates.jsonl in the seeded random order."""
import asyncio
import orjson
import pandas as pd
from loguru import logger
from common import ROOT, setup_logging, surface_forms
from llm_utils import LLM, BudgetStop

SYSTEM = ("You are a terminology annotator. For each English phrase decide, purely linguistically: "
          "is_well_formed_term = true if it is a complete noun phrase that could stand alone as a term (not a "
          "truncated fragment such as 'temperatures over the last' or 'critical nonlinear schr'); "
          "is_specific_technical_term = true if it names a specific technical/scientific notion, method, material, "
          "object class or phenomenon (not a generic expression); has_multiple_unrelated_senses; is_named_entity = "
          "true if it is a person, place, organisation, instrument/mission/experiment/survey name, conference or "
          "dataset name. Return ONLY a JSON array of objects {\"phrase\",\"is_well_formed_term\","
          "\"is_specific_technical_term\",\"has_multiple_unrelated_senses\",\"is_named_entity\"}, same order.")

async def run() -> None:
    df = pd.read_parquet(ROOT / "vocab" / "arxiv_mined.parquet").sort_values("rand_order")
    llm = LLM(ROOT / "vocab" / "llm_cost_arxiv.json")
    phrases = list(df.phrase)
    batches = [phrases[i:i + 60] for i in range(0, len(phrases), 60)]
    res = await asyncio.gather(*[llm.json_call(SYSTEM, "\n".join(b)) for b in batches], return_exceptions=True)
    lab = {}
    for b, r in zip(batches, res):
        if isinstance(r, BaseException) or not isinstance(r, list):
            logger.warning(f"batch failed: {r if isinstance(r, BaseException) else 'bad json'}")
            continue
        for x in r:
            if isinstance(x, dict) and "phrase" in x:
                lab[str(x["phrase"]).strip().lower()] = x
    out = []
    n_fail = 0
    for _, r in df.iterrows():
        x = lab.get(r.phrase)
        if x is None:
            n_fail += 1
            continue
        if not (x.get("is_well_formed_term") and x.get("is_specific_technical_term")) or x.get("is_named_entity"):
            continue
        out.append({"concept_id": r.concept_id, "phrase": r.phrase, "surface_forms": surface_forms(r.phrase),
                    "acronyms": [], "vocab_arms": ["arxiv_mined"], "primary_arm": "arxiv_mined", "links": {},
                    "labels": [r.phrase], "llm_screen": True,
                    "multi_sense_flag": bool(x.get("has_multiple_unrelated_senses")),
                    "arxiv_Y0": int(r.arxiv_Y0), "arxiv_early_titles": int(r.arxiv_early_titles),
                    "rand_order": int(r.rand_order)})
    (ROOT / "vocab" / "arxiv_candidates.jsonl").write_bytes(b"".join(orjson.dumps(o) + b"\n" for o in out))
    logger.info(f"arxiv candidates kept {len(out)} / {len(df)} (unlabelled {n_fail}); llm cost ${llm.cost:.4f}")

@logger.catch(reraise=True)
def main() -> None:
    setup_logging("select_arxiv")
    asyncio.run(run())

if __name__ == "__main__":
    main()
