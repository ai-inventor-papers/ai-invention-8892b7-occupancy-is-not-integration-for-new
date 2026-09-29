# Reproducibility

CPU only, no LLM calls, $0. Python 3.12 with uv. `LOOP` is the run's `3_invention_loop` directory. The R1 and D1 held-out folds are **one-look**: a rerun of `r1_open_once.py` refuses (guard file `results/r1/.opened`). To reproduce them from scratch you would need a fresh copy of the iteration-3 workspaces, and any such rerun counts as a second look at the fold.

## Steps (as executed on 2026-09-29, UTC)

1. **Copy and set up the environments.** Run `bash restore.sh`. It tar-copies iter_3 exp_5 and exp_6 into `deps_run/exp{5,6}` (byte-preserving, with `.venv` and caches excluded) and builds three uv venvs: the root one from `pyproject.toml`, plus one per copy.
2. **Integrity (S1).** Run `.venv/bin/python s1_integrity.py`, which writes `results/integrity_report.json`. Expected: 158/158 hashes ok, with R1 spec `535c2dd3…` and D1 spec `8f4bc85d…`.
3. **Pre-open tests (S2).**
   - `cd deps_run/exp5 && AII_INVENTION_LOOP=$LOOP .venv/bin/python -m pytest -q tests`: 64 passed.
   - Same directory: `AII_INVENTION_LOOP=$LOOP .venv/bin/python confirm_heldout.py --self-test-on-screen`: exit 0, passed = true, 68 onsets / 26 matched.
   - `cd deps_run/exp6 && AII_LOOP_ROOT=$LOOP .venv/bin/python -m pytest -q tests/test_confirm.py tests/test_guard.py`: 11 passed.
4. **Power (S3).** Run `.venv/bin/python s3_power.py`, which writes `results/pre_open_power.json`. D3 ladder level L1 is chosen (screen 102, held-out 49).
5. **Freeze (S4).** Run `.venv/bin/python s4_freeze.py`, which writes `eval_spec.json` (sha256 `099d0881…`) and `d3_spec.json` (sha256 `5d0144d7…`) and records them in `logs/eval_freeze_log.jsonl`. They were committed to git (`b297884`) before any fold was opened.
6. **D3 (S5).** Run `.venv/bin/python d3_link.py`, which writes `results/d3/*` and `figures/F2_d3_scatter.*`. The screen runs first, then the held-out fold. Seeds: bootstrap 20261001, permutation 20261002. It takes about 1 min.
7. **R1, opened once (S6).**
   - `AII_INVENTION_LOOP=$LOOP deps_run/exp5/.venv/bin/python r1_open_once.py`
   - `AII_INVENTION_LOOP=$LOOP deps_run/exp5/.venv/bin/python r1_balance.py`

   The wrapper's post-processing crashed after the verdict was written. SMDs were then computed from the recorded capture; see `deviations.md` item 7.
8. **D1, run once (S7).**
   - `cd deps_run/exp6 && AII_LOOP_ROOT=$LOOP AII_OPEN_HELDOUT=iter4 .venv/bin/python confirm_heldout.py`
   - Copy `results/heldout/{confirmation.json,heldout_outcomes.parquet}` to `results/d1/`.
9. **Audits.** Run `.venv/bin/python audit_d3.py && .venv/bin/python audit_d3_calibration.py`. The rebuild should match to 1e-16, and the null share of p < 0.05 should be about 0.043.
10. **Assemble (S8).** Run `.venv/bin/python eval.py`, which writes `eval_out.json` (schema exp_eval_sol_out), tables, F1 and `results_note.md`. `full_eval_out.json` is a copy of `eval_out.json`. `mini_eval_out.json` keeps the first 3 examples per dataset, and `preview_eval_out.json` is the mini file with strings truncated to 200 characters.

Read-only inputs come from the run tree:
- iter_3 exp_5, exp_6 and exp_7, including sealed files that are verified against their `.sha256` sidecars;
- iter_2 dataset_5 `hyd/concept_work.parquet` and `hyd/works/works_part_*.parquet`.
