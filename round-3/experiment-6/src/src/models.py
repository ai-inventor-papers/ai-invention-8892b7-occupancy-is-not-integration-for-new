"""Step 8: D1 models on the screen fold.

(a) OLS  Y ~ BASE + openness_z  (Y in Y1r, Y2, log1p Y3); concept-cluster bootstrap (B) + CR1; Holm over the 3 outcomes
(b) grouped-by-concept 5-fold CV x 20 repeats: delta-R2 (FULL - BASE) on pooled OOF rows, concept-bootstrap CI
    (+ fold-internal residualisation variant)
Pre-declared rule -> verdict.json;  (c) within-E_up;  (d) robustness grid;  (e) mediation;  (f) partial dependence;
(g) volume check + VIF;  sanity signals (placebo, label shuffle, leaky feature, B=1000 vs 2000, determinism).
"""
from __future__ import annotations

import json
import math

import numpy as np
import pandas as pd
import statsmodels.api as sm
from loguru import logger
from scipy import stats

import common as K
from common import OUT, WORK

import lib_metrics as lm
import stats_core as S
from openness import R1A

FDIR = OUT / "d1"
OUTCOMES = ["Y1r", "Y2", "log1p_Y3"]
RULE_TEXT = ("D1_SUPPORTED_SCREEN = exists Y in {Y1r, Y2, Y3}: coef(closure_res) < 0 AND bootstrap CI excludes 0 AND "
             "Holm-adjusted p < 0.05 AND grouped-CV delta-R2 CI lower bound > 0 for that same Y. Else "
             "D1_NOT_SUPPORTED_SCREEN. If the sibling RQ1 holds and D1 fails -> 'take-off correlate only'. Sign > 0 with CI "
             "excluding 0 -> 'closure predicts breadth in the OPPOSITE direction' (reported, rule not met).")
SEED = 20260929


def load_panel() -> pd.DataFrame:
    F = pd.read_parquet(FDIR / "features_ct.parquet")
    O = pd.read_parquet(FDIR / "outcomes_ct.parquet")
    d = F.merge(O, on=["concept_id", "t"], how="inner")
    assert len(d) == len(F)
    med = float(d.beta_sim_rar.median())
    d["beta_sim_missing"] = d.beta_sim_rar.isna().astype(float)
    d["beta_sim_rar_f"] = d.beta_sim_rar.fillna(med)
    lab = pd.read_parquet(OUT / "indicators" / "labels_screen.parquet").drop_duplicates("concept_id")
    d = d.merge(lab[["concept_id", "onset", "group"]].rename(columns={"onset": "E_up_onset", "group": "E_up_group"}),
                on="concept_id", how="left")
    d["E_up"] = d.E_up_onset.notna()
    d["routeA"] = (d.route == "A_openalex_native").astype(float)
    return d


def pop_mask(d: pd.DataFrame, pop: str) -> np.ndarray:
    return {"MAIN": d.in_MAIN, "STRICT": d.in_STRICT, "SENSITIVITY": d.in_SENSITIVITY}[pop].values.astype(bool)


def model_rows(d: pd.DataFrame, y: str, lead: list[str], num: list[str]) -> pd.DataFrame:
    cols = [y] + lead + num
    ok = np.isfinite(d[cols].astype(float).values).all(1)
    return d[ok].reset_index(drop=True)


def fit_one(d: pd.DataFrame, y: str, open_var: str, num: list[str] = S.NUM_BASE, B: int = 2000, seed: int = SEED,
            extra_lead: list[str] | None = None, cats: list[str] = S.CATS) -> dict:
    lead = [open_var] + (extra_lead or [])
    m = model_rows(d, y, lead, num)
    if m.concept_id.nunique() < 10:
        return dict(n_rows=len(m), n_concepts=int(m.concept_id.nunique()), coef=math.nan, note="too few concepts")
    X, names, _ = S.design(m, lead, num, cats)
    yy = m[y].astype(float).values
    g = m.concept_id.values
    beta, se = S.cr1(X, yy, g)
    draws = S.cluster_boot(X, yy, g, B, seed, 1)
    out = S.boot_summary(beta[1], draws)
    G = m.concept_id.nunique()
    out.update(se_cr1=float(se[1]), p_cr1=S.t_p_two_sided(beta[1], se[1], G - 1), n_rows=len(m), n_concepts=int(G),
               n_params=X.shape[1], sd_y=float(yy.std(ddof=1)), coef_in_sd_y=float(beta[1] / yy.std(ddof=1)))
    if extra_lead:
        for k, nm in enumerate(extra_lead, start=2):
            out[f"coef_{nm}"] = float(beta[k])
            out[f"se_cr1_{nm}"] = float(se[k])
    return out


