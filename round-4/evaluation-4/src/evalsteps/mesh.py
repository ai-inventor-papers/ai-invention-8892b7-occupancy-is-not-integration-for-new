"""STEP 3c-3f: MeSH second population under the frozen spec (results/mesh_spec.json)."""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
from loguru import logger

from base import BROAD, E4, E8, HO, LOCAL, RES, newcombe, share, sha256, wilson, write_json
from typology_extras import MEDO, add_margin, assign_series, crosstabs, dist_summary, type_shares

MR = RES / "mesh"
CATS3 = ["expansion_first", "same_year", "diffusion_first"]


def f_band(F: int) -> str:
    return "2005-07" if F <= 2007 else ("2008-11" if F <= 2011 else "2012-16")


def check_spec() -> str:
    log = (RES.parent / "logs/freeze_log.txt").read_text()
    h = sha256(RES / "mesh_spec.json")
    assert h in log, "mesh_spec.json hash not in freeze log"
    spec = json.loads((RES / "mesh_spec.json").read_text())
    for f, want in spec["frozen_function_sha256"].items():
        assert sha256(E8 / f) == want, f"frozen file drifted: {f}"
    assert sha256(RES.parent / "scripts/mesh_adapter.py") == spec["adapter_sha256"]["scripts/mesh_adapter.py"], "adapter drifted"
    return h


def typology_part(pop: pd.DataFrame, ind: pd.DataFrame, scr_d1: np.ndarray, p95: float) -> dict:
    ids = sorted(pop.concept_id)
    a = assign_series(ind, ids)
    a = a.merge(pop[["concept_id", "branch_group", "F", "rule_parity", "retrieval_complete", "origin_field"]], on="concept_id")
    a["F_band"] = a.F.map(f_band)
    a.to_csv(MR / "mesh_assignments.csv", index=False)
    out = dict(n=len(a), type_shares=type_shares(a), distances=dist_summary(a, p95, scr_d1))
    kb = int((a.cluster_name == BROAD).sum())
    ext = json.loads((RES / "typology_extras.json").read_text())
    sc = ext["screen"]["type_shares"][BROAD]
    out["newcombe_broad_vs_screen"] = newcombe(kb, len(a), sc["k"], sc["n"])
    if "heldout" in ext:
        ho = ext["heldout"]["type_shares"][BROAD]
        out["newcombe_broad_vs_heldout"] = newcombe(kb, len(a), ho["k"], ho["n"])
    rp = a[a.rule_parity]
    out["rule_parity_subset"] = dict(n=len(rp), broad=share(int((rp.cluster_name == BROAD).sum()), len(rp)))
    out["crosstabs"] = crosstabs(a, ["branch_group", "F_band"], check=None)
    out["lower_bound_note"] = ("178/191 MeSH concepts have PubMed-route works only, which deflates subfield breadth; "
                               "the MeSH BROAD share is a LOWER BOUND on the share that would be typed broad under full retrieval")
    # coverage bias on the 13 retrieval_complete concepts
    cov = pd.read_parquet(MR / "mesh_indicators_pubmed_only_rc.parquet")
    rc_ids = sorted(pop[pop.retrieval_complete].concept_id)
    a_all = a[a.concept_id.isin(rc_ids)].set_index("concept_id")
    a_pub = assign_series(cov, rc_ids).set_index("concept_id")
    common = a_all.index.intersection(a_pub.index)
    switch = int((a_all.loc[common, "cluster"] != a_pub.loc[common, "cluster"]).sum())
    j = ind[ind.concept_id.isin(rc_ids)].merge(cov, on=["concept_id", "year"], suffixes=("_all", "_pub"))
    j = j[j.year >= j.F_all] if "F_all" in j.columns else j
    defl = {ch: dict(mean_all=float(j[f"{ch}_all"].mean()), mean_pubmed_only=float(j[f"{ch}_pub"].mean()),
                     mean_diff_all_minus_pub=float((j[f"{ch}_all"] - j[f"{ch}_pub"]).mean()))
            for ch in ("H", "H_rar", "RS", "active_subfields_3y")}
    out["coverage_bias"] = dict(n=len(common), switch=share(switch, len(common)),
                                broad_all_works=int((a_all.loc[common, "cluster_name"] == BROAD).sum()),
                                broad_pubmed_only=int((a_pub.loc[common, "cluster_name"] == BROAD).sum()),
                                direction=[f"{a_pub.loc[c, 'cluster_name']} -> {a_all.loc[c, 'cluster_name']}" for c in common
                                           if a_all.loc[c, "cluster"] != a_pub.loc[c, "cluster"]],
                                channel_deflation=defl)
    return out, a


