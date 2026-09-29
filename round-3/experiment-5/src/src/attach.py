"""Step 3: attach pool concepts to the EXISTING exp_3 yearly snapshots and add turnover-proof openness metrics.

The snapshot graph of year y is reloaded from exp_3 work/snapshots/{nodes,edges,info}_y{y} (no rebuild, no Leiden).
The per-concept block below copies vendored stage_snapshots.build_snapshot lines 110-192 verbatim in logic (the
vendored helper functions _count_tags, _comm_weights, _rarefied_P and _pct_rank are imported, not re-implemented).

NEW per concept-year (frame-type c-papers, as closure):
  top_AS          full top-20 AS neighbour id list (json)                         [already in exp_3]
  top_AS_prev     top-20 list at y-1 (graph y-1, c-papers y-3..y-1)
  closure_persist Chung-Lu closure log-ratio on Kp = top_AS(y) ∩ top_AS(y-1) in snapshot y (NA if |Kp| < 5)  (R1b)
  n_ego, constraint, effsize, efficiency, cdeg_diag   Burt brokerage of the weighted ego network         (R1c)
  xc_obs, xc_exp, xc_excess, xc_n, xc_merges           cross-community pair excess over a strength-decile null (R1c)

Modes:
  repro_code : exp_3 active 145 concepts, exp_3 work/cp.parquet, rank pool = those 145   -> work/attach/repro_code
  repro_data : the same 145 concepts with dataset_5 c-papers                               -> work/attach/repro_data
  full       : 247 screen + 60 reference concepts, dataset_5 c-papers                       -> work/attach/full
  sealed     : 119 held-out concepts, years <= 2015; pct = insertion rank against the full-mode distribution,
               betweenness from a separate graph (kept + active + held-out), only held-out scores kept -> sealed/
               NO value is logged, only row counts.
"""
from __future__ import annotations

import argparse
import gc
import json
import multiprocessing as mp
import os
import time
from concurrent.futures import ProcessPoolExecutor, as_completed

import numpy as np
import pandas as pd
import scipy.sparse as sp
from loguru import logger

import common as K

MODES = ("repro_code", "repro_data", "full", "sealed")


# ----------------------------------------------------------------------------- graph
class Snap:
    """Reloaded snapshot: node order = exp_3 index order (np.unique of tag ids => sorted)."""

    def __init__(self, y: int):
        nd = pd.read_parquet(K.EXP3_SNAP / f"nodes_y{y}.parquet")
        E = pd.read_parquet(K.EXP3_SNAP / f"edges_y{y}.parquet")
        info = json.loads((K.EXP3_SNAP / f"info_y{y}.json").read_text())
        self.nodes = nd.node.values.astype(np.int64)
        assert np.all(np.diff(self.nodes) > 0), "node array not sorted"
        n = len(self.nodes)
        self.W = nd.W.values.astype(float)
        self.s = nd.strength.values.astype(float)
        self.memb = nd.comm.values.astype(np.int64)
        self.k_own = nd.k_own.values.astype(float)
        self.Wtot = float(info["Wtot"])
        ei = np.searchsorted(self.nodes, E.i.values)
        ej = np.searchsorted(self.nodes, E.j.values)
        assert np.all(self.nodes[ei] == E.i.values) and np.all(self.nodes[ej] == E.j.values)
        c = E.c_ij.values.astype(np.float64)
        self.ei, self.ej, self.kept = ei, ej, E.kept.values.astype(bool)
        self.eps = float(c.min()) if len(c) else 1.0
        U = sp.csr_matrix((c, (ei, ej)), shape=(n, n))
        self.Cw = (U + U.T).tocsr()
        A = sp.csr_matrix((E.AS_ij.values.astype(np.float64), (ei, ej)), shape=(n, n))
        self.AS = (A + A.T).tocsr()
        assert len(E) == info["n_edges"], "edge count differs from info"
        rs = np.asarray(self.Cw.sum(axis=1)).ravel()
        assert np.allclose(rs, self.s, rtol=1e-5, atol=1e-3), "Cw row sums differ from stored strengths"
        self.idx = {int(v): i for i, v in enumerate(self.nodes)}
        self.S_total = float(self.s.sum())
        self.kept_mask = self.memb >= 0
        # strength deciles of kept nodes (cross-community null bins, fixed per snapshot)
        import openness as O
        kept_pos = np.where(self.kept_mask)[0]
        self.dec_edges, dec = O.strength_decile_bins(self.s[kept_pos], K.SPEC3["xcomm_strength_deciles"])
        self.dec_pools = [kept_pos[dec == b] for b in range(K.SPEC3["xcomm_strength_deciles"])]
        self.dec_memb = [self.memb[p] for p in self.dec_pools]
        del E, nd, U, A


