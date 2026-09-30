# Concept-cleaning models for the emerging-concept frame (classifier, variant merger, NIL-aware linker)

This repository trains three models and applies them to the frozen frame of 426 emerging-concept candidates
(366 main + 60 reference; 206 hydrated + 220 pending hydration). It then freezes and hashes the accepted **test
population** that iteration 3 uses for H1/H2 and the RQ1 re-cut:

1. a **concept / not-concept classifier** (automatic term extraction as binary classification over candidate phrases);
2. a **pairwise variant merger** (SAME / DIFFERENT for surface variants, acronyms and synonyms);
3. a **NIL-aware embedding linker** to OpenAlex keywords, OpenAlex legacy concepts (with Wikidata ids), MeSH and Wikidata.
   Concepts with no suitable identifier stay in every output as first-class nodes (`node_id = concept_id`).

Every model runs side by side with its baselines in the same pipeline, and results carry 2,000-rep bootstrap 95% CIs.
No OpenAlex calls were made. LLM spend was **$0.053** (cap $0.30); Wikidata got 33 live calls before throttling.

> **Label status.** The D2 targets are **LLM-adjudicated SILVER labels** (gemini-2.5-flash-lite + gpt-4.1-nano, with
> claude-haiku-4.5 adjudication, from the DS4 dependency). The only **human-labelled** numbers here are the SemEval-2017
> Task 10 / SciERC anchors. They measure a related but different construct: annotated keyphrase or entity spans.

## Headline results

### Frozen test population (`results/test_population.json`, sha256 in `results/test_population.sha256`)

sha256 `6a887fb44d3a72951abbc647cb08a5be39081601e0e2647922376dcd40075505`. Two runs on the same inputs and code
commit give the same hash; the wall-clock time is kept in a separate sidecar file. The file records the code commit that
produced it (`57d50c1`). Later commits only add the mini-run plumbing, the entry point, the T3 checks and the README.

| list | rule | n | hydrated now |
|---|---|---|---|
| MAIN | main arm, `p_concept >= t_F1` (0.507), sense_pass (sense >= 0.70), canonical at `p_merge` | **156** | 156 |
| STRICT | main arm, `p_concept >= t_P90` (0.647), sense_pass, canonical at `p_merge_strict` | 147 | 147 |
| REFERENCE_ACCEPTED | reference arm, accepted_primary, canonical | 42 | 14 |
| SENSITIVITY | full frame, no filters | 426 | 206 |

- MAIN is at or above iteration 3's pre-declared 150-concept rule (156), but only just.
- All MAIN concepts are hydrated now. Pending concepts have `sense_status = missing` because the pre-declared F9 rule
  fired (see below). They enter MAIN only after hydration, through the frozen replacement rule written into the file.
- MAIN origin groups: Physics and Astronomy 69, Computer Science 33, other 54. By fold × F-band:
  screen 2005-07 21 / 2008-11 45 / 2012-16 36; heldout_concept 2005-07 11 / 2008-11 17 / 2012-16 26.

### 1. Concept classifier (D2 test, n = 300, silver labels; opened once after tuning and thresholds were frozen)

PRIMARY (pre-registered) model: L2 logistic regression on lexical + termhood + PCA64(MiniLM) + PCA64(SPECTER2) features.
It was tuned by 5-fold StratifiedGroupKFold on D2-train (groups = variant clusters); the chosen setting is C = 0.01.
There is 0 train/test key overlap.

