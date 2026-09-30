#!/usr/bin/env python3
"""STAGE 4: community-partition robustness layer.

Seed 0 = the iteration-2 partition (X3 nodes_y.comm, best of 5 Leiden runs). Seeds 101-105 = single Leiden runs
(RBConfiguration, AS weights, resolution 1.0, n_iterations=-1) on the same kept graph. For every partition: the vendored
alluvial rule (Jaccard >= 0.3 continuation, min community size 5, birth/death/split/merge) gives persistent ids, and
per concept-year role inputs are recomputed (all-type community weights, P_raw, P_rar with the same rarefaction seeds,
within-module z with k_own of that partition, dominant community, founder rank).

Outputs: work/leiden_seeds/memb_y{y}.parquet, work/leiden_seeds/cm_y{y}.parquet, work/leiden_seeds/persistent_s{s}.parquet,
work/leiden_seeds/events_s{s}.parquet, results/leiden_seeds_ami.csv, results/alluvial_reproduction.json.
"""
from __future__ import annotations

import multiprocessing as mp
import time
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed

import numpy as np
import pandas as pd
from loguru import logger

from common import NEW_SEEDS, RES, SNAP_X3, WORK, X3, YEARS, C, setup_logging, write_json

LS = WORK / "leiden_seeds"
SEEDS = [0] + NEW_SEEDS


def leiden_single(g, seed: int) -> np.ndarray:
    import igraph as ig
    import leidenalg
    ki, kj, kw = g.ei[g.kept], g.ej[g.kept], g.AS[g.kept]
    kept_nodes = np.unique(np.concatenate([ki, kj]))
    remap = -np.ones(len(g.nodes), dtype=np.int64)
    remap[kept_nodes] = np.arange(len(kept_nodes))
    G = ig.Graph(n=len(kept_nodes), edges=list(zip(remap[ki].tolist(), remap[kj].tolist())))
    G.es["weight"] = kw.tolist()
    part = leidenalg.find_partition(G, leidenalg.RBConfigurationVertexPartition, weights="weight",
                                    resolution_parameter=1.0, seed=seed, n_iterations=-1)
    memb = -np.ones(len(g.nodes), dtype=np.int64)
    memb[kept_nodes] = np.array(part.membership)
    return memb


def k_own_of(g, memb: np.ndarray) -> np.ndarray:
    same = (memb[g.ei] == memb[g.ej]) & (memb[g.ei] >= 0)
    k_own = np.zeros(len(g.nodes))
    np.add.at(k_own, g.ei[same], g.c[same])
    np.add.at(k_own, g.ej[same], g.c[same])
    return k_own


def seeds_year(y: int, concept_ids: list[str]) -> dict:
    import lib_metrics as lm
    from sklearn.metrics import adjusted_mutual_info_score
    from attach import load_cograph
    from stage_snapshots import _comm_weights, _rarefied_P
    setup_logging(f"seeds_{y}")
    t0 = time.time()
    g, memb0, k_own0, _ = load_cograph(y)
    idx = g.index_of()
    parts = {0: (memb0, k_own0)}
    ami = {}
    for s in NEW_SEEDS:
        m = leiden_single(g, s)
        parts[s] = (m, k_own_of(g, m))
        kept = memb0 >= 0
        ami[s] = float(adjusted_mutual_info_score(memb0[kept], m[kept]))
    pd.DataFrame({"node": g.nodes, **{f"comm_s{s}": parts[s][0] for s in SEEDS}}).to_parquet(LS / f"memb_y{y}.parquet", index=False)
    tags = pd.read_parquet(WORK / "attach" / f"tags_y{y}.parquet")
    tags = tags[tags.concept_id.isin(set(concept_ids))]
    y0 = y - 2
    cp = pd.read_parquet(WORK / "cp_hyd.parquet", columns=["concept_id", "year", "tags"],
                         filters=[("year", ">=", y0), ("year", "<=", y)])
    cp = cp[cp.concept_id.isin(set(concept_ids))]
    cp_by = {c: list(gr.tags.values) for c, gr in cp.groupby("concept_id")}
    rows = []
    comm_members = {s: pd.Series(np.arange(len(g.nodes))).groupby(parts[s][0]).apply(np.asarray).to_dict() for s in SEEDS}
    for cid, tg in tags.groupby("concept_id"):
        x_all = dict(zip(tg.node.values.tolist(), tg.x_all.values.tolist()))
        x_fr = {k: v for k, v in zip(tg.node.values.tolist(), tg.x_frame.values.tolist()) if v > 0}
        tl = cp_by.get(cid, [])
        for s in SEEDS:
            memb, k_own = parts[s]
            cw_all = _comm_weights(x_all, idx, memb)
            cw_fr = _comm_weights(x_fr, idx, memb)
            tot = sum(cw_all.values())
            dom = int(max(cw_all, key=cw_all.get)) if cw_all else -1
            r = dict(concept_id=cid, year=y, seed=s, dom_comm=dom, P_raw=lm.participation(cw_all) if cw_all else np.nan,
                     n_comm_25pct=int(sum(1 for v in cw_all.values() if tot > 0 and v >= 0.25 * tot)),
                     n_comm_10pct_all=int(sum(1 for v in cw_all.values() if tot > 0 and v >= 0.10 * tot)),
                     dom_share=float(cw_all[dom] / tot) if dom >= 0 and tot > 0 else np.nan)
            r["P_rar"] = _rarefied_P(tl, idx, memb, C.SPEC["rarefy_m"], C.SPEC["rarefy_draws"], lm.stable_seed(cid, y, "P"))
            if cw_fr:
                s_star = max(cw_fr, key=cw_fr.get)
                r["wmz"] = lm.within_module_z(float(cw_fr[s_star]), k_own[memb == s_star])
            else:
                r["wmz"] = np.nan
            if dom >= 0:
                w = float(cw_fr.get(dom, 0.0))
                peers = k_own[comm_members[s][dom]]
                r["founder_rank"] = int(1 + np.sum(peers > w)) if w > 0 else 10 ** 6
            else:
                r["founder_rank"] = 10 ** 6
            r["cw_all_json"] = "{" + ",".join(f'"{k}":{v}' for k, v in cw_all.items()) + "}"
            rows.append(r)
    pd.DataFrame(rows).to_parquet(LS / f"cm_y{y}.parquet", index=False)
    out = dict(year=y, **{f"ami_s{s}": v for s, v in ami.items()},
               **{f"n_comm_s{s}": int(parts[s][0].max() + 1) for s in SEEDS}, secs=round(time.time() - t0, 1))
    logger.info(f"seeds y={y} {out}")
    return out


