#!/usr/bin/env python3
"""Robustness checks on the snapshot substrate.

(a) Community stability: 20 within-stratum bootstrap resamples of the background sample on 3 snapshots
    -> Leiden -> AMI with the main partition (mean, 5th percentile).
(b) Degree-preserving rewiring null for closure: 20 igraph rewirings (10|E| swaps) of the kept graph on 3 snapshots;
    binary density among each pool concept's top-20 AS neighbours -> z; reported for a 10% random subsample of
    pool concept-years (plus Spearman with the Chung-Lu log-ratio).
(c) Edge-filter sensitivity: raw >= 1 kept graph on 2013 -> Leiden AMI vs main, Spearman of pool P_raw.
(d) Substrate cross-check with art_QpM5SM6a7SH6 (dataset_4 stratified corpus, design-weighted, legacy concepts
    score >= 0.3 by name): pool strength percentiles in 2008/2013 vs the main substrate (Spearman).
(e) Semantic-grounding lookup: pool phrases matched to dataset_4's LLM-labelled phrase set and phrase pool.
Output: results/robustness.json
"""
from __future__ import annotations

import json
import multiprocessing as mp
import re
import time
from collections import Counter
from concurrent.futures import ProcessPoolExecutor

import igraph as ig
import numpy as np
import pandas as pd
from loguru import logger
from scipy.stats import spearmanr
from sklearn.metrics import adjusted_mutual_info_score

import config as C
from netcore import build_cograph, leiden_best

SNAP = C.WORK / "snapshots"


def _window_bg(y: int) -> pd.DataFrame:
    bg = pd.read_parquet(C.WORK / "bg.parquet", columns=["year", "w_year", "tags", "stratum"])
    return bg[(bg.year >= y - 2) & (bg.year <= y)].reset_index(drop=True)


def _ami_vs_main(nodes: np.ndarray, memb: np.ndarray, main: pd.DataFrame) -> float:
    a = pd.DataFrame(dict(node=nodes, c2=memb))
    m = main.merge(a, on="node")
    m = m[(m.comm >= 0) & (m.c2 >= 0)]
    return float(adjusted_mutual_info_score(m.comm.values, m.c2.values)) if len(m) > 10 else float("nan")


def boot_one(args: tuple) -> dict:
    y, b = args
    C.setup_logging(f"robust_boot_{y}")
    import random
    random.seed(1000 * y + b)
    bg = _window_bg(y)
    rng = np.random.default_rng(1000 * y + b)
    idx = np.concatenate([rng.choice(g.index.values, size=len(g), replace=True) for _, g in bg.groupby("stratum")])
    # unique works carry their bootstrap multiplicity in the weight, so the kept rule (>= 2 raw co-occurrences)
    # still counts DISTINCT works and a duplicated work cannot create a kept edge on its own
    u, mult = np.unique(idx, return_counts=True)
    s = bg.loc[u]
    g = build_cograph(list(s.tags.values), s.w_year.values * mult, C.SPEC["kept_edge_min_raw"])
    memb, q, _ = leiden_best(g, **{k: C.SPEC["leiden"][k] for k in ("resolution", "seed", "n_runs")})
    main = pd.read_parquet(SNAP / f"nodes_y{y}.parquet", columns=["node", "comm"])
    return dict(year=y, b=b, ami=_ami_vs_main(g.nodes, memb, main), modularity=q)


