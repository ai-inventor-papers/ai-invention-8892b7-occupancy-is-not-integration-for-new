# Reproducibility: RQ2 held-out confirmation, MeSH second population, type × rooting

This file records what was actually run, on 2026-09-29, in iteration 4 of run `run_spUCG07dPEEP`.

## 1. Get the artifact

This workspace is published as one folder of the run's public GitHub repository. Clone the repository and `cd` into this folder, `round-4/evaluation-4/src/`.

Dependency artifacts are sibling folders of the same repository, laid out as `<LOOP>/iter_N/gen_art/<artifact>`, where `<LOOP>` is the repository's `3_invention_loop/` directory. By default the code resolves `<LOOP>` as three levels above this folder. You can override that with the environment variable `AII_LOOP_ROOT` (the frozen exp_8 code requires it to be set).

| Artifact id | Folder | What is read |
|---|---|---|
| art_QKsLguxnGFQT | `round-3/experiment-8/src` | Frozen RQ2 code and results (copied to `exp8_frozen/`). |
| art_2Cd2JJypeGuA | `round-3/experiment-7/src` | D2 host entries, including the sealed W1 held-out features. |
| art_yWUkgWWKyq_h | `round-2/experiment-4/src` | MeSH snapshots, features and patterns. |
| art_HGiVAYhqO-6q | `round-1/dataset-3/src` | MeSH population and works. |
| art_eR1Z7fMlOcxs | `round-2/dataset-5/src` | Hydrated corpus, read by the frozen prep stage, and `hyd/taxonomy.json`. |

**Caveat on file size.** The publish step skips files of 100 MB or more, and some dependency inputs, such as DS5 `hyd/`, live only on the run volume. A reader without the volume can inspect every output here but cannot rerun the held-out prep from raw data.

No user-uploaded inputs are used.

## 2. System, Python and libraries

- **Hardware:** Ubuntu Linux 6.8, 4 CPU cores (AMD EPYC 9655), 755 GB RAM visible. No GPU.
- **Python:** 3.12.14 via `uv`. `pip` is not used.
- **Environment:** `exp8_frozen/.venv`. It was built from exp_8's pinned `pyproject.toml` plus `pyfixest==0.60.0` and `lifelines==0.30.3`. Installing pyfixest downgraded pandas to **2.3.3**, and everything, including the held-out opening, ran on that version.
- **Pins:** the exact versions (79 packages, from `uv pip freeze`) are in `pyproject.toml` and `logs/pip_freeze.txt`.

```bash
bash install.sh     # tar-copies exp_8 into exp8_frozen/ (keeps an existing heldout_run/), builds exp8_frozen/.venv
# or, to match the exact versions used:
cd exp8_frozen && uv venv .venv --python 3.12 && uv pip install --python .venv/bin/python -r ../pyproject.toml && cd ..
export AII_LOOP_ROOT="$(cd ../../.. && pwd)"
PY=exp8_frozen/.venv/bin/python
```

No API keys are needed. No LLM or OpenAlex calls were made, and the cost was $0.

## 3. Commands actually run, in order

Wall-clock times are for the machine above.

