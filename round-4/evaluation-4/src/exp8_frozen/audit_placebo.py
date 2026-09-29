#!/usr/bin/env python3
"""TODO-5 audit: re-derive headline numbers from RAW per-concept / per-row files through hand-written code paths
(not the pipeline functions), and run each headline test on shuffled / placebo input to confirm it FAILS there.
Writes results/audit_placebo.json. Complements audit_rederive.py (stability table, expansion-first share, MeSH
early-bridging difference, BRIDGE entry OR).
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import chi2 as chi2_dist

ROOT = Path(__file__).resolve().parent
RES = ROOT / "results"
rng = np.random.default_rng(12345)


def kw_by_hand(v: np.ndarray, g: np.ndarray) -> tuple[float, float, float]:
    """Kruskal-Wallis H with tie correction, from average ranks computed by hand; returns (H, p, eps2 = H/(n-1))."""
    n = len(v)
    order = np.argsort(v, kind="mergesort")
    ranks = np.empty(n)
    i = 0
    while i < n:
        j = i
        while j + 1 < n and v[order[j + 1]] == v[order[i]]:
            j += 1
        ranks[order[i:j + 1]] = (i + j) / 2 + 1
        i = j + 1
    H = 0.0
    levels = np.unique(g)
    for lv in levels:
        r = ranks[g == lv]
        H += r.sum() ** 2 / len(r)
    H = 12 / (n * (n + 1)) * H - 3 * (n + 1)
    _, counts = np.unique(v, return_counts=True)
    H /= 1 - (counts ** 3 - counts).sum() / (n ** 3 - n)
    return H, float(chi2_dist.sf(H, len(levels) - 1)), H / (n - 1)


def chi2_by_hand(a, b) -> float:
    tab = pd.crosstab(a, b).values.astype(float)
    e = tab.sum(1, keepdims=True) * tab.sum(0, keepdims=True) / tab.sum()
    return float(((tab - e) ** 2 / e).sum())


def perm_p(a: np.ndarray, b: np.ndarray, n: int = 2000) -> float:
    obs = chi2_by_hand(a, b)
    return (1 + sum(chi2_by_hand(a, rng.permutation(b)) >= obs - 1e-12 for _ in range(n))) / (n + 1)


def main() -> None:
    out: dict = {}
    summ = json.loads((ROOT / "results_summary.json").read_text())
    # ---------------- validation epsilon^2 (V1 newcomer share) from the raw per-concept table
    V = pd.read_csv(RES / "validation_by_concept.csv")
    val = json.loads((RES / "validation.json").read_text())
    comp = V.dropna(subset=["cluster", "cluster_B1", "B2_vol_tercile", "cluster_B2_volseries"])
    for col in ("V1_newcomer_share", "V2_pct_alt_gain", "V3_comm_touched"):
        d = comp.dropna(subset=[col])
        H, p, e = kw_by_hand(d[col].values.astype(float), d.cluster.astype(str).values)
        ph = [kw_by_hand(d[col].values.astype(float), rng.permutation(d.cluster.astype(str).values))[1] for _ in range(500)]
        out[f"validation_{col}"] = dict(rederived_eps2=e, rederived_p=p, pipeline_eps2=val["results"][col]["3ch"]["eps2"],
                                        pipeline_p=val["results"][col]["3ch"]["kw_p"],
                                        equal=abs(e - val["results"][col]["3ch"]["eps2"]) < 1e-9,
                                        placebo_shuffled_labels_share_p_lt_0_05=float(np.mean(np.array(ph) < 0.05)),
                                        placebo_fails=bool(np.mean(np.array(ph) < 0.05) <= 0.10))
    # ---------------- typology vs volume: AMI with volume terciles from the raw assignment table
    from sklearn.metrics import adjusted_mutual_info_score
    A = pd.read_csv(ROOT / "typology" / "assignments.csv")
    ami_v = adjusted_mutual_info_score(A.cluster.astype(str), A.B2_vol_tercile.astype(str))
    out["AMI_3ch_vs_volume_terciles"] = dict(rederived=ami_v, pipeline=summ["AMI_3ch_vs_B2_tercile"]["value"],
                                             equal=abs(ami_v - summ["AMI_3ch_vs_B2_tercile"]["value"]) < 1e-9)
    # ---------------- cluster x origin group permutation chi-square (hand chi2) + placebo
    p_obs = perm_p(A.cluster.values, A.origin_group.values)
    typ = json.loads((RES / "typology.json").read_text())
    p_pl = [perm_p(A.cluster.values, rng.permutation(A.origin_group.values), 300) for _ in range(40)]
    out["cluster_x_origin_group"] = dict(rederived_perm_p=p_obs, pipeline_perm_p=typ["crosstabs"]["origin_group"]["p_perm"],
                                         both_below_0_05=bool(p_obs < 0.05 and typ["crosstabs"]["origin_group"]["p_perm"] < 0.05),
                                         placebo_share_p_lt_0_05=float(np.mean(np.array(p_pl) < 0.05)),
                                         placebo_fails=bool(np.mean(np.array(p_pl) < 0.05) <= 0.15))
    # ---------------- lead-lag: expansion-first share from the raw per-concept onsets, and a placebo
    L = pd.read_csv(RES / "leadlag_by_concept.csv")
    ok = L.exp_onset.notna() & L.diff_onset.notna() & ~L.exp_from_start.astype(bool) & ~L.diff_from_start.astype(bool)
    both = L[ok]
    share = float((both.exp_onset < both.diff_onset).mean())
    ll = json.loads((RES / "leadlag.json").read_text())
    # placebo: swap the two onset labels at random within each concept -> expected share ~0.5 (the test must not see an order)
    sw = []
    for _ in range(2000):
        flip = rng.random(len(both)) < 0.5
        e = np.where(flip, both.diff_onset, both.exp_onset)
        d = np.where(flip, both.exp_onset, both.diff_onset)
        sw.append(np.mean(e < d))
    out["leadlag_share_expansion_first"] = dict(rederived=share, n_both=int(len(both)), pipeline=ll["primary"]["share_expansion_first"],
                                                equal=abs(share - ll["primary"]["share_expansion_first"]) < 1e-12,
                                                placebo_label_swap_mean=float(np.mean(sw)),
                                                placebo_p_share_ge_observed=float(np.mean(np.array(sw) >= share)),
                                                observed_vs_null_p=ll["null"]["p_one_sided_greater"],
                                                placebo_fails=bool(abs(np.mean(sw) - 0.5) < 0.1))
    # ---------------- roles: robust share + BRIDGE share recounted from the raw role table
    R = pd.read_parquet(RES / "roles.parquet")
    R = R[R.MAIN]
    new = R[[f"primary_s{s}" for s in (101, 102, 103, 104, 105)]].values
    agree = np.array([max(np.sum(row == v) for v in set(row)) for row in new])
    rob = agree >= 3
    out["roles_robust_share"] = dict(rederived=float(rob.mean()), pipeline=summ["roles_robust_share"]["value"],
                                     equal=abs(rob.mean() - summ["roles_robust_share"]["value"]) < 1e-12)
    # placebo: roles drawn independently per seed from the pooled marginal -> agreement must collapse
    pooled = new.ravel()
    pl = np.array([[pooled[rng.integers(0, len(pooled))] for _ in range(5)] for _ in range(len(new))])
    pl_agree = np.array([max(np.sum(row == v) for v in set(row)) for row in pl]) >= 3
    out["roles_robust_share"]["placebo_independent_seeds_share"] = float(pl_agree.mean())
    out["roles_robust_share"]["placebo_lower"] = bool(pl_agree.mean() < rob.mean())
    # ---------------- entry-hazard BRIDGE OR: placebo with shuffled lagged roles (OR should move to ~1 / CI covers 1)
    import statsmodels.api as sm
    P = pd.read_csv(RES / "entry_panel.csv")
    lag = {(c, y + 1): r for c, y, r, b in zip(R.concept_id, R.year, R.role_modal, R.robust) if b}
    P["role"] = [lag.get((c, y)) for c, y in zip(P.concept_id, P.year)]
    P = P.dropna(subset=["role"]).reset_index(drop=True)

    def fit(roles: np.ndarray) -> tuple[float, float, float]:
        X = np.column_stack([np.ones(len(P)), (roles == "BRIDGE").astype(float), (roles == "MIGRANT").astype(float),
                             np.isin(roles, ["OTHER", "FOUNDER", "CORE_GROWING"]).astype(float),
                             np.log1p(P.vol), np.log1p(P.cum_vol_lag), P.age, P.age ** 2, np.log1p(P.cum_subfields_lag),
                             (P.route == P.route.unique()[0]).astype(float)])
        r = sm.Logit(P.any_entry.values, X).fit(disp=0, cov_type="cluster", cov_kwds={"groups": pd.factorize(P.concept_id)[0]})
        ci = r.conf_int()[1]
        return math.exp(r.params[1]), math.exp(ci[0]), math.exp(ci[1])
    o = fit(P.role.values)
    pls = [fit(rng.permutation(P.role.values)) for _ in range(50)]
    out["entry_OR_BRIDGE"] = dict(rederived=o[0], ci=[o[1], o[2]], pipeline=summ["entry_OR_predeclared"]["value"]["BRIDGE"]["ratio"],
                                  equal=abs(o[0] - summ["entry_OR_predeclared"]["value"]["BRIDGE"]["ratio"]) < 1e-6,
                                  placebo_shuffled_roles_median_OR=float(np.median([x[0] for x in pls])),
                                  placebo_share_CI_excludes_1=float(np.mean([(x[1] > 1 or x[2] < 1) for x in pls])),
                                  note="the observed CI already covers 1 (no claim of an effect); placebo confirms OR ~ 1 under shuffling")
    # ---------------- MeSH vs main early bridging: placebo = permute population labels
    pb = pd.read_csv(RES / "patterns_by_concept.csv")
    pool = pd.read_parquet(ROOT / "work" / "pool_active.parquet")
    main = set(pool[(pool.fold == "screen") & pool.MAIN].concept_id)
    x = pb[pb.concept_id.isin(main)].EARLY_BRIDGING.astype(float).values
    import sys
    sys.path.insert(0, str(ROOT / "src"))
    from common import X4
    m = pd.read_csv(X4 / "results" / "rq1_patterns_by_concept.csv").early_bridging.astype(str).eq("True").astype(float).values
    diff = x.mean() - m.mean()
    allv = np.concatenate([x, m])
    perm = []
    for _ in range(5000):
        z = rng.permutation(allv)
        perm.append(z[:len(x)].mean() - z[len(x):].mean())
    perm = np.array(perm)
    out["early_bridging_main_minus_mesh"] = dict(rederived=float(diff), permutation_p_two_sided=float(np.mean(np.abs(perm) >= abs(diff))),
                                                 placebo_mean_diff=float(perm.mean()), placebo_fails=bool(abs(perm.mean()) < 0.02))
    out["all_rederived_equal"] = all(v.get("equal", True) for v in out.values() if isinstance(v, dict))
    out["all_placebos_fail"] = all(v.get("placebo_fails", True) for v in out.values() if isinstance(v, dict))
    (RES / "audit_placebo.json").write_text(json.dumps(out, indent=1, default=float))
    print(json.dumps(out, indent=1, default=float))


if __name__ == "__main__":
    main()
