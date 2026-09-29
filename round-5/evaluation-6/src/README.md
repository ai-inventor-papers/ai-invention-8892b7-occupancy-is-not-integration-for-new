# Which margin idea rooting acts on: K1 margins, K3 field boundary, size-correct inference

**Label: POST-CONFIRMATION EXPLORATORY.** Every fold was already open before this work started, and the total D2 effect was known. Only the K-specific coefficients were unseen when the spec was frozen. The spec is `results/k13_spec.json`, sha256 `2435f909…ddbbd5`, frozen 2026-09-29T09:32:18Z (`logs/freeze_log.txt`) before any K coefficient was computed.

This artifact is a CPU-only, $0 evaluation of the confirmed D2 host-entry effect: host-leaning entry vocabulary (`A_cont`) predicts newcomer uptake (`Y_strict`) of a concept in a new host subfield. It asks three questions:

- **K1:** does the effect act on whether uptake *starts* (extensive margin) or on *how much* follows (intensive margin)?
- **K3:** does the effect stop at Physics/Astro-origin concepts?
- **INFERENCE:** are the headline p values size-correct with few clusters?

The inputs are the frozen screen, held-out and MeSH event tables. No fold was reopened, there were no API calls, and the held-out lock is untouched (its sha256 was checked before and after the run).

## Verdicts (frozen rules, quoted verbatim in `results/k13_spec.json`)

| Test | Verdict | Numbers that triggered it | Source |
|---|---|---|---|
| K1 | **BOTH** | IVW extensive (LPM) **+6.43 pp/SD [4.76, 8.11]**, randomization-t p 0.0005; IVW intensive (PPML on Y≥1) **IRR/SD 1.183 [1.104, 1.267]**; I² = 0 for both | `results/k13_summary.json` → K1 |
| K3 | **No detectable field boundary**; the physics screen null is within sampling variation | Wald equality (3 origin groups, 2 df, CRV1) p **0.638**, label-permutation p **0.770**; Physics/Astro-minus-rest ratio **0.942 [0.740, 1.199]**; MDE80 ratio **0.72** | `results/k3_results.json` |
| INFERENCE | **Held-out survives size-correct inference** | Randomization-t p **0.023** (Freedman-Lane 0.025, WCR-Webb 0.012); MeSH 0.0015; IVW 0.0005 | `results/inference_summary.json` |

The independent audit passes every check (`audit/audit_k.json`, `all_pass: true`).

**What this means for the paper:** the D2 effect is not only 'larger uptake among entries that would have taken off anyway'. One SD of `A_cont` raises the probability that *any* newcomer uptake starts by about 6.4 pp, about 12–14% of the base rate of about 0.51, in all three populations. The size given that uptake started is also about 18% higher per SD. By the log-link decomposition, about 38% of the combined log effect is on the extensive margin (IVW share 0.38 [0.21, 0.55]).

The intensive part conditions on Y ≥ 1. It is a descriptive conditional association, not a causal effect.

## Headline table (every number with its source)

All sources are relative to this directory. Each row's full precision is in `results/record_of_numbers.csv`, which gives source paths relative to the run root.

### Gates (R0)

| Gate | Result | Source |
|---|---|---|
| R0a | vendored `d2/src` sha256 = `gate_hashes.json`; `heldout_confirmation.json` sha256 = 4100e3cf…b3d6; MeSH vendor modules identical to d2/src | `results/gates.json` |
| R0b screen | IRR/SD 1.300 [1.164, 1.452], N 1,544, G 140 — exact | `results/gates.json` |
| R0b held-out | 1.187 [1.057, 1.335], N 972, G 74 — exact | `results/gates.json` |
| R0b MeSH (R2) | 1.233 [1.117, 1.361], N 2,171, G 160 — exact | `results/gates.json` |
| R0c | held-out EST_bin LPM coefficient 0.4761, p 0.1651; held-out z 2.9326 | `results/gates.json` |
| R0d | vendored pytest: 8 passed | `results/gates.json` |
| R0e: zero share (retained) | screen 0.444, held-out 0.444, MeSH 0.452 | `results/gates.json` |
| R0e: max Y | screen 290, held-out **808**, MeSH 87 | `results/gates.json` |

On R0e: the strategy's 'max 290' holds for the screen fold only.

### K1: which margin (co-primary FE concept + e + d; CRV1 by concept; t(G−1) CIs)

