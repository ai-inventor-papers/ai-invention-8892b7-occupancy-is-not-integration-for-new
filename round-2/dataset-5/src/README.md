# Concept pool, iteration 2: finish the concept downloads and fix the field labels

This repository **resumes and extends** the iteration-1 concept-pool build (`gen_art_dataset_1`). That build holds emerging
scientific concepts first used in 2005–2016, plus a stationary reference arm, with the complete OpenAlex work list for
each concept from 2000 to 2024. This round does four things:

* **P1 – hydration.** It downloads the works of the 220 frame concepts that were still pending, strictly in the frozen
  random `u`-order, so the included set stays an exact random prefix. It then re-assembles the pool in dataset_1's
  schema, adding a `hydration_batch` tag per concept, a `retrieval_batch` tag per work and all-age focal years.
* **P2 – nativeness profiles.** It buys **exact** OpenAlex counts: `primary_topic.subfield` × 5-year block for the legacy
  concept and keyword nodes that co-occur with pool concepts in *host* (non-origin) c-papers. Nodes are taken top-down
  by host co-occurrence weight.
* **P3 – venue habitat.** It builds a **citation-independent, journal-level ASJC habitat** from SCImago (Scopus)
  journal categories. A pre-period (2000–04), topic-derived fallback covers large unmatched venues and is labelled as
  not citation-independent.
* It carries forward dataset_1's subfield × year denominators unchanged.

No derived statistics are computed here. This is a data build; the analysis lives in the experiment artifacts.


> **Headline.** The **whole frozen frame is now hydrated**: K = **426 of 426** concepts (366 main + 60 reference). The
> included set is an exact prefix of `hydration_order` (`hyd/logs/validation.json`: `9_prefix_exact = true`) and nothing
> is pending. The corpus has **462,812 works** and **488,078 concept-work links**. P2 bought **5,488 exact profiles**
> (1,372 nodes × 4 blocks), covering **78.7 %** of host co-occurrence weight. The ASJC habitat covers **12.1 %** of
> c-paper links (11.4 % citation-independent). Credits spent: **7,237** of the 8,000 budget. OpenRouter: **$0.024**.

## Results of this run
All numbers were retrieved 2026-09-28 to 2026-09-29 (UTC). Machine-readable sources: `hyd/logs/assemble_summary.json`,
`hyd/logs/validation.json`, `hyd/context/quality_report.json`, `outputs/*.json`, `run_ledger.json`, `logs/run_notes.json`.

**P1 – hydration**
* Prefix K = 426/426: 366 main (fold screen 247, heldout_concept 119) + 60 reference. Pending: none. In iteration 1,
  K was 206 (184 main + 22 reference).
* Hydration batch: `iter1` = 211 concepts (the 206-concept prefix plus 5 completed beyond it in iteration 1),
  `iter2` = 215.
* Route by batch: iteration 1 A = 26, B = 185; iteration 2 A = 20, B = 195. Total **A = 46, B = 380**. Iteration 2 is
  still mostly Route B. The key was spent until 00:00 UTC, so 195 concepts were hydrated on free routes before the
  reset. The 20 Route-A concepts are the last ones in `u`-order. `metadata_retrieval_route` must be used as a covariate
  or for stratification.
* Works by fetch path (`retrieval_batch`): iter1 214,073; iter2_singleton 170,343; iter2_batch 78,396.
* Throughput: before the reset, about 16 free singleton calls/s (172,998 calls from 20:52 to 23:49 UTC). After it, the
  last 15 concepts, including *exoplanet* with 28,606 candidates, took 12 min on Route A plus the batch path.
* Batch equivalence (`probes/batch_equivalence.json`, `logs/batch_equivalence_attempt1.json`). Attempt 1 **failed**,
  1/200 mismatches: W1544516929 has 476 authors from the singleton but 100 from the list endpoint, which **truncates
  authorships at 100**. The fix: any work with ≥ 100 authorships from a list or batch call is re-fetched as a free
  singleton. Attempt 2 **passed**: 0/200 mismatches, abstracts 158/158 on both paths, so `abstract_inverted_index` is
  honoured. The one hydration process was stopped by PID and restarted with `--resume` to load the fix. Check: 0 of
  the 78,396 batch-stored works have ≥ 100 authorships, so no truncated record entered the data.