def alluvial_from(memb_by_year: dict[int, pd.DataFrame], thr: float = 0.3, min_size: int = 5) -> tuple[pd.DataFrame, pd.DataFrame]:
    """The iteration-2 stage_snapshots.alluvial() algorithm, verbatim, on in-memory (node, comm) tables."""
    next_id = 0
    prev_map: dict[int, int] = {}
    prev_sets: dict[int, set] = {}
    events, comm_rows = [], []
    for y in sorted(memb_by_year):
        nd = memb_by_year[y]
        nd = nd[nd.comm >= 0]
        sizes = nd.comm.value_counts()
        big = set(sizes[sizes >= min_size].index)
        cur_sets = {int(c): set(grp.node.tolist()) for c, grp in nd[nd.comm.isin(big)].groupby("comm")}
        cur_map: dict[int, int] = {}
        if prev_sets:
            pairs = []
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
    return pd.DataFrame(comm_rows), pd.DataFrame(events)


def verify_seed0_alluvial() -> dict:
    mb = {y: pd.read_parquet(SNAP_X3 / f"nodes_y{y}.parquet", columns=["node", "comm"]) for y in YEARS}
    cm, ev = alluvial_from(mb)
    x3 = pd.read_parquet(X3 / "work" / "communities" / "persistent_ids.parquet")
    x3e = pd.read_parquet(X3 / "work" / "communities" / "alluvial_events.parquet")
    a = cm.sort_values(["year", "comm"]).reset_index(drop=True)
    b = x3.sort_values(["year", "comm"]).reset_index(drop=True)
    ok = bool(a[["year", "comm", "pid", "size"]].equals(b[["year", "comm", "pid", "size"]].astype(a[["year", "comm", "pid", "size"]].dtypes)))
    return dict(persistent_ids_identical=ok, n_rows=len(a), n_rows_x3=len(b),
                events_identical_counts=ev.event.value_counts().to_dict() == x3e.event.value_counts().to_dict())


@logger.catch(reraise=True)
def main(workers: int = 4) -> None:
    setup_logging("leiden_seeds")
    C.set_ram_limit(26)
    t0 = time.time()
    rep = verify_seed0_alluvial()
    write_json(RES / "alluvial_reproduction.json", rep)
    logger.info(f"seed-0 alluvial reproduction {rep}")
    pool = pd.read_parquet(WORK / "pool_active.parquet")
    C.assert_not_sealed(pool.concept_id)
    ids = pool.concept_id.tolist()
    infos = []
    with ProcessPoolExecutor(max_workers=workers, mp_context=mp.get_context("spawn")) as ex:
        futs = {ex.submit(seeds_year, y, ids): y for y in YEARS}
        for f in as_completed(futs):
            infos.append(f.result())
            logger.info(f"seeds year {futs[f]} ok ({time.time() - t0:.0f}s)")
    info = pd.DataFrame(infos).sort_values("year")
    info.to_csv(RES / "leiden_seeds_ami.csv", index=False)
    memb = {y: pd.read_parquet(LS / f"memb_y{y}.parquet") for y in YEARS}
    for s in SEEDS:
        cm, ev = alluvial_from({y: m[["node", f"comm_s{s}"]].rename(columns={f"comm_s{s}": "comm"}) for y, m in memb.items()})
        cm.to_parquet(LS / f"persistent_s{s}.parquet", index=False)
        ev.to_parquet(LS / f"events_s{s}.parquet", index=False)
        logger.info(f"seed {s}: {cm.pid.nunique()} persistent communities; events {ev.event.value_counts().to_dict()}")
    logger.info(f"leiden seeds done in {time.time() - t0:.0f}s; mean AMI vs seed 0 "
                f"{ {s: round(info[f'ami_s{s}'].mean(), 3) for s in NEW_SEEDS} }")


if __name__ == "__main__":
    main()
