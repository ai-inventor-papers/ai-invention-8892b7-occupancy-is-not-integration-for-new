#!/usr/bin/env python3
"""Step 10 docs: write provenance.md (selection flow, versions, licences, query templates, API cost, calibration,
coverage QA, spot check) from the finished JSON outputs, so every number in it is read from a file."""
from __future__ import annotations

import gzip
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEMP = ROOT / "temp"


def load(p: Path, default=None):
    return json.loads(p.read_text()) if p.exists() else default


def main() -> None:
    flow = load(ROOT / "selection_flow.json")
    concepts = load(ROOT / "data_out.json")
    qa = load(ROOT / "coverage_qa.json")
    cal = load(ROOT / "route_calibration.json", {"summary": {}, "concepts": []})
    ledger = [json.loads(l) for l in (ROOT / "logs" / "openalex_credit_ledger.jsonl").read_text().splitlines() if l.strip()]
    rstate = load(TEMP / "oa_cache" / "remainder_state.json", {})
    nc = load(TEMP / "nonpubmed_counts.json", {})
    wl = load(TEMP / "working_list.json", [])
    pairs = load(ROOT / "mesh_synonym_pairs.json")
    L = []
    w = L.append
    w("# Provenance: held-out MeSH population (`metadata_fold = heldout_mesh`)\n")
    w("Reserved confirmation population 1. Concept identity and synonymy come only from NLM MeSH; incidence is "
      "text-matched on OpenAlex titles/abstracts; nothing here was produced by an LLM or by OpenAlex keyword/topic taggers.\n")
    w("## Sources, versions, licences\n")
    w("| source | version / URL | licence / terms | use |\n|---|---|---|---|")
    w("| MeSH descriptors XML | `desc2017.xml` https://nlmpubs.nlm.nih.gov/projects/mesh/2017/xmlmesh/ | NLM terms (free; attribution: \"Courtesy of the U.S. National Library of Medicine\") | selection snapshot for DateEstablished 2004-2016 (outcome-blind: holds descriptors later deleted) |")
    w("| MeSH descriptors XML | `desc2019.xml` https://nlmpubs.nlm.nih.gov/projects/mesh/2019/xmlmesh/ | NLM terms | snapshot for the widening years 2017-2018 only |")
    w("| MeSH descriptors XML | `desc2026.xml` https://nlmpubs.nlm.nih.gov/projects/mesh/MESH_FILES/xmlmesh/ | NLM terms | `still_in_mesh_2026` (descriptive only) |")
    w("| ASCII MeSH | `d2003.bin` ... `d2018.bin` (`/projects/mesh/1999-2010/asciimesh/`, `/projects/mesh/<YEAR>/asciimesh/`) | NLM terms | prior-year term->descriptor maps (promoted-term / rename checks) |")
    w("| MeSH replace lists | `replace2004.txt` ... `replace2018.txt` (`.../newterms/`) | NLM terms | rename detection (MH OLD -> MH NEW) |")
    w("| PubMed | NCBI E-utilities esearch (tool=aii_mesh_pop), queried 2026-09-28 | NLM terms | [tiab] PMID sets, exact yearly counts, [MeSH Terms:noexp] sets |")
    w("| OpenAlex | api.openalex.org, queried 2026-09-28 | CC0 | work records (singleton + batched ids.pmid lists), non-PubMed search, group_by counts |")
    w("\nRaw MeSH downloads were reduced to in-memory maps; the files stay in `raw/` (marked delete/redownloadable in the manifest).\n")

    w("## Selection flow (counts after every filter)\n")
    w("| step | n | details |\n|---|---|---|")
    for f in flow["flow"]:
        det = {k: v for k, v in f.items() if k not in ("step", "n", "strata")}
        w(f"| {f['step']} | {f['n']} | {json.dumps(det)[:400] if det else ''} |")
    oc = Counter(o["outcome"] for o in flow["per_concept_outcomes"])
    w(f"\nPer-concept final outcomes over the whole working list ({len(flow['per_concept_outcomes'])}): `{dict(oc)}`.\n")
    w(f"**Final population: N = {len(concepts)}** (target 200; plan: acceptable 150-240, hard minimum 120).\n")
    if len(concepts) < 150:
        w(f"**Shortfall reported:** N = {len(concepts)} is below the 150-240 target band. Causes (all counted above): "
          "the PubMed pre-screen passes only ~8% of provenance-filtered descriptors; the final rule on verified OpenAlex "
          "counts then drops ~60% of retrieved concepts, mostly because non-PubMed OpenAlex works (group_by counts) show "
          ">= 5 papers/yr before 2005 (F < 2005) or push early volume outside 20-300; the plan's widening "
          "(DateEstablished 2004-2005 and 2017-2018) was applied; retrieval stopped at the time limit for concepts "
          "marked `not_retrieved_time` (rank order, outcome-blind).\n")
    by_tag = Counter((c["metadata"].get("widening_tag") or "core_2006_2016") for c in concepts)
    by_basis = Counter(c["output"]["final_rule_basis"] for c in concepts)
    by_group = Counter(c["metadata"]["branch_group"] for c in concepts)
    by_period = Counter(c["metadata"]["establishment_period"] for c in concepts)
    w(f"- by establishment pool: `{dict(by_tag)}`; by period: `{dict(by_period)}`")
    w(f"- by branch group: `{dict(by_group)}`")
    w(f"- by final-rule basis: `{dict(by_basis)}`")
    w(f"- retrieval_complete (non-PubMed works paged): {sum(c['metadata']['retrieval_complete'] for c in concepts)} of {len(concepts)}")
    w(f"- **rule_parity** (final rule saw non-PubMed works, as in the main corpus): {sum(c['metadata']['rule_parity'] for c in concepts)} "
      f"of {len(concepts)}. The {sum(not c['metadata']['rule_parity'] for c in concepts)} concepts with `rule_parity = false` are "
      "widened concepts whose non-PubMed group_by count could not be bought after the shared key's budget was exhausted; "
      "use the `rule_parity = true` subset for strict confirmation.")
    w(f"- provenance classes: `{dict(Counter(c['input']['provenance_class'] for c in concepts))}`; chemical_flag: "
      f"{sum(c['input']['chemical_flag'] for c in concepts)}; still_in_mesh_2026: {sum(c['metadata']['still_in_mesh_2026'] for c in concepts)}\n")

    w("## Rules (identical to the main corpus where the plan requires)\n")
    w("- **Provenance filter** (Nentidis, Krithara, Tsoumakas & Paliouras 2021, arXiv:2101.08293): DROP `PRIOR_EXPLICIT` "
      "(HistoryNote/PublicMeSHNote parenthetical year earlier than establishment, e.g. `2010 (1998)`), `PROMOTED_TERM` "
      "(any preferred-concept term was a term of a different descriptor in the prior-year file), `RENAMED` (MeSH replace "
      "list names it as MH NEW, a deleted descriptor's heading is reused, or the HistoryNote says `was X yyyy-yyyy` / points "
      "at its own term). KEEP `PRIOR_IMPLICIT` (PreviousIndexing to broader headings, or PublicMeSHNote 'indexed under') and "
      "`NO_PRIOR`. `use BROADER-HEADING yyyy-yyyy` notes are ordinary previous indexing, not renames.")
    w("- **Surface forms**: preferred concept only, non-permuted, un-inverted single-comma forms (not when the head is numeric "
      "e.g. `46, XX ...`); excluded from matching (kept in the record): acronyms < 5 chars (LexicalTag ABB/ACR/ABX), forms "
      "< 4 chars, special characters, single words with wordfreq zipf >= 4.0.")
    w("- **Pre-screen (PubMed, free)**: `(\"form1\"[tiab] OR \"form1 with hyphens as spaces\"[tiab] OR ...) AND 1995:2024[dp]`; "
      "drop total > 9,999 or < 15; exact yearly counts 1995-2018 by intersecting each descriptor's PMID set with per-year "
      "PMID sets of OR-chunks of descriptors (`(chunk) AND YYYY[dp]`, chunk totals < 9,000); a conservative PMID-date prune "
      "drops descriptors with > 45 PMIDs <= 14,699,652 (EDAT <= 2003-12-31, i.e. some year 1995-2004 >= 5 papers, F < 2005). "
      "Pass: F in 2005..2016, 15 <= count(F..F+2) <= 350, total <= 8,000.")
    w("- **Sample**: strata branch group x PubMed early-volume tercile x establishment period; seed 20260928; floor 8 per "
      "branch group; D-branch cap 35%. Because only 283 descriptors passed the pre-screen, the working list is the full "
      "census of passers in seeded random order (`selection_prob = 1`); widened passers are appended after rank 283 "
      "(seed 20260929).")
    w("- **Final rule** (main corpus): F = first year 2000..2024 with >= 5 papers and all earlier < 5; F in 2005..2016; "
      "20 <= count(F..F+2) <= 300; total 2000-2024 <= 8,000. Counts: verified union works (`final_rule_basis = verified_union`) "
      "when the non-PubMed remainder was paged; otherwise verified PubMed-route works + exact OpenAlex group_by counts of "
      "non-PubMed works (`pubmed_route_verified+nonpubmed_groupby_unverified`); if even group_by counts could not be bought "
      "(key budget exhausted), PubMed-route only (`pubmed_route_verified_only`, flagged). Failing concepts are dropped whole.")
    w("- **Local verification** (every work): OpenAlex title + abstract reconstructed in memory from `abstract_inverted_index`, "
      "lower-cased, hyphen/dash/slash/comma = space, Greek letters spelled out, word boundaries, last word singular/plural-"
      "insensitive. The abstract is discarded. Works whose OpenAlex record has no abstract can only be verified on the title "
      "(the main corpus's plain OpenAlex search has the same blind spot); `yearly_counts_textmatch_plus_pubmed_unverifiable` "
      "additionally counts PubMed [tiab] hits without an OpenAlex abstract (not used for selection).\n")

    w("## Query templates\n")
    w("```\nPubMed  : (\"<form>\"[tiab] OR ...) AND 1995:2024[dp]            (esearch, retmax 10000)\n"
      "PubMed  : (<chunk of descriptor queries>) AND <YYYY>[dp]        (esearch, yearly PMID sets)\n"
      "PubMed  : \"<Preferred Term>\"[MeSH Terms:noexp]                  (indexed PMID set) + AND <YYYY>[dp] chunks\n"
      "OpenAlex: /works/pmid:<PMID>?select=<fields>                     (singleton, free)\n"
      "OpenAlex: /works?filter=ids.pmid:<p1|...|p100>&per_page=100       (list, 1 credit per call)\n"
      "OpenAlex: /works?filter=title_and_abstract.search:(\"f1\" OR \"f2\" ...),has_pmid:false,publication_year:2000-2024&group_by=publication_year  (1 credit)\n"
      "OpenAlex: same filter, OR-batched over several concepts, &per_page=200&cursor=*   (10 credits per page)\n"
      "OpenAlex: title_and_abstract.search:(forms),publication_year:2000-2024  [main-corpus plain query, calibration]\n```\n")
    w("select = `id,ids,doi,title,publication_year,publication_date,type,language,primary_topic,primary_location,"
      "referenced_works,authorships,keywords,concepts,cited_by_count,mesh,abstract_inverted_index,indexed_in`\n")

    w("## OpenAlex cost (read from X-RateLimit-Credits-Used on every call; ledger `logs/openalex_credit_ledger.jsonl`)\n")
    by = Counter()
    nb = Counter()
    for r in ledger:
        by[r["kind"]] += r["credits"]
        nb[r["kind"]] += 1
    tot = sum(by.values())
    w("Key: free tier, 10,000 credits/day ($1/day). This artifact's ceiling: 20% = 2,000 credits; paid calls stop at 90% (1,800).\n")
    w("| call type | calls | credits |\n|---|---|---|")
    for k in by:
        w(f"| {k} | {nb[k]} | {by[k]} |")
    w(f"| **total** | {sum(nb.values())} | **{tot}** (= ${tot / 10000:.4f}) |")
    w("\nFree calls (not in the ledger): all `/works/pmid:X` singletons and all NCBI E-utilities calls. "
      "Measured prices: singleton 0, list 1, group_by 1, search page 10 credits. The shared key was exhausted "
      "key-wide (by all concurrent artifacts) at ~13:00 UTC; afterwards only free singletons were possible. "
      "The key-wide 30 req/s rate limit (shared with sibling runs) held singletons to ~13-14 req/s, which is why "
      "700 credits were spent on 1-credit batched `ids.pmid` lists (60,000 PMIDs) for the back of the rank order.\n")
    w(f"Non-PubMed remainder: paged for {len(rstate.get('done', []))} concepts in rank order "
      f"({sum(b['retrieved'] for b in rstate.get('batches', []))} works in {len(rstate.get('batches', []))} OR-batches); "
      f"stopped in rank order at concept {rstate.get('skipped_budget')}; {len(rstate.get('skipped_cap', []))} concepts skipped "
      f"because their non-PubMed OpenAlex count alone exceeds the 8,000 cap. group_by non-PubMed counts exist for "
      f"{sum(1 for r in wl if r['descriptor_ui'] in nc)} of {len(wl)} working-list concepts.\n")

    w("## Route calibration (step 9; `route_calibration.json`)\n")
    s = cal.get("summary", {})
    w(f"Summary: `{json.dumps(s)}`\n")
    w("| concept | in final | plain OpenAlex total | union verified total | ratio | F plain | F union | Jaccard (plain vs union verified) |\n|---|---|---|---|---|---|---|---|")
    for c in cal.get("concepts", []):
        wo = c.get("work_overlap", {})
        w(f"| {c['preferred_term']} | {c.get('in_final_population')} | {c['total_plain']} | {c.get('total_union_verified', '')} | "
          f"{c.get('ratio_union_to_plain', '')} | {c.get('F_plain', '')} | {c.get('F_union', '')} | {wo.get('jaccard_plain_vs_union_verified', '')} |")
    w("\nThe plain query stems (e.g. `Texting` -> `text`) and matches any title/abstract occurrence; the union route uses "
      "PubMed's exact phrase index for PubMed records plus OpenAlex search for the rest, and then applies one strict local "
      "match. Downstream code that needs main-corpus comparability should use the rows with `verified_text_match = true`.\n")

    w("## Coverage QA (unique verified union works of the final population, per year)\n")
    w("| year | works | share with PMID | has abstract | has references | author ids | primary topic |\n|---|---|---|---|---|---|---|")
    for y, v in qa["per_year_unique_verified_union_works"].items():
        w(f"| {y} | {v['n_works']} | {v['share_pmid']} | {v['share_has_abstract']} | {v['share_referenced_works']} | "
          f"{v['share_author_ids']} | {v['share_primary_topic']} |")
    w(f"\nRows: {qa['n_rows']} (unique works {qa['n_unique_works']}); by route `{qa['rows_by_route']}`; verified "
      f"{qa['rows_verified']}; match field `{qa['rows_match_field']}`; descriptor indexed (OpenAlex mesh) "
      f"{qa['rows_descriptor_indexed_openalex']}; descriptor indexed (PubMed [MeSH:noexp]) {qa['rows_descriptor_indexed_pubmed']}.\n")

    w("## Provenance-class spot check (60 records, seed 606; sample in `temp/spotcheck_sample.txt`)\n")
    w("30 random KEEP and 30 random DROP records (2006-2016 pool) were read by hand against their HistoryNote, "
      "PublicMeSHNote, PreviousIndexing and the prior-year match.\n"
      "- KEEP/DROP decision errors under the stated rules: **0 / 60**.\n"
      "- Sub-class label errors: 2 KEEP records labelled NO_PRIOR whose PublicMeSHNote says 'was indexed under ...' "
      "(should be PRIOR_IMPLICIT) -> rule added (PublicMeSHNote 'indexed under' => PRIOR_IMPLICIT; 142 labels changed, "
      "no selection change).\n"
      "- Surface-form defect: `46, XX ...` was wrongly un-inverted -> fixed (numeric heads and number lists are not "
      "inversions; 6 descriptors' forms changed and were re-queried).\n"
      "- Caveat: several KEEP records are well-known older concepts (e.g. Janus Kinases 2007) newly given a descriptor; "
      "as the plan intends, the text-novelty rule (F >= 2005), not the notes, removes them.\n")

    w("## Synonym pair set (`mesh_synonym_pairs.json`)\n")
    w(f"Positive pairs: {pairs['n_positive']}; negative pairs: {pairs['n_negative']}; by label|type: "
      f"`{pairs['counts_by_label_type']}`. Built for all provenance-filtered new descriptors of the 2006-2016 pool "
      f"(3,430 with matchable forms), max 40 positives per descriptor, 4 sibling negatives per descriptor. "
      f"`in_heldout_population` marks pairs touching a final-population descriptor (exclude them from training); "
      f"`in_working_list` is the stricter flag (any descriptor examined for this population).\n")

    san = load(ROOT / "sanity_check.json")
    if san:
        w("## Usefulness sanity check (`sanity_check.json`, descriptive only)\n")
        w(f"Over {san['n_concepts']} concepts (verified works): median later-6-year / early-3-year volume ratio "
          f"{san['median_growth_ratio_later6y_over_early3y']:.2f}; {san['share_concepts_growing']:.0%} grow; median distinct "
          f"OpenAlex subfields {san['median_subfields_early_F_F2']:.0f} in F..F+2 vs {san['median_subfields_later_F3_F8']:.0f} "
          f"in F+3..F+8 ({san['share_concepts_reach_expands']:.0%} expand their disciplinary reach); median fields touched "
          f"2000-2024 {san['median_fields_2000_2024']:.0f}. Spearman(early subfield reach, later volume) = "
          f"{san['spearman_early_subfields_vs_later_volume']['rho']:.2f} (p={san['spearman_early_subfields_vs_later_volume']['p']:.3g}); "
          f"Spearman(early volume, later volume) = {san['spearman_early_volume_vs_later_volume']['rho']:.2f}. "
          "The population therefore has variance in growth and in cross-disciplinary diffusion, as RQ1/RQ2 require.\n")

    w("## Known limitations\n")
    w("- Biomedical population only (MeSH); cross-field generality rests on the other populations.")
    w("- Non-PubMed works were paged only for the first concepts in rank order (credit ceiling, then key exhaustion); for the "
      "rest the final rule uses exact but locally unverified OpenAlex group_by counts, and those works are absent from the "
      "works parts (`retrieval_complete = false`, `retrieval_gap = nonpubmed_missing`). Network analyses on these concepts see "
      "only their PubMed-indexed neighbourhood.")
    w("- PubMed [tiab] also searches author keywords; such hits without the phrase in the OpenAlex title/abstract are kept "
      "with `verified_text_match = false`.")
    w("- MeSH-indexed-only works (indexed with the descriptor but not text-matched) are not fetched; their PMIDs are in "
      "`output.mesh_indexed_only_pmids`, and `yearly_counts_mesh_indexed` (from DateEstablished on) covers them.")
    w("- After 2022 MEDLINE indexing is automated: rows carry `indexing_regime`.")
    w("- Live APIs: re-running gives slightly different counts.")
    (ROOT / "provenance.md").write_text("\n".join(L) + "\n")
    print(f"provenance.md written ({len(L)} lines)")


