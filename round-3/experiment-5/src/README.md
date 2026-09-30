# Is openness before take-off brokerage or churn? (RQ1 deepen, iteration 3)

Iteration 2 found one robust precursor of sustained uptake (E_up). Before onset, emerging concepts have **more open**
top-20 association-strength neighbourhoods than volume-matched controls: closure S = −0.837 [−1.26, −0.43], n = 21
matched. The obvious objection is **"turnover in disguise"**. A neighbourhood that renews fast has low closure
mechanically.

This artifact tests that objection. It is $0 and CPU only, with no OpenAlex and no LLM calls. It uses:
- **R1a**: closure residualised on the turnover measures (new-relation rate, novelty, β_sim), fitted label-free.
- **R1b**: closure recomputed on the **persistent** neighbours only (top-20(y) ∩ top-20(y−1)).
- **R1c**: Burt **constraint** / effective size of the weighted ego network (networkx formulas, unit-tested
  against networkx), plus a **cross-community pair excess** over a strength-decile-matched null.
- **R1d**: a hub-not-clique joint path (Δwmz > 0 and Δclosure < 0).

The pre-declared rule then labels the openness **BROKERAGE**, **TURNOVER** or **MIXED**. The held-out fold is sealed
under a hashed spec for iteration 4.

## Headline (all numbers from `results/results_summary.json`, `results/verdict.json`)

**Verdict (mechanical, MAIN × all concepts × E_up × route all): `MIXED`.**
- **Flags:** `underpowered` (26 matched < 30) and `R1a_model_dependent` (the complete-case R1a CI excludes 0; the
  declared mean-fill primary does not).
- No `R1c_degree_driven`, `R1b_selection` or `H_sensitive` flag.

| row (S over k = −3..0, 95 % concept-bootstrap CI, B = 2,000) | S | 95 % CI | Holm p (3-row family) |
|---|---|---|---|
| raw closure (row 0, the iteration-2 quantity) | **−0.439** | [−0.810, −0.050] | — |
| R1a closure_resT (turnover-residualised) | −0.295 | [−0.663, 0.092] | 0.194 |
| R1b closure_persist (persistent neighbours) | −0.575 | [−1.270, 0.122] | 0.194 |
| R1c Burt constraint | **+0.083** | [0.017, 0.147] | 0.039 (opposite to the brokerage sign) |
| R1c cross-community pair excess | **+0.063** | [0.012, 0.111] | — |
| log(n_ego × constraint) (degree diagnostic) | +0.278 | [0.086, 0.495] | — |
| R1d share(Δwmz > 0 & Δclosure < 0), treated − control | +0.061 | [−0.009, 0.133] | — |

**Why MIXED.**
- BROKERAGE fails: the R1a CI covers 0, and constraint is *higher* for emerging concepts, not lower.
- TURNOVER fails: |S_res| = 0.295 is **not** below half of |S_raw| (0.219). Residualising on turnover removes only
  about a third of the raw effect.

**What the evidence says.**
1. **Openness is only partly churn.**
   - Within concepts, closure correlates strongly with turnover: demeaned r = −0.33 with the new-relation rate and
     −0.42 with novelty; ~0 with β_sim (`results/r1a_correlations.json`).
   - Yet the openness signal keeps its sign after turnover residualisation (R1a) and on persistent neighbours (R1b).
   - Both point estimates are negative in every population × subset × route cell (`figures/fig_grid_forest.png`).
   - They reach significance in the **pooled panel**, which uses all 68 onsets:

     | pooled-panel row | coef | 95 % CI | Holm p |
     |---|---|---|---|
     | closure_resT | −0.40 | [−0.70, −0.12] | 0.0015 |
     | closure_persist | −1.12 | [−1.64, −0.71] | 0.0015 |
     | extended panel with the 6 turnover covariates + route: closure | −0.55 | [−0.83, −0.31] | — |

   - They also reach significance under **band-only matching** (52 matched): R1a −0.45 [−0.73, −0.18], R1b −1.32
     [−1.94, −0.80].
   - Partial logit: futE ~ closure + turnover covariates gives −0.73 per SD [−1.29, −0.41].
