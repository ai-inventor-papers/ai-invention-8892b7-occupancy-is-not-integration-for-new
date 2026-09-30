#!/usr/bin/env python3
"""Steps 4-5: FULL RETRIEVAL + HYDRATION of the frozen sample, strictly in hydration_order (u-order prefix).

Discovery per concept (years 2000-2024, never size-capped):
  Route A_openalex_native : group_by=ids.openalex over title_and_abstract.search (1 credit / 200 ids), used while
                            credits remain above the reserve.
  Route B_s2_index        : Semantic Scholar bulk search (free) with OR of quoted surface forms, every page; each hit
                            mapped to OpenAlex through FREE singletons (DOI -> MAG -> PMID -> arXiv DOI).
Hydration: FREE OpenAlex singletons (hydrate_lib). Local verification regex decides c-paper membership.
State: retrieval/<concept_id>.json (resume-safe). Stop rule: when the deadline passes, no NEW concept is started;
in-flight concepts finish; everything not complete goes to pending_hydration.json.

Usage: python hydrate.py --deadline-min 200 [--resume] [--max-concepts N]"""
import argparse
import asyncio
import sqlite3
import time
from collections import Counter
from pathlib import Path
from urllib.parse import quote

import aiohttp
import orjson
from loguru import logger

from common import OAClient, CreditExhausted, ROOT, fold, oa_query, setup_logging, verify_regex
from hydrate_lib import SELECT, Store, compact

RET = ROOT / "retrieval"
S2_URL = "https://api.semanticscholar.org/graph/v1/paper/search/bulk"
CREDIT_RESERVE = 60  # kept for the recall audit


class S2:
    def __init__(self) -> None:
        self.session: aiohttp.ClientSession | None = None
        self.last = 0.0
        self.lock = asyncio.Lock()
        self.n_calls = 0
        self.n_429 = 0

    async def get(self, params: dict) -> dict | None:
        async with self.lock:  # one S2 request at a time, >= 1.05 s apart
            delay = 2.0
            for attempt in range(12):
                wait = self.last + 1.05 - time.monotonic()
                if wait > 0:
                    await asyncio.sleep(wait)
                self.last = time.monotonic()
                try:
                    async with self.session.get(S2_URL, params=params, timeout=aiohttp.ClientTimeout(total=60)) as r:
                        self.n_calls += 1
                        if r.status == 200:
                            return await r.json()
                        if r.status in (429, 500, 502, 503, 504):
                            self.n_429 += 1
                            await asyncio.sleep(delay)
                            delay = min(delay * 1.6, 30)
                            continue
                        logger.warning(f"S2 HTTP {r.status}: {(await r.text())[:200]}")
                        return None
                except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                    logger.debug(f"S2 net error {e}")
                    await asyncio.sleep(delay)
            return None


def s2_query(forms: list[str]) -> str:
    return " | ".join(f'"{f}"' for f in forms)


class Mapper:
    """S2 CorpusId -> OpenAlex work id cache (sqlite)."""

    def __init__(self) -> None:
        self.con = sqlite3.connect(ROOT / "work_store" / "s2map.sqlite", timeout=60)
        self.con.execute("CREATE TABLE IF NOT EXISTS s2map (corpus_id INTEGER PRIMARY KEY, wid INTEGER, how TEXT)")
        self.con.commit()

    def get(self, cids: list[int]) -> dict[int, tuple[int, str]]:
        out = {}
        for i in range(0, len(cids), 900):
            ch = cids[i:i + 900]
            for c, w, h in self.con.execute(f"SELECT corpus_id, wid, how FROM s2map WHERE corpus_id IN ({','.join('?' * len(ch))})", ch):
                out[c] = (w, h)
        return out

    def put(self, rows: list[tuple[int, int, str]]) -> None:
        self.con.executemany("INSERT OR REPLACE INTO s2map VALUES (?,?,?)", rows)
        self.con.commit()


