#!/usr/bin/env python3
"""Step 1b (outcome-blind pre-filter): per-keyword and per-legacy-concept counts of works TAGGED in
1995-2004, via cursor-paged group_by (1 credit / 200 groups). Uses only pre-2005 information."""
import asyncio
import sys
from pathlib import Path
import orjson
from loguru import logger
from common import OAClient, setup_logging, ROOT

async def run(key: str, out: Path) -> None:
    async with OAClient() as oa:
        groups = await oa.group_by_all("publication_year:1995-2004", key)
        counts = {g["key"].rsplit("/", 1)[-1]: g["count"] for g in groups}
        out.write_bytes(orjson.dumps(counts))
        logger.info(f"{key}: {len(counts)} groups, spent_today={oa.spent_today}, remaining={oa.remaining_keywide}")

@logger.catch(reraise=True)
def main() -> None:
    setup_logging("prefilter")
    (ROOT / "vocab").mkdir(exist_ok=True)
    which = sys.argv[1]
    key = {"keywords": "keywords.id", "concepts": "concepts.id"}[which]
    asyncio.run(run(key, ROOT / "vocab" / f"pre2005_tag_counts_{which}.json"))

if __name__ == "__main__":
    main()
