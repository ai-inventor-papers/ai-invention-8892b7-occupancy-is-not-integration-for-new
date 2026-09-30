"""Step 2: c-papers of all 426 concepts from the hydrated corpus (vendored stage_prep logic adapted to DS5).

Outputs: work/cp.parquet (concept_id, work_id, year, type, frame, subfield, tags, refs, n_auth, match_evidence),
work/authors.parquet (work_id, year, author_ids for ALL corpus works), work/totals.json.
"""
from __future__ import annotations

import gc
import json

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from loguru import logger

from common import C, HYD, SPEC, WORK, write_json

N_WORKS, N_LINKS = 462812, 488078
COLS = ["work_id", "publication_year", "type", "subfield_id", "topic_score", "concept_ids", "concept_scores",
        "refs_in_corpus", "author_ids"]


def run() -> None:
    pool = pd.read_parquet(WORK / "pool.parquet", columns=["concept_id", "fold"])
    concepts = pd.read_parquet(C.D2 / "concepts.parquet", columns=["concept_id", "level"])
    concepts["cid"] = concepts.concept_id.str[1:].astype(np.int64)
    level = dict(zip(concepts.cid.values, concepts.level.values))
    links = pd.read_parquet(HYD / "concept_work.parquet", columns=["concept_id", "work_id", "year", "match_evidence"])
    logger.info(f"links {len(links)}")
    assert len(links) == N_LINKS, len(links)
    assert set(links.concept_id) <= set(pool.concept_id)
    parts = sorted((HYD / "works").glob("works_part_*.parquet"))
    schema = pq.read_schema(parts[0])
    missing = [c for c in COLS if c not in schema.names]
    assert not missing, f"schema mismatch: {missing}"
    frames, n_total = [], 0
    for p in parts:
        w = pd.read_parquet(p, columns=COLS)
        n_total += len(w)
        frames.append(w)
    works = pd.concat(frames, ignore_index=True)
    del frames
    gc.collect()
    logger.info(f"works {n_total} from {len(parts)} parts")
    assert n_total == N_WORKS, n_total
    assert works.work_id.is_unique

    def filt(ids, scores):
        out = [int(a) for a, s in zip(ids, scores) if s >= SPEC["tag_min_score"] and level.get(int(a), -1) >= SPEC["min_level"]]
        return np.array(sorted(set(out)), dtype=np.int64)

    works["tags"] = [filt(a, b) for a, b in zip(works.concept_ids.values, works.concept_scores.values)]
    sub = works.subfield_id.fillna(-1).astype(int)
    sub[(works.topic_score.fillna(0) < 0.05).values] = -1
    works["subfield"] = sub
    works["year"] = works.publication_year.astype(int)
    works["n_auth"] = works.author_ids.map(lambda a: 0 if a is None else len(a))
    # author index for all works (newcomer co-author sets)
    works[["work_id", "year", "author_ids"]].to_parquet(WORK / "authors.parquet", index=False)
    works = works.drop(columns=["concept_ids", "concept_scores", "author_ids", "publication_year"])
    cp = links.drop(columns=["year"]).merge(works, on="work_id", how="inner")
    cp["frame"] = cp.type.isin(SPEC["frame_types"])
    cp = cp.rename(columns={"refs_in_corpus": "refs"})
    cp = cp[["concept_id", "work_id", "year", "type", "frame", "subfield", "tags", "refs", "n_auth", "match_evidence"]]
    logger.info(f"c-paper rows {len(cp)} (missing work join {len(links) - len(cp)}); frame share {cp.frame.mean():.3f}; "
                f"unknown-subfield share {(cp.subfield < 0).mean():.3f}; no-author share {(cp.n_auth == 0).mean():.3f}")
    cp.to_parquet(WORK / "cp.parquet", index=False)

    syt = json.loads((HYD / "context" / "subfield_year_totals.json").read_text())
    at = syt["variants"]["all_types"]
    totals = {}
    for y, v in at.items():
        subs = {str(k): int(x) for k, x in v["subfield"].items()}
        totals[str(y)] = dict(subfield=subs, all_science=int(sum(subs.values()) + int(v.get("unknown", 0) or 0)))
    (WORK / "totals.json").write_text(json.dumps(totals))
    write_json(WORK / "prep_summary.json", dict(n_works=n_total, n_links=len(links), n_cp=len(cp),
                                                n_concepts_with_papers=int(cp.concept_id.nunique()),
                                                frame_share=float(cp.frame.mean()),
                                                unknown_subfield_share=float((cp.subfield < 0).mean()),
                                                no_author_share=float((cp.n_auth == 0).mean())))
    logger.info(f"totals years {min(totals)}..{max(totals)}")
