#!/usr/bin/env python3
"""MeSH adapter: per-concept yearly paper tables from the MeSH works (art_HGiVAYhqO-6q) and the four typology channels
(H, H_rar, RS, active_subfields_3y) computed with the SAME calls as vendor/stage_indicators.concept_indicators and
src/indicators.extra_channels (lib_metrics.rarefied_draws / stable_seed / shannon / rao_stirling, SPEC rarefy_m and
rarefy_draws, D and sidx from indicators.load_rs()). The frozen code is imported, never modified.

  python mesh_adapter.py gate   -> reproduction gate on 20 screen concepts (max |diff| < 1e-9 on all 4 channels)
  python mesh_adapter.py build  -> results/mesh/mesh_indicators.parquet (+ coverage-bias variant for retrieval_complete)
"""
from __future__ import annotations

import ast
import gzip
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from loguru import logger

WS = Path(__file__).resolve().parents[1]
E8 = WS / "exp8_frozen"
LOOP = WS.parents[2]
MESH_DS = LOOP / "iter_1/gen_art/gen_art_dataset_3"
import os
os.environ.setdefault("AII_LOOP_ROOT", str(LOOP))
sys.path.insert(0, str(E8 / "src"))
sys.path.insert(0, str(E8 / "vendor"))
import lib_metrics as lm  # noqa: E402
from config import SPEC  # noqa: E402

OUT = WS / "results" / "mesh"
CH4 = ["H", "H_rar", "RS", "active_subfields_3y"]


def load_rs_frozen():
    from indicators import load_rs
    return load_rs()


def channels(cid: str, F: float | None, papers: pd.DataFrame, D: np.ndarray, sidx: dict, y_last: int = 2024) -> list[dict]:
    """papers: rows (year, subfield) in the frozen row order; subfield -1 = unknown. Years max(2000,F-2)..2024,
    exactly the rows concept_indicators emits."""
    m, draws = SPEC["rarefy_m"], SPEC["rarefy_draws"]
    y_first = 2000 if (F is None or (isinstance(F, float) and math.isnan(F))) else max(2000, int(F) - 2)
    kn = papers[papers.subfield >= 0]
    vol_y = papers.groupby("year").size().to_dict()
    rows = []
    for y in range(y_first, y_last + 1):
        wp = kn[(kn.year >= y - 2) & (kn.year <= y)]
        sc = wp.subfield.value_counts().to_dict()
        subs_arr = wp.subfield.values
        dr = lm.rarefied_draws(len(subs_arr), m, draws, lm.stable_seed(cid, y, "H"))
        H_rar = float(np.nanmean([lm.shannon(pd.Series(subs_arr[d]).value_counts().values) for d in dr])) if dr else np.nan
        vc = wp.subfield.value_counts()
        vol3 = sum(vol_y.get(yy, 0) for yy in (y - 2, y - 1, y) if yy >= 2000)
        rows.append(dict(concept_id=cid, year=y, age=(y - int(F)) if (F is not None and not math.isnan(F)) else np.nan, vol=vol_y.get(y, 0), vol3=vol3,
                         subfield_count=len(sc), H=lm.shannon(sc.values()) if sc else np.nan,
                         RS=lm.rao_stirling(sc, dist_matrix=D, index=sidx) if sc else np.nan, H_rar=H_rar,
                         active_subfields_3y=int((vc >= 2).sum())))
    return rows


def gate(n: int = 20) -> dict:
    D, sidx = load_rs_frozen()
    ind = pd.read_parquet(E8 / "results/indicators/concept_year_indicators_hyd.parquet")
    cp_path = E8 / "heldout_run/work/cp_hyd.parquet"
    cp = pd.read_parquet(cp_path, columns=["concept_id", "year", "type", "subfield", "tags"])
    # the held-out cp table carries the 60 reference concepts computed by the frozen screen pipeline; screen MAIN
    # c-papers are not materialised in the copy, so the gate uses those 20 of 60 reference concepts (same DS5 rows,
    # same frozen indicator code) plus, when available, 20 held-out concepts against heldout_run indicators.
    scr = ind.concept_id.unique()
    ids = sorted(set(scr) & set(cp.concept_id))[:n]
    diffs = {c: 0.0 for c in CH4}
    n_rows, n_nan_mismatch = 0, 0
    for c in ids:
        g = cp[cp.concept_id == c]
        ref = ind[ind.concept_id == c].set_index("year")
        F = float(ref.F.iloc[0])
        got = pd.DataFrame(channels(c, F, g, D, sidx)).set_index("year")
        common = got.index.intersection(ref.index)
        n_rows += len(common)
        for ch in CH4:
            a, b = got.loc[common, ch].astype(float).values, ref.loc[common, ch].astype(float).values
            n_nan_mismatch += int((np.isnan(a) != np.isnan(b)).sum())
            ok = ~np.isnan(a) & ~np.isnan(b)
            if ok.any():
                diffs[ch] = max(diffs[ch], float(np.abs(a[ok] - b[ok]).max()))
    ho_path = E8 / "heldout_run/results/indicators/concept_year_indicators_hyd.parquet"
    ho_ids = []
    if ho_path.exists():
        hind = pd.read_parquet(ho_path)
        ho_ids = sorted(set(hind[(hind.fold == "screen") & hind.MAIN].concept_id) & set(cp.concept_id))[:n]
        for c in ho_ids:
            g = cp[cp.concept_id == c]
            ref = hind[hind.concept_id == c].set_index("year")
            got = pd.DataFrame(channels(c, float(ref.F.iloc[0]), g, D, sidx)).set_index("year")
            common = got.index.intersection(ref.index)
            n_rows += len(common)
            for ch in CH4:
                a, b = got.loc[common, ch].astype(float).values, ref.loc[common, ch].astype(float).values
                n_nan_mismatch += int((np.isnan(a) != np.isnan(b)).sum())
                ok = ~np.isnan(a) & ~np.isnan(b)
                if ok.any():
                    diffs[ch] = max(diffs[ch], float(np.abs(a[ok] - b[ok]).max()))
    ids = ids + ho_ids
    passed = bool(max(diffs.values()) < 1e-9 and n_nan_mismatch == 0 and n_rows > 0)
    res = dict(n_concepts=len(ids), concept_ids=ids, n_rows=n_rows, max_abs_diff=diffs, nan_pattern_mismatches=n_nan_mismatch,
               passed=passed, source_cp=str(cp_path.relative_to(WS)), reference="exp8_frozen/results/indicators/concept_year_indicators_hyd.parquet")
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "adapter_gate.json").write_text(json.dumps(res, indent=1))
    logger.info(f"adapter gate: {res['max_abs_diff']} nan-mismatch {n_nan_mismatch} passed={passed}")
    return res


