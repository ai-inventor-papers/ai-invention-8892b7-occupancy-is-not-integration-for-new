#!/usr/bin/env python3
"""Step 7: RECALL AUDIT on 30 included main concepts (stratified by F-band x volume tercile, uniform within strata).
 - Route A concepts (OpenAlex-native ids): cross-check against Semantic Scholar bulk search (free): per-year ratio
   of our verified counts to S2 index hits, Spearman rho of the yearly series.
 - Route B concepts (S2 discovery): cross-check against OpenAlex-native group_by=publication_year (1 credit each),
   if credits remain.
Also reports, for every included route-A concept, the verification pass rate (verified / OpenAlex search hits).
Output: context/recall_audit.json"""
import asyncio
import random
from collections import Counter, defaultdict

import aiohttp
import numpy as np
import orjson
from loguru import logger
from scipy.stats import spearmanr

from common import OAClient, CreditExhausted, ROOT, oa_query, setup_logging
from hydrate import S2, discover_s2

YEARS = list(range(2000, 2025))


async def run() -> None:
    d = orjson.loads((ROOT / "data_out.json").read_bytes())
    ex = [e for e in d["datasets"][0]["examples"] if e["metadata_arm"] == "main"]
    exA = [e for e in ex if e["metadata_retrieval_route"] == "A_openalex_native"]
    by = defaultdict(list)
    for e in sorted(ex, key=lambda z: z["metadata_concept_id"]):
        by[(e["metadata_F_band"], e["metadata_volume_tercile"])].append(e)
    rng = random.Random(20260928)
    k = len(by)
    pick = []
    per = max(1, 30 // max(k, 1))
    for s in sorted(by):
        pick += rng.sample(by[s], min(per, len(by[s])))
    rest = [e for e in ex if e not in pick]
    pick += rng.sample(rest, max(0, min(30 - len(pick), len(rest))))
    frame = orjson.loads((ROOT / "sample_frame_frozen.json").read_bytes())
    fr = {x["concept_id"]: x for x in frame["eligible"]}
    res = []
    async with OAClient() as oa, aiohttp.ClientSession() as sess:
        s2 = S2()
        s2.session = sess
        for e in pick:
            cid = e["metadata_concept_id"]
            out = orjson.loads(e["output"])
            ours = {int(y): n for y, n in out["oa_counts_by_year"].items()}
            # OpenAlex credits were exhausted key-wide, so every audited concept is compared with the S2 index:
            # route A -> independent index; route B -> measures S2->OpenAlex mapping + local-verification loss.
            st = orjson.loads((ROOT / "retrieval" / f"{cid}.json").read_bytes())
            if e["metadata_retrieval_route"] == "B_s2_index":
                hits = st["discovery"]["s2_hits"]
            else:
                hits = (await discover_s2(s2, fr[cid])).get("s2_hits", [])
            ref = Counter(int(h["year"]) for h in hits if h.get("year") and 2000 <= int(h["year"]) <= 2024)
            ref_name = "s2_index_hits"
            a = np.array([ours.get(y, 0) for y in YEARS], float)
            b = np.array([ref.get(y, 0) for y in YEARS], float)
            rho = spearmanr(a, b).correlation if a.std() > 0 and b.std() > 0 else None
            ratio_total = float(a.sum() / b.sum()) if b.sum() else None
            res.append({"concept_id": cid, "phrase": e["metadata_phrase"], "route": e["metadata_retrieval_route"],
                        "reference": ref_name, "ours_total": int(a.sum()), "reference_total": int(b.sum()),
                        "ratio_total": round(ratio_total, 4) if ratio_total is not None else None,
                        "spearman_yearly": round(float(rho), 4) if rho is not None and not np.isnan(rho) else None,
                        "per_year_ratio": {str(y): (round(float(a[i] / b[i]), 3) if b[i] else None) for i, y in enumerate(YEARS)},
                        "flag_ratio_lt_0.5": bool(ratio_total is not None and ratio_total < 0.5)})
            logger.info(f"audit {e['metadata_phrase']!r}: ours={int(a.sum())} ref={int(b.sum())} rho={rho}")
    ratios = [r["ratio_total"] for r in res if r["ratio_total"] is not None]
    rhos = [r["spearman_yearly"] for r in res if r["spearman_yearly"] is not None]
    # verification pass rate for route-A concepts
    pass_rates = []
    for e in ex:
        if e["metadata_retrieval_route"] == "A_openalex_native":
            st = orjson.loads((ROOT / "retrieval" / f"{e['metadata_concept_id']}.json").read_bytes())
            if st.get("n_candidates"):
                pass_rates.append(len(st["links"]) / st["n_candidates"])
    summary = {"n_audited": len(res), "median_ratio_total": float(np.median(ratios)) if ratios else None,
               "iqr_ratio_total": [float(np.percentile(ratios, 25)), float(np.percentile(ratios, 75))] if ratios else None,
               "median_spearman_yearly": float(np.median(rhos)) if rhos else None,
               "n_flag_ratio_lt_0.5": sum(r["flag_ratio_lt_0.5"] for r in res),
               "stated_expectation": "ratio 0.7-1.1 vs OpenAlex-native; vs S2 index the ratio also reflects "
                                     "index coverage differences (S2 vs OpenAlex) and S2 phrase-matching looseness",
               "routeA_verification_pass_rate_median": float(np.median(pass_rates)) if pass_rates else None,
               "routeA_verification_pass_rate_p10": float(np.percentile(pass_rates, 10)) if pass_rates else None,
               "s2_calls": s2.n_calls, "s2_429": s2.n_429}
    (ROOT / "context" / "recall_audit.json").write_bytes(orjson.dumps({"summary": summary, "concepts": res},
                                                                       option=orjson.OPT_INDENT_2))
    logger.info(orjson.dumps(summary).decode())


@logger.catch(reraise=True)
def main() -> None:
    setup_logging("audit")
    asyncio.run(run())


if __name__ == "__main__":
    main()
