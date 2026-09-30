# Do open concepts travel further across fields? RQ2-D1 screen test (iteration 3)

This repository tests **RQ2-D1** on the screen fold of the frozen, grounded MAIN concept population.
**Question:** does a concept's *neighbourhood openness* in the evolving co-word network at focal year *t* predict how
far its papers spread across disciplines in the following five years, W2 = [t+1, t+5]? The prediction has to hold
beyond the standard baselines of level, volume, momentum, burst, diversity and coherence.

It continues the iteration-2 RQ1 closure lead (exp_3, `art_mbFjmo5rbbf8`). The earlier finding was that concepts which
go on to sustained uptake had *less clustered* (more open) association-strength neighbourhoods beforehand. This test
asks whether openness also predicts **where** concepts go, i.e. cross-disciplinary breadth. It does not re-test
**whether** they take off.

The run costs $0: CPU only, no API or LLM calls. Every number below is filled in by `src/outputs.py` from the files
in `results/`; none is typed by hand.

![forest](figures/fig2_forest_openness.png)

## Verdict (pre-declared rule)

**D1_NOT_SUPPORTED_SCREEN**. Outcomes meeting the rule: none. Outcomes significant in the opposite direction: none.

> D1_SUPPORTED_SCREEN = exists Y in {Y1r, Y2, Y3}: coef(closure_res) < 0 AND bootstrap CI excludes 0 AND Holm-adjusted p < 0.05 AND grouped-CV delta-R2 CI lower bound > 0 for that same Y. Else D1_NOT_SUPPORTED_SCREEN. If the sibling RQ1 holds and D1 fails -> 'take-off correlate only'. Sign > 0 with CI excluding 0 -> 'closure predicts breadth in the OPPOSITE direction' (reported, rule not met).

Why the verdict comes out this way:
- **Co-primary measures.** The complete-case primary openness measure leaves 100 screen MAIN concepts
  and 351 rows. That is fewer than the pre-declared F3 threshold (150 concepts / 500 rows). So
  `closure_res_imp` (missing `beta_sim_rar` → screen median + dummy) was promoted to **co-primary** in
  `results/d1/rowcount_decision.json`, and this was written *before any outcome was computed*. D1 is supported only
  when both measures meet the rule for the same outcome.
- **Primary estimates.** No closure_res coefficient is negative with a CI excluding 0 after Holm correction. No
  grouped-CV ΔR² has a CI lower bound above 0.
- **Signs are mixed.** The Y1r and Y2 coefficients are positive: more closure goes with more entropy / Rao-Stirling
  gain, opposite to D1, and the CIs cover 0 for the primary measure. The Y3 coefficient is negative: more open
  neighbourhoods go with more newcomer-reached subfields, also not significant.
- **Co-primary Y2 points the other way.** For `closure_res_imp` on Y2 the bootstrap CI excludes 0 in the *opposite*
  direction: coef +0.0120 [+0.0017, +0.0207], p_boot 0.020, Holm p 0.060. It does not survive Holm correction.

In short, on this screen **openness is at most a take-off correlate. It does not predict where a concept travels
across fields beyond the baselines.**

## Results

**Table 1. Openness at t → W2 breadth gain (screen, MAIN population).** OLS on BASE + openness_z. The coefficient is per SD of openness, with a 95 % concept-cluster bootstrap CI (2,000 reps). p_boot is the two-sided bootstrap p. Holm is taken over the 3 outcomes (co-primary measures); BH q over the secondary measures. ΔR² is out-of-fold (grouped 5-fold CV × 20 repeats) with a concept-bootstrap CI.

