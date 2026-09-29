"""STEP 2 + year-local part of STEP 3: build one yearly snapshot and compute the focal indicators
that only need snapshot y (strength, degree, percentile, closure, participation, within-module z,
betweenness, rewiring z). Outcome-blind: reads only works with year in [y-2, y]."""

from __future__ import annotations

import json
import random
import time
from pathlib import Path

import numpy as np
import pandas as pd
import scipy.sparse as sp
from loguru import logger

import rq1_spec as S

ROOT = Path(__file__).resolve().parent
INTER = ROOT / "results" / "intermediate"
SNAP = ROOT / "results" / "snapshots"


def closure_counts(A_bin: sp.csr_matrix, T: np.ndarray, deg: np.ndarray, m: int) -> tuple[int, float]:
    """obs = #edges among T in the binary background graph; exp = Chung-Lu sum_{i<j} min(1, k_i k_j / 2m)."""
    if len(T) < 2:
        return 0, 0.0
    sub = A_bin[T][:, T]
    obs = int(sub.nnz // 2)
    k = deg[T].astype(float)
    P = np.minimum(1.0, np.outer(k, k) / (2.0 * m)) if m > 0 else np.zeros((len(T), len(T)))
    exp = float(np.triu(P, 1).sum())
    return obs, exp


def closure_lr(obs: float, exp: float) -> float:
    return float(np.log((obs + 0.5) / (exp + 0.5)))


def participation(k_cs: np.ndarray) -> float:
    s = k_cs.sum()
    if s <= 0:
        return float("nan")
    return float(1.0 - np.sum((k_cs / s) ** 2))


def module_stats(memb: np.ndarray, A_W: sp.csr_matrix) -> dict:
    """Within-module strength mean/sd over background nodes of each module."""
    n_t = len(memb)
    n_comm = int(memb.max() + 1)
    M = sp.csr_matrix((np.ones(n_t), (np.arange(n_t), memb)), shape=(n_t, n_comm))
    within = np.asarray((A_W @ M).tocsr()[np.arange(n_t), memb]).ravel()
    cnt = np.bincount(memb, minlength=n_comm)
    mean = np.bincount(memb, weights=within, minlength=n_comm) / np.maximum(cnt, 1)
    sq = np.bincount(memb, weights=within ** 2, minlength=n_comm) / np.maximum(cnt, 1)
    return {"memb": memb, "n_comm": n_comm, "mean": mean, "sd": np.sqrt(np.maximum(sq - mean ** 2, 0)), "n": cnt}


def focal_comm(ms: dict, nb: np.ndarray, wcj: np.ndarray) -> tuple[float, int, float, int]:
    """Participation P, module (argmax), within-module z and #modules touched of one focal node."""
    k_cs = np.bincount(ms["memb"][nb], weights=wcj, minlength=ms["n_comm"])
    mod = int(np.argmax(k_cs))
    sd = ms["sd"][mod]
    z = (k_cs[mod] - ms["mean"][mod]) / sd if (sd > 0 and ms["n"][mod] >= 2) else np.nan
    return participation(k_cs), mod, float(z), int((k_cs > 0).sum())


def leiden(n: int, edges: np.ndarray, weights: np.ndarray) -> tuple[np.ndarray, list[np.ndarray], dict]:
    """Best-of-5-seeds Leiden (RB configuration, resolution 1) on association-strength weights."""
    import igraph as ig
    import leidenalg as la
    from sklearn.metrics import normalized_mutual_info_score

    g = ig.Graph(n=n, edges=edges.tolist(), directed=False)
    w = (weights / weights.mean()).tolist() if len(weights) else []  # uniform rescale: partition-invariant
    parts, quals = [], []
    fallback = False
    t0 = time.time()
    for seed in S.LEIDEN["seeds"]:
        if not fallback:
            p = la.find_partition(g, la.RBConfigurationVertexPartition, weights=w,
                                  resolution_parameter=S.LEIDEN["resolution"], seed=seed,
                                  n_iterations=S.LEIDEN["n_iterations"])
        else:
            p = la.find_partition(g, la.ModularityVertexPartition, weights=w, seed=seed,
                                  n_iterations=S.LEIDEN["n_iterations"])
        parts.append(np.array(p.membership))
        quals.append(p.quality())
        if time.time() - t0 > S.LEIDEN_TIMEOUT_S and not fallback:
            logger.warning("Leiden exceeded timeout; falling back to ModularityVertexPartition (F2)")
            fallback = True
    best = int(np.argmax(quals))
    nmis = [normalized_mutual_info_score(parts[best], parts[i]) for i in range(len(parts)) if i != best]
    return parts[best], parts, {"quality": float(quals[best]), "nmi_seeds_mean": float(np.mean(nmis)) if nmis else 1.0,
                                "nmi_seeds_min": float(np.min(nmis)) if nmis else 1.0, "leiden_fallback": fallback,
                                "leiden_s": time.time() - t0}


def build_year(y: int, bg: pd.DataFrame, focal: pd.DataFrame, twins: dict[str, list[int]],
               rewire_units: set[str], out_dir: Path, tag: str = "") -> dict:
    """Build snapshot y, compute year-local focal indicators, write parquet files. Returns stats."""
    t0 = time.time()
    lo, hi = y - S.WINDOW + 1, y
    b = bg[(bg.year >= lo) & (bg.year <= hi)]
    rows, cols = [], []
    for wi, tags in enumerate(b.tags):
        for t in set(tags):
            rows.append(wi)
            cols.append(t)
    cols = np.asarray(cols, dtype=np.int64)
    uniq, cidx = np.unique(cols, return_inverse=True)
    n_t = len(uniq)
    X = sp.csr_matrix((np.ones(len(cidx)), (np.asarray(rows), cidx)), shape=(len(b), n_t))
    w = b.w_year.to_numpy(dtype=float)
    Wi = np.asarray(X.T @ w).ravel()
    C = (X.T @ sp.diags(w) @ X).tocoo()
    msk = (C.row < C.col) & (C.data >= S.EDGE_MIN_WCOUNT)
    ei, ej, Wij = C.row[msk], C.col[msk], C.data[msk]
    AS = Wij / (Wi[ei] * Wi[ej])
    m = len(ei)
    A_bin = sp.csr_matrix((np.ones(2 * m), (np.r_[ei, ej], np.r_[ej, ei])), shape=(n_t, n_t))
    A_W = sp.csr_matrix((np.r_[Wij, Wij], (np.r_[ei, ej], np.r_[ej, ei])), shape=(n_t, n_t))
    deg = np.asarray(A_bin.sum(axis=1)).ravel().astype(np.int64)
    t_build = time.time() - t0

    memb, parts, lstats = leiden(n_t, np.c_[ei, ej], AS)
    MS = [module_stats(pm, A_W) for pm in parts]
    ms_best = module_stats(memb, A_W)
    n_comm, mod_n = ms_best["n_comm"], ms_best["n"]
    bg_strength = np.asarray(A_W.sum(axis=1)).ravel()

    # ---- focal attachment (census, weight 1, trailing window)
    idx_of = {int(t): i for i, t in enumerate(uniq)}
    f = focal[(focal.year >= lo) & (focal.year <= hi)]
    frows = []
    focal_edges = []  # (focal index, bg index)
    n_tag_total = n_tag_notbg = 0
    for cid, g in f.groupby("concept_id", sort=True):
        W_c = int(g.work_id.nunique())
        tw = set(twins.get(cid, []))
        cnt: dict[int, int] = {}
        for tags in g.drop_duplicates("work_id").tags:
            for t in set(tags):
                if t in tw:
                    continue
                cnt[t] = cnt.get(t, 0) + 1
        n_tag_total += sum(1 for v in cnt.values() if v >= 2)
        nb, wcj = [], []
        for t, v in cnt.items():
            if v < S.EDGE_MIN_WCOUNT:
                continue
            j = idx_of.get(t)
            if j is None:
                n_tag_notbg += 1
                continue
            nb.append(j)
            wcj.append(v)
        nb = np.asarray(nb, dtype=np.int64)
        wcj = np.asarray(wcj, dtype=float)
        rec = {"concept_id": cid, "year": y, "W_c": W_c, "k": int(len(nb)), "s": float(wcj.sum())}
        if len(nb):
            as_cj = wcj / (W_c * Wi[nb])
            order = np.argsort(-as_cj, kind="stable")
            T = nb[order[: S.TOPK_CLOSURE]]
            obs, exp = closure_counts(A_bin, T, deg, m)
            Pc, mod, zc, ntouch = focal_comm(ms_best, nb, wcj)
            seeds = np.array([focal_comm(q, nb, wcj)[::2] for q in MS], dtype=float)  # (P, z) per seed
            rec.update({"closure_obs": obs, "closure_exp": exp, "closure_lr": closure_lr(obs, exp),
                        "P": Pc, "module_local": mod, "z_within": zc,
                        "P_seed_sd": float(np.nanstd(seeds[:, 0])), "z_seed_sd": float(np.nanstd(seeds[:, 1])),
                        "n_modules_touched": ntouch,
                        "neighbours": [int(uniq[j]) for j in nb], "topk": [int(uniq[j]) for j in T],
                        "_T": T})
            focal_edges.append((cid, nb, wcj))
        else:
            rec.update({"closure_obs": np.nan, "closure_exp": np.nan, "closure_lr": np.nan, "P": np.nan,
                        "module_local": -1, "z_within": np.nan, "n_modules_touched": 0,
                        "P_seed_sd": np.nan, "z_seed_sd": np.nan, "neighbours": [],
                        "topk": [], "_T": np.zeros(0, dtype=np.int64)})
        frows.append(rec)
    fdf = pd.DataFrame(frows)

    # ---- percentile of weighted degree among non-isolated nodes of G[y] (bg + focal)
    strength_all = bg_strength.copy()
    for _cid, nb, wcj in focal_edges:
        np.add.at(strength_all, nb, wcj)  # bg endpoints also gain the focal edge weights
    fstr = fdf.s.to_numpy() if len(fdf) else np.zeros(0)
    pool = np.r_[strength_all[strength_all > 0], fstr[fstr > 0]]
    pool.sort()
    if len(fdf):
        lt = np.searchsorted(pool, fstr, side="left")
        le = np.searchsorted(pool, fstr, side="right")
        pct = 100.0 * (lt + 0.5 * (le - lt)) / max(len(pool), 1)
        fdf["wdeg_pctl"] = np.where(fstr > 0, pct, np.nan)

    # ---- betweenness on G[y] incl. focal nodes (networkit, unweighted, normalised)
    t1 = time.time()
    betw_p90 = np.nan
    if len(fdf):
        try:
            import networkit as nk
            nk.setSeed(S.SEED, False)
            nk.engineering.setNumberOfThreads(1)
            n_f = len(fdf)
            G = nk.Graph(n_t + n_f, weighted=False, directed=False)
            G.addEdges((ei.astype(np.uint64), ej.astype(np.uint64)))
            pos = {c: n_t + i for i, c in enumerate(fdf.concept_id)}
            for cid, nb, _w in focal_edges:
                src = np.full(len(nb), pos[cid], dtype=np.uint64)
                G.addEdges((src, nb.astype(np.uint64)))
            eb = nk.centrality.EstimateBetweenness(G, S.BETWEENNESS_SAMPLES, normalized=True, parallel=False)
            eb.run()
            sc = np.asarray(eb.scores())
            fdf["betw"] = [sc[pos[c]] for c in fdf.concept_id]
            nonzero_deg = np.r_[deg > 0, fdf.k.to_numpy() > 0]
            betw_p90 = float(np.quantile(sc[nonzero_deg], S.PATTERN_BETW_DECILE)) if nonzero_deg.any() else np.nan
            fdf["betw_top_decile"] = (fdf.betw > betw_p90) & (fdf.k > 0)
            bmethod = "networkit.EstimateBetweenness"
        except ImportError:
            logger.warning("networkit missing; F3 fallback igraph betweenness cutoff=4")
            import igraph as ig
            g = ig.Graph(n=n_t, edges=np.c_[ei, ej].tolist())
            bmethod = "igraph_cutoff4"
            fdf["betw"] = np.nan
            fdf["betw_top_decile"] = False
    t_betw = time.time() - t1

    # ---- rewiring z (degree-preserving; the top-k set T is held fixed)
    t2 = time.time()
    fdf["rewire_z"] = np.nan
    sel = [i for i, c in enumerate(fdf.concept_id) if f"{c}|{y}" in rewire_units and len(fdf._T.iloc[i]) >= 2]
    if sel:
        import igraph as ig
        base = ig.Graph(n=n_t, edges=np.c_[ei, ej].tolist(), directed=False)
        null = np.zeros((len(sel), S.REWIRE_REPS))
        for r in range(S.REWIRE_REPS):
            random.seed(S.SEED + r)
            ig.set_random_number_generator(random)
            g = base.copy()
            g.rewire(n=S.REWIRE_SWAPS_PER_EDGE * m, mode="simple")
            el = np.asarray(g.get_edgelist())
            Ar = sp.csr_matrix((np.ones(2 * len(el)), (np.r_[el[:, 0], el[:, 1]], np.r_[el[:, 1], el[:, 0]])),
                               shape=(n_t, n_t))
            for q, i in enumerate(sel):
                T = fdf._T.iloc[i]
                null[q, r] = Ar[T][:, T].nnz // 2
        for q, i in enumerate(sel):
            mu, sd = null[q].mean(), null[q].std(ddof=1)
            fdf.loc[fdf.index[i], "rewire_z"] = (fdf.closure_obs.iloc[i] - mu) / sd if sd > 0 else np.nan
    t_rew = time.time() - t2

    # ---- write
    out_dir.mkdir(parents=True, exist_ok=True)
    if len(fdf):
        fdf = fdf.drop(columns=["_T"])
        fdf["module_local"] = fdf.module_local.astype(int)
    fdf.to_parquet(out_dir / f"focal_{y}{tag}.parquet")
    pd.DataFrame({"tag": uniq, "comm_local": memb, "W_i": Wi, "deg": deg}).to_parquet(out_dir / f"nodes_{y}{tag}.parquet")
    pd.DataFrame({"i": uniq[ei], "j": uniq[ej], "W_ij": Wij, "AS": AS}).to_parquet(out_dir / f"edges_{y}{tag}.parquet")
    stats = {"year": y, "tag": tag, "n_bg_works": int(len(b)), "n_nodes": int(n_t), "n_edges": int(m),
             "n_communities": n_comm, "n_comm_ge5": int((mod_n >= 5).sum()), **lstats,
             "n_focal": int(len(fdf)), "n_focal_nonisolated": int((fdf.k > 0).sum()) if len(fdf) else 0,
             "focal_tags_ge2": n_tag_total, "focal_tags_not_in_bg": n_tag_notbg,
             "betw_p90": betw_p90, "betweenness_method": bmethod if len(fdf) else None,
             "n_rewire_units": len(sel), "t_build_s": t_build, "t_betw_s": t_betw, "t_rewire_s": t_rew,
             "t_total_s": time.time() - t0, "sum_W_i": float(Wi.sum()),
             "sum_weighted_incidence": float((X.multiply(w[:, None])).sum())}
    (out_dir / f"stats_{y}{tag}.json").write_text(json.dumps(stats, indent=1))
    return stats


def worker(args: tuple) -> dict:
    """ProcessPool entry: load cached inputs from disk (spawn-safe) and build one year."""
    y, focal_ids, rewire_units, exclude_lowconf, tag = args
    bg = pd.read_parquet(INTER / "bg.parquet")
    if exclude_lowconf:
        bg = bg[~bg.low_conf_topic]
    focal = pd.read_parquet(INTER / "mesh_works.parquet")
    focal = focal[focal.primary & focal.concept_id.isin(focal_ids) & (focal.year >= y - S.WINDOW + 1) & (focal.year <= y)]
    twins = json.loads((INTER / "twins.json").read_text())
    return build_year(y, bg, focal, twins, set(rewire_units), SNAP, tag)
