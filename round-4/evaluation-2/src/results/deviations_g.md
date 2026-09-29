# Deviations from the evaluation plan (iteration 4, D2 held-out + G1-G3)

1. **Order of Steps 2 and 3.**
   - The spec was frozen at 06:58:28Z. The screen G run was launched right after (it started at 06:58:30), and the held-out opening followed at 06:58:58Z while that run was still going.
   - Both steps came after the freeze. Neither step reads the other's output, so no information flowed between them.
   - The screen G coefficients were written at 07:03.
2. **Projected MDEs.** The G1 held-out and pooled MDEs (1.30 and 1.15) were simulated at *projected* concept counts (84 and 258). Each projection is the screen G1-multi concept count scaled by the W1 concept counts per fold. The real multi-team status of held-out entries needs e+1 data, which was sealed at the freeze.
   - Realised G1-multi G: held-out 56 and pooled 161, against inputs of 84 and 258 concepts.
3. **Degenerate-fit flag.**
   - This is a post-hoc reporting flag, not a change to the spec. A row is flagged when IRR/SD < 0.01 or > 100, or when the CI bounds differ by more than a factor of 50.
   - Flagged rows: G3(iii) on screen (N 75, G 27) and the iteration-3 "stratum other" primary-FE row.
   - G3(iii) failed to fit on held-out (too few covered events after pruning).
   - These rows are listed, not dropped. They are excluded from the IRR ranges.
4. **Placebo-calibrated p.** The plan names SD 1.3. The spec asked for the SD to be recomputed from `placebo_draws.csv`, which gives 1.382 (co-primary FE) and 1.260 (primary FE); those values are used. On held-out, a calibration with the held-out placebo SD (1.297) is also reported.
5. **G3(ii) sec_host_share** is set to 0 for entry papers with no secondary topic, as declared in `g_spec`. This keeps the sample identical to the base model.
6. **Placebo host.** The candidate set uses subfield labels from the taxonomy's `sub_field` map. Every event had at least one candidate (median 22-23).
7. **No git commit.** The workspace is not a git repository. The freeze time is recorded in `logs/freeze_log.txt` and in `g_spec.json` (`frozen_utc`).
8. **Smoke test before the freeze.** `g_run.py --smoke` ran the full G code path on *random* Poisson outcomes before the freeze (`results/smoke/`), so that code bugs could not force post-freeze edits. No G code file changed after the freeze: `code_changed_after_freeze` is empty in all three summaries.
