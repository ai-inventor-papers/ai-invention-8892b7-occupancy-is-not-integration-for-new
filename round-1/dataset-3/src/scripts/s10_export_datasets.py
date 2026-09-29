#!/usr/bin/env python3
"""Export the four candidate datasets produced by this artifact into temp/datasets/ for data.py:

  heldout_mesh_concepts.json   concept table (copy of data_out.json)                        -> 1 row per concept
  mesh_synonym_pairs.json      MeSH synonym / hard-negative term pairs (copy)                -> 1 row per pair
  mesh_prescreen_table.json    every provenance-filtered new descriptor (2004-2018 pools) with its PubMed
                               pre-screen counts and outcome                                  -> 1 row per descriptor
  works/works_part_XX.jsonl.gz concept-work rows (hard links to ../../works/, no extra disk)  -> 1 row per (concept, work)
"""
from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEMP = ROOT / "temp"
OUT = TEMP / "datasets"
POOLS = {"": "2006-2016", "_w1": "2004-2005", "_w2": "2017-2018"}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ROOT / "data_out.json", OUT / "heldout_mesh_concepts.json")
    shutil.copyfile(ROOT / "mesh_synonym_pairs.json", OUT / "mesh_synonym_pairs.json")
    final = {c["input"]["descriptor_ui"] for c in json.loads((ROOT / "data_out.json").read_text())}
    rows = []
    for suf, pool in POOLS.items():
        cands = {r["descriptor_ui"]: r for r in json.loads((TEMP / f"candidates{suf}.json").read_text())}
        for d in json.loads((TEMP / f"prescreen{suf}.json").read_text()):
            r = cands[d["descriptor_ui"]]
            rows.append({
                "descriptor_ui": r["descriptor_ui"], "preferred_term": r["preferred_term"], "pool": pool,
                "date_established": r["date_established"], "tree_numbers": r["tree_numbers"],
                "tree_branch_primary": r["tree_branch_primary"], "provenance_class": r["provenance_class"],
                "chemical_flag": r["chemical_flag"], "surface_forms": r["surface_forms"],
                "pubmed_query": d["pubmed_query"], "total_pubmed_1995_2024": d["total_pubmed_1995_2024"],
                "yearly_pubmed_1995_2018": d.get("yearly_pubmed_1995_2018"), "F_pubmed": d.get("F_pubmed"),
                "early_pubmed_F_F2": d.get("early_pubmed_F_F2"), "prescreen_outcome": d["prescreen"],
                "in_final_population": r["descriptor_ui"] in final,
            })
    (OUT / "mesh_prescreen_table.json").write_text(json.dumps(rows))
    wd = OUT / "works"
    wd.mkdir(exist_ok=True)
    for old in wd.glob("*.jsonl.gz"):
        old.unlink()
    for p in sorted((ROOT / "works").glob("works_part_*.jsonl.gz")):
        os.link(p, wd / p.name)
    print(f"exported: {len(final)} concepts, {len(rows)} pre-screen rows, {len(list(wd.glob('*.gz')))} works parts")


if __name__ == "__main__":
    main()