| openness | outcome | coef [95% CI] | coef / SD(Y) | p_boot | Holm p / BH q | CR1 p | ΔR² [95% CI] | rows / concepts |
|---|---|---|---|---|---|---|---|---|
| closure_res (primary) | Y1r | +0.0194 [-0.0098, +0.0408] | +0.095 | 0.199 | 0.405 | 0.110 | +0.0067 [-0.0151, +0.0305] | 347 / 98 |
| closure_res (primary) | Y2 | +0.0070 [-0.0024, +0.0133] | +0.110 | 0.135 | 0.405 | 0.055 | +0.0123 [-0.0129, +0.0426] | 351 / 100 |
| closure_res (primary) | log1p_Y3 | -0.0650 [-0.1556, +0.0299] | -0.072 | 0.176 | 0.405 | 0.164 | +0.0011 [-0.0123, +0.0146] | 351 / 100 |
| closure_res_imp (co-primary) | Y1r | +0.0209 [-0.0079, +0.0410] | +0.091 | 0.166 | 0.332 | 0.076 | +0.0079 [-0.0110, +0.0271] | 452 / 123 |
| closure_res_imp (co-primary) | Y2 | +0.0120 [+0.0017, +0.0207] | +0.128 | 0.020 | 0.060 | 0.007 | +0.0182 [-0.0032, +0.0390] | 512 / 136 |
| closure_res_imp (co-primary) | log1p_Y3 | -0.0262 [-0.1029, +0.0610] | -0.027 | 0.554 | 0.554 | 0.520 | -0.0022 [-0.0061, +0.0021] | 515 / 136 |
| Burt constraint | Y1r | +0.0108 [-0.0162, +0.0341] | +0.047 | 0.435 | 0.714 | 0.376 | -0.0006 [-0.0087, +0.0088] | 453 / 123 |
| Burt constraint | Y2 | -0.0094 [-0.0208, +0.0036] | -0.092 | 0.179 | 0.615 | 0.121 | +0.0025 [-0.0219, +0.0165] | 523 / 137 |
| Burt constraint | log1p_Y3 | +0.0617 [-0.0290, +0.1440] | +0.064 | 0.205 | 0.615 | 0.148 | -0.0005 [-0.0105, +0.0093] | 528 / 138 |
| effective size / degree | Y1r | -0.0086 [-0.0429, +0.0331] | -0.038 | 0.712 | 0.854 | 0.642 | -0.0056 [-0.0130, +0.0006] | 453 / 123 |
| effective size / degree | Y2 | +0.0006 [-0.0167, +0.0252] | +0.006 | 0.863 | 0.863 | 0.958 | -0.0150 [-0.0331, -0.0039] | 523 / 137 |
| effective size / degree | log1p_Y3 | +0.0433 [-0.0764, +0.1831] | +0.045 | 0.476 | 0.714 | 0.516 | -0.0067 [-0.0201, +0.0025] | 528 / 138 |
| cross-community pairs | Y1r | +0.0033 [-0.0204, +0.0381] | +0.014 | 0.659 | – (not in a family) | 0.822 | -0.0105 [-0.0205, -0.0031] | 429 / 122 |
| cross-community pairs | Y2 | -0.0021 [-0.0144, +0.0110] | -0.021 | 0.785 | – (not in a family) | 0.743 | -0.0056 [-0.0114, -0.0018] | 497 / 136 |
| cross-community pairs | log1p_Y3 | +0.0457 [-0.0443, +0.1344] | +0.048 | 0.344 | – (not in a family) | 0.320 | -0.0016 [-0.0072, +0.0038] | 502 / 137 |

Fold-internal residualisation (R1a refit on the training folds only), closure_res: Y1r: ΔR² +0.0071 [-0.0152, +0.0315]; Y2: ΔR² +0.0122 [-0.0138, +0.0433]; log1p_Y3: ΔR² +0.0007 [-0.0116, +0.0132]

**Table 2. Within E_up concepts** (onset ≤ 2015, rows t ∈ [onset−3, onset]; 68 concepts, 81 rows; secondary analysis).

