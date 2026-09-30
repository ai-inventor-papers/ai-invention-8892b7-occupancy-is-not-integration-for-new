#!/usr/bin/env python3
"""Second, short re-derivation from RAW row/draw files + placebo checks (no k_lib, no vendored module).

(a) IVW K1a-LPM (pp/SD) and K1b (IRR/SD) recomputed with plain Python from the per-fold rows (estimate, se, sd_A).
(b) Held-out randomization-t p recomputed from the raw draw file (inference_draws.csv) with plain Python.
(c) Placebo 1: every null draw treated as if observed -> its randomization p against the other draws; the test must
    reject ~5% (it passes vacuously if it rejects much more).
(d) Placebo 2: K1a-LPM with A_cont shuffled within concept (pyfixest.feols, 40 draws per fold, seed 555); the IVW
    z of shuffled A must NOT reach the observed IVW z (7.53) and should reject at |z|>1.96 about 5% of the time.
Writes audit/audit_placebo.json.
"""
from __future__ import annotations

import csv
import json
import math
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import pyfixest as pf

warnings.filterwarnings("ignore")
WS = Path(__file__).resolve().parents[1]
RES = WS / "results"
CTRL2 = ["prox_od", "RD", "log_n_partner_tags", "cov", "demic", "mean_topic_score", "boundary_share",
         "abstract_share", "mom_d", "log_centrality", "log_W1"]


def ivw(e, s):
    w = [1 / x ** 2 for x in s]
    m = sum(wi * ei for wi, ei in zip(w, e)) / sum(w)
    se = math.sqrt(1 / sum(w))
    return m, se


def main() -> None:
    out = {}
    rows = list(csv.DictReader(open(RES / "k1_rows.csv")))
    get = lambda t, f: next(r for r in rows if r["test"] == t and r["fold"] == f)  # noqa: E731
    folds = ["SCREEN", "HELDOUT", "MESH"]
    e = [float(get("K1a_LPM", f)["estimate"]) for f in folds]
    s = [100 * float(get("K1a_LPM", f)["se"]) * float(get("K1a_LPM", f)["sd_A"]) for f in folds]
    m, se = ivw(e, s)
    out["ivw_lpm_pp_per_sd"] = {"rederived": m, "ci": [m - 1.96 * se, m + 1.96 * se],
                                "reported": float(get("K1f_IVW_K1a_LPM_pp_per_sd", "IVW")["estimate"])}
    b = [float(get("K1b", f)["b"]) * float(get("K1b", f)["sd_A"]) for f in folds]
    sb = [float(get("K1b", f)["se"]) * float(get("K1b", f)["sd_A"]) for f in folds]
    m2, se2 = ivw(b, sb)
    out["ivw_k1b_irr_per_sd"] = {"rederived": math.exp(m2), "ci": [math.exp(m2 - 1.96 * se2), math.exp(m2 + 1.96 * se2)],
                                 "reported": float(get("K1f_IVW_K1b_log_irr_per_sd", "IVW")["estimate"])}
    dr = list(csv.DictReader(open(RES / "inference_draws.csv")))
    ts = [float(r["HELDOUT_cnt_plain_t"]) for r in dr if r["HELDOUT_cnt_plain_t"] not in ("", "nan")]
    t_obs = json.loads((RES / "gates.json").read_text())["R0c"]["heldout_coprimary_z"]["z"]
    p = (1 + sum(abs(t) >= abs(t_obs) for t in ts)) / (1 + len(ts))
    out["heldout_rand_p"] = {"rederived": p, "reported": json.loads((RES / "inference_summary.json").read_text())
                             ["rows"]["HELDOUT.coprimary_A_count"]["p_rand_t"], "draws": len(ts)}
    # placebo 1: null draws as pseudo-observations
    rej = {}
    for f in folds:
        arr = np.abs(np.array([float(r[f"{f}_cnt_plain_t"]) for r in dr]))
        ps = [(1 + (np.delete(arr, i) >= arr[i]).sum()) / len(arr) for i in range(len(arr))]
        rej[f] = float(np.mean(np.array(ps) < 0.05))
    out["placebo_randomization_test_on_null_draws_reject_rate"] = rej
    # placebo 2: shuffled A_cont through an independent pyfixest LPM
    rng = np.random.default_rng(555)
    zs = []
    data = {}
    for f in folds:
        if f == "MESH":
            c = json.loads((WS / "mesh" / "results" / "mesh_spec.json").read_text())["models"]["secondary_controls"]
            d = pd.read_parquet(WS / "inputs" / "outcomes_mesh.parquet").dropna(subset=["A_cont", "CT"] + c)
        else:
            c = CTRL2
            fl = f.lower()
            d = pd.read_parquet(WS / "inputs" / f"g_features_{fl}_coprimary.parquet")
            d = d[(d.arm == "main") & (d.fold == fl) & d.kw5 & d.MAIN].dropna(subset=["A_cont", "CT"] + c)
        d = d.copy()
        d["Any"] = (d.Y_strict >= 1).astype(float)
        d["log_nep"] = np.log(d.n_entry_papers.astype(float))
        for col in ("concept_id", "e", "d"):
            d[col] = d[col].astype(str)
        data[f] = (d, c)
    for _ in range(40):
        bs, ses = [], []
        for f in folds:
            d, c = data[f]
            d = d.copy()
            d["A_cont"] = d.groupby("concept_id").A_cont.transform(lambda v: rng.permutation(v.to_numpy()))
            m_ = pf.feols(f"Any ~ A_cont + CT + {' + '.join(c)} + log_nep | concept_id + e + d", data=d,
                          vcov={"CRV1": "concept_id"})
            bs.append(float(m_.coef()["A_cont"]))
            ses.append(float(m_.se()["A_cont"]))
        w = [1 / x ** 2 for x in ses]
        zs.append(sum(wi * bi for wi, bi in zip(w, bs)) / math.sqrt(sum(w)))
    zs = np.array(zs)
    out["placebo_shuffled_A_lpm_ivw"] = {"draws": 40, "max_abs_z": float(np.abs(zs).max()),
                                         "share_abs_z_gt_1.96": float((np.abs(zs) > 1.96).mean()),
                                         "observed_ivw_z": 7.5305, "any_reaches_observed": bool((np.abs(zs) >= 7.5305).any())}
    out["pass"] = bool(abs(out["ivw_lpm_pp_per_sd"]["rederived"] - out["ivw_lpm_pp_per_sd"]["reported"]) < 1e-6
                       and abs(out["ivw_k1b_irr_per_sd"]["rederived"] - out["ivw_k1b_irr_per_sd"]["reported"]) < 1e-6
                       and abs(out["heldout_rand_p"]["rederived"] - out["heldout_rand_p"]["reported"]) < 1e-9
                       and not out["placebo_shuffled_A_lpm_ivw"]["any_reaches_observed"])
    (WS / "audit" / "audit_placebo.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
