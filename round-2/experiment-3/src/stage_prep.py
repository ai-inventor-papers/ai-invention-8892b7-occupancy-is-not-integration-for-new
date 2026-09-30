#!/usr/bin/env python3
"""Stage 1: load + verify inputs, write compact regenerable tables into work/.

Outputs: work/pool.parquet, work/cp.parquet (active c-papers with filtered tags), work/bg.parquet
(background works with filtered tags and post-stratified yearly weights), work/totals.json.
Held-out concepts are dropped here and never become nodes.
"""
from __future__ import annotations

import gc
import json

import numpy as np
import pandas as pd
from loguru import logger

import config as C


def load_pool() -> pd.DataFrame:
    d = json.loads((C.D1 / "data_out.json").read_text())
    rows = []
    for ds in d["datasets"]:
        for ex in ds["examples"]:
            inp = json.loads(ex["input"])
            out = json.loads(ex["output"])
            stratum = ex.get("metadata_stratum") or ""
            rows.append(dict(
                concept_id=inp["concept_id"], phrase=inp["phrase"], F=inp.get("F"),
                origin_field=inp.get("origin_field"), origin_subfield=inp.get("origin_subfield"),
                origin_group=stratum.split("|")[0] if ex.get("metadata_fold") != "reference" else "REFERENCE",
                fold=ex["metadata_fold"], arm=ex.get("metadata_arm"), F_band=ex.get("metadata_F_band"),
                volume_tercile=ex.get("metadata_volume_tercile"), route=ex.get("metadata_retrieval_route"),
                flags="|".join(ex.get("metadata_flags") or []),
                sense_check_fail="sense_check_fail" in (ex.get("metadata_flags") or []),
                oa_counts=json.dumps(out["oa_counts_by_year"]), n_works=out.get("n_works"),
            ))
    pool = pd.DataFrame(rows)
    return pool


