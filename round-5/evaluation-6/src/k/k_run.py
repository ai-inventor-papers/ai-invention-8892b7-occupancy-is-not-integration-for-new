#!/usr/bin/env python3
"""STEPS 2-4: K1 (which margin), K3 (field boundary), INFERENCE FIX. Asserts the frozen k13_spec.json hash first.

--synthetic runs the identical code on a SYNTHETIC outcome (Y_strict replaced by NB2 draws from the controls-only
co-primary fit, per fold; K3 from the pooled controls-only fit) with small draw counts, writing to results/smoke/.
"""
from __future__ import annotations

import os
os.environ.update(OPENBLAS_NUM_THREADS="1", OMP_NUM_THREADS="1", MKL_NUM_THREADS="1")
import argparse  # noqa: E402
import json  # noqa: E402
import math  # noqa: E402
import multiprocessing as mp  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402
from concurrent.futures import ProcessPoolExecutor, as_completed  # noqa: E402
from pathlib import Path  # noqa: E402

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from loguru import logger  # noqa: E402
from scipy import stats  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
import k_lib as K  # noqa: E402

logger.remove()
logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
logger.add(K.LOGS / "k_run.log", rotation="30 MB", level="DEBUG")

LABEL = "POST-CONFIRMATION EXPLORATORY"
_W: dict = {}


def _winit(payload: dict) -> None:
    K.set_worker_ram_limit()
    _W.update(payload)


def pool(payload: dict) -> ProcessPoolExecutor:
    return ProcessPoolExecutor(max_workers=K.n_workers(), mp_context=mp.get_context("spawn"), initializer=_winit,
                               initargs=(payload,))


def xv_lpm(fold: str) -> list[str]:
    return ["A_cont", "CT"] + K.controls(fold) + ["log_nep"]


def xv_cnt(fold: str) -> list[str]:
    return ["A_cont", "CT"] + K.controls(fold)


# ============================================================================================ synthetic outcome
def synthesize(s: pd.DataFrame, xc: list[str], fe: str, seed: int) -> pd.DataFrame:
    r = K.ppml_fit(s, "Y_strict", xc, fe, target="CT")
    mu = np.full(len(s), float(s.Y_strict.mean()))
    mu[r["keep"]] = r["mu"]
    rng = np.random.default_rng(seed)
    alpha = 0.5
    y = rng.poisson(rng.gamma(1 / alpha, mu * alpha)).astype(float)
    s = s.copy()
    s["Y_strict"] = y
    s["EST_bin"] = (y >= 3).astype(float)  # smoke only: no year profile is simulated
    return K.add_outcomes(s)


# ============================================================================================ K1
def _boot_draw(args: tuple) -> dict:
    fold, i = args
    s = _W["samples"][fold]
    rng = np.random.default_rng(K.SEED + 3_000_000 + i)
    b = K.cluster_resample(s, rng)
    out = {"fold": fold, "draw": i}
    rt = K.ppml_fit(b, "Y_strict", xv_cnt(fold), "coprimary")
    re = K.ppml_fit(b, "Any", xv_lpm(fold), "coprimary", offset=False)
    sub = b[b.Y_strict >= 1].reset_index(drop=True)
    ri = K.ppml_fit(sub, "Y_strict", xv_cnt(fold), "coprimary")
    out["b_tot"] = None if rt is None else rt["b"]
    out["b_ext"] = None if re is None else re["b"]
    out["b_int"] = None if ri is None else ri["b"]
    return out


def mde_of(spec: dict, kind: str, fold: str):
    m = spec["MDE"]
    if kind == "ext":
        return m["extensive_pp_per_sd"].get(fold, {}).get("MDE80")
    if kind == "int":
        return m["intensive_irr_per_sd"].get(fold, {}).get("MDE80")
    return None


