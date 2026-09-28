# Labelled concept phrases and a survivorship-free phrase pool (OpenAlex)

This is the semantic-grounding input for a study of **emerging scientific concepts as evolving knowledge-network
phenomena**. It produces seven datasets in the `exp_sel_data_out` schema (`{"datasets":[{"dataset","examples":[{input, output, metadata_*}]}]}`):

| # | dataset (group name) | rows | what it is |
|---|---|---|---|
| D1 | `openalex_stratified_corpus_2003_2016_with_prescreen_1995_2004` | 93,600 | Stratified (26 fields × year) sample of English OpenAlex articles/reviews with abstracts: 54,600 main (2003-2016) + 39,000 pre-period screen (1995-2004). Design weights stored. |
| D2 | `llm_labelled_candidate_phrases` | 4,599 | Noun-phrase / acronym candidates mined from D1, labelled CONCEPT / NOT_CONCEPT / TOO_GENERIC / VARIANT_OF by two cheap LLMs from different families, with a third-family adjudicator. 1,200 train / 300 test (split by variant cluster) + 3,099 `pool_screen`. |
| D3 | `variant_pairs` | 502 | SAME / DIFFERENT phrase pairs (281 / 221) for a variant merger. Curated positives come from Schwartz-Hearst, MeSH entry terms and Wikidata aliases. Hard negatives are acronym ambiguity and lexical near-duplicates. |
| D4a | `external_human_anchors_semeval2017_scierc_phrases` | 23,520 | **Human** annotations from SemEval-2017 Task 10 and SciERC, as phrase-level rows (annotated spans vs. noun chunks overlapping no annotation). Original splits are kept. |
| D4b | `external_human_anchors_acronym_identification` | 15,723 | **Human** acronym annotations from SciAD / acronym_identification (train + validation; the HF test split has hidden labels). Each row also carries our Schwartz-Hearst prediction. |
| D5 | `survivorship_free_phrase_pool_early` | 1,000 | Text-mined phrases first seen in the 2005-2016 sample. For each: yearly OpenAlex counts **up to F+2 only**, eligibility under the early-window anchor rule, inclusion weight, and links to OpenAlex keywords, legacy concepts, Wikidata and MeSH (UNLINKED phrases are kept). |
| D6 | `heldout_phrase_works` | 363 | All works (1990-2024) for an outcome-blind, pre-registered subsample of anchored pool phrases, with references, authors, institutions, fields and exact-match flags. |

`data_out/pool_outcomes_SEALED.json` holds the full 1980-2026 yearly counts of every pool phrase. It is **sealed**: nothing
that selects phrases reads it (`s8_works.py` uses it only to estimate API calls). Open it only at confirmation time.

> **Label status:** NO human has checked the D2/D3 LLM labels (`metadata_human_checked=false` on every row).
> Iteration 2 must call them **"LLM-adjudicated silver labels"** unless someone fills in `labelling/human_check_sheet.csv`
> (200 silver items, empty `human_label` column). *Nobody is scheduled to do this yet; this is flagged for the strategist.*

## Headline numbers

| quantity | value |
|---|---|
| Corpus | 93,600 works, all 26 fields, 624 strata, `sample=150` with a fixed seed per stratum |
| Distinct normalised candidate keys | 1,220,464 (35,782 acronym↔long-form pairs) |
| Track L (novel: first seen 2005-2016, ≥3 sample occurrences, absent pre-2005) | 7,879 available; 1,200 sampled + 300 non-novel frequent supplement |
| Track P (novel, ≥2 tokens or acronym, C-value ≥ q25) | 463,737 available; 3,099 screened (incl. a 100-key label-blind audit arm) |
| Final D2 labels, train (1,200) | CONCEPT 748 · NOT_CONCEPT 380 · TOO_GENERIC 72 |
| Final D2 labels, test (300) | CONCEPT 167 · NOT_CONCEPT 110 · TOO_GENERIC 23 (0 unresolved; every A≠B item adjudicated) |
| Leakage check | 1,489 variant clusters; **0** surface forms shared between train and test |

### Label quality (`labelling/quality.json`)

Models: A = `google/gemini-2.5-flash-lite`, B = `openai/gpt-4.1-nano`, adjudicator = `anthropic/claude-haiku-4.5`.
All ran at temperature 0 with JSON output on 2026-09-28, using the codebook in `labelling/codebook.md` (4 classes, 11 few-shot examples,
and an instruction to ignore later fame).