def light_graph(y: int) -> dict:
    """Only what top-20 AS needs at y-1: node index, W, Wtot."""
    nd = pd.read_parquet(K.EXP3_SNAP / f"nodes_y{y}.parquet", columns=["node", "W"])
    info = json.loads((K.EXP3_SNAP / f"info_y{y}.json").read_text())
    return dict(idx={int(v): i for i, v in enumerate(nd.node.values)}, nodes=nd.node.values, W=nd.W.values.astype(float),
                Wtot=float(info["Wtot"]))


def top_as_ids(x_frame: dict, n_c: int, idx: dict, nodes: np.ndarray, W: np.ndarray, Wtot: float, k: int = 20) -> list:
    """Top-k association-strength neighbour ids exactly as the vendored attachment (stable argsort)."""
    js = np.array([idx[j] for j in x_frame if j in idx], dtype=np.int64)
    if n_c <= 0 or not len(js):
        return []
    xs = np.array([x_frame[int(nodes[p])] for p in js], dtype=float)
    AS_c = xs * Wtot / (n_c * W[js])
    order = np.argsort(-AS_c, kind="stable")
    return nodes[js[order[:k]]].tolist()


def closure_on_ids(ids_y: list, ids_prev: list, idx: dict, Cw, s, S_total: float, eps: float) -> tuple[float, int]:
    """R1b: closure log-ratio on Kp = ids_y ∩ ids_prev in snapshot y; NA if |Kp| < persist_min."""
    import lib_metrics as lm
    kp = sorted(set(ids_y) & set(ids_prev))
    if len(kp) < K.SPEC3["persist_min"]:
        return float("nan"), len(kp)
    P = np.array([idx[j] for j in kp], dtype=np.int64)
    obs = float(Cw[P][:, P].sum() / 2.0)
    return lm.closure_log_ratio(obs, lm.chung_lu_expected(s[P], S_total), eps), len(kp)


