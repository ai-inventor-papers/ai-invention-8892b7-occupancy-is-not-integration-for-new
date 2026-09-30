#!/usr/bin/env python3
"""STAGE 1: attach every active (screen main-arm + reference) concept to the EXISTING iteration-2 yearly snapshots.

No snapshot is rebuilt: the CoGraph is reconstructed from X3 work/snapshots/{edges,nodes,info}_y*.parquet and the
iteration-2 POOL-ATTACHMENT block of stage_snapshots.build_snapshot is run verbatim (same helpers, same seeds, same
betweenness pivots/seed). Extra outputs per concept-year: all-type community weights, top-50 AS neighbours and the
long-format tag counts that the Leiden-seed robustness layer re-uses.

Outputs: work/attach/pool_metrics_y{y}.parquet, work/attach/tags_y{y}.parquet, work/attach/neigh_y{y}.parquet,
sealed/pct_alt_reference.npz (+ .sha256).
"""
from __future__ import annotations

import json
import multiprocessing as mp
import time
from concurrent.futures import ProcessPoolExecutor, as_completed

import numpy as np
import pandas as pd
import scipy.sparse as sp
from loguru import logger

from common import HELDOUT, MINI, C, SEALED, SNAP_X3, WORK, YEARS, setup_logging, sha256_file, write_json

ATT = WORK / "attach"


def load_cograph(y: int):
    """Reconstruct the iteration-2 CoGraph of snapshot y from its stored nodes/edges tables."""
    from netcore import CoGraph
    nd = pd.read_parquet(SNAP_X3 / f"nodes_y{y}.parquet")
    ed = pd.read_parquet(SNAP_X3 / f"edges_y{y}.parquet")
    info = json.loads((SNAP_X3 / f"info_y{y}.json").read_text())
    nodes = nd.node.values.astype(np.int64)
    assert np.all(np.diff(nodes) > 0), "nodes must be sorted (np.unique order)"
    ei = np.searchsorted(nodes, ed.i.values).astype(np.int32)
    ej = np.searchsorted(nodes, ed.j.values).astype(np.int32)
    c = ed.c_ij.values.astype(np.float64)
    n = len(nodes)
    Cw = sp.csr_matrix((np.concatenate([c, c]), (np.concatenate([ei, ej]), np.concatenate([ej, ei]))), shape=(n, n))
    g = CoGraph(nodes=nodes, W=nd.W.values.astype(float), s=nd.strength.values.astype(float), Wtot=float(info["Wtot"]),
                Cw=Cw, ei=ei, ej=ej, c=c, raw=ed.raw_ij.values, AS=ed.AS_ij.values.astype(np.float64),
                kept=ed.kept.values.astype(bool), n_works=int(info["n_works"]))
    memb = nd.comm.values.astype(np.int64)
    k_own = nd.k_own.values.astype(float)
    return g, memb, k_own, info


def check_cograph(y: int) -> dict:
    g, memb, k_own, info = load_cograph(y)
    n_comm = int(memb.max() + 1) if (memb >= 0).any() else 0
    kept_nodes = len(np.unique(np.concatenate([g.ei[g.kept], g.ej[g.kept]])))
    return dict(year=y, n_nodes=len(g.nodes) == info["n_nodes"], n_edges=len(g.c) == info["n_edges"],
                n_kept_edges=int(g.kept.sum()) == info["n_kept_edges"], n_kept_nodes=kept_nodes == info["n_kept_nodes"],
                n_comm=n_comm == info["n_comm"], strength_rowsum_maxrel=float(np.max(np.abs(
                    np.asarray(g.Cw.sum(axis=1)).ravel() - g.s) / np.maximum(g.s, 1e-9))))


