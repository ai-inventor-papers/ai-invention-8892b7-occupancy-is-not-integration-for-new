#!/usr/bin/env python3
"""STEP 7 (part a): apply the frozen concept classifier to all 426 frame concepts (main + reference, hydrated + pending).
Thresholds are READ from models/thresholds.json (never recomputed). Writes results/frame_predictions_prelabel.json and
its sha256 BEFORE any frame LLM label exists (s6 asserts this). Also: top-5 feature contributions per concept,
pre-declared covariate-shift diagnostic (adversarial LR D2-train vs frame per feature block), the -termhood sensitivity
flag, an uncensored-termhood sensitivity column, and the F4 best-comparison column."""
from __future__ import annotations

import hashlib
import json
import time

import joblib
import numpy as np
from loguru import logger
from sklearn.decomposition import PCA
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.metrics import roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from clfdata import FeatureSource
from common import DATA, MODELS, RESULTS, SEED, load_frame, load_hydrated, read_json, set_limits, setup_logging, write_json


def jaccard(a: set, b: set) -> float:
    return len(a & b) / len(a | b) if a | b else 1.0


def contributions(pipe, X: np.ndarray, names: list[str], blocks: dict) -> list[list[tuple[str, float]]]:
    ct = pipe.named_steps["ct"]
    coef = pipe.named_steps["clf"].coef_[0]
    Z = ct.transform(X)
    fn = []
    for name, tr, cols in ct.transformers_:
        if name == "remainder" or tr == "drop":
            continue
        if name == "tab":
            fn += [names[c] for c in cols]
        else:
            k = tr.named_steps["pca"].n_components_ if hasattr(tr, "named_steps") else len(cols)
            fn += [f"{name}_pc{i}" for i in range(k)] if hasattr(tr, "named_steps") else [names[c] for c in cols]
    C = Z * coef
    out = []
    for row in C:
        top = np.argsort(-np.abs(row))[:5]
        out.append([(fn[i], round(float(row[i]), 3)) for i in top])
    return out


