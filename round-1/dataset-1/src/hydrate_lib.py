#!/usr/bin/env python3
"""Work hydration via FREE OpenAlex singletons (/works/W...), stored compactly in a local SQLite store
(work_store/ shards; regenerable). Each stored record keeps every field the D2 works table needs, plus the
title+abstract text used ONLY for local surface-form verification (never published)."""
from __future__ import annotations

import asyncio
import sqlite3
import zlib
from datetime import date
from pathlib import Path

import orjson
from loguru import logger

from common import OAClient, ROOT, reconstruct_abstract

SELECT = ("id,doi,ids,title,publication_year,publication_date,type,language,primary_topic,topics,primary_location,"
          "referenced_works,authorships,keywords,concepts,abstract_inverted_index,cited_by_count")


def _wid(url: str | None) -> int | None:
    if not url:
        return None
    s = url.rsplit("/", 1)[-1]
    try:
        return int(s[1:])
    except ValueError:
        return None


def _num(url: str | None) -> int | None:
    """Numeric taxonomy ids (subfields/fields/domains): trailing digits."""
    if not url:
        return None
    s = url.rsplit("/", 1)[-1]
    return int(s) if s.isdigit() else None


def compact(w: dict) -> dict:
    """Reduce an OpenAlex work to the D2 columns (+ verification text)."""
    pt = w.get("primary_topic") or {}
    loc = w.get("primary_location") or {}
    src = loc.get("source") or {}
    abstract = reconstruct_abstract(w.get("abstract_inverted_index"))
    auths = w.get("authorships") or []
    ids = w.get("ids") or {}
    rec = {
        "work_id": _wid(w.get("id")),
        "doi_present": bool(w.get("doi")),
        "pmid_present": bool(ids.get("pmid")),
        "publication_year": w.get("publication_year"),
        "publication_date": w.get("publication_date"),
        "type": w.get("type"),
        "language": w.get("language"),
        "primary_topic_id": _wid(pt.get("id")) if pt else None,
        "topic_score": pt.get("score") if pt else None,
        "subfield_id": _num((pt.get("subfield") or {}).get("id")) if pt else None,
        "field_id": _num((pt.get("field") or {}).get("id")) if pt else None,
        "domain_id": _num((pt.get("domain") or {}).get("id")) if pt else None,
        "topics_top3": [_wid(t.get("id")) for t in (w.get("topics") or [])[:3]],
        "source_id": _wid(src.get("id")),
        "source_type": src.get("type"),
        "refs": [x for x in (_wid(r) for r in (w.get("referenced_works") or [])) if x is not None],
        "author_ids": [], "author_positions": [], "institution_ids": [],
        "keywords": [[(k.get("id") or "").rsplit("/", 1)[-1], float(k.get("score") or 0)] for k in (w.get("keywords") or [])],
        "concepts": [[_wid(c.get("id")), float(c.get("score") or 0)] for c in (w.get("concepts") or [])
                     if float(c.get("score") or 0) >= 0.2],
        "has_abstract": bool(abstract),
        "abstract_n_tokens": len(abstract.split()) if abstract else 0,
        "cited_by_count": w.get("cited_by_count"),
        "retrieved_at": date.today().isoformat(),
        "title": w.get("title") or "",
        "text": ((w.get("title") or "") + " \n " + abstract),
    }
    for a in auths:
        aid = _wid((a.get("author") or {}).get("id"))
        rec["author_ids"].append(aid if aid is not None else -1)
        rec["author_positions"].append(a.get("author_position") or "")
        rec["institution_ids"].append([x for x in (_wid(i.get("id")) for i in (a.get("institutions") or [])) if x])
    return rec


STORE_DIR = ROOT / "work_store"
N_SHARDS = 8


class Store:
    """Sharded store (work_store/works_XX.sqlite by work_id % N_SHARDS, each < 100 MB; S2 map in s2map.sqlite)."""

    def __init__(self, path: Path = STORE_DIR) -> None:
        path.mkdir(exist_ok=True)
        self.shards = []
        for i in range(N_SHARDS):
            c = sqlite3.connect(path / f"works_{i:02d}.sqlite", timeout=60)
            c.execute("CREATE TABLE IF NOT EXISTS works (id INTEGER PRIMARY KEY, rec BLOB)")
            c.execute("CREATE TABLE IF NOT EXISTS missing (id INTEGER PRIMARY KEY)")
            c.commit()
            self.shards.append(c)
        self.con = sqlite3.connect(path / "s2map.sqlite", timeout=60)
        self.con.execute("CREATE TABLE IF NOT EXISTS s2map (corpus_id INTEGER PRIMARY KEY, wid INTEGER, how TEXT)")
        self.con.commit()

    def _split(self, ids):
        by = {}
        for i in ids:
            by.setdefault(i % N_SHARDS, []).append(i)
        return by

    def have(self, ids: list[int]) -> set[int]:
        out: set[int] = set()
        for k, sub in self._split(ids).items():
            con = self.shards[k]
            for i in range(0, len(sub), 900):
                ch = sub[i:i + 900]
                for t in ("works", "missing"):
                    out.update(r[0] for r in con.execute(f"SELECT id FROM {t} WHERE id IN ({','.join('?' * len(ch))})", ch))
        return out

    def put(self, recs: list[dict]) -> None:
        by = {}
        for r in recs:
            by.setdefault(r["work_id"] % N_SHARDS, []).append((r["work_id"], zlib.compress(orjson.dumps(r), 3)))
        for k, rows in by.items():
            self.shards[k].executemany("INSERT OR REPLACE INTO works VALUES (?,?)", rows)
            self.shards[k].commit()

    def put_missing(self, ids: list[int]) -> None:
        for k, sub in self._split(ids).items():
            self.shards[k].executemany("INSERT OR IGNORE INTO missing VALUES (?)", [(i,) for i in sub])
            self.shards[k].commit()

    def get_many(self, ids: list[int]) -> dict[int, dict]:
        out = {}
        for k, sub in self._split(ids).items():
            for i in range(0, len(sub), 900):
                ch = sub[i:i + 900]
                for wid, blob in self.shards[k].execute(f"SELECT id, rec FROM works WHERE id IN ({','.join('?' * len(ch))})", ch):
                    out[wid] = orjson.loads(zlib.decompress(blob))
        return out

    def count(self) -> int:
        return sum(c.execute("SELECT COUNT(*) FROM works").fetchone()[0] for c in self.shards)


async def hydrate_ids(oa: OAClient, store: Store, ids: list[int], flush_every: int = 500) -> int:
    """Fetch missing works via free singletons. Returns number newly stored."""
    ids = list(dict.fromkeys(ids))
    have = store.have(ids)
    need = [i for i in ids if i not in have]
    if not need:
        return 0
    buf: list[dict] = []
    miss: list[int] = []
    n_new = 0

    async def one(wid: int) -> None:
        nonlocal n_new
        d = await oa.get(f"/works/W{wid}", {"select": SELECT}, kind="singleton", use_cache=False)
        if d is None or "__error__" in d:
            miss.append(wid)
            return
        rec = compact(d)
        if rec["work_id"] != wid:  # merged id -> store under both keys
            rec2 = dict(rec)
            rec2["work_id"] = wid
            rec2["merged_into"] = rec["work_id"]
            buf.append(rec2)
        else:
            buf.append(rec)
        n_new += 1

    for i in range(0, len(need), flush_every):
        await asyncio.gather(*[one(w) for w in need[i:i + flush_every]])
        store.put(buf)
        store.put_missing(miss)
        buf.clear()
        miss.clear()
    return n_new
