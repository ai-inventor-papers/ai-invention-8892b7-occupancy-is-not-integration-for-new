"""Stages 5-6: network-only emergence labels, matched controls and the precursor event study.

E(c,t) = uptake (mean c-papers/yr over t+1..t+5 >= 20 and no fall > 30% from t+1 to t+5)
         AND centrality gain (strength percentile gain >= 20 points from t to t+5).
Screen fold only; held-out concepts and focal years 2016-18 are refused by config.assert_not_sealed.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd
from loguru import logger

import config as C
import lib_metrics as lm

S = C.SPEC


# ----------------------------------------------------------------------------- labels
def assign_groups(lab: pd.DataFrame, col: str) -> pd.DataFrame:
    """Onset t0 = first eligible t in the screen onset window with label `col` = 1; never = eligible, all 0."""
    lab = lab.copy()
    win = lab[lab.t.isin(S["screen_onset_years"])]
    onset = win[win[col] == 1].groupby("concept_id").t.min()
    never = {c for c in set(win.concept_id) if c not in onset.index}
    lab["onset"] = lab.concept_id.map(onset).astype("float")
    lab["group"] = np.where(lab.concept_id.isin(onset.index), "emerging",
                            np.where(lab.concept_id.isin(never), "never", "other"))
    lab["label_col"] = col
    return lab


def group_counts(lab: pd.DataFrame) -> dict:
    g = lab.drop_duplicates("concept_id")
    return dict(n_emerging=int((g.group == "emerging").sum()), n_never=int((g.group == "never").sum()),
                n_other=int((g.group == "other").sum()),
                onset_year_counts={str(int(k)): int(v) for k, v in g.onset.dropna().value_counts().sort_index().items()})

def _series(ind: pd.DataFrame, col: str) -> dict:
    return {(c, int(y)): v for c, y, v in zip(ind.concept_id, ind.year, ind[col])}


def label_one(vol: dict, pct: dict, c: str, t: int, h: int, uptake: float, gain: float, max_fall: float,
              pct_key: dict | None = None) -> tuple[int, int, int, float, float]:
    """Returns (E, E_up, E_cg, mean uptake, percentile gain) for horizon h."""
    pk = pct_key if pct_key is not None else pct
    ups = [vol.get((c, t + k), 0) for k in range(1, h + 1)]
    mean_up = float(np.mean(ups))
    up = int(mean_up >= uptake and ups[-1] >= (1 - max_fall) * ups[0])
    g = pk.get((c, t + h), np.nan) - pk.get((c, t), np.nan)
    cg = int(np.isfinite(g) and g >= gain)
    return up & cg, up, cg, mean_up, float(g)


def build_labels(ind: pd.DataFrame, pool: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    scr = pool[pool.fold == "screen"]
    C.assert_not_sealed(scr.concept_id)
    vol, pct, pct_alt = _series(ind, "vol"), _series(ind, "pct"), _series(ind, "pct_alt")
    sfc = _series(ind, "subfield_count")
    rows = []
    for r in scr.itertuples(index=False):
        F = int(r.F)
        for t in range(F + S["ages"][0], F + S["ages"][1] + 1):
            if t > S["t_max"] or t in S["sealed_focal_years"]:
                continue
            C.assert_not_sealed([r.concept_id], [t])
            E, up, cg, mu, g = label_one(vol, pct, r.concept_id, t, 5, S["E_uptake_mean"], S["E_pct_gain"], S["E_max_fall"])
            E3, up3, cg3, _, g3 = label_one(vol, pct, r.concept_id, t, 3, S["E_uptake_mean"], S["E_pct_gain"], S["E_max_fall"])
            Ealt, _, _, _, galt = label_one(vol, pct, r.concept_id, t, 5, S["E_uptake_mean"], S["E_pct_gain"], S["E_max_fall"],
                                            pct_key=pct_alt)
            cent_gain = np.nanmean([pct.get((r.concept_id, t + k), np.nan) for k in (3, 4, 5)]) - pct.get((r.concept_id, t), np.nan)
            rows.append(dict(concept_id=r.concept_id, t=t, age=t - F, F=F, F_band=r.F_band, origin_group=r.origin_group,
                             sense_check_fail=bool(r.sense_check_fail), E=E, E_up=up, E_cg=cg, E3=E3, E3_up=up3,
                             E3_cg=cg3, E_alt=Ealt, uptake_mean5=mu, pct_gain5=g, pct_gain3=g3, pct_alt_gain5=galt,
                             subfield_gain=sfc.get((r.concept_id, t + 5), np.nan) - sfc.get((r.concept_id, t), np.nan),
                             cent_gain=cent_gain))
    lab = pd.DataFrame(rows)
    lab = assign_groups(lab, "E")
    onset = lab.drop_duplicates("concept_id").set_index("concept_id").onset.dropna()
    never = set(lab.loc[lab.group == "never", "concept_id"])
    # sensitivity grid (E rate over eligible concept-years; share of concepts with an onset)
    grid = {}
    for u in S["sensitivity_grid"]["uptake"]:
        for gth in S["sensitivity_grid"]["pct_gain"]:
            e = [label_one(vol, pct, c, t, 5, u, gth, S["E_max_fall"])[0] for c, t in zip(lab.concept_id, lab.t)]
            e = np.array(e)
            w = lab.t.isin(S["screen_onset_years"]).values
            n_on = lab[w].assign(e=e[w]).groupby("concept_id").e.max().sum()
            grid[f"uptake{u}_gain{gth}"] = dict(E_rate=float(e.mean()), n_onset_concepts=int(n_on))
    # reference arm negative control (stationary concepts; t in 2008..2015, no age rule)
    ref = pool[pool.fold == "reference"]
    rr = []
    for c in ref.concept_id:
        for t in S["screen_onset_years"]:
            E, up, cg, mu, g = label_one(vol, pct, c, t, 5, S["E_uptake_mean"], S["E_pct_gain"], S["E_max_fall"])
            rr.append(dict(concept_id=c, t=t, E=E, gain=g))
    rr = pd.DataFrame(rr)
    # drift diagnostic: growth of reference-arm c-paper volume vs all-science growth (coverage / field growth)
    refv = ind[ind.concept_id.isin(set(ref.concept_id))]
    med_by_year = refv.groupby("year").agg(vol=("vol", "median"), pct=("pct", "median"))
    scrv = ind[ind.concept_id.isin(set(scr.concept_id))].groupby("year").pct.median()
    drift = dict(ref_median_vol={int(k): float(v) for k, v in med_by_year.vol.items()},
                 ref_median_pct={int(k): float(v) for k, v in med_by_year.pct.items()},
                 screen_median_pct={int(k): float(v) for k, v in scrv.items()})
    info = dict(n_label_rows=len(lab), n_concepts=int(lab.concept_id.nunique()), E_rate=float(lab.E.mean()),
                E_up_rate=float(lab.E_up.mean()), E_cg_rate=float(lab.E_cg.mean()), E3_rate=float(lab.E3.mean()),
                E_alt_rate=float(lab.E_alt.mean()),
                n_emerging=int(len(onset)), n_never=len(never), n_other=int(lab.loc[lab.group == "other", "concept_id"].nunique()),
                onset_year_counts={str(int(k)): int(v) for k, v in onset.value_counts().sort_index().items()},
                by_band_group=lab.drop_duplicates("concept_id").groupby(["F_band", "origin_group", "group"]).size()
                .rename("n").reset_index().to_dict("records"),
                sensitivity_grid=grid,
                reference_arm=dict(n_concepts=int(rr.concept_id.nunique()), E_rate=float(rr.E.mean()),
                                   median_abs_pct_gain5=float(rr.gain.abs().median()),
                                   n_concepts_ever_E=int(rr.groupby("concept_id").E.max().sum()), drift=drift),
                variants={c: group_counts(assign_groups(lab, c)) for c in ("E", "E_alt", "E_up", "E_cg")})
    logger.info(f"labels: E rate {info['E_rate']:.3f}; emerging {info['n_emerging']}, never {info['n_never']}; "
                f"reference E rate {info['reference_arm']['E_rate']:.3f}")
    return lab, info


# ----------------------------------------------------------------------------- matching
def match(lab: pd.DataFrame, ind: pd.DataFrame, rng_seed: int = 0, band: bool = True, origin: bool = True,
          caliper: float = S["match"]["vol_caliper"], widen: float = S["match"]["widen"],
          treated_onsets: dict | None = None, never_set: set | None = None, exclude_self: bool = False) -> pd.DataFrame:
    """1:ratio nearest-neighbour matching (with replacement) on log vol3 at t0 within band x origin group."""
    info = lab.drop_duplicates("concept_id").set_index("concept_id")
    vol3 = {(c, int(y)): v for c, y, v in zip(ind.concept_id, ind.year, ind.vol3)}
    onsets = treated_onsets if treated_onsets is not None else lab[lab.group == "emerging"].drop_duplicates("concept_id") \
        .set_index("concept_id").onset.astype(int).to_dict()
    never = never_set if never_set is not None else set(lab.loc[lab.group == "never", "concept_id"])
    out = []
    for c, t0 in onsets.items():
        v = vol3.get((c, t0), 0)
        cands = [n for n in never if (not band or info.loc[n, "F_band"] == info.loc[c, "F_band"])
                 and (not origin or info.loc[n, "origin_group"] == info.loc[c, "origin_group"])
                 and (not exclude_self or n != c) and vol3.get((n, t0), 0) > 0]
        chosen, widened = [], False
        for cal in (caliper, widen):
            ok = [(abs(math.log(vol3[(n, t0)]) - math.log(max(v, 1))), n) for n in cands
                  if v > 0 and abs(vol3[(n, t0)] / v - 1) <= cal]
            if ok:
                ok.sort()
                chosen = [n for _, n in ok[: S["match"]["ratio"]]]
                widened = cal == widen
                break
        out.append(dict(concept_id=c, t0=t0, controls=chosen, n_controls=len(chosen), widened=widened,
                        vol3_t0=v))
    return pd.DataFrame(out)


def balance(m: pd.DataFrame, ind: pd.DataFrame, lab: pd.DataFrame) -> list:
    val = ind.set_index(["concept_id", "year"])
    covs = {"log_vol3": "log_vol3", "age": "age", "log_strength": None, "H": "H"}
    never = sorted(set(lab.loc[lab.group == "never", "concept_id"]))
    rows = []
    for name, col in covs.items():
        def g(c, y):
            try:
                x = val.loc[(c, y)]
            except KeyError:
                return np.nan
            return math.log1p(x["strength"]) if col is None else x[col]
        tr = [g(r.concept_id, r.t0) for r in m.itertuples()]
        before = [g(n, r.t0) for r in m.itertuples() for n in never]
        after = [np.nanmean([g(n, r.t0) for n in r.controls]) if r.controls else np.nan for r in m.itertuples()]
        trm = [a for a, r in zip(tr, m.itertuples()) if r.controls]
        after = [a for a in after if np.isfinite(a)]
        rows.append(dict(covariate=name, smd_before=lm.smd(tr, before), smd_after=lm.smd(trm, after),
                         mean_treated=float(np.nanmean(tr)) if tr else np.nan,
                         mean_controls_after=float(np.nanmean(after)) if after else np.nan))
    return rows


# ----------------------------------------------------------------------------- event study
def es_matrix(m: pd.DataFrame, ind: pd.DataFrame, col: str) -> tuple[np.ndarray, list]:
    """Per-treated x relative-year difference matrix (treated - mean of matched controls)."""
    val = {(c, int(y)): v for c, y, v in zip(ind.concept_id, ind.year, ind[col].astype(float))}
    ks = S["es_rel_years"]
    mm = m[m.n_controls > 0]
    M = np.full((len(mm), len(ks)), np.nan)
    contrib = []
    for i, r in enumerate(mm.itertuples()):
        for j, k in enumerate(ks):
            y = r.t0 + k
            tv = val.get((r.concept_id, y), np.nan)
            cv = np.array([val.get((n, y), np.nan) for n in r.controls], dtype=float)
            cm = float(np.nanmean(cv)) if np.isfinite(cv).any() else np.nan
            if np.isfinite(tv) and np.isfinite(cm):
                M[i, j] = tv - cm
            contrib.append(dict(concept_id=r.concept_id, t0=r.t0, k=k, indicator=col, treated=tv, control_mean=cm,
                                controls="|".join(r.controls)))
    return M, contrib


def es_stats(M: np.ndarray, B: int, seed: int) -> dict:
    ks = S["es_rel_years"]
    lo, hi = S["es_summary_window"]
    wk = [j for j, k in enumerate(ks) if lo <= k <= hi]
    with np.errstate(all="ignore"):
        import warnings
        warnings.simplefilter("ignore", RuntimeWarning)
        diff = np.nanmean(M, axis=0) if len(M) else np.full(len(ks), np.nan)
        Sp = float(np.nanmean(diff[wk])) if np.isfinite(diff[wk]).any() else np.nan
        rng = np.random.default_rng(seed)
        bd = np.full((B, len(ks)), np.nan)
        bS = np.full(B, np.nan)
        if len(M) >= 2:
            for b in range(B):
                idx = rng.integers(0, len(M), len(M))
                d = np.nanmean(M[idx], axis=0)
                bd[b] = d
                bS[b] = np.nanmean(d[wk]) if np.isfinite(d[wk]).any() else np.nan
    ok = np.isfinite(bS)
    if ok.sum() < 10:
        return dict(diff_k=diff.tolist(), n_k=np.isfinite(M).sum(0).tolist(), S=Sp, ci=[np.nan, np.nan], se=np.nan,
                    p=np.nan, ci_k=[[np.nan, np.nan]] * len(ks), n_treated=len(M))
    ci = np.percentile(bS[ok], [2.5, 97.5]).tolist()
    p = 2 * min(np.mean(bS[ok] <= 0), np.mean(bS[ok] >= 0))
    p = float(max(p, 1.0 / ok.sum()))
    ci_k = [np.nanpercentile(bd[:, j], [2.5, 97.5]).tolist() if np.isfinite(bd[:, j]).sum() > 10 else [np.nan, np.nan]
            for j in range(len(ks))]
    return dict(diff_k=diff.tolist(), n_k=np.isfinite(M).sum(0).astype(int).tolist(), S=Sp, ci=ci,
                se=float(np.nanstd(bS[ok], ddof=1)), p=min(1.0, p), ci_k=ci_k, n_treated=len(M))


def pooled_panel(lab: pd.DataFrame, ind: pd.DataFrame, cols: list[str], B: int) -> dict:
    """F2 alternative: precursor ~ futE + log vol3 + age + year FE on all screen concept-years, concept-cluster bootstrap."""
    grp = lab.drop_duplicates("concept_id").set_index("concept_id")
    d = ind[ind.concept_id.isin(grp.index[grp.group.isin(["emerging", "never"])])].copy()
    d = d[(d.age >= 0) & (d.year >= 2005) & (d.year <= 2015)]
    on = grp.onset.to_dict()
    d["futE"] = [(1.0 if (np.isfinite(on.get(c, np.nan)) and y <= on[c] <= y + 5) else 0.0) for c, y in zip(d.concept_id, d.year)]
    d = d[[not (np.isfinite(on.get(c, np.nan)) and y > on[c]) for c, y in zip(d.concept_id, d.year)]]
    out = {}
    years = sorted(d.year.unique())
    for col in cols:
        dd = d[np.isfinite(d[col].astype(float))]
        if len(dd) < 30 or dd.futE.sum() < 5:
            out[col] = dict(n=len(dd), coef=np.nan, ci=[np.nan, np.nan])
            continue
        X = np.column_stack([np.ones(len(dd)), dd.futE, dd.log_vol3, dd.age] +
                            [(dd.year == y).astype(float) for y in years[1:]])
        yv = dd[col].astype(float).values
        coef = np.linalg.lstsq(X, yv, rcond=None)[0][1]
        concepts = dd.concept_id.values
        uc = np.unique(concepts)
        rows_by = {c: np.where(concepts == c)[0] for c in uc}
        rng = np.random.default_rng(7)
        bs = []
        for _ in range(B):
            pick = rng.choice(uc, len(uc), replace=True)
            ii = np.concatenate([rows_by[c] for c in pick])
            Xb = X[ii]
            if Xb[:, 1].sum() < 2:
                continue
            bs.append(np.linalg.lstsq(Xb, yv[ii], rcond=None)[0][1])
        bs = np.array(bs)
        sd = float(np.nanstd(yv))
        out[col] = dict(n=len(dd), n_concepts=len(uc), n_futE_rows=int(dd.futE.sum()), coef=float(coef),
                        coef_in_sd=float(coef / sd) if sd > 0 else np.nan,
                        ci=np.percentile(bs, [2.5, 97.5]).tolist() if len(bs) > 20 else [np.nan, np.nan],
                        p=float(max(2 * min(np.mean(bs <= 0), np.mean(bs >= 0)), 1 / max(1, len(bs)))) if len(bs) > 20 else np.nan)
    return out


PRIMARY = {"accretion": ("accretion_shift_rar", "accretion_shift_raw", "accretion_shift_rar_res"),
           "closure": ("closure", "closure_raw", "closure_res"),
           "participation": ("P_rar", "P_raw", "P_rar_res")}
REFERENCE_ROWS = ["log_vol3", "pct", "strength_growth"]
EXPLORATORY = ["new_relation_rate", "neigh_growth", "novelty", "beta_sim_rar", "beta_sne_rar", "sne_share_rar", "wmz",
               "btw_pct", "btw_change", "comm_change", "n_comm_touched", "subfield_count", "H", "H_rar", "RS", "burst_state",
               "accretion_shift_rar5", "P_rar_m5", "pct_alt"]


def run_event_study(lab: pd.DataFrame, ind: pd.DataFrame) -> tuple[dict, pd.DataFrame, pd.DataFrame]:
    B = S["bootstrap"]
    m = match(lab, ind)
    n_tr = len(m)
    res: dict = dict(n_treated=n_tr, n_matched=int((m.n_controls > 0).sum()),
                     match_rate=float((m.n_controls > 0).mean()) if n_tr else np.nan,
                     widened_share=float(m.loc[m.n_controls > 0, "widened"].mean()) if (m.n_controls > 0).any() else np.nan,
                     mean_controls=float(m.loc[m.n_controls > 0, "n_controls"].mean()) if (m.n_controls > 0).any() else np.nan,
                     n_unique_controls=len({c for cs in m.controls for c in cs}))
    res["balance"] = balance(m, ind, lab) if n_tr else []
    contrib_all, table = [], []
    sd_pool = {}
    scr = ind[(ind.fold == "screen") & (ind.year <= 2015)]
    for fam, versions in PRIMARY.items():
        for vname, col in zip(("primary", "raw", "res"), versions):
            M, contrib = es_matrix(m, ind, col)
            contrib_all += contrib
            st = es_stats(M, B, seed=lm.stable_seed(col) % 2**31)
            sd = float(scr[col].astype(float).std())
            sd_pool[col] = sd
            st.update(family=fam, version=vname, indicator=col, mde=2.8 * st["se"] if np.isfinite(st["se"]) else np.nan,
                      pooled_sd=sd)
            st["mde_in_sd"] = st["mde"] / sd if sd and np.isfinite(st["mde"]) else np.nan
            # CI convergence check (500 vs 1000 reps)
            st500 = es_stats(M, 500, seed=lm.stable_seed(col) % 2**31 + 1)
            if np.isfinite(st["ci"][0]) and np.isfinite(st500["ci"][0]):
                width = st["ci"][1] - st["ci"][0]
                st["ci_change_500_vs_1000"] = float(max(abs(st["ci"][0] - st500["ci"][0]), abs(st["ci"][1] - st500["ci"][1])) / width) if width > 0 else np.nan
            table.append(st)
    # Holm over the three pre-named primaries (predicted sign +)
    prim = [t for t in table if t["version"] == "primary"]
    adj = lm.holm([t["p"] for t in prim])
    for t, a in zip(prim, adj):
        t["p_holm"] = a
        t["sign_as_predicted"] = bool(np.isfinite(t["S"]) and t["S"] > 0)
    for col in REFERENCE_ROWS + EXPLORATORY:
        if col not in ind.columns:
            continue
        M, contrib = es_matrix(m, ind, col)
        contrib_all += contrib
        st = es_stats(M, B, seed=lm.stable_seed(col) % 2**31)
        st.update(family="reference" if col in REFERENCE_ROWS else "exploratory", version="-", indicator=col,
                  mde=2.8 * st["se"] if np.isfinite(st["se"]) else np.nan)
        table.append(st)
    expl = [t for t in table if t["family"] == "exploratory"]
    for t, q in zip(expl, lm.bh([t["p"] if t["n_treated"] >= 10 else np.nan for t in expl])):
        t["q_bh"] = q
    res["table"] = table
    # placebo: never-emerging concepts with pseudo-onsets drawn from the treated t0 distribution (same band where possible)
    rng = np.random.default_rng(11)
    never = sorted(set(lab.loc[lab.group == "never", "concept_id"]))
    info = lab.drop_duplicates("concept_id").set_index("concept_id")
    t0s = m.t0.values if n_tr else np.array(S["screen_onset_years"])
    pseudo = {}
    for c in never:
        same = m[m.concept_id.map(lambda x: info.loc[x, "F_band"]) == info.loc[c, "F_band"]].t0.values if n_tr else []
        src = same if len(same) else t0s
        pseudo[c] = int(rng.choice(src))
    pm = match(lab, ind, treated_onsets=pseudo, never_set=set(never), exclude_self=True)
    pl = {}
    for fam, versions in PRIMARY.items():
        M, _ = es_matrix(pm, ind, versions[0])
        st = es_stats(M, B, seed=99)
        pl[versions[0]] = dict(S=st["S"], ci=st["ci"], p=st["p"], n_treated=st["n_treated"],
                               covers_zero=bool(np.isfinite(st["ci"][0]) and st["ci"][0] <= 0 <= st["ci"][1]))
    res["placebo"] = dict(n_pseudo=len(pseudo), match_rate=float((pm.n_controls > 0).mean()) if len(pm) else np.nan, results=pl)
    # relaxed matching (sensitivity; band only, no origin group)
    mr = match(lab, ind, origin=False)
    rel = {}
    for fam, versions in PRIMARY.items():
        M, _ = es_matrix(mr, ind, versions[0])
        st = es_stats(M, B, seed=5)
        rel[versions[0]] = dict(S=st["S"], ci=st["ci"], p=st["p"], n_treated=st["n_treated"])
    res["relaxed_matching_band_only"] = dict(match_rate=float((mr.n_controls > 0).mean()) if len(mr) else np.nan, results=rel)
    # F2 pooled panel alternative (all screen concept-years)
    res["pooled_panel"] = pooled_panel(lab, ind, [v[0] for v in PRIMARY.values()] + [v[1] for v in PRIMARY.values()] +
                                       ["pct", "accretion_shift_rar5", "P_rar_m5"], B)
    prim_cols = [v[0] for v in PRIMARY.values()]
    ph = lm.holm([res["pooled_panel"].get(c, {}).get("p", np.nan) for c in prim_cols])
    for c, a in zip(prim_cols, ph):
        if c in res["pooled_panel"]:
            res["pooled_panel"][c]["p_holm"] = a
    logger.info(f"event study: treated {n_tr}, match rate {res['match_rate']}")
    return res, pd.DataFrame(contrib_all), m
