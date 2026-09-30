"""F3: mechanism rows - G1 multi-team, G2a vocabulary classes, G3 classifier controls, adopter ORs."""
from __future__ import annotations

from pathlib import Path

import numpy as np

from src import style
from src.plots.common import forest, write_sidecars
from src.registry import Recorder, Registry

COLS = [("N", 0), ("G", 0), ("p", 0)]
FOLDS = (("scr", "Screen", "SCREEN", "SCREEN"),
         ("ho", "Held-out (suppl.)", "SUPPLEMENTARY/POOLED", "CONFIRMATORY"),
         ("pool", "Pooled (suppl.)", "SUPPLEMENTARY/POOLED", "SUPPLEMENTARY/POOLED"))


def _g(rid, label, fold, sty, rec_key=None, **kw):
    b = f"f3.{rid}"
    return {"id": rid, "label": label, "fold": fold, "style": sty, "est": f"{b}.est", "lo": f"{b}.lo",
            "hi": f"{b}.hi", "text": {"N": f"{b}.N", "G": f"{b}.G", "p": f"{b}.p"}, "record_key": rec_key, **kw}


def build(reg: Registry, out_root: Path) -> dict:
    rec = Recorder(reg, "F3")
    fig = style.new_figure(style.W_DOUBLE_MM, 175)
    # ---- (a) G1 multi-team vs single-paper ----
    mde = rec.s("f3.g1_mesh.mde", ".2f", panel="a", row="g1_mesh", field="mde80")
    ratio = rec.s("f3.g1_ho.ratio", ".2f", panel="a", row="g1_ho", field="interaction_ratio")
    ratio_p = rec.s("f3.g1_ho.ratio_p", ".3f", panel="a", row="g1_ho", field="interaction_p")
    rows_a = []
    for fk, name, lab, sty in FOLDS:
        rows_a += [{"label": name, "header": True},
                   _g(f"g1_{fk}", "Multi-team entries", lab, sty, f"f3.g1_{fk}.record_label"),
                   _g(f"g1s_{fk}", "Single-paper complement", lab, sty, f"f3.g1s_{fk}.record_label", hollow=True)]
    rows_a += [{"label": "REPLICATION (MeSH)", "header": True},
               _g("g1_mesh", "Multi-team entries (S1)", "REPLICATION", "REPLICATION",
                  note=f"undetected; MDE80 {mde}")]
    ax_a = fig.add_axes([0.19, 0.56, 0.16, 0.38])
    forest(ax_a, rows_a, rec, panel="a", xlim=(0.7, 2.2), cols=COLS, col_x0=1.04, col_dx=0.32)
    ax_a.set_title("a  G1: A_cont IRR/SD by entry type", loc="left", x=-1.05, fontweight="bold")
    ax_a.set_xlabel("IRR per SD (log)")
    ax_a.text(-1.05, -0.2, f"Held-out interaction ratio multi/single {ratio} (p {ratio_p})",
              transform=ax_a.transAxes, fontsize=style.SMALL_PT, color=style.DARK_GREY)
    # ---- (b) G2a NATIVE vs ADJACENT ----
    h_nat = rec.s("f3.g2_ho.holm_nat", ".3f", panel="b", row="g2nat_ho", field="holm")
    h_adj = rec.s("f3.g2_ho.holm_adj", ".3f", panel="b", row="g2adj_ho", field="holm")
    wald = rec.s("f3.g2_pool.wald_p", ".2f", panel="b", row="g2_pool", field="wald_equal_per01_p")
    rows_b = []
    for fk, name, lab, sty in FOLDS:
        rows_b += [{"label": name, "header": True},
                   _g(f"g2nat_{fk}", "NATIVE (>= 0.3)", lab, sty, f"f3.g2nat_{fk}.record_label"),
                   _g(f"g2adj_{fk}", "ADJACENT [0.05, 0.3)", lab, sty, f"f3.g2adj_{fk}.record_label", hollow=True)]
    rows_b += [{"label": "REPLICATION (MeSH, S2)", "header": True},
               _g("g2nat_mesh", "NATIVE", "REPLICATION", "REPLICATION"),
               _g("g2adj_mesh", "ADJACENT", "REPLICATION", "REPLICATION", hollow=True)]
    ax_b = fig.add_axes([0.66, 0.56, 0.16, 0.38])
    forest(ax_b, rows_b, rec, panel="b", xlim=(0.9, 1.8), cols=COLS, col_x0=1.04, col_dx=0.32)
    ax_b.set_xticks([1.0, 1.2, 1.4, 1.6])
    ax_b.set_xticklabels(["1", "1.2", "1.4", "1.6"])
    ax_b.set_title("b  G2a: partner vocabulary class", loc="left", x=-1.05, fontweight="bold")
    ax_b.set_xlabel("IRR per SD (log)")
    ax_b.text(-1.05, -0.2, f"Held-out Holm p NAT {h_nat} / ADJ {h_adj}; pooled equal-per-0.1 Wald p {wald}",
              transform=ax_b.transAxes, fontsize=style.SMALL_PT, color=style.DARK_GREY)
    # ---- (c) G3 % change in log-IRR ----
    ax_c = fig.add_axes([0.10, 0.07, 0.32, 0.30])
    groups = [("i", "G3(i+)"), ("ii", "G3(ii)"), ("comb", "G3 comb."), ("iii", "G3(iii)")]
    width = 0.26
    for j, (fk, name, lab, sty) in enumerate(FOLDS):
        colour, marker, _ = style.fold_style(sty)
        for gi, (gk, _gl) in enumerate(groups):
            x = gi + (j - 1) * width
            if gk == "iii":
                continue
            v = rec.v(f"f3.g3_{fk}.{gk}.pct", panel="c", row=f"g3_{fk}.{gk}", field="pct", fmt=".2f")
            lo = rec.v(f"f3.g3_{fk}.{gk}.lo", panel="c", row=f"g3_{fk}.{gk}", field="lo", fmt=".2f")
            hi = rec.v(f"f3.g3_{fk}.{gk}.hi", panel="c", row=f"g3_{fk}.{gk}", field="hi", fmt=".2f")
            rec.label(f"g3_{fk}.{gk}", lab, panel="c")
            if v is None:
                continue
            ax_c.bar(x, v, width * 0.9, color=colour, alpha=0.85, hatch=["", "///", "..."][j],
                     edgecolor="white", label=name if gi == 0 else None)
            ylo, yhi = -90, 70
            ax_c.plot([x, x], [max(lo, ylo), min(hi, yhi)], color="black", lw=0.7)
            if lo < ylo:
                ax_c.plot([x], [ylo], marker="v", color="black", ms=3)
            if hi > yhi:
                ax_c.plot([x], [yhi], marker="^", color="black", ms=3)
    cov = rec.s("f3.g3_pool.iii_cov", ".0%", panel="c", row="g3_pool.iii", field="venue_coverage")
    ax_c.bar(3, 0, 0.8)
    ax_c.add_patch(__import__("matplotlib.patches", fromlist=["Rectangle"]).Rectangle(
        (2.6, -35), 0.8, 65, fill=False, hatch="xxx", edgecolor=style.GREY, lw=0.5))
    ax_c.text(3, 45, f"not estimable\n(venue coverage {cov};\ndegenerate fit)", ha="center", va="center",
              fontsize=style.SMALL_PT, color=style.DARK_GREY)
    ax_c.axhline(0, color=style.DARK_GREY, lw=0.6)
    ax_c.set_ylim(-90, 70)
    ax_c.set_xticks(range(4))
    ax_c.set_xticklabels([g[1] for g in groups], fontsize=style.SMALL_PT)
    ax_c.set_ylabel("% change in A_cont log-IRR")
    ax_c.set_title("c  G3: topic-classifier controls", loc="left", x=-0.2, y=1.2, fontweight="bold")
    ax_c.legend(loc="lower right", fontsize=style.SMALL_PT, frameon=False, ncol=1)
    flags = []
    for fk, name, lab, sty in FOLDS:
        a = rec.raw(f"f3.g3_{fk}.plac_size", panel="c", row=f"g3_{fk}", field="placebo_size_PASS")
        b = rec.raw(f"f3.g3_{fk}.plac_prox", panel="c", row=f"g3_{fk}", field="placebo_prox_PASS")
        flags.append(f"{name.split(' (')[0]}: size {'PASS' if a else 'FAIL'}, prox {'PASS' if b else 'FAIL'}")
    ax_c.text(0.0, 1.02, "placebo host: " + ";\n".join(flags), transform=ax_c.transAxes,
              fontsize=style.SMALL_PT, color=style.DARK_GREY)
    # ---- (d) adopter ORs ----
    prev_c = rec.s("f3.or.prev_case", ".2f", panel="d", row="e_any", field="prev_case")
    prev_k = rec.s("f3.or.prev_ctrl", ".2f", panel="d", row="e_any", field="prev_control")
    n_pairs = rec.s("f3.or.n_pairs", ",.0f", panel="d", row="frame", field="n_adopter_pairs")
    pct = rec.s("f3.or.pct_excl", ".0f", panel="d", row="frame", field="pct_excluded")
    n_str = rec.s("f3.or.n_strata", ",.0f", panel="d", row="frame", field="n_strata")

    def o(k, label, **kw):
        return {"id": k, "label": label, "fold": "MECHANISM", "style": "MECHANISM", "est": f"f3.or.{k}.est",
                "lo": f"f3.or.{k}.lo", "hi": f"f3.or.{k}.hi", **kw}
    rows_d = [{"label": "Partner exposure (m2)", "header": True},
              o("e_any", f"Any partner (prev. {prev_c} vs {prev_k})"),
              o("e_neg", "Negative-control authors", hollow=True),
              o("e_plac", "Placebo-host partners", hollow=True),
              {"label": "Vocabulary class (m_voc)", "header": True},
              o("e_for", "FOREIGN partners"), o("e_adj", "ADJACENT partners"), o("e_nat", "NATIVE partners"),
              {"label": "Origin (m_comp)", "header": True},
              o("e_comp", "Origin companions"), o("e_noncomp", "Non-companions"),
              {"label": "Interaction (m_int)", "header": True},
              o("e_int", "E_any x A_cont (z)")]
    ax_d = fig.add_axes([0.75, 0.07, 0.22, 0.30])
    forest(ax_d, rows_d, rec, panel="d", xlim=(0.4, 5.0), est_fmt=".2f")
    ax_d.set_xticks(style.OR_TICKS)
    ax_d.set_xticklabels([f"{t:g}" for t in style.OR_TICKS])
    ax_d.set_xlabel("Conditional-logit odds ratio (log)")
    ax_d.set_title("d  MECHANISM (screen only): adopter ORs", loc="left", x=-1.05, y=1.12, fontweight="bold")
    ax_d.text(-1.05, 1.04, "consistent with absorptive capacity OR topical proximity", transform=ax_d.transAxes,
              fontsize=style.SMALL_PT, style="italic", color=style.DARK_GREY)
    out = out_root / "F3"
    audit = style.save(fig, out, "F3_mechanism")
    caption = (
        "F3. Mechanism evidence behind the grafting effect: (a) G1 multi-team versus single-paper entries, (b) G2a "
        "NATIVE versus ADJACENT partner shares, (c) G3 % change in the A_cont log-IRR after topic-classifier "
        "controls, and (d) screen-only adopter conditional-logit odds ratios. Panels a-b show PPML IRR per SD with "
        "95% CRV1 Wald CIs (concept-clustered; N entries and G clusters per row; held-out and pooled G rows were not "
        "in the frozen spec and are labelled SUPPLEMENTARY); panel c shows 95% concept-bootstrap CIs (B=499) and "
        f"panel d 95% concept-bootstrap CIs (B=1,000) over n = {n_str} matched strata. In d, {pct}% of {n_pairs} "
        "adopter pairs are excluded as career-new and exposure is corpus-only, so OR "
        f"{rec.s('f3.or.e_any.est', '.2f', panel='d', row='e_any', field='caption_or')} (prevalence {prev_c} vs "
        f"{prev_k}) is not a 'times more likely' statement. Sources: "
        "3_invention_loop/iter_4/gen_art/gen_art_evaluation_2/results/g_*_rows.csv (art_WZ8fbLn79nCq), "
        "3_invention_loop/iter_4/gen_art/gen_art_experiment_9/results/g4_models.json (art_XGdzjWgi-a88), "
        "3_invention_loop/iter_4/gen_art/gen_art_evaluation_5/results/enrichment.json (art_FZ2OCJwV6xHs).")
    write_sidecars(out, "F3", rec, {"width_mm": style.W_DOUBLE_MM, "panels": list("abcd"),
                                    "ci_type": "CRV1 Wald (a,b); concept bootstrap (c,d)"}, caption, audit)
    return audit


_ = np  # numpy kept for downstream extensions of the bar layout
