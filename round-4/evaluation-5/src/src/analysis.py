"""STEP 4: exposures and all metrics (M-i enrichment, M-ii interaction, M-iii vocabulary class, M-iv mediation,
balance, placebo/sanity, supplementary). Runs only after the mech_spec hash check in eval.py."""
from __future__ import annotations

import multiprocessing as mp
import warnings
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd
from loguru import logger
from scipy import stats

import mech_common as mc
from stats_core import boot_indices, boot_p, clogit, kappa, pct_ci, smd, wald_p

MODELS = {
    "m1": ["E_any", "lp"],
    "m2": ["E_any", "E_neg", "lp"],                      # PRIMARY estimand: OR(E_any | E_neg, prior_n)
    "m3": ["E_w", "E_neg", "lp"],
    "m_neg_only": ["E_neg", "lp"],
    "m_plac": ["E_any", "E_neg", "E_plac", "lp"],        # strata with a placebo entry only
    "m_plac_only": ["E_plac", "lp"],                     # strata with a placebo entry only
    "m_int": ["E_any", "E_neg", "lp", "E_any_x_zA"],
    "m_voc": ["E_nat", "E_adj", "E_for", "E_unprof", "E_neg", "lp"],
    "m_comp": ["E_comp", "E_noncomp", "E_neg", "lp"],
    "m_swap": ["E_swap", "E_neg", "lp"],                 # label shuffle: another entry's partner set, same host-year
    "m_any_incl_c": ["E_any_incl_c", "E_neg", "lp"],
}
PLAC_MODELS = {"m_plac", "m_plac_only", "m_swap"}


# ------------------------------------------------------------------ exposures
def compute_exposures(G: dict, C, L: pd.DataFrame, T: pd.DataFrame) -> pd.DataFrame:
    ptr, idx = G["P"]
    tg = T.set_index("entry_id")
    crow = {cid: set(G["links"][cid][0].tolist()) for cid in L.concept_id.unique()}
    out = []
    for r in L.itertuples():
        t = tg.loc[r.entry_id]
        w_all = C.author_works(int(r.au))
        w_all = w_all[C.year[w_all] <= int(r.e) - 1]
        cr = crow[r.concept_id]
        w_ex = np.array([x for x in w_all if int(x) not in cr], np.int64)
        tags = set()
        for row in w_ex:
            tags.update(idx[ptr[row]:ptr[row + 1]].tolist())
        tags_c = set(tags)
        for row in w_all:
            tags_c.update(idx[ptr[row]:ptr[row + 1]].tolist())
        P = list(t.P_nodes)
        w = np.asarray(t.P_w, float)
        used = np.array([p in tags for p in P], bool)
        cls = list(t.P_cls)
        comp = list(t.P_comp)
        neg, plac, pfull = list(t.NEG_nodes), list(t.PLAC_nodes), list(t.PLAC_full_nodes)
        targets = set(P) | set(neg) | set(plac)
        n_tw = 0
        for row in w_ex:
            if targets & set(idx[ptr[row]:ptr[row + 1]].tolist()):
                n_tw += 1
        out.append({
            "E_any": int(used.any()), "E_w": float((w * used).sum() / w.sum()) if w.sum() > 0 else 0.0,
            "E_nat": int(any(u for u, c in zip(used, cls) if c == "NATIVE")),
            "E_adj": int(any(u for u, c in zip(used, cls) if c == "ADJACENT")),
            "E_for": int(any(u for u, c in zip(used, cls) if c == "FOREIGN")),
            "E_unprof": int(any(u for u, c in zip(used, cls) if c == "UNPROFILED")),
            "E_comp": int(any(u for u, c in zip(used, comp) if c)),
            "E_noncomp": int(any(u for u, c in zip(used, comp) if not c)),
            "E_neg": int(any(n in tags for n in neg)),
            "E_neg_w": float(np.mean([n in tags for n in neg])) if neg else 0.0,
            "E_plac": int(any(n in tags for n in plac)),
            "E_swap": int(any(n in tags for n in pfull)),
            "has_plac": int(len(plac) > 0),
            "E_any_incl_c": int(any(p in tags_c for p in P)),
            "n_prior_used": int(len(w_ex)), "n_target_works": n_tw})
    E = pd.DataFrame(out, index=L.index)
    return pd.concat([L, E], axis=1)


