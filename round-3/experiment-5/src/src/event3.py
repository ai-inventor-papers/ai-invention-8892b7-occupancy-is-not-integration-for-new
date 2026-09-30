"""Step 6: matched E_up event study (exp_3 S definition) for raw closure, R1a, R1b, R1c and R1d rows; grid over
population x subset x label x route; primary family with Holm; H-matched sensitivity; pooled panels; R1a
correlations; R1d hub-not-clique.

S = mean over k in [-3, 0] of the per-k mean treated-minus-matched-control difference (vendored es_matrix/es_stats).
The bootstrap below replicates the vendored es_stats loop draw-for-draw (same RNG calls) and adds the -5..-1
sensitivity window and one-sided p-values; the primary S/CI are asserted equal to the vendored es_stats output.
"""
from __future__ import annotations

import math
import time
import warnings

import numpy as np
import pandas as pd
from loguru import logger

import common as K

ROWS_PRIMARY = ["closure_resT", "closure_persist", "constraint"]
ROWS = ["closure", "closure_resT", "closure_resT_cc", "closure_resT_raw", "closure_persist", "constraint", "cdeg_diag",
        "effsize", "efficiency", "xc_excess", "xc_obs", "wmz", "d_wmz", "d_closure", "new_relation_rate", "novelty",
        "beta_sim_rar", "log_vol3", "pct", "closure_res", "constraint_res", "xc_excess_res", "closure_persist_res",
        "n_ego", "persist_overlap"]
ROWS_GRID = ["closure", "closure_resT", "closure_persist", "constraint", "cdeg_diag", "xc_excess", "wmz", "d_wmz",
             "d_closure", "new_relation_rate", "novelty"]
DIRECTION = {"closure": -1, "closure_resT": -1, "closure_resT_cc": -1, "closure_resT_raw": -1, "closure_persist": -1,
             "constraint": -1, "cdeg_diag": -1, "closure_res": -1, "constraint_res": -1, "closure_persist_res": -1,
             "xc_excess": 1, "xc_excess_res": 1, "xc_obs": 1, "effsize": 1, "efficiency": 1, "wmz": 1, "d_wmz": 1,
             "d_closure": -1}


# ----------------------------------------------------------------------------- bootstrap (vendored draw order)
def es_boot(M: np.ndarray, B: int, seed: int, windows: dict | None = None) -> dict:
    ks = K.SPEC3["es_rel_years"]
    windows = windows or {"primary": tuple(K.SPEC3["es_primary_window"]), "sens": tuple(K.SPEC3["es_sens_window"])}
    wk = {n: [j for j, k in enumerate(ks) if lo <= k <= hi] for n, (lo, hi) in windows.items()}
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        diff = np.nanmean(M, axis=0) if len(M) else np.full(len(ks), np.nan)
        S = {n: (float(np.nanmean(diff[w])) if np.isfinite(diff[w]).any() else np.nan) for n, w in wk.items()}
        rng = np.random.default_rng(seed)
        bd = np.full((B, len(ks)), np.nan)
        bS = {n: np.full(B, np.nan) for n in wk}
        if len(M) >= 2:
            for b in range(B):
                idx = rng.integers(0, len(M), len(M))
                d = np.nanmean(M[idx], axis=0)
                bd[b] = d
                for n, w in wk.items():
                    bS[n][b] = np.nanmean(d[w]) if np.isfinite(d[w]).any() else np.nan
    out = dict(diff_k=diff.tolist(), n_k=np.isfinite(M).sum(0).astype(int).tolist() if len(M) else [0] * len(ks),
               n_treated=int(len(M)))
    for n in wk:
        x = bS[n][np.isfinite(bS[n])]
        if len(x) < 10:
            out[n] = dict(S=S[n], ci=[np.nan, np.nan], se=np.nan, p=np.nan, p_one_neg=np.nan, p_one_pos=np.nan,
                          ci90=[np.nan, np.nan])
            continue
        p = float(max(2 * min(np.mean(x <= 0), np.mean(x >= 0)), 1.0 / len(x)))
        out[n] = dict(S=S[n], ci=np.percentile(x, [2.5, 97.5]).tolist(), ci90=np.percentile(x, [5, 95]).tolist(),
                      se=float(np.std(x, ddof=1)), p=min(1.0, p),
                      p_one_neg=float(max(np.mean(x >= 0), 1.0 / len(x))),   # H1: S < 0
                      p_one_pos=float(max(np.mean(x <= 0), 1.0 / len(x))))   # H1: S > 0
    out["ci_k"] = [np.nanpercentile(bd[:, j], [2.5, 97.5]).tolist() if np.isfinite(bd[:, j]).sum() > 10 else [np.nan, np.nan]
                   for j in range(len(ks))]
    return out


