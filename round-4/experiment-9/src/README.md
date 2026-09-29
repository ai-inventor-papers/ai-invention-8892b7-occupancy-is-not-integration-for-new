# G4 — Does idea grafting replicate in biomedicine? (MeSH replication of the D2 host-entry test)

Iteration 4, experiment 9 of the AI Inventor run on emerging scientific concepts as evolving knowledge networks.

**Question.** When a new concept first enters a scientific subfield outside its origin (a *host entry*), is the entry
followed by more uptake from newcomers when the concept arrives with partners that are already native to the host
(**grafting**, measured by `A_cont`)? Or does it matter more that it arrives with its origin companions
(**toolkit / co-transfer**, `CT`)? Iteration 3 (exp_7) found grafting on the physics/CS-heavy main pool. Its
co-primary estimate was IRR 1.30 per SD of `A_cont` [1.16, 1.45], with 1.29 in the non-physics stratum and 0.95 in
physics. This artifact re-runs the same frozen test on **191 MeSH biomedical concepts** (art_HGiVAYhqO-6q), a
population never screened for D2.

## Result (one look, pre-registered rule)

**G4 verdict: REPLICATED.** Reading: GRAFTING in both the co-primary and the primary spec.

| row | spec | IRR per SD of A_cont [95% CI] | p (CRV1) | p (wild) | N | concepts |
|---|---|---|---|---|---|---|
| **R2 (decisive)** | concept + e + d FE | **1.233 [1.117, 1.361]** | 4.9e-05 (Holm 9.7e-05) | 0.001 | 2,171 | 160 |
| R1 | concept × e + d × e FE | 1.324 [1.098, 1.598] | 0.0037 (Holm 0.0073) | 0.001 | 1,004 | 122 |
| R3 | concept + d × e | 1.251 [1.133, 1.381] | 1.5e-05 | 0.002 | 1,852 | 158 |
| R4 | concept × 2-yr + d × e | 1.383 [1.215, 1.574] | 2.1e-06 | 0.002 | 1,320 | 138 |
| CT in R2 | co-transfer | 1.104 [0.999, 1.220] | 0.053 (Holm) | 0.06 | | |
| S3 placebo host | same partners, random covered host | 1.031 [0.963, 1.103] | 0.38 | 0.39 | 2,171 | 160 |

- **Same size as the main pool.** MeSH 1.233 vs main 1.300: dlog −0.053, z = −0.71, p = 0.48. The IVW-pooled
  estimate is **1.262 [1.173, 1.358]** with I² = 0. Against the non-physics stratum (1.29): z = −0.51, p = 0.61. The
  prediction "IRR/SD > 1 in biomedicine, consistent with 1.29" holds.
- **Power.** The design was powered before any outcome was computed: simulated MDE80 is 1.20 for R2, 1.40 for R1
  and 1.30 for G1.
- **Robustness.**
  - The nativeness permutation placebo gives p = 0.010 for R2 and p = 0.045 for R1 (200 draws).
  - A within-concept outcome shuffle gives p = 0.024 (the minimum possible with 40 draws).
  - pyfixest reproduces R2 to within 1e-4 on the coefficient and 1e-3 on the SE.
  - An independent plain-loop audit from the raw rows matches A_cont, CT and Y_strict for 20 events, and R2 b_A to
    6e-15.
  - A separate headline re-derivation (pyfixest, own pruning) reproduces the IRR/SD, CI, Holm p, z and IVW exactly. The
    same test rejects 0/20 shuffled-A placebos and 1/20 random-regressor placebos (`results/audit_headline.json`).
