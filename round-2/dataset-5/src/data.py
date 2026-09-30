#!/usr/bin/env python3
"""Row-level export of the iteration-2 datasets in the exp_sel_data_out schema (one example per data row, grouped
by dataset), split into < 90 MB parts in full_data_out/.

  concept_pool_2005_2016  hyd/data_out.json                  dataset_1 D1 schema + hydration_batch, focal_years_all
  concept_work_links      hyd/concept_work.parquet           dataset_1 D3 schema
  openalex_works          hyd/works/*.parquet                dataset_1 D2 schema (feature_names identical) +
                                                             metadata_retrieval_batch
  subfield_year_totals    hyd/context/subfield_year_totals.json  dataset_1 D4 (25,195 rows, copied unchanged)
  nativeness_profiles     p2/profiles.jsonl                  1 row / (node, block), exact API counts
  nativeness_coverage     outputs/nativeness_coverage.json   1 row / pool concept + overall row
  venue_habitat_asjc      outputs/venue_habitat_asjc.json    1 row / source_id seen in openalex_works

Usage: .venv/bin/python data.py
"""
import sys
from pathlib import Path

import orjson
import pyarrow.parquet as pq
from loguru import logger

ROOT = Path(__file__).resolve().parent
HYD = ROOT / "hyd"
sys.path.insert(0, str(HYD))
import data as d1  # noqa: E402  (hyd/data.py: dataset_1 builders, ROOT = hyd/)

PART_LIMIT = 85_000_000
J = lambda o: orjson.dumps(o).decode()  # noqa: E731

logger.remove()
logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
(ROOT / "logs").mkdir(exist_ok=True)
logger.add(ROOT / "logs" / "data.log", rotation="30 MB", level="DEBUG")


def ds_works() -> list[dict]:
    out = []
    cols = d1.WORK_FEATURES + ["subfield_id", "field_id", "domain_id", "retrieval_batch"]
    for p in sorted((HYD / "works").glob("works_part_*.parquet")):
        for r in pq.read_table(p, columns=cols).to_pylist():
            if r["topic_score"] is not None:
                r["topic_score"] = round(float(r["topic_score"]), 4)
            sf = r["subfield_id"]
            out.append({"input": J([r[k] for k in d1.WORK_FEATURES]),
                        "output": str(sf) if sf is not None else "unknown",
                        "metadata_field_id": r["field_id"], "metadata_domain_id": r["domain_id"],
                        "metadata_retrieval_batch": r["retrieval_batch"]})
    return out


def ds_profiles() -> list[dict]:
    out = []
    p = ROOT / "p2" / "profiles.jsonl"
    rows = [orjson.loads(x) for x in p.read_text().splitlines() if x.strip()] if p.exists() else []
    rows.sort(key=lambda r: (r["coverage_rank"], r["block"]))
    for r in rows:
        inp = {"node_id": r["node_id"], "node_type": r["node_type"], "display_name": r["display_name"],
               "level": r["level"], "block": r["block"]}
        outp = {"total": r["total"], "subfield_counts": r["subfield_counts"], "n_groups": r["n_groups"],
                "truncated_top200": r["truncated_top200"]}
        out.append({"input": J(inp), "output": J(outp), "metadata_coverage_rank": r["coverage_rank"],
                    "metadata_host_cooc_weight": r["host_cooc_weight"],
                    "metadata_cum_weight_share": round(r["cum_weight_share"], 6), "metadata_frame": r["frame"],
                    "metadata_retrieved_utc": r["retrieved_utc"], "metadata_credits": r["credits"],
                    "metadata_request_filter": r["request_filter"]})
    return out


def ds_coverage() -> list[dict]:
    d = orjson.loads((ROOT / "outputs" / "nativeness_coverage.json").read_bytes())
    out = []
    for r in d["concepts"]:
        out.append({"input": J({"concept_id": r["concept_id"], "origin_subfield": r["origin_subfield"]}),
                    "output": J({"covered_weight_share": r["covered_weight_share"],
                                 "n_host_cpapers": r["n_host_cpapers"], "n_distinct_nodes": r["n_distinct_nodes"],
                                 "host_weight": r["host_weight"]}),
                    "metadata_phrase": r["phrase"], "metadata_arm": r["arm"], "metadata_origin_rule": r["origin_rule"]})
    o = d["overall"]
    out.append({"input": J({"concept_id": "__OVERALL__", "origin_subfield": None}), "output": J(o),
                "metadata_phrase": None, "metadata_arm": "overall", "metadata_origin_rule": None})
    return out


