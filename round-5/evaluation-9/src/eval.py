#!/usr/bin/env python3
"""Evaluates the figure set: fidelity (M1), record drift (M2), completeness (M3), request coverage (M4),
production checks (M5), label integrity (M6) and spend (M7). Writes eval_out.json (exp_eval_sol_out)."""
from __future__ import annotations

import csv
import json
import re
import subprocess
import sys
from pathlib import Path

from loguru import logger

WS = Path(__file__).resolve().parent
sys.path.insert(0, str(WS))
sys.path.insert(0, str(WS / "checks"))
from independent import run_figure  # noqa: E402
from src import style  # noqa: E402

logger.remove()
logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
(WS / "logs").mkdir(exist_ok=True)
logger.add(WS / "logs" / "eval.log", rotation="30 MB", level="DEBUG")

FIGS = ["F1", "F2", "F3", "F4", "F5", "F6", "F7"]
ALL_FIGS = FIGS[:6] + ["F6b", "F7"]
ALLOWED = {"SCREEN", "CONFIRMATORY", "REPLICATION", "SUPPLEMENTARY/POOLED", "MECHANISM", "DESCRIPTIVE",
           "POST-CONFIRMATION EXPLORATORY"}
RECORD_MAP = {"SUPPLEMENTARY": "SUPPLEMENTARY/POOLED", "POOLED": "SUPPLEMENTARY/POOLED"}
COVERAGE = [
    ("1 semantic grounding (frame, classifier/linker, corpus)", "F1 band 1", "shown", ""),
    ("2 two network views (co-word snapshots; concept-subfield bipartite)", "F1 band 2; F6b ego/alluvial",
     "shown", "network layouts are embedded from exp_8 (supplementary)"),
    ("3 RQ1 structural precursors of emergence", "F4", "shown", "R1_DEAD stated on the figure"),
    ("4 RQ2 diffusion across disciplinary boundaries (host entry, grafting)", "F2, F3", "shown", ""),
    ("5 diffusion typology", "F5; F1 band 4", "shown", ""),
    ("6 case studies (quantitatively selected)", "F6; F6b", "shown", ""),
    ("7 methodology in graphical form", "F1", "shown", ""),
    ("8 comparison to related work", "none", "not shown",
     "a literature comparison is prose/table work for the paper step; no figure here"),
]


def sentences(text: str) -> int:
    body = re.sub(r"^F\d+b?\s*(\(\w+\))?\.\s*", "", text.strip())
    body = re.sub(r"\b(e\.g|i\.e|et al|vs|cf)\.", "x", body)
    return len([s for s in re.split(r"(?<=[.!?])\s+(?=[A-Z(])", body) if s.strip()])


def completeness() -> tuple[list[dict], float]:
    rows = []
    for f in FIGS:
        d = WS / "figures" / f
        cap = (d / "caption.md").read_text() if (d / "caption.md").exists() else ""
        chk = json.loads((WS / "results" / f"check_{f}.json").read_text()) if (
            WS / "results" / f"check_{f}.json").exists() else {"n_failed": 1}
        n_s = sentences(cap)
        cap_ok = (2 <= n_s <= 4 and bool(re.search(r"\bn\s*=|\bN\s*=|\b\d[\d,]*\s+(concepts|entries|draws|cases|"
                                                      r"strata|pairs|papers|events)", cap))
                  and bool(re.search(r"CI|confidence|no CIs|per row", cap))
                  and bool(re.search(r"3_invention_loop/iter_\d/gen_art/", cap)))
        rows.append({"figure": f, "pdf": any(d.glob("*.pdf")), "png": any(d.glob("*.png")),
                     "figure_spec": (d / "figure_spec.json").exists(), "caption": cap_ok,
                     "plotted_values": (d / "plotted_values.json").exists(),
                     "check_passes": chk["n_failed"] == 0 and (WS / "checks" / f"check_{f}.py").exists(),
                     "caption_sentences": n_s})
    cells = [v for r in rows for k, v in r.items() if k not in ("figure", "caption_sentences")]
    return rows, sum(cells) / len(cells)


