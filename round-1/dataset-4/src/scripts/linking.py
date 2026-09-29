"""S3 linking: exact / normalised-string matching of phrase keys to OpenAlex keywords, legacy
OpenAlex concepts (with Wikidata QIDs), MeSH descriptors + entry terms, and Wikidata (free API)."""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

import aiohttp
from loguru import logger

sys.path.insert(0, str(Path(__file__).resolve().parent))
from textnorm import normalise  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SNAP = ROOT / "temp" / "datasets" / "openalex_snapshot"
MESH = ROOT / "temp" / "datasets" / "mesh" / "mesh_descriptors_2026.json"
WD_CACHE = ROOT / "cache" / "wikidata"
WD_CACHE.mkdir(parents=True, exist_ok=True)


def _mesh_variants(term: str) -> list[str]:
    """MeSH entry terms are often inverted ('Coenzyme A, Acetyl'); add the un-inverted form."""
    out = [term]
    if ", " in term and term.count(", ") == 1:
        a, b = term.split(", ")
        out.append(f"{b} {a}")
    return out


class Linker:
    def __init__(self) -> None:
        self.kw: dict[str, dict] = {}
        for r in json.loads((SNAP / "keywords.json").read_text()):
            self.kw.setdefault(normalise(r["display_name"] or ""), r)
        self.co: dict[str, dict] = {}
        for r in json.loads((SNAP / "concepts.json").read_text()):
            self.co.setdefault(normalise(r["display_name"] or ""), r)
        self.mesh: dict[str, dict] = {}
        self.mesh_pairs: list[tuple[str, str, str]] = []  # (heading, entry term, ui)
        for r in json.loads(MESH.read_text()):
            for t in [r["heading"]] + r["entry_terms"]:
                for v in _mesh_variants(t):
                    self.mesh.setdefault(normalise(v), {"ui": r["ui"], "heading": r["heading"], "matched": v})
            for t in r["entry_terms"]:
                self.mesh_pairs.append((r["heading"], _mesh_variants(t)[-1], r["ui"]))
        self.kw.pop("", None)
        self.co.pop("", None)
        self.mesh.pop("", None)
        logger.info(f"linker: {len(self.kw)} keywords, {len(self.co)} concepts, {len(self.mesh)} MeSH strings")

    def link(self, key: str, surfaces: list[str] | None = None) -> dict:
        forms = {key} | {normalise(s) for s in (surfaces or [])}
        res = {"keyword": None, "concept": None, "mesh": None}
        for f in forms:
            if not res["keyword"] and f in self.kw:
                r = self.kw[f]
                res["keyword"] = {"id": r["id"], "display_name": r["display_name"], "works_count": r["works_count"]}
            if not res["concept"] and f in self.co:
                r = self.co[f]
                res["concept"] = {"id": r["id"], "display_name": r["display_name"], "level": r["level"], "wikidata": r["wikidata"]}
            if not res["mesh"] and f in self.mesh:
                res["mesh"] = self.mesh[f]
        return res


async def wikidata_lookup(keys: list[str], rps: float = 4.0) -> dict[str, dict | None]:
    """wbsearchentities for each key; keep hits whose label or alias normalises to the key."""
    out: dict[str, dict | None] = {}
    sem = asyncio.Semaphore(4)
    headers = {"User-Agent": "aii-emerging-concepts/0.1 (research dataset; mailto:adrian.m.grobelnik@ijs.si)"}
    lock = asyncio.Lock()
    last = [0.0]

    async def one(s: aiohttp.ClientSession, k: str):
        import hashlib
        cp = WD_CACHE / (hashlib.sha1(k.encode()).hexdigest() + ".json")
        if cp.exists():
            data = json.loads(cp.read_text())
        else:
            async with sem:
                async with lock:
                    wait = last[0] + 1.0 / rps - asyncio.get_event_loop().time()
                    if wait > 0:
                        await asyncio.sleep(wait)
                    last[0] = asyncio.get_event_loop().time()
                data = None
                for attempt in range(4):
                    try:
                        async with s.get("https://www.wikidata.org/w/api.php",
                                         params={"action": "wbsearchentities", "search": k, "language": "en",
                                                 "limit": 3, "format": "json", "type": "item"}) as r:
                            if r.status == 200:
                                data = await r.json()
                                break
                            await asyncio.sleep(2 ** attempt)
                    except (aiohttp.ClientError, asyncio.TimeoutError):
                        await asyncio.sleep(2 ** attempt)
                if data is None:
                    out[k] = None
                    return
                cp.write_text(json.dumps(data))
        hit = None
        for h in data.get("search", []):
            cands = [h.get("label", "")] + list(h.get("aliases", []) or [])
            m = h.get("match") or {}
            cands.append(m.get("text", ""))
            if any(normalise(c) == k for c in cands if c):
                hit = {"qid": h.get("id"), "label": h.get("label"), "description": h.get("description"),
                       "aliases": h.get("aliases", [])}
                break
        out[k] = hit

    async with aiohttp.ClientSession(headers=headers, timeout=aiohttp.ClientTimeout(total=60)) as s:
        await asyncio.gather(*[one(s, k) for k in keys])
    return out


async def wikidata_aliases(qids: list[str]) -> dict[str, dict]:
    """wbgetentities in batches of 50: English label + aliases."""
    out: dict[str, dict] = {}
    headers = {"User-Agent": "aii-emerging-concepts/0.1 (research dataset; mailto:adrian.m.grobelnik@ijs.si)"}
    async with aiohttp.ClientSession(headers=headers, timeout=aiohttp.ClientTimeout(total=90)) as s:
        for i in range(0, len(qids), 50):
            b = qids[i:i + 50]
            for attempt in range(4):
                try:
                    async with s.get("https://www.wikidata.org/w/api.php",
                                     params={"action": "wbgetentities", "ids": "|".join(b), "props": "labels|aliases",
                                             "languages": "en", "format": "json"}) as r:
                        if r.status == 200:
                            d = await r.json()
                            for q, e in (d.get("entities") or {}).items():
                                out[q] = {"label": ((e.get("labels") or {}).get("en") or {}).get("value"),
                                          "aliases": [a["value"] for a in ((e.get("aliases") or {}).get("en") or [])]}
                            break
                except (aiohttp.ClientError, asyncio.TimeoutError):
                    pass
                await asyncio.sleep(2 ** attempt)
            await asyncio.sleep(0.3)
    return out
