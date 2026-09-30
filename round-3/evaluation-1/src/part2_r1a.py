#!/usr/bin/env python3
"""PART 2: R1a turnover check on the two ALREADY-SEEN populations (main exp_3, MeSH exp_4).

Is 'lower Chung-Lu closure before sustained uptake (E_up)' reducible to neighbourhood turnover (new-relation rate,
neighbourhood novelty, Baselga beta_sim) plus volume/age? Steps 2.1-2.6 of the artifact plan:
  2.1 within-concept (demeaned) correlations with concept-cluster bootstrap CIs
  2.2 label-blind OLS residualisation of closure (concept-clustered SEs, partial R^2 of the turnover block)
  2.3 reproduction gate: S_raw re-run with the ORIGINAL estimator code and matched sets
  2.4 event study on residualised closure with ONE shared set of bootstrap indices (paired retained fraction)
  2.5 fixed-effect IVW pooling across populations, Cochran Q, I^2 (Q-profile CI)
  2.6 positive / negative / placebo pipeline controls
The spec (with thresholds) is written and hashed to results/r1a/r1a_spec.json BEFORE any statistic is computed.
"""
from __future__ import annotations

import hashlib
import json
import math

import numpy as np
import pandas as pd
from loguru import logger

import common as K

HEADER = K.HEADER
MAIN_B, MESH_B = 1000, 2000  # each population keeps its ORIGINAL estimator's bootstrap size
SPEC = {
    "header": HEADER,
    "question": "Is lower Chung-Lu closure before E_up onset reducible to neighbourhood turnover + volume + age?",
    "units": {
        "main": "exp_3 concept_year_indicators.parquet; fold in {screen, reference}; age >= 0; 2005 <= year <= 2019; "
                "closure finite (reference rows have age = NaN in the file and therefore drop out)",
        "mesh": "exp_4 features.parquet; age >= 0; 2005 <= year <= 2019; aligned 'closure' finite"},
    "variables": {
        "main": {"closure": "closure", "new_rel": "new_relation_rate", "novelty": "novelty", "beta_sim": "beta_sim_raw",
                 "beta_sim_rar": "beta_sim_rar", "entropy": "H"},
        "mesh": {"closure": "closure", "new_rel": "new_rel_rate", "novelty": "nbr_novelty", "beta_sim": "beta_sim_raw",
                 "beta_sim_rar": "beta_sim_rar", "entropy": "subfield_entropy (BIASED; sensitivity only)",
                 "beta_sim_native": "beta_sim (plan-native MeSH Baselga; sensitivity)"}},
    "deviation_D1": "The plan lists MeSH 'beta_sim' as aligned. In features.parquet the column computed with the vendored "
                    "main-pool code is 'beta_sim_raw' (Spearman/Pearson with plan-native 'beta_sim' only r = 0.16). "
                    "SPEC P therefore uses beta_sim_raw in BOTH populations (like-for-like); plan-literal 'beta_sim' is "
                    "run as sensitivity SPEC B_native. Declared before any statistic was computed.",
    "step_2_1": {"pairs": ["new_rel", "novelty", "beta_sim", "beta_sim_rar"], "context_pairs": ["closure_raw", "log_vol3"],
                 "demean": "within concept, rows with both finite; concepts with >= 3 valid years",
                 "ci": "concept-cluster bootstrap, B = 2000, percentile, seed 0"},
    "step_2_2": {
        "fit": {"main": "OLS on fold=='screen' unit rows with complete covariates, applied to all rows with complete covariates",
                "mesh": "OLS on all unit rows with complete covariates (label-blind), applied to all rows"},
        "se": "concept-clustered (statsmodels cov_type='cluster')",
        "specs": {
            "P": "closure ~ 1 + new_rel + novelty + beta_sim(raw) + log1p(vol) + log1p(vol3) + age [+ H in main]  (PRIMARY)",
            "R": "as P with beta_sim_rar replacing beta_sim(raw) (complete-case)",
            "V": "closure ~ 1 + log1p(vol) + log1p(vol3) + age [+ H in main]  (reduced model of P: volume-only baseline)",
            "D_new_rel / D_novelty / D_beta_sim": "closure ~ 1 + <one turnover variable> + log1p(vol) + log1p(vol3) + age (diagnostic)",
            "H_mesh": "MeSH only: P + subfield_entropy ('biased covariate')",
            "B_native": "MeSH only: P with plan-native beta_sim replacing beta_sim_raw",
            "POS": "closure ~ 1 + closure_raw + log1p(vol) + log1p(vol3) + age  (plan positive control)",
            "POS_ORACLE": "closure ~ 1 + (closure + N(0, (0.1 sd)^2) noise, seed 0) + log1p(vol) + log1p(vol3) + age  "
                          "(strict pipeline positive control: must erase the effect)",
            "NEG": "closure ~ 1 + N(0,1) noise (seed 0) + log1p(vol) + log1p(vol3) + age  (negative control)",
            "V0": "closure ~ 1 + log1p(vol) + log1p(vol3) + age  (reference for NEG: noise must retain ~100% of V0)"},
        "missing": "event-study cells whose covariates are missing get NaN (never imputed); the treated-unit loss is reported "
                   "and S_raw is recomputed on the SAME finite cells (S_raw_cc) as the retained-fraction denominator"},
    "step_2_3_gate": {
        "main": "analysis_event.es_matrix/es_stats (exp_3), matches_E_up.csv, B = 1000, seed = lib_metrics.stable_seed('closure') % 2**31",
        "mesh": "analysis.mainpool_es (exp_4), E_up matches from analysis_summary.json mainpool_block, B = 2000, fresh default_rng(42)",
        "pass": "|S diff| < 1e-6 AND both CI endpoints within 0.02 of the recorded CI"},
    "step_2_4": {"window": "es_rel_years -5..0, summary window [-3, 0]", "bootstrap": "resample treated units; ONE shared "
                 "index set for raw and residualised (paired); main B = 1000 (seed as gate), MeSH B = 2000 (seed 42)",
                 "retained": "S_res / S_raw_cc; paired-bootstrap percentile CI; replicates with |S_raw_cc_b| < 0.05 |S_raw_cc| dropped",
                 "mde": "2.8 x bootstrap SE; in SD units of the unit-level pooled SD of the outcome column"},
    "step_2_5": "fixed-effect IVW (w = 1/SE^2) of S_res across the two populations; Cochran Q (df = 1), p_Q, I^2 with Q-profile "
                "CI; same for S_raw (must reproduce side-by-side IVW -0.410, SE 0.125, Q 6.16). Q is underpowered at k = 2.",
    "verdict_rule": {
        "NOT REDUCIBLE TO TURNOVER (seen data)": "S_res 95% CI excludes 0 AND retained lower CI >= 0.5",
        "LARGELY TURNOVER": "S_res 95% CI covers 0 AND retained point estimate < 0.3",
        "AMBIGUOUS / UNDERPOWERED": "otherwise",
        "applies_to": "SPEC P per population; pooled verdict on S_ivw_res with the same rule (retained = S_ivw_res / S_ivw_raw_cc; "
                      "retained CI for the pooled verdict from the IVW of paired bootstrap replicates)"},
    "control_pass_rules": {"POS": "informative only: retained expected to shrink in proportion to the within-concept "
                                  "correlation of closure with closure_raw",
                           "POS_ORACLE": "retained point |.| < 0.2 in each population",
                           "NEG": "S_NEG / S_V0 within [0.9, 1.1] in each population",
                           "PLACEBO": "main only (exp_3 pseudo-onset design re-generated with rng 11): S_res CI covers 0"},
    "bad_control_caveat": "turnover may be part of the brokerage MECHANISM rather than a confounder; partialling it out then "
                          "understates brokerage, so S_res is a conservative lower bound; S_fit = S_raw_cc - S_res and the "
                          "single-covariate decompositions show which covariate carries the shared part.",
}


