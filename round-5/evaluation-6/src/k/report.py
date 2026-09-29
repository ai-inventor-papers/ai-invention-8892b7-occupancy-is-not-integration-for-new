#!/usr/bin/env python3
"""STEP 6: verdicts under the frozen rules (k13_summary.json), figures, record_of_numbers.csv, eval_out.json."""
from __future__ import annotations

import json
import math
import os
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from loguru import logger  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
import k_lib as K  # noqa: E402

logger.remove()
logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
logger.add(K.LOGS / "report.log", rotation="30 MB", level="DEBUG")

R = K.RESULTS
OKABE = ["#0072B2", "#E69F00", "#009E73", "#CC79A7", "#56B4E9", "#D55E00", "#F0E442", "#000000"]
FOLD_COL = {"SCREEN": OKABE[0], "HELDOUT": OKABE[1], "MESH": OKABE[2], "IVW": OKABE[7]}
plt.rcParams.update({"font.size": 9, "pdf.fonttype": 42, "ps.fonttype": 42, "axes.spines.top": False,
                     "axes.spines.right": False})
LABEL = "POST-CONFIRMATION EXPLORATORY"


def load() -> dict:
    j = lambda p: json.loads((R / p).read_text()) if (R / p).exists() else None  # noqa: E731
    c = lambda p: pd.read_csv(R / p) if (R / p).exists() else None  # noqa: E731
    audit_p = K.WS / "audit" / "audit_k.json"
    return {"spec": j("k13_spec.json"), "gates": j("gates.json"), "k1": c("k1_rows.csv"), "dec": j("k1_decomposition.json"),
            "k3": c("k3_rows.csv"), "k3j": j("k3_results.json"), "inf": c("inference_rows.csv"),
            "infj": j("inference_summary.json"), "status": j("stage_status.json") or {},
            "audit": json.loads(audit_p.read_text()) if audit_p.exists() else None,
            "draws": c("inference_draws.csv")}