| check | A | B |
|---|---|---|
| **Human-anchored validity** (300 SemEval-2017/SciERC test phrases, 150 annotated / 150 not). Binary CONCEPT κ | **0.56** (acc 0.78, P 0.79, R 0.76) | 0.39 (acc 0.69, P 0.63, R 0.94) |
| per source κ: SemEval-2017 / SciERC | 0.51 / 0.61 | 0.37 / 0.40 |
| SciERC `Generic` spans labelled non-CONCEPT | 12/13 | 8/13 |
| vs adjudicator on `silver_gold_200` (test, stratified, adjudicator blind to A/B), 4-class κ | **0.63** (acc 0.79) | 0.19 (acc 0.55) |
| vs adjudicator, binary κ | 0.67 (acc 0.83) | 0.19 (acc 0.56) |
| curated variant pairs (50 audit pairs), agreement | 0.80 | 0.64 |

- A-B reliability is **low**: on Track L, 4-class κ = 0.26, binary κ = 0.27 and raw agreement 0.68; on Track P, κ = 0.28.
  Per-class one-vs-rest κ: CONCEPT 0.27, NOT_CONCEPT 0.29, TOO_GENERIC 0.07.
  The cause is systematic: B labels about 89% of Track-L items CONCEPT, against A's 59%. The confusion matrix is in `quality.json`.
  On the 411 A≠B Track-L items, the adjudicator sided with A 325 times and with B 52 times.
  Low-confidence shares are 0.9% (A) and 1.7% (B).
- Interpretation: A plus the adjudicator are the usable signal; B mainly acts as a high-recall screen. The only
  human-referenced number is the anchor check above, and it concerns a related construct (annotated keyphrase or
  entity span), not "emerging-concept-capable term".
- VARIANT_OF was almost never used (2 links), because key normalisation already merges most surface variants.
- Schwartz-Hearst extractor on acronym_identification validation (`labelling/sh_eval.json`): short-form precision 0.99,
  pair precision 0.95, pair recall 0.93 against parenthetical definitions. Recall over ALL gold short forms is 0.47, a lower bound by construction:
  the dataset also labels undefined acronyms.

### Survivorship-free pool (D5/D6): yield shortfall, stated plainly

The **early-window anchor rule** is implemented as planned.
- A phrase enters only through a sample occurrence inside its own window [F, F+2].
- F is the first year ≥ 1990 with ≥ 3 papers, from `title_and_abstract.search.exact` yearly counts.
- The novelty rule is pre-F papers ≤ max(2, 5% of n_early).
- The inclusion weight is 1/(1 − ∏(1 − rate(field, y))^{n_y}).
- The 100-key label-blind audit arm was counted first.

Of the 1,000 counted phrases (audit arm, then CONCEPT by A OR B in random order):

| rule | eligible (before anchor) | anchor_ok |
|---|---|---|
| strict (plan): F 2005-2016, n_early 20-300 | 3 | **1** |
| plan fallback: F 2004-2017, n_early ≤ 500 | 4 | 1 |
| exploratory: n_early ≥ 10 | 11 | 6 |
| exploratory: n_early ≥ 5 (`relaxed_low_volume`) | 21 | **11** |

Rejection reasons:
- never ≥ 3 papers/yr: 408
- F before 2005 with pre-F papers (existed before, only unseen in a ~0.1% sample): about 430
- other combinations: the rest

**Minimum-acceptable targets that are NOT met:**
- ≥150 pool-eligible phrases: 1 strict, 11 anchored across all tiers.
- works for ≥50 pool phrases: 10 phrases, 363 works.

The reasons are (a) **yield**: text-mined phrases seen once in a ~0.1% sample are overwhelmingly compositional or older
than 2005; and (b) **budget**: the OpenAlex key's $1/day credit is shared with sibling artifacts, which drew it to the
$0.25 reserve during this run. The only strict phrase ("green low carbon") was stopped by that reserve before its works
were fetched.

