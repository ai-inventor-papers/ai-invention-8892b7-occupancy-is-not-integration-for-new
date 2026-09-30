"""F1: methodology, population flow and decision path (dead branches greyed), driven by flow_spec.json.

Node text templates contain placeholders {registry_key|format}; every number is filled from the registry.
"""
from __future__ import annotations

import csv
import json
import re
import textwrap
from pathlib import Path

from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

from src import style
from src.plots.common import write_sidecars
from src.registry import Recorder, Registry

STATUS_STYLE = {  # face, edge, text colour, line style
    "LIVE": ("#FFFFFF", style.DARK_GREY, "black", "-"),
    "CONFIRMED": ("#E8F1F8", style.OKABE_ITO["blue"], "black", "-"),
    "REPLICATED": ("#E6F4EF", style.OKABE_ITO["green"], "black", "-"),
    "MECHANISM": ("#FBF1DC", style.OKABE_ITO["orange"], "black", "-"),
    "DEAD": ("#F2F2F2", style.GREY, style.DARK_GREY, "--"),
    "NULL": ("#F2F2F2", style.GREY, style.DARK_GREY, "--"),
    "DESCRIPTIVE": ("#FFFFFF", style.GREY, "black", "-"),
}

# id, band, x, y, w, h (figure fractions of the main canvas), status, template
NODES = [
    ("frame", 1, 0.02, 0.855, 0.2, 0.075, "LIVE",
     "OpenAlex concept frame: {f1.frame_total|,.0f} candidates ({f1.frame_main|,.0f} emerging + "
     "{f1.frame_ref|,.0f} reference)"),
    ("works", 1, 0.25, 0.855, 0.16, 0.075, "LIVE", "Hydrated corpus: {f1.n_works|,.0f} works"),
    ("link", 1, 0.44, 0.855, 0.2, 0.075, "LIVE",
     "Classifier / merger / Wikidata linker: {f1.unlinked|,.0f} of {f1.frame_main|,.0f} emerging concepts "
     "unlinked (kept as new)"),
    ("mesh", 1, 0.02, 0.765, 0.2, 0.06, "LIVE", "MeSH biomedical pool: {f1.mesh_concepts|,.0f} concepts (never "
     "screened for D2)"),
    ("folds", 1, 0.25, 0.765, 0.39, 0.06, "LIVE",
     "sha1 fold rule: screen {f1.screen_concepts|,.0f} / sealed held-out {f1.heldout_concepts|,.0f} MAIN concepts"),
    ("cooc", 2, 0.02, 0.655, 0.3, 0.075, "LIVE",
     "View 1: yearly concept co-word snapshots 2000-2024, Leiden communities + alluvial paths (2023: "
     "{f1.snap_nodes_2023|,.0f} nodes, {f1.snap_kept_edges_2023|,.0f} kept edges)"),
    ("bip", 2, 0.34, 0.655, 0.3, 0.075, "LIVE",
     "View 2: concept-subfield bipartite network: host entries, partner host share A_cont, co-transfer CT"),
    ("viab", 3, 0.02, 0.525, 0.2, 0.075, "DEAD", "Source-sink viability hypothesis (H1/H2)"),
    ("gateA", 3, 0.25, 0.525, 0.18, 0.075, "DEAD",
     "Gate A FAIL: {f1.gateA_share|.1%} of host edges traced (>50% needed); Gate B: {f1.gateB_episodes|.0f} "
     "labelled episodes"),
    ("graft", 3, 0.46, 0.525, 0.18, 0.075, "LIVE", "Pre-declared graft fallback: host-entry grafting test (D2)"),
    ("d2s", 3, 0.02, 0.43, 0.2, 0.07, "LIVE",
     "D2 SCREEN: co-primary FE {f1.d2_scr_N|,.0f} entries, {f1.d2_scr_G|,.0f} concept clusters; GRAFTING"),
    ("d2h", 3, 0.25, 0.43, 0.18, 0.07, "CONFIRMED",
     "Sealed held-out, opened once: {f1.d2_ho_N|,.0f} / {f1.d2_ho_G|,.0f}; CONFIRMED"),
    ("d2m", 3, 0.46, 0.43, 0.18, 0.07, "REPLICATED",
     "MeSH one-look replication: {f1.mesh_N|,.0f} / {f1.mesh_G|,.0f}; {f1.mesh_verdict} (biomed->biomed)"),
    ("adopt", 3, 0.46, 0.335, 0.18, 0.06, "MECHANISM",
     "Adopter test (screen only): partner exposure OR {f1.adopter_or|.2f}; MECHANISM"),
    ("d1", 3, 0.02, 0.335, 0.2, 0.06, "NULL",
     "D1 openness -> breadth: {f1.d1_verdict} (Holm p {f1.d1_holm|.3f})"),
    ("ct", 3, 0.25, 0.335, 0.18, 0.06, "NULL",
     "Co-transfer CT: null (Holm p screen {f1.ct_holm|.2f}, MeSH {f1.ct_mesh_holm|.3f})"),
    ("d3", 3, 0.02, 0.25, 0.2, 0.055, "NULL", "D3 anchoring-typology link: {f1.d3_decision}"),
    ("r1", 3, 0.25, 0.25, 0.18, 0.055, "DEAD", "RQ1 structural precursors: {f1.r1_status} on held-out"),
    ("typ", 4, 0.02, 0.125, 0.15, 0.065, "DESCRIPTIVE",
     "Typology k = {f1.typ_k|.0f} (min Jaccard {f1.typ_jacc|.3f})"),
    ("roles", 4, 0.185, 0.125, 0.15, 0.065, "DESCRIPTIVE", "Community roles: BRIDGE share {f1.roles_bridge|.2f}"),
    ("ll", 4, 0.35, 0.125, 0.14, 0.065, "DESCRIPTIVE",
     "Lead-lag: expansion first in {f1.ll_share|.0%} of {f1.ll_n|.0f} (conditional)"),
    ("cases", 4, 0.505, 0.125, 0.135, 0.065, "DESCRIPTIVE", "4 typology cases (medoid rule; F6)"),
]
EDGES = [("frame", "works"), ("works", "link"), ("frame", "mesh"), ("link", "folds"), ("folds", "cooc"),
         ("folds", "bip"), ("cooc", "viab"), ("viab", "gateA"), ("gateA", "graft"), ("bip", "graft"),
         ("graft", "d2m"), ("graft", "d2s"), ("d2s", "d2h"), ("d2h", "d2m"), ("d2m", "adopt"), ("d2s", "d1"),
         ("d2s", "ct")]