def add_design(D: pd.DataFrame, sdA: float, mA: float) -> pd.DataFrame:
    D = D.copy()
    D["lp"] = np.log1p(D.n_prior_corpus.astype(float))
    D["zA"] = (D.A_cont - mA) / sdA
    D["E_any_x_zA"] = D.E_any * D.zA
    return D


# ------------------------------------------------------------------ model set + bootstrap
def fit_model(D: pd.DataFrame, cols: list[str], cluster: bool = True) -> dict | None:
    X = D[cols].to_numpy(float)
    keep = np.ones(len(cols), bool)
    # drop exposure columns without any within-stratum variation (unidentified)
    s = D.stratum.to_numpy()
    for j in range(len(cols)):
        mx = pd.Series(X[:, j]).groupby(s).agg(lambda z: z.max() - z.min())
        if (mx > 0).sum() == 0:
            keep[j] = False
    if keep.sum() == 0:
        return None
    r = clogit(D.case.to_numpy(), X[:, keep], s, D.cluster.to_numpy() if cluster else None)
    beta = np.full(len(cols), np.nan)
    se = np.full(len(cols), np.nan)
    sec = np.full(len(cols), np.nan)
    beta[keep], se[keep] = r["beta"], r["se"]
    if cluster:
        sec[keep] = r["se_crv"]
    return {"cols": cols, "beta": beta, "se": se, "se_crv": sec, "n_strata": r["n_strata"], "n": r["n"],
            "converged": r["converged"]}


def fast_betas(D: pd.DataFrame, cols: list[str]) -> np.ndarray:
    X = D[cols].to_numpy(float)
    try:
        r = clogit(D.case.to_numpy(), X, D.stratum.to_numpy(), None, maxit=30)
        b = r["beta"]
        b[np.abs(b) > 15] = np.nan  # separation in a replicate
        return b
    except (np.linalg.LinAlgError, FloatingPointError, ValueError):
        return np.full(len(cols), np.nan)


def model_suite(D: pd.DataFrame) -> dict:
    out = {}
    Dp = D[D.has_plac_stratum == 1]
    for name, cols in MODELS.items():
        out[name] = fast_betas(Dp if name in PLAC_MODELS else D, cols)
    for t in (1, 2, 3):
        Dt = D[D.A_tercile == t]
        out[f"m2_T{t}"] = fast_betas(Dt, MODELS["m2"]) if Dt.stratum.nunique() >= 20 else np.full(3, np.nan)
    return out


def bootstrap(D: pd.DataFrame, B: int, seed: int) -> dict:
    rng = np.random.default_rng(seed)
    st = D.drop_duplicates("stratum")[["stratum", "cluster"]]
    rows_by_stratum = D.groupby("stratum").indices
    reps = {}
    for b in range(B):
        sidx, rep = boot_indices(st.cluster.to_numpy(), rng)
        chosen = st.stratum.to_numpy()[sidx]
        parts, sid = [], []
        for k, s_ in enumerate(chosen):
            ix = rows_by_stratum[s_]
            parts.append(ix)
            sid.append(np.full(len(ix), k))
        ix = np.concatenate(parts)
        Db = D.iloc[ix].copy()
        Db["stratum"] = np.concatenate(sid)
        res = model_suite(Db)
        for k, v in res.items():
            reps.setdefault(k, []).append(v)
    return {k: np.vstack(v) for k, v in reps.items()}


