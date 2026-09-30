# Review of the iteration-1 research report (run_spUCG07dPEEP)

This folder holds an adversarial audit of the iteration-1 internal research report ("Occupancy is not integration...").
It checks each executed artifact against the report for completeness, traceability, recorded reasoning and honesty.

## Layout
| file | what |
|---|---|
| `.terminal_claude_agent_struct_out.json` | the review (ReviewerFeedback schema): scores, 12 critiques, coverage, blocking flag |
| `build_review.py` | writes the JSON above; every number in it was recomputed from the sibling artifact workspaces |
| `.aii/manifest.yaml` | storage decisions: empty, since this folder holds only small text and code files |

## How the numbers were checked
The artifact workspaces live under `../` (read-only). Checks run:
- `gen_art_dataset_1`: `logs/assemble_summary.json`, `context/quality_report.md` (Gate A by year), `concept_work.parquet`
  (match evidence split by arm), `data_out.json` (routes, flags), `assemble.py` (traced-share, sense-check and
  venue-habitat code), `screen.py` (reference rule), plus a count of pre-registered screen units
  (c, d != origin, t; >=10 d-papers in [t-5,t]) from `works/*.parquet`.
- `gen_art_dataset_2`: not referenced by the report. See `.aii_worker_result.json`, `README.md` and `data/calibration_by_decile.csv`.
- `gen_art_dataset_3`: `selection_flow.json`, `full_data_out.json` metadata, `provenance.md`.
- `gen_art_dataset_4`: `labelling/quality.json`, `data_out/pool_early.json`, `logs/summary.json`, `full_data_out/*`.
- `gen_art_research_1`: `research_report.md`, `research_verification.json`; and `gen_strat/gen_strat_1` for the pre-registration.

Run: `python3 build_review.py` regenerates the JSON (Python 3 standard library only).

## Restoring removed files
Nothing is marked `delete`; there is nothing to restore.