@logger.catch(reraise=True)
def main() -> None:
    C.setup_logging("stage_prep")
    C.set_ram_limit(20)
    pool = load_pool()
    summ = json.loads((C.D1 / "logs" / "assemble_summary.json").read_text())
    counts = pool.fold.value_counts().to_dict()
    logger.info(f"pool folds {counts}")
    assert counts == summ["fold_counts"] == {"screen": 123, "heldout_concept": 61, "reference": 22}, counts
    sealed = set(pool.loc[pool.fold == "heldout_concept", "concept_id"])
    (C.WORK / "sealed_ids.json").write_text(json.dumps(sorted(sealed)))
    active = pool[pool.fold.isin(["screen", "reference"])].copy()
    assert not (set(active.concept_id) & sealed)
    active.to_parquet(C.WORK / "pool.parquet", index=False)
    logger.info(f"active concepts {len(active)} (screen {int((active.fold=='screen').sum())}, reference {int((active.fold=='reference').sum())})")

    # ---- concept levels
    concepts = pd.read_parquet(C.D2 / "data" / "concepts.parquet", columns=["concept_id", "level"])
    concepts["cid"] = concepts.concept_id.str[1:].astype(np.int64)
    level = dict(zip(concepts.cid.values, concepts.level.values))

    # ---- c-papers of active concepts
    links = pd.read_parquet(C.D1 / "concept_work.parquet", columns=["concept_id", "work_id", "year", "match_evidence"])
    links = links[links.concept_id.isin(set(active.concept_id))]
    wids = set(links.work_id.unique())
    parts = []
    for i in range(4):
        w = pd.read_parquet(C.D1 / "works" / f"works_part_0{i}.parquet",
                            columns=["work_id", "publication_year", "type", "subfield_id", "topic_score",
                                     "concept_ids", "concept_scores"])
        n_all = len(w)
        if i == 0:
            n_total = 0
        n_total += n_all
        parts.append(w[w.work_id.isin(wids)])
        del w
        gc.collect()
    works = pd.concat(parts, ignore_index=True)
    logger.info(f"D2 works total {n_total}; linked to active {len(works)}")
    assert n_total == 208374, n_total

    def filt(ids, scores):
        out = [int(a) for a, s in zip(ids, scores) if s >= C.SPEC["tag_min_score"] and level.get(int(a), -1) >= C.SPEC["min_level"]]
        return np.array(sorted(set(out)), dtype=np.int64)

    works["tags"] = [filt(a, b) for a, b in zip(works.concept_ids.values, works.concept_scores.values)]
    sub = works.subfield_id.fillna(-1).astype(int)
    sub[(works.topic_score.fillna(0) < 0.05).values] = -1
    works["subfield"] = sub
    works = works.drop(columns=["concept_ids", "concept_scores"])
    cp = links.merge(works, on="work_id", how="inner")
    cp["year"] = cp.publication_year.astype(int)
    cp["frame"] = cp.type.isin(C.SPEC["frame_types"])
    cp = cp[["concept_id", "work_id", "year", "type", "frame", "subfield", "tags", "match_evidence"]]
    logger.info(f"c-paper rows {len(cp)}; missing work join {len(links) - len(cp)}; frame share {cp.frame.mean():.3f}")
    cp.to_parquet(C.WORK / "cp.parquet", index=False)

    # ---- background
    bg = pd.read_parquet(C.D2 / "data" / "bg_work_sample.parquet",
                         columns=["work_id", "year", "type", "subfield_id", "low_conf_topic", "concept_ids",
                                  "concept_scores", "concept_levels", "block", "stratum", "weight"])
    assert len(bg) == 259716, len(bg)
    bg_ids = set()
    tags = []
    for ids, sc, lv in zip(bg.concept_ids.values, bg.concept_scores.values, bg.concept_levels.values):
        t = sorted({int(a[1:]) for a, s, l in zip(ids, sc, lv) if s >= C.SPEC["tag_min_score"] and l >= C.SPEC["min_level"]})
        tags.append(np.array(t, dtype=np.int64))
        bg_ids.update(int(a[1:]) for a in ids)
    bg["tags"] = tags
    d2_ids = set()
    for ids in cp.tags.values:
        d2_ids.update(ids.tolist())
    all_d2 = set()
    for ids in works.tags.values:
        all_d2.update(ids.tolist())
    overlap = len(all_d2 & bg_ids) / max(1, len(all_d2))
    logger.info(f"tag-id overlap (D2 filtered tags found in bg) = {overlap:.4f}")
    assert overlap > 0.90, overlap
    tot = pd.read_parquet(C.D2 / "data" / "subfield_year_totals.parquet")
    tot = tot[tot.subfield != "unknown"].assign(subfield=lambda d: d.subfield.astype(int))
    bg = bg.merge(tot[["subfield", "year", "n_frame", "n_sampled"]], left_on=["subfield_id", "year"],
                  right_on=["subfield", "year"], how="left")
    bg["w_year"] = np.where(bg.n_sampled.fillna(0) > 0, bg.n_frame / bg.n_sampled.replace(0, np.nan), bg.weight)
    bg["w_year"] = bg.w_year.fillna(bg.weight)
    n_fallback = int((bg.n_sampled.fillna(0) <= 0).sum())
    logger.info(f"bg w_year: fallback to design weight for {n_fallback} works; sum w_year {bg.w_year.sum():.0f}")
    bg = bg.drop(columns=["concept_ids", "concept_scores", "concept_levels", "subfield", "n_frame", "n_sampled"])
    bg.to_parquet(C.WORK / "bg.parquet", index=False)

    # ---- denominators (all_types) per year
    syt = json.loads((C.D1 / "context" / "subfield_year_totals.json").read_text())
    at = syt["variants"]["all_types"]
    totals = {}
    for y, v in at.items():
        subs = {str(k): int(x) for k, x in v["subfield"].items()}
        totals[str(y)] = dict(subfield=subs, all_science=int(sum(subs.values()) + int(v.get("unknown", 0) or 0)))
    (C.WORK / "totals.json").write_text(json.dumps(totals))
    logger.info(f"totals years {sorted(totals)[:3]}..; all-science 2010 = {totals.get('2010', {}).get('all_science')}")
    summary = dict(fold_counts=counts, n_active=len(active), n_cp_rows=len(cp), n_bg=len(bg), tag_overlap=overlap,
                   n_d2_works=n_total, bg_wyear_fallback=n_fallback, n_sealed=len(sealed))
    (C.WORK / "prep_summary.json").write_text(json.dumps(summary, indent=1))
    logger.info(f"prep done {summary}")


if __name__ == "__main__":
    main()