**What would fix it:**
- Keep screening Track P with `scripts/s7_counts.py --max-calls N`. It is resumable, reads the cache, and costs 1 credit per phrase.
- Draw a second, oversampled stratum of Track-P keys with ≥ 2 sample occurrences inside the early window. Its inclusion probability P(X≥2) is still computable, so the design stays survivorship-free.
- A strategist decision on the n_early lower bound: the yield curve above shows n_early ≥ 5-10 multiplies yield by 6-11×.

`eligibility_tier` and `relaxed` flags keep every tier separable.

Later-dead share, the one aggregate read from the sealed file (< 5 papers/yr averaged over 2020-2024; tiers without the anchor rule):
- strict tier: 0/3 (LLM arm)
- all tiers: audit arm 4/4 = 1.00, LLM arm 10/17 = 0.59

These numbers are far too small to support conclusions, but the direction matches the fame-leak concern: the LLM filter keeps fewer later-dead phrases.

Linking of the 1,000 pool phrases, by exact or normalised string only:
- UNLINKED: 929 (an upper bound; embedding linking is deferred to iteration 2)
- Wikidata: 52
- OpenAlex keyword: 12
- MeSH: 7

S8 search precision per phrase (share of works whose normalised title+abstract contains the exact surface) ranges from 0.61 to 1.0
(`subsample/per_phrase_download_report.json`). "cfh mutation" is flagged `low_precision`.

## Provenance and datasheet notes

**D1 corpus.**
- Query: `GET /works?filter=primary_topic.field.id:{F},publication_year:{Y},has_abstract:true,language:en,type:article|review&sample=150&seed={seed}&per_page=150&select=…`
  over fields 11-36 (26 fields), 2003-2016 (main) and 1995-2004 (prescreen), run 2026-09-28. The seed formula is in `scripts/s1_fetch_corpus.py`.
- N_stratum comes from one `group_by=primary_topic.field.id` call per year; design weight = N_stratum / n_sampled.
- Abstracts are rebuilt from `abstract_inverted_index`. From authorships, only author and institution ids are kept.
- `output` = primary field name. The corpus is a text source, not a labelled set.
- Abstract coverage of English article|review works in OpenAlex: 0.49 (1995) → 0.56 (2003) → 0.64 (2010) → 0.62 (2016)
  (`raw/strata.json`). The `has_abstract` group_by returns an empty `false` bucket, so coverage is measured with and without the filter.
- Departure from the direction: the strata are field × year, not subfield × year (budget). Subfield is stored for post-stratification.

**D2 candidates.**
- Extraction: spaCy `en_core_web_sm` noun chunks with determiners, numbers and a stop-modifier list stripped, and parenthesised material removed (1-6 tokens), plus our own Schwartz-Hearst implementation.
- Keys: NFKC, lowercase, hyphen/slash unification, Greek letters spelled out, British→American mini-map, singular head token. Acronyms map to their long-form key inside the defining document.
- C-value uses the log2(|a|+1) variant so unigrams are scored.
- Track-L sampling is stratified by frequency band × form × 5 macro-domains (fixed seed).
- **Deviation:** 300 non-novel frequent keys are added, so that TOO_GENERIC and the high-frequency bands appear in training.
- **Deviation:** Track-P C-value filter is `>= q25`, because 44% of keys tie exactly at q25 = log2 3.
- Batches: 20 keys, grouped by head token.
- `metadata_key_quality` flags 31 keys (0.7%) that are publisher boilerplate ("© 2013 wiley periodical") or begin with punctuation or non-Latin script. This is a known normaliser defect, left unchanged so the outputs stay reproducible.

**D3 pairs.**
- Sources: 90 Schwartz-Hearst pairs (≥ 2 defining documents); 90 MeSH heading↔entry-term pairs with both strings in the corpus; 60 Wikidata label↔alias pairs for legacy-concept-linked phrases; 90 distinct-expansion pairs of one short form; 170 near-duplicates (rapidfuzz token_set_ratio ≥ 85); 2 VARIANT_OF links.
- A and B judged all uncurated pairs plus 50 curated audit pairs; the adjudicator resolved the 53 disagreements.
- Folds follow the D2 cluster split. 33 cross-split pairs go to test.
- The acronym_identification HF release ships no acronym dictionary, so ambiguity negatives are mined from the corpus only.

