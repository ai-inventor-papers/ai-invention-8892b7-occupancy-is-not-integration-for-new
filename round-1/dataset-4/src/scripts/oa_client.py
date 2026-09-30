#!/usr/bin/env python3
"""Single caching, budget-aware async OpenAlex client shared by every script.

- Every response is cached on disk under cache/openalex/<sha1(url without key)>.json
  together with the URL and the query date, so nothing is paid twice.
- The API key is read from the env var OPENALEX_API_KEY and is never written anywhere.
- X-RateLimit headers are appended to logs/openalex_spend.csv.
- A hard floor on the key's remaining daily credits (default 2,500 credits = $0.25,
  left for the sibling artifacts sharing the key) and a per-artifact credit cap stop
  new paid calls.
"""
from __future__ import annotations

import asyncio
import csv
import hashlib
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode

import aiohttp
from loguru import logger

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "cache" / "openalex"
CACHE.mkdir(parents=True, exist_ok=True)
SPEND_LOG = ROOT / "logs" / "openalex_spend.csv"
SPEND_LOG.parent.mkdir(parents=True, exist_ok=True)
BASE = "https://api.openalex.org"


class BudgetExhausted(RuntimeError):
    pass


class OAClient:
    def __init__(self, *, concurrency: int = 8, rps: float = 9.0,
                 floor_credits: int = 2500, artifact_cap_credits: int = 6000) -> None:
        self.key = os.environ["OPENALEX_API_KEY"]
        self.sem = asyncio.Semaphore(concurrency)
        self.min_interval = 1.0 / rps
        self._last = 0.0
        self._lock = asyncio.Lock()
        self.floor = floor_credits
        self.cap = artifact_cap_credits
        self.remaining: int | None = None
        self.session: aiohttp.ClientSession | None = None
        self.paid_calls = 0
        self.cache_hits = 0
        self.credits_spent = self._spent_so_far()
        self.stopped = False

    @staticmethod
    def _spent_so_far() -> int:
        if not SPEND_LOG.exists():
            return 0
        tot = 0
        with SPEND_LOG.open() as f:
            for row in csv.DictReader(f):
                try:
                    tot += int(row.get("credits_used") or 0)
                except ValueError:
                    pass
        return tot

    async def __aenter__(self) -> "OAClient":
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=120),
            headers={"User-Agent": "aii-emerging-concepts/0.1 (mailto:adrian.m.grobelnik@ijs.si)"})
        return self

    async def __aexit__(self, *a) -> None:
        if self.session:
            await self.session.close()

    @staticmethod
    def build_url(path: str, params: dict) -> str:
        return f"{BASE}{path}?{urlencode(params, safe=':,|\"*')}"

    @staticmethod
    def cache_path(url: str) -> Path:
        return CACHE / (hashlib.sha1(url.encode()).hexdigest() + ".json")

    def cached(self, path: str, params: dict) -> dict | None:
        p = self.cache_path(self.build_url(path, params))
        if p.exists():
            return json.loads(p.read_text())["response"]
        return None

    async def _throttle(self) -> None:
        async with self._lock:
            wait = self._last + self.min_interval - time.monotonic()
            if wait > 0:
                await asyncio.sleep(wait)
            self._last = time.monotonic()

    def _log_spend(self, url: str, h: dict) -> None:
        new = not SPEND_LOG.exists()
        with SPEND_LOG.open("a", newline="") as f:
            w = csv.writer(f)
            if new:
                w.writerow(["ts", "url", "credits_used", "cost_usd", "key_remaining_credits", "key_remaining_usd"])
            w.writerow([datetime.now(timezone.utc).isoformat(), url[:400],
                        h.get("x-ratelimit-credits-used", ""), h.get("x-ratelimit-cost-usd", ""),
                        h.get("x-ratelimit-remaining", ""), h.get("x-ratelimit-remaining-usd", "")])

    async def get(self, path: str, params: dict) -> dict:
        url = self.build_url(path, params)
        cp = self.cache_path(url)
        if cp.exists():
            self.cache_hits += 1
            return json.loads(cp.read_text())["response"]
        async with self.sem:
            if cp.exists():
                self.cache_hits += 1
                return json.loads(cp.read_text())["response"]
            if self.stopped:
                raise BudgetExhausted("stopped")
            if self.remaining is not None and self.remaining < self.floor:
                self.stopped = True
                raise BudgetExhausted(f"key remaining {self.remaining} < floor {self.floor}")
            if self.credits_spent >= self.cap:
                self.stopped = True
                raise BudgetExhausted(f"artifact cap {self.cap} credits reached")
            full = f"{url}&api_key={self.key}"
            delay = 2.0
            for attempt in range(6):
                await self._throttle()
                try:
                    assert self.session is not None
                    async with self.session.get(full) as r:
                        h = {k.lower(): v for k, v in r.headers.items()}
                        txt = await r.text()
                        if r.status == 200:
                            data = json.loads(txt)
                            cu = int(h.get("x-ratelimit-credits-used", "1") or 1)
                            self.credits_spent += cu
                            self.paid_calls += 1
                            if h.get("x-ratelimit-remaining"):
                                self.remaining = int(h["x-ratelimit-remaining"])
                            self._log_spend(url, h)
                            cp.write_text(json.dumps({"url": url, "query_date": datetime.now(timezone.utc).isoformat(),
                                                      "response": data}))
                            return data
                        if r.status in (429, 500, 502, 503, 504):
                            if r.status == 429 and "budget" in txt.lower():
                                self.stopped = True
                                raise BudgetExhausted(txt[:200])
                            logger.warning(f"HTTP {r.status} attempt {attempt}: {txt[:150]}")
                            await asyncio.sleep(delay)
                            delay *= 2
                            continue
                        raise RuntimeError(f"HTTP {r.status}: {txt[:300]} for {url[:200]}")
                except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                    logger.warning(f"net error {e!r} attempt {attempt}")
                    await asyncio.sleep(delay)
                    delay *= 2
            raise RuntimeError(f"failed after retries: {url[:200]}")
