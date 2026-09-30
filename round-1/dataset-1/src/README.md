# Concept pool 2005–2016: emerging scientific concepts with complete OpenAlex work lists

This repository builds an **outcome-blind pool of scientific concepts (noun phrases) first used between 2005 and 2016**, plus a small **stationary reference arm**. For each included concept it retrieves **every OpenAlex work from 2000 to 2024 that mentions it**, with all the fields a temporal knowledge-network study needs: primary-topic subfield, venue, full `referenced_works`, authorships, keywords, legacy concepts and an abstract flag. It also delivers subfield×year denominators, a venue-habitat table, pre-fixed concept and period splits, a Gate-A data-quality report and a recall audit.

It is the dataset artifact (iteration 1) for the research question *"how do emerging concepts acquire relations and diffuse across disciplines in an evolving knowledge network?"*. Downstream experiment artifacts build the concept–concept (co-occurrence) and concept–discipline networks from `works/` + `concept_work.parquet`.

> **Headline numbers** are in `logs/assemble_summary.json`, `context/quality_report.json` and `context/recall_audit.json`. They are summarised in the section [Results of this run](#results-of-this-run).

---

## 1. What was done (pipeline)

| Step | Script | Credits | What it does |
|---|---|---|---|
| 0 | `probes/` | ~30 | Live pricing probes on the run's OpenAlex key (free tier: 10,000 credits/day; list = 1, search = 10, singleton = 0). **Finding:** a list call with a `title_and_abstract.search` filter costs 10 credits, but **`group_by` with a search filter costs 1 credit**, and `group_by=ids.openalex` returns **200 work ids per credit**. |
| 1a | `download_snapshot.py` | 0 | OpenAlex S3 snapshot entity folders (keywords, concepts, topics, subfields, fields, domains, sources), plus the NLM MeSH 2026 descriptors. |
| 1b | `prefilter_tags.py` | ~650 | Outcome-blind pre-filter: per keyword and legacy concept, the count of works **tagged in 1995–2004** (`group_by=keywords.id` / `concepts.id`). |
| 1c | `build_vocab.py` | 0 | Normalise (lowercase, hyphen/space, strip parentheticals, singularise the last token), deduplicate across arms, apply the deterministic stop-list, apply the tag pre-filter (≤200 pre-2005 tags ≈ 25th percentile), then a seeded random order (seed 20260928). |
| 1d | `select_candidates.py` | 0 ($0.18 LLM) | Strictly linguistic LLM screen (specific term? named entity? multi-sense?) with `google/gemini-3.1-flash-lite`, walked in random order; no arm > 60 % of the draw. |
| 1e | `fetch_arxiv.py`, `mine_arxiv.py`, `select_arxiv.py` | 0 ($0.17 LLM) | **Failure-inclusive arXiv-mined arm** (plan Step 1(iv)). 1.48 M arXiv titles first submitted ≤ 2018 (HF `librarian-bots/arxiv-metadata-snapshot`). Keeps 2–4-gram noun-ish phrases whose first year with ≥ 3 titles is 2005–2016, with ≤ 2 earlier titles and ≥ 10 titles in their first 3 years. Fragments are removed, then an LLM well-formedness/genericity screen is applied. |
| 2 | `screen.py` | ~1,160 | **Outcome-blind first-use screening on OpenAlex** (Route A screening): one `group_by=publication_year` call per candidate over `title_and_abstract.search:"<phrase>"`, publication_year 1995–2018. The response is truncated to years ≤ F+2 **inside `truncate_and_classify` before anything is stored**; `meta.count` is never read. Rules: REJECT_PREEXISTING if Σ1995–2004 > 15 or any pre-2005 year ≥ 5. F = the first year 2005–2016 with n ≥ 5 (all earlier < 5, pre-F Σ ≤ 15). ELIGIBLE if V = n(F..F+2) ∈ [20, 300]. The burst flag is recorded. |
| 3 | `sample_frame.py` | 0 | **Freeze** before any post-F+2 data is fetched: `sample_frame_frozen.json`, with sha256 in `sample_frame_frozen.sha256`. Eligible main pool = 366 < 600, so every eligible concept is sampled (design prob = 1). Uniform key `u` (seed 20260929). Hydration order = ascending u, with 1 reference concept after every 8 main concepts. Fold = `sha1(concept_id) % 10 < 7 → screen`, else `heldout_concept`. Focal years are tagged (screen 2010–2014, held-out 2016–2018, ages 3–8; 2015 is a buffer). |
| 4–5 | `hydrate.py`, `hydrate_lib.py` | rest | **Full retrieval 2000–2024, never size-capped, strictly in u-order.** Route **A_openalex_native** (`group_by=ids.openalex`, 1 credit/200 ids) while credits lasted. After that, Route **B_s2_index**: Semantic Scholar bulk search (free) with an OR of quoted surface forms, every page, each hit mapped to OpenAlex through free singletons (DOI → MAG → PMID → arXiv DOI). S2 hits whose own title+abstract do not contain the phrase are skipped. All records are hydrated through **free OpenAlex singletons** (≤ 20 req/s) into `work_store/`. |
| 5b | `assemble.py` | 0 | Local surface-form verification (case-folded, accent-folded, hyphen/space-insensitive, optional plural), recomputed from every discovered candidate. Applies the **prefix rule**, writes D1–D5, the Gate-A quality report and a post-freeze LLM sense check on year-F titles (`sense_check_fail` flag). |
| 6a | `denominators.py` | ~200 | D4: subfield×year totals 2000–2024 in 4 variants. |
| 7 | `audit.py` | 0 | Recall audit on 30 stratified concepts: our verified yearly counts against Semantic Scholar index hits (an independent index for route-A concepts; for route-B concepts it measures mapping and verification loss). The OpenAlex-native comparison was impossible because the key had no credits left. |
| 8 | `validate.py` | 0 | Assertions: no screening record holds years > F+2; frame sha unchanged; 50 links re-verified; D3 ⊂ D2; fold ratio; ledger ≤ cap; no API key in outputs; no file ≥ 100 MB. |

Every OpenAlex call's credit cost is logged in `credit_ledger.jsonl`, from the response headers.

### Route decision (plan Step 0)
- P1 (`group_by=publication_year` with a search filter) cost **1 credit** → screening on OpenAlex (Route A screening).
- A paged list call with a search filter cost **10 credits** (probe `p1b`), so the plan's cursor-paging retrieval was unaffordable.
- `group_by=ids.openalex` (1 credit / 200 ids), discovered in probe `gb_ids.openalex`, replaced it for discovery.
- S2 unauthenticated throughput measured **0.24 req/s** (`probes/s2_throughput.txt`), too slow for S2-based screening. S2 was used only for discovery after the credits ran out.
- The key's free daily credits were exhausted key-wide at about 12:40 UTC; most of that spend came from sibling artifacts sharing the key. From then on every concept used Route B. `metadata_retrieval_route` records the route per concept.

### Deviations from the plan, and why
1. **Taxonomy arms had a 2.2 % eligibility yield** (3/134 screened OpenAlex keywords/legacy concepts/MeSH-new terms). Most taxonomy terms predate 2005, and pre-2005 classifier tag counts proved uninformative: *optogenetics* had 152 pre-2005 tagged works, *blockchain* 191. Screening was stopped after 134 candidates to save credits. The **arXiv-mined arm** (yield 36 %) supplies 363 of the 366 eligible concepts. **Consequence:** the main pool is heavily skewed to physics, astronomy, CS and maths (arXiv's coverage), and the arm balance (≤ 60 % per arm) is not met in the eligible pool. `vocab_arms` / `metadata_vocab_arm_tag` is recorded per concept.
2. **Origin field/subfield and the sense check were computed after freezing**, from the retrieved F..F+2 c-papers (outcome-blind information). With design probability 1 for every eligible concept, strata do not affect selection. `metadata_stratum` is descriptive, and `metadata_realized_inclusion_prob` is reported per (tercile × F-band) cell.
3. **Sense-check failures are flagged, not removed** (`metadata_flags` contains `sense_check_fail`), because hydration had already started when the check ran.
4. **The venue habitat uses all-years source topic counts only.** The pre-period (2000–2004) variant was not computed because the key's credits were exhausted.
5. **Realised N is below the plan's 400 floor.** Free singleton hydration was capped at 20 req/s and ran at about 14/s effective because of key-wide 429s. Heavy-tailed concept sizes (up to about 10k works) mean the u-order prefix stops well before 366. Remaining concepts are listed in `pending_hydration.json`. **Resume** on another day with `uv run hydrate.py --resume --deadline-min <m>` then `uv run assemble.py`; the prefix simply extends.
6. The reference arm is drawn from all screened candidates flagged `reference_eligible` (≥ 5 hits in every year 1998–2004, Σ ∈ [70, 700]), 60 sampled, not only from the dedicated reference screen.

## 2. Layout

| Path | What |
|---|---|
| `full_data_out/full_data_out_{1,2}.json` | **Standardised row-level export of the 5 selected datasets** (`uv run data.py`): `exp_sel_data_out` schema, one example per data row, grouped by dataset — `concept_pool_2005_2016` (206), `concept_work_links` (214,798), `openalex_works` (208,374), `subfield_year_totals` (25,195), `venue_habitat` (15,261). Split into < 90 MB parts; `mini_`/`preview_` variants per part. For compactness, `openalex_works` and `concept_work_links` inputs are JSON arrays whose column names are in the top-level `metadata.feature_names`. |
| `data.py` | uv inline script that builds the row-level export of the 5 selected datasets. |
| `data_out.json` | **D1 concept pool** (`exp_sel_data_out` schema; `input`/`output` are JSON strings). Also `full_/mini_/preview_data_out.json`. |
| `works/works_part_XX.parquet` | **D2 works table**: one row per unique work, all columns listed in section 3 (zstd). Kept on the run's volume; published if < 100 MB. |
| `concept_work.parquet` | **D3 concept-work links**: `concept_id, work_id, matched_form, match_evidence (oa_title / oa_abstract / oa_index_only / s2_only), year, dup_group`. |
| `context/subfield_year_totals.json` | **D4 denominators**: per year 2000–2024 × {all_types, typed_article_review_preprint_bookchapter, has_abstract, has_references} → subfield / field / domain totals. |
| `context/venue_habitat.json` | **D5 venue habitat**: per source seen in D2, subfield shares from source topic counts, dominant subfield/share, megajournal flag, `covered`, `uncovered_reason`. |
| `context/quality_report.json` | Gate-A report: traced shares (any / excl. year F / excl. F and top-5 cited), host traced share, reference/abstract/author coverage, primary-topic nulls, dup share, match-evidence mix, route counts, S2 mapping and unmapped shares, by origin-field group and year. |
| `context/recall_audit.json` | Recall audit (30 concepts) and the route-A verification pass rate. |
| `sample_frame_frozen.json` (+ `.sha256`) | Frozen frame: eligible concepts with F, V, screen counts ≤ F+2, u, folds, focal years, hydration order, reference arm. |
| `screen/` | `screen_results.jsonl` (every screened candidate, outcome-blind counts only) and `sense_check.jsonl`. |
| `retrieval/` | Per-concept discovery state (route, ids / S2 hits, links, mapping stats). |
| `vocab/` | Cleaned vocabulary, pre-2005 tag counts, LLM screens, arXiv-mined pool and candidates. |
| `taxonomy.json` | Domains, fields, subfields and topics (with subfield) from the snapshot. |
| `keywords_dict.json` | Index → OpenAlex keyword id for `keyword_idx` in D2. |
| `pending_hydration.json` | Concepts after the prefix, with the resume command. |
| `credit_ledger.jsonl` | Per-call credit ledger (ts, endpoint class, credits, key-wide remaining). |
| `probes/` | Pricing and throughput probe outputs. |
| `logs/` | Run logs, `assemble_summary.json`, `validation.json`. |
| `work_store/` | Local store of hydrated works, including title+abstract text used only for verification. **Kept on the run's volume, not published** (holds abstract text). |
| `temp/datasets/` | Small labelled resources for downstream semantic grounding (Inspec, SemEval-2017 Task 10, KP20k test, SciERC, WOS-46985, SciX UAT keywords); see section 5. |

## 3. D1 / D2 field reference
**D1 `input`**: `concept_id` (`c_` + sha1(phrase)[:12]), `phrase`, `surface_forms`, `acronyms_stored_not_used`, `vocab_arms`, `links` (openalex_keyword_id / legacy_concept_id / wikidata_qid / mesh_ui when present). Main arm: `F`, `screen_counts_by_year` (≤ F+2 only), `early_volume_V`, `origin_field`, `origin_subfield`, `early_oa_verified_count`. Reference arm: `screen_counts_by_year_1995_2004`.
**D1 `output`**: `oa_counts_by_year` (verified c-papers 2000–2024), `s2_counts_by_year` (route B only, raw S2 hits), `n_works`, `work_ids` (integer suffixes of W ids).
**D1 metadata**: `metadata_fold` (screen | heldout_concept | reference), `arm`, `stratum`, `F_band`, `volume_tercile`, `design_selection_prob`, `realized_inclusion_prob`, `sample_rank_u`, `focal_years_screen`, `focal_years_heldout`, `retrieval_route`, `s2_to_oa_mapping_rate`, `match_evidence_mix`, `hydration_complete`, `flags` (burst_start, sense_check_fail, large_concept, dup_groups_present, llm_multi_sense), `sense_dominant_share`, `covered_venue_share`, `vocab_arm_tag`.
**D2 columns**: `work_id, doi_present, s2_corpus_id, publication_year, publication_date, type, language, primary_topic_id, topic_score, subfield_id (e.g. 1702), field_id, domain_id, topics_top3, source_id, source_type, n_refs, refs (FULL referenced_works), refs_in_corpus, author_ids (-1 = no id), author_positions, institution_ids, keyword_idx, keyword_scores, concept_ids, concept_scores (legacy, score ≥ 0.2), has_abstract, abstract_n_tokens, cited_by_count (2026 snapshot), dup_group (same normalised title within a concept; flagged, not dropped), retrieved_at`.

## 4. How to run
```bash
uv venv .venv --python=3.12 && uv pip install --python=.venv/bin/python aiohttp orjson pandas pyarrow loguru wordfreq boto3 requests python-dotenv openai tenacity numpy scipy psutil pyyaml huggingface_hub
echo "OPENALEX_API_KEY=<your key>" > .env          # never committed (.gitignore)
uv run download_snapshot.py && curl -o mesh_raw/desc2026.gz https://nlmpubs.nlm.nih.gov/projects/mesh/MESH_FILES/xmlmesh/desc2026.gz
uv run prefilter_tags.py keywords && uv run prefilter_tags.py concepts   # ~650 credits
uv run build_vocab.py && uv run select_candidates.py 1000 150
uv run fetch_arxiv.py && uv run mine_arxiv.py && uv run select_arxiv.py
uv run screen.py vocab/candidates_main.jsonl main 134 && uv run screen.py vocab/arxiv_candidates.jsonl arxiv 950 && uv run screen.py vocab/candidates_ref.jsonl reference 80
uv run sample_frame.py                                                   # freeze (sha256 logged)
uv run denominators.py
uv run hydrate.py --deadline-min 180                                      # resumable: --resume
uv run assemble.py && uv run audit.py && uv run validate.py
```
Caches mean restarts never pay twice (`raw_cache/`, `work_store/`, `retrieval/`). The key is read only from `.env` and never written to outputs or logs.

## 5. Data sources and provenance
- **OpenAlex** (Priem et al. 2022), REST API retrieved 2026-09-28 and S3 snapshot `data/parquet/*`. OpenAlex ids can merge over time; `retrieved_at` is recorded. Reference-coverage caveats: Culbert et al., *Scientometrics* 130:2475–2492 (2025), arXiv:2401.16359. OpenAlex has fewer abstracts than WoS/Scopus, hence the abstract-availability columns and the `oa_index_only` / `s2_only` evidence classes.
- **NLM MeSH 2026** descriptors (`xmlmesh/desc2026.gz`); `DateIntroduced` 2005–2016 was used as the "new descriptor" arm.
- **arXiv metadata** via HF `librarian-bots/arxiv-metadata-snapshot` (a mirror of the Cornell/Kaggle arXiv OAI snapshot; 5.3k downloads), in the style of Science4Cast (Krenn et al. 2023).
- **Semantic Scholar** Graph API bulk search (Kinney et al. 2023), unauthenticated.
- `temp/datasets/` holds labelled resources for semantic grounding: `midas/inspec` (Hulth 2003), `midas/semeval2017` (ScienceIE, Augenstein et al. 2017), `taln-ls2n/kp20k` test split (Meng et al. 2017), `nsusemiehl/SciERC` (Luan et al. 2018), `river-martin/web-of-science-with-label-texts` (WOS-46985, Kowsari et al. 2017) and `adsabs/SciX_UAT_keywords` (UAT-tagged ADS abstracts). They are not used by this pipeline; they are candidates for training or evaluating a phrase-normalisation or grounding model downstream.

### Dataset selection (best 5)
An earlier version of `data.py` standardised 10 candidates: the 5 artifact datasets (D1–D5) plus 5 labelled grounding resources (Inspec, SemEval-2017 ScienceIE, KP20k test, WOS-46985, SciX UAT). All passed schema validation (441 MB total). The **best 5 for this artifact's objective are D1–D5**, which together support the evolving concept–concept and concept–discipline networks: concepts with outcome-blind frame metadata, verified concept→work links, per-work subfield/venue/reference/author/keyword attributes, subfield-year denominators, and venue-level classification. The labelled sets are off-target for this artifact. They are general keyphrase/discipline benchmarks, not temporal emergence data, and the phrase-normalisation/grounding step they could train is a downstream experiment. They stay in `temp/datasets/` as redownloadable resources.

## 6. Limitations
- **Vocabulary and field skew**: 363 of 366 eligible concepts come from the arXiv-mined arm, so origin fields are dominated by physics, astronomy, CS and maths. Health, social and life sciences are under-represented. The arXiv arm is failure-inclusive (it includes phrases that later died), which reduces survivorship bias relative to taxonomy vocabularies.
- **Mixed discovery routes**: native OpenAlex search ids (route A, complete for OpenAlex) versus S2 index hits mapped to OpenAlex (route B, which loses S2 records without a mappable id and OpenAlex works absent from S2). Compare within route or use `metadata_retrieval_route` as a covariate; see the recall audit.
- **Screening on OpenAlex, retrieval partly on S2**: F and V come from OpenAlex search counts, and `oa_counts_by_year` from verified c-papers, which can differ slightly from the screen counts.
- **Within-corpus co-authorship only**: newcomer definitions can use only authors seen in the pool.
- **Reference arm is sparse**; rho0 per subfield-year will likely need pooling at field level.
- `cited_by_count` is a 2026 snapshot; it is a proxy for canonical parents, never a label input.
- `raw_cache/` holds untruncated OpenAlex responses, including the screening calls. No selection code reads them except `screen.py`, which truncates to ≤ F+2 on receipt.

## 7. Restoring removed files
Entries marked `delete` in `.aii/manifest.yaml`:
- `snapshot_entities/` (redownloadable): `uv run download_snapshot.py` (anonymous `s3://openalex/data/parquet/<entity>`).
- `mesh_raw/` (redownloadable): `curl -o mesh_raw/desc2026.gz https://nlmpubs.nlm.nih.gov/projects/mesh/MESH_FILES/xmlmesh/desc2026.gz`.
- `arxiv_raw/` (redownloadable): `uv run fetch_arxiv.py` (HF `librarian-bots/arxiv-metadata-snapshot`).
- `.venv/` (redownloadable): `uv venv .venv --python=3.12 && uv pip install --python=.venv/bin/python -r pyproject.toml`.
- `__pycache__/` (regenerable): recreated automatically when any script runs.

`raw_cache/` and `temp/` fall under the auto-keep floor and stay in place. They are excluded from the published repository. To rebuild them, rerun the scripts in section 4 (`raw_cache/` costs OpenAlex credits) and `uv run temp/download_hf.py`.

## Results of this run
All numbers are from this run (retrieved 2026-09-28). Machine-readable versions: `logs/assemble_summary.json`, `context/quality_report.json`, `context/recall_audit.json`, `logs/validation.json`.

- **Screening:** 1,164 candidates screened (134 taxonomy/MeSH, 950 arXiv-mined, 80 reference-screen). 366 ELIGIBLE main concepts (363 arXiv-mined), all sampled with design prob = 1, plus 60 reference concepts drawn from 263 stationary-eligible candidates. The frame was frozen at 11:55 UTC, sha256 `80e3f244235b120be3e1201fdd8fb275ace4ba549f9a8884b96d2ea51c9a0c44`.
- **Included (u-order prefix):** 206 concepts = **184 main + 22 reference**. Realised inclusion ≈ 184/366 = 0.50 of the main frame, uniform in expectation across strata (per-cell values in `metadata_realized_inclusion_prob`). 220 concepts are pending (`pending_hydration.json`). **This is below the plan's floor of 400 main concepts**, because of the free-singleton hydration rate and the credit exhaustion described in section 1.
- **Folds (main):** screen = 123, heldout_concept = 61 (67/33). Non-empty focal years per F-band: {"2005-07": {"screen": 38, "heldout": 0}, "2008-11": {"screen": 76, "heldout": 76}, "2012-16": {"screen": 0, "heldout": 65}}. The period split is confounded with cohort: 2005-07 concepts have no held-out focal years and 2012-16 concepts have no screen focal years.
- **Origin-field groups (main):** {"F31:Physics and Astronomy": 82, "D3:Physical Sciences": 56, "F17:Computer Science": 45, "OTHER_small": 1}. The group `D3:Physical Sciences` pools the physical-science fields that have fewer than 30 concepts each (maths, engineering, materials, chemistry, …).
- **D2/D3:** 208,374 unique works (4 parquet parts, 73 MB) and 214,798 concept-work links. Routes: {"A_openalex_native": 26, "B_s2_index": 180}. Mean S2→OpenAlex mapping rate (route B) = 0.9278; the unmapped S2 share by year is in the quality report (about 10 % before 2016, falling to about 1 % in 2024).
- **Gate-A (main arm, descriptive):** share with references 0.8392; traced share (any earlier c-paper parent) 0.6699, excluding year-F parents 0.6493, also excluding the top-5 cited 0.608. **Host traced share (outside the origin subfield, excluding F) = 0.5518** over 41,861 host c-papers, above the 0.40 marker, which is not applied. Abstract share 0.7799, author-id coverage 0.9019, primary-topic nulls 0.0005, dup-group share 0.0539. Reference arm: traced share 0.5311.
- **Recall audit (30 concepts, compared with S2 index hits):** median ratio of our verified total to S2 hits = 0.84 (IQR 0.79–0.89); median Spearman of yearly series = 0.976; 1 concept below 0.5. Route-A verification pass rate (verified / OpenAlex search hits): median 0.975, p10 0.825. The OpenAlex-native comparison for route-B concepts could not run because no credits were left.
- **D5:** 15,261 venues, of which 4,292 are covered (dominant subfield share > 0.40, journal or conference, not a megajournal). Per-concept covered share is in `metadata_covered_venue_share`.
- **Flags:** sense_check_fail = 21 concepts (dominant sense < 70 % on year-F titles; kept but flagged), dup_groups_present = 154, burst_start = 1.
- **Cost:** OpenAlex credits spent by this artifact = 2,566 (ledger; cap 4,000/day). OpenRouter spend = $0.36 (gemini-3.1-flash-lite).
- **Kept artifacts on the run's volume (not all published):** `work_store/` (~430 MB, holds verification text; not published), `raw_cache/` (deleted after the round). Everything else in the layout table is small and published.

