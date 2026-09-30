# Do adopters already speak the partner language?

This is an adopter-level test of the absorptive-capacity mechanism behind the D2 host-share effect. D2's result is A_cont, with a co-primary IRR/SD of 1.30. The test was run on the **screen fold only**, so every number here is *screen-fold mechanism evidence, not confirmation*. Exposure is measured from the 463k-work corpus, and every exposure row is labelled **"corpus-exposure, coverage-limited"**. Iteration 4, gen_art_evaluation_5.

## Question
D2 found that host entries whose partner concepts are already host-native attract more author-disjoint newcomer uptake. If this reflects concept-level absorptive capacity, then the **actors** who adopt c in host d should already have used c's partner vocabulary before the entry year e. They should do so more than matched host authors who did not adopt.

## Design, all frozen and hashed before any exposure was read
- **Cases.** Newcomer adopters are authors of the W2 = [e+1, e+5] d-papers of c that are counted in `Y_strict`, i.e. papers with no author in Pset(c,e). The source is the 1,544 co-primary entries (140 concepts) of art_2Cd2JJypeGuA. The exp_7 code (`vendor/`) is byte-identical to the original, and its sha256 values are in `vendor/SHA256SUMS`.
- **Controls.** Controls are drawn by incidence-density sampling from in-corpus authors with a d-paper in the adoption year.
  - Excluded: Pset(c,e), every c-author 2000-2024, and every adopter of the same entry.
  - Exact match on four bins: prior-corpus-works bin, team-size bin, host-activity bin and first-year bin. A fixed relaxation order applies when no exact match exists.
  - Per case: 1 control plus 2 reserves. The reserves are used in the 1:3 supplementary.
- **Caps.** At most 6 cases per entry and 25 per concept, with a target of 500 per A_cont tercile and a hard cap of 1,500. The result is **1,013 matched strata** from 422 entries and 109 concepts.
- **Targets.** Partners P are the top-60 partners of each entry. They are classed NATIVE / ADJACENT / FOREIGN / UNPROFILED using G2's cut points (0.3, 0.05), with an origin-companion flag. Two comparison sets sit beside them:
  - NEG: up to 20 frequency-matched negative-control concepts.
  - PLAC: up to 20 placebo partners, taken from another concept's entry into the same host with |e'-e| <= 1.
- **Exposure.** Use of these concepts in the member's corpus works published **<= e-1**, excluding c-papers, under the vendored partner-tag rule.
- **Freeze.** `mech_spec.json` records the rules, formulas, reading rules and sha256 of every input and frame. Its hash is `mech_spec.sha256` (96e697c6…). `mech_spec_power.json` holds the simulated MDEs and was written before exposure. The analysis refuses to run if either hash differs.

## Headline results
All ORs below come from conditional logit with a 95% concept-cluster bootstrap CI (B = 1,000). In the vocabulary tables, "vs FOREIGN" means the OR ratio against FOREIGN with its bootstrap CI.

**Primary enrichment (M-i).** This is the primary estimand.

| | Value |
|---|---|
| OR(E_any \| E_neg, prior) | **3.09 [2.32, 4.28]** |
| Exposure prevalence, cases vs controls | 0.79 vs 0.61 |
| Discordant pairs | 354 (268 vs 86) |
| Negative-control OR (NEG) | **0.62 [0.49, 0.77]** |
| Placebo OR (PLAC) | **0.72 [0.57, 0.90]** |
| OR_partner / OR_neg | 5.02 [3.45, 7.51] |
| OR_partner / OR_plac | 4.53 [3.05, 7.21] |
| Swapped partner set (label shuffle) | 1.11 [0.86, 1.39] |
| Permutation null | mean OR 1.00 (95% range 0.80-1.27) |
| LPM check (pyfixest, stratum FE, CRV1 by concept) | +0.50, p 4e-14 |
| statsmodels ConditionalLogit | identical to within 7e-5 |

Match balance: every SMD is at most 0.032 after matching; before matching they reach up to 0.38. The attributable fraction among exposed cases is 0.53.

**Pre-declared reading: SUPPORT.** All three SUPPORT criteria are met. Adopters used c's specific partner vocabulary before e, and they are *less* likely than matched host authors to use generic host vocabulary (NEG) or another concept's partner vocabulary (PLAC). The ACTIVITY-ARTEFACT and GENERIC-HOST-VOCABULARY readings are both rejected.

**Interaction with A_cont (M-ii).**
- OR ratio per SD of A_cont: 0.87 [0.70, 1.14], so **enrichment is uniform across A_cont**. The MDE80 for the ratio is 1.3.
- Tercile ORs:

| Tercile | n | OR (95% CI) | MDE80 |
|---|---|---|---|
| T1 | 114 | 3.55 [1.85, 10.4] | ~3.0 |
| T2 | 238 | 4.18 [2.26, 8.46] | ~2.0 |
| T3 | 661 | 2.74 [1.90, 4.16] | ~1.5 |

**Vocabulary class (M-iii).** These readings were not pre-declared as outcomes, and are reported as-is.