def seed_for(col: str, cell: str = "") -> int:
    import lib_metrics as lm
    return lm.stable_seed(col, cell, K.SPEC3["seeds"]["es"]) % 2 ** 31


# ----------------------------------------------------------------------------- cell machinery
def cell_sets(lab: pd.DataFrame, P: str, subset: str, label: str, route: str, new_controls: str = "all") -> tuple[dict, set, pd.DataFrame]:
    d = lab[lab[P].astype(bool)]
    if route == "B_only":
        d = d[d.route == "B_s2_index"]
    per = d.drop_duplicates("concept_id").set_index("concept_id")
    g, on = per[f"group_{label}"], per[f"onset_{label}"]
    never = set(per.index[g == "never"])
    if subset == "new" and new_controls == "new_only":
        never = {c for c in never if per.loc[c, "old_new"] == "new"}
    tr = per[(g == "emerging")]
    if subset in ("old", "new"):
        tr = tr[tr.old_new == subset]
    onsets = {c: int(on[c]) for c in tr.index}
    lab_c = d.copy()
    lab_c["group"] = lab_c[f"group_{label}"]
    lab_c["onset"] = lab_c[f"onset_{label}"]
    return onsets, never, lab_c


def run_cell(lab: pd.DataFrame, ind: pd.DataFrame, P: str, subset: str, label: str, route: str, rows: list[str], B: int,
             new_controls: str = "all", match_fn=None) -> dict:
    import analysis_event as AE
    onsets, never, lab_c = cell_sets(lab, P, subset, label, route, new_controls)
    cell = f"{P}|{subset}|{label}|{route}" + ("|newctl" if new_controls != "all" else "")
    if not onsets:
        return dict(cell=cell, n_onsets=0, n_matched=0, rows={}, m=None)
    m = (match_fn or AE.match)(lab_c, ind, treated_onsets=onsets, never_set=never)
    mm = m[m.n_controls > 0]
    res = dict(cell=cell, n_onsets=len(m), n_matched=int(len(mm)), match_rate=float(len(mm) / len(m)),
               widened_share=float(mm.widened.mean()) if len(mm) else np.nan, n_never=len(never),
               n_unique_controls=len({c for cs in mm.controls for c in cs}), rows={}, m=m, contrib=[])
    for col in rows:
        if col not in ind.columns:
            continue
        M, contrib = AE.es_matrix(m, ind, col)
        st = es_boot(M, B, seed_for(col, cell))
        st["direction"] = DIRECTION.get(col, 0)
        res["rows"][col] = st
        res["contrib"] += contrib
    return res


def balance_ext(m: pd.DataFrame, ind: pd.DataFrame, lab_c: pd.DataFrame) -> list:
    import analysis_event as AE
    import lib_metrics as lm
    rows = AE.balance(m, ind, lab_c)
    val = ind.set_index(["concept_id", "year"])
    route = lab_c.drop_duplicates("concept_id").set_index("concept_id").route
    never = sorted(set(lab_c.loc[lab_c.group == "never", "concept_id"]))
    mm = m[m.n_controls > 0]

    def g(c, y, col):
        try:
            return float(val.loc[(c, y), col])
        except KeyError:
            return np.nan
    for col in ("closure", "closure_resT", "closure_persist", "constraint", "xc_excess", "new_relation_rate", "novelty",
                "beta_sim_rar", "wmz", "n_ego"):
        tr = [g(r.concept_id, r.t0, col) for r in mm.itertuples()]
        before = [g(n, r.t0, col) for r in mm.itertuples() for n in never]
        after = [np.nanmean([g(n, r.t0, col) for n in r.controls]) for r in mm.itertuples()]
        rows.append(dict(covariate=f"{col}@t0", smd_before=lm.smd(tr, before), smd_after=lm.smd(tr, after),
                         mean_treated=float(np.nanmean(tr)) if len(tr) else np.nan,
                         mean_controls_after=float(np.nanmean(after)) if len(after) else np.nan))
    rb_t = [float(route[c] == "B_s2_index") for c in mm.concept_id]
    rb_c = [float(np.mean([route[n] == "B_s2_index" for n in r.controls])) for r in mm.itertuples()]
    rows.append(dict(covariate="route_B_share", smd_before=lm.smd(rb_t, [float(route[n] == "B_s2_index") for n in never]),
                     smd_after=lm.smd(rb_t, rb_c), mean_treated=float(np.mean(rb_t)) if rb_t else np.nan,
                     mean_controls_after=float(np.mean(rb_c)) if rb_c else np.nan))
    return rows


