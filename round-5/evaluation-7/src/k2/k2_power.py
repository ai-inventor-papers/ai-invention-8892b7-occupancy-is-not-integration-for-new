#!/usr/bin/env python3
"""K2 Step 3: retention design analysis (after the freeze, before any K2 fit; reads NO K2 coefficient).

Per fold: mu0 from the PPML fit of Y on CT + controls + G_H + G_F (no A term); NB2 theta as g_lib.mde_sim.
DGP-S: ln mu = ln mu0 + beta_rec (A_cont - mean)          (host-specific, G terms 0)
DGP-G: ln mu = ln mu0 + gamma (Ahat - mean), Ahat = within-FE linear projection of A_cont on (G_H, G_F),
       gamma = beta_rec / R2_within (implied M0 b_A = beta_rec); not constructible if R2_within < 0.02.
300 reps each on the fixed observed design; M0 and M1 fitted per rep; retention = b1 / b0.
Output: results/k2_power.json (+ .sha256), results/k2_power_reps.csv.
"""
from __future__ import annotations

import json
import pickle
import sys
import time

import numpy as np
import pandas as pd

import k2_lib as L
from k2_lib import logger


def _rep(args) -> dict:
    fold, dgp, seed = args
    P = L._W["P"][fold]
    rng = np.random.default_rng(seed)
    mu = P["mu0"] * np.exp(P["lin"][dgp])
    y = rng.poisson(rng.gamma(P["theta"], mu / P["theta"]))
    s = P["base"].copy()
    s["Y_strict"] = y
    out = {"fold": fold, "dgp": dgp, "seed": seed}
    for m in ("M0", "M1"):
        xs = L.xvars_of(m)
        r = L.fit_b(s, xs)
        out[f"b_{m}"] = None if r is None else float(r["coef"][0])
        out[f"se_{m}"] = None if r is None else float(r["se"][0])
    return out


