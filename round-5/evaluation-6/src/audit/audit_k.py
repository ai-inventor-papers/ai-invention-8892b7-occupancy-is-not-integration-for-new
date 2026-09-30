#!/usr/bin/env python3
"""Independent re-derivation (pyfixest + pandas only; NO vendored module, NO k_lib import).

(1) K1a-LPM coefficient per fold (pyfixest.feols, own iterated singleton pruning) and its IVW (pp per SD).
(2) K3 Wald equality p (pyfixest.fepois with group-specific A_cont slopes; Wald from pyfixest's CRV1 vcov, F(2, G-1)).
(3) Held-out randomization-t p: 500 fresh within-concept shuffles, seed 777, pyfixest.fepois per draw.
Pass: |diff| < 1e-4 on coefficients; randomization p within 2 Monte Carlo SE. Writes audit/audit_k.json.
"""
from __future__ import annotations

import os
os.environ.update(OPENBLAS_NUM_THREADS="1", OMP_NUM_THREADS="1", MKL_NUM_THREADS="1")
import json  # noqa: E402
import math  # noqa: E402
import multiprocessing as mp  # noqa: E402
import sys  # noqa: E402
import warnings  # noqa: E402
from concurrent.futures import ProcessPoolExecutor  # noqa: E402
from pathlib import Path  # noqa: E402

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import pyfixest as pf  # noqa: E402
from scipy import stats  # noqa: E402

warnings.filterwarnings("ignore")
WS = Path(__file__).resolve().parents[1]
INP, RES = WS / "inputs", WS / "results"
CTRL2 = ["prox_od", "RD", "log_n_partner_tags", "cov", "demic", "mean_topic_score", "boundary_share",
         "abstract_share", "mom_d", "log_centrality", "log_W1"]
N_DRAWS, SEED = 500, 777


def mesh_ctrl() -> list[str]:
    return json.loads((WS / "mesh" / "results" / "mesh_spec.json").read_text())["models"]["secondary_controls"]


def fold_sample(fold: str) -> tuple[pd.DataFrame, list[str]]:
    if fold == "MESH":
        c = mesh_ctrl()
        d = pd.read_parquet(INP / "outcomes_mesh.parquet").dropna(subset=["A_cont", "CT"] + c)
    else:
        c = CTRL2
        f = "screen" if fold == "SCREEN" else "heldout"
        d = pd.read_parquet(INP / f"g_features_{f}_coprimary.parquet")
        d = d[(d.arm == "main") & (d.fold == f) & d.kw5 & d.MAIN].dropna(subset=["A_cont", "CT"] + c)
    d = d.copy()
    d["Any"] = (d.Y_strict >= 1).astype(float)
    d["log_nep"] = np.log(d.n_entry_papers.astype(float))
    d["off"] = d["log_nep"]
    for f in ("concept_id", "e", "d"):
        d[f] = d[f].astype(str)
    return d, c


def prune_singletons(d: pd.DataFrame, fes: list[str]) -> pd.DataFrame:
    while True:
        n0 = len(d)
        for f in fes:
            d = d[d.groupby(f)[f].transform("size") > 1]
        if len(d) == n0:
            return d


def prune_poisson(d: pd.DataFrame, y: str, fes: list[str]) -> pd.DataFrame:
    while True:
        n0 = len(d)
        for f in fes:
            g = d.groupby(f)[y]
            d = d[(g.transform("size") > 1) & (g.transform("sum") > 0)]
        if len(d) == n0:
            return d


def lpm_fold(fold: str) -> dict:
    d, c = fold_sample(fold)
    d = prune_singletons(d, ["concept_id", "e", "d"])
    m = pf.feols(f"Any ~ A_cont + CT + {' + '.join(c)} + log_nep | concept_id + e + d", data=d,
                 vcov={"CRV1": "concept_id"}, fixef_tol=1e-12)
    b, se = float(m.coef()["A_cont"]), float(m.se()["A_cont"])
    sd = float(d.A_cont.std())
    return {"b": b, "se": se, "pp_per_sd": 100 * b * sd, "se_pp_per_sd": 100 * se * sd, "N": int(m._N),
            "G": int(d.concept_id.nunique())}


