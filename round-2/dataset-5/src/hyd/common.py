#!/usr/bin/env python3
"""Shared helpers: OpenAlex async client with credit ledger, gzip response cache, rate limiting,
hard credit guard; phrase normalisation; logging setup."""
from __future__ import annotations

import asyncio
import gzip
import hashlib
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode

import aiohttp
import orjson
from loguru import logger

ROOT = Path(__file__).resolve().parent
RAW = ROOT / "raw_cache"
LEDGER = ROOT / "credit_ledger.jsonl"
BASE = "https://api.openalex.org"

# ---- credit policy (see README) ----
ARTIFACT_CAP = int(os.environ.get("AII_ARTIFACT_CAP", "4000"))  # credits this artifact may spend per UTC day
HARD_GUARD_REMAINING = 1500  # stop list/search calls when key-wide remaining falls below this
SINGLETON_RPS = float(os.environ.get("AII_SINGLETON_RPS", "18"))
LIST_RPS = 4.0


def setup_logging(name: str) -> None:
    (ROOT / "logs").mkdir(exist_ok=True)
    logger.remove()
    logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
    logger.add(ROOT / "logs" / f"{name}.log", rotation="30 MB", level="DEBUG")


def api_key() -> str:
    for line in (ROOT / ".env").read_text().splitlines():
        if line.startswith("OPENALEX_API_KEY="):
            return line.split("=", 1)[1].strip()
    raise RuntimeError("OPENALEX_API_KEY missing in .env")


def ledger_total(day: str | None = None) -> int:
    """Credits spent by this artifact (optionally on one UTC day)."""
    if not LEDGER.exists():
        return 0
    tot = 0
    for line in LEDGER.read_text().splitlines():
        if not line.strip():
            continue
        r = orjson.loads(line)
        if day is None or r["ts"][:10] == day:
            tot += int(r.get("credits", 0))
    return tot


class CreditExhausted(RuntimeError):
    pass


class RateLimiter:
    def __init__(self, rps: float) -> None:
        self.interval = 1.0 / rps
        self.next_t = 0.0
        self.lock = asyncio.Lock()

    async def wait(self) -> None:
        async with self.lock:
            now = time.monotonic()
            if self.next_t > now:
                await asyncio.sleep(self.next_t - now)
            self.next_t = max(now, self.next_t) + self.interval


