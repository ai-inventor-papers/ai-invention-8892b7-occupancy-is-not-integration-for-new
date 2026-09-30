"""F7: K1-K3 post-confirmation exploratory forest - a template filled only if k*_rows.csv exist at build time."""
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

from src import style
from src.plots.common import write_sidecars
from src.registry import RUN_ROOT, Recorder, Registry

TESTS = ["K1_ext", "K1_int", "K1_EST", "K2_A_cont_after_generality", "K2_A_lift", "K2_retained_share",
         "K3_physics", "K3_CS", "K3_other", "K3_MeSH"]
FOLDS = ["screen", "heldout", "mesh", "ivw"]
SCALES = {"IRR": 1.0, "ratio": 1.0, "LPM_pp": 0.0}  # reference line per scale
COLUMNS = ["test", "fold", "estimand", "scale", "est", "lo", "hi", "p", "holm_p", "N", "G", "decision",
           "source_path", "label"]
SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema", "title": "k_rows", "type": "array",
    "items": {"type": "object", "required": COLUMNS, "properties": {
        "test": {"enum": TESTS}, "fold": {"enum": FOLDS}, "estimand": {"type": "string"},
        "scale": {"enum": list(SCALES)}, "est": {"type": ["number", "null"]}, "lo": {"type": ["number", "null"]},
        "hi": {"type": ["number", "null"]}, "p": {"type": ["number", "null"]},
        "holm_p": {"type": ["number", "null"]}, "N": {"type": ["number", "null"]},
        "G": {"type": ["number", "null"]}, "decision": {"type": ["string", "null"]},
        "source_path": {"type": "string"}, "label": {"const": "POST-CONFIRMATION EXPLORATORY"}}}}
# K2 decision thresholds as declared in the plan's spec (drawn as guides, not data)
K2_RETAINED_MIN = 0.5


def _num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def plot_k_forest(rows: list[dict], out_dir: Path, stem: str, watermark: str | None = None) -> dict:
    scales = [s for s in SCALES if any(r["scale"] == s for r in rows)] or ["IRR"]
    fig = style.new_figure(style.W_DOUBLE_MM, 30 + 6 * max(len(rows), 4))
    for si, sc in enumerate(scales):
        sub = [r for r in rows if r["scale"] == sc]
        ax = fig.add_axes([0.3 + si * (0.66 / len(scales)), 0.12, 0.6 / len(scales) - 0.04, 0.8])
        for i, r in enumerate(sub):
            colour, marker, _ = style.fold_style("POST-CONFIRMATION EXPLORATORY")
            est, lo, hi = _num(r["est"]), _num(r["lo"]), _num(r["hi"])
            if est is None:
                continue
            if lo is not None and hi is not None:
                ax.plot([lo, hi], [i, i], color=colour, lw=0.9)
            ax.plot([est], [i], marker=marker, color=colour, ms=4)
        ax.axvline(SCALES[sc], color=style.DARK_GREY, lw=0.6, ls="--")
        if sc == "ratio":
            ax.axvline(K2_RETAINED_MIN, color=style.OKABE_ITO["vermillion"], lw=0.6, ls=":")
        ax.set_ylim(len(sub) - 0.5, -0.5)
        ax.set_yticks(range(len(sub)))
        ax.set_yticklabels([f"{r['test']} | {r['fold']}" for r in sub] if si == 0 else [""] * len(sub),
                           fontsize=style.SMALL_PT)
        ax.set_xlabel(sc)
    if watermark:
        style.no_overlap(fig.text(0.5, 0.5, watermark, fontsize=28, color="#BBBBBB", alpha=0.6, rotation=30,
                                  ha="center", va="center"))
    fig.text(0.01, 0.97, "POST-CONFIRMATION EXPLORATORY (K1-K3)", fontsize=style.BASE_PT, fontweight="bold",
             va="top")
    return style.save(fig, out_dir, stem)


def build(reg: Registry, out_root: Path) -> dict:
    rec = Recorder(reg, "F7")
    out = out_root / "F7"
    out.mkdir(parents=True, exist_ok=True)
    (out / "k_rows.schema.json").write_text(json.dumps(SCHEMA, indent=1))
    template = [{c: None for c in COLUMNS} | {"test": t, "fold": f, "label": "POST-CONFIRMATION EXPLORATORY",
                                              "source_path": ""} for t in TESTS for f in FOLDS]
    (out / "k_template.json").write_text(json.dumps(template, indent=1))
    # self-test with DUMMY rows (generated deterministically, clearly watermarked)
    dummy = [{"test": t, "fold": "screen", "estimand": "DUMMY", "scale": "IRR", "est": 1 + 0.02 * i,
              "lo": 0.9 + 0.02 * i, "hi": 1.1 + 0.02 * i, "p": None, "holm_p": None, "N": None, "G": None,
              "decision": "DUMMY", "source_path": "none", "label": "POST-CONFIRMATION EXPLORATORY"}
             for i, t in enumerate(TESTS)]
    audit = plot_k_forest(dummy, out, "F7_selftest", watermark="TEMPLATE - NOT DATA")
    found = sorted((RUN_ROOT / "." / "round-5" / ".").glob("*/results/k*_rows.csv"))
    status = {"template": True, "found_files": [str(p.relative_to(RUN_ROOT)) for p in found]}
    rows, invalid = [], []
    for p in found:
        with p.open() as fh:
            for r in csv.DictReader(fh):
                ok = (r.get("test") in TESTS and r.get("fold") in FOLDS and r.get("scale") in SCALES
                      and r.get("label") == "POST-CONFIRMATION EXPLORATORY")
                (rows if ok else invalid).append({**r, "_file": str(p.relative_to(RUN_ROOT)),
                                                  "_sha256": hashlib.sha256(p.read_bytes()).hexdigest()})
    status["n_valid_rows"], status["n_invalid_rows"] = len(rows), len(invalid)
    if rows:
        audit = plot_k_forest(rows, out, "F7_filled")
        status["filled"] = True
        (out / "STATUS.txt").write_text(f"filled from {len(found)} file(s); {len(rows)} valid rows, "
                                        f"{len(invalid)} invalid\n")
        (out / "filled_sources.json").write_text(json.dumps(rows, indent=1))
    else:
        status["filled"] = False
        msg = "template only; fill in paper step\n"
        if found:
            cols = sorted({c for r in invalid for c in r if not c.startswith("_")})
            msg += (f"found {len(found)} k*_rows.csv file(s) with {len(invalid)} rows, none valid against "
                    f"k_rows.schema.json (their columns: {', '.join(cols)}); the paper step must map "
                    "estimate/ci_lo/ci_hi/unit onto est/lo/hi/scale before filling F7.\n")
        (out / "STATUS.txt").write_text(msg)
    caption = ("F7 (template). K1-K3 post-confirmation exploratory rows, one panel per scale (IRR, LPM percentage "
               "points, ratio), each row labelled POST-CONFIRMATION EXPLORATORY with N = entry events and G = "
               "clusters as given per row. CI type is per row (95% as given in the source row), and F7_selftest.pdf "
               "shows DUMMY rows only. Source: 3_invention_loop/iter_5/gen_art/*/results/k*_rows.csv.")
    write_sidecars(out, "F7", rec, {"width_mm": style.W_DOUBLE_MM, "status": status, "ci_type": "per row"},
                   caption, audit)
    return {**audit, "status": status}
