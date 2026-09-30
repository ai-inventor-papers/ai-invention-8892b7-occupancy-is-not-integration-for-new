"""Minimal async NCBI E-utilities client with a global request-rate limiter and retries."""
from __future__ import annotations

import asyncio
import json
import os
import random
import time

import aiohttp
from loguru import logger

EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
TOOL = "aii_mesh_pop"
NCBI_KEY = os.environ.get("NCBI_API_KEY")
# NCBI allows 3 req/s without a key (10/s with). Stay slightly under.
MIN_INTERVAL = 0.105 if NCBI_KEY else 0.45


class EUtils:
    def __init__(self, session: aiohttp.ClientSession, concurrency: int = 3) -> None:
        self.session = session
        self.sem = asyncio.Semaphore(concurrency)
        self._lock = asyncio.Lock()
        self._last = 0.0
        self.n_calls = 0
        self.n_retries = 0

    async def _tick(self) -> None:
        async with self._lock:
            wait = self._last + MIN_INTERVAL - time.monotonic()
            if wait > 0:
                await asyncio.sleep(wait)
            self._last = time.monotonic()

    async def esearch(self, term: str, retmax: int = 0, extra: dict | None = None) -> dict:
        data = {"db": "pubmed", "term": term, "retmax": str(retmax), "retmode": "json", "tool": TOOL}
        if NCBI_KEY:
            data["api_key"] = NCBI_KEY
        if extra:
            data.update(extra)
        for attempt in range(8):
            async with self.sem:
                await self._tick()
                self.n_calls += 1
                try:
                    async with self.session.post(f"{EUTILS}/esearch.fcgi", data=data,
                                                 timeout=aiohttp.ClientTimeout(total=120)) as r:
                        txt = await r.text()
                        if r.status == 200:
                            js = json.loads(txt)
                            res = js.get("esearchresult")
                            if res is not None and "ERROR" not in res:
                                return res
                            logger.warning(f"esearch bad payload: {txt[:200]}")
                        else:
                            logger.warning(f"esearch HTTP {r.status}: {txt[:150]}")
                except (aiohttp.ClientError, asyncio.TimeoutError, json.JSONDecodeError) as e:
                    logger.warning(f"esearch error {type(e).__name__}: {str(e)[:120]}")
            self.n_retries += 1
            await asyncio.sleep(min(60, 2 ** attempt + random.random()))
        raise RuntimeError(f"esearch failed after retries: {term[:200]}")
