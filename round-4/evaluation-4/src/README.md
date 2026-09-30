# RQ2 descriptive layer: held-out confirmation, MeSH second population, and type × rooting

This repository evaluates the frozen RQ2 layer from the iteration-3 experiment (`art_QKsLguxnGFQT`). That layer has four parts: the k=2 diffusion typology, community roles, the expansion/diffusion lead-lag, and the emergence patterns. The evaluation does four things.

1. **One-time held-out opening.** The hash-checked `confirm_heldout.py` (spec sha256 `695166b4…`) ran on a byte-identical copy of the experiment. It scored the frozen decision rules E1-E5 on the 100 sealed held-out MAIN concepts.
2. **MeSH second population.** The same frozen functions ran on 191 new MeSH biomedical descriptors, through a gated adapter and a spec frozen before any MeSH output.
3. **Typology × occupancy/rooting.** Concept types were linked to the D2 host-entry mechanism (`art_2Cd2JJypeGuA`). Occupancy is entries per concept. Rooting is EST_bin, rooted share and Y_strict. Host share is A_cont, and co-transfer is CT. For the held-out fold only sealed W1 features were read; D2's W2 outcome stays sealed.
4. **Supporting outputs.** A lead-lag denominator table with censoring checks, four medoid-selected cases with their host entries, and figures F1-F6.

Everything runs on CPU, costs $0 and makes no API calls.

## Headline results

All numbers below are in `eval_out.json → metrics_agg`, with sources in `results/`.

### Held-out confirmation (E1-E5), frozen rules exactly as evaluated

| Rule | What it tests | Held-out | Screen | Result |
|---|---|---|---|---|
| E1 | BROAD type share | 0.35 [0.26, 0.45] | 0.33 [0.27, 0.39] | **pass** |
| E2 | Types separate validators V1-V3 (same median order, KW p < 0.05 for all 3) | ε² 0.108 / 0.080 / 0.056 | ε² 0.171 / 0.065 / 0.044 | **pass** |
| E3 | Expansion before diffusion | 10 of 10 concepts with both onsets | 15 of 16 | **pass** |
| E4 | Lagged-role entry-hazard ORs keep their sign | BRIDGE OR 1.86 | BRIDGE OR 0.64 | **fail**: signs flip |
| E5 | Pattern frequencies overlap | all overlap | — | **pass** |

- **E3 is weak evidence.** With n_both = 10 the bootstrap CI is degenerate at [1, 1].
- **E4 in detail.** Robust role shares replicate closely: BRIDGE 0.60 vs 0.61, OTHER 0.34 vs 0.33, and FOUNDER / CORE_GROWING 0 in both. Seed agreement is 0.976, against the screen placebo of 0.87. The failure is that the entry-hazard ORs flip sign, so "roles do not predict entry" has no stable direction.

### Is the typology's support adequate?

- **Held-out.** Median margin 0.43 (screen 0.50). 8% of concepts are ambiguous (margin < 0.05) and 7% fall outside the screen 95th-percentile distance. KS test of d1 against the screen: p = 0.13. Held-out concepts sit inside the typology's support.
- **MeSH.** 12.6% of concepts fall outside that distance, median margin 0.34, KS p = 4e-17. MeSH concepts lie further from both medoids.

### Cross-tabs of type with other variables

Holm correction is over the 4 substantive variables within each population.

- **Origin field.** V ≈ 0.28-0.30 in every population. Screen Holm p = 0.015, pooled Holm p = 0.001. The held-out fold alone is not significant (Holm p = 0.29), as the pre-stated MDE (w ≈ 0.35) predicted.
- **E_up emergence group.** Significant on held-out (Holm p = 0.016) and pooled (Holm p = 0.004), but not on the screen.
- **Retrieval route.** Null everywhere.

### Type × rooting

This is a new split. Screen rows are descriptive; the held-out rows are W1 only.

