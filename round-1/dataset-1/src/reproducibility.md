# Reproducibility: concept pool 2005–2016 (dataset artifact gen_plan_dataset_1_idx1, iteration 1)

This file describes what was **actually run** on 2026-09-28 (UTC). Paths are relative to this folder.

## 1. Get the artifact
```bash
git clone <this repository URL>
cd <repository>/<this artifact folder>      # the folder containing this file
```
Files not in the repository: `work_store/` (hydrated-work store, ~430 MB, holds abstract text), `raw_cache/`, `snapshot_entities/`, `mesh_raw/`, `arxiv_raw/`, `temp/`, `.venv/`. All except `work_store/` can be rebuilt with the commands below. The store is rebuilt by re-running `hydrate.py`, which uses free OpenAlex singletons plus Semantic Scholar and takes hours.

## 2. System and Python
- Ubuntu/Debian x86-64 with `curl` and `git`. **CPU only**: 4 vCPU and 29 GB RAM (container limit) were used; no GPU is needed.
- Python **3.12.14**, environment managed with `uv`:
```bash
uv venv .venv --python=3.12
uv pip install --python=.venv/bin/python -r pyproject.toml     # every version pinned (uv pip freeze of the run's .venv)
```
Key versions: aiohttp 3.14.3, orjson 3.12.0, pandas 3.0.6, pyarrow 25.0.1, numpy 2.5.3, scipy 1.18.1, loguru 0.7.3, wordfreq 3.1.1, boto3 1.43.103, openai 3.19.2, huggingface-hub 1.33.0.

## 3. Credentials and downloads (names only)
- `OPENALEX_API_KEY`: write it to a local `.env` file (`OPENALEX_API_KEY=...`). The file is git-ignored and never logged. The run used a **free-tier** key (10,000 credits/UTC day) shared with sibling artifacts.
- `OPENROUTER_API_KEY`, `OPENROUTER_BASE_URL`: environment variables for the LLM screens (model `google/gemini-3.1-flash-lite`; total spend $0.36).
- `HF_TOKEN` (optional): for the Hugging Face parquet API.
- Downloads: OpenAlex S3 snapshot entities (anonymous), NLM MeSH `desc2026.gz`, arXiv metadata (HF `librarian-bots/arxiv-metadata-snapshot`).
- No user-uploaded inputs are used, and no other artifact's outputs are read.

## 4. Commands, in the order they were run (seed 20260928 throughout)
| # | Command | Runtime | OpenAlex credits |
|---|---|---|---|
| 0 | pricing/throughput probes with `curl` (outputs in `probes/`) | 5 min | ~30 |
| 1 | `uv run download_snapshot.py`; `curl -o mesh_raw/desc2026.gz https://nlmpubs.nlm.nih.gov/projects/mesh/MESH_FILES/xmlmesh/desc2026.gz` | 1 min | 0 |
| 2 | `uv run prefilter_tags.py keywords` and `uv run prefilter_tags.py concepts` (run in parallel) | 10 min | ~650 |
| 3 | `uv run denominators.py` | 1 min | ~200 |
| 4 | `uv run build_vocab.py` then `uv run select_candidates.py 1000 150` | 3 min | 0 |
| 5 | `uv run screen.py vocab/candidates_main.jsonl main` (stopped manually after 134 candidates: 2 % yield) | 1 min | 134 |
| 6 | `uv run fetch_arxiv.py`, `uv run mine_arxiv.py`, `uv run select_arxiv.py` | 6 min | 0 |
| 7 | `uv run screen.py vocab/arxiv_candidates.jsonl arxiv 150`, then `... arxiv 950`, plus `uv run screen.py vocab/candidates_ref.jsonl reference 80` | 5 min | ~1,030 |
| 8 | `uv run sample_frame.py` (FREEZE; sha256 `80e3f244…0c44` in `sample_frame_frozen.sha256`) | <1 min | 0 |
| 9 | `AII_SINGLETON_RPS=20 uv run hydrate.py --deadline-min 190 --workers 4`, restarted at 13:06 UTC (`--deadline-min 164 --workers 5`) after adding the S2 text pre-filter, stopped at 16:01 UTC. State resumes from `retrieval/` and `work_store/`. | ~4 h | ~190 (then 0: key exhausted) |
| 10 | `uv run assemble.py` | 2 min | 0 |
| 11 | `uv run audit.py` | 1 min | 0 |
| 12 | `uv run validate.py` | 10 min | 0 |
| 13 | `uv run data.py` (5 selected datasets → `full_data_out/`), then the aii-json format script per part; the root `mini_`/`preview_data_out.json` merge the parts | 1 min | 0 |

`temp/download_hf.py` and `temp/inspect_hf.py` were used only for the candidate-dataset survey (not selected).

**Non-determinism:** OpenAlex and Semantic Scholar are live indexes. Counts, ids (merges) and the key-wide credit race with sibling artifacts change over time. The per-concept route (`A_openalex_native` or `B_s2_index`) depended on when the shared key's credits ran out. How many concepts complete in a given time depends on the free-singleton rate limit (about 14 works/s was achieved).

## 5. Expected outputs and numbers
- `data_out.json`: 206 concepts (184 main + 22 reference); `full_data_out/full_data_out_{1,2}.json`: the 5 datasets as rows: concept_pool 206, concept_work_links 214,798, openalex_works 208,374, subfield_year_totals 25,195, venue_habitat 15,261.
- `works/works_part_00..03.parquet`: 208,374 works; `concept_work.parquet`: 214,798 links.
- `context/quality_report.md`: main-arm host traced share (excluding F) 0.552, traced share 0.670, abstract share 0.780.
- `context/recall_audit.json`: median ratio to S2 index 0.84, median yearly Spearman 0.976.
- `logs/validation.json`: all assertions true; ledger total 2,566 credits.
These numbers feed the paper's data section (corpus description, coverage table and Gate-A check).
