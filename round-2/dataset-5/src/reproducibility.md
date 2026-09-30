# Reproducibility

These are the exact steps that were run to build this artifact (iteration 2, `gen_art_dataset_5`), in order. Every
path is relative to this folder.

## 1. Get the artifact
```bash
git clone <this repository>
cd <repository>/<this artifact folder>          # the folder that contains this file
```
This artifact resumes the iteration-1 artifact `gen_art_dataset_1` (id `art_94GEMUsgAmgK`). Its state was copied into
`hyd/` (code, frozen sample frame, per-concept retrieval state, work store, denominators). The large, unpublished
`hyd/work_store/` SQLite store (16 shards of about 55 MB each, 0.88 GB in total, holding title+abstract text used only for verification) stays on the run's
volume and is **not** in the repository. Without it, `hyd/hydrate.py --resume` rebuilds the store from OpenAlex at
the cost of API credits and time. Three small tables from the iteration-1 artifact `gen_art_dataset_2`
(`taxonomy_subfields`, `concepts`, `keywords` parquet) are copied into `deps/gen_art_dataset_2/`. Override that location
with `DATASET2_DATA_DIR`.

## 2. System and Python
* Built on Debian 12 (bookworm) in a container (the steps are identical on Ubuntu 22.04+), 4 CPU cores, no GPU (none needed), network access to api.openalex.org,
  api.semanticscholar.org, s3://openalex (anonymous), zenodo.org and raw.githubusercontent.com.
* Python 3.12 via `uv`:
```bash
uv venv .venv --python=3.12
uv pip install --python=.venv/bin/python -r pyproject.toml   # exact pins, see pyproject.toml
```
Installed (pinned in `pyproject.toml`): aiohttp 3.14.3, orjson, pandas, pyarrow, loguru, requests, python-dotenv, boto3,
numpy, openai, tenacity, pyyaml, scipy, psutil and their dependencies.

## 3. Credentials and downloads (names only)
* `hyd/.env` with `OPENALEX_API_KEY=<key>`: OpenAlex premium/free key (10,000 credits per UTC day). Never committed.
* `OPENROUTER_API_KEY`, `OPENROUTER_BASE_URL` (environment): used only by `hyd/assemble.py`'s post-freeze LLM sense
  check for newly included concepts (`google/gemini-3.1-flash-lite`, cost < $0.50).
* OpenAlex snapshot `sources` entity (anonymous S3): `cd hyd && ../.venv/bin/python download_snapshot.py sources`
  gives `hyd/snapshot_entities/sources/` (197 files, 163 MB, 256,981 sources, retrieved 2026-09-28).
* SCImago journal categories: the scimagojr.com export returned HTTP 403 (a Cloudflare challenge), so the
  standardised SJR panel from Zenodo record 22954453 was used (CC BY 4.0; data from SCImago Journal & Country Rank /
  Scopus):
```bash
mkdir -p scimago_raw && cd scimago_raw
for f in README.md data_dictionary.csv raw_file_manifest.csv LICENSE-DATA.txt sjr_category_panel.parquet; do
  curl -sSL -o "$f" "https://zenodo.org/api/records/22954453/files/$f/content"; done
curl -sSL -o asjc-codes_dhimmel.tsv https://raw.githubusercontent.com/dhimmel/scopus/main/data/asjc-codes.tsv
curl -sSL -o scimago_lookup_zenodo4767023.csv "https://zenodo.org/api/records/4767023/files/scimago_lookup.csv/content"
cd ..
```