| Step | Command | Output | Runtime |
|---|---|---|---|
| 0a | Copy exp_8 with `tar` (excluding `.venv`, `__pycache__`, `heldout_sim`, `mini_run`) | `exp8_frozen/` | seconds |
| 0b | Open guard: search for `**/heldout_run/OPENED` in exp_8 and in iter_4 | `logs/open_guard.json` (none found) | seconds |
| 0d | `$PY exp8_frozen/confirm_heldout.py --dry-run --expected-sha 695166b465d36f3311d13bdc7d315204a849ab96dc28c0c36fa002f4ad217d2a` | OK: 23 code files and 6 artefacts match (`logs/dry_run.log`) | seconds |
| 0d | `$PY -m pytest -q tests`, run from `exp8_frozen` | 12 passed (`logs/pytest.log`) | 1.6 min |
| 0e | `$PY scripts/power_mde.py`, before any outcome was read | `results/power_mde.json`, hash in `logs/freeze_log.txt` | seconds |
| 1 | `cd exp8_frozen && $PY confirm_heldout.py --expected-sha 695166b4… --open-heldout` (**one time only**; a rerun is refused) | `exp8_frozen/heldout_run/` including `results/confirmation.json` (`logs/heldout_open.log`) | ≈14 min |
| 3b | `$PY scripts/mesh_adapter.py gate` | `results/mesh/adapter_gate.json`: 40 concepts, 829 concept-years, max \|diff\| ≤ 2.2e-16 | < 1 min |
| 3a | `$PY scripts/freeze_mesh_spec.py` (run twice; v1 superseded, see `deviations.md` #4) | `results/mesh_spec.json`, hashes in `logs/freeze_log.txt` | seconds |
| 3b | `$PY scripts/mesh_adapter.py build` | `results/mesh/*.parquet` | ≈2 min |
| 2c | `$PY scripts/freeze_rooting_spec.py` | `results/rooting_spec.json`, hash logged | seconds |
| 2-7 | `$PY eval.py all` (steps: typology, rooting, mesh, leadlag, confirmation, cases, figures, assemble) | `results/`, `figures/`, `eval_out.json` | ≈4 min |
| 7 | aii-json `aii_json_format_mini_preview.py --input eval_out.json` | `full_`, `mini_` and `preview_eval_out.json` (all validate as `exp_eval_sol_out`) | seconds |
| 3e | `$PY scripts/mesh_seed_timing.py 2015` | 99 s per seed-year, so the MeSH seed-stability rerun was skipped (`logs/mesh_seed_timing.txt`) | 1.7 min |
| audit | `$PY scripts/audit_rederive.py && $PY scripts/audit_rederive_ppml.py` | `results/audit_rederive.json` | ≈3 min |

**Seeds.**
- Permutation chi-square: seed 0, 10,000 permutations.
- Concept-cluster bootstraps: seeds 1, 3 and 7, B = 2,000 (role tables B = 1,000).
- Cramér's V bootstrap: seed 0, B = 1,000.
- Year-shuffle null: seed 2026, 1,000 draws.
- MDE simulation: seed 0, 500 draws per cell.
- Frozen exp_8 stages use their own frozen seeds.

## 4. Expected outputs and numbers

All numbers are in `eval_out.json → metrics_agg`, with per-step files in `results/`. The audit reproduced each of the numbers below to at least 1e-6, and the IRRs to 1e-3.

| Number | Value |
|---|---|
| Held-out BROAD share, `heldout_share_broad` (screen 0.327) | **0.35** |
| E1-E5 results | E1, E2, E3 and E5 **pass**; E4 `same_sign_all` **fails** (`results/confirmation_report.json`) |
| Held-out median assignment margin | 0.434 |
| Held-out out-of-support share | 0.07 |
| Adjusted BROAD CT gap, screen / held-out | **−0.126 / −0.125** (held-out CI [−0.190, −0.059]) |
| Adjusted BROAD A_cont gap, held-out | +0.0005 [−0.0099, 0.0109] (declared prediction not supported) |
| EST rate, BROAD vs LOCALISED (screen) | 0.312 vs 0.131 |
| Rooted share, BROAD vs LOCALISED (screen) | 0.239 vs 0.120 |
| Entries per concept, BROAD vs LOCALISED (screen) | 18.4 vs 6.6 |
| PPML A_cont IRR per SD, BROAD / LOCALISED | 1.36 / 1.16 (interaction p = 0.11) |
| MeSH BROAD share (lower bound) | **0.712** [0.644, 0.772] |
| MeSH max z_within | −0.198 (CORE_GROWING cannot fire) |
| Lead-lag, pooled main | expansion first in 25 of 26 concepts with both onsets (N = 302) |
| Lead-lag, MeSH | expansion first in 9 of 13 (N = 191); null p = 0.43 |
| Pooled origin cross-tab | V = 0.282, permutation p = 0.0003 |

**Placebos (all fail, as they should).**
- Type shuffled across concepts: held-out CT gap mean −0.002, 9% of draws significant.
- Type shuffled: screen EST gap null mean 0.000, against an observed 0.181 (permutation p = 0.002).
- Shuffled origin cross-tab: 5.5% of draws have p < 0.05.
- A_cont shuffled within concept: PPML IRRs 1.09 (p = 0.18) and 1.00 (p = 0.97).

**Where the outputs go in the paper.** They feed the RQ2 held-out/replication subsection and the type × rooting subsection.
- Figures: F1 (cases), F2 (type × host share), F3 (lead-lag), F4 (roles), F5 (patterns), F6 (support).
- Case text: `results/case_interpretations.md`.
- Every departure from the plan: `deviations.md`.