def na_share_by_k(m: pd.DataFrame, ind: pd.DataFrame, col: str) -> dict:
    val = {(c, int(y)): v for c, y, v in zip(ind.concept_id, ind.year, ind[col].astype(float))}
    out = {}
    mm = m[m.n_controls > 0]
    for k in K.SPEC3["es_rel_years"]:
        t = [not np.isfinite(val.get((r.concept_id, r.t0 + k), np.nan)) for r in mm.itertuples()]
        c = [not np.isfinite(val.get((n, r.t0 + k), np.nan)) for r in mm.itertuples() for n in r.controls]
        out[str(k)] = dict(treated_na=float(np.mean(t)) if t else np.nan, control_na=float(np.mean(c)) if c else np.nan)
    win = [k for k in K.SPEC3["es_rel_years"] if K.SPEC3["es_primary_window"][0] <= k <= K.SPEC3["es_primary_window"][1]]
    tw = np.nanmean([out[str(k)]["treated_na"] for k in win])
    cw = np.nanmean([out[str(k)]["control_na"] for k in win])
    n_est = sum(1 for r in mm.itertuples() if any(np.isfinite(val.get((r.concept_id, r.t0 + k), np.nan)) for k in win))
    return dict(by_k=out, window_treated_na=float(tw), window_control_na=float(cw),
                window_na_gap_points=float(100 * (tw - cw)), n_treated_with_finite_in_window=int(n_est))


def match_H(lab: pd.DataFrame, ind: pd.DataFrame, treated_onsets: dict, never_set: set, h_caliper: float) -> pd.DataFrame:
    """Vendored matcher (same band x origin x +-20%/30% vol3 rule, 1:3 with replacement) + |H_t0 diff| <= h_caliper."""
    import config as C
    S = C.SPEC
    info = lab.drop_duplicates("concept_id").set_index("concept_id")
    vol3 = {(c, int(y)): v for c, y, v in zip(ind.concept_id, ind.year, ind.vol3)}
    H = {(c, int(y)): v for c, y, v in zip(ind.concept_id, ind.year, ind.H)}
    out = []
    for c, t0 in treated_onsets.items():
        v = vol3.get((c, t0), 0)
        h0 = H.get((c, t0), np.nan)
        cands = [n for n in never_set if info.loc[n, "F_band"] == info.loc[c, "F_band"]
                 and info.loc[n, "origin_group"] == info.loc[c, "origin_group"] and vol3.get((n, t0), 0) > 0
                 and np.isfinite(h0) and np.isfinite(H.get((n, t0), np.nan)) and abs(H[(n, t0)] - h0) <= h_caliper]
        chosen, widened = [], False
        for cal in (S["match"]["vol_caliper"], S["match"]["widen"]):
            ok = [(abs(math.log(vol3[(n, t0)]) - math.log(max(v, 1))), n) for n in cands if v > 0 and abs(vol3[(n, t0)] / v - 1) <= cal]
            if ok:
                ok.sort()
                chosen = [n for _, n in ok[: S["match"]["ratio"]]]
                widened = cal == S["match"]["widen"]
                break
        out.append(dict(concept_id=c, t0=t0, controls=chosen, n_controls=len(chosen), widened=widened, vol3_t0=v))
    return pd.DataFrame(out)


# ----------------------------------------------------------------------------- panels
def panel_frame(lab_c: pd.DataFrame, ind: pd.DataFrame) -> pd.DataFrame:
    """Vendored pooled-panel sample: emerging+never concepts, age >= 0, 2005-2015, drop post-onset years; futE."""
    grp = lab_c.drop_duplicates("concept_id").set_index("concept_id")
    d = ind[ind.concept_id.isin(grp.index[grp.group.isin(["emerging", "never"])])].copy()
    d = d[(d.age >= 0) & (d.year >= 2005) & (d.year <= 2015)]
    on = grp.onset.to_dict()
    d["futE"] = [(1.0 if (np.isfinite(on.get(c, np.nan)) and y <= on[c] <= y + 5) else 0.0) for c, y in zip(d.concept_id, d.year)]
    d = d[[not (np.isfinite(on.get(c, np.nan)) and y > on[c]) for c, y in zip(d.concept_id, d.year)]]
    d["route_B"] = (d.concept_id.map(grp.route) == "B_s2_index").astype(float)
    return d


