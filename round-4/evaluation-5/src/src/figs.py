"""Figures F1-F5 (matplotlib, PNG + PDF)."""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False, "pdf.fonttype": 42})
BLUE, ORANGE, GREY, GREEN, RED = "#2a6fb0", "#d9822b", "#8a8a8a", "#3a9a5b", "#b8433a"


def _save(fig, out: Path, name: str) -> None:
    fig.tight_layout()
    fig.savefig(out / f"{name}.png", dpi=200)
    fig.savefig(out / f"{name}.pdf")
    plt.close(fig)


def _term(m: dict, t: str):
    v = (m.get("terms") or {}).get(t)
    if not v or v.get("OR") is None:
        return None
    ci = v.get("OR_ci95_boot") or [np.nan, np.nan]
    return v["OR"], ci[0], ci[1]


def f1_forest(res: dict, out: Path) -> None:
    en, voc = res["enrichment"], res["vocab_class"]
    items = [("Partner (E_any) | NEG, prior", en["m2"], "E_any", BLUE),
             ("Negative control (NEG)", en["m2"], "E_neg", GREY),
             ("Partner | NEG, PLAC (placebo strata)", en["m_plac"], "E_any", BLUE),
             ("Placebo partners (PLAC)", en["m_plac"], "E_plac", ORANGE),
             ("Swapped partner set (label shuffle)", en["m_swap"], "E_swap", ORANGE),
             ("NATIVE partners (s>=0.3)", voc["m_voc"], "E_nat", GREEN),
             ("ADJACENT partners (0.05-0.3)", voc["m_voc"], "E_adj", GREEN),
             ("FOREIGN partners (<0.05)", voc["m_voc"], "E_for", GREEN),
             ("UNPROFILED partners", voc["m_voc"], "E_unprof", GREEN),
             ("Origin-companion partners", voc["m_comp"], "E_comp", RED),
             ("Non-companion partners", voc["m_comp"], "E_noncomp", RED)]
    fig, ax = plt.subplots(figsize=(7.2, 4.4))
    ys = []
    for i, (lab, m, t, col) in enumerate(items):
        v = _term(m, t)
        y = len(items) - i
        ys.append((y, lab))
        if v is None:
            ax.text(1, y, "not identified", va="center", fontsize=7, color=GREY)
            continue
        o, lo, hi = v
        ax.errorbar(o, y, xerr=[[o - lo], [hi - o]] if np.isfinite(lo) else None, fmt="o", color=col, ms=4, capsize=2)
    ax.axvline(1, color="k", lw=0.7, ls="--")
    ax.set_xscale("log")
    ax.set_yticks([y for y, _ in ys])
    ax.set_yticklabels([lab for _, lab in ys])
    ax.set_xlabel("OR, adopters vs matched host authors (95% concept-bootstrap CI)")
    ax.set_title("F1. Prior use of entry vocabulary (corpus exposure; screen fold)", fontsize=9)
    _save(fig, out, "F1_forest_ORs")


def f2_tercile(res: dict, out: Path) -> None:
    it = res["interaction"]
    fig, ax = plt.subplots(figsize=(4.8, 3.4))
    xs, os_ = [], []
    for t in (1, 2, 3):
        v = _term(it.get(f"m2_T{t}") or {}, "E_any")
        if v is None:
            continue
        o, lo, hi = v
        ax.errorbar(t, o, yerr=[[o - lo], [hi - o]] if np.isfinite(lo) else None, fmt="o", color=BLUE, capsize=3)
        mde = (it["tercile_MDE"].get(f"T{t}") or {}).get("MDE80_p0_0.25")
        ax.text(t + 0.08, o, f"n={it[f'm2_T{t}']['n_strata']}\nMDE80~{mde}", fontsize=7, va="center")
        xs.append(t)
        os_.append(o)
    vi = _term(it["m_int"], "E_any_x_zA")
    v0 = _term(it["m_int"], "E_any")
    if vi and v0:
        zz = np.linspace(-1.2, 1.2, 50)
        ax.plot(2 + zz, np.exp(np.log(v0[0]) + np.log(vi[0]) * zz), color=ORANGE, lw=1,
                label=f"continuous (x-2 = z(A_cont)): OR ratio/SD {vi[0]:.2f} [{vi[1]:.2f}, {vi[2]:.2f}]")
        ax.legend(fontsize=7, frameon=False)
    ax.axhline(1, color="k", lw=0.7, ls="--")
    ax.set_yscale("log")
    ax.set_xticks([1, 2, 3])
    ax.set_xticklabels(["T1 (low A_cont)", "T2", "T3 (high)"])
    ax.set_ylabel("OR(E_any | NEG, prior)")
    ax.set_title("F2. Enrichment by entry anchoring tercile", fontsize=9)
    _save(fig, out, "F2_OR_by_Acont_tercile")


