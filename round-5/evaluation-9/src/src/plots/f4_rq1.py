"""F4: RQ1 structural precursors, screen vs sealed held-out, one linear small multiple per metric."""
from __future__ import annotations

from pathlib import Path

from src import style
from src.plots.common import write_sidecars
from src.registry import Recorder, Registry

METRICS = [("closure", "Closure (SD)"), ("closure_resT", "Turnover-residualised closure (SD)"),
           ("closure_persist", "Persistent-neighbour closure (SD)"), ("constraint", "Burt constraint (raw)"),
           ("effsize", "Effective size (raw)"), ("wmz", "Within-module z (raw)")]
MARKS = [("es", "scr", "Screen, event study", "SCREEN"), ("es", "ho", "Held-out, event study", "CONFIRMATORY"),
         ("pp", "scr", "Screen, pooled panel", "SCREEN"), ("pp", "ho", "Held-out, pooled panel", "CONFIRMATORY")]


def build(reg: Registry, out_root: Path) -> dict:
    rec = Recorder(reg, "F4")
    fig = style.new_figure(style.W_DOUBLE_MM, 150)
    status = rec.raw("f4.status", panel="banner", row="r1", field="status")
    reading = rec.raw("f4.reading", panel="banner", row="r1", field="reading_label")
    sha = rec.raw("f4.spec_sha", panel="banner", row="r1", field="spec_sha256")
    banner = (f"{status} under the frozen kill mapping (heldout_spec sha256 {str(sha)[:8]}):\nstructural precursors "
              f"behave as volume/churn correlates. Reading test {reading}.")
    fig.text(0.01, 0.975, banner, fontsize=style.BASE_PT, fontweight="bold", va="top", color=style.OKABE_ITO["vermillion"])
    ncol, w, h = 3, 0.225, 0.25
    for m_i, (m, mname) in enumerate(METRICS):
        r, c = divmod(m_i, ncol)
        ax = fig.add_axes([0.2 + c * (w + 0.045), 0.58 - r * (h + 0.155), w, h])
        frozen = rec.raw(f"f4.{m}.frozen", panel=m, row=m, field="estimator_frozen")
        direction = rec.raw(f"f4.{m}.dir", panel=m, row=m, field="spec_direction")
        ylabels = []
        for yi, (est, fold, lab, fl) in enumerate(MARKS):
            rid = f"{m}.{est}.{fold}"
            colour, marker, _ = style.fold_style(fl)
            filled = (est == "es" and frozen == "event_study") or (est == "pp" and frozen == "pooled_panel")
            v = rec.v(f"f4.{m}.{est}.{fold}", panel=m, row=rid, field="est", fmt=".3f")
            lo = rec.v(f"f4.{m}.{est}.{fold}_lo", panel=m, row=rid, field="lo", fmt=".3f")
            hi = rec.v(f"f4.{m}.{est}.{fold}_hi", panel=m, row=rid, field="hi", fmt=".3f")
            rec.label(rid, fl, panel=m)
            ylabels.append(lab)
            if v is None:
                ax.text(0.02, yi, "not estimated in source", transform=ax.get_yaxis_transform(),
                        fontsize=style.SMALL_PT, va="center", color=style.DARK_GREY)
                continue
            if lo is not None and hi is not None:
                ax.plot([lo, hi], [yi, yi], color=colour, lw=0.9)
            ax.plot([v], [yi], marker=marker, color=colour, mfc=colour if filled else "white", ms=4, mew=0.8)
        if m == "closure_resT":
            v = rec.v("f4.iv_resT.est", panel=m, row="iv_resT", field="est", fmt=".3f")
            lo = rec.v("f4.iv_resT.lo", panel=m, row="iv_resT", field="lo", fmt=".3f")
            hi = rec.v("f4.iv_resT.hi", panel=m, row="iv_resT", field="hi", fmt=".3f")
            rec.label("iv_resT", "DESCRIPTIVE", panel=m)
            ax.plot([lo, hi], [4, 4], color=style.GREY, lw=0.9)
            ax.plot([v], [4], marker="v", color=style.GREY, ms=4)
            ax.text(lo, 4, "IVW screen+held-out (descr.)  ", fontsize=style.SMALL_PT, va="center", ha="right",
                    color=style.DARK_GREY)
        ax.axvline(0, color=style.DARK_GREY, lw=0.6, ls="--")
        ax.set_ylim(4.5, -0.5)
        ax.set_yticks(range(len(ylabels)))
        ax.set_yticklabels(ylabels if c == 0 else [""] * len(ylabels), fontsize=style.SMALL_PT)
        ax.set_xlabel(mname, fontsize=style.TICK_PT)
        ax.tick_params(axis="x", labelsize=style.SMALL_PT)
        # held-out sign of the frozen estimator against the pre-declared direction
        key = f"f4.{m}.{'es' if frozen == 'event_study' else 'pp'}.ho"
        obs = reg.try_get(key)
        if direction in ("negative", "positive") and obs is not None:
            match = (obs < 0) if direction == "negative" else (obs > 0)
            mark = "✓ sign matches" if match else "✗ sign opposite"
        else:
            mark = ""
        dec = reg.try_get(f"f4.{m}.decision") if f"f4.{m}.decision" in reg.keys else None
        holm = rec.s(f"f4.{m}.holm", ".3f", panel=m, row=m, field="holm") if dec is not None else None
        if dec is not None:
            rec.raw(f"f4.{m}.decision", panel=m, row=m, field="decision")
        tl = f"pre-declared {direction}; {mark}"
        t2 = f"{dec} (Holm p {holm})" if dec is not None else "not in the Holm family"
        ax.set_title(f"{tl}\n{t2}", fontsize=style.SMALL_PT, loc="left",
                     color=style.OKABE_ITO["vermillion"] if dec == "DEAD" else style.DARK_GREY)
    fb = rec.s("f4.fallback_screen_never", ".0f", panel="footnote", row="persist", field="screen_never_controls")
    smd = rec.s("f4.bal_H_smd", ".2f", panel="footnote", row="balance", field="H_smd_k0")
    nfl = rec.s("f4.bal_n_flag", ".0f", panel="footnote", row="balance", field="n_abs_smd_gt_0.25")
    nb = rec.s("f4.bal_n", ".0f", panel="footnote", row="balance", field="n_balance_rows")
    dauc = rec.s("f4.dauc", ".3f", panel="footnote", row="prediction", field="dAUC")
    dlo = rec.s("f4.dauc_lo", ".3f", panel="footnote", row="prediction", field="dAUC_lo")
    dhi = rec.s("f4.dauc_hi", ".3f", panel="footnote", row="prediction", field="dAUC_hi")
    foot = (f"Filled = frozen estimator for that metric; hollow = the other estimator.\nPersistent-neighbour closure is "
            f"CONFIRMED on held-out but its screen event-study CI includes 0;\nthe held-out control fallback added {fb} "
            f"screen never-controls; balance: H SMD {smd} at k=0, {nfl}/{nb} balance rows with |SMD| > 0.25.\n"
            f"Screen prediction check: dAUC {dauc} [{dlo}, {dhi}] (grouped CV, exp_5).")
    fig.text(0.01, 0.015, foot, fontsize=style.SMALL_PT, color=style.DARK_GREY)
    out = out_root / "F4"
    audit = style.save(fig, out, "F4_rq1_heldout")
    n_on = rec.s("f4.n_onsets", ".0f", panel="caption", row="caption", field="n_onsets")
    n_m = rec.s("f4.n_matched", ".0f", panel="caption", row="caption", field="n_matched")
    caption = (
        "F4. RQ1: pre-take-off structural precursors do not survive the sealed held-out test (R1_DEAD), shown as "
        "one small multiple per network metric on its own linear axis with a zero line (SD units for closure rows, "
        f"raw units for constraint, effective size and within-module z; held-out n = {n_on} onsets, {n_m} matched). "
        "Event-study CIs are 95% concept-bootstrap percentile (B=2,000), held-out pooled-panel CIs are 95% "
        "concept-clustered Wald, and screen pooled-panel CIs are derived as coef +/- 1.96 se (flagged derived in "
        "plotted_values.json); Holm p values are one-sided in the pre-declared direction. Sources: "
        "3_invention_loop/iter_4/gen_art/gen_art_evaluation_3/results/tables/r1_event_study_screen_vs_heldout.csv, "
        "r1_pooled_panel_screen_vs_heldout.csv and results/r1/r1_summary.json (art_zw_JJGsUFSnd).")
    write_sidecars(out, "F4", rec, {"width_mm": style.W_DOUBLE_MM, "panels": [m for m, _ in METRICS],
                                    "xscale": "linear", "ci_type": "concept bootstrap B=2,000 (ES); Wald (PP)"},
                   caption, audit)
    return audit
