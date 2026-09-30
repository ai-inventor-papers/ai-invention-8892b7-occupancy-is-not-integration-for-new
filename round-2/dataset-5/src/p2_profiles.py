#!/usr/bin/env python3
"""P2: exact nativeness profiles (primary_topic.subfield counts per 5-year block) for the OpenAlex legacy-concept /
keyword nodes that co-occur with pool concepts in HOST (non-origin) c-papers.

Stages
  rank      host co-occurrence weights W(X), W(c,X) -> p2/node_ranking.parquet (free)
  fetch     1 group_by call per (node, block), top-down by W until 95 % cumulative weight, the credit sub-cap
            or key-wide remaining < 1,500; all 4 blocks per node (node-major), cached per (node, block)
  coverage  per pool concept: share of its host weight whose node has all 4 blocks -> outputs/

Definitions
  c-paper       a verified concept-work link (hyd/concept_work.parquet after assembly; retrieval/*.json before)
  origin        main concepts: modal primary-topic subfield of the F..F+2 c-papers (as in assemble.py);
                reference concepts: modal subfield of their 2000-2004 c-papers (rule recorded per concept)
  host c-paper  a c-paper whose primary-topic subfield is known and differs from the concept's origin
  nodes of p    legacy concepts stored with score >= 0.2, plus keywords; a keyword whose display name equals a
                legacy concept's display name is merged into that concept (the concept id is kept)
  W(X)          sum over (c, host c-paper p of c) of 1[X in nodes(p)]
Frame: NO type filter (matches dataset_1's 'all_types' denominator and the all-type c-paper corpus).
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

import orjson
import pandas as pd
import pyarrow.parquet as pq
from loguru import logger

ROOT = Path(__file__).resolve().parent
HYD = ROOT / "hyd"
P2 = ROOT / "p2"
OUT = ROOT / "outputs"
# copies of gen_art_dataset_2 data/{concepts,keywords}.parquet (iteration-1 artifact), see README
DS2 = Path(os.environ.get("DATASET2_DATA_DIR", ROOT / "deps" / "gen_art_dataset_2"))
sys.path.insert(0, str(HYD))
BLOCKS = ["2000-2004", "2005-2009", "2010-2014", "2015-2019"]
TARGET_SHARE = 0.95
GUARD_REMAINING = 1500


def setup_logging() -> None:
    (ROOT / "logs").mkdir(exist_ok=True)
    logger.remove()
    logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
    logger.add(ROOT / "logs" / "p2_profiles.log", rotation="30 MB", level="DEBUG")


# ------------------------------------------------------------------ pool, links, origins
def load_pool() -> tuple[list[dict], dict[str, list[tuple[int, int]]], str]:
    """Included concepts (exact u-order prefix) and their c-paper links [(work_id, year)]."""
    frame = orjson.loads((HYD / "sample_frame_frozen.json").read_bytes())
    byid = {x["concept_id"]: x for x in frame["eligible"] + frame["reference"]}
    cw_p = HYD / "concept_work.parquet"
    if cw_p.exists() and (HYD / "data_out.json").exists() and os.environ.get("P2_LINKS") != "retrieval":
        cw = pd.read_parquet(cw_p, columns=["concept_id", "work_id", "year"])
        links = {c: list(zip(g["work_id"].astype(int), g["year"].astype(int))) for c, g in cw.groupby("concept_id")}
        pool = [byid[c] for c in frame["hydration_order"] if c in links]
        return pool, links, "assembled concept_work.parquet"
    pool, links = [], {}
    for cid in frame["hydration_order"]:
        p = HYD / "retrieval" / f"{cid}.json"
        st = orjson.loads(p.read_bytes()) if p.exists() else {}
        if not st.get("complete"):
            break
        pool.append(byid[cid])
        links[cid] = [(int(w), int(y)) for w, _, y in st["links"]]
    return pool, links, "retrieval/*.json (pre-assembly links)"


def origins(pool: list[dict], links: dict, works_sf: dict[int, int | None]) -> dict[str, dict]:
    out = {}
    for c in pool:
        cid = c["concept_id"]
        if c.get("arm") == "main":
            F = c["F"]
            sel = [w for w, y in links[cid] if F <= y <= F + 2]
            rule = "modal subfield of F..F+2 c-papers"
        else:
            sel = [w for w, y in links[cid] if 2000 <= y <= 2004]
            rule = "modal subfield of 2000-2004 c-papers (reference arm)"
        sfc = Counter(works_sf.get(w) for w in sel if works_sf.get(w))
        out[cid] = {"origin_subfield": sfc.most_common(1)[0][0] if sfc else None, "origin_rule": rule,
                    "origin_n": sum(sfc.values())}
    return out


def keyword_to_concept() -> tuple[dict[str, str], dict[str, dict], dict[str, str]]:
    con = pd.read_parquet(DS2 / "concepts.parquet", columns=["concept_id", "display_name", "level"])
    kw = pd.read_parquet(DS2 / "keywords.parquet", columns=["keyword_slug", "display_name"])
    name2c = {}
    for cid, n in zip(con["concept_id"], con["display_name"]):
        name2c.setdefault(n, cid)
    kw2c = {s: name2c[n] for s, n in zip(kw["keyword_slug"], kw["display_name"]) if n in name2c}
    cinfo = {cid: {"display_name": n, "level": int(lv)} for cid, n, lv in
             zip(con["concept_id"], con["display_name"], con["level"])}
    kwname = dict(zip(kw["keyword_slug"], kw["display_name"]))
    return kw2c, cinfo, kwname


def rank() -> None:
    from hydrate_lib import Store
    pool, links, src = load_pool()
    all_w = sorted({w for c in pool for w, _ in links[c["concept_id"]]})
    logger.info(f"pool {len(pool)} concepts ({src}); {len(all_w)} unique c-papers")
    store = Store(HYD / "work_store")
    recs = store.get_many(all_w)
    sf = {w: r.get("subfield_id") for w, r in recs.items()}
    org = origins(pool, links, sf)
    kw2c, cinfo, kwname = keyword_to_concept()
    W: Counter = Counter()
    Wc: dict[str, Counter] = defaultdict(Counter)
    n_host = Counter()
    for c in pool:
        cid = c["concept_id"]
        o = org[cid]["origin_subfield"]
        for w, _ in links[cid]:
            r = recs.get(w)
            if r is None or r.get("subfield_id") is None or o is None or r["subfield_id"] == o:
                continue
            n_host[cid] += 1
            nodes = {f"C{x}" for x, s in r["concepts"] if x is not None}
            for slug, _ in r["keywords"]:
                if not slug:
                    continue
                nodes.add(kw2c.get(slug, f"K:{slug}"))
            for x in nodes:
                W[x] += 1
                Wc[cid][x] += 1
    tot = sum(W.values())
    rows, cum = [], 0
    for i, (x, n) in enumerate(sorted(W.items(), key=lambda kv: (-kv[1], kv[0])), 1):  # ties broken by node id
        cum += n
        if x.startswith("K:"):
            slug = x[2:]
            rows.append({"node_id": x, "node_type": "keyword", "display_name": kwname.get(slug, slug), "level": None,
                         "host_cooc_weight": n, "coverage_rank": i, "cum_weight_share": cum / tot})
        else:
            ci = cinfo.get(x, {})
            rows.append({"node_id": x, "node_type": "legacy_concept", "display_name": ci.get("display_name"),
                         "level": ci.get("level"), "host_cooc_weight": n, "coverage_rank": i,
                         "cum_weight_share": cum / tot})
    P2.mkdir(exist_ok=True)
    pd.DataFrame(rows).to_parquet(P2 / "node_ranking.parquet", index=False)
    (P2 / "concept_host_weights.json").write_bytes(orjson.dumps({
        "source": src, "origins": org, "n_host": n_host, "Wc": {c: dict(v) for c, v in Wc.items()}}))
    k95 = next((r["coverage_rank"] for r in rows if r["cum_weight_share"] >= TARGET_SHARE), len(rows))
    logger.info(f"nodes {len(rows)}; total host weight {tot}; nodes to 95%: {k95}; host c-paper pairs "
                f"{sum(n_host.values())}; level-0 nodes in top 50: "
                f"{sum(1 for r in rows[:50] if r['level'] == 0)}")


# ------------------------------------------------------------------ fetch
def ckpt_path() -> Path:
    return P2 / "profiles.jsonl"


def load_done() -> dict[tuple[str, str], dict]:
    done = {}
    if ckpt_path().exists():
        for line in ckpt_path().read_text().splitlines():
            if line.strip():
                r = orjson.loads(line)
                done[(r["node_id"], r["block"])] = r
    return done


async def fetch(cap: int, rps: float, max_nodes: int) -> None:
    os.environ.setdefault("AII_STEP", "p2_profiles")
    from common import CreditExhausted, OAClient, RateLimiter
    rk = pd.read_parquet(P2 / "node_ranking.parquet")
    done = load_done()
    stop = {"reason": None}
    async with OAClient(cap=cap) as oa:
        oa.lim_list = RateLimiter(rps)
        # verify the keyword filter once (1 credit) before any keyword node is fetched
        kw_ok = True
        first_kw = rk[rk["node_type"] == "keyword"].head(1)
        if len(first_kw):
            slug = first_kw["node_id"].iloc[0][2:]
            d = await oa.get("/works", {"filter": f"keywords.id:{slug},publication_year:2010-2014",
                                        "group_by": "primary_topic.subfield.id:include_unknown", "per_page": 200})
            kw_ok = bool(d) and "__error__" not in d and "meta" in d
            logger.info(f"keyword filter check on {slug}: ok={kw_ok} count={(d or {}).get('meta', {}).get('count')}")
        f = ckpt_path().open("ab")

        async def one(row, block: str) -> dict | None:
            nid = row.node_id
            filt = (f"concepts.id:{nid}" if row.node_type == "legacy_concept" else f"keywords.id:{nid[2:]}")
            params = {"filter": f"{filt},publication_year:{block}",
                      "group_by": "primary_topic.subfield.id:include_unknown", "per_page": 200}
            d = await oa.get("/works", params)
            if d is None or "__error__" in d:
                logger.warning(f"{nid} {block}: {d}")
                return None
            groups = {str(g["key"]).rstrip("/").split("/")[-1]: int(g["count"]) for g in d.get("group_by", [])}
            groups = {("unknown" if (k == "unknown" or not k.isdigit()) else k): v for k, v in groups.items()}
            total = int(d["meta"]["count"])
            return {"node_id": nid, "node_type": row.node_type, "display_name": row.display_name,
                    "level": None if pd.isna(row.level) else int(row.level), "block": block, "total": total,
                    "subfield_counts": groups, "n_groups": len(groups),
                    "truncated_top200": len(groups) >= 200 and sum(groups.values()) < total,
                    "coverage_rank": int(row.coverage_rank), "host_cooc_weight": int(row.host_cooc_weight),
                    "cum_weight_share": float(row.cum_weight_share), "frame": "all_types (no type filter)",
                    "retrieved_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "credits": 1,
                    "request_filter": params["filter"]}

        n_nodes = 0
        batch: list = []
        rows = [r for r in rk.itertuples(index=False) if kw_ok or r.node_type != "keyword"]
        for row in rows:
            if max_nodes and n_nodes >= max_nodes:
                stop["reason"] = f"max_nodes {max_nodes}"
                break
            prev_share = row.cum_weight_share - row.host_cooc_weight / max(1, rk["host_cooc_weight"].sum())
            if prev_share >= TARGET_SHARE:
                stop["reason"] = "95% cumulative host weight reached"
                break
            todo = [b for b in BLOCKS if (row.node_id, b) not in done]
            n_nodes += 1
            if not todo:
                continue
            if not oa.can_spend(len(todo)) or (oa.remaining_keywide is not None
                                               and oa.remaining_keywide < GUARD_REMAINING + len(todo)):
                stop["reason"] = (f"credit stop: spent={oa.spent_today} cap={cap} "
                                  f"remaining_keywide={oa.remaining_keywide}")
                break
            batch.append((row, todo))
            if len(batch) >= 4:
                await run_batch(batch, one, f, done)
                batch = []
            if n_nodes % 50 == 0:
                logger.info(f"nodes {n_nodes} rank {row.coverage_rank} cum {row.cum_weight_share:.3f} "
                            f"credits(this proc) {oa.spent_today} rem {oa.remaining_keywide}")
        if batch:
            try:
                await run_batch(batch, one, f, done)
            except CreditExhausted as e:
                stop["reason"] = f"CreditExhausted {e}"
        f.close()
    logger.info(f"fetch stopped: {stop['reason']}; profiles now {len(load_done())}")
    (P2 / "fetch_stop.json").write_bytes(orjson.dumps({"reason": stop["reason"], "utc": time.strftime(
        "%Y-%m-%dT%H:%M:%SZ", time.gmtime())}))


async def run_batch(batch, one, f, done) -> None:
    from common import CreditExhausted
    tasks = [(row, b) for row, todo in batch for b in todo]
    res = await asyncio.gather(*[one(row, b) for row, b in tasks], return_exceptions=True)
    for (row, b), r in zip(tasks, res):
        if isinstance(r, CreditExhausted):
            raise r
        if isinstance(r, Exception):
            logger.error(f"{row.node_id} {b}: {r!r}")
            continue
        if r:
            f.write(orjson.dumps(r) + b"\n")
            done[(r["node_id"], b)] = r
    f.flush()


# ------------------------------------------------------------------ coverage
def coverage() -> None:
    hw = orjson.loads((P2 / "concept_host_weights.json").read_bytes())
    done = load_done()
    full = {n for n in {k[0] for k in done} if all((n, b) in done for b in BLOCKS)}
    frame = orjson.loads((HYD / "sample_frame_frozen.json").read_bytes())
    byid = {x["concept_id"]: x for x in frame["eligible"] + frame["reference"]}
    rows, tot_w, tot_cov = [], 0, 0
    for cid, wc in hw["Wc"].items():
        w = sum(wc.values())
        cov = sum(v for x, v in wc.items() if x in full)
        tot_w += w
        tot_cov += cov
        o = hw["origins"][cid]
        rows.append({"concept_id": cid, "phrase": byid[cid]["phrase"], "arm": byid[cid].get("arm"),
                     "origin_subfield": o["origin_subfield"], "origin_rule": o["origin_rule"],
                     "n_host_cpapers": int(hw["n_host"].get(cid, 0)), "n_distinct_nodes": len(wc),
                     "host_weight": w, "covered_weight_share": round(cov / w, 4) if w else None})
    for cid, o in hw["origins"].items():
        if cid not in hw["Wc"]:
            rows.append({"concept_id": cid, "phrase": byid[cid]["phrase"], "arm": byid[cid].get("arm"),
                         "origin_subfield": o["origin_subfield"], "origin_rule": o["origin_rule"],
                         "n_host_cpapers": 0, "n_distinct_nodes": 0, "host_weight": 0, "covered_weight_share": None})
    overall = {"concept_id": "__OVERALL__", "n_concepts": len(rows), "host_weight": tot_w,
               "covered_weight_share": round(tot_cov / tot_w, 4) if tot_w else None,
               "n_nodes_complete_4_blocks": len(full), "n_profiles": len(done), "links_source": hw["source"]}
    OUT.mkdir(exist_ok=True)
    (OUT / "nativeness_coverage.json").write_bytes(orjson.dumps({"overall": overall, "concepts": rows}))
    logger.info(f"coverage: {overall}")


@logger.catch(reraise=True)
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["rank", "fetch", "coverage"])
    ap.add_argument("--cap", type=int, default=int(os.environ.get("AII_ARTIFACT_CAP", "3700")))
    ap.add_argument("--rps", type=float, default=2.0)
    ap.add_argument("--max-nodes", type=int, default=0)
    a = ap.parse_args()
    setup_logging()
    if a.stage == "rank":
        rank()
    elif a.stage == "fetch":
        asyncio.run(fetch(a.cap, a.rps, a.max_nodes))
    else:
        coverage()


if __name__ == "__main__":
    main()
