# Citation gate, viability labels and power check (iteration 2)

This is a CPU-only experiment on the iteration-1 concept corpus (184 main and 22 reference concepts, 208,374 OpenAlex
works with full reference lists). It makes no OpenAlex or LLM calls. It asks whether citation lineages inside a host
subfield are visible enough to label concept→subfield edges as **SOURCE** (local reproduction), **SINK** (sustained
only by imports) or **FADING**. It also asks whether the realised panel has the power to test the pre-registered H1
and Gate-B claims **before** any W2 outcome is opened.

All rules were frozen and hashed before any statistic was computed:
`prereg/prereg_freeze.json`, sha256 `5dd16d8a…5aac`, frozen 2026-09-28T20:55:33Z. Deviations are listed in
`prereg/deviations.md`.

## Headline results

| Step | Result |
|---|---|
| Loader check (iteration-1 lenient any-parent share) | **Reproduced exactly**: main host 0.5518 (n = 41,861); 2010–14: 0.3174/0.3613/0.3476/0.4130/0.5171; reference 0.5311 (n = 92,969). |
| **Gate A** (within-host, non-canonical traced share ≥ 0.40 on > 50% of host edge-years with ≥ 10 children) | **FAIL**: 17.3% of 724 edge-years (97 concepts); mean 0.20, median 0.15. On the same edges the lenient any-parent share is 0.48 (64% ≥ 0.40), so iteration 1's 0.552 overstated host transmission. The within-origin share is 0.47 and the reference-arm host share 0.13. Every downstream label is **DESCRIPTIVE ONLY**. |
| Graft-fallback units (iteration 3) | 2,347 host-entry events; 2,154 have ≥ 5 entry-year keywords (screen 1,285 / held-out 869). |
| Viability layer | 779 eligible host edges (100 concepts). The n_min width rule was not met (median log-ρ CI width 1.3–1.8 in every bin), so the pre-declared fallback **n_min = 30** applies. 169 edges are tested in 38 concepts: 8.1% SOURCE, 3.3% SINK, 0.9% FADING and 87.7% UNDETERMINED over all eligible edges. ρ0 resolves at L1 4% / L2 55% / L3 26% / L4 14%. The sensitivities (EB, REF_BOOT, past-only L3, 3 references, CANON_W1) agree with the main labels on 94–99% of edges. |
| Synthetic validation (known truth, production code) | **Pre-declared criterion FAILS**: realised FDR is **0.209** at n_min 30, against the 0.15 limit. SOURCE is reliable (FDR 0.13); SINK (FDR 0.40) and FADING (0.28) are not, because m absorbs noise citations (m CI coverage 0.62). ρ̃ CI coverage is 0.77 (target 0.90) because ρ0 uncertainty is not propagated. Under misspecification FDR rises to 0.20–0.37, worst when host π is 0.8× the benchmark. Median ρ̃ tracks R monotonically (0.56/0.85/1.02/1.23/1.67 for R = 0.5/0.8/1/1.3/2). |
| Power, H1 (pre-registered SELECTION RULE pipeline) | Realised N_c = **38** concepts with a tested edge (projected 77.5, 90% interval 66–92; far below 150). **H1 = pilot only.** MDE ΔAUC = **0.134** at oracle BASE AUC 0.70 and **0.116** at 0.80. At n_min 5/10 the projected N_c is about 185–190 and the MDE is about 0.034–0.042. Continuous ΔR² MDEs are ≥ 0.03, so they cannot detect effects of Maillart's endogenous size (0.018). Size at γ = 0 is ≤ 1%. |
| Power, **Gate B** (PPML b2) | **FAIL**: 0 labelled episodes (SOURCE + SINK + cooling onset in W2), so the MDE is not estimable. The hypothetical designs, with cooling assigned at random, give MDEs of 56/32/27/18% at 10/30/60/120 clusters, so **≥ ~70 clusters** would be needed for ≤ 25%. With 10 clusters the CRV1 size is inflated (0.16 two-sided); the wild-cluster score bootstrap corrects it to 0.07. |
| Baseline comparison | Tested labels vs the W1 momentum baseline: 47/63 SOURCE edges are also "growing". Spearman(ρ̃, momentum) = 0.14 (p = 0.07, n = 169). ρ̃ carries information beyond momentum, but it is weak. |

## Layout

