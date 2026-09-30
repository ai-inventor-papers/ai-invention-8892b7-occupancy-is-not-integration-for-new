"""STEP 2a/2b (and 3c helper): assignment distances, margins, out-of-support, cross-tabs with Holm."""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
from loguru import logger
from scipy.stats import ks_2samp

from base import BROAD, E8, HO, LOCAL, RES, cramers_v_boot, holm, share, write_json

MEDO = json.loads((E8 / "typology/medoids.json").read_text())


def assign_series(ind: pd.DataFrame, ids: list[str]) -> pd.DataFrame:
    """Frozen rule: build_series (frozen missing rule) -> frozen scaling -> dtw_norm (radius 3) to each frozen medoid."""
    from typology import build_series, dtw_norm
    ser_raw, imp = build_series(ind, ids, MEDO["scaling"]["channels"])
    mu, sd = np.array(MEDO["scaling"]["mean"]), np.array(MEDO["scaling"]["sd"])
    rows = []
    for c in ids:
        if c not in ser_raw or len(ser_raw[c]) == 0:
            continue
        z = (ser_raw[c] - mu) / sd
        d = {m: dtw_norm(z, np.array(MEDO["medoid_series_z"][m]), MEDO["dtw"]["radius"]) for m in MEDO["medoid_ids"]}
        best = min(d, key=d.get)
        cl = MEDO["medoid_cluster"][best]
        rows.append(dict(concept_id=c, cluster=cl, cluster_name=MEDO["cluster_names"][str(cl)], nearest_medoid=best,
                         **{f"dtw_to_{m}": v for m, v in d.items()}))
    out = pd.DataFrame(rows).merge(imp, on="concept_id", how="left")
    return add_margin(out)


def add_margin(a: pd.DataFrame) -> pd.DataFrame:
    cols = [f"dtw_to_{m}" for m in MEDO["medoid_ids"]]
    D = a[cols].to_numpy(float)
    a = a.copy()
    a["d1"] = D.min(axis=1)
    a["d2"] = D.max(axis=1)
    a["margin"] = (a.d2 - a.d1) / (a.d2 + a.d1)
    return a


def dist_summary(a: pd.DataFrame, screen_d1_p95: float, screen_d1: np.ndarray | None = None) -> dict:
    n = len(a)
    amb = int((a.margin < 0.05).sum())
    oos = int((a.d1 > screen_d1_p95).sum())
    out = dict(n=n, d1_median=float(a.d1.median()), d1_iqr=[float(a.d1.quantile(0.25)), float(a.d1.quantile(0.75))],
               margin_median=float(a.margin.median()), margin_iqr=[float(a.margin.quantile(0.25)), float(a.margin.quantile(0.75))],
               ambiguous_margin_lt_0_05=share(amb, n), out_of_support_d1_gt_screen_p95=share(oos, n),
               by_type={t: dict(n=int(len(g)), d1_median=float(g.d1.median()), margin_median=float(g.margin.median()))
                        for t, g in a.groupby("cluster_name")})
    if screen_d1 is not None:
        ks = ks_2samp(a.d1.values, screen_d1)
        out["ks_vs_screen_d1"] = dict(stat=float(ks.statistic), p=float(ks.pvalue))
    return out


def crosstabs(a: pd.DataFrame, vars_: list[str], check: str | None = "route", n_perm: int = 10000) -> dict:
    from typology import perm_chi2
    res = {}
    for v in vars_ + ([check] if check else []):
        if v not in a.columns or a[v].notna().sum() < 5:
            res[v] = dict(n=0, note="not available")
            continue
        r = perm_chi2(a.cluster.astype(str), a[v].astype(str).where(a[v].notna()), n_perm=n_perm, seed=0)
        if np.isfinite(r.get("chi2", np.nan)):
            r["cramers_v_boot_ci"] = cramers_v_boot(a.cluster, a[v].where(a[v].notna()))
        res[v] = r
    ph = holm({v: res[v].get("p_perm") for v in vars_ if res[v].get("p_perm") is not None})
    for v in vars_:
        res[v]["p_holm"] = ph.get(v)
    return res


