# Reproducing this artifact (RQ2: diffusion types, community roles, expansion/diffusion timing)

These instructions describe what was actually run on 2026-09-29 (UTC). All paths are relative to this folder.

## 1. Get the artifact
This folder is one folder of the run's public GitHub repository. Clone the repository and `cd` into it:

```bash
git clone <repository-url>
cd <repository>/3_invention_loop/iter_3/gen_art/gen_art_experiment_8
```

The code reads its inputs from sibling artifact folders of the same repository. Paths are resolved relative to
`Path(__file__)` in `src/common.py`: `LOOP = <this folder>/../../..`, which is the `3_invention_loop/` folder. If the
siblings live elsewhere, set the environment variable `AII_LOOP_ROOT` to the folder that contains `iter_1/` and `iter_2/`.

| Constant in `src/common.py` | Relative path | Artifact |
|---|---|---|
| `DS5` | `iter_2/gen_art/gen_art_dataset_5` | **art_eR1Z7fMlOcxs**, the hydrated concept pool. Uses `hyd/data_out.json`, `hyd/concept_work.parquet`, `hyd/works/works_part_0{0..7}.parquet`, `hyd/context/subfield_year_totals.json` and `deps/gen_art_dataset_2/taxonomy_subfields.parquet`. |
| `X3` | `iter_2/gen_art/gen_art_experiment_3` | Iteration-2 RQ1 experiment. Uses `work/snapshots/*` (yearly co-word snapshots), `work/communities/*`, `work/cp.parquet`, `work/pool.parquet`, `work/totals.json`, `results/concept_subfield/rs_distance.parquet`, `results/indicators/concept_year_indicators.parquet`, `results/event_study/matches_E_up.csv`, `results/typology/*` and `results/patterns/summary_E_up.json`. Its code is vendored in `vendor/`. |
| `X1` | `iter_2/gen_art/gen_art_experiment_1` | `results/test_population.json` (frozen MAIN/STRICT rules). |
| `X4` | `iter_2/gen_art/gen_art_experiment_4` | `results/rq1_patterns.csv` and `results/rq1_patterns_by_concept.csv`: the MeSH pattern flags, derived from **art_HGiVAYhqO-6q** (`iter_1/gen_art/gen_art_dataset_3`). The MeSH dataset itself is not read directly. |
| `D2` | `iter_1/gen_art/gen_art_dataset_2` | `data/concepts.parquet` (legacy-concept levels and display names). |

- **Files over 100 MB.** Several of these inputs are parquet files. Any input of 100 MB or more is not in the published
  repository; it stays on the run's volume. All of the inputs listed above are below that size.
- **No downloads.** Nothing is downloaded: no API, no LLM, no model.
- **No secrets.** No environment variables or API keys are needed. `AII_LOOP_ROOT` is optional.
- **User uploads.** No user-uploaded file was used.

## 2. System, Python and libraries
- **OS and hardware.** Debian 12 (bookworm) container, Linux kernel 7.0. The container had **4 CPUs** (AMD EPYC 9655P,
  cgroup quota), **29 GB RAM** (cgroup limit) and **no GPU**. Ubuntu 22.04/24.04 works the same way.
- **Tools.** Python **3.12.14** and `uv`, with no other system packages. Where `uv` is missing, install it with
  `curl -LsSf https://astral.sh/uv/install.sh | sh`.
- **Environment:**
  ```bash
  uv venv .venv --python 3.12
  uv pip install --python .venv/bin/python -r pyproject.toml
  ```
- **Library versions.** `pyproject.toml` pins every installed package exactly. This is the output of
  `uv pip freeze`; the venv has no `pip`. The main pins are: numpy 2.5.3, pandas 3.0.6, pyarrow 25.0.1, scipy 1.18.1,
  scikit-learn 1.9.1, statsmodels 0.15.0, igraph 1.0.0, leidenalg 0.12.0, networkit 11.2.2, tslearn 0.9.0, kmedoids 0.5.5,
  networkx 3.7, matplotlib 3.11.2, loguru 0.7.3 and pytest 9.1.1.