| Partner class | OR (95% CI) | vs FOREIGN |
|---|---|---|
| NATIVE | 1.47 [1.02, 2.33] | 0.51 [0.33, 0.89] |
| ADJACENT | 1.91 [1.43, 2.73] | 0.66 [0.47, 0.96] |
| FOREIGN | 2.88 [2.28, 3.69] | — |
| UNPROFILED | 2.71 [1.33, 7.54] | — |

| Companion split | OR (95% CI) |
|---|---|
| Origin-companion partners | 3.10 [2.38, 4.26] |
| Non-companion partners | 1.36 [1.02, 1.87] |
| Ratio | 2.27 [1.64, 3.21] |

The FOREIGN > NATIVE contrast has a CI that excludes 0. At the adopter level, the enrichment is carried by c's origin-side / companion vocabulary, **not** host-native vocabulary. This contradicts a literal "grafting" reading at the actor level: adopters tend to be boundary-spanners who already know c's toolkit. It sits beside the entry-level null for CT.

**Supplementary origin-subfield check (added after the mini run; not pre-declared).**
- 30% of cases vs 12% of controls had earlier corpus work in c's origin subfield.
- Partner enrichment survives conditioning on this: OR **2.52 [1.91, 3.43]**. FOREIGN > NATIVE persists.

**Entry-level mediation (M-iv; co-primary PPML, all 1,544 entries).** The quantity reported is the attenuation share, (b_base - b_full) / b_base, where b_base = 4.739.

| Mediator added | Attenuation share (95% CI) |
|---|---|
| +M2 (pre-exposed host-author pool) | **0.05 [-0.08, 0.23]** |
| +M1 (exact OpenAlex prevalence) | 0.01 [-0.14, 0.25] |
| +M2_share | -0.01 [-0.26, 0.29] |
| +M2 native/adjacent (Gelbach) | -0.37 [-0.97, 0.31] (suppression; Gelbach terms sum to the movement, -1.772 vs -1.768) |

- The mediation MDE80 is 20% (joint significance). So **A_cont is not reducible to pool size**, and a mediated share of 30% or more is unlikely.
- Reverse attenuation: A_cont removes 68% [21%, 285%] of M2's own association with Y. M2 alone has IRR/SD 1.33, p 0.003.
- Mediator validation: Spearman 0.56 between M2_share and control exposure prevalence (359 entries with at least 3 controls); M2 vs M1 0.34.

**Supplementary robustness (E_any OR):**

| Variant | OR (95% CI) |
|---|---|
| 1:3 matched | 2.96 [2.29, 3.99] |
| Expanded frame, no concept cap (1,541 strata) | 2.62 [2.17, 3.45] |
| Physics/Astro | 3.87 [1.52, 12.7] |
| CS | 3.46 [2.52, 5.06] |
| Other fields | 2.72 [1.81, 5.02] |
| Single-paper entries | 3.59 |
| Multi-paper entries | 2.33 |

Including c-papers in the exposure window gives an identical result.

**Power, frozen before exposure.** The primary-OR MDE80 is 1.5 on the grid; power at OR 1.3 is 0.72-0.79 for p0 >= 0.25.