- **Sensitivity rows** (all IRR/SD, CIs excluding 1 unless noted):
  - Y_lenient 1.230; Y_all 1.230; EST_bin LPM coefficient positive (p < 1e-6).
  - Nativeness variants: exact profiles only 1.243; unprofiled tags counted as 0: 1.217; counted as 1: 1.722.
  - Concept subsets: rule_parity concepts 1.190; retrieval-complete concepts dropped 1.292; kw5 partner rule 1.239.
  - Single-paper entries 1.242; without topic controls 1.233; union c-paper set 1.162.
  - Host domain: Health Sciences 1.212; Life Sciences 1.220.
  - The only null row is the declared 0.50-coverage subset (S6: N 123, G 39, 1.007 [0.69, 1.48]). It is too small to
    be informative, and it is why the pre-declared F6 widening fired.
- **Pipeline vs population.** Harmonisation rows apply the MeSH data rules to the main screen: 0.3 tagging floor, no
  topic-score filter, no dup_group dedup, and the MeSH nativeness ranking and bg-fill rule. They move the main
  estimate only from 1.300 to between 1.289 and 1.299 (1.350 with exact profiles only). So the MeSH/main comparison
  is not a pipeline artefact.
- **Mechanism rows** (descriptive):
  - **G1**, multi-team entry, where the host has two author-disjoint papers within two years: 1.079 [0.956, 1.219],
    p = 0.22 (MDE80 1.30). Not detected.
  - **G2**: the effect is carried by both **NATIVE** partners (host share ≥ 0.30; 1.171 [1.078, 1.272]) and
    **ADJACENT** partners (0.05–0.30; 1.115 [1.027, 1.210]), each against FOREIGN partners.
- **Out-of-fold predictive check** (grouped by concept, descriptive): adding A_cont and CT lowers Poisson deviance
  by 0.146 [0.008, 0.306] per event. Spearman correlation rises from 0.221 to 0.286.

### Caveats a reader must see

1. **Only the widened design had enough concepts.** The declared design (kw5 partners and a PubMed share of at least
   0.50) had only 46 non-singleton concepts. The **pre-declared F6 widening** (kw3, then coverage 0.30) was applied
   from W1 counts before the freeze. The decisive sample is the widened one: 2,267 entries in 187 concepts,
   restricted to biomedical hosts (Medicine, Biochemistry/Genetics, Neuroscience, Immunology, Dentistry, …). The
   coverage rule removed 34% of partner-qualified entries, and every entry into a non-biomedical host is dropped
   (`results/entry_counts_by_host_field.csv`). G4 therefore speaks to **biomedicine → biomedicine** entries only.
2. **Entry years are measured with error.** 178 of 191 concepts have only their PubMed-indexed works retrieved. On
   the 13 concepts with complete retrieval, the PMID-only entry year equals the all-works entry year for 50% of
   entries into covered hosts (at the chosen 0.30 threshold) and 28% into uncovered hosts
   (`results/truncation_audit.json`). Dropping the complete-retrieval concepts (S9: 1.292) and keeping only
   rule-parity concepts (S8: 1.190) both leave the effect in place.
3. **CRV1 over-rejects in the null simulation.** At a true IRR/SD of 1.00, the rejection rate is 0.105 for CRV1 and
   0.10 for the wild bootstrap (n = 50) at α = .05. This matches exp_7's finding that CRV1 is mildly
   anti-conservative. Referring the observed R2 p to the 200 simulated null p values gives a calibrated p of 1/201,
   the minimum possible. This calibration is **post hoc**, not part of the frozen spec. The permutation placebo and
   the outcome shuffle, which were pre-declared, also reject.
4. **Nativeness.**
   - Tag-weighted profile coverage of the model sample is 0.833: 0.805 from exact OpenAlex profiles (dataset_5 reuse
     plus 2,509 new group_by calls) and the rest from background-sample shares. Those shares were admitted by a
     pre-declared check (r = 0.927 against exact shares; bg coverage 0.654), written and hashed before any paid call.
   - The exact-only row gives 1.243.
   - The fetch was limited by the key's remaining daily credits, not by the plan's 3,000-call cap.
