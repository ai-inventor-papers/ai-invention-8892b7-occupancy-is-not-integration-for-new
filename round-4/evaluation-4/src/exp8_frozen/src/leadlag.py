#!/usr/bin/env python3
"""STAGE 7: lead-lag between network-expansion onset and disciplinary-diffusion onset.

EXPANSION onset (primary): first y >= first_attach + 1 with pct_alt(y) - pct_alt(y-1) >= g AND pct_alt(y+1) - pct_alt(y) >= g
(g = 10 points; both differences defined). DIFFUSION onset (primary): first y with H_rar(y) - H_rar(y-2) >= h nats (h = 0.2;
both defined) AND a new active subfield appears in y (>= 2 c-papers in d within [y-2, y], d never active before y).
Left-censoring: a condition holding at the first evaluable year is 'from_start' and excluded from the ordered share
(included in a sensitivity). Null: 1,000 draws redrawing each existing onset uniformly over its evaluable years.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from loguru import logger

from common import RES, TYP, WORK, C as CONF, boot_mean_ci, load_sealed, setup_logging, write_json

CATS = ["expansion_first", "same_year", "diffusion_first", "expansion_only", "diffusion_only", "neither"]


def new_active_years(cp: pd.DataFrame) -> dict:
    """Per concept: set of years y in which a subfield becomes active (>= 2 c-papers within [y-2, y]) for the first time."""
    out = {}
    kn = cp[cp.subfield >= 0]
    for c, g in kn.groupby("concept_id"):
        cnt = g.groupby(["subfield", "year"]).size().unstack(fill_value=0)
        cnt = cnt.reindex(columns=range(1998, 2025), fill_value=0)
        roll = cnt.T.rolling(3, min_periods=1).sum().T
        yrs = set()
        for _, row in roll.iterrows():
            act = row[row >= 2]
            if len(act):
                yrs.add(int(act.index.min()))
        out[c] = yrs
    return out


def onsets_for(g: pd.DataFrame, fa: int, new_act: set, gain: float, rise: float, exp_variant: str = "2consec",
               pct_col: str = "pct_alt") -> dict:
    s = g.set_index("year")
    pct = s[pct_col].to_dict()
    H = s.H_rar.to_dict()
    ys = sorted(s.index)
    # expansion
    ev_e = []
    for y in ys:
        if y < fa + 1:
            continue
        a, b, c_ = pct.get(y - 1), pct.get(y), pct.get(y + 1)
        if exp_variant == "2consec":
            if a is None or b is None or c_ is None or not (np.isfinite(a) and np.isfinite(b) and np.isfinite(c_)):
                continue
            ev_e.append((y, (b - a >= gain) and (c_ - b >= gain)))
        else:  # 2-year cumulative
            if a is None or c_ is None or not (np.isfinite(a) and np.isfinite(c_)):
                continue
            ev_e.append((y, c_ - a >= gain))
    ev_d = []
    for y in ys:
        a, b = H.get(y - 2), H.get(y)
        if a is None or b is None or not (np.isfinite(a) and np.isfinite(b)):
            continue
        ev_d.append((y, (b - a >= rise) and (y in new_act)))
    def first(ev):
        on = [y for y, f in ev if f]
        if not on:
            return None, False
        return on[0], on[0] == ev[0][0]
    e, e_ls = first(ev_e)
    d, d_ls = first(ev_d)
    return dict(exp_onset=e, exp_from_start=e_ls, diff_onset=d, diff_from_start=d_ls,
                exp_eval_years=[y for y, _ in ev_e], diff_eval_years=[y for y, _ in ev_d])


def categorise(r: dict, include_from_start: bool = False) -> str:
    e, d = r["exp_onset"], r["diff_onset"]
    if not include_from_start:
        if r["exp_from_start"]:
            e = None
        if r["diff_from_start"]:
            d = None
    if e is not None and d is not None:
        return "expansion_first" if e < d else ("same_year" if e == d else "diffusion_first")
    if e is not None:
        return "expansion_only"
    if d is not None:
        return "diffusion_only"
    return "neither"


def run_all(ind: pd.DataFrame, ids: list[str], fa: dict, new_act: dict, gain=10, rise=0.2, variant="2consec",
            pct_col="pct_alt") -> pd.DataFrame:
    rows = []
    for c in ids:
        g = ind[ind.concept_id == c]
        r = onsets_for(g, fa.get(c, 9999), new_act.get(c, set()), gain, rise, variant, pct_col)
        r["concept_id"] = c
        r["category"] = categorise(r)
        r["category_incl_from_start"] = categorise(r, include_from_start=True)
        rows.append(r)
    return pd.DataFrame(rows)


def share_ef(df: pd.DataFrame, col: str = "category") -> tuple[float, int]:
    both = df[df[col].isin(["expansion_first", "same_year", "diffusion_first"])]
    return (float((both[col] == "expansion_first").mean()) if len(both) else np.nan, len(both))


def boot_share(df: pd.DataFrame, col: str = "category", B: int = 2000, seed: int = 0) -> list:
    both = (df[df[col].isin(["expansion_first", "same_year", "diffusion_first"])][col] == "expansion_first").astype(float).values
    return list(boot_mean_ci(both, B, seed))


@logger.catch(reraise=True)
def main() -> None:
    setup_logging("leadlag")
    load_sealed()
    ind = pd.read_parquet(RES / "indicators" / "concept_year_indicators_hyd.parquet")
    pool = pd.read_parquet(WORK / "pool_active.parquet")
    scr = pool[(pool.fold == "screen") & (pool.arm == "main")]
    CONF.assert_not_sealed(scr.concept_id)
    main_ids = sorted(scr.loc[scr.MAIN, "concept_id"])
    all_ids = sorted(scr.concept_id)
    cp = pd.read_parquet(WORK / "cp_hyd.parquet", columns=["concept_id", "year", "subfield"])
    cp = cp[cp.concept_id.isin(set(all_ids))]
    new_act = new_active_years(cp)
    fa = ind[ind.n_frame > 0].groupby("concept_id").year.min().to_dict()
    out: dict = {}
    res = run_all(ind, main_ids, fa, new_act)
    asg = pd.read_csv(TYP / "assignments.csv").set_index("concept_id") if (TYP / "assignments.csv").exists() else None
    res["cluster_name"] = res.concept_id.map(asg.cluster_name) if asg is not None else None
    res["origin_group"] = res.concept_id.map(pool.set_index("concept_id").origin_group)
    res["lag"] = [(d - e) if (cat in ("expansion_first", "same_year", "diffusion_first")) else np.nan
                  for d, e, cat in zip(res.diff_onset, res.exp_onset, res.category)]
    obs, n_both = share_ef(res)
    out["primary"] = dict(definition=dict(expansion="pct_alt +10 points in 2 consecutive years (y >= first_attach+1)",
                                          diffusion="H_rar(y)-H_rar(y-2) >= 0.2 nats AND a new active subfield in y"),
                          n_concepts=len(res), category_counts=res.category.value_counts().to_dict(),
                          category_counts_incl_from_start=res.category_incl_from_start.value_counts().to_dict(),
                          exp_from_start=int(res.exp_from_start.sum()), diff_from_start=int(res.diff_from_start.sum()),
                          n_both_onsets=n_both, share_expansion_first=obs, share_expansion_first_ci=boot_share(res)[1:],
                          share_same_year=float((res.category == "same_year").sum() / max(n_both, 1)),
                          share_diffusion_first=float((res.category == "diffusion_first").sum() / max(n_both, 1)),
                          share_incl_from_start=share_ef(res, "category_incl_from_start")[0],
                          share_incl_from_start_ci=boot_share(res, "category_incl_from_start")[1:],
                          n_both_incl_from_start=share_ef(res, "category_incl_from_start")[1],
                          lag_hist={str(int(k)): int(v) for k, v in res.lag.dropna().value_counts().sort_index().items()},
                          lag_median=float(res.lag.median()) if res.lag.notna().any() else None)
    # ---- year-shuffle null
    rng = np.random.default_rng(2026)
    null = []
    for _ in range(1000):
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
    out["null"] = dict(draws=1000, rule="each observed onset redrawn uniformly over that concept's evaluable (non-first) years",
                       observed=obs, null_mean=float(np.nanmean(null)), null_ci=np.nanpercentile(null, [2.5, 97.5]).tolist(),
                       p_one_sided_greater=float((np.sum(null >= obs) + 1) / (len(null) + 1)),
                       p_one_sided_less=float((np.sum(null <= obs) + 1) / (len(null) + 1)))
    # ---- grid
    grid = []
    for gval in (5, 10, 15, 20):
        for h in (0.1, 0.2, 0.3):
            rr = run_all(ind, main_ids, fa, new_act, gain=gval, rise=h)
            s, n = share_ef(rr)
            ci = boot_share(rr, B=1000)
            grid.append(dict(exp_gain=gval, diff_rise=h, n_both=n, share_expansion_first=s, ci_lo=ci[1], ci_hi=ci[2],
                             share_diffusion_first=float((rr.category == "diffusion_first").sum() / max(n, 1)),
                             share_same_year=float((rr.category == "same_year").sum() / max(n, 1))))
    pd.DataFrame(grid).to_csv(RES / "leadlag_grid.csv", index=False)
    # ---- secondary definitions
    sec = {}
    for name, kw in (("all_node_pct", dict(pct_col="pct")), ("cumulative_2yr", dict(variant="cum2")),
                     ("F7_widened_cum2_rise0.1", dict(variant="cum2", rise=0.1))):
        rr = run_all(ind, main_ids, fa, new_act, **kw)
        s, n = share_ef(rr)
        sec[name] = dict(n_both=n, share_expansion_first=s, ci=boot_share(rr, B=1000)[1:],
                         counts=rr.category.value_counts().to_dict())
    rr = run_all(ind, all_ids, fa, new_act)
    s, n = share_ef(rr)
    sec["all_screen_mainarm"] = dict(n_concepts=len(rr), n_both=n, share_expansion_first=s, ci=boot_share(rr, B=1000)[1:])
    # onsets <= 2015 only (sealed focal years 2016-18 are never E-labelled; descriptive onset use disclosed)
    early = res[(res.exp_onset.fillna(0) <= 2015) & (res.diff_onset.fillna(0) <= 2015)]
    s, n = share_ef(early)
    on = pd.concat([res.exp_onset, res.diff_onset]).dropna()
    sec["onsets_le_2015"] = dict(n_both=n, share_expansion_first=s, ci=boot_share(early, B=1000)[1:],
                                 share_onsets_in_2016_2018=float(on.between(2016, 2018).mean()) if len(on) else None)
    out["secondary"] = sec
    out["F7_underpowered"] = bool(n_both < 30)
    # ---- by cluster / origin group
    for by in ("cluster_name", "origin_group"):
        if res[by].notna().any():
            out[f"by_{by}"] = {str(k): dict(n=len(g), n_both=share_ef(g)[1], share_expansion_first=share_ef(g)[0],
                                             ci=boot_share(g, B=1000)[1:], counts=g.category.value_counts().to_dict())
                               for k, g in res.groupby(by)}
    # ---- continuous Granger-style panel (concept FE, clustered SE)
    import statsmodels.formula.api as smf
    p = ind[ind.concept_id.isin(main_ids)].sort_values(["concept_id", "year"]).copy()
    p["H_rar_f"] = p.H_rar
    p["dH"] = p.groupby("concept_id").H_rar_f.diff()
    p["dP"] = p.groupby("concept_id").pct_alt.diff()
    for k in (1, 2):
        p[f"dP_l{k}"] = p.groupby("concept_id").dP.shift(k)
        p[f"dH_l{k}"] = p.groupby("concept_id").dH.shift(k)
    gr = {}
    for yv, xs in (("dH", ["dP_l1", "dP_l2", "dH_l1", "dH_l2"]), ("dP", ["dH_l1", "dH_l2", "dP_l1", "dP_l2"])):
        q = p.dropna(subset=[yv] + xs)
        f = smf.ols(f"{yv} ~ {' + '.join(xs)} + C(concept_id)", q).fit(cov_type="cluster", cov_kwds={"groups": pd.factorize(q.concept_id)[0]})
        gr[f"{yv}_on_lags"] = dict(n=len(q), n_concepts=int(q.concept_id.nunique()),
                                   coefs={x: dict(b=float(f.params[x]), se=float(f.bse[x]), p=float(f.pvalues[x])) for x in xs})
    out["granger_panel"] = gr
    res.drop(columns=["exp_eval_years", "diff_eval_years"]).to_csv(RES / "leadlag_by_concept.csv", index=False)
    write_json(RES / "leadlag.json", out)
    logger.info(f"leadlag: n_both={n_both} share expansion first={obs:.3f} null={out['null']['null_mean']:.3f} "
                f"counts={out['primary']['category_counts']}")


if __name__ == "__main__":
    main()
