"""Stages 8-9: three pre-specified structural patterns and a preliminary DTW + k-medoids typology."""
from __future__ import annotations

import numpy as np
import pandas as pd
from loguru import logger
from scipy.stats import fisher_exact, kendalltau
from sklearn.metrics import adjusted_mutual_info_score

import config as C

S = C.SPEC
PATS = ["INCUBATION_THEN_EXPANSION", "GRADUAL_CENTRALISATION", "EARLY_BRIDGING"]


def _runs(flags: list[bool]) -> list[tuple[int, int]]:
    out, start = [], None
    for i, f in enumerate(flags + [False]):
        if f and start is None:
            start = i
        elif not f and start is not None:
            out.append((start, i - 1))
            start = None
    return out


def concept_patterns(g: pd.DataFrame, th: dict, F: int, sim_col: str = "beta_sim_rar", P_col: str = "P_raw") -> dict:
    """g = one concept's rows restricted to the analysis window, sorted by year (consecutive years)."""
    g = g.sort_values("year")
    years = g.year.tolist()
    # incubation then expansion
    quiet = [(np.isfinite(a) and a < th["sim_med"] and np.isfinite(b) and b < th["ng_med"])
             for a, b in zip(g[sim_col], g.neigh_growth)]
    sg = dict(zip(g.year, g.strength_growth))
    inc = False
    for s0, s1 in _runs(quiet):
        if s1 - s0 + 1 >= S["incubation"]["min_run"]:
            nxt = years[s1] + 1
            thr = th["sg_p90_by_age"].get(nxt - F, th["sg_p90"]) if th.get("age_adjusted") else th["sg_p90"]
            if sg.get(nxt, np.nan) > thr:
                inc = True
    # gradual centralisation
    gc = False
    z = g.wmz.values.astype(float)
    P = g[P_col].values.astype(float)
    L = S["gradual_centralisation"]["min_len"]
    for i in range(len(years)):
        for j in range(i + L - 1, len(years)):
            seg_z, seg_P = z[i:j + 1], P[i:j + 1]
            if not (np.isfinite(seg_z).all() and np.isfinite(seg_P).all()):
                continue
            if (seg_P < S["gradual_centralisation"]["P_max"]).all():
                tau = kendalltau(np.arange(len(seg_z)), seg_z).statistic
                if np.isfinite(tau) and tau > S["gradual_centralisation"]["tau"]:
                    gc = True
                    break
        if gc:
            break
    # early bridging (y in {F, F+1})
    early = g[g.year.isin([F, F + 1])]
    eb = bool(((early[P_col] > S["early_bridging"]["P_raw"]) | early.cross_comm_flag.astype(bool)).any())
    return {"INCUBATION_THEN_EXPANSION": inc, "GRADUAL_CENTRALISATION": gc, "EARLY_BRIDGING": eb}


def _boot_ci(x: np.ndarray, B: int, rng) -> list:
    if len(x) == 0:
        return [np.nan, np.nan]
    bs = [x[rng.integers(0, len(x), len(x))].mean() for _ in range(B)]
    return np.percentile(bs, [2.5, 97.5]).tolist()