def year_shuffle_null(res: pd.DataFrame, obs: float, draws: int = 1000) -> dict:
    """The frozen leadlag.main year-shuffle null, replicated line for line (it is inline in main, not a function)."""
    rng = np.random.default_rng(2026)
    null = []
    for _ in range(draws):
        cats = []
        for r in res.itertuples(index=False):
            e = r.exp_onset if (r.exp_onset is not None and not r.exp_from_start and np.isfinite(r.exp_onset)) else None
            d = r.diff_onset if (r.diff_onset is not None and not r.diff_from_start and np.isfinite(r.diff_onset)) else None
            if e is None or d is None:
                continue
            ey = [y for y in r.exp_eval_years if y != r.exp_eval_years[0]] or r.exp_eval_years
            dy = [y for y in r.diff_eval_years if y != r.diff_eval_years[0]] or r.diff_eval_years
            e2, d2 = rng.choice(ey), rng.choice(dy)
            cats.append(1.0 if e2 < d2 else 0.0)
        null.append(np.mean(cats) if cats else np.nan)
    null = np.array(null)
    ok = np.isfinite(null)
    if not ok.any() or obs is None or not np.isfinite(obs):
        return dict(draws=draws, null_mean=float(np.nanmean(null)) if ok.any() else None, p_one_sided_greater=None)
    return dict(draws=draws, null_mean=float(np.nanmean(null)), null_ci=np.nanpercentile(null, [2.5, 97.5]).tolist(),
                p_one_sided_greater=float((np.sum(null[ok] >= obs) + 1) / (ok.sum() + 1)))