| Row | Screen | Held-out | MeSH | IVW (Q, I²) |
|---|---|---|---|---|
| K1a-LPM, pp/SD (primary) | 6.46 [3.42, 9.51] | 7.29 [2.97, 11.61] | 6.17 [3.87, 8.46] | **6.43 [4.76, 8.11]** (I² 0) |
| … relative to base rate P(Y≥1) | 0.127 (0.509) | 0.141 (0.517) | 0.116 (0.532) | |
| K1a FE-logit, OR/SD | 1.90 [1.35, 2.66] | 2.29 [1.28, 4.11] | 1.45 [1.26, 1.68] | 1.54 [1.36, 1.75] |
| K1a-loglink, ratio of P(Y≥1)/SD | 1.103 [1.040, 1.171] | 1.120 [1.036, 1.211] | 1.124 [1.075, 1.174] | 1.117 [1.082, 1.153] |
| K1b intensive, IRR/SD (conditional, descriptive) | 1.272 [1.121, 1.443] | 1.163 [1.008, 1.342] | 1.137 [1.026, 1.260] | **1.183 [1.104, 1.267]** (I² 0) |
| Extensive share b_ext/(b_ext+b_int) | 0.31 [0.14, 0.57] | 0.46 [0.20, 1.51] | 0.50 [0.33, 0.90] | 0.38 [0.21, 0.55] |
| MDE80, extensive pp/SD | 4.99 | 6.22 | 3.60 | 2.37 |
| MDE80, intensive IRR/SD | 1.125 | 1.171 | 1.080 | 1.050 |

- **Sources:** `results/k1_rows.csv`, `results/k1_decomposition.json`, and `results/k13_spec.json` (MDEs, simulated before the freeze).
- **Share CIs:** these come from a 1,000-draw concept-cluster bootstrap per fold, with 0 failed draws.
- **The held-out share is unstable** (bootstrap SE about 1.0) because the ratio's denominator is close to 0 in some draws. The IVW share is therefore dominated by screen and MeSH.
- **Decomposition gap:** b_total − (b_ext + b_int) per SD is −0.055 (screen), −0.073 (held-out) and −0.025 (MeSH). The two parts use different samples and weights, so the gap is not 0 by construction.

**Threshold ladder** (LPM, pp/SD; `results/k1_rows.csv`, test `K1d_ladder`; figure `figures/k1_ladder.png`):

| Threshold | Screen | Held-out | MeSH |
|---|---|---|---|
| Y ≥ 1 | 6.46 | 7.29 | 6.17 |
| Y ≥ 3 | 5.53 | 3.72 | 5.37 |
| Y ≥ 5 | 4.55 | 2.56 (CI includes 0) | 2.76 |
| EST_bin | 5.37 | 2.54 [−1.01, 6.09], p 0.158 | 4.89 |

This explains the earlier held-out EST_bin null. On held-out the effect is concentrated at the *start* of uptake (Y ≥ 1). The strict establishment cut-off (Y ≥ 3 in at least 3 of 5 years) is too far out along the distribution for the held-out G = 85.

**Side row, primary FE** (concept × e + d × e): held-out LPM 5.73 [−1.88, 13.34] with G 38, and K1b G 15. Both are labelled underpowered and are never used for a verdict.

### K3: field boundary (pooled screen + held-out; FE concept + fold×e + d)

| Row | Estimate [95% CI] | G (concepts) | Entries |
|---|---|---|---|
| Physics/Astro origin, IRR per pooled SD | 1.178 [0.926, 1.499] | 77 | 478 |
| CS origin | 1.216 [1.066, 1.386] | 53 | 838 |
| Other origin | 1.281 [1.167, 1.407] | 84 | 1,278 |
| Wald equality (2 df) | W 0.90; p (CRV1, F) **0.638**; χ² p 0.638; **p_perm 0.770** (2,000 label permutations across concepts) | 214 | 2,594 |
| Physics/Astro − rest contrast | ratio 0.942 [0.740, 1.199]; p 0.626; p_perm 0.705; **MDE80 0.72** | | |
| SECONDARY: host-field grouping | Physics/Astro 1.201, CS 1.284, other 1.226; Wald p 0.822 | | |
| MeSH reference (R2, not pooled) | 1.233 [1.117, 1.361] | 160 | |

Sources: `results/k3_rows.csv`, `results/k3_results.json`; figure `figures/k3_field_forest.png`.