- **Occupancy.** BROAD concepts have many more host entries per concept: 18.4 vs 6.6 on the screen and 23.9 vs 7.2 on held-out.
- **Establishment.** On the screen, BROAD entries establish more often: EST rate 0.31 vs 0.13, rooted share 0.24 vs 0.12.
- **Host share of entries.**
  - The declared prediction was "BROAD concepts enter with higher host share (A_cont)". It is **not supported**.
  - Raw A_cont is *lower* for BROAD: −0.017 [−0.025, −0.010] on the screen, and replicated on held-out.
  - Adjusted for host × entry year and relatedness density, the gap is null: screen −0.0018 [−0.0088, 0.0053], held-out +0.0005 [−0.0099, 0.0109].
- **Co-transfer.** The prediction "BROAD has lower co-transfer" **replicates out of sample**:
  - screen adjusted CT −0.126 [−0.174, −0.078];
  - held-out −0.125 [−0.190, −0.059];
  - pooled −0.109.
- **Does host share matter more for BROAD concepts?** PPML with the D2 co-primary FE gives an A_cont IRR per SD of 1.36 [1.20, 1.55] for BROAD and 1.16 [0.98, 1.38] for LOCALISED. The interaction p is 0.11, so this is exploratory.

**Reading.** The typology measures occupancy. BROAD concepts enter many hosts as smaller packages, and their per-entry host share is not higher. Host share predicts rooting within both types.

### MeSH second population

- **Type share.** BROAD share 0.71 [0.64, 0.77], a lower bound because of the PubMed-only coverage bias. In the 13 retrieval-complete concepts, 1 of 13 switches type (localised → broad) when the non-PubMed works are added, and active_subfields_3y drops by 3.4 under PubMed-only retrieval.
- **Cross-tabs.** Type × MeSH branch group: p = 0.0003, V = 0.35.
- **Lead-lag.** Among the 13 of 191 concepts with both onsets observable, expansion came first in 9. The share, 0.69, is indistinguishable from the year-shuffle null of 0.62 (p = 0.43). 97 concepts are diffusion-only.
- **Roles.** CORE_GROWING and FOUNDER never fire, because max z_within is −0.20 < 1, so the necessary condition fails, as in the main pool. BRIDGE is 0.88. Seed stability was not assessed.
- **Patterns.** Early bridging is 0.71 held-out vs 0.59 MeSH, a difference of +0.12 [0.007, 0.23]. Incubation-then-expansion is 0.17 in MeSH vs 0 in both main folds.

### Lead-lag denominators

Pooled main: among the 26 of 302 concepts with both onsets observable, expansion came first in 25.

The censoring check (Kaplan-Meier and log-rank on time from F to onset) shows diffusion onsets are much rarer than expansion onsets (log-rank p = 0.005 pooled). So the high expansion-first share is conditional on a small, selected denominator. `results/leadlag_denominator_table.csv` gives every count and the F ≤ 2012 cohort.

### Cases

In both BROAD cases the single rooted entry had the highest host share: wireless backhaul +0.062 and EPR steering +0.115 A_cont compared with their non-rooted entries. Locally repairable code has one rooted entry and no contrast. Holographic QCD has no rooted entry: its 5 entries are packaged imports (CT up to 1.0). See `results/case_interpretations.md`.

## Layout

