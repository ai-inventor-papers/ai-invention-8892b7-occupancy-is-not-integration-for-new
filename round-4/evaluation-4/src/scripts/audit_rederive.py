#!/usr/bin/env python3
"""Independent re-derivation of headline numbers through code paths separate from evalsteps/ (own DTW, own series
builder, statsmodels dummies instead of pyfixest, scipy chi2 instead of the frozen perm_chi2, plain csv counting),
plus placebo runs that must FAIL. Writes results/audit_rederive.json."""
import csv
import json
import os
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from scipy.stats import chi2_contingency

WS = Path(__file__).resolve().parents[1]
LOOP = Path(os.environ.get("AII_LOOP_ROOT", WS.parents[2])).resolve()  # dependency artifacts: <LOOP>/iter_N/gen_art/<artifact>
E8, HO = WS / "exp8_frozen", WS / "exp8_frozen/heldout_run"
E7 = LOOP / "iter_3/gen_art/gen_art_experiment_7"
E4 = LOOP / "iter_2/gen_art/gen_art_experiment_4"
M = json.loads((WS / "eval_out.json").read_text())["metrics_agg"]
out = {}


def close(a, b, tol=1e-6):
    return a is not None and b is not None and abs(a - b) <= tol


# ---------- 1. own DTW (Sakoe-Chiba radius 3, Euclidean multichannel cost, normalised by sqrt(path length))
def my_dtw(a, b, r=3):
    """Own DP: Sakoe-Chiba band widened by the length difference, squared-Euclidean local cost,
    backtracked optimal path, distance = sqrt(total cost) / sqrt(path length)."""
    n, m = len(a), len(b)
    allow = np.zeros((n, m), bool)
    if n > m:
        w = n - m + r
        for j in range(m):
            allow[max(0, j - r):min(n, j + w) + 1, j] = True
    else:
        w = m - n + r
        for i in range(n):
            allow[i, max(0, i - r):min(m, i + w) + 1] = True
    D = ((a[:, None, :] - b[None, :, :]) ** 2).sum(-1)
    C = np.full((n + 1, m + 1), np.inf)
    C[0, 0] = 0.0
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            if allow[i - 1, j - 1]:
                C[i, j] = D[i - 1, j - 1] + min(C[i - 1, j - 1], C[i - 1, j], C[i, j - 1])
    i, j, L = n, m, 1
    while (i, j) != (1, 1):
        cands = [(C[i - 1, j - 1], i - 1, j - 1), (C[i - 1, j], i - 1, j), (C[i, j - 1], i, j - 1)]
        cands = [c for c in cands if c[1] >= 1 and c[2] >= 1]
        _, i, j = min(cands, key=lambda t: t[0])
        L += 1
    return math.sqrt(C[n, m]) / math.sqrt(L)


medo = json.loads((E8 / "typology/medoids.json").read_text())
mu, sd = np.array(medo["scaling"]["mean"]), np.array(medo["scaling"]["sd"])
MZ = {m: np.array(v) for m, v in medo["medoid_series_z"].items()}


def my_series(g):
    F = int(g.F.iloc[0])
    g = g[(g.year >= F) & (g.year <= 2024)].sort_values("year")
    h = g.H_rar.astype(float).where(g.H_rar.notna(), g.H.astype(float)).fillna(0).to_numpy()
    rs = g.RS.astype(float).fillna(0).to_numpy()
    ac = g.active_subfields_3y.astype(float).fillna(0).to_numpy()
    return (np.column_stack([h, rs, ac]) - mu) / sd


def my_assign(ind):
    res = {}
    for c, g in ind.groupby("concept_id"):
        z = my_series(g)
        if len(z) == 0:
            continue
        d = {m: my_dtw(z, s) for m, s in MZ.items()}
        best = min(d, key=d.get)
        d1, d2 = min(d.values()), max(d.values())
        res[c] = (medo["cluster_names"][str(medo["medoid_cluster"][best])], d1, (d2 - d1) / (d2 + d1))
    return res


ho_ids = [r["concept_id"] for r in csv.DictReader(open(HO / "typology/assignments.csv"))]
hind = pd.read_parquet(HO / "results/indicators/concept_year_indicators_hyd.parquet")
ha = my_assign(hind[hind.concept_id.isin(ho_ids)])
broad = "broad from the start (rapid interdisciplinary)"
kb = sum(v[0] == broad for v in ha.values())
frozen_lab = {r["concept_id"]: r["cluster_name"] for r in csv.DictReader(open(HO / "typology/assignments.csv"))}
out["heldout_share_broad"] = dict(rederived=kb / len(ha), reported=M["heldout_share_broad"], n=len(ha),
                                  label_agreement_with_frozen_pipeline=float(np.mean([ha[c][0] == frozen_lab[c] for c in ha])),
                                  match=close(kb / len(ha), M["heldout_share_broad"]))
