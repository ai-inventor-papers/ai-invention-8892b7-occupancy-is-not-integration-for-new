"""STAGE 7: PPML models on the screen fold (MAIN, kw5, main arm, F <= e <= 2019).

Primary:   Y_strict ~ A_cont + CT + event controls | concept x e + d x e, offset log(n_entry_papers), CRV1(concept)
Secondary: same + mom_d + log_centrality + log_W1 | concept + e + d (keeps singleton concept-years)
Decision (pre-declared): GRAFTING / TOOLKIT / BOTH / NEITHER on Holm-adjusted CRV1 p over {b_A, b_CT}.
"""
from __future__ import annotations

import json
import warnings

import numpy as np
import pandas as pd
from loguru import logger
from scipy import stats

import ppml
from config import RESULTS, SEED

A_VAR = "A_cont"  # primary anchoring measure after the pre-declared nativeness fallback (deviations.md #1)
CT_VAR = "CT"
EVENT_CONTROLS = ["prox_od", "RD", "log_n_partner_tags", "cov", "demic", "mean_topic_score", "boundary_share",
                  "abstract_share"]
SECONDARY_EXTRA = ["mom_d", "log_centrality", "log_W1"]


def primary_sample(df: pd.DataFrame, pop: str = "MAIN", fold: str = "screen") -> pd.DataFrame:
    s = df[(df.arm == "main") & (df.fold == fold) & df.kw5 & df[pop]].copy()
    need = [A_VAR, CT_VAR] + EVENT_CONTROLS + SECONDARY_EXTRA
    s = s.dropna(subset=[c for c in need if c in s.columns])
    s["cxe"] = pd.factorize(s.concept_id + "_" + s.e.astype(str))[0]
    s["dxe"] = pd.factorize(s.d.astype(str) + "_" + s.e.astype(str))[0]
    s["cfe"] = pd.factorize(s.concept_id)[0]
    s["efe"] = pd.factorize(s.e.astype(str))[0]
    s["dfe"] = pd.factorize(s.d.astype(str))[0]
    s["cx2"] = pd.factorize(s.concept_id + "_" + ((s.e - 2005) // 2).astype(str))[0]
    s["offset"] = np.log(s.n_entry_papers.astype(float))
    return s.reset_index(drop=True)


FE_SPECS = {"primary": ["cxe", "dxe"], "secondary": ["cfe", "efe", "dfe"],
            "coarse_cx2y": ["cx2", "dxe"],  # pre-declared coarsening: concept x 2-year entry bin + d x e
            "c_plus_dxe": ["cfe", "dxe"]}   # pre-declared alternative: concept + d x e


def fe_arrays(s: pd.DataFrame, spec: str) -> list[np.ndarray]:
    return [s[c].to_numpy() for c in FE_SPECS[spec]]


def fit_one(s: pd.DataFrame, y: str, xvars: list[str], spec: str = "primary", wild: bool = False,
            wild_vars: tuple = (), rng=None) -> dict | None:
    X = s[xvars].to_numpy(float)
    fes = fe_arrays(s, spec)
    yv = s[y].to_numpy(float)
    r = ppml.fit(yv, X, fes, s.offset.to_numpy(), s.concept_id.to_numpy(), maxit=500, tol=1e-12)
    if r is None:
        return None
    keep = r["keep"]
    G = r["G"]
    out = {"spec": spec, "y": y, "x": xvars, "n_input": int(len(s)), "n_retained": int(r["n"]), "G": int(G),
           "retained_share": float(r["n"] / len(s)), "coef": {}, "se": {}, "p": {}, "irr_sd": {}, "irr_01": {},
           "ci_irr_sd": {}, "sd_retained": {}}
    # singleton / separation accounting for the first FE dimension
    cells = pd.Series(fes[0]).value_counts()
    out["n_nonsingleton_fe0_cells"] = int((cells >= 2).sum())
    out["n_fe0_cells"] = int(len(cells))
    out["events_in_nonsingleton_fe0_cells"] = int(cells[cells >= 2].sum())
    tq = stats.t.ppf(0.975, G - 1)
    for i, v in enumerate(xvars):
        b, se = float(r["coef"][i]), float(r["se"][i])
        sd = float(s.loc[keep, v].std())
        tstat = b / se if se > 0 else np.nan
        out["coef"][v], out["se"][v] = b, se
        out["p"][v] = float(2 * stats.t.sf(abs(tstat), G - 1)) if se > 0 else np.nan
        out["sd_retained"][v] = sd
        out["irr_sd"][v] = float(np.exp(b * sd))
        out["irr_01"][v] = float(np.exp(b * 0.1))
        out["ci_irr_sd"][v] = [float(np.exp((b - tq * se) * sd)), float(np.exp((b + tq * se) * sd))]
    out["deviance"] = float(2 * np.sum(np.where(r["y"] > 0, r["y"] * np.log(np.where(r["y"] > 0, r["y"], 1) / r["mu"]),
                                                 0) - (r["y"] - r["mu"])))
    if wild:
        rng = rng or np.random.default_rng(SEED)
        out["p_wild"] = {}
        for v in wild_vars:
            j = xvars.index(v)
            Xr = np.delete(X, j, axis=1)
            out["p_wild"][v] = ppml.wild_score_test(yv, Xr, X[:, j], fes, s.offset.to_numpy(), s.concept_id.to_numpy(),
                                                    rng, reps=999)
    return out


def holm(pvals: dict) -> dict:
    items = sorted(pvals.items(), key=lambda kv: kv[1])
    m = len(items)
    adj, run = {}, 0.0
    for i, (k, p) in enumerate(items):
        run = max(run, min(1.0, (m - i) * p))
        adj[k] = run
    return adj


def decide(res: dict) -> dict:
    bA, bC = res["coef"][A_VAR], res["coef"][CT_VAR]
    h = holm({A_VAR: res["p"][A_VAR], CT_VAR: res["p"][CT_VAR]})
    sigA, sigC = h[A_VAR] < 0.05, h[CT_VAR] < 0.05
    if sigA and bA > 0 and not (sigC and bC > 0):
        reading = "GRAFTING"
    elif sigC and bC > 0 and not sigA:
        reading = "TOOLKIT"
    elif sigA and bA > 0 and sigC and bC > 0:
        reading = "BOTH"
    else:
        reading = "NEITHER"
    notes = []
    if sigA and bA < 0:
        notes.append("significant NEGATIVE anchoring coefficient (anchoring penalty)")
    if sigC and bC < 0:
        notes.append("significant NEGATIVE co-transfer coefficient (package penalty)")
    if sigC and bC > 0 and sigA and bA < 0:
        notes.append("co-transfer premium with an anchoring penalty")
    return {"reading": reading, "holm_p": h, "notes": notes}


def pyfixest_crosscheck(s: pd.DataFrame, y: str, xvars: list[str]) -> dict:
    """pyfixest.fepois on the sample retained by our iterated singleton/separation pruning, tight tolerances.
    (pyfixest's own pruning is not iterated, so on the unpruned sample it keeps extra singletons: same coefficients,
    different N and small-sample factor.)"""
    import pyfixest as pf
    r_own = fit_one(s, y, xvars, "primary")
    r_raw = ppml.fit(s[y].to_numpy(float), s[xvars].to_numpy(float), fe_arrays(s, "primary"), s.offset.to_numpy(),
                     s.concept_id.to_numpy())
    d = s[r_raw["keep"]].copy()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        m = pf.fepois(f"{y} ~ {' + '.join(xvars)} | cxe + dxe", data=d, offset="offset", vcov={"CRV1": "concept_id"},
                      demeaner_backend="scipy", fixef_tol=1e-12, iwls_tol=1e-12, iwls_maxiter=500)
    cf, se = m.coef(), m.se()
    diffs = {v: {"coef_own": r_own["coef"][v], "coef_pf": float(cf[v]), "abs_diff": abs(r_own["coef"][v] - float(cf[v])),
                 "se_own": r_own["se"][v], "se_pf": float(se[v]),
                 "se_rel_diff": abs(r_own["se"][v] - float(se[v])) / float(se[v])} for v in xvars}
    ok_coef = all(x["abs_diff"] < 1e-4 for x in diffs.values())
    ok_se = all(x["se_rel_diff"] < 1e-3 for x in diffs.values())
    return {"pass_coef_1e-4": ok_coef, "pass_se_rel_1e-3": ok_se, "n_pf": int(m._N), "per_var": diffs}


def lpm_fe(s: pd.DataFrame, y: str, xvars: list[str], spec: str = "primary") -> dict:
    import pyfixest as pf
    fe = "cxe + dxe" if spec == "primary" else "cfe + efe + dfe"
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        m = pf.feols(f"{y} ~ {' + '.join(xvars)} | {fe}", data=s, vcov={"CRV1": "concept_id"})
    return {"spec": spec, "y": y, "model": "linear probability, same FE", "n": int(m._N),
            "coef": {v: float(m.coef()[v]) for v in [A_VAR, CT_VAR] if v in xvars},
            "se": {v: float(m.se()[v]) for v in [A_VAR, CT_VAR] if v in xvars},
            "p": {v: float(m.pvalue()[v]) for v in [A_VAR, CT_VAR] if v in xvars},
            "effect_per_sd": {v: float(m.coef()[v] * s[v].std()) for v in [A_VAR, CT_VAR] if v in xvars}}


def run_models(df: pd.DataFrame, crosscheck: bool = False) -> dict:
    s = primary_sample(df)
    ctrl = EVENT_CONTROLS
    rng = np.random.default_rng(SEED)
    res = {"sample": {"n_events": int(len(s)), "n_concepts": int(s.concept_id.nunique()),
                      "rule": "screen fold, MAIN, kw5, main arm, complete controls",
                      "dropped_missing_controls": int(len(df[(df.arm == "main") & (df.fold == "screen") & df.kw5
                                                                & df.MAIN]) - len(s))}}
    res["M0"] = fit_one(s, "Y_strict", ctrl, "primary")
    res["M1"] = fit_one(s, "Y_strict", [A_VAR, CT_VAR] + ctrl, "primary", wild=True, wild_vars=(A_VAR, CT_VAR), rng=rng)
    res["M1a"] = fit_one(s, "Y_strict", [A_VAR] + ctrl, "primary")
    res["M1b"] = fit_one(s, "Y_strict", [CT_VAR] + ctrl, "primary")
    res["M1_secondary"] = fit_one(s, "Y_strict", [A_VAR, CT_VAR] + ctrl + SECONDARY_EXTRA, "secondary", wild=True,
                                  wild_vars=(A_VAR, CT_VAR), rng=rng)
    res["M0_secondary"] = fit_one(s, "Y_strict", ctrl + SECONDARY_EXTRA, "secondary")
    res["M1a_secondary"] = fit_one(s, "Y_strict", [A_VAR] + ctrl + SECONDARY_EXTRA, "secondary")
    res["M1b_secondary"] = fit_one(s, "Y_strict", [CT_VAR] + ctrl + SECONDARY_EXTRA, "secondary")
    res["M1_coarse_cx2y"] = fit_one(s, "Y_strict", [A_VAR, CT_VAR] + ctrl, "coarse_cx2y", wild=True,
                                    wild_vars=(A_VAR, CT_VAR), rng=rng)
    res["M1_c_plus_dxe"] = fit_one(s, "Y_strict", [A_VAR, CT_VAR] + ctrl, "c_plus_dxe", wild=True,
                                   wild_vars=(A_VAR, CT_VAR), rng=rng)
    for y in ["Y_all", "Y_lenient"]:
        res[f"M1_{y}"] = fit_one(s, y, [A_VAR, CT_VAR] + ctrl, "primary")
        res[f"M1_{y}_secondary"] = fit_one(s, y, [A_VAR, CT_VAR] + ctrl + SECONDARY_EXTRA, "secondary")
    res["EST_bin_LPM"] = lpm_fe(s, "EST_bin", [A_VAR, CT_VAR] + ctrl, "primary")
    res["EST_bin_LPM_secondary"] = lpm_fe(s, "EST_bin", [A_VAR, CT_VAR] + ctrl + SECONDARY_EXTRA, "secondary")
    m1 = res["M1"]
    thin = m1 is None or m1["retained_share"] < 0.30 or m1["G"] < 50
    res["fallback3_thin_cells"] = {"triggered": bool(thin),
                                   "retained_share": None if m1 is None else m1["retained_share"],
                                   "G": None if m1 is None else m1["G"],
                                   "rule": "retained < 30% of events or G < 50 -> secondary spec is co-primary"}
    res["decision_primary"] = decide(m1) if m1 else None
    res["decision_secondary"] = decide(res["M1_secondary"]) if res["M1_secondary"] else None
    if thin:
        res["decision_note"] = ("within concept x entry-year identification is thin: the secondary spec is "
                                "co-primary (pre-declared fallback 3)")
    for k in ["M1_coarse_cx2y", "M1_c_plus_dxe"]:
        res[f"decision_{k}"] = decide(res[k]) if res[k] else None
    cc = RESULTS / "pyfixest_crosscheck.json"
    if crosscheck or not cc.exists():
        try:
            cc.write_text(json.dumps(pyfixest_crosscheck(s, "Y_strict", [A_VAR, CT_VAR] + ctrl), indent=1, default=float))
        except Exception as ex:  # noqa: BLE001 - record and continue; the own estimator is validated in tests
            cc.write_text(json.dumps({"error": repr(ex)}))
    res["pyfixest_crosscheck"] = json.loads(cc.read_text())
    (RESULTS / "d2_models.json").write_text(json.dumps(res, indent=1, default=float))
    rows = []
    for k, v in res.items():
        if isinstance(v, dict) and "coef" in v and "x" in v:
            for var in [A_VAR, CT_VAR]:
                if var in v["coef"]:
                    rows.append({"model": k, "spec": v["spec"], "y": v["y"], "var": var, "coef": v["coef"][var],
                                 "se": v["se"][var], "p": v["p"][var], "irr_sd": v["irr_sd"][var],
                                 "irr_sd_lo": v["ci_irr_sd"][var][0], "irr_sd_hi": v["ci_irr_sd"][var][1],
                                 "irr_01": v["irr_01"][var], "n": v["n_retained"], "G": v["G"],
                                 "p_wild": (v.get("p_wild") or {}).get(var)})
    pd.DataFrame(rows).to_csv(RESULTS / "d2_models_table.csv", index=False)
    logger.info(f"M1: n={m1['n_retained']} G={m1['G']} bA={m1['coef'][A_VAR]:.3f} (p {m1['p'][A_VAR]:.4f}) "
                f"bCT={m1['coef'][CT_VAR]:.3f} (p {m1['p'][CT_VAR]:.4f}); decision {res['decision_primary']}")
    return res