| model | precision | recall | F1 [95% CI] | AUC | ΔF1 primary − model [95% CI] |
|---|---|---|---|---|---|
| **PRIMARY LR (t_F1)** | 0.759 | 0.886 | **0.818 [0.772, 0.859]** | 0.888 | – |
| PRIMARY LR (t_P90, strict) | 0.841 | 0.760 | 0.799 | 0.888 | – |
| HGB (same features) | 0.722 | 0.934 | 0.815 | 0.887 | +0.003 [−0.025, 0.031] |
| − termhood | 0.748 | 0.922 | 0.826 | 0.881 | −0.008 [−0.028, 0.010] |
| − embeddings | 0.702 | 0.862 | 0.774 | 0.823 | +0.043 [0.006, 0.079] |
| lexical only | 0.676 | 0.874 | 0.762 | 0.775 | +0.055 [0.013, 0.096] |
| MiniLM only | 0.677 | 0.916 | 0.779 | 0.834 | +0.039 [0.004, 0.075] |
| SPECTER2 only | 0.713 | 0.862 | 0.780 | 0.828 | +0.037 [−0.003, 0.079] |
| + context embedding (secondary) | 0.759 | 0.904 | 0.825 | 0.905 | −0.007 [−0.027, 0.010] |
| trained on D2 + D4a train (secondary) | 0.705 | 0.928 | 0.801 | 0.851 | see `classifier_results.json` |
| baseline: majority class | 0.557 | 1.000 | 0.715 | 0.500 | +0.102 [0.059, 0.143] |
| baseline: C-value ≥ t | 0.561 | 0.988 | 0.716 | 0.493 | +0.102 [0.058, 0.143] |
| baseline: LLM label B alone | 0.630 | 1.000 | 0.773 | – | +0.045 [0.003, 0.083] |
| baseline: LLM label A alone* | 0.876 | 0.928 | 0.901 | – | −0.083 [−0.128, −0.041] |

\*A and B helped create the silver labels (consensus, or haiku adjudication of A≠B), so these two baselines are
circular and optimistic. A wins against labels it co-produced.

- Other test metrics: Brier score and a reliability curve (`results/fig_reliability.png`).
- 3-class secondary model (CONCEPT / NOT / GENERIC): macro-F1 0.61, with TOO_GENERIC F1 0.31. The plan calls this
  "4-class"; VARIANT_OF has 2 train items and 0 test items, so only 3 classes exist.
- Per macro-domain F1: life 0.91, physical 0.83, computing/engineering 0.81, health 0.79, social 0.65.

**Human anchors (the only human-labelled numbers):**

| set | precision | recall | F1 [95% CI] | κ / AUC |
|---|---|---|---|---|
| E1: DS4's 300 anchor rows, PRIMARY | 0.758 | 0.607 | 0.674 [0.608, 0.738] | κ 0.41, AUC 0.84 |
| E1, same rows, LLM A (DS4) | 0.792 | 0.760 | 0.776 | κ 0.56 |
| E1, same rows, LLM B | 0.629 | 0.940 | 0.754 | κ 0.39 |
| E2: all SemEval/SciERC test rows (2,522 pos), negatives subsampled to 0.557 positive share, 20 seeds × bootstrap | 0.813 | 0.624 | 0.706 [0.690, 0.720] | AUC 0.82 |
| E2, 1–6 tokens | 0.811 | 0.613 | 0.699 [0.683, 0.714] | AUC 0.82 |
| E2 SciERC / SemEval-2017 | 0.92 / 0.76 | 0.61 / 0.64 | 0.733 / 0.695 | AUC 0.91 / 0.78 |

On E1 the classifier trails LLM A on F1 by −0.10 [−0.16, −0.04] but beats it on AUC by +0.06 [0.01, 0.10].

### 2. Variant merger

PRIMARY: L2 LR on 14 pair features. Training used D3 train + MeSH `train_eligible`/`working_list`: 21,338 pairs, with D3
carrying 30% of the weight. A leakage guard dropped 1,021 MeSH pairs that share a string with heldout_mesh and 354 that
share a descriptor; afterwards 0 descriptors overlap. `p_merge` = 0.855 is the max of the precision-0.90 thresholds on
the D3-OOF subset (0.563) and the MeSH-OOF subset (0.855). `p_merge_strict` = 0.925.

| test set | model | P | R | F1 [95% CI] | AUC |
|---|---|---|---|---|---|
| D3 test (115) | PRIMARY LR | 0.938 | 0.221 | 0.357 [0.222, 0.489] | 0.827 |
| | HGB | 0.944 | 0.250 | 0.395 | 0.869 |
| | LR D3-only | 0.852 | 0.765 | 0.806 | 0.866 |
| | cosine MiniLM ≥ t | 0.636 | 0.721 | 0.676 | 0.632 |
| | token_set ≥ 85 (partly circular on D3) | 0.500 | 0.456 | 0.477 | 0.379 |
| | normalised-equal | 0 | 0 | 0 | 0.5 |
| heldout_mesh (769) | PRIMARY LR | 0.846 | 0.128 | 0.222 [0.160, 0.283] | 0.814 |
| | HGB | 0.887 | 0.213 | 0.344 | 0.834 |
| | LR D3-only | 0.444 | 0.783 | 0.567 | 0.707 |
| | cosine MiniLM ≥ t | 0.488 | 0.891 | 0.631 | 0.779 |

