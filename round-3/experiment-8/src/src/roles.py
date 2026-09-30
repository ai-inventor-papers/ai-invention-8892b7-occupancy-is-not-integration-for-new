#!/usr/bin/env python3
"""STAGE 5: community roles per concept-year with a 5-seed Leiden agreement layer, Guimera-Amaral cross-tab,
threshold grid, role transitions and a discrete-time logit of host-subfield entry on the lagged role.

The rules are written to results/roles_spec.json and hashed BEFORE any role statistic is computed.
"""
from __future__ import annotations

import json
import warnings

import numpy as np
import pandas as pd
from loguru import logger

from common import NEW_SEEDS, RES, TYP, WORK, YEARS, C as CONF, load_sealed, setup_logging, sha256_json, write_json

LS = WORK / "leiden_seeds"
SEEDS = [0] + NEW_SEEDS
ROLES = ["FOUNDER", "CORE_GROWING", "BRIDGE", "MIGRANT", "STAYER", "OTHER"]

SPEC = dict(
    unit="concept-year y >= first attachment year + 1 (first year with frame-type c-papers in the snapshot)",
    dominant="dom(y) = persistent id of the community holding the largest all-type tag weight (plural community); "
             "communities < 5 nodes have no persistent id (dom = -1)",
    P="P_rar (m = 10, 50 draws, iteration-2 seeds); fallback P_raw if P_rar is NaN (flagged)",
    STAYER=dict(rule="dom(y) == dom(y-1) >= 0 AND P < P_stay", P_stay=0.3),
    MIGRANT=dict(rule="dom(y) != dom(y-1), both >= 0, AND dom(y) existed in y-1 (its persistent id is present at y-1)"),
    BRIDGE=dict(rule="P >= P_bridge OR >= 2 communities each holding >= share_bridge of the concept's all-type tag weight",
                P_bridge=0.6, share_bridge=0.25),
    CORE_GROWING=dict(rule="wmz >= z_core AND size(dom, y) >= (1 + growth) * size(dom, y-1)", z_core=1.0, growth=0.10),
    FOUNDER=dict(rule="dom(y) was born (alluvial 'birth', no Jaccard >= 0.3 match in y-1) in [first_attach-1, first_attach+1] "
                      "AND y - birth_year <= 1 AND the concept ranks in the top 5 of dom(y) by within-community strength "
                      "(its frame-type tag weight into dom vs k_own of the community's members)", top=5),
    precedence=ROLES,
    robust="the modal primary role over the 5 NEW seeds (101-105) occurs in >= 3 of them",
    GA=dict(hub_z=2.5, nonhub={"R1_ultra_peripheral": 0.05, "R2_peripheral": 0.62, "R3_connector": 0.80, "R4_kinless": 1.0},
            hub={"R5_provincial_hub": 0.30, "R6_connector_hub": 0.75, "R7_kinless_hub": 1.0}),
    grid=dict(P_stay=[0.2, 0.3, 0.4], P_bridge=[0.5, 0.6, 0.7], share_bridge=[0.2, 0.25, 0.33], z_core=[0.5, 1.0, 1.5],
              growth=[0.05, 0.10, 0.20]),
)


def load_seed_tables() -> tuple[pd.DataFrame, dict]:
    cm = pd.concat([pd.read_parquet(LS / f"cm_y{y}.parquet") for y in YEARS], ignore_index=True)
    comm = {}
    for s in SEEDS:
        per = pd.read_parquet(LS / f"persistent_s{s}.parquet")
        ev = pd.read_parquet(LS / f"events_s{s}.parquet")
        comm[s] = dict(pid={(int(y), int(c)): int(p) for y, c, p in zip(per.year, per.comm, per.pid)},
                       size={(int(y), int(p)): int(z) for y, p, z in zip(per.year, per.pid, per["size"])},
                       birth=ev[ev.event == "birth"].groupby("pid").year.min().to_dict())
    return cm, comm


