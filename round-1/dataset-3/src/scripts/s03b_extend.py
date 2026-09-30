#!/usr/bin/env python3
"""Plan failure scenario: the 2006-2016 pool could not yield >= 120 concepts passing the final rule, so
DateEstablished is widened to 2004-2005 (tag w1, desc2017 snapshot) and 2017-2018 (tag w2, desc2019 snapshot);
the F window stays 2005-2016. Pre-screen passers of the widened years are APPENDED to the working list with
sample ranks after the original 283 (seeded order), so the original rank order is untouched.

Outputs: updates temp/working_list.json, temp/mesh_indexed.json, temp/pubmed_tiab_pmids.json; writes temp/flow_step6_ext.json
"""
from __future__ import annotations

import asyncio
import json
import random
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from s03_sample_and_indexed import SEED, TEMP, branch_group, indexed_sets, logger  # noqa: E402

TAGS = {"w1": "2004-2005", "w2": "2017-2018"}


def main() -> None:
    wl = json.loads((TEMP / "working_list.json").read_text())
    have = {r["descriptor_ui"] for r in wl}
    cuts = json.loads((TEMP / "flow_step6.json").read_text())[0]["tercile_cuts_pubmed_early"]
    new, flow = [], []
    tiab = json.loads((TEMP / "pubmed_tiab_pmids.json").read_text())
    for tag, period in TAGS.items():
        cands = {r["descriptor_ui"]: r for r in json.loads((TEMP / f"candidates_{tag}.json").read_text())}
        pre = json.loads((TEMP / f"prescreen_{tag}.json").read_text())
        tiab.update(json.loads((TEMP / f"pubmed_tiab_pmids_{tag}.json").read_text()))
        n = 0
        for d in pre:
            if d["prescreen"] != "pass" or d["descriptor_ui"] in have:
                continue
            r = dict(cands[d["descriptor_ui"]])
            r.update({k: d[k] for k in ("total_pubmed_1995_2024", "F_pubmed", "early_pubmed_F_F2",
                                        "yearly_pubmed_1995_2018", "pubmed_query", "quoted_phrase_not_found")})
            r["branch_group"] = branch_group(r["tree_branch_primary"])
            r["period"] = period
            e = r["early_pubmed_F_F2"]
            r["volume_tercile"] = "T1_low" if e <= cuts[0] else ("T2_mid" if e <= cuts[1] else "T3_high")
            r["stratum"] = f"{r['branch_group']}|{r['volume_tercile']}|{r['period']}"
            r["selection_prob"] = 1.0
            r["selection_seed"] = SEED + 1
            r["widening_tag"] = tag
            new.append(r)
            n += 1
        flow.append({"step": f"widening {tag} ({period}) pre-screen passers appended", "n": n})
    new.sort(key=lambda r: r["descriptor_ui"])
    random.Random(SEED + 1).shuffle(new)
    start = max(r["sample_rank"] for r in wl)
    for i, r in enumerate(new, 1):
        r["sample_rank"] = start + i
    logger.info(f"appending {len(new)} widened passers; groups {Counter(r['branch_group'] for r in new)}")
    (TEMP / "pubmed_tiab_pmids.json").write_text(json.dumps(tiab))
    (TEMP / "working_list.json").write_text(json.dumps(wl + new, indent=1))
    (TEMP / "flow_step6_ext.json").write_text(json.dumps(flow, indent=1))
    logger.info("working list extended; fetching MeSH-indexed sets for the new concepts")
    idx = json.loads((TEMP / "mesh_indexed.json").read_text())
    if new:
        idx.update(asyncio.run(indexed_sets(new)))
    (TEMP / "mesh_indexed.json").write_text(json.dumps(idx))


if __name__ == "__main__":
    logger.catch(reraise=True)(main)()
