#!/usr/bin/env python3
"""STEP 3: concept / not-concept classifier.
PRIMARY (pre-registered): StandardScaler + L2 logistic regression on [lexical + termhood + PCA(MiniLM) + PCA(SPECTER2)],
tuned by 5-fold StratifiedGroupKFold (groups = D2 variant cluster) on D2-train only; thresholds from OOF probabilities
(t_F1 = argmax OOF F1, t_P90 = smallest t with OOF precision >= 0.90) are written to models/thresholds.json BEFORE the
300 test items are scored once. Comparisons, ablations, baselines, bootstrap CIs, paired bootstrap differences,
reliability curve, 4-class secondary model, and the human anchors (SemEval-2017 / SciERC) E1/E2."""
from __future__ import annotations

import hashlib
import itertools
import json
import time
from collections import Counter

import joblib
import matplotlib
import numpy as np
from loguru import logger
from sklearn.calibration import calibration_curve
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import confusion_matrix, f1_score
from sklearn.model_selection import StratifiedGroupKFold

from clfdata import (FeatureSource, _prf, best_f1_threshold, boot_idx, boot_metrics, make_pipeline, paired_diff,
                     point_metrics, precision_threshold)
from common import DATA, MINI, MODELS, RESULTS, SEED, normalise, read_json, set_limits, setup_logging, sha256_file, write_json

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

C_GRID = [0.01, 0.03, 0.1, 0.3, 1, 3, 10]
CW_GRID = [None, "balanced"]
PCA_GRID = [64, None]
FULL = ["lex", "th", "mini", "spec"]
ABLATIONS = {"no_termhood": ["lex", "mini", "spec"], "no_embeddings": ["lex", "th"], "lexical_only": ["lex"],
             "minilm_only": ["mini"], "specter2_only": ["spec"], "full_plus_context": FULL + ["ctx", "ctxflag"]}


def groups_for(rows: list[dict]) -> np.ndarray:
    g = []
    for i, r in enumerate(rows):
        c = r.get("metadata_variant_cluster")
        g.append(str(c) if c is not None else f"solo_{i}")
    return np.array(g)


FOLDS: dict = {}


def oof_proba(make, X, y, groups, n_splits=5) -> np.ndarray:
    cv = StratifiedGroupKFold(n_splits=n_splits, shuffle=True, random_state=SEED)
    p = np.zeros(len(y))
    fold = np.zeros(len(y), dtype=int)
    for k, (tr, va) in enumerate(cv.split(X, y, groups)):
        m = make()
        m.fit(X[tr], y[tr])
        p[va] = m.predict_proba(X[va])[:, 1]
        fold[va] = k
    FOLDS["last"] = fold
    return p


def mean_fold_f1(y, p, thr=0.5) -> float:
    fold = FOLDS["last"]
    return float(np.mean([f1_score(y[fold == k], (p[fold == k] >= thr).astype(int)) for k in np.unique(fold)]))


def tune_lr(X, y, groups, blocks, use, grid_pca=PCA_GRID) -> tuple[dict, list[dict], np.ndarray]:
    results = []
    best = None
    for C, cw, pca in itertools.product(C_GRID, CW_GRID, grid_pca):
        if not any(b in ("mini", "spec", "ctx") for b in use) and pca is not None:
            continue
        mk = lambda C=C, cw=cw, pca=pca: make_pipeline(blocks, use, pca=pca, C=C, class_weight=cw)
        p = oof_proba(mk, X, y, groups)
        f1 = mean_fold_f1(y, p)  # selection criterion: mean OOF F1 over the 5 folds (at 0.5)
        r = {"C": C, "class_weight": cw, "pca": pca, "oof_f1_at_0.5": f1, "oof_best_thr_f1": best_f1_threshold(y, p)[1],
             "oof_auc": float(point_metrics(y, p, (p >= 0.5).astype(int)).get("auc", np.nan))}
        results.append(r)
        if best is None or r["oof_f1_at_0.5"] > best[0]["oof_f1_at_0.5"]:
            best = (r, p)
    return best[0], results, best[1]


