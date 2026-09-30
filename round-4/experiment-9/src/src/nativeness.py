"""STAGE 6: nativeness profiles for the partners of MeSH entry events.

6a  $0 fallback admissibility check (written + hashed BEFORE any MeSH group_by call):
    s_bg(node, blk, d) = design-weighted share of the node's background-sample works in blk with primary subfield d
    (missing if < 20 works). Over the triples T = (node, blk, d) of the main SCREEN MAIN kw5 events (gate 2 sample),
    weight = tag count: r = weighted Pearson(s_bg, s_exact); admitted iff r >= 0.9 and bg coverage of T >= 0.6.
6b  exact profiles: needed = {(node, block_of(e))} over MESH_MAIN entry-year partners + G1 window partners, weighted
    by tag count. Reuse dataset_5 p2/profiles.jsonl for free; rank the rest by weight and fetch top-down
    (1 group_by list call = 1 credit each) until the call cap, 95% cumulative needed weight, or the key-wide guard.
    Smoke first: 3 re-fetches of dataset_5 profiles must match within 2% (live-index drift) before the capped run.
6c  source decision: exact (reused + fetched) is primary; bg values fill gaps ONLY if admitted in 6a (nat_source).
"""
from __future__ import annotations

import json
import pickle
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import orjson
import pandas as pd
from loguru import logger

import common
from common import BG, CACHE, D5, RESULTS, CreditStop, OpenAlex, dump, sha256_file

NAT = RESULTS / "nativeness"
NAT.mkdir(exist_ok=True)
FETCHED = NAT / "profiles_fetched.jsonl"
CALL_CAP = 3000
HYDRATION_RESERVE = 70
GUARD = 150
TARGET = 0.95


def block_of(e: int) -> str:
    from features import block_of as b  # vendored
    return b(int(e))


def load_d5_profiles() -> dict:
    from io_load import load_profiles  # vendored; returns {(node, block): (total_known, counts, trunc)}
    return load_profiles()


def parse_profile(rec: dict) -> tuple[int, dict, bool]:
    sc = rec["subfield_counts"]
    unk = int(sc.get("unknown", 0))
    return int(rec["total"]) - unk, {int(k): int(v) for k, v in sc.items() if k != "unknown"}, bool(rec.get("truncated_top200"))


def load_fetched() -> dict:
    out = {}
    if FETCHED.exists():
        for line in FETCHED.read_text().splitlines():
            if line.strip():
                r = orjson.loads(line)
                out[(int(r["node_id"][1:]), r["block"])] = parse_profile(r)
    return out


def all_profiles(include_fetched: bool = True) -> dict:
    p = dict(load_d5_profiles())
    if include_fetched:
        for k, v in load_fetched().items():
            p.setdefault(k, v)
    return p


# ------------------------------------------------------------------------------------------------------------ 6a
def bg_shares(nodes: set[int]) -> dict:
    b = pd.read_parquet(BG / "bg_work_sample.parquet", columns=["block", "concept_ids", "subfield_id", "weight"])
    b = b[b.block.isin(["2000-2004", "2005-2009", "2010-2014"])]
    acc = defaultdict(lambda: [0, 0.0, defaultdict(float)])
    for blk, cids, sf, w in zip(b.block, b.concept_ids, b.subfield_id, b.weight):
        if cids is None:
            continue
        for c in cids:
            n = int(c[1:])
            if n in nodes:
                a = acc[(n, blk)]
                a[0] += 1
                a[1] += w
                if sf is not None and sf >= 0:
                    a[2][int(sf)] += w
    out = {}
    for k, (n, wt, d) in acc.items():
        if n >= 20 and wt > 0:
            out[k] = (n, wt, dict(d))
    return out


def s_bg(bg: dict, node: int, blk: str, d: int) -> float | None:
    v = bg.get((node, blk))
    if v is None:
        return None
    return v[2].get(d, 0.0) / v[1]


