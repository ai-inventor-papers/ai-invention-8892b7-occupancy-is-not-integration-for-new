#!/usr/bin/env python3
"""K2 Steps 0c, 0d and 1: GATE-A (A_cont rebuilt from tags == stored, 1e-9), GATE-B (recorded co-primary IRR/SD
reproduced, |d ln IRR/SD| < 1e-6), partner generality measures and outcome-free descriptives.

Outputs: results/gates.json, results/partner_generality.parquet (one row per co-primary event of every fold),
results/k2_descriptives.json, cache/k2_samples.pkl (fold samples + tag arrays for the later steps).
Nothing here reads a K2 coefficient (GATE-B refits only the recorded M1 co-primary model).
"""
from __future__ import annotations

import gc
import json
import pickle
import sys
import time

import numpy as np
import pandas as pd

import k2_lib as L
from k2_lib import logger

RECORD = {
    "screen": {"file": "inputs/heldout_dryrun_on_screen.json", "source":
               "round-4/evaluation-2/src/d2/results/heldout_dryrun_on_screen.json"},
    "heldout": {"file": "inputs/heldout_confirmation.json", "source":
                "round-4/evaluation-2/src/d2/results/heldout_confirmation.json"},
    "mesh": {"file": "mesh/results/g4_summary.json", "source":
             "round-4/experiment-9/src/results/g4_summary.json"},
}


def recorded(fold: str) -> dict:
    d = json.loads((L.WS / RECORD[fold]["file"]).read_text())
    if fold == "mesh":
        r = d["R2"]
        return {"irr_sd": r["irr_sd"], "ci": r["ci"], "N": r["N"], "G": r["G"]}
    r = d["secondary"]
    return {"irr_sd": r["irr_sd"]["A_cont"], "ci": r["ci_irr_sd"]["A_cont"], "N": r["n_retained"], "G": r["G"],
            "b": r["coef"]["A_cont"]}


def heldout_lock() -> dict:
    lk = L.INP / "HELDOUT_OPENED.lock"
    if not lk.exists():
        raise SystemExit("REFUSED: held-out fold lock file missing; the held-out fold must already be opened")
    import config
    config.SEALED_IDS.clear()  # as eval_2 g/heldout_post.py (fold opened once in iteration 4)
    return {"lock_sha256": L.sha256_file(lk), "lock_text": lk.read_text().strip().splitlines(),
            "source": "round-4/evaluation-2/src/d2/results/HELDOUT_OPENED.lock",
            "note": "held-out fold already opened once in iteration 4; K2 only re-reads its stored W1 features and "
                    "outcomes; config.SEALED_IDS cleared as in heldout_post.py"}


def descriptives(k: pd.DataFrame, fold: str) -> dict:
    """Outcome-free descriptives on the K2 input sample."""
    d = {"N_k2_input": int(len(k)), "G_k2_input": int(k.concept_id.nunique())}
    for c in ("A_cont", "A_lift", "G_H", "G_F", "G_H_ub", "cov", "s_dB", "A_spec"):
        x = k[c].astype(float)
        d[f"{c}_mean"], d[f"{c}_sd"] = float(x.mean()), float(x.std())
        d[f"{c}_q"] = [float(x.quantile(q)) for q in (0.05, 0.25, 0.5, 0.75, 0.95)]
    d["pearson"] = {f"A_cont~{g}": float(k.A_cont.corr(k[g])) for g in ("G_H", "G_F")}
    d["pearson"]["G_H~G_F"] = float(k.G_H.corr(k.G_F))
    M = L.within(k, ["A_cont", "G_H", "G_F", "A_lift", "ln_A_cont", "ln_s_dB"])
    C = np.corrcoef(M, rowvar=False)
    d["within_fe_r"] = {"A_cont~G_H": float(C[0, 1]), "A_cont~G_F": float(C[0, 2]), "G_H~G_F": float(C[1, 2]),
                        "A_lift~ln_A_cont": float(C[3, 4]), "A_lift~ln_s_dB": float(C[3, 5])}
    d["within_fe_R2_A_cont_on_G"] = L.within_r2(k, "A_cont", ["G_H", "G_F"])
    v = M.var(0)
    d["share_within_var_A_lift_from_ln_s_dB"] = float(v[5] / v[3]) if v[3] > 0 else None
    d["within_var"] = {"A_lift": float(v[3]), "ln_A_cont": float(v[4]), "ln_s_dB": float(v[5])}
    d["vif"] = L.g_lib.vif(k, ["A_cont", "G_H", "G_F", "CT"] + L.CTRL)
    d["vif_lift"] = L.g_lib.vif(k, ["A_lift", "G_H", "G_F", "CT"] + L.CTRL)
    d["partial_residual_trigger_abs_r_gt_0.8"] = bool(max(abs(C[0, 1]), abs(C[0, 2])) > 0.8)
    d["cov_ge_0.8_events"] = int((k["cov"] >= 0.8).sum())
    d["max_abs_G_H_ub_minus_G_H"] = float((k.G_H_ub - k.G_H).abs().max())
    d["mean_G_H_ub_minus_G_H"] = float((k.G_H_ub - k.G_H).mean())
    if fold == "mesh":
        d["cov_exact_mean"] = float(k.cov_exact.mean())
        d["corr_G_H_bg~G_H"] = float(k.G_H_bg.corr(k.G_H))
    return d