def run_k1(samples: dict, spec: dict, out: Path, boot: int) -> dict:
    rows, per = [], {}
    src = f"{K.rel(out)}/k1_rows.csv"
    for fold, s in samples.items():
        tot = K.ppml_row(s, "Y_strict", xv_cnt(fold), "coprimary")
        lpm = K.lpm_row(s, "Any", xv_lpm(fold), "coprimary")
        lgt = K.logit_row(s, "Any", xv_lpm(fold), "coprimary")
        ll = K.ppml_row(s, "Any", xv_lpm(fold), "coprimary", offset=False)
        sub = s[s.Y_strict >= 1].reset_index(drop=True)
        k1b = K.ppml_row(sub, "Y_strict", xv_cnt(fold), "coprimary",
                         label="conditional on uptake starting; descriptive, subject to selection")
        ladder = {y: K.lpm_row(s, y, xv_lpm(fold), "coprimary") for y in ("Any", "Y_ge3", "Y_ge5", "EST_bin")}
        side_lpm = K.lpm_row(s, "Any", xv_lpm(fold), "primary")
        side_k1b = K.ppml_row(sub, "Y_strict", xv_cnt(fold), "primary")
        per[fold] = {"total": tot, "K1a_LPM": lpm, "K1a_logit": lgt, "K1a_loglink": ll, "K1b": k1b, "ladder": ladder,
                     "side_primary_LPM": side_lpm, "side_primary_K1b": side_k1b}

        def add(test, model, fe, outcome, est, unit, lo, hi, r, base=None, mde=None, note=""):
            rows.append({"test": test, "fold": fold, "model": model, "fe": fe, "outcome": outcome, "estimate": est,
                         "unit": unit, "ci_lo": lo, "ci_hi": hi, "p_crv1": r.get("p_crv1"), "N": r.get("N"),
                         "G": r.get("G"), "base_rate": base, "mde80": mde, "b": r.get("b"), "se": r.get("se"),
                         "sd_A": r.get("sd"), "label": LABEL, "note": note, "source": src})

        add("K1_total", "PPML", "concept+e+d", "Y_strict", tot["irr_per_sd"], "IRR/SD", *tot["ci_irr_per_sd"], tot,
            note="co-primary total (= R0b)")
        add("K1a_LPM", "LPM", "concept+e+d", "Any", lpm["pp_per_sd"], "pp/SD", *lpm["ci_pp_per_sd"], lpm,
            base=lpm["base_rate"], mde=mde_of(spec, "ext", fold),
            note=f"relative to base rate: {lpm['rel_to_base']:.4f}; log(n_entry_papers) as regressor")
        if lgt.get("status") == "ok":
            add("K1a_logit", "FE-logit", "concept+e+d", "Any", lgt["or_per_sd"], "OR/SD", *lgt["ci_or_per_sd"], lgt,
                note=f"concepts dropped (all-0/all-1/singleton): {lgt['concepts_dropped_all0_all1_or_singleton']}")
        else:
            rows.append({"test": "K1a_logit", "fold": fold, "model": "FE-logit", "note": lgt.get("status"),
                         "label": LABEL, "source": src})
        add("K1a_loglink", "PPML (log link, binary)", "concept+e+d", "Any", ll["irr_per_sd"], "ratio of P(Y>=1)/SD",
            *ll["ci_irr_per_sd"], ll, base=lpm["base_rate"])
        add("K1b", "PPML on Y>=1", "concept+e+d", "Y_strict | Y>=1", k1b["irr_per_sd"], "IRR/SD",
            *k1b["ci_irr_per_sd"], k1b, mde=mde_of(spec, "int", fold),
            note="conditional on uptake starting; descriptive, subject to selection")
        for y, r in ladder.items():
            add("K1d_ladder", "LPM", "concept+e+d", y, r["pp_per_sd"], "pp/SD", *r["ci_pp_per_sd"], r,
                base=r["base_rate"], note=f"relative to base rate: {r['rel_to_base']}")
        add("K1e_side_primaryFE", "LPM", "concept x e + d x e", "Any", side_lpm["pp_per_sd"], "pp/SD",
            *side_lpm["ci_pp_per_sd"], side_lpm, base=side_lpm["base_rate"],
            note="underpowered (G < 50)" if side_lpm["G"] < 50 else "side row")
        if side_k1b.get("status") == "ok":
            add("K1e_side_primaryFE", "PPML on Y>=1", "concept x e + d x e", "Y_strict | Y>=1", side_k1b["irr_per_sd"],
                "IRR/SD", *side_k1b["ci_irr_per_sd"], side_k1b,
                note="underpowered (G < 50)" if side_k1b["G"] < 50 else "side row")
        else:
            rows.append({"test": "K1e_side_primaryFE", "fold": fold, "model": "PPML on Y>=1", "fe": "concept x e + d x e",
                         "note": "not estimable", "label": LABEL, "source": src})
    # ---------------- decomposition + cluster bootstrap
    t0 = time.time()
    res = []
    with pool({"samples": samples}) as ex:
        futs = [ex.submit(_boot_draw, (f, i)) for f in samples for i in range(boot)]
        for fu in as_completed(futs):
            res.append(fu.result())
    bd = pd.DataFrame(res)
    bd.to_csv(out / "k1_bootstrap_draws.csv", index=False)
    logger.info(f"K1 bootstrap {len(bd)} draws in {time.time() - t0:.0f}s")
    dec = {"label": LABEL, "boot_draws_requested": boot, "folds": {}}
    for fold in samples:
        p = per[fold]
        sd = p["total"]["sd"]
        bt, be, bi = p["total"]["b"], p["K1a_loglink"]["b"], p["K1b"]["b"]
        d = bd[bd.fold == fold]
        ok = d.dropna(subset=["b_tot", "b_ext", "b_int"])
        sh = ok.b_ext / (ok.b_ext + ok.b_int)
        gap = ok.b_tot - (ok.b_ext + ok.b_int)
        pct = lambda v: [float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))] if len(v) else [None, None]  # noqa: E731
        dec["folds"][fold] = {
            "sd_full": sd, "b_total_sd": bt * sd, "b_ext_sd": be * sd, "b_int_sd": bi * sd,
            "ext_share": be / (be + bi), "gap_sd": (bt - (be + bi)) * sd,
            "ci_b_total_sd": [x * sd for x in pct(ok.b_tot)], "ci_b_ext_sd": [x * sd for x in pct(ok.b_ext)],
            "ci_b_int_sd": [x * sd for x in pct(ok.b_int)], "ci_ext_share": pct(sh), "ci_gap_sd": [x * sd for x in pct(gap)],
            "boot_se_ext_share": float(sh.std()), "boot_se_b_ext_sd": float(ok.b_ext.std() * sd),
            "boot_se_b_int_sd": float(ok.b_int.std() * sd),
            "draws_converged": int(len(ok)), "draws_failed": int(len(d) - len(ok)),
            "failed_share": float((len(d) - len(ok)) / max(len(d), 1)),
            "note": ("share conditions on converged draws" if (len(d) - len(ok)) > 0.05 * max(len(d), 1) else "")}
    # ---------------- IVW
    fl = list(samples)

    def iv(key, f_est, f_se):
        return K.ivw([f_est(per[f]) for f in fl], [f_se(per[f]) for f in fl])

    ivws = {
        "K1a_LPM_pp_per_sd": iv("lpm", lambda p: p["K1a_LPM"]["pp_per_sd"], lambda p: 100 * p["K1a_LPM"]["se"] * p["K1a_LPM"]["sd"]),
        "K1a_loglink_log_per_sd": iv("ll", lambda p: p["K1a_loglink"]["b"] * p["K1a_loglink"]["sd"],
                                     lambda p: p["K1a_loglink"]["se"] * p["K1a_loglink"]["sd"]),
        "K1b_log_irr_per_sd": iv("k1b", lambda p: p["K1b"]["b"] * p["K1b"]["sd"], lambda p: p["K1b"]["se"] * p["K1b"]["sd"]),
        "total_log_irr_per_sd": iv("tot", lambda p: p["total"]["b"] * p["total"]["sd"], lambda p: p["total"]["se"] * p["total"]["sd"]),
        "ext_share": K.ivw([dec["folds"][f]["ext_share"] for f in fl], [dec["folds"][f]["boot_se_ext_share"] for f in fl]),
    }
    if all(per[f]["K1a_logit"].get("status") == "ok" for f in fl):
        ivws["K1a_logit_log_or_per_sd"] = iv("lgt", lambda p: p["K1a_logit"]["b"] * p["K1a_logit"]["sd"],
                                             lambda p: p["K1a_logit"]["se"] * p["K1a_logit"]["sd"])
    ivws["folds_included"] = fl
    dec["ivw"] = ivws
    for key, unit, tr in [("K1a_LPM_pp_per_sd", "pp/SD", lambda x: x), ("K1a_loglink_log_per_sd", "ratio of P(Y>=1)/SD", math.exp),
                          ("K1b_log_irr_per_sd", "IRR/SD", math.exp), ("total_log_irr_per_sd", "IRR/SD", math.exp),
                          ("ext_share", "share", lambda x: x), ("K1a_logit_log_or_per_sd", "OR/SD", math.exp)]:
        if key not in ivws:
            continue
        v = ivws[key]
        rows.append({"test": f"K1f_IVW_{key}", "fold": "IVW", "model": "fixed-effect IVW", "fe": "concept+e+d",
                     "outcome": key, "estimate": tr(v["est"]), "unit": unit, "ci_lo": tr(v["ci"][0]),
                     "ci_hi": tr(v["ci"][1]), "p_crv1": v["p"], "N": None, "G": None, "base_rate": None,
                     "mde80": (spec["MDE"]["extensive_pp_per_sd"]["IVW"]["MDE80"] if key == "K1a_LPM_pp_per_sd" else
                               spec["MDE"]["intensive_irr_per_sd"]["IVW"]["MDE80"] if key == "K1b_log_irr_per_sd" else None),
                     "b": v["est"], "se": v["se"], "label": LABEL,
                     "note": f"Q={v['Q']:.3f} (df {v['Q_df']}, p {v['Q_p']}), I2={v['I2']:.3f}" +
                             (f"; DL random effects {v['random_effects_DL']}" if "random_effects_DL" in v else ""),
                     "source": f"{K.rel(out)}/k1_decomposition.json"})
    for fold in samples:
        d = dec["folds"][fold]
        rows.append({"test": "K1c_decomposition", "fold": fold, "model": "log-link two-part", "fe": "concept+e+d",
                     "outcome": "ext_share", "estimate": d["ext_share"], "unit": "share of (b_ext + b_int)",
                     "ci_lo": d["ci_ext_share"][0], "ci_hi": d["ci_ext_share"][1], "label": LABEL,
                     "note": f"b_total/SD {d['b_total_sd']:.4f}, b_ext/SD {d['b_ext_sd']:.4f}, b_int/SD {d['b_int_sd']:.4f}, "
                             f"gap/SD {d['gap_sd']:.4f}; bootstrap converged {d['draws_converged']}",
                     "source": f"{K.rel(out)}/k1_decomposition.json"})
    dec["per_fold_rows"] = per
    K.dump(K.clean(dec), out / "k1_decomposition.json")
    pd.DataFrame(rows).to_csv(out / "k1_rows.csv", index=False)
    logger.info(f"K1 IVW LPM {ivws['K1a_LPM_pp_per_sd']['est']:.3f} pp/SD {ivws['K1a_LPM_pp_per_sd']['ci']}; "
                f"K1b IRR {math.exp(ivws['K1b_log_irr_per_sd']['est']):.3f}")
    return dec


