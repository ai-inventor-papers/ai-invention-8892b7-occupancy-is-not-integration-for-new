# Iteration-4 audit of the research record (REVIEW_REPORT)

This folder holds the audit of the iteration-4 internal research report for run `run_spUCG07dPEEP`. The draft being audited is `../report-text/paper_draft.md`. Every headline number was recomputed from the results files of the five iteration-4 artifacts, which sit in the read-only sibling folder `../`.

## Files
| path | content |
|---|---|
| `.terminal_claude_agent_struct_out.json` | The review in ReviewerFeedback format: overall assessment, 5 strengths, 3 dimension scores and 8 critiques. It sets results_reported=true, coverage=partial, blocking=false, score=5 and confidence=4. |
| `build_review.py` | Writes the JSON above. All review text lives in this script. It needs only the standard library. |
| `.aii/manifest.yaml` | Manifest of disposable outputs. It has no entries. |

## Artifact to folder mapping used
| ID | folder |
|---|---|
| art_WZ8fbLn79nCq | gen_art_evaluation_2 |
| art_zw_JJGsUFSnd | gen_art_evaluation_3 |
| art_mu0h0npvNX_u | gen_art_evaluation_4 |
| art_FZ2OCJwV6xHs | gen_art_evaluation_5 |
| art_XGdzjWgi-a88 | gen_art_experiment_9 |

## Key checks

**Numbers that recompute exactly**
- `heldout_post.json`: 1.187 [1.057, 1.335], N 972, G 74. Primary 0.98, N 250, G 30.
- `robustness_recount.json`: 20/26.
- `g4` rows: R1, R2 and IVW.
- `r1_holm_decisions.csv`: all four Holm rows.
- `d3_table.csv`.
- `leadlag_denominator_table.csv`: all 24 counts.
- `vocab_class.json`.

**Mismatches and numbers that cannot be traced**
- Table 20 gives multi-team IRRs of 1.14 and 1.09. No results file contains them; the direct rows are 1.28 (pooled) and 1.19 (held-out).
- Table 22's E_any of 3.14 comes from model m1. The pre-declared primary is model m2, which gives 3.09.
- The Burt-constraint row of Table 20c mixes estimators.
- H SMD is given as 0.94; the file gives 0.957.
- The new robustness note says the 20/26 count excludes the base row and strata. It includes them.
- Table 16's primary CT p is still 0.48; the file gives 0.85.
- The report's 83% single-paper share cannot be traced to any file.

**Omitted caveats the artifacts state**
- R1_DEAD under the frozen kill rule.
- The within-concept permutation p of 0.050 and the CRV1 rejection rate of 17.5%.
- The EST_bin null.
- Holm p values for held-out G2.
- MeSH covers biomedicine-to-biomedicine entries only.
- 87% of adopters cannot be measured.
- MeSH lead-lag p is 0.43.
- The log-rank censoring test.
- The case interpretations.

**Chronology**
- The iteration 1-3 text was diffed against `../../gen_strat/current_report.md`. It is unchanged apart from dash normalisation, the artifact-ID swaps and one marked correction.
- Table 18 in the draft claims fixes (M2, M6, m1) that this diff shows were not made.

## How to run
`python3 build_review.py`

## Restoring removed files
No entries are marked `delete`, so there is nothing to restore.
