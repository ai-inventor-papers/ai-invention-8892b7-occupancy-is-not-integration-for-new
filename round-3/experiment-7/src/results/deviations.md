# Deviations from the frozen D2 spec (results/d2_prereg.json)

Every entry records what changed, why, and whether any outcome (W2) had been computed at the time. Outcomes were first
computed in stage 6; entries 1-4 were written before that.

1. **Nativeness fallback (plan fallback 6) triggered — pre-declared, decided on the native rate only.** At the 0.5
   threshold only 1.11% of profiled partner tags (MAIN, kw5, main arm, screen + held-out features, no outcomes) are
   native to the host (0.5 at 0.3). Broad legacy concepts rarely put >= 50% of their works in one subfield. As
   pre-declared for a native rate < 5%, the PRIMARY anchoring measure is **A_cont** (tag-weighted mean host share of
   the partners' pre-entry works) and the label threshold is native >= 0.3. The binary A at 0.5 / 0.3 / 0.7 is kept
   as robustness. The 2x2 partition is reported at 0.3 (primary) and 0.5. Coefficients are reported per SD of A_cont
   (SD 0.056) and per 0.1; 0.1 is about 1.8 SD, so the per-SD scale is the readable one. The excess-anchoring
   robustness uses A_cont - A0_cont (leave-one-concept-out host mean share), and the bounds use unprofiled tags
   counted with share 0 (lo) or 1 (hi).
2. **Event counts below the plan's expectation.** Main-arm entry events 4,177 (expected about 4,500); kw5 3,584
   (expected about 4,100); MAIN screen kw5 1,746 events in 184 concepts (expected about 2,500 in about 200). The
   causes: kw5 now counts distinct level >= 1 legacy-concept partners (not keyword_idx), the known-subfield rule
   (topic_score >= 0.05) drops weakly classified papers, 292 pre-F entries are excluded, and MAIN is 302 of 366
   main-arm concepts after the frozen sense-replacement rule. 184 clusters is still well above the 50-cluster norm.
3. **Portfolio relatedness density.** For 61 of 3,584 main kw5 events the concept has no c-paper with known
   subfield before e (e = F). RD then uses c-papers up to and including e (excluding the d-papers); the basis is
   recorded per event (RD_basis).
4. **Host benchmark A0 window.** A0(d, period) uses pool concepts' host d-papers published in the years of the
   entry period (2005-09, 2010-14, 2015-19), judged with that period's pre-period profile block, leave-one-concept-out.
   It uses only partner tags (no outcomes), but papers of other concepts may post-date e within the period.
5. **Placebo statistic (scale).** Permuting a node's subfield labels leaves its share distribution intact but moves its
   mass to random labels, so the placebo A_cont has a far smaller SD than the observed A_cont. Raw b_A is therefore
   not comparable between observed and placebo fits (a small-variance regressor gets large, noisy coefficients).
   The permutation p is computed on the z statistic b/se (primary) and also on the per-SD effect and raw b
   (reported). Detected on an 8-draw smoke run, before the 500-draw run.
6. **Fallback 3 triggered (thin within-cell identification).** The primary FE spec (concept x e + d x e) keeps 452 of
   1,740 events (26%) in 77 concept clusters (< 30% threshold). As pre-declared, the secondary spec (concept + e + d
   FE, 1,544 events, 140 clusters) is co-primary. The pre-declared coarsenings (concept x 2-year bin + d x e;
   concept + d x e) are reported alongside. The GRAFTING / TOOLKIT reading is given for each spec.
7. **Secondary spec covariates.** route_A is constant within concept and is absorbed by the concept FE, so it is not
   in the secondary spec; it enters the out-of-sample prediction model (which has no concept FE) instead.
8. **PPML convergence tolerance.** The vendored ppml.fit is called with tol = 1e-12 (maxit 500) instead of its default
   1e-9, so the SE cross-check against pyfixest (same retained sample, tight tolerances) meets the plan's 1e-3
   relative criterion. pyfixest's own pruning is not iterated and keeps 66 extra singleton events (518 vs 452); the
   cross-check therefore runs pyfixest on the sample retained by the iterated pruning.
9. **Held-out spec re-frozen once (no outcome change).** `src/config.py` gained per-dependency path overrides
   (AII_DEPS_ROOT, AII_DATASET5_DIR, ...) for portability, and `src/events.py` reads dataset_1 through config.D1.
   This changed a frozen code hash, so stage 14 was rerun. The first freeze hash, d3622f33…046b, is superseded by
   8db17113…ca7c (both are in logs/freeze.log). The screen estimates in the spec are unchanged, the dry run reproduces
   them bit for bit, and no held-out outcome was computed at any point.