def cv_one(d: pd.DataFrame, y: str, open_var: str, num: list[str] = S.NUM_BASE, B: int = 2000, reps: int = 20,
           foldwise: bool = False, seed: int = SEED + 7, extra_full: list[str] | None = None) -> dict:
    lead = [open_var] + (extra_full or [])
    m = model_rows(d, y, lead, num)
    Xf, names, _ = S.design(m, lead, num)
    Xb = np.delete(Xf, list(range(1, 1 + len(lead))), axis=1)
    yy = m[y].astype(float).values
    g = m.concept_id.values
    xf_fn = None
    if foldwise:
        fitrows = pd.read_parquet(WORK / "indicators_open.parquet")
        fitrows = fitrows[(fitrows.fold == "screen") & fitrows.age.between(3, 8) & (fitrows.year <= 2015)]
        regs = R1A + ["H_W1"]
        FX = np.column_stack([np.ones(len(fitrows))] + [fitrows[c].astype(float).values for c in regs])
        Fy = fitrows.closure.astype(float).values
        fok = np.isfinite(FX).all(1) & np.isfinite(Fy)
        FX, Fy, Fc = FX[fok], Fy[fok], fitrows.concept_id.values[fok]
        MX = np.column_stack([np.ones(len(m))] + [m[c].astype(float).values for c in regs])
        My = m.closure.astype(float).values

        def xf_fn(tr: np.ndarray) -> np.ndarray:
            trc = set(g[tr])
            sel = np.isin(Fc, list(trc))
            b = S.ols(FX[sel], Fy[sel])
            X2 = Xf.copy()
            X2[:, 1] = My - MX @ b
            return X2
    pb, pf = S.grouped_cv(Xb, Xf, yy, g, reps=reps, xf_fn=xf_fn)
    out = S.delta_r2_boot(yy, pb, pf, g, B, seed)
    out.update(n_rows=len(m), n_concepts=int(m.concept_id.nunique()), foldwise=foldwise)
    return out, m.assign(oof_base=pb, oof_full=pf)


# ----------------------------------------------------------------------------------------------------------------
def primary(d: pd.DataFrame, B: int) -> tuple[pd.DataFrame, pd.DataFrame, dict, dict]:
    dm = d[pop_mask(d, "MAIN")]
    coef_rows, cv_rows, oof = [], [], {}
    for ov in ["closure_res_z", "closure_res_imp_z", "constraint_z", "esize_norm_z", "xcomm_exc_z"]:
        for y in OUTCOMES:
            r = fit_one(dm, y, ov, B=B)
            coef_rows.append(dict(model="a_primary_OLS", population="MAIN", openness=ov, outcome=y, **r))
            c, m = cv_one(dm, y, ov, B=B)
            cv_rows.append(dict(model="b_grouped_cv", population="MAIN", openness=ov, outcome=y, **c))
            if ov in ("closure_res_z", "closure_res_imp_z"):
                oof[(ov, y)] = m
                if ov == "closure_res_z":
                    cfw, _ = cv_one(dm, y, ov, B=B, foldwise=True)
                    cv_rows.append(dict(model="b_grouped_cv_foldwise_R1a", population="MAIN", openness=ov, outcome=y, **cfw))
            logger.info(f"{ov:>18} {y:>9}: coef {r['coef']:+.4f} [{r['ci_lo']:+.4f}, {r['ci_hi']:+.4f}] p_boot {r['p_boot']:.4f} "
                        f"n={r['n_rows']}/{r['n_concepts']} | dR2 {c['delta_r2']:+.4f} [{c['ci_lo']:+.4f}, {c['ci_hi']:+.4f}]")
    coef = pd.DataFrame(coef_rows)
    cv = pd.DataFrame(cv_rows)
    # multiplicity: Holm over the 3 outcomes within each co-primary measure; BH over the secondary measures
    coef["p_holm"] = np.nan
    coef["q_bh_secondary"] = np.nan
    for ov in ["closure_res_z", "closure_res_imp_z"]:
        mk = coef.openness == ov
        coef.loc[mk, "p_holm"] = lm.holm(coef.loc[mk, "p_boot"].tolist())
    mk = coef.openness.isin(["constraint_z", "esize_norm_z"])
    coef.loc[mk, "q_bh_secondary"] = lm.bh(coef.loc[mk, "p_boot"].tolist())
    return coef, cv, oof, {}


