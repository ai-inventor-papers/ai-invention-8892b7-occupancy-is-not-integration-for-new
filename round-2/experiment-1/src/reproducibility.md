# Reproducing the concept-cleaning experiment

This file describes what was **actually run** on 2026-09-28 to produce `results/`, `models/` and `method_out.json`.
It covers the classifier, the variant merger, the NIL-aware linker and the frozen test population. All paths are
relative to this folder.

## 1. Get the artifact

This folder is one directory of the project's public GitHub repository:

```bash
git clone <repository-url>
cd <repository>/<this-artifact-folder>        # the folder that contains method.py and this file
```

### Input artifacts

The pipeline reads three input artifacts. The repository publishes them as sibling folders. Each is found through one
environment variable:

| env var | artifact id | used files |
|---|---|---|
| `AII_DS1` | `art_94GEMUsgAmgK` (new science concepts; frozen frame) | `sample_frame_frozen.json` (+ `.sha256`) |
| `AII_DS3` | `art_HGiVAYhqO-6q` (MeSH held-out set) | `full_data_out.json` |
| `AII_DS4` | `art_QpM5SM6a7SH6` (labelled phrases, anchors) | `full_data_out/full_data_out_1..7.json`, `data_out/vocab/*.json.gz` |

Without these variables the code falls back to its original run layout (`../../../iter_1/gen_art/gen_art_dataset_{1,3,4}`).
Point them at the sibling folders of your clone, for example:

```bash
export AII_DS1=../<folder of art_94GEMUsgAmgK> AII_DS3=../<folder of art_HGiVAYhqO-6q> AII_DS4=../<folder of art_QpM5SM6a7SH6>
```

The small inputs actually used are already copied into `data/`. These are the frame, its sha256, the hydrated rows, the
pending list, the sense checks, D2/D3/D4/D5, the MeSH pairs and the codebook. `s0_load.py` rebuilds `data/*.json` from the
artifacts above. The frame hash must be `80e3f244235b120be3e1201fdd8fb275ace4ba549f9a8884b96d2ea51c9a0c44`; the run
aborts if it is not. The DS4 file `pool_outcomes_SEALED.json` is never opened (`open_guard` in `src/common.py`). No user
upload is used.

## 2. System, Python and libraries