## 3. Commands actually run, in order
Every stage is a separate script under `src/` and is run from `src/`. `method.py` runs them in the same order
(`python method.py`, or `--stage <names>`).

| # | Command | What it does | Runtime (4 CPUs) |
|---|---|---|---|
| 1 | `cd src && ../.venv/bin/python prep.py` | Builds the population: the frozen replacement rule, so MAIN screen = 202. It checks the folds (366/366 agree), seals the 119 held-out ids and writes `work/cp_hyd.parquet`. | ~10 s |
| 2 | `../.venv/bin/python attach.py` | Re-attaches the 307 active concepts to the 25 X3 snapshots, using 4 spawn workers and networkit seed 20260928+y. It writes `sealed/pct_alt_reference.npz`. | ~50 s |
| 3 | `../.venv/bin/python indicators.py` | Computes the indicators and runs the **reproduction gate**: closure r = 0.9996, which passes. | ~40 s |
| 4 | `../.venv/bin/python labels.py` | Computes E_up groups and closure terciles, and verifies the 41 iteration-2 onsets. | ~5 s |
| 5 | `../.venv/bin/python leiden_seeds.py` | Runs Leiden seeds 101–105 × 25 years and the alluvial matching; checks that seed 0 reproduces X3. | ~6.5 min |
| 6 | `../.venv/bin/python typology.py` | Builds the 3-channel DTW + k-medoids typology (B = 200, stability seed = k) and the B1/B2 baselines and sensitivities. | ~2 min |
| 7 | `../.venv/bin/python leadlag.py` | Computes onsets, the 1,000-draw null (seed 2026), the grid and the panel. | ~1 min |
| 8 | `../.venv/bin/python roles.py` | Assigns roles (pre-declared rules and the pool-relative variant), then computes the GA class, transitions, threshold grid and entry hazard. | ~1.5 min |
| 9 | `../.venv/bin/python patterns.py` | Computes the RQ1 patterns, the MeSH contrast and the early-bridging gap diagnostic. | ~30 s |
| 10 | `../.venv/bin/python validation.py` | Computes V1/V2/V3, KW ε² with a 2,000-draw bootstrap (seed 11), and the residualised versions. | ~1 min |
| 11 | `../.venv/bin/python cases.py` | Selects the 4 medoid cases and draws all figures. | ~20 s |
| 12 | `cd .. && .venv/bin/python method.py --mini` | Smoke test on 10 old + 10 new concepts for 2005–2012. Output goes to `mini_run/`; the match is exact. | ~30 s |
| 13 | `cd src && ../.venv/bin/python method_out.py` | Writes `method_out.json`, `results_summary.json`, and `mini_`/`preview_method_out.json`. | ~30 s |
| 14 | `cd .. && .venv/bin/python -m pytest -q tests` | Runs the 12 unit tests. | ~40 s |
| 15 | `.venv/bin/python audit_rederive.py` | Re-derives the stability table, the expansion-first share, the MeSH difference and the BRIDGE OR, and runs the sanity checks. | ~2 min |
| 16 | `.venv/bin/python confirm_heldout.py --simulate` | Rehearses the held-out pipeline on 40 screen concepts. The real held-out set is never read. Output goes to `heldout_sim/`. | ~10 min |
| 17 | `cd src && ../.venv/bin/python freeze.py` | Writes `sealed/heldout_spec.json` and its hash log. **Run last.** | ~5 s |
| 18 | `cd .. && .venv/bin/python confirm_heldout.py --dry-run --expected-sha $(cat sealed/heldout_spec.sha256)` | Checks the hashes; it must print `OK`. | ~2 s |
| 19 | `aii-json aii_json_format_mini_preview.py --input method_out.json` | Writes `full_`/`mini_`/`preview_method_out.json`. This is the run's JSON skill; step 13 already writes equivalent mini and preview files. | ~2 s |
| 20 | `.venv/bin/python audit_placebo.py` | Re-derives the headline numbers from raw tables and runs the placebo tests. | ~3 min |