* Gate-A quality, main arm (`hyd/context/quality_report.md`): share with references 0.844, traced share 0.666 (0.646
  excluding year-F parents), **host traced share 0.544** over 90,406 host c-papers, abstract share 0.793, author-id
  coverage 0.898. Mean S2→OpenAlex mapping rate for Route B is 0.928.
* Origin-field groups (main): Physics and Astronomy 167, Computer Science 82, Materials Science 46, Engineering 36,
  Mathematics 32, other 3. The arXiv skew of iteration 1 remains (plan deviation 7).
* Flags: sense_check_fail 45 (the LLM post-freeze sense check, rerun only for new concepts; iteration-1 flags reused),
  dup_groups_present 314, llm_multi_sense 2, burst_start 2, large_concept 1.
* `metadata_focal_years_all` (every t with t − F in 3..8 and t ≤ 2019) is non-empty for all 366 main concepts. The
  older `focal_years_screen` / `focal_years_heldout` tags are kept and are **secondary**.
* Validation: no post-F+2 years in screening records; frame sha256 unchanged; 50/50 links re-verified; D3 ⊂ D2; no API
  key in outputs; prefix exact. No file is ≥ 100 MB: `hyd/work_store/` was re-sharded from 8 to 16 SQLite shards
  (`hyd/reshard_store.py`; 491,536 rows copied and counted; each shard about 55 MB).
  `6_ledger_le_cap = false` only because `validate.py` compares against iteration 1's default cap of 4,000 credits.
  This round's budget was 8,000, and 7,237 were spent.

**P2 – nativeness profiles**
* Final ranking on the 426-concept pool: 36,425 nodes, total host weight 2,388,779 over 191,252 (concept, host c-paper)
  pairs. Reaching 95 % would need 7,584 nodes, which does not fit the budget.
* Fetched: 1,372 nodes (coverage ranks 1–1,372, all four blocks each), 5,488 profiles. The run stopped at the P2 credit
  cap (5,488 credits) with 2,757 key-wide credits left. **Covered host weight = 0.787** overall; per-concept shares are
  in `nativeness_coverage`. Nodes were fetched in the order of an interim ranking (403-concept pool, kept as
  `p2/node_ranking_403prefix.parquet`). The coverage table uses the final ranking.
* **All nodes are legacy concepts.** Every co-occurring keyword matched a legacy concept by exact display name, which is
  consistent with the dossier's "keywords = legacy concepts" observation. No `keywords.id` calls were therefore needed.
* 2,073 of 5,488 profiles have more than 200 subfield groups (`truncated_top200 = true`). The missing tail is small:
  median 0.10 % of the total, p90 0.46 %, max 1.19 %, and 0.37 % of all counts. The exact `total` is always kept.
  Completing the tails would have cost about 2,000–4,000 more credits.

**P3 – venue habitat** (`outputs/venue_habitat_asjc.json`, `outputs/venue_coverage_report.json`)
* 22,970 venues seen in `openalex_works`. **COVERED: 2,929** (2,892 via SCImago, citation-independent; 37 via the
  pre-period fallback, NOT citation-independent).
* Uncovered reasons (venues / share of c-papers with a venue): multi_subfield 6,903 / 38.5 %; repository 1,160 / 16.3 %
  (mostly arXiv); general_only 1,563 / 11.3 %; no_match_small 10,007 / 7.3 %; megajournal 105 / 4.9 %; no_preperiod
  205 / 2.9 %; preperiod_share_le_0.40 87 / 2.3 %; unmapped_sjr_category 11 / 0.8 %. Covered venues hold 15.7 % of
  c-papers that have a venue.
* The covered share of **concept-work links** is 0.121 overall (0.114 citation-independent): main 0.121, reference
  0.122; Physics and Astronomy 0.172, Mathematics 0.133, Materials Science 0.113, Computer Science 0.107, Engineering
  0.101; Route A 0.115, Route B 0.123.
* The strict single-subfield ASJC rule therefore leaves most physics/CS c-papers uncovered: multi-category journals
  and arXiv dominate. `fractional_shares` (1/k) is the secondary variant for the 6,903 multi-subfield journals.