5. **The MeSH population is not wholly unseen.** exp_4 used it for RQ1 concept-level volume. No host-level entry
   outcome had ever been computed on it, and exp_4's label files were not opened here.

## Pre-registration discipline

- **Correctness gates first.** Gate 1 (iteration-1 events 2,347 / 2,154 / 2,000, row-level) and gate 2 (exp_7
  co-primary b_A = 4.7391, N 1,544, G 140; primary 5.9526, N 452, G 77) both reproduce **exactly**
  (`results/gates.json`).
- **Frozen before outcomes.** All MeSH definitions, the F6 decision, the controls, the MDE table, the row list, the
  decision rules and the G4 verdict rule were frozen in `results/mesh_spec.json`. Its sha256
  `b7cdabf8144581ab7903ea29c3a8e9d03e047e45e7f343c0dec1cb4a05a47c91` was recorded at 2026-09-29T07:11:10Z
  (`logs/freeze_log.txt`). MeSH outcomes were first computed at 07:12:10Z (`logs/outcome_log.txt`). The outcome code
  refuses to run unless the spec hash and the feature-file hashes match.
- **Dry run on synthetic outcomes.** The full model stage ran on synthetic NB2 outcomes before the freeze. This
  caught one argument bug in the verdict function, fixed before freezing.
- **One post-freeze change:** forest-plot tick formatting in `src/report.py`, logged in `logs/freeze_log.txt`.
- **Deviations** D-M1…D-M13 are listed in `results/mesh_spec.json` and repeated in `results/deviations.md`.

## Layout

| path | what |
|---|---|
| `method.py` | stage runner (`--stage gates|load|coverage|events|nativeness|features|freeze|outcomes|models|report|h6`, `--mini`) |
| `src/common.py` | paths (env-overridable), logging, hashing, OpenAlex client with a credit ledger (the key is never written) |
| `src/gates.py` | gates 1–2 on the main screen and harmonisation rows h1–h6 |
| `src/load_mesh.py` | MeSH concepts and works in the exp_7 G structure; yearly co-word substrate |
| `src/coverage.py` | PubMed host-coverage rule (24 group_by calls) and truncation audit |
| `src/events_mesh.py` | host-entry events, G1 multi-team events, pre-declared F6 widening |
| `src/nativeness.py` | 6a bg-fallback admissibility check, 6b exact-profile reuse and capped fetch |
| `src/features_mesh.py` | W1 features (A_cont, CT, G2 bins, placebo host, controls, topic hydration), leakage test |
| `src/power_mesh.py` | MDE simulation on the MeSH W1 design; T3 synthetic recovery |
| `src/freeze.py` | synthetic dry run, power, `mesh_spec.json` freeze |
| `src/outcomes_mesh.py` | spec-hash guard and author-disjoint outcomes (entry, G1, union set) |
| `src/models_mesh.py` | PPML rows R1–R4 and S1–S18, wild bootstrap, Holm, placebo, crosscheck, comparison, verdict |
| `src/report.py` | `method_out.json`, figures F1–F6, `results/g4_summary.json` |
| `vendor/` | exp_7 modules copied unchanged (`vendor/SHA256SUMS`) |
| `tests/` | `test_mesh.py` (T1 unit tests) plus the vendored exp_7 tests, run unchanged via `conftest.py` |
| `audit_rederive.py` | independent plain-loop audit, written to `results/audit_rederive.json` |
| `audit_headline.py` | headline re-derivation (pyfixest with its own pruning) plus placebo-input tests, written to `results/audit_headline.json` |
| `method_out.json`, `full_/mini_/preview_method_out.json` | one example per MeSH entry event (exp_gen_sol_out schema) |
| `results/g4_summary.json` | **start here**: every headline number |
| `results/g4_models.json`, `g4_rows.csv`, `g4_verdict.json` | all model rows, decisions, placebo, comparison |
| `results/comparison_main_vs_mesh.csv` | MeSH vs main z test and IVW pooled estimate |
| `results/mesh_spec.json`, `.sha256` | frozen spec |
| `results/power_mesh.json`, `power_reps_mesh.csv` | MDE curve and T3 |
| `results/gates.json`, `harmonisation_rows.csv`, `results/gate/` | gate and harmonisation outputs (main screen, already seen) |
| `results/events_mesh*.{parquet,json}`, `entry_counts_by_host_field.csv` | MeSH events and counts |
| `results/features_mesh*.parquet`, `outcomes_mesh*.parquet` | W1 features and W2 outcomes |
| `results/host_coverage*.{json,csv}`, `truncation_audit*.{json,csv}` | coverage rule and audit |
| `results/nativeness/profiles_fetched.jsonl` | **2,509 exact OpenAlex subfield profiles fetched here (paid data)** |
| `results/nativeness_fallback_check.json`, `.sha256`; `nativeness_ledger_summary.json` | 6a check and fetch summary |
| `results/topic_hydration.jsonl` | live primary-topic scores for 3,996 entry and window papers (paid data) |
| `results/substrate/` | yearly legacy-concept co-word network of MeSH c-papers (`mesh_coword.parquet`, `node_year.parquet`) |
| `results/placebo_*`, `outcome_shuffle_*` | permutation placebo and outcome-shuffle draws |
| `results/dryrun_synthetic/` | pre-freeze dry run on synthetic outcomes |
| `figures/` | F1 forest, F2 binned A_cont, F3 placebo z, F4 MDE curve, F5 host fields, F6 G2 bars |
| `logs/openalex_credit_ledger.jsonl` | every OpenAlex call: 2,578 credits in total (1 probe, 24 coverage, 2,512 nativeness incl. 3 smoke re-fetches, 41 topic hydration); all HTTP 200 |
| `cache/coverage_groupby.json` | raw coverage group_by responses (paid, small; kept) |