def run_patterns(lab: pd.DataFrame, ind: pd.DataFrame, matches: pd.DataFrame) -> tuple[dict, pd.DataFrame]:
    B = S["bootstrap"]
    scr = ind[ind.fold == "screen"].copy()
    base = scr[(scr.age >= 0) & (scr.age <= 8)]
    th = dict(sim_med=float(base.beta_sim_rar.median()), ng_med=float(base.neigh_growth.median()),
              sg_p90=float(base.strength_growth.quantile(S["incubation"]["burst_pct"] / 100)),
              sim_raw_med=float(base.beta_sim_raw.median()),
              sg_p90_by_age={int(a): float(g.strength_growth.quantile(S["incubation"]["burst_pct"] / 100))
                             for a, g in scr[(scr.age >= 0) & (scr.age <= 9)].groupby("age")})
    grp = lab.drop_duplicates("concept_id").set_index("concept_id")
    # pre-onset cut-offs
    t0 = grp.onset.dropna().astype(int).to_dict()
    ctrl_cut = {}
    for r in matches.itertuples():
        for c in r.controls:
            ctrl_cut[c] = min(ctrl_cut.get(c, 9999), r.t0)
    band_med = {b: int(np.median([t0[c] for c in t0 if grp.loc[c, "F_band"] == b])) for b in grp.F_band.unique()
                if any(grp.loc[c, "F_band"] == b for c in t0)}
    rows = []
    for c, g in scr.groupby("concept_id"):
        if c not in grp.index:
            continue
        F = int(grp.loc[c, "F"])
        g08 = g[(g.age >= 0) & (g.age <= 8)]
        cut = t0.get(c, ctrl_cut.get(c, band_med.get(grp.loc[c, "F_band"], 2012)))
        gpre = g08[g08.year <= cut]
        r = dict(concept_id=c, group=grp.loc[c, "group"], F_band=grp.loc[c, "F_band"], origin_group=grp.loc[c, "origin_group"])
        for win, gg in (("age0_8", g08), ("pre_onset", gpre)):
            p = concept_patterns(gg, th, F)
            for k, v in p.items():
                r[f"{k}__{win}"] = v
        # sensitivities: raw Baselga fallback for incubation; P_rar for bridging
        g2 = g08.copy()
        g2["beta_sim_fb"] = g2.beta_sim_rar.fillna(g2.beta_sim_raw)
        th2 = dict(th, sim_med=float(base.beta_sim_rar.fillna(base.beta_sim_raw).median()))
        r["INCUBATION_THEN_EXPANSION__age0_8_rawfallback"] = concept_patterns(g2, th2, F, sim_col="beta_sim_fb")["INCUBATION_THEN_EXPANSION"]
        r["EARLY_BRIDGING__age0_8_Prar"] = concept_patterns(g08, th, F, P_col="P_rar")["EARLY_BRIDGING"]
        # post-hoc (declared) sensitivity: expansion threshold = p90 of strength growth AT THE SAME AGE,
        # because pooled p90 growth only occurs in the birth years (ages 0-1)
        th_age = dict(th2, age_adjusted=True)
        r["INCUBATION_THEN_EXPANSION__age0_8_ageadj"] = concept_patterns(g2, th_age, F, sim_col="beta_sim_fb")["INCUBATION_THEN_EXPANSION"]
        g2pre = g2[g2.year <= cut]
        r["INCUBATION_THEN_EXPANSION__pre_onset_ageadj"] = concept_patterns(g2pre, th_age, F, sim_col="beta_sim_fb")["INCUBATION_THEN_EXPANSION"]
        rows.append(r)
    pat = pd.DataFrame(rows)
    rng = np.random.default_rng(21)
    freq = {}
    for win in ("age0_8", "pre_onset"):
        for k in PATS:
            col = f"{k}__{win}"
            x = pat[col].astype(float).values
            e = pat.loc[pat.group == "emerging", col].astype(float).values
            n = pat.loc[pat.group == "never", col].astype(float).values
            diff_bs = []
            for _ in range(B):
                if len(e) and len(n):
                    diff_bs.append(e[rng.integers(0, len(e), len(e))].mean() - n[rng.integers(0, len(n), len(n))].mean())
            fe = fisher_exact([[int(e.sum()), int(len(e) - e.sum())], [int(n.sum()), int(len(n) - n.sum())]]) if len(e) and len(n) else None
            freq[col] = dict(overall=float(x.mean()), overall_ci=_boot_ci(x, B, rng), n=len(x),
                             emerging=float(e.mean()) if len(e) else np.nan, n_emerging=len(e),
                             never=float(n.mean()) if len(n) else np.nan, n_never=len(n),
                             diff=float(e.mean() - n.mean()) if len(e) and len(n) else np.nan,
                             diff_ci=np.percentile(diff_bs, [2.5, 97.5]).tolist() if diff_bs else [np.nan, np.nan],
                             fisher_p=float(fe.pvalue) if fe is not None else np.nan)
    for col in ("INCUBATION_THEN_EXPANSION__age0_8_rawfallback", "EARLY_BRIDGING__age0_8_Prar",
                "INCUBATION_THEN_EXPANSION__age0_8_ageadj", "INCUBATION_THEN_EXPANSION__pre_onset_ageadj"):
        x = pat[col].astype(float).values
        e = pat.loc[pat.group == "emerging", col].astype(float).values
        n = pat.loc[pat.group == "never", col].astype(float).values
        fe = fisher_exact([[int(e.sum()), int(len(e) - e.sum())], [int(n.sum()), int(len(n) - n.sum())]]) if len(e) and len(n) else None
        freq[col] = dict(overall=float(x.mean()), overall_ci=_boot_ci(x, B, rng), n=len(x),
                         emerging=float(e.mean()) if len(e) else np.nan, never=float(n.mean()) if len(n) else np.nan,
                         fisher_p=float(fe.pvalue) if fe is not None else np.nan)
    # where do large strength-growth years occur? (explains the pooled-threshold incubation result)
    freq["_strength_growth_p90_by_age"] = th["sg_p90_by_age"]
    combo = pat[[f"{k}__age0_8" for k in PATS]].astype(int).astype(str).agg("".join, axis=1)
    pat["pattern_combo"] = combo
    venn = combo.value_counts().to_dict()
    logger.info(f"patterns: {({k: round(v['overall'], 3) for k, v in freq.items() if not k.startswith('_')})}")
    return dict(thresholds=th, frequencies=freq, venn_age0_8={f"I{k[0]}G{k[1]}B{k[2]}": int(v) for k, v in venn.items()}), pat


# ----------------------------------------------------------------------------- typology
def _series_tensor(ind: pd.DataFrame, channels: list[str]) -> tuple[np.ndarray, list[str], int]:
    T = S["typology"]
    scr = ind[(ind.fold == "screen")].copy()
    for ch in channels:
        v = scr[ch].astype(float)
        scr[ch] = (v - v.mean()) / v.std()
    ages = T["ages"]
    X, ids, dropped = [], [], 0
    for c, g in scr.groupby("concept_id"):
        g = g.set_index("age").reindex(ages)[channels]
        missing = g.isna().any(axis=1).sum()
        if missing > T["max_missing"]:
            dropped += 1
            continue
        g = g.ffill(limit=T["max_fill"]).bfill(limit=T["max_fill"]).fillna(0.0)
        X.append(g.values)
        ids.append(c)
    return np.array(X), ids, dropped


