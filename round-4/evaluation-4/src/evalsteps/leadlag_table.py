"""STEP 4: lead-lag denominator table (screen, held-out, pooled main, MeSH), censoring (KM, log-rank, F<=2012 cohort)."""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
from loguru import logger

from base import E8, HO, RES, share, write_json

CATS = ["neither", "diffusion_only", "expansion_only", "expansion_first", "same_year", "diffusion_first"]
BOTH = ["expansion_first", "same_year", "diffusion_first"]


def boot_ef(df: pd.DataFrame, B: int = 2000, seed: int = 0) -> list:
    x = (df[df.category.isin(BOTH)].category == "expansion_first").astype(float).values
    if len(x) == 0:
        return [None, None]
    rng = np.random.default_rng(seed)
    m = [x[rng.integers(0, len(x), len(x))].mean() for _ in range(B)]
    return np.percentile(m, [2.5, 97.5]).tolist()


def table(df: pd.DataFrame) -> dict:
    n = len(df)
    cnt = {c: int((df.category == c).sum()) for c in CATS}
    nb = sum(cnt[c] for c in BOTH)
    ef = cnt["expansion_first"]
    return dict(n=n, counts=cnt, shares={c: cnt[c] / n if n else None for c in CATS},
                exp_from_start=int(df.exp_from_start.astype(bool).sum()), diff_from_start=int(df.diff_from_start.astype(bool).sum()),
                counts_incl_from_start={c: int((df.category_incl_from_start == c).sum()) for c in CATS},
                n_both=nb, n_expansion_first=ef, share_expansion_first=(ef / nb) if nb else None, boot_ci=boot_ef(df),
                wilson=share(ef, nb)["wilson_ci"] if nb else [None, None],
                sentence=f"Among the {nb} of {n} concepts with both onsets observable, expansion came first in {ef}")


def km(times: np.ndarray, events: np.ndarray) -> dict:
    from lifelines import KaplanMeierFitter
    k = KaplanMeierFitter().fit(times, events)
    sf = k.survival_function_.iloc[:, 0]
    return dict(timeline=[float(t) for t in sf.index], survival=[float(v) for v in sf.values],
                median=float(k.median_survival_time_) if np.isfinite(k.median_survival_time_) else None,
                n=int(len(times)), n_events=int(events.sum()))


def censoring(df: pd.DataFrame, F: pd.Series) -> dict:
    from lifelines.statistics import logrank_test
    d = df.copy()
    d["F"] = d.concept_id.map(F)
    d = d[d.F.notna()]
    end = 2024 - 1
    out = {}
    tt = {}
    for kind, on, fs in (("expansion", "exp_onset", "exp_from_start"), ("diffusion", "diff_onset", "diff_from_start")):
        ev = d[on].notna().to_numpy()
        t = np.where(ev, np.where(d[fs].astype(bool), 0.0, d[on].fillna(0) - d.F), end - d.F).astype(float)
        t = np.clip(t, 0, None)
        tt[kind] = (t, ev.astype(int))
        out[f"km_{kind}"] = km(t, ev.astype(int))
        out[f"onset_year_hist_{kind}"] = {str(int(k)): int(v) for k, v in d[on].dropna().value_counts().sort_index().items()}
    lr = logrank_test(tt["expansion"][0], tt["diffusion"][0], tt["expansion"][1], tt["diffusion"][1])
    out["logrank_expansion_vs_diffusion"] = dict(stat=float(lr.test_statistic), p=float(lr.p_value))
    rc = d[d.F <= 2012]
    out["restricted_cohort_F_le_2012"] = table(rc)
    return out


def evaluability(ind: pd.DataFrame) -> dict:
    x = ind[ind.year >= ind.F]
    ev = x.groupby("concept_id").H_rar.apply(lambda s: s.notna().any())
    return dict(rule="H_rar needs vol3 >= 10 papers with known subfield in the 3-year window (rarefaction depth m = 10)",
                n_concepts=int(len(ev)), n_never_H_rar_evaluable=int((~ev).sum()))


def run() -> dict:
    out = {}
    ind_s = pd.read_parquet(E8 / "results/indicators/concept_year_indicators_hyd.parquet", columns=["concept_id", "year", "F", "H_rar", "MAIN", "fold"])
    Fs = ind_s.groupby("concept_id").F.first()
    s = pd.read_csv(E8 / "results/leadlag_by_concept.csv")
    ll_s = json.loads((E8 / "results/leadlag.json").read_text())
    pops = {"screen": (s, ll_s, Fs, ind_s[ind_s.concept_id.isin(s.concept_id)], pd.read_csv(E8 / "results/leadlag_grid.csv"))}
    if (HO / "results/leadlag_by_concept.csv").exists():
        h = pd.read_csv(HO / "results/leadlag_by_concept.csv")
        ll_h = json.loads((HO / "results/leadlag.json").read_text())
        ind_h = pd.read_parquet(HO / "results/indicators/concept_year_indicators_hyd.parquet", columns=["concept_id", "year", "F", "H_rar"])
        Fh = ind_h.groupby("concept_id").F.first()
        pops["heldout"] = (h, ll_h, Fh, ind_h[ind_h.concept_id.isin(h.concept_id)], pd.read_csv(HO / "results/leadlag_grid.csv"))
        pm = pd.concat([s, h], ignore_index=True)
        pops["pooled_main"] = (pm, None, Fs.combine_first(Fh), pd.concat([pops["screen"][3], pops["heldout"][3]]), None)
    mr = RES / "mesh/mesh_leadlag_by_concept.csv"
    if mr.exists():
        m = pd.read_csv(mr)
        mres = json.loads((RES / "mesh_results.json").read_text())["leadlag"] if (RES / "mesh_results.json").exists() else None
        ind_m = pd.read_parquet(RES / "mesh/mesh_indicators.parquet", columns=["concept_id", "year", "F", "H_rar"])
        pops["mesh"] = (m, mres, ind_m.groupby("concept_id").F.first(), ind_m, pd.read_csv(RES / "mesh/mesh_leadlag_grid.csv"))
    rows = []
    for name, (df, ll, F, ind, grid) in pops.items():
        t = table(df)
        t["evaluability"] = evaluability(ind)
        t["censoring"] = censoring(df, F)
        if ll is not None:
            t["null"] = ll.get("null")
            t["granger_panel"] = ll.get("granger_panel")
            t["secondary"] = ll.get("secondary")
        if grid is not None:
            t["grid"] = grid.to_dict("records")
        out[name] = t
        rows.append(dict(population=name, n=t["n"], **{f"n_{c}": t["counts"][c] for c in CATS}, n_both=t["n_both"],
                         share_ef=t["share_expansion_first"], ci_lo=t["boot_ci"][0], ci_hi=t["boot_ci"][1],
                         exp_from_start=t["exp_from_start"], diff_from_start=t["diff_from_start"],
                         restricted_n_both=t["censoring"]["restricted_cohort_F_le_2012"]["n_both"],
                         restricted_share_ef=t["censoring"]["restricted_cohort_F_le_2012"]["share_expansion_first"],
                         logrank_p=t["censoring"]["logrank_expansion_vs_diffusion"]["p"],
                         never_H_rar_evaluable=t["evaluability"]["n_never_H_rar_evaluable"]))
        logger.info(f"lead-lag {name}: {t['sentence']}")
    pd.DataFrame(rows).to_csv(RES / "leadlag_denominator_table.csv", index=False)
    write_json(RES / "leadlag_table.json", out)
    return out
