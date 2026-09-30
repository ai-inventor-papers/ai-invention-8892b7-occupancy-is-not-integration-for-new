#!/usr/bin/env python3
"""Equivalence check for the credit-priced batch hydration path (plan STEP 1(1)).

Takes 200 work ids already in the store (random, seeded), fetches them (a) through the batch list path
/works?filter=ids.openalex:W..|..&per_page=100&select=<SELECT> (2 credits) and (b) through free singletons, and
compares compact() records field by field (ignoring retrieved_at and retrieval_batch). Writes
hyd/probes/batch_equivalence.json with pass=true only if every returned record is identical and
abstract_inverted_index was honoured on the list endpoint. The running hydrate.py reads this flag before every
hydrate_ids call, so the batch path switches on without a restart.
"""
from __future__ import annotations

import asyncio
import os
import random
import sys
import time
from pathlib import Path

import orjson
from loguru import logger

ROOT = Path(__file__).resolve().parent
HYD = ROOT / "hyd"
sys.path.insert(0, str(HYD))
os.environ.setdefault("AII_STEP", "p1_batch_equivalence")
from common import OAClient  # noqa: E402
from hydrate_lib import SELECT, Store, compact, list_truncated  # noqa: E402

IGNORE = {"retrieved_at", "retrieval_batch"}


@logger.catch(reraise=True)
def main() -> None:
    logger.remove()
    logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
    logger.add(ROOT / "logs" / "batch_equivalence.log", level="DEBUG")
    store = Store(HYD / "work_store")
    ids = []
    for con in store.shards:
        ids += [r[0] for r in con.execute("SELECT id FROM works ORDER BY id LIMIT 3000")]
    random.Random(20260929).shuffle(ids)
    ids = ids[:200]
    res = asyncio.run(run(ids))
    (HYD / "probes").mkdir(exist_ok=True)
    (HYD / "probes" / "batch_equivalence.json").write_bytes(orjson.dumps(res, option=orjson.OPT_INDENT_2))
    (ROOT / "probes").mkdir(exist_ok=True)
    (ROOT / "probes" / "batch_equivalence.json").write_bytes(orjson.dumps(res, option=orjson.OPT_INDENT_2))
    logger.info({k: v for k, v in res.items() if k != "mismatch_examples"})


async def run(ids: list[int]) -> dict:
    async with OAClient(cap=int(os.environ.get("AII_ARTIFACT_CAP", "20"))) as oa:
        batch = {}
        truncated: list[int] = []
        for i in range(0, len(ids), 100):
            ch = ids[i:i + 100]
            d = await oa.get("/works", {"filter": "ids.openalex:" + "|".join(f"W{x}" for x in ch), "per_page": 100,
                                        "select": SELECT}, kind="list", use_cache=False)
            if d is None or "__error__" in d:
                return {"pass": False, "reason": f"batch call failed: {d}", "utc": _now()}
            for w in d.get("results", []):
                r = compact(w, batch="iter2_batch")
                if list_truncated(w):
                    truncated.append(r["work_id"])  # production path re-fetches these as singletons
                    continue
                batch[r["work_id"]] = r
        single = {}

        async def one(x: int) -> None:
            d = await oa.get(f"/works/W{x}", {"select": SELECT}, kind="singleton", use_cache=False)
            if d and "__error__" not in d:
                single[x] = compact(d)
        await asyncio.gather(*[one(x) for x in ids])
    both = [x for x in ids if x in batch and x in single]
    mism = []
    for x in both:
        a = {k: v for k, v in batch[x].items() if k not in IGNORE}
        b = {k: v for k, v in single[x].items() if k not in IGNORE}
        if a != b:
            diff = [k for k in set(a) | set(b) if a.get(k) != b.get(k)]
            mism.append({"work_id": x, "fields": diff})
    abstracts = sum(1 for x in both if batch[x]["has_abstract"])
    abstracts_single = sum(1 for x in both if single[x]["has_abstract"])
    ok = len(both) + len(truncated) >= 190 and not mism and abstracts == abstracts_single
    return {"pass": ok, "attempt": 2, "attempt1": "2026-09-29T00:01:11Z fail: 1/200 mismatch (W1544516929 "
            "author_ids/institution_ids/author_positions: list endpoint truncates authorships at 100)", "n_ids": len(ids), "n_batch_returned": len(batch), "n_singleton_returned": len(single),
            "n_compared": len(both), "n_mismatch": len(mism), "mismatch_examples": mism[:20],
            "abstracts_batch": abstracts, "abstracts_singleton": abstracts_single,
            "not_returned_by_batch": [x for x in ids if x not in batch and x not in truncated][:50],
            "authorships_ge_100_rerouted_to_singleton": truncated, "credits": 2, "utc": _now(),
            "rule": "identical compact() records apart from retrieved_at/retrieval_batch; abstract_inverted_index "
                    "honoured on the list endpoint"}


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


if __name__ == "__main__":
    main()
