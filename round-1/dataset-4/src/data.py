#!/usr/bin/env python3
"""Standardise all prepared datasets into the exp_sel_data_out schema.

Default: writes the 7 selected deliverables into full_data_out.json (one group per dataset, one example per row).
--all:   also stages all 14 candidate datasets (7 deliverables + 7 extra keyphrase/vocabulary resources) with
         up to 200 rows each into temp/all14_candidates_data_out.json for inspection and selection.

Inputs (all produced by scripts/ or downloaded into temp/datasets/):
  raw/corpus_works/corpus_works_part_*.jsonl, raw/strata.json    -> D1 corpus
  labelling/items.json, labels_AB.json, labels_adj.json, split.json -> D2 candidate labels
  labelling/variant_pairs.json                                   -> D3 variant pairs
  raw/anchor_phrases.jsonl, raw/anchor_acronyms.jsonl, labelling/anchor_labels.json -> D4a / D4b
  data_out/pool_early.json                                       -> D5 phrase pool (the sealed outcome file is NOT read)
  subsample/heldout_works_rows.json                              -> D6 held-out phrase works

After running, `python scripts/split_output.py` splits full_data_out.json into full_data_out/full_data_out_<i>.json
(<=45 MB each) and writes the combined mini_data_out.json / preview_data_out.json.
"""
from __future__ import annotations

import argparse
import ast
import json
import sys
from pathlib import Path

from loguru import logger

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "scripts"))
from textnorm import schwartz_hearst  # noqa: E402
from rawio import read_corpus_works  # noqa: E402

logger.remove()
logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
(ROOT / "logs").mkdir(exist_ok=True)
logger.add(ROOT / "logs" / "data_py.log", rotation="30 MB", level="DEBUG")

LAB = ROOT / "labelling"
TD = ROOT / "temp" / "datasets"


def jl(p: Path):
    with p.open() as f:
        for line in f:
            if line.strip():
                yield json.loads(line)


KEY_OK = __import__("re").compile(r"^[a-z0-9\u03b1-\u03c9]")
BOILER = ("©", "wiley periodical", "all rights reserved", "elsevier")


def key_quality(k: str) -> str:
    """Known extraction defect flag (documented in README): keys that start with punctuation/symbols,
    non-Latin script or publisher boilerplate. The normaliser is left unchanged so outputs stay reproducible."""
    if any(b in k for b in BOILER):
        return "boilerplate"
    if not KEY_OK.match(k):
        return "malformed_leading_char"
    return "ok"


def s(x) -> str:
    return x if isinstance(x, str) else json.dumps(x, ensure_ascii=False)


# ---------------------------------------------------------------- D1
def d1_corpus(limit: int | None = None) -> list[dict]:
    strata = json.loads((ROOT / "raw" / "strata.json").read_text())
    w = {(x["field_id"], x["year"], x["corpus"]): x for x in strata["strata"]}
    out = []
    for i, r in enumerate(read_corpus_works()):
        if limit and i >= limit:
            break
        st = w[(r["stratum_field"], r["stratum_year"], r["corpus"])]
        out.append({
            "input": ((r["title"] or "").strip() + " " + (r["abstract"] or "")).strip(),
            # the corpus is a text source, not a labelled set; output carries the OpenAlex primary field (stratum label)
            "output": r["field"] or "",
            "metadata_fold": f"corpus_{r['corpus']}",
            "metadata_work_id": r["id"], "metadata_doi": r["doi"], "metadata_title": r["title"],
            "metadata_publication_year": r["year"], "metadata_publication_date": r["date"],
            "metadata_field_id": r["field_id"], "metadata_field": r["field"], "metadata_subfield_id": r["subfield_id"],
            "metadata_subfield": r["subfield"], "metadata_domain": r["domain"], "metadata_topic_id": r["topic_id"],
            "metadata_topic": r["topic"], "metadata_venue_id": r["venue_id"], "metadata_venue_type": r["venue_type"],
            "metadata_keywords": r["keywords"], "metadata_legacy_concepts_score_ge_0_3": r["concepts"],
            "metadata_referenced_works_count": r["referenced_works_count"], "metadata_author_ids": r["author_ids"],
            "metadata_institution_ids": r["institution_ids"],
            "metadata_stratum": f"field{r['stratum_field']}_{r['stratum_year']}_{r['corpus']}",
            "metadata_N_stratum": st["N_stratum"], "metadata_n_sampled_stratum": st["n_sampled"],
            "metadata_design_weight": st["design_weight"], "metadata_sample_seed": st["seed"],
        })
    return out


# ---------------------------------------------------------------- D2
def band(n: int) -> str:
    return "3-5" if n <= 5 else "6-20" if n <= 20 else "21-100" if n <= 100 else ">100"


