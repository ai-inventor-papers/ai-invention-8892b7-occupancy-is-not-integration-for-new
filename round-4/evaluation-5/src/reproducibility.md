# Reproducibility: adopter-level absorptive-capacity test of D2 (iteration 4, gen_art_evaluation_5)

This file describes what was actually run on 2026-09-29.
- Machine: Debian 12 container (Linux x86-64) with **4 CPU cores, 29 GB RAM and no GPU**.
- Everything runs on CPU.
- OpenRouter: $0, no LLM calls.
- OpenAlex: **0 credits spent**. The guarded pull was blocked by the key-wide reserve rule (see section 4).

## 1. Get the artifact
This workspace is published as one folder of the run's public GitHub repository.
```bash
git clone <repository URL>
cd <repository>/<path to this artifact's folder>   # the iteration-4 folder gen_art_evaluation_5
```
Every path below is relative to this folder.

## 2. Input artifacts (read-only; published as sibling folders of the same repository)
All inputs are resolved from ONE root: the invention-loop folder that holds `iter_2/` and `iter_3/`.
- It defaults to three levels above this folder: `Path(__file__).parents[2]` in `vendor/config.py` and `audit_rederive.py`.
- Override it with the environment variable `AII_DEPS_ROOT`.

| Default location under the root | Artifact | Files read |
|---|---|---|
| `round-3/experiment-7/src` | **art_2Cd2JJypeGuA** (D2 host-entry experiment) | `results/screen_events_with_outcomes.parquet`, `results/features_screen.parquet`, `results/main_population_hydrated.json` (copied to `results/`), `results/d2_summary.json`. Its `src/{config,io_load,features,outcomes,ppml,models}.py` is vendored byte-identical in `vendor/`, checked against `vendor/SHA256SUMS` at every run. |
| `round-2/dataset-5/src` | **art_eR1Z7fMlOcxs** (hydrated 426-concept corpus) | `hyd/works/works_part_0{0..7}.parquet`, `hyd/concept_work.parquet`, `hyd/data_out.json`, `hyd/keywords_dict.json`, `hyd/taxonomy.json`, `hyd/context/subfield_year_totals.json`, `p2/profiles.jsonl`, `outputs/nativeness_coverage.json`, `deps/gen_art_dataset_2/{concepts,keywords}.parquet` |

The sha256 of every input is recorded in `mech_spec.json` under `input_sha256`. No user-uploaded file is used. No model or data download is needed beyond these sibling folders.

## 3. Environment
- Python **3.12.14** and `uv`. No system packages beyond a standard Ubuntu/Debian base.
- Install:
  ```bash
  uv venv .venv --python=3.12
  uv pip install --python .venv/bin/python -r pyproject.toml   # 76 exact pins = requirements.lock.txt (uv pip freeze)
  ```
- Key versions: numpy 2.5.3, pandas 3.0.6, scipy 1.18.1, statsmodels 0.15.0, pyfixest 0.60.0, pyarrow 25.0.1, aiohttp 3.14.3, matplotlib 3.11.2, loguru 0.7.3.
- Environment variables, by name only:
  - `OPENALEX_API_KEY` is needed only for `--stage pull`. If it is unset, the pull stage reads the key from the dataset_5 `hyd/.env` file, which is not published. The key is never logged or written.
  - `AII_DEPS_ROOT` is optional.

## 4. Commands, in the order they were run (4 CPUs)
```bash
.venv/bin/python eval.py --stage prepare   # ~15 s: vendor sha check, rebuild results/cache/prepared.pkl,
                                            # REPRODUCTION GATE b_A = 4.739106 (target 4.7391 +/- 1e-4), N 1,544, G 140 -> pass
.venv/bin/python eval.py --stage frame     # ~110 s: cases, risk-set controls, targets, mediators -> frames/*.parquet
.venv/bin/python eval.py --stage freeze    # ~350 s: mech_spec.json (sha256 96e697c6...) + simulated MDEs (mech_spec_power.json)
.venv/bin/python eval.py --stage pull --pull-mini 10   # mini pull: key-wide remaining 563 < 2,500 reserve -> blocked, 0 credits
.venv/bin/python eval.py --stage pull      # full pull: remaining 484 -> blocked by the guard, 0 credits (results/api_results.json)
.venv/bin/python eval.py --stage analyze --mini   # smoke run, B = 20 (its outputs in results/mini/ were deleted afterwards)
.venv/bin/python eval.py --stage analyze --B 1000 # ~13 min: exposures, model suite, B = 1000 bootstraps, mediation
.venv/bin/python eval.py --stage extra --B 1000   # ~20 s: supplementary origin-subfield check (added post hoc, labelled)
.venv/bin/python eval.py --stage assemble  # reading rule, tables, figures, eval_out.json (no refit)
.venv/bin/python make_variants.py          # own mini/preview (later overwritten by the aii-json format script)
.venv/bin/python audit_rederive.py         # ~1 min: independent re-derivation from the raw parquet files
```
The aii-json format script, run on `eval_out.json`, then wrote `full_eval_out.json`, `mini_eval_out.json` and `preview_eval_out.json`.