async def discover_native(oa: OAClient, c: dict) -> dict:
    groups = await oa.group_by_all(f"title_and_abstract.search:{oa_query(c['phrase'])},publication_year:2000-2024",
                                   "ids.openalex")
    ids = [int(g["key"].rsplit("/W", 1)[-1]) for g in groups if "/W" in g["key"]]
    return {"route": "A_openalex_native", "oa_ids": ids}


async def discover_s2(s2: S2, c: dict) -> dict:
    forms = c["surface_forms"] or [c["phrase"]]
    params = {"query": s2_query(forms), "fields": "externalIds,year,title,abstract", "year": "2000-2024"}
    rx = verify_regex(fold(c["phrase"]))
    hits, token, pages = [], None, 0
    while True:
        p = dict(params)
        if token:
            p["token"] = token
        d = await s2.get(p)
        pages += 1
        if d is None:
            return {"route": "B_s2_index", "error": "s2_failed", "s2_hits": hits, "s2_pages": pages}
        for x in d.get("data") or []:
            ext = x.get("externalIds") or {}
            hits.append({"cid": ext.get("CorpusId"), "doi": ext.get("DOI"), "mag": ext.get("MAG"),
                         "pmid": ext.get("PubMed"), "arxiv": ext.get("ArXiv"), "year": x.get("year"),
                         "title": (x.get("title") or "")[:300], "s2_has_abstract": bool(x.get("abstract")),
                         "s2_text_match": bool(rx.search(fold((x.get("title") or "") + " " + (x.get("abstract") or ""))))})
        token = d.get("token")
        if not token:
            break
    return {"route": "B_s2_index", "s2_hits": hits, "s2_pages": pages}


async def map_and_hydrate_s2(oa: OAClient, store: Store, mapper: Mapper, hits: list[dict]) -> dict[int, int]:
    """Returns corpus_id -> wid (or -1 unmapped). Hydrates every mapped work."""
    cids = [h["cid"] for h in hits if h.get("cid")]
    known = mapper.get(cids)
    res = {c: w for c, (w, _) in known.items()}
    # pre-filter (saves free-but-rate-limited singletons): skip hits whose S2 title+abstract is present and does
    # not contain the phrase; hits discovered before this filter existed carry no flag and are all hydrated.
    todo = [h for h in hits if h.get("cid") and h["cid"] not in known
            and (h.get("s2_text_match", True) or not h.get("s2_has_abstract", False))]
    new_rows, recs = [], []

    async def one(h: dict) -> None:
        tries = []
        if h.get("doi"):
            tries.append(("doi", f"/works/doi:{quote(h['doi'].lower(), safe='/:')}"))
        if h.get("mag"):
            tries.append(("mag", f"/works/mag:{h['mag']}"))
        if h.get("pmid"):
            tries.append(("pmid", f"/works/pmid:{h['pmid']}"))
        if h.get("arxiv"):
            tries.append(("arxiv", f"/works/doi:10.48550/arxiv.{h['arxiv'].lower()}"))
        for how, path in tries:
            d = await oa.get(path, {"select": SELECT}, kind="singleton", use_cache=False)
            if d and "__error__" not in d and d.get("id"):
                r = compact(d)
                recs.append(r)
                new_rows.append((h["cid"], r["work_id"], how))
                res[h["cid"]] = r["work_id"]
                return
        new_rows.append((h["cid"], -1, "unmapped" if tries else "no_ids"))
        res[h["cid"]] = -1

    # iter2: credit-priced DOI batch mapping (filter=doi:a|b|..., 50 DOIs / 1 credit) once the batch path is enabled;
    # hits it does not resolve (no DOI, DOI not in OpenAlex, odd characters) keep the free singleton chain below
    from hydrate_lib import batch_enabled, list_truncated
    if batch_enabled():
        from common import CreditExhausted
        doi_hits = [h for h in todo if h.get("doi") and not any(ch in h["doi"] for ch in ",|&?#\"")]
        resolved: set = set()
        chunks = [doi_hits[i:i + 50] for i in range(0, len(doi_hits), 50)]
        for j in range(0, len(chunks), 8):
            grp = chunks[j:j + 8]
            if not oa.can_spend(len(grp)):
                break

            async def fetch(ch: list[dict]):
                try:
                    return await oa.get("/works", {"filter": "doi:" + "|".join(h["doi"].lower() for h in ch),
                                                   "per_page": 50, "select": SELECT}, kind="list", use_cache=False)
                except CreditExhausted:
                    return None
            res_ = await asyncio.gather(*[fetch(ch) for ch in grp])
            for ch, d in zip(grp, res_):
                if not d or "__error__" in d:
                    continue
                by_doi = {}
                for w in d.get("results", []):
                    dd = (w.get("doi") or "").lower().replace("https://doi.org/", "")
                    if dd:
                        by_doi[dd] = w
                for h in ch:
                    w = by_doi.get(h["doi"].lower())
                    if w is None or list_truncated(w):
                        continue  # -> free singleton chain (unresolved, or authorships truncated by the list)
                    r = compact(w, batch="iter2_batch")
                    recs.append(r)
                    new_rows.append((h["cid"], r["work_id"], "doi_batch"))
                    res[h["cid"]] = r["work_id"]
                    resolved.add(h["cid"])
            store.put(recs)
            mapper.put(new_rows)
            recs.clear()
            new_rows.clear()
        todo = [h for h in todo if h["cid"] not in resolved]

    for i in range(0, len(todo), 400):
        await asyncio.gather(*[one(h) for h in todo[i:i + 400]])
        store.put(recs)
        mapper.put(new_rows)
        recs.clear()
        new_rows.clear()
    return res


