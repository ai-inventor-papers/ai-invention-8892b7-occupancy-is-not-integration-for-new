"""Independent re-derivation of the headline numbers (TODO audit). Different code paths from analysis.py/method.py:
labels are rebuilt from the raw data_out.json counts and from strength s re-ranked here (not wdeg_pctl_focal);
event-study differences use pandas merges; AUC uses the Mann-Whitney U formula; grouped CV uses a hand-written
median impute + z-score + sklearn LogisticRegression on numpy arrays. Placebo versions of each test must fail."""

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression

ROOT = Path(__file__).resolve().parent
RES = ROOT / "results"
import os
DS3 = Path(os.environ.get("AII_ITER1_GEN_ART", str(ROOT.parents[2] / "round-1" / "."))) / "gen_art_dataset_3"
out = {}

feat = pd.read_parquet(RES / "features.parquet")
raw = json.loads((DS3 / "data_out.json").read_text())
vol = {(r["input"]["concept_id"], int(y)): float(v) for r in raw for y, v in r["output"]["yearly_counts_textmatch"].items()}
F = {r["input"]["concept_id"]: int(r["input"]["F"]) for r in raw}

# ---- 1. labels from scratch: focal percentile = mid-rank of s among concepts with s > 0 in the same year
f = feat[["concept_id", "year", "s"]].copy()
pos = f[f.s > 0].copy()
pos["pct"] = pos.groupby("year").s.rank(method="average", pct=False)
pos["n"] = pos.groupby("year").s.transform("size")
pos["pct"] = 100 * (pos.pct - 0.5) / pos.n
pct = {(c, y): p for c, y, p in zip(pos.concept_id, pos.year, pos.pct)}
rows = []
for c, Fc in F.items():
    for t in range(Fc + 3, min(Fc + 8, 2019) + 1):
        W2 = [vol.get((c, y), 0.0) for y in range(t + 1, t + 6)]
        up = np.mean(W2) >= 20 and W2[-1] >= 0.7 * W2[0]
        gain = pct.get((c, t + 5), 0.0) - pct.get((c, t), 0.0)
        rows.append((c, t, int(up and gain >= 20), int(up)))
lab = pd.DataFrame(rows, columns=["concept_id", "t", "E", "E_up"])
onset = lab[lab.E == 1].groupby("concept_id").t.min()
out["n_units"] = len(lab)
out["n_emerging_PRIMARY"] = int(len(onset))
out["unit_rate_E"] = float(lab.E.mean())

# ---- 2. event-study D over rel -3..-1 (calendar t*-2..t*) from matched_sets.json, pandas path
sets = json.loads((RES / "matched_sets.json").read_text())
fv = feat.set_index(["concept_id", "year"])


def D_of(setlist, col, rng=None, B=0, placebo=False):
    recs = []
    for i, s in enumerate(setlist):
        if not s["controls"]:
            continue
        mem = [s["concept_id"]] + s["controls"]
        if placebo:  # a random member plays 'emerging'
            j = rng.integers(0, len(mem))
            mem = [mem[j]] + mem[:j] + mem[j + 1:]
        for y in range(s["t_star"] - 4, s["t_star"] + 1):
            k = y - s["t_star"] - 1
            e = fv[col].get((mem[0], y), np.nan)
            cs = [fv[col].get((c, y), np.nan) for c in mem[1:]]
            cm = np.nanmean(cs) if np.isfinite(cs).any() else np.nan
            recs.append((i, k, e - cm))
    d = pd.DataFrame(recs, columns=["set", "k", "diff"]).dropna()
    stat = d[d.k.isin([-3, -2, -1])].groupby("k")["diff"].mean().mean()
    if not B:
        return stat
    ids = d.set.unique()
    bs = []
    for _ in range(B):
        pick = rng.choice(ids, len(ids))
        dd = pd.concat([d[d.set == p] for p in pick])
        bs.append(dd[dd.k.isin([-3, -2, -1])].groupby("k")["diff"].mean().mean())
    return stat, np.nanpercentile(bs, [2.5, 97.5]).tolist()