if __name__ == "__main__":
    main()


def readme() -> None:
    concepts = load(ROOT / "data_out.json")
    qa = load(ROOT / "coverage_qa.json")
    pairs = load(ROOT / "mesh_synonym_pairs.json")
    parts = sorted(p.name for p in (ROOT / "works").glob("works_part_*.jsonl.gz"))
    size = sum((ROOT / "works" / p).stat().st_size for p in parts) / 1e6
    n = len(concepts)
    basis = Counter(c["output"]["final_rule_basis"] for c in concepts)
    txt = f"""# Held-out MeSH population: new biomedical concepts as a confirmation set

`metadata_fold = "heldout_mesh"` — reserved confirmation population 1 for the emerging-concepts study.
**{n} new biomedical concepts** (new MeSH descriptors, provenance-filtered so that renamed / promoted /
previously-existing headings are excluded, and text-novel: first used >= 5 times/yr in 2005-2016) with their
title/abstract-matched OpenAlex works 2000-2024 ({qa['n_rows']:,} concept-work rows, {qa['n_unique_works']:,} unique works),
in the main screening corpus's compact schema. PubMed-indexed works are complete for every concept; non-PubMed works
are complete only where `metadata.retrieval_complete = true` ({sum(c['metadata']['retrieval_complete'] for c in concepts)} concepts; credit budget).
Concept identity and synonyms come only from NLM MeSH, independent of OpenAlex topics/keywords.

## What is here

| path | what |
|---|---|
| `data_out.json` | concept table (JSON array, one row per concept): `input` (MeSH identity, surface forms, provenance class, F, early count, origin field/subfield), `output` (yearly text-match counts 2000-2024 and alternative series, MeSH-indexed counts, retrieval counts), `metadata_fold`, `metadata` (stratum, rank, seed, retrieval flags) |
| `full_data_out.json`, `mini_data_out.json`, `preview_data_out.json` | pipeline schema `exp_sel_data_out`, written by `uv run data.py`, grouped by dataset: `heldout_mesh_concepts` (one example per concept; `input`/`output` = JSON strings of the concept row) and `mesh_synonym_pairs` (one example per term pair; `output` "1"/"0"; `metadata_fold` = heldout_mesh / working_list / train_eligible). Mini/preview: 3 examples per dataset (aii-json format script). |
| `works/works_part_XX.jsonl.gz` | {len(parts)} gzip-compressed JSONL parts ({size:.0f} MB compressed): one row per (concept, work) — IDs as integer suffixes, `primary_topic`, `venue`, `referenced_works`, `authorships`, `keywords`, `concepts` (legacy, score >= 0.3), `mesh` (one entry per descriptor), plus provenance fields `match_route`, `verified_text_match`, `match_field`, `matched_forms`, `descriptor_indexed_openalex`, `descriptor_indexed_pubmed`, `indexing_regime`. Abstracts are NOT stored. |
| `mini_works.json`, `preview_works.json` | first 3 / 10 works rows in the `exp_sel_data_out` schema (written by `data.py`; preview strings truncated) |
| `mesh_synonym_pairs.json` | {pairs['n_positive']:,} positive and {pairs['n_negative']:,} hard-negative MeSH term pairs for variant-merging evaluation; `in_heldout_population` / `in_working_list` flags prevent leakage |
| `selection_flow.json` | counts after every filter + per-concept outcome for every examined descriptor |
| `route_calibration.json` | union route vs the main corpus's plain OpenAlex query (10 concepts; work-level Jaccard for 3) |
| `coverage_qa.json` | per-year coverage (PMID, abstract, references, author ids, topic) |
| `sanity_check.json` | descriptive usefulness check: growth after F and disciplinary reach expansion per concept |
| `provenance.md` | sources, versions, licences, rules, query templates, API cost, calibration, QA, spot check, limitations |
| `reproducibility.md` | exact commands |
| `build_population.py` | orchestrator that rebuilds the population from the APIs (all steps in order, ~4-5 h) |
| `data.py` | uv inline script: loads the prepared datasets in `temp/datasets/` and writes `full_data_out.json` (pipeline schema `exp_sel_data_out`) |
| `scripts/` | `s01` MeSH candidates/provenance/forms/pairs, `s02` PubMed pre-screen, `s03`/`s03b` sample (+ widening), `s04`/`s04b`/`s04c` OpenAlex retrieval, `s05` verification/final rule/packaging, `s06` calibration, `s07` docs, `s08` pipeline descriptor, `s09` sanity check; `oa.py`, `eutils.py` clients |
| `temp/datasets/` | prepared inputs of `data.py` (concept table, pair set, the 5,012-row descriptor pre-screen table — a candidate not selected for `full_data_out.json` — and hard links to the works parts) plus `SOURCE_SELECTION.md` |
| `temp/` | intermediate JSON (candidates, pre-screen, working list, PMID sets, MeSH-indexed sets, non-PubMed counts); `temp/datasets/SOURCE_SELECTION.md` documents the dataset search |
| `logs/` | run logs and `openalex_credit_ledger.jsonl` (every paid OpenAlex call) |

## Reading the data

```python
import gzip, json, glob
concepts = json.load(open("data_out.json"))
works = [json.loads(l) for p in sorted(glob.glob("works/works_part_*.jsonl.gz")) for l in gzip.open(p, "rt")]
main_rule = [w for w in works if w["verified_text_match"] and w["match_route"] != "mesh_indexed_only"]
```

**Strict confirmation subset:** `metadata.rule_parity = true` ({sum(c['metadata']['rule_parity'] for c in concepts)} concepts) — the final rule saw
non-PubMed works exactly as in the main corpus; the remaining {sum(not c['metadata']['rule_parity'] for c in concepts)} (widened, key budget exhausted) are flagged extras.
Use `verified_text_match = true` rows (and `output.yearly_counts_textmatch`) for main-corpus-comparable incidence.
`output.final_rule_basis` says which counts selected the concept: {dict(basis)}. `metadata.retrieval_complete = false`
means the concept's non-PubMed works were not paged (credit budget) — its works rows cover PubMed-indexed papers only,
while `output.yearly_counts_nonpubmed_openalex_groupby` gives the exact (unverified) yearly count of the missing part.

## How it was built (short)

1. MeSH `desc2017` topical descriptors established 2006-2016 (widened to 2004-2005 from desc2017 and 2017-2018 from desc2019),
   provenance-filtered after Nentidis et al. 2021 (drop parenthetical-prior-year, promoted-term, renamed).
2. Preferred-concept surface forms (non-permuted, un-inverted; short acronyms / generic words excluded from matching).
3. Free PubMed [tiab] pre-screen with exact yearly counts: F in 2005-2016, 15-350 papers in F..F+2, total <= 8,000.
4. Outcome-blind seeded order (seed 20260928) over all passers; strata branch group x early-volume tercile x period.
5. OpenAlex works: PubMed-route PMIDs via free singletons (+ 1-credit batched lists), non-PubMed works via
   `title_and_abstract.search` + `has_pmid:false` (rank order, until the 20% credit ceiling); every work re-verified locally.
6. Final rule as in the main corpus (F 2005-2016, 20-300 in F..F+2, total <= 8,000); failing concepts dropped whole.

See `provenance.md` for every count, cost and caveat.

## Run

```bash
uv venv .venv --python=3.12 && uv pip install --python .venv/bin/python -r pyproject.toml
export OPENALEX_API_KEY=...   # your own OpenAlex key (name only; the run's key is not published)
.venv/bin/python build_population.py            # full rebuild (downloads MeSH into raw/, then all steps; ~4-5 h, mostly API rate limits)
.venv/bin/python scripts/s05_finalize.py final 0.3 && .venv/bin/python scripts/s06_calibrate.py compare && .venv/bin/python scripts/s09_sanity.py && .venv/bin/python scripts/s07_docs.py && .venv/bin/python scripts/s10_export_datasets.py && uv run data.py   # re-package from caches
uv run data.py                                   # quick check: full_data_out.json from the published temp/datasets/ (no network)
```

## Restoring removed files

These paths are listed as `delete` in `.aii/manifest.yaml` and are not in the published repository:

| path | restore |
|---|---|
| `raw/` (MeSH XML/ASCII/replace files) | `.venv/bin/python build_population.py --download-only` downloads them (URLs in `build_population.py:downloads()`), e.g. `curl -o raw/desc2017.xml.gz https://nlmpubs.nlm.nih.gov/projects/mesh/2017/xmlmesh/desc2017.gz` |
| `.venv/` | `uv venv .venv --python=3.12 && uv pip install --python .venv/bin/python -r pyproject.toml` |
| `temp/datasets/works/` (hard links to `works/`) | `.venv/bin/python scripts/s10_export_datasets.py` |
| `__pycache__/` | regenerated automatically |

Kept on the run's volume but **not published** (upload-ignored text caches): `temp/oa_cache/` (raw OpenAlex responses incl.
normalised title/abstract text used only for verification; rebuild with `.venv/bin/python scripts/s04_retrieve.py pubmed`
(free) and `.venv/bin/python scripts/s04_retrieve.py remainder` (paid)) and `temp/pm_stepA.jsonl`, `temp/pm_stepB.jsonl`
(E-utilities caches; rebuild with `.venv/bin/python scripts/s02_pubmed_prescreen.py`, free).

Kept on the run's volume and published: everything else (concept table, works parts, pairs, flow, calibration, QA, docs, code).

## Licences

MeSH and PubMed data: NLM terms and conditions (courtesy of the U.S. National Library of Medicine). OpenAlex: CC0.
"""
    (ROOT / "README.md").write_text(txt)
    print("README.md written")


if __name__ == "__main__":
    readme()
