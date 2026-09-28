"""STEP 1 - load the MeSH concept table, the MeSH works, the background sample and the denominators."""

from __future__ import annotations

import gzip
import hashlib
import json
import os
import re
from pathlib import Path

import numpy as np
import pandas as pd
from loguru import logger

import rq1_spec as S

ROOT = Path(__file__).resolve().parent
# iteration-1 dependency workspaces: <run>/3_invention_loop/iter_1/gen_art (override with AII_ITER1_GEN_ART)
RUN = Path(os.environ.get("AII_ITER1_GEN_ART", str(ROOT.parents[2] / "round-1" / ".")))
DS1 = RUN / "gen_art_dataset_1"
DS2 = RUN / "gen_art_dataset_2"
DS3 = RUN / "gen_art_dataset_3"
RESULTS = ROOT / "results"
INTER = RESULTS / "intermediate"


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def f_band(F: int) -> str:
    for name, (a, b) in S.F_BANDS.items():
        if a <= F <= b:
            return name
    return "other"


def load_concepts() -> pd.DataFrame:
    """1a: concept table, one row per MeSH concept, with yearly volume series."""
    p = DS3 / "data_out.json"
    if p.exists():
        rows = json.loads(p.read_text())
    else:  # documented fallback
        full = json.loads((DS3 / "full_data_out.json").read_text())
        ds = [d for d in full["datasets"] if d["dataset"] == "heldout_mesh_concepts"][0]
        rows = []
        for ex in ds["examples"]:
            r = {"input": json.loads(ex["input"]), "output": json.loads(ex["output"])}
            r["metadata"] = {k.replace("metadata_", ""): v for k, v in ex.items() if k.startswith("metadata_")}
            rows.append(r)
    recs = []
    for r in rows:
        i, o, m = r["input"], r["output"], r["metadata"]
        de = i.get("date_established") or ""
        rec = {
            "concept_id": i["concept_id"],
            "F": int(i["F"]),
            "preferred_term": i["preferred_term"],
            "surface_forms": list(i.get("surface_forms") or []),
            "acronyms": list(i.get("acronyms") or []),
            "origin_field": int(i["origin_field"]) if i.get("origin_field") is not None else -1,
            "origin_subfield": int(i["origin_subfield"]) if i.get("origin_subfield") is not None else -1,
            "date_established": de,
            "de_year": int(de[:4]) if de[:4].isdigit() else int(i.get("mesh_year_established") or 9999),
            "tree_branch": i.get("tree_branch_primary"),
            "retrieval_complete": bool(m.get("retrieval_complete")),
            "rule_parity": bool(m.get("rule_parity")),
            "stratum": m.get("stratum"),
        }
        rec["retrieval_complete"] = bool(m.get("retrieval_complete"))
        npg = o.get("yearly_counts_nonpubmed_openalex_groupby")
        rec["np_available"] = npg is not None
        for y in S.YEARS:
            rec[f"tm_{y}"] = float(o["yearly_counts_textmatch"].get(str(y), 0))
            rec[f"mi_{y}"] = float(o["yearly_counts_mesh_indexed"].get(str(y), 0))
            # SENS1 volume: verified text-match + non-PubMed group_by count. Where the non-PubMed works were
            # paged and verified (retrieval_complete) they are already inside tm, so nothing is added; where the
            # group_by series is missing (19 'pubmed_route_verified_only' concepts) SENS1 falls back to tm.
            add = float(npg.get(str(y), 0)) if (npg is not None and not rec["retrieval_complete"]) else 0.0
            rec[f"s1_{y}"] = rec[f"tm_{y}"] + add
        recs.append(rec)
    df = pd.DataFrame(recs)
    df["F_band"] = df.F.map(f_band)
    assert len(df) == 191, f"expected 191 concepts, got {len(df)}"
    logger.info(f"concepts: {len(df)} rows; F-bands {df.F_band.value_counts().to_dict()}; "
                f"rule_parity {int(df.rule_parity.sum())}; retrieval_complete {int(df.retrieval_complete.sum())}")
    return df


def load_mesh_works() -> pd.DataFrame:
    """1b: primary (verified text-match, not mesh-indexed-only) concept-work rows with legacy tags."""
    INTER.mkdir(parents=True, exist_ok=True)
    cache = INTER / "mesh_works.parquet"
    if cache.exists():
        return pd.read_parquet(cache)
    recs = []
    n_all = 0
    for p in sorted((DS3 / "works").glob("works_part_*.jsonl.gz")):
        with gzip.open(p, "rt") as f:
            for line in f:
                n_all += 1
                r = json.loads(line)
                tags = [int(c["id"]) for c in (r.get("concepts") or [])
                        if c.get("score", 0) >= S.TAG_MIN_SCORE and (c.get("level", 0) >= 1 or not S.EXCLUDE_LEVEL0)]
                pt = r.get("primary_topic") or {}
                recs.append({
                    "concept_id": r["concept_id"],
                    "work_id": int(r["work_id"]),
                    "year": int(r["publication_year"]) if r.get("publication_year") else -1,
                    "primary": bool(r.get("verified_text_match")) and r.get("match_route") != "mesh_indexed_only",
                    "mesh_indexed": bool(r.get("descriptor_indexed_pubmed")) or bool(r.get("descriptor_indexed_openalex")),
                    "subfield_id": int(pt["subfield_id"]) if pt.get("subfield_id") is not None else -1,
                    "wtype": r.get("type") or "",
                    "tags": tags,
                })
    df = pd.DataFrame(recs)
    logger.info(f"mesh works rows: {n_all}; primary {int(df.primary.sum())}; mesh_indexed {int(df.mesh_indexed.sum())}")
    df.to_parquet(cache)
    return df


