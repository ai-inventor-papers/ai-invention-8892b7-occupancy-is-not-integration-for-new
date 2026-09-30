# /// script
# requires-python = ">=3.12"
# dependencies = ["orjson", "pandas", "pyarrow", "loguru"]
# ///
"""Standardise the candidate datasets to the exp_sel_data_out schema, ONE EXAMPLE PER DATA ROW, grouped by dataset.

Artifact datasets (built by this repo; canonical files at the workspace root):
  concept_pool_2005_2016   D1  data_out.json            1 row / concept      output = oa_counts_by_year+work_ids (JSON)
  concept_work_links       D3  concept_work.parquet     1 row / link         output = match_evidence
  openalex_works           D2  works/*.parquet          1 row / work         output = primary-topic subfield_id
  subfield_year_totals     D4  context/subfield_year_totals.json  1 row / (variant, year, subfield)  output = count
  venue_habitat            D5  context/venue_habitat.json         1 row / venue  output = dominant_subfield
(The 5 labelled HF grounding sets in temp/datasets/ were evaluated in an earlier version and not selected.)

Usage: uv run data.py   -> full_data_out.json, split into full_data_out/full_data_out_N.json when > 90 MB"""
import sys
from pathlib import Path

import orjson
import pandas as pd
import pyarrow.parquet as pq
from loguru import logger

ROOT = Path(__file__).resolve().parent
PART_LIMIT = 90_000_000
BEST5 = ["concept_pool_2005_2016", "concept_work_links", "openalex_works", "subfield_year_totals", "venue_habitat"]

logger.remove()
logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
logger.add(ROOT / "logs" / "data.log", rotation="30 MB", level="DEBUG")

J = lambda o: orjson.dumps(o).decode()  # noqa: E731


def concept_meta() -> dict:
    d = orjson.loads((ROOT / "data_out.json").read_bytes())
    return {e["metadata_concept_id"]: e for e in d["datasets"][0]["examples"]}


def ds_concept_pool() -> list[dict]:
    d = orjson.loads((ROOT / "data_out.json").read_bytes())
    return d["datasets"][0]["examples"]


LINK_FEATURES = ["concept_id", "work_id", "year"]


def ds_links(cm: dict) -> list[dict]:
    """input = JSON array ordered as LINK_FEATURES (names in top-level metadata to keep the file small)."""
    cw = pd.read_parquet(ROOT / "concept_work.parquet")
    out = []
    for i, r in enumerate(cw.itertuples(index=False)):
        c = cm[r.concept_id]
        out.append({"input": J([r.concept_id, int(r.work_id), int(r.year)]), "output": str(r.match_evidence),
                    "metadata_fold": c["metadata_fold"], "metadata_matched_form": r.matched_form,
                    "metadata_dup_group": None if pd.isna(r.dup_group) else int(r.dup_group)})
    return out


WORK_FEATURES = ["work_id", "publication_year", "type", "language", "doi_present", "s2_corpus_id", "primary_topic_id",
                 "topic_score", "topics_top3", "source_id", "source_type", "n_refs", "refs_in_corpus", "author_ids",
                 "keyword_idx", "concept_ids", "has_abstract", "abstract_n_tokens", "cited_by_count", "dup_group"]


def ds_works() -> list[dict]:
    """input = JSON array ordered as WORK_FEATURES; output = primary-topic subfield id (ASJC-style) or 'unknown'.
    Full referenced_works, institution_ids and keyword/concept scores stay in works/works_part_XX.parquet."""
    out = []
    cols = WORK_FEATURES + ["subfield_id", "field_id", "domain_id"]
    for p in sorted((ROOT / "works").glob("works_part_*.parquet")):
        for r in pq.read_table(p, columns=cols).to_pylist():
            if r["topic_score"] is not None:
                r["topic_score"] = round(float(r["topic_score"]), 4)
            sf = r["subfield_id"]
            out.append({"input": J([r[k] for k in WORK_FEATURES]), "output": str(sf) if sf is not None else "unknown",
                        "metadata_field_id": r["field_id"], "metadata_domain_id": r["domain_id"]})
    return out