@logger.catch(reraise=True)
def main() -> None:
    setup_logging("s7a_predict")
    set_limits(40)
    t0 = time.time()
    frame = load_frame()
    hyd = load_hydrated()
    thr = read_json(MODELS / "thresholds.json")
    thr_c = read_json(MODELS / "thresholds_comparisons.json")
    prim = joblib.load(MODELS / "concept_lr.joblib")
    nth = joblib.load(MODELS / "concept_lr_notermhood.joblib")
    bestc = joblib.load(MODELS / "concept_best_comparison.joblib")
    fs = FeatureSource()
    cids = sorted(frame)
    items = [{"ns": "frame", "id": c, "th_qid": f"frame:{c}", "text": frame[c]["phrase"], "ctx_key": f"frame:{c}"} for c in cids]
    X, blocks, names = fs.build(items)
    items_full = [{**it, "th_qid": f"framefull:{it['id']}"} for it in items]
    Xfull, _, _ = fs.build(items_full)
    p = prim["pipeline"].predict_proba(X)[:, 1]
    p_uncens = prim["pipeline"].predict_proba(Xfull)[:, 1]
    p_nth = nth["pipeline"].predict_proba(X)[:, 1]
    p_best = bestc["pipeline"].predict_proba(X)[:, 1]
    acc = p >= thr["t_F1"]
    acc_s = p >= thr["t_P90"]
    acc_nth = p_nth >= nth["t_F1"]
    acc_unc = p_uncens >= thr["t_F1"]
    acc_best = p_best >= bestc["t_F1"]
    reasons = contributions(prim["pipeline"], X, names, blocks)

    # ---------------- covariate-shift diagnostic (features only, no labels)
    d2 = read_json(DATA / "d2.json")
    tr_rows = [r for r in d2 if r["metadata_fold"] == "train" and r["output"] != "UNRESOLVED"]
    Xtr, _, _ = fs.build([{"ns": "d2", "id": r["key"], "th_qid": f"d2:{r['key']}", "text": r["key"], "ctx_key": f"d2:{r['key']}"} for r in tr_rows])
    shift = {}
    Xall = np.concatenate([Xtr, X])
    yall = np.r_[np.zeros(len(Xtr)), np.ones(len(X))]
    for bname, cols in (("termhood", blocks["th"]), ("lexical", blocks["lex"]), ("embeddings", blocks["mini"] + blocks["spec"])):
        steps = [("sc", StandardScaler())]
        if bname == "embeddings":
            steps.append(("pca", PCA(64, random_state=SEED)))
        steps.append(("lr", LogisticRegression(max_iter=5000, C=1.0, class_weight="balanced")))
        pp = cross_val_predict(Pipeline(steps), Xall[:, cols], yall, cv=StratifiedKFold(5, shuffle=True, random_state=SEED),
                               method="predict_proba")[:, 1]
        shift[bname] = float(roc_auc_score(yall, pp))
    # per-feature shift for termhood (standardised mean difference)
    smd = {}
    for c in blocks["th"]:
        a, b = Xtr[:, c], X[:, c]
        sd = np.sqrt((a.var() + b.var()) / 2) or 1.0
        smd[names[c]] = float((b.mean() - a.mean()) / sd)
    set_p, set_n = {c for c, a in zip(cids, acc) if a}, {c for c, a in zip(cids, acc_nth) if a}
    jac_nth = jaccard(set_p, set_n)
    rule_triggered = shift["termhood"] > 0.90
    sens_pair_required = bool(rule_triggered and jac_nth < 0.80)
    cls = read_json(RESULTS / "classifier_results.json")
    test_f1 = cls["test_primary_tF1"]["f1"]["point"]
    cv_f1 = cls["test_baselines"]["cvalue_threshold"]["metrics"]["f1"]["point"]
    f4 = bool(test_f1 < 0.70 or test_f1 < cv_f1)
    diag = {"adversarial_auc_by_block": shift, "termhood_standardised_mean_diff_frame_minus_d2train": smd,
            "rule": "if termhood-block AUC > 0.90 also compute accepted_primary_notermhood; if Jaccard(primary, notermhood) < 0.80 iteration 3 must run both as a sensitivity pair",
            "rule_triggered": rule_triggered, "jaccard_primary_vs_notermhood": jac_nth,
            "sensitivity_pair_required": sens_pair_required,
            "jaccard_primary_vs_uncensored_termhood": jaccard(set_p, {c for c, a in zip(cids, acc_unc) if a}),
            "F4_triggered": f4, "F4_rule": "test F1 < 0.70 or below the C-value baseline -> best CV comparison model's accept flags written as a sensitivity column; MAIN rule unchanged",
            "best_comparison_model": bestc.get("name")}
    recs = []
    for i, c in enumerate(cids):
        fr = frame[c]
        recs.append({"concept_id": c, "phrase": fr["phrase"], "arm": fr["arm"], "hydrated": c in hyd,
                     "p_concept": round(float(p[i]), 6), "accepted_primary": bool(acc[i]), "accepted_strict": bool(acc_s[i]),
                     "p_concept_notermhood": round(float(p_nth[i]), 6), "accepted_primary_notermhood": bool(acc_nth[i]),
                     "p_concept_uncensored_termhood": round(float(p_uncens[i]), 6), "accepted_primary_uncensored_termhood": bool(acc_unc[i]),
                     "p_concept_best_comparison": round(float(p_best[i]), 6), "accepted_best_comparison": bool(acc_best[i]),
                     "reason_top5": reasons[i],
                     "termhood": {n: round(float(X[i, j]), 4) for n, j in zip([names[j] for j in blocks["th"]], blocks["th"])}})
    out = {"meta": {"created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "thresholds": thr,
                    "model_sha256": thr["model_sha256"], "notermhood_t_F1": nth["t_F1"],
                    "note": "written BEFORE any frame LLM label is requested; s6 refuses to label without this file"},
           "diagnostics": diag, "predictions": recs}
    s = json.dumps(out, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    (RESULTS / "frame_predictions_prelabel.json").write_text(s)
    (RESULTS / "frame_predictions_prelabel.sha256").write_text(hashlib.sha256(s.encode()).hexdigest() + "\n")
    logger.info(f"frame: accepted_primary {int(acc.sum())}/{len(acc)} (main {sum(a for a, c in zip(acc, cids) if frame[c]['arm'] == 'main')}), "
                f"strict {int(acc_s.sum())}; shift {shift}; jaccard nth {jac_nth:.3f} ({time.time() - t0:.0f}s)")


if __name__ == "__main__":
    main()