def d2_labels() -> list[dict]:
    items = json.loads((LAB / "items.json").read_text())
    AB = json.loads((LAB / "labels_AB.json").read_text())
    ADJ = json.loads((LAB / "labels_adj.json").read_text())
    sp = json.loads((LAB / "split.json").read_text())
    silver = set(ADJ["silver_gold_200"])
    adj = ADJ["labels"]
    out = []
    for k in sorted(items):
        it = items[k]
        a, b, j = AB["A"].get(k, {}), AB["B"].get(k, {}), adj.get(k, {})

        def fmt(r: dict) -> str | None:
            if not r.get("label"):
                return None
            return f"VARIANT_OF:{r['variant_of']}" if r["label"] == "VARIANT_OF" and r.get("variant_of") else r["label"]

        la, lb, lj = fmt(a), fmt(b), fmt(j)
        if lj:
            final, basis = lj, "adjudicator"
        elif la and la == lb:
            final, basis = la, "A/B consensus"
        else:
            final, basis = "UNRESOLVED", "A/B disagree, not adjudicated" if la and lb else "missing label"
        if it["track"] == "P":
            fold = "pool_screen"
        else:
            fold = sp["split"][k]
            if fold == "test" and final == "UNRESOLVED":
                fold = "test_unresolved_excluded"
        st = it["stats"]
        form = "acronym" if st["is_acronym_long_form"] else ("1tok" if st["n_tokens"] == 1 else "2tok" if st["n_tokens"] == 2 else "3+tok")
        inp = {"key": k, "surface_forms": it["surface_forms"],
               "acronym_short_forms": it.get("acronym_short_forms", []),
               "snippets": it["snippets"], "n_sample_occ": st["n_occ"],
               "first_sample_year": st["first_main_year"], "n_fields": st["n_fields"]}
        out.append({
            "input": s(inp), "output": final, "metadata_fold": fold,
            "metadata_track": {"L": "L_novel", "L_nonnovel": "L_nonnovel_supplement", "P": "P_pool_screen"}[it["track"]],
            "metadata_label_basis": basis, "metadata_silver_gold_200": k in silver,
            "metadata_label_A": la, "metadata_label_B": lb, "metadata_label_adj": lj,
            "metadata_rationale_A": a.get("rationale"), "metadata_rationale_B": b.get("rationale"),
            "metadata_rationale_adj": j.get("rationale"),
            "metadata_confidence_A": a.get("confidence"), "metadata_confidence_B": b.get("confidence"),
            "metadata_confidence_adj": j.get("confidence"),
            "metadata_model_A": a.get("model"), "metadata_model_B": b.get("model"), "metadata_model_adj": j.get("model"),
            "metadata_label_date": a.get("date") or b.get("date"),
            "metadata_batch_cost_usd_A": a.get("batch_cost"), "metadata_batch_cost_usd_B": b.get("batch_cost"),
            "metadata_variant_cluster": sp["cluster"].get(k),
            "metadata_stratum": f"{band(st['n_occ']) if st['n_occ'] >= 3 else str(st['n_occ'])}|{form}|{st['macro_domain']}",
            "metadata_macro_domain": st["macro_domain"], "metadata_cvalue": st["cvalue"],
            "metadata_in_prescreen_or_pre2005": st["in_pre"], "metadata_audit_arm": bool(it.get("audit_arm", False)),
            "metadata_key_quality": key_quality(k),
            "metadata_human_checked": False,
        })
    return out


# ---------------------------------------------------------------- D3
def d3_pairs() -> list[dict]:
    V = json.loads((LAB / "variant_pairs.json").read_text())
    out = []
    for p in V["pairs"]:
        out.append({
            "input": s({"phrase_1": p["phrase_1"], "phrase_2": p["phrase_2"], "context_1": p["context_1"], "context_2": p["context_2"]}),
            "output": p["final_label"], "metadata_fold": p["fold"], "metadata_source": p["source"],
            "metadata_gold_source": p["gold_source"], "metadata_label_basis": p["label_basis"],
            "metadata_curated_label": p["curated_label"], "metadata_llm_label_A": p["llm_label_A"],
            "metadata_llm_label_B": p["llm_label_B"], "metadata_llm_label_adj": p["llm_label_adj"],
            "metadata_key_1": p["key_1"], "metadata_key_2": p["key_2"], "metadata_cross_split": p["cross_split"],
            "metadata_cluster_1": p["cluster_1"], "metadata_cluster_2": p["cluster_2"],
        })
    return out