2. **It is not Burt brokerage.**
   - Emerging concepts' weighted ego networks are *more* constrained (+0.083), and more redundant per tie
     (log(n·C) +0.28).
   - Their top-20 neighbours nonetheless span **more communities** than strength-matched nulls (xc_excess +0.063).
   - The pattern reads as *cross-community, sparsely closed top neighbourhoods inside a concentrated,
     redundant wider ego network*. That is openness toward other communities, not structural-hole brokerage.
3. **Hub-not-clique (R1d)** leans the right way (19.6 % vs 13.5 % of concept-years) but its CI covers 0.

**Replication and robustness.**
- **Fresh replication (124 new concepts, MAIN new = 100):** raw closure S = −0.455 [−1.006, 0.060], one-sided
  p = 0.044, n = 14 matched. The sign is **consistent**; the result is not significant at the two-sided 95 % level.
- **Route B-only:** all four primary rows keep their sign.
- **H-matched sensitivity:** closure_resT −0.75 [−1.39, −0.18], but only 7 matched.
- **Placebo:** pseudo-onsets cover 0 for every row.

**Prediction (reported, not claimed).**
- Grouped 5-fold CV × 5 seeds on 530 MAIN concept-years with 219 positives. BASE AUC is 0.854 and FULL
  (+ closure_resT + constraint) is 0.853: **ΔAUC −0.001 [−0.008, 0.006]**.
- The label-shuffle control gives ΔAUC −0.0005 ± 0.019.
- The openness block adds nothing beyond the volume, degree and entropy baselines, as in iteration 2.

**Held-out power (`results/power_mde.json`, `heldout_spec.json`).**
- Expected held-out matched treated: **12** (80 % band 8–16) from 63 eligible held-out MAIN concepts.
- For the closure rows the pooled panel has the smaller MDE, so it is the held-out primary estimator:

  | row | pooled-panel MDE | event-study MDE |
  |---|---|---|
  | closure | 0.38 SD | 0.56 SD |
  | closure_resT | 0.50 SD | 0.62 SD |
  | closure_persist | 0.44 SD | 0.62 SD |

- constraint, xc_excess and wmz keep the event study (tie or smaller MDE).
- Size check at δ = 0: 5–9 %. The small-n percentile bootstrap is mildly anti-conservative.
- The held-out fold can confirm effects of about ≥ 0.4–0.6 SD only. With a smaller n at the screen point
  estimate, event-study power is 0.33–0.63.

**Reproduction gate (passed before any label).**
- Code mode (a) re-attached exp_3's 145 concepts to the exp_3 snapshots:
  - Closure r = 1.000000 (max |diff| 5e-8); betweenness is identical.
  - The vendored E_up event study returns **41 onsets / 21 matched, S = −0.8370 [−1.2600, −0.4268]**, identical to
    iteration 2.
- Data mode (b) uses dataset_5 c-papers: closure r = 0.9996. Only 11 extra links and a 99.7 % identical
  per-(concept, year) count share (`results/repro/`).

## Populations and labels
- **Replacement rule.** The frozen rule from `test_population.json` filled 180 missing sense values from dataset_5.
- **Frozen membership check.** Every concept with a non-missing sense status keeps its frozen membership
  (156 MAIN / 147 STRICT).
- **Population sizes:**

  | population | screen | held-out |
  |---|---|---|
  | MAIN | 202 (102 old + 100 new) | 100 |
  | STRICT | 196 | 96 |
  | SENS | 247 | 119 |

- **Folds.** The sha1 rule reproduces dataset_5's folds exactly (247/119). The iteration-1 screen (123) and held-out
  (61) folds are nested in them, with no violations.
- **Labels, MAIN:**

  | label | onsets | never |
  |---|---|---|
  | E_up (primary) | **68** (33 old / 35 new) | 70 |
  | E_alt | 20 | — |
  | plan-literal E | 7 | — |