def evaluate_rule(coef: pd.DataFrame, cv: pd.DataFrame, ov: str) -> dict:
    per = {}
    for y in OUTCOMES:
        a = coef[(coef.openness == ov) & (coef.outcome == y) & (coef.model == "a_primary_OLS")].iloc[0]
        b = cv[(cv.openness == ov) & (cv.outcome == y) & (cv.model == "b_grouped_cv")].iloc[0]
        cond = dict(coef_negative=bool(a.coef < 0), ci_excludes_0=bool(a.ci_hi < 0 or a.ci_lo > 0),
                    holm_p_lt_005=bool(a.p_holm < 0.05), cv_delta_r2_ci_lo_gt_0=bool(b.ci_lo > 0))
        per[y] = dict(conditions=cond, met=all(cond.values()),
                      opposite_direction=bool(a.coef > 0 and a.ci_lo > 0),
                      coef=float(a.coef), ci=[float(a.ci_lo), float(a.ci_hi)], p_boot=float(a.p_boot),
                      p_holm=float(a.p_holm), delta_r2=float(b.delta_r2), delta_r2_ci=[float(b.ci_lo), float(b.ci_hi)])
    return per


def within_eup(d: pd.DataFrame, B: int) -> dict:
    dm = d[pop_mask(d, "MAIN") & d.E_up.values]
    dm = dm[(dm.t >= dm.E_up_onset - 3) & (dm.t <= dm.E_up_onset) & (dm.E_up_onset <= 2015)]
    res = dict(n_concepts=int(dm.concept_id.nunique()), n_rows=len(dm),
               rule="concepts with E_up onset <= 2015; rows t in [onset-3, onset], age 3..8, MAIN")
    res["underpowered"] = bool(res["n_concepts"] < 30)
    rows = []
    for ov in ["closure_res_z", "closure_res_imp_z", "constraint_z"]:
        for y in OUTCOMES:
            r = fit_one(dm, y, ov, B=B)
            try:
                c, _ = cv_one(dm, y, ov, B=B)
            except (np.linalg.LinAlgError, ValueError) as e:
                logger.warning(f"E_up CV failed {ov} {y}: {e}")
                c = {}
            rows.append(dict(openness=ov, outcome=y, **r, **{f"cv_{k}": v for k, v in c.items()}))
    res["estimates"] = rows
    res["label"] = "UNDERPOWERED - descriptive only" if res["underpowered"] else "secondary analysis"
    return res