# ---------------------------------------------------------------- D4
def d4a_phrases(limit: int | None = None) -> list[dict]:
    an = json.loads((LAB / "anchor_labels.json").read_text())
    by_phrase = {}
    for k, h in an["items"].items():
        by_phrase[(h["source"], h["source_doc_id"], h["phrase"], h["label"], h.get("entity_type"))] = (an["llm"].get("A", {}).get(k, {}), an["llm"].get("B", {}).get(k, {}))
    out = []
    for i, r in enumerate(jl(ROOT / "raw" / "anchor_phrases.jsonl")):
        if limit and i >= limit:
            break
        la, lb = by_phrase.pop((r["source"], r["source_doc_id"], r["phrase"], r["label"], r.get("entity_type")), ({}, {}))
        out.append({
            "input": s({"phrase": r["phrase"], "sentence_context": r["sentence_context"], "source_doc_id": r["source_doc_id"]}),
            "output": r["label"], "metadata_fold": r["fold"], "metadata_source": r["source"],
            "metadata_entity_type": r.get("entity_type"),
            "metadata_label_origin": "human annotation" if r["label"] != "NOT_ANNOTATED" else "spaCy noun chunk overlapping no human-annotated span",
            "metadata_in_llm_anchor_check": bool(la or lb),
            "metadata_llm_label_A": la.get("label"), "metadata_llm_label_B": lb.get("label"),
        })
    return out


def d4b_acronyms(limit: int | None = None) -> list[dict]:
    out = []
    for i, r in enumerate(jl(ROOT / "raw" / "anchor_acronyms.jsonl")):
        if limit and i >= limit:
            break
        gold = json.loads(r["output"])
        pairs = [{"short_form": a, "long_form": b} for a, b in schwartz_hearst(r["input"])]
        out.append({"input": r["input"], "output": s({"short_forms": gold["short_forms"], "long_forms": gold["long_forms"]}),
                    "metadata_fold": r["fold"], "metadata_sentence_id": r["id"],
                    "metadata_source": "amirveyseh/acronym_identification (SciAD)",
                    "metadata_schwartz_hearst_pred": pairs})
    return out


# ---------------------------------------------------------------- D5
def d5_pool() -> list[dict]:
    pool = json.loads((ROOT / "data_out" / "pool_early.json").read_text())
    out = []
    for p in pool:
        inp = {"key": p["key"], "surface_forms": p["surface_forms"], "acronym_short_forms": p["acronym_short_forms"],
               "snippets": p["snippets"]}
        row = {"input": s(inp), "output": p["link_status"], "metadata_fold": "heldout_phrase"}
        for k, v in p.items():
            if k in ("key", "surface_forms", "acronym_short_forms", "snippets", "link_status"):
                continue
            row[f"metadata_{k}"] = v
        row["metadata_key"] = p["key"]
        row["metadata_key_quality"] = key_quality(p["key"])
        out.append(row)
    return out


# ---------------------------------------------------------------- D6
def d6_works() -> list[dict]:
    return json.loads((ROOT / "subsample" / "heldout_works_rows.json").read_text())


# ---------------------------------------------------------------- extra candidates (staged only)
def midas_keyphrases(repo: str, files: list[tuple[str, str]], limit: int) -> list[dict]:
    out = []
    for fn, fold in files:
        p = TD / repo / fn
        if not p.exists():
            continue
        for r in jl(p):
            doc = r["document"] if isinstance(r["document"], list) else ast.literal_eval(r["document"])
            kp = r.get("extractive_keyphrases")
            kp = kp if isinstance(kp, list) else ast.literal_eval(kp or "[]")
            ab = r.get("abstractive_keyphrases")
            ab = ab if isinstance(ab, list) else ast.literal_eval(ab or "[]")
            out.append({"input": " ".join(doc)[:4000], "output": s({"extractive": kp, "abstractive": ab}),
                        "metadata_fold": fold, "metadata_doc_id": str(r.get("id") or r.get("paper_id") or r.get("document_id") or ""), "metadata_source": repo})
            if len(out) >= limit:
                return out
    return out


def kp20k(limit: int) -> list[dict]:
    out = []
    for r in jl(TD / "taln-ls2n__kp20k" / "test.json"):
        out.append({"input": (r["title"] + ". " + r["abstract"])[:4000], "output": s(r.get("keyphrases")),
                    "metadata_fold": "test", "metadata_doc_id": r["id"], "metadata_prmu": r.get("prmu"),
                    "metadata_source": "taln-ls2n/kp20k"})
        if len(out) >= limit:
            break
    return out


