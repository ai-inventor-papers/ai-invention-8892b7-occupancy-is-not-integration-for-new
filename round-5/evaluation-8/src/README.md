# Numbers-of-record audit (iteration 5, FIX slot)

This module checks every number and verdict the Applied Network Science paper may cite. Each one is compared with its source file in the iteration 1–4 artifacts and diffed line by line against `3_invention_loop/iter_5/gen_strat/current_report.md`. From the audited record it builds the paper-ready tables that the iteration-4 review asked for.

- Cost: CPU only, $0, no API calls.
- Access: read-only on every dependency. Nothing was written outside this directory.
- Runtime: about 50 s end to end.
- Paths: all paths in the outputs are relative to the run root (`run_spUCG07dPEEP/`).

## Results

The numbers below come from `results/audit_summary.json` and `eval_out.json`.

**What was audited.** The universe was frozen before any source was opened (`results/audit_spec.json`; universe sha256 `47f194ab…`). It holds 1,534 numeric tokens from the report and 319 curated cited numbers. The curated numbers come from the hypothesis' evidence-of-record lists and the report's claim tables.

- **M1 traceability.** 99.4% of the curated numbers have a source path and key (D2 98.2%; MeSH, RQ1, descriptive, adopter and data 100%). An auto-scan found a matching source value for 99.3% of report tokens with ≥2 significant digits. This match is weak evidence, because it does not check what the number means.
- **M2 agreement.** Agreement is measured on traced numbers that the report states:
  - 90.8% overall;
  - tier R (re-read from a summary file): 92.9% of 210;
  - tier C (recomputed from row-level files or primitives): 82.0% of 50. The disagreeing tier-C rows are the known drifts: 26/27, 83%, 8%, 3.1×.

  18 of 24 headline or verdict numbers are tier C. The six that are not are model coefficients or permutation p-values; recomputing them would mean refitting a model, which this audit does not do. They are `d2.ho.cop.p_sum`, `d2.ho.perm_within`, `d2.ho.estbin_cop`, `rq1.closure.ho`, `rq1.persist.sum` and `ll.pooled.ef_sum`.