def bootstrap_one(D: pd.DataFrame, cols: list[str], B: int, seed: int) -> np.ndarray:
    """Concept-cluster bootstrap for a single model (same resampling scheme as bootstrap())."""
    rng = np.random.default_rng(seed)
    st = D.drop_duplicates("stratum")[["stratum", "cluster"]]
    rows_by_stratum = D.groupby("stratum").indices
    out = []
    for _ in range(B):
        sidx, _rep = boot_indices(st.cluster.to_numpy(), rng)
        chosen = st.stratum.to_numpy()[sidx]
        ix = np.concatenate([rows_by_stratum[s_] for s_ in chosen])
        sid = np.concatenate([np.full(len(rows_by_stratum[s_]), k) for k, s_ in enumerate(chosen)])
        Db = D.iloc[ix].copy()
        Db["stratum"] = sid
        out.append(fast_betas(Db, cols))
    return np.vstack(out)


def summarize_model(name: str, fit: dict | None, boots: np.ndarray | None) -> dict:
    if fit is None:
        return {"model": name, "identified": False}
    out = {"model": name, "n_strata": fit["n_strata"], "n_rows": fit["n"], "converged": fit["converged"], "terms": {}}
    for j, c in enumerate(fit["cols"]):
        b = fit["beta"][j]
        term = {"beta": b, "OR": float(np.exp(b)) if np.isfinite(b) else None, "se_model": fit["se"][j],
                "se_crv_concept": fit["se_crv"][j], "p_model": wald_p(b, fit["se"][j]),
                "p_crv": wald_p(b, fit["se_crv"][j])}
        if boots is not None:
            bb = boots[:, j]
            ci = pct_ci(bb)
            term.update({"OR_ci95_boot": [float(np.exp(ci[0])), float(np.exp(ci[1]))] if np.isfinite(ci[0]) else None,
                         "p_boot": boot_p(bb), "boot_valid": int(np.isfinite(bb).sum())})
        out["terms"][c] = term
    return out


def ratio_summary(fit: dict, boots: np.ndarray, a: str, b: str) -> dict:
    ja, jb = fit["cols"].index(a), fit["cols"].index(b)
    est = fit["beta"][ja] - fit["beta"][jb]
    bb = boots[:, ja] - boots[:, jb]
    ci = pct_ci(bb)
    return {"log_ratio": est, "ratio": float(np.exp(est)) if np.isfinite(est) else None,
            "ci95_boot": [float(np.exp(ci[0])), float(np.exp(ci[1]))] if np.isfinite(ci[0]) else None,
            "p_boot": boot_p(bb), "log_contrast_ci95": ci}


def full_block(D: pd.DataFrame, B: int, seed: int) -> dict:
    """Point fits (with CRV SE) + concept-cluster bootstrap for the whole model suite."""
    fits = {}
    Dp = D[D.has_plac_stratum == 1]
    for name, cols in MODELS.items():
        fits[name] = fit_model(Dp if name in PLAC_MODELS else D, cols)
    for t in (1, 2, 3):
        Dt = D[D.A_tercile == t]
        fits[f"m2_T{t}"] = fit_model(Dt, MODELS["m2"]) if Dt.stratum.nunique() >= 20 else None
    boots = bootstrap(D, B, seed) if B > 0 else {}
    summ = {k: summarize_model(k, f, boots.get(k)) for k, f in fits.items()}
    ratios = {}
    if fits["m2"] is not None and B > 0:
        ratios["partner_over_neg"] = ratio_summary(fits["m2"], boots["m2"], "E_any", "E_neg")
    if fits["m_plac"] is not None and B > 0:
        ratios["partner_over_plac"] = ratio_summary(fits["m_plac"], boots["m_plac"], "E_any", "E_plac")
        ratios["partner_over_neg_in_plac_strata"] = ratio_summary(fits["m_plac"], boots["m_plac"], "E_any", "E_neg")
    if fits["m_voc"] is not None and B > 0:
        ratios["native_vs_foreign"] = ratio_summary(fits["m_voc"], boots["m_voc"], "E_nat", "E_for")
        ratios["adjacent_vs_foreign"] = ratio_summary(fits["m_voc"], boots["m_voc"], "E_adj", "E_for")
    if fits["m_comp"] is not None and B > 0:
        ratios["companion_vs_noncompanion"] = ratio_summary(fits["m_comp"], boots["m_comp"], "E_comp", "E_noncomp")
    return {"fits": summ, "ratios": ratios, "_fits": fits, "_boots": boots}