rng = np.random.default_rng(7)
for key, col in [("PRIMARY|all", "accretion_share"), ("PRIMARY|all", "closure_lr"), ("PRIMARY|all", "dP"),
                 ("SENS1|all", "closure_lr")]:
    st, ci = D_of(sets[key], col, rng, B=400)
    plac = [D_of(sets[key], col, rng, placebo=True) for _ in range(100)]
    out[f"D {key} {col}"] = {"D": round(float(st), 4), "ci_400boot": [round(x, 4) for x in ci],
                             "placebo_mean": round(float(np.nanmean(plac)), 4),
                             "placebo_sd": round(float(np.nanstd(plac)), 4)}

# ---- 3. aligned E_up closure (never-emerging controls; recomputed from labels_mainpool_aligned matches in summary)
summ = json.loads((RES / "analysis_summary.json").read_text())
m = summ["mainpool_block"]["E_up"]["matches"]
recs = []
for s in m:
    if not s["controls"]:
        continue
    for k in range(-3, 1):
        y = s["t0"] + k
        e = fv["closure"].get((s["concept_id"], y), np.nan)
        cs = [fv["closure"].get((c, y), np.nan) for c in s["controls"]]
        if np.isfinite(e) and np.isfinite(cs).any():
            recs.append((k, e - np.nanmean(cs)))
d = pd.DataFrame(recs, columns=["k", "diff"])
out["S E_up closure (rel -3..0)"] = round(float(d.groupby("k")["diff"].mean().mean()), 4)


# ---- 4. grouped-CV delta AUC (B - A) for PRIMARY E with a different implementation
def auc_mw(y, p):
    y = np.asarray(y)
    r = pd.Series(p).rank().to_numpy()
    n1 = y.sum()
    n0 = len(y) - n1
    return (r[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0)


labp = pd.read_parquet(RES / "labels.parquet")
u = labp[labp.in_age_range][["concept_id", "t", "E_PRIMARY"]].merge(feat.rename(columns={"year": "t"}), on=["concept_id", "t"])
A = ["logV_tm", "dlogV2_tm", "burst_active_tm", "burst_weight_tm", "log_s", "growth", "dpctl_focal", "dlogk", "dbetw"]
Bc = A + ["accretion_share", "closure_lr", "dP", "d2_accretion_share", "d2_closure_lr", "d2_dP"]
fold = u.concept_id.map(lambda c: int(hashlib.sha1(c.encode()).hexdigest(), 16) % 5).to_numpy()


def cv_pred(cols, y):
    X = u[cols].to_numpy(float)
    p = np.zeros(len(u))
    for k in range(5):
        tr, te = fold != k, fold == k
        med = np.nanmedian(X[tr], axis=0)
        Xt = np.where(np.isnan(X), med, X)
        mu, sd = Xt[tr].mean(0), Xt[tr].std(0)
        sd[sd == 0] = 1
        Z = (Xt - mu) / sd
        p[te] = LogisticRegression(C=1.0, max_iter=5000).fit(Z[tr], y[tr]).predict_proba(Z[te])[:, 1]
    return p


y = u.E_PRIMARY.to_numpy()
pa, pb = cv_pred(A, y), cv_pred(Bc, y)
out["gcv AUC_A"], out["gcv AUC_B"] = round(auc_mw(y, pa), 4), round(auc_mw(y, pb), 4)
out["gcv delta"] = round(out["gcv AUC_B"] - out["gcv AUC_A"], 4)
yp = np.random.default_rng(3).permutation(y)  # placebo: shuffled labels
out["gcv placebo AUC_A"] = round(auc_mw(yp, cv_pred(A, yp)), 4)
out["n_pos_gcv"] = int(y.sum())

# ---- 5. early bridging frequency straight from features (P > 0.6 or top-decile betweenness in first 2 network years)
eb = []
for c, g in feat.sort_values("year").groupby("concept_id"):
    g = g[g.k > 0].head(2)
    eb.append(bool(((g.P > 0.6) | g.betw_top_decile.fillna(False).astype(bool)).any()))
out["early_bridging_freq"] = round(float(np.mean(eb)), 4)

print(json.dumps(out, indent=1))
(RES / "audit_rederivation.json").write_text(json.dumps(out, indent=1))
