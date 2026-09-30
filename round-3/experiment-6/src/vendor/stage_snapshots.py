#!/usr/bin/env python3
"""Stage 2: 25 yearly concept-concept snapshots (3-year trailing windows) + pool attachment.

Per snapshot y (window [y-2, y]):
  * background co-word graph from the design-weighted whole-science sample (post-stratified w_year);
  * association-strength weights, kept graph (>= 2 raw sample co-occurrences), Leiden (RBConfiguration, best of 5 seeds);
  * exact attachment of the pool concepts (frame-type c-papers) -> strength, strength percentile, AS neighbours,
    top-20 closure over the Chung-Lu expectation, participation (raw + rarefied), within-module z,
    sampled betweenness (networkit, 500 pivots) and the cross-community-bridging flag;
  * pool-pool edges from shared c-papers.
Then alluvial Jaccard matching of communities across consecutive snapshots -> persistent community ids.

Usage: stage_snapshots.py [--years 2008 2013] [--workers 4]
"""
from __future__ import annotations

import argparse
import gc
import json
import multiprocessing as mp
import time
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
from itertools import combinations

import numpy as np
import pandas as pd
from loguru import logger

import config as C
import lib_metrics as lm
from netcore import build_cograph, leiden_best

SNAP = C.WORK / "snapshots"
SNAP.mkdir(parents=True, exist_ok=True)


def _pct_rank(values: np.ndarray, x: float) -> float:
    """Percentile (0-100) of x within sorted `values` (mid-rank for ties)."""
    lo = np.searchsorted(values, x, side="left")
    hi = np.searchsorted(values, x, side="right")
    return 100.0 * (lo + 0.5 * (hi - lo)) / len(values)


def _comm_weights(tag_counts: dict, idx: dict, memb: np.ndarray) -> dict:
    out: Counter = Counter()
    for j, x in tag_counts.items():
        p = idx.get(j)
        if p is not None and memb[p] >= 0:
            out[int(memb[p])] += x
    return dict(out)


def _count_tags(tag_lists) -> dict:
    if len(tag_lists) == 0:
        return {}
    flat = np.concatenate(list(tag_lists)) if len(tag_lists) else np.zeros(0, dtype=np.int64)
    if flat.size == 0:
        return {}
    u, c = np.unique(flat, return_counts=True)
    return dict(zip(u.tolist(), c.tolist()))


def _rarefied_P(tag_lists: list, idx: dict, memb: np.ndarray, m: int, draws: int, seed: int) -> float:
    ds = lm.rarefied_draws(len(tag_lists), m, draws, seed)
    if not ds:
        return np.nan
    vals = []
    for d in ds:
        cw = _comm_weights(_count_tags([tag_lists[i] for i in d]), idx, memb)
        vals.append(lm.participation(cw))
    vals = np.array(vals, dtype=float)
    return float(np.nanmean(vals)) if np.isfinite(vals).any() else np.nan


