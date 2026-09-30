# How new concepts spread: diffusion types, community roles and timing (RQ2)

This is a descriptive RQ2 experiment. It ran on CPU only and made no API or LLM calls. It uses the hydrated **screen
fold** of the concept pool (`gen_art_dataset_5`). The **primary population is screen MAIN**, n = 202. MAIN is the
iteration-2 MAIN rule, re-applied under its frozen replacement rule. The 247 unfiltered main-arm screen concepts are a
sensitivity population.

Every concept is re-attached to the **existing** iteration-2 yearly co-word snapshots (`gen_art_experiment_3`, called
X3 below), using that experiment's code, which is vendored here byte-identical. The experiment then produces:

- **(T)** A 3-channel diffusion typology. The channels are the rarefied Shannon entropy over subfields, Rao-Stirling
  diversity and the number of active subfields. Distances are multivariate DTW, clusters come from k-medoids, and k is
  chosen by Hennig bootstrap-Jaccard stability. It is compared with an entropy-only baseline (B1) and a volume-only
  baseline (B2). It is validated on quantities the clustering never saw.
- **(Ro)** Community roles per concept-year, kept only where 5 extra Leiden seeds agree. The section also has a
  Guimerà–Amaral cross-tab, a role-transition matrix and a discrete-time logit of host-subfield entry on the lagged role.
- **(L)** Lead-lag between the onset of network expansion and the onset of disciplinary diffusion. It comes with
  bootstrap CIs, a 4×3 threshold grid and a year-shuffle null of 1,000 draws.
- **(Pa)** The three RQ1 patterns on the hydrated pool, compared with the MeSH held-out set.
- **(C)** Four medoid case studies.
- A **sealed held-out test**: `sealed/heldout_spec.json`, its hash log, and `confirm_heldout.py`. Iteration 4 runs this
  test once.

All numbers below are read from the files named. `results_summary.json` lists every headline number with its source,
`audit_rederive.py` re-derives four of them by independent code paths (`results/audit_rederive.json`: all equal). `audit_placebo.py` re-derives the validation ε², the volume AMI, the lead-lag share, the robust-role share, the BRIDGE OR and the MeSH difference from the raw per-concept tables, using its own rank-based Kruskal-Wallis and χ² code. It also runs each test on shuffled or placebo input, and every placebo fails as it should (`results/audit_placebo.json`).

## Results

**Reproduction gates**
- On the 123 iteration-2 screen concepts, closure reproduces with r = 0.9996, which passes the ≥ 0.99 gate
  (`results/reproduction_check.json`).
- Strength, wmz, H and RS match exactly in 98.8 % of rows. The remaining rows belong to the 6 concepts whose
  re-hydrated work sets differ slightly (work-set Jaccard ≥ 0.9946).
- The seed-0 alluvial matching reproduces X3's persistent ids exactly (`results/alluvial_reproduction.json`).
- All 41 iteration-2 E_up onsets are reproduced (`results/labels/label_check.json`).
- The iteration-2 entropy-only typology is reproduced on the old 123 concepts: min Jaccard 0.947 vs 0.949, and AMI with
  the iteration-2 labels is 1.0.
- `--mini` gives an exact match on 10 old concepts (`mini_run/results/mini_comparison.json`).

**T – typology** (`results/typology.json`, `results/typology_naming.md`, `figures/typology_*.png`)
- **Stability.** Only k = 2 is fully stable: min cluster Jaccard 0.861 (k = 3: 0.599; k = 4: 0.439; k ≥ 5: ≤ 0.52). The
  two clusters, named after clustering, are:
  - **localised**, n = 136: median 1–2 active subfields for the whole life, H_rar about 0.2–0.3;
  - **broad from the start (rapid interdisciplinary)**, n = 66: H_rar about 0.7 at age 0, rising to about 1.2; active
    subfields grow from 1 to about 7.
- **Imputation.** 14.2 % of concept-years are imputed (the H_rar → raw-H rule). No concept is excluded.
- **Not a volume split.** AMI with volume terciles (B2) is 0.014. |Spearman(cluster, log cumulative volume)| is 0.23.
- **Exploratory k = 3**, at the "pattern" band (0.60): it splits off a **gradual broadening** group (n = 73) from
  localised (n = 115) and a small broad group (n = 14). Its cross-tab with the E_up group gives permutation p = 0.027.
- **Sensitivities.** AMI with the primary is 0.96 at radius 2, 0.85 for raw DTW, 0.69 with fully rarefied channels,
  0.60 for a fixed ages 0–8 window, 0.59 for STRICT, and 1.0 for all 247 concepts on the shared concepts. No MAIN concept
  is sense-check-flagged, so the "drop sense-fail" run is identical to the primary.
