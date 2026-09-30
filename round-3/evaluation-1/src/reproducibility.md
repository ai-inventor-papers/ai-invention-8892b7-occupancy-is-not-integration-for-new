# Reproducibility: Fix the record and test closure vs turnover

These are the steps that were actually run to produce every file in this folder. The run was CPU-only, cost $0, and made no
network calls (no OpenAlex, no LLM/OpenRouter calls).

## 1. Get the artifact
This folder is published as one folder of a public GitHub repository:
```bash
git clone <repository-url>
cd <repository>/<this-folder>          # the folder containing eval.py
```

## 2. Inputs (other artifacts, read-only)
The evaluation reads the outputs of five iteration-2 artifacts. It never writes into them.

| artifact id | folder name | files read |
|---|---|---|
| art_BdBvbNuNU8E7 | `gen_art_experiment_1` | `results/d2_test_predictions.json`, `classifier_results.json`, `merger_*.json`, `link_calibration.json`, `test_population.json` (+ `.sha256`) |
| art_yjFB8Spw2w6M | `gen_art_experiment_2` | `results/{gate_a,power,viability,synth,p1,origin}/*`, `prereg/prereg_freeze.json` (+ `.sha256`) |
| art_mbFjmo5rbbf8 | `gen_art_experiment_3` | `results/*` (indicators, labels, event_study, prediction, patterns, typology, robustness), `spec.json`, `config.py`, `lib_metrics.py`, `analysis_event.py` (imported) |
| art_yWUkgWWKyq_h | `gen_art_experiment_4` | `results/*` (features, analysis_summary, matched_sets, rq1_effects*, side_by_side, prereg_spec), `rq1_spec.py`, `analysis.py` (imported) |
| art_eR1Z7fMlOcxs | `gen_art_dataset_5` | `full_data_out/full_data_out_1..5.json`, `run_ledger.json`, `hyd/sample_frame_frozen.json` (+ `.sha256`) |

The following text inputs are also read, all through the run layout:
- `round-1/dataset-1/src/full_data_out/*.json`, used only to check the iteration-1 held-out fold ids;
- `iter_2/gen_strat/gen_strat_1/.terminal_claude_agent_struct_out.json`, for the verbatim decision rules;
- `iter_3/gen_strat/current_report.md`, the report being audited.

**Locating inputs.** All paths are resolved from `common.py` relative to its own location (`Path(__file__)`).
- **Default layout** (the AI-Inventor run layout): this folder sits at `<run>/3_invention_loop/iter_3/gen_art/<this folder>`, and the
  iteration-2 artifacts at `<run>/3_invention_loop/iter_2/gen_art/<folder name>`.
- **`AII_DEPS_ROOT`**: a path, relative to this folder or absolute, to the directory that holds the five iteration-2 artifact folders.
  Set it when they are published as sibling folders, for example `export AII_DEPS_ROOT=..`.
- **`AII_RUN_ROOT`**: the run root, if it differs. The report, strategy and iteration-1 files are found under it.

**No user uploads are used**, and no API keys or other environment variables are needed.

## 3. Environment
- Ubuntu (Linux 6.8), Python 3.12.14, `uv` 0.x. No system packages beyond a C runtime.
- Hardware actually used: 4 CPU cores (AMD EPYC 9655), no GPU. Peak RAM was under 3 GB, and scripts cap themselves at 16-20 GB (`RLIMIT_AS`).
```bash
uv venv .venv --python=3.12
uv pip install --python=.venv/bin/python \
  cloudpickle==3.1.2 contourpy==1.4.0 cycler==0.12.1 fonttools==4.66.0 formulaic==1.2.2 interface-meta==2.0.1 \
  joblib==1.6.0 kiwisolver==1.5.1 loguru==0.7.3 matplotlib==3.11.2 narwhals==2.26.0 numpy==2.5.3 packaging==26.3 \
  pandas==3.0.6 patsy==1.0.3 pillow==12.3.0 pyarrow==25.0.1 pyparsing==3.3.3 python-dateutil==2.9.0.post0 \
  pyyaml==6.0.3 scikit-learn==1.9.1 scipy==1.18.1 six==1.17.0 statsmodels==0.15.0 threadpoolctl==3.7.0 \
  typing-extensions==4.16.0 wrapt==2.5.0
```
The same pins are in `pyproject.toml`, so `uv sync` works too.

