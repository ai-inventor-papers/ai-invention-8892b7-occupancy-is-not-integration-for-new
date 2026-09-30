#!/usr/bin/env python3
"""POST-HOC DIAGNOSTIC (not in the frozen spec): why does the pre-declared S2 split-generality row absorb part of A_cont?

S2 enters GH_k = sum_{class-k tags} H_p / n_gen. Since H_p lies in [0, 1] and varies little across tags, GH_nat is
approximately (native tag share) x (mean native H), i.e. it re-encodes the host-share COMPOSITION that A_cont measures.
This script reports (i) the within-FE correlations of A_cont with GH_k / GF_k and with the class shares, and
(ii) S2b: A_cont + WITHIN-CLASS MEAN generality mH_k, mF_k (class absent -> fold mean + absence indicator), which
holds the generality of each class fixed without re-encoding its share. Retention vs the M0 of the frozen run.
It also reports a 499-draw concept bootstrap CI of the S2b retention.
Output: results/k2_s2b_diagnostic.json (+ rows appended to nothing; the frozen k2_rows.csv is not modified).
"""
from __future__ import annotations

import json
import pickle
import sys

import numpy as np
import pandas as pd

import k2_lib as L
from k2_lib import logger

CLS = ("nat", "adj", "for")


def class_means(arr: dict, n: int) -> pd.DataFrame:
    gen = (arr["src"] == 0) & ~np.isnan(arr["H"]) & ~np.isnan(arr["F"])
    sh = arr["sh"]
    cls = {"nat": sh >= L.NAT_CUT, "adj": (sh >= L.ADJ_LO) & (sh < L.NAT_CUT), "for": sh < L.ADJ_LO}
    out = pd.DataFrame(index=range(n))
    ng = np.bincount(arr["te"][gen], minlength=n).astype(float)
    for k, m in cls.items():
        mm = gen & m
        nk = np.bincount(arr["te"][mm], minlength=n).astype(float)
        with np.errstate(invalid="ignore", divide="ignore"):
            out[f"mH_{k}"] = np.bincount(arr["te"][mm], weights=arr["H"][mm], minlength=n) / nk
            out[f"mF_{k}"] = np.bincount(arr["te"][mm], weights=arr["F"][mm], minlength=n) / nk
            out[f"sh_{k}"] = nk / ng
        out[f"abs_{k}"] = (nk == 0).astype(float)
        for c in (f"mH_{k}", f"mF_{k}"):
            out[c] = out[c].fillna(out[c].mean())
    return out


XB = [f"m{x}_{k}" for x in "HF" for k in CLS] + ["abs_nat", "abs_adj"]


def _boot(args) -> dict:
    fold, seed = args
    s = L._W["s"][fold]
    b = L.resample(s, np.random.default_rng(seed))
    r0 = L.fit_b(b, L.xvars_of("M0"))
    r1 = L.fit_b(b, ["A_cont"] + XB + ["CT"] + L.CTRL)
    return {"fold": fold, "b0": None if r0 is None else float(r0["coef"][0]),
            "b1": None if r1 is None else float(r1["coef"][0])}


@logger.catch(reraise=True)
def main() -> None:
    L.setup_logging("k2_s2b")
    L.assert_spec_frozen()
    cache = pickle.loads((L.KCACHE / "k2_samples.pkl").read_bytes())
    summ = json.loads((L.RES / "k2_summary.json").read_text())
    out, S = {"label": "POST-HOC DIAGNOSTIC (not pre-specified; not in the rule)", "folds": {}}, {}
    for f in L.FOLDS:
        k = cache[f]["k2"]
        cm = class_means(cache[f]["arr"], len(k))
        s = pd.concat([k.reset_index(drop=True), cm], axis=1)
        S[f] = s
        cols = ["A_cont", "GH_nat", "GH_adj", "GH_for", "GF_nat", "GF_adj", "GF_for", "sh_nat", "sh_adj",
                "mH_nat", "mH_adj", "mH_for"]
        M = L.within(s, cols)
        C = np.corrcoef(M, rowvar=False)
        o = {"within_fe_r_with_A_cont": {c: float(C[0, i]) for i, c in enumerate(cols) if i},
             "within_fe_r_GH_nat_sh_nat": float(C[1, cols.index("sh_nat")]),
             "within_fe_r_GH_adj_sh_adj": float(C[2, cols.index("sh_adj")])}
        rr, r = L.fit_rows(s, ["A_cont"] + XB + ["CT"] + L.CTRL, ["A_cont"] + XB[:6], fold=f, model="S2b",
                           label=out["label"])
        a = {x["var"]: x for x in rr}
        o["S2b_A_cont_irr_sd"] = [a["A_cont"]["irr_sd"], a["A_cont"]["irr_sd_lo"], a["A_cont"]["irr_sd_hi"]]
        o["S2b_A_cont_p"] = a["A_cont"]["p_crv1"]
        o["S2b_ret"] = a["A_cont"]["b"] / summ["folds"][f]["M0_A_cont"]["b"]
        o["S2b_class_mean_irr_sd"] = {v: [a[v]["irr_sd"], a[v]["p_crv1"]] for v in XB[:6]}
        o["S2_ret_frozen_row"] = summ["supplementary"][f]["S2"]["ret"]
        o["_lnirr"] = (a["A_cont"]["lnirr_sd"], a["A_cont"]["lnirr_sd_se"])
        out["folds"][f] = o
        logger.info(f"[{f}] S2b ret {o['S2b_ret']:.3f} (S2 {o['S2_ret_frozen_row']:.3f}); r(A, GH_nat) "
                    f"{o['within_fe_r_with_A_cont']['GH_nat']:.3f}; r(GH_nat, sh_nat) {o['within_fe_r_GH_nat_sh_nat']:.3f}")
    tasks = [(f, L.SEED + 900_000 + 1000 * i + j) for i, f in enumerate(L.FOLDS) for j in range(499)]
    bd = pd.DataFrame(L.pool({"s": S}, _boot, tasks, chunksize=10))
    for f in L.FOLDS:
        x = bd[bd.fold == f].dropna()
        r = (x.b1 / x.b0).replace([np.inf, -np.inf], np.nan).dropna()
        out["folds"][f]["S2b_ret_ci"] = [float(r.quantile(.025)), float(r.quantile(.975))]
    p0 = summ["pooled"]["M0_A_cont"]
    lp = [out["folds"][f].pop("_lnirr") for f in L.FOLDS]
    iv = L.ivw([a for a, _ in lp], [b for _, b in lp])
    out["pooled"] = {"S2b_A_cont_irr_sd": [float(np.exp(iv["b"])), float(np.exp(iv["lo"])), float(np.exp(iv["hi"]))],
                     "S2b_ret": iv["b"] / p0["b"], "I2": iv["I2"]}
    L.dump(L.RES / "k2_s2b_diagnostic.json", L.clean(out))
    logger.info(f"pooled S2b: {out['pooled']}")


if __name__ == "__main__":
    sys.exit(main())
