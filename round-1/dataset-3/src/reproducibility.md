# Reproducing the held-out MeSH population (artifact `gen_plan_dataset_3_idx3`)

This describes what was actually run on 2026-09-28 to build this folder, in order, including the incremental
re-runs. Every path below is relative to this artifact's folder.

## 1. Get the artifact

The workspace is published as one folder of the run's public GitHub repository.

```bash
git clone <repository-url>
cd <repository>/gen_art_dataset_3        # this artifact's folder (artifact id gen_plan_dataset_3_idx3)
```

The published folder already contains the finished outputs and the prepared inputs of `data.py`
(`temp/datasets/heldout_mesh_concepts.json`, `temp/datasets/mesh_synonym_pairs.json`). The quick check in
section 4a regenerates `full_data_out.json` from them without any network access. Caches that are not published
(`raw/`, `temp/oa_cache/`, `temp/pm_step*.jsonl`, `.venv/`) are rebuilt by the full pipeline in section 4b.

No other artifact's output and no user-uploaded file is read by this artifact.

## 2. System, Python and libraries

- OS: Debian 12 (bookworm) / Ubuntu container; system packages: `curl`, `git` (downloads / cloning only).
- Hardware actually used: 4 CPU cores (AMD EPYC), 29 GB RAM container limit, **no GPU**. Peak RAM < 6 GB.
- Python 3.12.14, uv 0.6.14.

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh              # if uv is not installed
uv venv .venv --python=3.12
uv pip install --python .venv/bin/python -r pyproject.toml   # exact pinned versions (uv pip freeze of the run's .venv)
```

Direct dependencies (pinned in `pyproject.toml` together with their transitive dependencies): aiohttp 3.14.3,
requests 2.34.2, lxml 6.1.3, loguru 0.7.3, tenacity 9.1.4, wordfreq 3.1.1, numpy 2.5.3, pandas 3.0.6,
orjson 3.12.0, pyyaml 6.0.3, scipy 1.18.1. `data.py` itself is a uv inline script with no third-party dependencies.

## 3. Downloads, environment variables, API keys (names only)

| name | needed for | notes |
|---|---|---|
| `OPENALEX_API_KEY` | every OpenAlex call (`scripts/oa.py`) | the run used a free-tier key (10,000 credits/day = $1/day) supplied privately by the user; it is NOT published - use your own key from openalex.org |
| `NCBI_API_KEY` (optional) | PubMed E-utilities | without it the scripts stay under 3 req/s (what the run did); with it 10 req/s |
| `AII_SINGLETON_RPS` (optional) | free OpenAlex `/works/pmid:X` lookups | the run used 18 (the key-wide limit was 30 req/s, shared with sibling runs) |
| `AII_TAG`, `AII_YEARS`, `AII_SNAPSHOT` | widening pass (4b) | set per command below |

Data downloads (free, NLM terms): `.venv/bin/python build_population.py --download-only` fetches into `raw/`
`desc2017.xml.gz`, `desc2019.xml.gz`, `desc2026.xml.gz` (MeSH descriptor XML), ASCII MeSH `d2003.bin`..`d2018.bin`
and `replace2004.txt`..`replace2018.txt` from https://nlmpubs.nlm.nih.gov/projects/mesh/ (~460 MB, ~10 s here).

## 4. Commands, in the order they were run

### 4a. Quick check (no network, seconds)

```bash
uv run data.py        # -> full_data_out.json (191 concept + 23,097 pair examples, 14.5 MB)
# mini / preview with the aii-json skill's format script (AI Inventor tooling), then renamed:
#   aii_json_format_mini_preview.py --format exp_sel_data_out --input full_data_out.json
#   mv full_full_data_out.json full_data_out.json
#   mv mini_full_data_out.json mini_data_out.json
#   mv preview_full_data_out.json preview_data_out.json
```

### 4b. Full rebuild (network; ~5 h wall clock in this run, dominated by API rate limits)

`build_population.py` runs these steps in this order. What was actually executed, with approximate runtimes:

```bash
export OPENALEX_API_KEY=...                                   # your own key
.venv/bin/python build_population.py --download-only         # ~10 s
# steps 1-4: MeSH candidates 2006-2016 (desc2017), provenance classes, surface forms, synonym pairs   ~30 s
.venv/bin/python scripts/s01_mesh_candidates.py
# step 5: PubMed [tiab] pre-screen with exact yearly counts (free; 3,430 descriptors)                  ~55 min
.venv/bin/python scripts/s02_pubmed_prescreen.py
#   (re-run once after fixing an un-inversion bug; it re-queries only descriptors whose query changed) ~3 min
# step 6: seeded working list (seed 20260928; all 283 passers) + [MeSH Terms:noexp] PMID sets          ~13 min
.venv/bin/python scripts/s03_sample_and_indexed.py
# widening (plan failure scenario: the 2006-2016 pool alone projected < 120 final concepts)
AII_TAG=w1 AII_YEARS=2004,2005 AII_SNAPSHOT=desc2017.xml.gz .venv/bin/python scripts/s01_mesh_candidates.py
AII_TAG=w2 AII_YEARS=2017,2018 AII_SNAPSHOT=desc2019.xml.gz .venv/bin/python scripts/s01_mesh_candidates.py
AII_TAG=w1 .venv/bin/python scripts/s02_pubmed_prescreen.py                                         # ~7 min
AII_TAG=w2 .venv/bin/python scripts/s02_pubmed_prescreen.py                                         # ~12 min
.venv/bin/python scripts/s03b_extend.py   # appends 173 widened passers after rank 283 (seed 20260929)    ~3 min
# step 9a: plain main-corpus OpenAlex query for 10 calibration concepts (group_by = 1 credit; 3 id pagings)
.venv/bin/python scripts/s06_calibrate.py fetch                                                      # ~1 min
# non-PubMed sizing: title_and_abstract.search + has_pmid:false, group_by=publication_year (1 credit each)
.venv/bin/python scripts/s04b_nonpubmed_counts.py        # run before and again after the widening      ~3 min
# step 7b: paid non-PubMed remainder in rank order until 90% of the 2,000-credit ceiling
.venv/bin/python scripts/s04_retrieve.py remainder       # interrupted once and resumed                  ~10 min
# step 7a: PubMed-route works - 1-credit batched ids.pmid lists from the back of the rank order (60,000 PMIDs)
.venv/bin/python scripts/s04c_pmid_list_batches.py 700                                               # ~6 min
#   ... and free singletons from the front (resumable; restarted 3x as the working list grew)
AII_SINGLETON_RPS=18 .venv/bin/python scripts/s04_retrieve.py pubmed                                 # ~4.2 h
# steps 7d-8, 10: verification, final rule, packaging (legacy concepts trimmed to score >= 0.3)
.venv/bin/python scripts/s05_finalize.py final 0.3                                                   # ~30 s
.venv/bin/python scripts/s06_calibrate.py compare        # step 9b calibration table                   ~30 s
.venv/bin/python scripts/s09_sanity.py                   # descriptive usefulness check
.venv/bin/python scripts/s07_docs.py                     # provenance.md + README.md from the outputs
.venv/bin/python scripts/s10_export_datasets.py          # prepares temp/datasets/ for data.py
uv run data.py                                           # -> full_data_out.json, then mini/preview as in 4a
.venv/bin/python scripts/s08_struct_out.py               # pipeline descriptor (.terminal_claude_agent_struct_out.json)
```

Seeds: 20260928 (working-list order and pair shuffling), 20260929 (widened passers), 606 (provenance spot-check
sample). Every network step caches to `temp/` and resumes where it stopped.

**Why a re-run will not be byte-identical.** PubMed and OpenAlex are live indexes, so counts drift. The OpenAlex
credit budget decides how many concepts get their non-PubMed works paged (`metadata.retrieval_complete`) and whether
non-PubMed group_by counts can be bought for every concept (`metadata.rule_parity`). In this run the shared key was
exhausted at ~13:00 UTC by all concurrent artifacts: this artifact spent 1,784 credits
(`logs/openalex_credit_ledger.jsonl`), 26 concepts got their remainder paged, and 413 of 456 working-list concepts
got non-PubMed counts. The exact PubMed PMID sets used are kept in `temp/pubmed_tiab_pmids.json`.

## 5. What you should get

| file | expected content |
|---|---|
| `full_data_out.json` | `heldout_mesh_concepts`: 191 examples; `mesh_synonym_pairs`: 23,097 examples (9,477 label "1", 13,620 label "0"; folds heldout_mesh 769 / working_list 1,216 / train_eligible 21,112) |
| `data_out.json` | the same 191 concepts as a plain JSON array (plan-native layout) |
| `works/works_part_01..05.jsonl.gz` | 122,645 concept-work rows, 117,253 unique works |
| `selection_flow.json`, `provenance.md` | counts after every filter; final outcomes: pass 191, fail F window 160, fail early volume 86, fail cap on non-PubMed counts 17, fail cap 2 |
| `route_calibration.json` | union vs plain OpenAlex query: median count ratio 0.86 (0.54-0.91); F agrees for 8/10 concepts, within 1 year for 10/10; work-level Jaccard 0.86-0.91 for the 3 smallest |
| `sanity_check.json` | median distinct subfields 4 in F..F+2 vs 12 in F+3..F+8; 92% of concepts expand their disciplinary reach |

Strict subset for confirmation analyses: `metadata.rule_parity = true` (172 of 191 concepts).
In the paper these numbers belong to the held-out confirmation population (the MeSH-grounded robustness check of the
emergence and diffusion indicators): population size and selection flow in its data section, the calibration in the
discussion of retrieval routes and limitations, and the pair set in the evaluation of concept normalisation
(variant merging). The paper is drafted by a later pipeline step, so exact section numbers are not fixed here.
