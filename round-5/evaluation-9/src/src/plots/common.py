"""Shared drawing helpers: forest rows with clipped-CI arrows and right-margin text columns."""
from __future__ import annotations

import json
from pathlib import Path

from matplotlib.transforms import blended_transform_factory

from src import style
from src.registry import Recorder

WS = Path(__file__).resolve().parents[2]


def pfmt(v: float) -> str:
    """Format string for a p value (chosen from the value, stored so checks can reproduce it)."""
    return ".3f" if v >= 0.001 else ".1e"


def forest(ax, rows: list[dict], rec: Recorder, *, panel: str, xlim: tuple, log: bool = True,
           ref: float = 1.0, cols: list[tuple] = (), col_x0: float = 1.03, col_dx: float = 0.13,
           label_fs: float = style.TICK_PT, est_fmt: str = ".3f") -> dict:
    """Draw forest rows top-to-bottom. Row keys: label, fold (evidence label), style, est/lo/hi (registry
    keys), text {col: key}, note, header, hollow, point_only. Returns {row label: y}."""
    expanded = []
    for r in rows:
        expanded.append(r)
        if r.get("note") and not r.get("note_inline"):
            expanded.append({"spacer": True, "note_of": r})
    rows = expanded
    n = len(rows)
    ys = {}
    ax.set_ylim(n - 0.4, -0.8)
    ax.set_xlim(*xlim)
    if log:
        ax.set_xscale("log")
        ticks = [t for t in style.LOG_TICKS if xlim[0] <= t <= xlim[1]]
        ax.set_xticks(ticks)
        ax.set_xticklabels([f"{t:g}" for t in ticks])
        ax.minorticks_off()
    ax.axvline(ref, color=style.DARK_GREY, lw=0.6, ls="--", zorder=0)
    ax.set_yticks([])
    ax.spines["left"].set_visible(False)
    tr = blended_transform_factory(ax.transAxes, ax.transData)
    for j, (cname, _w) in enumerate(cols):
        ax.text(col_x0 + j * col_dx, -0.8, cname, transform=tr, ha="left", va="bottom",
                fontsize=style.SMALL_PT, fontweight="bold")
    for i, r in enumerate(rows):
        if r.get("spacer"):
            o = r["note_of"]
            ax.text(xlim[0] * (1.02 if log else 1), i - 0.15, o["note"], fontsize=style.SMALL_PT, ha="left",
                    va="center", color=o.get("note_colour", style.DARK_GREY), style="italic")
            continue
        ys[r.get("id", r["label"])] = i
        if r.get("header"):
            ax.text(-0.01, i, r["label"], transform=tr, ha="right", va="center", fontsize=label_fs,
                    fontweight="bold")
            ax.axhline(i - 0.5, color="#DDDDDD", lw=0.5, zorder=0)
            continue
        ax.text(-0.01, i, r["label"], transform=tr, ha="right", va="center", fontsize=label_fs)
        colour, marker, filled = style.fold_style(r.get("style", r.get("fold", "")))
        if r.get("hollow"):
            filled = False
        rid = r.get("id", r["label"])
        est = rec.v(r["est"], panel=panel, row=rid, field="est", fmt=est_fmt)
        rec.label(rid, r.get("fold", ""), r.get("record_key"), panel=panel)
        if est is None:
            ax.text(xlim[0] * 1.05 if log else xlim[0], i, "n/a - source missing", fontsize=style.SMALL_PT,
                    va="center", color=style.DARK_GREY)
            continue
        lo = rec.v(r["lo"], panel=panel, row=rid, field="lo", fmt=est_fmt) if r.get("lo") else None
        hi = rec.v(r["hi"], panel=panel, row=rid, field="hi", fmt=est_fmt) if r.get("hi") else None
        if lo is not None and hi is not None:
            clo, chi = max(lo, xlim[0]), min(hi, xlim[1])
            ax.plot([clo, chi], [i, i], color=colour, lw=0.9, solid_capstyle="butt",
                    ls=r.get("ls", "-"))
            if lo < xlim[0]:
                ax.plot([xlim[0]], [i], marker="<", color=colour, ms=3.5)
                ax.text(xlim[0], i + 0.42, f"{lo:{est_fmt}}", fontsize=style.SMALL_PT, ha="left",
                        va="center", color=colour)
            if hi > xlim[1]:
                ax.plot([xlim[1]], [i], marker=">", color=colour, ms=3.5)
                ax.text(xlim[1], i + 0.42, f"{hi:{est_fmt}}", fontsize=style.SMALL_PT, ha="right",
                        va="center", color=colour)
        if xlim[0] <= est <= xlim[1]:
            ax.plot([est], [i], marker=marker, ms=3.8, color=colour, mfc=colour if filled else "white",
                    mew=0.8, zorder=3)
        if r.get("note") and r.get("note_inline"):
            ax.text(r.get("note_x", xlim[1]), i - 0.02, r["note"], fontsize=style.SMALL_PT,
                    ha=r.get("note_ha", "right"), va="center", color=r.get("note_colour", style.DARK_GREY),
                    style="italic")
        for j, (cname, _w) in enumerate(cols):
            key = r.get("text", {}).get(cname)
            if not key:
                continue
            val = rec.v(key, panel=panel, row=rid, field=f"col:{cname}", fmt=None)
            if val is None:
                disp = "n/a"
            else:
                f = ",.0f" if cname in ("N", "G") else pfmt(val)
                rec.rows[-1]["format"], rec.rows[-1]["display_string"] = f, format(val, f)
                disp = format(val, f)
            ax.text(col_x0 + j * col_dx, i, disp, transform=tr, ha="left", va="center",
                    fontsize=style.SMALL_PT)
    return ys


def write_sidecars(out_dir: Path, fig_id: str, rec: Recorder, spec: dict, caption: str, audit: dict) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    rec.dump(out_dir / "plotted_values.json")
    (out_dir / "labels.json").write_text(json.dumps(rec.labels, indent=1))
    (out_dir / "caption.md").write_text(caption.strip() + "\n")
    spec = {"figure": fig_id, **spec, "production": audit,
            "sources": sorted({(r.get("artifact_id"), r.get("path")) for r in rec.rows if r.get("path")})}
    (out_dir / "figure_spec.json").write_text(json.dumps(spec, indent=1, default=str))
