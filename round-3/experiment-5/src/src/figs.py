"""Figures (vector PDF + PNG): event-study panels, R1d joint path, R1a correlations, grid forest, MDE curves."""
from __future__ import annotations

import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from loguru import logger  # noqa: E402

import common as K  # noqa: E402

plt.rcParams.update({"pdf.fonttype": 42, "ps.fonttype": 42, "font.size": 9, "axes.spines.top": False,
                     "axes.spines.right": False})
BLUE, RED, GREY, GREEN, ORANGE = "#2b6cb0", "#c0392b", "#7f8c8d", "#2e8b57", "#d68910"
NAMES = {"closure": "Raw closure\n(log obs / Chung-Lu)", "closure_resT": "R1a: turnover-residualised\nclosure",
         "closure_persist": "R1b: persistent-neighbour\nclosure", "constraint": "R1c: Burt constraint\n(ego network)",
         "xc_excess": "R1c: cross-community\npair excess", "cdeg_diag": "log(n_ego x constraint)", "wmz": "within-module z"}


def _save(fig, name: str) -> list[str]:
    out = []
    for ext in ("pdf", "png"):
        p = K.FIG / f"{name}.{ext}"
        fig.savefig(p, dpi=200, bbox_inches="tight")
        out.append(str(p.relative_to(K.ROOT)))
    plt.close(fig)
    return out


def _arr(x):
    return np.array([np.nan if v is None else v for v in x], dtype=float)


def fig_es_panels(pf: dict) -> list[str]:
    ks = K.SPEC3["es_rel_years"]
    rows = ["closure", "closure_resT", "closure_persist", "constraint", "xc_excess"]
    fig, axes = plt.subplots(1, 5, figsize=(15, 3.3))
    for ax, col in zip(axes, rows):
        st = pf["rows"][col]
        d = _arr(st["diff_k"])
        ci = np.array([_arr(c) for c in st["ci_k"]])
        colr = BLUE if col.startswith("closure") else (ORANGE if col == "constraint" else GREEN)
        ax.axvspan(K.SPEC3["es_primary_window"][0] - 0.4, K.SPEC3["es_primary_window"][1] + 0.4, color=GREY, alpha=0.08)
        ax.fill_between(ks, ci[:, 0], ci[:, 1], color=colr, alpha=0.18, lw=0)
        ax.plot(ks, d, "o-", color=colr, ms=4)
        ax.axhline(0, color="k", lw=0.7)
        S, c = st["primary"]["S"], st["primary"]["ci"]
        ax.set_title(f"{NAMES[col]}\nS = {S:.3f} [{c[0]:.3f}, {c[1]:.3f}]", fontsize=8.5)
        ax.set_xlabel("years relative to onset t0")
        ax.set_xticks(ks)
    axes[0].set_ylabel("treated - matched controls")
    fig.suptitle(f"MAIN x E_up matched event study (n = {pf['n_matched']} matched of {pf['n_onsets']} onsets; 95% concept-bootstrap CIs; "
                 f"shaded = S window -3..0)", fontsize=9)
    fig.tight_layout()
    return _save(fig, "fig_es_panels")


def fig_r1d(r1d: dict) -> list[str]:
    ks = K.SPEC3["es_rel_years"]
    fig, axes = plt.subplots(1, 2, figsize=(9, 3.2), gridspec_kw=dict(width_ratios=[2, 1]))
    ax = axes[0]
    for col, colr, lab in (("wmz", GREEN, "within-module z"), ("closure", BLUE, "closure")):
        jp = r1d["joint_path"][col]
        d = _arr(jp["diff_k"])
        ci = np.array([_arr(c) for c in jp["ci_k"]])
        sd = np.nanmax(np.abs(ci)) or 1.0
        ax.fill_between(ks, ci[:, 0] / sd, ci[:, 1] / sd, color=colr, alpha=0.15, lw=0)
        ax.plot(ks, d / sd, "o-", color=colr, label=f"{lab} (scaled by max |CI|)")
    ax.axhline(0, color="k", lw=0.7)
    ax.set_xlabel("years relative to onset t0")
    ax.set_ylabel("treated - control (scaled)")
    ax.legend(fontsize=7)
    ax.set_title("Joint path: hub-ness vs clustering", fontsize=9)
    ax = axes[1]
    vals = [r1d["share_T"], r1d["share_C"]]
    ax.bar([0, 1], vals, color=[RED, GREY])
    ax.set_xticks([0, 1])
    ax.set_xticklabels(["treated", "controls"])
    ci = r1d["diff_ci"]
    ax.set_title(f"share d_wmz>0 & d_closure<0 (k=-3..0)\ndiff {r1d['diff']:.3f} [{ci[0]:.3f}, {ci[1]:.3f}]", fontsize=8)
    fig.tight_layout()
    return _save(fig, "fig_r1d_joint")


