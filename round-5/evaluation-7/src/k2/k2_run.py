#!/usr/bin/env python3
"""K2 Steps 4-7 (except S10 placebo host): M0-M3 per fold with CRV1 / wild / placebo-calibrated / Freedman-Lane
randomisation p, 1000-draw concept bootstrap retention CIs, IVW pooling, the frozen decision rule, supplementary rows.

Outputs: results/k2_rows.csv, results/k2_summary.json, results/k2_boot_draws.csv, results/k2_perm_draws.csv.
Every row carries the label POST-CONFIRMATION EXPLORATORY (supplementary rows: '... / SUPPLEMENTARY').
"""
from __future__ import annotations

import json
import os
import pickle
import sys
import time

import numpy as np
import pandas as pd

import k2_lib as L
from k2_lib import logger

LAB = "POST-CONFIRMATION EXPLORATORY"
LABS = "POST-CONFIRMATION EXPLORATORY / SUPPLEMENTARY (not in the rule)"
S2X = ["A_cont", "GH_nat", "GH_adj", "GH_for", "GF_nat", "GF_adj", "GF_for"]


def boot_pairs(fold: str) -> list[tuple]:
    c = ["CT"] + L.CTRL
    pairs = [(m, L.xvars_of(m), [L.FOCAL[m]], "secondary") for m in L.MODELS]
    pairs += [("S1_M0", L.xvars_of("M0"), ["A_cont"], "primary"), ("S1_M1", L.xvars_of("M1"), ["A_cont"], "primary"),
              ("S2", S2X + c, ["A_cont"], "secondary"),
              ("S3_noG", ["NAT", "ADJ"] + c, ["NAT", "ADJ"], "secondary"),
              ("S3_G", ["NAT", "ADJ", "G_H", "G_F"] + c, ["NAT", "ADJ"], "secondary"),
              ("S6", ["A_cont", "G_H_ub", "G_F"] + c, ["A_cont"], "secondary")]
    if fold == "mesh":
        pairs.append(("S8", ["A_cont", "G_H_bg", "G_F"] + c, ["A_cont"], "secondary"))
    return pairs


def pct(x: pd.Series, q: float) -> float | None:
    x = x.replace([np.inf, -np.inf], np.nan).dropna()
    return float(x.quantile(q)) if len(x) > 20 else None


def ratio_ci(bd: pd.DataFrame, num: str, den: str) -> dict:
    r = (bd[num] / bd[den]).replace([np.inf, -np.inf], np.nan).dropna()
    return {"ci": [pct(r, .025), pct(r, .975)], "n_ok": int(len(r)), "boot_median": float(r.median()) if len(r) else None,
            "P_boot_ge_0.5": float((r >= 0.5).mean()) if len(r) else None}


def verdict(lift_lo: float | None, lift_hi: float | None, ret: float | None) -> str:
    if ret is None or not np.isfinite(ret):
        return "NOT DETERMINED"
    if ret < 0.5:
        return "GENERIC ACCESSIBILITY"
    if lift_lo is not None and lift_lo > 1 and ret >= 0.5:
        return "HOST-SPECIFIC"
    return "MIXED"