med_margin = float(np.median([v[2] for v in ha.values()]))
out["heldout_median_margin"] = dict(rederived=med_margin, reported=M["heldout_median_margin"], match=close(med_margin, M["heldout_median_margin"], 1e-4))
mi = pd.read_parquet(WS / "results/mesh/mesh_indicators.parquet")
ma = my_assign(mi)
kbm = sum(v[0] == broad for v in ma.values())
out["mesh_share_broad"] = dict(rederived=kbm / len(ma), reported=M["mesh_share_broad"], n=len(ma), match=close(kbm / len(ma), M["mesh_share_broad"]))

# ---------- 2. type x CT / A_cont adjusted gap with statsmodels dummies (not pyfixest), held-out W1 read raw
def fe_gap(df, y):
    d = df.copy()
    d["dxe"] = d.d.astype(str) + "_" + d.e.astype(str)
    d = d[d.groupby("dxe").dxe.transform("size") > 1]  # drop singletons as pyfixest does
    f = smf.ols(f"{y} ~ BROAD + log_n_partner_tags + RD + C(dxe)", d).fit(cov_type="cluster", cov_kwds={"groups": pd.factorize(d.concept_id)[0]})
    return float(f.params["BROAD"]), float(f.pvalues["BROAD"]), int(f.nobs)


h = pd.read_parquet(E7 / "sealed/heldout_features.parquet")
need = ["A_cont", "CT", "prox_od", "RD", "log_n_partner_tags", "cov", "demic", "mean_topic_score", "boundary_share", "abstract_share", "mom_d", "log_centrality", "log_W1"]
h = h[(h.arm == "main") & h.kw5 & h.MAIN].dropna(subset=need)
h["BROAD"] = h.concept_id.map({c: float(v[0] == broad) for c, v in ha.items()})
h = h.dropna(subset=["BROAD"])
for y, key in (("CT", "typegap_CT_heldout_adj"), ("A_cont", "typegap_Acont_heldout_adj")):
    b, p, n = fe_gap(h, y)
    out[key] = dict(rederived=b, p=p, n=n, reported=M[key], match=close(b, M[key], 1e-6))
# placebo: shuffle type across concepts (200 draws) -> CT gap should be centred on 0 and the observed |b| in the tail
rng = np.random.default_rng(11)
cons = h.concept_id.unique()
lab = h.groupby("concept_id").BROAD.first()
obs = out["typegap_CT_heldout_adj"]["rederived"]
pl, pl_sig = [], 0
for _ in range(200):
    perm = dict(zip(cons, rng.permutation(lab.loc[cons].to_numpy())))
    hh = h.assign(BROAD=h.concept_id.map(perm))
    b, p, _ = fe_gap(hh, "CT")
    pl.append(b)
    pl_sig += p < 0.05
pl = np.array(pl)
out["placebo_shuffled_type_CT_heldout"] = dict(mean=float(pl.mean()), sd=float(pl.std()), share_p_lt_0_05=pl_sig / 200,
                                               perm_p_two_sided=float((np.sum(np.abs(pl) >= abs(obs)) + 1) / 201),
                                               passes_placebo=bool(abs(pl.mean()) < 0.02 and pl_sig / 200 < 0.12))

# ---------- 3. screen descriptives from the raw D2 parquet (plain groupby)
ev = pd.read_parquet(E7 / "results/screen_events_with_outcomes.parquet")
styp = {r["concept_id"]: r["cluster_name"] for r in csv.DictReader(open(E8 / "typology/assignments.csv"))}
s = ev[(ev.arm == "main") & (ev.fold == "screen") & ev.kw5 & ev.MAIN].dropna(subset=need)
s = s[s.concept_id.isin(styp)]
s["T"] = s.concept_id.map(lambda c: "BROAD" if styp[c] == broad else "LOCALISED")
for t in ("BROAD", "LOCALISED"):
    g = s[s["T"] == t]
    out[f"EST_rate_{t}_screen"] = dict(rederived=float(g.EST_bin.mean()), reported=M[f"EST_rate_{t}_screen"], match=close(float(g.EST_bin.mean()), M[f"EST_rate_{t}_screen"]))
    rs = float(g.groupby("concept_id").EST_bin.mean().mean())
    out[f"rooted_share_{t}_screen"] = dict(rederived=rs, reported=M[f"rooted_share_{t}_screen"], match=close(rs, M[f"rooted_share_{t}_screen"]))
    am = ev[(ev.arm == "main") & (ev.fold == "screen") & ev.MAIN & ev.concept_id.isin([c for c in styp if (styp[c] == broad) == (t == "BROAD")])]
    epc = float(am.groupby("concept_id").size().mean())
    out[f"entries_per_concept_{t}_screen"] = dict(rederived=epc, reported=M[f"entries_per_concept_{t}_screen"], match=close(epc, M[f"entries_per_concept_{t}_screen"]))
