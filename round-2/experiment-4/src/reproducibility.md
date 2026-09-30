# Reproducibility — RQ1 replication on the 191 held-out MeSH concepts

This file describes what was actually run: the steps, their order, and the settings used. There were no API calls, no
LLM calls and no GPU.

## 1. Get the artifact

This folder is published as one folder of the run's public GitHub repository:

```bash
git clone <repository-url>
cd <repository>/gen_art_experiment_4        # this folder
```

## 2. System and Python environment

- **OS:** Ubuntu (Linux 6.x), used as-is. No extra system packages are needed: every wheel is manylinux.
- **Python:** 3.12.14.
- **Environment tool:** `uv`.

```bash
uv venv .venv --python=3.12
uv pip install --python .venv/bin/python -r pyproject.toml     # every dependency is pinned in pyproject.toml
```

Key versions, exactly as installed and pinned in `pyproject.toml`:

| library | version |
|---|---|
| numpy | 2.5.3 |
| pandas | 3.0.6 |
| pyarrow | 25.0.1 |
| scipy | 1.18.1 |
| scikit-learn | 1.9.1 |
| python-igraph / igraph | 1.0.0 |
| leidenalg | 0.12.0 |
| networkit | 11.2.2 |
| statsmodels | 0.15.0 |
| matplotlib | 3.11.2 |
| loguru | 0.7.3 |
| psutil | 7.2.2 |
| pyflakes | 4.0.0 |

## 3. Inputs (no downloads, no API keys)

All inputs are outputs of other artifacts of the same run. The repository publishes them as sibling folders. Two
environment variables locate them; both are optional, and each is given by NAME with its default:

- **`AII_ITER1_GEN_ART`** — the directory that holds the iteration-1 dataset folders. Default:
  `../../../round-1`, relative to this folder (the run layout). Point it at wherever the three folders below sit.
  - `gen_art_dataset_3` = artifact **art_HGiVAYhqO-6q** (the MeSH population): `data_out.json` and
    `works/works_part_01..05.jsonl.gz`.
  - `gen_art_dataset_2` = the background-sample dataset: `data/bg_work_sample.parquet`,
    `data/subfield_year_totals.parquet`, `data/concepts.parquet` and `data/taxonomy_fields.parquet`. The plan uses it by
    path; it is not a declared dependency.
  - `gen_art_dataset_1` = artifact **art_94GEMUsgAmgK**: `context/subfield_year_totals.json`, used for the Kleinberg
    denominators.
- **`AII_MAINPOOL_DIR`** — the sibling main-pool RQ1 experiment (iteration 2, `gen_art_experiment_3`). Default:
  `../../experiment-3/src`. Only its `results_summary.json` is read, to build the side-by-side table. Its metric code
  is vendored here as `vendor/mainpool_lib_metrics.py`; the sha256 is in `results/prereg_spec.json`.

No user-uploaded (private) input is used. The path anchors are in `load.py` (`RUN`, from `Path(__file__)`) and
`method.py` (`MAINPOOL_DIR`).

## 4. Commands actually run, in order

These ran on a 4-CPU container with a 32 GB memory cgroup, no GPU. `method.py` caps the address space at 26 GB.

