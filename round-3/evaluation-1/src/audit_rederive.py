#!/usr/bin/env python3
"""Independent re-derivation of the headline numbers through DIFFERENT code paths, plus placebo/shuffle checks.

Does not import part1/part2/part3 or the iteration-2 estimator code. Reads raw result rows directly:
- classifier metrics with plain loops and a Mann-Whitney AUC,
- E_up closure S_raw from matches csv + indicator rows with a hand-written loop,
- turnover residualisation with numpy lstsq (not statsmodels), S_res and retained,
- within-concept r with groupby demeaning + np.corrcoef,
- IVW / Q by hand, held-out id search by plain substring matching,
- placebos: permuted classifier labels, within-set treated/control role permutation, within-concept shuffled closure.
Writes results/audit_rederive.json.
"""
from __future__ import annotations

import csv
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

import common as K

OUT: dict = {}
TOL = {}


def check(name: str, mine: float, recorded: float, tol: float) -> None:
    ok = bool(abs(mine - recorded) <= tol)
    OUT[name] = dict(rederived=mine, reported_by_pipeline=recorded, tol=tol, match=ok)
    print(f"{'OK ' if ok else 'BAD'} {name}: {mine:.6f} vs {recorded:.6f}")


def auc_mw(y, p) -> float:
    pos = [s for s, t in zip(p, y) if t == 1]
    neg = [s for s, t in zip(p, y) if t == 0]
    wins = 0.0
    for a in pos:
        for b in neg:
            wins += 1.0 if a > b else 0.5 if a == b else 0.0
    return wins / (len(pos) * len(neg))


def classifier(ev: dict) -> None:
    items = json.loads((K.E1 / "results/d2_test_predictions.json").read_text())
    thr = json.loads((K.E1 / "results/classifier_results.json").read_text())["thresholds"]["t_F1"]
    tp = fp = fn = tn = 0
    for it in items:
        pred = 1 if it["p"] >= thr else 0
        if pred and it["y"]:
            tp += 1
        elif pred:
            fp += 1
        elif it["y"]:
            fn += 1
        else:
            tn += 1
    P, R = tp / (tp + fp), tp / (tp + fn)
    check("classifier_precision", P, ev["classifier_precision"], 1e-9)
    check("classifier_recall", R, ev["classifier_recall"], 1e-9)
    check("classifier_f1", 2 * P * R / (P + R), ev["classifier_f1"], 1e-9)
    check("classifier_accuracy", (tp + tn) / len(items), ev["classifier_accuracy"], 1e-9)
    y = [it["y"] for it in items]
    p = [it["p"] for it in items]
    check("classifier_auc", auc_mw(y, p), ev["classifier_auc"], 1e-9)
    npos = sum(y)
    Pa = npos / len(y)
    check("majority_all_positive_f1", 2 * Pa / (Pa + 1), ev["majority_all_positive_f1"], 1e-9)
    rng = np.random.default_rng(123)
    perm = [auc_mw(list(rng.permutation(y)), p) for _ in range(20)]
    OUT["placebo_classifier_auc_permuted_labels"] = dict(mean=float(np.mean(perm)), min=float(np.min(perm)), max=float(np.max(perm)),
                                                         fails_as_expected=bool(abs(np.mean(perm) - 0.5) < 0.05))
    print("placebo permuted-label AUC", OUT["placebo_classifier_auc_permuted_labels"])


def load_matches_main() -> list[tuple[str, int, list[str]]]:
    rows = []
    with open(K.E3 / "results/event_study/matches_E_up.csv") as f:
        for r in csv.DictReader(f):
            ctr = [c for c in (r["controls"] or "").split("|") if c]
            if ctr:
                rows.append((r["concept_id"], int(r["t0"]), ctr))
    return rows


def load_matches_mesh() -> list[tuple[str, int, list[str]]]:
    m = json.loads((K.E4 / "results/analysis_summary.json").read_text())["mainpool_block"]["E_up"]["matches"]
    return [(r["concept_id"], int(r["t0"]), list(r["controls"])) for r in m if r["controls"]]


def S_of(sets, val: dict, mask_val: dict | None = None) -> tuple[float, int]:
    """Mean over k in [-3,0] of the mean over treated of (treated - mean(finite controls)); optional finite-cell mask."""
    per_k = {k: [] for k in range(-5, 1)}
    used = set()
    for c, t0, ctr in sets:
        for k in range(-5, 1):
            y = t0 + k
            tv = val.get((c, y), float("nan"))
            cv = [val.get((n, y), float("nan")) for n in ctr]
            cv = [x for x in cv if not math.isnan(x)]
            if math.isnan(tv) or not cv:
                continue
            if mask_val is not None:
                mt = mask_val.get((c, y), float("nan"))
                mc = [mask_val.get((n, y), float("nan")) for n in ctr]
                mc = [x for x in mc if not math.isnan(x)]
                if math.isnan(mt) or not mc:
                    continue
            per_k[k].append(tv - sum(cv) / len(cv))
            if k >= -3:
                used.add(c)
    means = [sum(v) / len(v) for k, v in per_k.items() if k >= -3 and v]
    return sum(means) / len(means), len(used)