| openness | outcome | coef [95% CI] | p_boot | CV ΔR² [95% CI] |
|---|---|---|---|---|
| closure_res (primary) | Y1r | +0.0137 [-0.0821, +0.0988] | 0.841 | -0.0696 [-0.1927, -0.0098] |
| closure_res (primary) | Y2 | +0.0055 [-0.0240, +0.0328] | 0.789 | -0.1502 [-0.4785, -0.0098] |
| closure_res (primary) | log1p_Y3 | -0.0790 [-0.4518, +0.2408] | 0.553 | -0.0134 [-0.1296, 0.1449] |
| closure_res_imp (co-primary) | Y1r | +0.0178 [-0.0693, +0.0948] | 0.712 | -0.0254 [-0.0868, 0.0156] |
| closure_res_imp (co-primary) | Y2 | +0.0057 [-0.0197, +0.0272] | 0.752 | -0.0419 [-0.1323, 0.0089] |
| closure_res_imp (co-primary) | log1p_Y3 | -0.0573 [-0.3842, +0.2089] | 0.598 | -0.0120 [-0.0738, 0.0492] |
| Burt constraint | Y1r | -0.0808 [-0.1828, +0.0212] | 0.125 | 0.0665 [-0.0748, 0.2060] |
| Burt constraint | Y2 | -0.0216 [-0.0495, +0.0081] | 0.166 | 0.0459 [-0.0981, 0.1849] |
| Burt constraint | log1p_Y3 | +0.0949 [-0.1800, +0.3777] | 0.452 | -0.0165 [-0.0790, 0.0309] |

**Table 3. Robustness grid** (the share of specifications with a negative coefficient, i.e. the D1 direction, and with a CI excluding 0 in either direction; the alternative outcomes Y1, Y1r20, log1p_Y3b and the PPML Y3 row are single specifications; all rows are in `results/d1/robustness.csv`).

| openness | outcome | specs | share negative | share CI excl. 0 |
|---|---|---|---|---|
| closure_res (primary) | Y1 | 1 | 0.00 | 0.00 |
| closure_res (primary) | Y1r | 12 | 0.00 | 0.08 |
| closure_res (primary) | Y1r20 | 1 | 0.00 | 0.00 |
| closure_res (primary) | Y2 | 12 | 0.00 | 0.08 |
| closure_res (primary) | Y3 | 1 | 1.00 | 0.00 |
| closure_res (primary) | log1p_Y3 | 12 | 0.92 | 0.00 |
| closure_res (primary) | log1p_Y3b | 1 | 0.00 | 0.00 |
| closure_res_imp (co-primary) | Y1 | 1 | 0.00 | 1.00 |
| closure_res_imp (co-primary) | Y1r | 12 | 0.00 | 0.08 |
| closure_res_imp (co-primary) | Y1r20 | 1 | 0.00 | 0.00 |
| closure_res_imp (co-primary) | Y2 | 12 | 0.00 | 0.58 |
| closure_res_imp (co-primary) | Y3 | 1 | 1.00 | 0.00 |
| closure_res_imp (co-primary) | log1p_Y3 | 12 | 0.92 | 0.00 |
| closure_res_imp (co-primary) | log1p_Y3b | 1 | 0.00 | 1.00 |
| Burt constraint | Y1 | 1 | 1.00 | 0.00 |
| Burt constraint | Y1r | 12 | 0.08 | 0.00 |
| Burt constraint | Y1r20 | 1 | 0.00 | 0.00 |
| Burt constraint | Y2 | 12 | 0.92 | 0.00 |
| Burt constraint | Y3 | 1 | 0.00 | 0.00 |
| Burt constraint | log1p_Y3 | 12 | 0.00 | 0.08 |
| Burt constraint | log1p_Y3b | 1 | 0.00 | 0.00 |

**Table 4. Mediation through W2 cross-community neighbour pairs** (descriptive; concept-bootstrap 95 % CI).