def fig_r1a(r1a: dict) -> list[str]:
    items = [(k, v) for k, v in r1a.items()]
    fig, ax = plt.subplots(figsize=(7, 0.32 * len(items) * 2 + 1))
    y = 0
    labels = []
    for k, v in items:
        for kind, colr, off in (("demeaned_pearson", BLUE, 0.15), ("demeaned_spearman", ORANGE, -0.15)):
            ci = v[f"{kind}_ci"]
            ax.errorbar(v[kind], y + off, xerr=[[v[kind] - ci[0]], [ci[1] - v[kind]]], fmt="o", color=colr, ms=4, capsize=2,
                        label=kind.replace("_", " ") if y == 0 else None)
        labels.append(f"{k} (n={v['n']})")
        y += 1
    ax.axvline(0, color="k", lw=0.7)
    ax.set_yticks(range(len(labels)))
    ax.set_yticklabels(labels, fontsize=7)
    ax.set_xlabel("within-concept correlation of closure with the turnover measure (95% concept-bootstrap CI)")
    ax.legend(fontsize=7, loc="lower right")
    ax.invert_yaxis()
    fig.tight_layout()
    return _save(fig, "fig_r1a_corr")


def fig_grid(grid: pd.DataFrame) -> list[str]:
    rows = ["closure", "closure_resT", "closure_persist", "constraint", "xc_excess"]
    cells = [f"{P}|{s}|E_up|{r}" for P in ("MAIN", "STRICT", "SENS") for s in ("all", "old", "new") for r in ("all", "B_only")]
    fig, axes = plt.subplots(1, len(rows), figsize=(15, 6), sharey=True)
    for ax, col in zip(axes, rows):
        for i, c in enumerate(cells):
            r = grid[(grid.cell == c) & (grid.indicator == col)]
            if r.empty or not np.isfinite(r.S.iloc[0]):
                continue
            r = r.iloc[0]
            colr = RED if c.startswith("MAIN|all|E_up|all") else BLUE
            ax.errorbar(r.S, i, xerr=[[r.S - r.ci_lo], [r.ci_hi - r.S]] if np.isfinite(r.ci_lo) else None, fmt="o",
                        color=colr, ms=3.5, capsize=2)
        ax.axvline(0, color="k", lw=0.7)
        ax.set_title(NAMES[col], fontsize=8.5)
    nm = {c: grid.loc[grid.cell == c, "n_matched"].iloc[0] if (grid.cell == c).any() else 0 for c in cells}
    axes[0].set_yticks(range(len(cells)))
    axes[0].set_yticklabels([f"{c.replace('|E_up', '')} (n={nm[c]})" for c in cells], fontsize=7)
    axes[0].invert_yaxis()
    fig.suptitle("S (k=-3..0) by population x subset x route, label E_up (primary cell in red; 95% CIs)", fontsize=9)
    fig.tight_layout()
    return _save(fig, "fig_grid_forest")


def fig_mde(pw: dict) -> list[str]:
    rows = list(pw["rows"])
    fig, axes = plt.subplots(1, len(rows), figsize=(3 * len(rows), 2.9), sharey=True)
    for ax, col in zip(axes, rows):
        r = pw["rows"][col]
        g = np.array(r["grid"]) / r["sd"]
        ax.plot(g, r["es"]["power"], "-", color=BLUE, label="event study")
        ax.plot(g, r["panel"]["power"], "--", color=ORANGE, label="pooled panel")
        ax.axhline(0.8, color=GREY, lw=0.7, ls=":")
        ax.set_title(f"{col}\nprimary: {r['heldout_primary_estimator'].replace('_', ' ')}", fontsize=8)
        ax.set_xlabel("effect (SD of indicator)")
    axes[0].set_ylabel(f"power (held-out n_treated = {pw['n_h_treated']})")
    axes[0].legend(fontsize=7)
    fig.tight_layout()
    return _save(fig, "fig_mde")


def main() -> list[str]:
    pf = json.loads((K.RES / "event_study" / "primary_family.json").read_text())
    grid = pd.read_csv(K.RES / "event_study" / "summary_grid.csv")
    made = []
    made += fig_es_panels(pf)
    made += fig_r1d(json.loads((K.RES / "r1d.json").read_text()))
    made += fig_r1a(json.loads((K.RES / "r1a_correlations.json").read_text()))
    made += fig_grid(grid)
    made += fig_mde(json.loads((K.RES / "power_mde.json").read_text()))
    logger.info(f"figures: {made}")
    return made


if __name__ == "__main__":
    K.setup_logging("figs")
    main()