# ============================================================================================ verdicts
def verdicts(d: dict) -> dict:
    spec, st, audit = d["spec"], d["status"], d["audit"]
    out = {"label": LABEL, "spec_sha256": K.SPEC_HASH_PATH.read_text().split()[0],
           "decision_rules_verbatim": spec["decision_rules_verbatim"]}
    au = audit or {}
    # ---------------- K1
    if st.get("k1", {}).get("status") != "RUN" or d["dec"] is None:
        out["K1"] = {"verdict": "NOT RUN", "code": -1, "reason": st.get("k1")}
    else:
        iv = d["dec"]["ivw"]
        e, i = iv["K1a_LPM_pp_per_sd"], iv["K1b_log_irr_per_sd"]
        ext = not (e["ci"][0] <= 0 <= e["ci"][1])
        itn = not (i["ci"][0] <= 0 <= i["ci"][1])
        v = "BOTH" if ext and itn else "EXTENSIVE" if ext else "INTENSIVE-ONLY" if itn else "UNRESOLVED"
        infr = (d["infj"] or {}).get("rows", {}).get("IVW.K1a_LPM", {})
        p_ivw_rand = infr.get("p_rand_t")
        text = v
        if v in ("EXTENSIVE", "BOTH") and p_ivw_rand is not None and p_ivw_rand > 0.05:
            text += " (not size-robust)"
        mde = spec["MDE"]
        claim = {"EXTENSIVE": "host-leaning entry vocabulary raises the probability that any newcomer uptake starts",
                 "INTENSIVE-ONLY": "host-leaning entries scale uptake that starts for other reasons",
                 "BOTH": "host-leaning entry vocabulary raises both the probability that uptake starts and its size given it starts",
                 "UNRESOLVED": "neither margin is detected; MDEs stated"}[v]
        ll = iv["K1a_loglink_log_per_sd"]
        lg = iv.get("K1a_logit_log_or_per_sd")
        out["K1"] = {
            "verdict": v, "verdict_text": text, "code": spec["verdict_codes"]["K1"][v], "claim": claim,
            "triggering_numbers": {
                "ivw_ext_pp_per_sd": e["est"], "ivw_ext_ci": e["ci"], "ivw_ext_p_normal": e["p"],
                "ivw_ext_p_rand_t": p_ivw_rand, "ivw_int_irr_per_sd": math.exp(i["est"]),
                "ivw_int_ci": [math.exp(i["ci"][0]), math.exp(i["ci"][1])], "ivw_int_p": i["p"],
                "ext_I2": e["I2"], "int_I2": i["I2"]},
            "corroborating": {"ivw_loglink_ratio_per_sd": math.exp(ll["est"]),
                              "ivw_loglink_ci": [math.exp(ll["ci"][0]), math.exp(ll["ci"][1])],
                              "ivw_logit_or_per_sd": None if lg is None else math.exp(lg["est"]),
                              "ivw_logit_ci": None if lg is None else [math.exp(lg["ci"][0]), math.exp(lg["ci"][1])],
                              "ivw_ext_share": iv["ext_share"]["est"], "ivw_ext_share_ci": iv["ext_share"]["ci"]},
            "mde80": {"ext_pp_per_sd": {f: mde["extensive_pp_per_sd"][f]["MDE80"] for f in mde["extensive_pp_per_sd"]},
                      "int_irr_per_sd": {f: mde["intensive_irr_per_sd"][f]["MDE80"] for f in mde["intensive_irr_per_sd"]}},
            "caveat": "intensive margin conditions on Y>=1: descriptive conditional association, not causal (selection)",
            "audit": None if not au else {"K1a_LPM_coef_pass": all(v_["pass_coef_1e-4"] for v_ in au["K1a_LPM"]["folds"].values()),
                                          "K1a_LPM_ivw_pass": au["K1a_LPM"]["pass_ivw_1e-4_pp"]},
            "source": "results/k1_decomposition.json; results/k1_rows.csv; results/inference_rows.csv"}
    # ---------------- K3
    if st.get("k3", {}).get("status") != "RUN" or d["k3j"] is None:
        out["K3"] = {"verdict": "NOT RUN", "reason": st.get("k3")}
    else:
        k = d["k3j"]
        pw, pp = k["wald"]["p_F"], k["p_perm_wald"]
        incl = [g for g, v_ in k["groups"].items() if v_["ci"][0] <= 1 <= v_["ci"][1] and not v_["descriptive_only"]]
        boundary = pw < 0.05 and len(incl) > 0
        if boundary:
            text = f"FIELD BOUNDARY: groups differ (Wald p {pw:.4f}); CI includes 1 for {incl}"
            v = "FIELD BOUNDARY"
        else:
            text = ("no detectable field boundary; the physics screen null is within sampling variation "
                    f"(MDE80 ratio of IRR/SD phys/rest = {k['mde80_ratio']:.3f})")
            v = "NO DETECTABLE FIELD BOUNDARY"
        if (pw < 0.05) != (pp < 0.05):
            text += " (not size-robust)"
        out["K3"] = {"verdict": v, "verdict_text": text, "code": 1 if boundary else 0,
                     "triggering_numbers": {"wald_p_crv1_F": pw, "wald_p_chi2": k["wald"]["p_chi2"], "wald_W": k["wald"]["W"],
                                            "p_perm": pp, "groups_ci_including_1": incl,
                                            "group_irr": {g: [v_["irr_per_pooled_sd"], v_["ci"]] for g, v_ in k["groups"].items()},
                                            "phys_contrast_ratio": k["contrast"]["ratio"], "phys_contrast_ci": k["contrast"]["ci"],
                                            "phys_contrast_p": k["contrast"]["p"], "phys_contrast_p_perm": k["p_perm_contrast"],
                                            "mde80_ratio": k["mde80_ratio"]},
                     "secondary_host_grouping": k["secondary_host"],
                     "audit": None if not au else {"K3_wald_pass": au["K3_wald"].get("pass_p_1e-4"),
                                                   "abs_diff_p": au["K3_wald"].get("abs_diff_p")},
                     "source": "results/k3_results.json; results/k3_rows.csv"}
    # ---------------- INFERENCE
    if st.get("inference", {}).get("status") != "RUN" or d["infj"] is None:
        out["INFERENCE"] = {"verdict": "NOT RUN", "reason": st.get("inference")}
    else:
        rows = d["infj"]["rows"]
        h = rows["HELDOUT.coprimary_A_count"]
        if h["p_rand_t"] > 0.05:
            text = ("HELDOUT: borderline under size-correct inference; the headline leans on the MeSH and IVW rows "
                    f"(MeSH p_rand_t {rows['MESH.coprimary_A_count']['p_rand_t']:.4f}, IVW p_rand_t {rows['IVW.coprimary_A_count']['p_rand_t']:.4f})")
            v = "HELDOUT BORDERLINE"
        else:
            text = f"HELDOUT: survives size-correct inference (randomization-t p {h['p_rand_t']:.4f})"
            v = "HELDOUT SIZE-ROBUST"
        out["INFERENCE"] = {"verdict": v, "verdict_text": text, "headline_p": "randomization-t (plain within-concept shuffle)",
                            "rows": rows,
                            "audit": None if not au else {"heldout_rand_pass": au["heldout_rand_t"]["pass_within_2mcse"],
                                                          "audit_p": au["heldout_rand_t"]["p"], "tolerance": au["heldout_rand_t"]["tolerance_2mcse"]},
                            "source": "results/inference_summary.json; results/inference_rows.csv"}
    out["audit_all_pass"] = None if not au else au.get("all_pass")
    lock = Path(os.environ.get("AII_DEPS_ROOT", K.WS.parents[2])) / "iter_4/gen_art/gen_art_evaluation_2/d2/results/HELDOUT_OPENED.lock"
    lb = d["gates"]["R0a"]["lock_before"]
    try:  # art_WZ8fbLn79nCq lock; absent in a clone without that sibling folder -> None (not checked)
        out["heldout_lock_untouched"] = bool(K.sha256_file(lock) == lb["sha256"])
    except FileNotFoundError:
        out["heldout_lock_untouched"] = None
    out["gates"] = {"fold_pass": d["gates"]["fold_pass"], "R0d_pytest": d["gates"]["R0d"]["pass"]}
    out["stage_status"] = st
    return K.clean(out)