def _covmat(d: pd.DataFrame, covs: list[str]) -> tuple[np.ndarray, list[str]]:
    cols, names = [], []
    for c in covs:
        x = d[c].astype(float).values
        na = ~np.isfinite(x)
        cols.append(np.where(na, np.nanmean(x) if np.isfinite(x).any() else 0.0, x))
        names.append(c)
        if na.any():
            cols.append(na.astype(float))
            names.append(f"{c}_isNA")
    return np.column_stack(cols), names


def extended_panel(d: pd.DataFrame, col: str, B: int, seed: int) -> dict:
    """col ~ futE + 6 R1a covariates (+NA dummies) + route_B + year FE; concept-cluster bootstrap."""
    dd = d[np.isfinite(d[col].astype(float))].reset_index(drop=True)
    if len(dd) < 30 or dd.futE.sum() < 5:
        return dict(n=len(dd), coef=np.nan, ci=[np.nan, np.nan])
    Xc, names = _covmat(dd, K.SPEC3["r1a_covariates"])
    years = sorted(dd.year.unique())
    X = np.column_stack([np.ones(len(dd)), dd.futE.values, Xc, dd.route_B.values] + [(dd.year == y).astype(float).values for y in years[1:]])
    yv = dd[col].astype(float).values
    coef = float(np.linalg.lstsq(X, yv, rcond=None)[0][1])
    conc = dd.concept_id.values
    uc = np.unique(conc)
    rows_by = {c: np.where(conc == c)[0] for c in uc}
    rng = np.random.default_rng(seed)
    bs = []
    for _ in range(B):
        ii = np.concatenate([rows_by[c] for c in rng.choice(uc, len(uc), replace=True)])
        if X[ii, 1].sum() < 2:
            continue
        bs.append(np.linalg.lstsq(X[ii], yv[ii], rcond=None)[0][1])
    bs = np.array(bs)
    sd = float(np.nanstd(yv))
    return dict(n=len(dd), n_concepts=len(uc), n_futE_rows=int(dd.futE.sum()), coef=coef, coef_in_sd=coef / sd if sd else np.nan,
                ci=np.percentile(bs, [2.5, 97.5]).tolist(), p=float(max(2 * min(np.mean(bs <= 0), np.mean(bs >= 0)), 1 / len(bs))),
                p_one_neg=float(max(np.mean(bs >= 0), 1 / len(bs))), covariates=names + ["route_B", "year FE"])


def partial_logit(d: pd.DataFrame, B: int, seed: int) -> dict:
    """logit futE ~ z(closure) + 6 covariates (+NA dummies) + route_B + year FE; concept-cluster bootstrap CI."""
    import statsmodels.api as sm
    from statsmodels.tools.sm_exceptions import PerfectSeparationError, PerfectSeparationWarning
    dd = d[np.isfinite(d.closure.astype(float))].reset_index(drop=True)
    z = (dd.closure - dd.closure.mean()) / dd.closure.std()
    Xc, names = _covmat(dd, K.SPEC3["r1a_covariates"])
    Xc = (Xc - Xc.mean(0)) / np.where(Xc.std(0) > 0, Xc.std(0), 1)
    years = sorted(dd.year.unique())
    X = np.column_stack([np.ones(len(dd)), z.values, Xc, dd.route_B.values] + [(dd.year == y).astype(float).values for y in years[1:]])
    y = dd.futE.values

    def fit(ii):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            try:
                r = sm.Logit(y[ii], X[ii]).fit(disp=0, maxiter=200, method="newton")
                b = float(r.params[1])
                return b if np.isfinite(b) and abs(b) < 20 else np.nan
            except (PerfectSeparationError, np.linalg.LinAlgError, ValueError, PerfectSeparationWarning):
                return np.nan
    coef = fit(np.arange(len(dd)))
    conc = dd.concept_id.values
    uc = np.unique(conc)
    rows_by = {c: np.where(conc == c)[0] for c in uc}
    rng = np.random.default_rng(seed)
    bs = np.array([fit(np.concatenate([rows_by[c] for c in rng.choice(uc, len(uc), replace=True)])) for _ in range(B)])
    ok = bs[np.isfinite(bs)]
    return dict(n=len(dd), n_pos=int(y.sum()), coef_per_sd_closure=coef, n_boot_ok=int(len(ok)),
                ci=np.percentile(ok, [2.5, 97.5]).tolist() if len(ok) > 20 else [np.nan, np.nan],
                p=float(max(2 * min(np.mean(ok <= 0), np.mean(ok >= 0)), 1 / len(ok))) if len(ok) > 20 else np.nan,
                covariates=names + ["route_B", "year FE"])


