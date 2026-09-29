"""STEP 3: BLIND OpenAlex exposure pull (validation subsample). Reads ONLY frames/api_jobs.parquet (author id, cutoff
year, target ids; no case/control column). Pattern re-implemented from dataset_5 hyd/common.py (never imported).

Per job: GET /works?filter=author.id:A..,to_publication_date:{cutoff}-12-31,concepts.id:C..|C..
             &select=id,publication_year,concepts&per_page=200 (cursor, max 3 pages; 1 credit per page)
Per 50 authors: GET /authors?filter=id:A..|A..&select=id,works_count,counts_by_year&per_page=50 (1 credit)
Guards: own credits <= CAP and key-wide x-ratelimit-remaining >= RESERVE (checked before every paid call).
The key is read from env OPENALEX_API_KEY or dataset_5 hyd/.env and never logged or written.
"""
from __future__ import annotations

import asyncio
import gzip
import hashlib
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode

import aiohttp
import orjson
import pandas as pd
from loguru import logger

import mech_common as mc

BASE = "https://api.openalex.org"
CACHE = mc.WS / "api_cache"
LEDGER = mc.WS / "ledger.jsonl"


def api_key() -> str:
    k = os.environ.get("OPENALEX_API_KEY")
    if k:
        return k.strip()
    for line in (mc.D5 / "hyd" / ".env").read_text().splitlines():
        if line.startswith("OPENALEX_API_KEY="):
            return line.split("=", 1)[1].strip()
    raise RuntimeError("no OpenAlex key")


class Budget(RuntimeError):
    pass


class Client:
    def __init__(self, cap: int, reserve: int, conc: int = 8, rps: float = 8.0):
        self.key = api_key()
        self.cap, self.reserve = cap, reserve
        self.spent = 0
        self.remaining: int | None = None
        self.sem = asyncio.Semaphore(conc)
        self.interval = 1.0 / rps
        self.next_t = 0.0
        self.lock = asyncio.Lock()
        self.calls = {"paid": 0, "cache": 0, "free": 0}
        self.stopped = False
        CACHE.mkdir(exist_ok=True)

    async def _wait(self):
        async with self.lock:
            now = time.monotonic()
            if self.next_t > now:
                await asyncio.sleep(self.next_t - now)
            self.next_t = max(now, self.next_t) + self.interval

    @staticmethod
    def cpath(path: str, params: dict) -> Path:
        h = hashlib.sha1(f"{path}?{urlencode(sorted(params.items()))}".encode()).hexdigest()
        return CACHE / h[:2] / f"{h}.json.gz"

    def _ledger(self, path: str, credits: int):
        rec = {"ts": datetime.now(timezone.utc).isoformat(timespec="seconds"), "path": path, "credits": credits,
               "remaining_keywide": self.remaining, "spent_this_artifact": self.spent}
        with LEDGER.open("ab") as f:
            f.write(orjson.dumps(rec) + b"\n")

    async def probe(self, session: aiohttp.ClientSession) -> int | None:
        """Free singleton call to read key-wide remaining credits."""
        async with session.get(f"{BASE}/works/W2741809807", params={"api_key": self.key}) as r:
            await r.read()
            rem = r.headers.get("x-ratelimit-remaining")
            self.calls["free"] += 1
            self.remaining = int(rem) if rem is not None else None
        return self.remaining

    async def get(self, session, path: str, params: dict) -> dict | None:
        cp = self.cpath(path, params)
        if cp.exists():
            self.calls["cache"] += 1
            return orjson.loads(gzip.decompress(cp.read_bytes()))
        delay = 1.0
        for _ in range(7):
            if self.stopped or self.spent + 1 > self.cap or (self.remaining is not None and self.remaining - 1 < self.reserve):
                self.stopped = True
                raise Budget(f"guard: spent={self.spent} cap={self.cap} remaining={self.remaining} reserve={self.reserve}")
            await self._wait()
            try:
                async with self.sem:
                    async with session.get(f"{BASE}{path}", params={**params, "api_key": self.key}) as r:
                        st, hdr, body = r.status, r.headers, await r.read()
            except (aiohttp.ClientError, asyncio.TimeoutError) as ex:
                logger.debug(f"net {type(ex).__name__}; retry {delay}s")
                await asyncio.sleep(delay)
                delay = min(delay * 2, 30)
                continue
            cr = int(hdr.get("x-ratelimit-credits-used", "0") or 0)
            rem = hdr.get("x-ratelimit-remaining")
            if rem is not None:
                self.remaining = int(rem)
            if cr:
                self.spent += cr
                self._ledger(path, cr)
            if st == 200:
                self.calls["paid"] += 1
                cp.parent.mkdir(parents=True, exist_ok=True)
                cp.write_bytes(gzip.compress(body, 5))
                return orjson.loads(body)
            if st == 429 or st >= 500:
                txt = body[:200].decode(errors="replace").lower()
                if st == 429 and ("credit" in txt or "budget" in txt):
                    self.stopped = True
                    raise Budget(f"429 budget: {txt}")
                await asyncio.sleep(delay)
                delay = min(delay * 2, 30)
                continue
            logger.warning(f"HTTP {st} {path}: {body[:300]!r}")
            return {"__error__": st, "message": body[:300].decode(errors="replace")}
        return None