def role_inputs(cm: pd.DataFrame, comm: dict, first_attach: dict) -> pd.DataFrame:
    rows = []
    for s, g in cm.groupby("seed"):
        cs = comm[s]
        g = g.sort_values(["concept_id", "year"])
        pid = np.array([cs["pid"].get((int(y), int(c)), -1) if c >= 0 else -1 for y, c in zip(g.year, g.dom_comm)])
        d = g[["concept_id", "year", "seed", "P_raw", "P_rar", "wmz", "n_comm_25pct", "n_comm_10pct_all", "founder_rank",
               "dom_share", "cw_all_json"]].copy()
        d["dom"] = pid
        d["size"] = [cs["size"].get((int(y), int(p)), np.nan) if p >= 0 else np.nan for y, p in zip(d.year, d.dom)]
        d["size_prev"] = [cs["size"].get((int(y) - 1, int(p)), np.nan) if p >= 0 else np.nan for y, p in zip(d.year, d.dom)]
        d["dom_existed_prev"] = [bool(p >= 0 and (int(y) - 1, int(p)) in cs["size"]) for y, p in zip(d.year, d.dom)]
        d["birth_year"] = [cs["birth"].get(int(p), np.nan) if p >= 0 else np.nan for p in d.dom]
        prev = d.groupby("concept_id").dom.shift(1)
        prev_year = d.groupby("concept_id").year.shift(1)
        d["dom_prev"] = np.where(prev_year == d.year - 1, prev, np.nan)
        d["P"] = d.P_rar.where(d.P_rar.notna(), d.P_raw)
        d["P_fallback"] = d.P_rar.isna() & d.P_raw.notna()
        d["first_attach"] = d.concept_id.map(first_attach)
        rows.append(d)
    out = pd.concat(rows, ignore_index=True)
    return out[out.year >= out.first_attach + 1].reset_index(drop=True)


def assign_roles(d: pd.DataFrame, P_stay=0.3, P_bridge=0.6, share_bridge=0.25, z_core=1.0, growth=0.10, top=5) -> pd.DataFrame:
    dom, prev = d.dom.values, d.dom_prev.values
    P = d.P.values
    stayer = (dom >= 0) & (prev == dom) & (P < P_stay)
    migrant = (dom >= 0) & np.isfinite(prev) & (prev >= 0) & (prev != dom) & d.dom_existed_prev.values
    n_share = d.n_comm_25pct.values if share_bridge == 0.25 else d["_n_share"].values
    bridge = (P >= P_bridge) | (n_share >= 2)
    core = (d.wmz.values >= z_core) & d.dom_existed_prev.values & (d["size"].values >= (1 + growth) * d.size_prev.values)
    by = d.birth_year.values
    fa = d.first_attach.values
    founder = (dom >= 0) & np.isfinite(by) & (by >= fa - 1) & (by <= fa + 1) & (d.year.values - by <= 1) & \
              (d.year.values >= by) & (d.founder_rank.values <= top)
    flags = pd.DataFrame(dict(FOUNDER=founder, CORE_GROWING=core, BRIDGE=bridge, MIGRANT=migrant, STAYER=stayer), index=d.index)
    prim = np.full(len(d), "OTHER", dtype=object)
    for r in reversed(ROLES[:-1]):
        prim[flags[r].values] = r
    flags["primary"] = prim
    return flags


def n_share_at(d: pd.DataFrame, share: float) -> np.ndarray:
    out = []
    for js in d.cw_all_json.values:
        v = np.array(list(json.loads(js).values()), dtype=float)
        tot = v.sum()
        out.append(int((v >= share * tot).sum()) if tot > 0 else 0)
    return np.array(out)


