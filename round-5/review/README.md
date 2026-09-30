# Review of the iteration-5 research report (run_spUCG07dPEEP)

This folder holds an adversarial audit of the internal research report for iteration 5 (the report through iteration 5). The audit checks the report against the executed artifacts.

## Layout
- `.terminal_claude_agent_struct_out.json`: the structured review (scores, critiques, the results_reported, coverage and blocking flags).
- `.aii/manifest.yaml`: the disposable-output manifest. It is empty because this folder holds no heavy files.
- `README.md`: this file.

## What was checked
- A diff of the iteration 1-4 text against `iter_5/gen_strat/current_report.md`. The only differences are dash normalisation. No in-place corrections were made.
- K1 and K3 numbers against `round-5/evaluation-6/src/results/{k1_rows.csv,k13_summary.json,k3_rows.csv,inference_rows.csv}`.
- K2 numbers and the frozen rule against `round-5/evaluation-7/src/results/{k2_summary.json,k2_spec.json}` and its README caveats.
- The audit outputs in `round-5/evaluation-8/src/{results,tables}`.
- The figure status in `round-5/evaluation-9/src/figures/F7/STATUS.txt`.

## How to reproduce
This was a read-only review. To reproduce it, re-run the shell and python one-liners described in the review against the paths above.

## Restoring removed files
None. Nothing was marked for deletion.