**Reading:** the Physics/Astro CI includes 1, but the groups are not distinguishable (p 0.64). Under the frozen rule this is *not* a boundary. The design can only rule out a physics slope below about 0.72× the rest (the MDE80). A smaller difference is not excluded.

Correction to the plan's premise: Physics/Astro-origin concepts are the *largest* group by concept count (124 of 277 input concepts) but have the fewest entries.

### INFERENCE: size-correct p for the headline rows

| Row | CRV1 p | **Randomization-t p (headline)** ± MC SE | Freedman-Lane p | WCR Webb p (9,999) | Rademacher check (999) | CRV1 null rejection | Null z SD |
|---|---|---|---|---|---|---|---|
| Screen, co-primary count | 6e-6 | 0.0005 ± 0.0005 (floor) | 0.0005 | 0.0001 | 0.001 | 0.092 | 1.18 |
| Held-out, co-primary count | 0.0045 | **0.023 ± 0.003** | 0.025 | 0.012 | 0.011 (target 0.012 ✓) | 0.107 | 1.24 |
| MeSH, co-primary count | 5e-5 | 0.0015 ± 0.0009 | 0.001 | 0.0002 | 0.001 | 0.104 | 1.22 |
| IVW pooled z = 6.84 | <1e-10 | 0.0005 (floor) | 0.0005 | — | — | 0.106 (share \|z*\|>1.96) | 1.23 |
| K1a-LPM held-out | 0.0012 | 0.004 | 0.003 | 0.0002 | 0.001 | 0.065 | 1.06 |
| K1a-LPM IVW z = 7.53 | <1e-10 | 0.0005 (floor) | 0.0005 | — | — | 0.054 | 1.00 |

- **Sources:** `results/inference_rows.csv`, `results/inference_summary.json` and the draws in `results/inference_draws.csv`; figure `figures/inference_null_z.png`.
- **Floor p values:** a p of 0.0005 = 1/2001 means no null draw reached the observed |t|.
- **The PPML count rows over-reject under CRV1** (null z SD about 1.2, about 10% false rejections at a nominal 5%). The LPM rows are close to nominal size. This is why the randomization-t is the declared headline p.
- **Discrepancy with the earlier audit:** the held-out CRV1 null rejection here is 10.7% (z SD 1.24), against 17.5% (z SD 1.48) in the earlier 200-draw `audit_perm.json` of art_WZ8fbLn79nCq. The independent pyfixest audit here (500 fresh draws) gives 12.8% and z SD 1.23, which agrees with this run. The earlier figure is best read as small-sample Monte Carlo noise plus a heavy tail. The earlier permutation p (0.050 on 200 draws) sharpens to 0.023 on 2,000 draws.

### Independent re-derivation (`audit/audit_k.py`: pyfixest + pandas only, no vendored module)

| Check | Result | Pass |
|---|---|---|
| K1a-LPM coefficient per fold | \|diff\| ≤ 2e-15 (same N and G) | ✓ (< 1e-4) |
| K1a-LPM IVW | \|diff\| 5e-12 pp | ✓ |
| K3 Wald p | pyfixest 0.63835 vs 0.63835 (\|diff\| 3e-8) | ✓ |
| Held-out randomization-t p (500 draws, seed 777) | 0.020 vs 0.023, tolerance 2 MC SE = 0.014 | ✓ |

## Caveats (for the paper)

1. **Exploratory label.** All K verdicts are post-confirmation exploratory. The rules and MDEs were frozen before the K coefficients, but the data had been seen.
2. **Intensive selection.** K1b conditions on Y ≥ 1, so it measures 'larger uptake given that uptake started' and is descriptive. No Heckman correction was attempted, because there is no credible exclusion restriction.
3. **MeSH scope.** MeSH covers biomedicine → biomedicine entries only (the F6 widening). It is a separate row and never enters K3.
4. **Primary FE underpowered.** The within concept × year FE (held-out G 30–38) is a side row only. Identification is 'across a concept's entries', as for the headline.
5. **K3 reuses the screen fold**, where the physics null was first seen. It is the first *formal* test of that null, not a fresh one.
6. **FE-logit** is an unconditional FE logit (own IRLS with weighted within-transformation, concept + e + d FE). It may carry some incidental-parameter bias; it is a corroborating row only. Concepts dropped by the all-0/all-1/singleton pruning: screen 47, held-out 22, MeSH 28 (`results/k1_rows.csv`, note column).
7. **The randomization-t permutes A_cont within concept**, which also breaks the correlation between A_cont and the controls. Freedman-Lane is reported beside it and agrees everywhere.

