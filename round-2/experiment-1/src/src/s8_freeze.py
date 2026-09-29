#!/usr/bin/env python3
"""STEP 8: freeze and hash the accepted test population for iteration 3 (H1/H2 and the RQ1 re-cut).
results/test_population.json is serialised with sorted keys and compact separators (deterministic for fixed inputs and
code commit); its sha256 goes to results/test_population.sha256. The wall-clock creation time lives in a sidecar
(results/test_population.created.json) so that re-running on identical inputs reproduces the hash."""
from __future__ import annotations

import hashlib
import json
import subprocess
import time
from collections import Counter

from loguru import logger

from common import DATA, FRAME_SHA, MODELS, RESULTS, ROOT, f_band, load_frame, load_hydrated, read_json, setup_logging, sha256_file, write_json

SENSE_CUT = 0.70
RULES = {
    "MAIN": "arm == main AND accepted_primary (p_concept >= t_F1) AND sense_pass (sense_final >= 0.70) AND merged_into is null (canonical at p_merge)",
    "STRICT": "arm == main AND accepted_strict (p_concept >= t_P90) AND sense_pass AND merged_into_strict is null (canonical at p_merge_strict)",
    "REFERENCE_ACCEPTED": "arm == reference AND accepted_primary AND merged_into is null (rho0 benchmark; the full reference arm is a sensitivity set)",
    "SENSITIVITY": "the full frame (all 426 concepts), no filters",
    "sense_final": "OpenAlex-based DS1 sense check value if present (sense_status openalex_final); else the arXiv year-F title proxy (arxiv_proxy_provisional); else null (missing). null -> sense_pass False for MAIN/STRICT",
    "frozen_replacement_rule": ("When a pending concept is hydrated and DS1 assemble.py writes its OpenAlex sense value, that value replaces "
                                "the proxy (sense_status -> openalex_final) and sense_pass is recomputed with the same 0.70 cut. Nothing else may change: "
                                "p_concept, thresholds, accept flags, merge clusters and links stay exactly as frozen here."),
}


def git_commit() -> str | None:
    try:
        return subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