async def process(c: dict, oa: OAClient, s2: S2, store: Store, mapper: Mapper, use_native: bool) -> dict:
    t0 = time.time()
    st_p = RET / f"{c['concept_id']}.json"
    st = orjson.loads(st_p.read_bytes()) if st_p.exists() else {}
    if st.get("complete"):
        return st
    if "discovery" not in st:
        disc = None
        st["discovery_started_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        if use_native and oa.can_spend(CREDIT_RESERVE + 5):
            try:
                disc = await discover_native(oa, c)
            except CreditExhausted:
                disc = None
        if disc is None:
            disc = await discover_s2(s2, c)
        st["discovery"] = disc
        st_p.write_bytes(orjson.dumps(st))
    disc = st["discovery"]
    if disc.get("error"):
        st["complete"] = False
        return st
    rx = verify_regex(c["phrase"])
    links, s2_by_year, unmapped_by_year = [], Counter(), Counter()
    if disc["route"] == "A_openalex_native":
        ids = disc["oa_ids"]
        have = store.have(ids)
        need = [i for i in ids if i not in have]
        from hydrate_lib import hydrate_ids
        await hydrate_ids(oa, store, need)
        recs = store.get_many(ids)
        for wid in ids:
            w = recs.get(wid)
            if w is None:
                continue
            ev = "oa_title" if rx.search(w["title"]) else ("oa_abstract" if rx.search(w["text"]) else
                                                             ("oa_index_only" if not w["has_abstract"] else None))
            if ev:
                links.append((wid, ev, w["publication_year"]))
        st["n_candidates"] = len(ids)
        st["n_hydrated"] = len(recs)
    else:
        hits = disc["s2_hits"]
        for h in hits:
            if h.get("year"):
                s2_by_year[int(h["year"])] += 1
        m = await map_and_hydrate_s2(oa, store, mapper, hits)
        wids = sorted({w for w in m.values() if w and w > 0})
        recs = store.get_many(wids)
        seen = set()
        pref = lambda h: h.get("s2_has_abstract", False) and not h.get("s2_text_match", True)  # noqa: E731
        st["s2_prefiltered_n"] = sum(1 for h in hits if pref(h))
        for h in hits:
            if pref(h):
                continue
            w = m.get(h.get("cid"), -1) if h.get("cid") else -1
            if w is None or w <= 0:
                if h.get("year"):
                    unmapped_by_year[int(h["year"])] += 1
                continue
            if w in seen:
                continue
            seen.add(w)
            r = recs.get(w)
            if r is None:
                continue
            # s2_only = OpenAlex has no abstract text to verify against, S2 matched title/abstract
            ev = "oa_title" if rx.search(r["title"]) else ("oa_abstract" if rx.search(r["text"]) else
                                                           ("s2_only" if not r["has_abstract"] else None))
            if ev and r["publication_year"] and 2000 <= r["publication_year"] <= 2024:
                links.append((w, ev, r["publication_year"]))
        st["n_candidates"] = len(hits)
        st["n_hydrated"] = len(recs)
        st["s2_counts_by_year"] = {str(k): v for k, v in sorted(s2_by_year.items())}
        st["s2_unmapped_by_year"] = {str(k): v for k, v in sorted(unmapped_by_year.items())}
        n_with_id = sum(1 for h in hits if h.get("cid") and not pref(h))
        st["s2_to_oa_mapping_rate"] = round(sum(1 for h in hits if h.get("cid") and not pref(h)
                                                and (m.get(h["cid"]) or -1) > 0) / max(n_with_id, 1), 4)
    links = [(w, ev, y) for (w, ev, y) in links if y is not None and 2000 <= y <= 2024]
    st["links"] = links
    st["complete"] = True
    st["hydration_batch"] = "iter2"
    st["completed_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    st["seconds"] = round(time.time() - t0, 1)
    st_p.write_bytes(orjson.dumps(st))
    return st


async def run(args) -> None:
    RET.mkdir(exist_ok=True)
    frame = orjson.loads((ROOT / "sample_frame_frozen.json").read_bytes())
    byid = {x["concept_id"]: x for x in frame["eligible"] + frame["reference"]}
    order = frame["hydration_order"]
    if args.max_concepts:
        order = order[: args.max_concepts]
    deadline = time.time() + args.deadline_min * 60
    store, mapper, s2 = Store(), Mapper(), S2()
    q: asyncio.Queue = asyncio.Queue(maxsize=6)
    done_n = Counter()
    async with OAClient() as oa, aiohttp.ClientSession() as sess:
        s2.session = sess

        async def producer() -> None:
            for cid in order:
                if time.time() > deadline:
                    logger.info("deadline reached: no new concepts started")
                    break
                await q.put(cid)
            for _ in range(args.workers):
                await q.put(None)

        async def worker(k: int) -> None:
            while True:
                cid = await q.get()
                if cid is None:
                    return
                try:
                    st = await process(byid[cid], oa, s2, store, mapper, use_native=not args.no_native)
                    done_n["ok" if st.get("complete") else "fail"] += 1
                    logger.info(f"[{sum(done_n.values())}] {byid[cid]['phrase'][:40]!r} route={st.get('discovery', {}).get('route')} "
                                f"cand={st.get('n_candidates')} links={len(st.get('links', []))} t={st.get('seconds')}s "
                                f"credits={oa.spent_today} rem={oa.remaining_keywide} store={store.count()} s2calls={s2.n_calls}/{s2.n_429}")
                except Exception as e:  # noqa: BLE001 - log and continue with the next concept
                    logger.exception(f"concept {cid} failed: {e}")
                    done_n["fail"] += 1

        await asyncio.gather(producer(), *[worker(k) for k in range(args.workers)])
    logger.info(f"hydration finished: {dict(done_n)} store={store.count()}")


@logger.catch(reraise=True)
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--deadline-min", type=float, default=200)
    ap.add_argument("--max-concepts", type=int, default=0)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--no-native", action="store_true")
    ap.add_argument("--resume", action="store_true", help="state is always resumed from retrieval/*.json")
    args = ap.parse_args()
    setup_logging("hydrate")
    asyncio.run(run(args))


if __name__ == "__main__":
    main()