## Layout

| Path | What it is |
|---|---|
| `eval.py` | Entry point; runs the stages in order (freeze → smoke → run → audit → report) |
| `k/k_lib.py` | Loaders and fold samples; cached-projection LPM with HDFE; FE-logit; PPML wrappers (vendored `ppml.fit`); Webb/Rademacher wild score bootstrap; randomization engines; IVW; cluster bootstrap |
| `k/k_freeze.py` | Gates R0a–R0e → `results/gates.json`; MDE simulations; `results/k13_spec.json` + `.sha256` |
| `k/k_run.py` | K1, K3 and INFERENCE (asserts the spec hash); `--synthetic` smoke mode → `results/smoke/` |
| `k/report.py` | Verdicts → `results/k13_summary.json`; figures; `results/record_of_numbers.csv`; `eval_out.json` |
| `audit/audit_k.py`, `audit/audit_k.json` | Independent pyfixest re-derivation |
| `audit/audit_placebo.py`, `audit/audit_placebo.json` | Raw-file re-derivation of the IVW rows and held-out p; placebo checks (null draws as pseudo-observations reject 4.95%; shuffled-A LPM IVW max \|z\| 2.44 vs observed 7.53) |
| `reproducibility.md` | Step-by-step reproduction |
| `d2/` | Byte-exact vendored D2 stack from art_WZ8fbLn79nCq (src, tests, lock file); never edited |
| `mesh/` | Vendored MeSH code from art_XGdzjWgi-a88 (src, vendor, `results/mesh_spec.json`) |
| `inputs/` | Byte-exact copies of the three frozen event tables (sha256 in `results/input_hashes.json`) |
| `results/k1_rows.csv`, `k1_decomposition.json`, `k1_bootstrap_draws.csv` | K1 |
| `results/k3_rows.csv`, `k3_results.json`, `k3_perm_draws.csv` | K3 |
| `results/inference_rows.csv`, `inference_summary.json`, `inference_draws.csv` | INFERENCE |
| `results/k13_summary.json` | All verdicts, with the numbers that triggered them and audit flags |
| `results/record_of_numbers.csv` | One row per number: label (POST-CONFIRMATION EXPLORATORY / GATE / DESCRIPTIVE), value, source |
| `results/smoke/` | Smoke run on a synthetic NB2 outcome, and the freeze dry run |
| `figures/` | `k1_margin_forest`, `k1_ladder`, `k3_field_forest`, `inference_null_z` (PNG and PDF, Okabe-Ito palette) |
| `eval_out.json` (+ `full_`/`mini_`/`preview_`) | exp_eval_sol_out: `metrics_agg` (65 metrics); datasets `k_rows` (138) and `events` (5,086) |
| `logs/` | Freeze log (UTC freeze time and hash), run logs |

## How to run

```bash
export AII_DEPS_ROOT=<run>/3_invention_loop   # only needed for the R0a gate (reads art_WZ8fbLn79nCq gate hashes)
uv venv .venv --python 3.12 && uv pip install --python .venv/bin/python -r d2/requirements.lock.txt
.venv/bin/python eval.py                        # freeze is skipped because the spec already exists
.venv/bin/python eval.py --stages run,audit,report   # re-run on the frozen spec
```

Runtime on 6 CPUs, 5 workers:

| Stage | Time |
|---|---|
| Freeze | about 2 min (15,600 MDE simulation fits) |
| K1 | 1.5 min (3,000 bootstrap draws) |
| K3 | 1.7 min (2,000 permutations) |
| Inference | 2 min (2,000 draws × 3 folds × 2 schemes, plus 9,999 Webb draws) |
| Audit | about 1 min |

Seeds: `SEED = 20261001`, offset per scheme (see the spec).

## Restoring removed files

`.aii/manifest.yaml` marks only these for deletion. Everything else stays on the run's volume.

- `.venv/` (regenerable): `uv venv .venv --python 3.12 && uv pip install --python .venv/bin/python -r d2/requirements.lock.txt`
- `d2/.pytest_cache/` (regenerable): `cd d2 && ../.venv/bin/python -m pytest -q`
- `*/__pycache__/` (regenerable): rebuilt automatically on the next `python eval.py` (or `cd d2 && ../.venv/bin/python -m pytest -q` for `d2/tests/__pycache__`).