def resid_lstsq(d: pd.DataFrame, covs: list[str], fit: pd.Series) -> dict:
    X = np.column_stack([np.ones(len(d))] + [d[c].to_numpy(float) for c in covs])
    yv = d["closure"].to_numpy(float)
    ok = np.isfinite(X).all(axis=1) & np.isfinite(yv)
    b = np.linalg.lstsq(X[ok & fit.to_numpy()], yv[ok & fit.to_numpy()], rcond=None)[0]
    r = np.where(ok, yv - X @ b, np.nan)
    return {(c, int(t)): v for c, t, v in zip(d.concept_id, d.year, r)}


def r1a(ev: dict, r1: dict) -> None:
    evt = {(e["population"], e["spec"]): e for e in r1["event"]}
    # ---- main
    d = pd.read_parquet(K.E3 / "results/indicators/concept_year_indicators.parquet")
    d["lv"], d["lv3"] = np.log1p(d.vol.astype(float)), np.log1p(d.vol3.astype(float))
    raw = {(c, int(t)): float(v) for c, t, v in zip(d.concept_id, d.year, d.closure)}
    sets = load_matches_main()
    S_raw, n = S_of(sets, raw)
    check("main_S_raw", S_raw, ev["main_S_raw"], 1e-9)
    fit = (d.fold == "screen") & (d.age >= 0) & d.year.between(2005, 2019) & d.closure.notna()
    res = resid_lstsq(d, ["lv", "lv3", "age", "H", "new_relation_rate", "novelty", "beta_sim_raw"], fit)
    S_res, n_res = S_of(sets, res)
    S_cc, _ = S_of(sets, raw, mask_val=res)
    check("main_S_res", S_res, ev["main_S_res"], 1e-6)
    check("main_S_raw_cc", S_cc, ev["main_S_raw_cc"], 1e-6)
    check("main_retained", S_res / S_cc, ev["main_retained"], 1e-6)
    main_sets, main_res = sets, res
    # ---- MeSH
    f = pd.read_parquet(K.E4 / "results/features.parquet")
    f["lv"], f["lv3"] = np.log1p(f.vol.astype(float)), np.log1p(f.vol3.astype(float))
    rawm = {(c, int(t)): float(v) for c, t, v in zip(f.concept_id, f.year, f.closure)}
    msets = load_matches_mesh()
    Sm, _ = S_of(msets, rawm)
    check("mesh_S_raw", Sm, ev["mesh_S_raw"], 1e-9)
    fitm = (f.age >= 0) & f.year.between(2005, 2019) & f.closure.notna()
    resm = resid_lstsq(f, ["lv", "lv3", "age", "new_rel_rate", "nbr_novelty", "beta_sim_raw"], fitm)
    Smr, _ = S_of(msets, resm)
    Smcc, _ = S_of(msets, rawm, mask_val=resm)
    check("mesh_S_res", Smr, ev["mesh_S_res"], 1e-6)
    check("mesh_retained", Smr / Smcc, ev["mesh_retained"], 1e-6)
    # ---- IVW / Q by hand from the recorded S_res and SE
    a, b = evt[("main", "P")], evt[("mesh", "P")]
    w1, w2 = 1 / a["S_res_se"] ** 2, 1 / b["S_res_se"] ** 2
    mu = (w1 * a["S_res"] + w2 * b["S_res"]) / (w1 + w2)
    Q = w1 * (a["S_res"] - mu) ** 2 + w2 * (b["S_res"] - mu) ** 2
    check("ivw_S_res", mu, ev["ivw_S_res"], 1e-9)
    check("Q_res", Q, ev["Q_res"], 1e-9)
    check("I2_res", max(0.0, (Q - 1) / Q), ev["I2_res"], 1e-9)
    # independent bootstrap SE of main S_res (own RNG, own resampler): should be close to the pipeline SE
    rng = np.random.default_rng(2024)
    bs = [S_of([main_sets[i] for i in rng.integers(0, len(main_sets), len(main_sets))], main_res)[0] for _ in range(400)]
    OUT["main_S_res_se_independent_bootstrap"] = dict(se=float(np.std(bs, ddof=1)), pipeline_se=a["S_res_se"],
                                                      ci=np.percentile(bs, [2.5, 97.5]).tolist(), pipeline_ci=a["S_res_ci"])
    print("independent bootstrap", OUT["main_S_res_se_independent_bootstrap"])
    # ---- placebo 1: permute treated/control roles within each matched set (S should be centred on 0)
    rng = np.random.default_rng(7)
    for pop, ss, vv, obs in (("main", main_sets, main_res, S_res), ("mesh", msets, resm, Smr)):
        perm = []
        for _ in range(200):
            ps = []
            for c, t0, ctr in ss:
                mem = [c] + ctr
                j = int(rng.integers(0, len(mem)))
                ps.append((mem[j], t0, [m for i, m in enumerate(mem) if i != j]))
            perm.append(S_of(ps, vv)[0])
        perm = np.array(perm)
        OUT[f"placebo_{pop}_role_permutation_S_res"] = dict(mean=float(perm.mean()), sd=float(perm.std()), observed=obs,
                                                            share_abs_ge_observed=float(np.mean(np.abs(perm) >= abs(obs))),
                                                            centred_on_zero=bool(abs(perm.mean()) < 0.25 * perm.std()))
        print("placebo roles", pop, OUT[f"placebo_{pop}_role_permutation_S_res"])
    # ---- within-concept r (groupby demeaning, np.corrcoef) + within-concept shuffled placebo
    for pop, df, col, key in (("main", d, "new_relation_rate", "main_r_within_closure_new_rel"),
                              ("mesh", f, "new_rel_rate", "mesh_r_within_closure_new_rel")):
        u = df[(df.age >= 0) & df.year.between(2005, 2019) & df.closure.notna() & df[col].notna()]
        if pop == "main":
            u = u[u.fold.isin(["screen", "reference"])]
        u = u[u.groupby("concept_id").closure.transform("size") >= 3]
        x = u.closure - u.groupby("concept_id").closure.transform("mean")
        z = u[col] - u.groupby("concept_id")[col].transform("mean")
        check(key, float(np.corrcoef(x, z)[0, 1]), ev[key], 1e-9)
        rng = np.random.default_rng(11)
        rs = []
        for _ in range(50):
            sh = u.groupby("concept_id").closure.transform(lambda s: rng.permutation(s.to_numpy()))
            xs = sh - u.groupby("concept_id").closure.transform("mean")
            rs.append(np.corrcoef(xs, z)[0, 1])
        OUT[f"placebo_{pop}_within_shuffled_r"] = dict(mean=float(np.mean(rs)), p95_abs=float(np.percentile(np.abs(rs), 95)),
                                                       observed=ev[key], observed_exceeds_null=bool(abs(ev[key]) > np.percentile(np.abs(rs), 95)))
        print("placebo within r", pop, OUT[f"placebo_{pop}_within_shuffled_r"])


