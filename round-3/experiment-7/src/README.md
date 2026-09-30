# Do borrowed ideas stick when grafted locally? RQ2-D2 host-entry test

This experiment covers iteration 3, plan `gen_plan_experiment_3`. It asks what happens when an emerging concept c first
appears in a subfield d other than its origin o(c) (a *host entry* in year e). Its entry-year host papers may pair it
with partners that are **native to the host** (*anchoring / grafting*, A). They may instead carry the concept's **own
origin companions** along (*co-transfer / toolkit*, CT). The test is which of the two predicts that **newcomers**
(authors disjoint from the concept's prior author and co-author set) take the concept up in the host over the next five
years (W2 = [e+1, e+5]).

It runs on CPU only, costs $0 and uses no API. It is built on the hydrated 426-concept corpus (`gen_art_dataset_5`).
The pre-registration was frozen before any outcome was computed (`results/d2_prereg.json`, sha256 f800a0a9…9f74). The
held-out fold (119 main-arm concepts) stays **sealed**. `heldout_spec.json` (sha256 8db17113…ca7c) and the hash-checked
`confirm_heldout.py` let iteration 4 open it exactly once.

## Headline results (screen fold; MAIN population, entries with ≥ 5 distinct partners)
* **Reproduction.** The iteration-1 graft-fallback events are reproduced exactly: 2,347 / 2,154 / 2,000, with row-level
  equality (`results/repro_events_iter1.json`). Origins agree with the modal F..F+2 subfield for 366/366 concepts.
* **Events.** The corpus has 4,177 main-arm host entries (3,584 with ≥ 5 partners). The primary sample is 1,746 screen
  MAIN entries in 184 concepts (1,740 with complete controls). Held-out: 1,100 entries in 93 concepts (W1 features only).
* **Anchoring is rare, and entry is mostly a package.** Only 1.1 % of profiled partner tags are ≥ 50 % host-native (3.3 %
  at ≥ 0.3). As pre-declared for a native rate < 5 %, the primary A is therefore the continuous **A_cont**: the
  tag-weighted mean share of the partners' pre-entry works that lie in d (mean 0.043, SD 0.055). The partition of
  entry-year tags at native ≥ 0.3 is: graft 1.8 %, native companion 0.9 %, **package 69.6 %** (non-native origin
  companions), third party 27.7 %; 24 % of tags are unprofiled. Mean CT = 0.61.
* **Primary FE (concept × e + d × e)** — a within-concept-year comparison of hosts entered in the same year:
  * Only 452 of 1,740 events (26 %) survive singleton/separation pruning, in 77 concept clusters. This triggers the
    pre-declared **fallback 3**, which makes the secondary spec **co-primary**.
  * A_cont: IRR per SD **1.39** [0.97, 1.99], CRV1 p = 0.074 (Holm 0.149), wild p = 0.032.
  * CT: IRR per SD 1.04 [0.72, 1.50], p = 0.85.
  * Reading: **NEITHER**.
* **Co-primary FE (concept + e + d)**, 1,544 events, 140 clusters:
  * A_cont: IRR per SD **1.30** [1.16, 1.45], CRV1 p = 6e-6 (Holm 1.3e-5), wild p = 0.001.
  * CT: IRR per SD 1.05 [0.92, 1.21], p = 0.48.
  * Reading: **GRAFTING**.
* **Pre-declared coarsenings:**
  * Concept + d × e: IRR per SD 1.22 [1.05, 1.40], Holm p = 0.015, reading **GRAFTING**.
  * Concept × 2-year bin + d × e: IRR per SD 1.10 [0.83, 1.46], reading NEITHER.
* **Co-transfer (toolkit) is null in every specification.** There is no package penalty either.
* **Robustness** (`results/d2_robustness.csv`, `figures/F4_robustness_forest`, 27 variants × 2 FE):
  * Co-primary spec: the A_cont effect holds for STRICT, SENSITIVITY, route B only, route interaction, excess anchoring
    (A_cont − A0_cont), the lower coverage bound, coverage ≥ 0.6, entry topic_score ≥ 0.9, e ≤ 2018, CT_any, the
    pre-period-selected profile set, Y_all / Y_lenient, the direct-author newcomer rule and the [e, e+1] partner window
    (IRR per SD 1.25–1.56, all p ≤ 0.001).
  * The one co-primary exception is excluding single-paper entries: 200 events in 50 clusters, 1.24, p = 0.17.
  * Primary spec: it stays at p ≈ 0.05–0.2.
  * **Binary** native shares at 0.5 / 0.7 are null, being too rare. At 0.3 the co-primary gives 1.11 (p = 0.007).
  * Descriptive strata: the effect is carried by the "other" origin fields (math, materials, engineering): 1.29,
    p = 0.001. **Physics/Astro is null** (0.99) and CS is weak (1.15, p = 0.11).
* **Placebo.** Nativeness was permuted 500 times, with node label vectors permuted across subfields.
  * The placebo is centred on 0: mean z = 0.01 / −0.02, with z SD 1.26 / 1.38, so CRV1 is mildly anti-conservative.
  * Co-primary: observed z = 4.69, permutation p = 0.002.
  * Primary: z = 1.81, p = 0.15.
  * The within-cell label shuffle gives p = 0.02 (co-primary) and 0.16 (primary).
* **Graft labels** (entry-year lower 90 % bound on the native ≥ 0.3 share, compared with the reference-arm host median,
  which is 0 for 99 % of hosts). 15.3 % of screen entries are anchored. Raw establishment is 0.44 when anchored vs 0.20
  when not (diff 0.23 [0.18, 0.30], concept bootstrap). Newcomer papers per entry paper are 6.3 vs 2.0. Of the hosts
  still active at e+5, 26 % are anchored entries (vs 16 % of all entries). Anchored hosts carry 34 % of the concepts'
  W2 host entropy, while they make up 22 % of the concepts' host entries.
* **Out-of-sample prediction** (grouped-by-concept 5-fold; descriptive). Adding A and CT lowers the out-of-fold Poisson
  deviance by 0.23 per event [−0.54, 0.06]; Spearman goes from 0.419 to 0.431. The gain is modest and not significant.
* **Held-out power.** The held-out design has 93 concepts and 1,100 entries.
  * Co-primary spec: MDE (80 %) = IRR per SD **1.15**, below the screen 1.30, so it is adequately powered.
  * Primary spec: power is 27 % at 1.40, so no MDE is reached on the grid. A held-out null there is declared
    *inconclusive (underpowered)* in advance (`heldout_spec.json` → `power`).
* **Checks.**
  * pyfixest cross-check: coefficients agree to about 1e-9 and SEs within 1e-3 (`results/pyfixest_crosscheck.json`).
  * `audit_rederive.py` recomputes A_cont, CT and Y_strict for 20 random events with plain loops from the raw files:
    all match. It also re-derives the headline b_A with pyfixest (4.7391 vs 4.7391) and the establishment-by-label
    rates with plain pandas (exact match).
  * Shuffled input: Y_strict was permuted within concept 40 times and refitted with pyfixest. None of the 40 reach the
    observed |z| = 4.69. At p < 0.05, 10 % reject, which is the same CRV1 over-rejection the placebo shows.
  * `confirm_heldout.py --dry-run` reproduces the screen M1 coefficients bit for bit, and it refuses a one-byte edited
    spec.
  * 8 unit tests pass, including the sealing mutation test.

**Reading.** Across concepts, host entries whose entry-year partners are more host-native establish more newcomer
uptake. Concept + year + host FE give +30 % per SD. The effect survives the confounds a reviewer names first: host-wide
shocks, classification confidence, relatedness density, demic carriers, coverage and profile selection. It also
survives a nativeness-permutation placebo. It is **not** identified *within* a concept-year: that comparison is thin
(26 % of events retained) and underpowered. So the evidence is for *grafting across a concept's entries at different
times and hosts*, not between simultaneous entries. Carrying the origin toolkit (CT) neither helps nor hurts.
Substantively, entry is overwhelmingly a package: 70 % of partner tags are non-native origin companions. Truly native
grafts are rare, but where they occur, the concept sticks. The effect is absent for physics/astronomy concepts.

## Layout
| Path | What |
|---|---|
| `method.py` | Runs stages 0-16 (`--stage N`, `--mini`). |
| `src/config.py` | Paths, frozen SPEC, sealing guard (`assert_not_sealed`), `detect_cpus`, `set_ram_limit` (vendored from exp_3). |
| `src/io_load.py` | Stage 1: compact cache of dataset_5 (partners = dataset_5 node rule, level ≥ 1; dup_group dedup). |
| `src/population.py` | Stage 2: frozen replacement rule → MAIN 302 / STRICT 292 / SENSITIVITY 366 / REFERENCE_ACCEPTED 42; folds; sealed ids. |
| `src/events.py` | Stages 3a (row-level reproduction) and 4 (events). |
| `src/features.py` | Stage 5: W1 features — A, A_cont, thresholds, bounds, A0, CT, partition, controls. |
| `src/outcomes.py` | Stage 6: author-disjoint W2 outcomes (sparse co-author index; guarded). |
| `src/models.py`, `src/ppml.py` | Stage 7: PPML (ppml.py vendored unchanged from exp_2), Holm, decision, pyfixest cross-check. |
| `src/robustness.py`, `src/placebo.py`, `src/labels.py` | Stages 8, 9, 10-11. |
| `src/assemble_out.py`, `src/power.py`, `src/freeze.py`, `src/figures.py`, `src/summary.py` | Stages 12-16. |
| `confirm_heldout.py`, `heldout_spec.json`, `heldout_spec.sha256` | The frozen held-out confirmation (iteration 4). |
| `audit_rederive.py` | Independent plain-loop re-derivation. |
| `method_out.json` (+ `full_`/`mini_`/`preview_`) | exp_gen_sol_out: 1,740 screen entry events. `predict_baseline` = out-of-fold M0, `predict_method` = M0 + A + CT. |
| `results/` | `d2_summary.json` (headline, with a source file per number), `d2_models.json` / `d2_models_table.csv`, `d2_robustness.csv`, `placebo_*`, `labels_summary.json`, `graft_labels_screen.parquet`, `d3_concept_anchoring.parquet`, `power_heldout.json`, `oos_check.json`, `events_all.parquet`, `features_screen.parquet`, `screen_events_with_outcomes.parquet`, `deviations.md`, `d2_prereg.json`. |
| `sealed/` | Held-out W1 features, graft labels and D3 export, each with a sha256. No outcomes. |
| `figures/` | F1/F2 binned within-FE response, F3 partition by establishment, F4 robustness forest, F5 placebo, F6 power (PDF + PNG). |
| `tests/` | `test_d2.py` (sealing + mutation, grep, blocks, toy anchoring, newcomer rule, 3-FE PPML recovery), `test_ppml_vendored.py`. |
| `logs/` | Stage logs, `prereg_freeze.log`, `freeze.log`, `timings.json`. |

## How to run
See `reproducibility.md`. In short: `uv venv .venv --python=3.12 && uv pip install --python .venv/bin/python -r
pyproject.toml`, then `.venv/bin/python -m pytest -q -c pytest.ini tests`, then `.venv/bin/python method.py` (about
15 min on 4 CPUs).

## Deviations and limitations
All deviations are listed with reasons in `results/deviations.md`: the nativeness fallback, event counts, the RD basis,
the A0 window, the placebo statistic, fallback 3, route_A in the secondary spec, and the PPML tolerance. The
limitations:
1. **Vocabulary.** Partners are OpenAlex legacy-concept tags (the only vocabulary with exact profiles), not the run's own
   grounded concepts.
2. **Coverage.** 74 % of entry-year tags (tag-weighted) are profiled. Bounds and the coverage ≥ 0.6 subset are reported;
   the upper bound (unprofiled share = 1) is uninformative by construction.
3. **Field mix.** The pool is physics / CS / materials skewed (arXiv-mined), and the effect is null in physics.
4. **Newcomer rule.** Co-authorship is observed within the corpus only. The direct-author variant gives the same answer.
5. **W2 truncation.** W2 for e = 2019 ends in 2024; e ≤ 2018 gives the same answer.
6. **Standard errors.** CRV1 is mildly anti-conservative (placebo z SD about 1.3), so read the wild bootstrap and
   permutation p values alongside it.
7. **Snapshot indicators.** The exp_3 snapshot indicators are not used (distinct-partner centrality instead), so the
   exp_3 indicator reproduction check is N/A.

## Restoring removed files
Entries marked `delete` in `.aii/manifest.yaml` are removed after the round. To restore them:
* `.venv/`: `uv venv .venv --python=3.12 && uv pip install --python .venv/bin/python -r pyproject.toml` (exact pins in
  `requirements.lock.txt`).
* `results/cache/prepared.pkl`: `.venv/bin/python method.py --stage 1` (about 10 s from the dataset_5 files).
