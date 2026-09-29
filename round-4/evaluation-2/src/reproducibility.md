# Reproducibility: D2 held-out confirmation + G1-G3 artefact tests

This page describes what was actually run on 2026-09-29.

- Compute: CPU only, no GPU. 4 cores of an AMD EPYC 9655, on a heavily shared host with load average of 250-330.
- Cost: $0. There are no network calls, no LLM calls and no API keys.
- Total wall time: about 45 minutes. Per-step times are listed below.

## 1. Get the artifact

This workspace is one folder of the run's public GitHub repository. The repository mirrors the run layout `3_invention_loop/iter_N/gen_art/<artifact>/`.

```bash
git clone <repository-url> && cd <repository>/round-4/evaluation-2/src
```

Every path below is relative to this folder.

## 2. System, Python, environment

- Ubuntu with `uv` installed and Python **3.12** (3.12.14 was used).
- The environment lives in `d2/.venv`. It is built from the lock file vendored from the evaluated experiment. The root `pyproject.toml` pins the same 67 packages at the same versions. Key versions: numpy 2.5.3, pandas 3.0.6, scipy 1.18.1, pyfixest 0.60.0, scikit-learn 1.9.1, matplotlib 3.11.2, pyarrow 25.0.1, orjson 3.12.0, loguru 0.7.3.

```bash
cd d2 && uv venv .venv --python 3.12 && uv pip install --python .venv/bin/python -r requirements.lock.txt && cd ..
```

## 3. Inputs and environment variables

No downloads, no API keys. The only environment variable is **`AII_DEPS_ROOT`**, the folder that contains `iter_1/`, `iter_2/` and `iter_3/`.

- In a clone this is `../../..` relative to this folder.
- `g/g_lib.py` and `d2/open_once.sh` derive that default from their own location.
- Set it explicitly for the vendored scripts under `d2/`.

```bash
export AII_DEPS_ROOT="$(cd ../../.. && pwd)"
```

The artifacts read through it are sibling folders of the repository:

- **art_eR1Z7fMlOcxs**, `iter_2/gen_art/gen_art_dataset_5/`. Files used:
  - `hyd/works/works_part_00..07.parquet`
  - `hyd/concept_work.parquet`
  - `hyd/data_out.json`
  - `hyd/taxonomy.json`
  - `hyd/keywords_dict.json`
  - `hyd/context/subfield_year_totals.json`
  - `p2/profiles.jsonl`
  - `outputs/nativeness_coverage.json`
  - `outputs/venue_habitat_asjc.json`
  - `deps/gen_art_dataset_2/{concepts,keywords}.parquet`
- **iteration-2 experiments** `iter_2/gen_art/gen_art_experiment_1/results/test_population.json` and `iter_2/gen_art/gen_art_experiment_3/results/concept_subfield/rs_distance.parquet`.
- **art_2Cd2JJypeGuA**, `iter_3/gen_art/gen_art_experiment_7/`. It is vendored byte-exact into `d2/`; step 0 below shows the copy command.

`g/gate_hashes.py` checks the sha256 of every data file against `d2/heldout_spec.json`. No user-uploaded files are used.

## 4. Commands, in the order they were run

Seeds: the G code uses `20260930` (`g/g_lib.py: SEED`), and the frozen D2 code uses `20260929`. Every bootstrap, simulation and placebo replicate is seeded individually, so results do not depend on the worker count.