def _cluster(D: np.ndarray, k: int, seed: int = 0) -> np.ndarray:
    import kmedoids
    return np.asarray(kmedoids.fasterpam(D, k, random_state=seed).labels)


def _stability(D: np.ndarray, labels: np.ndarray, k: int, B: int, seed: int = 0) -> list[float]:
    rng = np.random.default_rng(seed)
    n = len(D)
    jac = np.zeros((B, k))
    for b in range(B):
        idx = np.unique(rng.integers(0, n, n))
        if len(idx) <= k:
            continue
        lb = _cluster(D[np.ix_(idx, idx)], k, seed=b)
        for ci in range(k):
            A = set(idx[labels[idx] == ci])
            best = 0.0
            for cb in range(k):
                Bs = set(idx[lb == cb])
                u = len(A | Bs)
                if u:
                    best = max(best, len(A & Bs) / u)
            jac[b, ci] = best
    return jac.mean(axis=0).tolist()


def run_typology(ind: pd.DataFrame, lab: pd.DataFrame, pat: pd.DataFrame) -> tuple[dict, pd.DataFrame]:
    from tslearn.metrics import cdist_dtw
    T = S["typology"]
    X, ids, dropped = _series_tensor(ind, T["channels"])
    out: dict = dict(n_concepts=len(ids), n_dropped_missing=dropped, channels=T["channels"])
    if len(ids) < 10:
        out["status"] = "too few concepts"
        return out, pd.DataFrame()
    D = cdist_dtw(X, global_constraint="sakoe_chiba", sakoe_chiba_radius=T["sakoe_chiba_radius"])
    ks = {}
    for k in T["k_range"]:
        lb = _cluster(D, k)
        st = _stability(D, lb, k, T["boot"], seed=k)
        ks[k] = dict(labels=lb, jaccard=st, min_jaccard=float(min(st)), sizes=np.bincount(lb, minlength=k).tolist())
    stable = [k for k in T["k_range"] if ks[k]["min_jaccard"] > T["jaccard_min"]]
    k_sel = max(stable) if stable else 2
    out["status"] = "stable" if stable else "no stable typology (showing k=2)"
    out["k_selected"] = k_sel
    out["by_k"] = {str(k): dict(min_jaccard=v["min_jaccard"], jaccard=v["jaccard"], sizes=v["sizes"]) for k, v in ks.items()}
    lab_sel = ks[k_sel]["labels"]
    asg = pd.DataFrame(dict(concept_id=ids, cluster=lab_sel))
    # medoid series and descriptives
    import kmedoids
    med = kmedoids.fasterpam(D, k_sel, random_state=0).medoids
    out["medoids"] = {str(int(lab_sel[m])): dict(concept_id=ids[m], series=X[m].tolist()) for m in med}
    out["cluster_mean_series"] = {str(c): X[lab_sel == c].mean(axis=0).tolist() for c in range(k_sel)}
    grp = lab.drop_duplicates("concept_id").set_index("concept_id").group
    asg["group"] = asg.concept_id.map(grp)
    asg = asg.merge(pat[["concept_id", "pattern_combo"]], on="concept_id", how="left")
    ok = asg.pattern_combo.notna()
    out["ami_vs_pattern_combo"] = float(adjusted_mutual_info_score(asg.loc[ok, "cluster"], asg.loc[ok, "pattern_combo"]))
    out["crosstab_cluster_x_pattern"] = pd.crosstab(asg.cluster, asg.pattern_combo).to_dict()
    er = asg[asg.group.isin(["emerging", "never"])]
    out["emerging_rate_by_cluster"] = {str(k): dict(n=len(g), rate=float((g.group == "emerging").mean()))
                                       for k, g in er.groupby("cluster")}
    # entropy-only contrast typology (H series alone)
    Xh, idh, _ = _series_tensor(ind, ["H"])
    Dh = cdist_dtw(Xh, global_constraint="sakoe_chiba", sakoe_chiba_radius=T["sakoe_chiba_radius"])
    lbh = _cluster(Dh, k_sel)
    mh = pd.DataFrame(dict(concept_id=idh, cluster_H=lbh))
    asg = asg.merge(mh, on="concept_id", how="left")
    okh = asg.cluster_H.notna()
    out["entropy_only"] = dict(n=len(idh), ami_vs_network_typology=float(adjusted_mutual_info_score(
        asg.loc[okh, "cluster"], asg.loc[okh, "cluster_H"].astype(int))) if okh.sum() > 5 else np.nan,
        min_jaccard=float(min(_stability(Dh, lbh, k_sel, T["boot"], seed=99))))
    logger.info(f"typology: k={k_sel} status={out['status']} min_jaccard by k "
                f"{ {k: round(v['min_jaccard'], 2) for k, v in ks.items()} }")
    return out, asg
