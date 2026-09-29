"""STEPS 4-8: emergence labels, matched controls, event study, rolling-origin prediction, patterns.

Only this module opens outcomes (volume and centrality in W2 = t+1..t+5)."""

from __future__ import annotations

import hashlib
import json

import numpy as np
import pandas as pd
from loguru import logger
from scipy.stats import kendalltau
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

import rq1_spec as S

VOL_KEY = {"PRIMARY": "tm", "SENS1": "s1", "SENS2": "mi"}


# =================================================================== STEP 4 labels
def label_table(feat: pd.DataFrame, concepts: pd.DataFrame) -> pd.DataFrame:
    """E_vol / E_cent / E for every concept and t in 2005..2019 under the three volume definitions."""
    pcol = "wdeg_pctl_focal" if S.E_CENT_REFERENCE == "focal" else "wdeg_pctl"
    pct_lut = {(c, y): v for c, y, v in zip(feat.concept_id, feat.year, feat[pcol])}
    pct_all_lut = {(c, y): v for c, y, v in zip(feat.concept_id, feat.year, feat.wdeg_pctl)}
    rows = []
    cmeta = concepts.set_index("concept_id")
    for cid in concepts.concept_id:
        F = int(cmeta.at[cid, "F"])
        de = int(cmeta.at[cid, "de_year"])
        pct = {y: pct_lut.get((cid, y), np.nan) for y in S.YEARS}
        pct = {y: (0.0 if pd.isna(v) else float(v)) for y, v in pct.items()}  # isolated focal node = bottom
        pall = {y: pct_all_lut.get((cid, y), np.nan) for y in S.YEARS}
        pall = {y: (0.0 if pd.isna(v) else float(v)) for y, v in pall.items()}
        for t in range(2005, S.T_MAX + 1):
            r = {"concept_id": cid, "t": t, "age": t - F, "F": F}
            r["in_age_range"] = S.AGE_RANGE[0] <= t - F <= S.AGE_RANGE[1]
            r["E_cent"] = int(pct[t + S.HORIZON] - pct[t] >= S.E_PCTL_GAIN)
            r["pctl_gain"] = pct[t + S.HORIZON] - pct[t]
            r["E_cent_allnodes"] = int(pall[t + S.HORIZON] - pall[t] >= S.E_PCTL_GAIN)
            r["pctl_gain_allnodes"] = pall[t + S.HORIZON] - pall[t]
            r["E_allnode_PRIMARY"] = 0  # filled below once E_vol_PRIMARY is known
            for vd, k in VOL_KEY.items():
                V = np.array([float(cmeta.at[cid, f"{k}_{y}"]) for y in range(t + 1, t + S.HORIZON + 1)])
                ev = int(V.mean() >= S.E_MIN_MEAN and V[-1] >= (1 - S.E_MAX_FALL) * V[0])
                r[f"E_vol_{vd}"] = ev
                r[f"E_{vd}"] = int(ev and r["E_cent"])
                r[f"V_t_{vd}"] = float(cmeta.at[cid, f"{k}_{t}"])
            r["E_allnode_PRIMARY"] = int(r["E_vol_PRIMARY"] and r["E_cent_allnodes"])
            # SENS2: MeSH-indexed series is structurally zero before DateEstablished
            r["sens2_valid"] = t >= de
            rows.append(r)
    return pd.DataFrame(rows)


def onsets(lab: pd.DataFrame, vd: str, outcome: str | None = None, t_max: int = S.T_MAX) -> dict[str, int]:
    col = outcome or f"E_{vd}"
    u = lab[lab.in_age_range & (lab.t <= t_max)]
    if vd == "SENS2":
        u = u[u.sens2_valid]
    u = u[u[col] == 1]
    return u.groupby("concept_id").t.min().to_dict()