# placebo for the EST gap: shuffle type across concepts, gap should vanish
gaps = []
cs = s.concept_id.unique()
lb = s.groupby("concept_id")["T"].first()
for _ in range(500):
    pm = dict(zip(cs, rng.permutation(lb.loc[cs].to_numpy())))
    tt = s.concept_id.map(pm)
    gaps.append(s.EST_bin[tt == "BROAD"].mean() - s.EST_bin[tt == "LOCALISED"].mean())
obs_g = s.EST_bin[s["T"] == "BROAD"].mean() - s.EST_bin[s["T"] == "LOCALISED"].mean()
gaps = np.array(gaps)
out["placebo_shuffled_type_EST_gap_screen"] = dict(observed=float(obs_g), null_mean=float(gaps.mean()), null_sd=float(gaps.std()),
                                                   perm_p=float((np.sum(np.abs(gaps) >= abs(obs_g)) + 1) / 501))

# ---------- 4. pooled origin cross-tab with scipy chi2 (asymptotic) + shuffled placebo
rows = [(r["cluster_name"], r["origin_group"]) for r in csv.DictReader(open(E8 / "typology/assignments.csv"))] + \
       [(r["cluster_name"], r["origin_group"]) for r in csv.DictReader(open(HO / "typology/assignments.csv"))]
tab = pd.crosstab(pd.Series([a for a, _ in rows]), pd.Series([b for _, b in rows]))
chi, p, dof, _ = chi2_contingency(tab)
V = math.sqrt(chi / (tab.to_numpy().sum() * (min(tab.shape) - 1)))
out["crosstab_pooled_origin"] = dict(chi2_asymptotic_p=float(p), cramers_v=V, reported_V=M["crosstab_V_pooled_origin_group"],
                                     reported_perm_p=M["crosstab_p_perm_pooled_origin_group"], V_match=close(V, M["crosstab_V_pooled_origin_group"], 1e-9))
ty = np.array([a for a, _ in rows])
og = np.array([b for _, b in rows])
pp = []
for _ in range(200):
    t2 = pd.crosstab(pd.Series(rng.permutation(ty)), pd.Series(og))
    pp.append(chi2_contingency(t2)[1])
out["placebo_shuffled_origin_crosstab"] = dict(share_p_lt_0_05=float(np.mean(np.array(pp) < 0.05)), median_p=float(np.median(pp)))

# ---------- 5. lead-lag counts by plain csv counting
def ll(path):
    r = list(csv.DictReader(open(path)))
    both = [x for x in r if x["category"] in ("expansion_first", "same_year", "diffusion_first")]
    return len(r), len(both), sum(x["category"] == "expansion_first" for x in both)
a, b = ll(E8 / "results/leadlag_by_concept.csv"), ll(HO / "results/leadlag_by_concept.csv")
m_ = ll(WS / "results/mesh/mesh_leadlag_by_concept.csv")
out["leadlag"] = dict(pooled_main=dict(N=a[0] + b[0], n_both=a[1] + b[1], ef=a[2] + b[2]), mesh=dict(N=m_[0], n_both=m_[1], ef=m_[2]),
                      match=bool(a[1] + b[1] == M["leadlag_pooled_main_n_both"] and a[2] + b[2] == M["leadlag_pooled_main_n_expansion_first"]
                                 and m_[1] == M["mesh_expansion_first_N_both"] and m_[2] == M["mesh_expansion_first_X"]))

# ---------- 6. MeSH max z_within straight from the substrate parquet
z = pd.read_parquet(E4 / "results/features.parquet", columns=["z_within"]).z_within.dropna()
out["mesh_max_z_within"] = dict(rederived=float(z.max()), reported=M["mesh_max_z_within"], match=close(float(z.max()), M["mesh_max_z_within"]))

# ---------- 7. case rooted-vs-unrooted A_cont straight from the raw D2 parquet
for cid, nm in (("c_3a8d31dc5fbf", "wireless_backhaul"), ("c_9cceb3c510be", "einstein_podolsky_rosen_steering")):
    g = s[s.concept_id == cid]
    dlt = float(g[g.EST_bin == 1].A_cont.mean() - g[g.EST_bin == 0].A_cont.mean())
    k = f"case_{nm}_rooted_minus_unrooted_Acont"
    out[k] = dict(rederived=dlt, reported=M.get(k), match=close(dlt, M.get(k)))

(WS / "results/audit_rederive.json").write_text(json.dumps(out, indent=1, default=float))
for k, v in out.items():
    print(k, {kk: (round(vv, 4) if isinstance(vv, float) else vv) for kk, vv in v.items() if kk != "pooled_main"})
