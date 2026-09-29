#!/usr/bin/env python3
"""STEP 0 gates (R0a-R0e) and STEP 1 freeze (samples, MDE simulations from controls-only fits, k13_spec.json + sha256).

No K coefficient (A_cont on any K outcome / subsample / interaction) is computed here. MDE simulations use
controls-only fits (A_cont excluded) and simulated outcomes only. The R0b/R0c gates re-fit the ALREADY-PUBLISHED
co-primary count and EST_bin rows, which are known numbers.
"""
from __future__ import annotations

import os
os.environ.update(OPENBLAS_NUM_THREADS="1", OMP_NUM_THREADS="1", MKL_NUM_THREADS="1")
import argparse
import json
import math
import multiprocessing as mp
import subprocess
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from loguru import logger
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parent))
import k_lib as K  # noqa: E402

logger.remove()
logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
logger.add(K.LOGS / "freeze.log", rotation="30 MB", level="DEBUG")

LOOP = K.WS.parents[2]
E2 = LOOP / "round-4" / "." / "gen_art_evaluation_2"
X9 = LOOP / "round-4" / "." / "gen_art_experiment_9"
LOCK = E2 / "d2" / "results" / "HELDOUT_OPENED.lock"
CONF = E2 / "d2" / "results" / "heldout_confirmation.json"
CONF_SHA = "4100e3cf849feabdc7fcf90ecd7deb39afc98661ab231e60286b17e25694b3d6"
R0B_TARGET = {"SCREEN": (1.300, 1.164, 1.452, 1544, 140), "HELDOUT": (1.187, 1.057, 1.335, 972, 74),
              "MESH": (1.233, 1.117, 1.361, 2171, 160)}

DECISION_RULES_VERBATIM = {
    "K1": ("EXTENSIVE if the IVW extensive-margin effect per SD has a 95% CI excluding 0. INTENSIVE-ONLY if the "
           "extensive CI includes 0 and the intensive IRR CI excludes 1; the paper's claim is then restated as "
           "'host-leaning entries scale uptake that starts for other reasons'. BOTH if both CIs exclude the null. "
           "UNRESOLVED otherwise, with MDEs stated."),
    "K1_clarification_added_at_freeze_not_a_change": (
        "EXTENSIVE applies when the extensive CI excludes 0 and the intensive CI includes 1. The extensive quantity "
        "is the K1a-LPM IVW row. The K1a-loglink and FE-logit rows are corroborating. If the verdict holds under the "
        "CRV1 CI but the IVW randomization-t p > 0.05, the verdict text carries '(not size-robust)'."),
    "K3": ("a FIELD BOUNDARY is stated only if the equality Wald test of the pre-declared groups rejects at 0.05 AND "
           "one group's CI includes 1. Otherwise: 'no detectable field boundary; the physics screen null is within "
           "sampling variation', with the MDE."),
    "K3_clarification_added_at_freeze_not_a_change": (
        "the Wald p used is the CRV1 one, and the label-permutation p is reported beside it. If they disagree at "
        "0.05, the verdict carries '(not size-robust)'."),
    "INFERENCE": ("if the held-out randomization-t p exceeds 0.05, the held-out sentence reads 'borderline under "
                  "size-correct inference', and the headline leans on the MeSH and IVW rows, reported with the same "
                  "procedure."),
    "BREAKAGE": "If a K-test breaks, it is reported as NOT RUN, and nothing is refitted after outcomes are seen.",
}


# ============================================================================================ GATES
def gate_r0a() -> dict:
    gh = json.loads((E2 / "results" / "gate_hashes.json").read_text())
    files = []
    for f in gh["files"]:
        if f["kind"] == "code" and f["path"].startswith("d2/src/"):
            p = K.WS / f["path"]
            got = K.sha256_file(p)
            files.append({"path": f["path"], "want": f["want"], "got": got, "match": got == f["want"]})
    for name in ("models.py", "ppml.py", "config.py"):
        a, b = K.sha256_file(K.WS / "d2" / "src" / name), K.sha256_file(K.WS / "mesh" / "vendor" / name)
        files.append({"path": f"mesh/vendor/{name} == d2/src/{name}", "want": a, "got": b, "match": a == b})
    conf = K.sha256_file(CONF)
    lock_before = {"sha256": K.sha256_file(LOCK), "mtime": LOCK.stat().st_mtime}
    return {"files": files, "heldout_confirmation_sha256": conf, "heldout_confirmation_match": conf == CONF_SHA,
            "lock_before": lock_before, "pass": all(f["match"] for f in files) and conf == CONF_SHA}


