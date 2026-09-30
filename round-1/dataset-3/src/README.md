# Held-out MeSH population: new biomedical concepts as a confirmation set

`metadata_fold = "heldout_mesh"` — reserved confirmation population 1 for the emerging-concepts study.
**191 new biomedical concepts** (new MeSH descriptors, provenance-filtered so that renamed / promoted /
previously-existing headings are excluded, and text-novel: first used >= 5 times/yr in 2005-2016) with their
title/abstract-matched OpenAlex works 2000-2024 (122,645 concept-work rows, 117,253 unique works),
in the main screening corpus's compact schema. PubMed-indexed works are complete for every concept; non-PubMed works
are complete only where `metadata.retrieval_complete = true` (13 concepts; credit budget).
Concept identity and synonyms come only from NLM MeSH, independent of OpenAlex topics/keywords.

## What is here

| path | what |
|---|---|
| `data_out.json` | concept table (JSON array, one row per concept): `input` (MeSH identity, surface forms, provenance class, F, early count, origin field/subfield), `output` (yearly text-match counts 2000-2024 and alternative series, MeSH-indexed counts, retrieval counts), `metadata_fold`, `metadata` (stratum, rank, seed, retrieval flags) |
| `full_data_out.json`, `mini_data_out.json`, `preview_data_out.json` | pipeline schema `exp_sel_data_out`, written by `uv run data.py`, grouped by dataset: `heldout_mesh_concepts` (one example per concept; `input`/`output` = JSON strings of the concept row) and `mesh_synonym_pairs` (one example per term pair; `output` "1"/"0"; `metadata_fold` = heldout_mesh / working_list / train_eligible). Mini/preview: 3 examples per dataset (aii-json format script). |
| `works/works_part_XX.jsonl.gz` | 5 gzip-compressed JSONL parts (73 MB compressed): one row per (concept, work) — IDs as integer suffixes, `primary_topic`, `venue`, `referenced_works`, `authorships`, `keywords`, `concepts` (legacy, score >= 0.3), `mesh` (one entry per descriptor), plus provenance fields `match_route`, `verified_text_match`, `match_field`, `matched_forms`, `descriptor_indexed_openalex`, `descriptor_indexed_pubmed`, `indexing_regime`. Abstracts are NOT stored. |
| `mini_works.json`, `preview_works.json` | first 3 / 10 works rows in the `exp_sel_data_out` schema (written by `data.py`; preview strings truncated) |
| `mesh_synonym_pairs.json` | 9,477 positive and 13,620 hard-negative MeSH term pairs for variant-merging evaluation; `in_heldout_population` / `in_working_list` flags prevent leakage |
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

**Strict confirmation subset:** `metadata.rule_parity = true` (172 concepts) — the final rule saw
non-PubMed works exactly as in the main corpus; the remaining 19 (widened, key budget exhausted) are flagged extras.
Use `verified_text_match = true` rows (and `output.yearly_counts_textmatch`) for main-corpus-comparable incidence.
`output.final_rule_basis` says which counts selected the concept: {'verified_union': 13, 'pubmed_route_verified+nonpubmed_groupby_unverified': 159, 'pubmed_route_verified_only': 19}. `metadata.retrieval_complete = false`
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