def attach_year(y: int, pool_ids: list[str], old_ids: list[str]) -> dict:
    import networkit as nk
    import lib_metrics as lm
    from stage_snapshots import _comm_weights, _count_tags, _pct_rank, _rarefied_P
    nk.setNumberOfThreads(1)
    nk.engineering.setSeed(20260928 + y, False)  # deterministic betweenness pivots (as iteration 2)
    setup_logging(f"attach_{y}")
    t0 = time.time()
    y0 = y - C.SPEC["window"] + 1
    g, memb, k_own, info = load_cograph(y)
    idx = g.index_of()
    cp = pd.read_parquet(WORK / "cp_hyd.parquet", columns=["concept_id", "work_id", "year", "frame", "tags"],
                         filters=[("year", ">=", y0), ("year", "<=", y)])
    cp = cp[cp.concept_id.isin(set(pool_ids))]
    by_c = {c: grp for c, grp in cp.groupby("concept_id")}
    S_total = float(g.s.sum())
    eps = float(g.c.min()) if len(g.c) else 1.0
    s_sorted_bg = np.sort(g.s)
    kept_nodes_mask = memb >= 0
    rows, pool_edges_nk, tag_rows, neigh_rows = [], [], [], []
    empty = cp.iloc[:0]
    for cid in pool_ids:
        sub = by_c.get(cid, empty)
        fr = sub[sub.frame]
        x_frame = _count_tags(list(fr.tags.values))
        x_all = _count_tags(list(sub.tags.values))
        n_c = len(fr)
        s_c = float(sum(x_frame.values()))
        r = dict(concept_id=cid, year=y, n_frame=n_c, n_all=len(sub), strength=s_c, n_tags_frame=len(x_frame),
                 n_tags_all=len(x_all))
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
            for rank, p in enumerate(js[order[:50]]):
                neigh_rows.append((cid, y, rank, int(g.nodes[p]), float(AS_c[order[rank]]), float(xs[order[rank]]),
                                   int(memb[p])))
        r.update(closure=closure, closure_obs=closure_obs, closure_exp=closure_exp, closure_nK=nK,
                 top_AS=json.dumps(K_ids[:20]))
        cw_all = _comm_weights(x_all, idx, memb)
        r["P_raw"] = lm.participation(cw_all)
        r["n_comm_touched"] = int(sum(1 for v in cw_all.values() if v > 0))
        r["plural_comm_raw"] = int(max(cw_all, key=cw_all.get)) if cw_all else -1
        tl = list(sub.tags.values)
        r["P_rar"] = _rarefied_P(tl, idx, memb, C.SPEC["rarefy_m"], C.SPEC["rarefy_draws"], lm.stable_seed(cid, y, "P"))
        r["P_rar_m5"] = _rarefied_P(tl, idx, memb, C.SPEC["rarefy_m_sensitivity"], C.SPEC["rarefy_draws"],
                                    lm.stable_seed(cid, y, "P5"))
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
        r["cw_all_json"] = json.dumps({str(k): float(v) for k, v in cw_all.items()})
        r["cw_frame_json"] = json.dumps({str(k): float(v) for k, v in cw_fr.items()})
        if n_c > 0:
            pool_edges_nk.append((cid, [int(p) for p in js if kept_nodes_mask[p]]))
        for j, xa in x_all.items():
            tag_rows.append((cid, y, int(j), int(xa), int(x_frame.get(j, 0))))
        rows.append(r)
    pr = pd.DataFrame(rows)
    act = pr.n_frame > 0
    pool_s = pr.loc[act, "strength"].values
    all_s = np.sort(np.concatenate([g.s, pool_s]))
    pr["pct"] = [(_pct_rank(all_s, s) if n > 0 else 0.0) for s, n in zip(pr.strength, pr.n_frame)]
    # iteration-2 comparable percentile: background + the 145 iteration-2 active concepts only (reproduction check)
    old_mask = pr.concept_id.isin(set(old_ids)) & act
    all_s_old = np.sort(np.concatenate([g.s, pr.loc[old_mask, "strength"].values]))
    pr["pct_iter2"] = [(_pct_rank(all_s_old, s) if n > 0 else 0.0) for s, n in zip(pr.strength, pr.n_frame)]
    pr["pct_bg_only"] = [(_pct_rank(s_sorted_bg, s) if n > 0 else 0.0) for s, n in zip(pr.strength, pr.n_frame)]
    # PRIMARY expansion percentile: rank among ALL active pool nodes with frame papers (population independent)
    ref_sorted = np.sort(pool_s)
    pr["pct_alt"] = [(midrank_pct(ref_sorted, s) if n > 0 else 0.0) for s, n in zip(pr.strength, pr.n_frame)]
    if HELDOUT:  # held-out concepts are placed into the FROZEN screen reference array; reference-arm values unchanged
        frozen = np.load(SEALED / "pct_alt_reference.npz")[f"y{y}"]
        pr["pct_alt"] = [(pct_alt_value(frozen, s) if n > 0 else 0.0) for s, n in zip(pr.strength, pr.n_frame)]
    # sampled betweenness on kept graph + active pool nodes (same seed and pivots as iteration 2)
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
    pr.to_parquet(ATT / f"pool_metrics_y{y}.parquet", index=False)
    pd.DataFrame(tag_rows, columns=["concept_id", "year", "node", "x_all", "x_frame"]).to_parquet(
        ATT / f"tags_y{y}.parquet", index=False)
    pd.DataFrame(neigh_rows, columns=["concept_id", "year", "rank", "node", "AS", "x_frame", "comm"]).to_parquet(
        ATT / f"neigh_y{y}.parquet", index=False)
    np.save(ATT / f"pct_alt_ref_y{y}.npy", ref_sorted)
    out = dict(year=y, n_active_frame=int(act.sum()), secs=round(time.time() - t0, 1), btw_secs=round(time.time() - tb, 1))
    logger.info(f"attach y={y} done {out}")
    return out


