# K2: is the host-entry effect host-specific, or just common words?

**Label: POST-CONFIRMATION EXPLORATORY.** Every fold was already opened in earlier iterations, so nothing here is confirmatory. CPU only, $0 API spend, no network calls.

## The question

When a concept enters a new subfield d, some of its partner keywords already have a high "host share": a large fraction of their pre-entry literature sits in d. The confirmed D2 result is that a higher mean host share (A_cont) predicts more uptake of the concept in d by newcomers. On the co-primary FE (concept + e + d), the IRR per SD is:
- screen: 1.300;
- held-out: 1.187;
- MeSH: 1.233.

K2 tests a rival explanation, **generic accessibility**: host-leaning partners might simply be widely used, frequent words that make any paper findable. The test adds the two standard term-generality proxies, both computed from exact pre-entry OpenAlex subfield × block profiles:
- **G_H**: the tag-weighted mean normalised Shannon entropy of each partner's subfield profile (dispersion);
- **G_F**: the tag-weighted mean log block frequency (volume).

It also replaces A_cont with its RCA / Activity-Index form, **A_lift** = ln(A_cont / s_d,B).

## Headline

The frozen decision rule gives **HOST-SPECIFIC** on the IVW pool (the pre-declared reading) and in every fold. No qualifier fires on the pool.

| | M0 A_cont IRR/SD | M1 A_cont \| G | retention b(M1)/b(M0) [95% concept-bootstrap CI] | M3 A_lift \| G IRR/SD | M1 G_H | M1 G_F | verdict |
|---|---|---|---|---|---|---|---|
| screen (N 1,544, G 140) | 1.300 [1.164, 1.452] | 1.302 [1.158, 1.464] | **1.01 [0.73, 1.31]** | 1.66 [1.36, 2.03] | 1.12 [0.87, 1.45] | 0.86 [0.70, 1.05] | HOST-SPECIFIC |
| held-out (N 972, G 74) | 1.187 [1.057, 1.335] | 1.200 [1.060, 1.360] | **1.06 [0.44, 1.80]** | 1.46 [1.15, 1.86] | 1.07 [0.84, 1.35] | 0.94 [0.77, 1.16] | HOST-SPECIFIC (retention CI includes 0.5: not decisive) |
| MeSH (N 2,171, G 160) | 1.233 [1.117, 1.361] | 1.201 [1.082, 1.334] | **0.88 [0.64, 1.04]** | 1.24 [1.12, 1.38] | 1.11 [0.98, 1.25] | **0.76 [0.68, 0.86]** | HOST-SPECIFIC |
| **IVW pool** | 1.240 [1.166, 1.319], I² 0 | 1.232 [1.154, 1.315], I² 0 | **0.97 [0.81, 1.10]** | **1.34 [1.23, 1.46]**, I² 0.72 | 1.10 [1.00, 1.22] | **0.81 [0.74, 0.89]** | **HOST-SPECIFIC** |

- **Almost none of the effect is removed.** Pooled pct_removed is 3.1%. A_lift retention (M3 vs M2) is 0.90 [0.81, 0.97].
- **The focal terms survive every test.** Across folds, M1 A_cont and M3 A_lift pass CRV1, the 999-draw wild score bootstrap, the placebo-calibrated p and the 2,000-draw within-concept Freedman–Lane randomisation p:
  - randomisation p ≤ 0.001 on screen and ≤ 0.0035 on MeSH;
  - randomisation p 0.029 (M1) and 0.023 (M3) on held-out.
  - No "fragile" flag fires.
- **The generic story makes predictions that fail:**
  1. It predicts generality proxies with IRR > 1. Instead, frequency *lowers* uptake: pooled G_F is 0.81, strongest in MeSH. Dispersion is at most weakly positive: pooled G_H is 1.10 [1.00, 1.22].
  2. It predicts that host share is positively tied to generality. Instead, within FE, A_cont is *negatively* correlated with both proxies:
     - r(A_cont, G_H): −0.22 / −0.16 / −0.39;
     - r(A_cont, G_F): −0.11 / −0.06 / −0.25;
     - generality explains only 3–16% of A_cont's within-FE variance.
  3. It predicts that the placebo host (S10) gains signal once generality is held fixed. Instead, S10 passes in every fold under M1, with share positive-significant 0.07 / 0.00 / 0.00 and median IRR 0.98 / 0.97 / 0.99. That is no higher than the no-generality placebo.
  4. It predicts that ADJACENT partners lose more to the generality controls (S3). Instead, pooled ADJACENT retention is 1.04 and NATIVE retention is 0.89.
- **Design analysis (Step 3, run before any K2 fit):**
  - Under a host-specific DGP, P(retention ≥ 0.5) is 1.00 / 1.00 / 0.99 per fold and 1.00 pooled.
  - Under a generic DGP (outcome driven by the part of A_cont that generality predicts), P(retention < 0.5) is 1.00 everywhere.
  - So every fold could separate the two readings. The observed retentions sit inside or above the host-specific range.