def robustness(d: pd.DataFrame, B: int) -> pd.DataFrame:
    specs = []
    for ov in ["closure_res_z", "closure_res_imp_z", "constraint_z"]:
        for y in OUTCOMES:
            specs += [
                dict(spec="MAIN (primary)", pop="MAIN", ov=ov, y=y),
                dict(spec="STRICT", pop="STRICT", ov=ov, y=y),
                dict(spec="SENSITIVITY (all main arm)", pop="SENSITIVITY", ov=ov, y=y),
                dict(spec="route A only", pop="MAIN", ov=ov, y=y, filt=lambda x: x.route == "A_openalex_native"),
                dict(spec="route B only", pop="MAIN", ov=ov, y=y, filt=lambda x: x.route == "B_s2_index"),
                dict(spec="route interaction", pop="MAIN", ov=ov, y=y, inter="routeA"),
                dict(spec="iteration-1 concepts (hydration_batch iter1)", pop="MAIN", ov=ov, y=y, filt=lambda x: x.hydration_batch == "iter1"),
                dict(spec="newly hydrated concepts (iter2)", pop="MAIN", ov=ov, y=y, filt=lambda x: x.hydration_batch == "iter2"),
                dict(spec="one row per concept (first eligible t)", pop="MAIN", ov=ov, y=y, first=True),
                dict(spec="turnover-augmented baseline", pop="MAIN", ov=ov, y=y, num=S.NUM_BASE + S.TURNOVER),
                dict(spec="+ origin-subfield proximity", pop="MAIN", ov=ov, y=y, num=S.NUM_BASE + ["origin_prox_f", "prox_missing"]),
                dict(spec="drop sense_check_fail", pop="MAIN", ov=ov, y=y, filt=lambda x: ~x.sense_check_fail.astype(bool)),
            ]
        for y2 in ["Y1", "Y1r20", "log1p_Y3b"]:
            specs.append(dict(spec=f"alt outcome {y2}", pop="MAIN", ov=ov, y=y2))
    for y in OUTCOMES:
        specs += [dict(spec="closure_unres (no residualisation)", pop="MAIN", ov="closure_unres_z", y=y),
                  dict(spec="closure_res_H3 (3-yr H in R1a)", pop="MAIN", ov="closure_res_H3_z", y=y),
                  dict(spec="W1-mean closure_res over [t-2, t]", pop="MAIN", ov="closure_res_w1mean_z", y=y),
                  dict(spec="xcomm_exc (cross-community pairs)", pop="MAIN", ov="xcomm_exc_z", y=y)]
    d = d.copy()
    d["log1p_Y3b"] = np.log1p(d.Y3b)
    if "Y1r20" not in d.columns:
        d["Y1r20"] = d.filter(regex=r"^Y1r\d+$").iloc[:, 0]
    rows = []
    for k, s in enumerate(specs):
        x = d[pop_mask(d, s["pop"])]
        if "filt" in s:
            x = x[s["filt"](x).values]
        if s.get("first"):
            x = model_rows(x, s["y"], [s["ov"]], s.get("num", S.NUM_BASE)).sort_values("t").drop_duplicates("concept_id")
        extra = None
        if s.get("inter"):
            x = x.assign(open_x_routeA=x[s["ov"]] * x[s["inter"]])
            extra = ["open_x_routeA"]
        cats = [c for c in S.CATS if not (s.get("first") and c == "t")] if s.get("first") else S.CATS
        r = fit_one(x, s["y"], s["ov"], num=s.get("num", S.NUM_BASE), B=B, seed=SEED + k, extra_lead=extra, cats=cats)
        rows.append(dict(spec=s["spec"], population=s["pop"], openness=s["ov"], outcome=s["y"], estimator="OLS", **r))
    # PPML for Y3 (Poisson QMLE, cluster-robust)
    for ov in ["closure_res_z", "closure_res_imp_z", "constraint_z"]:
        x = model_rows(d[pop_mask(d, "MAIN")], "Y3", [ov], S.NUM_BASE)
        X, names, _ = S.design(x, [ov])
        try:
            res = sm.GLM(x.Y3.astype(float).values, X, family=sm.families.Poisson()).fit(
                cov_type="cluster", cov_kwds={"groups": pd.factorize(x.concept_id)[0]})
            b, se = float(res.params[1]), float(res.bse[1])
            rows.append(dict(spec="PPML Y3 (Poisson QMLE, CR)", population="MAIN", openness=ov, outcome="Y3", estimator="PPML",
                             coef=b, ci_lo=b - 1.96 * se, ci_hi=b + 1.96 * se, se_cr1=se, p_cr1=float(res.pvalues[1]),
                             n_rows=len(x), n_concepts=int(x.concept_id.nunique())))
        except (np.linalg.LinAlgError, ValueError) as e:
            logger.warning(f"PPML failed for {ov}: {e}")
    return pd.DataFrame(rows)