- **Baseline B1 (entropy-only, iteration-2 recipe) is stable at a finer k = 4** (min Jaccard 0.856, n = 200). Its AMI
  with the 3-channel typology is 0.37.
- **Validation on unclustered outcomes**, t\* = F+3, 3-channel ε² [95 % CI] vs B1 vs B2 (`results/validation.json`):
  - **newcomer share:** ε² 0.171 [0.087, 0.284] vs 0.178 vs 0.117. The median is 0.55 for broad vs 0.37 for
    localised.
  - **pool-percentile gain:** 0.065 vs 0.131 vs 0.424. Volume dominates this outcome.
  - **communities touched:** 0.044 vs 0.023 vs 0.003.
  - **After residualising on early volume**, the 3-channel typology is **not better than B1** on any outcome: every
    Δε² CI includes 0 or favours B1. It is better than B2 on newcomer share and communities touched, but those CIs
    mostly include 0.
  - **Calibration.** Permuted labels give KW p that is roughly uniform: 2.5 % of p < 0.05, KS p = 0.21.
- **Cross-tabs** (permutation χ², 10,000 permutations):
  - cluster × origin group: p = 0.004, V = 0.28;
  - cluster × E_up group: p = 0.097;
  - cluster × closure tercile: p = 0.11;
  - cluster × retrieval route: p = 1.0. The typology is not a retrieval artefact.

**Ro – roles** (`results/roles.json`, `results/role_*.csv`, `figures/role_*.png`)
- **Seed agreement.** Primary roles agree in ≥ 3 of 5 new Leiden seeds for 97.2 % of MAIN concept-years. Mean AMI of
  the new seeds vs X3's partition is 0.83 (`results/leiden_seeds_ami.csv`).
- **Caveat on the 97.2 % agreement.** Drawing each seed's role independently from the pooled role mix already gives 0.87 agreement, because BRIDGE dominates (`audit_placebo.json`). The agreement is therefore only moderately above chance.
- **Robust shares under the pre-declared rules:** BRIDGE 0.61, OTHER 0.33, STAYER 0.034, MIGRANT 0.023, and
  **CORE_GROWING and FOUNDER 0**. These two rules can never fire because attached pool concepts are far below background
  nodes in within-community strength: wmz max −0.23, so wmz ≥ 1 and a top-5 rank are unreachable. The plan's departure
  (a) anticipated this.
- **Pool-relative variant**, declared post hoc: wmz ≥ the pool 90th percentile, and a newborn dominant community holding
  ≥ 50 % of the concept's weight. It gives FOUNDER 0.035 and CORE_GROWING 0.013.
- **Guimerà–Amaral classes:** R2 peripheral 0.49, R3 connector 0.40, R4 kinless 0.10, no hubs.
- **Transitions.** BRIDGE is absorbing: 0.80 of BRIDGE→BRIDGE.
- **By cluster.** BRIDGE is 0.71 in broad vs 0.56 in localised.
- **Host-subfield entry logit** (2,376 concept-years, 202 concepts, 1,061 events, concept-clustered SEs, STAYER as
  reference): OR for BRIDGE 0.64 [0.38, 1.08], MIGRANT 0.75 [0.35, 1.60], OTHER 0.65 [0.37, 1.14]. In the pool-relative
  variant, FOUNDER has OR 0.43 [0.19, 0.94]. No lagged role predicts entry robustly across the sensitivities: the entry
  definition with ≥ 2 papers, the Poisson count model and the multi-label flags.

**L – lead-lag** (`results/leadlag.json`, `results/leadlag_grid.csv`, `figures/leadlag_hist_grid.png`)
- **Primary definitions.** Only 16 of 202 concepts have both onsets outside left-censoring. The F7 fallback therefore
  applies: the result is underpowered.
- **Result.** Of these 16, 15 have expansion first, 1 is same-year and 0 have diffusion first. Share expansion-first
  = 0.94 [0.81, 1.0]. The year-shuffle null mean is 0.62 [0.38, 0.88], one-sided p = 0.004. Median lag is 5 years.
- **Left-censoring.** Expansion is present from the start for 41 concepts and diffusion for 15. The latter are the
  concepts with cross-disciplinary connectivity from the beginning.
- **Threshold grid.** No cell has diffusion first. The largest-n cell (gain 5, rise 0.1, n = 42) gives 0.95.
- **Granger-style panel.** Lagged Δpct_alt does not predict ΔH_rar (p = 0.07, negative sign).

**Pa – patterns vs MeSH** (`results/patterns*.csv`, `results/patterns.json`, `figures/patterns_main_vs_mesh.png`)
- **Frequencies, screen MAIN:** incubation→expansion 0.00, gradual centralisation 0.035 [0.01, 0.06], early bridging
  0.70 [0.64, 0.76], aligned early bridging 0.72.
