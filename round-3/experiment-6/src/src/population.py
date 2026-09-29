"""Step 1: frozen population after the frozen replacement rule, fold checks, sealed ids."""
from __future__ import annotations

import hashlib
import json
from collections import Counter

import pandas as pd
from loguru import logger

from common import C, EXP3_POOL, HYD, OUT, TP, WORK, sha256_file, write_json

POP = OUT / "population"


def parse_pool() -> pd.DataFrame:
    d = json.loads((HYD / "data_out.json").read_text())
    rows = []
    for ds in d["datasets"]:
        for ex in ds["examples"]:
            inp = json.loads(ex["input"])
            stratum = ex.get("metadata_stratum") or ""
            of, osf = inp.get("origin_field") or {}, inp.get("origin_subfield") or {}
            rows.append(dict(
                concept_id=inp["concept_id"], phrase=inp["phrase"], F=inp.get("F"),
                origin_field=of.get("name"), origin_field_id=of.get("id"),
                origin_subfield=osf.get("name"), origin_subfield_id=osf.get("id"),
                origin_group=stratum.split("|")[0] if ex["metadata_fold"] != "reference" else "REFERENCE",
                fold=ex["metadata_fold"], arm=ex.get("metadata_arm"), F_band=ex.get("metadata_F_band"),
                route=ex.get("metadata_retrieval_route"), hydration_batch=ex.get("metadata_hydration_batch"),
                sense_dominant_share=ex.get("metadata_sense_dominant_share"),
                flags="|".join(ex.get("metadata_flags") or []),
                sense_check_fail="sense_check_fail" in (ex.get("metadata_flags") or []),
                volume_tercile=ex.get("metadata_volume_tercile"), n_works=json.loads(ex["output"]).get("n_works"),
            ))
    return pd.DataFrame(rows)


def run() -> pd.DataFrame:
    POP.mkdir(parents=True, exist_ok=True)
    pool = parse_pool()
    counts = pool.fold.value_counts().to_dict()
    logger.info(f"pool {len(pool)} folds {counts}")
    assert counts == {"screen": 247, "heldout_concept": 119, "reference": 60}, counts
    # fold hash rule (main arm): sha1(concept_id) % 10 < 7  <=> screen
    main = pool[pool.arm == "main"]
    h = main.concept_id.map(lambda c: int(hashlib.sha1(c.encode()).hexdigest(), 16) % 10 < 7)
    n_mis = int((h != (main.fold == "screen")).sum())
    logger.info(f"fold-hash mismatches (sha1(concept_id)%10<7 vs metadata_fold): {n_mis}")
    old = pd.read_parquet(EXP3_POOL, columns=["concept_id", "fold"])
    old_screen = set(old.loc[old.fold == "screen", "concept_id"])
    new_screen = set(pool.loc[pool.fold == "screen", "concept_id"])
    assert old_screen <= new_screen, "iteration-1 screen concepts must stay in the screen fold"

    # frozen population file
    tp_sha = sha256_file(TP)
    assert tp_sha.startswith("6a887fb4") and tp_sha.endswith("5505"), tp_sha
    tp = json.loads(TP.read_text())
    tpc = {r["concept_id"]: r for r in tp["concepts"]}
    assert set(tpc) == set(pool.concept_id)
    rows, n_replaced = [], 0
    for r in pool.itertuples(index=False):
        t = tpc[r.concept_id]
        sense_final, status = t.get("sense_final"), t.get("sense_status")
        if status == "missing" and r.sense_dominant_share is not None and r.sense_dominant_share == r.sense_dominant_share:
            sense_final, status = float(r.sense_dominant_share), "openalex_final"
            n_replaced += 1
        sense_pass = bool(sense_final is not None and sense_final >= 0.70)
        in_main = bool(t["arm"] == "main" and t["accepted_primary"] and sense_pass and t["merged_into"] is None)
        in_strict = bool(t["arm"] == "main" and t["accepted_strict"] and sense_pass and t["merged_into_strict"] is None)
        rows.append(dict(concept_id=r.concept_id, arm=t["arm"], accepted_primary=bool(t["accepted_primary"]),
                         accepted_strict=bool(t["accepted_strict"]), merged_into=t["merged_into"],
                         merged_into_strict=t["merged_into_strict"], sense_status=status, sense_final=sense_final,
                         sense_pass=sense_pass, in_MAIN=in_main, in_STRICT=in_strict,
                         in_SENSITIVITY=bool(t["arm"] == "main"),
                         tp_in_MAIN=bool(t.get("in_MAIN")), tp_in_STRICT=bool(t.get("in_STRICT"))))
    fl = pd.DataFrame(rows)
    pool = pool.merge(fl, on="concept_id", how="left", suffixes=("", "_tp"))
    assert (pool.arm == pool.arm_tp).all()
    pool = pool.drop(columns=["arm_tp"])
    n_diff_main = int((pool.in_MAIN != pool.tp_in_MAIN).sum())
    n_diff_strict = int((pool.in_STRICT != pool.tp_in_STRICT).sum())
    logger.info(f"replacement rule applied to {n_replaced}; MAIN {int(pool.in_MAIN.sum())} (frozen file {int(pool.tp_in_MAIN.sum())}, "
                f"diff {n_diff_main}); STRICT {int(pool.in_STRICT.sum())} (diff {n_diff_strict})")

    cnt = {}
    for pop in ("in_MAIN", "in_STRICT", "in_SENSITIVITY"):
        s = pool[pool[pop]]
        cnt[pop] = dict(total=len(s), by_fold=dict(Counter(s.fold)), by_fold_route=dict(Counter(s.fold + "|" + s.route)),
                        by_fold_batch=dict(Counter(s.fold + "|" + s.hydration_batch)))
    sealed = sorted(pool.loc[pool.fold == "heldout_concept", "concept_id"])
    body = dict(rules_text_verbatim=tp["meta"]["rules"], frozen_population_sha256=tp_sha,
                replacement_rule_applied_to=n_replaced, fold_hash_rule="int(sha1(concept_id).hexdigest(),16) % 10 < 7 <=> screen (main arm)",
                fold_hash_mismatches=n_mis, iter1_screen_subset_of_screen=True, n_iter1_screen=len(old_screen),
                counts=cnt, differences_vs_frozen_flags=dict(MAIN=n_diff_main, STRICT=n_diff_strict),
                concepts=pool.drop(columns=["tp_in_MAIN", "tp_in_STRICT"]).to_dict("records"))
    txt = json.dumps(body, indent=1, default=str)
    (POP / "main_population_hydrated.json").write_text(txt)
    write_json(POP / "main_population_hydrated.sha256.json",
               dict(sha256=hashlib.sha256(txt.encode()).hexdigest(), file="main_population_hydrated.json"))
    write_json(POP / "sealed_ids.json", sealed)
    C.SEALED_IDS.update(sealed)
    pool["iter1_screen"] = pool.concept_id.isin(old_screen)
    pool.to_parquet(WORK / "pool.parquet", index=False)
    logger.info(f"population counts {json.dumps({k: v['by_fold'] for k, v in cnt.items()})}")
    return pool