| # | command | runtime | what it does |
|---|---|---|---|
| 1 | `.venv/bin/python tests.py` | seconds | unit tests: closure on a triangle / star, participation, a Baselga hand triple, Kleinberg known burst, Holm |
| 2 | `.venv/bin/python run_snapshots_cli.py --mini` | ~3 min | smoke run: 10 concepts (5 earliest F + 5 drawn with seed 42), snapshots 2008–2012 |
| 3 | `.venv/bin/python method.py --stage snapshots --workers 4` | ~20 min | 25 yearly snapshots + 1 low-confidence-topic sensitivity snapshot (2014), 4 spawn workers; writes `results/snapshots/`, `results/intermediate/`, `results/load_checks.json`, `results/snapshot_stats.json`, `results/rewire_units.json` |
| 4 | `.venv/bin/python tests.py 2014` | seconds | recomputes one focal node's participation P by hand from the saved snapshot |
| 5 | `.venv/bin/python method.py --stage features` | ~45 s | writes `results/features.parquet` and records its sha256 and the spec sha256 in `results/prereg_spec.json` (the FREEZE, before any outcome) |
| 6 | `.venv/bin/python method.py --stage outcomes` | ~8 min | asserts the freeze hashes, then writes the labels, event studies, prediction, patterns, verdicts, figures and `method_out.json` |
| 7 | `aii_json_format_mini_preview.py --input method_out.json` (aii-json skill) | seconds | writes `full_/mini_/preview_method_out.json`, all validated as `exp_gen_sol_out` |
| 8 | `.venv/bin/python audit_rederive.py` | ~2 min | independent re-derivation of the headline numbers plus placebo tests; writes `results/audit_rederivation.json` |

Seeds:
- Global seed 42; the 10% rewiring subsample is drawn with `numpy.default_rng(42)`.
- Leiden seeds 42–46, keeping the best quality.
- networkit seed 42, single thread.
- igraph rewiring seeded with `random.seed(42 + rep)`.
- All bootstraps and permutations use `numpy.default_rng(42)` in a fixed call order.
- Main-pool rarefaction uses `stable_seed(concept, year, ...)`.

Snapshots and bootstraps are single-threaded per worker, so reruns give identical numbers.

Declared deviations (all in `rq1_spec.py`, `DECLARED_CHOICES` and `MAINPOOL`):
- Leiden `n_iterations=2`.
- The E_cent percentile reference is the MeSH focal population.
- A second, main-pool-aligned analysis block.

## 5. Expected outputs and headline numbers

| number | expected value | file |
|---|---|---|
| (concept, t) units, ages 3–8 | 1,067 | `method_out.json` |
| PRIMARY emerging concepts | 18 (15 matched with data in rel −3..−1) | `results/analysis_summary.json` |
| accretion_share D | +0.094 [−0.036, 0.210], Holm 0.48 | `results/rq1_effects.csv` (`rel_year = D_-3_-1`, `volume_def = PRIMARY`, `subset = all`) |
| closure_lr D | −0.086 [−0.511, 0.402], Holm 0.68 | same |
| dP D | +0.025 [−0.017, 0.073], Holm 0.51 | same |
| SENS1 closure_lr D | −0.419 [−0.740, −0.115], Holm 0.039 | same |
| aligned E_up closure (MeSH) | S = −0.185 [−0.498, 0.108], n = 51 | `results/side_by_side_mainpool_vs_mesh.csv` |
| main pool E_up closure | −0.837; IVW pooled −0.41 (SE 0.125) | same |
| grouped-CV PRIMARY | AUC_A = 0.755, AUC_B = 0.758, ΔAUC = +0.002 [−0.035, 0.035], 42 positives | `results/rq1_prediction.csv` |
| rolling origin | 3 usable origins, 12 positives, ΔAUC = +0.041 [−0.050, 0.098] | same |
| early bridging | 0.586 | `results/rq1_patterns.csv` |
| incubation → expansion | 0.168 | same |
| gradual centralisation | 0.016 | same |

- Verdicts are in `results/replication_verdict.json`; figures are in `figures/`.
- In the paper, these numbers feed the RQ1 replication subsection: the event-study table, the side-by-side forest
  figure (`figures/side_by_side_mainpool_vs_mesh.png`), the ΔAUC forest and the pattern bars.
- The independent audit (`results/audit_rederivation.json`) reproduces the 18 onsets, all four D values, the E_up
  closure S, the grouped-CV AUCs and the early-bridging share through separate code paths. Its placebo versions centre
  on 0, and the shuffled-label AUC is 0.46.
- Bootstrap CI endpoints differ slightly in the audit (400 vs 2,000 reps).