BANDS = [(1, 0.75, 0.95, "1  DATA AND GROUNDING"), (2, 0.64, 0.745, "2  NETWORK VIEWS"),
         (3, 0.235, 0.63, "3  DECISION PATH"),
         (4, 0.11, 0.225, "4  RQ2 DESCRIPTIVE")]
SIDE = [("E_up onset", "f1.def.E_up", "art_htO_gJuUn6Pr"), ("A_cont", "f1.def.A_cont", "art_2Cd2JJypeGuA"),
        ("CT companions", "f1.def.CT", "art_2Cd2JJypeGuA"), ("Y_strict", "f1.def.Y_strict", "art_2Cd2JJypeGuA"),
        ("EST_bin", "f1.def.EST_bin", "art_2Cd2JJypeGuA"),
        ("Persist. closure", "f1.def.closure_persist", "art_htO_gJuUn6Pr"),
        ("Folds", "f1.def.folds", "art_2Cd2JJypeGuA")]
PH = re.compile(r"\{([a-zA-Z0-9_.]+)(?:\|([^}]+))?\}")


def fill(template: str, rec: Recorder, node: str) -> tuple[str, list[str]]:
    keys = []

    def sub(m):
        key, fmt = m.group(1), m.group(2)
        keys.append(key)
        val = rec.v(key, panel="flow", row=node, field=key, fmt=fmt)
        if val is None:
            return "n/a - source missing"
        return format(val, fmt) if fmt else str(val)
    return PH.sub(sub, template), keys


