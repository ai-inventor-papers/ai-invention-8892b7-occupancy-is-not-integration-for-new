# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Standardise the held-out MeSH population's two selected datasets (prepared in temp/datasets/ by
build_population.py -> scripts/s10_export_datasets.py) into the pipeline schema exp_sel_data_out and write
full_data_out.json. One example per data row, grouped by dataset:

  heldout_mesh_concepts  1 example per concept     input = concept identity (JSON), output = yearly incidence/retrieval (JSON)
  mesh_synonym_pairs     1 example per term pair   input = {"term_a","term_b"} (JSON), output = "1" synonym / "0" hard negative

(Two further candidates were evaluated and not selected: the descriptor pre-screen table, temp/datasets/mesh_prescreen_table.json,
and the concept-work rows, works/works_part_XX.jsonl.gz, which ship as their own file group.)

usage: uv run data.py
"""
from __future__ import annotations

import gzip
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "temp" / "datasets"
DATASETS = ["heldout_mesh_concepts", "mesh_synonym_pairs"]


def dumps(o) -> str:
    return json.dumps(o, ensure_ascii=False, separators=(",", ":"))


def flat_metadata(meta: dict, prefix: str = "metadata_") -> dict:
    """Flatten one nesting level into metadata_<key> / metadata_<key>_<sub> fields (schema wants flat fields)."""
    out = {}
    for k, v in meta.items():
        if isinstance(v, dict):
            for k2, v2 in v.items():
                out[f"{prefix}{k}_{k2}"] = v2
        else:
            out[f"{prefix}{k}"] = v
    return out


def concepts() -> list[dict]:
    rows = json.loads((SRC / "heldout_mesh_concepts.json").read_text())
    ex = []
    for i, c in enumerate(rows):
        e = {"input": dumps(c["input"]), "output": dumps(c["output"]), "metadata_fold": c["metadata_fold"]}
        e.update(flat_metadata(c["metadata"]))
        e.update({"metadata_row_index": i, "metadata_concept_id": c["input"]["concept_id"],
                  "metadata_preferred_term": c["input"]["preferred_term"], "metadata_F": c["input"]["F"],
                  "metadata_task_type": "emergence_trajectory",
                  "metadata_input_fields": sorted(c["input"]), "metadata_output_fields": sorted(c["output"])})
        ex.append(e)
    return ex


def pairs() -> list[dict]:
    d = json.loads((SRC / "mesh_synonym_pairs.json").read_text())
    ex = []
    for i, p in enumerate(d["pairs"]):
        fold = "heldout_mesh" if p["in_heldout_population"] else ("working_list" if p["in_working_list"] else "train_eligible")
        ex.append({"input": dumps({"term_a": p["term_a"], "term_b": p["term_b"]}), "output": str(p["label"]),
                   "metadata_fold": fold, "metadata_pair_type": p["pair_type"],
                   "metadata_descriptor_ui": p["descriptor_ui"], "metadata_descriptor_ui_b": p["descriptor_ui_b"],
                   "metadata_orig_a": p["orig_a"], "metadata_orig_b": p["orig_b"],
                   "metadata_in_heldout_population": p["in_heldout_population"],
                   "metadata_in_working_list": p["in_working_list"], "metadata_task_type": "classification",
                   "metadata_n_classes": 2, "metadata_row_index": i})
    return ex


def works_sample(n: int) -> list[dict]:
    """First n concept-work rows (works/works_part_01.jsonl.gz) as schema examples, for mini/preview_works.json.
    The works themselves ship as gzip JSONL parts (one row per (concept, work)), not in full_data_out.json."""
    assign = ("concept_id", "match_route", "verified_text_match", "match_field", "matched_forms",
              "descriptor_indexed_openalex", "descriptor_indexed_pubmed")
    ex = []
    with gzip.open(ROOT / "works" / "works_part_01.jsonl.gz", "rt", encoding="utf-8") as fh:
        for line in fh:
            w = json.loads(line)
            ex.append({"input": dumps({k: v for k, v in w.items() if k not in assign and k != "metadata_fold"}),
                       "output": dumps({k: w[k] for k in assign}), "metadata_fold": w["metadata_fold"],
                       "metadata_concept_id": w["concept_id"], "metadata_work_id": w["work_id"],
                       "metadata_publication_year": w["publication_year"], "metadata_row_index": len(ex)})
            if len(ex) >= n:
                break
    return ex


def truncate(o, n: int = 200):
    if isinstance(o, str):
        return o[:n]
    if isinstance(o, list):
        return [truncate(x, n) for x in o]
    if isinstance(o, dict):
        return {k: truncate(v, n) for k, v in o.items()}
    return o


BUILDERS = {"heldout_mesh_concepts": concepts, "mesh_synonym_pairs": pairs}


def main() -> None:
    missing = [f for f in ("heldout_mesh_concepts.json", "mesh_synonym_pairs.json") if not (SRC / f).exists()]
    if missing:
        sys.exit(f"missing inputs in {SRC}: {missing} (run scripts/s10_export_datasets.py after build_population.py)")
    out = {"metadata": {"source": "held-out MeSH population (metadata_fold heldout_mesh); NLM MeSH + PubMed + OpenAlex (CC0)",
                        "description": "See README.md and provenance.md. input/output are JSON strings unless noted.",
                        "datasets": DATASETS},
           "datasets": []}
    for n in DATASETS:
        ex = BUILDERS[n]()
        out["datasets"].append({"dataset": n, "examples": ex})
        print(f"{n}: {len(ex)} examples")
    target = ROOT / "full_data_out.json"
    target.write_text(json.dumps(out, ensure_ascii=False))
    print(f"wrote {target.name} ({target.stat().st_size / 1e6:.1f} MB)")
    if (ROOT / "works" / "works_part_01.jsonl.gz").exists():
        meta = {"description": "first concept-work rows of works/works_part_XX.jsonl.gz (heldout_mesh_works)"}
        wex = works_sample(10)
        (ROOT / "mini_works.json").write_text(json.dumps(
            {"metadata": meta, "datasets": [{"dataset": "heldout_mesh_works", "examples": wex[:3]}]}, indent=1))
        (ROOT / "preview_works.json").write_text(json.dumps(
            {"metadata": meta, "datasets": [{"dataset": "heldout_mesh_works", "examples": truncate(wex)}]}, indent=1))
        print("wrote mini_works.json, preview_works.json")


if __name__ == "__main__":
    main()
