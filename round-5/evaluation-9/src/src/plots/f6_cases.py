"""F6: four frozen typology cases (two k=2 medoids + nearest non-medoid of a different origin group each).
F6b (supplementary): existing ego / alluvial renders from exp_8, embedded unchanged (sha256 checked)."""
from __future__ import annotations

import textwrap
from pathlib import Path

import matplotlib.image as mpimg
from matplotlib.patches import Rectangle

from src import style
from src.plots.common import write_sidecars
from src.registry import Recorder, Registry, esc

META = {"other", "_other", "n_papers_3y"}
ROLES = ["BRIDGE", "OTHER", "STAYER", "MIGRANT", "FOUNDER", "CORE_GROWING"]
N_NAMED = 4


def _case_panels(fig, rec: Recorder, reg: Registry, col: int, cid: str, x0: float, w: float) -> None:
    d = reg.structure("cases")[cid]
    j = lambda p: reg.dyn("cases", {"json_pointer": f"/{esc(cid)}/{p}"})  # noqa: E731
    phrase = rec.raw(j("phrase"), panel=f"{col}", row=cid, field="phrase")
    rule = rec.raw(j("rule"), panel=f"{col}", row=cid, field="rule")
    cluster = rec.raw(j("cluster"), panel=f"{col}", row=cid, field="cluster")
    kind = cluster.split(" (")[0].split(" ")[0].upper()
    head = f"{'abcd'[col]}  " + "\n    ".join(textwrap.wrap(phrase, 22)) + f"\n    {kind}; " + (
        "medoid" if rule == "medoid" else "nearest other")
    fig.text(x0, 0.975, head, fontsize=style.TICK_PT, fontweight="bold", va="top")
    # ---- row i: subfield shares at the case's time points ----
    ax = fig.add_axes([x0 + 0.02, 0.69, w - 0.03, 0.2])
    tps = [str(t) for t in d["time_points"]]
    names = {}
    for tp in tps:
        for s, v in d["subfield_shares"][tp].items():
            if s not in META:
                names[s] = max(names.get(s, 0.0), v)
    named = [s for s, _ in sorted(names.items(), key=lambda kv: -kv[1])][:N_NAMED]
    for ti, tp in enumerate(tps):
        bottom = 0.0
        segs = [(s, i) for i, s in enumerate(named)] + [(s, None) for s in d["subfield_shares"][tp]
                                                       if s not in META and s not in named] + \
               [(s, None) for s in ("other", "_other") if s in d["subfield_shares"][tp]]
        for s, ci in segs:
            if s not in d["subfield_shares"][tp]:
                continue
            v = rec.v(reg.dyn("cases", {"json_pointer": f"/{esc(cid)}/subfield_shares/{tp}/{esc(s)}"}),
                      panel=f"{col}.i", row=f"{cid}.{tp}", field=f"share:{s}", fmt=".3f")
            colour = style.SHARE_COLOURS[ci] if ci is not None else "#DDDDDD"
            ax.bar(ti, v, 0.7, bottom=bottom, color=colour, hatch=style.SHARE_HATCHES[ci] if ci is not None else "",
                   edgecolor="white", lw=0.3)
            bottom += v
        n = rec.v(reg.dyn("cases", {"json_pointer": f"/{esc(cid)}/subfield_shares/{tp}/n_papers_3y"}),
                  panel=f"{col}.i", row=f"{cid}.{tp}", field="n_papers_3y", fmt=".0f")
        ax.text(ti, 1.02, f"n={n:.0f}", ha="center", fontsize=style.SMALL_PT)
    rec.label(f"{cid}.shares", "DESCRIPTIVE", panel=f"{col}.i")
    ax.set_xticks(range(len(tps)))
    ax.set_xticklabels(tps)
    ax.set_ylim(0, 1.1)
    ax.set_yticks([0, 0.5, 1.0])
    if col == 0:
        ax.set_ylabel("Subfield share\n(3-year window)")
    else:
        ax.set_yticklabels([])
    for i, s in enumerate(named):
        ax.add_patch(Rectangle((0, 0), 0, 0, color=style.SHARE_COLOURS[i], label=textwrap.shorten(s, 24)))
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.12), fontsize=style.SMALL_PT, frameon=False,
              handlelength=0.8, ncol=1)
    # ---- row ii: role path ----
    ax2 = fig.add_axes([x0 + 0.02, 0.495, w - 0.03, 0.035])
    for k, step in enumerate(d["role_path"]):
        yr = rec.v(reg.dyn("cases", {"json_pointer": f"/{esc(cid)}/role_path/{k}/year"}), panel=f"{col}.ii",
                   row=f"{cid}.role.{k}", field="year", fmt=".0f")
        role = rec.raw(reg.dyn("cases", {"json_pointer": f"/{esc(cid)}/role_path/{k}/role"}), panel=f"{col}.ii",
                       row=f"{cid}.role.{k}", field="role")
        robust = rec.raw(reg.dyn("cases", {"json_pointer": f"/{esc(cid)}/role_path/{k}/robust"}),
                         panel=f"{col}.ii", row=f"{cid}.role.{k}", field="robust")
        ax2.add_patch(Rectangle((yr - 0.5, 0), 1, 1, facecolor=style.ROLE_COLOURS.get(role, "#DDDDDD"),
                                edgecolor="white", lw=0.3, hatch="" if robust else "////"))
    rec.label(f"{cid}.roles", "DESCRIPTIVE", panel=f"{col}.ii")
    ax2.set_xlim(2003.5, 2024.5)
    ax2.set_ylim(0, 1)
    ax2.set_yticks([])
    ax2.set_xticks([2005, 2015, 2024])
    ax2.tick_params(axis="x", labelsize=style.SMALL_PT)
    if col == 0:
        ax2.set_ylabel("Role", rotation=0, ha="right", va="center")
    # ---- row iii: host entries, A_cont vs entry year ----
    ax3 = fig.add_axes([x0 + 0.02, 0.17, w - 0.03, 0.24])
    rows = [r for r in reg.structure("case_entries") if r["concept_id"] == cid]
    best = None
    for r in rows:
        flt = {"concept_id": cid, "d": r["d"], "e": r["e"]}
        a = rec.v(reg.dyn("case_entries", {"csv_row": {"filters": flt, "column": "A_cont"}}), panel=f"{col}.iii",
                  row=f"{cid}.{r['d']}.{r['e']}", field="A_cont", fmt=".3f")
        e = rec.v(reg.dyn("case_entries", {"csv_row": {"filters": flt, "column": "e"}}), panel=f"{col}.iii",
                  row=f"{cid}.{r['d']}.{r['e']}", field="e", fmt=".0f")
        est = rec.v(reg.dyn("case_entries", {"csv_row": {"filters": flt, "column": "EST_bin"}}),
                    panel=f"{col}.iii", row=f"{cid}.{r['d']}.{r['e']}", field="EST_bin", fmt=".0f")
        cop = rec.raw(reg.dyn("case_entries", {"csv_row": {"filters": flt, "column": "in_coprimary_sample"}}),
                      panel=f"{col}.iii", row=f"{cid}.{r['d']}.{r['e']}", field="in_coprimary_sample")
        if a is None or e is None:
            continue  # entry without an A_cont value in the source (logged as SOURCE_MISSING)
        rooted = est == 1
        colour = style.OKABE_ITO["vermillion"] if rooted else style.DARK_GREY
        ax3.plot([a], [e], marker="o" if cop == "True" else "^", ms=4, color=colour,
                 mfc=colour if rooted else "white", mew=0.8, ls="none")
        if rooted and cop == "True" and (best is None or a > best[0]):
            best = (a, e)
    rec.label(f"{cid}.entries", "DESCRIPTIVE", panel=f"{col}.iii")
    delta_key = {"wireless backhaul": "f6.delta_wireless",
                 "einstein podolsky rosen steering": "f6.delta_epr"}.get(phrase)
    if best is None:
        ax3.text(0.5, 0.92, "no rooted entry", transform=ax3.transAxes, ha="center", fontsize=style.SMALL_PT,
                 style="italic", color=style.OKABE_ITO["vermillion"])
    elif delta_key:
        dv = rec.s(delta_key, ".3f", panel=f"{col}.iii", row=cid, field="rooted_minus_unrooted_A_cont")
        ax3.annotate(f"rooted minus mean\nunrooted A_cont +{dv}", xy=best, xytext=(0.95, 0.9), textcoords="axes fraction",
                     ha="right", va="top", fontsize=style.SMALL_PT,
                     arrowprops={"arrowstyle": "-", "lw": 0.5, "color": style.DARK_GREY})
    else:
        ax3.text(0.5, 0.92, "rooted; no unrooted co-primary\nentry to contrast", transform=ax3.transAxes,
                 ha="center", va="top", fontsize=style.SMALL_PT, style="italic", color=style.DARK_GREY)
    ax3.set_xlim(-0.005, 0.16)
    ax3.set_xticks([0, 0.05, 0.1, 0.15])
    ax3.set_xticklabels(["0", ".05", ".10", ".15"])
    ax3.set_ylim(2004.5, 2024.5)
    ax3.set_yticks([2005, 2010, 2015, 2020])
    ax3.set_xlabel("A_cont at entry")
    ax3.tick_params(labelsize=style.SMALL_PT)
    if col == 0:
        ax3.set_ylabel("Entry year")
    else:
        ax3.set_yticklabels([])
    # ---- row iv: ego position text ----
    lines = []
    for tp in tps:
        P = rec.s(reg.dyn("cases", {"json_pointer": f"/{esc(cid)}/ego_position/{tp}/P"}), ".2f",
                  panel=f"{col}.iv", row=f"{cid}.{tp}", field="P")
        b = rec.s(reg.dyn("cases", {"json_pointer": f"/{esc(cid)}/ego_position/{tp}/betweenness_pct"}), ".0f",
                  panel=f"{col}.iv", row=f"{cid}.{tp}", field="betweenness_pct")
        lines.append(f"{tp}: P {P}, betw. pct {b}")
    fig.text(x0 + 0.02, 0.085, "\n".join(lines), fontsize=style.SMALL_PT, va="top", color=style.DARK_GREY)