def k3_wald() -> dict:
    parts = []
    for fold in ("SCREEN", "HELDOUT"):
        d, _ = fold_sample(fold)
        d["foldname"] = fold
        parts.append(d)
    d = pd.concat(parts, ignore_index=True)
    d["fold_e"] = d.foldname + "_" + d.e
    d["grp"] = d.field_group.astype(str)
    for g, col in (("Physics/Astro", "A_phys"), ("CS", "A_cs"), ("other", "A_oth")):
        d[col] = d.A_cont * (d.grp == g)
    d = prune_poisson(d, "Y_strict", ["concept_id", "fold_e", "d"])
    m = pf.fepois(f"Y_strict ~ A_phys + A_cs + A_oth + CT + {' + '.join(CTRL2)} | concept_id + fold_e + d", data=d,
                  offset="off", vcov={"CRV1": "concept_id"}, fixef_tol=1e-10, iwls_tol=1e-10, iwls_maxiter=500)
    names = list(m.coef().index)
    b = m.coef().to_numpy()
    V = np.asarray(m._vcov)
    i = [names.index(x) for x in ("A_phys", "A_cs", "A_oth")]
    R = np.zeros((2, len(b)))
    R[0, i[0]], R[0, i[1]] = 1, -1
    R[1, i[0]], R[1, i[2]] = 1, -1
    Rb = R @ b
    W = float(Rb @ np.linalg.solve(R @ V @ R.T, Rb))
    G = d.concept_id.nunique()
    return {"W": W, "p_F": float(stats.f.sf(W / 2, 2, G - 1)), "p_chi2": float(stats.chi2.sf(W, 2)), "N": int(len(d)),
            "G": int(G), "b": {n: float(m.coef()[n]) for n in ("A_phys", "A_cs", "A_oth")}}


_D: dict = {}


def _init(d, fml):
    _D.update(d=d, fml=fml)


def _z(d: pd.DataFrame, fml: str) -> float:
    m = pf.fepois(fml, data=d, offset="off", vcov={"CRV1": "concept_id"}, fixef_tol=1e-10, iwls_tol=1e-10)
    return float(m.coef()["A_cont"] / m.se()["A_cont"])


def _draw(i: int) -> float | None:
    rng = np.random.default_rng(SEED + i)
    d = _D["d"].copy()
    d["A_cont"] = d.groupby("concept_id").A_cont.transform(lambda v: rng.permutation(v.to_numpy()))
    try:
        return _z(d, _D["fml"])
    except Exception as ex:  # noqa: BLE001 - count failures, never silently: reported in draws_failed
        print("draw failed", i, repr(ex))
        return None


def heldout_rand() -> dict:
    d, c = fold_sample("HELDOUT")
    d = prune_poisson(d, "Y_strict", ["concept_id", "e", "d"])
    fml = f"Y_strict ~ A_cont + CT + {' + '.join(c)} | concept_id + e + d"
    zo = _z(d, fml)
    with ProcessPoolExecutor(max_workers=5, mp_context=mp.get_context("spawn"), initializer=_init,
                             initargs=(d, fml)) as ex:
        zs = list(ex.map(_draw, range(N_DRAWS), chunksize=10))
    ok = np.array([z for z in zs if z is not None])
    p = (1 + int((np.abs(ok) >= abs(zo)).sum())) / (1 + len(ok))
    return {"z_obs": zo, "draws": int(len(ok)), "draws_failed": int(N_DRAWS - len(ok)), "p": float(p),
            "mc_se": float(math.sqrt(p * (1 - p) / len(ok))), "z_sd": float(ok.std()),
            "crv1_null_rejection": float((2 * stats.t.sf(np.abs(ok), d.concept_id.nunique() - 1) < 0.05).mean())}