# ------------------------------------------------------------------ data
def load_main() -> pd.DataFrame:
    d = pd.read_parquet(K.E3 / "results/indicators/concept_year_indicators.parquet")
    d["lv"], d["lv3"] = np.log1p(d.vol), np.log1p(d.vol3)
    d["unit"] = d.fold.isin(["screen", "reference"]) & (d.age >= 0) & d.year.between(2005, 2019) & np.isfinite(d.closure)
    d["fitmask"] = d.unit & (d.fold == "screen")
    return d


def load_mesh() -> pd.DataFrame:
    d = pd.read_parquet(K.E4 / "results/features.parquet")
    d["lv"], d["lv3"] = np.log1p(d.vol), np.log1p(d.vol3)
    d["unit"] = (d.age >= 0) & d.year.between(2005, 2019) & np.isfinite(d.closure)
    d["fitmask"] = d.unit
    return d


# ------------------------------------------------------------------ 2.1 within-concept correlations
def within_corr(d: pd.DataFrame, x: str, y: str, B: int = 2000, seed: int = 0) -> dict:
    from scipy.stats import rankdata
    dd = d.loc[d.unit & np.isfinite(d[x]) & np.isfinite(d[y]), ["concept_id", x, y]].copy()
    cnt = dd.groupby("concept_id")[x].transform("size")
    dd = dd[cnt >= 3]
    if dd.concept_id.nunique() < 5:
        return dict(n_concepts=int(dd.concept_id.nunique()), n_rows=len(dd))
    dd["xd"] = dd[x] - dd.groupby("concept_id")[x].transform("mean")
    dd["yd"] = dd[y] - dd.groupby("concept_id")[y].transform("mean")
    codes, uc = pd.factorize(dd.concept_id)
    xd, yd, xr, yr = dd.xd.values, dd.yd.values, dd[x].values, dd[y].values
    rows_by = [np.where(codes == i)[0] for i in range(len(uc))]

    def pear(a, b):
        a, b = a - a.mean(), b - b.mean()
        den = math.sqrt((a * a).sum() * (b * b).sum())
        return float((a * b).sum() / den) if den > 0 else np.nan

    def spear(a, b):
        return pear(rankdata(a), rankdata(b))

    pt = dict(r_within=pear(xd, yd), rho_within=spear(xd, yd), r_pooled=pear(xr, yr), rho_pooled=spear(xr, yr))
    rng = np.random.default_rng(seed)
    bs = {k: np.empty(B) for k in pt}
    for b in range(B):
        ii = np.concatenate([rows_by[i] for i in rng.integers(0, len(uc), len(uc))])
        # re-demean inside the replicate is unnecessary: each resampled concept keeps its own zero mean
        bs["r_within"][b] = pear(xd[ii], yd[ii])
        bs["rho_within"][b] = spear(xd[ii], yd[ii])
        bs["r_pooled"][b] = pear(xr[ii], yr[ii])
        bs["rho_pooled"][b] = spear(xr[ii], yr[ii])
    out = dict(x=x, y=y, n_concepts=len(uc), n_rows=len(dd))
    for k, v in pt.items():
        lo, hi = np.nanpercentile(bs[k], [2.5, 97.5])
        out[k], out[k + "_ci"] = v, [float(lo), float(hi)]
    return out