def label_integrity() -> dict:
    labs = []
    for f in ALL_FIGS:
        p = WS / "figures" / f / "labels.json"
        if p.exists():
            labs += json.loads(p.read_text())
    labs += json.loads((WS / "tables" / "caveats_labels.json").read_text())
    bad_set = [l for l in labs if l["shown"] not in ALLOWED]
    mism = [l for l in labs if l.get("record_label") and RECORD_MAP.get(l["record_label"], l["record_label"])
            != l["shown"]]
    n_rec = sum(1 for l in labs if l.get("record_label"))
    return {"n_rows": len(labs), "n_with_record_label": n_rec, "not_in_allowed_set": bad_set,
            "record_mismatches": mism, "label_mismatches": len(bad_set) + len(mism)}


@logger.catch(reraise=True)
def main() -> None:
    logger.info("running per-figure checks")
    checks = {}
    for f in ALL_FIGS + ["caveats"]:
        rc = subprocess.run([sys.executable, str(WS / "checks" / f"check_{f}.py")], capture_output=True, text=True)
        checks[f] = json.loads((WS / "results" / f"check_{f}.json").read_text())
        logger.info(f"check_{f}: exit {rc.returncode} n_values {checks[f]['n_values']} failed {checks[f]['n_failed']}")
    for script in ("production.py", "lint_no_literals.py", "drift.py"):
        rc = subprocess.run([sys.executable, str(WS / "checks" / script)], capture_output=True, text=True)
        logger.info(f"{script}: exit {rc.returncode}")
    prod = json.loads((WS / "results" / "production_checks.json").read_text())
    lint = json.loads((WS / "results" / "lint_no_literals.json").read_text())
    drift = json.loads((WS / "results" / "drift_summary.json").read_text())
    selftest = json.loads((WS / "results" / "check_selftest.json").read_text())
    comp_rows, comp = completeness()
    labels = label_integrity()
    n_val = sum(c["n_values"] for c in checks.values())
    n_fail = sum(c["n_failed"] for c in checks.values())
    fidelity = {"n_values": n_val, "n_exact": sum(c["n_exact"] for c in checks.values()),
                "n_derived": sum(c["n_derived"] for c in checks.values()),
                "n_images": sum(c["n_images"] for c in checks.values()), "n_failed": n_fail,
                "n_source_missing_not_plotted": sum(c["n_source_missing"] for c in checks.values()),
                "value_fidelity": (n_val - n_fail) / n_val if n_val else 0.0, "per_figure": checks}
    (WS / "results" / "fidelity_summary.json").write_text(json.dumps(fidelity, indent=1, default=str))
    with (WS / "results" / "figure_completeness.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(comp_rows[0]))
        w.writeheader()
        w.writerows(comp_rows)
    with (WS / "results" / "request_coverage.csv").open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["activity", "figure_or_panel", "status", "reason"])
        w.writerows(COVERAGE)
    (WS / "results" / "label_integrity.json").write_text(json.dumps(labels, indent=1, default=str))
    metrics = {
        "value_fidelity": fidelity["value_fidelity"], "n_plotted_values": n_val, "n_exact": fidelity["n_exact"],
        "n_derived": fidelity["n_derived"], "n_images_hash_checked": fidelity["n_images"], "n_failed": n_fail,
        "n_source_missing_not_plotted": fidelity["n_source_missing_not_plotted"],
        "n_record_expectations": drift["n"], "n_match": drift["counts"]["MATCH"],
        "n_rounding_diff": drift["counts"]["ROUNDING_DIFF"], "n_drift": drift["counts"]["DRIFT"],
        "n_not_found": drift["counts"]["NOT_FOUND"], "figure_completeness": comp,
        "request_coverage_shown_fraction": sum(c[2] == "shown" for c in COVERAGE) / len(COVERAGE),
        "min_font_pt": min(p["min_font_pt"] for p in prod), "n_text_overlaps": sum(p["n_text_overlaps"] for p in prod),
        "production_pass_fraction": sum(p["pass"] for p in prod) / len(prod),
        "label_mismatches": labels["label_mismatches"], "lint_literal_hits": lint["n_hits"],
        "mutation_selftest_pass": float(selftest["selftest_pass"]), "openrouter_usd": 0.0,
    }
    ex_pv = []
    for f in ALL_FIGS + ["caveats"]:
        p = (WS / "tables" / "caveats_values.json") if f == "caveats" else (WS / "figures" / f / "plotted_values.json")
        failed = {(x["panel"], x["row"], x["field"]) for x in checks[f]["failures"]}
        for r in json.loads(p.read_text()):
            if r.get("status") != "OK":
                continue
            ex_pv.append({"input": f"{r['figure']} | panel {r['panel']} | row {r['row']} | {r['field']}",
                          "output": str(r["value"]), "metadata_key": r["key"],
                          "metadata_source_path": r.get("path", ""), "metadata_artifact_id": r.get("artifact_id", ""),
                          "metadata_sha256": r.get("sha256", ""), "metadata_fold_label": r.get("fold_label", ""),
                          "metadata_ci_type": r.get("ci_type", ""), "metadata_source_kind": r.get("source_kind", ""),
                          "metadata_display_string": r.get("display_string") or "",
                          "predict_figure": str(r["value"]),
                          "eval_value_match": 0.0 if (r["panel"], r["row"], r["field"]) in failed else 1.0})
    ex_drift = []
    for r in csv.DictReader((WS / "results" / "drift_report.csv").open()):
        ex_drift.append({"input": f"record quote {r['key']}: {r['quoted']}", "output": r["source_value"] or "NOT_FOUND",
                         "metadata_status": r["status"], "metadata_source": r["source"],
                         "metadata_note": r["note"], "predict_record": r["quoted"],
                         "eval_match": 1.0 if r["status"] == "MATCH" else 0.0})
    ex_comp = [{"input": f"figure {r['figure']} deliverables", "output": json.dumps(r),
                "predict_complete": str(all(v for k, v in r.items() if k not in ("figure", "caption_sentences"))),
                "eval_complete": float(all(v for k, v in r.items() if k not in ("figure", "caption_sentences")))}
               for r in comp_rows]
    ex_cov = [{"input": a, "output": f"{fp} ({st})", "metadata_reason": rsn, "predict_status": st,
               "eval_shown": 1.0 if st == "shown" else 0.0} for a, fp, st, rsn in COVERAGE]
    ex_prod = [{"input": f"production {p['figure']}", "output": "PASS" if p["pass"] else "FAIL",
                "predict_check": "PASS" if p["pass"] else "FAIL",
                "metadata_detail": json.dumps({k: v for k, v in p.items() if k != "colourblind"}),
                "eval_pass": float(p["pass"]), "eval_min_font_pt": float(p["min_font_pt"])} for p in prod]
    out = {"metadata": {"evaluation_name": "paper figure set drawn straight from result files",
                        "artifact_plan": "gen_plan_evaluation_4_idx5",
                        "description": "Fidelity, drift, completeness, coverage, production and label checks for "
                                       "figures F1-F7 and the inferential caveats table; nothing re-estimated.",
                        "figure_widths_mm": [style.W_DOUBLE_MM, style.W_SINGLE_MM]},
           "metrics_agg": metrics,
           "datasets": [{"dataset": "plotted_values", "examples": ex_pv}, {"dataset": "drift", "examples": ex_drift},
                        {"dataset": "figure_completeness", "examples": ex_comp},
                        {"dataset": "request_coverage", "examples": ex_cov},
                        {"dataset": "production_checks", "examples": ex_prod}]}
    (WS / "eval_out.json").write_text(json.dumps(out, indent=1, default=str))
    logger.info(json.dumps(metrics))


if __name__ == "__main__":
    main()
