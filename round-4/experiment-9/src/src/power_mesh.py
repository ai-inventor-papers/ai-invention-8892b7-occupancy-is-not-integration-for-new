"""STAGE 8a: MDE by simulation on the ACTUAL MeSH W1 design (no MeSH outcome is read) + T3 synthetic recovery.

Baseline rates come from the main SCREEN (gate 2) co-primary controls-only PPML (M0): gamma (controls) and the
fixed-effect component fe_i = log mu0_i - offset_i - X_i gamma. A MeSH event gets
    log mu0 = offset + X_mesh gamma + u_c + v_i
with u_c = a main concept's mean fe (one draw per MeSH concept) and v_i = a main within-concept fe deviation
(one draw per event), so the main pool's between/within-concept rate variation carries over. Outcomes are drawn as
NB2(mu0 x exp(b (A - mean A)), theta_main), b = log(IRR) / SD(A_cont on the MeSH sample). Each replicate refits
R2 (co-primary), R1 (primary) and the G1 co-primary; rejection = b > 0 and two-sided CRV1 p < 0.025 (the Holm
level for the smaller of two p values). T3: bias of the per-SD log IRR at 1.30 and 1.00, and size at 1.00 for CRV1
and for the wild score bootstrap (first 50 reps, 399 draws).
"""
from __future__ import annotations

import multiprocessing as mp
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd
from loguru import logger
from scipy import stats

import common
from common import SEED

_S: dict = {}
GRID = [1.00, 1.05, 1.10, 1.15, 1.20, 1.30, 1.40]


def nb2_theta(y: np.ndarray, mu: np.ndarray) -> float:
    num = np.sum(mu ** 2)
    den = np.sum((y - mu) ** 2 - y)
    return float(num / den) if den > 0 else 1e6


def main_baseline(sc: list[str]) -> dict:
    """gamma, theta and the fe decomposition from the main screen controls-only co-primary fit."""
    import models as vmodels
    import ppml
    df = pd.read_parquet(common.GATE / "gate2" / "screen_events_with_outcomes.parquet")
    s = vmodels.primary_sample(df)
    r0 = ppml.fit(s.Y_strict.to_numpy(float), s[sc].to_numpy(float), vmodels.fe_arrays(s, "secondary"),
                  s.offset.to_numpy(), s.concept_id.to_numpy(), maxit=500, tol=1e-12)
    base = s[r0["keep"]].copy()
    mu0 = r0["mu"]
    fe = np.log(mu0) - base.offset.to_numpy() - base[sc].to_numpy(float) @ r0["coef"]
    base["fe"] = fe
    cm = base.groupby("concept_id").fe.transform("mean")
    return {"gamma": r0["coef"], "theta": nb2_theta(base.Y_strict.to_numpy(float), mu0),
            "u": base.groupby("concept_id").fe.mean().to_numpy(), "v": (base.fe - cm).to_numpy(),
            "n_main": int(len(base)), "G_main": int(base.concept_id.nunique()),
            "main_mean_y_per_paper": float((base.Y_strict / base.n_entry_papers).mean())}


