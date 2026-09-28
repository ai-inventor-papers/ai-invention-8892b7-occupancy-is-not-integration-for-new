# Do network signs of emergence replicate in medicine? — RQ1 on 191 held-out MeSH concepts

This artifact re-runs the pre-declared RQ1 network-precursor test on a second, independent population. The population
is 191 new biomedical concepts (new MeSH descriptors, 2004-2018, text-novel, F = 2005-2016). The test uses only
concept–concept co-occurrence network indicators. It has two blocks:

1. **Plan-native block** (`rq1_spec.py`): the procedure written in the plan.
2. **Main-pool-aligned block** (`rq1_spec.MAINPOOL`): the sibling iteration-2 main-pool RQ1 run
   (`gen_art_experiment_3`) was found during this run. Its label variants (E / E_alt / E_up), its precursor
   operationalisations (rarefied accretion shift, weighted Chung-Lu closure, rarefied participation) and its
   event-study convention were recomputed here with its own metric code. That code is vendored read-only in
   `vendor/mainpool_lib_metrics.py` (sha256 in `results/prereg_spec.json`). Both populations can therefore be compared
   row by row (`results/side_by_side_mainpool_vs_mesh.csv`).

No API or LLM calls were made ($0), and everything ran on CPU. The features were frozen and hashed before any outcome
(W2 = t+1..t+5) was computed; the outcome stage refuses to run if the hashes do not match.

## Pipeline (what was computed)

**Step 1 — Load.**
- 191 concepts.
- 92,063 primary concept–work rows: `verified_text_match` and not `mesh_indexed_only`.
- Checks:
  - The works-derived yearly counts equal `yearly_counts_textmatch` for 100% of concept-years.
  - Tag-id overlap with the legacy-concept vocabulary is 1.00 (0.989 with the background sample).
  - 22 legacy-concept "twins" of MeSH concepts were removed from focal edges.

**Step 2 — Snapshots.** There are 25 yearly snapshots (2000–2024), each a 3-year trailing window over the
design-weighted background sample (259,716 works, post-stratified `w_year = n_frame/n_sampled`).
- The weighted totals match the frame totals exactly.
- Snapshot size (median): 27k nodes and 463k edges.
- Communities: best-of-5 Leiden (RB configuration, resolution 1, association-strength weights); 257–430 communities.
  Seed-to-seed NMI is 0.72–0.80.
- Focal MeSH nodes are attached as a census from their works in the same window. Focal co-tags must have W_cj ≥ 2;
  9.1% of those co-tags are not in the window's background vocabulary and are dropped.

**Step 3 — Indicators.** There are 4,775 concept-years (3,589 with a network):
- strength, degree, all-node and focal percentile, growth;
- new-relation rate, neighbourhood novelty;
- Baselga β_sor/β_sim/β_sne and accretion share;
- top-20 closure vs Chung-Lu (`closure_lr`), with a degree-preserving rewiring z on a seeded 10% subsample (391 units);
- participation P, within-module z, networkit betweenness (500 pivots);
- first differences, community-change flags (Jaccard-matched ids);
- per-paper (`_pp`) and volume-residualised (`_volres`) versions;
- Kleinberg burst (s = 2, γ = 1, whole-science denominators, recomputed on years ≤ t);
- the entropy family (flagged BIASED: 178/191 concepts have PubMed-only works);
- plus the main-pool-aligned columns.

Sanity check (T6): corr(all-node percentile, log papers) = 0.81.

**Steps 4–8.** These are:
- labels under three volume definitions (PRIMARY = verified text match; SENS1 = + non-PubMed group_by counts;
  SENS2 = MeSH-indexed, dropped before DateEstablished);
- 1:3 matched controls (same F-band and origin field, ±20% volume, widened to ±30%);
- the event study (2,000 concept-bootstrap reps, Holm over 3 precursors, permutation MDE);
- rolling-origin prediction (train t ≤ T−5) plus the labelled grouped-CV secondary;
- the three fixed pattern rules.

## Headline results