* Comparison only: iteration 1's topic-derived habitat (all-years source topics, not citation-independent) covered
  4,292 of 15,261 venues.
* SCImago→ASJC map: 310 categories; 306 mapped (291 exact in the ASJC table, 15 spelling variants by hand); 4 unmapped
  (newer than the table); 27 GENERAL.

**Credits (`run_ledger.json`)**: batch equivalence 4, P1 hydration 1,416, P2 profiles 5,488, P3 fallback 329; total
7,237. Key-wide remaining went from 9,999 after the reset to 2,757 at the end.

## Layout

| Path | What |
|---|---|
| `full_data_out/full_data_out_{1..5}.json` | **The 7 datasets** in the `exp_sel_data_out` schema, one example per data row, grouped by dataset, each part < 90 MB: `concept_pool_2005_2016` (426), `concept_work_links` (488,078), `openalex_works` (462,812), `subfield_year_totals` (25,195), `nativeness_profiles` (5,488), `nativeness_coverage` (427, with an `__OVERALL__` row), `venue_habitat_asjc` (22,970). `mini_data_out_N.json` / `preview_data_out_N.json` per part. |
| `mini_data_out.json`, `preview_data_out.json` | 3 examples per dataset (preview strings truncated to 200 chars). |
| `data.py` | Builds the export (`uv run data.py`). It reuses `hyd/data.py`'s dataset_1 builders. |
| `hyd/` | The resumed dataset_1 pipeline: `hydrate.py` / `hydrate_lib.py` / `common.py` (patched: batch path, DOI batch mapping, UTC rollover, `step` field in the ledger), `assemble.py` (patched: `hydration_batch`, `focal_years_all`, `retrieval_batch`), `validate.py` (plus the prefix-exactness check), `data.py`, `audit.py`, `denominators.py`, `download_snapshot.py` (now takes entity names). |
| `hyd/data_out.json` | D1 concept pool (dataset_1 schema). |
| `hyd/works/works_part_0{0..7}.parquet` | D2 works table with full `refs`, institutions and scores, plus `retrieval_batch` (163 MB in total, each part < 25 MB). |
| `hyd/concept_work.parquet` | D3 links. |
| `hyd/context/` | `subfield_year_totals.json` (D4, unchanged), `quality_report.{json,md}`, `recall_audit.json` (iteration 1, carried forward), `venue_habitat.json` (topic-derived, comparison only). |
| `hyd/sample_frame_frozen.json` (+ `.sha256`) | The frozen frame (unchanged). |
| `hyd/retrieval/` | Per-concept discovery state (route, ids / S2 hits, links, `hydration_batch`, timestamps). |
| `hyd/credit_ledger.jsonl` | Every credit-priced OpenAlex call this round, with `step`. `hyd/credit_ledger_iter1.jsonl` is iteration 1's ledger. |
| `hyd/probes/batch_equivalence.json`, `probes/` | Credit probe at start; equivalence check. |
| `hyd/work_store/` | SQLite store of hydrated works (16 shards `works_00..15.sqlite` of about 55 MB, routed by `work_id % 16`, plus `s2map.sqlite`; 0.88 GB), including the title+abstract text used only for verification. **Kept on the run's volume, not published** (it holds abstract text). |
| `p2_profiles.py`, `p2/` | P2 script; `p2/profiles.jsonl` (the raw profiles), `p2/node_ranking.parquet` (final ranking; ties broken by node id), `p2/node_ranking_403prefix.parquet` (the ranking the fetch order followed), `p2/concept_host_weights.json`. |
| `p3_venue_habitat.py`, `p3_coverage_report.py`, `outputs/` | P3 scripts; `outputs/venue_habitat_asjc.json`, `outputs/venue_coverage_report.json`, `outputs/nativeness_coverage.json`. |
| `scimago_raw/` | Zenodo 22954453 SJR panel and documentation, the ASJC code tables, `scimago_index.json` (derived). |
| `deps/gen_art_dataset_2/` | Copies of dataset_2's `taxonomy_subfields`, `concepts` and `keywords` parquet files. |
| `batch_equivalence.py`, `run_ledger.py`, `wait_reset.sh`, `tools/` | Equivalence check, ledger summary, the reset waiter, and monitoring helpers. |
| `run_ledger.json`, `logs/` | Credits and calls per step, run notes (mode, restart, throughput), logs. |