# ============================================================================================ K3
def crv1_V(r: dict, fes: list[np.ndarray]) -> np.ndarray:
    """Full CRV1 covariance from a vendored ppml.fit result (same construction and small-sample factor)."""
    Xt, mu, y, g = r["Xt"], r["mu"], r["y"], r["cl"]
    Hi = np.linalg.inv(Xt.T @ (Xt * mu[:, None]))
    G = int(g.max()) + 1
    S = np.zeros((G, Xt.shape[1]))
    np.add.at(S, g, Xt * (y - mu)[:, None])
    fk = [np.unique(f[r["keep"]], return_inverse=True)[1] for f in fes]
    adj = K.ssc_adj(len(y), Xt.shape[1], fk, g)
    return adj * Hi @ (S.T @ S) @ Hi


def k3_design(s: pd.DataFrame, gcol: str, groups: list[str]) -> tuple[pd.DataFrame, list[str]]:
    s = s.copy()
    cols = []
    for gname in groups:
        c = "A_g_" + gname.replace("/", "_")
        s[c] = s["A_cont"] * (s[gcol] == gname).astype(float)
        cols.append(c)
    s["A_x_phys"] = s["A_cont"] * (s[gcol] == "Physics/Astro").astype(float)
    return s, cols


def k3_fit(s: pd.DataFrame, gcol: str, groups: list[str]) -> dict | None:
    s2, cols = k3_design(s, gcol, groups)
    xv = cols + ["CT"] + K.CTRL2
    fes = [s2[c].to_numpy() for c in K.fe_cols_for("k3")]
    r = K.ppml_fit(s2, "Y_strict", xv, "k3", target=cols[0])
    if r is None:
        return None
    V = crv1_V(r, fes)
    b = r["coef"]
    kk = len(cols)
    R = np.zeros((kk - 1, len(b)))
    for i in range(1, kk):
        R[i - 1, 0], R[i - 1, i] = 1.0, -1.0
    Rb = R @ b
    W = float(Rb @ np.linalg.solve(R @ V @ R.T, Rb))
    G = r["G"]
    out = {"b": b[:kk].tolist(), "se": np.sqrt(np.diag(V))[:kk].tolist(), "W": W, "df": kk - 1,
           "p_F": float(stats.f.sf(W / (kk - 1), kk - 1, G - 1)), "p_chi2": float(stats.chi2.sf(W, kk - 1)),
           "G": G, "N": r["n"], "keep": r["keep"], "se_check_maxdiff": float(np.max(np.abs(np.sqrt(np.diag(V)) - r["se_all"])))}
    rf = K.ppml_fit(s2, "Y_strict", ["A_cont", "A_x_phys", "CT"] + K.CTRL2, "k3", target="A_x_phys")
    out["contrast"] = None if rf is None else {"b": rf["b"], "se": rf["se"], "t": rf["t"],
                                                "p": float(2 * stats.t.sf(abs(rf["t"]), rf["G"] - 1)), "G": rf["G"],
                                                "N": rf["n"], "b_rest": float(rf["coef"][0]), "se_rest": float(rf["se_all"][0])}
    return out