- **E_up is a post-hoc label** (promoted in iteration 2). This is disclosed in every output. Only the sealed held-out
  fold can remove that cost.

## Declared departures (see the plan's practice_alignment)
- **Match rate 38 % (26/68).**
  - The vendored matcher is unchanged, but origin groups now come from dataset_5 strata. These are finer than
    iteration 1's: 39 old concepts moved from a collapsed domain group to their own field.
  - The band-only sensitivity (52 matched) and the pooled panel (all onsets) are reported beside it.
- **H imbalance.** After matching, the SMD of entropy H is 0.55. H enters R1a, and the H-caliper sensitivity is
  reported. The SMD of log_vol3 is 0.10.
- **β_sim_rar NA.** β_sim_rar is NA for 55 % of pre-2016 screen concept-years. The primary handles this with
  mean-fill plus an NA dummy; the complete-case and raw-β versions are reported (flag `R1a_model_dependent`).
- **Constraint and degree.** Constraint is degree-sensitive, so the diagnostic log(n_ego · C) is reported. It moves
  with constraint, so the degree-driven flag is not raised.
- **Community noise.** Community-based rows (xc_excess, wmz) inherit Leiden noise (bootstrap AMI 0.62).
- **Scope.** The pool is physics- and CS-skewed. Neighbours are OpenAlex legacy concepts. No new MeSH replication.

## Layout
| path | content |
|---|---|
| `method.py` | Orchestrator: runs every step below in the pre-declared order (~8 min, 4 CPUs). |
| `confirm_heldout.py` | Iteration-4 confirmation. It is hash-checked (exit 2 on any spec or code change), computes the held-out E_up labels itself, and has a `--self-test-on-screen` mode that reproduces the Step-6 S values and CIs exactly. |
| `heldout_spec.json`, `heldout_spec.sha256` | Frozen held-out spec: estimands, directions, estimator per row by MDE, decision rules, population/sealed-file hashes, input manifest (exp_3 snapshots, dataset_5), screen betas, and code hashes. |
| `prereg_v3.json`, `prereg_v3.sha256` | SPEC3 pre-registration, written before any iteration-3 label. |
| `src/common.py` | Paths, **SPEC3** (all thresholds, seeds and the verdict rule text), helpers. |
| `src/setup.py` | Step 0: vendors exp_3 code byte-identical (`vendor/vendor_sha256.json`), checks the exp_3 spec hash, writes the prereg. |
| `src/population.py` | Step 1: replacement rule, MAIN/STRICT/SENS, folds, old/new → `results/main_population_hydrated.json`. |
| `src/prep3.py` | Step 2: dataset_5 c-papers (active and sealed), denominators, data-change check. |
| `src/openness.py` | Pure R1c metrics: Burt constraint / effective size / efficiency; cross-community share and decile null. |
| `src/attach.py` | Step 3: re-attaches concepts to the exp_3 snapshots (modes repro_code / repro_data / full / sealed) and computes R1b and R1c. |
| `src/indicators3.py` | Step 4: vendored indicators, new columns, R1a (label-free) and `_res`, sealed held-out pass with screen betas. |
| `src/repro.py` | Reproduction gate → `results/repro/reproduction_check.json`. |
| `src/labels3.py` | Step 5: E_up / E_alt / E on the screen fold (vendored), counts → `results/labels/`. |
| `src/leakage.py` | Recomputes 30 features with data after t removed (5 concept-years) → `results/leakage_test.json`. |
| `src/event3.py` | Step 6: event-study grid, primary family plus Holm, H-matched / band-only / placebo, pooled and extended panels, partial logit, R1a correlations, R1d. |
| `src/verdict.py` | Step 7: mechanical verdict and flags → `results/verdict.json`. |
| `src/power.py` | Step 8: held-out MDE (event study vs pooled panel) → `results/power_mde.json`. |
| `src/freeze.py`, `src/seal.py` | Step 8: held-out spec freeze; sealed-table loader guard. |
| `src/predict3.py` | Step 9: grouped-CV ΔAUC → `results/prediction.json`, `results/prediction/predictions.parquet`. |
| `src/audit.py` | Independent re-derivation of S, CI, Holm and the verdict → `results/audit.json` (max \|ΔS\| 6e-17, verdict agrees). |
| `src/figs.py`, `src/exports.py` | Figures; `method_out.json` and `results/results_summary.json`. |
| `vendor/` | exp_3 code copied byte-identical (`config.py`, `lib_metrics.py`, `netcore.py`, `stage_snapshots.py`, `stage_indicators.py`, `analysis_event.py`, `analysis_predict.py`, `spec.json`). The empty `vendor/{work,results,figures,logs}` folders are created on import by the vendored `config.py`. |
| `tests/` | 64 pytest tests: networkx equivalence (50 random ego graphs plus analytic stars), closure_persist identity, decile null, seal guard, label-free R1a, folds, population rule, confirm refusal. |
| `results/indicators/concept_year_indicators_hydrated.parquet` | 5,549 active concept-years × all raw, `_res`, R1a–R1c and lag columns. |
| `results/event_study/` | `primary_family.json` (primary cell and every sensitivity), `summary_grid.csv` (72 cells × rows), `grid_cells.json`, `contrib_primary.parquet`, `matches_primary.parquet`. |
| `results/` (other) | `verdict.json`, `power_mde.json`, `prediction.json`, `r1a_correlations.json`, `r1d.json`, `audit.json`, `leakage_test.json`, `confirm_selftest.json`, `results_summary.json`, `freeze_log.jsonl`. |
| `sealed/` | Held-out c-papers and W1 features (≤ 2015, sha256 side-file). **No analysis here reads them.** |
| `work/` | Population / pool tables (hash-bound by the spec), dataset_5 c-papers, attachment intermediates, repro-mode indicators. |
| `figures/` | `fig_es_panels`, `fig_grid_forest`, `fig_r1a_corr`, `fig_r1d_joint`, `fig_mde` (PDF + PNG). |
| `method_out.json` (+ `full_`/`mini_`/`preview_`) | `exp_gen_sol_out`: 530 screen MAIN concept-years. `output` = E_up; `predict_baseline` / `predict_method` = OOF scores of BASE / FULL. |