def gate_r0b(samples: dict) -> dict:
    out = {}
    for fold, s in samples.items():
        ctrl = K.controls(fold)
        r = K.models.fit_one(s, "Y_strict", ["A_cont", "CT"] + ctrl, "secondary")
        irr, (lo, hi) = r["irr_sd"]["A_cont"], r["ci_irr_sd"]["A_cont"]
        t = R0B_TARGET[fold]
        ok = (round(irr, 3) == t[0] and round(lo, 3) == t[1] and round(hi, 3) == t[2] and r["n_retained"] == t[3]
              and r["G"] == t[4])
        out[fold] = {"irr_sd": irr, "ci": [lo, hi], "N": r["n_retained"], "G": r["G"], "b": r["coef"]["A_cont"],
                     "se": r["se"]["A_cont"], "sd_retained": r["sd_retained"]["A_cont"], "p_crv1": r["p"]["A_cont"],
                     "target": {"irr_sd": t[0], "ci": [t[1], t[2]], "N": t[3], "G": t[4]}, "pass": bool(ok)}
    return out


def gate_r0c(samples: dict) -> dict:
    s = samples["HELDOUT"]
    lp = K.models.lpm_fe(s, "EST_bin", ["A_cont", "CT"] + K.CTRL2, "secondary")
    r = K.ppml_fit(s, "Y_strict", ["A_cont", "CT"] + K.CTRL2, "coprimary")
    ok = (abs(lp["coef"]["A_cont"] - 0.476) < 5e-4 and abs(lp["p"]["A_cont"] - 0.165) < 5e-4
          and abs(r["t"] - 2.9326) < 5e-4)
    return {"heldout_EST_bin_LPM_secondary": {"coef": lp["coef"]["A_cont"], "p": lp["p"]["A_cont"], "n": lp["n"],
                                              "target": {"coef": 0.476, "p": 0.165}},
            "heldout_coprimary_z": {"z": r["t"], "target": 2.9326}, "pass": bool(ok)}


def gate_r0d() -> dict:
    t0 = time.time()
    p = subprocess.run([sys.executable, "-m", "pytest", "-q"], cwd=K.WS / "d2", capture_output=True, text=True,
                       timeout=900)
    tail = (p.stdout or "").strip().splitlines()[-3:]
    return {"returncode": p.returncode, "tail": tail, "seconds": round(time.time() - t0, 1), "pass": p.returncode == 0}


def gate_r0e(samples: dict) -> dict:
    out = {}
    for fold, s in samples.items():
        ctrl = K.controls(fold)
        r = K.ppml_fit(s, "Y_strict", ["A_cont", "CT"] + ctrl, "coprimary")
        y = s.loc[r["keep"], "Y_strict"].astype(float)
        out[fold] = {"N_retained_coprimary": int(len(y)), "share_zero": float((y == 0).mean()),
                     "P_Y_ge1": float((y >= 1).mean()), "P_Y_ge3": float((y >= 3).mean()),
                     "P_Y_ge5": float((y >= 5).mean()), "EST_bin": float(s.loc[r["keep"], "EST_bin"].mean()),
                     "q50": float(y.quantile(0.5)), "q90": float(y.quantile(0.9)), "q99": float(y.quantile(0.99)),
                     "max": float(y.max()), "mean": float(y.mean()),
                     "N_input": int(len(s)), "share_zero_input": float((s.Y_strict == 0).mean())}
    out["strategy_checks"] = {
        "about_50pct_zeros": {f: out[f]["share_zero"] for f in samples},
        "max_290": {f: out[f]["max"] for f in samples},
        "note": "the strategy's 'max 290' refers to the screen fold; held-out and MeSH maxima are reported as found"}
    return out


