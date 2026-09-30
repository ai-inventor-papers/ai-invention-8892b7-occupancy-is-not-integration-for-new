#!/usr/bin/env python3
"""Null calibration of the D3 Freedman-Lane one-sided p: 300 draws with X randomly permuted across screen concepts
(breaks any X-Y link, keeps the covariate structure of Y); 2,000 permutations each. Reports the share of p < 0.05
(nominal 0.05) and a KS test of the p values against U(0,1). Writes results/d3/audit_d3_calibration.json."""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

WS = Path(__file__).resolve().parent
sys.path.insert(0, str(WS / "src_eval"))
import d3core as D  # noqa: E402
sys.path.insert(0, str(WS))
from d3_link import covariates  # noqa: E402

f = pd.read_csv(WS / "results" / "d3" / "d3_concepts_screen.csv")
d = f[np.isfinite(f.X) & np.isfinite(f.Y) & np.isfinite(f.log_vol_early)].reset_index(drop=True)
Z, rc = covariates(d)
rng = np.random.default_rng(777)
ps = []
for i in range(300):
    x = d.X.values[rng.permutation(len(d))]
    ps.append(D.freedman_lane(x, d.Y.values, Z, rc, 2000, 1000 + i)["p_one_neg"])
ps = np.array(ps)
out = dict(n_draws=300, n_perm=2000, n=len(d), share_p_lt_005=float((ps < 0.05).mean()),
           share_p_lt_010=float((ps < 0.10).mean()), ks_uniform_p=float(stats.kstest(ps, "uniform").pvalue),
           binomial_ci_share_p_lt_005=[float(x) for x in stats.binomtest(int((ps < 0.05).sum()), 300).proportion_ci()])
(WS / "results" / "d3" / "audit_d3_calibration.json").write_text(json.dumps(out, indent=1))
print(out)