# =================================================================== STEP 5 matching
def match_controls(lab: pd.DataFrame, concepts: pd.DataFrame, onset: dict[str, int], vd: str,
                   outcome_col: str, group_col: str = "origin_field", eligible: set | None = None,
                   check_label: bool = True) -> tuple[list[dict], dict]:
    """1:3 nearest-volume matching within F-band x group, +-20% (widen to +-30%), with replacement."""
    cm = concepts.set_index("concept_id")
    L = lab.set_index(["concept_id", "t"])
    sets = []
    n20 = n30 = n_any = 0
    pool = [c for c in concepts.concept_id if eligible is None or c in eligible]
    for c, ts in sorted(onset.items()):
        if eligible is not None and c not in eligible:
            continue
        Vc = float(L.at[(c, ts), f"V_t_{vd}"])
        cands = []
        for c2 in pool:
            if c2 == c or cm.at[c2, "F_band"] != cm.at[c, "F_band"] or cm.at[c2, group_col] != cm.at[c, group_col]:
                continue
            o2 = onset.get(c2)
            if o2 is not None and o2 <= ts:
                continue
            if check_label and L.at[(c2, ts), outcome_col] == 1:
                continue
            V2 = float(L.at[(c2, ts), f"V_t_{vd}"])
            rel = abs(V2 / Vc - 1) if Vc > 0 else (0.0 if V2 == 0 else np.inf)
            cands.append((abs(np.log1p(V2) - np.log1p(Vc)), rel, c2))
        cands.sort()
        tol = S.MATCH_VOL_TOL
        ctrl = [x for x in cands if x[1] <= tol][: S.MATCH_RATIO]
        if len(ctrl) < S.MATCH_RATIO:
            tol = S.MATCH_VOL_TOL_WIDE
            ctrl = [x for x in cands if x[1] <= tol][: S.MATCH_RATIO]
        full = len(ctrl) == S.MATCH_RATIO
        n20 += int(full and tol == S.MATCH_VOL_TOL)
        n30 += int(full)
        n_any += int(len(ctrl) > 0)
        sets.append({"concept_id": c, "t_star": ts, "controls": [x[2] for x in ctrl], "tol": tol,
                     "k": len(ctrl), "V": Vc})
    n = len(sets)
    info = {"n_emerging": n, "match_rate_3_at_20pct": n20 / n if n else np.nan,
            "match_rate_3_at_30pct": n30 / n if n else np.nan, "match_rate_any": n_any / n if n else np.nan,
            "F7_all_available_controls": bool(n and n30 / n < 0.5),
            "n_controls_total": int(sum(s["k"] for s in sets)),
            "n_unique_controls": len({c for s in sets for c in s["controls"]})}
    return sets, info


# =================================================================== STEP 6 event study
def set_matrices(sets: list[dict], feat_idx: pd.DataFrame, col: str) -> list[np.ndarray]:
    """For each matched set: array (1 + k) x len(EVENT_REL); row 0 = emerging. rel k <-> year t*+1+k."""
    out = []
    for s in sets:
        if s["k"] == 0:
            continue
        yrs = [s["t_star"] + 1 + k for k in S.EVENT_REL]
        mem = [s["concept_id"]] + s["controls"]
        M = np.full((len(mem), len(yrs)), np.nan)
        for i, c in enumerate(mem):
            for j, y in enumerate(yrs):
                if (c, y) in feat_idx.index:
                    M[i, j] = feat_idx.at[(c, y), col]
        out.append(M)
    return out


def _diffs(mats: list[np.ndarray], pick: np.ndarray | None = None) -> np.ndarray:
    """diff_{i,k} = emerging - mean(controls); pick[i] = which row plays 'emerging' (permutation null)."""
    D = np.full((len(mats), len(S.EVENT_REL)), np.nan)
    for i, M in enumerate(mats):
        e = 0 if pick is None else pick[i]
        rest = np.delete(M, e, axis=0)
        with np.errstate(all="ignore"):
            cmean = np.nanmean(rest, axis=0) if rest.shape[0] else np.full(M.shape[1], np.nan)
        D[i] = M[e] - cmean
    return D