# ============================================================================================ SAMPLES
def sample_sizes(samples: dict, pooled: pd.DataFrame) -> dict:
    out = {}
    for fold, s in samples.items():
        fes = [s[c].to_numpy() for c in K.fe_cols_for("coprimary")]
        keep = K.prune_singletons(fes)
        sub = s[s.Y_strict >= 1]
        fes_p = [s[c].to_numpy() for c in K.fe_cols_for("primary")]
        keep_p = K.prune_singletons(fes_p)
        out[fold] = {"N_input": int(len(s)), "concepts_input": int(s.concept_id.nunique()),
                     "K1a_LPM_coprimary_N": int(keep.sum()), "K1a_LPM_coprimary_G": int(s.loc[keep, "concept_id"].nunique()),
                     "K1a_LPM_primary_N": int(keep_p.sum()), "K1a_LPM_primary_G": int(s.loc[keep_p, "concept_id"].nunique()),
                     "K1b_subsample_Y_ge1_N_input": int(len(sub)), "K1b_subsample_concepts": int(sub.concept_id.nunique())}
    fes = [pooled[c].to_numpy() for c in K.fe_cols_for("k3")]
    keep = K.prune_singletons(fes)
    out["K3_POOLED"] = {"N_input": int(len(pooled)), "concepts_input": int(pooled.concept_id.nunique()),
                        "N_singleton_pruned": int(keep.sum()),
                        "concepts_by_origin_group": pooled.groupby("origin_group").concept_id.nunique().to_dict(),
                        "entries_by_origin_group": pooled.origin_group.value_counts().to_dict(),
                        "concepts_by_host_group": pooled.groupby("host_group").concept_id.nunique().to_dict(),
                        "entries_by_host_group": pooled.host_group.value_counts().to_dict(),
                        "origin_group_constant_within_concept": bool(pooled.groupby("concept_id").origin_group.nunique().max() == 1)}
    return out


# ============================================================================================ MDE
_W: dict = {}


def _winit(payload: dict) -> None:
    K.set_worker_ram_limit()
    _W.update(payload)


def _mde_ext_rep(args: tuple) -> tuple:
    fold, delta_pp, rep = args
    d = _W[fold]
    rng = np.random.default_rng(K.SEED + 7_000_000 + rep * 101 + int(delta_pp * 10))
    p = np.clip(d["p0"] + delta_pp / 100 * d["zA"], 0, 1)
    ysim = (rng.random(len(p)) < p).astype(float)
    eng: K.LPM = d["eng"]
    yfull = np.zeros(len(eng.keep))
    yfull[eng.keep] = ysim
    r = eng.fit(yfull, None, Xt=d["Xt"])
    b, se = r["coef"][0], r["se"][0]
    pv = 2 * stats.t.sf(abs(b / se), r["G"] - 1)
    return fold, delta_pp, rep, bool(pv < 0.05 and (b > 0 if delta_pp > 0 else True)), float(se * d["sdA"])


def _nb2_trunc(rng, m, alpha):
    """Zero-truncated NB2 draws (redraw zeros) with NB mean m and dispersion alpha."""
    if alpha <= 1e-8:
        y = rng.poisson(m).astype(float)
    else:
        lam = rng.gamma(1 / alpha, m * alpha)
        y = rng.poisson(lam).astype(float)
    for _ in range(200):
        z = y == 0
        if not z.any():
            break
        if alpha <= 1e-8:
            y[z] = rng.poisson(m[z])
        else:
            y[z] = rng.poisson(rng.gamma(1 / alpha, m[z] * alpha))
    y[y == 0] = 1.0
    return y


def _mde_int_rep(args: tuple) -> tuple:
    fold, irr, rep = args
    d = _W[fold + "_int"]
    rng = np.random.default_rng(K.SEED + 8_000_000 + rep * 101 + int(irr * 1000))
    m = d["mu0"] * irr ** d["zA"]
    ysim = _nb2_trunc(rng, m, d["alpha"])
    s = d["s"]
    r = K.ppml_fit(s, "Y_strict", d["xvars"], "coprimary", yv=ysim)
    if r is None:
        return fold, irr, rep, None, None
    pv = 2 * stats.t.sf(abs(r["t"]), r["G"] - 1)
    return fold, irr, rep, bool(pv < 0.05 and (r["b"] > 0 if irr > 1 else True)), float(r["se"] * d["sdA"])