## How to run
See `reproducibility.md` for the exact command sequence. In short: `uv venv .venv --python=3.12 && uv pip install
--python=.venv/bin/python -r pyproject.toml`; put `OPENALEX_API_KEY` in `hyd/.env`; run `cd hyd &&
../.venv/bin/python download_snapshot.py sources`; then `hydrate.py --resume` → `batch_equivalence.py` → `assemble.py`
→ `validate.py` → `p3_venue_habitat.py scimago/build --fallback` → `p2_profiles.py rank/fetch/coverage` →
`p3_coverage_report.py` → `uv run data.py` → `run_ledger.py`. Every step is resumable: `retrieval/`, `work_store/`,
`p2/profiles.jsonl` and `raw_cache/` mean restarts never pay twice.

## Sources and licences
* **OpenAlex** (Priem et al. 2022), REST API 2026-09-28/29 and the S3 snapshot `sources` entity (CC0).
* **SCImago Journal & Country Rank** (data source: **Scopus**, Elsevier), annual journal-ranking exports 1999–2025, via
  the standardised panel in Zenodo record 22954453 (Dorado, Alayon, Cabacas, Concepcion & Sandig 2026, CC BY 4.0). If
  you reuse the categories, please credit SCImago.
* **ASJC codes**: `dhimmel/scopus` `data/asjc-codes.tsv` (from the Scopus source title list). Cross-checked against
  OpenAlex subfield ids (all 252 are ASJC codes).
* **Semantic Scholar** Graph API bulk search (Kinney et al. 2023), unauthenticated (Route B).
* Wang & Waltman (2016, *J. Informetrics* 10(2):347–364) on the lower accuracy of ASJC journal assignments, which is
  why only single-subfield journals are COVERED.

## Restoring removed files
Entries marked `delete` in `.aii/manifest.yaml` are removed after the round. To restore them:
* `.venv/`: `uv venv .venv --python=3.12 && uv pip install --python=.venv/bin/python -r pyproject.toml`
* `hyd/snapshot_entities/`: `cd hyd && ../.venv/bin/python download_snapshot.py sources` (anonymous
  `s3://openalex/data/parquet/sources`).
* `scimago_raw/sjr_category_panel.parquet` and the other `scimago_raw/` downloads: the `curl` commands in
  `reproducibility.md` §3 (Zenodo 22954453 / 4767023, dhimmel/scopus). Then `scimago_raw/scimago_index.json`:
  `.venv/bin/python p3_venue_habitat.py scimago`.
* `hyd/__pycache__/`: recreated automatically when Python imports the modules.

`restore.sh` runs the free restores (venv, snapshot, SCImago files).

`hyd/raw_cache/` (a gzip cache of raw OpenAlex list/group_by responses, many small files) is not deleted. It is
excluded from the published repository, and rebuilding it would cost OpenAlex credits. Everything downstream needs
from it is already in `hyd/retrieval/`, `p2/profiles.jsonl` and `outputs/`.

Kept on the run's volume but not in the published repository: `hyd/work_store/` (irreproducible without about 250k API
calls plus credits; holds abstract text).

## Pipeline of this round