def _k3_perm(i: int) -> dict:
    s = _W["pooled"]
    rng = np.random.default_rng(K.SEED + 4_000_000 + i)
    cmap = _W["concept_group"]
    perm = dict(zip(cmap.index, rng.permutation(cmap.to_numpy())))
    s = s.copy()
    s["pgroup"] = s.concept_id.map(perm)
    r = k3_fit(s, "pgroup", list(K.GROUPS))
    if r is None:
        return {"draw": i, "W": None, "t_contrast": None}
    return {"draw": i, "W": r["W"], "t_contrast": None if r["contrast"] is None else r["contrast"]["t"]}


def run_k3(pooled: pd.DataFrame, spec: dict, gates: dict, out: Path, perms: int) -> dict:
    src = f"{K.rel(out)}/k3_rows.csv"
    groups = list(K.GROUPS)
    obs = k3_fit(pooled, "origin_group", groups)
    keep = obs["keep"]
    sd = float(pooled.loc[keep, "A_cont"].std())
    G = obs["G"]
    tq = stats.t.ppf(0.975, G - 1)
    ret = pooled[keep]
    rows, per_group = [], {}
    for j, gname in enumerate(groups):
        b, se = obs["b"][j], obs["se"][j]
        rg = ret[ret.origin_group == gname]
        per_group[gname] = {"b": b, "se": se, "irr_per_pooled_sd": math.exp(b * sd),
                            "ci": [math.exp((b - tq * se) * sd), math.exp((b + tq * se) * sd)],
                            "p_crv1": float(2 * stats.t.sf(abs(b / se), G - 1)), "entries": int(len(rg)),
                            "G_group": int(rg.concept_id.nunique()),
                            "descriptive_only": bool(rg.concept_id.nunique() < 30)}
        rows.append({"test": "K3_group", "row": gname, "grouping": "origin (declared)", "estimate": math.exp(b * sd),
                     "unit": "IRR per pooled SD", "ci_lo": per_group[gname]["ci"][0], "ci_hi": per_group[gname]["ci"][1],
                     "p_crv1": per_group[gname]["p_crv1"], "N": int(len(rg)), "G": int(rg.concept_id.nunique()),
                     "p_perm": None, "mde80": None, "label": LABEL, "source": src})
    excluded = [g for g in groups if per_group[g]["descriptive_only"]]
    if excluded:
        keepg = [g for g in groups if g not in excluded]
        obs_w = k3_fit(pooled[pooled.origin_group.isin(keepg)], "origin_group", keepg)
    else:
        obs_w = obs
    # label permutation
    t0 = time.time()
    cg = pooled.drop_duplicates("concept_id").set_index("concept_id").origin_group
    draws = []
    with pool({"pooled": pooled, "concept_group": cg}) as ex:
        for fu in as_completed([ex.submit(_k3_perm, i) for i in range(perms)]):
            draws.append(fu.result())
    dd = pd.DataFrame(draws).sort_values("draw")
    dd.to_csv(out / "k3_perm_draws.csv", index=False)
    Wd = dd.W.dropna().to_numpy()
    td = dd.t_contrast.dropna().to_numpy()
    p_perm_W = (1 + int((Wd >= obs_w["W"]).sum())) / (1 + len(Wd))
    c = obs["contrast"]
    p_perm_c = (1 + int((np.abs(td) >= abs(c["t"])).sum())) / (1 + len(td))
    logger.info(f"K3 perms {len(dd)} in {time.time() - t0:.0f}s; W {obs_w['W']:.3f} p_F {obs_w['p_F']:.4f} p_perm {p_perm_W:.4f}")
    mde = spec["MDE"]["k3_phys_ratio"]["MDE80_ratio"]
    rows.append({"test": "K3_wald_equality", "row": "3 groups (origin)", "grouping": "origin (declared)",
                 "estimate": obs_w["W"], "unit": f"Wald chi2({obs_w['df']}); p from F({obs_w['df']}, G-1)",
                 "ci_lo": None, "ci_hi": None, "p_crv1": obs_w["p_F"], "N": obs_w["N"], "G": obs_w["G"],
                 "p_perm": p_perm_W, "mde80": None, "label": LABEL,
                 "note": f"chi2 p {obs_w['p_chi2']:.4g}; perm draws converged {len(Wd)}; excluded groups: {excluded}",
                 "source": src})
    ratio = math.exp(c["b"] * sd)
    tqc = stats.t.ppf(0.975, c["G"] - 1)
    rows.append({"test": "K3_phys_contrast", "row": "Physics/Astro minus rest", "grouping": "origin (declared)",
                 "estimate": ratio, "unit": "ratio of IRR/SD (phys / rest)", "ci_lo": math.exp((c["b"] - tqc * c["se"]) * sd),
                 "ci_hi": math.exp((c["b"] + tqc * c["se"]) * sd), "p_crv1": c["p"], "N": c["N"], "G": c["G"],
                 "p_perm": p_perm_c, "mde80": mde, "label": LABEL,
                 "note": f"rest IRR/SD {math.exp(c['b_rest'] * sd):.4f}; MDE80 = ratio at which power reaches 0.80",
                 "source": src})
    # secondary: host-field grouping
    sec = k3_fit(pooled, "host_group", groups)
    sec_rows = {}
    if sec is not None:
        ret2 = pooled[sec["keep"]]
        sd2 = float(ret2.A_cont.std())
        tq2 = stats.t.ppf(0.975, sec["G"] - 1)
        for j, gname in enumerate(groups):
            b, se = sec["b"][j], sec["se"][j]
            rg = ret2[ret2.host_group == gname]
            sec_rows[gname] = {"irr": math.exp(b * sd2), "ci": [math.exp((b - tq2 * se) * sd2), math.exp((b + tq2 * se) * sd2)],
                               "p_crv1": float(2 * stats.t.sf(abs(b / se), sec["G"] - 1)), "entries": int(len(rg)),
                               "G_group": int(rg.concept_id.nunique())}
            rows.append({"test": "K3_SECONDARY_host_group", "row": gname, "grouping": "host field (SECONDARY)",
                         "estimate": sec_rows[gname]["irr"], "unit": "IRR per pooled SD", "ci_lo": sec_rows[gname]["ci"][0],
                         "ci_hi": sec_rows[gname]["ci"][1], "p_crv1": sec_rows[gname]["p_crv1"], "N": len(rg),
                         "G": sec_rows[gname]["G_group"], "label": LABEL + " / SECONDARY", "source": src})
        rows.append({"test": "K3_SECONDARY_wald_equality", "row": "3 groups (host)", "grouping": "host field (SECONDARY)",
                     "estimate": sec["W"], "unit": "Wald chi2(2); p from F(2, G-1)", "p_crv1": sec["p_F"], "N": sec["N"],
                     "G": sec["G"], "label": LABEL + " / SECONDARY", "note": f"contrast p {sec['contrast']['p'] if sec['contrast'] else None}",
                     "source": src})
    m = gates["R0b"]["MESH"]
    rows.append({"test": "K3_MESH_reference", "row": "MeSH biomedicine->biomedicine (R2)", "grouping": "separate population",
                 "estimate": m["irr_sd"], "unit": "IRR/SD (own SD)", "ci_lo": m["ci"][0], "ci_hi": m["ci"][1],
                 "p_crv1": m["p_crv1"], "N": m["N"], "G": m["G"], "label": "REFERENCE (not pooled into the test)",
                 "source": "results/gates.json (R0b MESH)"})
    k3 = {"label": LABEL, "groups": per_group, "pooled_sd": sd, "N": obs["N"], "G": G,
          "wald": {k: obs_w[k] for k in ("W", "df", "p_F", "p_chi2", "N", "G")}, "p_perm_wald": p_perm_W,
          "perm_draws_converged": int(len(Wd)), "perm_draws_requested": perms, "excluded_groups": excluded,
          "contrast": {**c, "ratio": ratio, "ci": None},
          "p_perm_contrast": p_perm_c, "mde80_ratio": mde, "secondary_host": {"groups": sec_rows,
          "wald": None if sec is None else {k: sec[k] for k in ("W", "df", "p_F", "p_chi2")}},
          "se_check_maxdiff": obs["se_check_maxdiff"]}
    crow = [r for r in rows if r["test"] == "K3_phys_contrast"][0]
    k3["contrast"]["ci"] = [crow["ci_lo"], crow["ci_hi"]]
    K.dump(K.clean(k3), out / "k3_results.json")
    pd.DataFrame(rows).to_csv(out / "k3_rows.csv", index=False)
    return k3