- **Main minus MeSH (n = 191):**
  - early bridging +0.11 [0.02, 0.20] (Newcombe [0.02, 0.20]);
  - aligned early bridging +0.13 [0.04, 0.22];
  - incubation −0.17 [−0.23, −0.12];
  - gradual centralisation +0.02 [−0.01, 0.05].
- **MeSH aggregates** reproduce iteration 2 exactly.
- **Old 123 concepts with frozen thresholds:** 0.00 / 0.033 / 0.715, vs the iteration-2 values 0.00 / 0.033 / 0.764.
  The early-bridging gap comes **entirely** from the betweenness-percentile component. With 307 instead of 145 pool
  nodes in the betweenness graph, the cross-community flag at F/F+1 falls from 0.31 to 0.14. Swapping in the
  iteration-2 flag restores 0.764 exactly, and the P_raw component is identical (`early_bridging_gap_diagnostic`).
  The betweenness percentile is therefore population-dependent, and the early-bridging frequency inherits that
  dependence.

**C – cases** (`cases/*.json`, `figures/case_*`, `results/cases_selection.json`)
- k\* = 2, so the cases are the two medoids plus, for each, the nearest non-medoid of a different origin group:
  - *wireless backhaul* (medoid, broad);
  - *Einstein–Podolsky–Rosen steering* (broad);
  - *locally repairable code* (medoid, localised);
  - *holographic QCD* (localised).
- Each case has ego networks at F+1, onset and 2022, an alluvial path with roles, a subfield × year heatmap, channel
  series, pattern flags and its lead-lag category.

**Held-out freeze.** The spec sha256 is `695166b465d36f3311d13bdc7d315204a849ab96dc28c0c36fa002f4ad217d2a` (`sealed/heldout_spec.sha256`, `results/heldout_spec_hashlog.jsonl`). It covers 23 code files and 6 frozen artefacts. **Do not edit `src/`, `vendor/`, `method.py` or `confirm_heldout.py`**: any edit makes the confirmation refuse. Iteration 4 runs `confirm_heldout.py --expected-sha 695166b465d36f3311d13bdc7d315204a849ab96dc28c0c36fa002f4ad217d2a --open-heldout` exactly once.

**Held-out rehearsal.** `confirm_heldout.py --simulate` runs the whole held-out pipeline on 40 screen concepts that play
the held-out role. The real held-out concepts stay sealed. It also evaluates the frozen decision rules:
`heldout_sim/results/confirmation_rehearsal.json`. `confirm_heldout.py --dry-run` refuses on a spec that differs by one
byte (`tests/test_all.py::test_confirm_refuses_modified_spec`).

## Caveats
- **Arxiv skew.** The pool is arXiv-skewed: physics, CS, materials science and mathematics make up about 90 %. Results
  describe these fields first.
- **Newcomer shares are upper bounds**, because the co-authorship check is within the corpus.
- **Validation windows overlap** the trajectories being clustered, so the validation is "not used by the clustering"
  rather than out-of-sample. Iteration 4 supplies the out-of-sample test.
- **The MeSH contrast crosses substrates**: MeSH has its own snapshots and anchor. It is a descriptive population
  contrast.
- **Lead-lag is underpowered.** Onsets depend on evaluability: H_rar needs ≥ 10 papers in the 3-year window.

## Deviations from the plan
1. **Workspace.** Everything was written to this artifact's workspace, not the `gen_plan` path named in the plan.
2. **Pool-relative role variant**, added post hoc and declared in `roles.json:pool_relative` and in the
   `assign_roles_rel` docstring. The pre-declared rules stay primary.
3. **Newcomer co-authorship window.** Co-authorship with W1 authors counts corpus papers published ≤ F+3, so there is
   no look-ahead. The residualisation uses log1p(W1 papers) and F. Age at t\* is constant (3), so F stands in for age.
4. **Migrant rule.** A migrant must also have had a dominant community in y−1 (dom(y−1) ≥ 0).
5. **B1 baseline.** B1 uses the iteration-2 recipe, including its missingness filter, so 2 concepts drop out
   (n = 200).
6. **mini/preview.** `mini_method_out.json` and `preview_method_out.json` come from `src/method_out.py`, because the
   skill formatter needs a top-level array.