| Step | Script | Credits | What it does |
|---|---|---|---|
| 0 | (shell) | 2 | Copies the iteration-1 state into `hyd/` and checks the frame hash (`logs/frame_check.log`). The credit probe (`probes/credit_probe_start.json`) found the key **spent for 2026-09-28** (remaining 0, reset in 3 h 09 min), so the round started in **credit-starved mode**. |
| 1 | `hyd/hydrate.py` (+ `hyd/hydrate_lib.py`, `hyd/common.py`) | P1 | ONE process, strictly in frozen `u`-order. Before the reset: Route **B** (Semantic Scholar bulk search, then free OpenAlex singletons for mapping and hydration). After 00:00 UTC, `OAClient._rollover` lifts the budget stop and new concepts use Route **A** (`group_by=ids.openalex` over `title_and_abstract.search`, 1 credit / 200 ids). Once the equivalence check passed, the **batch path** (`filter=ids.openalex:W1\|…\|W100`, 1 credit / 100 works) hydrates works. Ids a batch does not return (merged or deleted) fall back to singletons, which keep the `merged_into` handling. |
| 1b | `batch_equivalence.py` | 2 | 200 stored ids fetched both ways. `compact()` records must be identical apart from `retrieved_at` / `retrieval_batch`, and `abstract_inverted_index` must be honoured on the list endpoint. The flag goes to `hyd/probes/batch_equivalence.json`. |
| 2 | `p3_venue_habitat.py` | ≤ 800 | Journal-level ASJC habitat: SCImago categories joined on ISSN, a rule fixed in advance, and a labelled pre-period fallback. |
| 3 | `p2_profiles.py` | ≤ 3,700 | Host co-occurrence ranking (free), then exact `primary_topic.subfield` × block profiles, then the coverage table. |
| 4 | `hyd/assemble.py`, `hyd/validate.py`, `data.py` | 0 | Re-assembles D1–D3 in dataset_1's schema, validates, and exports the 7 datasets. |
| 6 | `run_ledger.py` | 0 | Summarises the per-call credit ledger (`hyd/credit_ledger.jsonl`, with a `step` field on every record) and throughput into `run_ledger.json`. |

### Deviations from the plan, and why
1. **Credit-starved start.** The key had 0 credits left for 2026-09-28 (iteration 1 and its siblings spent it). As the
   plan prescribes, P1 ran on Route B plus free singletons until 00:00 UTC, and every credit-priced call waited for the
   reset. The native route was not forced off with `--no-native`. Instead, `common.OAClient` gained a UTC-day rollover
   so the same process switched to Route A by itself after the reset. **Consequence:** in this round the
   `retrieval_route` depends on hydration *time*, not on concept properties, because `u` is random. Downstream work
   must use `metadata_retrieval_route` as a covariate or stratify on it.
2. **Batch hydration** (the plan's deviation (4)) was added to `hydrate_lib.hydrate_ids` and gated on the equivalence
   check. Every stored work carries `retrieval_batch` (`iter1` = stored in iteration 1, `iter2_singleton`,
   `iter2_batch`). Batch DOI mapping for Route B was **not** implemented. After the reset, new concepts use Route A,
   so it would only have helped the few Route-B concepts still in flight at midnight.
3. **SCImago source.** `scimagojr.com/journalrank.php?out=xls` returned HTTP 403 (a Cloudflare JavaScript challenge)
   even with a browser User-Agent, and the plan's gist fallback downloads from the same URL. The Zenodo 4767023
   "mirror" holds only the area/category *name* list. The categories therefore come from **Zenodo record 22954453**
   (Dorado et al. 2026, CC BY 4.0). It is a standardised panel of all 27 annual SCImago exports (1999–2025, retrieved
   2026-08-30, with per-file SHA-256 manifest), one row per journal × category × year, including ISSNs. Because every
   year is available, `sjr_year_used` is the year **closest to 2010 among all years**, not only among {2005, 2010, 2015,
   2019}. The union over the plan's 4 years is kept as metadata.
4. **Name → ASJC code map.** The category `<option>` list could not be scraped (same 403). Names were mapped to codes
   with the ASJC table from the Scopus source list (`dhimmel/scopus data/asjc-codes.tsv`, 334 codes; `plreyes/Scopus`
   holds the same list). 15 SCImago labels are spelling variants of table labels and were mapped by hand (`HAND_CODES`
   in `p3_venue_habitat.py`, e.g. *Neurology (clinical)* → 2728). **4 SCImago categories that are newer than the table
   stay unmapped**: *E-learning*, *Nanoscience and Nanotechnology*, *Social Work*, *Sports Science*. They are kept as
   specific pseudo-labels `SJR:<name>`. A journal whose only specific category is one of these is `UNCOVERED
   (unmapped_sjr_category)`.
5. **GENERAL codes.** The plan assumed the xx00 *General …* codes are absent from OpenAlex's 252 subfields. Some are
   present (e.g. 1100 *General Agricultural and Biological Sciences*). GENERAL is therefore defined **by label**:
   *General …*, *… (miscellaneous)* and *Multidisciplinary* (1000). The SCImago export in fact uses only the
   *(miscellaneous)* and *Multidisciplinary* forms.
6. **Snapshot sources.** The iteration-1 `snapshot_entities/sources` was incomplete (174,229 sources; e.g. *Physical
   Review B* was missing), so `sources` was re-downloaded from S3 (256,981 sources, 2026-09-28), as the plan's step
   0(f) prescribes.
7. **P4 (MeSH completion) was not run.** It is optional. The credit reset left about 2 h, and the critical path (P1
   Route A + batch, P2, P3 fallback, assembly, export) filled it. Reproducing dataset_3's works schema (MeSH fields,
   final rule) needs its `s04`/`s05` logic, which would not fit safely. dataset_3's exact non-PubMed yearly counts
   (`yearly_counts_nonpubmed_openalex_groupby`) remain the best available record of the gap.