def _summ(D: np.ndarray, w_idx: list[int]) -> tuple[np.ndarray, float]:
    with np.errstate(all="ignore"):
        dk = np.nanmean(D, axis=0)
        return dk, float(np.nanmean(dk[w_idx]))


def event_study(mats: list[np.ndarray], rng: np.random.Generator, sd_ref: float, do_mde: bool = True) -> dict:
    w_idx = [S.EVENT_REL.index(k) for k in S.PRIMARY_EVENT_WINDOW]
    D = _diffs(mats)
    n = len(mats)
    res = {"n_sets": n, "n_controls": int(sum(M.shape[0] - 1 for M in mats)),
           "n_eff": int((~np.isnan(D[:, w_idx])).any(axis=1).sum()) if n else 0,
           "n_at_rel": (~np.isnan(D)).sum(axis=0).tolist() if n else [0] * len(S.EVENT_REL)}
    if n == 0 or np.all(np.isnan(D)):
        res.update({"d_k": [np.nan] * len(S.EVENT_REL), "D": np.nan, "ci_k": [(np.nan, np.nan)] * len(S.EVENT_REL),
                    "ci_D": (np.nan, np.nan), "p_boot": np.nan, "p_boot_k": [np.nan] * len(S.EVENT_REL),
                    "se_D": np.nan, "mde_sd": np.nan, "D_sd": np.nan})
        return res
    dk, Dp = _summ(D, w_idx)
    idx = rng.integers(0, n, size=(S.BOOT, n))
    valid = ~np.isnan(D)
    Dz = np.where(valid, D, 0.0)
    sums = Dz[idx].sum(axis=1)  # B x K
    cnts = valid[idx].sum(axis=1)
    with np.errstate(all="ignore"):
        bk = sums / cnts
        bD = np.nanmean(bk[:, w_idx], axis=1)

    def pval(x: np.ndarray) -> float:
        x = x[~np.isnan(x)]
        if len(x) == 0:
            return np.nan
        return float(min(1.0, 2 * min((x <= 0).mean(), (x >= 0).mean())))

    res.update({"d_k": dk.tolist(), "D": Dp,
                "ci_k": [tuple(np.nanpercentile(bk[:, j], [2.5, 97.5])) if np.isfinite(bk[:, j]).any() else (np.nan, np.nan)
                         for j in range(len(S.EVENT_REL))],
                "ci_D": tuple(np.nanpercentile(bD, [2.5, 97.5])), "p_boot": pval(bD),
                "p_boot_k": [pval(bk[:, j]) for j in range(len(S.EVENT_REL))],
                "se_D": float(np.nanstd(bD)), "D_sd": Dp / sd_ref if sd_ref > 0 else np.nan})
    if do_mde:
        perm = np.empty(S.PERM_MDE)
        for b in range(S.PERM_MDE):
            pick = np.array([rng.integers(0, M.shape[0]) for M in mats])
            perm[b] = _summ(_diffs(mats, pick), w_idx)[1]
        se = float(np.nanstd(perm))
        res["mde_sd"] = 2.8 * se / sd_ref if sd_ref > 0 else np.nan
        res["perm_se"] = se
    else:
        res["mde_sd"] = np.nan
    return res


def holm(p: list[float]) -> list[float]:
    p = np.asarray(p, dtype=float)
    out = np.full(len(p), np.nan)
    ok = ~np.isnan(p)
    if not ok.any():
        return out.tolist()
    pv = p[ok]
    order = np.argsort(pv)
    m = len(pv)
    adj = np.empty(m)
    run = 0.0
    for r, i in enumerate(order):
        run = max(run, min(1.0, (m - r) * pv[i]))
        adj[i] = run
    out[ok] = adj
    return out.tolist()


def bh(p: list[float]) -> list[float]:
    p = np.asarray(p, dtype=float)
    out = np.full(len(p), np.nan)
    ok = ~np.isnan(p)
    if not ok.any():
        return out.tolist()
    pv = p[ok]
    m = len(pv)
    order = np.argsort(pv)
    q = pv[order] * m / np.arange(1, m + 1)
    q = np.minimum.accumulate(q[::-1])[::-1]
    res = np.empty(m)
    res[order] = np.minimum(q, 1.0)
    out[ok] = res
    return out.tolist()


