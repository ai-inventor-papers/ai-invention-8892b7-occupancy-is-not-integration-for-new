# Fix the record and test closure vs turnover (iteration 3, evaluation)

A $0, CPU-only, read-only evaluation over the five iteration-2 artifacts of the emerging-concepts study
(art_eR1Z7fMlOcxs dataset_5, art_BdBvbNuNU8E7 grounding, art_yjFB8Spw2w6M citation layer, art_mbFjmo5rbbf8 main-pool RQ1,
art_yWUkgWWKyq_h MeSH RQ1). It has three parts:

1. **Numbers of record**: every value the blocking review named, recomputed from item-level or row-level files where they exist.
   Each value carries its provenance (run-root-relative path and key), estimator, n, CI, and a drift flag against
   `3_invention_loop/iter_3/gen_strat/current_report.md`.
2. **R1a turnover pre-check on already-seen data**: is the pre-uptake closure deficit (E_up) reducible to neighbourhood
   turnover plus volume? This is run in the main pool (exp_3) and in MeSH (exp_4) with the original matched sets and the original estimator code.
3. **Decision rules (a)-(d)**: verbatim rule text, a pass/fail verdict per condition, the 9-row aligned-block table, the held-out seal
   audit, and the coverage table.

> Every R1a table carries this header: **PRE-CHECK ON ALREADY-SCREENED DATA; NOT CONFIRMATION; E_up promoted post hoc.**

## Headline results

### Part 1: record (406 rows; 182 recomputed from item- or row-level data)
The report has 42 non-OK flags: 14 WRONG_ESTIMATOR, 10 WRONG_UNITS, 9 WRONG_DEFINITION, 8 DRIFT_VALUE and 1 NOT_REDERIVABLE
(`results/drift_flags.csv`). The main ones:
- **Classifier Table 9.** P/R/accuracy 0.812/0.824/0.843 are not reproducible. At the frozen t_F1 = 0.5073 the values are P 0.759, R 0.886,
  accuracy 0.780, F1 0.818 and AUC 0.888 (TP 148, FP 47, FN 19, TN 86).
- **"Majority-class F1 0.000"** is WRONG_DEFINITION. CONCEPT is the majority class (167/300), so predict-all-positive gives F1 0.715.
- **"Classifier kappa 0.56 vs human anchors"** is WRONG_ESTIMATOR. 0.56 is LLM-A's value. The classifier's E1 kappa is 0.413.
- **The event-study S = -0.837 is called the "pooled panel coefficient"** (WRONG_ESTIMATOR). The pooled panel gives -0.743 [-1.06, -0.46].
  The Holm p values given for accretion (0.272) and participation (0.782) are pooled-panel values; the event-study values are 0.18 and 0.824.
  The E_alt closure Holm p 0.096 is also a pooled-panel value; the event-study value is 0.504.
- **Prediction Table 18 reports HGB throughout, while logit is the primary estimator.** For E_up, logit gives BASELINE 0.890, FULL 0.879
  and dAUC -0.010 [-0.045, 0.021]. The report's +0.019 is HGB.
- **Table 15 MDEs labelled "Cohen's d"** (1.22, 0.89, ...) are WRONG_UNITS. The file holds delta-AUC MDEs, for example 0.070 at n_min 5 and
  0.134 at n_min 30, both realised with BASE AUC 0.7.
- **"ASJC venue coverage 12.1%"** is WRONG_UNITS: 12.1% is a share of concept-work LINKS. The venue share is 12.8%.
  The nativeness figure of 78.7% is a share of host co-occurrence WEIGHT, not of edges (WRONG_DEFINITION).
- **MeSH.** The "SENS1 dP D 0.051, Holm 0.015" row is actually the E_cent-only row. The match rates 83.3%/72.2% are "any"/"3 at 30%",
  not "30%"/"20%".
- **Gate A.** The report explains the 0.55 → 0.17 drop as "pooling subfields", which is wrong (WRONG_DEFINITION). On the same 724 edges,
  lenient any-parent tracing gives a mean of 0.477 and within-host tracing gives 0.204.
- **Hashes.** dataset_5 frame, exp_2 prereg, exp_1 test population, exp_3 spec (inner) and the exp_4 features/spec hashes all match.
  Three exp_3 files (stage_snapshots.py, analysis_event.py, results_summary.json) differ from the hashes exp_4 recorded when it vendored them.

### Part 2: R1a (SPEC P, E_up, same matched sets and estimator)
| population | S_raw (all cells) | S_raw (same cells) | S_res [95% CI] | retained [95% CI] | MDE_res (SD) | verdict |
|---|---|---|---|---|---|---|
| main (n=21) | -0.837 | -0.758 | -0.566 [-1.140, 0.087] | 0.75 [0.08, 0.90] | 0.70 | AMBIGUOUS / UNDERPOWERED |
| MeSH (n=51) | -0.185 | -0.156 | -0.094 [-0.387, 0.217] | 0.60 [-1.28, 2.85] | 0.35 | AMBIGUOUS / UNDERPOWERED |
| IVW pooled | | -0.286 | -0.186 [-0.453, 0.081] | 0.65 [-0.63, 0.86] | | AMBIGUOUS / UNDERPOWERED |