# ----------------------------------------------------------------------------- R1a correlations, R1d
def r1a_correlations(ind: pd.DataFrame, pop_ids: set, B: int, seed: int) -> dict:
    from scipy.stats import spearmanr
    d = ind[ind.concept_id.isin(pop_ids) & (ind.fold == "screen") & (ind.year >= 2003) & (ind.year <= 2015) & (ind.age >= -2)]
    out = {}
    for sub_name, sub in [("all", d)] + [(k, g) for k, g in d.groupby("old_new")]:
        for cov in ("new_relation_rate", "novelty", "beta_sim_rar"):
            x = sub[["concept_id", "closure", cov]].dropna()
            if len(x) < 20:
                continue
            dm = x.copy()
            dm["closure"] -= dm.groupby("concept_id").closure.transform("mean")
            dm[cov] -= dm.groupby("concept_id")[cov].transform("mean")

            def stats(fr, frd):
                return (float(np.corrcoef(fr.closure, fr[cov])[0, 1]), float(spearmanr(fr.closure, fr[cov]).statistic),
                        float(np.corrcoef(frd.closure, frd[cov])[0, 1]), float(spearmanr(frd.closure, frd[cov]).statistic))
            pt = stats(x, dm)
            uc = x.concept_id.unique()
            idx_x = {c: np.where(x.concept_id.values == c)[0] for c in uc}
            rng = np.random.default_rng(seed)
            bs = []
            for _ in range(B):
                ii = np.concatenate([idx_x[c] for c in rng.choice(uc, len(uc), replace=True)])
                bs.append(stats(x.iloc[ii], dm.iloc[ii]))
            bs = np.array(bs)
            ci = np.nanpercentile(bs, [2.5, 97.5], axis=0)
            out[f"{sub_name}|{cov}"] = dict(n=len(x), n_concepts=len(uc),
                                            pooled_pearson=pt[0], pooled_pearson_ci=ci[:, 0].tolist(),
                                            pooled_spearman=pt[1], pooled_spearman_ci=ci[:, 1].tolist(),
                                            demeaned_pearson=pt[2], demeaned_pearson_ci=ci[:, 2].tolist(),
                                            demeaned_spearman=pt[3], demeaned_spearman_ci=ci[:, 3].tolist())
    return out


