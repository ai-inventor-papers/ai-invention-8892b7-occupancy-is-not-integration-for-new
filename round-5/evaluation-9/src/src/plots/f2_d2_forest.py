"""F2: D2 host-entry forest (A_cont and CT IRR per SD) across screen, sealed held-out, MeSH, IVW, placebos."""
from __future__ import annotations

from pathlib import Path

from matplotlib.gridspec import GridSpec

from src import style
from src.plots.common import forest, write_sidecars
from src.registry import Recorder, Registry

COLS = [("N", 0), ("G", 0), ("p", 0), ("Holm", 0), ("wild", 0)]
XLIM = (0.5, 2.2)


def _row(rid, label, fold, sty, term="A", holm=True, wild=True, **kw):
    b = f"f2.{rid}.{term}"
    text = {"N": f"{b}.N", "G": f"{b}.G", "p": f"{b}.p"}
    if holm:
        text["Holm"] = f"{b}.holm"
    if wild:
        text["wild"] = f"{b}.pw"
    return {"id": f"{rid}.{term}", "label": label, "fold": fold, "style": sty, "est": f"{b}.est",
            "lo": f"{b}.lo", "hi": f"{b}.hi", "text": text, **kw}


def build(reg: Registry, out_root: Path) -> dict:
    rec = Recorder(reg, "F2")
    kill = rec.raw("f2.ho.kill_dead", panel="a", row="ho_co.A", field="kill_rule_triggered")
    prim_label = rec.raw("f2.ho.primary_label", panel="a", row="ho_pri.A", field="primary_label")
    mde = rec.s("f2.ho.mde_co", ".2f", panel="a", row="ho_co.A", field="mde80")
    mesh_mde_pri = rec.s("f2.mesh_pri.mde", ".2f", panel="a", row="mesh_pri.A", field="mde80")
    i2 = rec.s("f2.ivw.A.I2", ".0f", panel="a", row="ivw.A", field="I2")
    p_diff = rec.s("f2.ivw.A.p_diff", ".2f", panel="a", row="ivw.A", field="p_main_vs_mesh")
    ret = rec.s("f2.retained_share_pct", ".0f", panel="a", row="scr_pri.A", field="retained_share_pct")
    main_irr = rec.s("f2.scr_co.A.est", ".2f", panel="a", row="ivw.A", field="main_in_ivw")
    kill_txt = "kill rule (CI incl. 1 or sign flip): " + ("TRIGGERED" if kill else "NOT triggered")

    def rows_for(term):
        rows = [{"label": "SCREEN (exp_7)", "header": True},
                _row("scr_co", "Co-primary FE: concept + e + host", "SCREEN", "SCREEN", term,
                     record_key="f2.scr_co.A.record_label" if term == "A" else None),
                _row("scr_pri", "Primary FE: concept x e + host x e", "SCREEN", "SCREEN", term,
                     note="underpowered (fallback 3)", hollow=True,
                     record_key="f2.scr_pri.A.record_label" if term == "A" else None),
                {"label": "CONFIRMATORY (sealed held-out)", "header": True},
                _row("ho_co", "Co-primary FE", "CONFIRMATORY", "CONFIRMATORY", term, holm=True,
                     wild=(term == "A"), record_key=f"f2.ho_co.{term}.record_label",
                     note=(kill_txt + f"; MDE80 {mde}") if term == "A" else None),
                _row("ho_pri", "Primary FE", "CONFIRMATORY", "CONFIRMATORY", term, wild=(term == "A"),
                     hollow=True, record_key=f"f2.ho_pri.{term}.record_label",
                     note=f"{prim_label}, as pre-declared" if term == "A" else None),
                {"label": "REPLICATION (MeSH, biomed->biomed)", "header": True},
                _row("mesh_co", "Co-primary FE (G4-decisive)", "REPLICATION", "REPLICATION", term),
                _row("mesh_pri", "Primary FE", "REPLICATION", "REPLICATION", term, hollow=True,
                     note=f"MDE80 {mesh_mde_pri}" if term == "A" else None)]
        if term == "A":
            rows += [{"label": "SUPPLEMENTARY/POOLED", "header": True},
                     {"id": "ivw.A", "label": f"IVW main {main_irr} + MeSH (I² = {i2}; p diff {p_diff})",
                      "fold": "SUPPLEMENTARY/POOLED", "style": "SUPPLEMENTARY/POOLED", "est": "f2.ivw.A.est",
                      "lo": "f2.ivw.A.lo", "hi": "f2.ivw.A.hi"},
                     {"label": "PLACEBO HOST (A from placebo host d')", "header": True},
                     {"id": "plac_scr.A", "label": "Screen, size-matched (100 draws)", "fold": "SCREEN",
                      "style": "PLACEBO", "est": "f2.plac_scr.A.est", "lo": "f2.plac_scr.A.lo",
                      "hi": "f2.plac_scr.A.hi", "text": {"N": "f2.plac_scr.A.N"}, "ls": ":"},
                     {"id": "plac_ho.A", "label": "Held-out, size-matched (100 draws)", "fold": "SUPPLEMENTARY/POOLED",
                      "style": "PLACEBO", "est": "f2.plac_ho.A.est", "lo": "f2.plac_ho.A.lo",
                      "hi": "f2.plac_ho.A.hi", "text": {"N": "f2.plac_ho.A.N"}, "ls": ":"},
                     {"id": "plac_pool.A", "label": "Pooled, size-matched (100 draws)", "fold": "SUPPLEMENTARY/POOLED",
                      "style": "PLACEBO", "est": "f2.plac_pool.A.est", "lo": "f2.plac_pool.A.lo",
                      "hi": "f2.plac_pool.A.hi", "text": {"N": "f2.plac_pool.A.N"}, "ls": ":"},
                     {"id": "plac_mesh.A", "label": "MeSH placebo host (CRV1)", "fold": "REPLICATION",
                      "style": "PLACEBO", "est": "f2.plac_mesh.A.est", "lo": "f2.plac_mesh.A.lo",
                      "hi": "f2.plac_mesh.A.hi",
                      "text": {"N": "f2.plac_mesh.A.N", "G": "f2.plac_mesh.A.G", "p": "f2.plac_mesh.A.p"}},
                     {"label": "DESCRIPTIVE", "header": True},
                     {"id": "phys.A", "label": "Main, Physics/Astro stratum (point only)", "fold": "DESCRIPTIVE",
                      "style": "DEAD/NULL", "est": "f2.phys.A.est", "note": "no CI in source"}]
        return rows

    rows_a, rows_b = rows_for("A"), rows_for("CT")
    fig = style.new_figure(style.W_DOUBLE_MM, 165)
    gs = GridSpec(2, 1, figure=fig, height_ratios=[len(rows_a), len(rows_b) + 1.2], left=0.33, right=0.58,
                  top=0.95, bottom=0.07, hspace=0.32)
    ax_a, ax_b = fig.add_subplot(gs[0]), fig.add_subplot(gs[1])
    forest(ax_a, rows_a, rec, panel="a", xlim=XLIM, cols=COLS, col_x0=1.04, col_dx=0.21)
    forest(ax_b, rows_b, rec, panel="b", xlim=XLIM, cols=COLS, col_x0=1.04, col_dx=0.21)
    ax_a.set_title("a  Host share of partners, A_cont: IRR per SD", loc="left", x=-0.62, fontweight="bold")
    ax_b.set_title("b  Co-transfer, CT: IRR per SD", loc="left", x=-0.62, fontweight="bold")
    ax_b.set_xlabel("IRR per SD of regressor (log scale); outcome W2 host papers by author-disjoint newcomers")
    for ax in (ax_a, ax_b):
        ax.tick_params(axis="x", labelsize=style.TICK_PT)
    out = out_root / "F2"
    audit = style.save(fig, out, "F2_d2_forest")
    caption = (
        "F2. Anchoring into host-native partners (A_cont) predicts newcomer uptake after host entry; co-transfer "
        "(CT) does not. Points are PPML IRR per SD with 95% CRV1 Wald CIs clustered by concept (placebo-host "
        "rows from the main folds show the median and 2.5-97.5% quantiles of 100 size-matched placebo draws); "
        "filled markers are the co-primary FE (concept + entry year + host), hollow markers the thinner primary "
        f"FE (concept x e + host x e), which retains {ret}% of screen events and is labelled underpowered. N = "
        "entry events, G = concept clusters; the pooled IVW row combines main and MeSH co-primary estimates. Sources: "
        "3_invention_loop/iter_3/gen_art/gen_art_experiment_7/results/d2_summary.json (art_2Cd2JJypeGuA), "
        "3_invention_loop/iter_4/gen_art/gen_art_evaluation_2/results/heldout_post.json (art_WZ8fbLn79nCq), "
        "3_invention_loop/iter_4/gen_art/gen_art_experiment_9/results/g4_models.json (art_XGdzjWgi-a88); "
        "wild, permutation and size-calibrated p values are in tables/inferential_caveats.csv.")
    write_sidecars(out, "F2", rec, {"width_mm": style.W_DOUBLE_MM, "panels": ["a", "b"], "xscale": "log",
                                    "xlim": list(XLIM), "ci_type": "95% CRV1 Wald, concept-clustered"},
                   caption, audit)
    return audit
