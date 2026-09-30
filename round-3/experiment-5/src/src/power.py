"""Step 8a: held-out MDE simulation for the event-study and pooled-panel estimators; picks the held-out primary.

Event study: M0 = screen primary-cell treated x k difference matrix with every k column centred (null). Each sim
draws n_h_treated rows with replacement and bootstraps S (B = 400); the one-sided 95% bound in the screened direction
is recorded. Injecting delta in the screened direction shifts every bootstrap S by exactly delta (all finite window
entries move by delta), so power(delta) = P(bound0 beyond delta) is computed from the same 500 null sims for every
grid value (exact, not an approximation).
Pooled panel: resample n_h concepts (with their concept-years) from the screen panel; the fitted futE effect is removed;
OLS row ~ futE + log_vol3 + age + year FE with CR1 concept-cluster SE. Adding delta to futE rows shifts coef(futE) by
exactly delta and leaves the SE unchanged, so power again follows from the null sims.
Rule (fixed in SPEC3): held-out primary estimator per row = smaller MDE; ties within 5% -> event study.
"""
from __future__ import annotations

import json
import math
import warnings

import numpy as np
import pandas as pd
from loguru import logger

import common as K

ROWS = ["closure", "closure_resT", "closure_persist", "constraint", "xc_excess", "wmz"]
Z95 = 1.6448536269514722


def eligible_heldout(pop: pd.DataFrame) -> int:
    """Held-out MAIN concepts with >= 1 focal t in [F+3, F+8] within the onset window (uses F only, no outcome)."""
    import config as C
    ho = pop[(pop.fold == "heldout") & pop.MAIN.astype(bool)]
    ok = 0
    for F in ho.F.astype(int):
        ts = [t for t in range(F + C.SPEC["ages"][0], F + C.SPEC["ages"][1] + 1)
              if t in C.SPEC["screen_onset_years"] and t <= C.SPEC["t_max"] and t not in C.SPEC["sealed_focal_years"]]
        ok += bool(ts)
    return ok


def es_bounds(M0: np.ndarray, n: int, sims: int, B: int, seed: int, direction: int) -> tuple[np.ndarray, np.ndarray]:
    """Null one-sided bounds (screened direction) and 95% CI widths for `sims` held-out-sized draws."""
    ks = K.SPEC3["es_rel_years"]
    lo, hi = K.SPEC3["es_primary_window"]
    wk = np.array([j for j, k in enumerate(ks) if lo <= k <= hi])
    rng = np.random.default_rng(seed)
    bounds, widths = np.full(sims, np.nan), np.full(sims, np.nan)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        for s in range(sims):
            Ms = M0[rng.integers(0, len(M0), n)]
            idx = rng.integers(0, n, (B, n))
            Mb = Ms[idx][:, :, wk]                      # B x n x window
            col = np.nanmean(Mb, axis=1)                # B x window
            bS = np.nanmean(col, axis=1)
            bS = bS[np.isfinite(bS)]
            if len(bS) < 10:
                continue
            bounds[s] = np.percentile(bS, 95) if direction < 0 else -np.percentile(bS, 5)
            widths[s] = np.percentile(bS, 97.5) - np.percentile(bS, 2.5)
    return bounds, widths


def power_curve(bounds: np.ndarray, grid: np.ndarray) -> np.ndarray:
    b = bounds[np.isfinite(bounds)]
    return np.array([float(np.mean(b < d)) for d in grid])


def mde_from(grid: np.ndarray, pw: np.ndarray, target: float) -> float:
    ok = np.where(pw >= target)[0]
    return float(grid[ok[0]]) if len(ok) else float("nan")


