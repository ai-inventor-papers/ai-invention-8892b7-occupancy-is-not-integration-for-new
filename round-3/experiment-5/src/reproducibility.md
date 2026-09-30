# Reproducibility

- Environment: Python 3.12.14, uv-managed `.venv` from `pyproject.toml` (numpy 2.5.3, pandas 3.0.6, networkit 11.2.2, scikit-learn 1.9.1,
  statsmodels 0.15.0, networkx for tests). CPU only (4 cgroup CPUs, 29 GB RAM cap; scripts set RLIMIT_AS 26 GB). No API or LLM calls ($0).
- Inputs (read-only): `../../../round-2/experiment-3/src` (snapshots, code vendored byte-identical, hashes in
  `vendor/vendor_sha256.json`), `../../../round-2/dataset-5/src/hyd`, and
  `../../../round-2/experiment-1/src/results/test_population.json` (sha256 6a887fb4...5505).
  sha256 of every snapshot / dataset_5 file used: `heldout_spec.json -> input_manifest`.
- Commands:
  ```bash
  uv venv .venv --python=3.12 && uv pip install --python=.venv/bin/python -r pyproject.toml
  .venv/bin/python -m pytest -q tests                 # 64 passed (~20 s)
  OMP_NUM_THREADS=1 .venv/bin/python method.py        # full pipeline, 451 s on 4 CPUs
  .venv/bin/python confirm_heldout.py --self-test-on-screen
  ```
- Step runtimes (last run): attach 3 modes x 25 years ~110 s; indicators 63 s; sealed attach+indicators 55 s; event study
  114 s; power 6 s; prediction 26 s; audit 8 s.
- Seeds (SPEC3, `prereg_v3.json`): event-study bootstrap seed = stable_seed(row, cell, 20261001) (B = 2,000); pooled panel 7;
  CV seeds 0-4, label shuffle 11; MDE simulation 13 (500 sims, B = 400); cross-community null stable_seed(concept, year, 'XC')
  (50 draws); betweenness pivots seeded 20260928 + year (networkit, 1 thread). Runs are deterministic.
- Expected numbers:
  - reproduction gate: closure r = 1.000000 (code mode), 0.9996 (data mode); E_up 41 onsets / 21 matched,
    S = -0.8370 [-1.2600, -0.4268];
  - primary cell MAIN x all x E_up: 68 onsets, 26 matched; raw closure S -0.439 [-0.810, -0.050]; closure_resT -0.295
    [-0.663, 0.092]; closure_persist -0.575 [-1.270, 0.122]; constraint +0.083 [0.017, 0.147]; verdict MIXED;
  - prediction dAUC(FULL - BASE) -0.001 [-0.008, 0.006]; held-out expected matched treated 12 [8, 16].
- Freeze log (`results/freeze_log.jsonl`): prereg_v3.json sha256 2f46d173...776b (04:16:24Z, before labels);
  heldout_spec.json sha256 535c2dd3...09b2 (04:34:59Z).
