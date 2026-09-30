#!/usr/bin/env python3
"""STEP 0: integrity checks + loading. Verifies the frozen frame hash, partitions the frame into hydrated/pending,
extracts every DS4/DS3 dataset we need into compact workspace files (data/*.json, cache/d1_corpus.parquet),
and prints the T0 smoke counts."""
import gc
import json
from collections import Counter

import pandas as pd
from loguru import logger

from common import (CACHE, DATA, DS3, DS4, RESULTS, load_ds3, load_ds4_subset, load_frame, load_hydrated, read_json,
                    set_limits, setup_logging, write_json, normalise)


@logger.catch(reraise=True)
def main() -> None:
    setup_logging("s0_load")
    set_limits(40)
    counts: dict = {}
    # ---------------- frame
    frame = load_frame()
    arms = Counter(c["arm"] for c in frame.values())
    logger.info(f"frame: {len(frame)} concepts {dict(arms)} (sha256 verified)")
    hyd = load_hydrated()
    pend = read_json(DATA / "pending_hydration.json")["pending"]
    pend_ids = {p["concept_id"] for p in pend}
    assert set(hyd) | pend_ids == set(frame), "hydrated u pending != frame"
    assert not (set(hyd) & pend_ids), "hydrated and pending overlap"
    sense_oa = {}
    for line in (DATA / "sense_check.jsonl").read_text().splitlines():
        r = json.loads(line)
        sense_oa[r["concept_id"]] = r["dominant_share"]
    counts["frame"] = {"total": len(frame), "arms": dict(arms), "hydrated": len(hyd), "pending": len(pend_ids),
                       "complete_beyond_prefix": sum(p["complete_beyond_prefix"] for p in pend),
                       "sense_oa": len(sense_oa),
                       "hydrated_by_arm": dict(Counter(frame[c]["arm"] for c in hyd)),
                       "pending_by_arm": dict(Counter(frame[c]["arm"] for c in pend_ids))}
    logger.info(counts["frame"])

    # ---------------- DS4 (read part by part; D1 corpus kept as parquet)
    names = ["openalex_stratified_corpus_2003_2016_with_prescreen_1995_2004", "llm_labelled_candidate_phrases",
             "variant_pairs", "external_human_anchors_semeval2017_scierc_phrases",
             "external_human_anchors_acronym_identification", "survivorship_free_phrase_pool_early"]
    ds = load_ds4_subset(names)
    for k, v in ds.items():
        logger.info(f"DS4 {k}: {len(v)} rows")
    d1 = ds.pop("openalex_stratified_corpus_2003_2016_with_prescreen_1995_2004")
    rows = []
    for e in d1:
        title = e.get("metadata_title") or ""
        inp = e["input"] or ""
        abstract = inp[len(title):].strip() if inp.startswith(title) else inp
        rows.append({"work_id": e["metadata_work_id"], "year": int(e["metadata_publication_year"]),
                     "field": e["metadata_field"], "fold": e["metadata_fold"], "title": title, "abstract": abstract})
    pd.DataFrame(rows).to_parquet(CACHE / "d1_corpus.parquet", compression="zstd")
    counts["D1"] = {"n": len(rows), "folds": dict(Counter(r["fold"] for r in rows))}
    del d1, rows
    gc.collect()

    d2 = ds["llm_labelled_candidate_phrases"]
    d2_rows = []
    for e in d2:
        inp = json.loads(e["input"])
        d2_rows.append({"key": inp["key"], "surface_forms": inp.get("surface_forms", []),
                        "acronym_short_forms": inp.get("acronym_short_forms", []),
                        "snippets": [s.get("text", "") for s in inp.get("snippets", [])],
                        "output": e["output"], **{k: v for k, v in e.items() if k.startswith("metadata_")}})
    write_json(DATA / "d2.json", d2_rows, indent=None)
    counts["D2"] = {"n": len(d2_rows), "fold": dict(Counter(r["metadata_fold"] for r in d2_rows)),
                    "train_labels": dict(Counter(r["output"] for r in d2_rows if r["metadata_fold"] == "train")),
                    "test_labels": dict(Counter(r["output"] for r in d2_rows if r["metadata_fold"] == "test"))}
    d3 = []
    for e in ds["variant_pairs"]:
        inp = json.loads(e["input"])
        d3.append({**inp, "output": e["output"], **{k: v for k, v in e.items() if k.startswith("metadata_")}})
    write_json(DATA / "d3.json", d3, indent=None)
    counts["D3"] = {"n": len(d3), "fold": dict(Counter(r["metadata_fold"] for r in d3)),
                    "labels": dict(Counter(r["output"] for r in d3)), "source": dict(Counter(r["metadata_source"] for r in d3))}
    d4a = []
    for e in ds["external_human_anchors_semeval2017_scierc_phrases"]:
        inp = json.loads(e["input"])
        d4a.append({**inp, "output": e["output"], **{k: v for k, v in e.items() if k.startswith("metadata_")}})
    write_json(DATA / "d4a.json", d4a, indent=None)
    counts["D4a"] = {"n": len(d4a), "fold": dict(Counter(r["metadata_fold"] for r in d4a)),
                     "source": dict(Counter(r["metadata_source"] for r in d4a)),
                     "in_llm_anchor_check": sum(bool(r.get("metadata_in_llm_anchor_check")) for r in d4a)}
    d4b = [{"sentence": e["input"], "gold": json.loads(e["output"]), "fold": e["metadata_fold"],
            "sh_pred": e.get("metadata_schwartz_hearst_pred")} for e in ds["external_human_anchors_acronym_identification"]]
    write_json(DATA / "d4b.json", d4b, indent=None)
    counts["D4b"] = {"n": len(d4b), "fold": dict(Counter(r["fold"] for r in d4b))}
    d5 = []
    for e in ds["survivorship_free_phrase_pool_early"]:
        inp = json.loads(e["input"]) if e["input"].startswith("{") else {"phrase": e["input"]}
        d5.append({"input": inp, **{k: v for k, v in e.items() if k.startswith("metadata_")}})
    write_json(DATA / "d5.json", d5, indent=None)
    counts["D5"] = {"n": len(d5)}
    del ds
    gc.collect()

    # ---------------- DS3
    ds3 = load_ds3()
    mp = []
    for e in ds3["mesh_synonym_pairs"]:
        inp = json.loads(e["input"])
        mp.append({"term_a": inp["term_a"], "term_b": inp["term_b"], "y": int(e["output"]),
                   **{k: v for k, v in e.items() if k.startswith("metadata_")}})
    write_json(DATA / "mesh_pairs.json", mp, indent=None)
    hm = []
    for e in ds3["heldout_mesh_concepts"]:
        inp = json.loads(e["input"])
        hm.append({"descriptor_ui": inp["descriptor_ui"], "preferred_term": inp["preferred_term"],
                   "surface_forms": inp.get("surface_forms", []), "acronyms": inp.get("acronyms", []),
                   "excluded_forms": inp.get("excluded_forms", [])})
    write_json(DATA / "heldout_mesh_concepts.json", hm, indent=None)
    counts["mesh_pairs"] = {"n": len(mp), "fold": dict(Counter(r["metadata_fold"] for r in mp)),
                            "pair_type": dict(Counter(r["metadata_pair_type"] for r in mp)),
                            "y": dict(Counter(r["y"] for r in mp))}
    counts["heldout_mesh_concepts"] = len(hm)
    # smoke expectation checks (logged, not fatal except the frame)
    exp = {"D2 train": (counts["D2"]["fold"].get("train"), 1200), "D2 test": (counts["D2"]["fold"].get("test"), 300),
           "D3": (len(d3), 502), "D4a": (len(d4a), 23520), "mesh pairs": (len(mp), 23097), "frame": (len(frame), 426),
           "sense_oa": (len(sense_oa), 183)}
    for k, (got, want) in exp.items():
        (logger.info if got == want else logger.warning)(f"T0 {k}: got {got} expected {want}")
    counts["normalise_check"] = normalise("Weyl semimetals") == normalise("weyl-semimetal")
    assert counts["normalise_check"], "normalise('Weyl semimetals') != normalise('weyl-semimetal')"
    write_json(RESULTS / "t0_counts.json", counts)
    logger.info(json.dumps(counts)[:3000])


if __name__ == "__main__":
    main()