@logger.catch(reraise=True)
def main() -> None:
    L.setup_logging("k2_features")
    t0 = time.time()
    lock = heldout_lock()
    gates, desc, parts, cache = {"heldout_lock": lock}, {}, [], {}
    for fold in L.FOLDS:
        tf = time.time()
        G = L.load_G(fold)
        s = L.coprimary_sample(fold)
        logger.info(f"[{fold}] co-primary input sample: {len(s)} events, {s.concept_id.nunique()} concepts")
        # ---- GATE-B: recorded co-primary reproduction (same fit as the record; no K2 term)
        rec = recorded(fold)
        r = L.models.fit_one(s, "Y_strict", ["A_cont", "CT"] + L.CTRL, "secondary")
        d_ln = abs(np.log(r["irr_sd"]["A_cont"]) - np.log(rec["irr_sd"]))
        gb = {"recorded": rec, "reproduced": {"irr_sd": r["irr_sd"]["A_cont"], "ci": r["ci_irr_sd"]["A_cont"],
                                              "N": r["n_retained"], "G": r["G"], "b": r["coef"]["A_cont"],
                                              "se": r["se"]["A_cont"], "p": r["p"]["A_cont"]},
              "abs_d_ln_irr_sd": float(d_ln), "source": RECORD[fold]["source"]}
        gb["PASS"] = bool(d_ln < 1e-6 and r["n_retained"] == rec["N"] and r["G"] == rec["G"])
        # ---- tags, GATE-A
        arr = L.tag_arrays(G, s, fold)
        ent = L.entry_measures(arr, s, G, fold)
        diff = np.abs(ent.A_cont_rebuilt.to_numpy() - s.A_cont.to_numpy())
        ga = {"max_abs_diff": float(np.nanmax(diff)), "n_events": int(len(s)),
              "n_nan_mismatch": int((np.isnan(ent.A_cont_rebuilt) != np.isnan(s.A_cont)).sum())}
        ga["PASS"] = bool(ga["max_abs_diff"] <= 1e-9 and ga["n_nan_mismatch"] == 0)
        if fold != "mesh":
            chk = L.placebo.a_cont(L.placebo.build_arrays(G, s))
            ga["placebo_build_arrays_max_abs_diff"] = float(np.nanmax(np.abs(chk - s.A_cont.to_numpy())))
        gates[fold] = {"gate_A": ga, "gate_B": gb, "status": "PASS" if ga["PASS"] and gb["PASS"] else "FAIL"}
        logger.info(f"[{fold}] GATE-A {ga}; GATE-B d_ln {d_ln:.2e} N {r['n_retained']}/{rec['N']} "
                    f"G {r['G']}/{rec['G']} -> {gates[fold]['status']}")
        # ---- entry table
        k = pd.concat([s.reset_index(drop=True), ent], axis=1)
        k["fold"] = fold
        if fold == "mesh":
            k["cov_gen"] = k.n_gen_tags / k.n_tags
        else:
            k["cov_exact"] = k["cov"]
            k["cov_gen"] = k["cov"]
            k["n_exact_tags"] = k["n_prof_tags"]
        spec_vals, spec_info = L.a_spec(arr, s, ent)
        k["A_spec"] = spec_vals
        lift = L.add_lift(k)
        k2 = L.refac(k.dropna(subset=["G_H", "G_F", "A_lift"]))
        desc[fold] = {"lift": lift, "A_spec_tag_ols": spec_info, "n_events_missing_G": int(len(k) - len(k2)),
                      "tag_counts": {"profiled_tags": int(len(arr["te"])), "exact_tags": int((arr["src"] == 0).sum()),
                                     "bg_tags": int((arr["src"] == 1).sum())},
                      **descriptives(k2, fold)}
        cols = ["fold", "concept_id", "d", "e", "o", "n_entry_papers", "A_cont", "A_cont_rebuilt", "A_lift", "s_dB",
                "K_B", "G_H", "G_F", "G_H_ub", "G_H_bg", "n_prof_tags", "n_gen_tags", "n_exact_tags", "cov",
                "cov_exact", "cov_gen", "GH_nat", "GH_adj", "GH_for", "GF_nat", "GF_adj", "GF_for", "NAT", "ADJ",
                "A_spec", "zeroA"]
        parts.append(k[cols])
        cache[fold] = {"k_full": k, "k2": k2, "arr": arr}
        logger.info(f"[{fold}] K2 input {len(k2)} (dropped {len(k) - len(k2)} missing G); "
                    f"within-FE r(A,G_H) {desc[fold]['within_fe_r']['A_cont~G_H']:.3f} r(A,G_F) "
                    f"{desc[fold]['within_fe_r']['A_cont~G_F']:.3f}; R2 {desc[fold]['within_fe_R2_A_cont_on_G']:.4f} "
                    f"({time.time() - tf:.0f}s)")
        del G
        gc.collect()
    pg = pd.concat(parts, ignore_index=True)
    pg.to_parquet(L.RES / "partner_generality.parquet", index=False)
    L.dump(L.RES / "gates.json", L.clean(gates))
    L.dump(L.RES / "k2_descriptives.json", L.clean(desc))
    (L.KCACHE / "k2_samples.pkl").write_bytes(pickle.dumps(cache, protocol=5))
    logger.info(f"done in {time.time() - t0:.0f}s; gates: {[(f, gates[f]['status']) for f in L.FOLDS]}")


if __name__ == "__main__":
    sys.exit(main())
