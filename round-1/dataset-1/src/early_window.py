#!/usr/bin/env python3
"""Step 2 (cont.): EARLY-WINDOW hydration for every ELIGIBLE candidate (outcome-blind: years F..F+2 only).
Per candidate: group_by=ids.openalex over title_and_abstract.search:"<phrase>",publication_year:F-(F+2)
(1 credit per 200 ids), then FREE singleton hydration of those works, local surface-form verification,
origin field/subfield from verified c-papers, and year-F titles for the LLM sense check.
Output: screen/early_window.jsonl"""
import asyncio
import random
from collections import Counter

import orjson
from loguru import logger

from common import OAClient, CreditExhausted, ROOT, oa_query, setup_logging, verify_regex
from hydrate_lib import Store, hydrate_ids

SCREEN = ROOT / "screen" / "screen_results.jsonl"
OUT = ROOT / "screen" / "early_window.jsonl"


def load_taxonomy() -> dict:
    return orjson.loads((ROOT / "taxonomy.json").read_bytes())


async def run() -> None:
    tax = load_taxonomy()
    sf_name = {int(k): v for k, v in tax["subfields"].items()}
    f_name = {int(k): v for k, v in tax["fields"].items()}
    rows = [orjson.loads(x) for x in SCREEN.read_text().splitlines() if x.strip()]
    elig = [r for r in rows if r["status"] == "ELIGIBLE"]
    done = {orjson.loads(x)["concept_id"] for x in OUT.read_text().splitlines()} if OUT.exists() else set()
    todo = [r for r in elig if r["concept_id"] not in done]
    logger.info(f"{len(elig)} eligible; {len(todo)} to process")
    store = Store()
    async with OAClient() as oa:
        sem = asyncio.Semaphore(8)

        async def one(r: dict) -> None:
            F = r["F"]
            async with sem:
                try:
                    groups = await oa.group_by_all(
                        f"title_and_abstract.search:{oa_query(r['phrase'])},publication_year:{F}-{F + 2}", "ids.openalex")
                except CreditExhausted as e:
                    logger.warning(f"credit stop {e}")
                    return
                ids = [int(g["key"].rsplit("/W", 1)[-1]) for g in groups if "/W" in g["key"]]
                await hydrate_ids(oa, store, ids)
            recs = store.get_many(ids)
            rx = verify_regex(r["phrase"])
            ver, sf, fld, yF_titles = [], Counter(), Counter(), []
            for wid in ids:
                w = recs.get(wid)
                if not w:
                    continue
                ev = "oa_title" if rx.search(w["title"] or "") else ("oa_abstract" if rx.search(w["text"]) else None)
                if ev is None and not w["has_abstract"]:
                    ev = "oa_search_only_no_abstract"
                if ev is None:
                    continue
                ver.append(wid)
                if w.get("subfield_id"):
                    sf[w["subfield_id"]] += 1
                if w.get("field_id"):
                    fld[w["field_id"]] += 1
                if w.get("publication_year") == F and w["title"]:
                    yF_titles.append(w["title"][:250])
            random.Random(r["concept_id"]).shuffle(yF_titles)
            n_top = sum(sf.values())
            rec = {"concept_id": r["concept_id"], "phrase": r["phrase"], "F": F, "V": r["V"],
                   "early_ids_n": len(ids), "early_hydrated_n": len(recs), "early_oa_verified_count": len(ver),
                   "early_verified_ids": ver,
                   "origin_subfield": ({"id": sf.most_common(1)[0][0], "name": sf_name.get(sf.most_common(1)[0][0]),
                                        "share": round(sf.most_common(1)[0][1] / n_top, 4)} if sf else None),
                   "origin_field": ({"id": fld.most_common(1)[0][0], "name": f_name.get(fld.most_common(1)[0][0]),
                                     "share": round(fld.most_common(1)[0][1] / sum(fld.values()), 4)} if fld else None),
                   "yearF_titles": yF_titles[:20]}
            with OUT.open("ab") as f:
                f.write(orjson.dumps(rec) + b"\n")

        await asyncio.gather(*[one(r) for r in todo])
        logger.info(f"early window done; spent_today={oa.spent_today} remaining={oa.remaining_keywide} "
                    f"store={store.count()} calls={oa.n_calls}")


@logger.catch(reraise=True)
def main() -> None:
    setup_logging("early_window")
    asyncio.run(run())


if __name__ == "__main__":
    main()
