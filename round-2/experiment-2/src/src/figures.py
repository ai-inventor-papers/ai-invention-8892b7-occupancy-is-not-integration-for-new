"""Figures (PDF + PNG) from the saved result tables; every number drawn comes from results/."""
from __future__ import annotations

import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from loguru import logger  # noqa: E402

from common import FIGS, RESULTS  # noqa: E402

plt.rcParams.update({"font.size": 9, "pdf.fonttype": 42, "axes.spines.top": False, "axes.spines.right": False})
C = {"SOURCE": "#1b7837", "SINK": "#762a83", "FADING": "#e08214", "UNDETERMINED": "#bababa", "ORIGIN": "#2166ac"}


def save(fig, name: str) -> None:
    FIGS.mkdir(exist_ok=True)
    fig.tight_layout()
    fig.savefig(FIGS / f"{name}.pdf")
    fig.savefig(FIGS / f"{name}.png", dpi=200)
    plt.close(fig)


def fig_gate_a() -> None:
    h = pd.read_parquet(RESULTS / "gate_a" / "gate_a_host_edges.parquet")
    h = h[h.n_children >= 10]
    r = pd.read_parquet(RESULTS / "cache" / "ref_cells.parquet")
    r = r[~r.is_modal & (r.n_children >= 10)]
    fig, ax = plt.subplots(1, 2, figsize=(8, 3), sharey=True)
    bins = np.linspace(0, 1, 21)
    ax[0].hist(h.lenient_share, bins, alpha=.6, label=f"lenient any-parent (mean {h.lenient_share.mean():.2f})", color="#999")
    ax[0].hist(h.within_host_share, bins, alpha=.7, label=f"within-host (mean {h.within_host_share.mean():.2f})", color="#2166ac")
    ax[0].axvline(0.4, ls="--", c="k", lw=1)
    ax[0].set_title(f"Main arm host edge-years, |Kd|>=10 (n={len(h)})")
    ax[0].set_xlabel("share of W1 host children traced")
    ax[0].set_ylabel("edge-years")
    ax[0].legend(frameon=False, fontsize=7)
    ax[1].hist(r.within_host_share, bins, alpha=.7, color="#b2182b", label=f"reference host (mean {r.within_host_share.mean():.2f})")
    ax[1].axvline(0.4, ls="--", c="k", lw=1)
    ax[1].set_title(f"Reference arm host cells (n={len(r)})")
    ax[1].set_xlabel("within-host traced share")
    ax[1].legend(frameon=False, fontsize=7)
    save(fig, "gate_a_distributions")


def fig_nmin_benchmark() -> None:
    s = json.loads((RESULTS / "viability" / "viability_summary.json").read_text())
    bins = s["n_min"]["bins"]
    fig, ax = plt.subplots(1, 3, figsize=(10, 3))
    ax[0].plot([b["bin_lo"] for b in bins], [b["median_width"] for b in bins], "o-")
    ax[0].axhline(0.7, ls="--", c="k", lw=1)
    ax[0].set_xlabel("|Kd| bin lower bound")
    ax[0].set_ylabel("median 90% CI width of log rho")
    ax[0].set_title("n_min rule (threshold 0.7)")
    ks = sorted(s["label_shares_by_nmin"], key=int)
    bottom = np.zeros(len(ks))
    for st in ["SOURCE", "SINK", "FADING", "UNDETERMINED"]:
        v = np.array([s["label_shares_by_nmin"][k].get(st, 0) for k in ks])
        ax[1].bar(ks, v, bottom=bottom, color=C[st], label=st)
        bottom += v
    ax[1].set_xlabel("n_min")
    ax[1].set_ylabel("share of eligible host edges")
    ax[1].set_title("Label shares vs n_min")
    ax[1].set_ylim(0, 1.35)
    ax[1].legend(frameon=False, fontsize=6, ncol=2, loc="upper center")
    lv = {k: v for k, v in s["benchmark_level_shares_edges"].items() if k != "n"}
    ax[2].bar(list(sorted(lv)), [lv[k] for k in sorted(lv)], color="#4393c3")
    ax[2].set_title("Benchmark rho0 resolution level")
    ax[2].set_ylabel("share of edges")
    save(fig, "nmin_labels_benchmark")


