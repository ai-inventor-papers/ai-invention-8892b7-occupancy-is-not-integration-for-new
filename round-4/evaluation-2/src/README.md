# D2 held-out confirmation (one look) and G1-G3 artefact tests

This evaluates the iteration-3 D2 host-entry experiment (art_2Cd2JJypeGuA). D2 asks whether the partners a concept arrives with, weighted by their pre-entry "host share", predict uptake by newcomers after the concept enters a new subfield.

The evaluation did four things:

- It vendored the frozen D2 code byte-exact into `d2/` and passed every reproduction gate.
- It froze and hashed a spec (`results/g_spec.json`) for three new artefact tests, G1-G3.
- It opened the sealed held-out fold **exactly once** through the hash-checked `confirm_heldout.py` under a lock file.
- It ran the G tests on the screen, held-out and pooled data, and applied the frozen mechanism rule.

The work is CPU-only and cost $0.

## Headline results

| | value | source |
|---|---|---|
| Gates R0a/R0b/R0c/R0d | R0a: 27/27 hashes match. R0b: dry run bit-identical (co-primary 1.300 [1.164, 1.452], N 1,544, G 140). R0c: max \|diff\| = 0 on 1,746 events. R0d: 8/8 tests pass. | `results/gate_hashes.json`, `d2/results/heldout_dryrun_on_screen.json`, `results/gate_r0c.json` |
| **Held-out co-primary** (concept + e + d FE) | A_cont IRR/SD **1.187 [1.057, 1.335]**, N 972, G 74. CRV1 p 0.0045, Holm p 0.009, wild p 0.012, placebo-calibrated p 0.034, nativeness-permutation p 0.026 (500 draws). CT 1.04 (p 0.60). Reading **GRAFTING = screen reading, so CONFIRMED**. Kill flag: **not dead**. | `d2/results/heldout_confirmation.json`, `results/heldout_post.json` |
| Held-out primary (concept x e + d x e FE) | 0.98 [0.70, 1.37], N 250, G 30. Reading NEITHER, which was declared in advance as **inconclusive (underpowered)** (no MDE on the grid). | same |
| Screen vs held-out heterogeneity | b 4.74 vs 3.07. The difference is not significant (p 0.25). | `results/heldout_post.json` |
| Held-out spec robustness (co-primary FE) | 7/7 rows significant (STRICT, excess anchoring, lower/upper bounds, Y_lenient, Y_all). Field-group strata are descriptive only. | `results/heldout_robustness.csv` |
| Held-out out-of-sample deviance (with A, CT minus controls only) | −0.50 [−1.24, 0.02]. Descriptive only. | `results/heldout_post.json` |
| **Mechanism label** (pooled, frozen rule) | **host-vocabulary (both)**. Pooled G2a: NATIVE 1.11 [1.05, 1.19], ADJACENT 1.32 [1.20, 1.46]. Both CIs exclude 1, and ADJACENT has the larger per-SD effect. The Wald test of equal per-0.1 effects gives p 0.64, so the two classes do not differ per unit of share. | `results/mechanism_label.json` |
| G1 multi-team entries (pooled) | 1.28 [1.11, 1.48], G 161, MDE 1.15, so **not a single-paper artefact**. Screen 1.58 [1.29, 1.94]. Held-out 1.19 [0.98, 1.44], which is inconclusive: G 56 against a held-out MDE of 1.30. | `results/g_*_rows.csv` |
| G3 classifier circularity | Adding min_topic_score + host_topic_share + sec_host_share changes the A log-IRR by **−7.3% [−27.5, 6.7]** on pooled data (−2.4% on screen, −10% on held-out). Nothing is absorbed. The placebo host **PASSES** in every fold and both stratifications (positive-significant share 0.01-0.10, median IRR 0.97-1.03). | `results/g_*_summary.json` |
| Iteration-3 robustness recount (declared rule) | Co-primary FE: **20 of 26** rows with an A term are significant (18 of 22 without the base row and the 3 strata), not "26 of 27". The nulls are binary ≥0.5, binary ≥0.7, A_distinct, excluding single-paper entries, the CS stratum and the Physics/Astro stratum. Primary FE: 2 of 24, one of them a degenerate stratum fit. | `results/robustness_recount.json` |

### Caveats the paper must carry

1. **The held-out G rows are SUPPLEMENTARY.** The frozen `heldout_spec` did not declare them, and the screen G rows were not blind. The mechanism label is "pooled, partially pre-specified".
2. **The host-vocabulary label rests on the per-SD comparison, not a per-unit difference.**
   - ADJACENT shares have a larger SD. The equal-per-0.1 Wald test is null in every fold.
   - G2b shows that all three classes carry positive signal (pooled A_nat 1.12, A_adj 1.35, A_for 1.19).
   - Read this as "the effect is a graded host-leaning gradient that is not confined to native partners", rather than as proof of a distinct re-contextualisation mechanism.
3. **G1 on held-out alone is underpowered and reverses the screen pattern.**
   - The multi-team row is null. The single-paper complement is significant (1.36 [1.14, 1.63]).
   - The multi x A interaction is negative (IRR ratio 0.80, p 0.004).
   - The pooled interaction is null (0.91, p 0.11). The pooled multi-team row is what rules out "artefact".
