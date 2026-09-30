# Reproducing the numbers-of-record audit

This is what was actually run on 2026-09-29. It uses the CPU only, costs $0, makes no API calls, and needs no keys or environment secrets.

## 1. Get the artifact

The workspace is published as one folder of the run's public GitHub repository:

```bash
git clone <repository-url>
cd <repository>/<this-artifact-folder>   # the folder containing eval.py
```

## 2. Inputs (other artifacts, read-only)

The audit reads files from earlier artifacts of the same run. Every path in the code is written relative to the run root, `<run>`. This artifact sits at `<run>/3_invention_loop/iter_5/gen_art/<this folder>`, so the code sets `RUN_ROOT = Path(__file__).resolve().parents[4]` by default. Set the environment variable `AII_RUN_ROOT` to point at a different root.

To reproduce, the following artifacts must be present at their run-relative locations. The repository publishes each as a sibling folder; copy or symlink them into a `<run>`-shaped tree if your checkout is flat.

| Artifact id | Run-relative folder |
|---|---|
| art_2Cd2JJypeGuA | `round-3/experiment-7/src` |
| art_htO_gJuUn6Pr | `round-3/experiment-5/src` |
| art_62TVG6A4f7Iy | `round-3/experiment-6/src` |
| art_QKsLguxnGFQT | `round-3/experiment-8/src` |
| art__i2cIye01VnN | `round-3/evaluation-1/src` |
| art_WZ8fbLn79nCq | `round-4/evaluation-2/src` |
| art_zw_JJGsUFSnd | `round-4/evaluation-3/src` |
| art_mu0h0npvNX_u | `round-4/evaluation-4/src` |
| art_FZ2OCJwV6xHs | `round-4/evaluation-5/src` |
| art_XGdzjWgi-a88 | `round-4/experiment-9/src` |

The auto-scan also indexes the iteration 1–2 artifacts listed in `audit_core.ARTIFACTS`.

It also reads these pipeline files:

- the report under audit, `3_invention_loop/iter_5/gen_strat/current_report.md`;
- the hypothesis, `3_invention_loop/iter_4/upd_hypo/upd_hypo/.terminal_claude_agent_struct_out.json`;
- the strategy files `3_invention_loop/iter_{2,3,4}/gen_strat/gen_strat_1/.terminal_claude_agent_struct_out.json`, from which the decision rules are quoted verbatim;
- `round-4/report-text/.terminal_claude_agent_struct_out.json`, which holds the fig_methodology spec.

No user-uploaded file is used.

## 3. Environment

The run used Ubuntu/Debian with Python 3.12 and `uv`. No system packages are needed beyond those.

```bash
uv venv .venv --python=3.12
uv pip install --python .venv/bin/python loguru==0.7.3 numpy==2.5.3 pandas==3.0.6 pyarrow==25.0.1 \
    python-dateutil==2.9.0.post0 scipy==1.18.1 six==1.17.0     # same pins as pyproject.toml
```

Hardware: a container with 6 CPUs and a 57 GB RAM limit. The L4 GPU was present but not used. Peak memory stays below 3 GB, and `RLIMIT_AS` is set to 24 GB.

## 4. Commands, in order

```bash
.venv/bin/python eval.py            # ~50-70 s; seeds 20260929 (pre-registered injection) and 20260930 (blind injection)
.venv/bin/python verify_headlines.py  # separate re-derivation of the headline metrics + shuffled-source placebo
.venv/bin/python audit_tables.py check-dir tables --out results/table_assertions.json   # table assertions (also called by eval.py)
```

`eval.py` runs the following steps:

1. It writes `results/audit_spec.json` and `results/audit_universe.json` before opening any source. These hold the universe of cited numbers, its sha256, a UTC timestamp, the match rule, the flags and the known-drift list.
2. It evaluates the 319 registry claims (`registry.py`): 13 decision rules, 23 verdict cells and 17 text assertions (`checks.py`).
3. It auto-scans every numeric token of the report.
4. It builds the drift list.
5. It runs the seeded injection twice.
6. It runs the independent re-derivation, `rederive_independent.py`, as a subprocess.
7. It builds the 11 tables and runs `audit_tables.py`; only tables that pass are written as `.csv` / `.md`.
8. It writes `tables/cases.md` and `eval_out.json`.

Afterwards the pipeline ran `aii_json_format_mini_preview.py --input eval_out.json`, which produced `full_`, `mini_` and `preview_eval_out.json`.

`results/precision_manual_labels.json` holds the executor's manual TRUE / FALSE / UNVERIFIED labels for the 30 sampled flagged lines. It is read, not regenerated. If the flagged set changes, you must relabel by hand.

## 5. Expected outputs

These numbers come from `results/audit_summary.json` and are re-derived in `results/verify_headlines.json`.

- **Registry claims.** 319 curated cited numbers.
  - Traceability: 99.4%.
  - Agreement: 90.8% overall; tier R 92.9% of 210; tier C 82.0% of 50.
  - Flags: 13 DRIFT_VALUE, 7 WRONG_ESTIMATOR, 4 WRONG_DEFINITION (plus 13 from text assertions), 2 NOT_TRACEABLE, 57 MISSING_IN_REPORT.
- **Report drift.** 45 drift rows on 32 report lines: 6 verdict-changing, 23 number-only, 16 wording. Known-drift recall is 12/12.
- **Seeded injection** (blind seed 20260930):

  | Error type | Recall |
  |---|---|
  | Overall | 0.60 |
  | CI swap | 1.0 |
  | Verdict flip | 0.9 |
  | Digit change | 0.4 |
  | Relabel | 0.1 |

  Manual precision is 0.83.
- **Independent re-derivation.** 73/73 values agree.
- **Tables.** 11/11 pass.
- **Verdict consistency.** 1 mismatch in 13 rules (R1_DEAD). One more rule is RULE_NOT_RECORDED.
- **MISSING_IN_REPORT.** 292 rows.
- **Table 18.** Of the claimed fixes, 3 DONE, 4 PARTIAL, 4 NOT DONE.
- **Placebo.** When source values are shuffled across claims, agreement falls to 1.6% on average (3.5% at most), so the match rule is not vacuous.

In the paper, the tables in `tables/` feed the design, population-flow, decision-rule, inferential-caveat, RQ1 and adopter tables, and the Availability statement. `results/report_drift.csv` lists which report sentences have to be corrected.
