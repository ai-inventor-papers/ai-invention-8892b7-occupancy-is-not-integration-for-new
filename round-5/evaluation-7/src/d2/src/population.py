"""STAGE 2: apply the frozen replacement rule of test_population.json to the fully hydrated pool; folds; sealing."""
from __future__ import annotations

import json
from collections import Counter

import pandas as pd
from loguru import logger

from config import E1, RESULTS, SEALED_IDS, fold_of, rel, sha256_file

SENSE_CUT = 0.70


def build(G: dict) -> dict:
    pop_path = E1 / "results" / "test_population.json"
    pop = json.loads(pop_path.read_text())
    d5 = G["concepts"].set_index("concept_id")
    rows, replaced, changed_final = [], 0, 0
    for c in pop["concepts"]:
        cid = c["concept_id"]
        sense = c.get("sense_final")
        status = c.get("sense_status")
        v5 = d5.at[cid, "sense_share_d5"] if cid in d5.index else None
        v5 = None if v5 is None or pd.isna(v5) else float(v5)
        if status != "openalex_final" and v5 is not None:
            # frozen_replacement_rule: the OpenAlex sense value replaces the proxy; nothing else changes
            sense, status = v5, "openalex_final"
            replaced += 1
        elif status == "openalex_final" and v5 is not None and abs(v5 - (sense or 0)) > 1e-9:
            changed_final += 1
        sense_pass = sense is not None and sense >= SENSE_CUT
        main = c["arm"] == "main"
        rows.append({
            "concept_id": cid, "arm": c["arm"], "sense_final": sense, "sense_status": status,
            "sense_pass": bool(sense_pass),
            "MAIN": bool(main and c["accepted_primary"] and sense_pass and c.get("merged_into") is None),
            "STRICT": bool(main and c["accepted_strict"] and sense_pass and c.get("merged_into_strict") is None),
            "REFERENCE_ACCEPTED": bool(c["arm"] == "reference" and c["accepted_primary"] and c.get("merged_into") is None),
            "SENSITIVITY": bool(main),
            "fold": fold_of(cid) if main else "reference",
            "fold_d5": d5.at[cid, "fold_d5"] if cid in d5.index else None,
            "route": d5.at[cid, "route"] if cid in d5.index else None})
    df = pd.DataFrame(rows)
    mm = df[df.arm == "main"]
    agree = int((mm.fold == mm.fold_d5.str.replace("heldout_concept", "heldout")).sum())
    if agree != len(mm):
        raise RuntimeError(f"fold rule disagrees with dataset_5 metadata_fold on {len(mm) - agree} concepts")
    lists = {k: sorted(df.loc[df[k], "concept_id"]) for k in ["MAIN", "STRICT", "SENSITIVITY", "REFERENCE_ACCEPTED"]}
    sealed = sorted(df.loc[(df.arm == "main") & (df.fold == "heldout"), "concept_id"])
    counts = {k: {"total": len(v), "by_fold": dict(Counter(df.set_index("concept_id").loc[v, "fold"])),
                  "by_route": dict(Counter(df.set_index("concept_id").loc[v, "route"]))} for k, v in lists.items()}
    out = {"source": rel(pop_path), "source_sha256": sha256_file(pop_path),
           "rule_applied": pop["meta"]["rules"]["frozen_replacement_rule"],
           "n_sense_replaced_by_dataset5": replaced, "n_final_sense_differing_from_dataset5_kept": changed_final,
           "fold_rule": "screen iff int(sha1(concept_id), 16) % 10 < 7 (main arm); agreement with dataset_5 = "
                        f"{agree}/{len(mm)}",
           "counts": counts, "lists": lists, "sealed_ids": sealed,
           "per_concept": df.drop(columns=["fold_d5"]).to_dict(orient="records")}
    p = RESULTS / "main_population_hydrated.json"
    p.write_text(json.dumps(out, indent=1, default=str))
    (RESULTS / "main_population_hydrated.sha256").write_text(f"{sha256_file(p)}  main_population_hydrated.json\n")
    SEALED_IDS.clear()
    SEALED_IDS.update(sealed)
    logger.info(f"population: { {k: v['total'] for k, v in counts.items()} }; MAIN by fold "
                f"{counts['MAIN']['by_fold']}; sealed ids {len(sealed)}; sense replaced {replaced}")
    return out