@logger.catch(reraise=True)
def main() -> None:
    L.setup_logging("k2_run")
    spec = L.assert_spec_frozen()
    t0 = time.time()
    cache = pickle.loads((L.KCACHE / "k2_samples.pkl").read_bytes())
    gates = json.loads((L.RES / "gates.json").read_text())
    power = json.loads((L.RES / "k2_power.json").read_text())
    desc = json.loads((L.RES / "k2_descriptives.json").read_text())
    folds = [f for f in L.FOLDS if gates[f]["status"] == "PASS"]
    rows, fits, samples = [], {}, {}
    for f in L.FOLDS:
        if f not in folds:
            rows.append({"fold": f, "model": "ALL", "label": LAB, "note": "NOT RUN (gate fail)"})
    # ------------------------------------------------------------------ Step 4 main fits
    for f in folds:
        s = cache[f]["k2"]
        samples[f] = s
        zsd = L.placebo_zsd(f)
        rng = np.random.default_rng(L.SEED)
        for m, xs0 in L.MODELS.items():
            xs = L.xvars_of(m)
            targets = xs0
            rr, r = L.fit_rows(s, xs, targets, fold=f, model=m, label=LAB, wild=(L.FOCAL[m],), zsd=zsd, rng=rng,
                               extra={"row_type": "main"})
            for x in rr:
                x["focal"] = x["var"] == L.FOCAL[m]
            rows += rr
            fits[(f, m)] = {x["var"]: x for x in rr}
        logger.info(f"[{f}] " + "; ".join(f"{m}: {L.FOCAL[m]} IRR/SD {fits[(f, m)][L.FOCAL[m]]['irr_sd']:.3f} "
                                          f"p {fits[(f, m)][L.FOCAL[m]]['p_crv1']:.4f}" for m in L.MODELS))
    # ------------------------------------------------------------------ Freedman-Lane randomisation
    fl = {(f, m): L.fl_prep(samples[f], L.xvars_of(m)) for f in folds for m in L.MODELS}
    R = spec["inference"]["randomisation_draws"]
    SMOKE = bool(os.environ.get("K2_SMOKE"))
    if SMOKE:  # timing / code test with 20 draws per model (plan: time the randomisation first)
        R = {m: 20 for m in R}
    tasks = [(f, m, L.SEED + 100_000 + 20_000 * fi + 5_000 * mi + k) for fi, f in enumerate(folds)
             for mi, m in enumerate(L.MODELS) for k in range(R[m])]
    tp = time.time()
    perm = pd.DataFrame(L.pool({"samples": samples, "fl": fl}, L._perm_task, tasks, chunksize=25))
    perm.to_csv((L.RES / "smoke" if SMOKE else L.RES) / "k2_perm_draws.csv", index=False) if (L.RES / "smoke").mkdir(exist_ok=True) is None else None
    logger.info(f"randomisation: {len(perm)} draws in {time.time() - tp:.0f}s")
    for f in folds:
        for m in L.MODELS:
            x = fits[(f, m)][L.FOCAL[m]]
            z = perm[(perm.fold == f) & (perm.model == m)].z.dropna()
            x["p_rand"] = float((1 + (z.abs() >= abs(x["z"])).sum()) / (1 + len(z)))
            x["rand_draws_ok"] = int(len(z))
            x["rand_z_sd"] = float(z.std())
            x["fl_r2_focal_on_rest"] = fl[(f, m)]["r2_focal_on_rest"]
    # ------------------------------------------------------------------ bootstrap
    B = 20 if SMOKE else 1000
    pairs = {f: boot_pairs(f) for f in folds}
    tb = time.time()
    tasks = [(f, L.SEED + 500_000 + 10_000 * fi + k) for fi, f in enumerate(folds) for k in range(B)]
    boot = pd.DataFrame(L.pool({"samples": samples, "pairs": pairs}, L._boot_task, tasks, chunksize=10))
    boot.to_csv((L.RES / "smoke" if SMOKE else L.RES) / "k2_boot_draws.csv", index=False)
    logger.info(f"bootstrap: {len(boot)} draws in {time.time() - tb:.0f}s")
    # ------------------------------------------------------------------ Step 5 retention per fold
    summ = {"label": LAB, "spec_sha256": L.SPEC_SHA.read_text().split()[0], "folds": {}, "pooled": {}}
    for f in folds:
        bd = boot[boot.fold == f]
        b = {m: fits[(f, m)][L.FOCAL[m]]["b"] for m in L.MODELS}
        ret = b["M1"] / b["M0"]
        ret_l = b["M3"] / b["M2"]
        hp = L.models.holm({"M1_A_cont": fits[(f, "M1")]["A_cont"]["p_crv1"],
                            "M2_A_lift": fits[(f, "M2")]["A_lift"]["p_crv1"],
                            "M3_A_lift": fits[(f, "M3")]["A_lift"]["p_crv1"]})
        for key, (m, v) in {"M1_A_cont": ("M1", "A_cont"), "M2_A_lift": ("M2", "A_lift"),
                            "M3_A_lift": ("M3", "A_lift")}.items():
            fits[(f, m)][v]["p_holm"] = hp[key]
        rc = ratio_ci(bd, "M1|A_cont", "M0|A_cont")
        rcl = ratio_ci(bd, "M3|A_lift", "M2|A_lift")
        m3 = fits[(f, "M3")]["A_lift"]
        v = verdict(m3["irr_sd_lo"], m3["irr_sd_hi"], ret)
        qual = []
        if rc["ci"][0] is not None and rc["ci"][0] <= 0.5 <= rc["ci"][1]:
            qual.append("retention CI includes 0.5 (not decisive)")
        frag = [f"{m} {L.FOCAL[m]}" for m in ("M1", "M3")
                if fits[(f, m)][L.FOCAL[m]]["p_rand"] > 0.05 and fits[(f, m)][L.FOCAL[m]]["p_crv1"] < 0.05]
        if frag:
            qual.append("fragile (randomisation p > 0.05 while CRV1 < 0.05: " + ", ".join(frag) + ")")
        if power["folds"][f]["retention_underpowered"]:
            qual.append("retention underpowered")
        if m3["irr_sd_hi"] < 1:
            qual.append("A_lift CI entirely below 1 (negative lift)")
        pick = lambda m, t: {k: fits[(f, m)][t].get(k) for k in ("b", "se", "irr_sd", "irr_sd_lo", "irr_sd_hi",  # noqa: E731
                                                                  "irr_01", "p_crv1", "p_wild", "p_placebo_cal",
                                                                  "p_rand", "p_holm", "N_input", "N", "G",
                                                                  "retained_share", "sd_retained")}
        summ["folds"][f] = {
            "verdict": v, "qualifiers": qual, "gate_status": gates[f]["status"],
            "ret": ret, "ret_ci": rc["ci"], "ret_boot": rc, "pct_removed": 100 * (1 - ret),
            "pct_removed_ci": [100 * (1 - rc["ci"][1]) if rc["ci"][1] is not None else None,
                               100 * (1 - rc["ci"][0]) if rc["ci"][0] is not None else None],
            "ret_lift": ret_l, "ret_lift_ci": rcl["ci"],
            "M0_A_cont": pick("M0", "A_cont"), "M1_A_cont": pick("M1", "A_cont"),
            "M2_A_lift": pick("M2", "A_lift"), "M3_A_lift": pick("M3", "A_lift"),
            "M1_G_H": pick("M1", "G_H"), "M1_G_F": pick("M1", "G_F"), "M3_G_H": pick("M3", "G_H"),
            "M3_G_F": pick("M3", "G_F"),
            "retention_power": {k: power["folds"][f][k] for k in ("DGP_S", "DGP_G", "retention_underpowered")}}
        logger.info(f"[{f}] ret {ret:.3f} {rc['ci']} ret_lift {ret_l:.3f} {rcl['ci']} -> {v} {qual}")
    # ------------------------------------------------------------------ IVW pooling
    if len(folds) >= 2:
        P = summ["pooled"]
        for m, t in [(m, t) for m in L.MODELS for t in L.MODELS[m]]:
            xs = [fits[(f, m)][t] for f in folds]
            p = L.ivw([x["lnirr_sd"] for x in xs], [x["lnirr_sd_se"] for x in xs])
            p.update({"irr_sd": float(np.exp(p["b"])), "irr_sd_lo": float(np.exp(p["lo"])),
                      "irr_sd_hi": float(np.exp(p["hi"])), "folds": folds})
            P[f"{m}_{t}"] = p
        w0 = np.array(P["M0_A_cont"]["weights"])
        w1 = np.array(P["M1_A_cont"]["weights"])
        ret_pool = P["M1_A_cont"]["b"] / P["M0_A_cont"]["b"]
        w2 = np.array(P["M2_A_lift"]["weights"])
        w3 = np.array(P["M3_A_lift"]["weights"])
        retl_pool = P["M3_A_lift"]["b"] / P["M2_A_lift"]["b"]
        # combined draws: draw k of every fold, fixed IVW weights
        ks = {f: boot[boot.fold == f].sort_values("seed").reset_index(drop=True) for f in folds}
        n = min(len(k) for k in ks.values())
        sd = {f: fits[(f, "M0")]["A_cont"]["sd_retained"] for f in folds}
        sdl = {f: fits[(f, "M2")]["A_lift"]["sd_retained"] for f in folds}
        num = sum(w1[i] * ks[f]["M1|A_cont"][:n].to_numpy(float) * sd[f] for i, f in enumerate(folds))
        den = sum(w0[i] * ks[f]["M0|A_cont"][:n].to_numpy(float) * sd[f] for i, f in enumerate(folds))
        rp = pd.Series(num / den)
        numl = sum(w3[i] * ks[f]["M3|A_lift"][:n].to_numpy(float) * sdl[f] for i, f in enumerate(folds))
        denl = sum(w2[i] * ks[f]["M2|A_lift"][:n].to_numpy(float) * sdl[f] for i, f in enumerate(folds))
        rpl = pd.Series(numl / denl)
        P["ret"] = ret_pool
        P["ret_ci"] = [pct(rp, .025), pct(rp, .975)]
        P["ret_boot_n_ok"] = int(rp.replace([np.inf, -np.inf], np.nan).notna().sum())
        P["pct_removed"] = 100 * (1 - ret_pool)
        P["ret_lift"] = retl_pool
        P["ret_lift_ci"] = [pct(rpl, .025), pct(rpl, .975)]
        m3p = P["M3_A_lift"]
        v = verdict(m3p["irr_sd_lo"], m3p["irr_sd_hi"], ret_pool)
        qual = []
        if P["ret_ci"][0] is not None and P["ret_ci"][0] <= 0.5 <= P["ret_ci"][1]:
            qual.append("retention CI includes 0.5 (not decisive)")
        frag = [f"{f}: {q}" for f in folds for q in summ["folds"][f]["qualifiers"] if q.startswith("fragile")]
        if frag:
            qual.append("fragile in fold(s): " + "; ".join(frag))
        if power["pooled"]["retention_underpowered"]:
            qual.append("retention underpowered")
        P["verdict"] = v
        P["qualifiers"] = qual
        P["folds_pooled"] = folds
        P["method"] = spec["ivw"]
        P["retention_power"] = power["pooled"]
        logger.info(f"[pooled] ret {ret_pool:.3f} {P['ret_ci']} ret_lift {retl_pool:.3f} {P['ret_lift_ci']}; "
                    f"A_lift M3 {m3p['irr_sd']:.3f} [{m3p['irr_sd_lo']:.3f}, {m3p['irr_sd_hi']:.3f}] -> {v} {qual}")
    # ------------------------------------------------------------------ Step 7 supplementary rows
    supp = {}
    c = ["CT"] + L.CTRL
    for f in folds:
        s = samples[f]
        bd = boot[boot.fold == f]
        sp = {}

        def add(key, xs, targets, sample=None, spec_="secondary", note=""):
            rr, r = L.fit_rows(sample if sample is not None else s, xs, targets, fold=f, model=key, spec=spec_,
                               label=LABS, extra={"row_type": "supplementary", "note": note})
            rows.extend(rr)
            return {x["var"]: x for x in rr}

        # S1 primary FE
        a0 = add("S1_M0", L.xvars_of("M0"), ["A_cont"], spec_="primary")
        a1 = add("S1_M1", L.xvars_of("M1"), ["A_cont", "G_H", "G_F"], spec_="primary")
        if "b" in a0["A_cont"] and "b" in a1["A_cont"]:
            thin = a0["A_cont"]["G"] < 50 or a0["A_cont"]["retained_share"] < 0.30
            sp["S1"] = {"ret": a1["A_cont"]["b"] / a0["A_cont"]["b"], "ret_ci": ratio_ci(bd, "S1_M1|A_cont", "S1_M0|A_cont")["ci"],
                        "M0_irr_sd": a0["A_cont"]["irr_sd"], "M1_irr_sd": a1["A_cont"]["irr_sd"],
                        "M1_ci": [a1["A_cont"]["irr_sd_lo"], a1["A_cont"]["irr_sd_hi"]],
                        "N": a0["A_cont"]["N"], "G": a0["A_cont"]["G"], "thin_cell_underpowered": bool(thin)}
        # S2 split generality
        a = add("S2", S2X + c, S2X)
        sp["S2"] = {"ret": a["A_cont"].get("b", np.nan) / fits[(f, "M0")]["A_cont"]["b"],
                    "ret_ci": ratio_ci(bd, "S2|A_cont", "M0|A_cont")["ci"],
                    "irr_sd": {k: a[k].get("irr_sd") for k in S2X}, "p": {k: a[k].get("p_crv1") for k in S2X}}
        # S3 G2a with generality
        n0 = add("S3_noG", ["NAT", "ADJ"] + c, ["NAT", "ADJ"])
        n1 = add("S3_G", ["NAT", "ADJ", "G_H", "G_F"] + c, ["NAT", "ADJ", "G_H", "G_F"])
        sp["S3"] = {k: {"noG_irr_sd": n0[k].get("irr_sd"), "G_irr_sd": n1[k].get("irr_sd"),
                        "noG_p": n0[k].get("p_crv1"), "G_p": n1[k].get("p_crv1"),
                        "ret": n1[k].get("b", np.nan) / n0[k].get("b", np.nan),
                        "ret_ci": ratio_ci(bd, f"S3_G|{k}", f"S3_noG|{k}")["ci"]} for k in ("NAT", "ADJ")}
        sp["S3"]["generic_prediction_ADJ_loses_more"] = bool(sp["S3"]["ADJ"]["ret"] < sp["S3"]["NAT"]["ret"])
        # S4 A_spec
        a = add("S4", ["A_spec"] + c, ["A_spec"])
        sp["S4"] = {k: a["A_spec"].get(k) for k in ("irr_sd", "irr_sd_lo", "irr_sd_hi", "p_crv1", "N", "G")}
        # S5 partial residual
        _, res, _ = L.within_proj(s, "A_cont", ["G_H", "G_F"])
        s5 = s.copy()
        s5["A_resid_G"] = res
        a = add("S5", ["A_resid_G"] + c, ["A_resid_G"], sample=s5,
                note="interpreted only if |within-FE r(A_cont, G)| > 0.8")
        trig = desc[f]["partial_residual_trigger_abs_r_gt_0.8"]
        sp["S5"] = {**{k: a["A_resid_G"].get(k) for k in ("irr_sd", "irr_sd_lo", "irr_sd_hi", "p_crv1", "N", "G")},
                    "triggered": trig, "interpreted": trig}
        # S6 truncation upper-bound entropy
        a = add("S6", ["A_cont", "G_H_ub", "G_F"] + c, ["A_cont", "G_H_ub", "G_F"])
        sp["S6"] = {"ret": a["A_cont"]["b"] / fits[(f, "M0")]["A_cont"]["b"],
                    "ret_ci": ratio_ci(bd, "S6|A_cont", "M0|A_cont")["ci"], "A_irr_sd": a["A_cont"]["irr_sd"],
                    "G_H_ub_irr_sd": a["G_H_ub"]["irr_sd"]}
        # S7 coverage >= 0.8
        s7 = L.refac(s[s["cov"] >= 0.8])
        a0 = add("S7_M0", L.xvars_of("M0"), ["A_cont"], sample=s7)
        a1 = add("S7_M1", L.xvars_of("M1"), ["A_cont", "G_H", "G_F"], sample=s7)
        sp["S7"] = {"N_input": int(len(s7)), "ret": a1["A_cont"].get("b", np.nan) / a0["A_cont"].get("b", np.nan),
                    "M0_irr_sd": a0["A_cont"].get("irr_sd"), "M1_irr_sd": a1["A_cont"].get("irr_sd"),
                    "M1_ci": [a1["A_cont"].get("irr_sd_lo"), a1["A_cont"].get("irr_sd_hi")],
                    "G": a0["A_cont"].get("G")}
        # S8 MeSH bg entropy
        if f == "mesh":
            a = add("S8", ["A_cont", "G_H_bg", "G_F"] + c, ["A_cont", "G_H_bg", "G_F"])
            sp["S8"] = {"ret": a["A_cont"]["b"] / fits[(f, "M0")]["A_cont"]["b"],
                        "ret_ci": ratio_ci(bd, "S8|A_cont", "M0|A_cont")["ci"], "A_irr_sd": a["A_cont"]["irr_sd"]}
        # S9 zero-A dropped
        nz = int(s.zeroA.sum())
        if nz:
            s9 = L.refac(s[~s.zeroA])
            a2 = add("S9_M2", L.xvars_of("M2"), ["A_lift"], sample=s9)
            a3 = add("S9_M3", L.xvars_of("M3"), ["A_lift", "G_H", "G_F"], sample=s9)
            sp["S9"] = {"n_zero": nz, "M2_irr_sd": a2["A_lift"].get("irr_sd"), "M3_irr_sd": a3["A_lift"].get("irr_sd"),
                        "M3_ci": [a3["A_lift"].get("irr_sd_lo"), a3["A_lift"].get("irr_sd_hi")],
                        "ret_lift": a3["A_lift"].get("b", np.nan) / a2["A_lift"].get("b", np.nan)}
        else:
            sp["S9"] = {"n_zero": 0, "note": "no zero-A events: identical to M2/M3"}
        # S11 EST_bin LPM (direction only)
        try:
            l0 = L.models.lpm_fe(s, "EST_bin", L.xvars_of("M0"), "secondary")
            l1 = L.models.lpm_fe(s, "EST_bin", L.xvars_of("M1"), "secondary")
            sp["S11"] = {"M0_A_cont_coef": l0["coef"]["A_cont"], "M0_p": l0["p"]["A_cont"],
                         "M1_A_cont_coef": l1["coef"]["A_cont"], "M1_p": l1["p"]["A_cont"],
                         "effect_per_sd_M0": l0["effect_per_sd"]["A_cont"], "effect_per_sd_M1": l1["effect_per_sd"]["A_cont"],
                         "n": l0["n"], "note": "direction only; links to K1; not in the rule"}
            for mname, lr in (("S11_M0", l0), ("S11_M1", l1)):
                rows.append({"fold": f, "model": mname, "spec": "secondary", "y": "EST_bin", "label": LABS,
                             "row_type": "supplementary", "var": "A_cont", "b": lr["coef"]["A_cont"],
                             "se": lr["se"]["A_cont"], "p_crv1": lr["p"]["A_cont"], "N": lr["n"],
                             "note": "linear probability model, same FE", "source": L.source_paths(f)})
        except (ValueError, RuntimeError, np.linalg.LinAlgError) as ex:
            logger.warning(f"S11 failed: {ex!r}")
            sp["S11"] = {"note": f"failed {ex!r}"}
        supp[f] = sp
        logger.info(f"[{f}] supplementary: S1 ret {sp.get('S1', {}).get('ret')}, S2 ret {sp['S2']['ret']:.3f}, "
                    f"S3 NAT ret {sp['S3']['NAT']['ret']:.3f} ADJ ret {sp['S3']['ADJ']['ret']:.3f}, S4 "
                    f"{sp['S4']['irr_sd']:.3f}, S6 ret {sp['S6']['ret']:.3f}, S7 ret {sp['S7']['ret']:.3f}")
    # pooled S rows (IVW of log-IRR/SD)
    if len(folds) >= 2:
        sub = {}
        for key, var in (("S4", "A_spec"), ("S5", "A_resid_G"), ("S2", "A_cont"), ("S6", "A_cont"),
                         ("S1_M1", "A_cont"), ("S1_M0", "A_cont")):
            xs = [x for x in rows if x.get("model") == key and x.get("var") == var and x.get("fold") in folds and "b" in x]
            if len(xs) >= 2:
                p = L.ivw([x["lnirr_sd"] for x in xs], [x["lnirr_sd_se"] for x in xs])
                sub[f"{key}_{var}"] = {"irr_sd": float(np.exp(p["b"])), "lo": float(np.exp(p["lo"])),
                                       "hi": float(np.exp(p["hi"])), "I2": p["I2"], "p_Q": p["p_Q"],
                                       "folds": [x["fold"] for x in xs]}
        s3p = {}
        for k in ("NAT", "ADJ"):
            for tag in ("S3_noG", "S3_G"):
                xs = [x for x in rows if x.get("model") == tag and x.get("var") == k and "b" in x]
                p = L.ivw([x["lnirr_sd"] for x in xs], [x["lnirr_sd_se"] for x in xs])
                s3p[f"{tag}_{k}"] = {"irr_sd": float(np.exp(p["b"])), "lo": float(np.exp(p["lo"])),
                                     "hi": float(np.exp(p["hi"])), "b": p["b"]}
            s3p[f"ret_{k}"] = s3p[f"S3_G_{k}"]["b"] / s3p[f"S3_noG_{k}"]["b"]
        sub["S3"] = s3p
        if all("S1" in supp[f] for f in folds):
            sub["S1_ret_pooled"] = sub["S1_M1_A_cont"]["irr_sd"] and (np.log(sub["S1_M1_A_cont"]["irr_sd"]) /
                                                                      np.log(sub["S1_M0_A_cont"]["irr_sd"]))
        supp["pooled"] = sub
    summ["supplementary"] = supp
    summ["descriptives"] = desc
    summ["gates"] = {f: gates[f]["status"] for f in L.FOLDS}
    summ["runtime_s"] = time.time() - t0
    # ------------------------------------------------------------------ write rows
    for f in folds:
        for m in L.MODELS:
            for t, x in fits[(f, m)].items():
                x.setdefault("p_holm", None)
    df = pd.DataFrame(rows)
    lead = ["fold", "model", "spec", "var", "label", "row_type", "focal", "b", "se", "z", "p_crv1", "p_wild",
            "p_placebo_cal", "p_rand", "p_holm", "irr_sd", "irr_sd_lo", "irr_sd_hi", "irr_01", "lnirr_sd",
            "lnirr_sd_se", "sd_retained", "N_input", "N", "G", "retained_share"]
    df = df[[c_ for c_ in lead if c_ in df.columns] + [c_ for c_ in df.columns if c_ not in lead]]
    # pooled IVW rows
    prow = []
    if summ["pooled"]:
        for key, p in summ["pooled"].items():
            if isinstance(p, dict) and "irr_sd" in p and key.startswith("M"):
                m, t = key.split("_", 1)
                prow.append({"fold": "pooled_IVW", "model": m, "spec": "secondary", "var": t, "label": LAB,
                             "row_type": "main", "focal": t == L.FOCAL[m], "b": p["b"], "se": p["se"], "z": p["z"],
                             "p_crv1": p["p"], "irr_sd": p["irr_sd"], "irr_sd_lo": p["irr_sd_lo"],
                             "irr_sd_hi": p["irr_sd_hi"], "lnirr_sd": p["b"], "lnirr_sd_se": p["se"],
                             "Q": p["Q"], "p_Q": p["p_Q"], "I2": p["I2"],
                             "note": "fixed-effect IVW of per-fold log-IRR/SD; p normal",
                             "source": "results/k2_rows.csv (per-fold rows)"})
    df = pd.concat([df, pd.DataFrame(prow)], ignore_index=True)
    out = L.RES / "smoke" if SMOKE else L.RES
    out.mkdir(exist_ok=True)
    df.to_csv(out / "k2_rows.csv", index=False)
    L.dump(out / "k2_summary.json", L.clean(summ))
    logger.info(f"wrote {len(df)} rows; total {time.time() - t0:.0f}s")


if __name__ == "__main__":
    sys.exit(main())