# ------------------------------------------------------------------ 2.2 residualisation
def fit_resid(d: pd.DataFrame, covs: list[str], turnover: list[str], name: str, outcome: str = "closure") -> tuple[pd.Series, dict]:
    import statsmodels.api as sm
    X = d[covs].astype(float)
    ok_cov = np.isfinite(X).all(axis=1) & np.isfinite(d[outcome])
    fit_rows = ok_cov & d.fitmask
    Xf = sm.add_constant(X[fit_rows], has_constant="add")
    yf = d.loc[fit_rows, outcome].astype(float)
    groups = pd.factorize(d.loc[fit_rows, "concept_id"])[0]
    mod = sm.OLS(yf, Xf).fit(cov_type="cluster", cov_kwds={"groups": groups})
    info = dict(spec=name, covariates=covs, turnover_block=turnover, n=int(fit_rows.sum()),
                n_concepts=int(d.loc[fit_rows, "concept_id"].nunique()), r2=float(mod.rsquared),
                coef={k: dict(b=float(mod.params[k]), se_cluster=float(mod.bse[k]), p=float(mod.pvalues[k]))
                      for k in mod.params.index})
    red = [c for c in covs if c not in turnover]
    if turnover and red:
        mr = sm.OLS(yf, sm.add_constant(X.loc[fit_rows, red], has_constant="add")).fit()
        info["r2_reduced"] = float(mr.rsquared)
        info["partial_r2_turnover_block"] = float((mod.rsquared - mr.rsquared) / (1 - mr.rsquared))
    res = pd.Series(np.nan, index=d.index)
    Xa = sm.add_constant(X[ok_cov], has_constant="add")
    res[ok_cov] = d.loc[ok_cov, outcome].astype(float).values - Xa.values @ mod.params.values
    info["n_applied"] = int(ok_cov.sum())
    return res, info


# ------------------------------------------------------------------ event-study matrices
KS = list(range(-5, 1))
WK = [j for j, k in enumerate(KS) if -3 <= k <= 0]


def es_mat(m: list[dict], d: pd.DataFrame, col: str) -> np.ndarray:
    """Identical logic to exp_3 analysis_event.es_matrix and exp_4 analysis.mainpool_es (treated - mean controls)."""
    val = {(c, int(y)): v for c, y, v in zip(d.concept_id, d.year, d[col].astype(float))}
    mm = [r for r in m if r["n_controls"] > 0]
    M = np.full((len(mm), len(KS)), np.nan)
    for i, r in enumerate(mm):
        for j, k in enumerate(KS):
            y = r["t0"] + k
            tv = val.get((r["concept_id"], y), np.nan)
            cv = np.array([val.get((n, y), np.nan) for n in r["controls"]], dtype=float)
            cm = float(np.nanmean(cv)) if np.isfinite(cv).any() else np.nan
            if np.isfinite(tv) and np.isfinite(cm):
                M[i, j] = tv - cm
    return M


def _S(M: np.ndarray) -> tuple[np.ndarray, float]:
    with np.errstate(all="ignore"):
        import warnings
        warnings.simplefilter("ignore", RuntimeWarning)
        diff = np.nanmean(M, axis=0)
        return diff, float(np.nanmean(diff[WK])) if np.isfinite(diff[WK]).any() else np.nan


def _pv(x: np.ndarray) -> float:
    x = x[np.isfinite(x)]
    return float(min(1.0, max(2 * min(np.mean(x <= 0), np.mean(x >= 0)), 1.0 / len(x)))) if len(x) else np.nan


def paired(M_raw: np.ndarray, M_res: np.ndarray, B: int, seed: int, sd_res: float, M_ref: np.ndarray | None = None) -> dict:
    """Raw (full), raw on residualised-finite cells (cc) and residualised S from ONE shared set of bootstrap indices."""
    M_cc = np.where(np.isfinite(M_res), M_raw, np.nan)
    mats = {"raw": M_raw, "raw_cc": M_cc, "res": M_res}
    if M_ref is not None:
        mats["ref"] = np.where(np.isfinite(M_res), M_ref, np.nan)
    n = len(M_raw)
    rng = np.random.default_rng(seed)
    bS = {k: np.full(B, np.nan) for k in mats}
    bd = {k: np.full((B, len(KS)), np.nan) for k in mats}
    for b in range(B):
        idx = rng.integers(0, n, n)  # same draw sequence as the original es_stats loop
        for k, M in mats.items():
            dk, s = _S(M[idx])
            bd[k][b], bS[k][b] = dk, s
    out = {}
    for k, M in mats.items():
        dk, s = _S(M)
        ok = np.isfinite(bS[k])
        se = float(np.nanstd(bS[k][ok], ddof=1))
        with np.errstate(all="ignore"):
            import warnings
            warnings.simplefilter("ignore", RuntimeWarning)
            cik = [np.nanpercentile(bd[k][:, j], [2.5, 97.5]).tolist() if np.isfinite(bd[k][:, j]).sum() > 10 else [np.nan, np.nan]
                   for j in range(len(KS))]
        out[k] = dict(S=s, ci=np.percentile(bS[k][ok], [2.5, 97.5]).tolist(), se=se, p=_pv(bS[k]),
                      n_treated=int(np.isfinite(M[:, WK]).any(axis=1).sum()), diff_k=dk.tolist(), ci_k=cik,
                      n_k=np.isfinite(M).sum(0).astype(int).tolist())
    r = out["res"]
    r["mde"] = 2.8 * r["se"]
    r["pooled_sd"] = sd_res
    r["mde_in_sd"] = r["mde"] / sd_res if sd_res > 0 else np.nan
    fit_b = bS["raw_cc"] - bS["res"]
    out["fit"] = dict(S=out["raw_cc"]["S"] - r["S"], ci=np.nanpercentile(fit_b, [2.5, 97.5]).tolist(),
                      se=float(np.nanstd(fit_b, ddof=1)), p=_pv(fit_b))
    base = out["raw_cc"]["S"]
    keep = np.isfinite(bS["raw_cc"]) & np.isfinite(bS["res"]) & (np.abs(bS["raw_cc"]) >= 0.05 * abs(base))
    ret_b = bS["res"][keep] / bS["raw_cc"][keep]
    out["retained"] = dict(point=r["S"] / base if base else np.nan, ci=np.percentile(ret_b, [2.5, 97.5]).tolist(),
                           n_boot_used=int(keep.sum()), n_boot_dropped=int(B - keep.sum()))
    if M_ref is not None:
        ref = out["ref"]["S"]
        keep2 = np.isfinite(bS["ref"]) & (np.abs(bS["ref"]) >= 0.05 * abs(ref))
        rb = bS["res"][keep2] / bS["ref"][keep2]
        out["retained_vs_ref"] = dict(point=r["S"] / ref if ref else np.nan, ci=np.percentile(rb, [2.5, 97.5]).tolist(),
                                      n_boot_dropped=int(B - keep2.sum()))
    out["_boot"] = {"raw_cc": bS["raw_cc"], "res": bS["res"]}
    return out