def ga_class(z: float, P: float) -> str:
    if not (np.isfinite(z) and np.isfinite(P)):
        return "NA"
    if z >= 2.5:
        return "R5_provincial_hub" if P <= 0.30 else ("R6_connector_hub" if P <= 0.75 else "R7_kinless_hub")
    return "R1_ultra_peripheral" if P <= 0.05 else ("R2_peripheral" if P <= 0.62 else ("R3_connector" if P <= 0.80 else "R4_kinless"))


def boot_share_by(df: pd.DataFrame, by: str, B: int = 1000, seed: int = 0) -> pd.DataFrame:
    """Role shares within each level of `by`, 95% CI from a concept bootstrap."""
    rng = np.random.default_rng(seed)
    cons = df.concept_id.unique()
    idx = {c: np.where(df.concept_id.values == c)[0] for c in cons}
    levels = sorted(df[by].dropna().unique())
    obs = {(l, r): float(np.mean(df.loc[df[by] == l, "role"] == r)) for l in levels for r in ROLES}
    bs = {k: [] for k in obs}
    for _ in range(B):
        take = np.concatenate([idx[c] for c in rng.choice(cons, len(cons))])
        sub = df.iloc[take]
        for l in levels:
            s = sub[sub[by] == l]
            for r in ROLES:
                bs[(l, r)].append(float(np.mean(s.role == r)) if len(s) else np.nan)
    rows = []
    for (l, r), v in obs.items():
        lo, hi = np.nanpercentile(bs[(l, r)], [2.5, 97.5])
        rows.append({by: l, "role": r, "share": v, "ci_lo": lo, "ci_hi": hi, "n_rows": int((df[by] == l).sum())})
    return pd.DataFrame(rows)


def host_entry_panel(ind: pd.DataFrame, pool: pd.DataFrame, ids: list[str], min_papers: int = 1) -> pd.DataFrame:
    cp = pd.read_parquet(WORK / "cp_hyd.parquet", columns=["concept_id", "year", "subfield"])
    cp = cp[cp.concept_id.isin(set(ids)) & (cp.subfield >= 0)]
    osub = pool.set_index("concept_id").origin_subfield_id
    ent = []
    for c, g in cp.groupby("concept_id"):
        o = osub.get(c)
        cnt = g.groupby(["subfield", "year"]).size().reset_index(name="n").sort_values("year")
        cnt["cum"] = cnt.groupby("subfield").n.cumsum()
        first = cnt[cnt.cum >= min_papers].groupby("subfield").year.min()
        first = first[first.index != (int(o) if o is not None and o == o else -999)]
        for y, n in first.value_counts().items():
            ent.append(dict(concept_id=c, year=int(y), n_new_host=int(n)))
    e = pd.DataFrame(ent)
    panel = ind[ind.concept_id.isin(set(ids)) & (ind.age >= 1) & (ind.age <= 15) & (ind.year <= 2024)][
        ["concept_id", "year", "age", "vol", "cum_vol", "cum_subfields", "route"]].copy()
    panel = panel.merge(e, on=["concept_id", "year"], how="left")
    panel["n_new_host"] = panel.n_new_host.fillna(0).astype(int)
    panel["any_entry"] = (panel.n_new_host > 0).astype(int)
    lagc = ind[["concept_id", "year", "cum_vol", "cum_subfields"]].copy()
    lagc["year"] += 1
    panel = panel.drop(columns=["cum_vol", "cum_subfields"]).merge(
        lagc.rename(columns={"cum_vol": "cum_vol_lag", "cum_subfields": "cum_subfields_lag"}), on=["concept_id", "year"], how="left")
    panel[["cum_vol_lag", "cum_subfields_lag"]] = panel[["cum_vol_lag", "cum_subfields_lag"]].fillna(0)
    return panel


