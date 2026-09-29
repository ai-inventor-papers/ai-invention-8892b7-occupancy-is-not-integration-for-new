# One-time held-out check of closure (R1), the D1 descriptive run and the D3 link

Iteration-4 evaluation artifact of the AI Inventor run on emerging scientific concepts in evolving co-word networks.
It is CPU-only, cost $0 and made no LLM calls. It performs three one-shot readouts on folds sealed in iteration 3:

1. **R1.** It opens the sealed RQ1 held-out fold **once**, with exp_5's hash-checked `confirm_heldout.py` (spec sha256 `535c2dd3…`). The script is byte-identical and runs inside a copy of exp_5.
2. **D1.** It runs exp_6's frozen **descriptive** held-out spec once (sha256 `8f4bc85d…`).
3. **D3.** It tests across concepts whether lower **early** closure goes with higher **later** host-entry anchoring (exp_7 A_cont).

The rules that decide what counts as R1 being "alive", plus the full D3 procedure, were frozen in `eval_spec.json` and `d3_spec.json` before anything was opened. Their sha256 values are in `logs/eval_freeze_log.jsonl`, and the freeze is git commit `b297884`.

## Results

| Part | Outcome |
|---|---|
| Integrity | 158/158 hashes match (spec, code, population, input manifest, sealed sidecars); exp_5 pytest 64/64, exp_6 11/11; the exp_5 screen self-test reproduces S to 1e-12 |
| R1 status (frozen kill mapping) | **R1_DEAD**. Raw closure pooled coef −0.391 (SE 0.236), one-sided p 0.049, **Holm p 0.147**. closure_resT −0.109, Holm 0.635 (DEAD). **closure_persist −1.073, Holm 0.015 (CONFIRMED)**. constraint S +0.105 [0.021, 0.187], DEAD in the pre-registered negative direction. |
| R1 event study (held-out) | closure S −0.534 [−1.200, 0.074]; closure_resT −0.266 [−0.891, 0.300]; closure_persist −0.826 [−1.706, −0.096]; xc_excess +0.038 [−0.061, 0.133]. Every row has the same sign as on the screen. |
| R1 mechanical verdict | **MIXED** again (flags: underpowered, R1a_model_dependent); \|S_res\|/\|S_raw\| = 0.50 |
| R1 reading test (R1-8) | **NOT_SUPPORTED** under the frozen rule. constraint > 0 with a CI excluding 0 and xc_excess > 0, but closure is not Holm-CONFIRMED. |
| R1 sample | 30 onsets (expected 12 [8, 16] matched). 14 matched within held-out, so the pre-declared fallback fired, giving 22 matched (73%). 17 of 25 controls, and 70 panel never-concepts, come from the screen. |
| R1 balance (SMD, screen SD) | H at k=0 **0.96**, subfield_count 0.71, closure at k=−3 −0.50, log_vol3 at k=−3 −0.37; 6 of 11 have \|SMD\| > 0.25 |
| D1 (descriptive only) | 6 cells, every CI includes 0 and every transfer ΔR² CI includes 0. Sign agrees with the screen in 5 of 6. |
| D3 decision | **NULL**. Screen partial ρ +0.025 [−0.199, 0.242], one-sided p 0.60, n 102, MDE 0.26. Held-out +0.053 [−0.279, 0.391], p 0.63, n 49, MDE 0.38. |
| D3 audit | Independent rebuild matches to 1e-16. Under the null, the permutation p falls below 0.05 in 4.3% of draws. |

The consequence for the paper text is written in `results_note.md`:
- The RQ1 raw-closure claim does not survive the held-out Holm family. It is replaced by 'structural precursors are volume/churn correlates', qualified by the confirmed persistent-neighbour row.
- The 'one mechanism at two scales' sentence (D3) is dropped.
- The Cheng et al. 2023 versus Salatino et al. 2017 tension is moot as a confirmed finding.

## Layout

