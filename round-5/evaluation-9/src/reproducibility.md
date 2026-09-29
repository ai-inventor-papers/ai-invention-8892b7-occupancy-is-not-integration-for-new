# Reproducing the figure set

This artifact re-estimates nothing. It reads result files that other artifacts produced, draws figures F1–F7 and F6b plus a caveats table from them, and checks every plotted number against its source. Everything is CPU-only and deterministic, and it makes no network calls and no LLM or API calls ($0).

## 1. Get the artifact

The workspace is published as one folder of a public GitHub repository:

```bash
git clone <repository-url>
cd <repository>/<this-artifact-folder>      # the folder that contains make_all.py
```

## 2. System, Python and libraries

- Ubuntu (any recent release) with `uv` installed (`curl -LsSf https://astral.sh/uv/install.sh | sh`). No other system packages are needed; matplotlib ships its own DejaVu Sans font, which is used when Arial is not installed (it was not installed on the build machine).
- Python 3.12 (built with 3.12.14).
- Exact library versions, which are also pinned in `pyproject.toml` and `requirements.txt`: attrs 26.1.0, contourpy 1.4.0, cycler 0.12.1, fonttools 4.66.0, iniconfig 2.3.0, jsonschema 4.26.0, jsonschema-specifications 2025.9.1, kiwisolver 1.5.1, loguru 0.7.3, matplotlib 3.11.2, numpy 2.5.3, packaging 26.3, pandas 3.0.6, pillow 12.3.0, pluggy 1.6.0, pyarrow 25.0.1, pygments 2.21.0, pyparsing 3.3.3, pypdf 6.19.0, pytest 9.1.1, python-dateutil 2.9.0.post0, pyyaml 6.0.3, referencing 0.37.0, rpds-py 2026.6.3, six 1.17.0, typing-extensions 4.16.0.

```bash
uv venv .venv --python=3.12
uv pip install --python .venv/bin/python -r requirements.txt
```

## 3. Input data (other artifacts), environment variables and keys

No downloads, no API keys and no user-uploaded files are used.

All inputs are result files of earlier artifacts in the same run. `src/registry.py` and `checks/independent.py` resolve them through ONE environment variable, `AII_RUN_ROOT`. Its default is the directory four levels above this folder, which is the run root on the build server. Each source path in `sources.yaml` is relative to that run root. For example, `art_2Cd2JJypeGuA` is read at `$AII_RUN_ROOT/3_invention_loop/iter_3/gen_art/gen_art_experiment_7/results/d2_summary.json`.

In the published repository each dependency artifact is its own sibling folder. To reproduce from a clone, point `AII_RUN_ROOT` at a directory in which each artifact folder is reachable under its run-root-relative path, for example with symlinks:

| Artifact id | Path under `AII_RUN_ROOT` |
|---|---|
| art_2Cd2JJypeGuA | `3_invention_loop/iter_3/gen_art/gen_art_experiment_7` |
| art_htO_gJuUn6Pr | `3_invention_loop/iter_3/gen_art/gen_art_experiment_5` |
| art_QKsLguxnGFQT | `3_invention_loop/iter_3/gen_art/gen_art_experiment_8` |
| art_62TVG6A4f7Iy | `3_invention_loop/iter_3/gen_art/gen_art_experiment_6` |
| art_XGdzjWgi-a88 | `3_invention_loop/iter_4/gen_art/gen_art_experiment_9` |
| art_WZ8fbLn79nCq | `3_invention_loop/iter_4/gen_art/gen_art_evaluation_2` |
| art_zw_JJGsUFSnd | `3_invention_loop/iter_4/gen_art/gen_art_evaluation_3` |
| art_mu0h0npvNX_u | `3_invention_loop/iter_4/gen_art/gen_art_evaluation_4` |
| art_FZ2OCJwV6xHs | `3_invention_loop/iter_4/gen_art/gen_art_evaluation_5` |
| art_eR1Z7fMlOcxs | `3_invention_loop/iter_2/gen_art/gen_art_dataset_5` |
| art_BdBvbNuNU8E7 | `3_invention_loop/iter_2/gen_art/gen_art_experiment_1` |
| art_yjFB8Spw2w6M | `3_invention_loop/iter_2/gen_art/gen_art_experiment_2` |
| art_mbFjmo5rbbf8 | `3_invention_loop/iter_2/gen_art/gen_art_experiment_3` |

