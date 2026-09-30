# Reproducibility: G4 MeSH replication of the D2 grafting test (iteration 4, experiment 9)

This document describes what was actually run on 2026-09-29 (UTC), in the order it was run.

## 1. Get the artifact

This workspace is published as one folder of the run's public GitHub repository. The folder is named after the
workspace `gen_art_experiment_9` of iteration 4.

```bash
git clone <repository-url>
cd <repository>/<this-folder>          # the folder that holds method.py, src/, vendor/, results/
```

The input artifacts are published as sibling folders of the same repository (see §3). No user-uploaded file is used:
the run's `user_uploads` folder was empty.

## 2. System, Python and libraries

- **OS and hardware.** Ubuntu (Linux 6.8 container) on CPU only: 4 cores (cgroup affinity), no GPU. Peak RAM in
  practice was under 4 GB; `method.py` caps the address space at 26 GB. BLAS threads are pinned to 1 inside
  `method.py`.
- **System packages.** None beyond `curl`/`git`, plus `uv` (installed with `curl -LsSf https://astral.sh/uv/install.sh | sh`).
- **Python.** 3.12.
- **Libraries.** `pyproject.toml` pins all 73 installed distributions exactly. It was checked against
  `uv pip freeze --python .venv/bin/python`, saved in `logs/pip_freeze.txt`; the venv has no pip. Key versions:
  numpy 2.5.3, pandas 3.0.6, scipy 1.18.1, pyfixest 0.60.0, statsmodels 0.15.0, pyarrow 25.0.1, orjson 3.12.0,
  loguru 0.7.3, matplotlib 3.11.2, requests 2.34.2, tenacity 9.1.4, pytest 9.1.1.

```bash
uv venv .venv --python=3.12
uv pip install --python .venv/bin/python -r pyproject.toml
```

## 3. Inputs, environment variables and keys (names only)

Every input is read through ONE environment variable. Its default is the run layout (`<loop>/iter_N/gen_art/<folder>`,
resolved relative to this file in `src/common.py` and `vendor/config.py`). In a clone of the repository, point each
variable at the sibling folder named below:

| variable | sibling folder (artifact) | files read |
|---|---|---|
| `AII_MESH_DIR` | `gen_art_dataset_3` of iteration 1 (**art_HGiVAYhqO-6q**, MeSH population) | `data_out.json`, `works/works_part_0{1..5}.jsonl.gz` |
| `AII_DATASET5_DIR` | `gen_art_dataset_5` of iteration 2 (**art_eR1Z7fMlOcxs**) | `hyd/works/*.parquet`, `hyd/concept_work.parquet`, `hyd/data_out.json`, `hyd/keywords_dict.json`, `hyd/taxonomy.json`, `hyd/context/subfield_year_totals.json`, `p2/profiles.jsonl`, `outputs/nativeness_coverage.json`, `deps/gen_art_dataset_2/{concepts,keywords}.parquet` |
| `AII_DATASET1_DIR` | `gen_art_dataset_1` of iteration 1 (**art_94GEMUsgAmgK**) | `data_out.json` (gate 1 concept list) |
| `AII_EXP7_DIR` | `gen_art_experiment_7` of iteration 3 (**art_2Cd2JJypeGuA**, D2 screen) | `results/main_population_hydrated.json` (+ `.sha256`); its `src/*.py` are vendored unchanged in `vendor/` |
| `AII_EXP3_DIR` | `gen_art_experiment_3` of iteration 2 | `results/concept_subfield/rs_distance.parquet` |
| `AII_EXP1_DIR` | `gen_art_experiment_1` of iteration 2 | `results/test_population.json` |
| `AII_EXP2_DIR` | `gen_art_experiment_2` of iteration 2 | `results/gate_a/graft_fallback_events.csv` (gate 1 row-level target) |
| `AII_BG_DIR` | `gen_art_dataset_2/data` of iteration 1 | `bg_work_sample.parquet` |

Alternatively, set `AII_DEPS_ROOT` to a folder containing `iter_1/`, `iter_2/` and `iter_3/` in the run layout.

**API key.**
- `OPENALEX_API_KEY` is needed only for the paid OpenAlex calls: coverage, the nativeness fetch and topic hydration.
  The code never writes it to disk.
- Every paid response is cached in the repository: `cache/coverage_groupby.json`,
  `results/nativeness/profiles_fetched.jsonl` and `results/topic_hydration.jsonl`. A rerun from a clone therefore
  needs no key and spends no credits.
- `AII_POLITE_CONTACT` (optional) is sent as OpenAlex `mailto`.
- No LLM or OpenRouter key is used ($0).

## 4. Commands actually run, in order

Seeds: 20260929 everywhere. Other seeds:
- mini-set selection: 42;
- placebo draws: 20260929+1000+i;
- outcome shuffles: 20260929+5000+i;
- power reps: 20260929+30000+1000·cell+rep;
- placebo-host draw: `default_rng([20260929, event_id])`.