# =================================================================== STEP 7 prediction
def feature_sets(vd: str, all_cols: list[str]) -> dict[str, list[str]]:
    k = VOL_KEY[vd]
    A1 = [f"logV_{k}", f"dlogV2_{k}", f"burst_active_{k}", f"burst_weight_{k}"]
    A2 = ["log_s", "growth", "dpctl_focal", "dlogk", "dbetw"]
    prec = ["accretion_share", "closure_lr", "dP", "d2_accretion_share", "d2_closure_lr", "d2_dP"]
    return {"A1_freq_burst": A1, "A2_degree_centrality": A2, "A": A1 + A2, "B": A1 + A2 + prec,
            "B_all": A1 + A2 + [c for c in all_cols if c not in A1 + A2],
            "C_entropy_BIASED": A1 + A2 + ["subfield_entropy", "d3_subfield_entropy"],
            "B_mp_aligned": A1 + A2 + ["accretion_shift_rar", "closure", "P_rar"]}


ALL_NET = ["s_pp", "k_pp", "wdeg_pctl", "wdeg_pctl_focal", "new_rel_rate", "new_rel_pp", "nbr_novelty", "beta_sor", "beta_sim",
           "beta_sne", "accretion_share", "closure_lr", "P", "z_within", "betw", "dP", "dz", "dbetw", "dpctl",
           "dk", "comm_change", "n_modules_touched", "growth_num_pp", "d2_accretion_share", "d2_closure_lr", "d2_dP"]


def _model() -> object:
    return make_pipeline(SimpleImputer(strategy="median"), StandardScaler(),
                         LogisticRegression(C=S.LOGREG["C"], class_weight=S.LOGREG["class_weight"],
                                            max_iter=S.LOGREG["max_iter"]))


def _fit_predict(tr: pd.DataFrame, te: pd.DataFrame, cols: list[str], y: str) -> np.ndarray:
    Xtr = tr[cols].to_numpy(dtype=float)
    keep = ~np.all(np.isnan(Xtr), axis=0)  # a column entirely missing in train cannot be imputed
    cols = [c for c, k in zip(cols, keep) if k]
    m = _model()
    m.fit(tr[cols].to_numpy(dtype=float), tr[y].to_numpy())
    return m.predict_proba(te[cols].to_numpy(dtype=float))[:, 1]


def rolling_origin(units: pd.DataFrame, fsets: dict, y: str) -> tuple[pd.DataFrame, dict]:
    preds, used, skipped = [], [], []
    for T in S.ORIGINS:
        te = units[units.t == T]
        tr = units[units.t <= T - S.TRAIN_LAG]
        assert (tr.t + S.HORIZON <= T).all(), "leakage: a training outcome is not observable at T"
        if len(te) == 0 or len(tr) < S.MIN_TRAIN_UNITS or tr[y].sum() < S.MIN_TRAIN_POS or tr[y].nunique() < 2:
            skipped.append({"T": T, "n_train": int(len(tr)), "n_train_pos": int(tr[y].sum()), "n_test": int(len(te))})
            continue
        out = te[["concept_id", "t", y]].copy()
        out["origin"] = T
        for name, cols in fsets.items():
            out[f"p_{name}"] = _fit_predict(tr, te, cols, y)
        preds.append(out)
        used.append({"T": T, "n_train": int(len(tr)), "n_train_pos": int(tr[y].sum()), "n_test": int(len(te)),
                     "n_test_pos": int(te[y].sum())})
    P = pd.concat(preds, ignore_index=True) if preds else pd.DataFrame()
    return P, {"origins_used": used, "origins_skipped": skipped}