| openness | outcome | total c | indirect a·b |
|---|---|---|---|
| closure_res (primary) | Y1r | +0.0197 [-0.0130, +0.0423] | -0.0031 [-0.0101, +0.0030] |
| closure_res (primary) | Y2 | +0.0073 [-0.0021, +0.0150] | -0.0012 [-0.0036, +0.0005] |
| closure_res (primary) | log1p_Y3 | -0.0747 [-0.1830, +0.0338] | -0.0276 [-0.0724, -0.0009] |
| closure_res_imp (co-primary) | Y1r | +0.0225 [-0.0078, +0.0466] | -0.0052 [-0.0138, +0.0001] |
| closure_res_imp (co-primary) | Y2 | +0.0132 [+0.0020, +0.0226] | -0.0026 [-0.0060, -0.0001] |
| closure_res_imp (co-primary) | log1p_Y3 | -0.0269 [-0.1105, +0.0685] | -0.0216 [-0.0510, -0.0016] |

**Table 5. Minimum detectable effect** (80 % power, one-sided CR1 test in the D1 direction; SD(Y) per SD of openness; 'n/a' = not reached within 0.5 SD).

| openness | outcome | MDE screen | MDE held-out (n concepts) | bootstrap-rule power at held-out MDE | transfer-ΔR² MDE |
|---|---|---|---|---|---|
| closure_res (primary) | Y1r | 0.140 | 0.207 (49) | 0.66 | 0.472 |
| closure_res (primary) | Y2 | 0.141 | 0.209 (49) | 0.67 | n/a |
| closure_res (primary) | log1p_Y3 | 0.128 | 0.180 (49) | 0.62 | 0.431 |
| closure_res_imp (co-primary) | Y1r | 0.123 | 0.172 (63) | 0.69 | 0.440 |
| closure_res_imp (co-primary) | Y2 | 0.124 | 0.181 (63) | 0.72 | 0.424 |
| closure_res_imp (co-primary) | log1p_Y3 | 0.108 | 0.156 (63) | 0.68 | 0.379 |

### How to read the results
- **Effect size units.** Coefficients are per screen SD of the openness measure. `coef_in_sd_y` rescales them to SDs
  of the outcome. Y1r is the rarefied Shannon change (nats), Y2 the Rao-Stirling change, Y3 is `log1p` of the count
  of new subfields reached by author-disjoint newcomers.
- **Primary population.** The effect sizes are small and the CIs cover 0 in the MAIN population. In the unfiltered
  **SENSITIVITY** population (all main-arm concepts, no grounding filters, 420 rows), the closure_res
  coefficients are Y1r +0.0302 [+0.0018, +0.0489] and Y2 +0.0110 [+0.0018, +0.0166]. Where these CIs exclude 0 the direction is *opposite* to D1,
  and the effect disappears once the grounding filters (MAIN / STRICT) are applied (`results/d1/robustness.csv`).
- **Mediation** (descriptive, M is post-t). A more closed neighbourhood at t predicts fewer excess cross-community
  neighbour pairs in W2 (a-path CI excludes 0). Cross-community pairs in W2 in turn go with more newcomer subfields
  (Y3 b-path). The implied indirect path for Y3 is -0.0276 [-0.0724, -0.0009]. This is a decomposition, not a causal estimate.
- **Volume in disguise is controlled on both sides.**
  - The outcome is rarefied (Y1r; Y1r20 and the unrarefied Y1 appear in the robustness grid).
  - Log volume and momentum enter the right-hand side.
  - Spearman(closure_res, log W1 volume) = 0.21; the VIF of closure_res is 1.08.
- **Power.**
  - At screen size (n = 98 concepts), the smallest detectable closure_res effect on Y1r is 0.140 SD(Y)
    per SD(closure_res).
  - At the effective held-out size (n = 49 MAIN held-out concepts with a finite closure_res), it is 0.207.
  - The observed screen effects in SD units are listed as `coef_in_sd_y` in `results/d1/coef_table_primary.csv`.
  - `results/power/mde.json` holds every curve, including the transfer-ΔR² curves, the co-primary measure and the
    E_up subset.

