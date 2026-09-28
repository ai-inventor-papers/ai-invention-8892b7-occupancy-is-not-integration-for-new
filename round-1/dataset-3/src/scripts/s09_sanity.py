#!/usr/bin/env python3
"""Usefulness sanity check (descriptive, not an analysis of the hypothesis): does the population carry the
emergence / diffusion structure the study needs? Uses only verified works of concepts.
Output: sanity_check.json
"""
from __future__ import annotations

import glob
import gzip
import json
from collections import defaultdict
from pathlib import Path

import numpy as np
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    concepts = {c["input"]["concept_id"]: c for c in json.loads((ROOT / "data_out.json").read_text())}
    sub = defaultdict(lambda: defaultdict(set))       # concept -> year -> subfields
    fld = defaultdict(lambda: defaultdict(set))
    refs = defaultdict(int)
    nw = defaultdict(int)
    for p in sorted(glob.glob(str(ROOT / "works" / "works_part_*.jsonl.gz"))):
        with gzip.open(p, "rt") as fh:
            for line in fh:
                w = json.loads(line)
                if not w["verified_text_match"] or w["match_route"] == "mesh_indexed_only":
                    continue
                pt = w["primary_topic"] or {}
                if pt.get("subfield_id"):
                    sub[w["concept_id"]][w["publication_year"]].add(pt["subfield_id"])
                    fld[w["concept_id"]][w["publication_year"]].add(pt["field_id"])
                nw[w["concept_id"]] += 1
                refs[w["concept_id"]] += bool(w["referenced_works"])
    rows = []
    for cid, c in concepts.items():
        F = c["input"]["F"]
        yc = {int(y): v for y, v in c["output"]["yearly_counts_textmatch"].items()}
        early = sum(yc.get(y, 0) for y in range(F, F + 3))
        later = sum(yc.get(y, 0) for y in range(F + 3, F + 9) if y <= 2024)
        reach_early = len(set().union(*[sub[cid].get(y, set()) for y in range(F, F + 3)]))
        reach_later = len(set().union(*[sub[cid].get(y, set()) for y in range(F + 3, min(F + 9, 2025))]))
        fields_early = len(set().union(*[fld[cid].get(y, set()) for y in range(F, F + 3)]))
        fields_all = len(set().union(*[fld[cid].get(y, set()) for y in range(2000, 2025)]))
        rows.append({"concept_id": cid, "F": F, "early": early, "later_F3_F8": later, "subfields_early": reach_early,
                     "subfields_later": reach_later, "fields_early": fields_early, "fields_all": fields_all,
                     "share_with_refs": refs[cid] / nw[cid] if nw[cid] else None})
    a = {k: np.array([r[k] for r in rows], dtype=float) for k in ("early", "later_F3_F8", "subfields_early", "subfields_later", "fields_all")}
    rho, pval = spearmanr(a["subfields_early"], a["later_F3_F8"]) if len(rows) > 5 else (None, None)
    rho2, p2 = spearmanr(a["early"], a["later_F3_F8"]) if len(rows) > 5 else (None, None)
    out = {
        "n_concepts": len(rows),
        "median_growth_ratio_later6y_over_early3y": float(np.median((a["later_F3_F8"] + 1) / (a["early"] + 1))),
        "share_concepts_growing": float(np.mean(a["later_F3_F8"] / 2 > a["early"])),
        "median_subfields_early_F_F2": float(np.median(a["subfields_early"])),
        "median_subfields_later_F3_F8": float(np.median(a["subfields_later"])),
        "share_concepts_reach_expands": float(np.mean(a["subfields_later"] > a["subfields_early"])),
        "median_fields_2000_2024": float(np.median(a["fields_all"])),
        "spearman_early_subfields_vs_later_volume": {"rho": None if rho is None else float(rho), "p": None if pval is None else float(pval)},
        "spearman_early_volume_vs_later_volume": {"rho": None if rho2 is None else float(rho2), "p": None if p2 is None else float(p2)},
        "per_concept": rows,
        "note": "Descriptive sanity check only: verified works; later window F+3..F+8 (truncated at 2024). Shows the "
                "population has variance in growth and in disciplinary reach, i.e. usable signal for RQ1/RQ2.",
    }
    (ROOT / "sanity_check.json").write_text(json.dumps(out, indent=1))
    print({k: v for k, v in out.items() if k not in ("per_concept", "note")})


if __name__ == "__main__":
    main()