def r1d(m: pd.DataFrame, ind: pd.DataFrame, pop_ids: set, B: int, seed: int) -> dict:
    val = ind.set_index(["concept_id", "year"])[["d_wmz", "d_closure"]]
    win = range(K.SPEC3["es_primary_window"][0], K.SPEC3["es_primary_window"][1] + 1)
    mm = m[m.n_controls > 0].reset_index(drop=True)

    def hub(c, y):
        try:
            a, b = val.loc[(c, y)]
        except KeyError:
            return np.nan
        return float(a > 0 and b < 0) if np.isfinite(a) and np.isfinite(b) else np.nan
    T = [[hub(r.concept_id, r.t0 + k) for k in win] for r in mm.itertuples()]
    Cc = [[hub(n, r.t0 + k) for n in r.controls for k in win] for r in mm.itertuples()]

    def share(ix):
        t = np.concatenate([np.array(T[i], float) for i in ix]) if len(ix) else np.array([])
        c = np.concatenate([np.array(Cc[i], float) for i in ix]) if len(ix) else np.array([])
        return (np.nanmean(t) if np.isfinite(t).any() else np.nan, np.nanmean(c) if np.isfinite(c).any() else np.nan)
    sT, sC = share(range(len(mm)))
    rng = np.random.default_rng(seed)
    bd = []
    for _ in range(B):
        a, b = share(rng.integers(0, len(mm), len(mm)))
        bd.append(a - b)
    bd = np.array(bd)
    bd = bd[np.isfinite(bd)]
    # within-concept correlation of d_wmz and d_closure
    d = ind[ind.concept_id.isin(pop_ids) & (ind.fold == "screen") & (ind.year <= 2015)][["concept_id", "year", "d_wmz", "d_closure"]].dropna()
    dm = d.copy()
    for c in ("d_wmz", "d_closure"):
        dm[c] -= dm.groupby("concept_id")[c].transform("mean")
    pre = pd.concat([d[(d.concept_id == r.concept_id) & (d.year >= r.t0 + min(win)) & (d.year <= r.t0 + max(win))] for r in mm.itertuples()]) if len(mm) else d.iloc[:0]
    return dict(n_treated=len(mm), share_T=sT, share_C=sC, diff=sT - sC if np.isfinite(sT) and np.isfinite(sC) else np.nan,
                diff_ci=np.percentile(bd, [2.5, 97.5]).tolist() if len(bd) > 20 else [np.nan, np.nan],
                n_T_concept_years=int(np.isfinite(np.concatenate([np.array(x, float) for x in T])).sum()) if T else 0,
                n_C_concept_years=int(np.isfinite(np.concatenate([np.array(x, float) for x in Cc])).sum()) if Cc else 0,
                within_corr_screen=float(np.corrcoef(dm.d_wmz, dm.d_closure)[0, 1]) if len(dm) > 3 else np.nan,
                n_screen=len(dm),
                corr_treated_pre=float(np.corrcoef(pre.d_wmz, pre.d_closure)[0, 1]) if len(pre) > 3 else np.nan,
                n_treated_pre=len(pre))


# ----------------------------------------------------------------------------- placebo (vendored pattern)
def placebo(lab_c: pd.DataFrame, ind: pd.DataFrame, m: pd.DataFrame, rows: list[str], B: int) -> dict:
    import analysis_event as AE
    rng = np.random.default_rng(11)
    never = sorted(set(lab_c.loc[lab_c.group == "never", "concept_id"]))
    info = lab_c.drop_duplicates("concept_id").set_index("concept_id")
    t0s = m.t0.values
    pseudo = {}
    for c in never:
        same = m[m.concept_id.map(lambda x: info.loc[x, "F_band"]) == info.loc[c, "F_band"]].t0.values
        pseudo[c] = int(rng.choice(same if len(same) else t0s))
    pm = AE.match(lab_c, ind, treated_onsets=pseudo, never_set=set(never), exclude_self=True)
    out = {}
    for col in rows:
        M, _ = AE.es_matrix(pm, ind, col)
        st = es_boot(M, B, 99)["primary"]
        out[col] = dict(S=st["S"], ci=st["ci"], p=st["p"], covers_zero=bool(np.isfinite(st["ci"][0]) and st["ci"][0] <= 0 <= st["ci"][1]))
    return dict(n_pseudo=len(pseudo), match_rate=float((pm.n_controls > 0).mean()), results=out)


# ----------------------------------------------------------------------------- main
def _flat(res: dict) -> list:
    out = []
    for col, st in res["rows"].items():
        out.append(dict(cell=res["cell"], indicator=col, n_onsets=res["n_onsets"], n_matched=res["n_matched"],
                        match_rate=res.get("match_rate"), S=st["primary"]["S"], ci_lo=st["primary"]["ci"][0],
                        ci_hi=st["primary"]["ci"][1], p=st["primary"]["p"], p_one_neg=st["primary"]["p_one_neg"],
                        p_one_pos=st["primary"]["p_one_pos"], se=st["primary"]["se"],
                        S_sens=st["sens"]["S"], ci_sens_lo=st["sens"]["ci"][0], ci_sens_hi=st["sens"]["ci"][1],
                        n_k=st["n_k"]))
    return out