**Seeds** (all recorded in `mech_spec.json` under `seeds`):

| Use | Seed |
|---|---|
| Frame | 20260929 |
| API subsample | +7 |
| Model-suite bootstrap | +11 |
| Permutation | +13 |
| Power | +17 |
| Mediation bootstrap | +19 |
| Supplementary bootstraps | +23 … +41 |
| Audit | 99 |

**Frozen before exposure:** `mech_spec.json`, `mech_spec.sha256` and `mech_spec_power.json`. The pull, analyze, extra and assemble stages refuse to run if either the spec hash or any `frames/*.parquet` hash differs.

**Credit rule:** paid OpenAlex calls stop at 400 own credits, or when key-wide `x-ratelimit-remaining` would fall below 2,500. Other agents on the same key had drawn it down to 484-563, so no paid call was made. Re-running the pull with ample credits would activate the API validation branch, and results would then differ in `supplementary.api_validation` only.

## 5. What you should get
The paper places these numbers in the RQ2 diffusion section, as adopter-level mechanism evidence for the D2 host-share effect: screen fold, corpus exposure.

| Output | Expected value | Where |
|---|---|---|
| Reproduction gate | b_A 4.739106, N 1,544, G 140, pass | `results/gate.json` |
| Adopters | 21,941 (author, entry) pairs in 857 of 1,544 entries; 87% career-new in the corpus | `results/frame_summary.json` |
| Matched sample | 1,013 strata, 422 entries, 109 concepts; SMDs after matching <= 0.032 | `results/match_balance.json` |
| MDE80 (before exposure) | primary OR 1.5 (grid), interaction ratio 1.3, mediation share 0.2 | `mech_spec_power.json` |
| Primary OR(E_any \| E_neg, lp) | **3.09 [2.32, 4.28]**; prevalence 0.79 vs 0.61; 354 discordant pairs | `results/enrichment.json` (m2), `eval_out.json` metrics_agg `m2_E_any_OR*` |
| NEG / PLAC ORs | 0.62 [0.49, 0.77] / 0.72 [0.57, 0.90]; ratios partner/NEG 5.02 [3.45, 7.51], partner/PLAC 4.53 [3.05, 7.21] | `results/ratios.json` |
| Reading | **SUPPORT**; interaction null (0.87 [0.70, 1.14]); FOREIGN > NATIVE (ratio 0.51 [0.33, 0.89]); companion 3.10 vs non-companion 1.36 | `results/mechanism_results.json` → `reading` |
| Mediation | attenuation by M2 0.05 [-0.08, 0.23]; by M1 0.01; reverse attenuation 0.68 | `results/mediation.json` |
| Origin check (post hoc) | E_any OR 2.52 [1.91, 3.43] given origin-subfield activity | `results/supplementary.json` |
| Figures | F1-F5 | `figures/*.png|pdf` |
| Audit | exposure agreement 1.000 (3,750 members); statsmodels OR 3.095; McNemar 268/86 = 3.12 [2.32, 4.24]; pyfixest b_A 4.7391 → 4.4933 (attenuation 0.0519); shuffled labels mean OR 0.97; random exposure OR 0.93 (p 0.43); shuffled M2 attenuation -0.002 | `results/audit_rederive.json` |

Bootstrap percentiles are deterministic given the seeds. BLAS-level floating-point differences (~1e-12) cannot change any reported digit.

A note on the audit's shuffled-label placebo: 7 of 50 shuffles (14%) reached a *model-based* p < 0.05. That is within binomial noise of 5% at n = 50, but it is one reason all inference uses the concept-cluster bootstrap. The 200-draw permutation null in `results/permutation.json` is centred on OR 1.00.