def rewire_one(y: int) -> dict:
    """Degree-preserving rewiring null for neighbourhood closure on the kept graph.

    For every pool concept with >= 5 of its top-20 AS neighbours in the kept graph (the plan's 10% subsample was
    too small because AS favours rare tags outside the kept graph), compare the binary density among those
    neighbours with 20 rewired graphs (10|E| swaps each): z-score (when the null varies) and empirical p.
    """
    C.setup_logging(f"robust_rewire_{y}")
    import random
    random.seed(y)  # igraph draws from Python's random module -> deterministic rewiring
    e = pd.read_parquet(SNAP / f"edges_y{y}.parquet", columns=["i", "j", "kept"])
    e = e[e.kept]
    nodes, inv = np.unique(np.concatenate([e.i.values, e.j.values]), return_inverse=True)
    m = len(e)
    G = ig.Graph(n=len(nodes), edges=np.column_stack([inv[:m], inv[m:]]).tolist())
    pos = {int(v): k for k, v in enumerate(nodes)}
    pm = pd.read_parquet(SNAP / f"pool_metrics_y{y}.parquet", columns=["concept_id", "closure", "closure_nK", "top_AS"])
    rows = []
    for r in pm.itertuples(index=False):
        K = [pos[j] for j in json.loads(r.top_AS) if j in pos]
        if len(K) >= 5:
            rows.append((r.concept_id, r.closure, K))

    def dens(graph: ig.Graph, K: list) -> float:
        sub = graph.induced_subgraph(K)
        return sub.ecount() / (len(K) * (len(K) - 1) / 2)

    obs = np.array([dens(G, K) for _, _, K in rows])
    null = np.zeros((C.SPEC["rewire_n"], len(rows)))
    for rr in range(C.SPEC["rewire_n"]):
        H = G.copy()
        H.rewire(n=10 * H.ecount())
        null[rr] = [dens(H, K) for _, _, K in rows]
    mu, sd = null.mean(axis=0), null.std(axis=0, ddof=1)
    z = np.where(sd > 0, (obs - mu) / np.where(sd > 0, sd, 1), np.nan)
    p_emp = (1 + (null >= obs[None, :]).sum(axis=0)) / (1 + C.SPEC["rewire_n"])
    clo = np.array([c for _, c, _ in rows], dtype=float)
    lr = np.log((obs + 1e-6) / (mu + 1e-6))
    ok = np.isfinite(clo)
    return dict(year=y, n_pool_with_5_kept_neighbours=len(rows), n_pool_total=len(pm), kept_nodes=len(nodes), kept_edges=m,
                share_p_emp_lt_0_05=float(np.mean(p_emp < 0.05)) if len(rows) else float("nan"),
                z_median=float(np.nanmedian(z)) if np.isfinite(z).any() else float("nan"), n_z_finite=int(np.isfinite(z).sum()),
                obs_density_median=float(np.median(obs)) if len(rows) else float("nan"),
                null_density_median=float(np.median(mu)) if len(rows) else float("nan"),
                spearman_closure_vs_binary_logratio=float(spearmanr(clo[ok], lr[ok]).statistic) if ok.sum() > 4 else float("nan"))


def edge_filter_sensitivity(y: int = 2013) -> dict:
    bg = _window_bg(y)
    g = build_cograph(list(bg.tags.values), bg.w_year.values, kept_min_raw=1)
    memb, q, nk = leiden_best(g, resolution=1.0, seed=42, n_runs=C.SPEC["leiden"]["n_runs"])
    main = pd.read_parquet(SNAP / f"nodes_y{y}.parquet", columns=["node", "comm"])
    ami = _ami_vs_main(g.nodes, memb, main)
    # pool P_raw under the raw>=1 partition
    cp = pd.read_parquet(C.WORK / "cp.parquet", columns=["concept_id", "year", "tags"])
    cp = cp[(cp.year >= y - 2) & (cp.year <= y)]
    idx = g.index_of()
    pm = pd.read_parquet(SNAP / f"pool_metrics_y{y}.parquet", columns=["concept_id", "P_raw"])
    alt = {}
    for cid, grp in cp.groupby("concept_id"):
        cnt: Counter = Counter()
        for t in grp.tags.values:
            for j in t.tolist():
                p = idx.get(j)
                if p is not None and memb[p] >= 0:
                    cnt[int(memb[p])] += 1
        v = np.array(list(cnt.values()), dtype=float)
        alt[cid] = 1 - np.sum((v / v.sum()) ** 2) if v.sum() > 0 else np.nan
    pm["P_raw_alt"] = pm.concept_id.map(alt)
    ok = pm[["P_raw", "P_raw_alt"]].dropna()
    return dict(year=y, kept_edges_raw_ge1=int(g.kept.sum()), kept_nodes=int(nk), modularity=q, ami_vs_main=ami,
                spearman_P_raw=float(spearmanr(ok.P_raw, ok.P_raw_alt).statistic) if len(ok) > 4 else float("nan"))


