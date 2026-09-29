#!/usr/bin/env python3
"""STAGE 0: population, folds and compact inputs.

Outputs: results/fold_check.json, results/main_population_hydrated.json, work/sealed_ids.json, work/pool_active.parquet,
work/cp_hyd.parquet (active c-papers: tags filtered exactly as iteration 2, subfield, frame flag, author ids),
work/totals.json. Held-out concepts are dropped here and never become nodes or rows.
"""
from __future__ import annotations

import gc
import hashlib
import json

import numpy as np
import pandas as pd
from loguru import logger

from common import HELDOUT, MINI, SIMULATE, C, D2, DS5, RES, WORK, X1, X3, sha256_json, write_json

HYD = DS5 / "hyd"


def fold_sha(cid: str) -> str:
    return "screen" if int(hashlib.sha1(cid.encode()).hexdigest(), 16) % 10 < 7 else "heldout"


def load_pool() -> pd.DataFrame:
    d = json.loads((HYD / "data_out.json").read_text())
    rows = []
    for ds in d["datasets"]:
        for ex in ds["examples"]:
            inp = json.loads(ex["input"])
            flags = ex.get("metadata_flags") or []
            stratum = ex.get("metadata_stratum") or ""
            of, osf = inp.get("origin_field") or {}, inp.get("origin_subfield") or {}
            rows.append(dict(
                concept_id=inp["concept_id"], phrase=inp["phrase"], F=inp.get("F"),
                origin_field=of.get("name"), origin_field_id=of.get("id"),
                origin_subfield=osf.get("name"), origin_subfield_id=osf.get("id"),
                origin_group=stratum.split("|")[0] if ex.get("metadata_fold") != "reference" else "REFERENCE",
                fold=ex["metadata_fold"], arm=ex.get("metadata_arm"), F_band=ex.get("metadata_F_band"),
                volume_tercile=ex.get("metadata_volume_tercile"), route=ex.get("metadata_retrieval_route"),
                flags="|".join(flags), sense_check_fail="sense_check_fail" in flags,
                hydration_batch=ex.get("metadata_hydration_batch"),
                sense_ds5=ex.get("metadata_sense_dominant_share")))
    return pd.DataFrame(rows)


def population(pool: pd.DataFrame) -> dict:
    """Frozen iteration-2 population rules with the frozen replacement rule for 'missing' sense values."""
    tp = json.loads((X1 / "results" / "test_population.json").read_text())
    rules = tp["meta"]["rules"]
    ds5 = pool.set_index("concept_id")
    cut = tp["meta"]["thresholds"]["sense_cut"]
    per, n_replaced = {}, 0
    for c in tp["concepts"]:
        cid = c["concept_id"]
        st, sf = c["sense_status"], c["sense_final"]
        if st == "missing" and cid in ds5.index and ds5.loc[cid, "sense_ds5"] is not None and \
                np.isfinite(float(ds5.loc[cid, "sense_ds5"])):
            sf, st = float(ds5.loc[cid, "sense_ds5"]), "openalex_final"
            n_replaced += 1
        sp = bool(sf is not None and sf >= cut)
        main = c["arm"] == "main" and bool(c["accepted_primary"]) and sp and c["merged_into"] is None
        strict = c["arm"] == "main" and bool(c["accepted_strict"]) and sp and c["merged_into_strict"] is None
        per[cid] = dict(arm=c["arm"], fold=c["fold"], sense_status=st, sense_final=sf, sense_pass=sp,
                        accepted_primary=bool(c["accepted_primary"]), accepted_strict=bool(c["accepted_strict"]),
                        merged_into=c["merged_into"], MAIN=main, STRICT=strict, SENSITIVITY=True,
                        was_in_MAIN_iter2=bool(c["in_MAIN"]))
    return dict(rules=rules, sense_cut=cut, n_sense_replaced=n_replaced, concepts=per)