class OAClient:
    """Async OpenAlex client. kind='singleton' is free; kind='list' costs credits (read from headers)."""

    def __init__(self, cap: int = ARTIFACT_CAP, singleton_rps: float = SINGLETON_RPS) -> None:
        self.key = api_key()
        self.cap = cap
        self.day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        self.spent_today = ledger_total(self.day)
        self.remaining_keywide: int | None = None
        self.lim_single = RateLimiter(singleton_rps)
        self.lim_list = RateLimiter(LIST_RPS)
        self.sem = asyncio.Semaphore(32)
        self.session: aiohttp.ClientSession | None = None
        self.stopped = False
        self.n_calls = {"singleton": 0, "list": 0, "cache": 0}
        RAW.mkdir(exist_ok=True)

    async def __aenter__(self) -> "OAClient":
        self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=90),
                                             connector=aiohttp.TCPConnector(limit=40))
        return self

    async def __aexit__(self, *a) -> None:
        if self.session:
            await self.session.close()

    @staticmethod
    def cache_path(path: str, params: dict) -> Path:
        q = urlencode(sorted(params.items()))
        h = hashlib.sha1(f"{path}?{q}".encode()).hexdigest()
        return RAW / h[:2] / f"{h}.json.gz"

    def _rollover(self) -> None:
        """iter2: the key resets at 00:00 UTC. After a day change, lift a budget stop and re-read today's spend."""
        day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if day != self.day:
            logger.info(f"UTC day changed {self.day} -> {day}: lifting stop, re-reading ledger")
            self.day = day
            self.stopped = False
            self.spent_today = ledger_total(day)
            self.remaining_keywide = None

    def can_spend(self, credits: int = 1) -> bool:
        self._rollover()
        if self.stopped:
            return False
        if self.spent_today + credits > self.cap:
            return False
        if self.remaining_keywide is not None and self.remaining_keywide < HARD_GUARD_REMAINING:
            return False
        return True

    def _ledger(self, kind: str, path: str, credits: int, remaining: int | None) -> None:
        rec = {"ts": datetime.now(timezone.utc).isoformat(timespec="seconds"), "endpoint_class": kind,
               "path": path.split("?")[0][:60], "credits": credits, "remaining": remaining,
               "step": os.environ.get("AII_STEP", "unspecified")}
        with LEDGER.open("ab") as f:
            f.write(orjson.dumps(rec) + b"\n")

    async def get(self, path: str, params: dict | None = None, kind: str = "list",
                  use_cache: bool = True) -> dict | None:
        """GET path with params. Returns parsed JSON, or None on 404. Raises CreditExhausted for list
        calls when the cap/guard is hit."""
        params = dict(params or {})
        cp = self.cache_path(path, params)
        if use_cache and cp.exists():
            self.n_calls["cache"] += 1
            return orjson.loads(gzip.decompress(cp.read_bytes()))
        if kind == "list" and not self.can_spend(1):
            self.stopped = True
            raise CreditExhausted(f"cap/guard reached: spent_today={self.spent_today} cap={self.cap} "
                                  f"remaining_keywide={self.remaining_keywide}")
        url = f"{BASE}{path}"
        qp = dict(params)
        qp["api_key"] = self.key
        delay = 1.0
        for attempt in range(9):
            await (self.lim_list if kind == "list" else self.lim_single).wait()
            try:
                async with self.sem:
                    async with self.session.get(url, params=qp) as r:
                        status = r.status
                        hdr = r.headers
                        body = await r.read()
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                logger.debug(f"net error {type(e).__name__} on {path}; retry in {delay}s")
                await asyncio.sleep(delay)
                delay = min(delay * 2, 60)
                continue
            credits = int(hdr.get("x-ratelimit-credits-used", "0") or 0)
            rem = hdr.get("x-ratelimit-remaining")
            if rem is not None:
                try:
                    self.remaining_keywide = int(rem)
                except ValueError:
                    pass
            if credits:
                self.spent_today += credits
                self._ledger(kind, path, credits, self.remaining_keywide)
            self.n_calls[kind] += 1
            tot = self.n_calls["singleton"] + self.n_calls["list"]
            if tot % 500 == 0:
                logger.info(f"[keywide] calls={self.n_calls} remaining_keywide={self.remaining_keywide} "
                            f"spent_today(artifact,this proc)={self.spent_today}")
            if status == 200:
                data = orjson.loads(body)
                cp.parent.mkdir(parents=True, exist_ok=True)
                cp.write_bytes(gzip.compress(body, 5))
                return data
            if status == 404:
                return None
            if status == 429 or status >= 500:
                ra = hdr.get("Retry-After")
                txt = body[:200].decode(errors="replace")
                if status == 429 and ("credit" in txt.lower() or "budget" in txt.lower()):
                    if kind == "list":
                        self.stopped = True
                        self.remaining_keywide = 0
                        raise CreditExhausted(f"429 budget: {txt}")
                    logger.debug("singleton 429 budget message; backing off")
                wait = float(ra) if ra and ra.replace(".", "").isdigit() else delay
                logger.debug(f"{status} on {path}; wait {wait}s")
                await asyncio.sleep(min(wait, 60))
                delay = min(delay * 2, 60)
                continue
            logger.warning(f"HTTP {status} on {path} params={ {k: v for k, v in params.items()} }: "
                           f"{body[:300].decode(errors='replace')}")
            return {"__error__": status, "message": body[:500].decode(errors="replace")}
        logger.error(f"giving up on {path}")
        return None

    async def group_by_all(self, filt: str, key: str, max_pages: int = 10_000) -> list[dict]:
        """Cursor-page a group_by query (1 credit per page). Stops when a page returns < 200 groups."""
        out: list[dict] = []
        cursor = "*"
        for _ in range(max_pages):
            d = await self.get("/works", {"filter": filt, "group_by": key, "per_page": 200, "cursor": cursor})
            if d is None or "__error__" in d:
                raise RuntimeError(f"group_by failed: {filt} {key} {d}")
            g = d.get("group_by", [])
            out.extend(g)
            cursor = d["meta"].get("next_cursor")
            if len(g) < 200 or not cursor:
                break
        return out


