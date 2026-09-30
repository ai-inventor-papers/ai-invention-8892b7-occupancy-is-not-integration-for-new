#!/usr/bin/env python3
"""K2 final assembly: figures F1-F3 and eval_out.json (schema exp_eval_sol_out) + full/mini/preview variants.

Reads only K2 result files (results/, audit/); computes no new coefficient.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from loguru import logger  # noqa: E402

WS = Path(__file__).resolve().parent
RES, FIGS, AUD = WS / "results", WS / "figures", WS / "audit"
FIGS.mkdir(exist_ok=True)
logger.remove()
logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
logger.add(WS / "logs" / "eval.log", rotation="30 MB", level="DEBUG")
FOLDS = ["screen", "heldout", "mesh"]
FNAME = {"screen": "Screen (main)", "heldout": "Held-out (main)", "mesh": "MeSH", "pooled": "IVW pooled"}
COL = {"screen": "#1f77b4", "heldout": "#ff7f0e", "mesh": "#2ca02c", "pooled": "#222222"}
VCODE = {"HOST-SPECIFIC": 1, "MIXED": 0, "GENERIC ACCESSIBILITY": -1, "NOT DETERMINED": np.nan}


def num(x) -> float | None:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if np.isfinite(v) else None


def fig_forest(rows: pd.DataFrame) -> None:
    items = [("M0", "A_cont", "M0: A_cont"), ("M1", "A_cont", "M1: A_cont | G"), ("M2", "A_lift", "M2: A_lift"),
             ("M3", "A_lift", "M3: A_lift | G"), ("M1", "G_H", "M1: G_H"), ("M1", "G_F", "M1: G_F")]
    fig, ax = plt.subplots(figsize=(8, 7.5))
    yt, yl, y = [], [], 0
    for m, v, lab in items:
        for f in FOLDS + ["pooled_IVW"]:
            r = rows[(rows.fold == f) & (rows.model == m) & (rows["var"] == v)]
            if not len(r):
                continue
            r = r.iloc[0]
            key = "pooled" if f == "pooled_IVW" else f
            ax.errorbar(r.irr_sd, y, xerr=[[r.irr_sd - r.irr_sd_lo], [r.irr_sd_hi - r.irr_sd]], fmt="D" if key ==
                        "pooled" else "o", color=COL[key], ms=6 if key == "pooled" else 4, capsize=2)
            yt.append(y)
            yl.append(f"{lab}  [{FNAME[key]}]")
            y -= 1
        y -= 0.6
    ax.axvline(1, color="grey", lw=0.8, ls="--")
    ax.set_xscale("log")
    ax.set_yticks(yt)
    ax.set_yticklabels(yl, fontsize=7.5)
    ax.set_xlabel("IRR per SD (95% CI; CRV1 t(G-1) per fold, IVW normal pooled)")
    ax.set_title("K2: host share vs partner generality (co-primary FE, Y_strict)\nPOST-CONFIRMATION EXPLORATORY",
                 fontsize=10)
    fig.tight_layout()
    for ext in ("png", "pdf"):
        fig.savefig(FIGS / f"F1_k2_forest.{ext}", dpi=200)
    plt.close(fig)


def fig_retention(summ: dict, power: dict) -> None:
    fig, ax = plt.subplots(figsize=(7.5, 4.8))
    keys = FOLDS + ["pooled"]
    for i, k in enumerate(keys):
        d = summ["pooled"] if k == "pooled" else summ["folds"][k]
        pw = power["pooled"] if k == "pooled" else power["folds"][k]
        for dgp, off, c in (("DGP_S", -0.25, "#9ecae1"), ("DGP_G", 0.25, "#fdae6b")):
            q = (pw.get(dgp) or {}).get("ret_q025_q975")
            if q:
                ax.fill_between([i + off - 0.1, i + off + 0.1], q[0], q[1], color=c, alpha=0.8,
                                label=("simulated ret range, host-specific DGP" if dgp == "DGP_S" else
                                       "simulated ret range, generic DGP") if i == 0 else None)
        lo, hi = d["ret_ci"]
        ax.errorbar(i, d["ret"], yerr=[[d["ret"] - lo], [hi - d["ret"]]], fmt="D" if k == "pooled" else "o",
                    color=COL[k], capsize=4, ms=7)
        ax.text(i + 0.06, d["ret"], f"{d['ret']:.2f}", fontsize=8, va="bottom")
    ax.axhline(0.5, color="red", ls="--", lw=1, label="rule threshold 0.5")
    ax.axhline(1.0, color="grey", ls=":", lw=0.8)
    ax.set_xticks(range(len(keys)))
    ax.set_xticklabels([FNAME[k] for k in keys])
    ax.set_ylabel("retention b_A(M1) / b_A(M0)\n(95% concept-bootstrap CI)")
    ax.set_title("Share of the A_cont effect retained after partner-generality controls", fontsize=10)
    ax.legend(fontsize=7, loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=3, frameon=False)
    fig.tight_layout()
    for ext in ("png", "pdf"):
        fig.savefig(FIGS / f"F2_retention.{ext}", dpi=200)
    plt.close(fig)


def within(df: pd.DataFrame, cols: list[str]) -> np.ndarray:
    sys.path.insert(0, str(WS / "d2" / "src"))
    import ppml
    fes = [pd.factorize(df[c])[0] for c in ("concept_id", "e", "d")]
    return ppml._demean(df[cols].to_numpy(float), np.ones(len(df)), fes)


def fig_scatter(pg: pd.DataFrame) -> None:
    fig, axs = plt.subplots(1, 2, figsize=(9, 4))
    for f in FOLDS:
        d = pg[(pg.fold == f)].dropna(subset=["A_cont", "G_H", "G_F"])
        M = within(d, ["A_cont", "G_H", "G_F"])
        for j, (ax, g) in enumerate(zip(axs, ("G_H", "G_F"))):
            r = np.corrcoef(M[:, 0], M[:, j + 1])[0, 1]
            ax.scatter(M[:, j + 1], M[:, 0], s=4, alpha=0.35, color=COL[f], label=f"{FNAME[f]} (r={r:.2f})")
    for ax, g in zip(axs, ("G_H (normalised entropy)", "G_F (log block frequency)")):
        ax.set_xlabel(f"within-FE {g}")
        ax.set_ylabel("within-FE A_cont")
        ax.legend(fontsize=7, markerscale=3)
    fig.suptitle("Host share vs partner generality after concept + e + d FE (K2 input samples)", fontsize=10)
    fig.tight_layout()
    for ext in ("png", "pdf"):
        fig.savefig(FIGS / f"F3_generality_scatter.{ext}", dpi=200)
    plt.close(fig)


def metrics(summ, power, plc, aud, gates, desc) -> dict:
    m = {}
    P = summ["pooled"]
    m["k2_ret_pooled"], (m["k2_ret_pooled_lo"], m["k2_ret_pooled_hi"]) = P["ret"], P["ret_ci"]
    m["k2_pct_removed_pooled"] = P["pct_removed"]
    m["k2_ret_lift_pooled"], (m["k2_ret_lift_pooled_lo"], m["k2_ret_lift_pooled_hi"]) = P["ret_lift"], P["ret_lift_ci"]
    m["k2_verdict_pooled"] = VCODE[P["verdict"]]
    for key in ("M0_A_cont", "M1_A_cont", "M2_A_lift", "M3_A_lift", "M1_G_H", "M1_G_F", "M3_G_H", "M3_G_F"):
        m[f"k2_pooled_{key}_irr_sd"] = P[key]["irr_sd"]
        m[f"k2_pooled_{key}_lo"] = P[key]["irr_sd_lo"]
        m[f"k2_pooled_{key}_hi"] = P[key]["irr_sd_hi"]
        m[f"k2_pooled_{key}_I2"] = P[key]["I2"]
        m[f"k2_pooled_{key}_pQ"] = P[key]["p_Q"]
    m["k2_n_qualifiers_pooled"] = len(P["qualifiers"])
    for f in FOLDS:
        d = summ["folds"][f]
        m[f"k2_ret_{f}"], (m[f"k2_ret_{f}_lo"], m[f"k2_ret_{f}_hi"]) = d["ret"], d["ret_ci"]
        m[f"k2_ret_lift_{f}"], (m[f"k2_ret_lift_{f}_lo"], m[f"k2_ret_lift_{f}_hi"]) = d["ret_lift"], d["ret_lift_ci"]
        m[f"k2_verdict_{f}"] = VCODE[d["verdict"]]
        m[f"k2_n_qualifiers_{f}"] = len(d["qualifiers"])
        for key in ("M0_A_cont", "M1_A_cont", "M2_A_lift", "M3_A_lift", "M1_G_H", "M1_G_F"):
            x = d[key]
            for s_ in ("irr_sd", "irr_sd_lo", "irr_sd_hi", "p_crv1", "p_wild", "p_placebo_cal", "p_rand", "p_holm"):
                if x.get(s_) is not None:
                    m[f"k2_{f}_{key}_{s_}"] = x[s_]
        m[f"k2_{f}_N"], m[f"k2_{f}_G"] = d["M0_A_cont"]["N"], d["M0_A_cont"]["G"]
        m[f"k2_{f}_N_input"] = d["M0_A_cont"]["N_input"]
        m[f"k2_{f}_gate_A_max_abs_diff"] = gates[f]["gate_A"]["max_abs_diff"]
        m[f"k2_{f}_gate_B_abs_d_ln_irr"] = gates[f]["gate_B"]["abs_d_ln_irr_sd"]
        m[f"k2_{f}_gate_pass"] = int(gates[f]["status"] == "PASS")
        pw = power["folds"][f]
        m[f"k2_{f}_power_P_ret_ge05_DGP_S"] = pw["DGP_S"]["P_ret_ge_0.5"]
        if pw.get("DGP_G"):
            m[f"k2_{f}_power_P_ret_lt05_DGP_G"] = pw["DGP_G"]["P_ret_lt_0.5"]
        m[f"k2_{f}_within_R2_A_on_G"] = desc[f]["within_fe_R2_A_cont_on_G"]
        m[f"k2_{f}_within_r_A_GH"] = desc[f]["within_fe_r"]["A_cont~G_H"]
        m[f"k2_{f}_within_r_A_GF"] = desc[f]["within_fe_r"]["A_cont~G_F"]
        m[f"k2_{f}_share_within_var_Alift_from_ln_s_dB"] = desc[f]["share_within_var_A_lift_from_ln_s_dB"]
        m[f"k2_{f}_corr_Alift_lnAcont_within"] = desc[f]["within_fe_r"]["A_lift~ln_A_cont"]
        m[f"k2_{f}_n_zero_A"] = desc[f]["lift"]["n_zero_A"]
        pf = plc["folds"][f]
        m[f"k2_{f}_S10_placebo_M1_pass"] = int(pf["plac_M1"]["PASS"])
        m[f"k2_{f}_S10_placebo_M1_share_pos_sig"] = pf["plac_M1"]["share_pos_sig"]
        m[f"k2_{f}_S10_placebo_M1_median_irr"] = pf["plac_M1"]["median_irr_sd"]
        m[f"k2_{f}_S10_placebo_noG_share_pos_sig"] = pf["plac_noG"]["share_pos_sig"]
        sp = summ["supplementary"][f]
        for k in ("S2", "S6", "S7"):
            if sp.get(k, {}).get("ret") is not None:
                m[f"k2_{f}_{k}_ret"] = sp[k]["ret"]
        if "S1" in sp:
            m[f"k2_{f}_S1_ret"] = sp["S1"]["ret"]
            m[f"k2_{f}_S1_thin"] = int(sp["S1"]["thin_cell_underpowered"])
        m[f"k2_{f}_S3_ret_NAT"] = sp["S3"]["NAT"]["ret"]
        m[f"k2_{f}_S3_ret_ADJ"] = sp["S3"]["ADJ"]["ret"]
        m[f"k2_{f}_S4_A_spec_irr_sd"] = sp["S4"]["irr_sd"]
        m[f"k2_{f}_S5_A_resid_irr_sd"] = sp["S5"]["irr_sd"]
    m["k2_pooled_power_P_ret_ge05_DGP_S"] = power["pooled"]["DGP_S"].get("P_ret_ge_0.5")
    m["k2_pooled_power_P_ret_lt05_DGP_G"] = power["pooled"]["DGP_G"].get("P_ret_lt_0.5")
    for k, v in aud["summary"].items():
        m[f"k2_audit_{k}_pass"] = int(v)
    s2b = json.loads((RES / "k2_s2b_diagnostic.json").read_text())
    m["k2_posthoc_S2b_ret_pooled"] = s2b["pooled"]["S2b_ret"]
    m["k2_posthoc_S2b_A_cont_irr_sd_pooled"], m["k2_posthoc_S2b_A_cont_lo_pooled"], m["k2_posthoc_S2b_A_cont_hi_pooled"] = \
        s2b["pooled"]["S2b_A_cont_irr_sd"]
    for f in FOLDS:
        m[f"k2_posthoc_S2b_ret_{f}"] = s2b["folds"][f]["S2b_ret"]
        m[f"k2_{f}_within_r_A_GHnat"] = s2b["folds"][f]["within_fe_r_with_A_cont"]["GH_nat"]
    m["k2_audit_entries_max_abs_diff"] = aud["a_entries"]["max_abs_diff"]
    m["k2_audit_pooled_ret_pyfixest"] = aud["b_pyfixest"]["pooled_ret_pf"]
    return {k: float(v) for k, v in m.items() if num(v) is not None}


def datasets(rows: pd.DataFrame, pg: pd.DataFrame) -> list[dict]:
    ex = []
    idcols = ["fold", "model", "spec", "var", "label", "row_type"]
    for r in rows.to_dict("records"):
        inp = {k: r.get(k) for k in idcols if pd.notna(r.get(k))}
        stats = {k: num(v) for k, v in r.items() if k not in idcols and num(v) is not None}
        e = {"input": json.dumps(inp), "output": json.dumps(stats),
             "metadata_fold": str(r.get("fold")), "metadata_model": str(r.get("model")),
             "metadata_var": str(r.get("var")), "metadata_label": str(r.get("label")),
             "metadata_source": str(r.get("source")) if pd.notna(r.get("source")) else "",
             "metadata_note": str(r.get("note")) if pd.notna(r.get("note")) else ""}
        for k in ("irr_sd", "irr_sd_lo", "irr_sd_hi", "p_crv1", "p_wild", "p_rand", "p_placebo_cal", "b", "se", "N", "G"):
            if num(r.get(k)) is not None:
                e[f"eval_{k}"] = num(r.get(k))
        ex.append(e)
    ev = []
    for r in pg.to_dict("records"):
        inp = {"fold": r["fold"], "concept_id": r["concept_id"], "d": int(r["d"]), "e": int(r["e"]), "o": int(r["o"])}
        outp = {k: num(r[k]) for k in ("A_cont", "A_lift", "s_dB", "G_H", "G_F", "G_H_ub", "G_H_bg", "NAT", "ADJ",
                                       "A_spec", "cov", "n_prof_tags", "n_gen_tags")}
        e = {"input": json.dumps(inp), "output": json.dumps(outp), "metadata_fold": r["fold"],
             "metadata_concept_id": r["concept_id"]}
        for k in ("A_cont", "A_lift", "G_H", "G_F", "s_dB", "A_spec"):
            if num(r[k]) is not None:
                e[f"eval_{k}"] = num(r[k])
        ev.append(e)
    return [{"dataset": "k2_rows", "examples": ex}, {"dataset": "entry_generality", "examples": ev}]


@logger.catch(reraise=True)
def main() -> None:
    summ = json.loads((RES / "k2_summary.json").read_text())
    power = json.loads((RES / "k2_power.json").read_text())
    plc = json.loads((RES / "k2_placebo_host.json").read_text())
    aud = json.loads((AUD / "audit_k2.json").read_text())
    gates = json.loads((RES / "gates.json").read_text())
    desc = json.loads((RES / "k2_descriptives.json").read_text())
    rows = pd.read_csv(RES / "k2_rows.csv")
    pg = pd.read_parquet(RES / "partner_generality.parquet")
    fig_forest(rows)
    fig_retention(summ, power)
    fig_scatter(pg)
    logger.info("figures written")
    out = {"metadata": {
        "evaluation_name": "K2 host-specific vs generic accessibility (POST-CONFIRMATION EXPLORATORY)",
        "spec_sha256": summ["spec_sha256"],
        "verdict_pooled": summ["pooled"]["verdict"], "qualifiers_pooled": summ["pooled"]["qualifiers"],
        "verdicts_folds": {f: summ["folds"][f]["verdict"] for f in FOLDS},
        "qualifiers_folds": {f: summ["folds"][f]["qualifiers"] for f in FOLDS},
        "verdict_coding": "k2_verdict_*: 1 HOST-SPECIFIC, 0 MIXED, -1 GENERIC ACCESSIBILITY",
        "decision_rule": json.loads((RES / "k2_spec.json").read_text())["decision_rule_verbatim"],
        "sources": "results/k2_summary.json, results/k2_rows.csv, results/k2_power.json, "
                   "results/k2_placebo_host.json, audit/audit_k2.json, results/gates.json"},
        "metrics_agg": metrics(summ, power, plc, aud, gates, desc),
        "datasets": datasets(rows, pg)}
    (WS / "eval_out.json").write_text(json.dumps(out, indent=1))
    logger.info(f"eval_out.json: {len(out['metrics_agg'])} metrics; datasets "
                f"{[(d['dataset'], len(d['examples'])) for d in out['datasets']]}")


if __name__ == "__main__":
    sys.exit(main())