@logger.catch(reraise=True)
def main(mini: bool = MINI) -> None:
    C.set_ram_limit(22)
    pool = load_pool()
    counts = pool.groupby(["fold", "arm"]).size().to_dict()
    logger.info(f"pool folds {counts}")
    assert int((pool.fold == "screen").sum()) == 247 and int((pool.fold == "heldout_concept").sum()) == 119 \
        and int((pool.fold == "reference").sum()) == 60, counts
    # ---- fold rule check (metadata_fold is authoritative)
    main_arm = pool[pool.arm == "main"]
    fs = main_arm.concept_id.map(fold_sha)
    meta = main_arm.fold.map({"screen": "screen", "heldout_concept": "heldout"})
    mism = main_arm.loc[fs.values != meta.values, "concept_id"].tolist()
    write_json(RES / "fold_check.json", dict(rule="screen if int(sha1(concept_id),16) % 10 < 7 else heldout",
                                            n_main=len(main_arm), n_agree=int((fs.values == meta.values).sum()),
                                            n_mismatch=len(mism), mismatch_ids=mism,
                                            authoritative="metadata_fold (sealed by iteration 2)"))
    logger.info(f"fold rule agreement {len(main_arm) - len(mism)}/{len(main_arm)}")
    # ---- population
    pop = population(pool)
    per = pop["concepts"]
    pool["MAIN"] = pool.concept_id.map(lambda c: per.get(c, {}).get("MAIN", False))
    pool["STRICT"] = pool.concept_id.map(lambda c: per.get(c, {}).get("STRICT", False))
    pool["sense_final"] = pool.concept_id.map(lambda c: per.get(c, {}).get("sense_final"))
    old = set(pd.read_parquet(X3 / "work" / "pool.parquet", columns=["concept_id"]).concept_id)
    pool["iter2_active"] = pool.concept_id.isin(old)
    cnt = {}
    for rule in ("MAIN", "STRICT"):
        for (f, r), n in pool[pool[rule]].groupby(["fold", "route"]).size().items():
            cnt[f"{rule}|{f}|{r}"] = int(n)
        cnt[f"{rule}|total"] = int(pool[rule].sum())
        cnt[f"{rule}|screen"] = int((pool[rule] & (pool.fold == "screen")).sum())
        cnt[f"{rule}|heldout"] = int((pool[rule] & (pool.fold == "heldout_concept")).sum())
    cnt["SENSITIVITY|total"] = len(pool)
    cnt["main_arm_screen_unfiltered"] = int(((pool.fold == "screen") & (pool.arm == "main")).sum())
    body = dict(rules=pop["rules"], sense_cut=pop["sense_cut"], n_sense_replaced_by_openalex_value=pop["n_sense_replaced"],
                counts=cnt, note=("The direction's '247' = main-arm screen fold, unfiltered (sensitivity population). "
                                  "PRIMARY = MAIN rule restricted to the screen fold."), concepts=per)
    body["sha256_of_content"] = sha256_json({k: v for k, v in body.items()})
    write_json(RES / "main_population_hydrated.json", body)
    logger.info(f"population counts {cnt}")
    # ---- seal
    sealed = sorted(pool.loc[pool.fold == "heldout_concept", "concept_id"])
    (WORK / "sealed_ids.json").write_text(json.dumps(sealed))
    if SIMULATE:
        # code-path rehearsal: a deterministic 40-concept subset of screen MAIN plays the held-out role; real held-out
        # concepts stay sealed and are never read
        pool["fold_orig"] = pool.fold
        sim = sorted(pool.loc[(pool.fold == "screen") & pool.MAIN, "concept_id"], key=lambda c: hashlib.sha1(c.encode()).hexdigest())[:40]
        pool.loc[pool.fold == "screen", "fold"] = "screen_frozen"
        pool.loc[pool.concept_id.isin(sim), "fold"] = "screen"
        pool["iter2_active"] = False
    elif HELDOUT:
        # held-out concepts become the analysed fold ('screen' label kept for code reuse; original fold in fold_orig)
        pool["fold_orig"] = pool.fold
        pool.loc[pool.fold == "screen", "fold"] = "screen_frozen"
        pool.loc[pool.fold_orig == "heldout_concept", "fold"] = "screen"
        pool["iter2_active"] = False
    if not HELDOUT or SIMULATE:
        C.SEALED_IDS.update(sealed)
    active = pool[pool.fold.isin(["screen", "reference"])].copy()
    if mini:
        o = active[(active.fold == "screen") & active.iter2_active].head(10)
        n = active[(active.fold == "screen") & ~active.iter2_active].head(10)
        r = active[active.fold == "reference"].head(5)
        active = pd.concat([o, n, r])
    C.assert_not_sealed(active.concept_id)
    active.to_parquet(WORK / "pool_active.parquet", index=False)
    logger.info(f"active concepts {len(active)}")
    # ---- c-papers
    concepts = pd.read_parquet(D2 / "data" / "concepts.parquet", columns=["concept_id", "level"])
    level = dict(zip(concepts.concept_id.str[1:].astype(np.int64).values, concepts.level.values))
    links = pd.read_parquet(HYD / "concept_work.parquet", columns=["concept_id", "work_id", "year", "match_evidence"])
    links = links[links.concept_id.isin(set(active.concept_id))]
    wids = set(links.work_id.unique())
    parts, n_total = [], 0
    for i in range(8):
        w = pd.read_parquet(HYD / "works" / f"works_part_0{i}.parquet",
                            columns=["work_id", "publication_year", "type", "subfield_id", "topic_score", "concept_ids",
                                     "concept_scores", "author_ids"])
        n_total += len(w)
        parts.append(w[w.work_id.isin(wids)])
        del w
        gc.collect()
    works = pd.concat(parts, ignore_index=True).drop_duplicates("work_id")
    logger.info(f"DS5 works total {n_total}; linked to active {len(works)}")
    tmin, lmin = C.SPEC["tag_min_score"], C.SPEC["min_level"]

    def filt(ids, scores):
        out = [int(a) for a, s in zip(ids, scores) if s >= tmin and level.get(int(a), -1) >= lmin]
        return np.array(sorted(set(out)), dtype=np.int64)

    works["tags"] = [filt(a, b) for a, b in zip(works.concept_ids.values, works.concept_scores.values)]
    sub = works.subfield_id.fillna(-1).astype(int)
    sub[(works.topic_score.fillna(0) < 0.05).values] = -1
    works["subfield"] = sub
    works["authors"] = [np.asarray(a if a is not None else [], dtype=np.int64) for a in works.author_ids.values]
    works = works.drop(columns=["concept_ids", "concept_scores", "author_ids"])
    cp = links.merge(works, on="work_id", how="inner")
    cp["year"] = cp.publication_year.astype(int)
    cp["frame"] = cp.type.isin(C.SPEC["frame_types"])
    cp = cp[["concept_id", "work_id", "year", "type", "frame", "subfield", "tags", "authors", "match_evidence"]]
    cp = cp[(cp.year >= 2000) & (cp.year <= 2024)]
    logger.info(f"c-paper rows {len(cp)}; missing work join {len(links) - len(cp)}; frame share {cp.frame.mean():.3f}")
    cp.to_parquet(WORK / "cp_hyd.parquet", index=False)
    # ---- denominators exactly as iteration 2
    syt = json.loads((HYD / "context" / "subfield_year_totals.json").read_text())
    totals = {}
    for y, v in syt["variants"]["all_types"].items():
        subs = {str(k): int(x) for k, x in v["subfield"].items()}
        totals[str(y)] = dict(subfield=subs, all_science=int(sum(subs.values()) + int(v.get("unknown", 0) or 0)))
    (WORK / "totals.json").write_text(json.dumps(totals))
    x3t = json.loads((X3 / "work" / "totals.json").read_text())
    write_json(WORK / "prep_summary.json", dict(n_active=len(active), n_cp_rows=len(cp), n_ds5_works=n_total,
                                               totals_equal_iter2=bool(x3t == totals), n_sealed=len(sealed), mini=mini))
    logger.info(f"prep done; totals identical to iteration 2: {x3t == totals}")


if __name__ == "__main__":
    from common import setup_logging
    setup_logging("prep")
    main()