def build(reg: Registry, out_root: Path) -> dict:
    rec = Recorder(reg, "F1")
    out = out_root / "F1"
    out.mkdir(parents=True, exist_ok=True)
    spec = {"nodes": [{"id": n[0], "band": n[1], "xywh": list(n[2:6]), "status": n[6], "text_template": n[7],
                       "number_keys": PH.findall(n[7])} for n in NODES],
            "edges": [{"from": a, "to": b, "style": "arrow"} for a, b in EDGES],
            "side_panel": [{"row": r, "definition_key": k, "artifact": a} for r, k, a in SIDE]}
    (out / "flow_spec.json").write_text(json.dumps(spec, indent=1))
    fig = style.new_figure(style.W_DOUBLE_MM, 220)
    for band, y0, y1, title in BANDS:
        fig.patches.append(FancyBboxPatch((0.03, y0), 0.645, y1 - y0, boxstyle="round,pad=0.004",
                                          transform=fig.transFigure, facecolor="#FAFAFA", edgecolor="#DDDDDD",
                                          lw=0.5, zorder=0))
        fig.text(0.017, (y0 + y1) / 2, title, fontsize=style.SMALL_PT, fontweight="bold", va="center",
                 ha="center", rotation=90)
    boxes, flow_rows = {}, []
    for nid, band, x, y, w, h, status, tmpl in NODES:
        x += 0.02
        text, keys = fill(tmpl, rec, nid)
        rec.label(nid, "DESCRIPTIVE", panel="flow")
        face, edge, tcol, ls = STATUS_STYLE[status]
        fig.patches.append(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.003", transform=fig.transFigure,
                                          facecolor=face, edgecolor=edge, lw=0.8, ls=ls, zorder=1))
        chars = max(int(w * 174 / 1.25), 10)
        wrapped = "\n".join(textwrap.wrap(text, chars))
        fig.text(x + w / 2, y + h / 2 + (0.006 if status in ("DEAD", "NULL") else 0), wrapped, ha="center",
                 va="center", fontsize=style.SMALL_PT, color=tcol, zorder=2)
        if status in ("DEAD", "NULL"):
            fig.text(x + w - 0.004, y + 0.004, status, ha="right", va="bottom", fontsize=style.SMALL_PT,
                     fontweight="bold", color=style.OKABE_ITO["vermillion"], zorder=2)
        boxes[nid] = (x, y, w, h)
        flow_rows.append({"id": nid, "band": band, "status": status, "text": text, "keys": ";".join(keys)})
    for a, b in EDGES:
        xa, ya, wa, ha = boxes[a]
        xb, yb, wb, hb = boxes[b]
        lo_x, hi_x = max(xa, xb), min(xa + wa, xb + wb)
        if abs(ya - yb) < 1e-9:
            p0, p1 = (xa + wa, ya + ha / 2), (xb, yb + hb / 2) if xb > xa else (xb + wb, yb + hb / 2)
            if xb < xa:
                p0 = (xa, ya + ha / 2)
        elif hi_x - lo_x > 0.02:
            xm = (lo_x + hi_x) / 2
            p0, p1 = (xm, ya), (xm, yb + hb)
        else:
            p0, p1 = (xa + wa / 2, ya), (xb + wb / 2, yb + hb)
        dead = STATUS_STYLE[dict((n[0], n[6]) for n in NODES)[b]][3] == "--"
        fig.patches.append(FancyArrowPatch(p0, p1, transform=fig.transFigure, arrowstyle="-|>", mutation_scale=6,
                                           lw=0.6, color=style.GREY if dead else style.DARK_GREY,
                                           ls="--" if dead else "-", zorder=1.5))
    # side panel: final design as executed
    fig.text(0.69, 0.95, "Final design as executed", fontsize=style.TICK_PT, fontweight="bold", va="top")
    y = 0.925
    for row, key, art in SIDE:
        val = rec.v(key, panel="side", row=row, field="definition", fmt=None)
        rec.label(row, "DESCRIPTIVE", panel="side")
        txt = str(val) if val is not None else "n/a - source missing (no definition string in the source files)"
        body = "\n".join(textwrap.wrap(txt, 40))
        t = fig.text(0.69, y, f"{row}  [{art}]", fontsize=style.SMALL_PT, fontweight="bold", va="top")
        t2 = fig.text(0.69, y - 0.013, body, fontsize=style.SMALL_PT, va="top", color=style.DARK_GREY)
        y -= 0.02 + 0.0105 * body.count("\n") + 0.018
        _ = (t, t2)
    # legend of statuses
    ly = 0.07
    for i, st in enumerate(["LIVE", "CONFIRMED", "REPLICATED", "MECHANISM", "DEAD"]):
        face, edge, _, ls = STATUS_STYLE[st]
        fig.patches.append(FancyBboxPatch((0.04 + i * 0.13, ly), 0.02, 0.012, boxstyle="round,pad=0.002",
                                          transform=fig.transFigure, facecolor=face, edgecolor=edge, lw=0.8, ls=ls))
        fig.text(0.065 + i * 0.13, ly + 0.006, st + (" / NULL (failed gate or null test; kept, not dropped)" if st == "DEAD" else ""), fontsize=style.SMALL_PT,
                 va="center")
    with (out / "flow_nodes.csv").open("w", newline="") as fh:
        wr = csv.DictWriter(fh, fieldnames=["id", "band", "status", "text", "keys"])
        wr.writeheader()
        wr.writerows(flow_rows)
    audit = style.save(fig, out, "F1_method_flow")
    caption = (
        f"F1. Methodology, population flow and decision path: grounding (n = "
        f"{rec.s('f1.frame_total', ',.0f', panel='caption', row='caption', field='n_frame')} candidate concepts, "
        f"{rec.s('f1.n_works', ',.0f', panel='caption', row='caption', field='n_works')} works), the two network "
        "views, the pre-registered decision path with failed and null branches kept in grey, and the RQ2 descriptive "
        "layer. No CIs are drawn here (counts and verdicts only; CIs are in F2-F5), and every number is read through "
        "the source registry (figures/F1/flow_nodes.csv lists each node with its keys). Sources: "
        "3_invention_loop/iter_3/gen_art/gen_art_experiment_7/results/d2_summary.json (art_2Cd2JJypeGuA), "
        "3_invention_loop/iter_4/gen_art/gen_art_evaluation_2/results/heldout_post.json (art_WZ8fbLn79nCq) and "
        "the other files listed in figure_spec.json.")
    write_sidecars(out, "F1", rec, {"width_mm": style.W_DOUBLE_MM, "ci_type": "none (counts and verdicts)",
                                    "flow_spec": "figures/F1/flow_spec.json"}, caption, audit)
    return audit