- `method.py`: orchestrator. Stages: `gate_a viability origin power audit synth p1 figures assemble` (or `all`).
- `src/prereg.py`: Step 0 freeze (verbatim iteration-1 SELECTION RULE copied from the gen_strat_1 file).
- `src/io_load.py`: loaders, within-concept citation table, dedup, lenient flags → `results/cache/prepared.pkl`.
- `src/leakage.py`: `W1View`. Every edge-year function accepts only a view with `t_max = t`.
- `src/lineage.py`: canonical routing, parentage weights, per-edge vectors (a, b, imp, tr), ρ, m, Gate-A shares, momentum.
- `src/labels.py`: paper-cluster bootstrap, BH per (c,t), states, n_min rule.
- `src/benchmark.py`: stationary reference cells, the ρ0 L1–L5 hierarchy, EB, REF_BOOT.
- `src/edges.py`: per-concept workers (reference arm and main arm).
- `src/gate_a.py`, `src/viability.py`, `src/origin.py`, `src/p1.py`, `src/audit.py`: Steps 2, 3, 5-origin, 5-P1, 1.
- `src/power_h1.py`, `src/power_h2.py`, `src/ppml.py`: Step 6. `ppml.py` is a two-way-FE PPML (IRLS, sparse exact projection, CRV1) that is numerically equal to `pyfixest.fepois` with the scipy demeaner (see `tests/test_ppml.py`). The default pyfixest demeaner did not converge on these panels, and the scipy backend took about 3 s per fit.
- `src/synth.py`: Step 4 synthetic lineages (same schema, unchanged production functions).
- `src/figures.py`, `src/assemble_out.py`: figures and `method_out.json`.
- `tests/`: toy lineage (hand-computed ρ, m and weights to 1e-9), BH vs statsmodels, bootstrap coverage, state truth table, **mutation leakage test** (injected post-t papers leave outputs byte-identical), static no-future-read check, and PPML vs pyfixest.
- `results/gate_a/`: `gate_A_verdict.json`, `lenient_loader_check.json`, per-edge parquet, tables by arm × fold × year, graft-fallback events.
- `results/viability/`: `viability_layer.csv` and `viability_layer_part_00.parquet` (one row per eligible edge-year, all columns listed in the plan), `viability_summary.json`, stationary benchmark cells.
- `results/synth/`: `synth_results.json` (confusion matrices, FDR, power by edge size, coverage, per-cell shares, misspecification scenarios) and per-edge parquet.
- `results/power/`: `projection.json`, `h1_mde.json`, `h1_power_curves.csv`, `h1_units_nmin*.csv`, `gate_b.json`, `gate_b_power_curves.csv`, `decisions.json`.
- `results/p1/`: entropy and Rao-Stirling state shares, curves over n_min with concept-bootstrap CIs, the tercile transition matrix, broad-but-hollow candidates. The fixed 2000–04 distance uses cosine for only 7 subfields with ≥ 50 in-corpus citations; about 97% of pairs fall back to taxonomy distance.
- `results/origin/`: O*(c,y) series and cooling onsets (θ = 0.6/0.7/0.8 give 33/51/83 of 184 concepts with an onset).
- `results/audit/`: reconciliation tables 1a–1g (routes 24/160 and 2/20 match; 21 sense flags; origin recompute agreement 100%).
- `figures/`: PDF and PNG figures for Gate A, n_min / labels / benchmark, synthetic validation, P1, H1 power and Gate B power.
- `audit_rederive.py` → `results/audit/rederive.json`: independent re-derivation of every headline number (plain loops over the raw parquet, hand-coded BH) plus placebo checks. All numbers match exactly. A sign-flip placebo of the within vs lenient contrast gives p = 0.16 (real p = 0.0002). Uniform-null p-values give 16 SOURCE labels at the chance rate, against 63 real.
- `reproducibility.md`: exact commands, versions and expected numbers.
- `method_out.json` (+ `full_`/`mini_`/`preview_`): exp_gen_sol_out format. Datasets: `viability_layer_edges` (779), `gate_a_edges` (779) and `synthetic_validation_cells` (100). The baselines are `predict_baseline_growing_edge` and `predict_baseline_lenient_share`.

## How to run

```bash
uv venv .venv --python=3.12 && uv pip install --python .venv/bin/python -r requirements.lock.txt   # exact pins (= pyproject.toml)
.venv/bin/python -m pytest -q -c pytest.ini --rootdir . tests      # T0 tests
.venv/bin/python method.py all                                      # about 25 min on 4 CPUs (H1 power takes about 13 min)
```

Input data is read from the iteration-1 dataset artifact at `<run>/round-1/dataset-1/src`
(see `config.yaml`). `<run>` is resolved as the 4th parent of this directory or taken from the env var `AII_RUN_DIR`.

## Caveats

- Gate A failed, so all labels, P1 shares and power numbers are descriptive or design-stage only.
- The habitat is OpenAlex primary-topic subfield only; no venue habitat is used.
- The canonical top-5 uses the 2026 cited_by_count, the one declared post-t input. The CANON_W1 sensitivity agrees on 98% of edges.
- The benchmark is thin (22 reference concepts); most ρ0 values come from pooled levels L2–L4.
- The iteration-1 hypothesis quote of 13/23/40/54/63 old-rule units is not reproduced exactly (see deviations 7).
- There was no manual audit of lineage links; a 30-edge audit is recommended for iteration 3.

## Restoring removed files

The manifest (`.aii/manifest.yaml`) marks these for deletion after the round:

- `.venv/` (redownloadable): run the `uv venv … && uv pip install …` command above.
- `results/cache/prepared.pkl` (regenerable, 49 MB): `cd src && ../.venv/bin/python -c 'import io_load; io_load.prepare(force=True)'`. `uv run method.py gate_a` also rebuilds it.
- `src/__pycache__/`, `tests/__pycache__/` (regenerable): recreated automatically on import or test.

Everything else, including all of `results/`, `figures/` and `method_out.json`, is small and stays in the published repository.
