"""STEP 1 cache + STEP 2 driver: prepare inputs and build all yearly snapshots in parallel (spawn pool)."""

from __future__ import annotations

import json
import multiprocessing as mp
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import numpy as np
import pandas as pd
from loguru import logger

import load
import network
import rq1_spec as S


def prepare(mini: bool) -> dict:
    """Load everything once and write spawn-safe caches to results/intermediate/."""
    load.INTER.mkdir(parents=True, exist_ok=True)
    concepts = load.load_concepts()
    mw = load.load_mesh_works()
    bg, bg_info = load.load_background()
    bg.to_parquet(load.INTER / "bg.parquet")
    names = load.load_concept_names()
    twins = load.find_twins(concepts, names)
    (load.INTER / "twins.json").write_text(json.dumps(twins))
    concepts.to_parquet(load.INTER / "concepts.parquet")

    # 1d ID-space check
    prim = mw[mw.primary]
    all_tags = [t for ts in prim.tags for t in ts]
    bg_vocab = {t for ts in bg.tags for t in ts}
    vocab = set(names.cid.tolist())
    share_vocab = float(np.mean([t in vocab for t in all_tags])) if all_tags else 0.0
    share_bg = float(np.mean([t in bg_vocab for t in all_tags])) if all_tags else 0.0
    if share_vocab < 0.9:
        raise RuntimeError(f"ID-space check failed: only {share_vocab:.3f} of MeSH tag ids in bg vocabulary (F1)")

    # T2: works-derived yearly counts vs table counts
    wc = prim.drop_duplicates(["concept_id", "work_id"]).groupby(["concept_id", "year"]).size().to_dict()
    agree = tot = 0
    for r in concepts.itertuples(index=False):
        rd = r._asdict()
        for y in S.YEARS:
            tot += 1
            agree += int(wc.get((rd["concept_id"], y), 0) == int(rd[f"tm_{y}"]))
    # twin removal changes no bg edges by construction (twins only filter focal->tag edges)
    info = {"bg": bg_info, "tag_share_in_concepts_parquet": share_vocab, "tag_share_in_bg_sample": share_bg,
            "n_twin_concepts": int(sum(1 for v in twins.values() if v)),
            "n_twin_ids": int(sum(len(v) for v in twins.values())),
            "works_vs_table_yearly_count_agreement": agree / tot,
            "n_primary_rows": int(len(prim)), "n_primary_unique_works": int(prim.work_id.nunique())}
    logger.info(f"prepare: {info}")
    return info


def rewire_units(concepts: pd.DataFrame, years: list[int]) -> list[str]:
    """Seeded 10% subsample of focal concept-years (c,y) with >=1 primary work in the window."""
    mw = pd.read_parquet(load.INTER / "mesh_works.parquet")
    mw = mw[mw.primary & mw.concept_id.isin(concepts.concept_id)]
    cand = set()
    by = mw.groupby("concept_id").year.apply(lambda s: set(s))
    for cid, ys in by.items():
        for y in years:
            if any(y - S.WINDOW + 1 <= q <= y for q in ys):
                cand.add(f"{cid}|{y}")
    cand = sorted(cand)
    rng = np.random.default_rng(S.SEED)
    k = int(round(S.REWIRE_FRAC * len(cand)))
    sel = sorted(rng.choice(cand, size=k, replace=False).tolist()) if k else []
    logger.info(f"rewiring subsample: {len(sel)} of {len(cand)} focal concept-years")
    return sel


def run_snapshots(concept_ids: list[str], years: list[int], n_workers: int) -> list[dict]:
    concepts = pd.read_parquet(load.INTER / "concepts.parquet")
    concepts = concepts[concepts.concept_id.isin(concept_ids)]
    units = rewire_units(concepts, years)
    (load.RESULTS / "rewire_units.json").write_text(json.dumps(units))
    jobs = [(y, list(concept_ids), [u for u in units if u.endswith(f"|{y}")], False, "") for y in years]
    # sensitivity: one snapshot without low-confidence-topic works (hazard H1)
    sens_year = 2014 if 2014 in years else years[len(years) // 2]
    jobs.append((sens_year, list(concept_ids), [], True, "_nolowconf"))
    # larger jobs (later years, more works) first
    jobs.sort(key=lambda j: -j[0])
    stats = []
    t0 = time.time()
    ctx = mp.get_context("spawn")
    with ProcessPoolExecutor(max_workers=n_workers, mp_context=ctx) as ex:
        futs = {ex.submit(network.worker, j): j for j in jobs}
        for fu in as_completed(futs):
            j = futs[fu]
            try:
                st = fu.result()
                stats.append(st)
                logger.info(f"snapshot {j[0]}{j[4]} done: nodes {st['n_nodes']} edges {st['n_edges']} "
                            f"comm {st['n_communities']} nmi {st['nmi_seeds_mean']:.3f} focal {st['n_focal']} "
                            f"t {st['t_total_s']:.0f}s (elapsed {time.time() - t0:.0f}s)")
            except Exception:
                logger.exception(f"snapshot {j[0]}{j[4]} failed")
                raise
    stats.sort(key=lambda s: (s["year"], s["tag"]))
    (load.RESULTS / "snapshot_stats.json").write_text(json.dumps(stats, indent=1))
    return stats
