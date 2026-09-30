# Reproducibility: RQ2-D1 screen test (openness → cross-disciplinary breadth gain)

This file describes what was actually run to produce the results in this folder: Ubuntu/Debian, CPU only, $0.
No API keys or LLM calls are needed.

## 1. Get the artifact
This workspace is published as one folder of a public GitHub repository.
```bash
git clone <repository-url>
cd <repository>/<this-artifact-folder>        # the folder containing method.py
```

## 2. System, Python and libraries
- OS: Debian 12 (bookworm) container. Any recent Ubuntu works. No extra system packages are needed beyond `curl`,
  to fetch `uv`.
- Python **3.12** (3.12.14 was used). The environment is created with [uv](https://docs.astral.sh/uv/):
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
uv venv .venv --python=3.12
uv pip install --python .venv/bin/python -r pyproject.toml
```
- `pyproject.toml` pins every package to the exact version installed in the run's `.venv`, for example
  numpy==2.5.3, pandas==3.0.6, scipy==1.18.1, statsmodels==0.15.0, scikit-learn==1.9.1, pyarrow==25.0.1,
  igraph==1.0.0, leidenalg==0.12.0, networkit==11.2.2, networkx==3.7, matplotlib==3.11.2, loguru==0.7.3 and
  pytest==9.1.1.

## 3. Input data (other artifacts; no downloads, no keys)
The code reads four artifacts produced earlier in this research run. They are read-only, and the repository
publishes them as sibling folders.

| id | role | env var for its folder |
|---|---|---|
| gen_art_experiment_3 (art_mbFjmo5rbbf8) | vendored code, 25 prebuilt co-word snapshots (`work/snapshots`), communities, fixed Rao-Stirling distance, reproduction target, DS1-derived `work/cp.parquet` | `AII_EXP3_DIR` |
| gen_art_dataset_5 (art_eR1Z7fMlOcxs) | hydrated corpus: `hyd/data_out.json`, `hyd/concept_work.parquet`, `hyd/works/works_part_00..07.parquet`, `hyd/context/subfield_year_totals.json`, `deps/gen_art_dataset_2/concepts.parquet` | `AII_DS5_DIR` |
| gen_art_experiment_1 | frozen population `results/test_population.json` (sha256 `6a887fb4…5505`, asserted) | `AII_EXP1_DIR` |
| gen_art_dataset_1 (art_94GEMUsgAmgK) | iteration-1 corpus; used through exp_3's `work/cp.parquet` for the code-equality check | `AII_DS1_DIR` |

- **Default resolution.** `src/common.py` resolves each folder relative to its own location:
  `<loop root>/iter_2/gen_art/<name>` and `<loop root>/iter_1/gen_art/<name>`, with loop root = three levels above
  this folder (override it with `AII_LOOP_ROOT`).
- **Other layouts.** In the published repository, point each env var at the sibling folder, for example
  `export AII_EXP3_DIR=../gen_art_experiment_3`.
- **Folders not published.** Some large inputs (exp_3's `work/snapshots`, dataset_5's `hyd/works`) may be absent
  from the published copies, because they sit on the run volume or exceed the 100 MB upload limit. Regenerate them
  with those artifacts' own instructions (exp_3: `method.py` snapshot stage; dataset_5: `restore.sh`).
- **User uploads.** No user-uploaded files are used.

## 4. Commands actually run (in order)
```bash
export OMP_NUM_THREADS=1               # method.py sets this itself; BLAS threading is ~1000x slower on these small solves
.venv/bin/python -m pytest -q          # 33 tests: 13 vendored + openness==networkx, guard, outcome toys, confirm refusal
.venv/bin/python method.py --stage population prep indicators openness features outcomes models --mini   # smoke run (20 concepts) -> mini_run/, < 2 min
.venv/bin/python method.py --stage all # vendor, population, prep, attach, indicators, openness, features, outcomes, models, power, freeze, outputs
.venv/bin/python audit_rederive.py     # independent re-derivation -> results/audit_rederive.json (all_match: true)
```

**Hardware.** 4 CPU cores (AMD EPYC, cgroup-limited), 29 GB RAM (the script caps its address space at 24 GB),
no GPU.

**Runtime.** The full `--stage all` run takes about 10–12 min:

| stage | time |
|---|---|
| attach | 72 s |
| indicators | 60 s |
| outcomes | 24 s |
| models | 67 s |
| power | 331 s |

**Seeds** (all fixed):
- `lib_metrics.stable_seed(concept, year, tag)`: rarefaction (Y1r 200 draws, P_rar 50 draws) and the xcomm null
  (50 draws);
- cluster bootstrap: 20260929 + offsets;
- CV repeat seeds: 0..19;
- power simulation: 20261003;
- frozen held-out bootstrap: 20261001.

Two complete runs gave identical coefficients, CIs and MDEs.

**Iteration 4 only.** Run `AII_OPEN_HELDOUT=iter4 .venv/bin/python confirm_heldout.py`. It refuses to run if
`results/heldout/heldout_spec.json` no longer matches `results/heldout/heldout_spec.sha256` (also the last line of
`logs/freeze_log.txt`).

## 5. What you should get
- **Reproduction gate** (`results/reproduction/reproduction_check.json`): r(closure) = 0.99956 against exp_3 on 123
  concepts × 2000–2019. Code equality on exp_3's inputs gives r = 1.000000. 6 concepts changed paper sets after
  hydration.
- **Population** (`results/population/`): MAIN = 202 screen + 100 held-out concepts. There are 530 screen MAIN
  (c, t) rows over 138 concepts; complete-case closure_res covers 351 rows / 100 concepts. The F3 rule makes
  `closure_res_imp` co-primary, as recorded in `results/d1/rowcount_decision.json` before any outcome was computed.
- **Verdict** (`results/d1/verdict.json`): **D1_NOT_SUPPORTED_SCREEN**. The primary closure_res coefficients per SD
  (`results/d1/coef_table_primary.csv`) and grouped-CV ΔR² (`results/d1/cv_delta_r2.csv`):

| outcome | coef [95% CI] | Holm p | ΔR² [95% CI] |
|---|---|---|---|
| Y1r | +0.0194 [−0.0098, +0.0408] | 0.405 | +0.0067 [−0.0151, +0.0305] |
| Y2 | +0.0070 [−0.0024, +0.0133] | 0.405 | +0.0123 [−0.0129, +0.0426] |
| log1p Y3 | −0.0650 [−0.1556, +0.0299] | 0.405 | +0.0011 [−0.0123, +0.0146] |

- **Secondary outputs.**
  - `results/d1/robustness.csv`: 132 specifications.
  - `results/d1/mediation.json`: the Y3 indirect effect via W2 cross-community pairs is −0.0276
    [−0.0724, −0.0009]. This is descriptive.
  - `results/power/mde.json`: the held-out MDE is about 0.18–0.21 SD(Y).
  - `results/d1/sanity_checks.json`: placebo, label shuffle, leaky feature, bootstrap stability, determinism.
- **Deliverables.**
  - Figures `figures/fig1..fig6` (PDF + PNG) back the paper's RQ2-D1 results subsection: reproduction, forest plot,
    ΔR², partial dependence, mediation, power.
  - `method_out.json` (full/mini/preview variants) holds one example per primary-model (c, t) row, with
    out-of-fold BASE and FULL predictions.
  - `results_summary.json` and `README.md` are filled automatically from the result files.
- **Audit** (`results/audit_rederive.json`):
  - The 3 primary coefficients are recomputed with the statsmodels formula API and match the pipeline to 1e-16.
  - 20 Y1r values are recomputed by a plain loop and match to 1e-15.
  - The Y3 mediation indirect effect is re-derived.
  - Shuffled-outcome controls reject at 4.5–5.5 % (the nominal 5 %), so the test is not vacuous.