def _mde_k3_rep(args: tuple) -> tuple:
    ratio, rep = args
    d = _W["k3"]
    rng = np.random.default_rng(K.SEED + 9_000_000 + rep * 101 + int(ratio * 1000))
    m = d["mu0"] * np.exp(np.log(ratio) * d["zA"] * d["phys"])
    if d["alpha"] <= 1e-8:
        ysim = rng.poisson(m).astype(float)
    else:
        ysim = rng.poisson(rng.gamma(1 / d["alpha"], m * d["alpha"])).astype(float)
    r = K.ppml_fit(d["s"], "Y_strict", d["xvars"], "k3", target="A_x_phys", yv=ysim)
    if r is None:
        return ratio, rep, None
    pv = 2 * stats.t.sf(abs(r["t"]), r["G"] - 1)
    return ratio, rep, bool(pv < 0.05 and (r["b"] < 0 if ratio < 1 else True))


def pearson_alpha(y: np.ndarray, mu: np.ndarray, k: int) -> float:
    """NB2 dispersion by method of moments on Pearson residuals: E[(y-mu)^2] = mu + alpha mu^2."""
    a = float(np.sum(((y - mu) ** 2 - y) / mu ** 2) / max(len(y) - k, 1))
    return max(a, 0.0)


def build_mde_payload(samples: dict, pooled: pd.DataFrame) -> tuple[dict, dict]:
    payload, meta = {}, {}
    for fold, s in samples.items():
        ctrl = K.controls(fold)
        # extensive: controls-only LPM (CT + controls + log_nep; NO A_cont), fitted p clipped to [0.01, 0.99]
        xc = ["CT"] + ctrl + ["log_nep"]
        fes = [s[c].to_numpy() for c in K.fe_cols_for("coprimary")]
        eng = K.LPM(fes, s.concept_id.to_numpy())
        r0 = eng.fit(s["Any"].to_numpy(float), s[xc].to_numpy(float))
        yk = s["Any"].to_numpy(float)[eng.keep]
        p0 = np.clip(yk - r0["resid"] + 0 * yk, 0.01, 0.99)  # fitted = y - residual (FE included)
        A = s["A_cont"].to_numpy(float)[eng.keep]
        zA = (A - A.mean()) / A.std(ddof=1)
        Xt = eng.demean(s[["A_cont"] + xc].to_numpy(float)[eng.keep])
        payload[fold] = {"eng": eng, "p0": p0, "zA": zA, "Xt": Xt, "sdA": float(A.std(ddof=1))}
        # intensive: controls-only PPML on Y >= 1 (offset), NB2 alpha from Pearson residuals
        sub = s[s.Y_strict >= 1].reset_index(drop=True)
        rc = K.ppml_fit(sub, "Y_strict", ["CT"] + ctrl, "coprimary", target="CT")
        keep = rc["keep"]
        sk = sub[keep].reset_index(drop=True)
        mu0 = rc["mu"]
        alpha = pearson_alpha(rc["y"], mu0, len(ctrl) + 1)
        Ak = sk["A_cont"].to_numpy(float)
        payload[fold + "_int"] = {"s": sk, "mu0": mu0, "zA": (Ak - Ak.mean()) / Ak.std(ddof=1), "alpha": alpha,
                                  "xvars": ["A_cont", "CT"] + ctrl, "sdA": float(Ak.std(ddof=1))}
        meta[fold] = {"ext_base_rate": float(yk.mean()), "ext_N": int(eng.n), "ext_G": int(eng.G),
                      "int_N": int(len(sk)), "int_G": int(rc["G"]), "int_nb2_alpha": alpha}
    # K3 contrast: no-interaction PPML controls fit (A_cont enters the DGP only through the simulated interaction;
    # the baseline mean comes from a controls-only fit, so no K3 coefficient is estimated here)
    xc = ["CT"] + K.CTRL2
    rc = K.ppml_fit(pooled, "Y_strict", xc, "k3", target="CT")
    sk = pooled[rc["keep"]].reset_index(drop=True).copy()
    Ak = sk["A_cont"].to_numpy(float)
    phys = (sk.origin_group == "Physics/Astro").to_numpy(float)
    sk["A_x_phys"] = Ak * phys
    payload["k3"] = {"s": sk, "mu0": rc["mu"], "zA": (Ak - Ak.mean()) / Ak.std(ddof=1), "phys": phys,
                     "alpha": pearson_alpha(rc["y"], rc["mu"], len(xc)), "xvars": ["A_cont", "A_x_phys"] + xc}
    meta["K3"] = {"N": int(len(sk)), "G": int(rc["G"]), "nb2_alpha": payload["k3"]["alpha"]}
    return payload, meta