| Path | What |
|---|---|
| `eval.py` | S8 assembler: R1 tables (R1-1..R1-10), forest plot F1, D1 table, `results_note.md`, `eval_out.json` (exp_eval_sol_out) |
| `s1_integrity.py` | S1: sha256 of every frozen file → `results/integrity_report.json` |
| `s3_power.py` | S3: R1 projected power and D3 counts-only ladder → `results/pre_open_power.json` |
| `s4_freeze.py` | S4: writes and freezes `eval_spec.json` and `d3_spec.json` (refuses to overwrite either) |
| `d3_link.py`, `src_eval/d3core.py` | S5: D3 screen, then held-out: partial Spearman, concept bootstrap (2,000, percentile + BCa), Freedman–Lane permutation (10,000), MDE, sensitivities S1–S8, figure F2 |
| `r1_open_once.py` | S6: imports `deps_run/exp5/confirm_heldout.py` by path, installs the recorders, calls `confirm()` once; guard file `results/r1/.opened` |
| `r1_balance.py` | R1-6 SMDs computed from the recorded capture (no re-opening; see `deviations.md` item 7) |
| `audit_d3.py`, `audit_d3_calibration.py` | Independent D3 re-derivation and null calibration of the permutation p |
| `eval_spec.json`, `d3_spec.json` | Frozen evaluation specs (hashes in `logs/eval_freeze_log.jsonl`) |
| `eval_out.json` | Final metrics and per-row, per-cell and per-fold examples (numeric codes in `metadata.metric_codes`) |
| `results_note.md` | Short note for the paper on the held-out outcome and the Cheng/Salatino tension |
| `deviations.md` | Planned and unplanned deviations, attempts log |
| `results/integrity_report.json`, `results/pre_open_power.json` | S1 and S3 outputs |
| `results/r1/verdict_heldout.json` | Output of the single R1 held-out run (copied from `deps_run/exp5/results_heldout/`) |
| `results/r1/r1_summary.json` | Everything for R1-1..R1-10 |
| `results/r1/r1_capture_balance.json`, `r1_matches_capture.parquet`, `r1_feat_capture.parquet` | Captured matched sets, features and balance |
| `results/r1/r1_capture_raw.pkl` | Raw recorder dump (15 MB). It stays on the run's volume and is kept; the published repository may skip it. |
| `results/d1/confirmation.json`, `heldout_outcomes.parquet` | Output of the single D1 run |
| `results/d3/` | `d3_results.json`, `d3_table.csv`, per-concept frames, audit files |
| `results/tables/*.csv` | Screen-vs-held-out tables, Holm decisions, n-flow, SMDs, IV synthesis (descriptive), D1 table |
| `figures/F1_r1_forest.{png,pdf}`, `figures/F2_d3_scatter.{png,pdf}` | Forest plot and D3 scatter |
| `logs/` | Every stage log, `eval_freeze_log.jsonl`, `r1_attempts.jsonl` |
| `deps_run/exp5`, `deps_run/exp6` | Byte copies of the iteration-3 workspaces (`tar`, with `.venv` and caches excluded) that the confirm scripts ran in. Their one-look outputs are `deps_run/exp5/results_heldout/` and `deps_run/exp6/results/heldout/confirmation.json`. |

## How to run (order matters; R1 and D1 are one-look and refuse a second opening)

```bash
LOOP=<run>/3_invention_loop     # parent of iter_2/, iter_3/, iter_4/
bash restore.sh                  # copies exp_5/exp_6 into deps_run/ and builds all three venvs
.venv/bin/python s1_integrity.py
(cd deps_run/exp5 && AII_INVENTION_LOOP=$LOOP .venv/bin/python -m pytest -q tests && AII_INVENTION_LOOP=$LOOP .venv/bin/python confirm_heldout.py --self-test-on-screen)
(cd deps_run/exp6 && AII_LOOP_ROOT=$LOOP .venv/bin/python -m pytest -q tests/test_confirm.py tests/test_guard.py)
.venv/bin/python s3_power.py
.venv/bin/python s4_freeze.py          # refuses if the specs already exist
.venv/bin/python d3_link.py
AII_INVENTION_LOOP=$LOOP deps_run/exp5/.venv/bin/python r1_open_once.py   # once only
AII_INVENTION_LOOP=$LOOP deps_run/exp5/.venv/bin/python r1_balance.py
(cd deps_run/exp6 && AII_LOOP_ROOT=$LOOP AII_OPEN_HELDOUT=iter4 .venv/bin/python confirm_heldout.py)  # once only
mkdir -p results/d1 && cp deps_run/exp6/results/heldout/{confirmation.json,heldout_outcomes.parquet} results/d1/
.venv/bin/python audit_d3.py && .venv/bin/python audit_d3_calibration.py
.venv/bin/python eval.py
```

The iteration-3 workspaces (exp_5, exp_6, exp_7) and the dataset_5 corpus (`iter_2/gen_art/gen_art_dataset_5/hyd/`) are read from the run tree. None of them is modified.

## Restoring removed files

`.aii/manifest.yaml` marks only regenerable bulk for deletion:

- `.venv/`: `uv venv .venv --python=3.12 && uv pip install --python=.venv/bin/python -r pyproject.toml`
- `deps_run/exp5/.venv/`: `cd deps_run/exp5 && uv venv .venv --python=3.12 && uv pip install --python=.venv/bin/python -r pyproject.toml`
- `deps_run/exp6/.venv/`: `cd deps_run/exp6 && uv venv .venv --python=3.12 && uv pip install --python=.venv/bin/python -r pyproject.toml`
- `deps_run/exp6/work/cp.parquet`, `deps_run/exp6/work/authors.parquet`: byte copies of `iter_3/gen_art/gen_art_experiment_6/work/{cp,authors}.parquet`. Restore with `cp -p $LOOP/iter_3/gen_art/gen_art_experiment_6/work/{cp,authors}.parquet deps_run/exp6/work/`.
- `__pycache__/`, `src_eval/__pycache__/`, `**/__pycache__/`: regenerated automatically by the Python interpreter on import (for example `.venv/bin/python eval.py`).
- `deps_run/exp5/.pytest_cache/`: `cd deps_run/exp5 && .venv/bin/python -m pytest -q tests`.

`restore.sh` performs all of the above.