def ds_denominators() -> list[dict]:
    d4 = orjson.loads((ROOT / "context" / "subfield_year_totals.json").read_bytes())
    tax = orjson.loads((ROOT / "taxonomy.json").read_bytes())
    out = []
    for v, years in d4["variants"].items():
        for y, t in sorted(years.items()):
            for sf, n in sorted(t["subfield"].items(), key=lambda x: int(x[0])):
                f = tax["subfield_field"].get(sf)
                out.append({"input": J({"variant": v, "year": int(y), "subfield_id": int(sf),
                                        "subfield_name": tax["subfields"].get(sf), "field_id": f,
                                        "domain_id": tax["field_domain"].get(str(f)) if f else None}),
                            "output": str(n), "metadata_level": "subfield", "metadata_task_type": "regression",
                            "metadata_year_total_with_topic": t["total_with_topic"], "metadata_year_unknown": t["unknown"]})
    return out


def ds_venues() -> list[dict]:
    d5 = orjson.loads((ROOT / "context" / "venue_habitat.json").read_bytes())
    out = []
    for v in d5["venues"]:
        inp = {k: v[k] for k in ["source_id", "issn_l", "display_name", "type", "host_org", "works_count",
                                 "max_works_per_year", "subfield_shares", "n_cpapers"]}
        out.append({"input": J(inp), "output": str(v["dominant_subfield"]) if v["dominant_subfield"] is not None else "unknown",
                    "metadata_dominant_share": v["dominant_share"], "metadata_megajournal": v["megajournal"],
                    "metadata_covered": v["covered"], "metadata_uncovered_reason": v["uncovered_reason"],
                    "metadata_task_type": "classification"})
    return out


TOP_META = {
    "description": "Concept pool 2005-2016 artifact (see README.md). One example per data row, grouped by dataset.",
    "feature_names": {"concept_work_links": LINK_FEATURES, "openalex_works": WORK_FEATURES},
    "notes": {"openalex_works": "input is a JSON array in feature_names order; output = primary_topic subfield_id; full "
                                "refs/institutions/scores in works/works_part_XX.parquet",
              "concept_work_links": "input = [concept_id, work_id, year]; output = match_evidence; concept details in "
                                    "concept_pool_2005_2016"}}


def write_parts(datasets: list[dict]) -> None:
    for old in [ROOT / "full_data_out.json"] + sorted((ROOT / "full_data_out").glob("full_data_out_*.json")):
        old.unlink(missing_ok=True)
    total = sum(len(orjson.dumps(e)) + 1 for d in datasets for e in d["examples"])
    if total < PART_LIMIT:
        (ROOT / "full_data_out.json").write_bytes(orjson.dumps({"metadata": TOP_META, "datasets": datasets}))
        logger.info(f"wrote full_data_out.json ({total / 1e6:.1f} MB)")
        return
    (ROOT / "full_data_out").mkdir(exist_ok=True)
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
        (ROOT / "full_data_out" / f"full_data_out_{k}.json").write_bytes(orjson.dumps({"metadata": TOP_META, "datasets": p}))
    logger.info(f"wrote {len(parts)} parts to full_data_out/ ({total / 1e6:.1f} MB total)")


@logger.catch(reraise=True)
def main() -> None:
    cm = concept_meta()
    builders = {
        "concept_pool_2005_2016": ds_concept_pool,
        "concept_work_links": lambda: ds_links(cm),
        "openalex_works": ds_works,
        "subfield_year_totals": ds_denominators,
        "venue_habitat": ds_venues,
    }
    names = BEST5
    datasets = []
    for n in names:
        try:
            ex = builders[n]()
        except (FileNotFoundError, KeyError, ValueError) as e:
            logger.error(f"{n}: failed ({e})")
            raise
        logger.info(f"{n}: {len(ex)} examples")
        datasets.append({"dataset": n, "examples": ex})
    write_parts(datasets)


if __name__ == "__main__":
    main()
