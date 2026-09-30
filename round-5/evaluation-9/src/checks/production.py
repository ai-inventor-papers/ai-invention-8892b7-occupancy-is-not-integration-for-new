#!/usr/bin/env python3
"""M5 production checks per figure: width/height (mm, from the PDF), fonts embedded as TrueType (no Type 3),
PNG dpi, minimum font size and text overlaps (from the draw-time audit), and colour-blind safety of fold styles."""
from __future__ import annotations

import colorsys
import itertools
import json
import re
import sys
from pathlib import Path

from PIL import Image
from pypdf import PdfReader

WS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WS))
from src import style  # noqa: E402

PT_TO_MM = 25.4 / 72


def luminance(hex_colour: str) -> float:
    r, g, b = (int(hex_colour[i:i + 2], 16) / 255 for i in (1, 3, 5))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def pdf_fonts(pdf: Path) -> dict:
    raw = pdf.read_bytes()
    reader = PdfReader(str(pdf))
    subtypes = set()
    for page in reader.pages:
        res = page.get("/Resources") or {}
        fonts = res.get("/Font") or {}
        for _, ref in fonts.items():
            f = ref.get_object()
            subtypes.add(str(f.get("/Subtype")))
    return {"subtypes": sorted(subtypes), "type3": ("/Type3" in subtypes) or bool(re.search(rb"/Type3", raw)),
            "truetype": any(s in ("/TrueType", "/Type0") for s in subtypes)}


def check_figure(fig_dir: Path) -> dict:
    spec = json.loads((fig_dir / "figure_spec.json").read_text())
    pdfs = sorted(p for p in fig_dir.glob("*.pdf"))
    out = {"figure": fig_dir.name, "files": []}
    for pdf in pdfs:
        box = PdfReader(str(pdf)).pages[0].mediabox
        w, h = float(box.width) * PT_TO_MM, float(box.height) * PT_TO_MM
        png = pdf.with_suffix(".png")
        dpi = Image.open(png).info.get("dpi", (0, 0))[0] if png.exists() else 0
        fonts = pdf_fonts(pdf)
        out["files"].append({"pdf": pdf.name, "width_mm": round(w, 2), "height_mm": round(h, 2),
                             "width_ok": min(abs(w - style.W_DOUBLE_MM), abs(w - style.W_SINGLE_MM)) <= 1,
                             "height_ok": h <= style.MAX_H_MM, "png_dpi": round(dpi),
                             "dpi_ok": round(dpi) >= style.PNG_DPI, "fonts": fonts["subtypes"],
                             "no_type3": not fonts["type3"], "truetype": fonts["truetype"]})
    prod = spec.get("production", {})
    out["min_font_pt"] = prod.get("min_font_pt")
    out["font_ok"] = prod.get("min_font_pt") is not None and prod["min_font_pt"] >= style.SMALL_PT
    out["n_text_overlaps"] = prod.get("n_overlaps", 0)
    out["n_clipped"] = prod.get("n_clipped", 0)
    labels = json.loads((fig_dir / "labels.json").read_text()) if (fig_dir / "labels.json").exists() else []
    used = sorted({l["shown"] for l in labels if l["shown"] in style.FOLD_STYLE})
    pairs = []
    for a, b in itertools.combinations(used, 2):
        ca, ma, fa = style.FOLD_STYLE[a]
        cb, mb, fb = style.FOLD_STYLE[b]
        dl = abs(luminance(ca) - luminance(cb))
        pairs.append({"a": a, "b": b, "dlum": round(dl, 3), "marker_differs": (ma, fa) != (mb, fb),
                      "ok": dl >= 0.15 or (ma, fa) != (mb, fb)})
    colours_ok = all(style.FOLD_STYLE[u][0] in style.ALLOWED_COLOURS for u in used)
    out["colourblind"] = {"folds": used, "palette_ok": colours_ok, "pairs": pairs,
                          "ok": colours_ok and all(p["ok"] for p in pairs)}
    out["pass"] = (all(f["width_ok"] and f["height_ok"] and f["dpi_ok"] and f["no_type3"] for f in out["files"])
                   and out["font_ok"] and out["n_text_overlaps"] == 0 and out["n_clipped"] == 0
                   and out["colourblind"]["ok"])
    return out


def main() -> int:
    res = [check_figure(d) for d in sorted((WS / "figures").iterdir()) if (d / "figure_spec.json").exists()]
    (WS / "results" / "production_checks.json").write_text(json.dumps(res, indent=1))
    for r in res:
        print(r["figure"], "PASS" if r["pass"] else "FAIL", r["min_font_pt"], r["n_text_overlaps"],
              [(f["pdf"], f["width_mm"], f["height_mm"], f["png_dpi"], f["fonts"]) for f in r["files"]])
    return 0 if all(r["pass"] for r in res) else 1


if __name__ == "__main__":
    sys.exit(main())