def leadlag_part(pop: pd.DataFrame, ind: pd.DataFrame, cp: pd.DataFrame, feat: pd.DataFrame) -> dict:
    from leadlag import boot_share, new_active_years, run_all, share_ef
    ids = sorted(pop.concept_id)
    f = feat[["concept_id", "year", "wdeg_pctl_focal", "wdeg_pctl", "k", "s"]]
    L = ind[["concept_id", "year", "F", "H_rar", "vol3"]].merge(f, on=["concept_id", "year"], how="left")
    net = feat[(feat.k.fillna(0) > 0) | (feat.s.fillna(0) > 0)]
    fa = net.groupby("concept_id").year.min().to_dict()
    new_act = new_active_years(cp[["concept_id", "year", "subfield"]])
    res = run_all(L, ids, fa, new_act, pct_col="wdeg_pctl_focal")
    obs, n_both = share_ef(res)
    out = dict(primary=dict(definition="expansion: wdeg_pctl_focal +10 in 2 consecutive years (y >= first_attach+1); diffusion: frozen",
                            n_concepts=len(res), category_counts=res.category.value_counts().to_dict(),
                            category_counts_incl_from_start=res.category_incl_from_start.value_counts().to_dict(),
                            exp_from_start=int(res.exp_from_start.sum()), diff_from_start=int(res.diff_from_start.sum()),
                            n_both_onsets=n_both, share_expansion_first=obs,
                            share_expansion_first_ci=boot_share(res)[1:] if n_both else [None, None],
                            share_incl_from_start=share_ef(res, "category_incl_from_start")[0],
                            n_both_incl_from_start=share_ef(res, "category_incl_from_start")[1]))
    out["null"] = year_shuffle_null(res, obs)
    grid = []
    for g in (5, 10, 15, 20):
        for h in (0.1, 0.2, 0.3):
            rr = run_all(L, ids, fa, new_act, gain=g, rise=h, pct_col="wdeg_pctl_focal")
            s_, n_ = share_ef(rr)
            ci = boot_share(rr, B=1000) if n_ else [None, None, None]
            grid.append(dict(exp_gain=g, diff_rise=h, n_both=n_, share_expansion_first=s_, ci_lo=ci[1], ci_hi=ci[2],
                             share_diffusion_first=float((rr.category == "diffusion_first").sum() / max(n_, 1))))
    pd.DataFrame(grid).to_csv(MR / "mesh_leadlag_grid.csv", index=False)
    out["grid"] = grid
    sec = {}
    for name, kw in (("cumulative_2yr", dict(variant="cum2", pct_col="wdeg_pctl_focal")), ("all_node_wdeg_pctl", dict(pct_col="wdeg_pctl"))):
        rr = run_all(L, ids, fa, new_act, **kw)
        s_, n_ = share_ef(rr)
        sec[name] = dict(n_both=n_, share_expansion_first=s_, ci=boot_share(rr, B=1000)[1:] if n_ else [None, None],
                         counts=rr.category.value_counts().to_dict())
    out["secondary"] = sec
    import statsmodels.formula.api as smf
    p = L[L.concept_id.isin(ids)].sort_values(["concept_id", "year"]).copy()
    p["dH"] = p.groupby("concept_id").H_rar.diff()
    p["dP"] = p.groupby("concept_id").wdeg_pctl_focal.diff()
    for k in (1, 2):
        p[f"dP_l{k}"] = p.groupby("concept_id").dP.shift(k)
        p[f"dH_l{k}"] = p.groupby("concept_id").dH.shift(k)
    gr = {}
    for yv, xs in (("dH", ["dP_l1", "dP_l2", "dH_l1", "dH_l2"]), ("dP", ["dH_l1", "dH_l2", "dP_l1", "dP_l2"])):
        q = p.dropna(subset=[yv] + xs)
        fit = smf.ols(f"{yv} ~ {' + '.join(xs)} + C(concept_id)", q).fit(cov_type="cluster", cov_kwds={"groups": pd.factorize(q.concept_id)[0]})
        gr[f"{yv}_on_lags"] = dict(n=len(q), n_concepts=int(q.concept_id.nunique()),
                                   coefs={x: dict(b=float(fit.params[x]), se=float(fit.bse[x]), p=float(fit.pvalues[x]),
                                                  ci=[float(v) for v in fit.conf_int().loc[x]]) for x in xs})
    out["granger_panel"] = gr
    out["pct_alt_reference_sensitivity"] = ("NOT RUN: MeSH strengths s come from the MeSH background co-occurrence graph (post-stratified "
                                            "259,716-work sample), whose strength scale is not the main-pool X3 snapshot scale; placing them "
                                            "into sealed/pct_alt_reference.npz would compare numbers from different graphs")
    res["F"] = res.concept_id.map(pop.set_index("concept_id").F)
    res["first_attach"] = res.concept_id.map(fa)
    res["n_exp_eval_years"] = res.exp_eval_years.map(len)
    res["n_diff_eval_years"] = res.diff_eval_years.map(len)
    res.drop(columns=["exp_eval_years", "diff_eval_years"]).to_csv(MR / "mesh_leadlag_by_concept.csv", index=False)
    return out