def descriptives(D: pd.DataFrame) -> dict:
    ca, co = D[D.case == 1], D[D.case == 0]
    out = {"n_cases": int(len(ca)), "n_controls": int(len(co)), "n_strata": int(D.stratum.nunique()),
           "n_concepts": int(D.cluster.nunique()), "n_entries": int(D.entry_id.nunique())}
    for c in ["E_any", "E_neg", "E_plac", "E_nat", "E_adj", "E_for", "E_unprof", "E_comp", "E_noncomp", "E_swap",
              "E_any_incl_c"]:
        out[f"prev_case_{c}"] = float(ca[c].mean())
        out[f"prev_control_{c}"] = float(co[c].mean())
    out["mean_case_E_w"], out["mean_control_E_w"] = float(ca.E_w.mean()), float(co.E_w.mean())
    # discordant pairs (1:1)
    w = D.pivot_table(index="stratum", columns="case", values="E_any", aggfunc="max")
    out["discordant_case_only"] = int(((w[1] == 1) & (w[0] == 0)).sum())
    out["discordant_control_only"] = int(((w[1] == 0) & (w[0] == 1)).sum())
    out["discordant_pairs"] = out["discordant_case_only"] + out["discordant_control_only"]
    return out


def balance(D: pd.DataFrame, pre: pd.DataFrame | None) -> dict:
    ca, co = D[D.case == 1], D[D.case == 0]
    out = {}
    for c in ["team_bin", "act_bin", "fy_bin", "prior_bin", "lp", "first_year"]:
        out[f"smd_after_{c}"] = smd(ca[c], co[c])
    if pre is not None and len(pre):
        for c, col in [("team_bin", "risk_team_bin_mean"), ("act_bin", "risk_act_bin_mean"),
                       ("prior_bin", "risk_prior_bin_mean"), ("lp", "risk_log1p_prior_mean")]:
            if col in pre:
                sd = np.sqrt((ca[c].var(ddof=1) + co[c].var(ddof=1)) / 2)
                out[f"smd_before_{c}"] = float((ca[c].mean() - pre[col].mean()) / sd) if sd > 0 else 0.0
    out["relax_counts"] = D[D.case == 1].relax.value_counts().sort_index().to_dict()
    return out


def permutation_null(D: pd.DataFrame, n: int, seed: int) -> dict:
    rng = np.random.default_rng(seed)
    bs = []
    Dq = D.sort_values(["stratum", "case"]).copy()
    strata = Dq.stratum.to_numpy()
    for _ in range(n):
        u = rng.random(len(Dq))
        # within-stratum random reassignment of the single case label
        order = pd.Series(u).groupby(strata).rank(method="first").to_numpy()
        Dq["case"] = (order == 1).astype(int)
        bs.append(fast_betas(Dq, MODELS["m2"])[0])
    bs = np.array(bs)
    return {"n": n, "mean_logOR": float(np.nanmean(bs)), "sd_logOR": float(np.nanstd(bs)),
            "mean_OR": float(np.exp(np.nanmean(bs))), "q025_OR": float(np.exp(np.nanquantile(bs, 0.025))),
            "q975_OR": float(np.exp(np.nanquantile(bs, 0.975))), "draws": bs.tolist()}


def lpm_crosscheck(D: pd.DataFrame) -> dict:
    import pyfixest as pf
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        m = pf.feols("case ~ E_any + E_neg + lp | stratum", data=D.assign(stratum=D.stratum.astype(str)),
                     vcov={"CRV1": "cluster"})
    return {"coef_E_any": float(m.coef()["E_any"]), "se_E_any": float(m.se()["E_any"]),
            "p_E_any": float(m.pvalue()["E_any"]), "coef_E_neg": float(m.coef()["E_neg"]),
            "p_E_neg": float(m.pvalue()["E_neg"]), "n": int(m._N)}