- **Reproduction gate.** In the main pool S and CI are reproduced exactly. In MeSH, S is exact but the CI is off by 0.025. The cause is that
  exp_4's shared RNG stream cannot be replayed; the recorded CI lies inside the 30-seed Monte-Carlo range of CI endpoints.
- **Within-concept correlations of closure with turnover are weak.**
  - closure ~ new-relation rate: main -0.19 [-0.26, -0.12], MeSH -0.15 [-0.20, -0.09]
  - closure ~ novelty: main -0.17, MeSH -0.03
  - closure ~ beta_sim: about 0.03 in both populations
  - partial R² of the turnover block: 0.014 (main) and 0.002 (MeSH)
- **Main pool.** Volume and age alone retain 0.87 [0.74, 0.93] of the effect. Each single turnover covariate retains between 0.71 (novelty) and
  0.86 (beta_sim), and the full block retains 0.75. Most of the deficit survives, but its CI now touches 0 because the Baselga cells lost
  widen it. With rarefied Baselga (SPEC R, n = 15 treated) the verdict is NOT REDUCIBLE: S_res is -1.09 [-1.45, -0.55].
- **MeSH.** Volume alone already halves the small effect (retains 0.51).
- **Pooling.** Q = 1.88 (p = 0.17) and I² = 0.47 [0, 1.0]. Q is underpowered at k = 2; the raw-closure IVW from the recorded values is
  -0.407 with Q 6.02, against 6.16 in the side-by-side file.
- **Controls behave as intended.**
  - Oracle positive control (noisy copy of closure) retains 0.02 (main) and 0.06 (MeSH).
  - Negative control (N(0,1) noise) retains 1.00 and 0.97 of the volume-only effect.
  - The pseudo-onset placebo regenerates exactly (S -0.0286, n 38); its residualised S is 0.006 [-0.35, 0.35].
  - The plan's closure_raw positive control only partly erases the effect (retains 0.44 and 0.08), because closure and closure_raw correlate
    only r = 0.38 within concepts.
- **Caveat: turnover may be a bad control.** Turnover may be part of the brokerage mechanism rather than a confounder, so S_res is a conservative
  lower bound. S_fit is the turnover-explained share: main -0.19, MeSH -0.06.

### Part 3: rules
| rule | verdict |
|---|---|
| (a) | **TRIGGERED**: Gate A share 0.1727 < 0.5. Graft events: 2,347 total, 2,154 with ≥ 5 keywords (1,285 screen, 869 held-out). |
| (b) | **H1 PILOT-ONLY** (N_c 38 < 150; MDE dAUC 0.134 / 0.116). H2 is not primary (Gate B has 0 labelled episodes). |
| (c) | **NOT MET**: c2 fails for every label (the logit dAUC CI covers 0), no significant effect has the pre-registered + sign, and c4 has not been run. |
| (d) | **SEALED for exp_3/exp_4**: 0 held-out ids in 161 files, and 0 label rows in 2016-18. The 61 iteration-1 ids are a subset of the 119. Caveat: exp_2 computed origin series and cooling onsets through 2024 for 61 held-out concepts. |

The aligned-block table re-derives the side-by-side IVW and Q exactly when SE = CI width / 3.92, which is the file's method.
Only 5 of the 9 rows are interpretable (n ≥ 10 and n_eff ≥ 10).

### Independent re-derivation (`audit_rederive.py` → `results/audit_rederive.json`)
`audit_rederive.py` re-derives the headline numbers through separate code paths: plain loops, a Mann-Whitney AUC, a numpy-lstsq
residualisation, a hand-written event matrix, hand IVW/Q, and a substring search for held-out ids.
- **Exact matches, 19 of 19:**
  - classifier P/R/F1/accuracy/AUC and the all-positive F1;
  - main S_raw, S_raw_cc, S_res and retained;
  - MeSH S_raw, S_res and retained;
  - IVW S_res, Q and I²;
  - the within-concept r values;
  - the count of held-out hits.
- **Placebos behave as expected:**
  - Permuted-label classifier AUC is 0.506.
  - Treated/control role permutation within matched sets centres S_res on 0 (main: mean 0.007, SD 0.27; MeSH: -0.013).
    For main, only 3% of permutations are as extreme as the observed -0.566. This is a secondary signal: the pre-declared bootstrap CI still covers 0.
  - Shuffling closure within concepts gives r ≈ 0, with |r| at the 95th percentile of 0.06 (main) and 0.04 (MeSH), so the observed -0.19 and -0.15 exceed the null.
- **Scanner check:** the held-out scanner's positive control detects 38 held-out ids in exp_2's viability layer.
- **Report cross-check:** all 36 flagged report lines contain the quoted value.