def d4_substrate(years: tuple = (2008, 2013)) -> dict:
    """Pool strength percentiles on the independent dataset_4 stratified corpus (<= 2016)."""
    con = pd.read_parquet(C.D2 / "data" / "concepts.parquet", columns=["concept_id", "display_name", "level", "works_count"])
    con = con[con.level >= C.SPEC["min_level"]].sort_values("works_count", ascending=False).drop_duplicates("display_name")
    name2id = dict(zip(con.display_name, con.concept_id.str[1:].astype(np.int64)))
    rows = []
    n_names = n_mapped = 0
    for f in sorted((C.D4 / "full_data_out").glob("full_data_out_*.json")):
        d = json.loads(f.read_text())
        for ds in d["datasets"]:
            if not ds["dataset"].startswith("openalex_stratified_corpus"):
                continue
            for ex in ds["examples"]:
                names = ex.get("metadata_legacy_concepts_score_ge_0_3") or []
                ids = [name2id[n] for n in names if n in name2id]
                n_names += len(names)
                n_mapped += len(ids)
                rows.append((int(ex["metadata_publication_year"]), float(ex["metadata_design_weight"]),
                             np.array(sorted(set(ids)), dtype=np.int64)))
        del d
    corpus = pd.DataFrame(rows, columns=["year", "w", "tags"])
    logger.info(f"D4 corpus {len(corpus)} works; concept names mapped {n_mapped}/{n_names}")
    cp = pd.read_parquet(C.WORK / "cp.parquet", columns=["concept_id", "year", "frame", "tags"])
    out = dict(n_works=len(corpus), name_map_rate=n_mapped / max(1, n_names), years={},
               note="percentile ranks of pool concepts are monotone in their (substrate-independent) strength within a "
                    "year, so level Spearman is trivially ~1; the informative checks are the percentile GAINS across "
                    "years and the overlap of top-20 association-strength neighbours")
    pct = {}
    for y in years:
        w = corpus[(corpus.year >= y - 2) & (corpus.year <= y)]
        g = build_cograph(list(w.tags.values), w.w.values, 2)
        gidx = g.index_of()
        cw = cp[(cp.year >= y - 2) & (cp.year <= y) & cp.frame]
        main = pd.read_parquet(SNAP / f"pool_metrics_y{y}.parquet", columns=["concept_id", "pct", "n_frame", "top_AS"]).set_index("concept_id")
        s_pool, jac = {}, []
        for cid, grp in cw.groupby("concept_id"):
            flat = np.concatenate(list(grp.tags.values)) if len(grp) else np.zeros(0, dtype=np.int64)
            s_pool[cid] = float(len(flat))
            u, cnt = np.unique(flat, return_counts=True)
            js = [(k, c) for k, c in zip(u.tolist(), cnt.tolist()) if k in gidx]
            if len(js) >= 5 and cid in main.index:
                AS = np.array([c * g.Wtot / (len(grp) * g.W[gidx[k]]) for k, c in js])
                top = {js[i][0] for i in np.argsort(-AS, kind="stable")[:20]}
                mt = set(json.loads(main.loc[cid, "top_AS"]))
                if mt:
                    jac.append(len(top & mt) / len(top | mt))
        all_s = np.sort(np.concatenate([g.s, np.array(list(s_pool.values()))]))
        pct[y] = {c: 100.0 * np.searchsorted(all_s, v, side="left") / len(all_s) for c, v in s_pool.items()}
        out["years"][str(y)] = dict(n_works_window=len(w), n_nodes=int(len(g.nodes)), n_pool=len(s_pool),
                                    median_pct_main=float(main.loc[main.n_frame > 0, "pct"].median()),
                                    median_pct_d4=float(np.median(list(pct[y].values()))),
                                    top20_AS_neighbour_jaccard_median=float(np.median(jac)) if jac else float("nan"),
                                    n_jaccard=len(jac))
    y0, y1 = years[0], years[-1]
    m0 = pd.read_parquet(SNAP / f"pool_metrics_y{y0}.parquet", columns=["concept_id", "pct", "n_frame"]).set_index("concept_id")
    m1 = pd.read_parquet(SNAP / f"pool_metrics_y{y1}.parquet", columns=["concept_id", "pct", "n_frame"]).set_index("concept_id")
    common = [c for c in pct[y0] if c in pct[y1] and m0.loc[c, "n_frame"] > 0 and m1.loc[c, "n_frame"] > 0]
    g_main = np.array([m1.loc[c, "pct"] - m0.loc[c, "pct"] for c in common])
    g_d4 = np.array([pct[y1][c] - pct[y0][c] for c in common])
    out["pct_gain_%d_%d" % (y0, y1)] = dict(n=len(common), spearman=float(spearmanr(g_main, g_d4).statistic) if len(common) > 4 else float("nan"),
                                            median_gain_main=float(np.median(g_main)) if len(common) else float("nan"),
                                            median_gain_d4=float(np.median(g_d4)) if len(common) else float("nan"))
    return out