- Ubuntu/Debian with `git` and `curl`, plus [`uv`](https://docs.astral.sh/uv/). No other system packages are needed.
- Python **3.12.14**.
- Exact library versions are pinned in `pyproject.toml` (the output of `uv pip freeze` from the run's `.venv`, 122
  packages). Key ones: `torch==2.14.0` (CUDA 13.0 build), `numpy==2.5.3`, `scikit-learn==1.9.1`,
  `sentence-transformers==5.7.0`, `adapters==1.3.0`, `spacy==3.8.16` with `en_core_web_sm` 3.8.0, `pyahocorasick`,
  `rapidfuzz`, `wordfreq==3.1.1`.

```bash
uv venv .venv --python=3.12
uv pip install --python .venv/bin/python -r pyproject.toml      # includes the en_core_web_sm wheel URL
```

## 3. Downloads, keys and environment

- **Hugging Face (downloaded automatically on first use):**
  - dataset `librarian-bots/arxiv-metadata-snapshot` (parquet conversion; only id/title/versions/categories columns are
    read; 1,484,085 titles 1991-2018);
  - models `sentence-transformers/all-MiniLM-L6-v2`, `allenai/specter2_base` + adapter `allenai/specter2`, and
    `cambridgeltl/SapBERT-from-PubMedBERT-fulltext` (calibration comparison only).
  - `HF_TOKEN` is optional.
- **OpenRouter** (step `s6` only): `OPENROUTER_BASE_URL`, `OPENROUTER_API_KEY`. Models:
  - `google/gemini-3.1-flash-lite` (sense proxy);
  - `google/gemini-2.5-flash-lite` (frame labels, link audit);
  - `anthropic/claude-haiku-4.5` (adjudication).
  - All calls use temperature 0. Every response is cached in `cache/llm/` and logged in `logs/llm_spend.jsonl`; the
    total was **$0.0531**. The hard cap is $0.30 (`HARD_CAP_USD` in `src/s6_llm_audit.py`). With the cache present a
    rerun costs nothing.
- **Wikidata** `wbsearchentities` (no key; ≤ 1 req/s; responses cached in `cache/wikidata/`). The API throttled this
  run (HTTP 429): 166 of 426 phrases have a search, and the F7 fallback stopped live calls.
- **No OpenAlex calls.**

## 4. Commands actually run (in order)

Hardware: 1× NVIDIA RTX A4500 (20 GB VRAM), a 12-CPU container quota (AMD EPYC 7352) and 57 GB RAM.
Global seed `SEED = 20261001` (`src/common.py`). Every bootstrap uses 2,000 reps.

```bash
.venv/bin/python src/s0_load.py            # ~20 s   integrity + extraction -> data/, cache/d1_corpus.parquet, results/t0_counts.json
.venv/bin/python src/s1a_fetch_arxiv.py    # ~60 s   arXiv titles <= 2018 -> cache/arxiv_titles_le2018.parquet
.venv/bin/python src/s1_corpus.py --limit-arxiv 100000   # T5 timing run (~5 min; output overwritten by the next line)
.venv/bin/python src/s1_corpus.py          # ~11 min termhood (Aho-Corasick, 11 workers) -> cache/termhood.pkl
.venv/bin/python src/t1_reused_code.py     # T1 check -> results/t1_reused_code.json
.venv/bin/python src/s2_features.py        # ~4 min  lexical + MiniLM/SPECTER2 embeddings (GPU fp16) -> cache/lexical.parquet, cache/emb/
.venv/bin/python src/s3_classifier.py      # ~43 min classifier grid, ablations, HGB, baselines, anchors -> models/, results/classifier_results.json
.venv/bin/python src/s4_merger.py          # ~20 min (run in parallel with s3) -> models/merger_*, results/merger_results.json
.venv/bin/python src/s4b_merger_choice.py  # ~30 s   F5 admissibility -> models/merger_choice.json
.venv/bin/python src/s5_link_calib.py      # ~3 min  NIL-aware calibration (GPU) -> models/link_thresholds.json, results/link_calibration.json
.venv/bin/python src/s6_llm_audit.py --probe   # T6 cost probe (5 items per model)
.venv/bin/python src/s7a_predict.py        # ~15 s   frame predictions + sha256, frozen BEFORE any frame label
.venv/bin/python src/s6_llm_audit.py       # ~20 s   sense proxy, model-A frame labels, haiku adjudication
.venv/bin/python src/s7b_merge_link.py     # ~6 min  merging, acronyms, linking, Wikidata -> results/frame_merge_link.json
.venv/bin/python src/s6_llm_audit.py --links   # link/merge audit -> results/link_audit.json
git init && git add ... && git commit      # code commit 57d50c1, recorded in the frozen population
.venv/bin/python src/s8_freeze.py          # frozen population -> results/test_population.json + .sha256 (run twice: same hash)
.venv/bin/python src/s9_report.py          # method_out.json, results/summary.json, *.csv
.venv/bin/python method.py --mini          # T2 mini pipeline (LLM stubbed) -> mini_run/
.venv/bin/python src/t3_leakage_checks.py  # T3/T7 -> results/t3_t7_checks.json
.venv/bin/python src/audit_rederive.py     # independent re-derivation + placebo checks -> results/audit_rederive.json
```

`.venv/bin/python method.py` runs the same sequence, from s0 to t3, in one command.

### Reruns during the session

Several steps were rerun after bug fixes. None of the fixes changed a model or a threshold after the test sets were
opened, except where stated below.

- `s4_merger`: first crash in a bootstrap helper; the rerun produced the reported numbers.
- `s5_link_calib`: crash on a non-idempotent normaliser key; fixed and rerun.
- `s6_llm_audit`: an asyncio semaphore was bound to the wrong event loop. The rerun used the cache for completed calls.
- `s7b_merge_link` ran three times:
  1. stopped during Wikidata throttling; the F7 fallback was then implemented;
  2. used the D3-only merger chosen by the F5 rule, which built topical mega-clusters (up to 70 phrases);
  3. used the merger selected by `s4b_merger_choice.py`, which applies the plan's two-subset precision rule to F5 using
     train pairs only. This is the reported run.

## 5. Expected outputs and numbers

| output | number(s) | where used |
|---|---|---|
| `results/test_population.sha256` | `6a887fb44d3a72951abbc647cb08a5be39081601e0e2647922376dcd40075505` | frozen population for iteration 3 (H1/H2, RQ1 re-cut) |
| `results/test_population.json` lists | MAIN 156 (all hydrated), STRICT 147, REFERENCE_ACCEPTED 42, SENSITIVITY 426 | data and grounding section: the analysed concept set |
| `results/classifier_results.json` | D2 test F1 0.818 [0.772, 0.859], AUC 0.888. Majority F1 0.715; C-value 0.716; LLM-B 0.773; LLM-A 0.901 (circular) | grounding validation table |
| same, `human_anchors` | E1 F1 0.674 (LLM A 0.776), E2 F1 0.706 [0.690, 0.720], AUC 0.82 | human-anchored validity |
| `results/merger_results.json` | D3 test F1 0.357, AUC 0.827; heldout_mesh F1 0.222, AUC 0.814; B-cubed F1 0.780 | variant merging |
| `results/link_calibration.json` | MiniLM τ = 0.95 at link precision ≥ 0.90 for NIL prior 0.9; in-KB recall 0.404; NIL false-link 0.004 | linking |
| `results/summary.json` → `frame_application` | 388 of 426 accepted; covariate-shift AUC termhood 0.996; Jaccard to −termhood 0.93; UNLINKED 312 of 366 main; Fisher p = 0.025 (rejection × sense_check_fail) | frame application and limitations |
| `results/audit_rederive.json` | the same numbers, re-derived independently, plus placebo checks | audit |

Small differences in the last digit of bootstrap CIs can come from BLAS thread nondeterminism in the logistic-regression
fits. Point estimates and the population hash are deterministic on identical inputs, code and hardware.