def main() -> None:
    out = {"code_path": "pyfixest 0.60 feols/fepois + pandas; no vendored module, no k_lib"}
    k1 = pd.read_csv(RES / "k1_rows.csv")
    main_rows = k1[k1.test == "K1a_LPM"].set_index("fold")
    lp = {}
    for fold in ("SCREEN", "HELDOUT", "MESH"):
        a = lpm_fold(fold)
        m = main_rows.loc[fold]
        a["b_main"], a["abs_diff_b"] = float(m.b), abs(a["b"] - float(m.b))
        a["se_main"], a["se_rel_diff"] = float(m.se), abs(a["se"] - float(m.se)) / float(m.se)
        a["N_main"], a["G_main"] = int(m.N), int(m.G)
        a["pass_coef_1e-4"] = bool(a["abs_diff_b"] < 1e-4)
        lp[fold] = a
    w = np.array([1 / lp[f]["se_pp_per_sd"] ** 2 for f in lp])
    e = np.array([lp[f]["pp_per_sd"] for f in lp])
    ivw_a = float((w * e).sum() / w.sum())
    ivw_m = float(k1[k1.test == "K1f_IVW_K1a_LPM_pp_per_sd"].estimate.iloc[0])
    out["K1a_LPM"] = {"folds": lp, "ivw_audit_pp_per_sd": ivw_a, "ivw_main_pp_per_sd": ivw_m,
                      "ivw_abs_diff_pp": abs(ivw_a - ivw_m), "pass_ivw_1e-4_pp": bool(abs(ivw_a - ivw_m) < 1e-4)}
    k3m = json.loads((RES / "k3_results.json").read_text())
    try:
        k3a = k3_wald()
        k3a["p_F_main"], k3a["W_main"] = k3m["wald"]["p_F"], k3m["wald"]["W"]
        k3a["abs_diff_p"] = abs(k3a["p_F"] - k3a["p_F_main"])
        k3a["pass_p_1e-4"] = bool(k3a["abs_diff_p"] < 1e-4)
        out["K3_wald"] = k3a
    except Exception as ex:  # noqa: BLE001 - reported as audit failure next to the verdict
        out["K3_wald"] = {"error": repr(ex), "pass_p_1e-4": False}
    inf = json.loads((RES / "inference_summary.json").read_text())
    main_p = inf["rows"]["HELDOUT.coprimary_A_count"]["p_rand_t"]
    main_se = inf["rows"]["HELDOUT.coprimary_A_count"]["mc_se_rand_t"]
    hr = heldout_rand()
    hr["p_main"], hr["mc_se_main"] = main_p, main_se
    tol = 2 * math.sqrt(hr["mc_se"] ** 2 + main_se ** 2)
    hr["abs_diff"], hr["tolerance_2mcse"] = abs(hr["p"] - main_p), tol
    hr["pass_within_2mcse"] = bool(abs(hr["p"] - main_p) <= tol)
    out["heldout_rand_t"] = hr
    out["all_pass"] = bool(all(v["pass_coef_1e-4"] for v in lp.values()) and out["K1a_LPM"]["pass_ivw_1e-4_pp"]
                           and out["K3_wald"].get("pass_p_1e-4") and hr["pass_within_2mcse"])
    (WS / "audit" / "audit_k.json").write_text(json.dumps(out, indent=1, default=float))
    print(json.dumps({"all_pass": out["all_pass"], "lpm": {f: lp[f]["abs_diff_b"] for f in lp},
                      "ivw_diff": out["K1a_LPM"]["ivw_abs_diff_pp"], "k3": out["K3_wald"].get("abs_diff_p"),
                      "rand": [hr["p"], main_p, tol]}, default=float))


if __name__ == "__main__":
    main()