def grouped_cv(units: pd.DataFrame, fsets: dict, y: str) -> pd.DataFrame:
    g = units.concept_id.map(lambda c: int(hashlib.sha1(c.encode()).hexdigest(), 16) % S.GROUPED_CV_FOLDS)
    preds = []
    for k in range(S.GROUPED_CV_FOLDS):
        tr, te = units[g != k], units[g == k]
        if tr[y].nunique() < 2 or len(te) == 0:
            continue
        out = te[["concept_id", "t", y]].copy()
        out["fold"] = k
        for name, cols in fsets.items():
            out[f"p_{name}"] = _fit_predict(tr, te, cols, y)
        preds.append(out)
    return pd.concat(preds, ignore_index=True) if preds else pd.DataFrame()


def _auc(yv: np.ndarray, p: np.ndarray) -> float:
    return float(roc_auc_score(yv, p)) if len(np.unique(yv)) == 2 else np.nan


def auc_boot(P: pd.DataFrame, y: str, a: str, b: str, rng: np.random.Generator) -> dict:
    """AUC_a, AUC_b, delta with concept-bootstrap 95% CIs over pooled predictions."""
    if len(P) == 0 or P[y].nunique() < 2:
        return {k: np.nan for k in ("auc_a", "auc_a_lo", "auc_a_hi", "auc_b", "auc_b_lo", "auc_b_hi", "delta",
                                    "delta_lo", "delta_hi", "prauc_a", "prauc_b", "p_delta_le0")}
    yv, pa, pb = P[y].to_numpy(), P[f"p_{a}"].to_numpy(), P[f"p_{b}"].to_numpy()
    res = {"auc_a": _auc(yv, pa), "auc_b": _auc(yv, pb),
           "prauc_a": float(average_precision_score(yv, pa)), "prauc_b": float(average_precision_score(yv, pb))}
    res["delta"] = res["auc_b"] - res["auc_a"]
    cids = P.concept_id.unique()
    rows_of = {c: np.where(P.concept_id.to_numpy() == c)[0] for c in cids}
    ba, bb = [], []
    for _ in range(S.BOOT):
        pick = rng.choice(cids, size=len(cids), replace=True)
        ix = np.concatenate([rows_of[c] for c in pick])
        if len(np.unique(yv[ix])) < 2:
            continue
        ba.append(_auc(yv[ix], pa[ix]))
        bb.append(_auc(yv[ix], pb[ix]))
    ba, bb = np.array(ba), np.array(bb)
    dd = bb - ba
    res.update({"auc_a_lo": float(np.percentile(ba, 2.5)), "auc_a_hi": float(np.percentile(ba, 97.5)),
                "auc_b_lo": float(np.percentile(bb, 2.5)), "auc_b_hi": float(np.percentile(bb, 97.5)),
                "delta_lo": float(np.percentile(dd, 2.5)), "delta_hi": float(np.percentile(dd, 97.5)),
                "p_delta_le0": float((dd <= 0).mean()), "n_boot_valid": int(len(dd))})
    return res


def auc_single(P: pd.DataFrame, y: str, a: str, rng: np.random.Generator) -> dict:
    if len(P) == 0 or P[y].nunique() < 2:
        return {"auc": np.nan, "lo": np.nan, "hi": np.nan, "prauc": np.nan}
    yv, pa = P[y].to_numpy(), P[f"p_{a}"].to_numpy()
    cids = P.concept_id.unique()
    rows_of = {c: np.where(P.concept_id.to_numpy() == c)[0] for c in cids}
    bs = []
    for _ in range(S.BOOT):
        ix = np.concatenate([rows_of[c] for c in rng.choice(cids, size=len(cids), replace=True)])
        if len(np.unique(yv[ix])) == 2:
            bs.append(_auc(yv[ix], pa[ix]))
    return {"auc": _auc(yv, pa), "lo": float(np.percentile(bs, 2.5)), "hi": float(np.percentile(bs, 97.5)),
            "prauc": float(average_precision_score(yv, pa))}