def tune_hgb(X, y, groups, blocks, use) -> tuple[dict, list[dict], np.ndarray]:
    results, best = [], None
    for lr, leaves, l2 in itertools.product([0.05, 0.1], [15, 31], [0.0, 1.0]):
        hp = {"learning_rate": lr, "max_leaf_nodes": leaves, "l2_regularization": l2, "max_iter": 300,
              "early_stopping": False}
        mk = lambda hp=hp: make_pipeline(blocks, use, pca=64, model="hgb", hgb=hp)
        p = oof_proba(mk, X, y, groups)
        f1 = mean_fold_f1(y, p)
        r = {**hp, "oof_f1_at_0.5": f1, "oof_best_thr_f1": best_f1_threshold(y, p)[1]}
        results.append(r)
        if best is None or f1 > best[0]["oof_f1_at_0.5"]:
            best = (r, p)
    return best[0], results, best[1]


def model_hash(path) -> str:
    return sha256_file(path)


@logger.catch(reraise=True)
def main() -> None:
    setup_logging("s3_classifier")
    set_limits(40)
    t0 = time.time()
    d2 = read_json(DATA / "d2.json")
    tr_rows = [r for r in d2 if r["metadata_fold"] == "train" and r["output"] != "UNRESOLVED"]
    te_rows = [r for r in d2 if r["metadata_fold"] == "test" and r["output"] != "UNRESOLVED"]
    n_unres = sum(r["output"] == "UNRESOLVED" for r in d2 if r["metadata_fold"] in ("train", "test"))
    if MINI:
        tr_rows, te_rows = tr_rows[:60] + tr_rows[-60:], te_rows[:30] + te_rows[-30:]
    logger.info(f"train {len(tr_rows)} {Counter(r['output'] for r in tr_rows)}; test {len(te_rows)} "
                f"{Counter(r['output'] for r in te_rows)}; dropped UNRESOLVED {n_unres}")
    # leakage assert: no normalised key shared between train and test
    k_tr = {normalise(r["key"]) for r in tr_rows} | {normalise(s) for r in tr_rows for s in r["surface_forms"]}
    k_te = {normalise(r["key"]) for r in te_rows} | {normalise(s) for r in te_rows for s in r["surface_forms"]}
    overlap = k_tr & k_te
    assert len(overlap) == 0 or MINI, f"D2 train/test key overlap: {list(overlap)[:5]}"

    fs = FeatureSource()

    def items_d2(rows):
        return [{"ns": "d2", "id": r["key"], "th_qid": f"d2:{r['key']}", "text": r["key"], "ctx_key": f"d2:{r['key']}"} for r in rows]

    Xtr, blocks, names = fs.build(items_d2(tr_rows))
    Xte, _, _ = fs.build(items_d2(te_rows))
    ytr = np.array([r["output"] == "CONCEPT" for r in tr_rows], dtype=int)
    yte = np.array([r["output"] == "CONCEPT" for r in te_rows], dtype=int)
    gtr = groups_for(tr_rows)
    logger.info(f"X train {Xtr.shape}, blocks { {k: len(v) for k, v in blocks.items()} }")

    # ---------------- PRIMARY tuning (train only)
    best, grid, p_oof = tune_lr(Xtr, ytr, gtr, blocks, FULL)
    logger.info(f"PRIMARY best config {best} ({time.time() - t0:.0f}s)")
    t_f1, oof_f1 = best_f1_threshold(ytr, p_oof)
    t_p90 = precision_threshold(ytr, p_oof, 0.90)
    primary = make_pipeline(blocks, FULL, pca=best["pca"], C=best["C"], class_weight=best["class_weight"])
    primary.fit(Xtr, ytr)
    MODELS.mkdir(exist_ok=True)
    joblib.dump({"pipeline": primary, "blocks": blocks, "use": FULL, "names": names, "config": best}, MODELS / "concept_lr.joblib")
    thresholds = {"t_F1": t_f1, "oof_f1_at_t_F1": oof_f1, "t_P90": t_p90,
                  "t_P90_note": "smallest t with OOF precision >= 0.90" if t_p90 is not None else "precision 0.90 never reached; STRICT uses max OOF prob",
                  "config": best, "frozen_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                  "model_sha256": model_hash(MODELS / "concept_lr.joblib")}
    if t_p90 is None:
        thresholds["t_P90"] = float(np.max(p_oof))
    write_json(MODELS / "thresholds.json", thresholds)
    logger.info(f"thresholds frozen: {thresholds}")

    # ---------------- ablations + HGB (same CV) + save the sensitivity models needed by s7
    comp: dict = {}
    oofs = {"primary": p_oof}
    for name, use in ABLATIONS.items():
        if "ctx" in use and fs.ctx is None:
            continue
        b, _, p = tune_lr(Xtr, ytr, gtr, blocks, use)
        tt, _ = best_f1_threshold(ytr, p)
        m = make_pipeline(blocks, use, pca=b["pca"], C=b["C"], class_weight=b["class_weight"]).fit(Xtr, ytr)
        comp[name] = {"config": b, "t_F1": tt, "model": m, "use": use}
        oofs[name] = p
        logger.info(f"ablation {name}: {b}")
    hb, hgrid, hp = tune_hgb(Xtr, ytr, gtr, blocks, FULL)
    ht, _ = best_f1_threshold(ytr, hp)
    hm = make_pipeline(blocks, FULL, pca=64, model="hgb", hgb={k: hb[k] for k in ("learning_rate", "max_leaf_nodes", "l2_regularization", "max_iter", "early_stopping")}).fit(Xtr, ytr)
    comp["hgb"] = {"config": hb, "t_F1": ht, "model": hm, "use": FULL}
    oofs["hgb"] = hp
    joblib.dump({"pipeline": comp["no_termhood"]["model"], "blocks": blocks, "use": comp["no_termhood"]["use"],
                 "config": comp["no_termhood"]["config"], "t_F1": comp["no_termhood"]["t_F1"]}, MODELS / "concept_lr_notermhood.joblib")
    # best CV comparison model (F4 sensitivity column): highest OOF best-threshold F1 among comparisons
    cv_scores = {k: best_f1_threshold(ytr, v)[1] for k, v in oofs.items() if k != "primary" and k != "full_plus_context"}
    best_comp = max(cv_scores, key=cv_scores.get)
    joblib.dump({"pipeline": comp[best_comp]["model"], "blocks": blocks, "use": comp[best_comp]["use"], "name": best_comp,
                 "t_F1": comp[best_comp]["t_F1"]}, MODELS / "concept_best_comparison.joblib")
    write_json(MODELS / "thresholds_comparisons.json", {k: {"t_F1": v["t_F1"], "config": v["config"]} for k, v in comp.items()} |
               {"best_cv_comparison": best_comp, "cv_best_thr_f1": cv_scores})

    # ---------------- baselines tuned on train OOF
    th_idx = names.index("th_cvalue")
    cv_tr = Xtr[:, th_idx]
    t_cv, _ = best_f1_threshold(ytr, cv_tr)

    # ================= TEST (opened once, after everything above is frozen)
    p_te = primary.predict_proba(Xte)[:, 1]
    h_te = (p_te >= t_f1).astype(int)
    h_te_strict = (p_te >= thresholds["t_P90"]).astype(int)
    idx = boot_idx(len(yte))
    res: dict = {"n_train": len(ytr), "n_test": len(yte), "train_label_counts": dict(Counter(r["output"] for r in tr_rows)),
                 "test_label_counts": dict(Counter(r["output"] for r in te_rows)), "dropped_unresolved": n_unres,
                 "train_test_key_overlap": len(overlap), "primary_config": best, "thresholds": thresholds,
                 "cv_grid_primary": grid, "hgb_grid": hgrid}
    res["test_primary_tF1"] = boot_metrics(yte, p_te, h_te, idx)
    res["test_primary_tP90"] = boot_metrics(yte, p_te, h_te_strict, idx)
    res["confusion_primary_tF1"] = confusion_matrix(yte, h_te).tolist()
    # comparisons
    res["test_comparisons"] = {}
    for name, c in comp.items():
        pc = c["model"].predict_proba(Xte)[:, 1]
        hc = (pc >= c["t_F1"]).astype(int)
        res["test_comparisons"][name] = {"metrics": boot_metrics(yte, pc, hc, idx), "config": c["config"],
                                         "paired_primary_minus_this": paired_diff(yte, p_te, h_te, pc, hc, idx)}
    # baselines
    maj = int(ytr.mean() >= 0.5)
    base = {"majority_class": (np.full(len(yte), 0.5), np.full(len(yte), maj)),
            "cvalue_threshold": (Xte[:, th_idx], (Xte[:, th_idx] >= t_cv).astype(int)),
            "llm_label_A": (None, np.array([r.get("metadata_label_A") == "CONCEPT" for r in te_rows], dtype=int)),
            "llm_label_B": (None, np.array([r.get("metadata_label_B") == "CONCEPT" for r in te_rows], dtype=int))}
    res["test_baselines"] = {}
    for name, (pb, hb_) in base.items():
        score = pb if pb is not None else hb_.astype(float)
        m = boot_metrics(yte, score if name != "majority_class" else None, hb_, idx)
        if name == "majority_class":
            m["auc"] = {"point": 0.5, "ci95": [0.5, 0.5]}
        res["test_baselines"][name] = {"metrics": m, "paired_primary_minus_this": paired_diff(yte, p_te, h_te, score, hb_, idx)}
    res["test_baselines"]["cvalue_threshold"]["t"] = t_cv
    res["baseline_note"] = ("LLM labels A (gemini-2.5-flash-lite) and B (gpt-4.1-nano) helped create the silver labels "
                            "(consensus or haiku adjudication of A!=B), so the A/B baselines are optimistic/circular.")
    # reliability curve
    fr, mp_ = calibration_curve(yte, p_te, n_bins=10, strategy="uniform")
    res["reliability_curve"] = {"mean_predicted": mp_.tolist(), "fraction_positive": fr.tolist()}
    plt.figure(figsize=(4.2, 4))
    plt.plot([0, 1], [0, 1], "k--", lw=1)
    plt.plot(mp_, fr, "o-", color="#1f77b4", label="primary LR (D2 test)")
    plt.xlabel("mean predicted P(CONCEPT)")
    plt.ylabel("observed CONCEPT share")
    plt.legend(loc="upper left", fontsize=8)
    plt.tight_layout()
    plt.savefig(RESULTS / "fig_reliability.png", dpi=150)
    plt.close()
    # per macro-domain + silver_gold_200
    res["per_macro_domain"] = {}
    for dom in sorted({r.get("metadata_macro_domain") for r in te_rows}, key=str):
        ii = np.array([r.get("metadata_macro_domain") == dom for r in te_rows])
        if ii.sum() >= 5:
            res["per_macro_domain"][str(dom)] = point_metrics(yte[ii], p_te[ii] if len(set(yte[ii])) > 1 else None, h_te[ii])
    sg = np.array([bool(r.get("metadata_silver_gold_200")) for r in te_rows])
    if sg.sum():
        y_adj = np.array([r.get("metadata_label_adj") == "CONCEPT" for r in te_rows], dtype=int)
        res["silver_gold_200"] = {"vs_final_silver": point_metrics(yte[sg], p_te[sg], h_te[sg]),
                                  "vs_adjudicator_label": point_metrics(y_adj[sg], p_te[sg], h_te[sg]),
                                  "llmA_vs_adjudicator_label": point_metrics(
                                      y_adj[sg], None, np.array([r.get("metadata_label_A") == "CONCEPT" for r in te_rows], dtype=int)[sg])}
    # ---------------- SECONDARY 4-class
    lab3 = {"CONCEPT": 0, "NOT_CONCEPT": 1, "TOO_GENERIC": 2}
    y3tr = np.array([lab3.get(r["output"], 1) for r in tr_rows])
    y3te = np.array([lab3.get(r["output"], 1) for r in te_rows])
    m3 = make_pipeline(blocks, FULL, pca=best["pca"], C=best["C"], class_weight="balanced").fit(Xtr, y3tr)
    pr3 = m3.predict(Xte)
    res["secondary_3class"] = {"macro_f1": float(f1_score(y3te, pr3, average="macro")),
                               "per_class_f1": dict(zip(lab3, f1_score(y3te, pr3, average=None, labels=[0, 1, 2]).tolist())),
                               "confusion": confusion_matrix(y3te, pr3, labels=[0, 1, 2]).tolist(), "labels": list(lab3),
                               "note": "the plan names this '4-class'; VARIANT_OF has 2 train items and 0 test items, so 3 classes"}

    # ---------------- SECONDARY: train on D2-train + D4a-train
    d4a = read_json(DATA / "d4a.json")
    te_keys = {normalise(r["key"]) for r in te_rows}
    d4tr = [r for r in d4a if r["metadata_fold"] == "train" and normalise(r["phrase"]) not in te_keys]
    rng = np.random.default_rng(SEED)
    pos = [r for r in d4tr if r["output"] == "CONCEPT"]
    neg = [r for r in d4tr if r["output"] != "CONCEPT"]
    share = ytr.mean()
    n_neg = min(len(neg), int(round(len(pos) * (1 - share) / share)))
    neg = [neg[i] for i in rng.choice(len(neg), n_neg, replace=False)]
    d4sel = pos + neg
    if MINI:
        d4sel = d4sel[:200]
    items_d4 = [{"ns": "d4a", "id": r["phrase"], "th_qid": f"d4a:{r['phrase']}", "text": r["phrase"], "ctx_key": None} for r in d4sel]
    Xd4, _, _ = fs.build(items_d4)
    yd4 = np.array([r["output"] == "CONCEPT" for r in d4sel], dtype=int)
    m_aug = make_pipeline(blocks, FULL, pca=best["pca"], C=best["C"], class_weight=best["class_weight"]).fit(
        np.concatenate([Xtr, Xd4]), np.concatenate([ytr, yd4]))
    p_aug_oof = oof_proba(lambda: make_pipeline(blocks, FULL, pca=best["pca"], C=best["C"], class_weight=best["class_weight"]),
                          Xtr, ytr, gtr)  # threshold from D2-train OOF of the same config
    t_aug = best_f1_threshold(ytr, p_aug_oof)[0]
    pa = m_aug.predict_proba(Xte)[:, 1]
    res["secondary_train_plus_d4a"] = {"n_d4a_added": len(d4sel), "d4a_pos": int(yd4.sum()),
                                       "metrics": boot_metrics(yte, pa, (pa >= t_aug).astype(int), idx),
                                       "paired_primary_minus_this": paired_diff(yte, p_te, h_te, pa, (pa >= t_aug).astype(int), idx)}

    # ================= HUMAN ANCHORS
    d2_train_keys = {normalise(r["key"]) for r in tr_rows}

    def anchor_items(rows):
        return [{"ns": "d4a", "id": r["phrase"], "th_qid": f"d4a:{r['phrase']}", "text": r["phrase"], "ctx_key": None} for r in rows]

    # E1: the 300 rows of DS4's LLM anchor check
    e1 = [r for r in d4a if r.get("metadata_in_llm_anchor_check")]
    ha: dict = {"note": ("These are the only human-labelled numbers in this artifact; the construct is keyphrase/entity span "
                         "(SemEval-2017 Task 10, SciERC), not emerging-concept term.")}
    if e1:
        X1, _, _ = fs.build(anchor_items(e1))
        y1 = np.array([r["output"] == "CONCEPT" for r in e1], dtype=int)
        p1 = primary.predict_proba(X1)[:, 1]
        h1 = (p1 >= t_f1).astype(int)
        i1 = boot_idx(len(y1))
        a1 = np.array([r.get("metadata_llm_label_A") == "CONCEPT" for r in e1], dtype=int)
        b1 = np.array([r.get("metadata_llm_label_B") == "CONCEPT" for r in e1], dtype=int)
        ha["E1_llm_anchor_rows"] = {"n": len(e1), "primary": boot_metrics(y1, p1, h1, i1),
                                    "llm_A_same_rows": point_metrics(y1, None, a1), "llm_B_same_rows": point_metrics(y1, None, b1),
                                    "llm_A_reported_DS4": {"precision": 0.7917, "recall": 0.76, "f1": 0.7755, "kappa": 0.56},
                                    "paired_primary_minus_A": paired_diff(y1, p1, h1, a1.astype(float), a1, i1),
                                    "per_source": {}}
        for src in sorted({r["metadata_source"] for r in e1}):
            ii = np.array([r["metadata_source"] == src for r in e1])
            ha["E1_llm_anchor_rows"]["per_source"][src] = {"primary": point_metrics(y1[ii], p1[ii], h1[ii]),
                                                           "llm_A": point_metrics(y1[ii], None, a1[ii])}
    # E2: all test-fold anchor rows, negatives subsampled to the D2-test positive share, 20 seeds x bootstrap
    test_folds = sorted({r["metadata_fold"] for r in d4a if r["metadata_fold"] not in ("train",)})
    e2 = [r for r in d4a if r["metadata_fold"] in test_folds and "test" in r["metadata_fold"]
          and normalise(r["phrase"]) not in d2_train_keys]
    if MINI:
        e2 = e2[:300]
    ha["E2_folds_used"] = sorted({r["metadata_fold"] for r in e2})
    if e2:
        X2, _, _ = fs.build(anchor_items(e2))
        y2 = np.array([r["output"] == "CONCEPT" for r in e2], dtype=int)
        p2 = primary.predict_proba(X2)[:, 1]
        h2 = (p2 >= t_f1).astype(int)
        ntok = np.array([len((normalise(r["phrase"]) or "").split()) for r in e2])
        srcs = np.array([r["metadata_source"] for r in e2])
        target_share = float(yte.mean())

        def e2_eval(mask: np.ndarray) -> dict:
            pos_i = np.where(mask & (y2 == 1))[0]
            neg_i = np.where(mask & (y2 == 0))[0]
            if len(pos_i) < 5 or len(neg_i) < 5:
                return {"n_pos": int(len(pos_i)), "n_neg": int(len(neg_i)), "skipped": True}
            n_neg = int(round(len(pos_i) * (1 - target_share) / target_share))
            vals = {k: [] for k in ("precision", "recall", "f1", "auc")}
            for s in range(20):
                r_ = np.random.default_rng(SEED + s)
                if n_neg <= len(neg_i):
                    sel = np.concatenate([pos_i, r_.choice(neg_i, n_neg, replace=False)])
                else:
                    n_pos = int(round(len(neg_i) * target_share / (1 - target_share)))
                    sel = np.concatenate([r_.choice(pos_i, n_pos, replace=False), neg_i])
                bi = r_.integers(0, len(sel), size=(100, len(sel)))
                for b in bi:
                    ss = sel[b]
                    P, R, F = _prf(y2[ss], h2[ss])
                    vals["precision"].append(P)
                    vals["recall"].append(R)
                    vals["f1"].append(F)
                    from sklearn.metrics import roc_auc_score
                    vals["auc"].append(roc_auc_score(y2[ss], p2[ss]))
            return {"n_pos": int(len(pos_i)), "n_neg_available": int(len(neg_i)),
                    **{k: {"mean": float(np.mean(v)), "ci95": [float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))]}
                       for k, v in vals.items()}}

        allm = np.ones(len(e2), dtype=bool)
        ha["E2_test_anchor_rows"] = {"n_rows": len(e2), "positive_share_target": target_share,
                                     "all": e2_eval(allm), "len_1_6_tokens": e2_eval((ntok >= 1) & (ntok <= 6)),
                                     "per_source": {s: {"all": e2_eval(srcs == s), "len_1_6_tokens": e2_eval((srcs == s) & (ntok >= 1) & (ntok <= 6))}
                                                    for s in sorted(set(srcs))}}
    res["human_anchors"] = ha
    res["runtime_s"] = time.time() - t0
    res["feature_names"] = names[:len(blocks["lex"]) + len(blocks["th"])]
    write_json(RESULTS / "classifier_results.json", res)
    # per-item test predictions (for method_out.json)
    write_json(RESULTS / "d2_test_predictions.json", [
        {"key": r["key"], "silver": r["output"], "y": int(y), "p": float(p), "accept_tF1": int(h), "accept_tP90": int(hs),
         "label_A": r.get("metadata_label_A"), "label_B": r.get("metadata_label_B"), "macro_domain": r.get("metadata_macro_domain")}
        for r, y, p, h, hs in zip(te_rows, yte, p_te, h_te, h_te_strict)], indent=None)
    logger.info(f"TEST primary: F1 {res['test_primary_tF1']['f1']} AUC {res['test_primary_tF1'].get('auc')}")
    logger.info(f"done in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
