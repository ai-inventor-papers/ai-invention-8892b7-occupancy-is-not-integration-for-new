#!/usr/bin/env python3
"""Step 6a / D4: subfield x year work totals 2000-2024 in four variants (all types; typed; has_abstract;
has references), via group_by=primary_topic.subfield.id (1 credit per 200 groups). Field and domain totals
are derived by summing subfields through taxonomy.json."""
import asyncio
from datetime import date
import orjson
from loguru import logger
from common import OAClient, setup_logging, ROOT, CreditExhausted

VARIANTS = {
    "all_types": "",
    "typed_article_review_preprint_bookchapter": ",type:article|review|preprint|book-chapter",
    "has_abstract": ",has_abstract:true",
    "has_references": ",referenced_works_count:>0",
}

async def run() -> None:
    out_p = ROOT / "context" / "subfield_year_totals_raw.json"
    res = orjson.loads(out_p.read_bytes()) if out_p.exists() else {}
    async with OAClient() as oa:
        async def one(v: str, y: int):
            k = f"{v}|{y}"
            if k in res:
                return
            try:
                g = await oa.group_by_all(f"publication_year:{y}{VARIANTS[v]}", "primary_topic.subfield.id")
            except CreditExhausted as e:
                logger.warning(f"stop: {e}")
                return
            res[k] = {x["key"].rsplit("/", 1)[-1]: x["count"] for x in g}
        await asyncio.gather(*[one(v, y) for v in VARIANTS for y in range(2000, 2025)])
        out_p.write_bytes(orjson.dumps(res))
        logger.info(f"done {len(res)}/{len(VARIANTS)*25} spent_today={oa.spent_today} remaining={oa.remaining_keywide}")

@logger.catch(reraise=True)
def main() -> None:
    setup_logging("denominators")
    (ROOT / "context").mkdir(exist_ok=True)
    asyncio.run(run())

if __name__ == "__main__":
    main()
