"""Step 3: attach pool concepts to exp_3's PREBUILT yearly co-word snapshots + ego-network openness.

The pool block replicates vendored stage_snapshots.build_snapshot verbatim (same helper functions, same order of
operations) on a CoGraph-equivalent rebuilt from edges_y / nodes_y / info_y. Betweenness is not recomputed (NaN).
New per (c, y): Burt constraint and weighted effective size on the association-strength ego graph, and the
cross-community pair share among the top-20 AS neighbours in excess of a strength-decile null (xcomm_exc).
Held-out concepts are attached only for y <= 2015 (their W1 years).
"""
from __future__ import annotations

import gc
import json
import multiprocessing as mp
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd
import scipy.sparse as sp
from loguru import logger

import common as K
from common import SNAP, SPEC, T_MAX_SCREEN, WORK

EGO_CAP = 3000
XCOMM_DRAWS = 50


# ----------------------------------------------------------------------------- openness (pure functions)
def burt_from_ego(A: np.ndarray) -> tuple[float, float, int]:
    """Burt constraint and weighted effective size of node 0 of a symmetric non-negative weight matrix A.

    Identical to networkx.constraint / networkx.effective_size (weight=...) on the graph defined by A:
    P = row-normalised mutual weight; constraint = sum_j (P0j + sum_q P0q Pqj)^2 over neighbours j of 0;
    esize = sum_j (1 - sum_q P0q * A_jq / max_k A_jk).
    """
    A = np.asarray(A, dtype=float)
    nb = np.where(A[0] > 0)[0]
    nb = nb[nb != 0]
    if nb.size == 0:
        return np.nan, np.nan, 0
    rs = A.sum(1)
    rs[rs == 0] = 1.0
    P = A / rs[:, None]
    v = P[0] + P[0] @ P
    constraint = float(np.sum(v[nb] ** 2))
    mx = A.max(1)
    mx[mx == 0] = 1.0
    M = A / mx[:, None]
    red = M[nb] @ P[0]
    esize = float(np.sum(1.0 - red))
    return constraint, esize, int(nb.size)