- **Cluster test** (902 heldout_mesh terms, 566 descriptors, average linkage): B-cubed P/R/F1 = 0.984 / 0.646 / 0.780 at
  `p_merge`, against normalised-equality 1.000 / 0.627 / 0.771 and MiniLM cosine 0.485 / 0.861 / 0.620.
- **Reading.** The merger is a high-precision, low-recall tool. The MeSH hard negatives (siblings, narrower concepts)
  force `p_merge` up, and recall collapses. The plan's sanity expectation (MeSH OOF AUC > 0.9) is **not met**: the OOF
  AUC is 0.75.
- The F5 fallback (D3-only model) is the best on D3 test, but it is inadmissible under the plan's own threshold rule
  (`src/s4b_merger_choice.py`). At its D3 threshold its precision on MeSH train pairs is 0.45. When it was applied to the
  frame before this check, it produced topical mega-clusters of up to 70 phrases. The frame therefore uses the primary merger.

### 3. NIL-aware linker (MeSH calibration, 3,000 queries; heldout_mesh and H-strings excluded)

- Query types: (a) in-KB, with the query's own string removed from the index; (b) NIL, with all strings of the query's
  descriptor removed.
- Precision at NIL prior π: `precision_π = (1−π)TP / ((1−π)(TP+wrong) + π·FL)`.

| encoder | τ at precision_0.9 ≥ 0.90 (merger-gated) | in-KB recall at τ | NIL false-link rate | top-1 in-KB accuracy (no threshold) |
|---|---|---|---|---|
| **MiniLM (chosen)** | **0.95** | **0.404** | 0.004 | 0.745 |
| SPECTER2 | never reached | – | – | 0.710 |
| SapBERT (reported only) | 0.95 | 0.359 | 0.004 | 0.785 |

- No encoder reaches the target without the merger gate.
- Stage-1 exact-string false links on NIL queries occur at a rate of 0.0023; these are ambiguous MeSH entry terms.
- Curves are in `results/fig_link_calibration.png`. `tau_broader` = 0.90.
- T4 sanity checks pass:
  - "follicular dendritic cell" links to *Dendritic Cells, Follicular*;
  - a nonsense string returns NIL;
  - MiniLM cos(massive mimo, massive multiple-input multiple-output) = 0.44 > cos(massive mimo, massive star) = 0.39.

### 4. Application to the frame (426 concepts)

- **Classifier.** It accepts 388 of 426 concepts (346 of 366 main); STRICT accepts 362. Predictions and their sha256 were
  written to `results/frame_predictions_prelabel.json` **before** any frame LLM label was requested.
- **Covariate-shift diagnostic** (adversarial AUC, D2-train vs frame): termhood 0.996, lexical 0.897, embeddings 0.930.
  - The pre-declared rule fired because termhood AUC > 0.90.
  - Jaccard(primary accept set, −termhood accept set) = 0.93, which is ≥ 0.80. The primary flag therefore stays and no
    sensitivity pair is required. Both columns are in the population file.
  - Jaccard with uncensored termhood = 0.95.
- **In-domain silver audit.**
  - Model A labelled all 426 phrases CONCEPT for 401 of them. On an LLM-prescreened frame A is lenient.
  - Classifier vs A: κ 0.27, with 43 disagreements, all adjudicated by haiku. The adjudicator sided with the classifier 10 times.
  - Against the adjudicated silver labels the classifier gets P 0.969, R 0.947, F1 0.958 [0.943, 0.971], κ 0.47.
    This number is optimistic by construction: items where the classifier and A agree cannot count against it.
    It is also nearly uninformative: 93% of the silver labels are CONCEPT, and the same predictions scored against
    permuted labels still reach F1 0.922 (`results/audit_rederive.json`). Read κ 0.47 instead.