def mediation(d: pd.DataFrame, B: int, ov: str = "closure_res_z") -> dict:
    dm = d[pop_mask(d, "MAIN")]
    out = dict(note="M_W2 (mean excess cross-community pair share over t+1..t+5) is post-t: the decomposition is "
                    "descriptive, not causal.", openness=ov, per_outcome={})
    for y in OUTCOMES:
        m = model_rows(dm, y, [ov, "M_W2"], S.NUM_BASE)
        Xc, _, _ = S.design(m, [ov])
        Xb, _, _ = S.design(m, [ov, "M_W2"])
        yy, mm, g = m[y].astype(float).values, m.M_W2.astype(float).values, m.concept_id.values

        def est(idx):
            a = S.ols(Xc[idx], mm[idx])[1]
            bb = S.ols(Xb[idx], yy[idx])
            c = S.ols(Xc[idx], yy[idx])[1]
            return np.array([a, bb[2], a * bb[2], c, bb[1], (a * bb[2] / c) if c != 0 else np.nan])
        full = est(np.arange(len(m)))
        blocks = S.blocks_of(g)
        rng = np.random.default_rng(SEED + 99)
        draws = np.array([est(np.concatenate([blocks[k] for k in rng.integers(0, len(blocks), len(blocks))])) for _ in range(B)])
        names = ["a_path", "b_path", "indirect_ab", "total_c", "direct_c_prime", "proportion_mediated"]
        out["per_outcome"][y] = dict(n_rows=len(m), n_concepts=int(m.concept_id.nunique()),
                                     **{n: dict(est=float(full[i]), ci=[float(np.nanpercentile(draws[:, i], 2.5)),
                                                                        float(np.nanpercentile(draws[:, i], 97.5))])
                                        for i, n in enumerate(names)})
    return out


def partial_dependence(d: pd.DataFrame, B: int, ov: str = "closure_res") -> pd.DataFrame:
    dm = d[pop_mask(d, "MAIN")]
    rows = []
    for y in OUTCOMES:
        m = model_rows(dm, y, [ov], S.NUM_BASE)
        Xb, _, _ = S.design(m, [], S.NUM_BASE)
        yr = m[y].values - Xb @ S.ols(Xb, m[y].values.astype(float))
        xr = m[ov].values - Xb @ S.ols(Xb, m[ov].values.astype(float))
        dec = pd.qcut(xr, 10, labels=False, duplicates="drop")
        g = m.concept_id.values
        blocks = S.blocks_of(g)
        rng = np.random.default_rng(SEED + 5)
        bs = []
        for _ in range(min(B, 1000)):
            idx = np.concatenate([blocks[k] for k in rng.integers(0, len(blocks), len(blocks))])
            bs.append(pd.Series(yr[idx]).groupby(dec[idx]).mean().reindex(range(10)).values)
        bs = np.array(bs)
        for k in range(int(np.nanmax(dec)) + 1):
            sel = dec == k
            rows.append(dict(outcome=y, decile=k + 1, x_resid_mean=float(xr[sel].mean()), y_resid_mean=float(yr[sel].mean()),
                             ci_lo=float(np.nanpercentile(bs[:, k], 2.5)), ci_hi=float(np.nanpercentile(bs[:, k], 97.5)),
                             n=int(sel.sum())))
    return pd.DataFrame(rows)


def volume_check(d: pd.DataFrame) -> tuple[dict, pd.DataFrame]:
    dm = d[pop_mask(d, "MAIN")]
    out = {}
    for ov in ["closure_res", "closure_res_imp", "constraint", "esize_norm"]:
        for c in ["log_vol_W1", "momentum", "H_W1", "n_active_W1"]:
            x = dm[[ov, c]].dropna()
            out[f"spearman_{ov}_vs_{c}"] = float(stats.spearmanr(x[ov], x[c])[0])
    m = model_rows(dm, "Y1r", ["closure_res_z"], S.NUM_BASE)
    cols = ["closure_res_z"] + S.NUM_BASE
    Z = m[cols].astype(float).values
    vif = []
    for i, c in enumerate(cols):
        others = np.column_stack([np.ones(len(Z)), np.delete(Z, i, axis=1)])
        if np.ptp(Z[:, i]) == 0:
            vif.append(dict(variable=c, vif=math.nan, note="constant on these rows (dropped from the design)"))
            continue
        r2 = S.r2(Z[:, i], others @ S.ols(others, Z[:, i]))
        vif.append(dict(variable=c, vif=float(1 / (1 - r2)) if r2 < 1 else math.inf, note=""))
    return out, pd.DataFrame(vif)


