"""OpenAlex helpers: async client with credit ledger + artifact ceiling, compact work schema, local text matching."""
from __future__ import annotations

import asyncio
import json
import os
import random
import re
import time
from datetime import datetime, timezone
from pathlib import Path

import aiohttp
from loguru import logger

ROOT = Path(__file__).resolve().parent.parent
BASE = "https://api.openalex.org"
API_KEY = os.environ.get("OPENALEX_API_KEY", "")  # set OPENALEX_API_KEY; never commit the key
LEDGER = ROOT / "logs" / "openalex_credit_ledger.jsonl"
DAILY_CREDITS = 10_000          # measured via /rate-limit on 2026-09-28 (free tier, $1/day)
OA_CEILING = int(0.20 * DAILY_CREDITS)   # this artifact's share
STOP_AT = int(0.90 * OA_CEILING)          # stop paid calls at 90% of the ceiling
SELECT = ("id,ids,doi,title,publication_year,publication_date,type,language,primary_topic,primary_location,"
          "referenced_works,authorships,keywords,concepts,cited_by_count,mesh,abstract_inverted_index,indexed_in")


def ledger_total() -> int:
    if not LEDGER.exists():
        return 0
    return sum(json.loads(l)["credits"] for l in LEDGER.read_text().splitlines() if l.strip())


class OA:
    def __init__(self, session: aiohttp.ClientSession, rps: float = 30.0, conc: int = 30) -> None:
        self.s = session
        self.sem = asyncio.Semaphore(conc)
        self.interval = 1.0 / rps
        self._lock = asyncio.Lock()
        self._last = 0.0
        self.spent = ledger_total()
        self.budget_exhausted = False
        self.n = 0

    async def _tick(self) -> None:
        async with self._lock:
            w = self._last + self.interval - time.monotonic()
            if w > 0:
                await asyncio.sleep(w)
            self._last = time.monotonic()

    def can_spend(self, credits: int) -> bool:
        return (not self.budget_exhausted) and self.spent + credits <= STOP_AT

    async def get(self, path: str, params: dict, paid_kind: str | None = None) -> tuple[int, dict | None]:
        """Returns (status, json). paid_kind: None for free singletons, else 'search'/'list'/'group_by'."""
        params = dict(params)
        params["api_key"] = API_KEY
        for attempt in range(7):
            async with self.sem:
                await self._tick()
                self.n += 1
                try:
                    async with self.s.get(f"{BASE}{path}", params=params,
                                          timeout=aiohttp.ClientTimeout(total=90)) as r:
                        used = int(r.headers.get("x-ratelimit-credits-used", "0") or 0)
                        rem = r.headers.get("x-ratelimit-remaining")
                        if used:
                            self.spent += used
                            with LEDGER.open("a") as fh:
                                fh.write(json.dumps({"ts": datetime.now(timezone.utc).isoformat(), "kind": paid_kind,
                                                     "path": path, "credits": used, "key_remaining": rem,
                                                     "filter": str(params.get("filter", ""))[:300]}) + "\n")
                        if r.status == 200:
                            return 200, await r.json(content_type=None)
                        if r.status == 404:
                            return 404, None
                        body = (await r.text())[:200]
                        if r.status == 429 and paid_kind and ("budget" in body.lower() or "credit" in body.lower()):
                            logger.error(f"Budget 429 on paid call: {body}")
                            self.budget_exhausted = True
                            return 429, None
                        logger.warning(f"OA HTTP {r.status} {path}: {body[:120]}")
                except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                    logger.warning(f"OA error {type(e).__name__} {path}: {str(e)[:100]}")
            await asyncio.sleep(min(30, 1.5 ** attempt + random.random()))
        return -1, None


def _int_id(url: str | None) -> int | None:
    if not url:
        return None
    m = re.search(r"(\d+)$", url)
    return int(m.group(1)) if m else None


def reconstruct_abstract(inv: dict | None) -> str:
    if not inv:
        return ""
    pos = []
    for w, idxs in inv.items():
        for i in idxs:
            pos.append((i, w))
    pos.sort()
    return " ".join(w for _, w in pos)


GREEK = {"α": "alpha", "β": "beta", "γ": "gamma", "δ": "delta", "κ": "kappa", "λ": "lambda", "ε": "epsilon",
         "θ": "theta", "μ": "mu", "σ": "sigma", "ω": "omega", "ζ": "zeta", "η": "eta", "τ": "tau"}
