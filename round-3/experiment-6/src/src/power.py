"""Step 9a: minimum detectable effects (MDE) by simulation.

Held-out size: MAIN held-out concepts with >= 1 eligible W1 row where the openness measure is finite (sealed W1
feature file; no outcomes are read). Data-generating process per rep: resample n concepts (whole row blocks) from the
screen MAIN model rows; Y* = X b_hat (openness coefficient set to 0) + beta * SD(Y) * openness_z + e*, where e* is
the concept's own residual block times a Rademacher sign per concept (wild-cluster). Test: one-sided CR1 t-test
(G-1 df) at 0.05 in the D1 direction (negative). MDE = smallest |beta| (in SD(Y) per SD(openness)) with power >= 0.80.
Verification at the MDE uses the frozen decision rule (cluster-bootstrap 95% CI excluding 0, 200 reps).
Transfer delta-R2 MDE: FULL and BASE fit on a simulated screen, evaluated on a simulated held-out sample,
concept-bootstrap (200) CI lower bound > 0.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from loguru import logger
from scipy import stats

import common as K
from common import OUT, SEALED

import stats_core as S
from models import OUTCOMES, model_rows, pop_mask

PDIR = OUT / "power"
BETAS = np.linspace(0, 0.5, 15)
SEED = 20261003


def _sim_setup(m: pd.DataFrame, y: str, ov: str) -> dict:
    X, names, _ = S.design(m, [ov])
    yy = m[y].astype(float).values
    b = S.ols(X, yy)
    resid = yy - X @ b
    b0 = b.copy()
    b0[1] = 0.0
    return dict(X=X, mu0=X @ b0, resid=resid, sdy=float(yy.std(ddof=1)), blocks=S.blocks_of(m.concept_id.values))


def _draw(st: dict, n: int, beta: float, rng) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    pick = rng.integers(0, len(st["blocks"]), n)
    idx = np.concatenate([st["blocks"][k] for k in pick])
    g = np.repeat(np.arange(n), [len(st["blocks"][k]) for k in pick])
    sign = rng.choice([-1.0, 1.0], n)[g]
    X = st["X"][idx]
    y = st["mu0"][idx] + beta * st["sdy"] * X[:, 1] + sign * st["resid"][idx]
    return X, y, g


def power_curve(st: dict, n: int, reps: int, rng) -> list[dict]:
    out = []
    for beta in BETAS:
        rej = 0
        for _ in range(reps):
            X, y, g = _draw(st, n, -beta, rng)
            bb, se = S.cr1(X, y, g)
            tcrit = stats.t.ppf(0.95, n - 1)
            rej += int(se[1] > 0 and bb[1] / se[1] < -tcrit)
        out.append(dict(beta_sd=float(beta), power=rej / reps))
    return out


def mde_from(curve: list[dict]) -> float:
    for a, b in zip(curve, curve[1:]):
        if a["power"] < 0.8 <= b["power"]:
            return float(a["beta_sd"] + (0.8 - a["power"]) * (b["beta_sd"] - a["beta_sd"]) / (b["power"] - a["power"]))
    return float(curve[0]["beta_sd"]) if curve[0]["power"] >= 0.8 else float("nan")


def verify_boot(st: dict, n: int, beta: float, rng, n_sets: int = 100, B: int = 200) -> float:
    ok = 0
    for _ in range(n_sets):
        X, y, g = _draw(st, n, -beta, rng)
        dr = S.cluster_boot(X, y, g, B, int(rng.integers(1 << 30)), 1)
        ok += int(np.percentile(dr, 97.5) < 0)
    return ok / n_sets


def transfer_curve(st: dict, n_scr: int, n_ho: int, reps: int, rng, B: int = 200) -> list[dict]:
    out = []
    for beta in BETAS:
        hits = 0
        for _ in range(reps):
            Xs, ys, _ = _draw(st, n_scr, -beta, rng)
            Xh, yh, gh = _draw(st, n_ho, -beta, rng)
            pf = Xh @ S.ols(Xs, ys)
            Xsb, Xhb = np.delete(Xs, 1, axis=1), np.delete(Xh, 1, axis=1)
            pb = Xhb @ S.ols(Xsb, ys)
            blocks = S.blocks_of(gh)
            d = []
            for _b in range(B):
                idx = np.concatenate([blocks[k] for k in rng.integers(0, len(blocks), len(blocks))])
                d.append(S.r2(yh[idx], pf[idx]) - S.r2(yh[idx], pb[idx]))
            hits += int(np.percentile(d, 2.5) > 0)
        out.append(dict(beta_sd=float(beta), power=hits / reps))
    return out


def run(mini: bool = False) -> None:
    PDIR.mkdir(parents=True, exist_ok=True)
    reps = 100 if mini else 1000
    treps = 60 if mini else 300
    d = pd.read_parquet(OUT / "d1" / "panel_ct.parquet")
    dm = d[pop_mask(d, "MAIN")]
    H = pd.read_parquet(SEALED / "features_ct_heldout.parquet")
    H = H[H.in_MAIN]
    rng = np.random.default_rng(SEED)
    res = dict(method=__doc__, n_MAIN_heldout_concepts_total=None, per_measure={})
    import json
    pop = json.loads((OUT / "population" / "main_population_hydrated.json").read_text())
    res["n_MAIN_heldout_concepts_total"] = pop["counts"]["in_MAIN"]["by_fold"].get("heldout_concept")
    for ov in ["closure_res_z", "closure_res_imp_z"]:
        Hc = H[H[ov].notna()]
        n_ho = int(Hc.concept_id.nunique())
        rpc = Hc.groupby("concept_id").size().value_counts().sort_index().to_dict()
        per = dict(n_ho_effective=n_ho, heldout_rows=len(Hc), heldout_rows_per_concept=rpc, outcomes={})
        for y in OUTCOMES:
            m = model_rows(dm, y, [ov], S.NUM_BASE)
            st = _sim_setup(m, y, ov)
            n_scr = int(m.concept_id.nunique())
            curve = power_curve(st, n_ho, reps, rng)
            mde = mde_from(curve)
            curve_scr = power_curve(st, n_scr, max(reps // 2, 50), rng)
            mde_scr = mde_from(curve_scr)
            ver = verify_boot(st, n_ho, mde, rng, n_sets=40 if mini else 100) if np.isfinite(mde) else float("nan")
            tcurve = transfer_curve(st, n_scr, n_ho, treps, rng)
            per["outcomes"][y] = dict(sd_y=st["sdy"], n_screen_concepts=n_scr, power_curve_heldout=curve, mde_heldout_sd=mde,
                                      mde_heldout_raw=mde * st["sdy"] if np.isfinite(mde) else None,
                                      power_curve_screen=curve_scr, mde_screen_sd=mde_scr,
                                      bootstrap_rule_power_at_mde=ver, transfer_delta_r2_power_curve=tcurve,
                                      transfer_mde_sd=mde_from(tcurve))
            logger.info(f"MDE {ov} {y}: held-out n={n_ho} -> {mde:.3f} SD(Y) (boot-rule power at MDE {ver}); "
                        f"screen n={n_scr} -> {mde_scr:.3f}; transfer dR2 MDE {mde_from(tcurve):.3f}")
        res["per_measure"][ov] = per
    # E_up subset (secondary): MDE at its own screen size (rows t in [onset-3, onset])
    eu = dm[dm.E_up.values.astype(bool)]
    eu = eu[(eu.t >= eu.E_up_onset - 3) & (eu.t <= eu.E_up_onset) & (eu.E_up_onset <= 2015)]
    res["E_up_subset"] = {}
    for y in OUTCOMES:
        m = model_rows(eu, y, ["closure_res_z"], S.NUM_BASE)
        if m.concept_id.nunique() < 10:
            continue
        st = _sim_setup(m, y, "closure_res_z")
        n = int(m.concept_id.nunique())
        curve = power_curve(st, n, max(reps // 2, 50), rng)
        res["E_up_subset"][y] = dict(n_concepts=n, n_rows=len(m), power_curve=curve, mde_sd=mde_from(curve), sd_y=st["sdy"])
        logger.info(f"MDE E_up subset {y}: n={n} -> {mde_from(curve):.3f} SD(Y)")
    K.write_json(PDIR / "mde.json", res)