def verdict(S_ci: list[float], ret_point: float, ret_lo: float) -> str:
    excl = S_ci[0] > 0 or S_ci[1] < 0
    if excl and ret_lo >= 0.5:
        return "NOT REDUCIBLE TO TURNOVER (seen data)"
    if (not excl) and ret_point < 0.3:
        return "LARGELY TURNOVER"
    return "AMBIGUOUS / UNDERPOWERED"


# ------------------------------------------------------------------ matched sets
def main_matches() -> list[dict]:
    mt = pd.read_csv(K.E3 / "results/event_study/matches_E_up.csv", dtype={"controls": str})
    return [dict(concept_id=r.concept_id, t0=int(r.t0), controls=[] if pd.isna(r.controls) or r.controls == "" else r.controls.split("|"),
                 n_controls=int(r.n_controls), widened=bool(r.widened), vol3_t0=r.vol3_t0) for r in mt.itertuples()]


def mesh_matches() -> list[dict]:
    return K.load_json(K.E4 / "results/analysis_summary.json")["mainpool_block"]["E_up"]["matches"]


# ------------------------------------------------------------------ main
@logger.catch(reraise=True)
def main() -> dict:
    K.setup_logging("part2_r1a")
    K.set_ram_limit(16)
    spec_txt = json.dumps(SPEC, sort_keys=True, indent=1)
    spec_hash = hashlib.sha256(spec_txt.encode()).hexdigest()
    K.dump({"spec": SPEC, "sha256_of_spec_json_sorted": spec_hash,
            "hash_method": "sha256 of json.dumps(spec, sort_keys=True, indent=1)"}, K.R1A / "r1a_spec.json")
    logger.info(f"R1a spec frozen sha256 {spec_hash}")

    # ---- original estimator code (read-only imports)
    cfg, lm, ae = K.import_from(K.E3, "config", "lib_metrics", "analysis_event")
    rq, an = K.import_from(K.E4, "rq1_spec", "analysis")

    pops = {"main": load_main(), "mesh": load_mesh()}
    V = SPEC["variables"]
    out: dict = {"header": HEADER, "spec_sha256": spec_hash, "correlations": [], "fits": [], "event": [], "gate": {},
                 "controls": {}, "pooling": {}, "verdicts": {}}

    # ---- 2.1 correlations
    for pop, d in pops.items():
        v = V[pop]
        for key in ["new_rel", "novelty", "beta_sim", "beta_sim_rar", "closure_raw", "log_vol3"] + (["beta_sim_native"] if pop == "mesh" else []):
            col = {"closure_raw": "closure_raw", "log_vol3": "log_vol3", "beta_sim_native": "beta_sim"}.get(key, v.get(key))
            r = within_corr(d, "closure", col)
            r.update(population=pop, pair=f"closure~{key}", role="context" if key in ("closure_raw", "log_vol3", "beta_sim_native") else "primary")
            out["correlations"].append(r)
            logger.info(f"[{pop}] closure~{col}: r_within={r.get('r_within', np.nan):.3f} {r.get('r_within_ci')} "
                        f"n_c={r['n_concepts']} n={r['n_rows']}")

    # ---- 2.2 residualisations
    specs = {}
    for pop, d in pops.items():
        v = V[pop]
        nr, nv, bs, bsr = v["new_rel"], v["novelty"], v["beta_sim"], v["beta_sim_rar"]
        rng0 = np.random.default_rng(0)
        d["noise"] = rng0.standard_normal(len(d))
        sd_c = float(d.loc[d.unit, "closure"].std())
        d["closure_oracle"] = d.closure + np.random.default_rng(0).normal(0, 0.1 * sd_c, len(d))
        vol = ["lv", "lv3", "age"]
        volH = vol + (["H"] if pop == "main" else [])
        s = {"P": (volH + [nr, nv, bs], [nr, nv, bs]), "R": (volH + [nr, nv, bsr], [nr, nv, bsr]),
             "V": (volH, []), "V0": (vol, []),
             "D_new_rel": (vol + [nr], [nr]), "D_novelty": (vol + [nv], [nv]), "D_beta_sim": (vol + [bs], [bs]),
             "POS": (vol + ["closure_raw"], ["closure_raw"]), "POS_ORACLE": (vol + ["closure_oracle"], ["closure_oracle"]),
             "NEG": (vol + ["noise"], ["noise"])}
        if pop == "mesh":
            s["H_mesh"] = (volH + [nr, nv, bs, "subfield_entropy"], [nr, nv, bs])
            s["B_native"] = (volH + [nr, nv, "beta_sim"], [nr, nv, "beta_sim"])
        specs[pop] = s
        for name, (covs, turn) in s.items():
            res, info = fit_resid(d, covs, turn, name)
            d[f"cres_{name}"] = res
            info["population"] = pop
            out["fits"].append(info)
            logger.info(f"[{pop}] fit {name}: n={info['n']} R2={info['r2']:.3f} partialR2={info.get('partial_r2_turnover_block', np.nan):.3f}")

    # ---- 2.3 reproduction gate
    m_main, m_mesh = main_matches(), mesh_matches()
    d = pops["main"]
    mdf = pd.DataFrame(m_main)
    seed_main = lm.stable_seed("closure") % 2 ** 31
    M_orig, _ = ae.es_matrix(mdf, d, "closure")
    st = ae.es_stats(M_orig, MAIN_B, seed=seed_main)
    rec = [t for t in K.load_json(K.E3 / "results/event_study/summary_E_up.json")["table"] if t["indicator"] == "closure" and t["version"] == "primary"][0]
    M_mine = es_mat(m_main, d, "closure")
    g = dict(S_reproduced=st["S"], ci_reproduced=st["ci"], se_reproduced=st["se"], n_treated=st["n_treated"],
             S_recorded=rec["S"], ci_recorded=rec["ci"], se_recorded=rec["se"], n_treated_recorded=rec["n_treated"],
             S_diff=abs(st["S"] - rec["S"]), ci_maxdiff=max(abs(a - b) for a, b in zip(st["ci"], rec["ci"])),
             replica_matrix_equal=bool(np.allclose(M_orig, M_mine, equal_nan=True)),
             source="round-2/experiment-3/src/results/event_study/summary_E_up.json#table[indicator=closure,version=primary]",
             estimator="exp_3 analysis_event.es_matrix + es_stats (imported read-only), B=1000, seed stable_seed('closure')")
    g["passed"] = bool(g["S_diff"] < 1e-6 and g["ci_maxdiff"] < 0.02 and g["replica_matrix_equal"])
    g["S_exact"] = bool(g["S_diff"] < 1e-6)
    g["gate_status"] = "PASS" if g["passed"] else "FAIL"
    out["gate"]["main"] = g
    logger.info(f"GATE main: S {st['S']:.6f} vs {rec['S']:.6f}; CI {st['ci']} vs {rec['ci']}; pass={g['passed']}")

    dm = pops["mesh"]
    idx = {(a, int(y)): float(v) for a, y, v in zip(dm.concept_id, dm.year, dm["closure"].astype(float))}
    unit_mesh = (dm.age >= rq.AGE_RANGE[0]) & (dm.age <= rq.AGE_RANGE[1]) & (dm.year <= rq.T_MAX)
    sd_mesh = float(dm.loc[unit_mesh, "closure"].std())
    st4 = an.mainpool_es(m_mesh, idx, "closure", np.random.default_rng(rq.SEED), sd_mesh)
    al = pd.read_csv(K.E4 / "results/rq1_effects_mainpool_aligned.csv")
    r4 = al[(al.label == "E_up") & (al.indicator == "closure") & (al.version == "primary")].iloc[0]
    M4 = es_mat(m_mesh, dm, "closure")
    g4 = dict(S_reproduced=st4["S"], ci_reproduced=st4["ci"], se_reproduced=st4["se"], n_treated=st4["n_treated"],
              S_recorded=float(r4.S), ci_recorded=[float(r4.ci_lo), float(r4.ci_hi)], se_recorded=float(r4.se),
              n_treated_recorded=int(r4.n_treated), S_diff=abs(st4["S"] - float(r4.S)),
              ci_maxdiff=max(abs(st4["ci"][0] - r4.ci_lo), abs(st4["ci"][1] - r4.ci_hi)),
              replica_S=_S(M4)[1],
              source="round-2/experiment-4/src/results/rq1_effects_mainpool_aligned.csv[label=E_up,indicator=closure,version=primary]",
              estimator="exp_4 analysis.mainpool_es (imported read-only), B=2000; original used a shared rng advanced "
                        "through earlier stages, so a fresh default_rng(42) cannot replay its exact bootstrap draws")
    g4["replica_matrix_equal"] = bool(abs(g4["replica_S"] - st4["S"]) < 1e-12)
    g4["passed"] = bool(g4["S_diff"] < 1e-6 and g4["ci_maxdiff"] < 0.02 and g4["replica_matrix_equal"])
    g4["S_exact"] = bool(g4["S_diff"] < 1e-6)
    # Monte-Carlo spread of the B=2000 percentile CI endpoints over 30 fresh seeds: is the CI gap bootstrap noise?
    mc = np.array([an.mainpool_es(m_mesh, idx, "closure", np.random.default_rng(1000 + s), sd_mesh)["ci"] for s in range(30)])
    g4["mc_ci_endpoint_sd"] = mc.std(axis=0, ddof=1).tolist()
    g4["mc_ci_endpoint_range"] = [mc.min(axis=0).tolist(), mc.max(axis=0).tolist()]
    g4["recorded_ci_within_mc_range"] = bool(all(mc[:, j].min() - 1e-9 <= g4["ci_recorded"][j] <= mc[:, j].max() + 1e-9 for j in (0, 1)))
    g4["gate_status"] = ("PASS" if g4["passed"] else
                         "FAIL on CI tolerance only (S exact; recorded CI " + ("inside" if g4["recorded_ci_within_mc_range"] else "outside")
                         + " the 30-seed Monte-Carlo range of CI endpoints) -> continue with reproduced S_raw per plan")
    out["gate"]["mesh"] = g4
    logger.info(f"GATE mesh: S {st4['S']:.6f} vs {r4.S:.6f}; CI {st4['ci']} vs {[r4.ci_lo, r4.ci_hi]}; pass={g4['passed']}")

    # ---- 2.4 event studies
    cfgs = {"main": (m_main, MAIN_B, seed_main, (d.fold == "screen") & (d.year <= 2015)),
            "mesh": (m_mesh, MESH_B, rq.SEED, unit_mesh)}
    boots = {}
    for pop, dd in pops.items():
        m, B, seed, sdmask = cfgs[pop]
        M_raw = es_mat(m, dd, "closure")
        M_V0 = es_mat(m, dd, "cres_V0")
        for name in specs[pop]:
            col = f"cres_{name}"
            M_res = es_mat(m, dd, col)
            sd_res = float(dd.loc[sdmask, col].std())
            r = paired(M_raw, M_res, B, seed, sd_res, M_ref=M_V0 if name == "NEG" else None)
            boots[(pop, name)] = r.pop("_boot")
            row = dict(population=pop, spec=name, B=B, seed=seed, header=HEADER,
                       S_raw=r["raw"]["S"], S_raw_ci=r["raw"]["ci"], S_raw_se=r["raw"]["se"], n_treated_raw=r["raw"]["n_treated"],
                       S_raw_cc=r["raw_cc"]["S"], S_raw_cc_ci=r["raw_cc"]["ci"], S_raw_cc_se=r["raw_cc"]["se"],
                       S_res=r["res"]["S"], S_res_ci=r["res"]["ci"], S_res_se=r["res"]["se"], S_res_p=r["res"]["p"],
                       n_treated_res=r["res"]["n_treated"], treated_lost=r["raw"]["n_treated"] - r["res"]["n_treated"],
                       S_fit=r["fit"]["S"], S_fit_ci=r["fit"]["ci"], S_fit_se=r["fit"]["se"],
                       retained=r["retained"]["point"], retained_ci=r["retained"]["ci"],
                       retained_boot_dropped=r["retained"]["n_boot_dropped"],
                       mde_res=r["res"]["mde"], mde_res_in_sd=r["res"]["mde_in_sd"], pooled_sd_res=r["res"]["pooled_sd"],
                       diff_k_raw=r["raw"]["diff_k"], ci_k_raw=r["raw"]["ci_k"], diff_k_res=r["res"]["diff_k"],
                       ci_k_res=r["res"]["ci_k"], n_k_res=r["res"]["n_k"])
            if "retained_vs_ref" in r:
                row["retained_vs_V0"] = r["retained_vs_ref"]["point"]
                row["retained_vs_V0_ci"] = r["retained_vs_ref"]["ci"]
            row["verdict_rule_applied"] = verdict(row["S_res_ci"], row["retained"], row["retained_ci"][0])
            out["event"].append(row)
            logger.info(f"[{pop}] {name}: S_raw_cc {row['S_raw_cc']:.3f} S_res {row['S_res']:.3f} {np.round(row['S_res_ci'], 3)} "
                        f"retained {row['retained']:.2f} {np.round(row['retained_ci'], 2)} n_res {row['n_treated_res']} -> {row['verdict_rule_applied']}")

    ev = {(r["population"], r["spec"]): r for r in out["event"]}
    for pop in pops:
        r = ev[(pop, "P")]
        out["verdicts"][pop] = dict(verdict=r["verdict_rule_applied"], S_res=r["S_res"], S_res_ci=r["S_res_ci"],
                                    retained=r["retained"], retained_ci=r["retained_ci"], gate_passed=out["gate"][pop]["passed"],
                                    note="SPEC P; " + HEADER)

    # ---- 2.5 pooling
    pool = {}
    for name in ["P", "R", "V", "V0", "D_new_rel", "D_novelty", "D_beta_sim", "POS", "POS_ORACLE", "NEG"]:
        a, b = ev[("main", name)], ev[("mesh", name)]
        pool[name] = dict(res=K.ivw([a["S_res"], b["S_res"]], [a["S_res_se"], b["S_res_se"]]),
                          raw_cc=K.ivw([a["S_raw_cc"], b["S_raw_cc"]], [a["S_raw_cc_se"], b["S_raw_cc_se"]]),
                          sign_agree_res=bool(np.sign(a["S_res"]) == np.sign(b["S_res"])))
    a, b = ev[("main", "P")], ev[("mesh", "P")]
    pool["raw_full_reproduced"] = K.ivw([a["S_raw"], b["S_raw"]], [a["S_raw_se"], b["S_raw_se"]])
    pool["raw_recorded_files"] = K.ivw([g["S_recorded"], g4["S_recorded"]], [g["se_recorded"], g4["se_recorded"]])
    sbs = pd.read_csv(K.E4 / "results/side_by_side_mainpool_vs_mesh.csv")
    sr = sbs[(sbs.label == "E_up") & (sbs.indicator == "closure") & (sbs.version == "primary")].iloc[0]
    pool["raw_side_by_side_file"] = dict(S_ivw=float(sr.S_pooled_ivw), se_ivw=float(sr.se_pooled_ivw), Q=float(sr.Q_heterogeneity))
    pool["raw_reproduces_side_by_side"] = bool(abs(pool["raw_recorded_files"]["S_ivw"] - sr.S_pooled_ivw) < 5e-3
                                               and abs(pool["raw_recorded_files"]["Q"] - sr.Q_heterogeneity) < 0.05)
    # pooled verdict: IVW of paired bootstrap replicates for the retained CI
    bm, bh = boots[("main", "P")], boots[("mesh", "P")]
    wm, wh = 1 / a["S_res_se"] ** 2, 1 / b["S_res_se"] ** 2
    wmr, whr = 1 / a["S_raw_cc_se"] ** 2, 1 / b["S_raw_cc_se"] ** 2
    rng = np.random.default_rng(0)
    nb = min(len(bm["res"]), len(bh["res"]))
    im, ih = rng.integers(0, len(bm["res"]), 4000), rng.integers(0, len(bh["res"]), 4000)
    pres = (wm * bm["res"][im] + wh * bh["res"][ih]) / (wm + wh)
    praw = (wmr * bm["raw_cc"][im] + whr * bh["raw_cc"][ih]) / (wmr + whr)
    Sres, Sraw = pool["P"]["res"]["S_ivw"], pool["P"]["raw_cc"]["S_ivw"]
    keep = np.isfinite(pres) & np.isfinite(praw) & (np.abs(praw) >= 0.05 * abs(Sraw))
    rci = np.percentile(pres[keep] / praw[keep], [2.5, 97.5]).tolist()
    pool["pooled_verdict"] = dict(S_ivw_res=Sres, S_ivw_res_ci=pool["P"]["res"]["ci"], S_ivw_raw_cc=Sraw,
                                  retained=Sres / Sraw, retained_ci=rci, n_boot_pairs=int(keep.sum()), n_boot_source=nb,
                                  verdict=verdict(pool["P"]["res"]["ci"], Sres / Sraw, rci[0]),
                                  note="independent draws of each population's paired bootstrap replicates, combined with "
                                       "the fixed IVW weights; " + HEADER)
    out["pooling"] = pool
    out["verdicts"]["pooled"] = pool["pooled_verdict"]
    logger.info(f"POOLED: S_ivw_res {Sres:.3f} {np.round(pool['P']['res']['ci'], 3)} Q {pool['P']['res']['Q']:.2f} "
                f"retained {Sres / Sraw:.2f} {np.round(rci, 2)} -> {pool['pooled_verdict']['verdict']}")

    # ---- 2.6 controls
    ctr = {}
    for pop in pops:
        ctr[pop] = dict(
            POS=dict(retained=ev[(pop, "POS")]["retained"], retained_ci=ev[(pop, "POS")]["retained_ci"],
                     r_within_closure_closure_raw=[c for c in out["correlations"] if c["population"] == pop and c["pair"] == "closure~closure_raw"][0].get("r_within")),
            POS_ORACLE=dict(retained=ev[(pop, "POS_ORACLE")]["retained"], passed=bool(abs(ev[(pop, "POS_ORACLE")]["retained"]) < 0.2)),
            NEG=dict(retained_vs_raw=ev[(pop, "NEG")]["retained"], retained_vs_V0=ev[(pop, "NEG")]["retained_vs_V0"],
                     retained_vs_V0_ci=ev[(pop, "NEG")]["retained_vs_V0_ci"],
                     passed=bool(0.9 <= ev[(pop, "NEG")]["retained_vs_V0"] <= 1.1)))
    # placebo (main only): regenerate exp_3 pseudo-onset matched sets exactly
    lab = pd.read_parquet(K.E3 / "results/labels/emergence_screen.parquet")
    lab = ae.assign_groups(lab, "E_up")
    never = sorted(set(lab.loc[lab.group == "never", "concept_id"]))
    info = lab.drop_duplicates("concept_id").set_index("concept_id")
    rngp = np.random.default_rng(11)
    t0s = mdf.t0.values
    pseudo = {}
    for c in never:
        same = mdf[mdf.concept_id.map(lambda x: info.loc[x, "F_band"]) == info.loc[c, "F_band"]].t0.values
        pseudo[c] = int(rngp.choice(same if len(same) else t0s))
    pm = ae.match(lab, d, treated_onsets=pseudo, never_set=set(never), exclude_self=True)
    Mp, _ = ae.es_matrix(pm, d, "closure")
    stp = ae.es_stats(Mp, MAIN_B, seed=99)
    recp = K.load_json(K.E3 / "results/event_study/summary_E_up.json")["placebo"]["results"]["closure"]
    pm_l = [dict(concept_id=r.concept_id, t0=int(r.t0), controls=list(r.controls), n_controls=int(r.n_controls)) for r in pm.itertuples()]
    pr = paired(es_mat(pm_l, d, "closure"), es_mat(pm_l, d, "cres_P"), MAIN_B, 99, 1.0)
    ctr["main"]["PLACEBO"] = dict(regenerated_S_raw=stp["S"], recorded_S_raw=recp["S"], regenerated_n=stp["n_treated"],
                                  recorded_n=recp["n_treated"], regeneration_exact=bool(abs(stp["S"] - recp["S"]) < 1e-9),
                                  S_res=pr["res"]["S"], S_res_ci=pr["res"]["ci"],
                                  passed=bool(pr["res"]["ci"][0] <= 0 <= pr["res"]["ci"][1]))
    ctr["mesh"]["PLACEBO"] = dict(skipped=True, reason="exp_4 did not save pseudo-onset matched sets for the main-pool-aligned "
                                                       "block; its own placebo (plan-native) is transcribed in Part 1 B4")
    out["controls"] = ctr
    logger.info(f"controls: {json.dumps(K.clean(ctr))[:800]}")

    # ---- figure
    fig_eventstudy(ev)
    K.dump(out, K.R1A / "r1a_results.json")
    tables(out)
    return out


