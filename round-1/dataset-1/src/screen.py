#!/usr/bin/env python3
"""Step 2: OUTCOME-BLIND first-use screening on OpenAlex (Route A screening; 1 credit per candidate).

One call per candidate: filter=title_and_abstract.search:"<phrase>",publication_year:1995-2018
&group_by=publication_year. The response's meta.count and every year > F+2 are discarded IMMEDIATELY inside
`truncate_and_classify`; nothing downstream of that function ever sees them. Only years <= F+2 (or <= 2004 for
pre-existing candidates, <= 2016 for no-onset) are written to screen/screen_results.jsonl.

Usage: python screen.py <candidates.jsonl> <arm_tag> [max_n]
"""
import asyncio
import sys
from pathlib import Path

import orjson
from loguru import logger

from common import OAClient, CreditExhausted, ROOT, oa_query, setup_logging

OUT = ROOT / "screen" / "screen_results.jsonl"


def truncate_and_classify(groups: list[dict]) -> dict:
    """Apply the pre-registered first-use rules. Returns only outcome-blind information."""
    n = {int(g["key"]): int(g["count"]) for g in groups if str(g["key"]).isdigit()}
    get = lambda y: n.get(y, 0)  # noqa: E731
    pre = sum(get(y) for y in range(1995, 2005))
    if pre > 15 or any(get(y) >= 5 for y in range(1995, 2005)):
        ref_ok = all(get(y) >= 5 for y in range(1998, 2005)) and 70 <= sum(get(y) for y in range(1998, 2005)) <= 700
        return {"status": "REJECT_PREEXISTING", "counts": {y: get(y) for y in range(1995, 2005)},
                "reference_eligible": ref_ok}
    F = None
    for y in range(2005, 2017):
        if get(y) >= 5 and all(get(z) < 5 for z in range(1995, y)) and sum(get(z) for z in range(1995, y)) <= 15:
            F = y
            break
        if get(y) >= 5:  # first >=5 year but pre-F sum > 15 -> not a clean onset
            return {"status": "REJECT_DIFFUSE_ONSET", "counts": {z: get(z) for z in range(1995, y + 1)}}
    if F is None:
        return {"status": "REJECT_NO_ONSET", "counts": {y: get(y) for y in range(1995, 2017)}}
    counts = {y: get(y) for y in range(1995, F + 3)}  # <= F+2 only
    V = get(F) + get(F + 1) + get(F + 2)
    burst = get(F) >= 50 and get(F) > 10 * max(get(F - 1), 1)
    status = "ELIGIBLE" if 20 <= V <= 300 else ("REJECT_LOW_VOLUME" if V < 20 else "REJECT_HIGH_VOLUME")
    return {"status": status, "F": F, "V": V, "burst_start": bool(burst), "counts": counts}


async def run(cands: list[dict], arm_tag: str) -> None:
    done = set()
    if OUT.exists():
        for line in OUT.read_text().splitlines():
            done.add(orjson.loads(line)["concept_id"])
    todo = [c for c in cands if c["concept_id"] not in done]
    logger.info(f"{len(todo)} candidates to screen ({len(done)} already screened)")
    stop = asyncio.Event()
    async with OAClient() as oa:
        sem = asyncio.Semaphore(6)

        async def one(c: dict) -> None:
            if stop.is_set():
                return
            async with sem:
                if stop.is_set():
                    return
                try:
                    d = await oa.get("/works", {"filter": f"title_and_abstract.search:{oa_query(c['phrase'])},"
                                                          f"publication_year:1995-2018",
                                                "group_by": "publication_year"})
                except CreditExhausted as e:
                    logger.warning(f"credit stop: {e}")
                    stop.set()
                    return
            if d is None or "__error__" in d:
                rec = {"concept_id": c["concept_id"], "phrase": c["phrase"], "arm_tag": arm_tag, "status": "ERROR",
                       "error": (d or {}).get("message", "none")[:200]}
            else:
                res = truncate_and_classify(d.get("group_by", []))
                del d  # outcome-bearing payload dropped here
                rec = {"concept_id": c["concept_id"], "phrase": c["phrase"], "arm_tag": arm_tag, **res}
            with OUT.open("ab") as f:
                f.write(orjson.dumps(rec, option=orjson.OPT_NON_STR_KEYS) + b"\n")

        await asyncio.gather(*[one(c) for c in todo])
        logger.info(f"screen done; spent_today={oa.spent_today} remaining={oa.remaining_keywide}")


@logger.catch(reraise=True)
def main() -> None:
    setup_logging("screen")
    OUT.parent.mkdir(exist_ok=True)
    cands = [orjson.loads(x) for x in Path(sys.argv[1]).read_text().splitlines() if x.strip()]
    if len(sys.argv) > 3:
        cands = cands[: int(sys.argv[3])]
    asyncio.run(run(cands, sys.argv[2]))


if __name__ == "__main__":
    main()