```bash
# 0. vendor + gates (about 3 min)
cp -rp ../../../iter_3/gen_art/gen_art_experiment_7/{src,tests,sealed,results,confirm_heldout.py,heldout_spec.json,heldout_spec.sha256,pyproject.toml,requirements.lock.txt,pytest.ini,audit_rederive.py} d2/
d2/.venv/bin/python g/gate_hashes.py                        # R0a: 27/27 hashes -> results/gate_hashes.json
(cd d2 && .venv/bin/python confirm_heldout.py --dry-run)    # R0b: bit-identical to iteration 3 (builds d2/results/cache, ~1 min)
(cd d2 && .venv/bin/python -m pytest -q)                    # R0d: 8 passed
(cd g && ../d2/.venv/bin/python g_features.py --gate-r0c)   # R0c: max |diff| = 0 -> results/gate_r0c.json
# 1. freeze (about 10 min, mostly MDE simulations: 6 targets x 8 grid points x 200 reps)
(cd g && ../d2/.venv/bin/python g_features.py --fold screen)
(cd g && ../d2/.venv/bin/python g_freeze.py --draft)
(cd g && ../d2/.venv/bin/python g_run.py --fold screen --smoke)   # code test on RANDOM outcomes -> results/smoke/
(cd g && ../d2/.venv/bin/python g_freeze.py --finalize)           # results/g_spec.json + .sha256, logs/freeze_log.txt
# 2. screen G rows (about 5 min)
d2/.venv/bin/python g/g_run.py --fold screen
# 3. ONE-TIME opening (about 1 min). REFUSES TO RUN AGAIN: d2/results/HELDOUT_OPENED.lock exists.
d2/open_once.sh
(cd g && ../d2/.venv/bin/python g_features.py --fold heldout)     # about 1 min
d2/.venv/bin/python g/heldout_post.py                             # about 2 min (500-draw placebo)
# 5. supplementary G rows (about 5 + 7 min)
d2/.venv/bin/python g/g_run.py --fold heldout
d2/.venv/bin/python g/g_run.py --fold pooled
# 4. record, figures, eval_out.json, then the independent audit (about 3 min)
d2/.venv/bin/python eval.py
(cd audit && ../d2/.venv/bin/python audit_headline.py && ../d2/.venv/bin/python audit_perm.py)
d2/.venv/bin/python eval.py            # re-run to add the audit metrics
```

**The held-out fold can be opened only once.** `d2/open_once.sh` refuses to run while the lock or `HELDOUT_OPENING_STARTED` exists. The outputs of that one look are committed: `d2/results/heldout_confirmation.json` and the lock.

To reproduce the post-opening numbers, do not re-open. Run the steps from `g_features.py --fold heldout` onward; they reread the already-opened fold deterministically.

## 5. Expected outputs and numbers

All numbers in `eval_out.json` are also listed, each with a source path, in `results/record_of_numbers.csv`.

| Number | Value | File |
|---|---|---|
| Screen co-primary (gate R0b) | A_cont IRR/SD 1.300 [1.164, 1.452], N 1,544, G 140 | `d2/results/heldout_dryrun_on_screen.json` |
| **Held-out co-primary (confirmatory)** | **1.187 [1.057, 1.335]**, N 972, G 74. p 0.0045, Holm 0.009, wild 0.012. Reading GRAFTING, so CONFIRMED, not dead. | `d2/results/heldout_confirmation.json`, `results/heldout_post.json` |
| Held-out co-primary, calibrated p | placebo-calibrated 0.034. Nativeness permutation (spec, 500 draws) 0.026. Audit within-concept A shuffle (200 draws) **0.050**. | `results/heldout_post.json`, `audit/audit_perm.json` |
| Held-out primary | 0.98 [0.70, 1.37], G 30, inconclusive (underpowered) as pre-declared | same |
| Pooled G1 multi-team | 1.28 [1.11, 1.48], G 161 (MDE 1.15) | `results/g_pooled_rows.csv` |
| Pooled G2a NATIVE / ADJACENT | 1.11 [1.05, 1.19] / 1.32 [1.20, 1.46]; mechanism label host-vocabulary (both) | `results/mechanism_label.json` |
| Pooled G3(combined) | −7.3% [−27.5, 6.7] change in the log-IRR; placebo host PASS | `results/g_pooled_summary.json` |
| Iteration-3 robustness recount | 20/26 co-primary rows significant; 2/24 primary rows | `results/robustness_recount.json` |

The paper should use these as follows:

- Confirmation paragraph and table: the held-out row.
- Mechanism and robustness section: the G rows (labelled SUPPLEMENTARY).
- Limitations: the recount, the degenerate venue row and the permutation p values.
- Figures: `figures/F1`-`F4` (PNG + PDF).

Independent audit (`audit/`): pyfixest reproduces the held-out co-primary, pooled G1-multi, pooled G2a NAT/ADJ, pooled G3 % and the recount to within about 1e-9. The tag-by-tag rebuild of A_cont gives max |diff| 0.