**Notes on the actual run order**
- **Order.** The stages ran interleaved as they were debugged, but every final output was produced by the scripts in
  their final form, in the dependency order above. `typology.py` ran twice; the second run added the exploratory
  k = 3/4 descriptions and gave identical k = 2 labels.
- **Stale npz.** An early `--mini` run overwrote `sealed/pct_alt_reference.npz`. It was rebuilt from the full run's
  `work/attach/pct_alt_ref_y*.npy` before the freeze, and `attach.py` now refuses to write it in mini mode.
- **Seeds.** Leiden seeds are 101–105, and seed 0 is X3's best-of-5 run with seed 42. The rarefaction seeds are
  `stable_seed(concept, year, tag)` from the vendored `lib_metrics`. Bootstrap and permutation seeds are fixed in each
  script.

**Expected freeze hash.** A full rerun reproduces every result number. The sha256 of `sealed/heldout_spec.json` may
still differ from `695166b465d36f3311d13bdc7d315204a849ab96dc28c0c36fa002f4ad217d2a`, because `np.savez` stores zip
timestamps inside `pct_alt_reference.npz`. The shipped spec, npz and hash log are the ones iteration 4 must use.

## 4. Outputs and the numbers you should get
All of these come from `results_summary.json`, each with its source file. They feed the RQ2 results section of the
paper: typology, roles, timing, patterns vs MeSH and the case studies.

**Reproduction** (`results/reproduction_check.json`)
- Closure r = 0.9996.
- 41 of 41 E_up onsets reproduced.
- The B1 entropy-only typology on the old 123 concepts has min Jaccard 0.947; iteration 2 had 0.949.

**Typology** (`results/typology.json`, `figures/typology_trajectories.png`)
- k = 2 is stable, with min Jaccard 0.861. Clusters: localised, n = 136; broad from the start, n = 66.
- Min Jaccard is 0.599 at k = 3 and 0.439 at k = 4.
- AMI with volume terciles is 0.014.
- B1 on hydrated MAIN is stable at k = 4 (0.856).

**Validation** (`results/validation.json`)

| Outcome | ε² [95 % CI] | p |
|---|---|---|
| Newcomer share | 0.171 [0.087, 0.284] | 5e-9 |
| Pool-percentile gain | 0.065 | — |
| Communities touched | 0.044 | 0.003 |

- After residualising, no Δε² against B1 excludes 0.

**Roles** (`results/roles.json`)
- 97.2 % of concept-years are robust across seeds. The placebo with independent seeds already gives 0.87, because
  BRIDGE dominates the role mix.
- Robust shares: BRIDGE 0.61, OTHER 0.33, STAYER 0.034, MIGRANT 0.023. CORE_GROWING and FOUNDER are 0 under the
  pre-declared rules.
- Entry OR for BRIDGE: 0.64 [0.38, 1.08].

**Lead-lag** (`results/leadlag.json`)
- 16 concepts have both onsets; 15 have expansion first, a share of 0.94 [0.81, 1.0].
- The null mean is 0.62, with p = 0.004.

**Patterns** (`results/patterns_contrast.csv`)
- Early bridging in main minus MeSH is +0.11 [0.02, 0.20].
- Incubation in main minus MeSH is −0.17 [−0.23, −0.12].

**Other outputs**
- **Audits.** `results/audit_rederive.json` and `results/audit_placebo.json` report all numbers equal and all
  placebos failing.
- **method_out.** `method_out.json` / `full_method_out.json` follow the exp_gen_sol_out schema, with 202 + 247 examples.
- **Figures.** Figures are in `figures/`, as PNG at 300 dpi and PDF. Case data are in `cases/`.

## 5. Held-out confirmation (iteration 4 only)
```bash
.venv/bin/python confirm_heldout.py --expected-sha 695166b465d36f3311d13bdc7d315204a849ab96dc28c0c36fa002f4ad217d2a --open-heldout
```
This runs exactly once. It writes `heldout_run/OPENED`, runs all stages on the 119 sealed concepts and evaluates the
frozen rules E1–E5 into `heldout_run/results/confirmation.json`. Editing any file under `src/` or `vendor/`,
`method.py` or `confirm_heldout.py` makes it refuse.
