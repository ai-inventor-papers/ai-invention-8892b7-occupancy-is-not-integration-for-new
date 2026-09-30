"""STEP 2 power: design-based MDEs on the ACTUAL frozen strata / concept structure, before any exposure is read.

(a) primary enrichment OR: control prevalence p0 x true OR grid, concept random effect (latent ICC 0.1), 1:1 strata,
    conditional logit with concept-cluster-robust Wald test (two-sided 0.05, positive direction counted).
(b) continuous interaction: OR_i = OR_main * ratio^{z(A_cont)_i}, test of E x z.
(c) mediation: synthetic outcome from the fitted co-primary PPML where a share s of b_A runs through the ACTUAL M2
    (Y* ~ Poisson), joint-significance detection (Gamma path fixed and significant; beta_M CRV1 p < 0.05), plus the
    sampling distribution of the attenuation share.
"""
from __future__ import annotations

import multiprocessing as mp
from concurrent.futures import ProcessPoolExecutor

import numpy as np
from scipy import stats

from stats_core import clogit

ICC = 0.1
SIG_U = float(np.sqrt(ICC * (np.pi ** 2 / 3) / (1 - ICC)))


def _expit(x):
    return 1 / (1 + np.exp(-x))


def sim_pairs(conc: np.ndarray, z: np.ndarray, p0: float, orv: float, ratio: float, reps: int, seed: int,
              interaction: bool) -> float:
    rng = np.random.default_rng(seed)
    n = len(conc)
    _, ci = np.unique(conc, return_inverse=True)
    strata = np.repeat(np.arange(n), 2)
    y = np.tile([1, 0], n)
    cl = np.repeat(conc, 2)
    hits = 0
    done = 0
    for _ in range(reps):
        u = rng.normal(0, SIG_U, ci.max() + 1)[ci]
        pc = _expit(np.log(p0 / (1 - p0)) + u)
        x0 = rng.random(n) < pc
        orr = orv * (ratio ** z) if interaction else np.full(n, orv)
        p1 = pc * orr / (1 - pc + pc * orr)
        x1 = rng.random(n) < p1
        E = np.empty(2 * n)
        E[0::2], E[1::2] = x1, x0
        if interaction:
            X = np.column_stack([E, E * np.repeat(z, 2)])
            j = 1
        else:
            X = E[:, None]
            j = 0
        try:
            r = clogit(y, X, strata, cl)
        except (FloatingPointError, ValueError):
            continue
        b, se = r["beta"][j], r["se_crv"][j]
        done += 1
        if np.isfinite(se) and se > 0 and b / se > stats.norm.ppf(0.975):
            hits += 1
    return hits / max(done, 1)


def _pair_job(args):
    return args[:4], sim_pairs(*args[4:])


def pair_power(conc: np.ndarray, z: np.ndarray, reps: int, seed: int, workers: int) -> dict:
    jobs = []
    k = 0
    for p0 in (0.1, 0.25, 0.4, 0.6):
        for orv in (1.0, 1.1, 1.2, 1.3, 1.5, 2.0):
            jobs.append(("main", p0, orv, 1.0, conc, z, p0, orv, 1.0, reps, seed + k, False))
            k += 1
        for ratio in (1.0, 1.1, 1.2, 1.3, 1.5):
            jobs.append(("inter", p0, 1.2, ratio, conc, z, p0, 1.2, ratio, reps, seed + k, True))
            k += 1
    with ProcessPoolExecutor(max_workers=workers, mp_context=mp.get_context("spawn")) as ex:
        res = list(ex.map(_pair_job, jobs))
    grid = [{"kind": a[0], "p0": a[1], "OR": a[2], "ratio": a[3], "power": pw} for a, pw in res]
    out = {"grid": grid, "reps": reps, "icc": ICC, "n_pairs": int(len(conc)), "n_concepts": int(len(np.unique(conc)))}
    mde = {}
    for p0 in (0.1, 0.25, 0.4, 0.6):
        g = [r for r in grid if r["kind"] == "main" and r["p0"] == p0 and r["power"] >= 0.8]
        mde[f"OR_p0_{p0}"] = min((r["OR"] for r in g), default=None)
        g = [r for r in grid if r["kind"] == "inter" and r["p0"] == p0 and r["power"] >= 0.8]
        mde[f"inter_ratio_p0_{p0}"] = min((r["ratio"] for r in g), default=None)
    out["MDE80"] = mde
    return out


# ------------------------- mediation power -------------------------
def _med_job(args):
    import sys
    sys.path.insert(0, args["vendor"])
    import ppml  # vendored
    rng = np.random.default_rng(args["seed"])
    mu_base, A, M, X, fes, off, cl = (args[k] for k in ("mu0", "A", "M", "X", "fes", "off", "cl"))
    bA, s, Gam = args["bA"], args["share"], args["Gamma"]
    bM = s * bA / Gam if Gam != 0 else 0.0
    eta = np.log(mu_base) - bA * A + (1 - s) * bA * A + bM * (M - M.mean())
    hits, att = 0, []
    for _ in range(args["reps"]):
        ys = rng.poisson(np.exp(np.clip(eta, -30, 20))).astype(float)
        r0 = ppml.fit(ys, X, fes, off, cl, maxit=200, tol=1e-9)
        r1 = ppml.fit(ys, np.column_stack([X, M]), fes, off, cl, maxit=200, tol=1e-9)
        if r0 is None or r1 is None:
            continue
        b0, b1 = r0["coef"][0], r1["coef"][0]
        att.append((b0 - b1) / b0 if b0 != 0 else np.nan)
        tq = stats.t.ppf(0.975, r1["G"] - 1)
        if abs(r1["coef"][-1] / r1["se"][-1]) > tq:
            hits += 1
    return {"share": s, "power_joint": hits / max(len(att), 1), "att_mean": float(np.nanmean(att)),
            "att_sd": float(np.nanstd(att)), "n_ok": len(att)}


def mediation_power(base: dict, reps: int, seed: int, workers: int, gamma_sig: bool) -> dict:
    jobs = []
    per = int(np.ceil(reps / 2))
    for k, s in enumerate((0.0, 0.2, 0.4, 0.6)):
        for h in range(2):
            jobs.append({**base, "share": s, "reps": per, "seed": seed + 100 * k + h})
    with ProcessPoolExecutor(max_workers=workers, mp_context=mp.get_context("spawn")) as ex:
        res = list(ex.map(_med_job, jobs))
    agg = {}
    for r in res:
        a = agg.setdefault(r["share"], {"hits": 0.0, "n": 0, "att": [], "sd": []})
        a["hits"] += r["power_joint"] * r["n_ok"]
        a["n"] += r["n_ok"]
        a["att"].append(r["att_mean"])
        a["sd"].append(r["att_sd"])
    grid = [{"share": s, "power_joint": (a["hits"] / a["n"] if a["n"] else None) if gamma_sig else 0.0,
             "att_mean": float(np.mean(a["att"])), "att_sd": float(np.mean(a["sd"])), "n_reps": a["n"]}
            for s, a in sorted(agg.items())]
    mde = min((g["share"] for g in grid if g["share"] > 0 and g["power_joint"] and g["power_joint"] >= 0.8),
              default=None)
    return {"grid": grid, "MDE80_share": mde, "gamma_significant": gamma_sig, "Gamma": base["Gamma"]}
