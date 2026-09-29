# Reproducibility: K2 host-specific vs generic accessibility

This records what was actually run on 2026-09-29 (UTC).

- Compute: CPU only. 5 cores (cgroup quota 5.1) and 28 GB RAM, on a Linux container that also had an idle RTX 2000 Ada GPU (not used).
- Cost: $0. There were no LLM calls, and `OPENALEX_API_KEY` was unset in every script, so there were no network calls.
- Total wall time: about 35 minutes.

## 1. Environment

The environment is Python 3.12 managed by `uv`. It has 67 pinned packages, identical to `d2/requirements.lock.txt`, which is the lock file vendored from iteration-4 art_WZ8fbLn79nCq. Key versions:

- numpy 2.5.3
- pandas 3.0.6
- scipy 1.18.1
- pyfixest 0.60.0
- matplotlib 3.11.2
- loguru 0.7.3

```bash
uv venv .venv --python 3.12 && uv pip install --python .venv/bin/python -r d2/requirements.lock.txt
export AII_DEPS_ROOT="$(cd ../../.. && pwd)"    # <run>/3_invention_loop (holds iter_1 .. iter_4)
```

## 2. Inputs (read-only, all on the run volume)

- **art_eR1Z7fMlOcxs** `iter_2/gen_art/gen_art_dataset_5`. Files used:
  - `hyd/works/*.parquet`
  - `hyd/concept_work.parquet`
  - `hyd/data_out.json`
  - `hyd/taxonomy.json`
  - `hyd/keywords_dict.json`
  - `hyd/context/subfield_year_totals.json` (`all_types`)
  - `p2/profiles.jsonl`
  - `outputs/nativeness_coverage.json`
  - `deps/gen_art_dataset_2/*.parquet`
- **art_2Cd2JJypeGuA** (iteration-3 exp_7) code, through its byte-identical copy in art_WZ8fbLn79nCq `d2/src`. `results/vendor_hashes.json` records that every file matches both.
- **art_WZ8fbLn79nCq** `iter_4/gen_art/gen_art_evaluation_2`. Cited, not a declared dependency. Copied to `inputs/`:
  - `results/g_features_{screen,heldout}_coprimary.parquet`
  - `results/g_spec.json`
  - `d2/results/{placebo_draws.csv, heldout_confirmation.json, heldout_dryrun_on_screen.json, HELDOUT_OPENED.lock}`
  - `g/g_lib.py` and `g/g_samples.py`, copied to `g/`
- **art_XGdzjWgi-a88** `iter_4/gen_art/gen_art_experiment_9`. `src/` and `vendor/` are copied to `mesh/`. Copied to `mesh/results/`:
  - `results/{outcomes_mesh.parquet, features_mesh.parquet, mesh_spec.json, g4_summary.json, host_coverage.json, placebo_draws_mesh.csv, nativeness_fallback_check.json, events_mesh_summary.json}`
  - `results/nativeness/{profiles_fetched.jsonl, needed_pairs.csv}`
  - The MeSH cache is rebuilt from `iter_1/gen_art/gen_art_dataset_3/works/*.jsonl.gz`. The bg shares come from `iter_1/gen_art/gen_art_dataset_2/data/bg_work_sample.parquet`.

## 3. Commands, in the order they were run

The seed is `20261001`. Every draw is seeded individually, so results do not depend on the worker count.

```bash
.venv/bin/python k2/vendor_hashes.py               # step 0a: 60/60 identical
.venv/bin/python k2/k2_prepare.py main             # step 0b: d2/results/cache/prepared.pkl (~30 s)
.venv/bin/python k2/k2_prepare.py mesh             # step 0b: mesh/cache/{mesh_prepared,bg_shares}.pkl (~30 s)
cd k2
../.venv/bin/python k2_features.py                 # gates A/B (all PASS), partner measures, descriptives (~10 s)
../.venv/bin/python k2_freeze.py                   # results/k2_spec.json sha256 866c60a8... frozen 09:24:22Z
../.venv/bin/python k2_power.py                    # step 3 (1,800 reps, ~90 s), hashed before any K2 fit
K2_SMOKE=1 ../.venv/bin/python k2_run.py           # code/timing test, 20 draws -> results/smoke/ (superseded)
../.venv/bin/python k2_run.py                      # steps 4-7 (~11 min: 24,000 randomisation + 3,000 bootstrap draws)
../.venv/bin/python k2_placebo.py                  # S10 (~2 min)
../.venv/bin/python k2_s2b.py                      # post-hoc S2 diagnostic (~2 min)
cd .. && .venv/bin/python audit/audit_k2.py        # audit (~1 min)
.venv/bin/python eval.py                           # figures + eval_out.json
```

## 4. Deviations from the plan

All deviations were declared in the spec before any coefficient was computed, unless marked post-hoc.

1. **No git commit of the spec.** The freeze is the sha256 plus a UTC timestamp in `logs/freeze_log.txt`, and every script checks the hash. A nested `.git` would interfere with publishing this folder as part of the run repository.
2. **Power simulation design.** The Step-3 simulation uses the fixed observed design rather than concept resampling, because retention is a within-sample ratio.
3. **IVW scale.** IVW pools log-IRR/SD, not raw b, because the fold SDs of A_cont differ.
4. **Randomisation draws.** The full 2,000 Freedman–Lane draws were run for every model. The time fallback was not needed.
5. **MeSH placebo host.** It was run, so the fallback of dropping it was not needed.
6. **S1 retention CI.** This CI (primary FE) comes from the same bootstrap draws. Screen and held-out are flagged thin: G < 50 or retained share < 0.30 (G 77 and retained share 0.26 for screen; G 30 for held-out).
7. **Audit (a), post-hoc fix.** The first audit run used c0 = 0 for A_lift. The held-out fold has one zero-A event, so the spec's fold-wide c0 applies to the whole fold. The audit bug was fixed, and the re-derivation then matched to 3.6e-15.
8. **Audit (d), post-hoc checks.** The oracle as specified is near-collinear and therefore not identified. It is reported as FAIL. Two post-hoc checks were added next to it:
   - d2, whether the total effect is conserved: passes on 2 of 3 folds;
   - d3, the Step-3 generic DGP as the positive control: passes.
9. **S2b (post-hoc).** A diagnostic added after seeing S2, with the explanation in the README. It is not part of the rule.