def f3_prevalence(res: dict, out: Path) -> None:
    ds = res["descriptives"]
    labs = [("E_any", "any partner"), ("E_nat", "NATIVE"), ("E_adj", "ADJACENT"), ("E_for", "FOREIGN"),
            ("E_unprof", "UNPROF."), ("E_comp", "companion"), ("E_neg", "NEG"), ("E_plac", "PLAC")]
    x = np.arange(len(labs))
    fig, ax = plt.subplots(figsize=(6.0, 3.2))
    ax.bar(x - 0.2, [ds[f"prev_case_{k}"] for k, _ in labs], 0.4, color=BLUE, label=f"adopters (n={ds['n_cases']})")
    ax.bar(x + 0.2, [ds[f"prev_control_{k}"] for k, _ in labs], 0.4, color=GREY, label=f"controls (n={ds['n_controls']})")
    ax.set_xticks(x)
    ax.set_xticklabels([l for _, l in labs], rotation=20)
    ax.set_ylabel("share with prior use (<= e-1)")
    ax.legend(frameon=False, fontsize=7)
    ax.set_title("F3. Exposure prevalence by vocabulary class", fontsize=9)
    _save(fig, out, "F3_exposure_prevalence")


def f4_mediation(res: dict, out: Path) -> None:
    med = res["mediation"]
    fig, ax = plt.subplots(figsize=(4.8, 3.2))
    for k, col, lab in [("boot_draws_att_M2", BLUE, "+M2"), ("boot_draws_att_M2_split", ORANGE, "+M2 native/adjacent")]:
        v = np.asarray(med.get(k) or [], float)
        v = v[np.isfinite(v)]
        if len(v):
            ax.hist(np.clip(v, -1, 1.5), bins=40, alpha=0.55, color=col, label=lab)
    a = med["point"]["att"].get("att_M2")
    if a is not None:
        ax.axvline(a, color=BLUE, lw=1.2)
    ax.axvline(0, color="k", lw=0.7, ls="--")
    ax.set_xlabel("attenuation share of b_A (co-primary PPML)")
    ax.set_ylabel("bootstrap replicates")
    ax.legend(frameon=False, fontsize=7)
    ax.set_title("F4. Mediation-style attenuation (concept bootstrap)", fontsize=9)
    _save(fig, out, "F4_attenuation_bootstrap")


def f5_power(res: dict, out: Path) -> None:
    pw = res["power"]
    g = pd.DataFrame(pw["pairs"]["grid"])
    fig, axs = plt.subplots(1, 3, figsize=(9.6, 3.0))
    for p0, col in zip((0.1, 0.25, 0.4, 0.6), (GREY, BLUE, ORANGE, GREEN)):
        s = g[(g.kind == "main") & (g.p0 == p0)]
        axs[0].plot(s.OR, s.power, "o-", color=col, ms=3, label=f"p0={p0}")
        s = g[(g.kind == "inter") & (g.p0 == p0)]
        axs[1].plot(s.ratio, s.power, "o-", color=col, ms=3, label=f"p0={p0}")
    m = pd.DataFrame(pw["mediation"]["grid"])
    axs[2].plot(m.share, m.power_joint.fillna(0), "o-", color=BLUE, ms=3)
    for a, xl, tt in zip(axs, ["true OR", "true OR ratio per SD A_cont", "true mediated share of b_A"],
                         ["primary OR", "interaction", "mediation (joint significance)"]):
        a.axhline(0.8, color="k", lw=0.7, ls="--")
        a.set_xlabel(xl)
        a.set_title(tt, fontsize=8)
        a.set_ylim(0, 1.02)
    axs[0].set_ylabel("power (300 reps)")
    axs[0].legend(frameon=False, fontsize=6)
    fig.suptitle("F5. Design-based power on the frozen strata (computed before exposure)", fontsize=9)
    _save(fig, out, "F5_power_curves")


def run(res: dict, D: pd.DataFrame, out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    for f in (f1_forest, f2_tercile, f3_prevalence, f4_mediation, f5_power):
        f(res, out)