def fe_cols(s: pd.DataFrame) -> pd.DataFrame:
    s = s.copy()
    s["cxe"] = pd.factorize(s.concept_id + "_" + s.e.astype(str))[0]
    s["dxe"] = pd.factorize(s.d.astype(str) + "_" + s.e.astype(str))[0]
    s["cfe"] = pd.factorize(s.concept_id)[0]
    s["efe"] = pd.factorize(s.e.astype(str))[0]
    s["dfe"] = pd.factorize(s.d.astype(str))[0]
    s["cx2"] = pd.factorize(s.concept_id + "_" + ((s.e - 2005) // 2).astype(str))[0]
    s["offset"] = np.log(s.n_entry_papers.astype(float))
    return s


def _init(designs: dict, bl: dict):
    _S.update(designs=designs, bl=bl)


def _rep(args) -> dict:
    import ppml
    irr, seed, do_wild = args
    rng = np.random.default_rng(seed)
    bl = _S["bl"]
    out = {"irr": irr, "seed": seed}
    for name, dsg in _S["designs"].items():
        s, sc, fes_spec = dsg["s"], dsg["controls_sim"], dsg["fe"]
        conc = s.concept_id.to_numpy()
        uc = {c: rng.choice(bl["u"]) for c in np.unique(conc)}
        eta = s.offset.to_numpy() + s[sc].to_numpy(float) @ bl["gamma"] + np.array([uc[c] for c in conc]) + \
            rng.choice(bl["v"], len(s))
        a = s.A_cont.to_numpy()
        b = np.log(irr) / a.std(ddof=1)
        mu = np.exp(np.clip(eta + b * (a - a.mean()), -20, 12))
        lam = rng.gamma(bl["theta"], mu / bl["theta"])
        y = rng.poisson(lam).astype(float)
        X = s[["A_cont", "CT"] + dsg["controls"]].to_numpy(float)
        fes = [s[c].to_numpy() for c in fes_spec]
        try:
            r = ppml.fit(y, X, fes, s.offset.to_numpy(), conc, maxit=200, tol=1e-10)
        except (RuntimeError, np.linalg.LinAlgError, ValueError):
            r = None
        if r is None:
            out[f"reject_{name}"] = None
            continue
        t = r["coef"][0] / r["se"][0]
        p = 2 * stats.t.sf(abs(t), r["G"] - 1)
        sd = float(s.loc[r["keep"], "A_cont"].std())
        out[f"reject_{name}"] = bool(p < 0.025 and r["coef"][0] > 0)
        out[f"p_{name}"] = float(p)
        out[f"lnirr_sd_{name}"] = float(r["coef"][0] * sd)
        out[f"n_{name}"] = int(r["n"])
        out[f"G_{name}"] = int(r["G"])
        if do_wild and name == "R2":
            Xr = np.delete(X, 0, axis=1)
            out["p_wild_R2"] = ppml.wild_score_test(y, Xr, X[:, 0], fes, s.offset.to_numpy(), conc, rng, reps=399)
    return out


def run(designs: dict, sc_main: list[str], reps: int = 200, wild_reps_first: int = 50) -> dict:
    bl = main_baseline(sc_main)
    logger.info(f"power baseline: theta {bl['theta']:.3f}; main N {bl['n_main']} G {bl['G_main']}")
    tasks = [(irr, SEED + 30000 + 1000 * gi + k, (irr in (1.0, 1.3)) and k < wild_reps_first)
             for gi, irr in enumerate(GRID) for k in range(reps)]
    with ProcessPoolExecutor(common.detect_cpus(), mp_context=mp.get_context("spawn"), initializer=_init,
                             initargs=(designs, bl)) as ex:
        res = pd.DataFrame(list(ex.map(_rep, tasks, chunksize=8)))
    res.to_csv(common.RESULTS / "power_reps_mesh.csv", index=False)
    curve, mde, fails = {}, {}, {}
    for name in designs:
        col = f"reject_{name}"
        pw = res.groupby("irr")[col].apply(lambda x: float(pd.Series(x).dropna().astype(float).mean()))
        curve[name] = {str(k): v for k, v in pw.items()}
        fails[name] = int(res[col].isna().sum())
        mde[name] = next((float(k) for k, v in sorted(pw.items()) if v >= 0.80), None)
    t3 = {}
    for irr in (1.0, 1.3):
        g = res[res.irr == irr]
        e = g["lnirr_sd_R2"].dropna()
        t3[str(irr)] = {"mean_lnirr_sd_R2": float(e.mean()), "true": float(np.log(irr)),
                        "bias": float(e.mean() - np.log(irr)), "n": int(len(e))}
    g0 = res[res.irr == 1.0]
    size_crv1 = float((g0["p_R2"].dropna() < 0.05).mean())
    pw_ = g0["p_wild_R2"].dropna() if "p_wild_R2" in g0 else pd.Series(dtype=float)
    size_wild = float((pw_ < 0.05).mean()) if len(pw_) else None
    t3["size_at_1.00_R2"] = {"crv1_two_sided_0.05": size_crv1, "wild_0.05": size_wild, "n_wild": int(len(pw_))}
    t3["pass_bias"] = all(abs(t3[k]["bias"]) < 0.02 for k in ("1.0", "1.3"))
    t3["pass_size"] = bool(0.03 <= size_crv1 <= 0.08 and (size_wild is None or 0.03 <= size_wild <= 0.08))
    out = {"grid": GRID, "reps_per_cell": reps, "theta_nb2_main": bl["theta"], "power_curve": curve,
           "MDE80_irr_per_sd": mde, "failed_fits": fails,
           "mean_retained": {n: {"N": float(res[f"n_{n}"].mean()), "G": float(res[f"G_{n}"].mean())} for n in designs
                             if f"n_{n}" in res},
           "rejection_rule": "b_A > 0 and two-sided CRV1 p < 0.025 (Holm level for the smaller of two p values)",
           "T3_synthetic_recovery": t3,
           "dgp": "log mu0 = offset + X gamma_main + u_c + v_i (main screen M0 decomposition); NB2(theta_main)",
           "sd_A_cont_design": {n: float(d["s"].A_cont.std()) for n, d in designs.items()}}
    common.dump(common.RESULTS / "power_mesh.json", out)
    logger.info(f"power: MDE {mde}; T3 {t3}")
    return out
