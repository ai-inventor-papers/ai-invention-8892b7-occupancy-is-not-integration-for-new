"""F5: the diffusion typology measures occupancy; host share predicts rooting within both types."""
from __future__ import annotations

from pathlib import Path

from src import style
from src.plots.common import write_sidecars
from src.registry import Recorder, Registry

TYPES = (("BROAD", "BROAD", style.OKABE_ITO["blue"], "s"), ("LOCALISED", "LOCALISED", style.OKABE_ITO["orange"], "o"))
FOLDS = (("screen", "Screen", "SCREEN"), ("heldout", "Held-out W1", "CONFIRMATORY"))


def _pt(ax, rec, base, x, colour, marker, panel, row, filled=True):
    v = rec.v(f"{base}.est", panel=panel, row=row, field="est", fmt=".3f")
    lo = rec.v(f"{base}.lo", panel=panel, row=row, field="lo", fmt=".3f")
    hi = rec.v(f"{base}.hi", panel=panel, row=row, field="hi", fmt=".3f")
    if v is None:
        return
    ax.plot([x, x], [lo, hi], color=colour, lw=0.9)
    ax.plot([x], [v], marker=marker, color=colour, mfc=colour if filled else "white", ms=4.5, mew=0.8)


def build(reg: Registry, out_root: Path) -> dict:
    rec = Recorder(reg, "F5")
    fig = style.new_figure(style.W_DOUBLE_MM, 118)
    W, H = 0.21, 0.28
    xs = [0.11, 0.44, 0.765]
    ax = {k: fig.add_axes([xs[i % 3], 0.6 if i < 3 else 0.12, W, H])
          for i, k in enumerate(["a1", "a2", "b1", "b2", "c", "d"])}
    # (a1) entries per concept by type (no CI in source)
    for i, (ty, lab, col, mk) in enumerate(TYPES):
        for j, (fold, fname, fl) in enumerate(FOLDS):
            v = rec.v(f"f5.{fold}.{ty}.entries_pc", panel="a1", row=f"{fold}.{ty}", field="entries_per_concept",
                      fmt=".1f")
            nc = rec.s(f"f5.{fold}.{ty}.n_concepts", ".0f", panel="a1", row=f"{fold}.{ty}", field="n_concepts")
            rec.label(f"{fold}.{ty}", "DESCRIPTIVE", panel="a1")
            x = i + (j - 0.5) * 0.38
            ax["a1"].bar(x, v, 0.34, color=col, alpha=0.9 if j == 0 else 0.45, hatch="" if j == 0 else "///",
                         edgecolor="white")
            ax["a1"].text(x, v, f"{v:.1f}\n({nc})", ha="center", va="bottom", fontsize=style.SMALL_PT)
    ax["a1"].set_xticks([0, 1])
    ax["a1"].set_xticklabels([t[1] for t in TYPES])
    ax["a1"].set_ylabel("Host entries per concept")
    ax["a1"].set_ylim(0, 32)
    ax["a1"].set_title("a  OCCUPANCY (solid screen,\n    hatched held-out; n concepts)", loc="left",
                       fontsize=style.TICK_PT, fontweight="bold")
    # (a2) EST rate by type (screen) with bootstrap CI
    for i, (ty, lab, col, mk) in enumerate(TYPES):
        _pt(ax["a2"], rec, f"f5.screen.{ty}.EST_rate", i, col, mk, "a2", f"screen.{ty}")
        rec.label(f"screen.{ty}.EST", "DESCRIPTIVE", panel="a2")
    ax["a2"].set_xticks([0, 1])
    ax["a2"].set_xticklabels([t[1] for t in TYPES])
    ax["a2"].set_xlim(-0.6, 1.6)
    ax["a2"].set_ylabel("Establishment rate (EST_bin)")
    ax["a2"].set_title("a'  Rooting rate by type (screen)", loc="left", fontsize=style.TICK_PT, fontweight="bold")
    # (b1) raw A_cont mean by type and fold
    for i, (ty, lab, col, mk) in enumerate(TYPES):
        for j, (fold, fname, fl) in enumerate(FOLDS):
            _pt(ax["b1"], rec, f"f5.{fold}.{ty}.A_cont_mean", i + (j - 0.5) * 0.3, col, mk, "b1", f"{fold}.{ty}",
                filled=(j == 0))
            rec.label(f"{fold}.{ty}.A_cont_mean", "DESCRIPTIVE", panel="b1")
    ax["b1"].set_xticks([0, 1])
    ax["b1"].set_xticklabels([t[1] for t in TYPES])
    ax["b1"].set_xlim(-0.6, 1.6)
    ax["b1"].set_ylabel("Mean A_cont (raw)")
    ax["b1"].set_title("b  HOST SHARE, raw\n    (filled screen, hollow HO)", loc="left", fontsize=style.TICK_PT,
                       fontweight="bold")
    # (b2) adjusted A_cont gap; (c) adjusted CT gap
    for key, a, title, verdict in (("model_i_Acont", "b2", "b'  Adjusted A_cont gap\n    (BROAD - LOCALISED)",
                                    "declared BROAD-higher\nprediction FAILED"),
                                   ("model_ii_CT", "c", "c  Adjusted CT gap\n    (BROAD - LOCALISED)",
                                    "declared BROAD-lower\nREPLICATED")):
        for j, (fold, fname, fl) in enumerate(FOLDS):
            colour, marker, _ = style.fold_style(fl)
            _pt(ax[a], rec, f"f5.{fold}.{key}", j, colour, marker, a, f"{fold}.{key}")
            rec.label(f"{fold}.{key}", fl, panel=a)
        ax[a].axhline(0, color=style.DARK_GREY, lw=0.6, ls="--")
        ax[a].set_xticks([0, 1])
        ax[a].set_xticklabels([f[1] for f in FOLDS])
        ax[a].set_xlim(-0.6, 1.6)
        ax[a].set_ylabel("Coef. (host x year FE)")
        ax[a].set_title(title, loc="left", fontsize=style.TICK_PT, fontweight="bold", y=1.12)
        ax[a].text(0.0, 1.02, verdict.replace("\n", " "), transform=ax[a].transAxes, ha="left",
                   fontsize=style.SMALL_PT, style="italic",
                   color=style.OKABE_ITO["vermillion"] if "FAILED" in verdict else style.DARK_GREY)
    # (d) EST rate across A_cont quintiles within type + PPML by type
    for ty, lab, col, mk in TYPES:
        vals = [rec.v(f"f5.estq.{ty}.q{q}", panel="d", row=f"{ty}.q{q}", field="EST_rate", fmt=".3f")
                for q in range(1, 6)]
        for q in range(1, 6):
            rec.v(f"f5.estq.{ty}.q{q}.n", panel="d", row=f"{ty}.q{q}", field="n", fmt=".0f")
        rec.label(f"{ty}.quintiles", "DESCRIPTIVE", panel="d")
        ax["d"].plot(range(1, 6), vals, marker=mk, color=col, ms=3.5, label=lab)
    ppml = []
    for ty, lab, col, mk in TYPES:
        e = rec.s(f"f5.ppml.{ty}.est", ".2f", panel="d", row=f"ppml.{ty}", field="est")
        lo = rec.s(f"f5.ppml.{ty}.lo", ".2f", panel="d", row=f"ppml.{ty}", field="lo")
        hi = rec.s(f"f5.ppml.{ty}.hi", ".2f", panel="d", row=f"ppml.{ty}", field="hi")
        rec.label(f"ppml.{ty}", "SCREEN", panel="d")
        ppml.append(f"{lab} {e} [{lo}, {hi}]")
    ip = rec.s("f5.ppml.int_p", ".2f", panel="d", row="ppml", field="interaction_p")
    ax["d"].text(0.03, 0.97, "PPML IRR/SD:\n" + "\n".join(ppml) + f"\ninteraction p {ip} (exploratory)",
                 transform=ax["d"].transAxes, va="top", fontsize=style.SMALL_PT)
    ax["d"].set_xticks(range(1, 6))
    ax["d"].set_xlabel("A_cont quintile (screen)")
    ax["d"].set_ylabel("Establishment rate")
    ax["d"].set_ylim(0, 1.05)
    ax["d"].legend(loc="center left", fontsize=style.SMALL_PT, frameon=False)
    ax["d"].set_title("d  ROOTING within type", loc="left", fontsize=style.TICK_PT, fontweight="bold")
    out = out_root / "F5"
    audit = style.save(fig, out, "F5_occupancy_rooting")
    nb = rec.s("f5.screen.BROAD.n_concepts", ".0f", panel="caption", row="caption", field="n_broad")
    nl = rec.s("f5.screen.LOCALISED.n_concepts", ".0f", panel="caption", row="caption", field="n_local")
    caption = (
        "F5. The k=2 diffusion typology measures occupancy, and host share predicts rooting within both types: "
        "BROAD concepts make more host entries and a larger share of them establish (a, a'), their partners' host "
        "share is not higher after host x year FE (b, b'), their co-transfer is lower (c), and establishment rises across "
        f"A_cont quintiles within both types (d; screen n = {nb} BROAD and {nl} LOCALISED concepts). CIs are 95% "
        "concept-bootstrap (B=2,000) for descriptives, 95% concept-clustered Wald for the adjusted gaps and 95% "
        "CRV1 for the PPML IRRs; held-out rows use W1 data only. Source: 3_invention_loop/iter_4/gen_art/"
        "gen_art_evaluation_4/results/rooting.json (art_mu0h0npvNX_u).")
    write_sidecars(out, "F5", rec, {"width_mm": style.W_DOUBLE_MM, "panels": list(ax), "ci_type":
                                    "concept bootstrap B=2,000 (descriptives); concept-clustered Wald (gaps)"},
                   caption, audit)
    return audit