async def _job(cl: Client, session, j: dict, max_pages: int = 3) -> dict:
    ids = "|".join(f"C{n}" for n in j["targets"])
    filt = f"author.id:A{j['raw_author_id']},to_publication_date:{j['cutoff_year']}-12-31,concepts.id:{ids}"
    cursor, works, pages, truncated, count = "*", [], 0, False, None
    while True:
        d = await cl.get(session, "/works", {"filter": filt, "select": "id,publication_year,concepts",
                                            "per_page": 200, "cursor": cursor})
        pages += 1
        if d is None or "__error__" in d:
            return {**j, "ok": False, "error": None if d is None else d.get("message")}
        count = d["meta"]["count"]
        for w in d.get("results", []):
            works.append({"y": w.get("publication_year"),
                          "c": [(int(c["id"].rsplit("C", 1)[1]), float(c.get("score", 0))) for c in w.get("concepts", [])]})
        cursor = d["meta"].get("next_cursor")
        if not cursor or len(d.get("results", [])) < 200:
            break
        if pages >= max_pages:
            truncated = True
            break
    return {**j, "ok": True, "meta_count": count, "pages": pages, "truncated": truncated, "works": works}


async def _authors(cl: Client, session, ids: list[int]) -> list[dict]:
    d = await cl.get(session, "/authors", {"filter": "id:" + "|".join(f"A{i}" for i in ids),
                                           "select": "id,works_count,counts_by_year", "per_page": 50})
    return [] if d is None or "__error__" in d else d.get("results", [])


async def run(jobs: pd.DataFrame, cap: int, reserve: int, mini: int | None = None) -> dict:
    cl = Client(cap=cap, reserve=reserve)
    out, auth, err = [], [], None
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=90)) as session:
        rem0 = await cl.probe(session)
        logger.info(f"key-wide remaining at start: {rem0}; own cap {cap}; reserve {reserve}")
        J = jobs.to_dict("records")
        if mini:
            J = J[:mini]
        try:
            res = await asyncio.gather(*[_job(cl, session, j) for j in J], return_exceptions=True)
            for r in res:
                if isinstance(r, Budget):
                    err = str(r)
                elif isinstance(r, Exception):
                    logger.error(f"job error {r!r}")
                else:
                    out.append(r)
            ids = sorted({int(j["raw_author_id"]) for j in J})
            for i in range(0, len(ids), 50):
                auth.extend(await _authors(cl, session, ids[i:i + 50]))
        except Budget as ex:
            err = str(ex)
        rem1 = await cl.probe(session)
    logger.info(f"API: jobs ok {sum(o.get('ok', False) for o in out)}/{len(J)}; spent {cl.spent}; remaining {rem1}; "
                f"calls {cl.calls}; stop {err}")
    return {"results": out, "authors": auth, "spent": cl.spent, "remaining_start": rem0, "remaining_end": rem1,
            "calls": cl.calls, "stop_reason": err, "n_jobs": len(J)}


def pull(jobs_path: Path, cap: int, reserve: int, mini: int | None = None) -> dict:
    jobs = pd.read_parquet(jobs_path)
    assert "case" not in jobs.columns and "role" not in jobs.columns, "pull must be blind to case status"
    jobs["targets"] = jobs.targets.apply(lambda x: [int(v) for v in x])
    return asyncio.run(run(jobs, cap, reserve, mini))


def save(res: dict, path: Path) -> None:
    path.write_text(json.dumps(res, default=str))