def interp_mde(grid: list[float], power: list[float], null: float, target: float = 0.8) -> float | None:
    """Smallest effect (moving away from the null) at which interpolated power reaches 0.80."""
    pts = sorted(zip(grid, power), key=lambda t: abs(t[0] - null))
    for (x0, p0), (x1, p1) in zip(pts, pts[1:]):
        if p0 < target <= p1:
            return float(x0 + (target - p0) * (x1 - x0) / (p1 - p0))
        if p0 >= target and x0 == pts[0][0]:
            return float(x0)
    return None


def run_mde(samples: dict, pooled: pd.DataFrame, reps: int) -> dict:
    payload, meta = build_mde_payload(samples, pooled)
    ext_grid = [0, 1, 2, 3, 4, 5, 7.5, 10]
    int_grid = [1.00, 1.05, 1.10, 1.15, 1.20, 1.30, 1.40]
    k3_grid = [0.70, 0.75, 0.80, 0.85, 0.90, 0.95, 1.00]
    jobs_ext = [(f, d, r) for f in samples for d in ext_grid for r in range(reps)]
    jobs_int = [(f, i, r) for f in samples for i in int_grid for r in range(reps)]
    jobs_k3 = [(q, r) for q in k3_grid for r in range(reps)]
    res_ext, res_int, res_k3 = [], [], []
    t0 = time.time()
    with ProcessPoolExecutor(max_workers=K.n_workers(), mp_context=mp.get_context("spawn"), initializer=_winit,
                             initargs=(payload,)) as ex:
        kind = {}
        for j in jobs_ext:
            kind[ex.submit(_mde_ext_rep, j)] = res_ext
        for j in jobs_int:
            kind[ex.submit(_mde_int_rep, j)] = res_int
        for j in jobs_k3:
            kind[ex.submit(_mde_k3_rep, j)] = res_k3
        futs = list(kind)
        for i, fu in enumerate(as_completed(futs)):
            kind[fu].append(fu.result())
            if (i + 1) % 2000 == 0:
                logger.info(f"MDE sims {i + 1}/{len(futs)} ({time.time() - t0:.0f}s)")
    out = {"reps_per_grid_point": reps, "meta": meta, "extensive_pp_per_sd": {}, "intensive_irr_per_sd": {},
           "k3_phys_ratio": {}}
    de = pd.DataFrame(res_ext, columns=["fold", "g", "rep", "rej", "se_sd"])
    di = pd.DataFrame(res_int, columns=["fold", "g", "rep", "rej", "se_sd"])
    for fold in samples:
        e = de[de.fold == fold].groupby("g").rej.mean()
        i = di[di.fold == fold].dropna().groupby("g").rej.mean()
        out["extensive_pp_per_sd"][fold] = {"grid": [float(x) for x in e.index], "power": [float(x) for x in e],
                                            "MDE80": interp_mde(list(e.index), list(e), 0.0),
                                            "sim_se_pp_per_sd_null": float(100 * de[(de.fold == fold) & (de.g == 0)].se_sd.mean()),
                                            "size_at_null": float(e.loc[0])}
        out["intensive_irr_per_sd"][fold] = {"grid": [float(x) for x in i.index], "power": [float(x) for x in i],
                                             "MDE80": interp_mde(list(i.index), list(i), 1.0),
                                             "sim_se_logirr_per_sd_null": float(di[(di.fold == fold) & (di.g == 1.0)].dropna().se_sd.mean()),
                                             "size_at_null": float(i.loc[1.0]),
                                             "failed": int(di[(di.fold == fold)].rej.isna().sum())}
    # IVW MDE from per-fold simulated SEs at the null: MDE80 = (1.96 + 0.84) x SE_ivw
    se_e = [out["extensive_pp_per_sd"][f]["sim_se_pp_per_sd_null"] for f in samples]
    se_i = [out["intensive_irr_per_sd"][f]["sim_se_logirr_per_sd_null"] for f in samples]
    se_ivw_e = 1 / math.sqrt(sum(1 / x ** 2 for x in se_e))
    se_ivw_i = 1 / math.sqrt(sum(1 / x ** 2 for x in se_i))
    out["extensive_pp_per_sd"]["IVW"] = {"MDE80": 2.8 * se_ivw_e, "se_ivw": se_ivw_e,
                                         "rule": "(1.96 + 0.84) x IVW SE from per-fold simulated null SEs"}
    out["intensive_irr_per_sd"]["IVW"] = {"MDE80": math.exp(2.8 * se_ivw_i), "se_ivw_log": se_ivw_i,
                                          "rule": "exp((1.96 + 0.84) x IVW SE of log IRR/SD)"}
    dk = pd.DataFrame(res_k3, columns=["g", "rep", "rej"]).dropna()
    k = dk.groupby("g").rej.mean()
    out["k3_phys_ratio"] = {"grid": [float(x) for x in k.index], "power": [float(x) for x in k],
                            "MDE80_ratio": interp_mde(list(k.index), list(k), 1.0), "size_at_null": float(k.loc[1.0]),
                            "failed": int(len(jobs_k3) - len(dk)),
                            "definition": "ratio of IRR/SD (Physics/Astro over rest) = exp(contrast x pooled SD)"}
    out["seconds"] = round(time.time() - t0, 1)
    return out