| # | command | what it does | wall time |
|---|---|---|---|
| 1 | `.venv/bin/python method.py --stage gates` | gate 1 (iteration-1 events 2,347 / 2,154 / 2,000, row-level vs exp_2 CSV) and gate 2 (exp_7 co-primary b_A 4.7391, N 1,544, G 140; primary 5.9526, N 452, G 77), then harmonisation rows h1–h5 | 2.6 min |
| 2 | `.venv/bin/python method.py --stage load` | MeSH concepts and works into the exp_7 structure; yearly co-word substrate | 10 s |
| 3 | `OPENALEX_API_KEY=… .venv/bin/python method.py --stage coverage` | 24 group_by calls: PubMed-share host-coverage rule and truncation audit | 20 s |
| 4 | `.venv/bin/python method.py --mini --stage events`, then `--stage events` | mini (10 concepts) then full entry events; the pre-declared F6 widening is chosen from W1 counts | 5 s each |
| 5 | `.venv/bin/python method.py --mini --stage nativeness`, then `OPENALEX_API_KEY=… … --stage nativeness` | 6a fallback check (written and hashed first); 3 smoke re-fetches; 2,509 capped group_by calls at ≤ 4 req/s | 12 min |
| 6 | `.venv/bin/python method.py --mini --stage features`, then `OPENALEX_API_KEY=… … --stage features` | 41 topic-hydration calls; W1 features; leakage test (bit-identical); union set | 1 min |
| 7 | `.venv/bin/python -m pytest -q tests/` | 17 tests: vendored exp_7 tests unchanged, T1 unit tests, window-outcome equality on main | 30 s |
| 8 | `.venv/bin/python method.py --stage freeze` | synthetic dry run of the model stage; 200-rep power simulation; `results/mesh_spec.json` sha256 freeze (07:11:10Z) | 2 min |
| 9 | `.venv/bin/python method.py --stage outcomes` | spec and feature hash check, then outcomes computed once (07:12:10Z) | 10 s |
| 10 | `.venv/bin/python method.py --stage models` | R1–R4, S1–S18; 999-draw wild bootstrap; 200 placebo permutations; 40 outcome shuffles; pyfixest crosscheck; comparison; verdict | 1 min |
| 11 | `.venv/bin/python method.py --stage report` | `method_out.json`, figures F1–F6, `results/g4_summary.json` | 25 s |
| 12 | `.venv/bin/python method.py --stage h6` | harmonisation h6a/h6b on the main screen | 1 min |
| 13 | `.venv/bin/python audit_rederive.py` | raw-row plain-loop audit of 20 events and R2 via pyfixest | 1 min |
| 14 | `.venv/bin/python audit_headline.py` | headline re-derivation through a different code path, plus placebo-input tests | 1 min |
| 15 | `aii_json_format_mini_preview.py --input method_out.json` | full, mini and preview files; each validated against `exp_gen_sol_out` | seconds |

Two things to know when rerunning:
- `.venv/bin/python method.py` with no arguments runs stages 1–12 in order.
- A rerun of `freeze` refuses once outcomes exist, and `outcomes` refuses unless the spec and feature hashes match.
  To redo the freeze, delete `results/outcomes_mesh*.parquet` first.

## 5. What a reader should get

These are the results the paper's RQ2 host-entry (grafting) replication section reports, in its model table and
forest figure (F1):

| number | value | file |
|---|---|---|
| G4 verdict | REPLICATED (reading GRAFTING in R1 and R2) | `results/g4_verdict.json` |
| R2 co-primary IRR per SD of A_cont | 1.233 [1.117, 1.361]; Holm p 9.7e-05; wild p 0.001; N 2,171; G 160 | `results/g4_rows.csv`, `results/g4_summary.json` |
| R1 primary | 1.324 [1.098, 1.598]; p 0.0037 | same |
| MeSH vs main 1.300 | z −0.705, p 0.48; IVW pooled 1.262 [1.173, 1.358]; I² 0 | `results/comparison_main_vs_mesh.csv` |
| Placebo host (S3) | 1.031 [0.963, 1.103] | `results/g4_rows.csv` |
| Permutation placebo p (R2 / R1) | 0.010 / 0.045 | `results/placebo_mesh.json` |
| MDE80 (R2 / R1 / G1) | 1.20 / 1.40 / 1.30 | `results/power_mesh.json` |
| Gates | both exact | `results/gates.json` |
| Frozen spec sha256 | `b7cdabf8144581ab7903ea29c3a8e9d03e047e45e7f343c0dec1cb4a05a47c91` | `results/mesh_spec.sha256` |
| features_mesh.parquet sha256 | `44b6270dc793584d9daf6817bf5b5f7078f20b2aa43566006d51d4860f3f051a` | `results/features_mesh.sha256` |
| Independent re-derivations | `all_match: true`; `match: true`; placebo inputs reject 0/20 and 1/20 | `results/audit_rederive.json`, `results/audit_headline.json` |

Figures are in `figures/` (F1 forest, F2 binned A_cont, F3 placebo z, F4 MDE curve, F5 host fields, F6 G2
decomposition).

A fresh fetch on another day may differ slightly because of live OpenAlex index drift. The smoke test found 0.0%
drift on 2026-09-29. Using the cached responses shipped here reproduces every number exactly.

## 6. OpenAlex credits spent

2,578 credits, all HTTP 200, one line per call in `logs/openalex_credit_ledger.jsonl`:
- 1 manual probe;
- 24 coverage calls;
- 2,512 nativeness calls (3 smoke re-fetches plus 2,509 new profiles);
- 41 topic-hydration calls.