## 4. Commands, in the order run
```bash
.venv/bin/python eval.py            # ~85 s: Part 2 (R1a) -> Part 1 (record) -> Part 3 (rules), then writes eval_out.json
.venv/bin/python audit_rederive.py  # ~75 s: independent re-derivation + placebo checks -> results/audit_rederive.json
# mini/preview variants (aii-json skill script; any equivalent 'first 3 examples per dataset' truncation works):
python <aii-json>/scripts/aii_json_format_mini_preview.py --input eval_out.json
```
**Seeds and settings.** All of these are fixed in the code:
- main event-study bootstrap: B = 1000, seed `stable_seed('closure') % 2**31`, exactly as in exp_3;
- MeSH bootstrap: B = 2000 with `default_rng(42)`;
- within-concept correlations: concept-cluster bootstrap B = 2000, seed 0;
- negative-control noise: seed 0;
- placebo regeneration: `default_rng(11)` and seed 99, as in exp_3;
- classifier bootstrap: B = 2000, seed 0;
- prediction delta CI: concept bootstrap B = 1000, seed 0.

The R1a spec (`results/r1a/r1a_spec.json`) is written and hashed before any statistic is computed.
Its sha256 is `60f44c0fb645a5cc19b7ec60f6a4b8c61b596c1220d9da160d268d1aa0ca614a`.

Re-running is deterministic: two full runs gave identical numbers.

## 5. What you should get
**`eval_out.json`** (exp_eval_sol_out): 117 metrics and 6 datasets (406 / 22 / 13 / 9 / 4 / 8 examples). Key values:
- `record_n_rows` 406, `record_n_flags` 42 (WRONG_ESTIMATOR 14, WRONG_UNITS 10, WRONG_DEFINITION 9, DRIFT_VALUE 8, NOT_REDERIVABLE 1)
- classifier at t_F1 = 0.5073: precision 0.7590, recall 0.8862, accuracy 0.780, F1 0.8177, AUC 0.8879; `majority_all_positive_f1` 0.7152
- `main_S_raw` -0.8370; `main_S_raw_cc` -0.7577; `main_S_res` -0.5655 [-1.140, 0.087]; `main_retained` 0.746 [0.080, 0.895]
- `mesh_S_raw` -0.1846; `mesh_S_res` -0.0940 [-0.387, 0.217]; `mesh_retained` 0.604
- `ivw_S_res` -0.1859 (SE 0.136); `Q_res` 1.88, `p_Q_res` 0.170, `I2_res` 0.47
- verdicts: main, MeSH and pooled are all AMBIGUOUS / UNDERPOWERED
- within-concept r(closure, new-relation rate): main -0.187, MeSH -0.145
- rules: `rule_a_triggered` 1, `rule_b_pilot_only` 1, `rule_c_met` 0, `rule_d_sealed` 1, `heldout_id_hits_exp3_exp4` 0

**Other outputs**:
- `results/record_of_numbers.md` and `results/drift_flags.csv`: the sentence-level corrections for the paper's dataset, grounding,
  viability, event-study, prediction and MeSH sections.
- `results/r1a/r1a_summary.md` and `fig_r1a_eventstudy.png`: the RQ1 turnover pre-check.
- `results/decision_rules.md`, `aligned_block_table.md` and `coverage_table.md`.
- `results/audit_rederive.json`: 19 of 19 headline numbers re-derived exactly through independent code paths. The placebo checks:
  - permuted-label classifier AUC is 0.506;
  - role-permuted S_res is centred on 0 (main mean 0.007, SD 0.27);
  - within-concept-shuffled r is about 0;
  - the held-out scanner's positive control detects ids in exp_2.

## 6. Notes
- The exp_4 CI cannot be replayed bit-for-bit, because its bootstrap drew from an RNG shared with earlier stages. The S point estimate is
  reproduced exactly, and the CI to within 0.025.
- `.venv/` and `__pycache__/` are not published. Recreate them with the commands above.
