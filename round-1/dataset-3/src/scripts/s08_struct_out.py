#!/usr/bin/env python3
"""Write ./.terminal_claude_agent_struct_out.json (pipeline artifact descriptor) from the files actually on disk."""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    concepts = json.loads((ROOT / "data_out.json").read_text())
    qa = json.loads((ROOT / "coverage_qa.json").read_text())
    pairs = json.loads((ROOT / "mesh_synonym_pairs.json").read_text())
    cal = json.loads((ROOT / "route_calibration.json").read_text()).get("summary", {})
    parts = sorted(str(p.relative_to(ROOT)) for p in (ROOT / "works").glob("works_part_*.jsonl.gz"))
    for f in ["data.py", "build_population.py", "reproducibility.md", "full_data_out.json", "mini_data_out.json",
              "preview_data_out.json", "mini_works.json", "preview_works.json", *parts]:
        assert (ROOT / f).exists(), f"missing {f}"
    n = len(concepts)
    rc = sum(c["metadata"]["retrieval_complete"] for c in concepts)
    basis = dict(Counter(c["output"]["final_rule_basis"] for c in concepts))
    pools = dict(Counter(c["metadata"].get("widening_tag") or "2006-2016" for c in concepts))
    groups = dict(Counter(c["metadata"]["branch_group"] for c in concepts))
    summary = (
        f"Held-out MeSH confirmation population (metadata_fold='heldout_mesh'): {n} new biomedical concepts = new MeSH "
        f"descriptors (DateEstablished 2006-2016 from desc2017, widened per plan to 2004-2005 and 2017-2018; pools {pools}) "
        f"that survive a Nentidis-style provenance filter (drop parenthetical-prior-year, promoted-term, renamed), a free PubMed "
        f"[tiab] novelty pre-screen with exact yearly counts, and the main corpus's final rule on OpenAlex counts "
        f"(F=first year >=5 papers in 2005-2016, 20-300 papers in F..F+2, total 2000-2024 <= 8,000). Identity/synonyms come "
        f"only from MeSH preferred-concept terms. Branch groups {groups}. "
        f"full_data_out.json (exp_sel_data_out, built by data.py from temp/datasets/) holds the 2 selected datasets: "
        f"(1) heldout_mesh_concepts, one example per concept (plan-native array also in data_out.json) with input (descriptor UI, preferred term, surface_forms, "
        f"excluded_forms, acronyms, tree numbers, DateEstablished, notes, provenance_class, F, early_count_F_to_F2, "
        f"origin_field/subfield as OpenAlex ids) and output (yearly_counts_textmatch 2000-2024 over locally verified works, "
        f"yearly_counts_mesh_indexed, yearly_counts_nonpubmed_openalex_groupby, yearly_counts_final_rule, final_rule_basis "
        f"{basis}, retrieval counts, mesh_indexed_only_pmids); metadata has stratum, sample_rank, seed, retrieval_complete "
        f"({rc}/{n} have non-PubMed works paged; the rest have PubMed-indexed works only, because the shared OpenAlex key's "
        f"credits ran out), calibration_member, rule_parity ({sum(c['metadata']['rule_parity'] for c in concepts)}/{n} = strict "
        f"subset whose final rule saw non-PubMed works as in the main corpus; the other "
        f"{sum(not c['metadata']['rule_parity'] for c in concepts)} are flagged widened extras). "
        f"works/works_part_XX.jsonl.gz: {qa['n_rows']:,} (concept, work) rows "
        f"({qa['n_unique_works']:,} unique works) in the main-corpus compact schema (integer-suffix work/author/institution/"
        f"source/topic ids, publication_year/date, primary_topic, venue, referenced_works, authorships, keywords, concepts>=0.3, "
        f"deduplicated mesh, cited_by_count, has_abstract) plus match_route, verified_text_match, match_field, matched_forms, "
        f"descriptor_indexed_openalex/pubmed, indexing_regime; use verified_text_match=true for main-corpus-comparable counts. "
        f"(2) mesh_synonym_pairs (also mesh_synonym_pairs.json): {pairs['n_positive']:,} positive synonym/"
        f"acronym pairs and {pairs['n_negative']:,} hard negatives (narrower/related concept, sibling descriptor) over all "
        f"3,430 provenance-filtered 2006-2016 descriptors, output '1'/'0', metadata_fold heldout_mesh/working_list/train_eligible "
        f"to prevent leakage. Two further candidates were built and not selected: the 5,012-descriptor PubMed pre-screen "
        f"table (temp/datasets/mesh_prescreen_table.json) and the works rows (kept as the separate works/ file group). "
        f"route_calibration.json: union route vs plain OpenAlex title_and_abstract.search for 10 concepts "
        f"(median union/plain count ratio {cal.get('ratio_union_to_plain_median')}). selection_flow.json has counts after every "
        f"filter and per-concept outcomes; provenance.md documents versions, licences, query templates, OpenAlex credit ledger "
        f"({cal.get('artifact_openalex_credits_spent_total')} credits), coverage QA and a 60-record provenance spot check "
        f"(0 decision errors)."
    )
    out = {
        "title": "New MeSH medical terms as a held-out check set",
        "layman_summary": (f"A reserved test set of {n} medical concepts that NLM newly added to its MeSH vocabulary, "
                           f"each with the research papers that mention it, to check emergence findings on independent data."),
        "summary": summary[:4990],
        "out_expected_files": {
            "script": "data.py",
            "datasets": [
                {"full": ["full_data_out.json"], "mini": "mini_data_out.json", "preview": "preview_data_out.json"},
            ],
            "reproducibility": "reproducibility.md",
        },
        "upload_ignore_regexes": [r"(^|/)raw/", r"(^|/)temp/oa_cache/", r"(^|/)\.venv/", r"(^|/)__pycache__/",
                                  r"^temp/pm_step[AB]\.jsonl$", r"^temp/datasets/works/", r"(^|/)\.repl_agent\.ptylog$",
                                  r"(^|/)\.aii_claude_session\.json$"],
    }
    assert 12 <= len(out["title"]) <= 90 and 80 <= len(out["layman_summary"]) <= 250 and 500 <= len(out["summary"]) <= 5000
    (ROOT / ".terminal_claude_agent_struct_out.json").write_text(json.dumps(out, indent=1))
    print(f"struct out written: N={n}, summary {len(out['summary'])} chars")


if __name__ == "__main__":
    main()