def cluster_ols(X: np.ndarray, y: np.ndarray, g: np.ndarray) -> tuple[float, float]:
    """coef[1] and its CR1 cluster-robust SE."""
    XtX_inv = np.linalg.pinv(X.T @ X)
    b = XtX_inv @ X.T @ y
    u = y - X @ b
    Xu = X * u[:, None]
    ug, inv = np.unique(g, return_inverse=True)
    S = np.zeros((len(ug), X.shape[1]))
    np.add.at(S, inv, Xu)
    meat = S.T @ S
    G, N, Kp = len(ug), len(y), X.shape[1]
    V = XtX_inv @ meat @ XtX_inv * (G / (G - 1)) * ((N - 1) / max(N - Kp, 1))
    return float(b[1]), float(math.sqrt(max(V[1, 1], 0)))


def panel_bounds(d: pd.DataFrame, col: str, n_conc: int, sims: int, seed: int, direction: int) -> tuple[np.ndarray, float, float]:
    dd = d[np.isfinite(d[col].astype(float))].reset_index(drop=True)
    years = sorted(dd.year.unique())

    def design(frame):
        return np.column_stack([np.ones(len(frame)), frame.futE.values, frame.log_vol3.values, frame.age.values] +
                               [(frame.year == y).astype(float).values for y in years[1:]])
    X = design(dd)
    y = dd[col].astype(float).values
    coef_full = float(np.linalg.lstsq(X, y, rcond=None)[0][1])
    y0 = y - coef_full * dd.futE.values
    conc = dd.concept_id.values
    uc = np.unique(conc)
    rows_by = {c: np.where(conc == c)[0] for c in uc}
    rng = np.random.default_rng(seed)
    out = np.full(sims, np.nan)
    for s in range(sims):
        pick = rng.choice(uc, n_conc, replace=True)
        ii = np.concatenate([rows_by[c] for c in pick])
        gid = np.concatenate([np.full(len(rows_by[c]), k) for k, c in enumerate(pick)])
        if X[ii, 1].sum() < 2:
            continue
        b, se = cluster_ols(X[ii], y0[ii], gid)
        out[s] = (b + Z95 * se) if direction < 0 else (-b + Z95 * se)
    return out, coef_full, float(np.nanstd(y))