def build_snapshot(y: int, write: bool = True) -> dict:
    import networkit as nk
    nk.setNumberOfThreads(1)
    nk.engineering.setSeed(20260928 + y, False)  # deterministic betweenness pivots
    C.setup_logging(f"snap_{y}")
    t0 = time.time()
    y0 = y - C.SPEC["window"] + 1
    bg = pd.read_parquet(C.WORK / "bg.parquet", columns=["year", "w_year", "tags"])
    bg = bg[(bg.year >= y0) & (bg.year <= y)]
    g = build_cograph(list(bg.tags.values), bg.w_year.values, C.SPEC["kept_edge_min_raw"])
    del bg
    gc.collect()
    idx = g.index_of()
    memb, modularity, n_kept_nodes = leiden_best(g, **{k: C.SPEC["leiden"][k] for k in ("resolution", "seed", "n_runs")})
    n_comm = int(memb.max() + 1) if (memb >= 0).any() else 0
    comm_sizes = np.bincount(memb[memb >= 0]) if n_comm else np.zeros(0)
    logger.info(f"y={y} works={g.n_works} nodes={len(g.nodes)} edges={len(g.c)} kept_edges={int(g.kept.sum())} "
                f"kept_nodes={n_kept_nodes} comms={n_comm} (>=5 nodes: {int((comm_sizes >= 5).sum())}) Q={modularity:.3f}")

    # within-community strength for every bg node
    same = (memb[g.ei] == memb[g.ej]) & (memb[g.ei] >= 0)
    k_own = np.zeros(len(g.nodes))
    np.add.at(k_own, g.ei[same], g.c[same])
    np.add.at(k_own, g.ej[same], g.c[same])

    # ---- pool attachment
    pool = pd.read_parquet(C.WORK / "pool.parquet", columns=["concept_id", "fold"])
    cp = pd.read_parquet(C.WORK / "cp.parquet", columns=["concept_id", "work_id", "year", "frame", "tags"])
    cp = cp[(cp.year >= y0) & (cp.year <= y)]
    S_total = float(g.s.sum())
    eps = float(g.c.min()) if len(g.c) else 1.0
    s_sorted_bg = np.sort(g.s)
    rows, pool_edges_nk = [], []
    kept_nodes_mask = memb >= 0
    for cid in pool.concept_id.values:
        sub = cp[cp.concept_id == cid]
        fr = sub[sub.frame]
        x_frame = _count_tags(list(fr.tags.values))
        x_all = _count_tags(list(sub.tags.values))
        n_c = len(fr)
        s_c = float(sum(x_frame.values()))
        r = dict(concept_id=cid, year=y, n_frame=n_c, n_all=len(sub), strength=s_c, n_tags_frame=len(x_frame),
                 n_tags_all=len(x_all))
        # association strength neighbours (frame-type)
        js = np.array([idx[j] for j in x_frame if j in idx], dtype=np.int64)
        closure = closure_obs = closure_exp = np.nan
        nK = 0
        K_ids: list[int] = []
        if n_c > 0 and len(js):
            xs = np.array([x_frame[int(g.nodes[p])] for p in js], dtype=float)
            AS_c = xs * g.Wtot / (n_c * g.W[js])
            order = np.argsort(-AS_c, kind="stable")
            K = js[order[: C.SPEC["topk_closure"]]]
            nK = len(K)
            K_ids = g.nodes[K].tolist()
            if nK >= C.SPEC["closure_min_neighbours"]:
                sub_c = g.Cw[K][:, K]
                closure_obs = float(sub_c.sum() / 2.0)
                closure_exp = lm.chung_lu_expected(g.s[K], S_total)
                closure = lm.closure_log_ratio(closure_obs, closure_exp, eps)
        r.update(closure=closure, closure_obs=closure_obs, closure_exp=closure_exp, closure_nK=nK,
                 top_AS=json.dumps(K_ids[:20]))
        # participation / community (all types, raw + rarefied)
        cw_all = _comm_weights(x_all, idx, memb)
        r["P_raw"] = lm.participation(cw_all)
        r["n_comm_touched"] = int(sum(1 for v in cw_all.values() if v > 0))
        r["plural_comm_raw"] = int(max(cw_all, key=cw_all.get)) if cw_all else -1
        tl = list(sub.tags.values)
        r["P_rar"] = _rarefied_P(tl, idx, memb, C.SPEC["rarefy_m"], C.SPEC["rarefy_draws"], lm.stable_seed(cid, y, "P"))
        r["P_rar_m5"] = _rarefied_P(tl, idx, memb, C.SPEC["rarefy_m_sensitivity"], C.SPEC["rarefy_draws"],
                                    lm.stable_seed(cid, y, "P5"))
        # within-module z (frame-type, population units)
        cw_fr = _comm_weights(x_frame, idx, memb)
        if cw_fr:
            s_star = max(cw_fr, key=cw_fr.get)
            peers = k_own[memb == s_star]
            r["wmz"] = lm.within_module_z(float(cw_fr[s_star]), peers)
            tot_fr = sum(cw_fr.values())
            r["n_comm_10pct_frame"] = int(sum(1 for v in cw_fr.values() if v >= C.SPEC["early_bridging"]["min_comm_share"] * tot_fr))
        else:
            r["wmz"] = np.nan
            r["n_comm_10pct_frame"] = 0
        # betweenness attachment edges (frame tags in kept graph)
        if n_c > 0:
            pool_edges_nk.append((cid, [int(p) for p in js if kept_nodes_mask[p]]))
        rows.append(r)
    pr = pd.DataFrame(rows)
    # strength percentile among all nodes (bg + active pool nodes with frame papers)
    pool_s = pr.loc[pr.n_frame > 0, "strength"].values
    all_s = np.sort(np.concatenate([g.s, pool_s]))
    pr["pct"] = [(_pct_rank(all_s, s) if n > 0 else 0.0) for s, n in zip(pr.strength, pr.n_frame)]
    pr["pct_bg_only"] = [(_pct_rank(s_sorted_bg, s) if n > 0 else 0.0) for s, n in zip(pr.strength, pr.n_frame)]

    # ---- sampled betweenness on the kept graph + pool nodes
    tb = time.time()
    kept_nodes = np.where(kept_nodes_mask)[0]
    remap = -np.ones(len(g.nodes), dtype=np.int64)
    remap[kept_nodes] = np.arange(len(kept_nodes))
    n_bg = len(kept_nodes)
    G = nk.Graph(n_bg + len(pool_edges_nk), weighted=False, directed=False)
    for a, b in zip(remap[g.ei[g.kept]], remap[g.ej[g.kept]]):
        G.addEdge(int(a), int(b))
    pool_pos = {}
    for k, (cid, nbrs) in enumerate(pool_edges_nk):
        u = n_bg + k
        pool_pos[cid] = u
        for p in nbrs:
            G.addEdge(u, int(remap[p]))
    btw = nk.centrality.EstimateBetweenness(G, C.SPEC["betweenness_pivots"], normalized=True, parallel=False)
    btw.run()
    scores = np.array(btw.scores())
    sorted_sc = np.sort(scores)
    pr["btw"] = [scores[pool_pos[c]] if c in pool_pos else np.nan for c in pr.concept_id]
    pr["btw_pct"] = [(_pct_rank(sorted_sc, scores[pool_pos[c]]) if c in pool_pos else np.nan) for c in pr.concept_id]
    eb = C.SPEC["early_bridging"]
    pr["cross_comm_flag"] = (pr.btw_pct >= eb["btw_pct"]) & (pr.n_comm_10pct_frame >= eb["min_comms"])
    logger.info(f"y={y} betweenness on {G.numberOfNodes()} nodes / {G.numberOfEdges()} edges in {time.time()-tb:.1f}s")

    # ---- pool-pool edges (shared c-papers, all types)
    pp: Counter = Counter()
    for _, grp in cp.groupby("work_id").concept_id:
        cs = sorted(set(grp))
        for a, b in combinations(cs, 2):
            pp[(a, b)] += 1
    pool_pool = pd.DataFrame([(a, b, n) for (a, b), n in pp.items()], columns=["c1", "c2", "n_shared"])

    info = dict(year=y, n_works=g.n_works, n_nodes=int(len(g.nodes)), n_edges=int(len(g.c)),
                n_kept_edges=int(g.kept.sum()), n_kept_nodes=int(n_kept_nodes), n_comm=n_comm,
                n_comm_ge5=int((comm_sizes >= 5).sum()), modularity=modularity, Wtot=g.Wtot,
                btw_nodes=int(G.numberOfNodes()), btw_edges=int(G.numberOfEdges()), secs=round(time.time() - t0, 1),
                n_pool_active=int((pr.n_all > 0).sum()), n_pool_pool_edges=len(pool_pool))
    if write:
        pd.DataFrame(dict(i=g.nodes[g.ei], j=g.nodes[g.ej], c_ij=g.c.astype(np.float32), raw_ij=g.raw.astype(np.int32),
                          AS_ij=g.AS.astype(np.float32), kept=g.kept)).to_parquet(SNAP / f"edges_y{y}.parquet", index=False)
        pd.DataFrame(dict(node=g.nodes, W=g.W, strength=g.s, comm=memb, k_own=k_own)).to_parquet(
            SNAP / f"nodes_y{y}.parquet", index=False)
        pr.to_parquet(SNAP / f"pool_metrics_y{y}.parquet", index=False)
        pool_pool.to_parquet(SNAP / f"pool_edges_y{y}.parquet", index=False)
        (SNAP / f"info_y{y}.json").write_text(json.dumps(info))
    logger.info(f"y={y} done in {info['secs']}s")
    return info