def _key(ex: dict) -> str:
    try:
        return json.loads(ex["input"]).get("key", "")
    except (json.JSONDecodeError, TypeError, AttributeError):
        return ex.get("metadata_key") or ""


def grounding_lookup() -> dict:
    """Match pool phrases to dataset_4's LLM-labelled phrases (D2) and survivorship-free phrase pool (D5)."""
    norm = lambda s: re.sub(r"[\s\-]+", " ", str(s).lower()).strip()
    pool = pd.read_parquet(C.WORK / "pool.parquet", columns=["concept_id", "phrase", "fold"])
    ph = {norm(p): c for c, p in zip(pool.concept_id, pool.phrase)}
    labels, pool_hits = {}, []
    for f in sorted((C.D4 / "full_data_out").glob("full_data_out_*.json")):
        d = json.loads(f.read_text())
        for ds in d["datasets"]:
            if ds["dataset"].startswith("llm_labelled_candidate_phrases"):
                for ex in ds["examples"]:
                    key = norm(_key(ex))
                    if key in ph:
                        labels[ph[key]] = ex["output"]
            elif ds["dataset"].startswith("survivorship_free_phrase_pool"):
                for ex in ds["examples"]:
                    key = norm(_key(ex))
                    if key in ph:
                        pool_hits.append(ph[key])
        del d
    return dict(n_pool_phrases=len(ph), n_matched_llm_labels=len(labels), label_counts=Counter(labels.values()),
                matched=labels, n_in_d4_phrase_pool=len(set(pool_hits)))


@logger.catch(reraise=True)
def main() -> None:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="*", default=None, help="subset of: rewire d4 grounding (merges into robustness.json)")
    a = ap.parse_args()
    C.setup_logging("stage_robust")
    C.set_ram_limit(26)
    t0 = time.time()
    if a.only:
        res = json.loads((C.OUT / "robustness.json").read_text())
        if "rewire" in a.only:
            with ProcessPoolExecutor(max_workers=3, mp_context=mp.get_context("spawn")) as ex:
                res["rewire"] = list(ex.map(rewire_one, C.SPEC["rewire_snapshots"]))
            logger.info(f"rewire {res['rewire']}")
        if "d4" in a.only:
            res["d4_substrate"] = d4_substrate()
            logger.info(f"d4 {res['d4_substrate']}")
        if "grounding" in a.only:
            res["grounding_lookup"] = grounding_lookup()
        (C.OUT / "robustness.json").write_text(json.dumps(res, indent=1, default=str))
        logger.info(f"partial robust rerun {a.only} done in {time.time()-t0:.0f}s")
        return
    res: dict = {}
    snaps = C.SPEC["stability_snapshots"]
    with ProcessPoolExecutor(max_workers=max(1, min(4, C.detect_cpus()) - 1), mp_context=mp.get_context("spawn")) as ex:
        f_boot = [ex.submit(boot_one, (y, b)) for y in snaps for b in range(C.SPEC["stability_resamples"])]
        f_rew = [ex.submit(rewire_one, y) for y in C.SPEC["rewire_snapshots"]]
        f_edge = ex.submit(edge_filter_sensitivity, 2013)
        boots = [f.result() for f in f_boot]
        res["rewire"] = [f.result() for f in f_rew]
        res["edge_filter_raw_ge1"] = f_edge.result()
    bdf = pd.DataFrame(boots)
    res["leiden_stability"] = {str(y): dict(ami_mean=float(g.ami.mean()), ami_p05=float(g.ami.quantile(0.05)),
                                            ami_min=float(g.ami.min()), n=len(g)) for y, g in bdf.groupby("year")}
    logger.info(f"stability {res['leiden_stability']}")
    logger.info(f"rewire {res['rewire']}")
    try:
        res["d4_substrate"] = d4_substrate()
    except (KeyError, ValueError, OSError) as e:
        logger.exception("d4 substrate check failed")
        res["d4_substrate"] = dict(error=str(e))
    try:
        res["grounding_lookup"] = grounding_lookup()
    except (KeyError, ValueError, OSError) as e:
        logger.exception("grounding lookup failed")
        res["grounding_lookup"] = dict(error=str(e))
    res["secs"] = round(time.time() - t0, 1)
    (C.OUT / "robustness.json").write_text(json.dumps(res, indent=1, default=str))
    logger.info(f"robust done in {res['secs']}s")


if __name__ == "__main__":
    main()