# ----------------------------------------------------------------------------- per concept
def concept_block(cid: str, sub: pd.DataFrame, g: Snap, y: int, prev: dict | None, cp_prev: pd.DataFrame | None) -> tuple[dict, list]:
    import config as C
    import lib_metrics as lm
    import openness as O
    from stage_snapshots import _comm_weights, _count_tags, _rarefied_P
    idx, memb, k_own = g.idx, g.memb, g.k_own
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
    Kpos = np.zeros(0, dtype=np.int64)
    AS_c = np.zeros(0)
    if n_c > 0 and len(js):
        xs = np.array([x_frame[int(g.nodes[p])] for p in js], dtype=float)
        AS_c = xs * g.Wtot / (n_c * g.W[js])
        order = np.argsort(-AS_c, kind="stable")
        Kpos = js[order[: C.SPEC["topk_closure"]]]
        nK = len(Kpos)
        K_ids = g.nodes[Kpos].tolist()
        if nK >= C.SPEC["closure_min_neighbours"]:
            sub_c = g.Cw[Kpos][:, Kpos]
            closure_obs = float(sub_c.sum() / 2.0)
            closure_exp = lm.chung_lu_expected(g.s[Kpos], g.S_total)
            closure = lm.closure_log_ratio(closure_obs, closure_exp, g.eps)
    r.update(closure=closure, closure_obs=closure_obs, closure_exp=closure_exp, closure_nK=nK, top_AS=json.dumps(K_ids[:20]))
    cw_all = _comm_weights(x_all, idx, memb)
    r["P_raw"] = lm.participation(cw_all)
    r["n_comm_touched"] = int(sum(1 for v in cw_all.values() if v > 0))
    r["plural_comm_raw"] = int(max(cw_all, key=cw_all.get)) if cw_all else -1
    tl = list(sub.tags.values)
    r["P_rar"] = _rarefied_P(tl, idx, memb, C.SPEC["rarefy_m"], C.SPEC["rarefy_draws"], lm.stable_seed(cid, y, "P"))
    r["P_rar_m5"] = _rarefied_P(tl, idx, memb, C.SPEC["rarefy_m_sensitivity"], C.SPEC["rarefy_draws"], lm.stable_seed(cid, y, "P5"))
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
    btw_nbrs = [int(p) for p in js if g.kept_mask[p]] if n_c > 0 else None
    # ---------------- NEW: R1b persistent-neighbour closure
    if prev is not None and cp_prev is not None:
        fp = cp_prev[cp_prev.frame]
        ids_prev = top_as_ids(_count_tags(list(fp.tags.values)), len(fp), prev["idx"], prev["nodes"], prev["W"], prev["Wtot"])
    else:
        ids_prev = []
    r["top_AS_prev"] = json.dumps(ids_prev)
    cp_val, nkp = closure_on_ids(K_ids[:20], ids_prev, idx, g.Cw, g.s, g.S_total, g.eps) if K_ids else (np.nan, 0)
    r["closure_persist"], r["persist_n"] = cp_val, nkp
    r["persist_overlap"] = (nkp / len(K_ids)) if K_ids and ids_prev else np.nan
    # ---------------- NEW: R1c Burt brokerage of the weighted ego network (all frame neighbours)
    eb = dict(n_ego=len(js), constraint=np.nan, effsize=np.nan, efficiency=np.nan, cdeg_diag=np.nan)
    if n_c > 0 and len(js) >= K.SPEC3["ego_min_neighbours"]:
        A = g.AS[js][:, js]
        eb = O.ego_brokerage(AS_c, A)
    r.update(eb)
    # ---------------- NEW: R1c cross-community pair excess over a strength-decile null (top-20 K, memb >= 0)
    xc_obs = xc_exp = np.nan
    merges = 0
    Kc = Kpos[memb[Kpos] >= 0] if len(Kpos) else Kpos
    if len(Kc) >= K.SPEC3["xc_min_members"]:
        xc_obs = O.cross_share(memb[Kc])
        bins = np.clip(np.searchsorted(g.dec_edges, g.s[Kc], side="right") - 1, 0, len(g.dec_pools) - 1)
        xc_exp, merges = O.xc_null(bins, g.dec_pools, g.dec_memb, K.SPEC3["xcomm_null_draws"], lm.stable_seed(cid, y, "XC"))
    r.update(xc_obs=xc_obs, xc_exp=xc_exp, xc_excess=(xc_obs - xc_exp) if np.isfinite(xc_obs) else np.nan,
             xc_n=int(len(Kc)), xc_merges=merges)
    return r, btw_nbrs