def roles_part(pop: pd.DataFrame, feat: pd.DataFrame) -> dict:
    from leiden_seeds import alluvial_from
    from roles import assign_roles, ga_class
    snap = E4 / "results/snapshots"
    z = feat.z_within.dropna()
    nec = dict(n_concept_years=int(len(z)), max_z_within=float(z.max()), q99=float(z.quantile(0.99)), median=float(z.median()),
               share_ge_1=float((z >= 1).mean()), share_ge_2_5=float((z >= 2.5).mean()),
               core_growing_can_fire=bool(z.max() >= 1.0))
    comm = pd.read_parquet(E4 / "results/communities_y.parquet")
    memb = {int(y): g.rename(columns={"tag": "node", "comm_local": "comm"})[["node", "comm"]] for y, g in comm.groupby("year")}
    per, ev = alluvial_from(memb, thr=0.3, min_size=5)
    pid = {(int(y), int(c)): int(p) for y, c, p in zip(per.year, per.comm, per.pid)}
    size = {(int(y), int(p)): int(s) for y, p, s in zip(per.year, per.pid, per["size"])}
    birth = ev[ev.event == "birth"].groupby("pid").year.min().to_dict()
    rows = []
    for y in range(2000, 2025):
        fo = pd.read_parquet(snap / f"focal_{y}.parquet")
        nd = pd.read_parquet(snap / f"nodes_{y}.parquet")
        cmap = dict(zip(nd.tag, nd.comm_local))
        wmap = dict(zip(nd.tag, nd.W_i))
        for r in fo.itertuples(index=False):
            nb = [cmap.get(int(t), -1) for t in (r.neighbours if r.neighbours is not None else [])]
            nb = [c for c in nb if c >= 0]
            if not nb:
                continue
            vc = pd.Series(nb).value_counts(normalize=True)
            dom_local = int(r.module_local) if r.module_local is not None and np.isfinite(r.module_local) and r.module_local >= 0 else int(vc.index[0])
            peers = nd[nd.comm_local == dom_local].W_i.values
            founder_rank = int((peers > r.s).sum()) + 1 if np.isfinite(r.s) else 10 ** 6
            p_ = pid.get((y, dom_local), -1)
            rows.append(dict(concept_id=r.concept_id, year=y, P=r.P, wmz=r.z_within, n_comm_25pct=int((vc >= 0.25).sum()),
                             dom_share=float(vc.get(dom_local, 0.0)), dom=p_, founder_rank=founder_rank,
                             size=size.get((y, p_), np.nan) if p_ >= 0 else np.nan,
                             size_prev=size.get((y - 1, p_), np.nan) if p_ >= 0 else np.nan,
                             dom_existed_prev=bool(p_ >= 0 and (y - 1, p_) in size), birth_year=birth.get(p_, np.nan) if p_ >= 0 else np.nan))
    d = pd.DataFrame(rows).sort_values(["concept_id", "year"]).reset_index(drop=True)
    fa = d.groupby("concept_id").year.min().to_dict()
    prev = d.groupby("concept_id").dom.shift(1)
    prev_year = d.groupby("concept_id").year.shift(1)
    d["dom_prev"] = np.where(prev_year == d.year - 1, prev, np.nan)
    d["first_attach"] = d.concept_id.map(fa)
    d = d[d.year >= d.first_attach + 1].reset_index(drop=True)
    d["P"] = d.P.astype(float)
    fl = assign_roles(d)
    d = pd.concat([d, fl], axis=1)
    d["GA_class"] = [ga_class(zz, pp) for zz, pp in zip(d.wmz.astype(float), d.P.astype(float))]
    d.to_parquet(MR / "mesh_roles.parquet", index=False)
    n = len(d)
    rs = {r: share(int((d.primary == r).sum()), n) for r in ["FOUNDER", "CORE_GROWING", "BRIDGE", "MIGRANT", "STAYER", "OTHER"]}
    ga = {g: share(int((d.GA_class == g).sum()), n) for g in sorted(d.GA_class.unique())}
    T = pd.crosstab(d.groupby("concept_id").primary.shift(1), d.primary)
    return dict(necessary_condition=nec, n_concept_years=n, n_concepts=int(d.concept_id.nunique()), role_shares=rs, GA_classes=ga,
                flag_rates={r: share(int(d[r].sum()), n) for r in ["FOUNDER", "CORE_GROWING", "BRIDGE", "MIGRANT", "STAYER"]},
                transition_counts=T.to_dict(), founder_wilson_upper=wilson(int(d.FOUNDER.sum()), n)[1],
                core_growing_wilson_upper=wilson(int(d.CORE_GROWING.sum()), n)[1],
                seed_stability="NOT ASSESSED (5-seed Leiden rerun on the MeSH background graph not run within the time budget; roles use the "
                               "single best-of-5 partition of art_yWUkgWWKyq_h)",
                construction=("dom = art_yWUkgWWKyq_h module_local (weighted focal attachment) mapped to persistent ids by the frozen alluvial_from(0.3, 5); "
                              "P and wmz = that artifact's weighted P and z_within; n_comm_25pct from UNWEIGHTED neighbour counts per community "
                              "(focal neighbour weights are not stored); founder_rank = rank of focal s among the dominant community's node strengths W_i"),
                caveat="descriptive population contrast, not a replication of the main-pool role shares (different substrate and attachment rule)")