### Sanity signals (`results/d1/sanity_checks.json`)
- **Placebo.** Permuting closure_res within calendar year across rows gives coefficients centred on 0. The observed
  coefficient sits at percentile 98 (Y1r) / 99 (Y2) / 6 (Y3) of that
  distribution. This row-level permutation ignores concept clustering, so it is anti-conservative. The
  concept-cluster bootstrap p-values in the table are the inferential ones.
- **Label shuffle.** With shuffled labels, the mean CV ΔR² is -0.0036 (≈ 0).
- **Leaky feature.** Adding a post-t feature raises out-of-fold R² sharply, which shows the CV harness can detect
  signal. For Y3, W2 volume takes R² from 0.418 to 0.587. For Y1r, the W2 entropy level takes it
  from 0.193 to 0.983.
- **Bootstrap stability.** Bootstrap CI widths change by < 1.6 % between 1,000 and 2,000 reps.
- **Determinism.** A same-seed refit is identical (True).
- **Audit.** `audit_rederive.py` re-derives the three primary coefficients (statsmodels formula API vs numpy) and
  20 Y1r values (plain loop), and checks the summary against its source files: all match = True.

## What was done

1. **Vendoring.** exp_3's code is copied verbatim into `vendor/` (sha256 in `vendor/SHA256SUMS`). The frozen SPEC
   hash `2e4c4894…2614` is asserted at import. The 13 vendored tests plus this repo's tests are run.
2. **Population** (`results/population/main_population_hydrated.json`).
   - The source is dataset_5 (426 concepts; folds screen 247 / held-out 119 / reference 60). The fold hash rule
     `sha1(concept_id) % 10 < 7` reproduces every main-arm fold.
   - The frozen replacement rule from exp_1's `test_population.json` (sha256 `6a887fb4…5505`) was applied to
     180 concepts that were pending in iteration 2.
   - MAIN = 202 screen + 100 held-out concepts (STRICT 196 + 96). The 119 held-out concepts are **sealed**: a code guard refuses any W2 computation for
     them, and for focal years 2016–18.
3. **Snapshots reused, not rebuilt.**
   - All 426 concepts are attached to exp_3's 25 prebuilt yearly co-word snapshots with the vendored pool-block code.
     The closure log-ratio against the top-20 Chung-Lu expectation is recomputed from `edges_y*` / `nodes_y*`.
   - **Reproduction gate:** r(closure) = 0.99956 on the 123 iteration-1 screen concepts × 2000–2019 (gate ≥ 0.99:
     PASS).
   - **Code equality:** on exp_3's own iteration-1 inputs, r = 1.000000.
   - 6 of the 123 concepts have a different paper set after hydration.
4. **Openness at t (W1 data only).**
   - `closure_res` (primary) is the R1a residual of closure on new-relation rate, novelty, β_sim (rarefied),
     log vol3, age and H_W1. It is fit once on all screen concept-years with age 3–8 and t ≤ 2015
     (424 rows, R² = 0.058). The coefficients are frozen in `results/openness/r1a_fit.json` for
     iteration 4.
   - Secondary measures:
     - Burt **constraint** and normalised **effective size** on the association-strength ego graph (vectorised;
       equal to networkx to 1e-9 in `tests/test_openness.py`);
     - the excess share of **cross-community pairs** among the top-20 neighbours over a strength-decile null.
5. **Baselines at t, BASE** (W1 = [t−5, t]):
   - H_W1 and the number of active subfields;
   - log W1 volume and momentum (slope of log per-10⁴ share);
   - growing-edge breadth (Shannon over subfields with a significantly growing yearly count);
   - Kleinberg burst state (truncated at t) and rarefied participation P_rar;
   - Rafols coherence on within-concept citation flows (median-filled + dummy when < 10 flows);
   - origin group, F-band, retrieval route and year-of-t dummies.