# ----------------------------------------------------------------------------- per year
def _mode_inputs(mode: str) -> dict:
    if mode == "repro_code":
        pool = pd.read_parquet(K.EXP3 / "work" / "pool.parquet", columns=["concept_id"])
        return dict(ids=pool.concept_id.tolist(), cp=K.EXP3 / "work" / "cp.parquet", out=K.WORK / "attach" / "repro_code")
    if mode == "repro_data":
        pool = pd.read_parquet(K.EXP3 / "work" / "pool.parquet", columns=["concept_id"])
        return dict(ids=pool.concept_id.tolist(), cp=K.WORK / "cp_active.parquet", out=K.WORK / "attach" / "repro_data")
    if mode == "full":
        pool = pd.read_parquet(K.WORK / "pool_active.parquet", columns=["concept_id"])
        return dict(ids=pool.concept_id.tolist(), cp=K.WORK / "cp_active.parquet", out=K.WORK / "attach" / "full")
    if mode == "sealed":
        pool = pd.read_parquet(K.WORK / "pool_heldout.parquet", columns=["concept_id"])
        return dict(ids=pool.concept_id.tolist(), cp=K.SEALED / "cp_heldout.parquet", out=K.SEALED / "attach")
    raise ValueError(mode)


def attach_year(mode: str, y: int, ids_override: list | None = None, out_override: str | None = None) -> dict:
    import networkit as nk
    from stage_snapshots import _count_tags, _pct_rank
    import config as C
    nk.setNumberOfThreads(1)
    nk.engineering.setSeed(K.SPEC3["betweenness_seed_base"] + y, False)
    K.setup_logging(f"attach_{mode}_{y}")
    t0 = time.time()
    mi = _mode_inputs(mode)
    ids = ids_override if ids_override is not None else mi["ids"]
    out = mi["out"] if out_override is None else __import__("pathlib").Path(out_override)
    out.mkdir(parents=True, exist_ok=True)
    if mode == "sealed":
        assert y <= K.SPEC3["sealed_max_year"]
    y0 = y - C.SPEC["window"] + 1
    g = Snap(y)
    cp = pd.read_parquet(mi["cp"], columns=["concept_id", "year", "frame", "tags"])
    cp = cp[cp.concept_id.isin(set(ids)) & (cp.year >= y0 - 1) & (cp.year <= y)]
    cur = cp[cp.year >= y0]
    prv = cp[cp.year <= y - 1] if y - 1 >= 2000 else None
    prev = light_graph(y - 1) if y - 1 >= 2000 else None
    rows, pool_edges_nk = [], []
    for cid in ids:
        sub = cur[cur.concept_id == cid]
        r, nb = concept_block(cid, sub, g, y, prev, prv[prv.concept_id == cid] if prv is not None else None)
        if nb is not None:
            pool_edges_nk.append((cid, nb))
        rows.append(r)
    pr = pd.DataFrame(rows)
    # --- percentile + betweenness
    if mode != "sealed":
        pool_s = pr.loc[pr.n_frame > 0, "strength"].values
        rank_s = np.sort(np.concatenate([g.s, pool_s]))
        extra_edges = []
    else:
        act = pd.concat([pd.read_parquet(K.WORK / "attach" / "full" / f"pool_metrics_v3_y{y}.parquet",
                                         columns=["concept_id", "n_frame", "strength"])])
        rank_s = np.sort(np.concatenate([g.s, act.loc[act.n_frame > 0, "strength"].values]))
        # active attachment edges for the betweenness graph (identical rule: frame tags in the kept graph)
        acp = pd.read_parquet(K.WORK / "cp_active.parquet", columns=["concept_id", "year", "frame", "tags"])
        acp = acp[(acp.year >= y0) & (acp.year <= y) & acp.frame]
        extra_edges = []
        for cid in sorted(set(act.concept_id)):
            x = _count_tags(list(acp.loc[acp.concept_id == cid, "tags"].values))
            if not x:
                continue
            extra_edges.append((cid, [g.idx[j] for j in x if j in g.idx and g.kept_mask[g.idx[j]]]))
        del acp
    s_sorted_bg = np.sort(g.s)
    pr["pct"] = [(_pct_rank(rank_s, s) if n > 0 else 0.0) for s, n in zip(pr.strength, pr.n_frame)]
    pr["pct_bg_only"] = [(_pct_rank(s_sorted_bg, s) if n > 0 else 0.0) for s, n in zip(pr.strength, pr.n_frame)]
    kept_nodes = np.where(g.kept_mask)[0]
    remap = -np.ones(len(g.nodes), dtype=np.int64)
    remap[kept_nodes] = np.arange(len(kept_nodes))
    n_bg = len(kept_nodes)
    all_pool = extra_edges + pool_edges_nk  # sealed: active nodes first, then held-out
    G = nk.Graph(n_bg + len(all_pool), weighted=False, directed=False)
    for a, b in zip(remap[g.ei[g.kept]], remap[g.ej[g.kept]]):
        G.addEdge(int(a), int(b))
    pool_pos = {}
    for k, (cid, nbrs) in enumerate(all_pool):
        u = n_bg + k
        assert cid not in pool_pos
        pool_pos[cid] = u
        for p in nbrs:
            G.addEdge(u, int(remap[p]))
    btw = nk.centrality.EstimateBetweenness(G, C.SPEC["betweenness_pivots"], normalized=True, parallel=False)
    btw.run()
    scores = np.array(btw.scores())
    sorted_sc = np.sort(scores)
    own = {c for c, _ in pool_edges_nk}
    pr["btw"] = [scores[pool_pos[c]] if c in own else np.nan for c in pr.concept_id]
    pr["btw_pct"] = [(_pct_rank(sorted_sc, scores[pool_pos[c]]) if c in own else np.nan) for c in pr.concept_id]
    ebr = C.SPEC["early_bridging"]
    pr["cross_comm_flag"] = (pr.btw_pct >= ebr["btw_pct"]) & (pr.n_comm_10pct_frame >= ebr["min_comms"])
    fn = (f"pool_metrics_heldout_y{y}.parquet" if mode == "sealed" else f"pool_metrics_v3_y{y}.parquet")
    pr.to_parquet(out / fn, index=False)
    secs = round(time.time() - t0, 1)
    if mode == "sealed":
        logger.info(f"[sealed] y={y} rows={len(pr)} written in {secs}s (no values logged)")
    else:
        logger.info(f"[{mode}] y={y} concepts={len(pr)} active={int((pr.n_all > 0).sum())} btw graph "
                    f"{G.numberOfNodes()}/{G.numberOfEdges()} in {secs}s")
    del g, cp, G
    gc.collect()
    return dict(mode=mode, year=y, rows=len(pr), secs=secs)