**D4 licences, as the cards state them:**
- SemEval-2017 Task 10 (midas/semeval2017; Augenstein et al. 2017): the card states no licence field. The original task data is CC BY (ScienceDirect open access).
- SciERC (zj88zj/SCIERC mirror of Luan et al. 2018): no licence on the mirror; see the original release terms.
- acronym_identification (Veyseh et al. 2020): the HF card says MIT; the plan cited CC BY-NC-SA 4.0, so treat it as non-commercial to be safe.

**D5/D6 queries.**
- Counts: `filter=title_and_abstract.search.exact:"<surface>"&group_by=publication_year` (unstemmed; the API rejects `.no_stem`).
  - A zero result is retried once with the stemmed unquoted search and flagged `count_retry_flag`.
  - The audit arm also stores the stemmed-quoted vector in the sealed file.
  - Years 2025-2026 are partial (right-censored); the query date is in the sealed file.
- Works: cursor paging, per_page=200, `publication_year:1990-2024`. Phrases with < 50 works are OR-batched (≤ 10 per query) and assigned locally by exact match.
  Abstract text is used only for `exact_surface_in_text`, then dropped.
- Billing was verified on one call: `title_and_abstract.search*` filters are billed at list price ($0.0001).

**Known biases:**
- English only; `has_abstract` under-represents some publishers and older years.
- OpenAlex keywords are produced by its topic (citation-clustering) machinery, so they are used only for linking, never to define concepts.
- Topics and fields are retroactively tagged.
- Exact-phrase search misses plural and inflected forms; stemmed search adds false positives.
- LLM labellers may know which terms later became famous. The codebook forbids using this knowledge, and the audit arm measures it.
- D1 sample rates (~0.1-0.3% per field-year) make single occurrences a weak novelty signal (see the shortfall section).

## Spend

| resource | this artifact |
|---|---|
| OpenAlex API | 1,847 credits = **$0.185** (`logs/openalex_spend.csv`: every call with its X-RateLimit headers). Keywords and concepts came from the free S3 snapshot instead of ~1,300 list calls. |
| OpenRouter LLM | **$0.674**: A $0.167, B $0.157, adjudicator $0.351 (`logs/llm_spend.jsonl`: usage.cost per call) |

## Layout

```
reproducibility.md           step-by-step exact rebuild (seeds, models, dates)
data.py                      builds full_data_out.json (7 selected datasets); --all stages 14 candidates into temp/
full_data_out/               full_data_out_1..7.json (<=45 MB each, schema-valid parts) + mini_/preview_ per part
mini_data_out.json           3 rows per dataset (all 7); preview_data_out.json = same, strings truncated to 200 chars
data_out/pool_early.json     D5 source (early information only)
data_out/pool_outcomes_SEALED.json   full yearly counts 1980-2026 per pool phrase (SEALED)
data_out/vocab/*.json.gz     OpenAlex keywords (65,004) and legacy concepts (65,026; snapshot 2026-09-23), MeSH 2026 (31,110 descriptors)
labelling/codebook.md        labelling codebook (embedded in the prompt)
labelling/items.json         the 4,599 labelled items with snippets and stats
labelling/labels_AB.json, labels_adj.json, anchor_labels.json, variant_pairs.json, split.json   raw label outputs
labelling/quality.json       kappa, confusion matrices, human-anchor check; sh_eval.json = Schwartz-Hearst P/R
labelling/human_check_sheet.csv   200 silver items for a human to fill in (human_label empty)
labelling/selection_summary.json  Track L/P availability and sampling
subsample/selection_protocol.json pre-registered random priority order (written before downloading)
subsample/download_plan.json, per_phrase_download_report.json, heldout_works_rows.json
raw/strata.json              strata, N_stratum, design weights, seeds, abstract coverage
raw/anchor_*.jsonl           converted D4 rows
raw/corpus_works/            D1 source works, split into <=80 MB JSONL parts (scripts/rawio.py reads/writes them)
raw/*.pkl.gz                 gzip-compressed intermediates (candidates, docs_meta, key_stats); every file stays < 100 MB
scripts/                     pipeline (see "How to run"); oa_client.py = the single caching, budget-guarded OpenAlex client
logs/                        run logs, openalex_spend.csv, llm_spend.jsonl, summary.json (yield curve, spend, sealed aggregate)
cache/openalex_cache.tar.gz.part_00/01  all 1,800 paid OpenAlex responses (168 MB split into 90 MB parts; stays on the run volume, not in the published repo)
```