8. **Recall audit.** It was not re-run for new concepts. `hyd/audit.py` compares against Semantic Scholar at about 1
   req/s, and a second S2 client would race the hydration process. Iteration 1's audit (30 concepts; median ratio 0.84,
   Spearman 0.976) is carried forward in `hyd/context/recall_audit.json`.
9. **`data.py`** is a plain script (`uv run data.py` with the workspace `pyproject.toml`). It reads the artifact's own
   outputs, not `temp/datasets/`, and writes `mini_*`/`preview_*` itself, following the same rules as the aii-json
   format script, which would also write an 85 MB duplicate of every part.

## Definitions that downstream steps rely on
* **Denominators.** `subfield_year_totals` is dataset_1's D4, copied unchanged. The **`all_types`** variant is the
  per-10^4 denominator: c-papers include every work type (conference papers, preprints, …), so the denominator must
  use the same frame. dataset_2's typed totals only weighted its background sample.
* **Nativeness profiles** (`nativeness_profiles`): `filter=concepts.id:C…` (or `keywords.id:<slug>`)
  `,publication_year:<block>&group_by=primary_topic.subfield.id:include_unknown&per_page=200`, with **no type filter**
  (the same all-types frame). `total` = `meta.count` (exact). `subfield_counts` keys are 4-digit ASJC = OpenAlex
  subfield ids, plus `unknown`. `truncated_top200` is true only if more than 200 groups exist and their sum falls short
  of the total. The filter matches concepts at **any score**, while co-occurrence edges use the stored score ≥ 0.2, so
  node totals are slightly inflated relative to edge weights (plan deviation 6). Level-0 legacy concepts (field labels)
  are included, and `level` flags them. Pool concepts need no profile calls, because their complete work lists are
  already exact.
* **Host co-occurrence weight**: W(X) = Σ over (pool concept c, host c-paper p of c) of 1[X ∈ nodes(p)]. A host
  c-paper has a known primary-topic subfield different from c's origin. Origin is the modal subfield of the F..F+2
  c-papers (main arm) or of the 2000–2004 c-papers (reference arm). Nodes are legacy concepts with stored score ≥ 0.2,
  plus keywords. A keyword whose display name equals a legacy concept's display name is merged into that concept.
* **Venue habitat rule** (fixed before any outcome was looked at): UNCOVERED if repository (OpenAlex type,
  `is_preprint_repository`, or the name matches arXiv/bioRxiv/medRxiv/SSRN/Zenodo/RePEc), or megajournal (iteration-1
  MEGA list or ASJC 1000 only). Otherwise GENERAL codes are dropped, and the venue is COVERED if exactly one specific
  code remains. None left → `general_only` (2-digit field recorded). Two or more → `multi_subfield`, with
  `fractional_shares` = 1/k as the secondary variant. SCImago-unmatched venues with ≥ 20 c-papers get one 2000–2004
  `group_by=primary_topic.subfield.id` call. They are covered if ≥ 20 works and the dominant share > 0.40, with
  `route=preperiod_groupby` and **`citation_independent=false`** (topics are citation clusters). Venues with fewer
  c-papers are `no_match_small`. `habitat_in_openalex_subfields=false` marks a covered ASJC code with no OpenAlex
  subfield counterpart (e.g. nursing sub-categories).
