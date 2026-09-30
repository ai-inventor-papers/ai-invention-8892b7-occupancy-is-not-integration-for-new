"""Step 1: grounded populations after the frozen replacement rule; folds; old/new split.

Frozen replacement rule (test_population.json meta.rules): a concept whose sense_status is 'missing' and whose
dataset_5 record now carries an OpenAlex sense value gets sense_final = that value (status 'openalex_final');
sense_pass is recomputed with the same 0.70 cut. Nothing else changes (p_concept, accept flags, merges, links).
"""
from __future__ import annotations

import hashlib
import json

import pandas as pd
from loguru import logger

import common as K


def fold_sha1(cid: str) -> str:
    return "screen" if int(hashlib.sha1(cid.encode()).hexdigest(), 16) % 10 < 7 else "heldout"


def load_ds5_pool() -> pd.DataFrame:
    """dataset_5 concept pool in the vendored stage_prep.load_pool schema (+ hydration batch, sense value)."""
    d = json.loads((K.DS5 / "hyd" / "data_out.json").read_text())
    rows = []
    for ds in d["datasets"]:
        for ex in ds["examples"]:
            inp = json.loads(ex["input"])
            stratum = ex.get("metadata_stratum") or ""
            flags = ex.get("metadata_flags") or []
            rows.append(dict(
                concept_id=inp["concept_id"], phrase=inp["phrase"], F=inp.get("F"),
                origin_field=(inp.get("origin_field") or {}).get("name"),
                origin_subfield=(inp.get("origin_subfield") or {}).get("name"),
                origin_group=stratum.split("|")[0] if ex.get("metadata_fold") != "reference" else "REFERENCE",
                ds5_fold=ex["metadata_fold"], arm=ex.get("metadata_arm"), F_band=ex.get("metadata_F_band"),
                route=ex.get("metadata_retrieval_route"), hydration_batch=ex.get("metadata_hydration_batch"),
                flags="|".join(flags), sense_check_fail="sense_check_fail" in flags,
                ds5_sense=ex.get("metadata_sense_dominant_share"), stratum=stratum))
    return pd.DataFrame(rows)