## Layout
| Path | What |
|---|---|
| `method.py` | Orchestrator: `--stage <names>`, or `--mini` for the smoke test. |
| `src/common.py` | Paths (relative; override with `AII_LOOP_ROOT`), sealing, statistics helpers, and the HELDOUT / SIMULATE / MINI modes. |
| `src/prep.py` | Stage 0: population with the frozen replacement rule, fold check, c-papers with author ids. |
| `src/attach.py` | Stage 1: re-attachment to the X3 snapshots; `pct_alt` and the frozen reference arrays. |
| `src/indicators.py` | Stage 2: vendored `concept_indicators` plus the diffusion channels and the reproduction gate. |
| `src/labels.py` | Stage 3: E_up groups (vendored) and closure terciles. |
| `src/leiden_seeds.py` | Stage 4: 5 Leiden seeds, the alluvial rule, and per-seed role inputs. |
| `src/roles.py` | Stage 5: roles, agreement, the Guimerà–Amaral cross-tab, transitions, the threshold grid and the entry hazard. |
| `src/typology.py` | Stage 6: 3-channel typology, baselines B1/B2, sensitivities, naming, cross-tabs, held-out assignment. |
| `src/validation.py` | Stage 6b: V1/V2/V3 with ε² bootstrap CIs, deltas and the residualised versions. |
| `src/leadlag.py` | Stage 7: onsets, null, grid and panel. |
| `src/patterns.py` | Stage 8: RQ1 patterns and the MeSH contrast. |
| `src/cases.py` | Stage 9: cases and all figures. |
| `src/method_out.py` | Stage 11: `method_out.json`, `results_summary.json` and the mini/preview files. |
| `src/freeze.py` | Stage 10: the held-out spec plus its hash (run last). |
| `vendor/` | Iteration-2 code, byte-identical (`VENDOR_SHA256.json`). |
| `confirm_heldout.py` | `--dry-run`, `--simulate`, or `--open-heldout` (iteration 4 only; one time). |
| `audit_rederive.py`, `audit_placebo.py` | Independent re-derivation of the headline numbers, and the placebo tests. |
| `full_method_out.json`, `mini_method_out.json`, `preview_method_out.json` | Output variants from the aii-json format script. |
| `reproducibility.md`, `pyproject.toml` | Exact reproduction steps and exact pinned versions. |
| `tests/test_all.py` | T0 unit tests: 12 tests. |
| `results/` | All result tables and JSON. |
| `typology/` | Assignments, frozen `medoids.json` / `scaling.json`, `D_primary.npy`. |
| `sealed/` | `heldout_spec.json` (+ sha256), `pct_alt_reference.npz`. |
| `cases/`, `figures/` | Case JSONs, and figures as PNG (300 dpi) and PDF. |
| `method_out.json` | exp_gen_sol_out: 202 screen MAIN plus 247 sensitivity examples. The output is the diffusion type, `predict_method` is the 3-channel type, `predict_baseline` is the entropy-only type and `predict_volume_baseline` is the volume tercile. |
| `heldout_sim/results/` | Held-out rehearsal outputs. |

## How to run
```bash
uv venv .venv --python 3.12 && uv pip install --python .venv/bin/python -r pyproject.toml
.venv/bin/python method.py --mini          # smoke test (~1 min)
.venv/bin/python method.py                 # all stages (~15 min on 4 CPUs; the Leiden seeds take ~7 min)
.venv/bin/python -m pytest -q tests
.venv/bin/python audit_rederive.py
.venv/bin/python confirm_heldout.py --dry-run --expected-sha $(cat sealed/heldout_spec.sha256)
```
The run needs the sibling artifacts `iter_2/gen_art/{gen_art_dataset_5, gen_art_experiment_1, gen_art_experiment_3,
gen_art_experiment_4}` and `iter_1/gen_art/gen_art_dataset_2`. Set `AII_LOOP_ROOT` if they live elsewhere.

## Restoring removed files
Entries marked `delete` in `.aii/manifest.yaml`, and how to rebuild them:
- `.venv/`: `uv venv .venv --python 3.12 && uv pip install --python .venv/bin/python -r pyproject.toml`
- `work/cp_hyd.parquet`: `.venv/bin/python method.py --stage prep`
- `heldout_sim/work/`: `.venv/bin/python confirm_heldout.py --simulate`
- `__pycache__/`, `src/__pycache__/`, `vendor/__pycache__/`, `tests/__pycache__/`: recreated automatically when Python
  imports the modules.

The regenerable intermediates `work/attach/` and `work/leiden_seeds/` are made of small files and are kept. To rebuild
them: `.venv/bin/python method.py --stage attach` and `.venv/bin/python method.py --stage leiden_seeds`.

Everything else is kept on the run's volume at the same relative path: `results/`, `typology/`, `sealed/`, `cases/`,
`figures/`, `method_out.json` and `heldout_sim/results/`. No file is ≥ 100 MB, so all kept files are also in the
published repository.