def fallback_check() -> dict:
    import models as vmodels
    from features import Nativeness, event_tags
    Gm = pickle.loads((common.RESULTS / "cache" / "prepared.pkl").read_bytes())
    df = pd.read_parquet(common.GATE / "gate2" / "screen_events_with_outcomes.parquet",
                         columns=["concept_id", "d", "e", "arm", "fold", "kw5", "MAIN", "A_cont", "CT", "prox_od", "RD",
                                  "log_n_partner_tags", "cov", "demic", "mean_topic_score", "boundary_share",
                                  "abstract_share", "mom_d", "log_centrality", "log_W1", "n_entry_papers"])
    s = vmodels.primary_sample(df)
    con = Gm["concepts"].set_index("concept_id")
    nat = Nativeness(Gm["prof"])
    trip = defaultdict(float)
    ev_nodes = []
    for ev in s.itertuples():
        c = con.loc[ev.concept_id]
        own = int(c.own_node) if pd.notna(c.own_node) else None
        _, _, nn = event_tags(Gm, ev.concept_id, int(ev.d), int(ev.e), own)
        blk = block_of(int(ev.e))
        ev_nodes.append((nn, blk, int(ev.d)))
        for j in nn:
            trip[(int(j), blk, int(ev.d))] += 1
    del Gm
    nodes = {k[0] for k in trip}
    bg = bg_shares(nodes)
    xs, ys, ws, w_all, w_bg, w_ex = [], [], [], 0.0, 0.0, 0.0
    for (j, blk, d), w in trip.items():
        w_all += w
        sb = s_bg(bg, j, blk, d)
        se = nat.share(j, blk, d)
        if sb is not None:
            w_bg += w
        if se is not None:
            w_ex += w
        if sb is not None and se is not None:
            xs.append(sb)
            ys.append(se)
            ws.append(w)
    xs, ys, ws = np.array(xs), np.array(ys), np.array(ws)

    def wcorr(a, b, w):
        ma, mb = np.average(a, weights=w), np.average(b, weights=w)
        cov = np.average((a - ma) * (b - mb), weights=w)
        return float(cov / np.sqrt(np.average((a - ma) ** 2, weights=w) * np.average((b - mb) ** 2, weights=w)))

    r = wcorr(xs, ys, ws) if len(xs) > 2 else None
    a_bg, a_ex = [], []
    for nn, blk, d in ev_nodes:
        sb = [s_bg(bg, int(j), blk, d) for j in nn]
        sb = [x for x in sb if x is not None]
        a_bg.append(np.mean(sb) if sb else np.nan)
    a_ex = s.A_cont.to_numpy()
    m = ~np.isnan(a_bg)
    r_ev = float(np.corrcoef(np.array(a_bg)[m], a_ex[m])[0, 1]) if m.sum() > 2 else None
    out = {"rule": "admitted iff weighted Pearson r(s_bg, s_exact) >= 0.9 over main screen triples AND bg coverage of "
                   "triple tag weight >= 0.6 (bg share missing if < 20 bg works in the block)",
           "n_triples": len(trip), "n_triples_both": int(len(xs)), "r_weighted": r,
           "bg_coverage_tag_weight": w_bg / w_all, "exact_coverage_tag_weight": w_ex / w_all,
           "r_event_level_A_cont": r_ev, "n_events": int(len(s)), "n_events_with_bg_A": int(m.sum())}
    out["admitted"] = bool(r is not None and r >= 0.9 and out["bg_coverage_tag_weight"] >= 0.6)
    p = RESULTS / "nativeness_fallback_check.json"
    dump(p, out)
    (RESULTS / "nativeness_fallback_check.sha256").write_text(
        f"{sha256_file(p)}  nativeness_fallback_check.json  written {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}\n")
    logger.info(f"6a fallback check: {out}")
    return out