# ============================================================================================ figures
def save(fig, name: str) -> None:
    for ext in ("png", "pdf"):
        fig.savefig(K.FIGS / f"{name}.{ext}", dpi=200, bbox_inches="tight")
    plt.close(fig)


def fig_margin(d: dict) -> None:
    k1, spec = d["k1"], d["spec"]
    fig, axs = plt.subplots(1, 2, figsize=(12, 3.6), gridspec_kw={"wspace": 0.45})
    for ax, test, ivw_key, null, mdekey, xl, tr in (
            (axs[0], "K1a_LPM", "K1f_IVW_K1a_LPM_pp_per_sd", 0.0, "extensive_pp_per_sd", "Extensive: pp per SD of A_cont (LPM, Any = 1[Y>=1])", lambda x: x),
            (axs[1], "K1b", "K1f_IVW_K1b_log_irr_per_sd", 1.0, "intensive_irr_per_sd", "Intensive: IRR per SD (PPML on Y>=1; conditional)", lambda x: x)):
        labels = ["SCREEN", "HELDOUT", "MESH", "IVW"]
        for yi, f in enumerate(labels):
            r = k1[(k1.test == (ivw_key if f == "IVW" else test)) & (k1.fold == f)]
            if r.empty:
                continue
            r = r.iloc[0]
            m = spec["MDE"][mdekey][f]["MDE80"]
            if m is not None:
                lo, hi = (null - m, null + m) if null == 0 else (1 / m, m)
                ax.fill_betweenx([yi - 0.3, yi + 0.3], lo, hi, color="#DDDDDD", zorder=0,
                                 label="MDE80 band (null +/- MDE)" if yi == 0 else None)
            ax.errorbar(r.estimate, yi, xerr=[[r.estimate - r.ci_lo], [r.ci_hi - r.estimate]], fmt="D" if f == "IVW" else "o",
                        color=FOLD_COL[f], capsize=3)
            ax.text(r.ci_hi, yi + 0.18, f" {r.estimate:.3f} [{r.ci_lo:.3f}, {r.ci_hi:.3f}]", fontsize=7)
        ax.axvline(null, color="k", lw=0.8, ls="--")
        x0, x1 = ax.get_xlim()
        ax.set_xlim(x0, x1 + 0.35 * (x1 - x0))
        ax.set_yticks(range(4))
        ax.set_yticklabels(["Screen", "Held-out", "MeSH (biomed)", "IVW"])
        ax.invert_yaxis()
        ax.set_xlabel(xl, fontsize=8)
    axs[0].legend(fontsize=7, loc="lower right", frameon=False)
    fig.suptitle("K1: which margin (post-confirmation exploratory; 95% CI, t(G-1) per fold, normal for IVW)", fontsize=9)
    save(fig, "k1_margin_forest")