### Caveats the paper must carry

1. **Post-confirmation and exploratory.** K2 gives a bounded interpretation of an already-confirmed effect, not a new confirmation.
2. **The A_lift leg adds little independent evidence.** Within FE:
   - corr(A_lift, ln A_cont) is 0.997 / 0.997 / 0.999;
   - ln s_d,B carries only 0.3–0.7% of A_lift's variance.
   - "A_lift CI excludes 1" therefore mostly tests the log-vs-linear functional form. **The generality retention is the decisive leg.**
   - The pooled A_lift estimate is heterogeneous (I² 0.72, Q p 0.03; screen 1.66 vs MeSH 1.24). The pooled A_cont estimate is not (I² 0).
3. **The held-out retention alone is not decisive.** Its CI is [0.44, 1.80]. The pooled CI [0.81, 1.10] excludes 0.5.
4. **The pre-declared split-generality row S2 is partly mechanical.** It absorbs A_cont (retention 0.51 / 0.95 / 0.31; pooled A_cont 1.11 [0.96, 1.28]). But GH_nat = Σ_native H_p / n equals (native share) × (mean native entropy) to within r 0.97, so it re-encodes the host-share composition that A_cont measures (within-FE r(A_cont, GH_nat) 0.78).
   - A **post-hoc diagnostic** (S2b, `results/k2_s2b_diagnostic.json`, not pre-specified) holds the *within-class mean* entropy and frequency fixed instead. Those means are uncorrelated with A_cont (|r| ≤ 0.15). A_cont then stays at 1.18 [1.09, 1.28] pooled (retention 0.77).
   - The paper should report S2 with this explanation rather than as evidence for the generic reading.
5. **Generality is observed only for profiled partners.** Main tags are 78.7% profiled; MeSH generality uses exact profiles only (bg-filled tags enter A_cont but not G).
   - If rare, unprofiled partners were the specific ones, retention would be biased toward 1.
   - The cov ≥ 0.8 subset (S7) gives retention 1.03 / 0.79 / 1.15 (held-out: N 552, G 48, A n.s.).
   - The bg-entropy sensitivity (S8, MeSH) gives 0.92.
6. **No pair-level conventionality (Uzzi-style) measure** and **no Oster δ bound** (PPML pseudo-R² does not map onto it). Two partner-level proxies do not rule out every generic confounder.
7. **Within concept × year (S1, primary FE) the retention is uninformative.** Screen (G 77) and held-out (G 30) are thin, with retention CIs spanning ±4 to ±19. MeSH (G 122) gives M1 A_cont 1.38 [1.14, 1.68].
8. **The Step-3 host-specific DGP is conservative.** mu0 carries the fitted G terms from the no-A fit, and those partly proxy A_cont, so the simulated host-specific retention centres at 0.77–0.90 rather than 1.
9. **The oracle audit check failed as specified; the positive control passed.** The oracle (G_H := A_cont + noise at 0.1 SD) is near-collinear (r 0.995; A_cont SE about 10× larger), so its retention is noise (−0.23 / 3.38 / 2.17). The pre-declared positive control of *retention* is therefore the Step-3 generic DGP simulation, which passes (P(ret < 0.5) = 1 in every fold). The other audit checks pass:
   - 30-entry plain-loop re-derivation, max |diff| 3.6e-15;
   - pyfixest, |db| < 3e-14, pooled retention identical;
   - shuffled-G retention means 0.998 / 0.999 / 1.000.

## How the numbers were produced

1. **Gates** (`results/gates.json`, all PASS):
   - GATE-A: A_cont rebuilt from tags matches the stored column to max |diff| 1.1e-16 on all 5,086 events.
   - GATE-B: the recorded co-primary is reproduced exactly (|Δ ln IRR| < 1e-15; N/G 1,544/140, 972/74, 2,171/160).
   - The held-out fold was opened once in iteration 4. Its lock file sha256 is recorded, and `config.SEALED_IDS` was cleared as `heldout_post.py` does.
2. **Partner measures** (`results/partner_generality.parquet`, one row per event) and outcome-free descriptives (`results/k2_descriptives.json`).
3. **Freeze**: `results/k2_spec.json` was hashed at 09:24:22Z (sha256 `866c60a8…`, `logs/freeze_log.txt`) before any K2 coefficient. Every later script calls `assert_spec_frozen()`.
4. **Retention design analysis**: `results/k2_power.json`, 300 reps × 2 DGPs × 3 folds, hashed before the fits.
5. **K2 fits** (`k2/k2_run.py`):
   - M0–M3 per fold on the identical input sample;
   - CRV1 t(G−1), wild (999), placebo-calibrated p, Freedman–Lane randomisation (2,000 per model, 24,000 PPML refits);
   - 1,000 concept-bootstrap draws per fold, all models refit per draw;
   - IVW pool of log-IRR/SD, with the pooled retention CI from combined draws;
   - the frozen rule, then S1–S9 and S11.