| Path | Contents |
|---|---|
| `eval.py` | Orchestrator: `python eval.py all`, or one or more of `typology rooting mesh leadlag confirmation cases figures assemble`. |
| `evalsteps/base.py` | Paths, Wilson and Newcombe CIs, concept-cluster bootstrap, Holm correction, Cramér's V bootstrap. |
| `evalsteps/typology_extras.py` | Step 2a/2b: DTW distances to the frozen medoids, margins, out-of-support share, permutation cross-tabs, screen reproduction gate. |
| `evalsteps/rooting.py` | Step 2c/2d: type × occupancy/rooting descriptives, pyfixest host × year FE models, PPML interaction, host share per lagged role. |
| `evalsteps/mesh.py` | Step 3: MeSH typology (with coverage bias), lead-lag, roles, patterns. |
| `evalsteps/leadlag_table.py` | Step 4: denominator tables, KM curves, log-rank test, F ≤ 2012 cohort, evaluability. |
| `evalsteps/confirmation.py` | Step 1c: E1-E5 report. |
| `evalsteps/cases_rooting.py` | Step 5: cases with subfield shares, ego position and host-entry tables. |
| `evalsteps/make_figures.py` | Step 6: F1-F6. |
| `evalsteps/assemble.py` | Step 7: `eval_out.json` plus full, mini and preview variants. |
| `scripts/power_mde.py` | Step 0e: MDEs, written before any outcome (`results/power_mde.json`). |
| `scripts/mesh_adapter.py` | MeSH paper tables and channels using the frozen calls; `gate` / `build` subcommands. |
| `scripts/freeze_mesh_spec.py`, `scripts/freeze_rooting_spec.py` | Write the pre-outcome specs and hash them into `logs/freeze_log.txt`. |
| `scripts/mesh_seed_timing.py` | Timing test that decided the MeSH seed-stability skip. |
| `exp8_frozen/` | Byte-identical copy of the frozen RQ2 experiment. Its code is unmodified. |
| `exp8_frozen/heldout_run/` | **The one-time held-out opening.** Contains `OPENED`, all stage outputs, and `results/confirmation.json`. It is kept on the run's volume and cannot be regenerated, because a second opening is refused. |
| `results/` | `confirmation_report.json`, `typology_extras.json`, `typology_distances.csv`, `rooting.json`, `rooting_*_sample*.parquet`, `mesh_results.json`, `mesh/` (adapter outputs, assignments, lead-lag, roles), `leadlag_table.json`, `leadlag_denominator_table.csv`, `cases_rooting.json`, `case_entries.csv`, `case_interpretations.md`, and the specs `power_mde.json`, `rooting_spec.json` and `mesh_spec.json`. |
| `figures/` | F1 case subfield shares with host entries; F2 type × host share, rooting and occupancy; F3 lead-lag categories; F4 roles and GA classes; F5 pattern forest plot; F6 assignment margin and support. PNG at 300 dpi, plus PDF. |
| `logs/` | Open guard, dry run, pytest, held-out opening log, freeze log, MeSH seed timing, eval logs. |
| `eval_out.json` (+ `full_`, `mini_`, `preview_`) | Output in the `exp_eval_sol_out` schema: 292 metrics, plus datasets `concept_level` (493), `case_entries` (33) and `confirmation_rules` (5). |
| `deviations.md` | Every departure from the plan. |
| `reproducibility.md`, `pyproject.toml`, `install.sh` | Step-by-step reproduction, exact pinned environment (uv pip freeze), environment rebuild. |
| `scripts/audit_rederive.py`, `scripts/audit_rederive_ppml.py` | Independent re-derivation of headline numbers plus placebos (`results/audit_rederive.json`). |

## How to run

```bash
bash install.sh                       # copy of the frozen experiment + pinned environment
export AII_LOOP_ROOT=<run>/3_invention_loop
exp8_frozen/.venv/bin/python exp8_frozen/confirm_heldout.py --dry-run --expected-sha 695166b465d36f3311d13bdc7d315204a849ab96dc28c0c36fa002f4ad217d2a
exp8_frozen/.venv/bin/python scripts/power_mde.py
exp8_frozen/.venv/bin/python scripts/mesh_adapter.py gate && exp8_frozen/.venv/bin/python scripts/mesh_adapter.py build
exp8_frozen/.venv/bin/python eval.py all
```

The opening itself (`confirm_heldout.py --open-heldout`) has already happened and **must not be repeated**. `eval.py` reads `exp8_frozen/heldout_run/`, which stays on the run's volume.

## Restoring removed files

After the round ends, only the virtual environment and the Python bytecode caches are deleted. Everything else stays where it is, including `exp8_frozen/heldout_run/` (the one-time opening, kept on the run's volume) and `exp8_frozen/work/`.

| Removed path | How to restore |
|---|---|
| `exp8_frozen/.venv/` | `cd exp8_frozen && uv venv .venv --python 3.12 && uv pip install --python .venv/bin/python -r ../pyproject.toml` (exact pinned versions). `bash install.sh` does the same from exp_8's own pins plus `pyfixest==0.60.0` and `lifelines==0.30.3`. |
| `__pycache__/`, `scripts/__pycache__/`, `evalsteps/__pycache__/`, `exp8_frozen/{src,vendor,tests}/__pycache__/` | Python bytecode, recreated automatically on import. |