def fig_synth() -> None:
    p = RESULTS / "synth" / "synth_results.json"
    if not p.exists():
        return
    s = json.loads(p.read_text())
    nm = s["n_min_main"]
    conf = pd.DataFrame(s["correct"][f"n_min_{nm}"]["confusion_truth_x_label"]).fillna(0)
    rows = [r for r in ["SOURCE", "SINK", "FADING", "NULL"] if r in conf.index]
    cols = [c for c in ["SOURCE", "SINK", "FADING", "UNDETERMINED"] if c in conf.columns]
    conf = conf.loc[rows, cols]
    fig, ax = plt.subplots(1, 2, figsize=(9, 3.4))
    m = conf.div(conf.sum(1), axis=0).to_numpy()
    im = ax[0].imshow(m, cmap="Blues", vmin=0, vmax=1)
    for i in range(m.shape[0]):
        for j in range(m.shape[1]):
            ax[0].text(j, i, f"{m[i, j]:.2f}\n({int(conf.iloc[i, j])})", ha="center", va="center", fontsize=7,
                       color="w" if m[i, j] > .6 else "k")
    ax[0].set_xticks(range(len(cols)), cols, rotation=20)
    ax[0].set_yticks(range(len(rows)), rows)
    ax[0].set_xlabel("label (main n_min)")
    ax[0].set_ylabel("truth")
    fdr = s["correct"][f"n_min_{nm}"]["realised_FDR"]
    ax[0].set_title(f"Synthetic confusion (FDR={fdr:.3f})" if fdr is not None else "Synthetic confusion")
    fig.colorbar(im, ax=ax[0], fraction=.04)
    pw = pd.DataFrame(s["correct"]["power_by_n_children"])
    order = ["[0.0, 10.0)", "[10.0, 20.0)", "[20.0, 30.0)", "[30.0, 50.0)", "[50.0, 100.0)", "[100.0, 1000000000.0)"]
    for st in ["SOURCE", "SINK", "FADING"]:
        g = pw[pw.truth == st].set_index("n_children_bin").reindex(order)
        ax[1].plot(range(len(order)), g.power_main, "o-", c=C[st], label=f"{st} (main n_min)")
        ax[1].plot(range(len(order)), g.power_nmin5, "o--", c=C[st], alpha=.5, label=f"{st} (n_min 5)")
    ax[1].set_xticks(range(len(order)), ["<10", "10-19", "20-29", "30-49", "50-99", "100+"])
    ax[1].set_xlabel("|Kd| (children)")
    ax[1].set_ylabel("power (correct label)")
    ax[1].legend(frameon=False, fontsize=6)
    ax[1].set_title("Synthetic power by edge size")
    save(fig, "synthetic_validation")


def fig_p1() -> None:
    cv = pd.read_csv(RESULTS / "p1" / "p1_share_curves.csv")
    pooled = cv[cv.measure == "H_pooled_json"]
    fig, ax = plt.subplots(figsize=(4.5, 3))
    ks = pooled.n_min.to_numpy()
    sh = [json.loads(x) for x in pooled.pooled]
    bottom = np.zeros(len(ks))
    for st in ["ORIGIN", "SOURCE", "SINK", "FADING", "UNDETERMINED"]:
        v = np.array([d[st] for d in sh])
        ax.bar([str(k) for k in ks], v, bottom=bottom, color=C[st], label=st)
        bottom += v
    ax.set_xlabel("n_min")
    ax.set_ylabel("mean entropy share (all (c,t))")
    ax.set_title("P1: W1 entropy decomposed by edge state")
    ax.legend(frameon=False, fontsize=6, ncol=2)
    save(fig, "p1_entropy_shares")


def fig_power() -> None:
    p = RESULTS / "power" / "h1_power_curves.csv"
    if p.exists():
        d = pd.read_csv(p)
        cols = {5: "#1b9e77", 10: "#d95f02", 20: "#7570b3", 30: "#e7298a"}
        ls = {"realised": "-", "projected": "--", "N150": ":"}
        fig, ax = plt.subplots(1, 3, figsize=(12, 3.3))
        for i, bt in enumerate([0.7, 0.8]):
            a = d[(d.outcome == "auc") & (d.base_target == bt)]
            for (nm, des), g in a.groupby(["n_min", "design"]):
                ax[i].plot(g.true_delta, g.power, ls[des], marker="o", ms=3, c=cols.get(nm, "k"), label=f"n_min {nm}, {des}")
            ax[i].axhline(0.8, ls="--", c="k", lw=.8)
            ax[i].set_xlabel("true delta-AUC")
            ax[i].set_title(f"H1 power (delta-AUC), oracle BASE AUC {bt}")
        ax[0].set_ylabel("power (SELECTION RULE)")
        ax[0].legend(frameon=False, fontsize=6, ncol=2)
        a = d[(d.outcome == "r2") & (d.base_target == 0.1)]
        for (nm, des), g in a.groupby(["n_min", "design"]):
            ax[2].plot(g.true_delta, g.power, ls[des], marker="o", ms=3, c=cols.get(nm, "k"))
        ax[2].axhline(0.8, ls="--", c="k", lw=.8)
        ax[2].axvline(0.018, ls=":", c="r", lw=1)
        ax[2].text(0.02, 0.05, "Maillart endogenous R2 = 0.018", color="r", fontsize=7)
        ax[2].set_xlabel("true delta-R2")
        ax[2].set_title("Continuous variant, BASE R2 0.10")
        save(fig, "h1_power")
    q = RESULTS / "power" / "gate_b_power_curves.csv"
    if q.exists():
        d = pd.read_csv(q)
        fig, ax = plt.subplots(figsize=(4.5, 3))
        for k, g in d.groupby("key"):
            g = g.sort_values("pct")
            ax.plot(-g.pct, g.power, "o-", ms=3, label=k)
        ax.axhline(0.8, ls="--", c="k", lw=1)
        ax.axvline(25, ls=":", c="r", lw=1)
        ax.set_xlabel("|exp(b2) - 1| (%)")
        ax.set_ylabel("power (CI95 upper < 0)")
        ax.set_title("Gate B power")
        ax.legend(frameon=False, fontsize=6)
        save(fig, "gate_b_power")


def run() -> None:
    for f in [fig_gate_a, fig_nmin_benchmark, fig_synth, fig_p1, fig_power]:
        try:
            f()
        except (KeyError, ValueError, FileNotFoundError, IndexError) as ex:
            logger.error(f"figure {f.__name__} failed: {ex}")
            raise
    logger.info("figures written to figures/")