def fit_entry(panel: pd.DataFrame, role_col: str | None, outcome: str = "any_entry", family: str = "logit",
              extra_terms: str = "") -> dict:
    import statsmodels.formula.api as smf
    import statsmodels.api as sm
    d = panel.dropna(subset=[role_col]).copy() if role_col else panel.copy()
    counts = d.groupby(role_col)[outcome].agg(["size", "sum"]) if role_col else pd.DataFrame(columns=["size", "sum"])
    merged = []
    for r in list(counts.index):
        if r != "STAYER" and (counts.loc[r, "sum"] < 5 or counts.loc[r, "size"] - counts.loc[r, "sum"] < 5) and family == "logit":
            merged.append(r)
    if merged:
        d[role_col] = d[role_col].replace({r: ("CORE_GROWING" if r == "FOUNDER" else "OTHER") for r in merged})
    role_term = f"C({role_col}, Treatment(reference='STAYER')) + " if role_col else ""
    rhs = (f"{role_term}np.log1p(vol) + np.log1p(cum_vol_lag) + age + I(age**2) + "
           f"np.log1p(cum_subfields_lag) + C(route){extra_terms}")
    groups = pd.factorize(d.concept_id)[0]
    res, method = None, "mle_cluster"
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        try:
            if family == "logit":
                res = smf.logit(f"{outcome} ~ {rhs}", d).fit(disp=0, maxiter=200, cov_type="cluster", cov_kwds={"groups": groups})
            else:
                res = smf.glm(f"{outcome} ~ {rhs}", d, family=sm.families.Poisson()).fit(cov_type="cluster", cov_kwds={"groups": groups})
            if not np.all(np.isfinite(res.bse)):
                raise ValueError("non-finite SE")
        except Exception as e:  # separation / non-convergence -> L2-penalised fit (F6)
            logger.warning(f"entry model {role_col}/{outcome}: {e!r}; using L2-penalised fit")
            method = "l2_penalised_alpha_0.01"
            mod = smf.logit(f"{outcome} ~ {rhs}", d) if family == "logit" else smf.glm(f"{outcome} ~ {rhs}", d, family=sm.families.Poisson())
            res = mod.fit_regularized(alpha=0.01, L1_wt=0.0) if family == "logit" else mod.fit_regularized(alpha=0.01, L1_wt=0.0)
    params = res.params
    try:
        ci = res.conf_int()
        pv = res.pvalues
    except Exception:
        ci = pd.DataFrame({0: params * np.nan, 1: params * np.nan})
        pv = params * np.nan
    terms = {}
    for t in params.index:
        if (role_col and role_col in t) or "robustflag" in t or t.startswith("np.log1p") or t in ("age", "I(age ** 2)"):
            nm = t.split("[T.")[-1].rstrip("]") if (role_col and role_col in t) else t
            terms[nm] = dict(coef=float(params[t]), ratio=float(np.exp(params[t])), ci_lo=float(np.exp(ci.loc[t, 0])),
                             ci_hi=float(np.exp(ci.loc[t, 1])), p=float(pv[t]))
    return dict(family=family, outcome=outcome, role_col=role_col, method=method, n_rows=len(d), n_concepts=int(d.concept_id.nunique()),
                n_events=int(d[outcome].sum()), merged_levels=merged, role_counts=counts.to_dict("index"), terms=terms)


