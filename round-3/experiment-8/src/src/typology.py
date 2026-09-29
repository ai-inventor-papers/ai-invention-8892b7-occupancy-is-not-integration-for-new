#!/usr/bin/env python3
"""STAGE 6: 3-channel diffusion typology (multivariate DTW + k-medoids, Hennig bootstrap-Jaccard k selection),
baselines (B1 entropy-only = iteration-2 recipe; B2 volume-only), sensitivities, cluster description and naming,
cross-tabs with permutation chi-square. Validation on unclustered quantities lives in validation.py.

Population: screen MAIN (primary); STRICT, all 247 screen main-arm and 'drop sense_check_fail' as sensitivities.
Series: years F..2024 per concept; channels ch1 = H_rar (3-yr window, m=10), ch2 = RS (3-yr), ch3 = active_subfields_3y.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd
from loguru import logger
from scipy.stats import spearmanr
from sklearn.metrics import adjusted_mutual_info_score, silhouette_score

from common import HELDOUT, RES, TYP, TYP_FROZEN, WORK, X3, C, load_sealed, setup_logging, sha256_file, write_json, wilson

CH = ["H_rar", "RS", "active_subfields_3y"]
CH_RAR = ["H_rar", "RS_rar", "richness_rar"]
K_RANGE = list(range(2, 9))
B_BOOT = 200
JAC_MIN = 0.75
DTW_RADIUS = 3


# ----------------------------------------------------------------------------- series
def build_series(ind: pd.DataFrame, ids: list[str], channels: list[str], ages: list[int] | None = None,
                 impute: bool = True) -> tuple[dict, pd.DataFrame]:
    """Per-concept raw (unscaled) multichannel series and the per-concept imputed share.

    Declared missing rule: H_rar NaN (vol3 < 10) -> raw H of the same window (imputed); if vol3 == 0 -> H = RS = 0 and
    count = 0 (imputed if the value was NaN); any other NaN (e.g. all window papers without a known subfield) -> 0
    (imputed). No concept is excluded.
    """
    ser, imp = {}, []
    sub = ind[ind.concept_id.isin(set(ids))]
    for c, g in sub.groupby("concept_id"):
        F = int(g.F.iloc[0])
        g = g[(g.year >= F) & (g.year <= 2024)].sort_values("year")
        if ages is not None:
            g = g[g.age.isin(ages)]
        X = np.zeros((len(g), len(channels)))
        n_imp = np.zeros(len(g), dtype=bool)
        for j, ch in enumerate(channels):
            v = g[ch].astype(float).values.copy()
            if ch == "H_rar":
                fb = np.isnan(v)
                v[fb] = g.H.astype(float).values[fb]
                n_imp |= fb
            nan = np.isnan(v)
            n_imp |= nan
            v[nan] = 0.0
            X[:, j] = v
        ser[c] = X
        imp.append(dict(concept_id=c, n_years=len(g), imputed_share=float(n_imp.mean()) if len(g) else np.nan))
    return ser, pd.DataFrame(imp)


def zscale(ser: dict) -> tuple[dict, dict]:
    allv = np.vstack(list(ser.values()))
    mu, sd = allv.mean(axis=0), allv.std(axis=0)
    sd[sd == 0] = 1.0
    return {c: (X - mu) / sd for c, X in ser.items()}, dict(mean=mu.tolist(), sd=sd.tolist())


def dtw_norm(a: np.ndarray, b: np.ndarray, radius: int = DTW_RADIUS, normalise: bool = True) -> float:
    from tslearn.metrics import dtw_path
    path, d = dtw_path(a, b, global_constraint="sakoe_chiba", sakoe_chiba_radius=radius)
    return float(d / math.sqrt(len(path))) if normalise else float(d)


def dist_matrix(ser: dict, ids: list[str], radius: int = DTW_RADIUS, normalise: bool = True) -> np.ndarray:
    n = len(ids)
    D = np.zeros((n, n))
    for i in range(n):
        for j in range(i + 1, n):
            D[i, j] = D[j, i] = dtw_norm(ser[ids[i]], ser[ids[j]], radius, normalise)
    return D


# ----------------------------------------------------------------------------- clustering
def select_k(D: np.ndarray, k_range=K_RANGE, B: int = B_BOOT) -> dict:
    from analysis_patterns import _cluster, _stability
    import kmedoids
    res = {}
    for k in k_range:
        if k >= len(D):
            continue
        lb = _cluster(D, k)
        st = _stability(D, lb, k, B, seed=k)
        sil = float(silhouette_score(D, lb, metric="precomputed")) if len(set(lb)) > 1 else np.nan
        med = kmedoids.fasterpam(D, k, random_state=0).medoids
        res[k] = dict(labels=lb, jaccard=st, min_jaccard=float(min(st)), silhouette=sil,
                      sizes=np.bincount(lb, minlength=k).tolist(), medoids=[int(m) for m in med])
    stable = [k for k in res if res[k]["min_jaccard"] > JAC_MIN]
    if stable:
        top = max(stable)
        # tie-break: among stable k in the same min-Jaccard band (within 0.02 of each other) prefer higher silhouette
        band = [k for k in stable if abs(res[k]["min_jaccard"] - res[top]["min_jaccard"]) < 0.02 and k >= top - 1]
        k_sel = max(band, key=lambda k: (res[k]["silhouette"], k))
        status = "stable"
    else:
        k_sel = max(res, key=lambda k: (res[k]["min_jaccard"], res[k]["silhouette"]))
        status = "no stable typology"
    return dict(by_k=res, k_sel=k_sel, status=status, stable_ks=stable)


def hennig_band(j: float) -> str:
    return "stable" if j > 0.75 else ("pattern" if j >= 0.6 else ("weak" if j > 0.5 else "dissolved"))


def ami(a: pd.Series, b: pd.Series) -> float:
    m = pd.concat([a.rename("a"), b.rename("b")], axis=1).dropna()
    return float(adjusted_mutual_info_score(m.a.astype(str), m.b.astype(str))) if len(m) > 5 else np.nan


# ----------------------------------------------------------------------------- baselines
def entropy_only(ind: pd.DataFrame, ids: list[str], k: int | None, B: int = B_BOOT, seed: int = 99) -> dict:
    """B1: the iteration-2 entropy-only recipe (analysis_patterns._series_tensor on raw H, ages 0..8, z-scored over the
    given screen concepts, cdist_dtw radius 2, fasterpam). k=None -> k selected by the same stability rule."""
    from analysis_patterns import _cluster, _series_tensor, _stability
    from tslearn.metrics import cdist_dtw
    sub = ind[ind.concept_id.isin(set(ids))].copy()
    sub["fold"] = "screen"
    X, idh, dropped = _series_tensor(sub, ["H"])
    Dh = cdist_dtw(X, global_constraint="sakoe_chiba", sakoe_chiba_radius=2)
    if k is None:
        sel = select_k(Dh, B=B)
        k = sel["k_sel"]
        lb = sel["by_k"][k]["labels"]
        st = sel["by_k"][k]["jaccard"]
        table = {str(kk): dict(min_jaccard=v["min_jaccard"], jaccard=v["jaccard"], silhouette=v["silhouette"], sizes=v["sizes"])
                 for kk, v in sel["by_k"].items()}
        status = sel["status"]
    else:
        lb = _cluster(Dh, k)
        st = _stability(Dh, lb, k, B, seed=seed)
        table, status = None, None
    return dict(ids=idh, labels=np.asarray(lb), k=k, jaccard=st, min_jaccard=float(min(st)), n=len(idh),
                n_dropped_missing=dropped, table=table, status=status, D=Dh)


def perm_chi2(a: pd.Series, b: pd.Series, n_perm: int = 10000, seed: int = 0) -> dict:
    m = pd.concat([a.rename("a"), b.rename("b")], axis=1).dropna()
    ai = pd.factorize(m.a.astype(str), sort=True)
    bi = pd.factorize(m.b.astype(str), sort=True)
    ka, kb, n = len(ai[1]), len(bi[1]), len(m)
    if ka < 2 or kb < 2:
        return dict(n=n, chi2=np.nan, p_perm=np.nan)

    def chi2(x, y):
        tab = np.bincount(x * kb + y, minlength=ka * kb).reshape(ka, kb).astype(float)
        e = tab.sum(1, keepdims=True) * tab.sum(0, keepdims=True) / n
        return float(((tab - e) ** 2 / np.where(e > 0, e, 1)).sum()), tab, e

    obs, tab, e = chi2(ai[0], bi[0])
    rng = np.random.default_rng(seed)
    ge = 0
    for _ in range(n_perm):
        if chi2(ai[0], rng.permutation(bi[0]))[0] >= obs - 1e-12:
            ge += 1
    rs = (tab - e) / np.sqrt(np.where(e > 0, e, 1) * (1 - tab.sum(1, keepdims=True) / n) * (1 - tab.sum(0, keepdims=True) / n))
    V = math.sqrt(obs / (n * (min(ka, kb) - 1)))
    return dict(n=n, chi2=obs, p_perm=(ge + 1) / (n_perm + 1), cramers_v=V, rows=list(ai[1]), cols=list(bi[1]),
                table=tab.astype(int).tolist(), std_residuals=np.round(rs, 3).tolist(), min_expected=float(e.min()))


# ----------------------------------------------------------------------------- description & naming
def describe(ser_raw: dict, ind: pd.DataFrame, asg: pd.DataFrame, channels: list[str]) -> tuple[pd.DataFrame, dict]:
    rows = []
    for c, X in ser_raw.items():
        cl = asg.loc[asg.concept_id == c, "cluster"]
        if cl.empty:
            continue
        for a in range(len(X)):
            rows.append(dict(concept_id=c, cluster=int(cl.iloc[0]), age=a, **{ch: X[a, j] for j, ch in enumerate(channels)}))
    long = pd.DataFrame(rows)
    traj = long.groupby(["cluster", "age"]).agg(n=("concept_id", "size"),
                                                **{f"{ch}_{q}": (ch, (lambda v, q=q: np.quantile(v, q))) for ch in channels
                                                   for q in (0.25, 0.5, 0.75)}).reset_index()
    desc = {}
    for cl, g in traj.groupby("cluster"):
        g = g[g.n >= 5]
        d = {}
        for ch in channels:
            med = g[f"{ch}_0.5"].values
            d[ch] = dict(start=float(med[:2].mean()), final=float(med[-3:].mean()), peak=float(med.max()),
                         peak_age=int(g.age.values[int(np.argmax(med))]), slope=float(np.polyfit(g.age.values, med, 1)[0]),
                         drop_from_peak=float(med.max() - med[-3:].mean()))
        desc[int(cl)] = d
    return traj, desc


def name_clusters(desc: dict, sizes: dict, ch_key: str = "active_subfields_3y") -> tuple[dict, str]:
    """Name clusters AFTER clustering from the median breadth trajectory (declared rule, numbers written out)."""
    cl = sorted(desc)
    fin = {c: desc[c][ch_key]["final"] for c in cl}
    start = {c: desc[c][ch_key]["start"] for c in cl}
    drop = {c: desc[c][ch_key]["drop_from_peak"] / max(desc[c][ch_key]["peak"], 1e-9) for c in cl}
    slope = {c: desc[c][ch_key]["slope"] for c in cl}
    names = {}
    lo = min(cl, key=lambda c: fin[c])
    names[lo] = "localised"
    rest = [c for c in cl if c not in names]
    if rest:
        hs = max(rest, key=lambda c: start[c])
        if start[hs] >= np.median(list(start.values())) and start[hs] > start[lo]:
            names[hs] = "broad from the start (rapid interdisciplinary)"
    for c in cl:
        if c in names:
            continue
        if drop[c] >= 0.30:
            names[c] = "temporary expansion"
        elif slope[c] > 0:
            names[c] = "gradual broadening"
        else:
            names[c] = "stable intermediate"
    seen: dict = {}
    for c in cl:
        seen[names[c]] = seen.get(names[c], 0) + 1
    for c in cl:
        if seen[names[c]] > 1:
            rank = sorted([x for x in cl if names[x] == names[c]], key=lambda x: fin[x]).index(c) + 1
            names[c] = f"{names[c]} ({'narrower' if rank == 1 else 'broader'}{'' if rank <= 2 else ' ' + str(rank)})"
    lines = ["# Typology naming rule (applied after clustering)", "",
             f"Names come from the median trajectory of `{ch_key}` (number of subfields with >= 2 c-papers in the 3-year window)",
             "by concept age, computed per cluster over ages with >= 5 concepts:", "",
             "1. the cluster with the lowest final level (mean of the last 3 median ages) = **localised**;",
             "2. of the rest, the cluster with the highest start level (mean of ages 0-1), if >= the median start and above",
             "   the localised start = **broad from the start (rapid interdisciplinary)**;",
             "3. any other cluster whose final level is >= 30% below its peak = **temporary expansion**;",
             "4. else positive OLS slope over age = **gradual broadening**; else **stable intermediate**;",
             "5. duplicates are suffixed narrower/broader by final level.", "",
             "| cluster | n | start | peak (age) | final | slope/yr | drop from peak | name |", "|---|---|---|---|---|---|---|---|"]
    for c in cl:
        d = desc[c][ch_key]
        lines.append(f"| {c} | {sizes.get(c, '')} | {d['start']:.2f} | {d['peak']:.2f} ({d['peak_age']}) | {d['final']:.2f} | "
                     f"{d['slope']:.3f} | {drop[c]:.2f} | {names[c]} |")
    return names, "\n".join(lines) + "\n"


# ----------------------------------------------------------------------------- held-out assignment (iteration 4, E1)
def assign_heldout() -> None:
    """Assign every held-out MAIN concept to the nearest FROZEN medoid under the frozen scaling and DTW rule."""
    import json
    medo = json.loads((TYP_FROZEN / "medoids.json").read_text())
    ind = pd.read_parquet(RES / "indicators" / "concept_year_indicators_hyd.parquet")
    pool = pd.read_parquet(WORK / "pool_active.parquet")
    scr = pool[(pool.fold == "screen") & (pool.arm == "main")]
    ids = sorted(scr.loc[scr.MAIN, "concept_id"])
    ser_raw, imp = build_series(ind, ids, medo["scaling"]["channels"])
    mu, sd = np.array(medo["scaling"]["mean"]), np.array(medo["scaling"]["sd"])
    rows = []
    for c in ids:
        z = (ser_raw[c] - mu) / sd
        d = {m: dtw_norm(z, np.array(medo["medoid_series_z"][m]), medo["dtw"]["radius"]) for m in medo["medoid_ids"]}
        best = min(d, key=d.get)
        cl = medo["medoid_cluster"][best]
        rows.append(dict(concept_id=c, cluster=cl, cluster_name=medo["cluster_names"][str(cl)], nearest_medoid=best,
                         **{f"dtw_to_{m}": v for m, v in d.items()}))
    asg = pd.DataFrame(rows)
    grp = pd.read_csv(RES / "labels" / "groups.csv").set_index("concept_id")
    pinfo = pool.set_index("concept_id")
    asg["E_up_group"] = asg.concept_id.map(grp.group)
    asg["closure_tercile"] = asg.concept_id.map(grp.closure_tercile)
    for col in ("origin_group", "route", "F_band"):
        asg[col] = asg.concept_id.map(pinfo[col])
    asg["is_medoid"] = False
    asg.to_csv(TYP / "assignments.csv", index=False)
    imp.to_csv(TYP / "imputed_share.csv", index=False)
    n = len(asg)
    shares = {name: dict(n=int(k), share=k / n, wilson_ci=list(wilson(int(k), n))) for name, k in asg.cluster_name.value_counts().items()}
    write_json(RES / "typology.json", dict(mode="heldout assignment to frozen medoids", n=n, shares=shares,
                                           medoids_sha256=sha256_file(TYP_FROZEN / "medoids.json")))
    logger.info(f"held-out assignment: {shares}")


# ----------------------------------------------------------------------------- main
@logger.catch(reraise=True)
def main() -> None:
    import kmedoids
    setup_logging("typology")
    load_sealed()
    if HELDOUT:
        assign_heldout()
        return
    ind = pd.read_parquet(RES / "indicators" / "concept_year_indicators_hyd.parquet")
    pool = pd.read_parquet(WORK / "pool_active.parquet")
    scr = pool[(pool.fold == "screen") & (pool.arm == "main")]
    pops = {"MAIN": sorted(scr.loc[scr.MAIN, "concept_id"]), "STRICT": sorted(scr.loc[scr.STRICT, "concept_id"]),
            "ALL_SCREEN_MAINARM": sorted(scr.concept_id),
            "MAIN_no_sense_fail": sorted(scr.loc[scr.MAIN & ~scr.sense_check_fail, "concept_id"])}
    for p in pops.values():
        C.assert_not_sealed(p)
    ids = pops["MAIN"]
    out: dict = dict(population="screen MAIN", n=len(ids), channels=CH, dtw=dict(radius=DTW_RADIUS, normalisation="dtw/sqrt(len(path))",
                     constraint="sakoe_chiba"), k_range=K_RANGE, B=B_BOOT, jaccard_min=JAC_MIN)
    ser_raw, imp = build_series(ind, ids, CH)
    imp.to_csv(TYP / "imputed_share.csv", index=False)
    out["imputation"] = dict(concept_year_imputed_share=float(np.average(imp.imputed_share, weights=imp.n_years)),
                             median_concept_share=float(imp.imputed_share.median()), n_excluded=0,
                             series_length_range=[int(imp.n_years.min()), int(imp.n_years.max())])
    ser, scaling = zscale(ser_raw)
    (TYP / "scaling.json").write_text(__import__("json").dumps(dict(channels=CH, **scaling), indent=1))
    D = dist_matrix(ser, ids)
    np.save(TYP / "D_primary.npy", D)
    sel = select_k(D)
    k = sel["k_sel"]
    out["status"] = sel["status"]
    out["stable_ks"] = sel["stable_ks"]
    out["k_selected"] = k
    out["by_k"] = {str(kk): dict(min_jaccard=v["min_jaccard"], jaccard=v["jaccard"], silhouette=v["silhouette"],
                                 sizes=v["sizes"], hennig_band_min=hennig_band(v["min_jaccard"]))
                   for kk, v in sel["by_k"].items()}
    logger.info(f"3-channel typology: status={sel['status']} k={k}; min Jaccard by k "
                f"{ {kk: round(v['min_jaccard'], 3) for kk, v in sel['by_k'].items()} }")
    lab3 = sel["by_k"][k]["labels"]
    # ---- entropy-only baseline (B1): reproduce iteration 2 on the 123 old concepts, then hydrated MAIN
    old = sorted(pool.loc[pool.iter2_active & (pool.fold == "screen"), "concept_id"])
    b1_old = entropy_only(ind, old, k=2)
    x3a = pd.read_parquet(X3 / "results" / "typology" / "assignments.parquet")
    x3s = __import__("json").loads((X3 / "results" / "typology" / "stability.json").read_text())
    b1_old_ami = ami(pd.Series(b1_old["labels"], index=b1_old["ids"]), x3a.set_index("concept_id").cluster_H)
    out["B1_reproduction_old123"] = dict(n=b1_old["n"], k=2, min_jaccard=b1_old["min_jaccard"], jaccard=b1_old["jaccard"],
                                         iter2_min_jaccard=x3s["entropy_only"]["min_jaccard"], iter2_n=x3s["entropy_only"]["n"],
                                         within_0_03=bool(abs(b1_old["min_jaccard"] - x3s["entropy_only"]["min_jaccard"]) <= 0.03),
                                         ami_vs_iter2_labels_on_overlap=b1_old_ami)
    logger.info(f"B1 reproduction on old 123: {out['B1_reproduction_old123']}")
    b1 = entropy_only(ind, ids, k=None)
    out["B1_entropy_only_MAIN"] = dict(n=b1["n"], n_dropped_missing=b1["n_dropped_missing"], k=b1["k"], status=b1["status"],
                                       min_jaccard=b1["min_jaccard"], by_k=b1["table"])
    b1_fixed = entropy_only(ind, ids, k=k)
    out["B1_entropy_only_MAIN_at_kstar"] = dict(k=k, min_jaccard=b1_fixed["min_jaccard"], jaccard=b1_fixed["jaccard"])
    # ---- volume-only baseline (B2)
    cumv = {c: float(ind[(ind.concept_id == c) & (ind.year >= int(ind.loc[ind.concept_id == c, "F"].iloc[0]))].vol.sum()) for c in ids}
    logv = pd.Series({c: math.log1p(v) for c, v in cumv.items()})
    terc = pd.qcut(logv.rank(method="first"), 3, labels=["V1_low", "V2_mid", "V3_high"])
    vser = {}
    for c in ids:
        g = ind[(ind.concept_id == c)].sort_values("year")
        g = g[g.year >= int(g.F.iloc[0])]
        vser[c] = np.log1p(g.vol.values.astype(float))[:, None]
    vz, _ = zscale(vser)
    Dv = dist_matrix(vz, ids)
    from analysis_patterns import _cluster, _stability
    lbv = _cluster(Dv, k)
    asg = pd.DataFrame(dict(concept_id=ids, cluster=lab3))
    asg["cluster_B1"] = asg.concept_id.map(dict(zip(b1["ids"], b1["labels"])))
    asg["cluster_B1_kstar"] = asg.concept_id.map(dict(zip(b1_fixed["ids"], b1_fixed["labels"])))
    asg["B2_vol_tercile"] = asg.concept_id.map(terc.astype(str))
    asg["cluster_B2_volseries"] = lbv
    asg["log_cum_vol"] = asg.concept_id.map(logv)
    rho = spearmanr(asg.cluster, asg.log_cum_vol).statistic
    # cluster-level volume association (rank of cluster by median volume vs volume)
    med_rank = asg.groupby("cluster").log_cum_vol.median().rank().to_dict()
    rho_ord = spearmanr(asg.cluster.map(med_rank), asg.log_cum_vol).statistic
    out["baselines"] = dict(
        AMI_3ch_vs_B1=ami(asg.cluster, asg.cluster_B1), AMI_3ch_vs_B1_kstar=ami(asg.cluster, asg.cluster_B1_kstar),
        AMI_3ch_vs_B2_tercile=ami(asg.cluster, asg.B2_vol_tercile), AMI_3ch_vs_B2_volseries=ami(asg.cluster, asg.cluster_B2_volseries),
        B2_volseries_min_jaccard=float(min(_stability(Dv, lbv, k, B_BOOT, seed=7))),
        spearman_cluster_code_vs_logcumvol=float(rho), spearman_cluster_volrank_vs_logcumvol=float(rho_ord))
    old_lab = x3a.set_index("concept_id").cluster_H
    out["baselines"]["AMI_3ch_vs_iter2_entropy_labels_old"] = ami(asg.set_index("concept_id").cluster, old_lab)
    vol_driven = bool(out["baselines"]["AMI_3ch_vs_B2_tercile"] > 0.5 or abs(rho_ord) > 0.6)
    out["volume_driven_flag"] = dict(rule="AMI(3ch, volume terciles) > 0.5 or |Spearman(cluster volume rank, log cum vol)| > 0.6",
                                     flag=vol_driven)
    # ---- secondary: volume-residualised channels (each channel residualised on log1p(vol3) and age before z-scoring)
    rr = ind[ind.concept_id.isin(ids) & (ind.year >= ind.F)].copy()
    rr["H_rar"] = rr.H_rar.fillna(rr.H).fillna(0.0)
    rr["RS"] = rr.RS.fillna(0.0)
    Xr = np.column_stack([np.ones(len(rr)), np.log1p(rr.vol3), rr.age])
    for ch in CH:
        beta, *_ = np.linalg.lstsq(Xr, rr[ch].astype(float).values, rcond=None)
        rr[ch] = rr[ch].astype(float).values - Xr @ beta
    ser_res = {c: g.sort_values("year")[CH].values for c, g in rr.groupby("concept_id")}
    ser_res, _ = zscale(ser_res)
    Dres = dist_matrix(ser_res, ids)
    sel_res = select_k(Dres, B=100)
    asg["cluster_volres"] = sel_res["by_k"][sel_res["k_sel"]]["labels"]
    out["volume_residualised_variant"] = dict(k=sel_res["k_sel"], status=sel_res["status"],
                                              min_jaccard=sel_res["by_k"][sel_res["k_sel"]]["min_jaccard"],
                                              by_k={str(kk): v["min_jaccard"] for kk, v in sel_res["by_k"].items()},
                                              AMI_vs_primary=ami(asg.cluster, asg.cluster_volres),
                                              AMI_vs_B2_tercile=ami(asg.cluster_volres, asg.B2_vol_tercile))
    # ---- sensitivities (k* fixed; AMI with primary on common concepts; stability B=100)
    sens = {}

    def run_sens(name, s_ids, channels=CH, ages=None, radius=DTW_RADIUS, normalise=True):
        sr, _ = build_series(ind, s_ids, channels, ages=ages)
        sz, _ = zscale(sr)
        Ds = dist_matrix(sz, s_ids, radius, normalise)
        lb = _cluster(Ds, k)
        st = _stability(Ds, lb, k, 100, seed=k)
        a = ami(asg.set_index("concept_id").cluster, pd.Series(lb, index=s_ids))
        sens[name] = dict(n=len(s_ids), k=k, min_jaccard=float(min(st)), AMI_vs_primary=a, sizes=np.bincount(lb).tolist())
        logger.info(f"sensitivity {name}: {sens[name]}")

    run_sens("rarefied_channels", ids, channels=CH_RAR)
    run_sens("ages_0_8", ids, ages=list(range(0, 9)))
    run_sens("raw_dtw_unnormalised", ids, normalise=False)
    run_sens("radius_2", ids, radius=2)
    run_sens("STRICT", pops["STRICT"])
    run_sens("ALL_SCREEN_MAINARM", pops["ALL_SCREEN_MAINARM"])
    run_sens("MAIN_no_sense_fail", pops["MAIN_no_sense_fail"])
    out["sensitivities"] = sens
    # ---- all-247 assignments for the sensitivity dataset (same k)
    sr, _ = build_series(ind, pops["ALL_SCREEN_MAINARM"], CH)
    sz, _ = zscale(sr)
    Dall = dist_matrix(sz, pops["ALL_SCREEN_MAINARM"])
    asg_all = pd.DataFrame(dict(concept_id=pops["ALL_SCREEN_MAINARM"], cluster=_cluster(Dall, k)))
    # ---- describe + name
    traj, desc = describe(ser_raw, ind, asg, CH)
    traj.to_csv(TYP / "cluster_trajectories_by_age.csv", index=False)
    sizes = asg.cluster.value_counts().to_dict()
    names, md = name_clusters(desc, sizes)
    (RES / "typology_naming.md").write_text(md)
    asg["cluster_name"] = asg.cluster.map(names)
    out["cluster_names"] = {str(c): n for c, n in names.items()}
    out["cluster_description"] = desc
    out["cluster_sizes"] = {str(c): int(v) for c, v in sizes.items()}
    out["interpretable_clusters"] = {str(c): bool(v >= 10) for c, v in sizes.items()}
    # B1 naming (so predict_baseline carries a readable label)
    serH, _ = build_series(ind, b1["ids"], ["H"], ages=list(range(0, 9)))
    b1asg = pd.DataFrame(dict(concept_id=b1["ids"], cluster=b1["labels"]))
    medH = {c: float(np.median([serH[x][:, 0].mean() for x in b1asg.concept_id[b1asg.cluster == c]])) for c in sorted(set(b1["labels"]))}
    order = sorted(medH, key=medH.get)
    b1names = {c: f"entropy-{'low' if i == 0 else ('high' if i == len(order) - 1 else 'mid' + str(i))} (H median {medH[c]:.2f})"
               for i, c in enumerate(order)}
    asg["cluster_B1_name"] = asg.cluster_B1.map(b1names)
    out["B1_names"] = {str(c): v for c, v in b1names.items()}
    # ---- exploratory finer partitions (not fully stable; Hennig 'pattern'/'weak' bands) - described, never primary
    grp = pd.read_csv(RES / "labels" / "groups.csv").set_index("concept_id")
    expl = {}
    for kk in (3, 4):
        if kk not in sel["by_k"]:
            continue
        a2 = pd.DataFrame(dict(concept_id=ids, cluster=sel["by_k"][kk]["labels"]))
        _, dsc = describe(ser_raw, ind, a2, CH)
        nm, md_k = name_clusters(dsc, a2.cluster.value_counts().to_dict())
        asg[f"cluster_k{kk}"] = a2.cluster.values
        asg[f"cluster_k{kk}_name"] = a2.cluster.map(nm).values
        expl[str(kk)] = dict(status=f"exploratory ({hennig_band(sel['by_k'][kk]['min_jaccard'])} by min Jaccard)",
                             jaccard=sel["by_k"][kk]["jaccard"], sizes=sel["by_k"][kk]["sizes"],
                             names={str(c): n for c, n in nm.items()}, description=dsc,
                             AMI_vs_k2=ami(asg.cluster, a2.set_index(asg.index).cluster),
                             crosstab_E_up=perm_chi2(a2.cluster.map(nm), a2.concept_id.map(grp.group), n_perm=2000),
                             nesting=pd.crosstab(asg.cluster_name, a2.cluster.map(nm).values).to_dict())
        (RES / f"typology_naming_k{kk}_exploratory.md").write_text(md_k)
    out["exploratory_finer_k"] = expl
    # ---- cross-tabs
    pinfo = pool.set_index("concept_id")
    asg["E_up_group"] = asg.concept_id.map(grp.group)
    asg["closure_tercile"] = asg.concept_id.map(grp.closure_tercile)
    for col in ("origin_group", "route", "F_band", "sense_check_fail", "iter2_active"):
        asg[col] = asg.concept_id.map(pinfo[col])
    ct = {}
    for col in ("E_up_group", "closure_tercile", "origin_group", "route", "F_band"):
        ct[col] = perm_chi2(asg.cluster, asg[col])
        ct[f"{col}__B1"] = perm_chi2(asg.cluster_B1, asg[col])
    out["crosstabs"] = ct
    # ---- medoids (frozen)
    med = sel["by_k"][k]["medoids"]
    asg["is_medoid"] = asg.index.isin(med)
    medo = dict(k=k, medoid_ids=[ids[m] for m in med], medoid_cluster={ids[m]: int(lab3[m]) for m in med},
                cluster_names={str(c): n for c, n in names.items()},
                medoid_series_z={ids[m]: ser[ids[m]].tolist() for m in med},
                medoid_series_raw={ids[m]: ser_raw[ids[m]].tolist() for m in med},
                scaling=dict(channels=CH, **scaling), dtw=out["dtw"],
                missing_rule="H_rar NaN -> raw H of the same window; remaining NaN -> 0; series years F..2024",
                code_sha256={p.name: sha256_file(p) for p in sorted((TYP.parent / "src").glob("*.py"))})
    import json
    (TYP / "medoids.json").write_text(json.dumps(medo, indent=1))
    (TYP / "medoids.json.sha256").write_text(sha256_file(TYP / "medoids.json"))
    asg.to_csv(TYP / "assignments.csv", index=False)
    asg_all.to_csv(TYP / "assignments_all_screen_mainarm.csv", index=False)
    write_json(RES / "typology.json", out)
    logger.info(f"typology done: k={k} names={names} baselines={out['baselines']}")


if __name__ == "__main__":
    main()