def statsmodels_check(D: pd.DataFrame) -> dict:
    from statsmodels.discrete.conditional_models import ConditionalLogit
    m = ConditionalLogit(D.case.to_numpy(), D[MODELS["m2"]].to_numpy(float), groups=D.stratum.to_numpy()).fit(disp=0)
    own = clogit(D.case.to_numpy(), D[MODELS["m2"]].to_numpy(float), D.stratum.to_numpy())
    return {"sm_beta": m.params.tolist(), "own_beta": own["beta"].tolist(),
            "max_abs_diff": float(np.max(np.abs(m.params - own["beta"]))),
            "sm_se": m.bse.tolist(), "own_se": own["se"].tolist()}


# ------------------------------------------------------------------ mediation (entry level)
def _ppml_arrays(E: pd.DataFrame, cols: list[str], conc: np.ndarray | None = None):
    cf = pd.factorize(E.concept_id if conc is None else conc)[0]
    fes = [cf, pd.factorize(E.e.astype(str))[0], pd.factorize(E.d.astype(str))[0]]
    return (E.Y_strict.to_numpy(float), E[cols].to_numpy(float), fes, E.offset.to_numpy(),
            (E.concept_id.to_numpy() if conc is None else conc))


MED_SPECS = {"base": [], "M2": ["M2"], "M2_split": ["M2_native", "M2_adjacent"], "M1": ["M1"], "M2_share": ["M2_share"]}


def _med_fit_all(E: pd.DataFrame, conc: np.ndarray | None = None) -> dict:
    import ppml  # vendored
    res = {}
    for k, extra in MED_SPECS.items():
        y, X, fes, off, cl = _ppml_arrays(E, mc.XVARS + extra, conc)
        r = ppml.fit(y, X, fes, off, cl, maxit=300, tol=1e-10)
        res[k] = None if r is None else {"coef": r["coef"], "se": r["se"], "G": r["G"], "n": r["n"], "mu": r["mu"],
                                         "keep": r["keep"]}
    # reverse: M2 without A_cont
    cols = [c for c in mc.XVARS if c != "A_cont"] + ["M2"]
    y, X, fes, off, cl = _ppml_arrays(E, cols, conc)
    r = ppml.fit(y, X, fes, off, cl, maxit=300, tol=1e-10)
    res["M2_noA"] = None if r is None else {"coef": r["coef"], "se": r["se"], "G": r["G"], "n": r["n"]}
    return res


def _gelbach(E: pd.DataFrame, fit_full: dict, extra: list[str], conc=None) -> dict:
    """delta_k = Gamma_k[A] * beta_k, Gamma from mu-weighted FE auxiliary regressions of each mediator on the base X."""
    import ppml
    y, X, fes, off, cl = _ppml_arrays(E, mc.XVARS + extra, conc)
    keep = fit_full["keep"]
    fes_k = [np.unique(f[keep], return_inverse=True)[1] for f in fes]
    mu = fit_full["mu"]
    Mt = ppml._demean(X[keep], mu, fes_k)
    Xb, Mm = Mt[:, :len(mc.XVARS)], Mt[:, len(mc.XVARS):]
    WX = Xb * mu[:, None]
    Gam = np.linalg.solve(Xb.T @ WX, WX.T @ Mm)  # k_base x n_med
    out = {}
    for j, m in enumerate(extra):
        out[m] = float(Gam[0, j] * fit_full["coef"][len(mc.XVARS) + j])
    return out


def _att(res: dict) -> dict:
    b0 = res["base"]["coef"][0] if res.get("base") else np.nan
    out = {"b_base": b0}
    for k in ("M2", "M2_split", "M1", "M2_share"):
        if res.get(k):
            out[f"att_{k}"] = (b0 - res[k]["coef"][0]) / b0
            out[f"b_full_{k}"] = res[k]["coef"][0]
    if res.get("M2_noA") and res.get("M2"):
        bm_alone = res["M2_noA"]["coef"][-1]
        bm_full = res["M2"]["coef"][-1]
        out["reverse_att_M2"] = (bm_alone - bm_full) / bm_alone if bm_alone != 0 else np.nan
    return out