@logger.catch(reraise=True)
def main() -> None:
    setup_logging("roles")
    load_sealed()
    spec_hash = sha256_json(SPEC)
    write_json(RES / "roles_spec.json", dict(spec=SPEC, sha256=spec_hash))
    (RES / "roles_spec_hashlog.jsonl").open("a").write(json.dumps(dict(sha256=spec_hash, utc=pd.Timestamp.utcnow().isoformat())) + "\n")
    ind = pd.read_parquet(RES / "indicators" / "concept_year_indicators_hyd.parquet")
    pool = pd.read_parquet(WORK / "pool_active.parquet")
    scr = pool[(pool.fold == "screen") & (pool.arm == "main")]
    CONF.assert_not_sealed(scr.concept_id)
    main_ids = set(scr.loc[scr.MAIN, "concept_id"])
    first_attach = ind[ind.n_frame > 0].groupby("concept_id").year.min().to_dict()
    cm, comm = load_seed_tables()
    cm = cm[cm.concept_id.isin(set(scr.concept_id))]
    d_base = role_inputs(cm, comm, first_attach)
    Fm = pool.set_index("concept_id").F
    panels = {1: host_entry_panel(ind, pool, sorted(main_ids)), 2: host_entry_panel(ind, pool, sorted(main_ids), min_papers=2)}
    panels[1].to_csv(RES / "entry_panel.csv", index=False)
    res_all = {}
    for variant, suffix in (("predeclared", ""), ("pool_relative", "_poolrel")):
        res_all[variant] = analyse(d_base, variant, suffix, main_ids, Fm, panels, spec_hash)
    write_json(RES / "roles.json", res_all)
    for v, o in res_all.items():
        logger.info(f"roles[{v}]: robust share {o['agreement']['robust_share']:.3f}; robust shares {o['robust_shares']}; "
                    f"entry ORs { {k: round(t['ratio'], 3) for k, t in o['entry_hazard']['primary_logit_robust']['terms'].items() if k.isupper()} }")