def xcomm_share(memb_k: np.ndarray) -> tuple[float, int]:
    m = len(memb_k)
    if m < 2:
        return np.nan, 0
    pairs = m * (m - 1) // 2
    same = sum(int(c) * (int(c) - 1) // 2 for c in np.unique(memb_k, return_counts=True)[1])
    return (pairs - same) / pairs, pairs


# ----------------------------------------------------------------------------- snapshot rebuild
def load_graph(y: int) -> dict:
    E = pd.read_parquet(SNAP / f"edges_y{y}.parquet")
    N = pd.read_parquet(SNAP / f"nodes_y{y}.parquet")
    info = json.loads((SNAP / f"info_y{y}.json").read_text())
    nodes = N.node.values
    assert np.all(np.diff(nodes) > 0), "nodes must be sorted (np.unique order)"
    pos = np.searchsorted(nodes, E.i.values), np.searchsorted(nodes, E.j.values)
    n = len(nodes)
    c = E.c_ij.values.astype(np.float64)
    Cw = sp.coo_matrix((np.r_[c, c], (np.r_[pos[0], pos[1]], np.r_[pos[1], pos[0]])), shape=(n, n)).tocsr()
    AS = E.AS_ij.values.astype(np.float64)
    ASm = sp.coo_matrix((np.r_[AS, AS], (np.r_[pos[0], pos[1]], np.r_[pos[1], pos[0]])), shape=(n, n)).tocsr()
    s = N.strength.values.astype(np.float64)
    rel = np.abs(np.asarray(Cw.sum(1)).ravel() - s) / np.maximum(s, 1e-12)
    ok_share = float(np.mean(rel < 1e-4))
    return dict(nodes=nodes, W=N.W.values.astype(np.float64), s=s, Wtot=float(info["Wtot"]), Cw=Cw, ASm=ASm,
                memb=N.comm.values.astype(np.int64), k_own=N.k_own.values.astype(np.float64),
                eps=float(c.min()) if len(c) else 1.0, strength_check=ok_share)


def attach_year(y: int, cp_path: str, out_dir: str, heldout: list[str], concept_ids: list[str] | None = None) -> dict:
    import lib_metrics as lm
    from stage_snapshots import _comm_weights, _count_tags, _pct_rank, _rarefied_P
    K.setup_logging(f"attach_{Path(out_dir).name}_{y}")
    t0 = time.time()
    g = load_graph(y)
    if g["strength_check"] < 0.999:
        logger.warning(f"y={y} strength check share {g['strength_check']:.4f} < 0.999 (float32 c_ij)")
    nodes, W, s, Wtot, Cw, ASm, memb, k_own = (g[k] for k in ("nodes", "W", "s", "Wtot", "Cw", "ASm", "memb", "k_own"))
    idx = {int(v): i for i, v in enumerate(nodes)}
    y0 = y - SPEC["window"] + 1
    cp = pd.read_parquet(cp_path, columns=["concept_id", "work_id", "year", "frame", "tags"])
    cp = cp[(cp.year >= y0) & (cp.year <= y)]
    ids = concept_ids if concept_ids is not None else sorted(set(pd.read_parquet(WORK / "pool.parquet").concept_id))
    ho = set(heldout)
    if y > T_MAX_SCREEN:
        ids = [c for c in ids if c not in ho]
    S_total = float(s.sum())
    eps = g["eps"]
    s_sorted_bg = np.sort(s)
    kept = np.where(memb >= 0)[0]
    # strength deciles among community members (xcomm null)
    dec_edges = np.quantile(s[kept], np.linspace(0, 1, 11)[1:-1]) if len(kept) else np.zeros(9)
    dec_of = np.searchsorted(dec_edges, s, side="right")
    dec_pools = {d: kept[dec_of[kept] == d] for d in range(10)}
    dec_pools = {d: (v if len(v) else kept) for d, v in dec_pools.items()}
    rows, n_trunc = [], 0
    grp = {c: sub for c, sub in cp.groupby("concept_id")}
    empty = cp.iloc[0:0]
    for cid in ids:
        sub = grp.get(cid, empty)
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
            xs = np.array([x_frame[int(nodes[p])] for p in js], dtype=float)
            AS_c = xs * Wtot / (n_c * W[js])
            order = np.argsort(-AS_c, kind="stable")
            Kpos = js[order[: SPEC["topk_closure"]]]
            nK = len(Kpos)
            K_ids = nodes[Kpos].tolist()
            if nK >= SPEC["closure_min_neighbours"]:
                sub_c = Cw[Kpos][:, Kpos]
                closure_obs = float(sub_c.sum() / 2.0)
                closure_exp = lm.chung_lu_expected(s[Kpos], S_total)
                closure = lm.closure_log_ratio(closure_obs, closure_exp, eps)
        r.update(closure=closure, closure_obs=closure_obs, closure_exp=closure_exp, closure_nK=nK,
                 top_AS=json.dumps(K_ids[:20]))
        cw_all = _comm_weights(x_all, idx, memb)
        r["P_raw"] = lm.participation(cw_all)
        r["n_comm_touched"] = int(sum(1 for v in cw_all.values() if v > 0))
        r["plural_comm_raw"] = int(max(cw_all, key=cw_all.get)) if cw_all else -1
        tl = list(sub.tags.values)
        r["P_rar"] = _rarefied_P(tl, idx, memb, SPEC["rarefy_m"], SPEC["rarefy_draws"], lm.stable_seed(cid, y, "P"))
        r["P_rar_m5"] = _rarefied_P(tl, idx, memb, SPEC["rarefy_m_sensitivity"], SPEC["rarefy_draws"],
                                    lm.stable_seed(cid, y, "P5"))
        cw_fr = _comm_weights(x_frame, idx, memb)
        if cw_fr:
            s_star = max(cw_fr, key=cw_fr.get)
            peers = k_own[memb == s_star]
            r["wmz"] = lm.within_module_z(float(cw_fr[s_star]), peers)
            tot_fr = sum(cw_fr.values())
            r["n_comm_10pct_frame"] = int(sum(1 for v in cw_fr.values() if v >= SPEC["early_bridging"]["min_comm_share"] * tot_fr))
        else:
            r["wmz"] = np.nan
            r["n_comm_10pct_frame"] = 0
        # ---- NEW: ego-network openness (frame-type AS neighbours; all background edges among them)
        constraint = esize = np.nan
        deg = 0
        if len(js):
            e_js, e_w = js, AS_c
            if len(js) > EGO_CAP:
                n_trunc += 1
                top = np.argsort(-AS_c, kind="stable")[:EGO_CAP]
                e_js, e_w = js[top], AS_c[top]
            A = np.zeros((len(e_js) + 1, len(e_js) + 1))
            A[1:, 1:] = ASm[e_js][:, e_js].toarray()
            A[0, 1:] = e_w
            A[1:, 0] = e_w
            constraint, esize, deg = burt_from_ego(A)
        r.update(constraint=constraint, esize=esize, ego_deg=deg, esize_norm=(esize / deg) if deg else np.nan)
        # ---- NEW: cross-community pair share among top-20 AS neighbours vs strength-decile null
        km = Kpos[memb[Kpos] >= 0] if nK else Kpos
        xo, npairs = xcomm_share(memb[km]) if len(km) >= SPEC["closure_min_neighbours"] else (np.nan, 0)
        xnull = np.nan
        if np.isfinite(xo):
            rng = np.random.default_rng(lm.stable_seed(cid, y, "X"))
            vals = []
            dk = dec_of[km]
            for _ in range(XCOMM_DRAWS):
                pick = np.array([rng.choice(dec_pools[d]) for d in dk])
                vals.append(xcomm_share(memb[pick])[0])
            xnull = float(np.mean(vals))
        r.update(xcomm_obs=xo, xcomm_null=xnull, xcomm_exc=(xo - xnull) if np.isfinite(xo) else np.nan,
                 xcomm_n_pairs=npairs)
        rows.append(r)
    pr = pd.DataFrame(rows)
    pool_s = pr.loc[pr.n_frame > 0, "strength"].values
    all_s = np.sort(np.concatenate([s, pool_s]))
    pr["pct"] = [(_pct_rank(all_s, v) if n > 0 else 0.0) for v, n in zip(pr.strength, pr.n_frame)]
    pr["pct_bg_only"] = [(_pct_rank(s_sorted_bg, v) if n > 0 else 0.0) for v, n in zip(pr.strength, pr.n_frame)]
    pr["btw"] = np.nan
    pr["btw_pct"] = np.nan
    pr["cross_comm_flag"] = False
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    pr.to_parquet(Path(out_dir) / f"pool_metrics_y{y}.parquet", index=False)
    info = dict(year=y, n_concepts=len(ids), n_active=int((pr.n_all > 0).sum()), ego_truncations=n_trunc,
                strength_check_share=g["strength_check"], secs=round(time.time() - t0, 1))
    logger.info(f"attach y={y}: {info}")
    del g, Cw, ASm, cp
    gc.collect()
    return info


def run(years: list[int] | None = None, cp_path: Path | None = None, out_dir: Path | None = None,
        concept_ids: list[str] | None = None, workers: int = 4) -> list[dict]:
    years = years or SPEC["years"]
    cp_path = cp_path or WORK / "cp.parquet"
    out_dir = out_dir or WORK / "pool_metrics"
    heldout = sorted(K.load_sealed_ids())
    t0 = time.time()
    infos = []
    with ProcessPoolExecutor(max_workers=workers, mp_context=mp.get_context("spawn")) as ex:
        futs = {ex.submit(attach_year, y, str(cp_path), str(out_dir), heldout, concept_ids): y for y in years}
        for f in as_completed(futs):
            infos.append(f.result())
            logger.info(f"attached y={futs[f]} ({time.time() - t0:.0f}s elapsed)")
    infos.sort(key=lambda d: d["year"])
    K.write_json(Path(out_dir) / "attach_info.json", infos)
    return infos