# ============================================================================================ SPEC
def build_spec(sizes: dict, mde: dict, gates_summary: dict) -> dict:
    return {
        "name": "K1 (which margin) / K3 (field boundary) / INFERENCE FIX for the confirmed D2 host-entry effect",
        "label": "POST-CONFIRMATION EXPLORATORY: every fold has been opened; only K-specific coefficients unseen at freeze",
        "frozen_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "builds_on": {"art_WZ8fbLn79nCq": "iter_4/gen_art/gen_art_evaluation_2 (d2 stack, screen/held-out tables)",
                      "art_XGdzjWgi-a88": "iter_4/gen_art/gen_art_experiment_9 (MeSH D2)",
                      "art_2Cd2JJypeGuA": "iter_3/gen_art/gen_art_experiment_7 (origin of every definition)",
                      "art_eR1Z7fMlOcxs": "iter_2/gen_art/gen_art_dataset_5 (corpus; subfield taxonomy)"},
        "common": {"outcome": "Y_strict (W2 host d-papers by author-disjoint newcomers)",
                   "coprimary_fe": "concept + e + d (FE_SPECS secondary)", "primary_fe_side_row": "concept x e + d x e",
                   "controls_main": K.CTRL2, "controls_mesh": K.mesh_controls(), "offset": "log(n_entry_papers) in every PPML count model",
                   "se": "CRV1 by concept, pyfixest small-sample factor (fixef_k nested), t(G-1) CIs",
                   "per_sd": "SD of A_cont on the retained sample of THAT fit (K1 decomposition: full co-primary retained SD)",
                   "folds": {"SCREEN": "main screen MAIN kw5", "HELDOUT": "main held-out (already opened)",
                             "MESH": "biomedicine -> biomedicine entries only (F6 widening)"}},
        "K1": {
            "K1a_LPM_primary": "OLS on Any = 1[Y_strict>=1] | concept + e + d; regressors A_cont + CT + controls + log(n_entry_papers) "
                               "(offset meaningless for a probability: declared); iterated singleton pruning; effect in pp per SD",
            "K1a_logit": "unconditional FE logit (IRLS, weighted within-transformation, exact sparse projection) with concept + e + d; "
                         "iterated pruning of singleton and all-0/all-1 FE levels; odds ratio per SD. Deviation: pyfixest feglm not used "
                         "(no FE support for logit in the pinned version is assumed; own IRLS used instead and declared)",
            "K1a_loglink": "PPML on Any, same FE and regressors (log n as regressor, no offset); proportional effect on P(Y>=1) per SD",
            "K1b": "PPML on subsample Y_strict >= 1, same FE, controls + CT, offset; IRR per SD; re-pruned; label "
                   "'conditional on uptake starting; descriptive, subject to selection'",
            "decomposition": {"b_total": "co-primary b (R0b)", "share": "b_ext / (b_ext + b_int), both per SD of the FULL co-primary retained sample",
                              "gap": "b_total - (b_ext + b_int)", "bootstrap": {"draws": 1000, "unit": "concept (copies become distinct concepts)",
                                                                             "ci": "percentile", "seed": "SEED + 3_000_000 + draw"}},
            "ladder": ["Any", "Y_ge3", "Y_ge5", "EST_bin"],
            "side_rows": "primary FE (concept x e + d x e) for K1a-LPM and K1b, labelled underpowered where G < 50",
            "ivw": ["K1a_LPM pp/SD", "K1a_loglink log/SD", "K1b log IRR/SD", "extensive share (bootstrap SE)"],
        },
        "K3": {"sample": "pooled SCREEN + HELDOUT frozen samples with fold indicator", "fe": "concept + (fold x e) + d",
               "model": "Y_strict ~ A_cont x {Physics/Astro, CS, other} + CT + CTRL2, offset, PPML, CRV1 concept",
               "group_coding": "field_group = ORIGIN field of concept (31 Physics/Astro, 17 CS, else other); constant within concept",
               "irr_per_sd": "ONE common SD = SD of A_cont on the pooled retained sample",
               "wald": "H0 b_phys = b_cs = b_other, 2 df, CRV1 V; p from F(2, G-1) = W/2 (chi2(2) p reported beside)",
               "focal_contrast": "separate model A_cont + A_cont x Phys (1 df): b(A x Phys) = b_phys - b_rest; ratio of IRR/SD",
               "perm": {"draws": 2000, "scheme": "permute origin-group labels across CONCEPTS (group sizes in concepts preserved); recompute Wald W and contrast t",
                        "seed": "SEED + 4_000_000 + draw"},
               "secondary": "host-field grouping (field_d: 31/17/other), group main effect absorbed by d; labelled SECONDARY",
               "mesh_row": "MeSH R2 shown separately (biomedical), never pooled",
               "descriptive_rule": "any group with G < 30 is descriptive and excluded from the Wald test"},
        "INFERENCE": {"rows": ["SCREEN coprimary A_cont", "HELDOUT coprimary A_cont", "MESH coprimary A_cont", "IVW pooled z",
                               "K1a-LPM per fold", "K1a-LPM IVW"],
                      "rand_t": {"draws": 2000, "scheme": "permute A_cont within concept; Y, controls, FE fixed; t = b/SE_CRV1",
                                 "p": "(1 + #|t*| >= |t_obs|) / (1 + draws)", "seed": "SEED + draw (same draw index in every fold)",
                                 "headline": True},
                      "freedman_lane": {"draws": 2000, "scheme": "residualise A_cont on CT + controls (+ log n for LPM) + FE by OLS; permute residual within concept; add back fitted",
                                        "seed": "SEED + 1_000_000 + draw"},
                      "wcr_webb": {"draws": 9999, "weights": "Webb 6-point", "statistic": "Kline-Santos score, restricted fit",
                                   "seed": "SEED + 2_000_000 (+ row offset)"},
                      "wcr_rademacher_check": {"draws": 999, "target": "held-out wild p 0.012 within 0.01"},
                      "crv1_null_rejection": "share of rand-t draws with CRV1 p < 0.05 (t(G-1)); plus z SD of the draws",
                      "mc_se": "sqrt(p(1-p)/B)", "ivw_rand": "same draw index across folds; z_IVW* from per-fold b*, SE* (log IRR/SD)"},
        "audit": {"path": "audit/audit_k.py (pyfixest + pandas only)", "checks": ["K1a-LPM per fold + IVW |diff|<1e-4",
                  "K3 Wald p (pyfixest fepois + own Wald from its vcov)", "held-out rand-t p with 500 fresh draws, seed 777, within 2 MC SE"]},
        "sample_sizes": sizes,
        "MDE": mde,
        "gates_summary": gates_summary,
        "decision_rules_verbatim": DECISION_RULES_VERBATIM,
        "verdict_codes": {"K1": {"EXTENSIVE": 1, "INTENSIVE-ONLY": 2, "BOTH": 3, "UNRESOLVED": 0, "NOT RUN": -1}},
        "output_rows": ["results/k1_rows.csv", "results/k1_decomposition.json", "results/k3_rows.csv",
                        "results/inference_rows.csv", "results/k13_summary.json", "audit/audit_k.json"],
        "seed": K.SEED,
    }


