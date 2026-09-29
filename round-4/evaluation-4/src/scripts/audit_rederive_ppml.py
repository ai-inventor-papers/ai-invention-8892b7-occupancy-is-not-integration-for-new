#!/usr/bin/env python3
"""Audit part 2: screen CT type gap (statsmodels dummies) and the PPML A_cont IRR per SD within each type
(statsmodels Poisson GLM with concept + e + host dummies, offset log n_entry_papers, cluster by concept) - a
different estimator implementation than exp_7 src/ppml.py. Appends to results/audit_rederive.json."""
import csv
import json
import os
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf

WS = Path(__file__).resolve().parents[1]
LOOP = Path(os.environ.get("AII_LOOP_ROOT", WS.parents[2])).resolve()  # dependency artifacts: <LOOP>/iter_N/gen_art/<artifact>
E7 = LOOP / "iter_3/gen_art/gen_art_experiment_7"
M = json.loads((WS / "eval_out.json").read_text())["metrics_agg"]
A = json.loads((WS / "results/audit_rederive.json").read_text())
broad = "broad from the start (rapid interdisciplinary)"
styp = {r["concept_id"]: float(r["cluster_name"] == broad) for r in csv.DictReader(open(WS / "exp8_frozen/typology/assignments.csv"))}
need = ["A_cont", "CT", "prox_od", "RD", "log_n_partner_tags", "cov", "demic", "mean_topic_score", "boundary_share", "abstract_share", "mom_d", "log_centrality", "log_W1"]
ev = pd.read_parquet(E7 / "results/screen_events_with_outcomes.parquet")
s = ev[(ev.arm == "main") & (ev.fold == "screen") & ev.kw5 & ev.MAIN].dropna(subset=need).copy()
s = s[s.concept_id.isin(styp)]
s["BROAD"] = s.concept_id.map(styp)
d = s.assign(dxe=s.d.astype(str) + "_" + s.e.astype(str))
d = d[d.groupby("dxe").dxe.transform("size") > 1]
f = smf.ols("CT ~ BROAD + log_n_partner_tags + RD + C(dxe)", d).fit(cov_type="cluster", cov_kwds={"groups": pd.factorize(d.concept_id)[0]})
A["typegap_CT_screen_adj"] = dict(rederived=float(f.params["BROAD"]), reported=M["typegap_CT_screen_adj"],
                                  match=bool(abs(f.params["BROAD"] - M["typegap_CT_screen_adj"]) < 1e-6))
# PPML: drop concepts / hosts / years whose Y is all zero (separation), then GLM Poisson with dummies
p = s.copy()
for _ in range(5):
    for k in ("concept_id", "d", "e"):
        p = p[p.groupby(k).Y_strict.transform("sum") > 0]
sdA = s.A_cont.std()
p["A_L"] = p.A_cont * (1 - p.BROAD)
p["A_B"] = p.A_cont * p.BROAD
ctrl = " + ".join(["CT"] + need[2:])
g = smf.glm(f"Y_strict ~ A_L + A_B + {ctrl} + C(concept_id) + C(e) + C(d)", p, family=sm.families.Poisson(),
            offset=np.log(p.n_entry_papers.astype(float))).fit(cov_type="cluster", cov_kwds={"groups": pd.factorize(p.concept_id)[0]}, maxiter=200)
for t, col in (("BROAD", "A_B"), ("LOCALISED", "A_L")):
    irr = float(np.exp(g.params[col] * sdA))
    A[f"IRR_A_per_sd_{t}"] = dict(rederived=irr, reported=M[f"IRR_A_per_sd_{t}"], n=int(g.nobs),
                                  match_tol_1e3=bool(abs(irr - M[f"IRR_A_per_sd_{t}"]) < 1e-3))
# placebo: nativeness-free control - shuffle A_cont within concept; the BROAD IRR should collapse towards 1
rng = np.random.default_rng(5)
q = p.copy()
q["A_cont"] = q.groupby("concept_id").A_cont.transform(lambda x: rng.permutation(x.to_numpy()))
q["A_L"] = q.A_cont * (1 - q.BROAD)
q["A_B"] = q.A_cont * q.BROAD
gq = smf.glm(f"Y_strict ~ A_L + A_B + {ctrl} + C(concept_id) + C(e) + C(d)", q, family=sm.families.Poisson(),
             offset=np.log(q.n_entry_papers.astype(float))).fit(cov_type="cluster", cov_kwds={"groups": pd.factorize(q.concept_id)[0]}, maxiter=200)
A["placebo_within_concept_shuffled_Acont_ppml"] = dict(IRR_BROAD=float(np.exp(gq.params["A_B"] * sdA)), p_BROAD=float(gq.pvalues["A_B"]),
                                                        IRR_LOCAL=float(np.exp(gq.params["A_L"] * sdA)), p_LOCAL=float(gq.pvalues["A_L"]))
(WS / "results/audit_rederive.json").write_text(json.dumps(A, indent=1, default=float))
for k in ("typegap_CT_screen_adj", "IRR_A_per_sd_BROAD", "IRR_A_per_sd_LOCALISED", "placebo_within_concept_shuffled_Acont_ppml"):
    print(k, A[k])