- **Rejection vs sense-check failure** (184 hydrated main concepts): rejected concepts are enriched for DS1
  `sense_check_fail`. 4 of 11 rejected concepts are flagged, against 17 of 173 accepted (OR 5.2, Fisher p = 0.025).
- **Named fragments:**
  - "multi label image": p 0.38, rejected;
  - "modulo theory": p 0.67, accepted, and A says CONCEPT;
  - "detector in pp collision": p 0.58, accepted, while A says NOT_CONCEPT. This is a known false accept.
  - Nothing was tuned on these phrases.
  - Every rejected main phrase is listed in `results/rejected_main_phrases.csv` with its p, top-5 reasons and A label.
- **Sense proxy.** Year-F arXiv titles with the DS1 `SENSE_SYS` prompt verbatim cover only 205 of 426 concepts (≥ 3 titles).
  On the 95 concepts that overlap the 183 OpenAlex-based values, the proxy **never** flags a failure (κ = 0.0, Spearman 0.11).
  The pre-declared **F9** rule therefore fired: the proxy is kept only as a column, and pending concepts get
  `sense_status = missing`. arXiv titles come from one community and cannot reveal cross-field polysemy.
- **Merging.** Two 2-member clusters at `p_merge` ("massive mimo uplink" ≈ "uplink massive mimo"; "superluminal neutrino"
  ≈ plural). The LLM audit judged both SAME. Plural and hyphen variants had already been merged by the frame's normaliser.
- **Linking.** Main arm: LINKED_EXACT 39, BROADER_ONLY 15, UNLINKED 312. Reference arm: 34 / 1 / 25.
  - All exact links are stage-1 string matches or Wikidata label/alias matches. At τ = 0.95 no stage-2 `exact_embed`
    link was accepted.
  - LLM audit of the 38 broader links: 35 are hierarchical or identical, 3 are DIFFERENT (e.g. relative locality →
    Locality). The judge model inverted the BROADER/NARROWER label direction, so both labels are read as "hierarchical".
  - D5 pool (1,000 phrases): LINKED_EXACT 18, BROADER_ONLY 52, UNLINKED 930. Iteration 1 counted 929 UNLINKED by exact match.
- **Acronyms.** 67,727 Schwartz-Hearst pairs from D1 abstracts and D4b sentences. 28 frame concepts have short forms,
  each with a collision risk. All carry `flag_for_later_retrieval = true`; they are not used now.

## Tests (testing plan T0-T7)

| test | result |
|---|---|
| T0 smoke (`results/t0_counts.json`) | D2 train 1,200 / test 300, D3 502, D4a 23,520, MeSH pairs 23,097 (769 / 1,216 / 21,112), frame 426 = 206 hydrated + 220 pending, SENSE_OA 183; frame sha256 verified |
| T1 reused code (`results/t1_reused_code.json`) | vendored Schwartz-Hearst: pair precision 0.9522 (DS4: 0.9522); `normalise('Weyl semimetals') == normalise('weyl-semimetal')`; only the guard mentions the sealed file |
| T2 mini pipeline (`results/t2_mini_pipeline.json`) | `method.py --mini` runs every step with exit 0 and LLM calls stubbed; the test-population sha256 is identical across two runs; mini `method_out.json` passes the schema |
| T3 leakage (`results/t3_t7_checks.json`) | 0 D2 train/test key overlap; 0 heldout_mesh descriptors in merger training; prelabel predictions older than labels (mtime + sha recorded in the audit); all threshold files older than the apply outputs |
| T4 sanity | CV F1 of primary 0.868 vs majority 0.715; merger OOF AUC on MeSH **0.75 (expected > 0.9: not met)**; FDC → *Dendritic Cells, Follicular*; nonsense string → NIL; MIMO cosine ordering holds |
| T5 scaling | encoders: 10k strings in 3.7 s (MiniLM) and 1.0 s (SPECTER2), so the whole 279,522-string set took < 1 min each on the GPU; Aho-Corasick timed on 100k arXiv titles (57 s) before the full 1.48M (465 s) |
| T6 LLM probe | 5-item batch per model: A $0.00023, haiku $0.00314, gemini-3.1-flash-lite $0.00080; projected about $0.20; actual total **$0.053** |
| T7 final | lists are subsets of the frame; every UNLINKED concept has `node_id`; counts match `method_out.json`; the internal population schema passes; aii-json exp_gen_sol_out passes; no file >= 100 MB outside `cache/` |