def load_background() -> tuple[pd.DataFrame, dict]:
    """1c: background sample with post-stratified yearly weights and level>=1, score>=0.3 tags (int ids)."""
    cols = ["work_id", "year", "subfield_id", "low_conf_topic", "weight", "concept_ids", "concept_scores", "concept_levels"]
    bg = pd.read_parquet(DS2 / "data" / "bg_work_sample.parquet", columns=cols)
    tot = pd.read_parquet(DS2 / "data" / "subfield_year_totals.parquet")
    tot = tot[tot.subfield != "unknown"].assign(subfield=lambda d: d.subfield.astype(int))
    tot = tot[["subfield", "year", "n_frame", "n_sampled"]]
    bg = bg.merge(tot, left_on=["subfield_id", "year"], right_on=["subfield", "year"], how="left")
    bg["w_year"] = bg.n_frame / bg.n_sampled
    miss = bg.w_year.isna() | ~np.isfinite(bg.w_year)
    bg.loc[miss, "w_year"] = bg.loc[miss, "weight"]  # unknown subfield-year keeps its design weight
    tags = []
    for ids, sc, lv in zip(bg.concept_ids, bg.concept_scores, bg.concept_levels):
        sc = np.asarray(sc, dtype=float)
        lv = np.asarray(lv, dtype=int)
        keep = (sc >= S.TAG_MIN_SCORE) & ((lv >= 1) | (not S.EXCLUDE_LEVEL0))
        tags.append([int(x[1:]) for x, k in zip(ids, keep) if k])
    bg["tags"] = tags
    info = {
        "n_works": int(len(bg)),
        "n_w_year_missing_used_design_weight": int(miss.sum()),
        "low_conf_topic_share_raw": float(bg.low_conf_topic.mean()),
        "low_conf_topic_share_weighted": float((bg.w_year * bg.low_conf_topic).sum() / bg.w_year.sum()),
        "mean_tags_per_work": float(np.mean([len(t) for t in tags])),
    }
    # T2: weighted window totals vs exact frame totals
    frame_tot = tot.groupby("year").n_frame.sum()
    est = bg.groupby("year").w_year.sum()
    info["weighted_vs_frame_max_abs_rel_dev"] = float(((est - frame_tot) / frame_tot).abs().max())
    bg = bg[["work_id", "year", "subfield_id", "low_conf_topic", "w_year", "tags"]]
    logger.info(f"background: {info}")
    return bg, info


def load_concept_names() -> pd.DataFrame:
    c = pd.read_parquet(DS2 / "data" / "concepts.parquet", columns=["concept_id", "display_name", "level"])
    c["cid"] = c.concept_id.str[1:].astype(np.int64)
    return c


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s.strip().lower())


def find_twins(concepts: pd.DataFrame, names: pd.DataFrame) -> dict[str, list[int]]:
    """1e: legacy concepts whose lower-cased name equals the preferred term / a surface form / an acronym."""
    lut: dict[str, list[int]] = {}
    for cid, nm in zip(names.cid, names.display_name):
        if isinstance(nm, str):
            lut.setdefault(_norm(nm), []).append(int(cid))
    twins = {}
    for _, r in concepts.iterrows():
        forms = {_norm(r.preferred_term)} | {_norm(x) for x in r.surface_forms} | {_norm(x) for x in r.acronyms}
        ids = sorted({i for f in forms for i in lut.get(f, [])})
        twins[r.concept_id] = ids
    logger.info(f"twins: {sum(1 for v in twins.values() if v)} concepts have >=1 legacy twin "
                f"({sum(len(v) for v in twins.values())} twin ids)")
    return twins


def load_denominators() -> dict[int, float]:
    """Kleinberg d_t: OpenAlex all_types works per year (dataset_1 context/subfield_year_totals.json)."""
    s = json.loads((DS1 / "context" / "subfield_year_totals.json").read_text())
    a = s["variants"]["all_types"]
    d = {}
    for y, v in a.items():
        d[int(y)] = float(v.get("total_with_topic", sum(v["subfield"].values()))) + float(v.get("unknown", 0) or 0)
    return d
