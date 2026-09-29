"""Step 2: compact input tables from dataset_5 (mirrors the vendored stage_prep logic; only the source changes).

work/cp_active.parquet   c-papers of screen (247 main) + reference (60) concepts
sealed/cp_heldout.parquet c-papers of the 119 held-out concepts (raw input; read only by the sealed feature pass and
                          by confirm_heldout.py)
work/totals.json          all-types subfield x year denominators (exactly as vendored stage_prep)
work/pool_active.parquet  pool table (vendored schema) for active concepts; work/pool_heldout.parquet for sealed ones
results/repro/data_change.json  per-(concept, year) count / tag-set identity vs exp_3 work/cp.parquet (145 concepts)
"""
from __future__ import annotations

import gc
import json

import numpy as np
import pandas as pd
from loguru import logger

import common as K
import config as C  # vendored (SPEC: tag_min_score, min_level, frame_types)

WORK_COLS = ["work_id", "publication_year", "type", "subfield_id", "topic_score", "concept_ids", "concept_scores"]


def load_levels() -> dict:
    p = K.DS5 / "deps" / "gen_art_dataset_2" / "concepts.parquet"
    concepts = pd.read_parquet(p, columns=["concept_id", "level"])
    concepts["cid"] = concepts.concept_id.str[1:].astype(np.int64)
    return dict(zip(concepts.cid.values, concepts.level.values))


def build_cp(concept_ids: set, level: dict) -> pd.DataFrame:
    links = pd.read_parquet(K.DS5 / "hyd" / "concept_work.parquet", columns=["concept_id", "work_id", "year", "match_evidence"])
    links = links[links.concept_id.isin(concept_ids)]
    wids = set(links.work_id.unique())
    parts, n_total = [], 0
    for f in sorted((K.DS5 / "hyd" / "works").glob("works_part_*.parquet")):
        w = pd.read_parquet(f, columns=WORK_COLS)
        n_total += len(w)
        parts.append(w[w.work_id.isin(wids)])
        del w
        gc.collect()
    works = pd.concat(parts, ignore_index=True)
    assert n_total == 462812, n_total
    assert works.work_id.is_unique

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
    logger.info(f"c-paper rows {len(cp)} for {cp.concept_id.nunique()} concepts; missing work join {len(links) - len(cp)}; "
                f"frame share {cp.frame.mean():.3f}")
    return cp


def totals() -> dict:
    syt = json.loads((K.DS5 / "hyd" / "context" / "subfield_year_totals.json").read_text())
    at = syt["variants"]["all_types"]
    out = {}
    for y, v in at.items():
        subs = {str(k): int(x) for k, x in v["subfield"].items()}
        out[str(y)] = dict(subfield=subs, all_science=int(sum(subs.values()) + int(v.get("unknown", 0) or 0)))
    return out


def pool_table(pop: pd.DataFrame, ids: set) -> pd.DataFrame:
    p = pop[pop.concept_id.isin(ids)].copy()
    p["F"] = p.F.astype(float)
    return p[["concept_id", "phrase", "F", "F_band", "origin_group", "fold", "arm", "route", "hydration_batch",
              "sense_check_fail", "old_new", "MAIN", "STRICT", "SENS"]].sort_values("concept_id").reset_index(drop=True)


def data_change(cp_new: pd.DataFrame) -> dict:
    old = pd.read_parquet(K.EXP3 / "work" / "cp.parquet", columns=["concept_id", "work_id", "year", "tags"])
    ids = set(old.concept_id)
    new = cp_new[cp_new.concept_id.isin(ids)]
    a = old.groupby(["concept_id", "year"]).size().rename("n_old")
    b = new.groupby(["concept_id", "year"]).size().rename("n_new")
    j = pd.concat([a, b], axis=1).fillna(0)
    ident = float((j.n_old == j.n_new).mean())
    # tag sets per (concept, work)
    mo = old.assign(t=old.tags.map(lambda x: tuple(x))).set_index(["concept_id", "work_id"]).t
    mn = new.assign(t=new.tags.map(lambda x: tuple(x))).set_index(["concept_id", "work_id"]).t
    common_idx = mo.index.intersection(mn.index)
    tag_ident = float((mo.loc[common_idx] == mn.loc[common_idx]).mean()) if len(common_idx) else float("nan")
    wo, wn = set(mo.index), set(mn.index)
    out = dict(n_concepts=len(ids), n_concept_years=int(len(j)), identical_count_share=ident,
               max_abs_count_diff=float((j.n_old - j.n_new).abs().max()),
               n_links_old=len(wo), n_links_new=len(wn), links_only_old=len(wo - wn), links_only_new=len(wn - wo),
               tag_set_identical_share_common_links=tag_ident,
               worst=j.assign(d=(j.n_old - j.n_new).abs()).sort_values("d", ascending=False).head(10).reset_index()
               .to_dict("records"))
    K.write_json(K.RES / "repro" / "data_change.json", out)
    logger.info(f"data change vs exp_3 cp: identical count share {ident:.4f}, max |diff| {out['max_abs_count_diff']}, "
                f"tag-set identical {tag_ident:.4f}")
    return out


def main() -> dict:
    pop = pd.read_parquet(K.WORK / "population.parquet")
    active = set(pop.loc[pop.fold.isin(["screen", "reference"]), "concept_id"])
    held = set(pop.loc[pop.fold == "heldout", "concept_id"])
    assert not active & held
    level = load_levels()
    cp = build_cp(active | held, level)
    cp_act = cp[cp.concept_id.isin(active)].reset_index(drop=True)
    cp_ho = cp[cp.concept_id.isin(held)].reset_index(drop=True)
    cp_act.to_parquet(K.WORK / "cp_active.parquet", index=False)
    cp_ho.to_parquet(K.SEALED / "cp_heldout.parquet", index=False)
    del cp
    gc.collect()
    (K.WORK / "totals.json").write_text(json.dumps(totals()))
    pool_table(pop, active).to_parquet(K.WORK / "pool_active.parquet", index=False)
    pool_table(pop, held).to_parquet(K.WORK / "pool_heldout.parquet", index=False)
    dc = data_change(cp_act)
    summ = dict(n_active=len(active), n_heldout=len(held), cp_active_rows=len(cp_act), cp_heldout_rows=len(cp_ho),
                data_change=dict((k, v) for k, v in dc.items() if k != "worst"))
    K.write_json(K.WORK / "prep3_summary.json", summ)
    logger.info(f"prep3 done: {summ}")
    return summ


if __name__ == "__main__":
    K.setup_logging("prep3")
    main()