def fig_eventstudy(ev: dict) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.8), sharey=False)
    for ax, pop, title in zip(axes, ["main", "mesh"], ["Main pool (exp_3), E_up", "MeSH aligned (exp_4), E_up"]):
        r = ev[(pop, "P")]
        for key, cik, lab_, col, off in [("diff_k_raw", "ci_k_raw", "raw closure (all cells)", "#1f77b4", -0.1),
                                         ("diff_k_res", "ci_k_res", "turnover-residualised (SPEC P)", "#d62728", 0.1)]:
            y = np.array(r[key], float)
            ci = np.array(r[cik], float)
            x = np.array(KS) + off
            ax.errorbar(x, y, yerr=[y - ci[:, 0], ci[:, 1] - y], fmt="o-", color=col, capsize=3, label=lab_, lw=1.4, ms=4)
        ax.axhline(0, color="grey", lw=0.8)
        ax.axvspan(-3.4, 0.4, color="0.92", zorder=0)
        ax.set_xticks(KS)
        ax.set_xlabel("k (years relative to onset t0)")
        ax.set_title(f"{title}\nS_raw_cc={r['S_raw_cc']:.2f}, S_res={r['S_res']:.2f}, retained={r['retained']:.2f}", fontsize=9)
    axes[0].set_ylabel("treated - matched-control mean")
    axes[0].legend(fontsize=8, loc="lower left")
    fig.suptitle(HEADER, fontsize=8, y=1.02)
    fig.tight_layout()
    for ext in ("png", "pdf"):
        fig.savefig(K.R1A / f"fig_r1a_eventstudy.{ext}", dpi=200, bbox_inches="tight")
    plt.close(fig)