## Deviations from the plan (and why)
1. **OpenAlex exposure was not pulled.** Key-wide remaining credits were 2,757 at the first check (below the plan's 4,000 threshold) and 484-563 at pull time (below the 2,500 reserve kept for G4 and other agents). The guard blocked every paid call and **0 credits were spent** (`results/api_results.json`). Corpus exposure is therefore primary, as the plan pre-declares. The API validation subsample (kappa) and the `/authors` productivity covariate could not run. The rate variant, which needs the API `meta.count`, was not run.
2. **Coverage.** 87% of all 21,941 adopter pairs have no corpus work <= e-1 ("career-new in the corpus"), so their exposure cannot be measured. Before freezing, the design was adapted as follows:
   - cases restricted to exposure-measurable adopters;
   - controls required to have at least 1 prior corpus work;
   - the prior-works bin added as an exact match variable.
   The productivity covariate is log1p(prior corpus works). The generalisation therefore covers adopters already active in the pool's topic space.
3. Tercile T1 had only 114 measurable cases available after caps, so the shortfall went to T3 and the total is 1,013 rather than 1,500.
4. The productivity-floor reserve rule is moot, because all controls have prior works. The reserves feed the 1:3 supplementary instead.
5. The origin-subfield check and the FOREIGN > NATIVE reading label were added post hoc, and are marked as such.
6. Mediation power uses joint significance (a fixed A->M2 path plus CRV1 on M2). The size at share 0 is 0.08; exp_7 already noted that CRV1 is mildly anti-conservative.
7. **Interpretation limit.** Prior use of c's partners is equally consistent with plain topical proximity (adopters were already working next to c). The design separates it from generic host vocabulary (PLAC, NEG), from activity and from origin-field membership. It does not separate it from topical relatedness itself.

## Layout
| Path | What |
|---|---|
| `eval.py` | Orchestrator, with stages `prepare`, `frame`, `freeze`, `pull`, `analyze`, `extra` and `assemble`. |
| `src/mech_common.py` | Paths, vendored imports and the reproduction gate. |
| `src/frame.py` | Cases, risk-set controls, target sets and entry mediators M1/M2. No exposure is read. |
| `src/power_sim.py` | Simulated MDEs: pairs, interaction and mediation. |
| `src/api_pull.py` | Blind, guarded OpenAlex client. |
| `src/stats_core.py` | Conditional logit and bootstrap helpers. |
| `src/analysis.py` | Exposures, model suite, bootstrap and mediation. |
| `src/figs.py` | Figures. |
| `vendor/` | exp_7 `config, io_load, features, outcomes, ppml, models`, byte-identical, with `SHA256SUMS`. |
| `mech_spec.json`, `mech_spec.sha256`, `mech_spec_power.json` | Frozen spec, its hash and the pre-exposure MDEs. |
| `frames/` | Frozen frames: `entries`, `strata_long`, `strata_long_expanded`, `targets`, `cases_all`, `risk_balance_pre*`, `api_jobs` (blind) and `api_jobs_key`. |
| `results/mechanism_results.json` | Every number. |
| `results/{enrichment,interaction,vocab_class,mediation,match_balance,permutation,ratios,supplementary,power}.json`, `results/model_terms.csv` | Per-analysis results. |
| `results/exposures_{primary,expanded}.parquet` | Per-member exposure indicators. |
| `results/gate.json`, `results/frame_summary.json` | Reproduction gate: b_A 4.739106, N 1,544, G 140, pass. Frame summary. |
| `results/api_results.json`, `ledger.jsonl` | API stop record, 0 credits. The ledger is absent because nothing was charged. |
| `eval_out.json`, `mini_eval_out.json`, `preview_eval_out.json` | exp_eval_sol_out output. Contains 2,026 stratum-member rows and 1,544 entry rows. |
| `figures/F1_forest_ORs` | Forest plot of ORs. |
| `figures/F2_OR_by_Acont_tercile` | OR by A_cont tercile. |
| `figures/F3_exposure_prevalence` | Exposure prevalence, cases vs controls. |
| `figures/F4_attenuation_bootstrap` | Bootstrap distribution of the attenuation share. |
| `figures/F5_power_curves` | Power curves. Each figure is saved as .png and .pdf. |
| `full_eval_out.json` | aii-json full variant of `eval_out.json`. |
| `audit_rederive.py`, `results/audit_rederive.json` | Independent re-derivation from the raw parquet files. Exposure agreement 1.000; statsmodels OR 3.095; McNemar 3.12; pyfixest attenuation 0.052. Shuffled and random placebos fail as they should. |
| `reproducibility.md`, `requirements.lock.txt` | Exact steps and the 76 pinned packages. |
| `logs/` | Run logs and timings. |
| `sealed/` | Empty folder created by the vendored `config.py`. No held-out data is ever written here. |

Inputs are read-only sibling artifacts, resolved from the invention-loop root (`AII_DEPS_ROOT`, default three levels up):
- art_2Cd2JJypeGuA (`round-3/experiment-7/src/results/`);
- art_eR1Z7fMlOcxs (`round-2/dataset-5/src/`).

## How to run
```bash
uv venv .venv --python=3.12 && uv pip install --python .venv/bin/python -r pyproject.toml
.venv/bin/python eval.py --stage prepare    # ~15 s; stops unless b_A = 4.7391 (1e-4), N 1544, G 140
.venv/bin/python eval.py --stage frame      # ~2 min
.venv/bin/python eval.py --stage freeze     # ~6 min (writes mech_spec.json + MDEs; re-freezing changes the hash)
.venv/bin/python eval.py --stage pull       # guarded; needs OPENALEX_API_KEY (never written to outputs)
.venv/bin/python eval.py --stage analyze    # ~13 min on 4 CPUs (B = 1000)
.venv/bin/python eval.py --stage extra      # supplementary origin-subfield check (~20 s)
.venv/bin/python eval.py --stage assemble   # tables, figures, eval_out.json from saved results
.venv/bin/python make_variants.py           # mini / preview eval_out
```
Seeds are recorded in `mech_spec.json`. The frame seed is 20260929.

## Restoring removed files
| Removed path | Restore with |
|---|---|
| `.venv/` | `uv venv .venv --python=3.12 && uv pip install --python .venv/bin/python -r pyproject.toml` |
| `results/cache/` (`prepared.pkl` 156 MB, `author_raw_ids.npy`) | `.venv/bin/python eval.py --stage prepare`. This needs the dataset_5 sibling folder. |
| `src/__pycache__/`, `vendor/__pycache__/` | Python recreates them automatically on the next import, e.g. `.venv/bin/python eval.py --stage assemble`. |

`frames/` and `api_cache/` are kept as ordinary files. They are small enough that they need no manifest entry. `api_cache/` is empty because no paid call was made. No file in this folder is 100 MB or larger apart from the regenerable cache.