## Layout
| path | content |
|---|---|
| `eval.py` | Runs Parts 2 → 1 → 3 and writes `eval_out.json` (exp_eval_sol_out schema, validated with aii-json) |
| `common.py` | paths (run-root-relative output; `AII_RUN_ROOT` / `AII_DEPS_ROOT` overrides), JSON helpers, IVW/Cochran Q/I² with a Q-profile CI |
| `audit_rederive.py` | independent re-derivation and placebo checks -> `results/audit_rederive.json` |
| `reproducibility.md`, `pyproject.toml` | exact reproduction steps; pinned dependencies |
| `part1_record.py` | numbers of record, blocks B1-B13 |
| `part2_r1a.py` | R1a steps 2.1-2.6 (spec hashed before any statistic) |
| `part3_rules.py` | aligned-block table, seal audit, decision rules, coverage |
| `eval_out.json`, `full_/mini_/preview_eval_out.json` | aggregate metrics (117) plus 6 datasets: numbers_of_record (406), r1a_results (22), r1a_within_concept_correlations (13), aligned_block (9), decision_rules (4), coverage (8) |
| `results/record_of_numbers.{json,csv,md}`, `results/drift_flags.csv`, `results/record_summary.json` | Part 1 |
| `results/r1a/r1a_spec.json` | pre-declared R1a spec, thresholds and controls, with its sha256 |
| `results/r1a/r1a_results.json`, `r1a_summary.md`, `r1a_event_table.csv`, `r1a_correlations.csv`, `r1a_residualisation_fits.csv` | Part 2 |
| `results/r1a/fig_r1a_eventstudy.{png,pdf}` | per-k treated-minus-control differences, raw vs residualised, for both populations |
| `results/aligned_block_table.{csv,md}`, `results/decision_rules.{json,md}`, `results/heldout_audit.json`, `results/coverage_table.{csv,md}` | Part 3 |
| `results/cache_d5_pool.json` | concept id → fold for the 426 dataset_5 concepts, extracted in Part 1 and reused in Part 3 |
| `logs/` | run logs |

## How to run
```bash
uv venv .venv --python=3.12
uv pip install --python=.venv/bin/python pandas pyarrow numpy scipy scikit-learn statsmodels loguru matplotlib pyyaml
.venv/bin/python eval.py      # ~90 s on 4 CPUs; reads the iteration-2 folders read-only
```
The scripts locate the run root from their own path (`<run>/3_invention_loop/iter_3/gen_art/<this folder>`) and read
`3_invention_loop/iter_2/gen_art/*`, `3_invention_loop/iter_1/gen_art/gen_art_dataset_1` (held-out fold check only),
`3_invention_loop/iter_2/gen_strat/gen_strat_1` (verbatim rule text) and `3_invention_loop/iter_3/gen_strat/current_report.md`.
They import the original estimator code read-only, with bytecode writing disabled:
- exp_3: `analysis_event.es_matrix`, `es_stats`, `match` and `assign_groups`
- exp_4: `analysis.mainpool_es`

## Deviations and limitations
- **D1.** The plan names MeSH `beta_sim` as the aligned Baselga column. In the features file, however, the column computed with the main-pool code
  is `beta_sim_raw`, and it correlates only r = 0.16 with `beta_sim`. SPEC P therefore uses `beta_sim_raw` in both populations, and the
  plan-literal `beta_sim` is reported as sensitivity `B_native` (retained 0.49). This was declared in the spec before any statistic was computed.
- **Bootstrap size.** Each population keeps its original bootstrap size, B = 1000 for main and 2000 for MeSH, so "same estimator" holds exactly.
- **Denominator.** The retained-fraction denominator is S_raw computed on the same finite cells as S_res (`S_raw_cc`). In the main pool,
  `beta_sim_raw` is missing in some pre-onset cells, so S_raw_cc = -0.758 while S_raw = -0.837.
- **Main-pool fit rows.** Main-pool fit units are screen concept-years with age ≥ 0 and year 2005-2019. Reference rows have no age in the
  indicator file and drop out.
- **Seal audit.** The audit is analysis-level only: dataset_5 holds full works for all 426 concepts, so it cannot show that nobody looked at raw
  held-out data.
- **Transcribed values.** Human-anchor, B-cubed, linker, Gate B, synthetic and power values have no item-level files and are transcribed with
  `recomputed=false`.
- **What this cannot show.** Nothing here confirms R1: both populations were screened, and E_up was promoted post hoc.
- **Provenance note.** During setup an empty `.venv` was created by mistake inside the exp_3 folder by a `uv run` call. It was removed within
  seconds and no exp_3 file was changed.

## Restoring removed files
| deleted path | restore command |
|---|---|
| `.venv/` | `uv venv .venv --python=3.12 && uv pip install --python=.venv/bin/python -r pyproject.toml` (all versions pinned) |