def build(reg: Registry, out_root: Path) -> dict:
    rec = Recorder(reg, "F6")
    fig = style.new_figure(style.W_DOUBLE_MM, 200)
    cids = list(reg.structure("cases").keys())
    w = 0.915 / len(cids)
    for col, cid in enumerate(cids):
        _case_panels(fig, rec, reg, col, cid, 0.075 + col * w, w)
    # role legend
    for i, r in enumerate(ROLES[:4]):
        fig.patches.append(Rectangle((0.095 + i * 0.12, 0.555), 0.012, 0.008, transform=fig.transFigure,
                                     facecolor=style.ROLE_COLOURS[r], edgecolor=style.DARK_GREY, lw=0.3))
        fig.text(0.11 + i * 0.12, 0.559, r, fontsize=style.SMALL_PT, va="center")
    fig.text(0.60, 0.559, "hatched = non-robust year (5-seed Leiden)", fontsize=style.SMALL_PT, va="center")
    fig.text(0.095, 0.44, "Filled red = rooted (EST_bin = 1); hollow = not rooted; circle = co-primary sample, "
             "triangle = outside it (< 5 partners)", fontsize=style.SMALL_PT)
    out = out_root / "F6"
    audit = style.save(fig, out, "F6_cases")
    caption = (
        "F6. Four cases chosen by the frozen k=2 typology (two medoids plus, for each, the nearest non-medoid with a "
        "different origin group), not by fame: row i subfield shares at F+1, onset and 2022 (n = papers in the "
        "3-year window), row ii the yearly community role, row iii every host entry (A_cont against entry year; "
        "rooted when EST_bin = 1), row iv Guimera-Amaral P and betweenness percentile. The panels are descriptive, "
        "so no CIs are drawn. Sources: 3_invention_loop/iter_4/gen_art/gen_art_evaluation_4/results/"
        "cases_rooting.json and case_entries.csv (art_mu0h0npvNX_u).")
    write_sidecars(out, "F6", rec, {"width_mm": style.W_DOUBLE_MM, "cases": cids, "ci_type": "none (descriptive)"},
                   caption, audit)
    audit_b = build_f6b(reg, out_root, cids)
    return {**audit, "F6b": audit_b}


