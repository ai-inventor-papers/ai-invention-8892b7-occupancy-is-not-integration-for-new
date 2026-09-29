#!/usr/bin/env python3
"""Independent re-derivation of the headline numbers through different code paths (no analysis_* imports).

1. Label yield: E / E_alt / E_up onsets recomputed with vectorised pandas from the indicator panel.
2. E_up closure event study S (mean of per-k treated-minus-control-mean diffs over k = -3..0) from the indicator
   panel + matches file, via pandas merges; plus a within-pair label-swap control that must NOT reject.
3. E_up pooled-panel closure coefficient via statsmodels OLS with year fixed effects; plus shuffled futE control.
4. E_up rolling-origin AUCs and delta-AUC via a rank-sum (Mann-Whitney) AUC, not sklearn; plus shuffled labels.
Writes results/audit_headlines.json.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from scipy.stats import rankdata

ROOT = Path(__file__).resolve().parent
R = ROOT / "results"
ind = pd.read_parquet(R / "indicators" / "concept_year_indicators.parquet")
lab_stored = pd.read_parquet(R / "labels" / "emergence_screen.parquet")
out = {}

# ---------------------------------------------------------------- 1. labels
scr = ind[ind.fold == "screen"][["concept_id", "year", "vol", "pct", "pct_alt", "F"]].copy()
vol = scr.pivot(index="concept_id", columns="year", values="vol")
pct = scr.pivot(index="concept_id", columns="year", values="pct")
pcta = scr.pivot(index="concept_id", columns="year", values="pct_alt")
F = scr.groupby("concept_id").F.first()
rows = []
for c in F.index:
    for t in range(int(F[c]) + 3, int(F[c]) + 9):
        if t > 2019 or t in (2016, 2017, 2018):
            continue
        v = [vol.loc[c].get(t + k, 0) if np.isfinite(vol.loc[c].get(t + k, np.nan)) else 0 for k in range(1, 6)]
        up = (np.mean(v) >= 20) and (v[-1] >= 0.7 * v[0])
        g = pct.loc[c].get(t + 5, np.nan) - pct.loc[c].get(t, np.nan)
        ga = pcta.loc[c].get(t + 5, np.nan) - pcta.loc[c].get(t, np.nan)
        rows.append((c, t, int(up and g >= 20), int(up and ga >= 20), int(up)))
lab = pd.DataFrame(rows, columns=["concept_id", "t", "E", "E_alt", "E_up"])
win = lab[lab.t.between(2008, 2015)]
out["labels"] = {k: dict(n_rows=len(lab), rate=round(float(lab[k].mean()), 4),
                         n_onset=int(win.groupby("concept_id")[k].max().sum()),
                         n_never=int((win.groupby("concept_id")[k].max() == 0).sum()))
                 for k in ("E", "E_alt", "E_up")}
m = lab.merge(lab_stored[["concept_id", "t", "E", "E_alt", "E_up"]], on=["concept_id", "t"], suffixes=("", "_stored"))
out["labels"]["row_agreement_with_stored"] = {k: float((m[k] == m[f"{k}_stored"]).mean()) for k in ("E", "E_alt", "E_up")}

# ---------------------------------------------------------------- 2. event study (E_up closure)
mt = pd.read_csv(R / "event_study" / "matches_E_up.csv")
mt = mt[mt.n_controls > 0].copy()
pairs = []
for r in mt.itertuples():
    for ctrl in str(r.controls).split("|"):
        pairs.append((r.concept_id, int(r.t0), ctrl))
pairs = pd.DataFrame(pairs, columns=["treated", "t0", "ctrl"])
val = ind.set_index(["concept_id", "year"]).closure


def es_S(pairs: pd.DataFrame) -> float:
    per = []
    for k in range(-3, 1):
        p = pairs.assign(y=pairs.t0 + k)
        p["tv"] = [val.get((a, b), np.nan) for a, b in zip(p.treated, p.y)]
        p["cv"] = [val.get((a, b), np.nan) for a, b in zip(p.ctrl, p.y)]
        cm = p.groupby(["treated", "t0"]).agg(tv=("tv", "first"), cm=("cv", "mean")).dropna()
        per.append((cm.tv - cm.cm).mean() if len(cm) else np.nan)
    return float(np.nanmean(per))


S = es_S(pairs)
rng = np.random.default_rng(0)
treated = pairs.treated.unique()
boots = []
for _ in range(500):
    pick = rng.choice(treated, len(treated), replace=True)
    bp = pd.concat([pairs[pairs.treated == t].assign(treated=f"{t}#{i}") for i, t in enumerate(pick)])
    # keep lookups on the original id
    bp["orig"] = bp.treated.str.split("#").str[0]
    bp2 = bp.assign(treated=bp.orig)
    per = []
    for k in range(-3, 1):
        p = bp.assign(y=bp.t0 + k)
        p["tv"] = [val.get((a, b), np.nan) for a, b in zip(p.orig, p.y)]
        p["cv"] = [val.get((a, b), np.nan) for a, b in zip(p.ctrl, p.y)]
        cm = p.groupby(["treated", "t0"]).agg(tv=("tv", "first"), cm=("cv", "mean")).dropna()
        per.append((cm.tv - cm.cm).mean() if len(cm) else np.nan)
    boots.append(np.nanmean(per))
ci = np.percentile(boots, [2.5, 97.5]).tolist()
# control: randomly swap treated/control roles within each pair -> the contrast must vanish (CI covers 0)
sw = []
for _ in range(200):
    flip = rng.random(len(pairs)) < 0.5
    p2 = pairs.copy()
    p2.loc[flip, ["treated", "ctrl"]] = p2.loc[flip, ["ctrl", "treated"]].values
    sw.append(es_S(p2))
out["event_study_E_up_closure"] = dict(S=S, ci95_boot500=ci, n_treated=int(len(treated)),
                                       swap_control_mean=float(np.mean(sw)),
                                       swap_control_p95=np.percentile(sw, [2.5, 97.5]).tolist(),
                                       observed_outside_swap_range=bool(S < np.percentile(sw, 2.5) or S > np.percentile(sw, 97.5)))

# ---------------------------------------------------------------- 3. pooled panel (E_up closure)
on = win[win.E_up == 1].groupby("concept_id").t.min()
never = set(win.groupby("concept_id").E_up.max().loc[lambda s: s == 0].index)
d = ind[(ind.fold == "screen") & ind.concept_id.isin(set(on.index) | never) & (ind.age >= 0) & ind.year.between(2005, 2015)].copy()
d["t0"] = d.concept_id.map(on)
d = d[~(d.t0.notna() & (d.year > d.t0))]
d["futE"] = ((d.t0.notna()) & (d.t0 >= d.year) & (d.t0 <= d.year + 5)).astype(float)
d = d[np.isfinite(d.closure)]
fit = smf.ols("closure ~ futE + log_vol3 + age + C(year)", data=d).fit(cov_type="cluster", cov_kwds={"groups": pd.factorize(d.concept_id)[0]})
sh = []
for _ in range(200):
    dd = d.copy()
    # shuffle the concept-level future-emergence status across concepts
    cs = dd.concept_id.unique()
    perm = dict(zip(cs, rng.permutation(cs)))
    t0p = dd.drop_duplicates("concept_id").set_index("concept_id").t0
    dd["t0s"] = dd.concept_id.map(lambda c: t0p.get(perm[c]))
    dd["futE"] = ((dd.t0s.notna()) & (dd.t0s >= dd.year) & (dd.t0s <= dd.year + 5)).astype(float)
    if dd.futE.sum() < 3:
        continue
    sh.append(smf.ols("closure ~ futE + log_vol3 + age + C(year)", data=dd).fit().params["futE"])
out["pooled_panel_E_up_closure"] = dict(coef=float(fit.params["futE"]), cluster_se=float(fit.bse["futE"]),
                                        cluster_p=float(fit.pvalues["futE"]), n=int(len(d)),
                                        shuffled_coef_p95=np.percentile(sh, [2.5, 97.5]).tolist(),
                                        observed_outside_shuffled_range=bool(fit.params["futE"] < np.percentile(sh, 2.5)))

# ---------------------------------------------------------------- 4. prediction AUC (E_up, logistic)
def auc_rank(y, s):
    y = np.asarray(y).astype(int)
    r = rankdata(s)
    n1, n0 = y.sum(), len(y) - y.sum()
    return float((r[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0))


pr = pd.read_parquet(R / "prediction" / "predictions.parquet")
res = {}
for mdl in ("logit", "hgb"):
    g = pr[(pr.target == "E_up") & (pr.model == mdl)]
    piv = g.pivot_table(index=["concept_id", "t", "T"], columns="featureset", values="y_score")
    y = g.drop_duplicates(["concept_id", "t", "T"]).set_index(["concept_id", "t", "T"]).y_true.reindex(piv.index).values
    a_b, a_f = auc_rank(y, piv.BASELINE), auc_rank(y, piv.FULL)
    shuf = [auc_rank(rng.permutation(y), piv.FULL) for _ in range(500)]
    res[mdl] = dict(n=int(len(y)), n_pos=int(y.sum()), AUC_BASELINE=a_b, AUC_FULL=a_f, delta=a_f - a_b,
                    AUC_FULL_shuffled_labels_mean=float(np.mean(shuf)), AUC_FULL_shuffled_p95=np.percentile(shuf, [2.5, 97.5]).tolist())
out["prediction_E_up"] = res
(R / "audit_headlines.json").write_text(json.dumps(out, indent=1))
print(json.dumps(out, indent=1))