6. **Outcomes on W2** (screen only, every function guarded):
   - Y1r: rarefied Shannon change at n* = min(n_W1, n_W2) ≥ 20, 200 draws;
   - Y2: Rao-Stirling change with exp_3's fixed 2000–04 cosine distance;
   - Y3: subfields not active in W1 that are reached by ≥ 1 W2 paper whose authors are disjoint from the concept's
     W1 authors and their co-authors;
   - mediator M_W2.
7. **Models.**
   - OLS of Y on BASE + openness_z, with a concept-cluster bootstrap (2,000 reps) and CR1 SEs. Holm over the three
     outcomes; BH over the secondary measures.
   - Grouped-by-concept 5-fold CV × 20 repeats: ΔR² = FULL − BASE on pooled out-of-fold rows, with a
     concept-bootstrap CI. A fold-internal R1a variant is also reported.
   - Within-E_up subset, a robustness grid of 132 rows, mediation, partial dependence by decile, VIF.
8. **Power and freeze.**
   - MDE simulation at the effective held-out size.
   - `results/heldout/heldout_spec.json` (sha256 `8f4bc85d425eccbef10088151ff88eb21b0e04d3f11be462d1d00f0488d16509`, logged in `logs/freeze_log.txt`) plus the guarded
     `confirm_heldout.py`.
   - Because D1 is not supported on the screen, the spec freezes the held-out analysis as **descriptive only, with
     no confirmation claim**.

## Declared departures and limitations
- **Sample size and window.**
  - Focal years must satisfy t ≤ 2015 so that W2 ends by 2020, and t ≥ F+3. Concepts first seen after 2012 therefore
    contribute no rows. MAIN screen rows total 530 over 138 concepts.
  - Complete-case closure_res needs a rarefied β_sim, so the F3 co-primary rule applies (see the verdict section).
- **P_rar missing values.** P_rar is missing for concept-years with < 10 c-papers in the 3-year window. It is
  median-filled with a missing dummy, as is Rafols coherence. This was not listed in the plan and is declared here.
- **Circularity of the discipline layer.**
  - The discipline layer is the OpenAlex primary-topic subfield, and that classifier uses citations. The tags that
    define openness and the topics that define breadth come from different OpenAlex classifiers but the same papers.
  - The venue (ASJC) habitat covers only 12.1 % of links, so it is not used for D1.
- **Coherence scope.** Rafols coherence uses only within-concept citation flows.
- **Co-authorship scope.** The newcomer rule (Y3) sees co-authorship only inside the hydrated corpus (462,812 works),
  so "newcomer" means new to the concept's corpus neighbourhood.
- **Diversity vs diffusion.** Breadth outcomes do not separate knowledge integration from diffusion. Variety (Y3)
  and diversity (Y1r, Y2) are reported separately.
- **Placebo scope.** The placebo is row-level (see the sanity signals above).
- **No betweenness.** Betweenness is not recomputed on the reused snapshots (NaN). The strength percentile `pct`
  differs from exp_3 by design, because 426 concepts are now attached instead of 145.
- **E_up subset.** Pre-onset rows are few per concept (81 rows over 68 concepts). Its
  own MDE (`results/power/mde.json → E_up_subset`) is n/a / n/a / 0.45 SD(Y) for Y1r / Y2 / Y3, where 'n/a' means
  80 % power is not reached within 0.5 SD. The E_up estimates are therefore **descriptive**, even though the subset
  clears the 30-concept floor.

## Layout

