# Deviations and disclosures (iteration 4, gen_art_evaluation_3)

All times UTC, 2026-09-29. `eval_spec.json` (sha256 `099d0881…`) and `d3_spec.json` (sha256 `5d0144d7…`) were frozen at
06:39:13 (`logs/eval_freeze_log.jsonl`, git commit `b297884`). Both freezes came before any held-out fold was opened and before any D3 association was computed.

## Planned departures (declared in the artifact plan)

1. **R1 recorder wrapper.** `deps_run/exp5/confirm_heldout.py` was not run through its CLI. Instead, `r1_open_once.py` imported it by file path and called `confirm()` once. The script's bytes are unchanged: `results/integrity_report.json` shows 125/125 hashes matching, and `confirm()` re-checks its own hash. The wrapper records the return value of `run_fold` and the inputs to `analysis_event.match`. Nothing else is touched.
2. **The kill mapping (R1-7) and the reading test (R1-8) are this artifact's own rules.** They are frozen in `eval_spec.json` before the opening, and they are not part of the iteration-3 spec. The reading test's positive constraint direction contradicts the spec's pre-registered negative direction. The reading test is therefore secondary and never overrides a Holm decision.
3. **The R1 fallback triggered, as the spec allows.** Within the held-out fold, 14 of 30 onsets were matched (33 held-out never-controls). This is below 20, so the spec's rule added the screen MAIN never set (70 concepts), which gave 22 of 30 matched. Of the 25 unique event-study controls, 17 are screen concepts.

   Because the frozen `run_fold` builds the pooled-panel sample from the same enlarged never set, the **pooled panel also includes the 70 screen never-concepts**. Its 133 concepts are 30 held-out emerging + 33 held-out never + 70 screen never, and every treated (futE = 1) row is held-out. On the control side, then, neither estimator is independent of the screen. This follows from the pre-declared fallback, and it is the main caveat on the CONFIRMED closure_persist row and on the one-sided raw-closure p of 0.049.
4. **D3 exposure is an early-life window (ages 3-5), not literally pre-onset.** S2 gives the literal pre-onset version on the screen: n = 42, partial ρ +0.034.
5. **D3 is cross-sectional.** It can show an association, not a mechanism.
6. **The population is arXiv-skewed** (mostly physics and CS). S5 reports the non-physics subset.

## Unplanned deviations

7. **The wrapper's post-processing crashed after the verdict was written.** Timeline (`logs/r1_attempts.jsonl`):
   - 06:43:02: start.
   - 06:43:16: `verdict_written` (MIXED, fallback true). Then the guard file `results/r1/.opened` and the raw recorder dump `results/r1/r1_capture_raw.pkl` were written.
   - Afterwards, the SMD step raised `TypeError`. With the fallback, the run's feature frame contains the 60 reference concepts twice: once from the held-out call and once from the screen-controls block. That makes 1,500 duplicate (concept, year) keys.

   The fold was **not** re-opened, and `confirm()` was not called again. `r1_balance.py` read the recorded capture, checked that the duplicated rows are identical (`duplicates_identical = true`), de-duplicated them, and computed the SMDs. The verdict and all R1 numbers come from the single `confirm()` call.
8. **Origin-group merging in D3.** The spec says that groups with fewer than 5 concepts merge into "Other". In both folds "Other" itself has fewer than 5 concepts (2 on the screen, 1 held-out). Applying the same rule once more, the tiny "Other" group was folded into the largest group (Physics&Astronomy). It would otherwise be a dummy for 1-2 concepts. The independent audit (`audit_d3.py`) uses the same rule and reproduces the statistic to 1e-16.
9. **Held-out early volume (a D3 covariate).** It is log1p of mean yearly c-papers over F..F+5, taken from the dataset_5 link table. For held-out concepts with F ≥ 2011 this reads link counts after 2015. It is a single per-concept mean. No E_up label or other W2 outcome was computed from it, and the R1 confirm code was frozen and hash-checked beforehand. D3 (S5) was run before R1 (S6), as the plan orders.
10. **Screen reference values in `r1_pooled_panel_screen_vs_heldout.csv`.** For the four Holm rows they come from `confirm_selftest.json` (same code path, CR1 SE). For the other rows they come from `primary_family.json` `pooled_panel` (bootstrap CI, no SE).
11. **Verdict flags computed on the held-out run.** `verdict.decide` is called by the frozen script with an empty grid. Its `fresh_replication`, `old_subset_raw_closure` and `route_B_only_agreement` flags are therefore empty on the held-out fold. Its `F2_fallback_triggered` flag uses the post-fallback n_matched (22), so it reads false even though the spec's fallback did fire. `r1_summary.json` → `accounting.fallback_screen_controls` is the authoritative field.
12. **The self-test was run in the copy.** `confirm_heldout.py --self-test-on-screen` rewrote `deps_run/exp5/results/confirm_selftest.json`. This file is not hashed by the spec, and it came out identical in content (passed = true, 68 onsets, 26 matched).

## Attempts log

| UTC | event |
|---|---|
| 06:34:05 | exp5 screen self-test passed (exit 0) |
| 06:43:02 | R1 `confirm()` start (import + recorder) |
| 06:43:16 | R1 verdict_heldout.json written, the only look |
| 06:43:16 | wrapper post-processing crash (balance only), see item 7 |
| 06:42:55-06:43:29 | D1 `AII_OPEN_HELDOUT=iter4 confirm_heldout.py`, one run, exit 0 |
| 06:40:51-06:41:48 | D3 screen then held-out, one run |