def alluvial() -> pd.DataFrame:
    """Match communities of consecutive snapshots by Jaccard of node sets; assign persistent ids."""
    years = C.SPEC["years"]
    thr, min_size = C.SPEC["alluvial_min_jaccard"], C.SPEC["alluvial_min_comm_size"]
    next_id = 0
    prev_map: dict[int, int] = {}
    prev_sets: dict[int, set] = {}
    events, comm_rows = [], []
    for y in years:
        nd = pd.read_parquet(SNAP / f"nodes_y{y}.parquet", columns=["node", "comm"])
        nd = nd[nd.comm >= 0]
        sizes = nd.comm.value_counts()
        big = set(sizes[sizes >= min_size].index)
        cur_sets = {int(c): set(grp.node.tolist()) for c, grp in nd[nd.comm.isin(big)].groupby("comm")}
        cur_map: dict[int, int] = {}
        if prev_sets:
            pairs = []
            # candidate pairs through shared nodes
            node2prev = {}
            for pc, s in prev_sets.items():
                for n in s:
                    node2prev[n] = pc
            for cc, s in cur_sets.items():
                inter = Counter(node2prev[n] for n in s if n in node2prev)
                for pc, k in inter.items():
                    jac = k / (len(s) + len(prev_sets[pc]) - k)
                    pairs.append((jac, pc, cc, k))
            pairs.sort(reverse=True)
            used_p, used_c = set(), set()
            for jac, pc, cc, k in pairs:
                if jac < thr:
                    break
                if pc in used_p or cc in used_c:
                    continue
                cur_map[cc] = prev_map[pc]
                used_p.add(pc)
                used_c.add(cc)
                events.append(dict(year=y, event="continue", pid=prev_map[pc], jaccard=jac))
            # splits / merges: >= 30% of a community's surviving nodes flowing to >= 2 partners
            for pc, s in prev_sets.items():
                flows = [k for (jac, p2, cc, k) in pairs if p2 == pc]
                surv = sum(flows)
                if surv and sum(1 for k in flows if k >= 0.3 * surv) >= 2:
                    events.append(dict(year=y, event="split", pid=prev_map[pc], jaccard=np.nan))
                if pc not in used_p:
                    events.append(dict(year=y, event="death", pid=prev_map[pc], jaccard=np.nan))
            for cc, s in cur_sets.items():
                flows = [k for (jac, p2, c2, k) in pairs if c2 == cc]
                surv = sum(flows)
                if surv and sum(1 for k in flows if k >= 0.3 * surv) >= 2:
                    events.append(dict(year=y, event="merge", pid=cur_map.get(cc, -1), jaccard=np.nan))
        for cc in cur_sets:
            if cc not in cur_map:
                cur_map[cc] = next_id
                events.append(dict(year=y, event="birth", pid=next_id, jaccard=np.nan))
                next_id += 1
        for cc, pid in cur_map.items():
            comm_rows.append(dict(year=y, comm=cc, pid=pid, size=len(cur_sets[cc])))
        prev_map, prev_sets = cur_map, cur_sets
    cm = pd.DataFrame(comm_rows)
    ev = pd.DataFrame(events)
    (C.WORK / "communities").mkdir(exist_ok=True)
    cm.to_parquet(C.WORK / "communities" / "persistent_ids.parquet", index=False)
    ev.to_parquet(C.WORK / "communities" / "alluvial_events.parquet", index=False)
    logger.info(f"alluvial: {cm.pid.nunique()} persistent communities; events {ev.event.value_counts().to_dict()}")
    return cm


@logger.catch(reraise=True)
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--years", type=int, nargs="*", default=None)
    ap.add_argument("--workers", type=int, default=min(4, C.detect_cpus()))
    ap.add_argument("--skip-existing", action="store_true")
    a = ap.parse_args()
    C.setup_logging("stage_snapshots")
    C.set_ram_limit(26)
    years = a.years or C.SPEC["years"]
    if a.skip_existing:
        years = [y for y in years if not (SNAP / f"info_y{y}.json").exists()]
    logger.info(f"building snapshots {years} with {a.workers} workers")
    t0 = time.time()
    infos = []
    with ProcessPoolExecutor(max_workers=a.workers, mp_context=mp.get_context("spawn")) as ex:
        futs = {ex.submit(build_snapshot, y): y for y in years}
        for f in as_completed(futs):
            try:
                infos.append(f.result())
                logger.info(f"snapshot {futs[f]} ok ({time.time()-t0:.0f}s elapsed)")
            except Exception:
                logger.exception(f"snapshot {futs[f]} failed")
                raise
    if all((SNAP / f"info_y{y}.json").exists() for y in C.SPEC["years"]):
        alluvial()
    logger.info(f"stage_snapshots done in {time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()