_DASH = re.compile(r"[\-‐‑‒–—−/,]")
_WS = re.compile(r"\s+")


def norm_text(s: str) -> str:
    s = (s or "").lower()
    for g, n in GREEK.items():
        s = s.replace(g, n)
    s = _DASH.sub(" ", s)
    s = re.sub(r"<[^>]+>", " ", s)
    return _WS.sub(" ", s).strip()


def _number_insensitive(last: str) -> str:
    """Regex for the last word matching singular or plural (MeSH terms are often plural, text often singular)."""
    if len(last) > 4 and last.endswith("ies"):
        return re.escape(last[:-3]) + "(?:y|ies)"
    if len(last) > 4 and last.endswith(("ses", "xes", "ches", "shes")):
        return re.escape(last[:-2]) + "(?:es)?"
    if len(last) > 3 and last.endswith("s") and not last.endswith(("ss", "us", "is")):
        return re.escape(last[:-1]) + "(?:s|es)?"
    return re.escape(last) + "(?:s|es)?"


def form_regex(forms: list[str]) -> list[tuple[str, re.Pattern]]:
    out = []
    for f in forms:
        toks = norm_text(f).split()
        if not toks:
            continue
        body = " ".join([re.escape(t) for t in toks[:-1]] + [_number_insensitive(toks[-1])])
        out.append((f, re.compile(r"(?<![a-z0-9])" + body + r"(?![a-z0-9])")))
    return out


def match_work(title_n: str, abs_n: str, regs: list[tuple[str, re.Pattern]]) -> tuple[bool, str, list[str]]:
    in_t, in_a, forms = False, False, []
    for f, rg in regs:
        t = bool(rg.search(title_n))
        a = bool(rg.search(abs_n))
        if t or a:
            forms.append(f)
        in_t |= t
        in_a |= a
    field = "both" if in_t and in_a else "title" if in_t else "abstract" if in_a else "none_local"
    return (in_t or in_a), field, forms


def compact(w: dict) -> dict:
    """Main-corpus compact schema (integer-suffix IDs, abstract not stored)."""
    ids = w.get("ids") or {}
    pt = w.get("primary_topic") or {}
    src = ((w.get("primary_location") or {}).get("source") or {})
    pm = ids.get("pmid")
    return {
        "work_id": _int_id(w.get("id")),
        "pmid": _int_id(pm) if pm else None,
        "doi": (w.get("doi") or "").replace("https://doi.org/", "") or None,
        "publication_year": w.get("publication_year"),
        "publication_date": w.get("publication_date"),
        "type": w.get("type"),
        "language": w.get("language"),
        "primary_topic": {"topic_id": _int_id(pt.get("id")),
                          "subfield_id": _int_id((pt.get("subfield") or {}).get("id")),
                          "field_id": _int_id((pt.get("field") or {}).get("id")),
                          "domain_id": _int_id((pt.get("domain") or {}).get("id"))} if pt else None,
        "venue": {"source_id": _int_id(src.get("id")), "source_type": src.get("type"),
                  "issn_l": src.get("issn_l")} if src else None,
        "referenced_works": [_int_id(x) for x in (w.get("referenced_works") or [])],
        "authorships": [{"author_id": _int_id((a.get("author") or {}).get("id")),
                         "institution_ids": [_int_id(i.get("id")) for i in (a.get("institutions") or []) if i.get("id")],
                         "author_position": a.get("author_position")} for a in (w.get("authorships") or [])],
        "keywords": [{"id": (k.get("id") or "").rsplit("/", 1)[-1], "score": round(k.get("score") or 0, 3)}
                     for k in (w.get("keywords") or [])],
        "concepts": [{"id": _int_id(c.get("id")), "level": c.get("level"), "score": round(c.get("score") or 0, 3)}
                     for c in (w.get("concepts") or [])],
        "cited_by_count": w.get("cited_by_count"),
        "has_abstract": w.get("abstract_inverted_index") is not None,
        "mesh": [{"descriptor_ui": m.get("descriptor_ui"), "is_major_topic": m.get("is_major_topic")}
                 for m in (w.get("mesh") or []) if m.get("descriptor_ui")],
        "indexed_in": w.get("indexed_in") or [],
    }


def texts(w: dict) -> tuple[str, str]:
    return norm_text(w.get("title") or ""), norm_text(reconstruct_abstract(w.get("abstract_inverted_index")))
