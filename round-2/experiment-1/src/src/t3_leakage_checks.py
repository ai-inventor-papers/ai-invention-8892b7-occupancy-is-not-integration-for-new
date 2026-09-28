#!/usr/bin/env python3
"""T3 hard failures + T7 final checks on the finished run:
- 0 D2 train/test normalised-key overlap; 0 heldout_mesh descriptor or string in merger training
- frame silver labels written only after results/frame_predictions_prelabel.json (mtime and sha)
- threshold files older than every apply output (mtime)
- MAIN/STRICT/REFERENCE_ACCEPTED are subsets of the frame; every UNLINKED concept has node_id; counts match
- test_population.sha256 matches the file; no output file >= 100 MB outside cache/.venv"""
import hashlib
import json
from pathlib import Path

from loguru import logger

from common import MINI, DATA, MODELS, RESULTS, ROOT, normalise, read_json, setup_logging, write_json


@logger.catch(reraise=True)
def main() -> None:
    setup_logging("t3_leakage_checks")
    chk = {}
    d2 = read_json(DATA / "d2.json")
    tr = {normalise(x) for r in d2 if r["metadata_fold"] == "train" for x in [r["key"]] + r["surface_forms"]}
    te = {normalise(x) for r in d2 if r["metadata_fold"] == "test" for x in [r["key"]] + r["surface_forms"]}
    chk["d2_train_test_overlap"] = len(tr & te)
    mres = read_json(RESULTS / "merger_results.json")
    chk["merger_descriptor_overlap_after_guard"] = mres["leakage_guard"]["descriptor_overlap_after_guard"]
    m = lambda p: Path(p).stat().st_mtime
    pre = RESULTS / "frame_predictions_prelabel.json"
    chk["prelabel_before_labels"] = m(pre) < m(RESULTS / "frame_llm_audit.json")
    chk["prelabel_sha_matches"] = hashlib.sha256(pre.read_bytes()).hexdigest() == (RESULTS / "frame_predictions_prelabel.sha256").read_text().strip()
    audit = read_json(RESULTS / "frame_llm_audit.json")
    chk["audit_records_prelabel_sha"] = audit.get("prelabel_sha256") == (RESULTS / "frame_predictions_prelabel.sha256").read_text().strip()
    chk["classifier_thresholds_before_apply"] = m(MODELS / "thresholds.json") < m(pre)
    chk["merger_link_thresholds_before_apply"] = max(m(MODELS / "merger_thresholds.json"), m(MODELS / "link_thresholds.json"),
                                                     m(MODELS / "merger_choice.json")) < m(RESULTS / "frame_merge_link.json")
    tp_path = RESULTS / "test_population.json"
    tp = json.loads(tp_path.read_text())
    chk["test_population_sha_matches"] = hashlib.sha256(tp_path.read_bytes()).hexdigest() == (RESULTS / "test_population.sha256").read_text().strip()
    # internal schema of the frozen population (T2): required fields and types per concept record
    req = {"concept_id": str, "node_id": str, "phrase": str, "arm": str, "hydrated": bool, "p_concept": float,
           "accepted_primary": bool, "accepted_strict": bool, "sense_status": str, "sense_pass": bool, "link_status": str,
           "links": list, "acronyms": list, "merge_cluster_id": str, "canonical_id": str, "in_MAIN": bool, "in_STRICT": bool,
           "in_REFERENCE_ACCEPTED": bool, "reason_top5": list}
    bad = [(c.get("concept_id"), k) for c in tp["concepts"] for k, t in req.items() if not isinstance(c.get(k), t)]
    bad += [("meta", k) for k in ("frame_sha256", "code_git_commit", "model_sha256", "thresholds", "rules", "counts") if k not in tp["meta"]]
    bad += [("lists", k) for k in ("MAIN", "STRICT", "REFERENCE_ACCEPTED", "SENSITIVITY") if k not in tp["lists"]]
    chk["population_internal_schema_ok"] = not bad
    chk["population_schema_violations"] = bad[:10]
    chk["link_status_values_ok"] = all(c["link_status"] in ("LINKED_EXACT", "BROADER_ONLY", "UNLINKED") for c in tp["concepts"])
    ids = {c["concept_id"] for c in tp["concepts"]}
    chk["lists_subset_of_frame"] = all(set(v) <= ids for v in tp["lists"].values())
    chk["unlinked_have_node_id"] = all(c["node_id"] == c["concept_id"] for c in tp["concepts"] if c["link_status"] == "UNLINKED")
    chk["counts_match_lists"] = all(tp["meta"]["counts"][k] == len(v) for k, v in tp["lists"].items())
    mo = json.loads(((ROOT / "mini_run" / "method_out.json") if MINI else (ROOT / "method_out.json")).read_text())
    chk["method_out_counts_match"] = mo["metadata"]["summary"]["test_population_counts"] == tp["meta"]["counts"]
    big = [str(p.relative_to(ROOT)) for p in ROOT.rglob("*") if p.is_file() and p.stat().st_size >= 100 * 1024 ** 2
           and not str(p.relative_to(ROOT)).startswith((".venv", "cache", "mini_run/work"))]
    chk["no_file_ge_100MB_outside_cache"] = not big
    ok = (chk["d2_train_test_overlap"] == 0 and chk["merger_descriptor_overlap_after_guard"] == 0 and
          all(v for k, v in chk.items() if isinstance(v, bool)))
    chk["ALL_PASS"] = ok
    write_json(RESULTS / "t3_t7_checks.json", chk)
    logger.info(chk)
    assert ok, chk


if __name__ == "__main__":
    main()