All kept artifacts stay on the run's volume at these relative paths. Every file is below 100 MB, so they are also in
the published repository.

## How to run
```bash
uv venv .venv --python=3.12
uv pip install --python=.venv/bin/python -r pyproject.toml
.venv/bin/python -m pytest -q tests                  # 64 tests
OMP_NUM_THREADS=1 .venv/bin/python method.py         # full pipeline, ~8 min on 4 CPUs
.venv/bin/python confirm_heldout.py --self-test-on-screen
# iteration 4, ONCE:
.venv/bin/python confirm_heldout.py --spec heldout_spec.json --expected-sha256 $(cat heldout_spec.sha256)
```
Dependencies are read-only sibling artifacts under `../../../round-2/` (`gen_art_experiment_3`,
`gen_art_dataset_5`, `gen_art_experiment_1/results/test_population.json`). Override the base with
`AII_INVENTION_LOOP`. **Do not edit any `src/`, `vendor/` or root `.py` file after the freeze.** `confirm_heldout.py`
refuses to run when a code hash has changed.

## Restoring removed files
Entries marked `delete` in `.aii/manifest.yaml`:
- `.venv/` (redownloadable):
  `uv venv .venv --python=3.12 && uv pip install --python=.venv/bin/python -r pyproject.toml`
- `__pycache__/`, `src/__pycache__/`, `vendor/__pycache__/`, `tests/__pycache__/`, `.pytest_cache/` (regenerable): Python recreates
  them when you run `.venv/bin/python method.py` or `.venv/bin/python -m pytest -q tests`.
