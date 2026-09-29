# Reproducing the K1 / K3 / INFERENCE evaluation

This is exactly what was run on 2026-09-29, with times in UTC.

## 1. Get the artifact

This workspace is published as one folder of a public GitHub repository.

```bash
git clone <repository-url>
cd <repository>/<this-folder>          # the folder that holds eval.py, k/, audit/, d2/, mesh/, inputs/
```

The folder is self-contained for every K result:

- **`inputs/`** holds byte-exact copies of the three frozen event tables:
  - `g_features_screen_coprimary.parquet` and `g_features_heldout_coprimary.parquet`, from art_WZ8fbLn79nCq;
  - `outcomes_mesh.parquet`, from art_XGdzjWgi-a88.

  Their sha256 values are in `results/input_hashes.json`.
- **`d2/`** is the byte-exact vendored D2 estimator stack (from art_WZ8fbLn79nCq, originally art_2Cd2JJypeGuA).
- **`mesh/`** is the vendored MeSH code and `mesh_spec.json` (art_XGdzjWgi-a88).

No user-uploaded file is used.

## 2. System, Python and libraries

What was used:

- **OS and hardware:** Debian 12 container, 6 CPUs (cgroup quota; 5 worker processes), 28 GB RAM limit. No GPU was used (CPU only).
- **Python and uv:** Python 3.12, with `uv`. `pip` is not used.

```bash
uv venv .venv --python 3.12
uv pip install --python .venv/bin/python -r d2/requirements.lock.txt
```

`d2/requirements.lock.txt` (67 pins) is identical to the dependency list in `pyproject.toml`; `uv pip freeze` of the venv matches it line for line. Key pins: numpy==2.5.3, pandas==3.0.6, scipy==1.18.1, pyfixest==0.60.0, matplotlib==3.11.2, loguru==0.7.3, pyarrow==25.0.1.

## 3. Data, environment variables, keys

- **No downloads, no API keys, no LLM calls.** The run cost $0.
- **`AII_DEPS_ROOT`** (optional) is the directory that holds `iter_4/gen_art/gen_art_evaluation_2/` (art_WZ8fbLn79nCq) as a sibling. It defaults to three levels above this folder. It is read only by:
  - gate R0a (`k/k_freeze.py`), which compares the vendored d2 hashes with art_WZ8fbLn79nCq's `results/gate_hashes.json` and records the held-out lock hash;
  - the lock-untouched check in `k/report.py`. If the folder is absent, that check is reported as `null`.
- **No other variable is needed.** `k/k_lib.py` sets `OPENBLAS/OMP/MKL_NUM_THREADS=1`.

## 4. Commands, in the order they were run

```bash
export AII_DEPS_ROOT=<path-to>/3_invention_loop     # only for gate R0a / lock check
.venv/bin/python k/k_freeze.py --gates-only           # R0a-R0e -> results/gates.json            (~30 s)
.venv/bin/python k/k_freeze.py --reps 6 --skip-pytest # freeze dry run -> results/smoke/k13_spec_dryrun.json
.venv/bin/python k/k_freeze.py --reps 300             # gates + MDE sims (15,600 fits) + FREEZE     (~2.5 min)
                                                      # -> results/k13_spec.json, k13_spec.sha256, logs/freeze_log.txt
.venv/bin/python k/k_run.py --synthetic               # smoke test on NB2 synthetic outcome -> results/smoke/ (~2.5 min)
.venv/bin/python k/k_run.py --stage all               # K1 (1,000 cluster-bootstrap draws/fold), K3 (2,000 label perms),
                                                      # INFERENCE (2,000 rand-t + 2,000 Freedman-Lane draws/fold,
                                                      # 9,999 Webb + 999 Rademacher wild draws)          (~5.5 min)
.venv/bin/python audit/audit_k.py                     # independent pyfixest re-derivation -> audit/audit_k.json (~1 min)
.venv/bin/python k/report.py                          # verdicts, figures, record_of_numbers, eval_out.json (~20 s)
.venv/bin/python audit/audit_placebo.py               # raw-file re-derivation + placebos -> audit/audit_placebo.json (~1 min)
```

The same sequence is wrapped in `eval.py`: `.venv/bin/python eval.py`. It skips the freeze when `results/k13_spec.json` exists, because re-freezing would change the hash that every run script asserts.

The mini/preview JSON variants were made with the aii-json formatter: `full_eval_out.json`, `mini_eval_out.json` and `preview_eval_out.json`.

**Seeds** (all in `results/k13_spec.json`):

| Use | Seed |
|---|---|
| Base | `SEED = 20261001` |
| Randomization-t draw i | SEED + i |
| Freedman-Lane draw i | SEED + 1,000,000 + i |
| Wild bootstrap | SEED + 2,000,000 (+100,000 per variant) + fold index |
| K1 bootstrap | SEED + 3,000,000 + i |
| K3 permutations | SEED + 4,000,000 + i |
| MDE simulations | SEED + 7/8/9,000,000 + rep·101 + grid |
| `audit_k.py` | 777 |
| `audit_placebo.py` | 555 |

**Determinism.** Every draw is seeded independently of worker scheduling, so results are identical across runs and worker counts. The code change made after the freeze is logged in `logs/freeze_log.txt`: it affects result-dict assembly only, not the estimator, samples or rules.

## 5. What you should get

| Quantity | Value | File |
|---|---|---|
| Spec sha256 | `2435f909758bfab445fc28adab7b99efb5e4eed44a9f0e9b7377c1a470ddbbd5` | `results/k13_spec.sha256` |
| R0b co-primary IRR/SD (screen / held-out / MeSH) | 1.300 / 1.187 / 1.233 (exact reproductions) | `results/gates.json` |
| K1 IVW extensive (LPM) | +6.43 pp/SD [4.76, 8.11], I² 0 | `results/k1_rows.csv` |
| K1 IVW intensive (PPML on Y≥1) | IRR/SD 1.183 [1.104, 1.267] | `results/k1_rows.csv` |
| K1 IVW extensive share | 0.38 [0.21, 0.55] | `results/k1_decomposition.json` |
| K1 verdict | **BOTH** | `results/k13_summary.json` |
| K3 Wald equality p (CRV1) / label-permutation p | 0.638 / 0.770 | `results/k3_results.json` |
| K3 phys/rest ratio (MDE80) | 0.942 [0.740, 1.199] (0.72) | `results/k3_results.json` |
| K3 verdict | no detectable field boundary | `results/k13_summary.json` |
| Held-out p: randomization-t / Freedman-Lane / WCR-Webb | 0.023 / 0.025 / 0.012 | `results/inference_rows.csv` |
| MeSH / IVW randomization-t p | 0.0015 / 0.0005 | `results/inference_rows.csv` |
| Audits | `all_pass: true`; `pass: true` | `audit/audit_k.json`, `audit/audit_placebo.json` |

The figures are `figures/k1_margin_forest`, `k1_ladder`, `k3_field_forest` and `inference_null_z`, each as PNG and PDF. In the paper they belong to the D2 results section on mechanism (which margin), on scope (the field boundary) and on inference robustness. Every number is labelled POST-CONFIRMATION EXPLORATORY; see `README.md` for the caveats.