def vocab(kind: str, limit: int) -> list[dict]:
    if kind == "mesh":
        rows = json.loads((TD / "mesh" / "mesh_descriptors_2026.json").read_text())[:limit]
        return [{"input": r["heading"], "output": s(r["entry_terms"]), "metadata_fold": "vocab", "metadata_ui": r["ui"],
                 "metadata_tree_numbers": r["tree_numbers"]} for r in rows]
    rows = json.loads((TD / "openalex_snapshot" / f"{kind}.json").read_text())[:limit]
    return [{"input": r["display_name"] or "", "output": r["id"], "metadata_fold": "vocab",
             **{f"metadata_{k}": v for k, v in r.items() if k not in ("display_name", "id")}} for r in rows]


SELECTED = [
    ("openalex_stratified_corpus_2003_2016_with_prescreen_1995_2004", lambda: d1_corpus()),
    ("llm_labelled_candidate_phrases", d2_labels),
    ("variant_pairs", d3_pairs),
    ("external_human_anchors_semeval2017_scierc_phrases", lambda: d4a_phrases()),
    ("external_human_anchors_acronym_identification", lambda: d4b_acronyms()),
    ("survivorship_free_phrase_pool_early", d5_pool),
    ("heldout_phrase_works", d6_works),
]


def extra_candidates(n: int) -> list[tuple[str, callable]]:
    return [
        ("midas_inspec_keyphrases", lambda: midas_keyphrases("midas__inspec", [("train.jsonl", "train"), ("valid.jsonl", "validation"), ("test.jsonl", "test")], n)),
        ("midas_semeval2010_keyphrases", lambda: midas_keyphrases("midas__semeval2010", [("train.jsonl", "train"), ("test.jsonl", "test")], n)),
        ("midas_nus_keyphrases", lambda: midas_keyphrases("midas__nus", [("test.jsonl", "test")], n)),
        ("taln_ls2n_kp20k_test_keyphrases", lambda: kp20k(n)),
        ("openalex_keywords_vocabulary", lambda: vocab("keywords", n)),
        ("openalex_legacy_concepts_vocabulary", lambda: vocab("concepts", n)),
        ("nlm_mesh_2026_descriptors", lambda: vocab("mesh", n)),
    ]


def check_rows(name: str, rows: list[dict]) -> None:
    bad = 0
    for r in rows:
        if not isinstance(r.get("input"), str) or not isinstance(r.get("output"), str):
            bad += 1
        for k in r:
            if k not in ("input", "output") and not k.startswith("metadata_"):
                raise ValueError(f"{name}: illegal field {k}")
    if bad:
        raise ValueError(f"{name}: {bad} rows with non-string input/output")


@logger.catch(reraise=True)
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true", help="stage all 14 candidates (<=200 rows each) into temp/")
    ap.add_argument("--out", default=str(ROOT / "full_data_out.json"))
    a = ap.parse_args()
    if a.all:
        groups = []
        for name, fn in SELECTED[:1]:
            groups.append({"dataset": name, "examples": d1_corpus(limit=200)})
        for name, fn in SELECTED[1:]:
            rows = fn()[:200]
            groups.append({"dataset": name, "examples": rows})
        for name, fn in extra_candidates(200):
            groups.append({"dataset": name, "examples": fn()})
        for g in groups:
            check_rows(g["dataset"], g["examples"])
            logger.info(f"staged {g['dataset']}: {len(g['examples'])} rows")
        p = ROOT / "temp" / "all14_candidates_data_out.json"
        p.write_text(json.dumps({"metadata": {"note": "staging of 14 candidate datasets, <=200 rows each"}, "datasets": groups}, ensure_ascii=False))
        logger.info(f"wrote {p}")
        return
    groups = []
    for name, fn in SELECTED:
        rows = fn()
        check_rows(name, rows)
        logger.info(f"{name}: {len(rows)} examples")
        groups.append({"dataset": name, "examples": rows})
    meta = {
        "artifact": "gen_plan_dataset_4_idx4: labelled concept phrases and survivorship-free phrase pool",
        "created": "2026-09-28",
        "sources": "OpenAlex API (sampled works, counts, works), OpenAlex S3 snapshot (keywords, concepts), NLM MeSH 2026, "
                   "Wikidata API, HF: midas/semeval2017, zj88zj/SCIERC, amirveyseh/acronym_identification",
        "label_status": "D2/D3 LLM labels are LLM-adjudicated SILVER labels; no human has checked them (human_checked=false).",
        "sealed_file": "data_out/pool_outcomes_SEALED.json holds the full yearly counts and is deliberately NOT included here.",
    }
    Path(a.out).write_text(json.dumps({"metadata": meta, "datasets": groups}, ensure_ascii=False))
    logger.info(f"wrote {a.out}")


if __name__ == "__main__":
    main()