All numbers below come from `results/` (`replication_verdict.json`, `rq1_effects*.csv`, `rq1_prediction.csv`,
`rq1_patterns.csv`, `analysis_summary.json`).

**1. The plan-literal centrality label is structurally infeasible here.** This was declared before any outcome was
opened.
- Every sampled legacy tag stands for hundreds of population works, so focal MeSH nodes sit at the 1.8th percentile of
  weighted degree among all nodes (median; 99th percentile = 34).
- The all-node label therefore yields only 17 positive units, 6 onsets and 5 matched concepts.
- The PRIMARY E_cent therefore ranks strength among the MeSH focal nodes of each snapshot (`E_CENT_REFERENCE="focal"`,
  = the main pool's E_alt). The all-node label is still reported (`E_cent_allnodes`, main-pool E).
- The main pool hit the same wall independently: 4 onsets under its primary E.

**2. Plan-native event study (PRIMARY, E = uptake AND focal-percentile gain ≥ 20).**
- There are 18 emerging concepts, 15 matched with data in rel −3..−1. Match rate at ±20% is 0.39 and at ±30% is 0.72.
- Statistic D = mean (emerging − matched) over rel −3..−1:

| precursor | D [95% CI] | Holm p | MDE (SD) | verdict |
|---|---|---|---|---|
| accretion_share | +0.094 [−0.036, 0.210] | 0.48 | 0.43 | not detected |
| closure_lr (Chung-Lu) | −0.086 [−0.511, 0.402] | 0.68 | 0.56 | not detected |
| dP (participation rise) | +0.025 [−0.017, 0.073] | 0.51 | 0.46 | not detected |

- The sensitivities agree: rule_parity (n = 14), t ≤ 2018 (identical, with no right-censoring effect) and
  domain-coarsened matching all have CIs that include 0.
- **SENS1** (+ non-PubMed volume, n = 29): **closure_lr is lower before emergence, D = −0.42 [−0.74, −0.11], Holm
  p = 0.039.** This is the same direction as the main pool's closure finding. The volume-residualised version is
  −0.32 [−0.55, −0.08].
- **E_cent only** (centrality gain, n = 30): dP = +0.051 [0.014, 0.087], Holm p = 0.015. This is descriptive.
- Exploratory (BH over all indicators, PRIMARY): the participation **level** P is higher before emergence, +0.054
  [0.025, 0.092] = 0.37 SD, q < 0.001; the volume-residualised version is +0.052. The *rise* dP is not.
- T5 permutation null (200 onset permutations within F-band): |mean D| < 0.25 bootstrap SE for all 3 precursors,
  as required.

**3. Main-pool-aligned block, side by side** (S = mean over rel −3..0, never-emerging controls, vol3 caliper).
Full rows are in `results/side_by_side_mainpool_vs_mesh.csv`. The verdict uses the pre-declared F5 rule (fewer than
15 → underpowered) applied to the *effective n*: treated concepts with data in the summary window.

| label | precursor | MeSH S [CI] (n_eff) | main pool S [CI] (n) | verdict |
|---|---|---|---|---|
| E | accretion_shift_rar | +0.044 [0.004, 0.129] (5) | −0.104 [−0.120, −0.016] (3) | underpowered in both |
| E | closure | +0.49 [−0.61, 1.58] (5) | −0.63 [−0.66, −0.59] (3) | underpowered in both |
| E_alt | accretion_shift_rar | +0.049 [0.010, 0.095] (3) | −0.021 [−0.034, 0.093] (10) | underpowered (rarefaction needs ≥ 10 papers/yr) |
| E_alt | closure | +0.08 [−0.30, 0.48] (17) | −0.40 [−0.92, 0.19] (10) | null in both |
| E_alt | P_rar | +0.029 [0.001, 0.059] (17), Holm 0.088 | −0.044 [−0.227, 0.102] (10) | null after Holm |
| E_up | accretion_shift_rar | +0.043 [0.007, 0.069] (12) | −0.140 [−0.185, 0.018] (21) | underpowered in MeSH |
| **E_up** | **closure** | **−0.18 [−0.50, 0.11] (51)** | **−0.84 [−1.26, −0.43] (21)** | **same sign, not significant in MeSH**; IVW pooled −0.41 (SE 0.125), heterogeneity Q = 6.2 |
| E_up | P_rar | +0.017 [−0.004, 0.037] (51) | −0.007 [−0.066, 0.056] (21) | null in both |

- The "significant" MeSH accretion-shift rows rest on 3–12 concepts: the rarefied Baselga is NA for 63% of networked
  concept-years. They are *not* evidence for accretion.
- Exploratory rows (BH q < 0.1, n ≥ 10): burst state is higher before E_alt and E_up onset (+0.35 and +0.21, q = 0.009).
  Before E_up onset the new-relation rate (+0.054) and strength growth (+0.14) are higher, while the centrality
  percentile is lower. This profile of **open, fast-renewing neighbourhoods plus a burst** matches the main pool's
  exploratory profile.

**4. Prediction — the precursors add no out-of-sample value beyond frequency/burst + degree/centrality.**
- PRIMARY E, rolling origin: only 3 usable origins (2017–2019) with 12 test positives, so fallback F6 applies.
  AUC_A = 0.66 [0.54, 0.76]; ΔAUC(B − A) = +0.041 [−0.050, 0.098].
- Grouped-CV secondary (42 positives): A = 0.755, and ΔAUC(B) = +0.002 [−0.035, 0.035].
- The main-pool-aligned precursor set gives ΔAUC(B_mp) = +0.012 [−0.047, 0.060].
- Uptake-only (E_vol, 256 positives, 7 origins): A = 0.900; ΔAUC(B) = −0.009 [−0.016, −0.003], i.e. slightly worse.
  The main pool found the same (−0.014).
- E_cent (60 positives, 6 origins): ΔAUC(B) = −0.036 [−0.061, −0.015].
- Checks:
  - The leaky feature (focal percentile at t+5) lifts grouped-CV AUC from 0.76 to 0.90, as a sanity check; it was
    used only in that check.
  - Label permutation gives a mean ΔAUC of −0.015 (≈ 0).
  - The entropy family (C, biased) is reported but not used as a baseline.

**5. Patterns (three fixed rules, 191 concepts; the main pool's figures are in brackets).**

| pattern | MeSH | main pool |
|---|---|---|
| early bridging | 0.59 [0.51, 0.65] | 0.76 |
| incubation → expansion | 0.17 [0.12, 0.22] | 0.00 |
| gradual centralisation | 0.016 [0.00, 0.04] | 0.03 |

- Emerging vs non-emerging (PRIMARY) differ by +0.12 (incubation) and +0.15 (bridging), both with CIs that include 0.
- Overlap: incubation & bridging = 12 concepts.
- MeSH concepts, unlike the arXiv-dominated main pool, do show quiet low-turnover years followed by strength
  expansion. This is a genuine between-population difference in trajectory shape; the percentile references for the
  pattern rules are the MeSH focal concept-years.

**Replication verdict.**
- None of the three pre-named positive precursors (accretion, closure, participation rise) is supported in the MeSH
  population.
- The main pool's one consistent signal — *lower* closure before sustained uptake — has the same sign in MeSH:
  - E_up: −0.18, CI includes 0, heterogeneous with the main pool.
  - Plan-native SENS1: −0.42, Holm p = 0.039.
- So the "open neighbourhood before emergence" reading gains directional, not confirmatory, support.
- The accretion hypothesis stays untested in both populations, because the rarefied estimator needs ≥ 10 papers per
  year.

## Caveats (read before citing)

- **Weak ground truth.** Only about 25% of new MeSH descriptors are genuinely new concepts; MeSH introduction lags use.
  The emergence outcome here is network-plus-volume only and does not depend on MeSH status.
- **Coverage.** 178/191 concepts have PubMed-indexed works only (non-PubMed works were not paged). The route
  calibration median ratio is 0.86 against a plain OpenAlex query. SENS1 adds the unverified non-PubMed group_by counts.
- **Sample size.** 18 PRIMARY emerging concepts (15 effective) is a small panel. The MDEs are 0.43–0.56 SD, so
  effects smaller than about 0.5 SD cannot be excluded.
- **Communities.** Community-based indicators come from a weighted *sample* network with seed NMI of 0.72–0.80
  (fallback F2). P and z therefore carry their spread across seeds (`P_seed_sd` median 0.04, `z_seed_sd` median 0.05).
  Leiden used `n_iterations=2`, a declared deviation: quality was within 0.3% of `-1` at about 15× less CPU.
- **Background tags (hazard H2).** The background co-occurrence uses retroactive MAG legacy tags, the same as in the
  main pool.
- **Concept-discipline indicators.** No concept-discipline indicator from the background sample enters any test,
  because sample-based profiles are unreliable. The entropy family, computed from the concepts' own works, is
  flagged BIASED and excluded from the primary baseline.
- **Low-confidence-topic sensitivity (2014).** Spearman ρ between the snapshots with and without low-confidence-topic
  works: percentile 1.00, closure 1.00, betweenness 0.96, P 0.77, z 0.76.
- **Spec history.** The spec was extended twice before the features were frozen and before any outcome was computed:
  first with the focal percentile reference, then with the main-pool block. The snapshot-level constants did not
  change. `results/prereg_spec.json` holds the final spec hash and the features hash. No transfer test was run,
  because no main-pool model file exists.
- **Kept artifacts.** Everything in `results/` and `figures/` is small and is published. `results/snapshots/`
  (161 MB) and `results/intermediate/` stay on the run's volume and are regenerable.
## Layout

| path | what |
|---|---|
| `method.py` | orchestrator; `--stage snapshots|features|outcomes|all` (`--mini` for the 10-concept, 2008-2012 smoke run) |
| `run_all.py` | alias of `method.py` (name used in the plan) |
| `rq1_spec.py` | every frozen constant plus `DECLARED_CHOICES` (deviations and resolved ambiguities); its sha256 is in `results/prereg_spec.json` |
| `load.py` | STEP 1: concept table, MeSH works (verified text match, not `mesh_indexed_only`), background sample with post-stratified `w_year`, legacy-concept twins, Kleinberg denominators |
| `network.py` | STEP 2 + year-local STEP 3: one yearly snapshot (sparse `X^T diag(w) X`), best-of-5 Leiden, focal attachment, percentile, Chung-Lu closure, rewiring z, participation, within-module z, networkit betweenness |
| `snapshots.py`, `run_snapshots_cli.py` | STEP 1 checks (ID space, count agreement) and the parallel (spawn) snapshot driver |
| `features.py` | STEP 3 cross-year indicators (growth, new relations, novelty, Baselga, deltas, community ids, per-paper and volume-residualised versions, Kleinberg burst, entropy family) |
| `analysis.py` | STEPS 4-8: labels, matching, event study (concept bootstrap, Holm, permutation MDE), rolling-origin + grouped-CV prediction, patterns |
| `mainpool_align.py` | main-pool-aligned columns (accretion_shift_rar/raw, closure, closure_raw, P_raw, P_rar, *_res, vol3) computed with the main pool's metric code |
| `vendor/mainpool_lib_metrics.py` | read-only copy of the main-pool run's `lib_metrics.py` (sha256 in `prereg_spec.json`) |
| `audit_rederive.py`, `results/audit_rederivation.json` | independent re-derivation of the headline numbers through separate code paths, with placebo tests |
| `tests.py` | T1 unit tests (closure on triangle/star, participation, Baselga hand triple, Kleinberg known burst, Holm, a focal node's P recomputed by hand) |
| `results/prereg_spec.json` | spec + feature freeze: spec sha256, features.parquet sha256 and timestamps (written BEFORE outcomes), main-pool search log, T6 and low-confidence sensitivity |
| `results/features.parquet` | frozen concept-year indicator table (191 concepts x 2000-2024) |
| `results/indicator_columns.json` | indicator -> column per version (raw / pp / volres) |
| `results/labels.parquet` | E, E_vol, E_cent (focal and all-node references) per concept and t, for 3 volume definitions |
| `results/matched_sets.json` | emerging (c, t*) and their controls for every analysis variant |
| `results/rq1_effects.csv` | event-study effects: population, volume_def, subset, outcome, indicator, version, rel_year (-5..-1 and `D_-3_-1`), diff, ci_lo, ci_hi, p_boot, p_holm, n_emerging, n_controls, diff_sd, mde_sd, q_bh_all_indicators |
| `results/rq1_prediction.csv` | AUC / delta-AUC with concept-bootstrap CIs (rolling origin, grouped CV, per origin) |
| `results/rq1_patterns.csv`, `results/rq1_patterns_by_concept.csv` | the 3 fixed pattern rules: frequencies with CIs by group, and per concept |
| `results/rq1_effects_mainpool_aligned.csv` | main-pool-aligned event study: label (E / E_alt / E_up), family, version (primary / raw / res / exploratory), S, CI, p, p_holm, q_bh, MDE, n_treated, n_eff_window, per-k diffs |
| `results/side_by_side_mainpool_vs_mesh.csv` | row-by-row join with the main pool's `event_study_table`: sign agreement, CI status, inverse-variance pooled S and heterogeneity Q |
| `results/labels_mainpool_aligned.parquet`, `results/mainpool_align_fit.json` | E / E_alt / E_up labels; residualisation fits and NA shares |
| `results/replication_verdict.json` | per-precursor sign / CI / Holm / MDE / verdict across variants |
| `results/analysis_summary.json` | label counts, match rates, T5 null checks, T3 leaky-feature check, prediction origins |
| `results/snapshot_stats.json`, `results/load_checks.json`, `results/communities_y.parquet`, `results/volres_fit.json`, `results/rewire_units.json` | diagnostics |
| `figures/` | event-study panel, main pool vs MeSH side-by-side forest, delta-AUC forest plot, pattern-frequency bars (PNG + PDF) |
| `method_out.json` → `full_method_out.json`, `mini_method_out.json`, `preview_method_out.json` | exp_gen_sol_out: one example per (concept, t) unit |
| `results/snapshots/` | per-year edge / node / focal parquet files (regenerable; kept on the volume, not uploaded) |
| `results/intermediate/` | parsed input caches (regenerable; kept on the volume, not uploaded) |
| `logs/` | run logs |

## How to run

```bash
uv venv .venv --python=3.12 && uv pip install --python .venv/bin/python -r pyproject.toml
.venv/bin/python tests.py                       # unit tests (add a year, e.g. `tests.py 2010`, after snapshots exist)
.venv/bin/python method.py --stage snapshots    # ~25 min on 4 CPUs (25 yearly snapshots + 1 sensitivity snapshot)
.venv/bin/python method.py --stage features     # freezes results/features.parquet (sha256 -> prereg_spec.json)
.venv/bin/python method.py --stage outcomes     # refuses to run if the freeze hashes do not match
```

The inputs are read-only files from iteration 1 of this run (dataset_3 = held-out MeSH population,
dataset_2 = design-weighted background sample, dataset_1 = yearly OpenAlex totals). No API or LLM calls are made ($0).

## Restoring removed files

These paths are listed as `delete` in `.aii/manifest.yaml`:

| deleted path | restore with |
|---|---|
| `.venv/` | `uv venv .venv --python=3.12 && uv pip install --python .venv/bin/python -r pyproject.toml` |
| `__pycache__/`, `vendor/__pycache__/` | recreated automatically by Python on import |

`results/snapshots/` (per-year parquet files, each under 10 MB, 161 MB in total) and `results/intermediate/` stay on
the run's volume. They are not uploaded to the repository (upload-ignored), and you can rebuild them
deterministically with `.venv/bin/python method.py --stage snapshots`.
