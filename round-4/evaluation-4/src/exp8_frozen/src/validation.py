#!/usr/bin/env python3
"""STAGE 6b: validate the typology on quantities the clustering never saw (reference age t* = F+3).

V1 newcomer share: share of W2 = [F+4, F+8] c-papers (with >= 1 author id) whose authors ALL had no c-paper of the concept in
   W1 = [F-2, F+3] and never co-authored (within the hydrated c-paper corpus, papers published <= F+3) with any W1 author.
   Also newcomer papers per 10^4 all-science papers of W2. Author ids are within-corpus -> shares are upper bounds.
V2 pool-percentile gain: pct_alt(F+8) - pct_alt(F+3).
V3 communities touched: distinct persistent communities holding >= 10% of the concept's all-type tag weight in any year
   F..2024 (seed 0); robust version = median over the 5 new Leiden seeds.
Tests: Kruskal-Wallis + epsilon^2 (H/(n-1)) with a 2,000-draw concept bootstrap CI per grouping (3-channel, B1 entropy-only,
B2 volume terciles, B2 volume-series k-medoids); paired bootstrap of delta epsilon^2; all repeated after residualising each V
on log1p(c-papers F-2..F+3) and F (age at t* is constant = 3, so calendar F stands in for the age term).
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
from loguru import logger
from scipy.stats import kruskal

from common import NEW_SEEDS, RES, TYP, WORK, YEARS, X3, C, load_sealed, setup_logging, write_json

LS = WORK / "leiden_seeds"


def newcomer_shares(pool: pd.DataFrame, ids: list[str], totals: dict) -> pd.DataFrame:
    cp = pd.read_parquet(WORK / "cp_hyd.parquet", columns=["concept_id", "work_id", "year", "authors"])
    works = cp.drop_duplicates("work_id")[["work_id", "year", "authors"]]
    ex = works.explode("authors").dropna(subset=["authors"])
    ex["authors"] = ex.authors.astype(np.int64)
    auth_of = dict(zip(works.work_id, works.authors))
    Fm = pool.set_index("concept_id").F
    rows = []
    for c in ids:
        F = int(Fm[c])
        mine = cp[cp.concept_id == c]
        w1 = mine[(mine.year >= F - 2) & (mine.year <= F + 3)]
        w2 = mine[(mine.year >= F + 4) & (mine.year <= F + 8)]
        A1 = set(np.concatenate([np.asarray(a, dtype=np.int64) for a in w1.authors.values]).tolist()) if len(w1) else set()
        hit = ex[(ex.year <= F + 3) & ex.authors.isin(A1)].work_id.unique() if A1 else []
        N1 = set()
        for w in hit:
            N1.update(np.asarray(auth_of[w], dtype=np.int64).tolist())
        known = A1 | N1
        w2a = [np.asarray(a, dtype=np.int64) for a in w2.authors.values if a is not None and len(a)]
        n_new = sum(1 for a in w2a if not (set(a.tolist()) & known))
        denom = sum(totals[str(y)]["all_science"] for y in range(F + 4, F + 9))
        rows.append(dict(concept_id=c, n_W1=len(w1), n_W1_authors=len(A1), n_known_authors=len(known), n_W2=len(w2),
                         n_W2_with_authors=len(w2a), n_newcomer=n_new,
                         V1_newcomer_share=n_new / len(w2a) if w2a else np.nan,
                         V1_newcomer_per_1e4=1e4 * n_new / denom if denom else np.nan,
                         vol_W1=len(w1)))
    return pd.DataFrame(rows)


def comm_touched(ind: pd.DataFrame, ids: list[str]) -> pd.DataFrame:
    Fm = ind.groupby("concept_id").F.first()
    per0 = pd.read_parquet(X3 / "work" / "communities" / "persistent_ids.parquet")
    pid0 = {(int(y), int(c)): int(p) for y, c, p in zip(per0.year, per0.comm, per0.pid)}
    out = {c: dict(concept_id=c) for c in ids}
    sub = ind[ind.concept_id.isin(set(ids))]
    for c, g in sub.groupby("concept_id"):
        pids = set()
        for y, js in zip(g.year, g.cw_all_json):
            if y < Fm[c] or not isinstance(js, str):
                continue
            cw = {int(k): v for k, v in json.loads(js).items()}
            tot = sum(cw.values())
            for k, v in cw.items():
                if tot > 0 and v >= 0.10 * tot and (int(y), k) in pid0:
                    pids.add(pid0[(int(y), k)])
        out[c]["V3_comm_touched"] = len(pids)
    cm = pd.concat([pd.read_parquet(LS / f"cm_y{y}.parquet", columns=["concept_id", "year", "seed", "cw_all_json"]) for y in YEARS])
    cm = cm[cm.concept_id.isin(set(ids)) & cm.seed.isin(NEW_SEEDS)]
    for s, gs in cm.groupby("seed"):
        per = pd.read_parquet(LS / f"persistent_s{s}.parquet")
        pm = {(int(y), int(c)): int(p) for y, c, p in zip(per.year, per.comm, per.pid)}
        for c, g in gs.groupby("concept_id"):
            pids = set()
            for y, js in zip(g.year, g.cw_all_json):
                if y < Fm[c]:
                    continue
                cw = {int(k): v for k, v in json.loads(js).items()}
                tot = sum(cw.values())
                for k, v in cw.items():
                    if tot > 0 and v >= 0.10 * tot and (int(y), k) in pm:
                        pids.add(pm[(int(y), k)])
            out[c][f"V3_s{s}"] = len(pids)
    df = pd.DataFrame(list(out.values()))
    df["V3_comm_touched_robust"] = df[[f"V3_s{s}" for s in NEW_SEEDS]].median(axis=1)
    return df


def eps2(v: np.ndarray, g: np.ndarray) -> tuple[float, float]:
    groups = [v[g == k] for k in np.unique(g)]
    groups = [x for x in groups if len(x) > 0]
    if len(groups) < 2 or len(v) < 3 or np.ptp(v) == 0:
        return np.nan, np.nan
    H, p = kruskal(*groups)
    return float(H / (len(v) - 1)), float(p)


def residualise(df: pd.DataFrame, col: str) -> np.ndarray:
    ok = df[col].notna()
    X = np.column_stack([np.ones(ok.sum()), np.log1p(df.loc[ok, "vol_W1"]), df.loc[ok, "F"]])
    beta, *_ = np.linalg.lstsq(X, df.loc[ok, col].values, rcond=None)
    out = np.full(len(df), np.nan)
    out[ok.values] = df.loc[ok, col].values - X @ beta
    return out


@logger.catch(reraise=True)
def main() -> None:
    setup_logging("validation")
    load_sealed()
    ind = pd.read_parquet(RES / "indicators" / "concept_year_indicators_hyd.parquet")
    pool = pd.read_parquet(WORK / "pool_active.parquet")
    asg = pd.read_csv(TYP / "assignments.csv")
    ids = asg.concept_id.tolist()
    C.assert_not_sealed(ids)
    totals = json.loads((WORK / "totals.json").read_text())
    v1 = newcomer_shares(pool, ids, totals)
    Fm = pool.set_index("concept_id").F
    pa = ind.set_index(["concept_id", "year"]).pct_alt
    v2 = pd.DataFrame(dict(concept_id=ids, V2_pct_alt_gain=[pa.get((c, int(Fm[c]) + 8), np.nan) - pa.get((c, int(Fm[c]) + 3), np.nan)
                                                            for c in ids]))
    v3 = comm_touched(ind, ids)
    V = asg.merge(v1, on="concept_id").merge(v2, on="concept_id").merge(v3, on="concept_id")
    V["F"] = V.concept_id.map(Fm).astype(float)
    vcols = ["V1_newcomer_share", "V1_newcomer_per_1e4", "V2_pct_alt_gain", "V3_comm_touched", "V3_comm_touched_robust"]
    for col in vcols:
        V[f"{col}_res"] = residualise(V, col)
    V.to_csv(RES / "validation_by_concept.csv", index=False)
    groupings = {k: v for k, v in {"3ch": "cluster", "B1_entropy": "cluster_B1", "B2_vol_tercile": "B2_vol_tercile",
                                   "B2_volseries": "cluster_B2_volseries"}.items() if v in V.columns}
    if "cluster_k3" in V:
        groupings["3ch_k3_exploratory"] = "cluster_k3"
    rng = np.random.default_rng(11)
    out: dict = dict(n=len(V), t_star="F+3", W1="[F-2, F+3]", W2="[F+4, F+8]", groupings=groupings, results={})
    B = 2000
    comp = V.dropna(subset=list(groupings.values()))
    idx_boot = [rng.integers(0, len(comp), len(comp)) for _ in range(B)]
    for col in vcols + [f"{c}_res" for c in vcols]:
        res = {}
        d = comp.dropna(subset=[col])
        boots = {}
        for gname, gcol in groupings.items():
            e, p = eps2(d[col].values, d[gcol].astype(str).values)
            meds = d.groupby(gcol)[col].median().to_dict()
            bs = []
            vals, labs = comp[col].values, comp[gcol].astype(str).values
            for ib in idx_boot:
                vv, ll = vals[ib], labs[ib]
                ok = np.isfinite(vv)
                bs.append(eps2(vv[ok], ll[ok])[0])
            boots[gname] = np.array(bs)
            res[gname] = dict(n=len(d), eps2=e, kw_p=p, eps2_ci=np.nanpercentile(bs, [2.5, 97.5]).tolist(),
                              medians={str(k): float(v) for k, v in meds.items()},
                              median_rank_order=[str(k) for k in sorted(meds, key=meds.get)])
        for base in [b for b in ("B1_entropy", "B2_vol_tercile", "B2_volseries") if b in groupings]:
            diff = boots["3ch"] - boots[base]
            e3 = res["3ch"]["eps2"]
            eb = res[base]["eps2"]
            res[f"delta_3ch_minus_{base}"] = dict(delta=(e3 - eb) if np.isfinite(e3) and np.isfinite(eb) else np.nan,
                                                   ci=np.nanpercentile(diff, [2.5, 97.5]).tolist())
        # medians by named 3-channel cluster (for the paper)
        res["by_cluster_name"] = {str(k): dict(n=len(g), median=float(g[col].median()), q25=float(g[col].quantile(0.25)),
                                               q75=float(g[col].quantile(0.75))) for k, g in d.groupby("cluster_name")}
        out["results"][col] = res
    # permutation calibration: KW p under permuted cluster labels should be ~uniform
    perm_p = []
    d = comp.dropna(subset=["V2_pct_alt_gain"])
    for _ in range(200):
        perm_p.append(eps2(d.V2_pct_alt_gain.values, rng.permutation(d.cluster.astype(str).values))[1])
    perm_p = np.array(perm_p)
    out["permutation_calibration_V2"] = dict(n=200, share_p_lt_0_05=float(np.mean(perm_p < 0.05)),
                                             mean_p=float(np.mean(perm_p)), ks_uniform_p=float(__import__("scipy.stats").stats.kstest(perm_p, "uniform").pvalue))
    out["newcomer_note"] = "author ids are within the hydrated c-paper corpus; newcomer shares are upper bounds"
    write_json(RES / "validation.json", out)
    logger.info("validation: " + "; ".join(f"{c}: " + " ".join(f"{g}={out['results'][c][g]['eps2']} (p={out['results'][c][g]['kw_p']})"
                                                               for g in groupings) for c in vcols))


if __name__ == "__main__":
    main()