def fig_ladder(d: dict) -> None:
    k1 = d["k1"]
    lad = k1[k1.test == "K1d_ladder"]
    order = ["Any", "Y_ge3", "Y_ge5", "EST_bin"]
    names = ["Y>=1", "Y>=3", "Y>=5", "EST_bin"]
    fig, axs = plt.subplots(1, 2, figsize=(9, 3.2))
    for j, f in enumerate(["SCREEN", "HELDOUT", "MESH"]):
        r = lad[lad.fold == f].set_index("outcome").loc[order]
        x = np.arange(4) + (j - 1) * 0.2
        axs[0].errorbar(x, r.estimate, yerr=[r.estimate - r.ci_lo, r.ci_hi - r.estimate], fmt="o", color=FOLD_COL[f],
                        capsize=2, label=f)
        rel = r.estimate / (100 * r.base_rate)
        axs[1].plot(x, rel, "o", color=FOLD_COL[f], label=f)
    for ax in axs:
        ax.axhline(0, color="k", lw=0.8, ls="--")
        ax.set_xticks(range(4))
        ax.set_xticklabels(names)
    axs[0].set_ylabel("pp per SD of A_cont (LPM, 95% CI)")
    axs[1].set_ylabel("effect / base rate")
    axs[0].legend(fontsize=7, frameon=False)
    fig.suptitle("K1d threshold ladder: where along the Y distribution the effect sits", fontsize=9)
    save(fig, "k1_ladder")


def fig_k3(d: dict) -> None:
    k3, kj = d["k3"], d["k3j"]
    rows = k3[k3.test.isin(["K3_group", "K3_SECONDARY_host_group", "K3_MESH_reference"])].reset_index(drop=True)
    fig, ax = plt.subplots(figsize=(7, 3.6))
    cols = {"K3_group": OKABE[0], "K3_SECONDARY_host_group": OKABE[4], "K3_MESH_reference": OKABE[2]}
    lab = []
    for i, r in rows.iterrows():
        ax.errorbar(r.estimate, i, xerr=[[r.estimate - r.ci_lo], [r.ci_hi - r.estimate]], fmt="o", color=cols[r.test], capsize=3)
        ax.text(r.ci_hi, i + 0.2, f" {r.estimate:.3f} [{r.ci_lo:.3f}, {r.ci_hi:.3f}] G={int(r.G)}", fontsize=7)
        pre = {"K3_group": "origin: ", "K3_SECONDARY_host_group": "host (secondary): ", "K3_MESH_reference": ""}[r.test]
        lab.append(pre + str(r.row))
    ax.axvline(1, color="k", lw=0.8, ls="--")
    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels(lab, fontsize=7)
    ax.invert_yaxis()
    ax.set_xlabel("IRR per SD of A_cont (pooled SD for K3 groups; own SD for MeSH)")
    ax.set_title(f"K3 field boundary: Wald (origin, 2 df) p_CRV1 = {kj['wald']['p_F']:.3f}, p_perm = {kj['p_perm_wald']:.3f}; "
                 f"phys/rest ratio {kj['contrast']['ratio']:.3f} (MDE80 {kj['mde80_ratio']:.2f})", fontsize=8)
    save(fig, "k3_field_forest")