# ---------------- phrase normalisation ----------------
_PAREN = re.compile(r"\s*\(([^)]*)\)\s*")
_WS = re.compile(r"\s+")
_ACR = re.compile(r"^[A-Z][A-Za-z0-9\-]{1,9}$")


def singularise(tok: str) -> str:
    if len(tok) <= 3:
        return tok
    if tok.endswith("ies") and len(tok) > 4:
        return tok[:-3] + "y"
    if tok.endswith(("sses", "shes", "ches", "xes", "zes")):
        return tok[:-2]
    if tok.endswith(("ss", "us", "is", "os", "as", "ys")):
        return tok
    if tok.endswith("s"):
        return tok[:-1]
    return tok


def normalise(label: str) -> tuple[str, str | None]:
    """Return (normalised phrase, acronym or None)."""
    acr = None
    for m in _PAREN.finditer(label):
        inner = m.group(1).strip()
        if _ACR.match(inner) and sum(c.isupper() for c in inner) >= 2:
            acr = inner
    s = _PAREN.sub(" ", label)
    s = s.lower().replace("‐", "-").replace("–", "-").replace("—", "-")
    s = s.replace("-", " ").replace("/", " ")
    s = re.sub(r"[^\w\s'.,+]", " ", s)
    s = s.replace(",", " ")
    s = _WS.sub(" ", s).strip(" .'")
    toks = s.split()
    if toks:
        toks[-1] = singularise(toks[-1])
    return " ".join(toks), acr


def surface_forms(phrase: str) -> list[str]:
    """Hyphen/space and plural variants used for local verification and display."""
    toks = phrase.split()
    forms = {phrase}
    if len(toks) >= 2:
        forms.add("-".join(toks))
    last = toks[-1] if toks else ""
    if last and not last.endswith("s"):
        plural = last[:-1] + "ies" if last.endswith("y") and len(last) > 3 and last[-2] not in "aeiou" else last + "s"
        forms.add(" ".join(toks[:-1] + [plural]))
    return sorted(forms)


def verify_regex(phrase: str) -> re.Pattern:
    """Case-folded, hyphen/space-insensitive regex with optional plural on the last token."""
    toks = [re.escape(t) for t in phrase.split()]
    if not toks:
        return re.compile(r"(?!x)x")
    last = toks[-1]
    if phrase.split()[-1].endswith("y"):
        last = last[:-1] + r"(?:y|ies)"
    else:
        last = last + r"(?:s|es)?"
    body = r"[\s\-]+".join(toks[:-1] + [last])
    return re.compile(r"(?<![\w])" + body + r"(?![\w])", re.IGNORECASE)


def fold(text: str) -> str:
    """Accent-fold (NFKD, drop combining marks) so 'Hořava' matches 'horava'."""
    import unicodedata
    t = "".join(ch for ch in unicodedata.normalize("NFKD", text or "") if not unicodedata.combining(ch))
    return re.sub("[\u2010-\u2015\u2212]", "-", t)


def concept_id(phrase: str) -> str:
    return "c_" + hashlib.sha1(phrase.encode()).hexdigest()[:12]


def oa_query(phrase: str) -> str:
    """OpenAlex title_and_abstract.search value: quoted phrase (OpenAlex stems, so plurals are covered)."""
    return f'"{phrase}"'


def reconstruct_abstract(inv: dict | None) -> str:
    if not inv:
        return ""
    pos: list[tuple[int, str]] = []
    for w, ps in inv.items():
        for p in ps:
            pos.append((p, w))
    pos.sort()
    return " ".join(w for _, w in pos)