def sanity(d: pd.DataFrame, coef: pd.DataFrame, B: int) -> dict:
    dm = d[pop_mask(d, "MAIN")]
    out = {}
    rng = np.random.default_rng(SEED + 11)
    for y in OUTCOMES:
        m = model_rows(dm, y, ["closure_res_z"], S.NUM_BASE)
        X, _, _ = S.design(m, ["closure_res_z"])
        yy = m[y].astype(float).values
        obs = S.ols(X, yy)[1]
        # placebo: closure_res permuted within calendar year across concepts
        perm_coefs = []
        tt = m.t.values
        for _ in range(200):
            Xp = X.copy()
            col = Xp[:, 1].copy()
            for yr in np.unique(tt):
                ix = np.where(tt == yr)[0]
                col[ix] = col[rng.permutation(ix)]
            Xp[:, 1] = col
            perm_coefs.append(S.ols(Xp, yy)[1])
        perm_coefs = np.array(perm_coefs)
        # label shuffle (concept-level) -> CV delta-R2 should be ~0
        g = m.concept_id.values
        dshuf = []
        for s in range(10):
            yp = yy[np.random.default_rng(1000 + s).permutation(len(yy))]
            Xb = np.delete(X, 1, axis=1)
            pb, pf = S.grouped_cv(Xb, X, yp, g, reps=5)
            dshuf.append(S.r2(yp, pf) - S.r2(yp, pb))
        # leaky features (post-t): W2 volume, and the W2 level of the breadth measure itself -> R2 must rise
        Xb = np.delete(X, 1, axis=1)
        pb, pf = S.grouped_cv(Xb, X, yy, g, reps=5)
        pbl, pfl = S.grouped_cv(Xb, np.column_stack([X, m.log_vol_W2.values]), yy, g, reps=5)
        lv = {"Y1r": "H_W2", "Y2": "RS_W2", "log1p_Y3": "n_newcomer_W2"}[y]
        lvx = m[lv].astype(float).fillna(m[lv].median()).values
        if y == "log1p_Y3":
            lvx = np.log1p(lvx)
        pbl2, pfl2 = S.grouped_cv(Xb, np.column_stack([X, lvx]), yy, g, reps=5)
        # bootstrap stability 1000 vs 2000
        b1 = S.cluster_boot(X, yy, g, 1000, SEED, 1)
        b2 = S.cluster_boot(X, yy, g, 2000, SEED, 1)
        w1, w2 = np.subtract(*np.percentile(b1, [97.5, 2.5])), np.subtract(*np.percentile(b2, [97.5, 2.5]))
        # determinism: identical refit
        again = fit_one(dm, y, "closure_res_z", B=B)
        prim = coef[(coef.openness == "closure_res_z") & (coef.outcome == y) & (coef.model == "a_primary_OLS")].iloc[0]
        out[y] = dict(placebo_mean=float(perm_coefs.mean()), placebo_sd=float(perm_coefs.std(ddof=1)),
                      observed=float(obs), observed_percentile_in_placebo=float(np.mean(perm_coefs <= obs) * 100),
                      label_shuffle_delta_r2_mean=float(np.mean(dshuf)), label_shuffle_delta_r2_max=float(np.max(dshuf)),
                      leaky_r2_base=S.r2(yy, pb), leaky_r2_full=S.r2(yy, pf), leaky_r2_with_W2_volume=S.r2(yy, pfl), leaky_breadth_feature=lv,
                      leaky_r2_with_W2_breadth_level=S.r2(yy, pfl2),
                      leaky_detected=bool(max(S.r2(yy, pfl), S.r2(yy, pfl2)) > S.r2(yy, pf) + 0.05),
                      boot_ci_width_1000=float(w1), boot_ci_width_2000=float(w2),
                      boot_ci_width_rel_change=float(abs(w2 - w1) / w2),
                      deterministic=bool(again["coef"] == prim.coef and again["ci_lo"] == prim.ci_lo and again["ci_hi"] == prim.ci_hi))
    return out