def fig_null(d: dict) -> None:
    dd, infj = d["draws"], d["infj"]
    fig, axs = plt.subplots(1, 4, figsize=(12, 2.8))
    for ax, f in zip(axs, ["SCREEN", "HELDOUT", "MESH", "IVW"]):
        if f == "IVW":
            o = infj["rows"]["IVW.coprimary_A_count"]
            fl = ["SCREEN", "HELDOUT", "MESH"]
            sds = {x: infj["rows"][f"{x}.coprimary_A_count"] for x in fl}
            B = np.column_stack([dd[f"{x}_cnt_plain_b"] for x in fl])
            S = np.column_stack([dd[f"{x}_cnt_plain_se"] for x in fl])
            W = 1 / S ** 2
            ts = (W * B).sum(1) / np.sqrt(W.sum(1))  # SD scaling cancels within fold in z (b/se ratio per fold)
            tobs, p = o["z_obs"], o["p_rand_t"]
            del sds
        else:
            o = infj["rows"][f"{f}.coprimary_A_count"]
            ts = dd[f"{f}_cnt_plain_t"].dropna()
            tobs, p = o["t_obs"], o["p_rand_t"]
        ax.hist(ts, bins=40, color=FOLD_COL[f], alpha=0.7)
        ax.axvline(tobs, color="k", lw=1.2)
        for v in (-1.96, 1.96):
            ax.axvline(v, color="grey", ls="--", lw=0.8)
        ax.set_title(f"{f}: t_obs {tobs:.2f}, p_rand {p:.4f}", fontsize=8)
        ax.set_xlabel("null t (within-concept A_cont shuffle)")
    fig.suptitle("Randomization-t null distributions (2,000 draws; dashed = +/-1.96)", fontsize=9, y=1.06)
    save(fig, "inference_null_z")