# ------------------------------------------------------------------------------------------------------------ 6b
def needed_pairs(G: dict, ev: pd.DataFrame) -> pd.DataFrame:
    """(node, block) -> tag weight over MESH_MAIN entry-year partners and G1 window partners."""
    from events_mesh import entry_partners
    W = G["W"]
    con = G["concepts"].set_index("concept_id")
    acc = defaultdict(lambda: [0.0, 0.0])
    for x in ev[ev.MESH_MAIN].itertuples():
        c = con.loc[x.concept_id]
        own = set(c.own_nodes)
        r, y = G["links"][x.concept_id]
        sub = W["sub"][r]
        er = r[(sub == x.d) & (y == x.e)]
        for a in entry_partners(G, er, own):
            for j in a.tolist():
                acc[(j, block_of(x.e))][0] += 1
        if pd.notna(x.g1_t):
            t = int(x.g1_t)
            wr = r[(sub == x.d) & (y >= t) & (y <= t + 1)]
            for a in entry_partners(G, wr, own):
                for j in a.tolist():
                    acc[(j, block_of(t))][1] += 1
    df = pd.DataFrame([{"node": k[0], "block": k[1], "w_main": v[0], "w_g1": v[1], "w": v[0] + v[1]}
                       for k, v in acc.items()])
    return df.sort_values(["w", "node", "block"], ascending=[False, True, True]).reset_index(drop=True)