| path | content |
|---|---|
| `method.py` | orchestrator: `--stage vendor population prep attach indicators openness features outcomes models power freeze outputs` or `--stage all`; `--mini` writes a 20-concept smoke run to `mini_run/` |
| `src/common.py` | dependency paths (derived from the repo location; override with `AII_LOOP_ROOT`), vendored-config shim, held-out guard (`@outcome_fn`) |
| `src/population.py` | step 1: frozen population + replacement rule, fold checks, sealed ids |
| `src/prep.py` | step 2: c-papers of all 426 concepts, author index, per-10⁴ denominators |
| `src/attach.py` | step 3: attachment to the prebuilt snapshots, Burt constraint / effective size, cross-community pairs |
| `src/indicators.py` | step 4: vendored indicators, reproduction gate + code-equality run, E_up labels |
| `src/openness.py` | step 5: R1a residualisation (`closure_res`, `_imp`, `_H3`, W1 mean), z-scaling, F3 decision |
| `src/features.py` | step 6: W1 baselines (growing-edge breadth, momentum, Rafols coherence, ...) |
| `src/outcomes.py` | step 7: W2 outcomes Y1/Y1r/Y1r20/Y2/Y3/Y3b and the mediator |
| `src/stats_core.py`, `src/models.py` | step 8: OLS + cluster bootstrap, grouped CV, robustness, mediation, sanity checks |
| `src/power.py`, `src/freeze.py` | step 9: MDE simulation, held-out spec freeze |
| `src/outputs.py` | step 10: `method_out.json`, figures, `results_summary.json`, this README |
| `confirm_heldout.py` | iteration-4 held-out confirmation (refuses without the frozen hash and `AII_OPEN_HELDOUT=iter4`) |
| `audit_rederive.py` | independent re-derivation of the headline numbers |
| `vendor/` | exp_3 code, copied verbatim (+ `SHA256SUMS`) |
| `tests/` | openness == networkx, guard, outcomes toy cases, confirmation refusal paths |
| `method_out.json` (+ `mini_`/`preview_`) | exp_gen_sol_out: one example per screen (c, t) row of each primary model, with OOF BASE / FULL predictions |
| `results_summary.json` | all headline numbers, read from `results/` |
| `results/population/` | hydrated MAIN population (+ sha256), sealed ids |
| `results/reproduction/` | reproduction gate and code-equality tables |
| `results/indicators/` | per-(concept, year) indicators on the hydrated corpus, E_up labels |
| `results/openness/` | `openness_ct.parquet` (D3 merge: per screen (c, t) openness), `r1a_fit.json` |
| `results/d1/` | features, outcomes, panel, coefficient tables, CV ΔR², robustness, mediation, partial dependence, verdict |
| `results/power/mde.json`, `results/heldout/` | MDE curves; frozen held-out spec + sha256 |
| `sealed/` | held-out W1 rows only (no outcomes), with sha256 |
| `figures/` | fig1 reproduction, fig2 forest, fig3 ΔR², fig4 partial dependence, fig5 mediation, fig6 power (PDF + PNG) |
| `logs/` | run logs, `freeze_log.txt`, pytest log |
| `work/` | regenerable intermediates (c-papers, author index, per-year pool metrics) |

## How to run

```bash
uv venv .venv --python=3.12 && uv pip install --python .venv/bin/python -r pyproject.toml
.venv/bin/python -m pytest -q                 # vendored + repo tests
.venv/bin/python method.py --stage all        # ~12 min on 4 CPUs, RAM < 6 GB
.venv/bin/python audit_rederive.py
```

The dependency artifacts are read in place, read-only, from the run tree: `round-2/experiment-3/src`,
`gen_art_dataset_5`, `gen_art_experiment_1` and `round-1/dataset-1/src`, all relative to the invention
loop root.

## Restoring removed files

`.aii/manifest.yaml` marks only `.venv/` for deletion (redownloadable). Restore it with:

```bash
uv venv .venv --python=3.12 && uv pip install --python .venv/bin/python -r pyproject.toml
```

`work/` (50 MB: c-papers, author index, per-year pool metrics) is **kept** on the run volume, because
`confirm_heldout.py` reads it in iteration 4. If it is missing, rebuild it in about 4 min with
`.venv/bin/python method.py --stage population prep attach indicators openness`. `__pycache__/` folders are recreated
automatically by Python.