def _med_boot_job(args):
    import sys
    sys.path.insert(0, args["vendor"])
    sys.path.insert(0, args["src"])
    E = pd.read_parquet(args["path"])
    rng = np.random.default_rng(args["seed"])
    uc = E.concept_id.unique()
    by = E.groupby("concept_id").indices
    outs = []
    for _ in range(args["reps"]):
        draw = rng.choice(uc, len(uc), replace=True)
        ix = np.concatenate([by[c] for c in draw])
        conc = np.concatenate([np.full(len(by[c]), f"b{t}") for t, c in enumerate(draw)])
        Eb = E.iloc[ix].reset_index(drop=True)
        try:
            res = _med_fit_all(Eb, conc)
            a = _att(res)
            if res.get("M2_split"):
                g = _gelbach(Eb, res["M2_split"], MED_SPECS["M2_split"], conc)
                a.update({f"gelbach_{k}": v / a["b_base"] for k, v in g.items()})
            if res.get("M2"):
                a["bM2_full"] = res["M2"]["coef"][-1]
        except (np.linalg.LinAlgError, ValueError, RuntimeError):
            a = {}
        outs.append(a)
    return outs


def mediation(E: pd.DataFrame, B: int, seed: int, workers: int) -> dict:
    res = _med_fit_all(E)
    att = _att(res)
    sd = {c: float(E.loc[res["base"]["keep"], c].std()) for c in ["A_cont", "M2", "M1", "M2_share", "M2_native",
                                                                   "M2_adjacent"]}
    point = {"att": att, "models": {}}
    for k, r in res.items():
        if r is None:
            point["models"][k] = None
            continue
        cols = (mc.XVARS + MED_SPECS[k]) if k in MED_SPECS else [c for c in mc.XVARS if c != "A_cont"] + ["M2"]
        tq = stats.t.ppf(0.975, r["G"] - 1)
        point["models"][k] = {"n": r["n"], "G": r["G"], "terms": {
            c: {"b": float(r["coef"][i]), "se": float(r["se"][i]),
                "p": float(2 * stats.t.sf(abs(r["coef"][i] / r["se"][i]), r["G"] - 1)),
                "irr_sd": float(np.exp(r["coef"][i] * sd[c])) if c in sd else None,
                "irr_sd_ci": [float(np.exp((r["coef"][i] - tq * r["se"][i]) * sd[c])),
                              float(np.exp((r["coef"][i] + tq * r["se"][i]) * sd[c]))] if c in sd else None}
            for i, c in enumerate(cols) if c in ("A_cont", "CT", "M2", "M2_native", "M2_adjacent", "M1", "M2_share")}}
    g = _gelbach(E, res["M2_split"], MED_SPECS["M2_split"]) if res.get("M2_split") else {}
    point["gelbach_M2_split"] = {k: {"delta": v, "share_of_b_base": v / att["b_base"]} for k, v in g.items()}
    point["gelbach_sum_vs_movement"] = {"sum_delta": float(sum(g.values())) if g else None,
                                        "movement": float(att["b_base"] - att.get("b_full_M2_split", np.nan))}
    # bootstrap
    p = mc.RESULTS / "cache_mediation_entries.parquet"
    E.to_parquet(p)
    per = int(np.ceil(B / workers))
    jobs = [{"path": str(p), "seed": seed + i, "reps": per, "vendor": str(mc.WS / "vendor"), "src": str(mc.WS / "src")}
            for i in range(workers)]
    with ProcessPoolExecutor(max_workers=workers, mp_context=mp.get_context("spawn")) as ex:
        allb = [a for r in ex.map(_med_boot_job, jobs) for a in r][:B]
    p.unlink(missing_ok=True)
    bdf = pd.DataFrame(allb)
    boot = {}
    for c in bdf.columns:
        v = bdf[c].to_numpy(float)
        boot[c] = {"ci95": pct_ci(v), "p_boot_vs0": boot_p(v), "valid": int(np.isfinite(v).sum()),
                   "median": float(np.nanmedian(v))}
    return {"point": point, "boot": boot, "B": int(len(bdf)), "boot_draws_att_M2": bdf.get("att_M2", pd.Series()).tolist(),
            "boot_draws_att_M2_split": bdf.get("att_M2_split", pd.Series()).tolist()}