## Independent re-derivation audit (`src/audit_rederive.py` -> `results/audit_rederive.json`)

The script reads only raw per-item files (`d2_test_predictions.json`, `merger_test_predictions.json`, the per-concept
records, the LLM label files, the calibration curve, the spend ledger). It recomputes through separate code: hand-written
F1, rank-based AUC, its own bootstrap RNG and its own population rules.

**Re-derived exactly:**
- classifier F1 0.818 and AUC 0.888;
- ΔF1 vs majority [+0.062, +0.146] and vs LLM A [−0.127, −0.039];
- merger F1 0.357 / 0.222 and AUC 0.827 / 0.814;
- MAIN 156 (set-identical), STRICT 147, REFERENCE_ACCEPTED 42, 388 accepted, 312 main UNLINKED, and the population sha256;
- Fisher p 0.025;
- linker τ 0.95 and recall 0.404;
- LLM spend $0.0531.

**Placebos behave as they should:**
- permuted D2 labels give AUC 0.53 and a negative ΔF1 vs majority;
- permuted sense flags give p < 0.05 in 2.4% of 1,000 permutations;
- the frame silver F1 does *not* separate from its placebo (0.958 vs 0.922), which is why it is flagged above.

**Not independently re-derived:** the human-anchor numbers (E1/E2), because no per-row anchor predictions are saved,
and the B-cubed cluster scores.

## Deviations from the plan (and why)

1. **Outcome-blind termhood.** Frame phrases are counted only in documents up to F+2 (main arm) or 2004 (reference arm).
   The plan counted arXiv titles up to 2018, which for early-F concepts would let post-window uptake decide who enters the
   test population. As a consequence, 63 frame phrases have no occurrence inside their window (`th_missing`), because
   OpenAlex F often precedes arXiv uptake. The flag has a large negative weight (see `reason_top5`). The pre-declared
   −termhood and an extra uncensored-termhood sensitivity column bound its effect (Jaccard 0.93 / 0.95).
2. **Extension-token POS** comes from a token-level POS lexicon (spaCy on a fixed random sample of 250k corpus units)
   rather than per-occurrence tagging. C-value nesting counts only content-word extensions (not 'and', 'of').
3. **Merger choice (F5).** The plan's F5 scenario says "fails on D3 while doing well on MeSH"; here the merger failed on
   both. The fixed F5 choice rule (higher D3-OOF F1) was applied, restricted to thresholds that satisfy the plan's own
   two-subset precision rule (`src/s4b_merger_choice.py`, which uses train pairs only). That restriction selects the
   pre-registered primary merger. The D3-only model's earlier frame application (topical mega-clusters) is recorded above.
   The linker gate always uses the primary merger with `p_merge`, as calibrated.
4. **Wikidata (F7).** wbsearchentities returned HTTP 429 repeatedly. After three throttling events, live calls stopped:
   166 of 426 frame phrases have a Wikidata search (cached in `cache/wikidata/`). The rest rely on legacy-concept
   Wikidata ids.
5. **Sense proxy for the reference arm** (which has no F) uses the 2000–2004 titles. The proxy is informational only (F9).
6. The link audit judge (gemini-2.5-flash-lite) confused the BROADER/NARROWER direction; see section 4.
7. SPECTER2 never reached link precision 0.90, so MiniLM is the linker encoder. This follows the plan's rule (tie → MiniLM).

## Layout