def patterns_part() -> dict:
    def from_csv(p, pop_label):
        t = pd.read_csv(p)
        t = t[(t.population == pop_label) & (t.subset == "all") & (t.threshold_version == "recomputed_hydrated")]
        return {r.pattern: dict(k=int(r["count"]), n=int(r.n), freq=float(r.freq)) for _, r in t.iterrows()}
    out = {"screen": from_csv(E8 / "results/patterns.csv", "screen_MAIN")}
    if (HO / "results/patterns.csv").exists():
        out["heldout"] = from_csv(HO / "results/patterns.csv", "screen_MAIN")
    mb = pd.read_csv(E4 / "results/rq1_patterns_by_concept.csv")
    n = len(mb)
    mp = {"EARLY_BRIDGING": "early_bridging", "INCUBATION_THEN_EXPANSION": "incubation_expansion", "GRADUAL_CENTRALISATION": "gradual_centralisation"}
    out["mesh"] = {k: dict(k=int(mb[v].astype(bool).sum()), n=n, freq=float(mb[v].astype(bool).mean())) for k, v in mp.items()}
    for pop in out:
        for k, v in out[pop].items():
            v["wilson_ci"] = wilson(v["k"], v["n"])
    diffs = {}
    for pat in mp:
        for a, b in (("screen", "mesh"), ("heldout", "mesh"), ("heldout", "screen")):
            if a in out and b in out and pat in out[a] and pat in out[b]:
                diffs[f"{pat}|{a}-{b}"] = newcombe(out[a][pat]["k"], out[a][pat]["n"], out[b][pat]["k"], out[b][pat]["n"])
    return dict(frequencies=out, newcombe=diffs,
                note="MeSH pattern flags from art_yWUkgWWKyq_h (reproduced by exp8); aligned/age-adjusted variants exist only for main-pool populations")


def run() -> dict:
    MR.mkdir(parents=True, exist_ok=True)
    h = check_spec()
    pop = pd.read_parquet(MR / "mesh_population.parquet")
    ind = pd.read_parquet(MR / "mesh_indicators.parquet")
    cp = pd.read_parquet(MR / "mesh_cpapers.parquet")
    feat = pd.read_parquet(E4 / "results/features.parquet")
    ext = json.loads((RES / "typology_extras.json").read_text())
    dist = pd.read_csv(RES / "typology_distances.csv")
    scr_d1 = dist[dist.population == "screen"].d1.values
    out = dict(mesh_spec_sha256=h)
    out["typology"], a = typology_part(pop, ind, scr_d1, ext["screen"]["d1_p95"])
    logger.info(f"MeSH typology {out['typology']['type_shares']}")
    out["leadlag"] = leadlag_part(pop, ind, cp, feat)
    logger.info(f"MeSH lead-lag {out['leadlag']['primary']['category_counts']}")
    out["roles"] = roles_part(pop, feat)
    logger.info(f"MeSH roles {out['roles']['role_shares']}")
    out["patterns"] = patterns_part()
    write_json(RES / "mesh_results.json", out)
    return out