# ============================================================================================ record + eval_out
def record(d: dict, summ: dict) -> pd.DataFrame:
    rows = []
    RUN = "round-5/evaluation-6/src/"

    def add(label, name, value, source):
        if value is None or (isinstance(value, float) and not np.isfinite(value)):
            return
        rows.append({"label": label, "name": name, "value": value, "source": RUN + source})

    for _, r in d["k1"].iterrows():
        for c in ("estimate", "ci_lo", "ci_hi", "p_crv1", "N", "G", "base_rate", "mde80"):
            v = r.get(c)
            if pd.notna(v):
                add(LABEL, f"k1.{r.test}.{r.fold}.{r.outcome}.{c}", float(v), "results/k1_rows.csv")
    for _, r in d["k3"].iterrows():
        for c in ("estimate", "ci_lo", "ci_hi", "p_crv1", "p_perm", "N", "G", "mde80"):
            v = r.get(c)
            if pd.notna(v):
                add(LABEL if "REFERENCE" not in str(r.label) else "DESCRIPTIVE", f"k3.{r.test}.{r.row}.{c}", float(v), "results/k3_rows.csv")
    for _, r in d["inf"].iterrows():
        if pd.notna(r.value):
            add(LABEL, f"inference.{r.test}.{r.fold}.{r.row}", float(r.value), "results/inference_rows.csv")
    g = d["gates"]
    for f in K.FOLDS:
        for c in ("irr_sd", "N", "G", "p_crv1"):
            add("GATE", f"R0b.{f}.{c}", float(g["R0b"][f][c]), "results/gates.json")
        add("GATE", f"R0b.{f}.ci_lo", g["R0b"][f]["ci"][0], "results/gates.json")
        add("GATE", f"R0b.{f}.ci_hi", g["R0b"][f]["ci"][1], "results/gates.json")
        for c, v in g["R0e"][f].items():
            add("DESCRIPTIVE", f"R0e.{f}.{c}", float(v), "results/gates.json")
    add("GATE", "R0c.heldout_EST_bin_LPM.coef", g["R0c"]["heldout_EST_bin_LPM_secondary"]["coef"], "results/gates.json")
    add("GATE", "R0c.heldout_EST_bin_LPM.p", g["R0c"]["heldout_EST_bin_LPM_secondary"]["p"], "results/gates.json")
    add("GATE", "R0c.heldout_z", g["R0c"]["heldout_coprimary_z"]["z"], "results/gates.json")
    for f, dd in d["dec"]["folds"].items():
        for c in ("b_total_sd", "b_ext_sd", "b_int_sd", "ext_share", "gap_sd", "draws_converged"):
            add(LABEL, f"k1.decomposition.{f}.{c}", float(dd[c]), "results/k1_decomposition.json")
        for c in ("ci_ext_share", "ci_b_ext_sd", "ci_b_int_sd", "ci_gap_sd"):
            add(LABEL, f"k1.decomposition.{f}.{c}.lo", dd[c][0], "results/k1_decomposition.json")
            add(LABEL, f"k1.decomposition.{f}.{c}.hi", dd[c][1], "results/k1_decomposition.json")
    m = d["spec"]["MDE"]
    for kk in ("extensive_pp_per_sd", "intensive_irr_per_sd"):
        for f, v in m[kk].items():
            add("DESCRIPTIVE", f"mde.{kk}.{f}.MDE80", v.get("MDE80"), "results/k13_spec.json")
    add("DESCRIPTIVE", "mde.k3_phys_ratio.MDE80", m["k3_phys_ratio"]["MDE80_ratio"], "results/k13_spec.json")
    if d["audit"]:
        a = d["audit"]
        for f, v in a["K1a_LPM"]["folds"].items():
            add("GATE", f"audit.K1a_LPM.{f}.abs_diff_b", v["abs_diff_b"], "audit/audit_k.json")
        add("GATE", "audit.K3_wald.abs_diff_p", a["K3_wald"].get("abs_diff_p"), "audit/audit_k.json")
        add("GATE", "audit.heldout_rand_t.p", a["heldout_rand_t"]["p"], "audit/audit_k.json")
    df = pd.DataFrame(rows)
    df.to_csv(R / "record_of_numbers.csv", index=False)
    return df


def fnum(x) -> float | None:
    try:
        x = float(x)
    except (TypeError, ValueError):
        return None
    return x if np.isfinite(x) else None