## How to run

```bash
./restore.sh                                   # venv + spaCy model + downloads + unpack the OpenAlex cache
export OPENALEX_API_KEY=...                    # never written to disk by any script
export OPENROUTER_BASE_URL=... OPENROUTER_API_KEY=...
.venv/bin/python scripts/s0_download_hf.py     # S0 HF raw files -> temp/datasets/
.venv/bin/python scripts/s0_convert_anchors.py # D4 rows + Schwartz-Hearst evaluation
.venv/bin/python scripts/s1_fetch_corpus.py    # S1 corpus (from cache: free)
.venv/bin/python scripts/s1b_coverage.py       # abstract coverage
.venv/bin/python scripts/s3_fetch_snapshot_vocab.py && .venv/bin/python scripts/s3_parse_mesh.py
.venv/bin/python scripts/s2_candidates.py      # ~10 min on 4 cores
.venv/bin/python scripts/s5_label.py select    # then: probe | label | split | adjudicate | adjudicate_extra | anchor | report
.venv/bin/python scripts/s5b_pairs.py && .venv/bin/python scripts/s5c_human_sheet.py
.venv/bin/python scripts/s7_counts.py --max-calls 1000   # resumable; raise N to screen more of Track P
.venv/bin/python scripts/s8_works.py --budget-credits 80 # --resume: fetched pages come from the cache
.venv/bin/python scripts/s9_summary.py
.venv/bin/python data.py && .venv/bin/python scripts/split_output.py
```
All LLM calls are cached under `cache/llm/` and all OpenAlex calls under `cache/openalex/`, so a rerun costs nothing.
**TODO (budget-limited, resumable):** `s7_counts.py --max-calls 3000` (remaining Track-P CONCEPT candidates) and
`s8_works.py --resume --budget-credits 1500` (works for "green low carbon" and newly eligible phrases).

Reading the split output:
```python
import glob, json, collections
ds = collections.defaultdict(list)
for f in sorted(glob.glob("full_data_out/full_data_out_*.json")):
    for g in json.load(open(f))["datasets"]:
        ds[g["dataset"]].extend(g["examples"])
```

## Restoring removed files

These paths are marked `delete` in `.aii/manifest.yaml`. Restore them all with `./restore.sh`, or one at a time:

| path | how to restore |
|---|---|
| `.venv/` | `uv venv .venv --python=3.12 && uv pip install --python .venv/bin/python aiohttp loguru pandas numpy scikit-learn rapidfuzz "spacy>=3.7" datasets openai tenacity pyyaml orjson requests pyarrow huggingface_hub && .venv/bin/python -m spacy download en_core_web_sm` |
| `temp/datasets/` | `.venv/bin/python scripts/s0_download_hf.py` (HF: midas/semeval2017, zj88zj/SCIERC, amirveyseh/acronym_identification, midas/inspec, midas/semeval2010, midas/nus, taln-ls2n/kp20k), then `curl -s https://openalex.s3.amazonaws.com/data/jsonl/{keywords,concepts}/manifest.json` into `temp/datasets/openalex_snapshot/`, then `.venv/bin/python scripts/s3_fetch_snapshot_vocab.py && .venv/bin/python scripts/s3_parse_mesh.py` |
| `raw/mesh/` | `curl -L -o raw/mesh/desc2026.gz https://nlmpubs.nlm.nih.gov/projects/mesh/MESH_FILES/xmlmesh/desc2026.gz` |
| `raw/candidates.pkl.gz`, `raw/docs_meta.pkl.gz` | `.venv/bin/python scripts/s2_candidates.py` (reads `raw/corpus_works/`; about 10 min) |
| `raw/key_stats.pkl.gz` | `.venv/bin/python scripts/s5_label.py select` (deterministic, seed 20260928) |
| `scripts/__pycache__/` | regenerated automatically by Python |

If `cache/openalex/` is ever missing, rebuild it from the kept split archive:
`cat cache/openalex_cache.tar.gz.part_* | tar -xzf - -C cache`.

Kept on the run's volume but **not** in the published repository: `cache/openalex_cache.tar.gz.part_*` (168 MB in two parts, paid API
responses) and the LLM/Wikidata caches under `cache/` (excluded from upload as content-addressed caches).
