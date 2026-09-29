"""House style for the ANS figure set: Okabe-Ito colours, fold -> colour+marker, Springer widths.

Numbers in this module are axis cosmetics only (sizes, widths, reference lines); the literal
lint (checks/lint_no_literals.py) whitelists this file. No data value may live here.
"""
from __future__ import annotations

import itertools
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import font_manager  # noqa: E402

MM = 1 / 25.4
W_DOUBLE_MM = 174
W_SINGLE_MM = 84
MAX_H_MM = 234
BASE_PT = 8
TICK_PT = 7
SMALL_PT = 6.5  # absolute floor used for dense annotations (M5 target >= 6.5)
LINE_PT = 0.7
PNG_DPI = 600

OKABE_ITO = {
    "black": "#000000", "orange": "#E69F00", "skyblue": "#56B4E9", "green": "#009E73",
    "yellow": "#F0E442", "blue": "#0072B2", "vermillion": "#D55E00", "purple": "#CC79A7",
}
GREY = "#999999"
DARK_GREY = "#555555"
ALLOWED_COLOURS = set(OKABE_ITO.values()) | {GREY, DARK_GREY, "#FFFFFF", "#DDDDDD", "#BBBBBB"}

# fold label -> (colour, marker, filled)
FOLD_STYLE = {
    "SCREEN": (DARK_GREY, "o", True),
    "CONFIRMATORY": (OKABE_ITO["blue"], "s", True),
    "REPLICATION": (OKABE_ITO["green"], "D", True),
    "SUPPLEMENTARY/POOLED": (OKABE_ITO["purple"], "^", True),
    "MECHANISM": (OKABE_ITO["orange"], "o", True),
    "DESCRIPTIVE": (GREY, "v", True),
    "PLACEBO": (GREY, "x", True),
    "DEAD/NULL": (GREY, "o", False),
    "POST-CONFIRMATION EXPLORATORY": (OKABE_ITO["vermillion"], "P", True),
}
FOLD_LABELS = set(FOLD_STYLE) | {"SUPPLEMENTARY", "POOLED"}

# Tick positions for the log IRR axes (cosmetic).
LOG_TICKS = [0.5, 0.7, 1.0, 1.4, 2.0]
OR_TICKS = [0.5, 1.0, 2.0, 4.0]

ROLE_COLOURS = {"BRIDGE": OKABE_ITO["blue"], "OTHER": "#DDDDDD", "STAYER": OKABE_ITO["orange"],
                "MIGRANT": OKABE_ITO["vermillion"], "FOUNDER": OKABE_ITO["green"],
                "CORE_GROWING": OKABE_ITO["purple"]}
SHARE_COLOURS = [OKABE_ITO["blue"], OKABE_ITO["orange"], OKABE_ITO["green"], OKABE_ITO["skyblue"],
                 OKABE_ITO["vermillion"], "#DDDDDD"]
SHARE_HATCHES = ["", "///", "...", "\\\\\\", "xx", ""]


def _font_family() -> str:
    names = {f.name for f in font_manager.fontManager.ttflist}
    return "Arial" if "Arial" in names else "DejaVu Sans"


def apply_style() -> None:
    plt.rcParams.update({
        "pdf.fonttype": 42, "ps.fonttype": 42, "font.family": "sans-serif",
        "font.sans-serif": [_font_family(), "DejaVu Sans"], "font.size": BASE_PT,
        "axes.titlesize": BASE_PT, "axes.labelsize": BASE_PT, "xtick.labelsize": TICK_PT,
        "ytick.labelsize": TICK_PT, "legend.fontsize": TICK_PT, "lines.linewidth": LINE_PT,
        "axes.linewidth": 0.6, "xtick.major.width": 0.6, "ytick.major.width": 0.6,
        "patch.linewidth": 0.5, "hatch.linewidth": 0.5, "axes.spines.top": False,
        "axes.spines.right": False, "savefig.dpi": PNG_DPI, "figure.dpi": 100,
        "axes.unicode_minus": True, "mathtext.default": "regular",
    })


def new_figure(width_mm: float, height_mm: float):
    apply_style()
    return plt.figure(figsize=(width_mm * MM, height_mm * MM))


def text_audit(fig) -> dict:
    """Minimum rendered font size and pairwise overlaps of visible text artists (M5)."""
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    hidden = set()
    for ax in fig.axes:
        if not ax.axison:
            hidden.update(id(t) for t in ax.get_xticklabels() + ax.get_yticklabels())
            hidden.update(id(t) for tk in ax.xaxis.get_major_ticks() + ax.yaxis.get_major_ticks()
                          for t in (tk.label1, tk.label2))
            hidden.update({id(ax.xaxis.label), id(ax.yaxis.label)})
            continue
        for axis in (ax.xaxis, ax.yaxis):
            drawn = set(axis._update_ticks())
            for tk in axis.get_major_ticks() + axis.get_minor_ticks():
                if tk not in drawn:
                    hidden.update({id(tk.label1), id(tk.label2)})
                elif not tk.label2.get_visible() or not tk.label2On if hasattr(tk, "label2On") else False:
                    hidden.add(id(tk.label2))
    texts = [t for t in fig.findobj(matplotlib.text.Text)
             if t.get_visible() and t.get_text().strip() and id(t) not in hidden]
    sizes = [t.get_fontsize() for t in texts]
    boxes = []
    for t in texts:
        try:
            bb = t.get_window_extent(renderer)
        except (RuntimeError, ValueError):
            continue
        if bb.width > 0 and bb.height > 0:
            boxes.append((t, bb.shrunk(0.9, 0.8)))
    overlaps = []
    for (t1, b1), (t2, b2) in itertools.combinations(boxes, 2):
        if getattr(t1, "_allow_overlap", False) or getattr(t2, "_allow_overlap", False):
            continue
        if b1.overlaps(b2):
            overlaps.append([t1.get_text()[:40], t2.get_text()[:40]])
    fw, fh = fig.get_size_inches() * fig.dpi
    clipped = [t.get_text()[:40] for t, b in boxes
               if b.x0 < -1 or b.y0 < -1 or b.x1 > fw + 1 or b.y1 > fh + 1]
    return {"min_font_pt": min(sizes) if sizes else None, "n_text": len(texts),
            "n_overlaps": len(overlaps), "overlaps": overlaps[:20], "n_clipped": len(clipped),
            "clipped": clipped[:20]}


def save(fig, out_dir: Path, stem: str) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    audit = text_audit(fig)
    fig.savefig(out_dir / f"{stem}.pdf", metadata={"CreationDate": None})
    fig.savefig(out_dir / f"{stem}.png", dpi=PNG_DPI)
    w, h = fig.get_size_inches() / MM
    plt.close(fig)
    audit.update({"width_mm": round(float(w), 2), "height_mm": round(float(h), 2)})
    return audit


def fold_style(label: str):
    return FOLD_STYLE.get(label, FOLD_STYLE["DESCRIPTIVE"])


def no_overlap(t):
    """Mark a text artist as a deliberate overlay (e.g. a watermark) exempt from the overlap audit."""
    t._allow_overlap = True
    return t