# ============================================================================================ INFERENCE
def _inf_draw(i: int) -> dict:
    out = {"draw": i}
    for fold, d in _W["folds"].items():
        s = d["s"]
        A = d["A"]
        rng = np.random.default_rng(K.SEED + i)
        Ap = K.within_concept_perm(A, d["grp"], rng)
        rng2 = np.random.default_rng(K.SEED + 1_000_000 + i)
        Afl = d["fl_fit"] + K.within_concept_perm(d["fl_res"], d["grp"], rng2)
        Afl_l = d["fl_fit_l"] + K.within_concept_perm(d["fl_res_l"], d["grp"], rng2)
        for tag, Ax in (("plain", Ap), ("fl", Afl)):
            r = K.ppml_fit(s, "Y_strict", d["xv"], "coprimary", A=Ax)
            out[f"{fold}_cnt_{tag}_t"] = None if r is None else r["t"]
            out[f"{fold}_cnt_{tag}_b"] = None if r is None else r["b"]
            out[f"{fold}_cnt_{tag}_se"] = None if r is None else r["se"]
        eng: K.LPM = d["eng"]
        for tag, Ax in (("plain", Ap), ("fl", Afl_l)):
            Xt = d["Xt_l"].copy()
            Xt[:, 0] = eng.demean(Ax[eng.keep][:, None])[:, 0]
            yfull = s["Any"].to_numpy(float)
            r = eng.fit(yfull, None, Xt=Xt)
            out[f"{fold}_lpm_{tag}_t"] = float(r["coef"][0] / r["se"][0])
            out[f"{fold}_lpm_{tag}_b"] = float(r["coef"][0])
            out[f"{fold}_lpm_{tag}_se"] = float(r["se"][0])
    return out