def ds_venues() -> list[dict]:
    d = orjson.loads((ROOT / "outputs" / "venue_habitat_asjc.json").read_bytes())
    out = []
    for v in d["venues"]:
        inp = {"source_id": v["source_id"], "issn_l": v.get("issn_l"), "issns": v.get("issns"),
               "display_name": v.get("display_name"), "openalex_type": v.get("openalex_type")}
        outp = {"habitat_subfield": v["habitat_subfield"], "fractional_shares": v["fractional_shares"],
                "asjc_codes_raw": v["asjc_codes_raw"]}
        out.append({"input": J(inp), "output": J(outp), "metadata_route": v["route"],
                    "metadata_sjr_year_used": v["sjr_year_used"], "metadata_uncovered_reason": v["uncovered_reason"],
                    "metadata_n_c_papers": v["n_c_papers"], "metadata_citation_independent": v["citation_independent"],
                    "metadata_habitat_in_openalex_subfields": v.get("habitat_in_openalex_subfields"),
                    "metadata_asjc_codes_union_2005_2010_2015_2019": J(v.get("asjc_codes_union_2005_2010_2015_2019")),
                    "metadata_scopus_source_ids": J(v.get("scopus_source_ids")),
                    "metadata_general_field": v.get("general_field"),
                    "metadata_preperiod_dominant_share": v.get("preperiod_dominant_share")})
    return out


TOP_META = {
    "description": "Iteration-2 concept-pool artifact (see README.md). One example per data row, grouped by dataset.",
    "feature_names": {"concept_work_links": d1.LINK_FEATURES, "openalex_works": d1.WORK_FEATURES},
    "notes": {**d1.TOP_META["notes"],
              "subfield_year_totals": "dataset_1 D4 copied unchanged; the 'all_types' variant is the per-10^4 "
                                      "denominator (c-papers include every work type)",
              "nativeness_profiles": "exact OpenAlex meta.count and group_by counts, never sample-based; frame = all "
                                     "types; 'unknown' = works without a primary topic",
              "venue_habitat_asjc": "habitat_subfield = 4-digit ASJC code (= OpenAlex subfield id where one exists) "
                                    "or 'UNCOVERED'; route preperiod_groupby is NOT citation-independent"}}


def trunc(o, n: int = 200):
    """Preview variant: every string truncated to n characters (recursively)."""
    if isinstance(o, str):
        return o if len(o) <= n else o[:n] + "..."
    if isinstance(o, list):
        return [trunc(x, n) for x in o]
    if isinstance(o, dict):
        return {k: trunc(v, n) for k, v in o.items()}
    return o


def write_small(path_stem: Path, datasets: list[dict]) -> None:
    """mini_* (3 examples per dataset) and preview_* (mini with strings truncated to 200 chars)."""
    mini = {"metadata": TOP_META, "datasets": [{"dataset": d["dataset"], "examples": d["examples"][:3]}
                                               for d in datasets]}
    (path_stem.parent / f"mini_{path_stem.name}.json").write_bytes(orjson.dumps(mini, option=orjson.OPT_INDENT_2))
    (path_stem.parent / f"preview_{path_stem.name}.json").write_bytes(
        orjson.dumps(trunc(mini), option=orjson.OPT_INDENT_2))


def write_parts(datasets: list[dict]) -> None:
    out_dir = ROOT / "full_data_out"
    out_dir.mkdir(exist_ok=True)
    for old in sorted(out_dir.glob("*.json")):
        old.unlink()
    parts, cur, size = [], [], 0
    for d in datasets:
        chunk = []
        for e in d["examples"]:
            b = len(orjson.dumps(e)) + 1
            if size + b > PART_LIMIT and (chunk or cur):
                if chunk:
                    cur.append({"dataset": d["dataset"], "examples": chunk})
                parts.append(cur)
                cur, chunk, size = [], [], 0
            chunk.append(e)
            size += b
        if chunk:
            cur.append({"dataset": d["dataset"], "examples": chunk})
    if cur:
        parts.append(cur)
    for k, p in enumerate(parts, 1):
        (out_dir / f"full_data_out_{k}.json").write_bytes(orjson.dumps({"metadata": TOP_META, "datasets": p}))
        write_small(out_dir / f"data_out_{k}", p)
        logger.info(f"part {k}: " + ", ".join(f"{x['dataset']}={len(x['examples'])}" for x in p))
    logger.info(f"wrote {len(parts)} parts to full_data_out/")


@logger.catch(reraise=True)
def main() -> None:
    cm = d1.concept_meta()
    builders = {
        "concept_pool_2005_2016": d1.ds_concept_pool,
        "concept_work_links": lambda: d1.ds_links(cm),
        "openalex_works": ds_works,
        "subfield_year_totals": d1.ds_denominators,
        "nativeness_profiles": ds_profiles,
        "nativeness_coverage": ds_coverage,
        "venue_habitat_asjc": ds_venues,
    }
    datasets = []
    for n, fn in builders.items():
        ex = fn()
        logger.info(f"{n}: {len(ex)} examples")
        if not ex:
            logger.warning(f"{n}: no rows yet, dataset left out of this export")
            continue
        datasets.append({"dataset": n, "examples": ex})
    write_parts(datasets)
    write_small(ROOT / "data_out", datasets)  # root mini_data_out.json / preview_data_out.json: 3 per dataset


if __name__ == "__main__":
    main()