4. **G3(iii), the only citation-independent (venue ASJC) row, covers about 12% of events.** It is degenerate on the screen fold (N 75, separation-type IRRs) and fails on held-out. Pooled it is estimable (A 1.67 [1.06, 2.63], venue_d_share n.s.) but uninformative, and it is excluded from the mechanism rule. Every G3 control that worked comes from OpenAlex's own classifier, so some residual circularity cannot be excluded.
5. **Placebo-calibrated p uses the placebo z SD recomputed from `placebo_draws.csv`:** 1.38 for the co-primary FE and 1.26 for the primary FE. The iteration-3 summary said 1.3.
6. **CRV1 is anti-conservative on held-out, and the stricter permutation is borderline.**
   - An independent pyfixest audit shuffled A_cont within concepts 200 times. Shuffled z has SD 1.48, and CRV1 rejects in 17.5% of the shuffles.
   - The within-concept permutation p for the held-out headline is **0.050**. For comparison: the spec's nativeness-permutation p is 0.026 and the placebo-calibrated p is 0.034.
   - Report the confirmation as significant under the pre-registered tests, and name the within-concept permutation as borderline (`audit/audit_perm.json`).
7. **The claim remains "across a concept's entries".** Within concept x year, the result is inconclusive on both folds.

## Layout

- `eval.py`: final assembly. It does the robustness recount, the mechanism label, `results/record_of_numbers.csv`, the figures and `eval_out.json` (+ full/mini/preview).
- `d2/`: the iteration-3 D2 experiment, vendored byte-exact. It holds `src/`, `tests/`, `sealed/`, `results/`, `confirm_heldout.py`, `heldout_spec.json` and `requirements.lock.txt`. It also holds:
  - `d2/open_once.sh`: the one-time opening. It refuses to run without a matching `g_spec` hash and refuses ever to rerun.
  - `d2/results/heldout_confirmation.json`: the confirmatory held-out result.
  - `d2/results/HELDOUT_OPENED.lock`: the UTC time and the sha256 values of the result, the `g_spec` and the `heldout_spec`.
- `g/`: new code. It imports the vendored modules and never edits them.
  - `g_lib.py`: features, fits, MDE simulation and placebo host.
  - `g_samples.py`: sample construction.
  - `g_features.py`: builds the per-fold tables and the R0c gate.
  - `g_freeze.py`: sizes, MDEs and the spec freeze.
  - `g_run.py`: all G rows for one fold.
  - `heldout_post.py`: the spec robustness rows on held-out, the 500-draw placebo, the flags and OOS.
  - `gate_hashes.py`: the R0a gate.
- `results/`:
  - `g_spec.json` / `.sha256`: the frozen spec (the freeze time is in `logs/freeze_log.txt`).
  - `g_{screen,heldout,pooled}_rows.csv` and `_summary.json`: every G row, with IRR/SD, CI, CRV1 p, wild p, placebo-calibrated p, Holm p, N, G and retained share.
  - `g_placebo_host_draws_*.csv`, `heldout_robustness.csv`, `heldout_placebo_draws.csv`, `heldout_post.json`, `mechanism_label.json`, `robustness_recount.json`, `record_of_numbers.csv`.
  - `g_features_*.parquet`: the feature tables.
  - `heldout_event_predictions.parquet`.
  - `smoke/`: the pre-freeze code test on random outcomes.
- `figures/`:
  - F1: forest plot of screen, held-out and pooled rows.
  - F2: G2 threshold heatmaps.
  - F3: placebo-host histograms.
  - F4: G1 multi-team vs single-paper rows.
  - Each figure is saved as PNG and PDF.
- `eval_out.json` / `full_eval_out.json` / `mini_eval_out.json` / `preview_eval_out.json` (schema `exp_eval_sol_out`):
  - `metrics_agg` holds 279 flat metrics.
  - Dataset `d2_heldout_events` has 1,097 held-out events: W1 features → Y_strict, with screen-trained predictions.
  - Dataset `g_rows` has 162 model rows.
- `results/deviations_g.md`: deviations from the plan.
- `audit/`: independent re-derivation. `audit_headline.py` refits the headline numbers with pyfixest and pandas and runs shuffled-input placebos; `audit_perm.py` computes the 200-draw within-concept permutation p. Results are in `audit/*.json`.
- `pyproject.toml`: all 67 packages pinned, identical to `d2/requirements.lock.txt`.
- `reproducibility.md`: exact commands.
- `logs/`: the logs.

## How to run

See `reproducibility.md`. In short:

- `export AII_DEPS_ROOT=<run>/3_invention_loop`.
- Build the venv in `d2/`.
- Run in order: `g_features --fold screen` → `g_freeze --draft/--finalize` → `g_run --fold screen` → `d2/open_once.sh` (already done; it cannot be rerun) → `g_features --fold heldout` → `heldout_post.py` → `g_run --fold heldout/pooled` → `eval.py`.

## Storage

Nothing heavy leaves the run volume:

- `d2/results/cache/prepared.pkl` (152 MB) is regenerable.
- `d2/.venv` (2.8 GB) is regenerable.

Both are marked `delete` in `.aii/manifest.yaml`. Every result file is small and published.

## Restoring removed files

```bash
cd d2 && uv venv .venv --python 3.12 && uv pip install --python .venv/bin/python -r requirements.lock.txt   # d2/.venv/
cd d2 && AII_DEPS_ROOT=<run>/3_invention_loop .venv/bin/python -c "import sys; sys.path.insert(0, 'src'); import io_load; io_load.prepare()"  # d2/results/cache/
# g/__pycache__/, audit/__pycache__/, d2/src/__pycache__/, d2/tests/__pycache__/: recreated automatically by python on import
cd d2 && .venv/bin/python -m pytest -q   # d2/.pytest_cache/
```