def analyse(d_base: pd.DataFrame, variant: str, suffix: str, main_ids: set, Fm: pd.Series, panels: dict, spec_hash: str) -> dict:
    d = d_base.copy()
    fl = assign_roles(d) if variant == "predeclared" else assign_roles_rel(d)
    d = pd.concat([d, fl], axis=1)
    # ---- agreement layer
    piv = d.pivot_table(index=["concept_id", "year"], columns="seed", values="primary", aggfunc="first")
    piv.columns = [f"primary_s{s}" for s in piv.columns]
    new = piv[[f"primary_s{s}" for s in NEW_SEEDS]]
    modal = new.apply(lambda r: r.value_counts().index[0] if r.notna().any() else np.nan, axis=1)
    n_agree = new.apply(lambda r: int(r.value_counts().iloc[0]) if r.notna().any() else 0, axis=1)
    rl = piv.reset_index()
    rl["role_modal"] = modal.values
    rl["n_seed_agree"] = n_agree.values
    rl["robust"] = rl.n_seed_agree >= 3
    rl["seed0_agrees_modal"] = rl.primary_s0 == rl.role_modal
    d0 = d[d.seed == 0].set_index(["concept_id", "year"])
    for col in ["FOUNDER", "CORE_GROWING", "BRIDGE", "MIGRANT", "STAYER", "dom", "P", "P_raw", "wmz", "P_fallback", "size", "birth_year",
                "first_attach"]:
        rl[f"{col}_s0" if col in ("dom", "P", "P_raw", "wmz", "size") else col] = d0[col].reindex(pd.MultiIndex.from_frame(rl[["concept_id", "year"]])).values
    # flag agreement (multi-label) in >= 3/5 new seeds
    for r in ROLES[:-1]:
        fm = d[d.seed.isin(NEW_SEEDS)].groupby(["concept_id", "year"])[r].sum()
        rl[f"{r}_robustflag"] = (fm.reindex(pd.MultiIndex.from_frame(rl[["concept_id", "year"]])).values >= 3)
    rl["age"] = rl.year - rl.concept_id.map(Fm).astype(int)
    rl["GA_class"] = [ga_class(z, P) for z, P in zip(rl.wmz_s0, rl.P_raw_s0)]
    rl["MAIN"] = rl.concept_id.isin(main_ids)
    rl.to_parquet(RES / f"roles{suffix}.parquet", index=False)
    M = rl[rl.MAIN].copy()
    out: dict = dict(variant=variant, spec_sha256=spec_hash, n_concept_years_MAIN=len(M), n_concepts_MAIN=int(M.concept_id.nunique()))
    out["agreement"] = dict(robust_share=float(M.robust.mean()),
                            robust_share_by_role={r: float(g.robust.mean()) for r, g in M.groupby("role_modal")},
                            robust_share_by_year={int(y): float(g.robust.mean()) for y, g in M.groupby("year")},
                            seed0_agrees_modal=float(M.seed0_agrees_modal.mean()),
                            mean_n_seed_agree=float(M.n_seed_agree.mean()),
                            P_rar_fallback_share=float(M.P_fallback.mean()))
    low_agree = out["agreement"]["robust_share"] < 0.5
    out["F5_low_agreement"] = bool(low_agree)
    # seed-averaged shares (mean over the 5 new seeds with between-seed SD) - always reported
    dm = d[d.concept_id.isin(main_ids) & d.seed.isin(NEW_SEEDS)]
    sh = dm.groupby("seed").primary.value_counts(normalize=True).unstack(fill_value=0)
    out["seed_averaged_shares"] = {r: dict(mean=float(sh[r].mean()) if r in sh else 0.0, sd=float(sh[r].std()) if r in sh else 0.0)
                                   for r in ROLES}
    sh0 = d[d.concept_id.isin(main_ids) & (d.seed == 0)].primary.value_counts(normalize=True)
    out["seed0_shares"] = {r: float(sh0.get(r, 0.0)) for r in ROLES}
    R = M[M.robust].copy()
    R["role"] = R.role_modal
    out["robust_shares"] = {r: float((R.role == r).mean()) for r in ROLES}
    out["robust_shares_all_rows_seed0"] = out["seed0_shares"]
    # ---- shares by age (0..15), bootstrap CI over concepts
    R["age_c"] = R.age.clip(upper=15)
    by_age = boot_share_by(R[(R.age >= 0) & (R.age <= 15)], "age_c")
    by_age.to_csv(RES / f"role_shares_by_age{suffix}.csv", index=False)
    # ---- GA cross-tab
    ga = pd.crosstab(R.role, R.GA_class)
    ga.to_csv(RES / f"roles_x_GA{suffix}.csv")
    out["GA_crosstab"] = ga.to_dict()
    out["GA_class_shares"] = R.GA_class.value_counts(normalize=True).to_dict()
    # ---- transitions (robust rows in both years)
    Rk = R.set_index(["concept_id", "year"]).role
    tr = []
    for (c, y), r in Rk.items():
        p = Rk.get((c, y - 1))
        if p is not None:
            tr.append((p, r))
    T = pd.crosstab(pd.Series([a for a, _ in tr], name="from"), pd.Series([b for _, b in tr], name="to"))
    T = T.reindex(index=ROLES, columns=ROLES, fill_value=0)
    Tn = T.div(T.sum(axis=1).replace(0, np.nan), axis=0)
    T.to_csv(RES / f"role_transition_counts{suffix}.csv")
    Tn.to_csv(RES / f"role_transition_matrix{suffix}.csv")
    out["transition_n_pairs"] = int(T.values.sum())
    # ---- threshold grid (seed 0, MAIN, all rows; pre-declared rules only)
    if variant == "predeclared":
        _grid(d, main_ids)
    # ---- by typology cluster
    asg_p = TYP / "assignments.csv"
    if asg_p.exists():
        asg = pd.read_csv(asg_p)
        R["cluster_name"] = R.concept_id.map(asg.set_index("concept_id").cluster_name)
        bc = boot_share_by(R.dropna(subset=["cluster_name"]), "cluster_name")
        bc.to_csv(RES / f"role_shares_by_cluster{suffix}.csv", index=False)
        from typology import perm_chi2
        out["role_x_cluster_perm_chi2"] = perm_chi2(R.dropna(subset=["cluster_name"]).cluster_name, R.dropna(subset=["cluster_name"]).role, n_perm=2000)
        out["role_x_cluster_note"] = "concept-years are not independent; permutation p is descriptive (labels permuted at row level)"
    # ---- entry hazard
    panel = panels[1]
    lagr = rl[["concept_id", "year", "role_modal", "robust", "primary_s0"] + [f"{r}_robustflag" for r in ROLES[:-1]]].copy()
    lagr["year"] += 1
    P1 = panel.merge(lagr, on=["concept_id", "year"], how="left")
    P1["role_lag"] = np.where(P1.robust == True, P1.role_modal, np.nan)  # noqa: E712
    P1["role_lag_all"] = P1.primary_s0
    ent = {"primary_logit_robust": fit_entry(P1, "role_lag")}
    ent["all_rows_seed0_logit"] = fit_entry(P1, "role_lag_all")
    P2 = panels[2].merge(lagr, on=["concept_id", "year"], how="left")
    P2["role_lag"] = np.where(P2.robust == True, P2.role_modal, np.nan)  # noqa: E712
    ent["entry_ge2_papers_logit_robust"] = fit_entry(P2, "role_lag")
    ent["poisson_count_robust"] = fit_entry(P1, "role_lag", outcome="n_new_host", family="poisson")
    P3 = P1.dropna(subset=["role_lag"]).copy()
    for r in ROLES[:-1]:
        P3[f"{r}_robustflag"] = P3[f"{r}_robustflag"].astype(float)
    usable = [r for r in ["FOUNDER", "CORE_GROWING", "BRIDGE", "MIGRANT", "STAYER"]
              if P3[f"{r}_robustflag"].sum() >= 5 and (P3[f"{r}_robustflag"] * P3.any_entry).sum() >= 1]
    flags_terms = " + " + " + ".join(f"{r}_robustflag" for r in usable)
    try:
        ent["multilabel_flags_logit"] = fit_entry(P3, None, extra_terms=flags_terms)
    except Exception as e:  # noqa: BLE001
        logger.warning(f"multilabel flag model failed: {e!r}")
        ent["multilabel_flags_logit"] = dict(error=repr(e))
    out["entry_hazard"] = ent
    return out