def main() -> dict:
    import analysis_event as AE
    from event3 import cell_sets, panel_frame
    from labels3 import guard
    guard()
    ind = pd.read_parquet(K.RES / "indicators" / "concept_year_indicators_hydrated.parquet")
    lab = pd.read_parquet(K.RES / "labels" / "labels_screen.parquet")
    pf = json.loads((K.RES / "event_study" / "primary_family.json").read_text())
    m = pd.read_parquet(K.RES / "event_study" / "matches_primary.parquet")
    m["controls"] = m.controls.map(lambda s: [x for x in s.split("|") if x])
    pop = pd.read_parquet(K.WORK / "population.parquet")
    n_h_concepts = int(((pop.fold == "heldout") & pop.MAIN.astype(bool)).sum())
    n_h_elig = eligible_heldout(pop)
    onsets, never, lab_c = cell_sets(lab, "MAIN", "all", "E_up", "all")
    n_scr_elig = len(onsets) + len(never)
    onset_rate = len(onsets) / n_scr_elig
    match_rate = pf["match_rate"]
    n_h_treated = int(round(n_h_elig * onset_rate * match_rate))
    rng = np.random.default_rng(K.SPEC3["seeds"]["sim"])
    band = rng.binomial(rng.binomial(n_h_elig, onset_rate, 20000), match_rate)
    cfg = K.SPEC3["mde"]
    sd_rows = {c: float(ind.loc[(ind.fold == "screen") & (ind.year <= 2015), c].astype(float).std()) for c in ROWS}
    pfr = panel_frame(lab_c, ind)
    res = dict(n_h_concepts_MAIN=n_h_concepts, n_h_eligible=n_h_elig, screen_eligible=n_scr_elig, onset_rate=onset_rate,
               match_rate=match_rate, n_h_treated=n_h_treated, n_h_treated_80band=[int(np.percentile(band, 10)), int(np.percentile(band, 90))],
               n_screen_matched=pf["n_matched"], rows={})
    n_panel = int(round(n_h_elig))
    for col in ROWS:
        direction = -1 if K.SPEC3["screened_direction"].get(col, "-") == "-" else 1
        M, _ = AE.es_matrix(m, ind, col)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            M0 = M - np.nanmean(M, axis=0)[None, :]
        grid = np.linspace(0, cfg["grid_max_sd"] * sd_rows[col], cfg["grid_n"])
        b_es, w_es = es_bounds(M0, max(n_h_treated, 2), cfg["sims"], cfg["boot"], K.SPEC3["seeds"]["sim"], direction)
        pw_es = power_curve(b_es, grid)
        mde_es = mde_from(grid, pw_es, cfg["power"])
        b_scr, w_scr = es_bounds(M0, len(M0), cfg["sims"], cfg["boot"], K.SPEC3["seeds"]["sim"] + 1, direction)
        S_obs = pf["rows"][col]["primary"]["S"]
        ci_obs = pf["rows"][col]["primary"]["ci"]
        b_pp, coef_full, sd_y = panel_bounds(pfr, col, n_panel, cfg["sims"], K.SPEC3["seeds"]["sim"] + 2, direction)
        pw_pp = power_curve(b_pp, grid)
        mde_pp = mde_from(grid, pw_pp, cfg["power"])
        eff = abs(S_obs) if np.isfinite(S_obs) else np.nan
        chosen = "event_study"
        if np.isfinite(mde_pp) and (not np.isfinite(mde_es) or mde_pp < mde_es * (1 - cfg["tie_rel"])):
            chosen = "pooled_panel"
        res["rows"][col] = dict(
            direction="negative" if direction < 0 else "positive", sd=sd_rows[col], grid=grid.tolist(),
            es=dict(power=pw_es.tolist(), mde=mde_es, mde_sd=mde_es / sd_rows[col] if sd_rows[col] else np.nan,
                    mde_continuous=float(np.nanpercentile(b_es, 80)), size_at_0=float(np.nanmean(b_es < 0)),
                    power_at_screen_S=float(np.nanmean(b_es < eff)) if np.isfinite(eff) else np.nan,
                    power_at_half_screen_S=float(np.nanmean(b_es < eff / 2)) if np.isfinite(eff) else np.nan,
                    screen_n_power_at_screen_S=float(np.nanmean(b_scr < eff)) if np.isfinite(eff) else np.nan,
                    screen_n_mean_sim_ci_width=float(np.nanmean(w_scr)),
                    observed_ci_width=float(ci_obs[1] - ci_obs[0]) if ci_obs[0] is not None and np.isfinite(ci_obs[0]) else np.nan,
                    screen_S_sign_matches_direction=bool(np.isfinite(S_obs) and np.sign(S_obs) == direction)),
            panel=dict(power=pw_pp.tolist(), mde=mde_pp, mde_sd=mde_pp / sd_rows[col] if sd_rows[col] else np.nan,
                       mde_continuous=float(np.nanpercentile(b_pp, 80)), size_at_0=float(np.nanmean(b_pp < 0)),
                       n_concepts_per_sim=n_panel, screen_coef=coef_full,
                       power_at_screen_coef=float(np.nanmean(b_pp < abs(coef_full))),
                       power_at_half_screen_coef=float(np.nanmean(b_pp < abs(coef_full) / 2))),
            heldout_primary_estimator=chosen)
        logger.info(f"MDE {col}: ES {mde_es:.3f} ({res['rows'][col]['es']['mde_sd']:.2f} SD, size {res['rows'][col]['es']['size_at_0']:.3f}) "
                    f"vs panel {mde_pp:.3f} ({res['rows'][col]['panel']['mde_sd']:.2f} SD, size {res['rows'][col]['panel']['size_at_0']:.3f}) -> {chosen}")
    K.write_json(K.RES / "power_mde.json", res)
    return res


if __name__ == "__main__":
    K.setup_logging("power")
    main()