def f3(x) -> str:
    return "NA" if x is None or (isinstance(x, float) and not math.isfinite(x)) else f"{x:.3f}"


def tables(out: dict) -> None:
    rows = []
    for r in out["event"]:
        rows.append({k: (json.dumps(K.clean(v)) if isinstance(v, list) else v) for k, v in r.items() if not k.startswith(("diff_k", "ci_k", "n_k"))})
    pd.DataFrame(rows).to_csv(K.R1A / "r1a_event_table.csv", index=False)
    pd.DataFrame([{k: (json.dumps(K.clean(v)) if isinstance(v, (list, dict)) else v) for k, v in c.items()} for c in out["correlations"]]) \
        .to_csv(K.R1A / "r1a_correlations.csv", index=False)
    fr = []
    for f in out["fits"]:
        for k, c in f["coef"].items():
            fr.append(dict(population=f["population"], spec=f["spec"], term=k, b=c["b"], se_cluster=c["se_cluster"], p=c["p"],
                           r2=f["r2"], partial_r2_turnover_block=f.get("partial_r2_turnover_block"), n=f["n"], n_concepts=f["n_concepts"]))
    pd.DataFrame(fr).to_csv(K.R1A / "r1a_residualisation_fits.csv", index=False)
    L = [f"# R1a turnover check (Part 2)\n\n**{HEADER}**\n",
         f"Spec sha256 `{out['spec_sha256']}` (results/r1a/r1a_spec.json, written before any statistic).\n",
         "## Reproduction gate\n", "| population | S reproduced | S recorded | CI reproduced | CI recorded | max CI diff | pass |", "|---|---|---|---|---|---|---|"]
    for pop, g in out["gate"].items():
        L.append(f"| {pop} | {g['S_reproduced']:.5f} | {g['S_recorded']:.5f} | [{g['ci_reproduced'][0]:.4f}, {g['ci_reproduced'][1]:.4f}] | "
                 f"[{g['ci_recorded'][0]:.4f}, {g['ci_recorded'][1]:.4f}] | {g['ci_maxdiff']:.4f} | {g['gate_status']} |")
    L.append("\nSource: exp_3 results/event_study/summary_E_up.json; exp_4 results/rq1_effects_mainpool_aligned.csv\n")
    L += ["## Within-concept correlations (closure vs turnover)\n", "| population | pair | r within [95% CI] | rho within | r pooled | n concepts | n rows |", "|---|---|---|---|---|---|---|"]
    for c in out["correlations"]:
        if "r_within" in c:
            L.append(f"| {c['population']} | {c['pair']} ({c['y']}) | {c['r_within']:.3f} [{c['r_within_ci'][0]:.3f}, {c['r_within_ci'][1]:.3f}] | "
                     f"{c['rho_within']:.3f} | {c['r_pooled']:.3f} | {c['n_concepts']} | {c['n_rows']} |")
    L.append("\nSource: exp_3 results/indicators/concept_year_indicators.parquet; exp_4 results/features.parquet (concept-cluster bootstrap B=2000)\n")
    L += [f"## Event study, raw vs residualised closure (E_up) — {HEADER}\n",
          "| pop | spec | S_raw (full) | S_raw_cc | S_res [95% CI] | S_fit | retained [95% CI] | n treated raw/res | MDE_res (SD) | verdict rule |",
          "|---|---|---|---|---|---|---|---|---|---|"]
    for r in out["event"]:
        L.append(f"| {r['population']} | {r['spec']} | {f3(r['S_raw'])} | {f3(r['S_raw_cc'])} | {f3(r['S_res'])} [{f3(r['S_res_ci'][0])}, {f3(r['S_res_ci'][1])}] | "
                 f"{f3(r['S_fit'])} | {f3(r['retained'])} [{f3(r['retained_ci'][0])}, {f3(r['retained_ci'][1])}] | {r['n_treated_raw']}/{r['n_treated_res']} | "
                 f"{f3(r['mde_res'])} ({f3(r['mde_res_in_sd'])}) | {r['verdict_rule_applied']} |")
    L.append("\nSource: this artifact, results/r1a/r1a_results.json (matched sets: exp_3 matches_E_up.csv; exp_4 analysis_summary.json mainpool_block.E_up.matches)\n")
    p = out["pooling"]
    L += ["## IVW pooling across populations (k = 2; Q is underpowered)\n", "| spec | S_ivw_res [95% CI] | se | Q (df=1) | p_Q | I^2 [Q-profile CI] | S_ivw_raw_cc |", "|---|---|---|---|---|---|---|"]
    for name in ["P", "R", "V", "V0", "D_new_rel", "D_novelty", "D_beta_sim", "POS", "POS_ORACLE", "NEG"]:
        q = p[name]["res"]
        L.append(f"| {name} | {q['S_ivw']:.3f} [{q['ci'][0]:.3f}, {q['ci'][1]:.3f}] | {q['se_ivw']:.3f} | {q['Q']:.2f} | {q['p_Q']:.3f} | "
                 f"{q['I2']:.2f} [{f3(q['I2_ci_qprofile'][0])}, {f3(q['I2_ci_qprofile'][1])}] | {p[name]['raw_cc']['S_ivw']:.3f} |")
    rr = p["raw_recorded_files"]
    L.append(f"\nRaw closure IVW from recorded file values: {rr['S_ivw']:.3f} (SE {rr['se_ivw']:.3f}), Q = {rr['Q']:.2f}; side-by-side file: "
             f"{p['raw_side_by_side_file']['S_ivw']:.3f} (SE {p['raw_side_by_side_file']['se_ivw']:.3f}), Q = {p['raw_side_by_side_file']['Q']:.2f}.\n")
    L.append("## Verdicts (pre-declared rule, SPEC P)\n")
    for k, v in out["verdicts"].items():
        L.append(f"- **{k}**: {v['verdict']}  (S_res {f3(v.get('S_res', v.get('S_ivw_res')))}, retained {f3(v['retained'])} "
                 f"[{f3(v['retained_ci'][0])}, {f3(v['retained_ci'][1])}])")
    L.append(f"\n## Controls\n\n```\n{json.dumps(K.clean(out['controls']), indent=1)}\n```\n")
    L.append(f"\nBad-control caveat: {SPEC['bad_control_caveat']}\n\nDeviation D1: {SPEC['deviation_D1']}\n")
    (K.R1A / "r1a_summary.md").write_text("\n".join(L))


if __name__ == "__main__":
    main()
