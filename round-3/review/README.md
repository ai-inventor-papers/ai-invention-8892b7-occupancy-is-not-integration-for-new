# Iteration-3 review of the research record (REVIEW_REPORT)

This folder holds an audit of the iteration-3 internal research report for run `run_spUCG07dPEEP` ("Open neighbourhoods precede concept spread"). The audit checks four things: that the report is complete, that each number traces to an artifact, that the reasoning behind each step is recorded, and that the claims match the evidence. Headline numbers were recomputed from the artifacts' own result files, which are read-only sibling workspaces under `../`.

## Files
| path | content |
|---|---|
| `.terminal_claude_agent_struct_out.json` | The review (ReviewerFeedback schema): assessment, strengths, 3 dimension scores, 11 critiques, results_reported / coverage / blocking / score / confidence. |
| `build_review.py` | Writes the JSON above. All review text lives in this script. |
| `.aii/manifest.yaml` | Disposable-output manifest. It has no heavy files, so it has no entries. |

## Key checks performed
- **Recomputed and matching:**
  - exp_5 `results/verdict.json`: S_raw −0.439, S_res −0.295, constraint +0.083, verdict MIXED.
  - exp_6 `results/headline_tables.md`: Table 1.
  - exp_7 `results/d2_models_table.csv`: co-primary IRR/SD 1.300 [1.164, 1.452].
  - exp_8 `results/leadlag.json`: 15/16 expansion-first, p 0.004.
- **Mismatches found:**
  - Table 16 gives the primary-spec CT p as 0.48; the file says 0.846.
  - "26 of 27 robustness variants" cannot be recomputed from `d2_robustness.csv`.
- **Chronology:** the iteration-2 section of the previous report (`../../gen_strat/current_report.md`, lines 224–554) was diffed against the new draft (`../report-text/paper_draft.md`).

## How to run
`python3 build_review.py` regenerates the JSON. It needs no dependencies beyond the standard library.

## Restoring removed files
No entries are marked `delete`, so there is nothing to restore.
