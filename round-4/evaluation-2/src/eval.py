#!/usr/bin/env python3
"""Evaluation assembly for the iteration-4 D2 held-out confirmation + G1-G3 artefact tests.

Reads the outputs of the staged scripts (see README.md for the run order), then
  * recounts the iteration-3 robustness grid from d2/results/d2_robustness.csv by a declared rule (Step 4),
  * applies the frozen mechanism rule to the pooled G rows (results/mechanism_label.json),
  * writes results/record_of_numbers.csv (one row per reported number with its source path and fold label),
  * draws the figures (figures/*.png + *.pdf),
  * writes eval_out.json (exp_eval_sol_out schema): metrics_agg + datasets d2_heldout_events and g_rows.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from loguru import logger

WS = Path(__file__).resolve().parent
RES, FIGS, D2 = WS / "results", WS / "figures", WS / "d2"
RUN_REL = "round-4/evaluation-2/src"  # this workspace relative to the run root
FIGS.mkdir(exist_ok=True)
(WS / "logs").mkdir(exist_ok=True)
logger.remove()
logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
logger.add(WS / "logs" / "eval.log", rotation="30 MB", level="DEBUG")


def jload(p: Path) -> dict | None:
    return json.loads(p.read_text()) if p.exists() else None


def degenerate(lo, hi, v) -> bool:
    """Post-hoc flag (not a spec change): separation-like fits with an exploding IRR or CI are not interpretable."""
    lo, hi, v = num(lo), num(hi), num(v)
    if v is None or lo is None or hi is None:
        return False
    return bool(v < 0.01 or v > 100 or lo <= 0 or hi / max(lo, 1e-300) > 50)


def num(x) -> float | None:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if np.isfinite(v) else None


# ------------------------------------------------------------------------------------------------ Step 4 recount
def robustness_recount() -> dict:
    r = pd.read_csv(D2 / "results" / "d2_robustness.csv")
    out = {"rule": "rows with a non-null irr_sd_A; significant = irr_sd_A_lo > 1 AND p_A < 0.05; counted per FE spec; "
                   "second denominator excludes the base row 'PRIMARY (MAIN)' and the 3 descriptive field-group strata; "
                   "IRR range over significant rows excludes the A_cont_hi bound (different scale)",
           "source": "round-3/experiment-7/src/results/d2_robustness.csv"}
    for fe in ("secondary", "primary"):
        x = r[(r.fe == fe) & r.irr_sd_A.notna()].copy()
        x["sig"] = (x.irr_sd_A_lo > 1) & (x.p_A < 0.05)
        ex = x[~x.spec.str.startswith("PRIMARY (MAIN)") & ~x.spec.str.contains("descriptive")]
        x["degenerate"] = [degenerate(a, b, c) for a, b, c in zip(x.irr_sd_A_lo, x.irr_sd_A_hi, x.irr_sd_A)]
        rng = x[x.sig & ~x.spec.str.contains("A_cont_hi") & ~x.degenerate]
        out[fe] = {"n_rows_with_A": int(len(x)), "n_significant": int(x.sig.sum()),
                   "n_rows_excl_base_and_strata": int(len(ex)), "n_significant_excl_base_and_strata": int(ex.sig.sum()),
                   "irr_range_significant_excl_hi_bound": [num(rng.irr_sd_A.min()), num(rng.irr_sd_A.max())],
                   "null_rows": [{"spec": s.spec, "irr_sd_A": num(s.irr_sd_A), "ci": [num(s.irr_sd_A_lo), num(s.irr_sd_A_hi)],
                                  "p_A": num(s.p_A), "N": num(s.N), "G": num(s.G)} for s in x[~x.sig].itertuples()],
                   "degenerate_rows (counted above, excluded from the IRR range)": x[x.degenerate].spec.tolist(),
                   "n_significant_non_degenerate": int((x.sig & ~x.degenerate).sum()),
                   "rows_without_A_or_failed": [s for s in r[(r.fe == fe) & r.irr_sd_A.isna()].spec.tolist()]}
    (RES / "robustness_recount.json").write_text(json.dumps(out, indent=1))
    return out


# ------------------------------------------------------------------------------------------------ mechanism label
def mechanism_label(spec: dict) -> dict | None:
    ps = jload(RES / "g_pooled_summary.json")
    if ps is None:
        return None
    rows = pd.read_csv(RES / "g_pooled_rows.csv")
    g1 = rows[(rows.row == "G1-multi (co-primary FE)") & (rows["var"] == "A_cont")].iloc[0]
    mde = spec["mde"]["G1_multi_pooled_projected"]["MDE_irr_sd_power80"]
    g1_null = not (g1.irr_sd_lo > 1 or g1.irr_sd_hi < 1)
    g1_small = g1.irr_sd < 1.10 and g1_null
    pct = ps["G3_pct"]["G3(combined)"]["pct"]
    art = bool(g1_small and mde is not None and mde <= 1.20 and pct is not None and pct > 50 and g1.G >= 30)
    g2 = ps["G2a"]["reading"]
    if art:
        label = "artefact"
    elif g2.startswith("grafting"):
        label = "grafting"
    elif g2.startswith("host-vocabulary"):
        label = "host-vocabulary"
    else:
        label = "unresolved"
    out = {"label": label, "scope": "pooled screen + held-out; partially pre-specified (held-out G rows were not in the "
                                    "frozen heldout_spec; screen G rows were not blind)",
           "inputs": {"G1_multi_irr_sd": g1.irr_sd, "G1_multi_ci": [g1.irr_sd_lo, g1.irr_sd_hi], "G1_multi_G": int(g1.G),
                      "G1_mde_pooled_projected": mde, "G1_status": ps["G1_status"]["label"],
                      "G3_combined_pct_logirr_removed": pct,
                      "G3_combined_pct_ci": ps["G3_pct"]["G3(combined)"].get("ci95"), "G2a_reading": g2,
                      "G2a_NAT": {k: ps["G2a"]["NAT"].get(k) for k in ("irr_sd", "irr_sd_lo", "irr_sd_hi", "p")},
                      "G2a_ADJ": {k: ps["G2a"]["ADJ"].get(k) for k in ("irr_sd", "irr_sd_lo", "irr_sd_hi", "p")}},
           "artefact_conditions": {"G1_multi_irr_lt_1.10_and_ci_includes_1": bool(g1_small),
                                   "G1_mde_le_1.20": bool(mde is not None and mde <= 1.20),
                                   "G3_combined_removes_gt_50pct": bool(pct is not None and pct > 50),
                                   "G1_G_ge_30": bool(g1.G >= 30)},
           "placebo_host_qualifier": {k: {"PASS": v["PASS"], "share_pos_sig": v["share_pos_sig"],
                                          "median_irr_sd": v["placebo_irr_sd_median"]}
                                      for k, v in ps["placebo_host"].items()},
           "rule": spec["definitions"]["mechanism_rule"]}
    (RES / "mechanism_label.json").write_text(json.dumps(out, indent=1, default=float))
    return out


# ------------------------------------------------------------------------------------------------ record
def record(conf: dict | None, post: dict | None, rec: dict) -> pd.DataFrame:
    recs = []
    lab = {"screen": "SCREEN", "heldout": "SUPPLEMENTARY", "pooled": "SUPPLEMENTARY"}
    for fold in ("screen", "heldout", "pooled"):
        p = RES / f"g_{fold}_rows.csv"
        if not p.exists():
            continue
        for r in pd.read_csv(p).itertuples():
            if pd.isna(getattr(r, "irr_sd", np.nan)):
                continue
            dg = " [DEGENERATE FIT: not interpretable]" if degenerate(r.irr_sd_lo, r.irr_sd_hi, r.irr_sd) else ""
            recs.append({"number": f"{r.row} | {r.var} IRR/SD{dg}", "value": r.irr_sd, "CI": f"[{r.irr_sd_lo:.4g}, {r.irr_sd_hi:.4g}]",
                         "p": r.p, "p_wild": getattr(r, "p_wild", None), "N": r.N, "G": r.G, "spec": r.spec,
                         "source_path": f"{RUN_REL}/results/g_{fold}_rows.csv", "fold": fold, "label": lab[fold]})
    if conf:
        for sp in ("primary", "secondary"):
            r = conf.get(sp)
            if not r:
                continue
            for v in ("A_cont", "CT"):
                ci = r["ci_irr_sd"][v]
                recs.append({"number": f"D2 held-out {sp} {v} IRR/SD", "value": r["irr_sd"][v],
                             "CI": f"[{ci[0]:.4f}, {ci[1]:.4f}]", "p": r["p"][v], "p_wild": r["p_wild"][v],
                             "N": r["n_retained"], "G": r["G"], "spec": sp,
                             "source_path": f"{RUN_REL}/d2/results/heldout_confirmation.json", "fold": "heldout",
                             "label": "CONFIRMATORY"})
    scr = jload(D2 / "results" / "heldout_dryrun_on_screen.json")
    for sp in ("primary", "secondary"):
        r = scr[sp]
        ci = r["ci_irr_sd"]["A_cont"]
        recs.append({"number": f"D2 screen {sp} A_cont IRR/SD (dry-run reproduction)", "value": r["irr_sd"]["A_cont"],
                     "CI": f"[{ci[0]:.4f}, {ci[1]:.4f}]", "p": r["p"]["A_cont"], "p_wild": r["p_wild"]["A_cont"],
                     "N": r["n_retained"], "G": r["G"], "spec": sp,
                     "source_path": f"{RUN_REL}/d2/results/heldout_dryrun_on_screen.json", "fold": "screen",
                     "label": "SCREEN"})
    if post is not None and Path(RES / "heldout_robustness.csv").exists():
        for r in pd.read_csv(RES / "heldout_robustness.csv").itertuples():
            if pd.isna(getattr(r, "irr_sd_A", np.nan)):
                continue
            recs.append({"number": f"held-out robustness: {r.spec} A IRR/SD", "value": r.irr_sd_A,
                         "CI": f"[{r.irr_sd_A_lo:.4f}, {r.irr_sd_A_hi:.4f}]", "p": r.p_A, "p_wild": None, "N": r.N,
                         "G": r.G, "spec": r.fe, "source_path": f"{RUN_REL}/results/heldout_robustness.csv",
                         "fold": "heldout", "label": "CONFIRMATORY"})
    for fe in ("secondary", "primary"):
        recs.append({"number": f"iteration-3 robustness recount ({fe}): significant rows", "value": rec[fe]["n_significant"],
                     "CI": f"of {rec[fe]['n_rows_with_A']} rows with an A term", "p": None, "p_wild": None, "N": None,
                     "G": None, "spec": fe, "source_path": f"{RUN_REL}/results/robustness_recount.json",
                     "fold": "screen", "label": "SCREEN"})
    df = pd.DataFrame(recs)
    df.to_csv(RES / "record_of_numbers.csv", index=False)
    return df


# ------------------------------------------------------------------------------------------------ figures
def figures(conf: dict | None, spec: dict) -> list[str]:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.ticker
    plt.rcParams.update({"font.size": 9, "pdf.fonttype": 42})
    col = {"screen": "#4C72B0", "heldout": "#DD8452", "pooled": "#55A868"}
    made = []
    tabs = {f: pd.read_csv(RES / f"g_{f}_rows.csv") for f in ("screen", "heldout", "pooled") if (RES / f"g_{f}_rows.csv").exists()}
    if not tabs:
        return made
    # F1 forest
    keys = [("G1-multi (co-primary FE)", "A_cont"), ("G1-multi, MAIN only", "A_cont"), ("G1-single complement", "A_cont"),
            ("G1-all-window", "A_cont"), ("G2a NATIVE+ADJACENT (native>=0.3, adjacent [0.05,0.3))", "NAT"),
            ("G2a NATIVE+ADJACENT (native>=0.3, adjacent [0.05,0.3))", "ADJ"),
            ("G3 base: co-primary (reports mean_topic_score = G3(i))", "A_cont"), ("G3(combined)", "A_cont"),
            ("G3 restriction: entry papers topic_score >= 0.9", "A_cont"),
            ("G3(iii) venue agreement (coverage-limited)", "A_cont"),
            ("G3(iv) outcome Y_strict_hc (W2 papers with topic_score >= 0.9)", "A_cont")]
    labels = ["G1 multi-team", "G1 multi-team, MAIN", "G1 single-paper", "G1 all window", "G2a NATIVE share",
              "G2a ADJACENT share", "Co-primary A_cont", "G3 combined controls", "G3 topic score >= 0.9",
              "G3(iii) venue (12% cov.)", "G3(iv) outcome topic >= 0.9"]
    fig, ax = plt.subplots(figsize=(7.2, 6.4))
    y0 = 0
    yt, yl = [], []
    if conf:
        for sp, nm in (("secondary", "D2 co-primary (frozen)"), ("primary", "D2 primary (frozen)")):
            sc = jload(D2 / "results" / "heldout_dryrun_on_screen.json")[sp]
            for k, (src, f) in enumerate(((sc, "screen"), (conf.get(sp), "heldout"))):
                if src:
                    v, (lo, hi) = src["irr_sd"]["A_cont"], src["ci_irr_sd"]["A_cont"]
                    ax.errorbar(v, y0 + 0.25 * k, xerr=[[v - lo], [hi - v]], fmt="o", color=col[f], ms=4, capsize=2)
            yt.append(y0 + 0.12)
            yl.append(nm)
            y0 += 1
    for (rw, var), nm in zip(keys, labels):
        for k, f in enumerate(("screen", "heldout", "pooled")):
            if f not in tabs:
                continue
            t = tabs[f]
            x = t[(t.row == rw) & (t["var"] == var)]
            if len(x) and pd.notna(x.irr_sd.iloc[0]):
                v, lo, hi = x.irr_sd.iloc[0], x.irr_sd_lo.iloc[0], x.irr_sd_hi.iloc[0]
                if degenerate(lo, hi, v):
                    ax.text(0.52, y0 + 0.25 * k, f"{f}: degenerate fit", color=col[f], fontsize=6, va="center")
                    continue
                ax.errorbar(v, y0 + 0.25 * k, xerr=[[v - lo], [hi - v]], fmt="o", color=col[f], ms=4, capsize=2)
            elif f in tabs:
                ax.text(0.52, y0 + 0.25 * k, f"{f}: fit failed", color=col[f], fontsize=6, va="center")
        yt.append(y0 + 0.25)
        yl.append(nm)
        y0 += 1
    ax.axvline(1, color="grey", lw=0.8, ls="--")
    ax.set_yticks(yt)
    ax.set_yticklabels(yl)
    ax.invert_yaxis()
    ax.set_xscale("log")
    ax.set_xlim(0.5, 3.5)
    ax.set_xticks([0.5, 0.75, 1, 1.5, 2, 3])
    ax.set_xticklabels(["0.5", "0.75", "1", "1.5", "2", "3"])
    ax.xaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())
    ax.set_xlabel("IRR per SD of the regressor (95% CI, log scale)")
    for f in col:
        ax.plot([], [], "o", color=col[f], label=f)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.08), ncol=3, frameon=False)
    ax.set_title("Screen vs held-out vs pooled: D2 co-primary and G1-G3 rows")
    fig.tight_layout()
    for ext in ("png", "pdf"):
        fig.savefig(FIGS / f"F1_forest_screen_heldout_pooled.{ext}", dpi=200)
    plt.close(fig)
    made.append("figures/F1_forest_screen_heldout_pooled.png")
    # F2 G2 heatmap
    folds = [f for f in ("screen", "pooled") if f in tabs]
    fig, axes = plt.subplots(len(folds), 2, figsize=(8, 3.4 * len(folds)), squeeze=False,
                             gridspec_kw={"wspace": 0.45, "hspace": 0.45})
    P = spec["parameters"]
    for i, f in enumerate(folds):
        t = tabs[f]
        t = t[t.row.str.startswith("G2a")]
        for j, var in enumerate(("NAT", "ADJ")):
            M = np.full((3, 3), np.nan)
            S = np.full((3, 3), "", dtype=object)
            for a, nc in enumerate(P["g2_native_cuts"]):
                for b, al in enumerate(P["g2_adjacent_lower_cuts"]):
                    x = t[(t.nat_cut == nc) & (t.adj_lo == al) & (t["var"] == var)]
                    if len(x) and pd.notna(x.irr_sd.iloc[0]):
                        M[a, b] = x.irr_sd.iloc[0]
                        S[a, b] = f"{x.irr_sd.iloc[0]:.2f}\n[{x.irr_sd_lo.iloc[0]:.2f},{x.irr_sd_hi.iloc[0]:.2f}]"
            ax = axes[i, j]
            im = ax.imshow(M, cmap="RdBu_r", vmin=0.5, vmax=1.5)
            for a in range(3):
                for b in range(3):
                    dark = np.isfinite(M[a, b]) and M[a, b] > 1.33
                    ax.text(b, a, S[a, b], ha="center", va="center", fontsize=7, color="white" if dark else "black")
            ax.set_xticks(range(3))
            ax.set_xticklabels([str(x) for x in P["g2_adjacent_lower_cuts"]])
            ax.set_yticks(range(3))
            ax.set_yticklabels([str(x) for x in P["g2_native_cuts"]])
            ax.set_xlabel("adjacent lower cut")
            ax.set_ylabel("native cut")
            ax.set_title(f"{f}: {'NATIVE' if var == 'NAT' else 'ADJACENT'} share IRR/SD")
    fig.colorbar(im, ax=axes.ravel().tolist(), shrink=0.7)
    for ext in ("png", "pdf"):
        fig.savefig(FIGS / f"F2_G2_threshold_heatmap.{ext}", dpi=200)
    plt.close(fig)
    made.append("figures/F2_G2_threshold_heatmap.png")
    # F3 placebo host
    fs = [f for f in ("screen", "heldout", "pooled") if (RES / f"g_placebo_host_draws_{f}.csv").exists()]
    fig, axes = plt.subplots(1, len(fs), figsize=(3.4 * len(fs), 2.9), squeeze=False)
    for i, f in enumerate(fs):
        d = pd.read_csv(RES / f"g_placebo_host_draws_{f}.csv")
        ax = axes[0, i]
        for strat, c in (("size", "#4C72B0"), ("prox", "#C44E52")):
            v = d[(d.strat == strat) & d.plac_ok].plac_irr_sd_plac
            ax.hist(v, bins=20, alpha=0.6, color=c, label=f"placebo host ({strat} decile)")
        t = tabs[f]
        obs = t[(t.row.str.startswith("G3 base")) & (t["var"] == "A_cont")].irr_sd.iloc[0]
        ax.axvline(obs, color="k", lw=1.2, label=f"observed A_cont {obs:.2f}")
        ax.axvline(1, color="grey", ls="--", lw=0.8)
        ax.set_title(f"{f}")
        ax.set_xlabel("IRR per SD")
        if i == 0:
            ax.legend(fontsize=6, frameon=False)
    fig.tight_layout()
    for ext in ("png", "pdf"):
        fig.savefig(FIGS / f"F3_placebo_host.{ext}", dpi=200)
    plt.close(fig)
    made.append("figures/F3_placebo_host.png")
    # F4 G1 multi vs single
    fig, ax = plt.subplots(figsize=(6, 2.8))
    rws = [("G1-multi (co-primary FE)", "multi-team"), ("G1-multi, MAIN only", "multi-team MAIN"),
           ("G1-single complement", "single / same team"), ("G1-all-window", "all window entries")]
    for j, (rw, nm) in enumerate(rws):
        for k, f in enumerate(("screen", "heldout", "pooled")):
            if f not in tabs:
                continue
            x = tabs[f][(tabs[f].row == rw) & (tabs[f]["var"] == "A_cont")]
            if len(x) and pd.notna(x.irr_sd.iloc[0]):
                v, lo, hi = x.irr_sd.iloc[0], x.irr_sd_lo.iloc[0], x.irr_sd_hi.iloc[0]
                ax.errorbar(j + 0.2 * (k - 1), v, yerr=[[v - lo], [hi - v]], fmt="o", color=col[f], ms=4, capsize=2,
                            label=f if j == 0 else None)
    ax.axhline(1, color="grey", ls="--", lw=0.8)
    ax.set_xticks(range(len(rws)))
    ax.set_xticklabels([n for _, n in rws])
    ax.set_ylabel("A_cont IRR per SD")
    ax.set_title("G1: two-year entry window, multi-team vs single-paper entries")
    ax.legend(frameon=False, fontsize=7)
    fig.tight_layout()
    for ext in ("png", "pdf"):
        fig.savefig(FIGS / f"F4_G1_multi_vs_single.{ext}", dpi=200)
    plt.close(fig)
    made.append("figures/F4_G1_multi_vs_single.png")
    return made


# ------------------------------------------------------------------------------------------------ eval_out
def g_row_examples() -> list[dict]:
    ex = []
    for fold in ("screen", "heldout", "pooled"):
        p = RES / f"g_{fold}_rows.csv"
        if not p.exists():
            continue
        for r in pd.read_csv(p).to_dict("records"):
            inp = {k: r.get(k) for k in ("row", "fold", "spec", "y", "var", "test", "nat_cut", "adj_lo") if pd.notna(r.get(k))}
            outp = {k: num(r.get(k)) for k in ("b", "se", "p", "irr_sd", "irr_sd_lo", "irr_sd_hi", "irr_01", "p_wild",
                                              "p_placebo_cal", "p_holm_G", "N", "G", "retained_share", "N_input")}
            e = {"input": json.dumps(inp), "output": json.dumps(outp),
                 "metadata_fold": fold, "metadata_label": "SCREEN" if fold == "screen" else "SUPPLEMENTARY",
                 "metadata_row": r["row"], "metadata_var": r["var"]}
            for k in ("irr_sd", "irr_sd_lo", "irr_sd_hi", "p", "p_wild", "p_placebo_cal", "N", "G"):
                v = num(r.get(k))
                if v is not None:
                    e[f"eval_{k}"] = v
            e["eval_ci_excludes_1"] = float(num(r.get("irr_sd_lo")) is not None and
                                            (r["irr_sd_lo"] > 1 or r["irr_sd_hi"] < 1))
            e["eval_degenerate_fit"] = float(degenerate(r.get("irr_sd_lo"), r.get("irr_sd_hi"), r.get("irr_sd")))
            ex.append(e)
    return ex


def heldout_examples() -> list[dict]:
    p = RES / "heldout_event_predictions.parquet"
    if not p.exists():
        return []
    te = pd.read_parquet(p)
    feats = ["A_cont", "CT", "prox_od", "RD", "log_n_partner_tags", "cov", "demic", "mean_topic_score",
             "boundary_share", "abstract_share", "mom_d", "log_centrality", "log_W1", "n_entry_papers"]
    ex = []
    for r in te.itertuples():
        inp = {"concept_id": r.concept_id, "host_subfield_d": int(r.d), "entry_year_e": int(r.e),
               "origin_subfield_o": int(r.o), **{f: num(getattr(r, f)) for f in feats}}
        ex.append({"input": json.dumps(inp), "output": str(int(r.Y_strict)),
                   "predict_coprimary_screen_fit": f"{r.mu1:.6f}", "predict_controls_only": f"{r.mu0:.6f}",
                   "metadata_concept_id": r.concept_id, "metadata_fold": "heldout",
                   "metadata_field_group": r.field_group,
                   "eval_poisson_deviance_coprimary_screen_fit": float(r.dev1),
                   "eval_poisson_deviance_controls_only": float(r.dev0),
                   "eval_deviance_gain": float(r.dev0 - r.dev1)})
    return ex


def _trunc(x, n: int = 200):
    if isinstance(x, str):
        return x[:n]
    if isinstance(x, dict):
        return {k: _trunc(v, n) for k, v in x.items()}
    if isinstance(x, list):
        return [_trunc(v, n) for v in x]
    return x


def write_variants(out: dict) -> None:
    """full = eval_out.json; mini = first 3 examples per dataset; preview = mini with strings cut to 200 chars."""
    (WS / "full_eval_out.json").write_text(json.dumps(out, indent=1, default=float))
    mini = {**out, "datasets": [{**d, "examples": d["examples"][:3]} for d in out["datasets"]]}
    (WS / "mini_eval_out.json").write_text(json.dumps(mini, indent=1, default=float))
    prev = {"metadata": _trunc(out["metadata"]), "metrics_agg": out["metrics_agg"],
            "datasets": [{"dataset": d["dataset"], "examples": _trunc(d["examples"][:3])} for d in out["datasets"]]}
    (WS / "preview_eval_out.json").write_text(json.dumps(prev, indent=1, default=float))


def main() -> None:
    spec = jload(RES / "g_spec.json")
    conf = jload(D2 / "results" / "heldout_confirmation.json")
    post = jload(RES / "heldout_post.json")
    gates = {"R0a": jload(RES / "gate_hashes.json"), "R0c": jload(RES / "gate_r0c.json")}
    rec = robustness_recount()
    mech = mechanism_label(spec) if spec else None
    rn = record(conf, post, rec)
    figs = figures(conf, spec) if spec else []
    M: dict[str, float] = {}

    def put(k, v):
        v = num(v)
        if v is not None:
            M[k] = v

    put("gate_R0a_all_hashes_match", float(bool(gates["R0a"] and gates["R0a"]["all_match"])))
    put("gate_R0c_pass", float(bool(gates["R0c"] and gates["R0c"]["pass"])))
    dry = jload(D2 / "results" / "heldout_dryrun_on_screen.json")
    put("gate_R0b_screen_coprimary_irr_sd", dry["secondary"]["irr_sd"]["A_cont"])
    put("gate_R0b_pass", float(abs(dry["secondary"]["irr_sd"]["A_cont"] - 1.300) < 5e-4 and dry["secondary"]["n_retained"] == 1544
                               and dry["secondary"]["G"] == 140 and dry["primary"]["n_retained"] == 452))
    if conf:
        for sp, tag in (("secondary", "coprimary"), ("primary", "primary")):
            r = conf.get(sp)
            if r:
                put(f"heldout_{tag}_irr_sd", r["irr_sd"]["A_cont"])
                put(f"heldout_{tag}_ci_lo", r["ci_irr_sd"]["A_cont"][0])
                put(f"heldout_{tag}_ci_hi", r["ci_irr_sd"]["A_cont"][1])
                put(f"heldout_{tag}_p", r["p"]["A_cont"])
                put(f"heldout_{tag}_p_wild", r["p_wild"]["A_cont"])
                put(f"heldout_{tag}_ct_irr_sd", r["irr_sd"]["CT"])
                put(f"heldout_{tag}_ct_p", r["p"]["CT"])
                put(f"heldout_{tag}_N", r["n_retained"])
                put(f"heldout_{tag}_G", r["G"])
                put(f"heldout_{tag}_retained_share", r["retained_share"])
            dec = conf.get(f"decision_{sp}")
            if dec:
                put(f"heldout_{tag}_holm_p_A", dec["holm_p"]["A_cont"])
                put(f"heldout_{tag}_reading_grafting", float(dec["reading"] == "GRAFTING"))
    if post:
        f = post["flags"]
        put("d2_dead", float(f["KILL_co_primary_dead"]))
        put("heldout_coprimary_confirmed", float(f["secondary"]["confirmed"]))
        put("heldout_primary_confirmed", float(f["primary"]["confirmed"]))
        put("heldout_primary_inconclusive_underpowered", float(f["primary_label"] == "inconclusive (underpowered)"))
        put("heldout_coprimary_p_placebo_cal", f["secondary"].get("p_placebo_cal_screenSD"))
        put("heldout_coprimary_p_placebo_cal_heldoutSD", f["secondary"].get("p_placebo_cal_heldoutSD"))
        h = f["secondary"].get("heterogeneity_screen_vs_heldout") or {}
        put("heterogeneity_screen_vs_heldout_p", h.get("p"))
        put("heterogeneity_b_diff", h.get("diff"))
        pp = post["nativeness_permutation_placebo"].get("secondary", {})
        put("heldout_perm_placebo_p_coprimary", pp.get("perm_p_two_sided_z"))
        put("heldout_perm_placebo_z_sd_coprimary", pp.get("placebo_z_sd"))
        put("heldout_oos_deviance_diff", post["oos"]["deviance_diff_with_minus_controls"])
        put("heldout_oos_deviance_diff_ci_lo", post["oos"]["ci95_concept_bootstrap"][0])
        put("heldout_oos_deviance_diff_ci_hi", post["oos"]["ci95_concept_bootstrap"][1])
        rb = pd.read_csv(RES / "heldout_robustness.csv")
        x = rb[(rb.fe == "secondary") & rb.irr_sd_A.notna() & ~rb.spec.str.contains("descriptive")]
        put("heldout_robustness_secondary_sig_count", ((x.irr_sd_A_lo > 1) & (x.p_A < 0.05)).sum())
        put("heldout_robustness_secondary_rows", len(x))
        put("d3_heldout_hash_match", float(post["d3_heldout_sha256"]["match"]))
    for fold in ("screen", "heldout", "pooled"):
        p = RES / f"g_{fold}_rows.csv"
        sm = jload(RES / f"g_{fold}_summary.json")
        if not p.exists() or sm is None:
            continue
        t = pd.read_csv(p)

        def g(row, var="A_cont", col="irr_sd"):
            x = t[(t.row == row) & (t["var"] == var)]
            return x[col].iloc[0] if len(x) and col in x else None

        for key, row, var in (("g1_multi", "G1-multi (co-primary FE)", "A_cont"), ("g1_multi_main", "G1-multi, MAIN only", "A_cont"),
                              ("g1_single", "G1-single complement", "A_cont"), ("g1_all_window", "G1-all-window", "A_cont"),
                              ("g1_bridge", "G1-bridge: iteration-3 row (partner window [e,e+1], W2 [e+2,e+6], entry-year controls)", "A_cont_v"),
                              ("g2_native", "G2a NATIVE+ADJACENT (native>=0.3, adjacent [0.05,0.3))", "NAT"),
                              ("g2_adjacent", "G2a NATIVE+ADJACENT (native>=0.3, adjacent [0.05,0.3))", "ADJ"),
                              ("g3_base", "G3 base: co-primary (reports mean_topic_score = G3(i))", "A_cont"),
                              ("g3_combined", "G3(combined)", "A_cont")):
            put(f"{fold}_{key}_irr_sd", g(row, var))
            put(f"{fold}_{key}_ci_lo", g(row, var, "irr_sd_lo"))
            put(f"{fold}_{key}_ci_hi", g(row, var, "irr_sd_hi"))
            put(f"{fold}_{key}_p", g(row, var, "p"))
            put(f"{fold}_{key}_G", g(row, var, "G"))
        put(f"{fold}_g1_multi_share", sm["G1_descriptive"]["share_multi"])
        put(f"{fold}_g1_mde", sm["G1_status"]["mde"])
        gi = sm.get("G1_interaction") or {}
        put(f"{fold}_g1_interaction_ratio", gi.get("ratio_irr_multi_over_single"))
        put(f"{fold}_g1_interaction_p", gi.get("p_interaction"))
        put(f"{fold}_g2_wald_equal_p", sm["G2a"]["wald_equal_per01"].get("p"))
        put(f"{fold}_g2_corr_nat_adj", sm["G2a"]["corr_NAT_ADJ"])
        put(f"{fold}_g2_reading_grafting", float(sm["G2a"]["reading"].startswith("grafting")))
        put(f"{fold}_g2_reading_host_vocabulary", float(sm["G2a"]["reading"].startswith("host-vocabulary")))
        for k, v in sm["G3_pct"].items():
            kk = {"G3(i+) + min_topic_score": "i_plus", "G3(ii) + host_topic_share + sec_host_share": "ii",
                  "G3(combined)": "combined", "G3(iii) + venue_d_share": "iii"}[k]
            put(f"{fold}_g3_{kk}_pct_logirr_removed", v.get("pct"))
            if v.get("ci95"):
                put(f"{fold}_g3_{kk}_pct_ci_lo", v["ci95"][0])
                put(f"{fold}_g3_{kk}_pct_ci_hi", v["ci95"][1])
        for strat, v in sm["placebo_host"].items():
            put(f"{fold}_placebo_host_{strat}_share_pos_sig", v["share_pos_sig"])
            put(f"{fold}_placebo_host_{strat}_median_irr_sd", v["placebo_irr_sd_median"])
            put(f"{fold}_placebo_host_{strat}_pass", float(v["PASS"]))
            put(f"{fold}_placebo_host_{strat}_joint_A_irr_sd_median", v.get("joint_A_cont_irr_sd_median"))
    # headline aliases requested by the plan
    for k_new, k_old in (("g1_multi_irr_sd", "pooled_g1_multi_irr_sd"), ("g1_mde", "pooled_g1_mde"),
                         ("g2_native_irr_sd", "pooled_g2_native_irr_sd"), ("g2_adjacent_irr_sd", "pooled_g2_adjacent_irr_sd"),
                         ("g3_combined_pct_logirr_removed", "pooled_g3_combined_pct_logirr_removed"),
                         ("placebo_host_share_sig", "pooled_placebo_host_size_share_pos_sig")):
        if k_old in M:
            M[k_new] = M[k_old]
    ap = jload(WS / "audit" / "audit_perm.json")  # independent pyfixest audit (audit/audit_perm.py)
    if ap:
        put("audit_heldout_within_concept_perm_p", ap["perm_p_two_sided"])
        put("audit_heldout_within_concept_perm_z_sd", ap["z_sd"])
        put("audit_heldout_shuffled_crv1_reject_rate", ap["share_crv1_p_lt_0.05"])
    ah = jload(WS / "audit" / "audit_headline.json")
    if ah:
        put("audit_heldout_coprimary_irr_sd_abs_diff", abs(ah["heldout_coprimary"]["rederived"]["irr_sd"] -
                                                           ah["heldout_coprimary"]["reported"]["irr_sd"]))
    put("robustness_sig_count", rec["secondary"]["n_significant"])
    put("robustness_denominator", rec["secondary"]["n_rows_with_A"])
    put("robustness_sig_count_excl_base_strata", rec["secondary"]["n_significant_excl_base_and_strata"])
    put("robustness_denominator_excl_base_strata", rec["secondary"]["n_rows_excl_base_and_strata"])
    put("robustness_primary_sig_count", rec["primary"]["n_significant"])
    put("robustness_primary_denominator", rec["primary"]["n_rows_with_A"])
    if mech:
        for lb in ("artefact", "grafting", "host-vocabulary", "unresolved"):
            M[f"mechanism_label_{lb.replace('-', '_')}"] = float(mech["label"] == lb)
    datasets = []
    he = heldout_examples()
    if he:
        datasets.append({"dataset": "d2_heldout_events", "examples": he})
    ge = g_row_examples()
    if ge:
        datasets.append({"dataset": "g_rows", "examples": ge})
    meta = {"evaluation_name": "D2 held-out confirmation (one look) + G1-G3 artefact tests",
            "evaluated_artifact": "art_2Cd2JJypeGuA (iter_3/gen_art/gen_art_experiment_7), vendored in d2/",
            "heldout_spec_sha256": (D2 / "heldout_spec.sha256").read_text().split()[0],
            "g_spec_sha256": (RES / "g_spec.sha256").read_text().split()[0] if (RES / "g_spec.sha256").exists() else None,
            "heldout_lock": (D2 / "results" / "HELDOUT_OPENED.lock").read_text() if (D2 / "results" / "HELDOUT_OPENED.lock").exists() else None,
            "mechanism_label": mech["label"] if mech else None,
            "heldout_flags": post["flags"] if post else None, "figures": figs,
            "labels": "SCREEN = screen fold (not blind); CONFIRMATORY = frozen heldout_spec rows on the held-out fold; "
                      "SUPPLEMENTARY = G rows on held-out / pooled (not pre-declared in heldout_spec)",
            "record_of_numbers": "results/record_of_numbers.csv", "n_record_rows": int(len(rn))}
    out = {"metadata": meta, "metrics_agg": M, "datasets": datasets}
    (WS / "eval_out.json").write_text(json.dumps(out, indent=1, default=float))
    write_variants(out)
    logger.info(f"eval_out.json: {len(M)} metrics, datasets {[(d['dataset'], len(d['examples'])) for d in datasets]}; "
                f"mechanism {meta['mechanism_label']}")


if __name__ == "__main__":
    main()