## How to run

```bash
uv venv .venv --python=3.12 && uv pip install --python .venv/bin/python -r pyproject.toml
export OPENALEX_API_KEY=...        # only for coverage, nativeness fetch and topic hydration (cached afterwards)
.venv/bin/python -m pytest -q tests/                                          # 17 tests
.venv/bin/python method.py --mini                                             # 10-concept smoke run (no outcomes)
.venv/bin/python method.py                                                    # all stages in order
.venv/bin/python audit_rederive.py
.venv/bin/python audit_headline.py
```

The dependency artifacts are read from the run layout `<loop>/iter_{1,2,3}/gen_art/...`. Override them with
`AII_DEPS_ROOT`, `AII_MESH_DIR`, `AII_DATASET5_DIR`, `AII_DATASET1_DIR`, `AII_EXP7_DIR`, `AII_EXP3_DIR` or
`AII_BG_DIR`. The paid responses are cached in `results/nativeness/profiles_fetched.jsonl`,
`results/topic_hydration.jsonl` and `cache/coverage_groupby.json`, so a rerun costs no credits. `outcomes` refuses to
run if `results/mesh_spec.json` changed, and `freeze` refuses to run once outcomes exist.

## Restoring removed files

The manifest (`.aii/manifest.yaml`) deletes only regenerable bulk:

| removed path | restore with |
|---|---|
| `.venv/` | `uv venv .venv --python=3.12 && uv pip install --python .venv/bin/python -r pyproject.toml` |
| `results/cache/prepared.pkl` | `.venv/bin/python method.py --stage gates` (vendored `io_load.prepare()` over dataset_5; about 10 s, then the gates rerun) |
| `cache/mesh_prepared.pkl` | `.venv/bin/python method.py --stage load` |
| `**/__pycache__/`, `.pytest_cache/` | regenerated automatically by Python and pytest |

Everything else, including the paid OpenAlex responses and every result file, stays on the run's volume at the
paths above. No file here is 100 MB or larger except `results/cache/prepared.pkl` (156 MB, regenerable, not
published).
