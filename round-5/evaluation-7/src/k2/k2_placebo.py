#!/usr/bin/env python3
"""K2 S10: placebo host under M1 (generality held fixed). 100 size-decile draws per fold (g_lib.placebo_candidates:
d' != o, d' != d, no c-paper in d' at <= e, same size decile of subfield totals in year e; MeSH also the exp_9
coverage rule covered(pm, d', e, 0.30)). A_plac = mean share of the SAME profiled tags toward d' (MeSH: Nat(exact+bg)).
Fits per draw: plac_noG  A_plac + CT + controls (the recorded no-generality placebo form)
               plac_M1   A_plac + CT + G_H + G_F + controls
               joint_M1  A_cont + A_plac + CT + G_H + G_F + controls
PASS rule (g_spec): share of positive-significant placebo IRR <= 0.10 AND median placebo IRR/SD < 1.10.
Outputs: results/k2_placebo_host_draws.csv, results/k2_placebo_host.json.
"""
from __future__ import annotations

import pickle
import sys
import time

import numpy as np
import pandas as pd

import k2_lib as L
from k2_lib import logger

FITS = {"plac_noG": ["A_plac", "CT"] + L.CTRL,
        "plac_M1": ["A_plac", "CT", "G_H", "G_F"] + L.CTRL,
        "joint_M1": ["A_cont", "A_plac", "CT", "G_H", "G_F"] + L.CTRL}


def candidates(G: dict, s: pd.DataFrame, fold: str, labels: list[int]) -> list[np.ndarray]:
    cand = L.g_lib.placebo_candidates(G, s, labels, "size")
    if fold != "mesh":
        return cand
    sys.path.insert(0, str(L.WS / "mesh" / "src"))
    import coverage
    pm = coverage.load_rule()
    out = []
    for c, e in zip(cand, s.e.to_numpy()):
        out.append(np.array([i for i in c if coverage.covered(pm, labels[i], int(e), 0.30)], np.int64))
    return out


def _draw(args) -> dict:
    fold, seed = args
    s, arr, cand = (L._W[k][fold] for k in ("s", "arr", "cand"))
    rng = np.random.default_rng(seed)
    pick = np.array([c[rng.integers(len(c))] if len(c) else -1 for c in cand])
    lab = pick[arr["te"]]
    ok = lab >= 0
    sh = np.zeros(len(lab))
    sh[ok] = arr["S"][arr["tn"][ok], arr["tb"][ok], lab[ok]]
    num = np.bincount(arr["te"], weights=sh, minlength=arr["n"])
    den = np.bincount(arr["te"], minlength=arr["n"])
    with np.errstate(invalid="ignore", divide="ignore"):
        ap = np.where(pick >= 0, num / den, np.nan)
    ss = s.copy()
    ss["A_plac"] = ap
    ss = L.refac(ss.dropna(subset=["A_plac"]))
    out = {"fold": fold, "seed": seed, "n_events": int(len(ss))}
    for name, xs in FITS.items():
        try:
            r = L.models.fit_one(ss, "Y_strict", xs, "secondary")
        except (np.linalg.LinAlgError, ValueError, RuntimeError):
            r = None
        out[f"{name}_ok"] = r is not None
        if r is None:
            continue
        out[f"{name}_irr_sd_plac"] = r["irr_sd"]["A_plac"]
        out[f"{name}_p_plac"] = r["p"]["A_plac"]
        if name == "joint_M1":
            out["joint_M1_irr_sd_A"] = r["irr_sd"]["A_cont"]
            out["joint_M1_p_A"] = r["p"]["A_cont"]
    return out


def summarise(d: pd.DataFrame, name: str) -> dict:
    ok = d[d[f"{name}_ok"]]
    irr, p = ok[f"{name}_irr_sd_plac"], ok[f"{name}_p_plac"]
    pos = float(((p < 0.05) & (irr > 1)).mean()) if len(ok) else np.nan
    med = float(irr.median()) if len(ok) else np.nan
    return {"n_ok": int(len(ok)), "share_pos_sig": pos, "median_irr_sd": med,
            "q025_q975": [float(irr.quantile(.025)), float(irr.quantile(.975))] if len(ok) else None,
            "PASS": bool(pos <= 0.10 and med < 1.10)}


@logger.catch(reraise=True)
def main() -> None:
    L.setup_logging("k2_placebo")
    L.assert_spec_frozen()
    t0 = time.time()
    cache = pickle.loads((L.KCACHE / "k2_samples.pkl").read_bytes())
    S, A, C, info = {}, {}, {}, {}
    for fold in L.FOLDS:
        G = L.load_G(fold)
        s = cache[fold]["k2"]
        arr = L.tag_arrays(G, s, fold)
        chk = np.abs(L._emean(arr["te"], arr["sh"], arr["n"]) - s.A_cont.to_numpy())
        assert np.nanmax(chk) < 1e-9, "tag arrays do not rebuild A_cont"
        labels = arr["labels"]
        cand = candidates(G, s, fold, labels)
        S[fold], A[fold], C[fold] = s, {k: arr[k] for k in ("S", "te", "tn", "tb", "n")}, cand
        info[fold] = {"events_without_candidate": int(sum(len(c) == 0 for c in cand)),
                      "median_candidates": float(np.median([len(c) for c in cand]))}
        del G
    tasks = [(f, L.SEED + 700_000 + 1000 * fi + k) for fi, f in enumerate(L.FOLDS) for k in range(100)]
    res = pd.DataFrame(L.pool({"s": S, "arr": A, "cand": C}, _draw, tasks, chunksize=4))
    res.to_csv(L.RES / "k2_placebo_host_draws.csv", index=False)
    out = {"label": "POST-CONFIRMATION EXPLORATORY / SUPPLEMENTARY S10", "draws": 100, "strat": "size",
           "pass_rule": "PASS if share_pos_sig <= 0.10 AND median placebo IRR/SD < 1.10",
           "generic_prediction": "FAIL under M1, or share_pos_sig(plac_M1) > share_pos_sig(plac_noG)", "folds": {}}
    for f in L.FOLDS:
        d = res[res.fold == f]
        o = {**info[f], "n_events": int(len(S[f]))}
        for name in FITS:
            o[name] = summarise(d, name)
        o["joint_M1_A_cont_irr_sd_median"] = float(d.joint_M1_irr_sd_A.median())
        o["joint_M1_A_cont_share_p05"] = float((d.joint_M1_p_A < 0.05).mean())
        o["generic_prediction_met"] = bool((not o["plac_M1"]["PASS"]) or
                                           o["plac_M1"]["share_pos_sig"] > o["plac_noG"]["share_pos_sig"])
        out["folds"][f] = o
        logger.info(f"[{f}] {o}")
    L.dump(L.RES / "k2_placebo_host.json", L.clean(out))
    logger.info(f"done in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    sys.exit(main())
