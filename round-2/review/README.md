# Review of the iteration-2 research report (run_spUCG07dPEEP)

This folder holds an adversarial audit of the iteration-2 internal research report. The audit checks the report against the five iteration-2 artifacts and the iteration-1 record.

## Layout

| Path | What |
|---|---|
| `.terminal_claude_agent_struct_out.json` | The structured review (ReviewerFeedback schema): assessment, strengths, scores, 12 critiques, and the results_reported, coverage and blocking flags. |
| `build_review.py` | Script that writes the JSON above (`python3 build_review.py`). |
| `notes/recomputed_numbers.md` | Every report number the reviewer recomputed or looked up, with its artifact file and a verdict (OK, MISMATCH, UNTRACEABLE, CONTRADICTED). |
| `.aii/manifest.yaml` | Disposable-output manifest. It is empty because there are no heavy files. |

## How it was produced

The reviewer read the report and each artifact's README and result files under `3_invention_loop/iter_2/gen_art/*`. Classifier metrics were recomputed from `d2_test_predictions.json`. Event-study, prediction, power, Gate A and MeSH values were cross-checked against their JSON and CSV outputs. The iteration-1 section was diffed against `gen_strat/current_report.md`. The review makes no API calls and uses no heavy compute.

## Restoring removed files

Nothing is marked `delete`, so nothing needs restoring.