- **M3 flags on the numbers.** Full list in `results/flags_by_block.csv` and `results/record_of_numbers_final.csv`.

  | Flag | Count |
  |---|---|
  | DRIFT_VALUE | 13 |
  | WRONG_ESTIMATOR | 7 |
  | WRONG_DEFINITION | 4, plus 13 text assertions |
  | NOT_TRACEABLE | 2 (Table 20's 1.14 / 1.09) |
  | VERDICT_DRIFT | 3 text assertions, plus 1 decision rule (R1) |
  | MISSING_IN_REPORT | 57 numbers of record the report never states |

- **M4 report drift.** 45 drift rows on 32 lines of the report (`results/report_drift.csv`): 6 VERDICT-CHANGING, 23 NUMBER-ONLY, 16 WORDING.
  - The known-drift gate passes: 12/12 items are detected (100%). They include the RQ1 rescue (lines 7 and 867), fig_methodology, 26 of 27, CT p 0.48→0.85, 83%, Table 20's 1.14/1.09, 3.1×, NEG/PLAC/matching, k=2 on MeSH, MeSH lead-lag and "predict establishment".
  - A new finding: the "83%" can be traced. It is the single-paper share over all 1,746 screen MAIN kw5 entries. On the 1,544-event co-primary sample the share is 87% (1,344/1,544). The flag is therefore WRONG_DEFINITION (unstated denominator), not NOT_TRACEABLE.
- **M5 detector validity.** The detector was tested by planting 40 errors in a scratch copy of the report (10 of each type) and re-running it without the list. **Recall was 0.60**, below the 0.95 target:

  | Error type | Recall |
  |---|---|
  | CI-bound swap | 1.0 |
  | Verdict flip | 0.9 |
  | Digit change | 0.4 |
  | Estimator/fold relabel | 0.1 |

  Precision on a 30-line manual check of lines the detector flags in the real report is 0.83 (25 TRUE; 5 are design constants or unverifiable values). Labels are in `results/precision_manual_labels.json`.
  - **Blindness.** The pre-registered seed 20260929 gave recall 0.35 with the first detector version. I inspected those misses. That exposed a bug: a changed verdict statement did not flag its line. I then added generic checks (verdict cells for every verdict table, a sentence-level fold-label check, a co-location check). Because I had seen that draw, the headline M5 comes from a fresh draw (seed 20260930). The re-run on seed 20260929 (0.60) is reported but is not blind.
  - **What M5 means for the paper.** The auto-scan is the weak part. It matches a number against about 3.8M source values, so a changed digit usually still matches something by chance, and a relabelled fold word on a line with no registry claim goes unnoticed. The detector is reliable only on the 319 curated claims, on verdict cells and on CI structure. Uncurated prose numbers should be treated as unverified.
- **M6 independent re-derivation.** `rederive_independent.py` is a second code path that shares no code with the audit (plain json/pandas and its own recomputations). It agrees on 73/73 numbers: a stratified ≥8 per block plus every headline number. No table was blocked.
- **M7 tables.** 11/11 tables pass the assertion script, which re-reads every sourced cell from its source file (0 failing cells).
- **M8 review closure.** All 6 MAJOR items of the iteration-4 review are CLOSED by an emitted table or drift row (`results/review_closure.json`).
- **M9 verdict consistency.** 13 decision rules were checked; their verbatim text is taken from the iteration 2–4 gen_strat files. There is 1 mismatch: R1_DEAD is never stated, and the report headlines the persistent-neighbour row instead. One more rule is RULE_NOT_RECORDED: the typology E1–E5 thresholds exist only in the artifact's sealed spec.
- **M10 MISSING_IN_REPORT rows.** The flag column has 292 rows, and a grep also finds 292. They are transcribed in `tables/T_missing.*`, including 8 SENS2 rows. The r1a correlations and the Granger row are not MISSING_IN_REPORT rows in that CSV:
  - the r1a correlations are in `3_invention_loop/iter_3/gen_art/gen_art_evaluation_1/results/r1a/r1a_correlations.csv`;
  - the Granger row is `ll.granger_b` in `record_of_numbers_final.csv` (b −0.0013, from art_mu0h0npvNX_u `leadlag_table.json`).
- **M11 Table 18 honesty.** Of the 11 claimed fixes, 3 were DONE, 4 PARTIAL and 4 NOT DONE (M2, M6, M9, m1). Details are in `tables/T_table18.md`.

**Verdict for the paper.** RQ1 is **R1_DEAD** under the frozen kill rule: held-out pooled-panel closure is −0.391 [−0.855, 0.072], Holm 0.147. The RQ1 sentence is "Structural precursors of sustained uptake are volume/churn correlates." D2 is confirmed on the held-out fold (1.187 [1.057, 1.335]) with the caveats in `T_caveats`: within-concept permutation p 0.050, CRV1 rejects 17.5% of null shuffles, EST_bin p 0.165. MeSH replicates for biomedicine → biomedicine entries only. The adopter result is OR 3.09 [2.32, 4.28] (m2), with a risk ratio of about 1.30.

## Layout

| Path | What it is |
|---|---|
| `eval.py` | Orchestrator. Steps: freeze → evaluate claims, rules and assertions → auto-scan → drift list → seeded injection → independent re-derivation → tables → `eval_out.json` |
| `audit_core.py` | Report tokenizer, frozen match rule, source reader (`relpath::key`), per-artifact numeric index |
| `registry.py` | The 319 curated cited numbers: intended source key, alternates (other estimator/fold/definition) and report/hypothesis regex |
| `checks.py` | Tier-C recomputations from row-level files, decision rules (verbatim quotes and re-application), verdict cells, text assertions |
| `audit_tables.py` | **Reusable checker (CLI).** Re-reads every sourced table cell. `check-rows` mode checks K1/K2/K3 `k*_rows.csv` files with a `relpath::key` source column |
| `rederive_independent.py` | Independent second loader (M6) |
| `results/audit_spec.json` | Frozen spec: universe hash, UTC timestamp, match rule, flag taxonomy, known-drift list, injection design |
| `results/record_of_numbers_final.csv` | One row per cited number: source, value, recompute, tier, report line and value, flag, replacement |
| `results/report_drift.csv` | Every report line that contradicts the record: correct text, source, severity |
| `results/verdict_consistency.json`, `verdict_cells.json` | Decision-rule re-application and verdict-cell checks |
| `results/seeded_injection.json`, `seeded_perturbations_SEALED_*.json` | M5 perturbations and detection results |
| `results/independent_rederivation.json` | M6 |
| `results/table_assertions.json` | M7 cell-level assertion results |
| `results/table18_honesty.json`, `review_closure.json`, `audit_summary.json` | M11, M8, all metrics |
| `tables/T_*.md` / `.csv` / `.cells.json` | Paper-ready tables: design, flow, decision, caveats, table18, rooting, rq1, adopter, mesh, missing, coverage. The cells file gives each cell's source |
| `tables/cases.md` | Verbatim transcription of the four case interpretations with source line numbers and recomputed rooted-minus-unrooted A_cont |
| `tables/closed_strands.md` | One sentence per closed strand |
| `verify_headlines.py` → `results/verify_headlines.json` | Short separate re-derivation of the headline metrics from the raw CSV/JSON outputs + shuffled-source placebo (agreement collapses to 1.6%) |
| `full_eval_out.json`, `mini_eval_out.json`, `preview_eval_out.json` | full / 3-item / truncated variants of `eval_out.json` |
| `reproducibility.md` | exact reproduction steps (run root via `AII_RUN_ROOT`, default `Path(__file__).parents[4]`) |
| `eval_out.json` | `exp_eval_sol_out` output. Datasets: record_of_numbers, report_drift, verdict_consistency, seeded_injection, independent_rederivation, table_assertions |

## How to run

```bash
uv venv .venv --python=3.12 && uv pip install --python .venv/bin/python pandas numpy pyarrow loguru scipy
.venv/bin/python eval.py                               # full audit, about 50 s
.venv/bin/python audit_tables.py check-dir tables --out results/table_assertions.json
.venv/bin/python audit_tables.py check-rows <k1_rows.csv> --value-col value --source-col source   # later K-row check
```

## Departures from the plan

- The "second analyst" is a second code path, not a second person.
- Seeded injection covers only four error types. A correct number attached to the wrong citation is not covered.
- M5 misses its target. The final M5 uses a fresh seed, because the pre-registered draw was inspected (see M5 above).
- The six headline numbers above are tier R, because recomputing them would need a model refit.
- No statistical estimation was redone.

## Restoring removed files

The only `delete` entries in `.aii/manifest.yaml` are regenerable environment and cache directories:

- `.venv/`: `uv venv .venv --python=3.12 && uv pip install --python .venv/bin/python pandas numpy pyarrow loguru scipy`
- `__pycache__/`: regenerated automatically by `.venv/bin/python eval.py`
