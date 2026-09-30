# Reproducibility: RQ2-D2 host-entry test (grafting vs co-transfer)

This file describes what was actually run on 2026-09-29, on Ubuntu (Linux, x86-64) with **4 CPU cores, 32 GB RAM and no
GPU**. Everything is CPU-only, makes no API calls and uses no API keys, and cost $0. No OpenRouter or OpenAlex calls
were made.

## 1. Get the artifact
This workspace is published as one folder of the run's public GitHub repository. Clone that repository and `cd` into
the folder for this artifact (the experiment workspace `gen_art_experiment_7` of iteration 3):
```bash
git clone <repository URL>
cd <repository>/<path to this artifact's folder>
```
Every path below is relative to this folder.

## 2. Input artifacts (read-only; published as sibling folders of the same repository)
All inputs are read through ONE root, `config.LOOP` in `src/config.py`. It defaults to three levels above this folder,
i.e. the folder that holds `iter_1/`, `iter_2/` and `iter_3/`. Override it with the environment variable
`AII_DEPS_ROOT`, or point one input elsewhere with its own variable:

| Variable (default under the root) | Artifact | Files read |
|---|---|---|
| `AII_DATASET5_DIR` (`round-2/dataset-5/src`) | **art_eR1Z7fMlOcxs** (hydrated 426-concept corpus) | `hyd/works/works_part_0{0..7}.parquet`, `hyd/concept_work.parquet`, `hyd/data_out.json`, `hyd/keywords_dict.json`, `hyd/taxonomy.json`, `hyd/context/subfield_year_totals.json`, `p2/profiles.jsonl`, `outputs/nativeness_coverage.json`, `deps/gen_art_dataset_2/{concepts,keywords}.parquet` |
| `AII_DATASET1_DIR` (`round-1/dataset-1/src`) | **art_94GEMUsgAmgK** (iteration-1 pool) | `data_out.json` (iteration-1 concept list and origins, used only for the reproduction check) |
| `AII_EXP1_DIR` (`round-2/experiment-1/src`) | iteration-2 classifier experiment | `results/test_population.json` (sha256 6a887fb4…5505) |
| `AII_EXP2_DIR` (`round-2/experiment-2/src`) | iteration-2 citation-gate experiment | `results/gate_a/graft_fallback_events.csv` (reproduction target); `src/ppml.py` is vendored here unchanged (sha256 369a93a6…) |
| `AII_EXP3_DIR` (`round-2/experiment-3/src`) | iteration-2 network experiment | `results/concept_subfield/rs_distance.parquet` |

The sha256 of every input file is recorded in `heldout_spec.json` → `data_files`. No user-uploaded file is used.
No data, model or checkpoint downloads are needed beyond these sibling folders.

## 3. Environment
* System: Ubuntu with Python **3.12.14** and `uv` (any recent version). No other system packages are needed.
* Create the venv and install the exact pins (67 packages, identical to `requirements.lock.txt` = `uv pip freeze`):
```bash
uv venv .venv --python=3.12
uv pip install --python .venv/bin/python -r pyproject.toml
```
Key versions: numpy 2.5.3, pandas 3.0.6, scipy 1.18.1, pyfixest 0.60.0, scikit-learn 1.9.1, pyarrow 25.0.1,
matplotlib 3.11.2, loguru 0.7.3, orjson 3.12.0, pytest 9.1.1.

## 4. Commands, in the order they were run
```bash
.venv/bin/python -m pytest -q -c pytest.ini tests      # 8 tests pass (about 20 s)
.venv/bin/python method.py                             # stages 0-16, about 11 min wall time on 4 CPUs
.venv/bin/python audit_rederive.py                     # independent re-derivation, about 1 min
.venv/bin/python confirm_heldout.py --dry-run          # frozen code path on SCREEN data; held-out stays sealed
```
Measured stage times (`logs/method_full_run.out` / `logs/timings.json`, full run): load 10 s, features 15 s, outcomes 11 s, models 186 s
(includes the tight-tolerance pyfixest cross-check), robustness 20 s, placebo 77 s (500 + 50 fits x 2 specs, 4
processes), labels 30 s, out-of-sample 80 s, power 214 s (7 x 300 replicates x 2 specs), figures 22 s.

* **Seeds:** SEED = 20260929 (`src/config.py`). Placebo draw i uses SEED + 1000 + i; label shuffle i uses SEED + 5000 + i;
  power replicate k at grid point g uses SEED + 20000 + 1000 g + k; the audit's shuffles use SEED + 99.
* **Pre-registration:** stage 0 writes `results/d2_prereg.json` (sha256 f800a0a9…9f74). It refuses to run if the SPEC
  in `src/config.py` changes. Deviations are in `results/deviations.md`.
* `method.py --stage N` runs one stage. `method.py --mini` runs stages 0-7 on 10 screen + 3 reference concepts; it
  overwrites `results/events_all.parquet`, so rerun `method.py` in full afterwards.
* Held-out confirmation (iteration 4, exactly once): `.venv/bin/python confirm_heldout.py --open-heldout`. It refuses to
  run unless `sha256(heldout_spec.json)` equals `heldout_spec.sha256` (8db17113…ca7c) and every frozen code file
  (`src/{config,io_load,features,outcomes,models,ppml}.py`, `confirm_heldout.py`) matches its recorded hash.

## 5. What you should get
| Output | Expected value | Where |
|---|---|---|
| Iteration-1 event reproduction | 2,347 / 2,154 / 2,000, row-level equal | `results/repro_events_iter1.json` |
| Events | 4,177 main-arm entries; 1,746 screen MAIN kw5 (184 concepts); 1,100 held-out (93) | `results/events_summary.json` |
| Native share of partner tags at 0.5 / 0.3 | 0.011 / 0.033 → A_cont primary (fallback 6) | `results/features_summary.json` |
| Primary FE (concept x e + d x e) | N = 452, G = 77; A_cont IRR/SD 1.386 [0.968, 1.985], Holm p 0.149; CT 1.037; reading NEITHER | `results/d2_models.json` → `M1`, `decision_primary` |
| Co-primary FE (concept + e + d) | N = 1,544, G = 140; A_cont IRR/SD 1.300 [1.164, 1.452], Holm p 1.3e-5, wild p 0.001; CT 1.051 (p 0.48); reading GRAFTING | `M1_secondary`, `decision_secondary` |
| Robustness grid | 54 rows | `results/d2_robustness.csv`, `figures/F4_robustness_forest` |
| Nativeness placebo (z statistic) | co-primary p = 0.002, primary p = 0.154; placebo z mean about 0 | `results/placebo_summary.json`, `figures/F5_placebo` |
| Graft labels | 15.3 % anchored; EST_bin 0.4375 vs 0.2030 | `results/labels_summary.json` |
| Out-of-sample | deviance diff -0.234 [-0.537, 0.063]; Spearman 0.419 → 0.431 | `results/oos_check.json`, `method_out.json` metadata |
| Held-out power | MDE co-primary 1.15; primary none on the grid (underpowered, declared) | `results/power_heldout.json`, `figures/F6_power_heldout` |
| Audit | 20/20 events match; pyfixest b_A 4.7391; 0/40 shuffled fits reach \|z\| 4.69 | `results/audit_rederive.json` |
| Headline, with a source file per number | — | `results/d2_summary.json` |

Numerical results are deterministic given the seeds and pins. Tiny floating-point differences (≈1e-12) across BLAS
builds cannot change any reported digit. In the paper these numbers belong to the RQ2 diffusion section, under
"entry anchoring vs co-transfer": the coefficient table, the robustness forest, the placebo and the power statement.
