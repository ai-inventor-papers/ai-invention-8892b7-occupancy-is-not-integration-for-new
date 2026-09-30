# Reproducing the RQ1 emergence-precursor experiment

This describes exactly what was run to produce `method_out.json`, `results_summary.json`, `results/` and `figures/`.
All paths are relative to this artifact folder.

## 1. Get the artifact

This folder is published as one folder of a public GitHub repository, which mirrors the run layout
(`3_invention_loop/<iter>/gen_art/<artifact>`). Clone it and `cd` into the folder:

```bash
git clone <repository-url> repo
cd repo/round-2/experiment-3/src
```

The inputs are read-only files of three iteration-1 artifacts. The repository publishes them as sibling folders,
reached through ONE constant, `RUN` in `config.py`. It defaults to `../../../round-1` relative to this folder,
and can be overridden with the environment variable `AII_DEPS_ROOT`:

| folder under `iter_1/gen_art/` | artifact id | files read |
|---|---|---|
| `gen_art_dataset_1` | art_94GEMUsgAmgK | `data_out.json`, `concept_work.parquet`, `works/works_part_00..03.parquet`, `context/subfield_year_totals.json`, `logs/assemble_summary.json` |
| `gen_art_dataset_2` | background sample, used by path; the sibling dataset artifact of the same iteration | `data/bg_work_sample.parquet`, `data/concepts.parquet`, `data/subfield_year_totals.parquet` |
| `gen_art_dataset_4` | art_QpM5SM6a7SH6 | `full_data_out/full_data_out_1..7.json` (substrate cross-check and grounding lookup only) |
| `gen_art_research_1` | art_bNCGUJX2MUhX | not read by code; its formulas are followed |

If a sibling folder is missing from your clone, regenerate it with that artifact's own `data.py` /
`reproducibility.md`, or point `AII_DEPS_ROOT` at a copy. No user-uploaded files are used.

## 2. Environment

- Ubuntu (Debian 12 container used), Python **3.12.14**, [uv](https://github.com/astral-sh/uv) for environments.
  No system packages beyond a C toolchain are required: wheels exist for every dependency.
- Exact versions are pinned in `pyproject.toml`: numpy 2.5.3, pandas 3.0.6, scipy 1.18.1, scikit-learn 1.9.1,
  python-igraph 1.0.0, leidenalg 0.12.0, networkit 11.2.2, tslearn 0.9.0, kmedoids 0.5.5, statsmodels 0.15.0,
  matplotlib 3.11.2, pyarrow 25.0.1, loguru 0.7.3, among others.

```bash
uv venv .venv --python=3.12
uv pip install --python=.venv/bin/python -r pyproject.toml
```

- **No API keys, no network calls, no LLM calls.** OpenAlex and OpenRouter are not used; spend was $0.
- Hardware: 4 CPU cores (AMD EPYC 9654), 29 GB RAM container limit, no GPU. Scripts cap RAM with `RLIMIT_AS`
  (24–26 GB). Set `OMP_NUM_THREADS=1` to avoid OpenMP oversubscription.

## 3. Commands actually run, in order

```bash
.venv/bin/python -m pytest -q -c pytest.ini tests                 # 13 unit tests (hand-computed answers), ~2 s
OMP_NUM_THREADS=1 .venv/bin/python method.py --all               # ~27 min end to end, as listed below
```

`method.py --all` runs, in order:

1. `stage_prep.py` (~10 s): asserts fold counts 123/61/22, 208,374 works, 259,716 background rows and a tag-id
   overlap of 0.918 (> 0.90). It writes `work/{pool,cp,bg}.parquet` and `work/totals.json`.
2. `stage_snapshots.py` (~6 min, 4 spawn workers): 25 snapshots (2000–2024), then alluvial matching. Output goes
   to `work/snapshots/` and `work/communities/`.
3. `stage_indicators.py` (~20 s): writes `results/indicators/` and `results/concept_subfield/`.
4. `stage_robust.py` (~18 min, 3 workers): writes `results/robustness.json`.
5. The analysis (~2 min): labels, leakage test, matched event studies (E, E_alt, E_up), rolling-origin prediction,
   patterns, typology and figures. It writes `method_out.json`, `results_summary.json`, `results/*` and `figures/*`.

It also writes `spec.json` (frozen configuration, sha256 `2e4c4894…2614`) before any label is computed.

Then:

```bash
.venv/bin/python make_previews.py            # mini/preview variants
# aii-json formatter (pipeline tool) was also run: full_method_out.json / mini_ / preview_method_out.json
.venv/bin/python audit_headlines.py          # independent re-derivation -> results/audit_headlines.json
```

For the analysis only (the stages already run): `OMP_NUM_THREADS=1 .venv/bin/python method.py`.
A partial robustness rerun is `stage_robust.py --only rewire d4 grounding`.

**Seeds and determinism.**
- Leiden: seeds 42..46, best of 5.
- networkit betweenness pivots: `setSeed(20260928 + year)`.
- igraph rewiring: `random.seed(year)`.
- Rarefaction: sha1-derived seed per (concept, year).
- Bootstraps: fixed numpy seeds. HistGB: `random_state=0`. k-medoids: `random_state=0`.

Two consecutive runs gave identical verdicts and prediction tables; only ~1e-16 floating-point noise remained in
two SMD values, and that was then removed by sorting.

## 4. Expected outputs and numbers

These are in `results_summary.json` (sections `labels`, `event_study_table`, `prediction`, `verdicts`) and are
re-derived in `results/audit_headlines.json`:

- **Labels (screen fold, 419 eligible concept-years)**:
  - primary E: rate 0.0215, 4 onsets, 86 never-emerging;
  - E_alt: 14 onsets;
  - E_up: 41 onsets, 49 never-emerging.
- **Event study, E_up, closure** (21 matched treated): S = −0.837, 95 % CI [−1.26, −0.43], Holm p = 0.003.
  - Residualised: S = −0.731 [−1.18, −0.29].
  - Pooled panel: coef = −0.743 [−1.06, −0.46].
  - This is the opposite of the predicted sign.
- **Accretion shift and participation**: underpowered or null.
  - Accretion MDE is 1.4–2.1 SD.
  - E_up participation: S = −0.007 [−0.066, 0.056].
- **Prediction, E_up** (131 test rows, 42 positives):
  - Logistic: AUC BASELINE 0.890, FULL 0.879, ΔAUC −0.010 [−0.045, 0.021].
  - HistGB: ΔAUC +0.019 [−0.025, 0.060].
- **Primary E / E_alt prediction**: single-origin pilots (2–3 test positives).
- **Robustness**:
  - Leiden bootstrap AMI 0.62–0.63.
  - Rewiring: 63–79 % of neighbourhoods are denser than the null.
  - dataset_4 substrate: percentile-gain Spearman 0.98.
- **Figures**: `figures/methodology.png` (methodology diagram), `es_precursors*.png` (event studies),
  `trajectories_*.png`, `delta_auc.png`, `pattern_bars.png`, `typology_series.png`, `alluvial_summary.png`.
  In the paper these are the RQ1 methods and results figures.

## 5. Notes

- The held-out concept fold (61 concepts) and the focal years 2016–2018 are sealed by `config.assert_not_sealed`
  and never processed.
- The `work/` intermediates (~146 MB across many files, each < 100 MB) are regenerable with `method.py --all`.