6. **Placebo host S10** (`k2/k2_placebo.py`): 100 size-decile draws per fold. MeSH also applies the exp_9 coverage rule; 111 of 2,249 MeSH events have no candidate.
7. **Audit** (`audit/audit_k2.py`, a separate code path): `audit/audit_k2.json`.

## Layout

| path | what |
|---|---|
| `k2/k2_lib.py` | shared code: tag arrays, H_p / F_p / s_dB, entry means, A_lift, A_spec, fits, IVW, workers |
| `k2/k2_prepare.py` | rebuilds the regenerable caches (main `prepared.pkl`, MeSH `mesh_prepared.pkl`, bg shares) with no network |
| `k2/k2_features.py` | gates A and B, partner generality, descriptives |
| `k2/k2_freeze.py` | freezes `results/k2_spec.json` |
| `k2/k2_power.py` | Step-3 retention design analysis |
| `k2/k2_run.py` | M0–M3, p-value set, bootstrap, IVW, verdict, supplementary rows |
| `k2/k2_placebo.py` | S10 placebo host under M1 |
| `k2/k2_s2b.py` | post-hoc S2 diagnostic (not pre-specified) |
| `k2/vendor_hashes.py` | sha256 of every vendored file vs its source (`results/vendor_hashes.json`; all 60 identical) |
| `audit/audit_k2.py`, `audit/audit_k2.json` | independent audit |
| `eval.py` | figures and `eval_out.json` (schema `exp_eval_sol_out`: 297 flat metrics; datasets `k2_rows` (123) and `entry_generality` (5,086)); also `full_`/`mini_`/`preview_eval_out.json` |
| `results/k2_rows.csv` | every model row: fold, model, var, b, SE, z, CRV1/wild/placebo-cal/randomisation/Holm p, IRR/SD + CI, IRR per 0.1, N, G, retained share, label, run-root-relative source paths; includes the pooled IVW rows |
| `results/k2_summary.json` | per fold and pooled: verdict, qualifiers, retention and CI, ret_lift, focal and G terms, p set, power, supplementary rows |
| `results/k2_spec.json` / `.sha256` | the frozen spec |
| `results/k2_power.json` / `.sha256`, `results/k2_power_reps.csv` | design analysis |
| `results/k2_boot_draws.csv`, `results/k2_perm_draws.csv` | bootstrap and randomisation draws |
| `results/k2_placebo_host.json`, `results/k2_placebo_host_draws.csv` | S10 |
| `results/k2_s2b_diagnostic.json` | post-hoc S2 diagnostic |
| `results/smoke/` | pre-run code test (20 draws); superseded by the full run |
| `figures/F1_k2_forest`, `F2_retention`, `F3_generality_scatter` (`.png`, `.pdf`) | figures |
| `d2/src/`, `g/`, `mesh/src/`, `mesh/vendor/` | vendored code (byte-identical to art_WZ8fbLn79nCq, art_2Cd2JJypeGuA and art_XGdzjWgi-a88) |
| `inputs/`, `mesh/results/` | read-only copies of the recorded event tables, gate records, placebo draws and MeSH profiles |
| `pyproject.toml`, `d2/requirements.lock.txt` | 67 pinned packages (Python 3.12) |
| `logs/` | run logs and the freeze log |

## How to run

See `reproducibility.md`. In short:

```bash
export AII_DEPS_ROOT=<run>/3_invention_loop        # folder holding iter_1 .. iter_4
uv venv .venv --python 3.12 && uv pip install --python .venv/bin/python -r d2/requirements.lock.txt
.venv/bin/python k2/k2_prepare.py all                # ~1 min, caches
cd k2 && ../.venv/bin/python k2_features.py && ../.venv/bin/python k2_freeze.py   # freeze refuses to overwrite
../.venv/bin/python k2_power.py && ../.venv/bin/python k2_run.py && ../.venv/bin/python k2_placebo.py
../.venv/bin/python k2_s2b.py && cd .. && .venv/bin/python audit/audit_k2.py && .venv/bin/python eval.py
```

## Storage

Nothing heavy is kept. Every regenerable cache is marked `delete` in `.aii/manifest.yaml` and also excluded from the upload by the regexes `(^|/)cache/`, `(^|/)\.venv/` and `__pycache__`. All results are small text or parquet files and are published.

## Restoring removed files

```bash
uv venv .venv --python 3.12 && uv pip install --python .venv/bin/python -r d2/requirements.lock.txt  # .venv/
AII_DEPS_ROOT=<run>/3_invention_loop .venv/bin/python k2/k2_prepare.py main   # d2/results/cache/prepared.pkl
AII_DEPS_ROOT=<run>/3_invention_loop .venv/bin/python k2/k2_prepare.py mesh   # mesh/cache/{mesh_prepared,bg_shares}.pkl
cd k2 && ../.venv/bin/python k2_features.py      # cache/k2_samples.pkl (also rewrites gates/descriptives identically)
# __pycache__/ directories are recreated automatically by python on import
```