| path | what |
|---|---|
| `method.py` | entry point; runs all steps in order (`--mini` = T2 mini pipeline into `mini_run/`) |
| `src/common.py` | paths, sealed-file guard (`open_guard`), loaders, matching normaliser |
| `src/vendor/` | DS4 `textnorm.py`, `linking.py`, `llm.py`, copied unchanged (normalise, Schwartz-Hearst, `_mesh_variants`, budget-guarded LLM client) |
| `src/s0_load.py` … `src/s9_report.py` | pipeline steps (see the `method.py` docstring) |
| `src/featlib.py`, `clfdata.py`, `mergelib.py`, `linklib.py`, `encoders.py` | feature code shared by training and application |
| `src/audit_rederive.py` | independent re-derivation of headline numbers + placebo checks |
| `reproducibility.md` | exact commands, versions, hardware, runtimes and expected numbers |
| `full_/mini_/preview_method_out.json` | aii-json variants of `method_out.json` |
| `src/t1_reused_code.py` | T1: vendored Schwartz-Hearst reproduces DS4 pair precision 0.9522 exactly; guard check |
| `data/` | small inputs copied from the dependencies (frame + sha256, hydrated rows, pending list, sense checks, D2/D3/D4/D5, MeSH pairs, codebook) |
| `models/` | `concept_lr.joblib` (+ `thresholds.json`), `concept_lr_notermhood.joblib`, `concept_best_comparison.joblib`, `merger_lr*.joblib` (+ `merger_thresholds.json`, `merger_choice.json`), `link_thresholds.json` |
| `results/test_population.json` + `.sha256` | **the frozen test population** (per-concept records, lists, rules, thresholds, model hashes, code commit) |
| `results/classifier_results.json`, `merger_results.json`, `link_calibration.json` | full evaluation outputs, with CIs and grids |
| `results/frame_predictions_prelabel.json` + `.sha256` | classifier outputs on the frame, frozen before LLM labels |
| `results/frame_llm_audit.json`, `link_audit.json`, `frame_merge_link.json` | LLM audits, merge clusters, links, acronyms |
| `results/summary.json`, `*.csv`, `fig_*.png` | report tables and figures |
| `method_out.json` | exp_gen_sol_out output: frame concepts, D2 test predictions and merger test pairs as examples; `metadata.summary` holds every number above |
| `logs/` | per-step logs, `llm_spend.jsonl` (usage.cost per call) |
| `mini_run/` | T2 mini-pipeline outputs (`results/`, `models/`, `method_out.json`; `work/` is regenerable) |
| `cache/llm/`, `cache/wikidata/` | paid LLM responses and Wikidata responses (kept; a rerun costs nothing) |

Everything stays on the run's volume. The published repository skips files of 100 MB or more (`cache/emb/*.npy`, `.venv/`).

## How to run

```bash
uv venv .venv --python=3.12 && uv pip install --python .venv/bin/python -r pyproject.toml
.venv/bin/python -m spacy download en_core_web_sm
export OPENROUTER_BASE_URL=... OPENROUTER_API_KEY=...        # only s6 needs it; responses are cached in cache/llm/
.venv/bin/python method.py                                  # full run: ~70 min on 12 CPUs + 1 GPU (classifier grid ~45 min)
.venv/bin/python method.py --mini                           # T2 mini pipeline, no LLM spend, outputs in mini_run/
```

The dependency workspaces are found relative to this directory (`../../../iter_1/gen_art/gen_art_dataset_{1,3,4}`).
Override the location with `AII_DEPS_ROOT`. The DS4 file `pool_outcomes_SEALED.json` is never opened; `open_guard`
raises if any path contains "SEALED".

## Restoring removed files

These paths are marked `delete` in `.aii/manifest.yaml`:

| path | restore with |
|---|---|
| `.venv/` | `uv venv .venv --python=3.12 && uv pip install --python .venv/bin/python -r pyproject.toml && .venv/bin/python -m spacy download en_core_web_sm` |
| `cache/arxiv_titles_le2018.parquet` | `.venv/bin/python src/s1a_fetch_arxiv.py` (HF `librarian-bots/arxiv-metadata-snapshot`, parquet conversion; ~1 min) |
| `cache/d1_corpus.parquet` | `.venv/bin/python src/s0_load.py` |
| `cache/emb/` | `.venv/bin/python src/s2_features.py` (~4 min on GPU; models `sentence-transformers/all-MiniLM-L6-v2`, `allenai/specter2_base` + adapter `allenai/specter2`) |
| `mini_run/work/` | `.venv/bin/python method.py --mini` |
| `src/__pycache__/`, `src/vendor/__pycache__/` | recreated automatically by Python on import |

The HF model weights live in the run's shared HF cache, not in this directory.