def eval_out(d: dict, summ: dict) -> dict:
    k1, dec, k3j, infj = d["k1"], d["dec"], d["k3j"], d["infj"]
    iv = dec["ivw"]
    rows = infj["rows"]
    t = summ["K1"]["triggering_numbers"]
    ma = {
        "k1_ivw_ext_pp_per_sd": t["ivw_ext_pp_per_sd"], "k1_ivw_ext_pp_per_sd_ci_lo": t["ivw_ext_ci"][0],
        "k1_ivw_ext_pp_per_sd_ci_hi": t["ivw_ext_ci"][1], "k1_ivw_int_irr_sd": t["ivw_int_irr_per_sd"],
        "k1_ivw_int_irr_sd_ci_lo": t["ivw_int_ci"][0], "k1_ivw_int_irr_sd_ci_hi": t["ivw_int_ci"][1],
        "k1_ext_share": iv["ext_share"]["est"], "k1_ext_share_ci_lo": iv["ext_share"]["ci"][0],
        "k1_ext_share_ci_hi": iv["ext_share"]["ci"][1], "k1_verdict_code": summ["K1"]["code"],
        "k1_ivw_loglink_ratio_sd": summ["K1"]["corroborating"]["ivw_loglink_ratio_per_sd"],
        "k1_ivw_logit_or_sd": summ["K1"]["corroborating"]["ivw_logit_or_per_sd"],
        "k1_ivw_ext_p_rand_t": rows["IVW.K1a_LPM"]["p_rand_t"],
        "k1_mde80_ext_ivw_pp": d["spec"]["MDE"]["extensive_pp_per_sd"]["IVW"]["MDE80"],
        "k1_mde80_int_ivw_irr": d["spec"]["MDE"]["intensive_irr_per_sd"]["IVW"]["MDE80"],
        "k3_wald_p": k3j["wald"]["p_F"], "k3_wald_p_chi2": k3j["wald"]["p_chi2"], "k3_perm_p": k3j["p_perm_wald"],
        "k3_phys_contrast": k3j["contrast"]["ratio"], "k3_phys_contrast_ci_lo": k3j["contrast"]["ci"][0],
        "k3_phys_contrast_ci_hi": k3j["contrast"]["ci"][1], "k3_phys_contrast_p": k3j["contrast"]["p"],
        "k3_phys_contrast_p_perm": k3j["p_perm_contrast"], "k3_mde": k3j["mde80_ratio"], "k3_verdict_code": summ["K3"]["code"],
        "k3_irr_phys": k3j["groups"]["Physics/Astro"]["irr_per_pooled_sd"], "k3_irr_cs": k3j["groups"]["CS"]["irr_per_pooled_sd"],
        "k3_irr_other": k3j["groups"]["other"]["irr_per_pooled_sd"],
    }
    for f in ("SCREEN", "HELDOUT", "MESH"):
        r = rows[f"{f}.coprimary_A_count"]
        fl = f.lower()
        ma[f"p_rand_t_{fl}"] = r["p_rand_t"]
        ma[f"p_freedman_lane_{fl}"] = r["p_freedman_lane"]
        ma[f"p_wcr_webb_{fl}"] = r["p_wcr_webb"]
        ma[f"p_wcr_rademacher_{fl}"] = r["p_wcr_rademacher_check"]
        ma[f"p_crv1_{fl}"] = r["p_crv1"]
        ma[f"crv1_null_rejection_{fl}"] = r["crv1_null_rejection_rand_t"]
        ma[f"z_sd_null_{fl}"] = r["z_sd_null_rand_t"]
        ma[f"p_rand_t_k1lpm_{fl}"] = rows[f"{f}.K1a_LPM"]["p_rand_t"]
        lp = k1[(k1.test == "K1a_LPM") & (k1.fold == f)].iloc[0]
        kb = k1[(k1.test == "K1b") & (k1.fold == f)].iloc[0]
        ma[f"k1_ext_pp_per_sd_{fl}"] = lp.estimate
        ma[f"k1_int_irr_sd_{fl}"] = kb.estimate
        ma[f"k1_ext_share_{fl}"] = dec["folds"][f]["ext_share"]
    ma["p_rand_t_ivw"] = rows["IVW.coprimary_A_count"]["p_rand_t"]
    ma["p_freedman_lane_ivw"] = rows["IVW.coprimary_A_count"]["p_freedman_lane"]
    ma["z_ivw"] = rows["IVW.coprimary_A_count"]["z_obs"]
    ma["audit_all_pass"] = 1.0 if summ.get("audit_all_pass") else 0.0
    ma = {k: fnum(v) for k, v in ma.items() if fnum(v) is not None}
    # datasets
    ex_rows = []
    for tbl, name in ((k1, "k1_rows.csv"), (d["k3"], "k3_rows.csv")):
        for _, r in tbl.iterrows():
            fold = r.get("fold", "POOLED") if "fold" in tbl.columns else "POOLED"
            what = r.get("outcome", r.get("row"))
            e = {"input": f"{r.test} | fold={fold} | model={r.get('model', r.get('grouping'))} | outcome/row={what} | unit={r.get('unit')}",
                 "output": (f"{r.estimate:.6g} [{r.ci_lo:.6g}, {r.ci_hi:.6g}]" if pd.notna(r.get("ci_lo")) and pd.notna(r.get("estimate"))
                            else f"{r.get('estimate')}" if pd.notna(r.get("estimate")) else f"NOT ESTIMABLE: {r.get('note')}"),
                 "metadata_test": str(r.test), "metadata_fold": str(fold), "metadata_label": str(r.get("label")),
                 "metadata_note": "" if pd.isna(r.get("note")) else str(r.get("note")),
                 "metadata_source": "round-5/evaluation-6/src/results/" + name,
                 "predict_estimate": str(r.get("estimate"))}
            for c in ("estimate", "ci_lo", "ci_hi", "p_crv1", "N", "G", "base_rate", "mde80", "p_perm"):
                v = fnum(r.get(c)) if c in tbl.columns else None
                if v is not None:
                    e[f"eval_{c}"] = v
            ex_rows.append(e)
    for _, r in d["inf"].iterrows():
        v = fnum(r.value)
        e = {"input": f"inference | {r.test} | fold={r.fold} | row={r.row}", "output": "NA" if v is None else f"{v:.6g}",
             "metadata_test": f"INFERENCE.{r.test}", "metadata_fold": str(r.fold), "metadata_label": LABEL,
             "metadata_note": "" if pd.isna(r.note) else str(r.note),
             "metadata_source": "round-5/evaluation-6/src/results/inference_rows.csv",
             "predict_estimate": "NA" if v is None else str(v)}
        if v is not None:
            e["eval_estimate"] = v
        ex_rows.append(e)
    ev = []
    for f in K.FOLDS:
        s = K.load_fold(f)
        z = (s.A_cont - s.A_cont.mean()) / s.A_cont.std()
        for (_, r), zz in zip(s.iterrows(), z):
            fg = r.get("field_group") if "field_group" in s.columns else "biomedicine (MeSH)"
            ev.append({"input": f"entry of concept {r.concept_id} into host subfield {r.d} in year {int(r.e)} (fold {f})",
                       "output": str(int(r.Y_strict)), "metadata_fold": f, "metadata_concept_id": str(r.concept_id),
                       "metadata_d": str(r.d), "metadata_e": int(r.e), "metadata_field_group": str(fg),
                       "predict_any_uptake": str(int(r.Y_strict >= 1)),
                       "eval_Y_strict": float(r.Y_strict), "eval_Any": float(r.Y_strict >= 1),
                       "eval_A_cont_z": float(zz), "eval_A_cont": float(r.A_cont), "eval_CT": float(r.CT),
                       "eval_n_entry_papers": float(r.n_entry_papers)})
    return {"metadata": {"evaluation_name": "K1 margins / K3 field boundary / size-correct inference for the D2 host-entry effect",
                         "label": LABEL, "spec_sha256": summ["spec_sha256"],
                         "evaluated_artifacts": ["art_WZ8fbLn79nCq", "art_XGdzjWgi-a88", "art_2Cd2JJypeGuA", "art_eR1Z7fMlOcxs"],
                         "verdicts": {k: summ[k].get("verdict_text", summ[k].get("verdict")) for k in ("K1", "K3", "INFERENCE")},
                         "summary_path": "results/k13_summary.json"},
            "metrics_agg": ma,
            "datasets": [{"dataset": "k_rows", "examples": ex_rows}, {"dataset": "events", "examples": ev}]}


@logger.catch(reraise=True)
def main() -> None:
    K.assert_spec_hash()
    d = load()
    summ = verdicts(d)
    K.dump(summ, R / "k13_summary.json")
    logger.info(f"K1 {summ['K1'].get('verdict_text')} | K3 {summ['K3'].get('verdict_text')} | INF {summ['INFERENCE'].get('verdict_text')}")
    fig_margin(d)
    fig_ladder(d)
    fig_k3(d)
    fig_null(d)
    rec = record(d, summ)
    logger.info(f"record_of_numbers: {len(rec)} rows")
    eo = eval_out(d, summ)
    (K.WS / "eval_out.json").write_text(json.dumps(K.clean(eo), indent=1))
    logger.info(f"eval_out.json: {len(eo['metrics_agg'])} metrics, {[len(x['examples']) for x in eo['datasets']]} examples")


if __name__ == "__main__":
    main()