def run(boot: int = 2000, mini: bool = False) -> None:
    FDIR.mkdir(parents=True, exist_ok=True)
    B = 200 if mini else boot
    Bg = 200 if mini else 1000
    d = load_panel()
    d.to_parquet(FDIR / "panel_ct.parquet", index=False)
    dec = json.loads((FDIR / "rowcount_decision.json").read_text())
    coef, cv, oof, _ = primary(d, B)
    verdict = dict(rule_text_verbatim=RULE_TEXT, row_count_decision=dec)
    per = {ov: evaluate_rule(coef, cv, ov) for ov in ["closure_res_z", "closure_res_imp_z"]}
    verdict["per_measure"] = per
    met_primary = [y for y, v in per["closure_res_z"].items() if v["met"]]
    met_imp = [y for y, v in per["closure_res_imp_z"].items() if v["met"]]
    if dec.get("F3_triggered"):
        met = [y for y in met_primary if y in met_imp]
        verdict["co_primary_note"] = dec.get("coprimary_rule")
    else:
        met = met_primary
    verdict["outcomes_meeting_rule"] = met
    verdict["verdict"] = "D1_SUPPORTED_SCREEN" if met else "D1_NOT_SUPPORTED_SCREEN"
    opp = [y for y, v in per["closure_res_z"].items() if v["opposite_direction"]]
    verdict["opposite_direction_outcomes"] = opp
    verdict["interpretation"] = ("closure (low openness) predicts breadth gain in the pre-declared direction on the screen"
                                 if met else ("closure predicts breadth in the OPPOSITE direction (rule not met)" if opp else
                                              "no screen support: openness is a take-off correlate only (if RQ1 holds)"))
    logger.info(f"VERDICT: {verdict['verdict']} (met: {met}; opposite: {opp})")
    coef.to_csv(FDIR / "coef_table_primary.csv", index=False)
    cv.to_csv(FDIR / "cv_delta_r2.csv", index=False)
    K.write_json(FDIR / "verdict.json", verdict)
    oof_df = oof[("closure_res_z", "Y1r")][["concept_id", "t", "Y1r", "oof_base", "oof_full"]]
    oof_df.to_parquet(FDIR / "oof_Y1r_closure_res.parquet", index=False)
    for (ov, y), m in oof.items():
        m[["concept_id", "t", y, "oof_base", "oof_full"]].to_parquet(FDIR / f"oof_{y}_{ov}.parquet", index=False)

    eup = within_eup(d, B)
    K.write_json(FDIR / "within_E_up.json", eup)
    logger.info(f"E_up subset: {eup['n_concepts']} concepts / {eup['n_rows']} rows ({eup['label']})")
    rob = robustness(d, Bg)
    rob.to_csv(FDIR / "robustness.csv", index=False)
    logger.info(f"robustness grid: {len(rob)} rows")
    med = {ov: mediation(d, B, ov) for ov in ["closure_res_z", "closure_res_imp_z"]}
    K.write_json(FDIR / "mediation.json", med)
    pdp = partial_dependence(d, B)
    pdp.to_csv(FDIR / "partial_dependence.csv", index=False)
    vc, vif = volume_check(d)
    vif.to_csv(FDIR / "vif.csv", index=False)
    K.write_json(FDIR / "volume_check.json", vc)
    san = sanity(d, coef, B)
    K.write_json(FDIR / "sanity_checks.json", san)
    # combined coefficient table (every model x outcome x openness x population)
    eup_rows = pd.DataFrame(eup["estimates"]).assign(model="c_within_E_up", population="MAIN")
    all_coef = pd.concat([coef, eup_rows[[c for c in eup_rows.columns if not c.startswith("cv_")]],
                          rob.rename(columns={"spec": "model"})], ignore_index=True)
    all_coef.to_csv(FDIR / "coef_table.csv", index=False)
    logger.info("models done")