def midrank_pct(sorted_vals: np.ndarray, s: float) -> float:
    """pandas rank(pct=True, method='average') * 100 of a value s that is an element of sorted_vals."""
    lo = np.searchsorted(sorted_vals, s, "left")
    hi = np.searchsorted(sorted_vals, s, "right")
    return 100.0 * (lo + 0.5 * (hi - lo) + 0.5) / len(sorted_vals)


def pct_alt_value(ref_sorted: np.ndarray, s: float) -> float:
    """Percentile of a NEW (held-out) strength s placed into the frozen per-year reference array (s is inserted)."""
    return midrank_pct(np.sort(np.append(ref_sorted, s)), s)


@logger.catch(reraise=True)
def main(workers: int = 4, years: list[int] | None = None) -> None:
    setup_logging("attach")
    C.set_ram_limit(26)
    pool = pd.read_parquet(WORK / "pool_active.parquet")
    C.assert_not_sealed(pool.concept_id)
    old = pool.loc[pool.iter2_active, "concept_id"].tolist()
    years = years or YEARS
    chk = [check_cograph(y) for y in (2008, 2013, 2018) if y in years]
    write_json(WORK / "attach" / "cograph_check.json", chk)
    logger.info(f"CoGraph reconstruction check {chk}")
    t0 = time.time()
    infos = []
    with ProcessPoolExecutor(max_workers=workers, mp_context=mp.get_context("spawn")) as ex:
        futs = {ex.submit(attach_year, y, pool.concept_id.tolist(), old): y for y in years}
        for f in as_completed(futs):
            infos.append(f.result())
            logger.info(f"year {futs[f]} ok ({time.time() - t0:.0f}s)")
    write_json(WORK / "attach" / "attach_info.json", sorted(infos, key=lambda d: d["year"]))
    refs = {f"y{y}": np.load(ATT / f"pct_alt_ref_y{y}.npy") for y in YEARS if (ATT / f"pct_alt_ref_y{y}.npy").exists()}
    if not HELDOUT and not MINI:  # only the full screen run may write the frozen reference
        np.savez(SEALED / "pct_alt_reference.npz", **refs)
        (SEALED / "pct_alt_reference.npz.sha256").write_text(sha256_file(SEALED / "pct_alt_reference.npz"))
    logger.info(f"attach done in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