# =================================================================== STEP 8 patterns
def patterns(feat: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    net = feat[feat.k > 0]
    ref = {"beta_sim_median": float(net.beta_sim.median()), "dk_median": float(net.dk.median()),
           "growth_p90": float(np.nanpercentile(net.growth, S.PATTERN_GROWTH_PCTL))}
    out = []
    for cid, g in feat.sort_values("year").groupby("concept_id"):
        g = g.reset_index(drop=True)
        first = g.index[g.k > 0]
        rec = {"concept_id": cid, "incubation_expansion": False, "gradual_centralisation": False,
               "early_bridging": False, "first_network_year": np.nan}
        if len(first) == 0:
            out.append(rec)
            continue
        g = g.loc[first[0]:].reset_index(drop=True)
        rec["first_network_year"] = int(g.year.iloc[0])
        quiet = ((g.beta_sim < ref["beta_sim_median"]) & (g.dk < ref["dk_median"])).to_numpy()
        grow = (g.growth > ref["growth_p90"]).to_numpy()
        run = 0
        for i in range(len(g)):
            if quiet[i]:
                run += 1
                continue
            if run >= S.PATTERN_QUIET_YEARS and grow[i]:
                rec["incubation_expansion"] = True
                rec["incubation_year"] = int(g.year.iloc[i])
                break
            run = 0
        Pv, zv = g.P.to_numpy(dtype=float), g.z_within.to_numpy(dtype=float)
        L = len(g)
        for a in range(L):
            for b in range(a + S.PATTERN_CENTRAL_YEARS, L + 1):
                seg = slice(a, b)
                if np.any(np.isnan(Pv[seg])) or np.any(np.isnan(zv[seg])) or not np.all(Pv[seg] < S.PATTERN_P_LOW):
                    break
                tau = kendalltau(np.arange(b - a), zv[seg]).statistic
                if tau is not None and np.isfinite(tau) and tau > S.PATTERN_TAU:
                    rec["gradual_centralisation"] = True
                    rec["centralisation_start"] = int(g.year.iloc[a])
                    break
            if rec["gradual_centralisation"]:
                break
        e = g.head(S.PATTERN_EARLY_YEARS)
        rec["early_bridging"] = bool(((e.P > S.PATTERN_P_HIGH) | (e.betw_top_decile.fillna(False).astype(bool))).any())
        out.append(rec)
    return pd.DataFrame(out), ref


def boot_freq(x: np.ndarray, rng: np.random.Generator) -> tuple[float, float, float]:
    x = np.asarray(x, dtype=float)
    if len(x) == 0:
        return np.nan, np.nan, np.nan
    b = x[rng.integers(0, len(x), size=(S.BOOT, len(x)))].mean(axis=1)
    return float(x.mean()), float(np.percentile(b, 2.5)), float(np.percentile(b, 97.5))


# =================================================================== main-pool-aligned block
def mainpool_labels(lab: pd.DataFrame) -> pd.DataFrame:
    """E (all-node percentile), E_alt (focal percentile), E_up (uptake only), all with PRIMARY volume."""
    lab = lab.copy()
    lab["MP_E"] = (lab.E_vol_PRIMARY.astype(bool) & lab.E_cent_allnodes.astype(bool)).astype(int)
    lab["MP_E_alt"] = lab.E_PRIMARY.astype(int)
    lab["MP_E_up"] = lab.E_vol_PRIMARY.astype(int)
    return lab


def mainpool_groups(lab: pd.DataFrame, col: str) -> tuple[dict, set]:
    win = lab[lab.in_age_range]
    onset = win[win[col] == 1].groupby("concept_id").t.min().to_dict()
    never = set(win.concept_id) - set(onset)
    return onset, never


def mainpool_match(onset: dict, never: set, concepts: pd.DataFrame, feat: pd.DataFrame,
                   group_col: str = "origin_field") -> list[dict]:
    """Main-pool matching: never-emerging controls, same F-band and origin group, log vol3 caliper 0.2 then 0.3."""
    import math
    info = concepts.set_index("concept_id")
    vol3 = {(c, int(y)): v for c, y, v in zip(feat.concept_id, feat.year, feat.vol3)}
    out = []
    for c, t0 in sorted(onset.items()):
        v = vol3.get((c, t0), 0)
        cands = [n for n in never if info.at[n, "F_band"] == info.at[c, "F_band"]
                 and info.at[n, group_col] == info.at[c, group_col] and vol3.get((n, t0), 0) > 0]
        chosen, widened = [], False
        for cal in (S.MATCH_VOL_TOL, S.MATCH_VOL_TOL_WIDE):
            ok = sorted((abs(math.log(vol3[(n, t0)]) - math.log(max(v, 1))), n) for n in cands
                        if v > 0 and abs(vol3[(n, t0)] / v - 1) <= cal)
            if ok:
                chosen = [n for _, n in ok[: S.MATCH_RATIO]]
                widened = cal == S.MATCH_VOL_TOL_WIDE
                break
        out.append({"concept_id": c, "t0": int(t0), "controls": chosen, "n_controls": len(chosen), "widened": widened,
                    "vol3_t0": float(v)})
    return out


def mainpool_es(m: list[dict], feat_idx: dict, col: str, rng: np.random.Generator, sd_ref: float) -> dict:
    ks = S.MAINPOOL["es_rel_years"]
    lo, hi = S.MAINPOOL["es_summary_window"]
    wk = [j for j, k in enumerate(ks) if lo <= k <= hi]
    mm = [r for r in m if r["n_controls"] > 0]
    M = np.full((len(mm), len(ks)), np.nan)
    for i, r in enumerate(mm):
        for j, k in enumerate(ks):
            y = r["t0"] + k
            tv = feat_idx.get((r["concept_id"], y), np.nan)
            cv = np.array([feat_idx.get((n, y), np.nan) for n in r["controls"]], dtype=float)
            cm = float(np.nanmean(cv)) if np.isfinite(cv).any() else np.nan
            if np.isfinite(tv) and np.isfinite(cm):
                M[i, j] = tv - cm
    with np.errstate(all="ignore"):
        import warnings
        warnings.simplefilter("ignore", RuntimeWarning)
        diff = np.nanmean(M, axis=0) if len(M) else np.full(len(ks), np.nan)
        Sp = float(np.nanmean(diff[wk])) if np.isfinite(diff[wk]).any() else np.nan
        bd = np.full((S.BOOT, len(ks)), np.nan)
        bS = np.full(S.BOOT, np.nan)
        if len(M) >= 2:
            for b in range(S.BOOT):
                d = np.nanmean(M[rng.integers(0, len(M), len(M))], axis=0)
                bd[b] = d
                bS[b] = np.nanmean(d[wk]) if np.isfinite(d[wk]).any() else np.nan
    ok = np.isfinite(bS)
    res = {"diff_k": diff.tolist(), "n_k": np.isfinite(M).sum(0).astype(int).tolist(), "S": Sp,
           "n_treated": int(len(mm)), "n_controls": int(sum(r["n_controls"] for r in mm)),
           # treated units that contribute at least one finite difference inside the summary window
           "n_eff": int(np.isfinite(M[:, wk]).any(axis=1).sum()) if len(M) else 0}
    if ok.sum() < 10:
        res.update({"ci": [np.nan, np.nan], "se": np.nan, "p": np.nan, "ci_k": [[np.nan, np.nan]] * len(ks),
                    "mde": np.nan, "mde_in_sd": np.nan})
        return res
    p = 2 * min(np.mean(bS[ok] <= 0), np.mean(bS[ok] >= 0))
    se = float(np.nanstd(bS[ok], ddof=1))
    res.update({"ci": np.percentile(bS[ok], [2.5, 97.5]).tolist(), "se": se, "p": float(min(1.0, max(p, 1.0 / ok.sum()))),
                "ci_k": [np.nanpercentile(bd[:, j], [2.5, 97.5]).tolist() if np.isfinite(bd[:, j]).sum() > 10
                         else [np.nan, np.nan] for j in range(len(ks))],
                "mde": 2.8 * se, "mde_in_sd": 2.8 * se / sd_ref if sd_ref > 0 else np.nan})
    return res