def fetch_one(oa: OpenAlex, node: int, block: str) -> dict:
    params = {"filter": f"concepts.id:C{node},publication_year:{block}",
              "group_by": "primary_topic.subfield.id:include_unknown", "per_page": 200}
    d = oa.get("/works", params, tag=f"C{node} {block}")
    groups = {str(g["key"]).rstrip("/").split("/")[-1]: int(g["count"]) for g in d.get("group_by", [])}
    groups = {("unknown" if (k == "unknown" or not k.isdigit()) else k): v for k, v in groups.items()}
    total = int(d["meta"]["count"])
    return {"node_id": f"C{node}", "node_type": "legacy_concept", "block": block, "total": total,
            "subfield_counts": groups, "n_groups": len(groups),
            "truncated_top200": len(groups) >= 200 and sum(groups.values()) < total,
            "frame": "all_types (no type filter)", "retrieved_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "request_filter": params["filter"]}


def smoke(oa: OpenAlex, need: pd.DataFrame, d5: dict) -> dict:
    free = need[[(int(n), b) in d5 for n, b in zip(need.node, need.block)]].head(3)
    comp = []
    for x in free.itertuples():
        rec = fetch_one(oa, int(x.node), x.block)
        tot, counts, _ = parse_profile(rec)
        t5, c5, _ = d5[(int(x.node), x.block)]
        top = sorted(c5, key=lambda k: -c5[k])[:5]
        rel = [abs(counts.get(k, 0) - c5[k]) / max(c5[k], 1) for k in top]
        comp.append({"node": int(x.node), "block": x.block, "total_known_live": tot, "total_known_d5": t5,
                     "total_rel_diff": abs(tot - t5) / max(t5, 1), "top5_max_rel_diff": max(rel)})
    ok = all(c["total_rel_diff"] < 0.02 and c["top5_max_rel_diff"] < 0.02 for c in comp)
    return {"comparisons": comp, "pass_2pct": ok}


def run(mini: bool = False) -> dict:
    import events_mesh
    import load_mesh
    G = load_mesh.prepare()
    ev = events_mesh.load_events(mini)
    fb_path = RESULTS / "nativeness_fallback_check.json"
    fb = json.loads(fb_path.read_text()) if fb_path.exists() else fallback_check()
    need = needed_pairs(G, ev)
    d5 = load_d5_profiles()
    need["free"] = [(int(n), b) in d5 for n, b in zip(need.node, need.block)]
    have = load_fetched()
    need["fetched"] = [(int(n), b) in have for n, b in zip(need.node, need.block)]
    tot_w = need.w.sum()
    summ = {"n_needed_pairs": int(len(need)), "needed_tag_weight": float(tot_w),
            "free_pairs": int(need.free.sum()), "free_weight_share": float(need.w[need.free].sum() / tot_w)}
    logger.info(f"6b needed: {summ}")
    if mini:
        need.to_csv(RESULTS / "mini" / "nativeness_needed.csv", index=False)
        dump(RESULTS / "mini" / "nativeness_summary.json", summ)
        return summ
    oa = OpenAlex("nativeness", rps=4.0, guard_remaining=GUARD)
    stop = "not started"
    smoke_res = None
    if oa.available():
        try:
            rl = oa.rate_limit()
            oa.remaining = int(rl.get("credits_remaining", 0))
            logger.info(f"credit probe: remaining {oa.remaining}")
            sm_path = NAT / "smoke.json"
            if sm_path.exists():
                smoke_res = json.loads(sm_path.read_text())
            else:
                smoke_res = smoke(oa, need, d5)
                dump(sm_path, smoke_res)
            logger.info(f"smoke: {smoke_res}")
            if not smoke_res["pass_2pct"]:
                logger.warning("smoke comparison drift > 2% -- fetch continues but drift is reported")
            cap = min(CALL_CAP, max(0, (oa.remaining or 0) - GUARD - HYDRATION_RESERVE))
            todo = need[~need.free & ~need.fetched].copy()
            covered_w = need.w[need.free | need.fetched].sum()
            order = []
            for x in todo.itertuples():
                if covered_w / tot_w >= TARGET:
                    break
                if len(order) >= cap:
                    break
                order.append((int(x.node), x.block))
                covered_w += x.w
            logger.info(f"fetch plan: {len(order)} calls (cap {cap}); projected weight coverage {covered_w / tot_w:.3f}")
            stop = "plan complete"
            with open(FETCHED, "a") as f, ThreadPoolExecutor(4) as ex:
                for i in range(0, len(order), 40):
                    chunk = order[i:i + 40]
                    futs = [ex.submit(fetch_one, oa, n, b) for n, b in chunk]
                    cs = False
                    for fu in futs:
                        try:
                            rec = fu.result()
                            f.write(orjson.dumps(rec).decode() + "\n")
                        except CreditStop as e:
                            cs = True
                            stop = f"CreditStop: {e}"
                        except RuntimeError as e:
                            logger.error(f"fetch error: {e}")
                    f.flush()
                    if cs:
                        break
                    if i % 400 == 0:
                        logger.info(f"fetched {i + len(chunk)}/{len(order)}; credits {oa.credits}; remaining {oa.remaining}")
        except CreditStop as e:
            stop = f"CreditStop at probe: {e}"
    else:
        stop = "no OPENALEX_API_KEY: exact reuse only"
    have = load_fetched()
    need["fetched"] = [(int(n), b) in have for n, b in zip(need.node, need.block)]
    need["exact"] = need.free | need.fetched
    need.to_csv(NAT / "needed_pairs.csv", index=False)
    summ.update({"fetch_stop": stop, "calls_this_run": oa.calls, "credits_this_run": oa.credits,
                 "remaining_after": oa.remaining, "fetched_pairs_total": int(need.fetched.sum()),
                 "exact_weight_share": float(need.w[need.exact].sum() / tot_w),
                 "exact_weight_share_main_only": float(need.w_main[need.exact].sum() / need.w_main.sum()),
                 "fallback_admitted": fb["admitted"], "smoke": smoke_res,
                 "source_decision": "exact (dataset_5 reuse + fetched) primary; bg fill " +
                                    ("USED for gaps (admitted)" if fb["admitted"] else "NOT used (not admitted)")})
    dump(RESULTS / "nativeness_ledger_summary.json", summ)
    logger.info(f"nativeness: {summ}")
    return summ