def main(fast: bool = False) -> dict:
    import analysis_event as AE
    import config as C
    import lib_metrics as lm
    from labels3 import guard
    t_start = time.time()
    held = guard()
    B = K.SPEC3["bootstrap"]
    Bn = K.SPEC3["bootstrap_nonprimary"] if not fast else 200
    ind = pd.read_parquet(K.RES / "indicators" / "concept_year_indicators_hydrated.parquet")
    lab = pd.read_parquet(K.RES / "labels" / "labels_screen.parquet")
    C.assert_not_sealed(lab.concept_id)
    assert not (set(ind.concept_id) & held)
    out_dir = K.RES / "event_study"
    out_dir.mkdir(parents=True, exist_ok=True)
    main_ids = set(lab.loc[lab.MAIN.astype(bool), "concept_id"])
    # ---------------- primary cell
    prim = run_cell(lab, ind, "MAIN", "all", "E_up", "all", ROWS, B)
    _, never_p, lab_p = cell_sets(lab, "MAIN", "all", "E_up", "all")
    m = prim["m"]
    # assert identity with the vendored es_stats for the primary window (same bootstrap draws)
    for col in ("closure", "closure_resT", "constraint"):
        Mv, _ = AE.es_matrix(m, ind, col)
        vs = AE.es_stats(Mv, B, seed_for(col, prim["cell"]))
        mine = prim["rows"][col]["primary"]
        assert (np.isnan(vs["S"]) and np.isnan(mine["S"])) or abs(vs["S"] - mine["S"]) < 1e-12, col
        assert np.allclose(vs["ci"], mine["ci"], equal_nan=True), col
    pf_p = [prim["rows"][c]["primary"]["p"] for c in ROWS_PRIMARY]
    holm = lm.holm(pf_p)
    fam = {c: dict(S=prim["rows"][c]["primary"]["S"], ci=prim["rows"][c]["primary"]["ci"], p_two=p, p_holm=h,
                   p_one_screened=prim["rows"][c]["primary"]["p_one_neg"], S_sens=prim["rows"][c]["sens"]["S"],
                   ci_sens=prim["rows"][c]["sens"]["ci"], n_k=prim["rows"][c]["n_k"])
           for c, p, h in zip(ROWS_PRIMARY, pf_p, holm)}
    fam["closure_raw_row0"] = dict(S=prim["rows"]["closure"]["primary"]["S"], ci=prim["rows"]["closure"]["primary"]["ci"],
                                   p_two=prim["rows"]["closure"]["primary"]["p"],
                                   p_one_screened=prim["rows"]["closure"]["primary"]["p_one_neg"])
    na_persist = na_share_by_k(m, ind, "closure_persist")
    bal = balance_ext(m, ind, lab_p)
    primary = dict(cell=prim["cell"], n_onsets=prim["n_onsets"], n_matched=prim["n_matched"], match_rate=prim["match_rate"],
                   widened_share=prim["widened_share"], n_never=prim["n_never"], n_unique_controls=prim["n_unique_controls"],
                   family=fam, holm_family=ROWS_PRIMARY, rows={k: v for k, v in prim["rows"].items()},
                   closure_persist_na=na_persist, balance=bal)
    logger.info(f"PRIMARY {prim['cell']}: onsets {prim['n_onsets']} matched {prim['n_matched']}; " +
                "; ".join(f"{c} S={fam[c]['S']:.3f} [{fam[c]['ci'][0]:.3f},{fam[c]['ci'][1]:.3f}] pHolm={fam[c]['p_holm']:.3f}"
                          for c in ROWS_PRIMARY) + f"; raw closure S={fam['closure_raw_row0']['S']:.3f}")
    pd.DataFrame(prim["contrib"]).to_parquet(out_dir / "contrib_primary.parquet", index=False)
    m.assign(controls=m.controls.map("|".join)).to_parquet(out_dir / "matches_primary.parquet", index=False)
    # ---------------- sensitivities of the primary cell
    sdH = float(ind.loc[(ind.fold == "screen") & (ind.year <= 2015), "H"].std())
    onsets_p, _, _ = cell_sets(lab, "MAIN", "all", "E_up", "all")
    mh = match_H(lab_p, ind, onsets_p, never_p, K.SPEC3["match_H_sensitivity_caliper_sd"] * sdH)
    hres = {}
    for col in ("closure", "closure_resT", "closure_persist", "constraint", "xc_excess"):
        M, _ = AE.es_matrix(mh, ind, col)
        hres[col] = es_boot(M, B, seed_for(col, "Hmatch"))["primary"]
    primary["H_matched"] = dict(caliper=K.SPEC3["match_H_sensitivity_caliper_sd"] * sdH, sd_H=sdH,
                                n_matched=int((mh.n_controls > 0).sum()), rows=hres,
                                balance=[r for r in AE.balance(mh, ind, lab_p) if r["covariate"] in ("H", "log_vol3")])
    mr = AE.match(lab_p, ind, treated_onsets=onsets_p, never_set=never_p, origin=False)
    rel = {}
    for col in ("closure", "closure_resT", "closure_persist", "constraint", "xc_excess"):
        M, _ = AE.es_matrix(mr, ind, col)
        rel[col] = es_boot(M, B, seed_for(col, "bandonly"))["primary"]
    primary["band_only_matching"] = dict(n_matched=int((mr.n_controls > 0).sum()), rows=rel)
    primary["placebo"] = placebo(lab_p, ind, m, ["closure", "closure_resT", "closure_persist", "constraint", "xc_excess",
                                                 "cdeg_diag", "wmz"], B)
    # pooled panels
    pp_rows = ["closure", "closure_resT", "closure_persist", "constraint", "xc_excess", "cdeg_diag", "wmz"]
    primary["pooled_panel"] = AE.pooled_panel(lab_p, ind, pp_rows, B)
    ph = lm.holm([primary["pooled_panel"].get(c, {}).get("p", np.nan) for c in ROWS_PRIMARY])
    for c, a in zip(ROWS_PRIMARY, ph):
        primary["pooled_panel"][c]["p_holm"] = a
    pf = panel_frame(lab_p, ind)
    primary["extended_panel_closure"] = extended_panel(pf, "closure", B, K.SPEC3["seeds"]["panel"])
    primary["partial_logit_closure"] = partial_logit(pf, 1000 if not fast else 100, K.SPEC3["seeds"]["panel"])
    logger.info(f"pooled panel closure_resT {primary['pooled_panel'].get('closure_resT')}; extended {primary['extended_panel_closure'].get('coef')}")
    # R1d
    r1d_res = r1d(m, ind, main_ids, B, 17)
    r1d_res["joint_path"] = {c: dict(diff_k=prim["rows"][c]["diff_k"], ci_k=prim["rows"][c]["ci_k"]) for c in ("wmz", "closure", "d_wmz", "d_closure")}
    K.write_json(K.RES / "r1d.json", r1d_res)
    # R1a correlations
    r1a = r1a_correlations(ind, main_ids, B, 23)
    K.write_json(K.RES / "r1a_correlations.json", r1a)
    K.write_json(out_dir / "primary_family.json", {k: v for k, v in primary.items()})
    logger.info(f"primary cell + sensitivities done ({time.time() - t_start:.0f}s)")
    # ---------------- grid
    flat = _flat(prim)
    grid_meta = []
    cells = [(P, s, lb, r) for P in ("MAIN", "STRICT", "SENS") for s in ("all", "old", "new") for lb in ("E_up", "E_alt", "E")
             for r in ("all", "B_only")]
    for P, s, lb, r in cells:
        if (P, s, lb, r) == ("MAIN", "all", "E_up", "all"):
            continue
        res = run_cell(lab, ind, P, s, lb, r, ROWS_GRID, Bn)
        flat += _flat(res)
        meta = dict(cell=res["cell"], n_onsets=res["n_onsets"], n_matched=res["n_matched"], match_rate=res.get("match_rate"))
        if res.get("m") is not None and res["n_matched"] >= 2 and lb == "E_up":
            _, _, lab_cc = cell_sets(lab, P, s, lb, r)
            meta["balance"] = [b for b in AE.balance(res["m"], ind, lab_cc) if b["covariate"] in ("log_vol3", "H")]
            if s == "all" and r == "all":
                meta["pooled_panel"] = AE.pooled_panel(lab_cc, ind, ["closure", "closure_resT", "closure_persist", "constraint"], 500)
        grid_meta.append(meta)
        if s == "new":
            res2 = run_cell(lab, ind, P, s, lb, r, ROWS_GRID, Bn, new_controls="new_only")
            flat += _flat(res2)
            grid_meta.append(dict(cell=res2["cell"], n_onsets=res2["n_onsets"], n_matched=res2["n_matched"],
                                  match_rate=res2.get("match_rate")))
    grid = pd.DataFrame(flat)
    grid.assign(n_k=grid.n_k.map(lambda x: "|".join(map(str, x)))).to_csv(out_dir / "summary_grid.csv", index=False)
    K.write_json(out_dir / "grid_cells.json", grid_meta)
    logger.info(f"grid done: {len(grid)} rows over {grid.cell.nunique()} cells ({time.time() - t_start:.0f}s)")
    return dict(primary=primary, grid=grid, r1d=r1d_res, r1a=r1a)


if __name__ == "__main__":
    import sys
    K.setup_logging("event3")
    main(fast="--fast" in sys.argv)
