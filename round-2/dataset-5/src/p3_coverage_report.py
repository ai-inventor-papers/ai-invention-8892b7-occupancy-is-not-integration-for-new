#!/usr/bin/env python3
"""P3 bookkeeping: share of each concept's c-papers published in a COVERED venue (habitat_subfield != UNCOVERED),
overall, by origin-field group and by retrieval route; citation-independent (scimago) vs fallback split.
Writes outputs/venue_coverage_report.json. Coverage counts only, no analysis statistics."""
from collections import defaultdict
from pathlib import Path

import orjson
import pandas as pd
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parent
HYD = ROOT / "hyd"


def main() -> None:
    vh = orjson.loads((ROOT / "outputs" / "venue_habitat_asjc.json").read_bytes())["venues"]
    cov = {v["source_id"]: ("scimago" if v["route"] == "scimago" else "fallback")
           for v in vh if v["habitat_subfield"] != "UNCOVERED"}
    src = {}
    for f in sorted((HYD / "works").glob("works_part_*.parquet")):
        t = pq.read_table(f, columns=["work_id", "source_id"]).to_pandas()
        src.update(zip(t["work_id"].astype(int), t["source_id"]))
    cw = pd.read_parquet(HYD / "concept_work.parquet", columns=["concept_id", "work_id"])
    d = orjson.loads((HYD / "data_out.json").read_bytes())["datasets"][0]["examples"]
    gmap = orjson.loads((HYD / "data_out.json").read_bytes())["metadata"]["origin_field_group_map"]
    meta = {}
    for e in d:
        inp = orjson.loads(e["input"])
        of = (inp.get("origin_field") or {}).get("id")
        meta[e["metadata_concept_id"]] = {"route": e["metadata_retrieval_route"], "arm": e["metadata_arm"],
                                          "group": gmap.get(str(of), "REFERENCE" if e["metadata_arm"] == "reference" else "NA")}
    per = {}
    agg = defaultdict(lambda: [0, 0, 0])
    for cid, g in cw.groupby("concept_id"):
        kinds = [cov.get(src.get(int(w))) for w in g["work_id"]]
        n = len(kinds)
        a = sum(k is not None for k in kinds)
        s = sum(k == "scimago" for k in kinds)
        m = meta[cid]
        per[cid] = {"n_cpapers": n, "covered_share": round(a / n, 4) if n else None,
                    "covered_share_citation_independent": round(s / n, 4) if n else None, **m}
        for key in ("overall", f"group:{m['group']}", f"route:{m['route']}", f"arm:{m['arm']}"):
            agg[key][0] += n
            agg[key][1] += a
            agg[key][2] += s
    out = {"definition": __doc__,
           "aggregates": {k: {"n_cpaper_links": v[0], "covered_share": round(v[1] / v[0], 4),
                              "covered_share_citation_independent": round(v[2] / v[0], 4)} for k, v in sorted(agg.items())},
           "iteration1_topic_derived_comparison": {"n_venues": 15261, "n_covered": 4292,
                                                   "rule": "dominant all-years topic subfield share > 0.40 (NOT citation-independent)"},
           "per_concept": per}
    (ROOT / "outputs" / "venue_coverage_report.json").write_bytes(orjson.dumps(out, option=orjson.OPT_INDENT_2))
    print(orjson.dumps(out["aggregates"], option=orjson.OPT_INDENT_2).decode())


if __name__ == "__main__":
    main()