def build_f6b(reg: Registry, out_root: Path, cids: list[str]) -> dict:
    rec = Recorder(reg, "F6b")
    fig = style.new_figure(style.W_DOUBLE_MM, 225)
    for i, cid in enumerate(cids):
        for jj, kind in enumerate(("ego", "alluvial")):
            ax = fig.add_axes([0.01 + jj * 0.5, 0.75 - i * 0.245, 0.48, 0.215])
            p = rec.image(f"img_{cid}_{kind}", panel=f"{cid}.{kind}", row=cid)
            rec.label(f"{cid}.{kind}", "DESCRIPTIVE", panel=f"{cid}.{kind}")
            ax.axis("off")
            if p is None:
                ax.text(0.5, 0.5, "source missing", ha="center")
                continue
            ax.imshow(mpimg.imread(p), interpolation="lanczos")
            ax.set_title(f"{'abcdefgh'[2 * i + jj]}  {reg.files[f'img_{cid}_{kind}']['path'].split('/')[-1]}",
                         fontsize=style.SMALL_PT, loc="left")
    out = out_root / "F6b"
    audit = style.save(fig, out, "F6b_case_networks")
    caption = (
        "F6b (supplementary). Ego networks and alluvial community paths of the four F6 cases, embedded unchanged "
        "from exp_8 (raster inside a vector page; the sha256 of every embedded PNG is checked against its source). "
        "n = 4 cases; descriptive, no CIs. Source: 3_invention_loop/iter_3/gen_art/gen_art_experiment_8/figures/"
        "case_c_*_{ego,alluvial}.png (art_QKsLguxnGFQT).")
    write_sidecars(out, "F6b", rec, {"width_mm": style.W_DOUBLE_MM, "ci_type": "none"}, caption, audit)
    return audit