def run_inference(samples: dict, out: Path, draws: int, wild_reps: int) -> dict:
    payload, obs = {"folds": {}}, {}
    for fold, s in samples.items():
        xv, xl = xv_cnt(fold), xv_lpm(fold)
        fes = [s[c].to_numpy() for c in K.fe_cols_for("coprimary")]
        eng = K.LPM(fes, s.concept_id.to_numpy())
        Xt_l = eng.demean(s[xl].to_numpy(float)[eng.keep])
        fl_fit, fl_res = K.freedman_lane_parts(s, xv, "coprimary")
        fl_fit_l, fl_res_l = K.freedman_lane_parts(s, xl, "coprimary")
        payload["folds"][fold] = {"s": s, "A": s.A_cont.to_numpy(float), "grp": pd.factorize(s.concept_id)[0],
                                  "xv": xv, "eng": eng, "Xt_l": Xt_l, "fl_fit": fl_fit, "fl_res": fl_res,
                                  "fl_fit_l": fl_fit_l, "fl_res_l": fl_res_l}
        rc = K.ppml_fit(s, "Y_strict", xv, "coprimary")
        rl = eng.fit(s["Any"].to_numpy(float), None, Xt=Xt_l)
        sd_c = float(s.loc[rc["keep"], "A_cont"].std())
        sd_l = float(s.loc[eng.keep, "A_cont"].std())
        obs[fold] = {"cnt": {"t": rc["t"], "b": rc["b"], "se": rc["se"], "G": rc["G"], "sd": sd_c,
                             "p_crv1": float(2 * stats.t.sf(abs(rc["t"]), rc["G"] - 1))},
                     "lpm": {"t": float(rl["coef"][0] / rl["se"][0]), "b": float(rl["coef"][0]), "se": float(rl["se"][0]),
                             "G": rl["G"], "sd": sd_l, "p_crv1": float(2 * stats.t.sf(abs(rl["coef"][0] / rl["se"][0]), rl["G"] - 1))}}
        # wild cluster score bootstraps (restricted fit; Webb 9999 headline, Rademacher 999 check)
        scc = K.score_components_ppml(s, "Y_strict", xv, "coprimary")
        scl = K.score_components_lpm(s, "Any", xl, "coprimary")
        k = K.FOLDS.index(fold)
        obs[fold]["cnt"]["wcr_webb"] = K.wild_score_test_webb(scc, np.random.default_rng(K.SEED + 2_000_000 + k), wild_reps, "webb")
        obs[fold]["cnt"]["wcr_rademacher_check"] = K.wild_score_test_webb(scc, np.random.default_rng(K.SEED + 2_100_000 + k), 999, "rademacher")
        obs[fold]["lpm"]["wcr_webb"] = K.wild_score_test_webb(scl, np.random.default_rng(K.SEED + 2_200_000 + k), wild_reps, "webb")
        obs[fold]["lpm"]["wcr_rademacher_check"] = K.wild_score_test_webb(scl, np.random.default_rng(K.SEED + 2_300_000 + k), 999, "rademacher")
    t0 = time.time()
    res = []
    with pool(payload) as ex:
        for j, fu in enumerate(as_completed([ex.submit(_inf_draw, i) for i in range(draws)])):
            res.append(fu.result())
            if (j + 1) % 500 == 0:
                logger.info(f"inference draws {j + 1}/{draws} ({time.time() - t0:.0f}s)")
    dd = pd.DataFrame(res).sort_values("draw").reset_index(drop=True)
    dd.to_csv(out / "inference_draws.csv", index=False)
    rows, summ = [], {"label": LABEL, "draws": draws, "wild_reps": wild_reps, "rows": {}}
    src = f"{K.rel(out)}/inference_rows.csv"

    def put(test, fold, row, value, note=""):
        rows.append({"test": test, "fold": fold, "row": row, "value": value, "note": note, "source": src})

    for fold in samples:
        for mdl, row in (("cnt", "coprimary_A_count"), ("lpm", "K1a_LPM")):
            o = obs[fold][mdl]
            ent = {"t_obs": o["t"], "p_crv1": o["p_crv1"], "G": o["G"]}
            for tag, name in (("plain", "rand_t"), ("fl", "freedman_lane")):
                ts = dd[f"{fold}_{mdl}_{tag}_t"].to_numpy(dtype=float)
                rp = K.rand_p(o["t"], ts)
                ent[f"p_{name}"], ent[f"mc_se_{name}"], ent[f"converged_{name}"] = rp["p"], rp["mc_se"], rp["draws_converged"]
                tsf = ts[np.isfinite(ts)]
                pcr = 2 * stats.t.sf(np.abs(tsf), o["G"] - 1)
                ent[f"crv1_null_rejection_{name}"] = float((pcr < 0.05).mean())
                ent[f"z_sd_null_{name}"] = float(tsf.std())
                ent[f"z_mean_null_{name}"] = float(tsf.mean())
            ent["p_wcr_webb"] = (o["wcr_webb"] or {}).get("p")
            ent["p_wcr_rademacher_check"] = (o["wcr_rademacher_check"] or {}).get("p")
            summ["rows"][f"{fold}.{row}"] = ent
            put("p_crv1", fold, row, o["p_crv1"])
            put("p_rand_t", fold, row, ent["p_rand_t"], "headline p (declared)")
            put("mc_se_rand_t", fold, row, ent["mc_se_rand_t"])
            put("p_freedman_lane", fold, row, ent["p_freedman_lane"])
            put("mc_se_freedman_lane", fold, row, ent["mc_se_freedman_lane"])
            put("p_wcr_webb", fold, row, ent["p_wcr_webb"], f"{wild_reps} Webb draws")
            put("p_wcr_rademacher_check", fold, row, ent["p_wcr_rademacher_check"], "999 Rademacher draws")
            put("crv1_null_rejection", fold, row, ent["crv1_null_rejection_rand_t"], "share of plain-shuffle draws with CRV1 p<0.05")
            put("z_sd_null", fold, row, ent["z_sd_null_rand_t"])
            put("crv1_null_rejection_fl", fold, row, ent["crv1_null_rejection_freedman_lane"])
            put("z_sd_null_fl", fold, row, ent["z_sd_null_freedman_lane"])
            put("draws_converged", fold, row, ent["converged_rand_t"])
    # IVW pooled randomization (same draw index across folds)
    for mdl, row in (("cnt", "coprimary_A_count"), ("lpm", "K1a_LPM")):
        fl = list(samples)
        b = np.array([obs[f][mdl]["b"] * obs[f][mdl]["sd"] for f in fl])
        se = np.array([obs[f][mdl]["se"] * obs[f][mdl]["sd"] for f in fl])
        w = 1 / se ** 2
        z_obs = float((w * b).sum() / math.sqrt(w.sum()))
        ent = {"z_obs": z_obs, "p_normal": float(2 * stats.norm.sf(abs(z_obs)))}
        for tag, name in (("plain", "rand_t"), ("fl", "freedman_lane")):
            B = np.column_stack([dd[f"{f}_{mdl}_{tag}_b"].to_numpy(float) * obs[f][mdl]["sd"] for f in fl])
            S = np.column_stack([dd[f"{f}_{mdl}_{tag}_se"].to_numpy(float) * obs[f][mdl]["sd"] for f in fl])
            ok = np.all(np.isfinite(B) & np.isfinite(S), axis=1)
            W_ = 1 / S[ok] ** 2
            zs = (W_ * B[ok]).sum(1) / np.sqrt(W_.sum(1))
            rp = K.rand_p(z_obs, zs)
            ent[f"p_{name}"], ent[f"mc_se_{name}"], ent[f"converged_{name}"] = rp["p"], rp["mc_se"], rp["draws_converged"]
            ent[f"z_sd_null_{name}"] = float(zs.std())
            ent[f"normal_null_rejection_{name}"] = float((np.abs(zs) > 1.96).mean())
        summ["rows"][f"IVW.{row}"] = ent
        put("p_normal", "IVW", row, ent["p_normal"])
        put("p_rand_t", "IVW", row, ent["p_rand_t"], "same draw index in every fold")
        put("mc_se_rand_t", "IVW", row, ent["mc_se_rand_t"])
        put("p_freedman_lane", "IVW", row, ent["p_freedman_lane"])
        put("z_sd_null", "IVW", row, ent["z_sd_null_rand_t"])
        put("crv1_null_rejection", "IVW", row, ent["normal_null_rejection_rand_t"], "share of draws with |z_IVW*| > 1.96")
        put("p_wcr_webb", "IVW", row, None, "not defined for the pooled z (per-fold wild p reported)")
    K.dump(K.clean(summ), out / "inference_summary.json")
    pd.DataFrame(rows).to_csv(out / "inference_rows.csv", index=False)
    logger.info(f"inference done in {time.time() - t0:.0f}s: " +
                "; ".join(f"{k} p_rand {v.get('p_rand_t'):.4f}" for k, v in summ["rows"].items()))
    return summ


