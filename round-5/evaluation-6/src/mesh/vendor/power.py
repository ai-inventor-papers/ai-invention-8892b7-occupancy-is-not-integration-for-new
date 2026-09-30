"""STAGE 13: held-out MDE by simulation (no held-out outcomes are touched).

The held-out design size (MAIN, kw5, main arm) is read from the sealed feature file (W1 only). Each replicate
resamples screen MAIN concepts with replacement to the held-out concept count (duplicates get distinct ids), keeps
their events and covariates, draws Y ~ NB2(mu, theta) with mu = M0-fitted mu x exp(b (A - mean A)), b = log(IRR)/SD(A),
fits M1 (primary and co-primary secondary FE) and records rejection of b_A at the Holm level alpha = 0.025.
"""
from __future__ import annotations

import json
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd
from loguru import logger
from scipy import stats

import models
import ppml
from config import RESULTS, SEALED, SEED, SPEC, detect_cpus

_S = {}


def _init(base: pd.DataFrame, theta: float, n_conc: int, sd_a: float):
    _S.update(base=base, theta=theta, n_conc=n_conc, sd_a=sd_a)


def _rep(args) -> dict:
    irr, seed = args
    base, theta, n_conc, sd_a = _S["base"], _S["theta"], _S["n_conc"], _S["sd_a"]
    rng = np.random.default_rng(seed)
    cids = base.concept_id.unique()
    pick = rng.choice(cids, n_conc)
    g = {c: x for c, x in base.groupby("concept_id")}
    parts = []
    for i, c in enumerate(pick):
        x = g[c].copy()
        x["concept_id"] = f"{c}#{i}"
        parts.append(x)
    s = pd.concat(parts, ignore_index=True)
    b = np.log(irr) / sd_a
    mu = s.mu0.to_numpy() * np.exp(b * (s.A_cont.to_numpy() - base.A_cont.mean()))
    lam = rng.gamma(theta, mu / theta)
    s["Y_strict"] = rng.poisson(lam)
    s["cxe"] = pd.factorize(s.concept_id + "_" + s.e.astype(str))[0]
    s["dxe"] = pd.factorize(s.d.astype(str) + "_" + s.e.astype(str))[0]
    s["cfe"] = pd.factorize(s.concept_id)[0]
    out = {"irr": irr, "seed": seed}
    for spec, xs in (("primary", models.EVENT_CONTROLS), ("secondary", models.EVENT_CONTROLS + models.SECONDARY_EXTRA)):
        X = s[["A_cont", "CT"] + xs].to_numpy(float)
        try:
            r = ppml.fit(s.Y_strict.to_numpy(float), X, models.fe_arrays(s, spec), s.offset.to_numpy(),
                         s.concept_id.to_numpy())
        except (RuntimeError, np.linalg.LinAlgError):  # singular FE system in a resampled design -> failed fit
            r = None
        if r is None:
            out[f"reject_{spec}"] = None
            continue
        t = r["coef"][0] / r["se"][0]
        p = 2 * stats.t.sf(abs(t), r["G"] - 1)
        out[f"reject_{spec}"] = bool(p < 0.025 and r["coef"][0] > 0)
        out[f"n_{spec}"] = int(r["n"])
    return out


def nb2_theta(y: np.ndarray, mu: np.ndarray) -> float:
    """Method-of-moments NB2 dispersion: Var = mu + mu^2 / theta."""
    num = np.sum(mu ** 2)
    den = np.sum((y - mu) ** 2 - y)
    return float(num / den) if den > 0 else 1e6


def run(df: pd.DataFrame, reps: int | None = None) -> dict:
    reps = reps or SPEC["power_reps"]
    ho = pd.read_parquet(SEALED / "heldout_features.parquet", columns=["concept_id", "kw5", "MAIN", "arm"])
    ho = ho[ho.kw5 & ho.MAIN & (ho.arm == "main")]
    n_conc, n_ev = int(ho.concept_id.nunique()), int(len(ho))
    s = models.primary_sample(df)
    xs = models.EVENT_CONTROLS + models.SECONDARY_EXTRA
    r0 = ppml.fit(s.Y_strict.to_numpy(float), s[xs].to_numpy(float), models.fe_arrays(s, "secondary"),
                  s.offset.to_numpy(), s.concept_id.to_numpy(), maxit=500, tol=1e-12)
    base = s[r0["keep"]].copy()
    base["mu0"] = r0["mu"]
    r1 = models.fit_one(s, "Y_strict", ["A_cont", "CT"] + xs, "secondary")
    theta = nb2_theta(base.Y_strict.to_numpy(float), base.mu0.to_numpy())
    sd_a = float(base.A_cont.std())
    grid = SPEC["power_grid"]
    tasks = [(irr, SEED + 20000 + 1000 * gi + k) for gi, irr in enumerate(grid) for k in range(reps)]
    with ProcessPoolExecutor(detect_cpus(), initializer=_init, initargs=(base, theta, n_conc, sd_a)) as ex:
        res = pd.DataFrame(list(ex.map(_rep, tasks, chunksize=10)))
    res.to_csv(RESULTS / "power_reps.csv", index=False)
    curve = {}
    for spec in ("primary", "secondary"):
        pw = res.groupby("irr")[f"reject_{spec}"].apply(lambda x: float(pd.Series(x).dropna().astype(float).mean()))
        curve[spec] = {str(k): v for k, v in pw.items()}
        curve[f"{spec}_failed_fits"] = int(res[f"reject_{spec}"].isna().sum())
    mde = {spec: next((float(k) for k, v in sorted(((float(a), b) for a, b in curve[spec].items())) if v >= 0.80), None)
           for spec in ("primary", "secondary")}
    screen_irr = {"primary": models.fit_one(s, "Y_strict", ["A_cont", "CT"] + models.EVENT_CONTROLS, "primary")
                  ["irr_sd"]["A_cont"], "secondary": r1["irr_sd"]["A_cont"]}
    out = {"heldout_design": {"n_concepts": n_conc, "n_events": n_ev, "source": "sealed/heldout_features.parquet (W1 only)"},
           "reps_per_cell": reps, "theta_nb2": theta, "sd_A_cont": sd_a, "alpha": 0.025, "power_curve": curve,
           "MDE_irr_per_sd_power80": mde, "screen_irr_per_sd": screen_irr,
           "adequately_powered": {k: (mde[k] is not None and mde[k] <= screen_irr[k]) for k in mde},
           "dgp": "base mu from the screen secondary-FE M0 fit (controls only); NB2 gamma-Poisson; one-sided rejection "
                  "(b_A > 0 and two-sided p < 0.025)"}
    (RESULTS / "power_heldout.json").write_text(json.dumps(out, indent=1))
    logger.info(f"power: {out}")
    return out