@logger.catch(reraise=True)
def main() -> None:
    L.setup_logging("k2_power")
    spec = L.assert_spec_frozen()
    reps = spec["power_step3"]["reps_per_dgp"]
    cache = pickle.loads((L.KCACHE / "k2_samples.pkl").read_bytes())
    gates = json.loads((L.RES / "gates.json").read_text())
    P, info = {}, {}
    for fold in L.FOLDS:
        s = cache[fold]["k2"]
        beta = gates[fold]["gate_B"]["reproduced"]["b"]
        ctrl = ["CT"] + L.CTRL + ["G_H", "G_F"]
        r0 = L.fit_b(s, ctrl)
        base = L.refac(s[r0["keep"]].copy())
        mu0 = r0["mu"]
        yb = base.Y_strict.to_numpy(float)
        theta = float(np.sum(mu0 ** 2) / max(np.sum((yb - mu0) ** 2 - yb), 1e-9))
        theta = theta if theta > 0 else 1e6
        a = base.A_cont.to_numpy(float)
        fitted, res, r2 = L.within_proj(base, "A_cont", ["G_H", "G_F"])
        M = L.within(base, ["A_cont", "G_H", "G_F"])
        bproj, *_ = np.linalg.lstsq(M[:, 1:], M[:, 0], rcond=None)
        ahat = base[["G_H", "G_F"]].to_numpy(float) @ bproj
        lin = {"S": beta * (a - a.mean())}
        constructible = r2 >= 0.02
        if constructible:
            gamma = beta / r2
            lin["G"] = gamma * (ahat - ahat.mean())
        P[fold] = {"base": base, "mu0": mu0, "theta": theta, "lin": lin}
        info[fold] = {"beta_rec": beta, "theta": theta, "n_base": int(len(base)), "G_base": int(base.concept_id.nunique()),
                      "within_R2_A_on_G": r2, "proj_coef_G_H_G_F": bproj.tolist(),
                      "DGP_G_constructible": bool(constructible), "gamma": beta / r2 if constructible else None,
                      "sd_A_base": float(a.std(ddof=1)),
                      "recorded_se_b": gates[fold]["gate_B"]["reproduced"]["se"]}
        logger.info(f"[{fold}] {info[fold]}")
    tasks = [(f, dgp, L.SEED + 10_000 * fi + 5_000 * di + k) for fi, f in enumerate(L.FOLDS)
             for di, dgp in enumerate(("S", "G")) if dgp in P[f]["lin"] for k in range(reps)]
    t0 = time.time()
    res = pd.DataFrame(L.pool({"P": P}, _rep, tasks, chunksize=10))
    logger.info(f"{len(res)} reps in {time.time() - t0:.0f}s")
    res["ret"] = res.b_M1 / res.b_M0
    res.to_csv(L.RES / "k2_power_reps.csv", index=False)
    out = {"label": "POST-CONFIRMATION EXPLORATORY: design analysis (no K2 coefficient read)", "reps": reps,
           "folds": {}}
    # fixed IVW weights for the pooled simulated retention: recorded co-primary SE on the log-IRR/SD scale
    w = {f: 1 / (info[f]["recorded_se_b"] * info[f]["sd_A_base"]) ** 2 for f in L.FOLDS}
    for f in L.FOLDS:
        o = dict(info[f])
        for dgp in ("S", "G"):
            x = res[(res.fold == f) & (res.dgp == dgp)].dropna(subset=["ret"])
            if not len(x):
                o[f"DGP_{dgp}"] = None
                continue
            o[f"DGP_{dgp}"] = {"n_ok": int(len(x)), "ret_median": float(x.ret.median()),
                               "ret_q025_q975": [float(x.ret.quantile(.025)), float(x.ret.quantile(.975))],
                               "P_ret_ge_0.5": float((x.ret >= 0.5).mean()), "P_ret_lt_0.5": float((x.ret < 0.5).mean()),
                               "b0_mean": float(x.b_M0.mean()), "b1_mean": float(x.b_M1.mean())}
        o["retention_underpowered"] = bool(o["DGP_S"] is None or o["DGP_S"]["P_ret_ge_0.5"] < 0.8)
        out["folds"][f] = o
    pooled = {}
    for dgp in ("S", "G"):
        folds = [f for f in L.FOLDS if dgp in P[f]["lin"]]
        if len(folds) < len(L.FOLDS):
            pooled[f"DGP_{dgp}"] = {"note": f"not constructible in {sorted(set(L.FOLDS) - set(folds))}"}
            continue
        ks = [res[(res.fold == f) & (res.dgp == dgp)].sort_values("seed").reset_index(drop=True) for f in folds]
        n = min(len(k) for k in ks)
        num = sum(w[f] * ks[i].b_M1[:n].to_numpy() * info[f]["sd_A_base"] for i, f in enumerate(folds))
        den = sum(w[f] * ks[i].b_M0[:n].to_numpy() * info[f]["sd_A_base"] for i, f in enumerate(folds))
        r = pd.Series(num / den).dropna()
        pooled[f"DGP_{dgp}"] = {"n_ok": int(len(r)), "ret_median": float(r.median()),
                                "ret_q025_q975": [float(r.quantile(.025)), float(r.quantile(.975))],
                                "P_ret_ge_0.5": float((r >= 0.5).mean()), "P_ret_lt_0.5": float((r < 0.5).mean())}
    pooled["weights"] = {f: w[f] / sum(w.values()) for f in L.FOLDS}
    pooled["retention_underpowered"] = bool("P_ret_ge_0.5" not in pooled["DGP_S"] or
                                            pooled["DGP_S"]["P_ret_ge_0.5"] < 0.8)
    out["pooled"] = pooled
    p = L.RES / "k2_power.json"
    L.dump(p, L.clean(out))
    (L.RES / "k2_power.sha256").write_text(f"{L.sha256_file(p)}  k2_power.json  "
                                           f"{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}\n")
    with open(L.LOGS / "freeze_log.txt", "a") as fh:
        fh.write(f"k2_power.json sha256={L.sha256_file(p)} written before any K2 fit\n")
    logger.info(json.dumps(L.clean({f: {k: out["folds"][f][k] for k in ("DGP_S", "DGP_G", "retention_underpowered")}
                                     for f in L.FOLDS}), default=str)[:3000])
    logger.info(f"pooled: {out['pooled']}")


if __name__ == "__main__":
    sys.exit(main())