def _w(args):
    return attach_year(*args)


def run(modes: list[str], years: list[int], workers: int, ids_override: list | None = None, out_override: str | None = None) -> list:
    tasks = [(m, y, ids_override, out_override) for m in modes for y in years
             if not (m == "sealed" and y > K.SPEC3["sealed_max_year"])]
    # heavy years first for load balance
    tasks.sort(key=lambda t: -t[1])
    infos = []
    t0 = time.time()
    with ProcessPoolExecutor(max_workers=workers, mp_context=mp.get_context("spawn")) as ex:
        futs = {ex.submit(_w, t): t for t in tasks}
        for f in as_completed(futs):
            infos.append(f.result())
            logger.info(f"attach {futs[f][:2]} ok ({time.time() - t0:.0f}s elapsed, {len(infos)}/{len(tasks)})")
    return infos


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--modes", nargs="+", default=["repro_code", "repro_data", "full"])
    ap.add_argument("--years", type=int, nargs="*", default=list(range(2000, 2025)))
    ap.add_argument("--workers", type=int, default=min(4, K.detect_cpus()))
    ap.add_argument("--ids", nargs="*", default=None)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    K.setup_logging("attach")
    K.set_ram_limit(26)
    os.environ.setdefault("OMP_NUM_THREADS", "1")
    infos = run(a.modes, a.years, a.workers, a.ids, a.out)
    K.write_json(K.LOGS / f"attach_{'_'.join(a.modes)}_timing.json", infos)


if __name__ == "__main__":
    main()