@logger.catch(reraise=True)
def main() -> None:
    setup_logging("s8_freeze")
    frame = load_frame()
    hyd = load_hydrated()
    pre = json.loads((RESULTS / "frame_predictions_prelabel.json").read_text())
    preds = {r["concept_id"]: r for r in pre["predictions"]}
    diag = pre["diagnostics"]
    ml = read_json(RESULTS / "frame_merge_link.json")
    audit = read_json(RESULTS / "frame_llm_audit.json")
    sense_oa = {json.loads(l)["concept_id"]: json.loads(l)["dominant_share"] for l in (DATA / "sense_check.jsonl").read_text().splitlines()}
    proxy = audit.get("sense_proxy", {})
    f9 = bool(audit.get("sense_validation", {}).get("F9_triggered", False))
    thr = read_json(MODELS / "thresholds.json")
    mthr = read_json(MODELS / "merger_thresholds.json")
    lthr = read_json(MODELS / "link_thresholds.json")
    concepts = []
    for cid in sorted(frame):
        c = frame[cid]
        p = preds[cid]
        m = ml["concepts"][cid]
        h = hyd.get(cid)
        flags = (h or {}).get("meta", {}).get("metadata_flags", []) if h else []
        if sense_oa.get(cid) is not None:
            sf, st = float(sense_oa[cid]), "openalex_final"
        elif cid in proxy and not f9:
            sf, st = float(proxy[cid]), "arxiv_proxy_provisional"
        else:
            sf, st = None, "missing"
        sp = bool(sf is not None and sf >= SENSE_CUT)
        rec = {"concept_id": cid, "node_id": cid, "phrase": c["phrase"], "arm": c["arm"], "fold": c.get("metadata_fold"),
               "hydrated": h is not None, "F": c.get("F"), "F_band": f_band(int(c["F"])) if c.get("F") else None, "V": c.get("V"),
               "origin_field": (h["input"].get("origin_field") or {}).get("name") if h else None,
               "origin_subfield": (h["input"].get("origin_subfield") or {}).get("name") if h else None,
               "p_concept": p["p_concept"], "accepted_primary": p["accepted_primary"], "accepted_strict": p["accepted_strict"],
               "accepted_primary_notermhood": p["accepted_primary_notermhood"],
               "accepted_primary_uncensored_termhood": p["accepted_primary_uncensored_termhood"],
               "accepted_best_comparison": p["accepted_best_comparison"],
               "reason_top5": p["reason_top5"], "sense_final": sf, "sense_status": st, "sense_pass": sp,
               "sense_proxy": proxy.get(cid), "sense_openalex": sense_oa.get(cid),
               "sense_check_fail_flag": "sense_check_fail" in flags,
               "merge_cluster_id": m["merge_cluster_id"], "merge_cluster_id_strict": m["merge_cluster_id_strict"],
               "canonical_id": m["merge_canonical_id"], "merged_into": m["merge_merged_into"], "merged_into_strict": m["merged_into_strict"],
               "merge_cross_arm": m["merge_cross_arm"], "link_status": m["link_status"], "links": m["links"], "wikidata_qid": m["wikidata_qid"],
               "acronyms": [{k: a[k] for k in ("short_form", "collision_risk", "flag_for_later_retrieval")} for a in m["acronyms"]],
               "frame_llm_label_A": (audit.get("labels_A", {}).get(cid) or {}).get("label"),
               "frame_llm_label_adj": (audit.get("labels_adj", {}).get(cid) or {}).get("label")}
        rec["in_MAIN"] = bool(c["arm"] == "main" and rec["accepted_primary"] and sp and rec["merged_into"] is None)
        rec["in_STRICT"] = bool(c["arm"] == "main" and rec["accepted_strict"] and sp and rec["merged_into_strict"] is None)
        rec["in_REFERENCE_ACCEPTED"] = bool(c["arm"] == "reference" and rec["accepted_primary"] and rec["merged_into"] is None)
        concepts.append(rec)
    lists = {"MAIN": [r["concept_id"] for r in concepts if r["in_MAIN"]],
             "STRICT": [r["concept_id"] for r in concepts if r["in_STRICT"]],
             "REFERENCE_ACCEPTED": [r["concept_id"] for r in concepts if r["in_REFERENCE_ACCEPTED"]],
             "SENSITIVITY": [r["concept_id"] for r in concepts]}
    meta = {"frame_sha256": FRAME_SHA, "code_git_commit": git_commit(),
            "model_sha256": {"concept_lr": sha256_file(MODELS / "concept_lr.joblib"), "merger_lr": sha256_file(MODELS / "merger_lr.joblib"),
                             "concept_lr_notermhood": sha256_file(MODELS / "concept_lr_notermhood.joblib")},
            "thresholds": {"t_F1": thr["t_F1"], "t_P90": thr["t_P90"], "p_merge": ml["meta"]["p_merge"], "p_merge_strict": ml["meta"]["p_merge_strict"],
                           "link": lthr, "sense_cut": SENSE_CUT},
            "merger_used": ml["meta"]["merger"], "prelabel_sha256": (RESULTS / "frame_predictions_prelabel.sha256").read_text().strip(),
            "rules": RULES, "shift_diagnostic": diag, "F9_sense_proxy_rejected": f9,
            "sensitivity_pair_required": diag["sensitivity_pair_required"],
            "counts": {k: len(v) for k, v in lists.items()},
            "main_hydrated_now": sum(1 for r in concepts if r["in_MAIN"] and r["hydrated"]),
            "main_pending": sum(1 for r in concepts if r["in_MAIN"] and not r["hydrated"]),
            "power_rule_note": "iteration 3 pre-declared rule: H1 is a confirmatory test only with >= 150 MAIN concepts; hydrated-only count reported separately"}
    obj = {"meta": meta, "concepts": concepts, "lists": lists}
    s = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    (RESULTS / "test_population.json").write_text(s)
    h = hashlib.sha256(s.encode()).hexdigest()
    (RESULTS / "test_population.sha256").write_text(h + "\n")
    write_json(RESULTS / "test_population.created.json", {"created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "sha256": h})
    # T7 checks
    ids = {r["concept_id"] for r in concepts}
    for k, v in lists.items():
        assert set(v) <= ids, f"{k} not a subset of the frame"
    assert all(r["node_id"] == r["concept_id"] for r in concepts if r["link_status"] == "UNLINKED")
    assert len(concepts) == len(frame)
    logger.info(f"test population frozen sha256 {h}; counts {meta['counts']}; MAIN hydrated {meta['main_hydrated_now']} pending {meta['main_pending']}")


if __name__ == "__main__":
    main()
