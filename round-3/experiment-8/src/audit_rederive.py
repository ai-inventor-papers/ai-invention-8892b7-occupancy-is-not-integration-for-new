#!/usr/bin/env python3
"""T6 audit: re-derive four headline numbers through independent code paths (plain loops, no pipeline helpers) and
assert equality with the pipeline outputs. Writes results/audit_rederive.json; exits 1 on any mismatch.

1. k* stability table: cluster-wise mean best Jaccard at k = 2..8 from typology/D_primary.npy (own bootstrap loop,
   same resample seeds as the pipeline).
2. share expansion_first: onsets re-detected from the indicator table with explicit loops.
3. early-bridging difference, hydrated screen MAIN minus MeSH.
4. entry-hazard OR for BRIDGE: logit refitted on a hand-built design matrix (no formula API).
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))
from common import X4  # noqa: E402

RES = ROOT / "results"


def jaccard_table(D: np.ndarray, B: int = 200) -> dict:
    import kmedoids
    out = {}
    n = len(D)
    for k in range(2, 9):
        labels = np.asarray(kmedoids.fasterpam(D, k, random_state=0).labels)
        rng = np.random.default_rng(k)
        tot = [0.0] * k
        for b in range(B):
            idx = np.unique(rng.integers(0, n, n))
            lb = np.asarray(kmedoids.fasterpam(D[np.ix_(idx, idx)], k, random_state=b).labels)
            for ci in range(k):
                A = {int(i) for i, l in zip(idx, labels[idx]) if l == ci}
                best = 0.0
                for cb in range(k):
                    Bs = {int(i) for i, l in zip(idx, lb) if l == cb}
                    u = len(A | Bs)
                    if u:
                        best = max(best, len(A & Bs) / u)
                tot[ci] += best
        out[str(k)] = min(t / B for t in tot)
    return out


def expansion_first_share() -> float:
    ind = pd.read_parquet(RES / "indicators" / "concept_year_indicators_hyd.parquet")
    pool = pd.read_parquet(ROOT / "work" / "pool_active.parquet")
    ids = sorted(pool[(pool.fold == "screen") & (pool.arm == "main") & pool.MAIN].concept_id)
    cp = pd.read_parquet(ROOT / "work" / "cp_hyd.parquet", columns=["concept_id", "year", "subfield"])
    ef = tot = 0
    for c in ids:
        g = ind[ind.concept_id == c]
        pct = dict(zip(g.year, g.pct_alt))
        H = dict(zip(g.year, g.H_rar))
        nf = dict(zip(g.year, g.n_frame))
        fa = min([y for y, v in nf.items() if v > 0], default=None)
        # first-activation years of subfields (>= 2 c-papers in a 3-year window)
        mine = cp[(cp.concept_id == c) & (cp.subfield >= 0)]
        counts = {}
        for s_, y in zip(mine.subfield, mine.year):
            counts[(s_, y)] = counts.get((s_, y), 0) + 1
        first_act = {}
        for s_ in set(mine.subfield):
            for y in range(1998, 2025):
                if sum(counts.get((s_, yy), 0) for yy in (y - 2, y - 1, y)) >= 2:
                    first_act[s_] = y
                    break
        new_years = set(first_act.values())
        ys = sorted(g.year)
        exp, exp_first_eval = None, None
        for y in ys:
            if fa is None or y < fa + 1:
                continue
            a, b, d = pct.get(y - 1), pct.get(y), pct.get(y + 1)
            if a is None or b is None or d is None or any(isinstance(v, float) and math.isnan(v) for v in (a, b, d)):
                continue
            if exp_first_eval is None:
                exp_first_eval = y
            if b - a >= 10 and d - b >= 10:
                exp = y
                break
        dif, dif_first_eval = None, None
        for y in ys:
            a, b = H.get(y - 2), H.get(y)
            if a is None or b is None or math.isnan(a) or math.isnan(b):
                continue
            if dif_first_eval is None:
                dif_first_eval = y
            if b - a >= 0.2 and y in new_years:
                dif = y
                break
        if exp == exp_first_eval:
            exp = None
        if dif == dif_first_eval:
            dif = None
        if exp is not None and dif is not None:
            tot += 1
            ef += exp < dif
    return ef / tot


def eb_diff() -> float:
    p = pd.read_csv(RES / "patterns_by_concept.csv")
    pool = pd.read_parquet(ROOT / "work" / "pool_active.parquet")
    main = set(pool[(pool.fold == "screen") & pool.MAIN].concept_id)
    x = [bool(v) for c, v in zip(p.concept_id, p.EARLY_BRIDGING) if c in main]
    m = pd.read_csv(X4 / "results" / "rq1_patterns_by_concept.csv")
    y = [str(v) == "True" for v in m.early_bridging]
    return sum(x) / len(x) - sum(y) / len(y)


def bridge_or() -> float:
    import statsmodels.api as sm
    panel = pd.read_csv(RES / "entry_panel.csv")
    r = pd.read_parquet(RES / "roles.parquet")
    lag = {(c, y + 1): (role if rob else None) for c, y, role, rob in zip(r.concept_id, r.year, r.role_modal, r.robust)}
    rows, yv, groups = [], [], []
    levels = sorted({v for v in lag.values() if v is not None} - {"STAYER"})
    routes = sorted(panel.route.dropna().unique())
    counts = {}
    for c, y, e in zip(panel.concept_id, panel.year, panel.any_entry):
        role = lag.get((c, y))
        if role is not None:
            counts.setdefault(role, [0, 0])
            counts[role][0] += 1
            counts[role][1] += e
    merged = {l for l in levels if counts.get(l, [0, 0])[1] < 5 or counts[l][0] - counts[l][1] < 5}
    levels = [l for l in levels if l not in merged] + (["OTHER"] if merged and "OTHER" not in levels else [])
    levels = sorted(set(levels))
    for rec in panel.itertuples():
        role = lag.get((rec.concept_id, rec.year))
        if role is None:
            continue
        if role in merged:
            role = "CORE_GROWING" if role == "FOUNDER" else "OTHER"
        x = [1.0] + [1.0 if role == l else 0.0 for l in levels if l != "STAYER"]
        x += [math.log1p(rec.vol), math.log1p(rec.cum_vol_lag), rec.age, rec.age ** 2, math.log1p(rec.cum_subfields_lag)]
        x += [1.0 if rec.route == rt else 0.0 for rt in routes[1:]]
        rows.append(x)
        yv.append(rec.any_entry)
        groups.append(rec.concept_id)
    X = np.array(rows)
    names = [l for l in levels if l != "STAYER"]
    res = sm.Logit(np.array(yv), X).fit(disp=0, maxiter=200)
    return float(math.exp(res.params[1 + names.index("BRIDGE")]))


def main() -> None:
    typ = json.loads((RES / "typology.json").read_text())
    ll = json.loads((RES / "leadlag.json").read_text())
    roles = json.loads((RES / "roles.json").read_text())
    pc = pd.read_csv(RES / "patterns_contrast.csv")
    pc = pc[(pc.threshold_version == "recomputed_hydrated") & (pc.population == "screen_MAIN") & (pc.main_pattern == "EARLY_BRIDGING")]
    checks = {}
    jt = jaccard_table(np.load(ROOT / "typology" / "D_primary.npy"))
    checks["stability_min_jaccard_by_k"] = dict(audit=jt, pipeline={k: v["min_jaccard"] for k, v in typ["by_k"].items()},
                                                equal=all(abs(jt[k] - typ["by_k"][k]["min_jaccard"]) < 1e-9 for k in jt))
    s = expansion_first_share()
    checks["share_expansion_first"] = dict(audit=s, pipeline=ll["primary"]["share_expansion_first"],
                                           equal=abs(s - ll["primary"]["share_expansion_first"]) < 1e-12)
    d = eb_diff()
    checks["early_bridging_main_minus_mesh"] = dict(audit=d, pipeline=float(pc["diff"].iloc[0]), equal=abs(d - float(pc["diff"].iloc[0])) < 1e-12)
    o = bridge_or()
    op = roles["predeclared"]["entry_hazard"]["primary_logit_robust"]["terms"]["BRIDGE"]["ratio"]
    checks["entry_OR_BRIDGE"] = dict(audit=o, pipeline=op, equal=abs(o - op) < 1e-6)
    # T4 sanity checks
    sanity = {}
    for suf in ("", "_poolrel"):
        ba = pd.read_csv(RES / f"role_shares_by_age{suf}.csv")
        sums = ba.groupby("age_c").share.sum()
        tm = pd.read_csv(RES / f"role_transition_matrix{suf}.csv", index_col=0).dropna(how="all")
        sanity[f"role_shares_sum_to_1{suf}"] = bool(np.allclose(sums.values, 1.0))
        sanity[f"transition_rows_sum_to_1{suf}"] = bool(np.allclose(tm.sum(axis=1).values, 1.0))
    pj = json.loads((RES / "patterns.json").read_text())
    sanity["mesh_aggregates_reproduced"] = all(v["equal"] for v in pj["mesh_verification"].values())
    o = pj["old123_frozen_reproduction"]
    sanity["old123_incubation_and_centralisation_reproduced"] = all(abs(o["hydrated"][k] - o["iter2"][k]) < 1e-12
                                                                    for k in ("INCUBATION_THEN_EXPANSION", "GRADUAL_CENTRALISATION"))
    sanity["old123_early_bridging_restored_with_iter2_flag"] = abs(pj["early_bridging_gap_diagnostic"]["hydrated_with_iter2_cross_flag"]
                                                                  - o["iter2"]["EARLY_BRIDGING"]) < 1e-12
    sanity["null_mean_between_0_and_1"] = 0 < ll["null"]["null_mean"] < 1
    val = json.loads((RES / "validation.json").read_text())
    sanity["permuted_KW_p_calibrated"] = val["permutation_calibration_V2"]["ks_uniform_p"] > 0.01
    checks["sanity"] = dict(audit=sanity, pipeline=None, equal=all(sanity.values()))
    ok = all(v["equal"] for v in checks.values())
    (RES / "audit_rederive.json").write_text(json.dumps(dict(all_equal=ok, checks=checks), indent=1))
    print(json.dumps(dict(all_equal=ok, **{k: (v["audit"], v["pipeline"], v["equal"]) for k, v in checks.items()}), indent=1, default=str))
    if not ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