## 4. Commands, in the order they were run
```bash
# STEP 0: frame integrity (must print the iteration-1 hash)
sha256sum hyd/sample_frame_frozen.json   # 80e3f244235b120be3e1201fdd8fb275ace4ba549f9a8884b96d2ea51c9a0c44 (logs/frame_check.log)
# credit probe -> probes/credit_probe_start.json (key-wide remaining was 0 at 20:50 UTC: CREDIT-STARVED MODE)

# STEP 1: P1 hydration, ONE process, strictly in frozen u-order (resumable)
cd hyd && AII_STEP=p1_hydration AII_ARTIFACT_CAP=3500 nohup ../.venv/bin/python hydrate.py --resume \
    --deadline-min 230 --workers 4 > ../logs/hydrate_iter2.out 2>&1 & echo $! > ../logs/hydrate.pid; cd ..
#   Credit calls re-enable themselves after the 00:00 UTC reset (common.OAClient._rollover): new concepts then use
#   Route A (group_by=ids.openalex over title_and_abstract.search) and the batch path (100 ids / 1 credit), which is
#   switched on only after the equivalence check below passes.

# STEP 2: P3 venue habitat (SCImago part free)
.venv/bin/python p3_venue_habitat.py scimago

# after 00:00 UTC (wait_reset.sh, started with nohup): batch-path equivalence check on 200 stored ids (2 credits)
AII_STEP=p1_batch_equivalence AII_ARTIFACT_CAP=20 .venv/bin/python batch_equivalence.py
#   attempt 1 (00:01 UTC) FAILED: the list endpoint truncates authorships at 100 -> fix in hydrate_lib.list_truncated,
#   then attempt 2 (00:02 UTC) PASSED. The one hydration process was stopped BY PID and restarted to load the fix:
kill <hydrate PID>
cd hyd && AII_STEP=p1_hydration AII_ARTIFACT_CAP=3500 nohup ../.venv/bin/python hydrate.py --resume \
    --deadline-min 42 --workers 4 > ../logs/hydrate_iter2.out 2>&1 & cd ..     # finished 00:14:56 UTC, K = 426

# STEP 3: P2 nativeness profiles. Interim ranking on the live retrieval state (403 concepts at 00:04 UTC), fetch
# started in parallel with P1 at <= 2 req/s. The client cap counts this process's own spend on top of the day's ledger
# at its start, and was raised to 5,500 because P1 finished far under budget.
P2_LINKS=retrieval .venv/bin/python p2_profiles.py rank
AII_STEP=p2_profiles nohup .venv/bin/python p2_profiles.py fetch --cap 5500 --rps 2 > logs/p2_fetch.out 2>&1 &

# STEP 4: assemble after the hydration PID exited, then validate
cd hyd && ../.venv/bin/python assemble.py && ../.venv/bin/python validate.py && cd ..
# P3 build + fallback. The cap must be (credits already in today's ledger + 800): a first run with cap 800 made 0 calls
AII_STEP=p3_fallback AII_ARTIFACT_CAP=$((LEDGER_TODAY + 800)) .venv/bin/python p3_venue_habitat.py build --fallback
.venv/bin/python p2_profiles.py rank          # final ranking on the assembled 426-concept pool (concept_work.parquet)
# (the P2 fetch stopped by itself at its cap at 00:50 UTC: 5,488 profiles = 1,372 nodes x 4 blocks)
.venv/bin/python p2_profiles.py coverage
.venv/bin/python p3_coverage_report.py
uv run data.py                       # -> full_data_out/full_data_out_{1..5}.json + mini/preview
.venv/bin/python run_ledger.py       # -> run_ledger.json
# afterwards: the 8 store shards were 117-119 MB (> GitHub's 100 MB), so the store was re-sharded to 16 shards
cd hyd && ../.venv/bin/python reshard_store.py && cd ..   # + N_SHARDS = 16 in hyd/hydrate_lib.py
.venv/bin/python p2_profiles.py rank && .venv/bin/python p2_profiles.py coverage && uv run data.py   # re-tested, same numbers
```
Seeds: the frame (u keys, seed 20260929) and folds are frozen from iteration 1. The equivalence-check id sample uses
seed 20260929. The LLM sense check uses temperature 0. Runtime: hydration is wall-clock bound (free singletons about
16/s; batch path about 100 works per call); everything else takes minutes.

## 5. Expected outputs
See README.md, section "Results of this run", for the numbers (included prefix K, works, links, profiles, venue
coverage, credits). The files are `full_data_out/full_data_out_N.json` (7 datasets, `exp_sel_data_out` schema),
`mini_data_out.json`, `preview_data_out.json`, `run_ledger.json`, `hyd/logs/validation.json`,
`hyd/logs/assemble_summary.json`, `outputs/venue_habitat_asjc.json`, `outputs/nativeness_coverage.json` and
`p2/profiles.jsonl`. OpenAlex is a live index, so re-running later gives slightly different counts (merged ids,
re-classified topics). `retrieved_utc` / `retrieved_at` fields record the dates.

Numbers a reader should get (this run): K = 426/426 concepts (366 main + 60 reference, prefix exact); 462,812 works;
488,078 concept-work links; routes A = 46 / B = 380; 5,488 nativeness profiles (1,372 nodes, 78.7 % of host
co-occurrence weight); 22,970 venues, of which 2,929 are covered (2,892 SCImago + 37 pre-period fallback); covered
share of concept-work links 0.121; 7,237 OpenAlex credits; $0.024 OpenRouter. In the paper they appear in the data
section: corpus size, route mix, the habitat and nativeness coverage caveats.