def type_shares(a: pd.DataFrame) -> dict:
    n = len(a)
    return {t: share(int((a.cluster_name == t).sum()), n) for t in (BROAD, LOCAL)}


def run() -> dict:
    ind_s = pd.read_parquet(E8 / "results/indicators/concept_year_indicators_hyd.parquet")
    asg_s = pd.read_csv(E8 / "typology/assignments.csv")
    ids_s = sorted(asg_s.concept_id)
    rs = assign_series(ind_s, ids_s)
    rs = rs.merge(asg_s[["concept_id", "cluster", "cluster_name", "E_up_group", "closure_tercile", "origin_group", "route", "F_band"]]
                  .rename(columns={"cluster": "cluster_frozen", "cluster_name": "cluster_name_frozen"}), on="concept_id")
    agree = float((rs.cluster == rs.cluster_frozen).mean())
    # D_primary cross-check at the medoid columns (ids order = sorted MAIN ids)
    Dp = np.load(E8 / "typology/D_primary.npy")
    dp_check = None
    if Dp.shape[0] == len(ids_s):
        mcol = [ids_s.index(m) for m in MEDO["medoid_ids"]]
        dd = Dp[:, mcol]
        ours = rs.set_index("concept_id").loc[ids_s, [f"dtw_to_{m}" for m in MEDO["medoid_ids"]]].to_numpy()
        dp_check = float(np.abs(dd - ours).max())
    # screen cross-tabs use the FROZEN cluster labels (gate: reproduce exp8 p-values)
    scr = rs.copy()
    scr["cluster"] = scr.cluster_frozen
    scr["cluster_name"] = scr.cluster_name_frozen
    p95 = float(scr.d1.quantile(0.95))
    out = dict(screen=dict(n=len(scr), nearest_medoid_agreement_with_frozen=agree, D_primary_max_abs_diff=dp_check,
                           type_shares=type_shares(scr), distances=dist_summary(scr, p95), d1_p95=p95))
    CT_VARS = ["E_up_group", "closure_tercile", "F_band", "origin_group"]
    ct_s = crosstabs(scr, CT_VARS)
    target = dict(E_up_group=0.097, closure_tercile=0.11, F_band=0.077, origin_group=0.004)
    gate = {v: dict(got=round(ct_s[v]["p_perm"], 3), want=target[v], ok=abs(round(ct_s[v]["p_perm"], 2) - round(target[v], 2)) < 1e-9 or abs(ct_s[v]["p_perm"] - target[v]) < 0.006)
            for v in CT_VARS}
    out["screen"]["crosstabs"] = ct_s
    out["screen_crosstab_gate"] = dict(by_var=gate, passed=all(g["ok"] for g in gate.values()))
    logger.info(f"screen cross-tab gate {out['screen_crosstab_gate']}")
    frames = {"screen": scr}
    if (HO / "typology/assignments.csv").exists():
        ho = pd.read_csv(HO / "typology/assignments.csv")
        ho = add_margin(ho)
        frames["heldout"] = ho
        out["heldout"] = dict(n=len(ho), type_shares=type_shares(ho), distances=dist_summary(ho, p95, scr.d1.values))
        if out["screen_crosstab_gate"]["passed"]:
            out["heldout"]["crosstabs"] = crosstabs(ho, CT_VARS)
            pool = pd.concat([scr.assign(population="screen"), ho.assign(population="heldout")], ignore_index=True)
            frames["pooled"] = pool
            out["pooled"] = dict(n=len(pool), type_shares=type_shares(pool), crosstabs=crosstabs(pool, CT_VARS))
        else:
            out["heldout"]["crosstabs"] = "withheld: screen reproduction gate failed"
    cols = ["concept_id", "cluster", "cluster_name", "d1", "d2", "margin"] + [f"dtw_to_{m}" for m in MEDO["medoid_ids"]] + CT_VARS + ["route"]
    pd.concat([f.assign(population=k)[[c for c in cols if c in f.columns] + ["population"]] for k, f in frames.items() if k != "pooled"],
              ignore_index=True).to_csv(RES / "typology_distances.csv", index=False)
    write_json(RES / "typology_extras.json", out)
    return out
