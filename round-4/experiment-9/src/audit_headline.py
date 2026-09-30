#!/usr/bin/env python3
"""Headline re-derivation (different code path from src/models_mesh.py + vendored ppml).

Reads the RAW per-event outcome file (results/outcomes_mesh.parquet) and the frozen control list, prunes singleton /
all-zero FE levels with its own pandas loop, fits R2 with pyfixest.fepois (CRV1 by concept) and recomputes:
IRR per SD of A_cont with its 95% CI, the Holm p, the MeSH-vs-main z test and the IVW pooled estimate (main
numbers typed in from exp_7 results/d2_models.json). Then runs the SAME test on placebo input: A_cont shuffled
across events (20 draws) and an independent random regressor (20 draws); these must not reject systematically.
Writes results/audit_headline.json.
"""
from __future__ import annotations

import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import pyfixest as pf
from scipy import stats

WS = Path(__file__).resolve().parent


def prune(d: pd.DataFrame) -> pd.DataFrame:
    while True:
        n = len(d)
        for fe in ("concept_id", "e", "d"):
            g = d.groupby(fe).Y_strict.agg(["size", "sum"])
            bad = g[(g["size"] <= 1) | (g["sum"] <= 0)].index
            d = d[~d[fe].isin(bad)]
        if len(d) == n:
            return d


def fit(d: pd.DataFrame, x: str, ctrl: list[str]):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return pf.fepois(f"Y_strict ~ {x} + CT + {' + '.join(ctrl)} | concept_id + e + d", data=d,
                         offset="off", vcov={"CRV1": "concept_id"}, demeaner_backend="scipy", fixef_tol=1e-12,
                         iwls_tol=1e-12, iwls_maxiter=500)


def main() -> None:
    spec = json.loads((WS / "results" / "mesh_spec.json").read_text())
    ctrl = spec["models"]["secondary_controls"]
    raw = pd.read_parquet(WS / "results" / "outcomes_mesh.parquet")
    d = raw.dropna(subset=["A_cont", "CT"] + ctrl).copy()
    d["off"] = np.log(d.n_entry_papers.astype(float))
    d["e"] = d.e.astype(str)
    d["d"] = d.d.astype(str)
    d = prune(d)
    m = fit(d, "A_cont", ctrl)
    G = d.concept_id.nunique()
    b, se = float(m.coef()["A_cont"]), float(m.se()["A_cont"])
    sd = float(d.A_cont.std())
    tq = stats.t.ppf(0.975, G - 1)
    p_a = 2 * stats.t.sf(abs(b / se), G - 1)
    p_ct = 2 * stats.t.sf(abs(float(m.coef()["CT"]) / float(m.se()["CT"])), G - 1)
    holm_a = min(1.0, 2 * p_a) if p_a <= p_ct else max(min(1.0, 2 * p_ct), p_a)
    irr, lo, hi = np.exp(b * sd), np.exp((b - tq * se) * sd), np.exp((b + tq * se) * sd)
    # comparison with main (exp_7 co-primary b 4.739105939721475, se 1.0102888770711833, IRR/SD 1.300076888024346)
    bm, sem, irrm = 4.739105939721475, 1.0102888770711833, 1.300076888024346
    sdm = np.log(irrm) / bm
    l1, s1, l2, s2 = b * sd, se * sd, np.log(irrm), sem * sdm
    z = (l1 - l2) / np.hypot(s1, s2)
    w1, w2 = s1 ** -2, s2 ** -2
    pooled = np.exp((w1 * l1 + w2 * l2) / (w1 + w2))
    # placebo inputs
    rng = np.random.default_rng(20260929)
    sh_p, rnd_p = [], []
    for _ in range(20):
        dd = d.copy()
        dd["A_sh"] = rng.permutation(dd.A_cont.to_numpy())
        r = fit(dd, "A_sh", ctrl)
        sh_p.append(float(r.pvalue()["A_sh"]))
        dd["A_rnd"] = rng.normal(size=len(dd))
        r = fit(dd, "A_rnd", ctrl)
        rnd_p.append(float(r.pvalue()["A_rnd"]))
    pipe = json.loads((WS / "results" / "g4_verdict.json").read_text())
    cmpj = json.loads((WS / "results" / "g4_models.json").read_text())["comparison_main_vs_mesh"]["main_coprimary_1.30"]
    out = {"N": int(len(d)), "G": int(G), "irr_sd": float(irr), "ci95": [float(lo), float(hi)], "p_crv1": float(p_a),
           "holm_p": float(holm_a), "z_vs_main": float(z), "p_vs_main": float(2 * stats.norm.sf(abs(z))),
           "ivw_pooled": float(pooled),
           "pipeline": {"irr_sd": pipe["irr_sd"], "ci95": pipe["ci95"], "holm_p": pipe["holm_p"], "z": cmpj["z"],
                        "ivw": cmpj["ivw_pooled_irr_sd"]},
           "match": bool(abs(irr - pipe["irr_sd"]) < 1e-6 and abs(lo - pipe["ci95"][0]) < 1e-3
                         and abs(hi - pipe["ci95"][1]) < 1e-3 and abs(z - cmpj["z"]) < 1e-3
                         and abs(pooled - cmpj["ivw_pooled_irr_sd"]) < 1e-3),
           "placebo_shuffled_A": {"n": 20, "share_p_lt_0.05": float(np.mean(np.array(sh_p) < 0.05)),
                                  "min_p": float(min(sh_p)), "median_p": float(np.median(sh_p))},
           "placebo_random_regressor": {"n": 20, "share_p_lt_0.05": float(np.mean(np.array(rnd_p) < 0.05)),
                                        "min_p": float(min(rnd_p)), "median_p": float(np.median(rnd_p))}}
    (WS / "results" / "audit_headline.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