```bash
mkdir -p runroot/3_invention_loop/iter_4/gen_art          # repeat for iter_2 and iter_3
ln -s "$PWD/../<folder of art_WZ8fbLn79nCq>" runroot/3_invention_loop/iter_4/gen_art/gen_art_evaluation_2
# ... one symlink per row of the table ...
export AII_RUN_ROOT="$PWD/runroot"
```

F7 also globs `$AII_RUN_ROOT/3_invention_loop/iter_5/gen_art/*/results/k*_rows.csv`. If none are present or none are schema-valid, F7 ships as a template. That was the case in this build: two files were found, but their columns did not match the schema.

Before rendering, compare `results/source_hashes.json` (sha256 of every source file read in this build) with your copies. If a hash differs, the source changed and the figures will differ.

## 4. Commands actually run (in order)

Hardware: a CPU-only Linux container (48 logical cores and about 250 GB RAM visible; the scripts are single-process and need under 1 GB RAM). No GPU. Nothing is random except the lint probe and the placebo shuffle in `audit/rederive_headlines.py` (seed 0).

```bash
.venv/bin/python make_all.py                      # ~50 s: writes sources.yaml, figures/F1..F7 (+F6b), tables/
.venv/bin/python checks/selftest_mutation.py      # ~25 s: mutation + lint self-test -> results/check_selftest.json
.venv/bin/python eval.py                          # ~30 s: per-figure checks, production, lint, drift -> eval_out.json
.venv/bin/python audit/rederive_headlines.py      # ~1 s: independent re-derivation + shuffled placebo
.venv/bin/python -m pytest -q                     # ~40 s: 12 tests (all checks, lint, production, self-test)
# JSON size variants (pipeline skill aii-json; any copy of full/mini/preview logic works):
#   aii_json_format_mini_preview.py --input eval_out.json  -> full_/mini_/preview_eval_out.json
```

`make_all.py f2_d2_forest f5_rooting` rebuilds only the named modules. A full rebuild takes about 2.5 minutes wall time in total.

## 5. What you should get

- `figures/F1/F1_method_flow.pdf` (methodology and decision flow; the paper's "general methodology in graphical form"), `figures/F2/F2_d2_forest.pdf` (D2 grafting forest: screen co-primary IRR/SD 1.300 [1.164, 1.452]; held-out co-primary 1.187 [1.057, 1.335], Holm p 0.009; MeSH 1.233 [1.117, 1.361]; IVW 1.262 [1.173, 1.358], I² = 0), `figures/F3/F3_mechanism.pdf`, `figures/F4/F4_rq1_heldout.pdf` (R1_DEAD), `figures/F5/F5_occupancy_rooting.pdf`, `figures/F6/F6_cases.pdf`, `figures/F6b/F6b_case_networks.pdf` (supplementary), `figures/F7/F7_selftest.pdf` (template). Each figure comes as a vector PDF (TrueType fonts) plus a 600 dpi PNG, with `caption.md`, `figure_spec.json` and `plotted_values.json`.
- `tables/inferential_caveats.tex` (17 rows) goes beside F2 in the paper's results section.
- `eval_out.json` `metrics_agg`: value_fidelity 1.0 over 957 plotted values; drift 170 MATCH / 3 DRIFT / 1 NOT_FOUND over 174 record quotes; figure_completeness 1.0; request_coverage_shown_fraction 0.875; min_font_pt 6.5; n_text_overlaps 0; label_mismatches 0; openrouter_usd 0.
- `results/drift_report.csv` lists the three DRIFT rows and the NOT_FOUND row (see README "Known discrepancies"). These are corrections for the paper text.
- `audit/rederive_headlines.json` has `all_ok: true`.

In the paper, F1 goes in Methods, F2–F3 in the RQ2 (diffusion) results, F4 in the RQ1 results, F5 with the typology, F6 in the case-study section, F6b and F7 in the supplement.