def _grid(d: pd.DataFrame, main_ids: set) -> None:
    d0m = d[(d.seed == 0) & d.concept_id.isin(main_ids)].copy()
    grid = []
    base = dict(P_stay=0.3, P_bridge=0.6, share_bridge=0.25, z_core=1.0, growth=0.10)
    share_cache = {sb: n_share_at(d0m, sb) for sb in SPEC["grid"]["share_bridge"]}
    for par, vals in SPEC["grid"].items():
        for v in vals:
            kw = dict(base, **{par: v})
            dd = d0m.copy()
            dd["_n_share"] = share_cache[kw["share_bridge"]]
            f = assign_roles(dd, **kw)
            vc = f.primary.value_counts(normalize=True)
            grid.append(dict(param=par, value=v, **{r: float(vc.get(r, 0.0)) for r in ROLES}))
    pd.DataFrame(grid).to_csv(RES / "roles_threshold_grid.csv", index=False)


def assign_roles_rel(d: pd.DataFrame, q: float = 0.90, founder_share: float = 0.5) -> pd.DataFrame:
    """Declared POST-HOC pool-relative variant: CORE_GROWING uses wmz >= the per-(seed, year) 90th percentile of wmz among
    screen main-arm concept-years (instead of the absolute wmz >= 1 that attached pool concepts never reach); FOUNDER replaces
    the top-5 within-community rank by 'the newborn dominant community holds >= 50% of the concept's all-type tag weight'."""
    thr = d.groupby(["seed", "year"]).wmz.transform(lambda v: v.quantile(q) if v.notna().any() else np.nan)
    f = assign_roles(d.assign(wmz=np.where(d.wmz >= thr, 10.0, -10.0), founder_rank=np.where(d.dom_share >= founder_share, 1, 10 ** 6)),
                     z_core=1.0)
    return f


if __name__ == "__main__":
    main()
