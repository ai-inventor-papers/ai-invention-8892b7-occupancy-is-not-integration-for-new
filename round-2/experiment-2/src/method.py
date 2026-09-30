#!/usr/bin/env python3
"""Citation gate, viability labels and power check: orchestrator.

Execution order (plan): 0 prereg -> 1-lite (loaders + lenient reproduction) -> 2 Gate A -> 3 viability layer
-> 5-origin (cooling onsets, needed by 6c) -> 6 power -> 1-full audit -> 4 synthetic validation -> 5 P1 -> assemble.

Usage: uv run method.py [stage ...]   (stages: prereg gate_a viability origin power audit synth p1 figures assemble all)
"""
from __future__ import annotations

import json
import os

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_v, "1")
import multiprocessing as mp
import pickle
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from loguru import logger  # noqa: E402

import io_load  # noqa: E402
from common import B, RESULTS, SEED, detect_cpus, set_ram_limit, setup_logging  # noqa: E402

CACHE = RESULTS / "cache"
N_WORKERS = min(4, detect_cpus())


def pool_map(fn, items, payload: dict, label: str) -> list:
    import edges
    out = [None] * len(items)
    t0 = time.time()
    with ProcessPoolExecutor(max_workers=N_WORKERS, mp_context=mp.get_context("spawn"),
                             initializer=edges.init_worker, initargs=(payload,)) as ex:
        futs = {ex.submit(fn, it): i for i, it in enumerate(items)}
        done = 0
        for f in as_completed(futs):
            i = futs[f]
            try:
                out[i] = f.result()
            except Exception:
                logger.exception(f"{label}: task {items[i] if not isinstance(items[i], tuple) else items[i][0]} failed")
                raise
            done += 1
            if done % 20 == 0 or done == len(items):
                logger.info(f"{label}: {done}/{len(items)} ({time.time() - t0:.0f}s)")
    return out


def stage_gate_a() -> None:
    import edges
    import gate_a
    G = io_load.prepare()
    chk = gate_a.lenient_check(G["links_lenient"])
    (RESULTS / "gate_a").mkdir(parents=True, exist_ok=True)
    (RESULTS / "gate_a" / "lenient_loader_check.json").write_text(json.dumps(chk, indent=2, default=str))
    totals = io_load.load_totals()
    payload = {"totals": totals}
    con = G["concepts"]
    refs = con[con.arm == "reference"].concept_id.tolist()
    mains = con[con.arm == "main"].concept_id.tolist()
    ref_rows = pool_map(edges.run_ref_task, refs, payload, "ref-pass")
    ref_df = pd.DataFrame([r for rr in ref_rows for r in rr])
    ref_df.to_parquet(CACHE / "ref_cells.parquet", index=False)
    res = pool_map(edges.run_main_task, [(c, {"boot": False}) for c in mains], payload, "main-noboot")
    e = pd.DataFrame([r for x in res for r in x["rows"]])
    ct = [c for x in res for c in x["ct"]]
    e.to_parquet(CACHE / "main_edges_noboot.parquet", index=False)
    (CACHE / "ct_counts.pkl").write_bytes(pickle.dumps(ct))
    gate_a.gate_a_tables(e, ref_df, con)
    gf = gate_a.graft_fallback(G)
    logger.info(f"graft fallback: {gf['n_events_all']} events, {gf['n_events_kw5']} with >= 5 keywords")


def stage_viability() -> None:
    import viability
    viability.run(pool_map)


def main(stages: list[str]) -> None:
    setup_logging("method")
    set_ram_limit(24)
    CACHE.mkdir(parents=True, exist_ok=True)
    order = ["gate_a", "viability", "origin", "power", "audit", "synth", "p1", "figures", "assemble"]
    if stages == ["all"]:
        stages = order
    for s in stages:
        t0 = time.time()
        logger.info(f"=== stage {s} ===")
        if s == "prereg":
            import prereg
            prereg.main()
        elif s == "gate_a":
            stage_gate_a()
        elif s == "viability":
            stage_viability()
        elif s == "origin":
            import origin
            origin.run()
        elif s == "power":
            import power_h1
            import power_h2
            power_h1.run()
            power_h2.run()
        elif s == "power_h1":
            import power_h1
            power_h1.run()
        elif s == "power_h2":
            import power_h2
            power_h2.run()
        elif s == "audit":
            import audit
            audit.run()
        elif s == "synth":
            import synth
            synth.run()
        elif s == "p1":
            import p1
            p1.run()
        elif s == "figures":
            import figures
            figures.run()
        elif s == "assemble":
            import assemble_out
            assemble_out.run()
        else:
            raise ValueError(f"unknown stage {s}")
        logger.info(f"=== stage {s} done in {time.time() - t0:.0f}s ===")


if __name__ == "__main__":
    logger.catch(reraise=True)(main)(sys.argv[1:] or ["all"])
