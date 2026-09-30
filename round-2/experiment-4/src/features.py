"""STEP 3 (cross-year part): assemble the frozen concept-year indicator table from the snapshots.

Every indicator at (c, y) uses only snapshots <= y and volume counts <= y."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from loguru import logger
from scipy.special import gammaln

import load
import rq1_spec as S

SNAP = load.RESULTS / "snapshots"


# ------------------------------------------------------------------ Kleinberg (batched, 2-state)
def _binom_nll(r: np.ndarray, d: np.ndarray, p: float) -> np.ndarray:
    p = min(max(p, 1e-15), 1 - 1e-12)
    return -(gammaln(d + 1) - gammaln(r + 1) - gammaln(d - r + 1) + r * np.log(p) + (d - r) * np.log1p(-p))


def kleinberg_batched(r: np.ndarray, d: np.ndarray, s: float = 2.0, gamma: float = 1.0) -> tuple[np.ndarray, np.ndarray]:
    """Kleinberg (2002) batched two-state automaton. Returns (states, burst_weight per position).
    burst_weight = sum over the burst interval containing t of (cost_state0 - cost_state1), 0 outside bursts."""
    r = np.asarray(r, dtype=float)
    d = np.asarray(d, dtype=float)
    n = len(r)
    if n == 0 or r.sum() <= 0:
        return np.zeros(n, dtype=int), np.zeros(n)
    p0 = r.sum() / d.sum()
    p1 = min(s * p0, 0.9999)
    c0, c1 = _binom_nll(r, d, p0), _binom_nll(r, d, p1)
    up = gamma * np.log(n)
    # Viterbi, start in state 0
    cost = np.array([c0[0], c1[0] + up])
    back = np.zeros((n, 2), dtype=int)
    for t in range(1, n):
        n0 = np.array([cost[0], cost[1]])  # to state 0 (down move is free)
        n1 = np.array([cost[0] + up, cost[1]])
        back[t, 0], back[t, 1] = int(np.argmin(n0)), int(np.argmin(n1))
        cost = np.array([n0.min() + c0[t], n1.min() + c1[t]])
    st = np.zeros(n, dtype=int)
    st[-1] = int(np.argmin(cost))
    for t in range(n - 1, 0, -1):
        st[t - 1] = back[t, st[t]]
    w = np.zeros(n)
    t = 0
    while t < n:
        if st[t] == 1:
            u = t
            while u < n and st[u] == 1:
                u += 1
            w[t:u] = (c0[t:u] - c1[t:u]).sum()
            t = u
        else:
            t += 1
    return st, w


def burst_features(vol: np.ndarray, years: list[int], denom: dict[int, float]) -> tuple[np.ndarray, np.ndarray]:
    """burst_active_t and burst_weight_t using ONLY years <= t (Viterbi rerun for every t)."""
    d = np.array([denom[y] for y in years])
    act, wt = np.zeros(len(years)), np.zeros(len(years))
    for i in range(len(years)):
        st, w = kleinberg_batched(vol[: i + 1], d[: i + 1], S.KLEINBERG["s"], S.KLEINBERG["gamma"])
        act[i], wt[i] = st[-1], w[-1]
    return act, wt


# ------------------------------------------------------------------ community id matching
def match_communities(years: list[int]) -> pd.DataFrame:
    """Give communities persistent ids: a community at y inherits the id of the y-1 community with maximal
    Jaccard >= 0.3 (one-to-one, best pairs first); otherwise it gets a new id."""
    out = []
    prev = None
    next_id = 0
    for y in years:
        nd = pd.read_parquet(SNAP / f"nodes_{y}.parquet", columns=["tag", "comm_local"])
        sizes = nd.comm_local.value_counts()
        gid = {}
        if prev is not None:
            m = nd.merge(prev, on="tag", suffixes=("", "_prev"))
            inter = m.groupby(["comm_local", "gid_prev"]).size().rename("inter").reset_index()
            psz = prev.gid_prev.value_counts()
            inter["jac"] = inter.inter / (inter.comm_local.map(sizes) + inter.gid_prev.map(psz) - inter.inter)
            inter = inter[inter.jac >= S.COMMUNITY_MATCH_JACCARD].sort_values("jac", ascending=False)
            used = set()
            for r in inter.itertuples():
                if r.comm_local in gid or r.gid_prev in used:
                    continue
                gid[r.comm_local] = int(r.gid_prev)
                used.add(r.gid_prev)
        for c in sorted(sizes.index):
            if c not in gid:
                gid[c] = next_id
                next_id += 1
            else:
                next_id = max(next_id, gid[c] + 1)
        nd["gid"] = nd.comm_local.map(gid)
        nd["year"] = y
        out.append(nd[["year", "tag", "comm_local", "gid"]])
        prev = nd[["tag", "gid"]].rename(columns={"gid": "gid_prev"})
    return pd.concat(out, ignore_index=True)


def entropy(counts: np.ndarray) -> float:
    c = counts[counts > 0].astype(float)
    if c.sum() <= 0:
        return np.nan
    p = c / c.sum()
    return float(-(p * np.log(p)).sum())


# ------------------------------------------------------------------ main assembly
def build_features(concept_ids: list[str], years: list[int]) -> pd.DataFrame:
    concepts = pd.read_parquet(load.INTER / "concepts.parquet")
    concepts = concepts[concepts.concept_id.isin(concept_ids)].reset_index(drop=True)
    denom = load.load_denominators()

    # first snapshot in which each bg tag appears
    first_snap: dict[int, int] = {}
    for y in years:
        for t in pd.read_parquet(SNAP / f"nodes_{y}.parquet", columns=["tag"]).tag:
            first_snap.setdefault(int(t), y)

    comms = match_communities(years)
    comms.to_parquet(load.RESULTS / "communities_y.parquet")

    focal = []
    for y in years:
        f = pd.read_parquet(SNAP / f"focal_{y}.parquet")
        if len(f):
            nd = comms[comms.year == y].set_index("comm_local").gid.drop_duplicates()
            f["module_gid"] = [int(nd.get(m, -1)) if m >= 0 else -1 for m in f.module_local]
            focal.append(f)
    focal = pd.concat(focal, ignore_index=True)

    mw = pd.read_parquet(load.INTER / "mesh_works.parquet")
    mw = mw[mw.primary].drop_duplicates(["concept_id", "work_id"])

    rows = []
    for c in concepts.itertuples(index=False):
        cd = c._asdict()
        fc = focal[focal.concept_id == c.concept_id].set_index("year")
        vols = {k: np.array([cd[f"{k}_{y}"] for y in years]) for k in ("tm", "s1", "mi")}
        bursts = {k: burst_features(v, years, denom) for k, v in vols.items()}
        cw = mw[mw.concept_id == c.concept_id]
        nbr_hist: dict[int, set] = {}
        prev = None
        for i, y in enumerate(years):
            r = {"concept_id": c.concept_id, "year": y, "F": c.F, "age": y - c.F}
            for k, v in vols.items():
                r[f"V_{k}"] = float(v[i])
                r[f"logV_{k}"] = float(np.log1p(v[i]))
                r[f"dlogV2_{k}"] = float(np.log1p(v[i]) - np.log1p(v[i - 2])) if i >= 2 else np.nan
                r[f"burst_active_{k}"] = float(bursts[k][0][i])
                r[f"burst_weight_{k}"] = float(bursts[k][1][i])
            # entropy-growth family (flagged BIASED: 178/191 concepts have PubMed-only works)
            win = cw[(cw.year >= y - S.WINDOW + 1) & (cw.year <= y)]
            r["subfield_entropy"] = entropy(win.subfield_id.value_counts().to_numpy()) if len(win) else np.nan
            r["n_subfields"] = int(win.subfield_id.nunique()) if len(win) else 0
            present = y in fc.index
            if present:
                q = fc.loc[y]
                N = set(q.neighbours)
                for col in ("W_c", "k", "s", "wdeg_pctl", "closure_obs", "closure_exp", "closure_lr", "P",
                            "z_within", "P_seed_sd", "z_seed_sd", "betw", "betw_top_decile", "rewire_z",
                            "n_modules_touched", "module_gid"):
                    r[col] = q[col] if col in q.index else np.nan
            else:
                N = set()
                r.update({"W_c": 0, "k": 0, "s": 0.0})
            nbr_hist[y] = N
            # temporal indicators (need snapshots y-1..y-5 only)
            Nprev = nbr_hist.get(y - 1, set())
            union5 = set().union(*[nbr_hist.get(y - l, set()) for l in range(1, 6)])
            k = len(N)
            r["new_rel_count"] = len(N - union5)
            r["new_rel_rate"] = (len(N - union5) / k) if k else np.nan
            r["nbr_novelty"] = (np.mean([first_snap.get(j, y) >= y - S.WINDOW + 1 for j in N]) if k else np.nan)
            a, b, cc = len(N & Nprev), len(N - Nprev), len(Nprev - N)
            den = 2 * a + b + cc
            bsor = (b + cc) / den if den else 0.0
            bsim = min(b, cc) / (a + min(b, cc)) if (a + min(b, cc)) else 0.0
            bsne = bsor - bsim
            r.update({"baselga_a": a, "baselga_b": b, "baselga_c": cc, "beta_sor": bsor, "beta_sim": bsim,
                      "beta_sne": bsne,
                      "accretion_share": float(np.sign(b - cc) * bsne / bsor) if bsor > 0 else 0.0})
            if k == 0 and len(Nprev) == 0:
                for kk in ("beta_sor", "beta_sim", "beta_sne", "accretion_share"):
                    r[kk] = np.nan  # no network in either year
            sp_ = prev["s"] if prev is not None else 0.0
            r["growth"] = float(np.log((r["s"] + 1) / (sp_ + 1)))
            r["dk"] = k - (prev["k"] if prev is not None else 0)
            r["dlogk"] = float(np.log1p(k) - np.log1p(prev["k"] if prev is not None else 0))
            for base in ("P", "z_within", "betw", "wdeg_pctl", "closure_lr"):
                cur = r.get(base, np.nan)
                pv = prev.get(base, np.nan) if prev is not None else np.nan
                r[f"d{base}"] = float(cur - pv) if (pd.notna(cur) and pd.notna(pv)) else np.nan
            r["dz"] = r.pop("dz_within")
            r["dpctl"] = r.pop("dwdeg_pctl")
            r["dbetw"] = r["dbetw"]
            pm = prev.get("module_gid", np.nan) if prev is not None else np.nan
            cm = r.get("module_gid", np.nan)
            r["comm_change"] = float(cm != pm) if (pd.notna(cm) and pd.notna(pm) and cm >= 0 and pm >= 0) else np.nan
            # per-paper versions of extensive indicators
            W = r["W_c"]
            r["s_pp"] = r["s"] / W if W else np.nan
            r["k_pp"] = k / W if W else np.nan
            r["new_rel_pp"] = r["new_rel_count"] / W if W else np.nan
            r["growth_num_pp"] = (r["s"] - sp_) / W if W else np.nan
            rows.append(r)
            prev = r
    df = pd.DataFrame(rows)
    # entropy change over 3 years
    df = df.sort_values(["concept_id", "year"]).reset_index(drop=True)
    df["d3_subfield_entropy"] = df.groupby("concept_id").subfield_entropy.diff(3)
    df["dP2"] = df.groupby("concept_id").P.diff(2)
    df["d2_accretion_share"] = df.groupby("concept_id").accretion_share.diff(2)
    df["d2_closure_lr"] = df.groupby("concept_id").closure_lr.diff(2)
    df["d2_dP"] = df.groupby("concept_id").dP.diff(2)
    # percentile of weighted degree among the non-isolated focal MeSH nodes of each snapshot (declared E_cent ref)
    df["wdeg_pctl_focal"] = np.nan
    for y, g in df[df.s > 0].groupby("year"):
        v = np.sort(g.s.to_numpy())
        lt = np.searchsorted(v, g.s.to_numpy(), side="left")
        le = np.searchsorted(v, g.s.to_numpy(), side="right")
        df.loc[g.index, "wdeg_pctl_focal"] = 100.0 * (lt + 0.5 * (le - lt)) / len(v)
    df["dpctl_focal"] = df.groupby("concept_id").wdeg_pctl_focal.diff(1)
    df["logW_c"] = np.log1p(df.W_c)
    df["log_s"] = np.log1p(df.s)
    # volume-residualised intensive indicators (declared; fitted outcome-blind on all focal concept-years)
    volres_meta = {}
    for col in INTENSIVE:
        m = df[col].notna() & (df.W_c > 0)
        if m.sum() < 10:
            df[f"{col}_volres"] = np.nan
            continue
        X = np.c_[np.ones(m.sum()), df.loc[m, "logW_c"]]
        beta, *_ = np.linalg.lstsq(X, df.loc[m, col].to_numpy(dtype=float), rcond=None)
        df[f"{col}_volres"] = np.where(m, df[col] - (beta[0] + beta[1] * df.logW_c), np.nan)
        volres_meta[col] = {"intercept": float(beta[0]), "slope_logW": float(beta[1]), "n": int(m.sum())}
    (load.RESULTS / "volres_fit.json").write_text(json.dumps(volres_meta, indent=1))
    import mainpool_align
    df, mp_meta = mainpool_align.add_mainpool_columns(df, concepts, years)
    df["closure_raw"] = np.log1p(df.closure_mp_obs)
    (load.RESULTS / "mainpool_align_fit.json").write_text(json.dumps(mp_meta, indent=1))
    logger.info(f"features: {len(df)} concept-years, {df.concept_id.nunique()} concepts, "
                f"{int((df.k > 0).sum())} with a network")
    return df


INTENSIVE = ["accretion_share", "closure_lr", "P", "z_within", "nbr_novelty", "new_rel_rate", "dP", "beta_sim",
             "beta_sne", "beta_sor", "rewire_z"]
EXTENSIVE_PP = {"s": "s_pp", "k": "k_pp", "new_rel_count": "new_rel_pp", "growth": "growth_num_pp"}
INDICATORS = ["s", "k", "wdeg_pctl", "wdeg_pctl_focal", "dpctl_focal", "growth", "new_rel_count", "new_rel_rate", "nbr_novelty", "beta_sor",
              "beta_sim", "beta_sne", "accretion_share", "closure_lr", "rewire_z", "P", "z_within", "betw",
              "dP", "dz", "dbetw", "dpctl", "dk", "comm_change", "n_modules_touched"]


def indicator_columns() -> dict:
    cols = {}
    for ind in INDICATORS:
        cols[ind] = {"raw": ind}
        if ind in EXTENSIVE_PP:
            cols[ind]["pp"] = EXTENSIVE_PP[ind]
        if ind in INTENSIVE:
            cols[ind]["volres"] = f"{ind}_volres"
    return cols