@logger.catch(reraise=True)
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reps", type=int, default=300)
    ap.add_argument("--gates-only", action="store_true")
    ap.add_argument("--skip-pytest", action="store_true")
    a = ap.parse_args()
    K.set_main_ram_limit()
    # input hashes
    hashes = {p.name: K.sha256_file(p) for p in sorted(K.INPUTS.glob("*.parquet"))}
    K.dump({"inputs": hashes, "sources": K.SRC_MAIN}, K.RESULTS / "input_hashes.json")
    samples = {f: K.load_fold(f) for f in K.FOLDS}
    pooled = K.load_pooled_k3()
    logger.info({f: len(s) for f, s in samples.items()} | {"pooled": len(pooled)})
    gates = {"R0a": gate_r0a(), "R0b": gate_r0b(samples), "R0c": gate_r0c(samples)}
    gates["R0d"] = {"skipped": True, "pass": None} if a.skip_pytest else gate_r0d()
    gates["R0e"] = gate_r0e(samples)
    gates["fold_pass"] = {f: bool(gates["R0a"]["pass"] and gates["R0b"][f]["pass"]) for f in K.FOLDS}
    gates["fold_pass"]["HELDOUT"] = bool(gates["fold_pass"]["HELDOUT"] and gates["R0c"]["pass"])
    K.dump(K.clean(gates), K.RESULTS / "gates.json")
    logger.info(f"gates: R0a {gates['R0a']['pass']} R0b {[gates['R0b'][f]['pass'] for f in K.FOLDS]} "
                f"R0c {gates['R0c']['pass']} R0d {gates['R0d']['pass']}")
    if a.gates_only:
        return
    sizes = sample_sizes(samples, pooled)
    mde = run_mde(samples, pooled, a.reps)
    logger.info(f"MDE ext {[mde['extensive_pp_per_sd'][f]['MDE80'] for f in list(K.FOLDS) + ['IVW']]} "
                f"int {[mde['intensive_irr_per_sd'][f]['MDE80'] for f in list(K.FOLDS) + ['IVW']]} "
                f"k3 {mde['k3_phys_ratio']['MDE80_ratio']}")
    gsum = {"fold_pass": gates["fold_pass"], "R0d": gates["R0d"]["pass"],
            "R0b": {f: {k: gates["R0b"][f][k] for k in ("irr_sd", "ci", "N", "G")} for f in K.FOLDS}}
    spec = K.clean(build_spec(sizes, mde, gsum))
    if a.reps < 300:  # dry run of the freeze machinery: never overwrites or logs the real spec
        K.dump(spec, K.RESULTS / "smoke" / "k13_spec_dryrun.json")
        logger.info("dry-run spec written to results/smoke/k13_spec_dryrun.json")
        return
    K.dump(spec, K.SPEC_PATH)
    h = K.sha256_file(K.SPEC_PATH)
    K.SPEC_HASH_PATH.write_text(f"{h}  k13_spec.json\n")
    with open(K.LOGS / "freeze_log.txt", "a") as f:
        f.write(f"{spec['frozen_utc']} FROZEN k13_spec.json sha256={h} (before any K coefficient)\n")
    logger.info(f"spec frozen sha256={h}")


if __name__ == "__main__":
    main()