def load_mesh_population() -> pd.DataFrame:
    d = json.loads((MESH_DS / "full_data_out.json").read_text())
    ex = [x for x in d["datasets"] if x["dataset"] == "heldout_mesh_concepts"][0]["examples"]
    rows = []
    for e in ex:
        inp = json.loads(e["input"])
        rows.append(dict(concept_id=e["metadata_concept_id"], preferred_term=e["metadata_preferred_term"], F=int(e["metadata_F"]),
                         branch_group=e["metadata_branch_group"], retrieval_complete=str(e["metadata_retrieval_complete"]) == "True",
                         rule_parity=str(e["metadata_rule_parity"]) == "True", origin_field=inp.get("origin_field"),
                         origin_subfield=inp.get("origin_subfield"), volume_tercile=e["metadata_volume_tercile"]))
    return pd.DataFrame(rows)


def load_mesh_works() -> pd.DataFrame:
    rows = []
    for p in sorted((MESH_DS / "works").glob("works_part_*.jsonl.gz")):
        with gzip.open(p, "rt") as fh:
            for line in fh:
                r = json.loads(line)
                if str(r.get("verified_text_match")) != "True":
                    continue
                pt = r.get("primary_topic")
                sf = -1
                if pt not in (None, "None", ""):
                    try:
                        v = ast.literal_eval(pt) if isinstance(pt, str) else pt
                        sf = int(v.get("subfield_id")) if v and v.get("subfield_id") is not None else -1
                    except (ValueError, SyntaxError):
                        sf = -1
                au_raw = r.get("authorships")
                try:
                    au_l = ast.literal_eval(au_raw) if isinstance(au_raw, str) and au_raw not in ("None", "") else (au_raw or [])
                    au = [a["author_id"] for a in au_l]
                except (ValueError, SyntaxError, TypeError, KeyError):
                    au = []
                rows.append(dict(concept_id=r["concept_id"], work_id=int(r["work_id"]), year=int(r["publication_year"]),
                                 subfield=sf, match_route=r.get("match_route"), indexed_in=r.get("indexed_in"), authors=au))
    w = pd.DataFrame(rows)
    w = w[(w.year >= 2000) & (w.year <= 2024)].drop_duplicates(["concept_id", "work_id"]).sort_values(["concept_id", "year", "work_id"])
    return w.reset_index(drop=True)


def build() -> None:
    D, sidx = load_rs_frozen()
    pop = load_mesh_population()
    w = load_mesh_works()
    OUT.mkdir(parents=True, exist_ok=True)
    w.to_parquet(OUT / "mesh_cpapers.parquet", index=False)
    pop.to_parquet(OUT / "mesh_population.parquet", index=False)
    logger.info(f"MeSH works (verified): {len(w)} rows, {w.concept_id.nunique()} concepts; routes {w.match_route.value_counts().to_dict()}")
    rows = []
    for r in pop.itertuples(index=False):
        rows.extend(channels(r.concept_id, float(r.F), w[w.concept_id == r.concept_id], D, sidx))
    ind = pd.DataFrame(rows).merge(pop, on="concept_id", how="left", suffixes=("", "_pop"))
    ind["F"] = ind.concept_id.map(pop.set_index("concept_id").F)
    ind.to_parquet(OUT / "mesh_indicators.parquet", index=False)
    # coverage bias: retrieval_complete concepts, all verified works vs PubMed-route works only
    rc = pop[pop.retrieval_complete]
    pub = w[w.match_route.astype(str) != "openalex_nonpubmed_search"]  # PubMed route = pubmed_tiab + mesh_indexed_only
    rows2 = []
    for r in rc.itertuples(index=False):
        rows2.extend(channels(r.concept_id, float(r.F), pub[pub.concept_id == r.concept_id], D, sidx))
    cov = pd.DataFrame(rows2)
    cov["F"] = cov.concept_id.map(pop.set_index("concept_id").F)
    cov.to_parquet(OUT / "mesh_indicators_pubmed_only_rc.parquet", index=False)
    logger.info(f"MeSH indicators: {len(ind)} rows; coverage variant {len(cov)} rows for {rc.shape[0]} concepts")


if __name__ == "__main__":
    logger.remove()
    logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
    logger.add(str(WS / "logs/mesh_adapter.log"), rotation="30 MB", level="DEBUG")
    {"gate": gate, "build": build}[sys.argv[1]]()