def build() -> pd.DataFrame:
    assert K.sha256_file(K.TESTPOP) == K.TESTPOP_SHA, "test_population.json hash changed"
    tp = json.loads(K.TESTPOP.read_text())
    rules = tp["meta"]["rules"]
    cut = tp["meta"]["thresholds"]["sense_cut"]
    ds5 = load_ds5_pool().set_index("concept_id")
    rows, n_replaced = [], 0
    for rec in tp["concepts"]:
        cid = rec["concept_id"]
        r = dict(rec)
        r["sense_status_frozen"] = rec["sense_status"]
        if rec["sense_status"] == "missing" and ds5.loc[cid, "ds5_sense"] is not None and pd.notna(ds5.loc[cid, "ds5_sense"]):
            r["sense_final"] = float(ds5.loc[cid, "ds5_sense"])
            r["sense_status"] = "openalex_final"
            n_replaced += 1
        r["sense_pass"] = bool(r["sense_final"] is not None and r["sense_final"] >= cut)
        r["MAIN"] = bool(r["arm"] == "main" and r["accepted_primary"] and r["sense_pass"] and r["merged_into"] is None)
        r["STRICT"] = bool(r["arm"] == "main" and r["accepted_strict"] and r["sense_pass"] and r["merged_into_strict"] is None)
        r["SENS"] = True
        r["REFERENCE_ACCEPTED"] = bool(rec["in_REFERENCE_ACCEPTED"])
        if rec["sense_status"] != "missing":  # frozen membership must be unchanged for every non-missing concept
            assert r["MAIN"] == rec["in_MAIN"] and r["STRICT"] == rec["in_STRICT"], cid
        rows.append(r)
    pop = pd.DataFrame(rows)
    pop = pop.join(ds5[["F_band", "origin_group", "ds5_fold", "route", "hydration_batch", "flags",
                        "sense_check_fail", "stratum"]].rename(columns={"F_band": "F_band_ds5"}), on="concept_id")
    # folds: sha1 rule vs ds5 metadata_fold (ds5 authoritative)
    main = pop.arm == "main"
    pop["fold_sha1"] = [fold_sha1(c) if m else "reference" for c, m in zip(pop.concept_id, main)]
    pop["fold"] = pop.ds5_fold.map({"screen": "screen", "heldout_concept": "heldout", "reference": "reference"})
    mism = pop[main & (pop.fold_sha1 != pop.fold)]
    for r in mism.itertuples():
        logger.warning(f"fold mismatch {r.concept_id}: sha1 {r.fold_sha1} vs ds5 {r.fold} (ds5 authoritative)")
    # old/new from iteration-1 folds (exp_3 pool) and iteration-1 dataset_1
    p3 = pd.read_parquet(K.EXP3 / "work" / "pool.parquet", columns=["concept_id", "fold"])
    old = set(p3.loc[p3.fold == "screen", "concept_id"])
    ho1 = set(json.loads((K.EXP3 / "work" / "sealed_ids.json").read_text()))
    scr = set(pop.loc[pop.fold == "screen", "concept_id"])
    ho = set(pop.loc[pop.fold == "heldout", "concept_id"])
    viol_old = sorted(old - scr)
    viol_ho = sorted(ho1 - ho)
    if viol_old or viol_ho:  # F8: hard stop on those concepts
        logger.error(f"FOLD INCONSISTENCY old-screen not in screen {viol_old}; iter1 heldout not in heldout {viol_ho}")
    pop["fold_violation"] = pop.concept_id.isin(set(viol_old) | set(viol_ho))
    pop["old_new"] = ["old" if c in old else ("new" if f == "screen" else ("old_heldout" if c in ho1 else
                      ("new_heldout" if f == "heldout" else "reference"))) for c, f in zip(pop.concept_id, pop.fold)]
    pop.attrs["n_replaced"] = n_replaced
    pop.attrs["rules"] = rules
    pop.attrs["fold_mismatch"] = mism.concept_id.tolist()
    pop.attrs["violations"] = dict(old_not_in_screen=viol_old, iter1_heldout_not_in_heldout=viol_ho)
    return pop


def export(pop: pd.DataFrame) -> dict:
    cols = ["concept_id", "phrase", "arm", "fold", "fold_sha1", "old_new", "route", "hydration_batch", "F", "F_band",
            "origin_group", "sense_status_frozen", "sense_status", "sense_final", "sense_pass", "MAIN", "STRICT", "SENS",
            "REFERENCE_ACCEPTED", "sense_check_fail", "fold_violation"]
    per = pop[cols].to_dict("records")
    counts = {}
    for P in ("MAIN", "STRICT", "SENS"):
        sub = pop[pop[P]]
        counts[P] = dict(total=int(len(sub)), by_fold=sub.fold.value_counts().to_dict(),
                         by_old_new=sub.old_new.value_counts().to_dict(),
                         screen_by_route=sub[sub.fold == "screen"].route.value_counts().to_dict(),
                         screen_by_old_new_route=sub[sub.fold == "screen"].groupby(["old_new", "route"]).size()
                         .rename("n").reset_index().to_dict("records"))
    body = dict(rules=pop.attrs["rules"], n_sense_replaced=pop.attrs["n_replaced"], fold_mismatch=pop.attrs["fold_mismatch"],
                fold_violations=pop.attrs["violations"], counts=counts, concepts=per,
                frozen_counts_iter2=dict(MAIN=156, STRICT=147, SENSITIVITY=426))
    blob = json.dumps(K.clean(body), sort_keys=True).encode()
    body["sha256_of_body"] = hashlib.sha256(blob).hexdigest()
    K.write_json(K.RES / "main_population_hydrated.json", body)
    pop[cols].to_parquet(K.WORK / "population.parquet", index=False)
    logger.info(f"population: replaced {pop.attrs['n_replaced']} sense values; MAIN {counts['MAIN']['by_fold']}, "
                f"STRICT {counts['STRICT']['by_fold']}; old/new screen MAIN {counts['MAIN']['by_old_new']}")
    return body


def main() -> pd.DataFrame:
    pop = build()
    export(pop)
    return pop


if __name__ == "__main__":
    K.setup_logging("population")
    main()
