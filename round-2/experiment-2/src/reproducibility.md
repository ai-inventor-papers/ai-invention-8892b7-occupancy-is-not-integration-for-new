# Reproducibility: citation gate, viability labels and power check

This file records exactly what was run to produce the results in this folder (2026-09-28). It uses no network APIs, no
LLM calls and no API keys.

## 1. Get the artifact

This folder is one directory of the run's public GitHub repository.

```bash
git clone <repository-url>
cd <repository>/<path-to-this-folder>        # the folder holding method.py, src/, results/
```

## 2. System, Python and libraries

- OS: Debian 12 container (any Ubuntu 22.04+ works). No system packages beyond a C toolchain are needed. The wheels are prebuilt.
- Python **3.12.14**, managed with [uv](https://docs.astral.sh/uv/).
- Hardware used: 4 CPU cores (AMD EPYC 9654, container quota), 29 GB RAM limit, **no GPU**.

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh          # if uv is not installed
uv venv .venv --python=3.12
uv pip install --python .venv/bin/python -r requirements.lock.txt   # exact pins (same as pyproject.toml)
```

`pyproject.toml` and `requirements.lock.txt` pin all 67 packages actually installed. The key versions are numpy 2.5.3,
pandas 3.0.6, pyarrow 25.0.1, scipy 1.18.1, statsmodels 0.15.0, scikit-learn 1.9.1, pyfixest 0.60.0, matplotlib 3.11.2,
loguru 0.7.3, orjson 3.12.0, pytest 9.1.1 and pyyaml 6.0.3.

## 3. Input data (no downloads)

The only input is the iteration-1 dataset artifact **art_94GEMUsgAmgK** ("New science concepts and their papers",
folder `gen_art_dataset_1`), published in the same repository. The code reads it through ONE path:

- default: `<run>/3_invention_loop/iter_1/gen_art/gen_art_dataset_1` (from `config.yaml`, key `ds1`). `<run>` is
  the 4th parent of this folder, or the value of env var `AII_RUN_DIR`;
- override: set env var **`AII_DS1_DIR`** to the dataset folder (for example `../gen_art_dataset_1` in your clone).

Files read from it: `data_out.json`, `concept_work.parquet`, `works/works_part_00..03.parquet`, `taxonomy.json`,
`context/subfield_year_totals.json`, `sample_frame_frozen.json`, `pending_hydration.json`, `logs/assemble_summary.json`,
`screen.py` and `sample_frame.py` (the last two are quoted in the audit).

The pre-registration step also reads the iteration-1 strategy file
(`<run>/3_invention_loop/iter_1/gen_strat/gen_strat_1/.terminal_claude_agent_struct_out.json`) to copy the SELECTION
RULE verbatim. The frozen copy is already in `prereg/prereg_freeze.json`, so rerunning the prereg is unnecessary: it
refuses to overwrite an existing freeze. No user-uploaded files are used. Env vars and API keys: none required.

## 4. Commands, in the order they were run

All randomness is seeded from `config.yaml` (`seed: 20261001`). The per-edge bootstrap seeds are
`(20261001, sha1(concept), t, d)`, so results do not depend on worker scheduling. `B = 1000`, with 4 worker processes (spawn).

```bash
.venv/bin/python src/prereg.py                    # Step 0: freeze (done once, 20:55:33 UTC; sha256 5dd16d8a...5aac)
.venv/bin/python -m pytest -q -c pytest.ini --rootdir . tests   # T0 tests (12 tests, ~40 s)
.venv/bin/python method.py gate_a                 # cache + lenient loader check + Gate A + graft fallback (~1 min)
.venv/bin/python method.py viability              # Step 3 labels, benchmark, sensitivities (~1 min)
.venv/bin/python method.py origin                 # O* and cooling onsets (~10 s)
.venv/bin/python method.py p1                     # P1 entropy / Rao-Stirling shares (~30 s)
.venv/bin/python method.py audit                  # Step 1 reconciliation tables (~40 s)
.venv/bin/python method.py power_h1               # 6a projection + H1 MDE, 384 tasks x 200 (binary) / 100 (continuous) sims (~13 min)
.venv/bin/python method.py synth                  # Step 4 synthetic validation, 60k edges (~2.5 min)
.venv/bin/python method.py power_h2               # 6c Gate B + decisions.json (~4 min)
.venv/bin/python method.py figures assemble       # figures/ and method_out.json (~30 s)
.venv/bin/python audit_rederive.py                # independent re-derivation + placebo checks (~1 min)
# mini/preview variants (aii-json skill script; any "first 3 examples per dataset" truncation is equivalent)
```

`.venv/bin/python method.py all` runs the same stages (gate_a → assemble) in one call, about 25 minutes on 4 cores.
Note that Gate B uses `src/ppml.py`, a two-way-FE PPML verified equal to `pyfixest.fepois(..., demeaner_backend="scipy")`
in `tests/test_ppml.py`. The default pyfixest demeaner failed to converge on these panels.

## 5. Expected outputs and numbers

| Quantity | Value | File |
|---|---|---|
| Lenient loader check (iteration-1 reproduction) | main host 0.5518 (n = 41,861); 2010–14 0.3174/0.3613/0.3476/0.4130/0.5171; reference 0.5311 (n = 92,969) | `results/gate_a/lenient_loader_check.json` |
| Gate A verdict | FAIL; 17.27% of 724 host edge-years (97 concepts) have within-host share ≥ 0.40 (mean 0.204; lenient 0.477) | `results/gate_a/gate_A_verdict.json` |
| n_min | rule not met → 30 (fallback) | `results/viability/viability_summary.json` |
| Viability labels | 779 eligible edges; 169 tested (38 concepts); SOURCE 63, SINK 26, FADING 7, UNDETERMINED 683 | `results/viability/viability_layer.csv` |
| Synthetic validation | realised FDR 0.209 at n_min 30 (criterion ≤ 0.15 FAILS); ρ̃ CI coverage 0.77; m coverage 0.62 | `results/synth/synth_results.json` |
| Projection | N_c realised 38, projected 77.5 (90%: 66–92) at n_min 30 | `results/power/projection.json` |
| H1 MDE (ΔAUC, realised, n_min 30) | 0.134 (BASE AUC 0.70), 0.116 (0.80); H1 = pilot only | `results/power/h1_mde.json`, `decisions.json` |
| Gate B | 0 labelled episodes → MDE not estimable → FAIL; hypothetical 10/30/60/120 clusters MDE 56/32/27/18% | `results/power/gate_b.json` |
| Independent re-derivation | all of the above match exactly (0 edge mismatches for Gate A) | `results/audit/rederive.json` |

Figures are in `figures/` (Gate A distributions, n_min and labels, synthetic validation, P1 shares, H1 power, Gate B
power). These numbers feed the iteration-2 paper draft's sections on the citation-lineage gate (Gate A), the viability
layer (descriptive), labeller validation and the design-stage power analysis. The simulation-based power numbers can
differ in the last digit on a different BLAS or CPU. The labels and the Gate A figures are deterministic.