def heldout(ev: dict) -> None:
    pool = json.loads((K.RES / "cache_d5_pool.json").read_text())["pool"]
    ids = [c for c, f, _ in pool if f == "heldout_concept"]
    hits, n_files = 0, 0
    for root in (K.E3 / "results", K.E4 / "results"):
        for p in root.rglob("*"):
            if not p.is_file():
                continue
            n_files += 1
            if p.suffix == ".parquet":
                txt = pd.read_parquet(p).to_csv(index=False)
            else:
                txt = p.read_bytes().decode("latin-1")
            hits += sum(1 for i in ids if i in txt)
    check("heldout_id_hits_exp3_exp4", float(hits), ev["heldout_id_hits_exp3_exp4"], 0)
    OUT["heldout_files_scanned_substring"] = n_files
    # positive control for the scanner: exp_2 viability layer DOES contain held-out ids of the iteration-1 fold
    it1 = json.loads((K.RES / "heldout_audit.json").read_text())
    ex2 = [r for r in it1["exp2"] if r.get("n_heldout_hits", 0)]
    txt = (K.E2 / "results/viability/viability_layer.csv").read_text()
    OUT["scanner_positive_control_exp2_viability_hits"] = sum(1 for i in ids if i in txt)
    OUT["scanner_positive_control_detects"] = OUT["scanner_positive_control_exp2_viability_hits"] > 0 and len(ex2) > 0


def drift_links() -> None:
    rep = K.REPORT.read_text().splitlines()
    rows = json.loads((K.RES / "record_of_numbers.json").read_text())["rows"]
    bad, n = [], 0
    for r in rows:
        if r["flag"] in ("OK", "MISSING_IN_REPORT", "NOT_REDERIVABLE") or r["report_line"] is None or r["report_value"] is None:
            continue
        n += 1
        line = rep[int(r["report_line"]) - 1].replace(",", "")
        v = r["report_value"]
        cands = {f"{v:g}", f"{v:.1f}", f"{v:.2f}", f"{v:.3f}", f"{abs(v):.3f}", f"{abs(v):.2f}", f"{v:+.3f}"}
        if not any(c in line for c in cands):
            bad.append(r["id"])
    OUT["drift_flag_report_lines_verified"] = dict(n_checked=n, n_line_mismatch=len(bad), mismatched=bad)
    print("drift links", OUT["drift_flag_report_lines_verified"])


def main() -> None:
    ev = json.loads((K.WS / "eval_out.json").read_text())["metrics_agg"]
    r1 = json.loads((K.R1A / "r1a_results.json").read_text())
    classifier(ev)
    r1a(ev, r1)
    heldout(ev)
    drift_links()
    n_ok = sum(1 for v in OUT.values() if isinstance(v, dict) and v.get("match") is True)
    n_chk = sum(1 for v in OUT.values() if isinstance(v, dict) and "match" in v)
    OUT["summary"] = dict(n_checked=n_chk, n_match=n_ok)
    K.dump(OUT, K.RES / "audit_rederive.json")
    print(OUT["summary"])


if __name__ == "__main__":
    main()