@logger.catch(reraise=True)
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", default="all", choices=["k1", "k3", "inference", "all"])
    ap.add_argument("--synthetic", action="store_true")
    a = ap.parse_args()
    K.set_main_ram_limit()
    h = K.assert_spec_hash()
    spec = json.loads(K.SPEC_PATH.read_text())
    gates = json.loads((K.RESULTS / "gates.json").read_text())
    logger.info(f"spec hash OK {h[:16]}; synthetic={a.synthetic}")
    samples = {f: K.load_fold(f) for f in K.FOLDS}
    pooled = K.load_pooled_k3()
    if a.synthetic:
        out = K.RESULTS / "smoke"
        samples = {f: synthesize(s, ["CT"] + K.controls(f), "coprimary", 99 + i) for i, (f, s) in enumerate(samples.items())}
        pooled = synthesize(pooled, ["CT"] + K.CTRL2, "k3", 7)
        boot, perms, draws, wild = 24, 24, 24, 199
    else:
        out = K.RESULTS
        boot = spec["K1"]["decomposition"]["bootstrap"]["draws"]
        perms = spec["K3"]["perm"]["draws"]
        draws = spec["INFERENCE"]["rand_t"]["draws"]
        wild = spec["INFERENCE"]["wcr_webb"]["draws"]
    out.mkdir(parents=True, exist_ok=True)
    fp = gates["fold_pass"]
    failed = [f for f in K.FOLDS if not fp.get(f)]
    if failed:
        logger.warning(f"gate-failed folds (NOT RUN): {failed}")
        samples = {f: s for f, s in samples.items() if f not in failed}
    status = {}
    for stage, fn in (("k1", lambda: run_k1(samples, spec, out, boot)),
                      ("k3", lambda: run_k3(pooled, spec, gates, out, perms)),
                      ("inference", lambda: run_inference(samples, out, draws, wild))):
        if a.stage not in (stage, "all"):
            continue
        t0 = time.time()
        try:
            fn()
            status[stage] = {"status": "RUN", "seconds": round(time.time() - t0, 1)}
        except (np.linalg.LinAlgError, ValueError, KeyError, RuntimeError, TypeError, ZeroDivisionError) as ex:
            logger.exception(f"stage {stage} broke")
            status[stage] = {"status": "NOT RUN", "error": repr(ex)}
    prev = {}
    sp = out / "stage_status.json"
    if sp.exists():
        prev = json.loads(sp.read_text())
    prev.update(status)
    K.dump(prev, sp)
    logger.info(f"stage status: {status}")


if __name__ == "__main__":
    main()
