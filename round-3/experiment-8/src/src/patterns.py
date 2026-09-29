#!/usr/bin/env python3
"""STAGE 8: the three named RQ1 patterns (vendored analysis_patterns.concept_patterns, window ages 0-8) on the hydrated
screen pool, with thresholds (a) recomputed on the hydrated screen main-arm pool (primary) and (b) frozen at the
iteration-2 values; an 'aligned' early-bridging variant anchored at the first network year (MeSH rule); frequencies with
bootstrap CIs, by E_up group and by typology cluster; MeSH contrast with bootstrap and Newcombe CIs.
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
from loguru import logger
from scipy.stats import fisher_exact

from common import HELDOUT, RES, RES_SCREEN, TYP, WORK, X3, X4, C, boot_mean_ci, load_sealed, newcombe, setup_logging, write_json

PATS = {"INCUBATION_THEN_EXPANSION": "incubation_expansion", "GRADUAL_CENTRALISATION": "gradual_centralisation",
        "EARLY_BRIDGING": "early_bridging"}


def thresholds(ind: pd.DataFrame, ids: set) -> dict:
    S = C.SPEC
    scr = ind[ind.concept_id.isin(ids)]
    base = scr[(scr.age >= 0) & (scr.age <= 8)]
    return dict(sim_med=float(base.beta_sim_rar.median()), ng_med=float(base.neigh_growth.median()),
                sg_p90=float(base.strength_growth.quantile(S["incubation"]["burst_pct"] / 100)),
                sim_raw_med=float(base.beta_sim_raw.median()),
                sg_p90_by_age={int(a): float(g.strength_growth.quantile(S["incubation"]["burst_pct"] / 100))
                               for a, g in scr[(scr.age >= 0) & (scr.age <= 9)].groupby("age")})


def flags_for(ind: pd.DataFrame, ids: list[str], th: dict, fa: dict) -> pd.DataFrame:
    from analysis_patterns import concept_patterns
    rows = []
    for c, g in ind[ind.concept_id.isin(set(ids))].groupby("concept_id"):
        F = int(g.F.iloc[0])
        g08 = g[(g.age >= 0) & (g.age <= 8)]
        p = concept_patterns(g08, th, F)
        r = dict(concept_id=c, **p)
        # declared sensitivity (iteration 2): age-adjusted expansion threshold with raw-Baselga fallback
        g2 = g08.copy()
        g2["beta_sim_fb"] = g2.beta_sim_rar.fillna(g2.beta_sim_raw)
        r["INCUBATION_THEN_EXPANSION_ageadj"] = concept_patterns(g2, dict(th, age_adjusted=True), F, sim_col="beta_sim_fb")["INCUBATION_THEN_EXPANSION"]
        # aligned early bridging: anchored at the first network year (first attachment year and the next), as the MeSH rule
        y0 = fa.get(c)
        e = g[g.year.isin([y0, y0 + 1])] if y0 is not None else g.iloc[:0]
        r["EARLY_BRIDGING_aligned"] = bool(((e.P_raw > C.SPEC["early_bridging"]["P_raw"]) | e.cross_comm_flag.astype(bool)).any())
        r["first_network_year"] = y0
        rows.append(r)
    return pd.DataFrame(rows)


def freq_rows(df: pd.DataFrame, pop: str, subset: str, tv: str, cols: list[str]) -> list[dict]:
    out = []
    for col in cols:
        x = df[col].astype(float).values
        m, lo, hi = boot_mean_ci(x, 2000, seed=hash((pop, subset, col)) % 2 ** 31)
        out.append(dict(population=pop, subset=subset, pattern=col, freq=m, ci_lo=lo, ci_hi=hi, n=len(x), count=int(x.sum()),
                        threshold_version=tv))
    return out


@logger.catch(reraise=True)
def main() -> None:
    setup_logging("patterns")
    load_sealed()
    ind = pd.read_parquet(RES / "indicators" / "concept_year_indicators_hyd.parquet")
    pool = pd.read_parquet(WORK / "pool_active.parquet")
    scr = pool[(pool.fold == "screen") & (pool.arm == "main")]
    C.assert_not_sealed(scr.concept_id)
    main_ids = sorted(scr.loc[scr.MAIN, "concept_id"])
    all_ids = sorted(scr.concept_id)
    old_ids = sorted(scr.loc[scr.iter2_active, "concept_id"])
    fa = ind[ind.n_frame > 0].groupby("concept_id").year.min().to_dict()
    # held-out scoring uses the FROZEN screen thresholds (never recomputed on held-out concepts)
    th_new = thresholds(ind, set(all_ids)) if not HELDOUT else \
        {k: ({int(a): b for a, b in v.items()} if k == "sg_p90_by_age" else v)
         for k, v in json.loads((RES_SCREEN / "patterns.json").read_text())["thresholds_recomputed"].items()}
    th_old = json.loads((X3 / "results" / "patterns" / "summary_E_up.json").read_text())["thresholds"]
    th_old["sg_p90_by_age"] = {int(k): v for k, v in th_old["sg_p90_by_age"].items()}
    cols = list(PATS) + ["INCUBATION_THEN_EXPANSION_ageadj", "EARLY_BRIDGING_aligned"]
    fl_new = flags_for(ind, all_ids, th_new, fa)
    fl_old = flags_for(ind, all_ids, th_old, fa)
    grp = pd.read_csv(RES / "labels" / "groups.csv").set_index("concept_id")
    asg = pd.read_csv(TYP / "assignments.csv").set_index("concept_id")
    for fl in (fl_new, fl_old):
        fl["E_up_group"] = fl.concept_id.map(grp.group)
        fl["cluster_name"] = fl.concept_id.map(asg.cluster_name)
        fl["MAIN"] = fl.concept_id.isin(set(main_ids))
        fl["iter2_old"] = fl.concept_id.isin(set(old_ids))
    rows = []
    for tv, fl in (("recomputed_hydrated", fl_new), ("frozen_iter2", fl_old)):
        rows += freq_rows(fl[fl.MAIN], "screen_MAIN", "all", tv, cols)
        rows += freq_rows(fl, "screen_mainarm_all247", "all", tv, cols)
        rows += freq_rows(fl[fl.iter2_old], "screen_old123", "all", tv, cols)
        rows += freq_rows(fl[~fl.iter2_old], "screen_new124", "all", tv, cols)
        for gname, g in fl[fl.MAIN].groupby("E_up_group"):
            rows += freq_rows(g, "screen_MAIN", f"E_up={gname}", tv, cols)
        for cname, g in fl[fl.MAIN].groupby("cluster_name"):
            rows += freq_rows(g, "screen_MAIN", f"cluster={cname}", tv, cols)
    pdf = pd.DataFrame(rows)
    pdf.to_csv(RES / "patterns.csv", index=False)
    fl_new.to_csv(RES / "patterns_by_concept.csv", index=False)
    # tests by E_up group and cluster (MAIN, recomputed thresholds)
    M = fl_new[fl_new.MAIN]
    tests = {}
    from typology import perm_chi2
    for col in cols:
        for by in ("E_up_group", "cluster_name"):
            sub = M.dropna(subset=[by])
            lv = sorted(sub[by].unique())
            if len(lv) == 2:
                a = sub[sub[by] == lv[0]][col].astype(int)
                b = sub[sub[by] == lv[1]][col].astype(int)
                fe = fisher_exact([[a.sum(), len(a) - a.sum()], [b.sum(), len(b) - b.sum()]])
                tests[f"{col}__{by}"] = dict(test="fisher_exact", levels=lv, p=float(fe.pvalue), odds_ratio=float(fe.statistic))
            else:
                tests[f"{col}__{by}"] = dict(test="permutation_chi2", **perm_chi2(sub[by], sub[col].astype(str), n_perm=5000))
    # MeSH contrast
    mesh = pd.read_csv(X4 / "results" / "rq1_patterns_by_concept.csv")
    agg = pd.read_csv(X4 / "results" / "rq1_patterns.csv")
    agg = agg[(agg.population == "mesh_heldout") & (agg.group == "all")].drop_duplicates("pattern").set_index("pattern")
    verify = {p: dict(recomputed=float(mesh[p].astype(float).mean()), reported=float(agg.loc[p, "freq"]),
                      equal=bool(abs(mesh[p].astype(float).mean() - agg.loc[p, "freq"]) < 1e-9)) for p in PATS.values()}
    rng = np.random.default_rng(99)
    contrast = []
    comps = [("INCUBATION_THEN_EXPANSION", "incubation_expansion"), ("INCUBATION_THEN_EXPANSION_ageadj", "incubation_expansion"),
             ("GRADUAL_CENTRALISATION", "gradual_centralisation"), ("EARLY_BRIDGING", "early_bridging"),
             ("EARLY_BRIDGING_aligned", "early_bridging")]
    for tv, fl in (("recomputed_hydrated", fl_new), ("frozen_iter2", fl_old)):
        for popname, sub in (("screen_MAIN", fl[fl.MAIN]), ("screen_mainarm_all247", fl)):
            for mcol, mesh_col in comps:
                x = sub[mcol].astype(float).values
                y = mesh[mesh_col].astype(float).values
                bs = x[rng.integers(0, len(x), (10000, len(x)))].mean(1) - y[rng.integers(0, len(y), (10000, len(y)))].mean(1)
                nc = newcombe(int(x.sum()), len(x), int(y.sum()), len(y))
                contrast.append(dict(threshold_version=tv, population=popname, main_pattern=mcol, mesh_pattern=mesh_col,
                                     p_main=x.mean(), n_main=len(x), p_mesh=y.mean(), n_mesh=len(y), diff=x.mean() - y.mean(),
                                     boot_ci_lo=float(np.percentile(bs, 2.5)), boot_ci_hi=float(np.percentile(bs, 97.5)),
                                     newcombe_lo=nc[0], newcombe_hi=nc[1]))
    cdf = pd.DataFrame(contrast)
    cdf.to_csv(RES / "patterns_contrast.csv", index=False)
    old_rep = pdf[(pdf.population == "screen_old123") & (pdf.threshold_version == "frozen_iter2")].set_index("pattern").freq.to_dict()
    x3f = json.loads((X3 / "results" / "patterns" / "summary_E_up.json").read_text())["frequencies"]
    if HELDOUT:
        write_json(RES / "patterns.json", dict(thresholds_frozen_screen=th_new, mesh_verification=verify, tests=tests))
        return
    # diagnostic for the early-bridging gap on the old 123: swap in iteration-2 cross_comm_flag (betweenness percentile
    # computed with 145 instead of 307 pool nodes in the betweenness graph)
    x3i = pd.read_parquet(X3 / "results" / "indicators" / "concept_year_indicators.parquet")
    x3i = x3i[x3i.concept_id.isin(set(old_ids))]
    fl_x3 = flags_for(x3i, old_ids, th_old, fa)
    hyb = ind[ind.concept_id.isin(set(old_ids))].drop(columns=["cross_comm_flag"]).merge(
        x3i[["concept_id", "year", "cross_comm_flag"]], on=["concept_id", "year"], how="left")
    hyb["cross_comm_flag"] = hyb.cross_comm_flag.fillna(False).astype(bool)
    fl_h = flags_for(hyb, old_ids, th_old, fa)
    p_only = flags_for(ind[ind.concept_id.isin(set(old_ids))].assign(cross_comm_flag=False), old_ids, th_old, fa)
    p_only_x3 = flags_for(x3i.assign(cross_comm_flag=False), old_ids, th_old, fa)
    eb_diag = dict(iter2_indicators_rescored=float(fl_x3.EARLY_BRIDGING.mean()), hydrated_with_iter2_cross_flag=float(fl_h.EARLY_BRIDGING.mean()),
                   hydrated_P_raw_component_only=float(p_only.EARLY_BRIDGING.mean()), iter2_P_raw_component_only=float(p_only_x3.EARLY_BRIDGING.mean()),
                   cross_flag_share_F_F1_hydrated=float(ind[ind.concept_id.isin(set(old_ids)) & (ind.age.isin([0, 1]))].cross_comm_flag.mean()),
                   cross_flag_share_F_F1_iter2=float(x3i[x3i.age.isin([0, 1])].cross_comm_flag.mean()))
    write_json(RES / "patterns.json", dict(
        thresholds_recomputed=th_new, thresholds_frozen_iter2=th_old, mesh_verification=verify, tests=tests,
        early_bridging_gap_diagnostic=eb_diag,
        old123_frozen_reproduction=dict(hydrated={k: old_rep.get(k) for k in PATS},
                                        iter2={k: x3f[f"{k}__age0_8"]["overall"] for k in PATS}),
        note=("MeSH flags come from iteration 2 (own background snapshots, Leiden n_iterations=2, first-network-year anchor): "
              "the contrast is a descriptive population contrast; the aligned early-bridging variant re-scores the main pool "
              "under the MeSH anchoring rule.")))
    logger.info(f"patterns MAIN (recomputed): {pdf[(pdf.population=='screen_MAIN')&(pdf.subset=='all')&(pdf.threshold_version=='recomputed_hydrated')][['pattern','freq','n']].to_dict('records')}")


if __name__ == "__main__":
    main()
