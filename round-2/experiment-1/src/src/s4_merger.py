#!/usr/bin/env python3
"""STEP 4: pairwise variant merger.
Train on D3 train pairs + MeSH synonym pairs (train_eligible + working_list), with a leakage guard against every
heldout_mesh string/descriptor. PRIMARY: L2 logistic regression (class_weight balanced, C tuned by grouped 5-fold CV),
D3 pairs carrying 30% of the training weight. Comparisons: HGB, unweighted LR. Baselines: normalised-equal, MiniLM
cosine >= t, rapidfuzz token_set_ratio >= 85. Thresholds p_merge (OOF precision >= 0.90 on BOTH the D3 and MeSH OOF
subsets; the max of the two) and p_merge_strict (0.97). Test: D3 test and heldout_mesh pairs; cluster test with
average-linkage agglomerative clustering + B-cubed on heldout_mesh descriptor terms."""
from __future__ import annotations

import itertools
import time
from collections import Counter, defaultdict

import joblib
import numpy as np
from loguru import logger
from scipy.cluster.hierarchy import fcluster, linkage
from scipy.spatial.distance import squareform
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score, roc_auc_score
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from clfdata import _prf, best_f1_threshold, boot_idx, boot_metrics, paired_diff, precision_threshold
from common import DATA, MINI, MODELS, RESULTS, SEED, normalise, read_json, set_limits, setup_logging, sha256_file, write_json
from mergelib import PAIR_NAMES, PairFeaturizer

C_GRID = [0.01, 0.03, 0.1, 0.3, 1, 3, 10]
PRED: dict = {}


def lr_model(C: float) -> Pipeline:
    return Pipeline([("sc", StandardScaler()), ("clf", LogisticRegression(C=C, class_weight="balanced", max_iter=5000))])


def hgb_model(hp: dict) -> HistGradientBoostingClassifier:
    return HistGradientBoostingClassifier(random_state=SEED, class_weight="balanced", **hp)


def oof(make, X, y, w, groups, k=5) -> np.ndarray:
    p = np.zeros(len(y))
    for tr, va in GroupKFold(n_splits=k).split(X, y, groups):
        m = make()
        if isinstance(m, Pipeline):
            m.fit(X[tr], y[tr], clf__sample_weight=w[tr])
        else:
            m.fit(X[tr], y[tr], sample_weight=w[tr])
        p[va] = m.predict_proba(X[va])[:, 1]
    return p


def fit(make, X, y, w):
    m = make()
    if isinstance(m, Pipeline):
        m.fit(X, y, clf__sample_weight=w)
    else:
        m.fit(X, y, sample_weight=w)
    return m


def bcubed(pred: np.ndarray, gold: np.ndarray) -> dict:
    P, R = [], []
    for i in range(len(pred)):
        same_pred = pred == pred[i]
        same_gold = gold == gold[i]
        inter = float((same_pred & same_gold).sum())
        P.append(inter / same_pred.sum())
        R.append(inter / same_gold.sum())
    p, r = float(np.mean(P)), float(np.mean(R))
    return {"precision": p, "recall": r, "f1": 2 * p * r / (p + r) if p + r else 0.0,
            "n_items": int(len(pred)), "n_pred_clusters": int(len(set(pred))), "n_gold_clusters": int(len(set(gold)))}


@logger.catch(reraise=True)
def main() -> None:
    setup_logging("s4_merger")
    set_limits(40)
    t0 = time.time()
    d3 = read_json(DATA / "d3.json")
    mp = read_json(DATA / "mesh_pairs.json")
    hm = read_json(DATA / "heldout_mesh_concepts.json")
    held = [r for r in mp if r["metadata_fold"] == "heldout_mesh"]
    # ---------------- leakage guard
    H = set()
    for r in held:
        H |= {normalise(r["term_a"]), normalise(r["term_b"])}
    for c in hm:
        H |= {normalise(x) for x in [c["preferred_term"]] + c["surface_forms"] + c["acronyms"]}
    H.discard("")
    held_ui = {r["metadata_descriptor_ui"] for r in held} | {r["metadata_descriptor_ui_b"] for r in held} | {c["descriptor_ui"] for c in hm}
    mtr_all = [r for r in mp if r["metadata_fold"] in ("train_eligible", "working_list")]
    mtr = [r for r in mtr_all if normalise(r["term_a"]) not in H and normalise(r["term_b"]) not in H]
    n_drop_str = len(mtr_all) - len(mtr)
    mtr2 = [r for r in mtr if r["metadata_descriptor_ui"] not in held_ui and r["metadata_descriptor_ui_b"] not in held_ui]
    n_drop_ui = len(mtr) - len(mtr2)
    mtr = mtr2
    assert not ({r["metadata_descriptor_ui"] for r in mtr} | {r["metadata_descriptor_ui_b"] for r in mtr}) & held_ui
    d3tr = [r for r in d3 if r["metadata_fold"] == "train"]
    d3te = [r for r in d3 if r["metadata_fold"] == "test"]
    n_d3_drop = sum(1 for r in d3tr if normalise(r["phrase_1"]) in H or normalise(r["phrase_2"]) in H)
    d3tr = [r for r in d3tr if normalise(r["phrase_1"]) not in H and normalise(r["phrase_2"]) not in H]
    if MINI:  # seeded random samples (the files are ordered by label)
        import random
        rs = random.Random(SEED)
        mtr, held, d3tr, d3te = rs.sample(mtr, 400), rs.sample(held, 150), rs.sample(d3tr, 150), rs.sample(d3te, 60)
    logger.info(f"MeSH train {len(mtr)} (dropped {n_drop_str} by string, {n_drop_ui} by descriptor), D3 train {len(d3tr)} "
                f"(dropped {n_d3_drop}), D3 test {len(d3te)}, heldout_mesh test {len(held)}")

    pf = PairFeaturizer()
    tr_pairs = [(r["phrase_1"], r["phrase_2"]) for r in d3tr] + [(r["term_a"], r["term_b"]) for r in mtr]
    Xtr = pf.features(tr_pairs)
    ytr = np.array([r["output"] == "SAME" for r in d3tr] + [r["y"] == 1 for r in mtr], dtype=int)
    is_d3 = np.array([True] * len(d3tr) + [False] * len(mtr))
    groups = np.array([f"d3:{r.get('metadata_cluster_1') or r.get('metadata_key_1')}" for r in d3tr] +
                      [f"mesh:{r['metadata_descriptor_ui']}" for r in mtr])
    # D3 carries 30% of the total training weight
    w = np.where(is_d3, 0.30 / is_d3.sum(), 0.70 / (~is_d3).sum()) * len(ytr)
    w_unw = np.ones(len(ytr))
    logger.info(f"train pairs {len(ytr)} (SAME {ytr.sum()}), features {Xtr.shape} ({time.time() - t0:.0f}s)")

    # ---------------- tuning
    grid = []
    best = None
    for C in C_GRID:
        p = oof(lambda C=C: lr_model(C), Xtr, ytr, w, groups)
        f_d3 = best_f1_threshold(ytr[is_d3], p[is_d3])[1]
        auc = roc_auc_score(ytr, p)
        r = {"C": C, "oof_auc_all": auc, "oof_auc_mesh": roc_auc_score(ytr[~is_d3], p[~is_d3]),
             "oof_auc_d3": roc_auc_score(ytr[is_d3], p[is_d3]), "oof_best_f1_d3": f_d3}
        grid.append(r)
        if best is None or auc > best[0]["oof_auc_all"]:
            best = (r, p)
    cfg, p_oof = best
    logger.info(f"merger LR best {cfg}")
    t_d3 = precision_threshold(ytr[is_d3], p_oof[is_d3], 0.90)
    t_me = precision_threshold(ytr[~is_d3], p_oof[~is_d3], 0.90)
    t_d3s = precision_threshold(ytr[is_d3], p_oof[is_d3], 0.97)
    t_mes = precision_threshold(ytr[~is_d3], p_oof[~is_d3], 0.97)
    p_merge = max(t for t in (t_d3, t_me, 0.5) if t is not None)
    p_merge_strict = max([t for t in (t_d3s, t_mes) if t is not None] + [p_merge])
    primary = fit(lambda: lr_model(cfg["C"]), Xtr, ytr, w)
    # comparisons
    p_unw = oof(lambda: lr_model(cfg["C"]), Xtr, ytr, w_unw, groups)
    unw = fit(lambda: lr_model(cfg["C"]), Xtr, ytr, w_unw)
    hbest = None
    hgrid = []
    for lr_, leaves, l2 in itertools.product([0.05, 0.1], [15, 31], [0.0, 1.0]):
        hp = {"learning_rate": lr_, "max_leaf_nodes": leaves, "l2_regularization": l2, "max_iter": 300}
        p = oof(lambda hp=hp: hgb_model(hp), Xtr, ytr, w, groups)
        r = {**hp, "oof_auc_all": roc_auc_score(ytr, p), "oof_best_f1_d3": best_f1_threshold(ytr[is_d3], p[is_d3])[1]}
        hgrid.append(r)
        if hbest is None or r["oof_auc_all"] > hbest[0]["oof_auc_all"]:
            hbest = (r, p)
    hcfg, p_hgb = hbest
    hgb = fit(lambda: hgb_model({k: hcfg[k] for k in ("learning_rate", "max_leaf_nodes", "l2_regularization", "max_iter")}), Xtr, ytr, w)
    th_hgb = max(t for t in (precision_threshold(ytr[is_d3], p_hgb[is_d3], 0.90), precision_threshold(ytr[~is_d3], p_hgb[~is_d3], 0.90), 0.5) if t is not None)
    th_unw = max(t for t in (precision_threshold(ytr[is_d3], p_unw[is_d3], 0.90), precision_threshold(ytr[~is_d3], p_unw[~is_d3], 0.90), 0.5) if t is not None)
    # baselines tuned on train
    ci = PAIR_NAMES.index("cos_minilm")
    t_cos = best_f1_threshold(ytr, Xtr[:, ci])[0]
    # F5 rule (fixed before test): frame merge uses the model with the higher D3-OOF F1 (primary vs D3-only retrain) if
    # the primary fails on D3 test; the D3-only variant is trained now so the choice needs no refit later.
    d3only = fit(lambda: lr_model(cfg["C"]), Xtr[is_d3], ytr[is_d3], np.ones(is_d3.sum()))
    p_d3only_oof = oof(lambda: lr_model(cfg["C"]), Xtr[is_d3], ytr[is_d3], np.ones(is_d3.sum()), groups[is_d3])
    th_d3only = precision_threshold(ytr[is_d3], p_d3only_oof, 0.90) or 0.5
    oof_f1_d3 = {"primary": _prf(ytr[is_d3], (p_oof[is_d3] >= p_merge).astype(int))[2],
                 "d3_only": _prf(ytr[is_d3], (p_d3only_oof >= th_d3only).astype(int))[2]}
    joblib.dump({"model": primary, "names": PAIR_NAMES, "config": cfg}, MODELS / "merger_lr.joblib")
    joblib.dump({"model": d3only, "names": PAIR_NAMES, "threshold": th_d3only}, MODELS / "merger_lr_d3only.joblib")
    thr = {"p_merge": p_merge, "p_merge_strict": p_merge_strict, "components": {"d3_p90": t_d3, "mesh_p90": t_me,
           "d3_p97": t_d3s, "mesh_p97": t_mes}, "config": cfg, "model_sha256": sha256_file(MODELS / "merger_lr.joblib"),
           "d3only_threshold": th_d3only, "oof_f1_d3_at_threshold": oof_f1_d3,
           "frozen_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    write_json(MODELS / "merger_thresholds.json", thr)
    logger.info(f"merger thresholds {thr}")

    # ================= TEST
    res: dict = {"n_train_pairs": int(len(ytr)), "n_train_d3": int(is_d3.sum()), "n_train_mesh": int((~is_d3).sum()),
                 "leakage_guard": {"H_strings": len(H), "mesh_train_dropped_by_string": n_drop_str,
                                   "mesh_train_dropped_by_descriptor": n_drop_ui, "d3_train_dropped": n_d3_drop,
                                   "descriptor_overlap_after_guard": 0},
                 "lr_grid": grid, "hgb_grid": hgrid, "thresholds": thr, "hgb_threshold": th_hgb, "unweighted_threshold": th_unw,
                 "cos_minilm_threshold": t_cos, "feature_names": PAIR_NAMES,
                 "lr_coefficients": dict(zip(PAIR_NAMES, primary.named_steps["clf"].coef_[0].tolist())), "test": {}}
    sets = {"d3_test": ([(r["phrase_1"], r["phrase_2"]) for r in d3te], np.array([r["output"] == "SAME" for r in d3te], dtype=int),
                        [r["metadata_source"].split("(")[0] for r in d3te]),
            "heldout_mesh": ([(r["term_a"], r["term_b"]) for r in held], np.array([r["y"] for r in held], dtype=int),
                             [r["metadata_pair_type"] for r in held])}
    for name, (pairs, y, strata) in sets.items():
        X = pf.features(pairs)
        idx = boot_idx(len(y))
        p = primary.predict_proba(X)[:, 1]
        h = (p >= p_merge).astype(int)
        out = {"primary": boot_metrics(y, p, h, idx, keys=("precision", "recall", "f1", "accuracy", "auc", "auprc", "brier", "balanced_accuracy")),
               "primary_strict": boot_metrics(y, p, (p >= p_merge_strict).astype(int), idx, keys=("precision", "recall", "f1", "accuracy", "auc", "auprc", "brier", "balanced_accuracy"))}
        comps = {"hgb": (hgb.predict_proba(X)[:, 1], th_hgb), "lr_unweighted": (unw.predict_proba(X)[:, 1], th_unw),
                 "lr_d3_only": (d3only.predict_proba(X)[:, 1], th_d3only)}
        for cn, (pc, tc) in comps.items():
            hc = (pc >= tc).astype(int)
            out[cn] = {"metrics": boot_metrics(y, pc, hc, idx, keys=("precision", "recall", "f1", "auc")),
                       "paired_primary_minus_this": paired_diff(y, p, h, pc, hc, idx)}
        ne = X[:, PAIR_NAMES.index("norm_equal")]
        cm = X[:, ci]
        ts = X[:, PAIR_NAMES.index("fz_token_set")]
        bases = {"normalised_equal": (ne, (ne >= 0.5).astype(int)), "cos_minilm_ge_t": (cm, (cm >= t_cos).astype(int)),
                 "token_set_ratio_ge_85": (ts, (ts >= 0.85).astype(int))}
        for bn, (sc, hb) in bases.items():
            out[f"baseline_{bn}"] = {"metrics": boot_metrics(y, sc, hb, idx, keys=("precision", "recall", "f1", "auc")),
                                     "paired_primary_minus_this": paired_diff(y, p, h, sc, hb, idx)}
        out["baseline_note"] = "D3 near-duplicate items were built with token_set_ratio >= 85, so that baseline is partly circular on D3."
        out["by_stratum"] = {}
        for s in sorted(set(strata)):
            ii = np.array([x == s for x in strata])
            P, R, F = _prf(y[ii], h[ii])
            out["by_stratum"][s] = {"n": int(ii.sum()), "n_same": int(y[ii].sum()), "precision": P, "recall": R, "f1": F,
                                    "accuracy": float((y[ii] == h[ii]).mean()),
                                    "auc": float(roc_auc_score(y[ii], p[ii])) if len(set(y[ii])) > 1 else None}
        res["test"][name] = out
        PRED[name] = [{"a": a, "b": b, "y": int(yy), "p": round(float(pp), 5), "merge": int(hh), "stratum": st,
                       "norm_equal": int(n_ >= 0.5), "cos_minilm": round(float(c_), 4), "cos_ge_t": int(c_ >= t_cos),
                       "token_set": round(float(t_), 4)}
                      for (a, b), yy, pp, hh, st, n_, c_, t_ in zip(pairs, y, p, h, strata, ne, cm, ts)]
        logger.info(f"{name}: F1 {out['primary']['f1']} AUC {out['primary'].get('auc')}")

    # ---------------- cluster test (heldout_mesh descriptor terms)
    term_ui: dict[str, str] = {}
    conflicts = 0
    for r in held:
        for t, ui in ((r["term_a"], r["metadata_descriptor_ui"]), (r["term_b"], r["metadata_descriptor_ui_b"])):
            k = normalise(t)
            if k in term_ui and term_ui[k][1] != ui:
                conflicts += 1
                continue
            term_ui.setdefault(k, (t, ui))
    for c in hm:
        for t in [c["preferred_term"]] + c["surface_forms"]:
            k = normalise(t)
            if k and k not in term_ui:
                term_ui[k] = (t, c["descriptor_ui"])
    terms = [v[0] for v in term_ui.values()]
    gold = np.array([v[1] for v in term_ui.values()])
    n = len(terms)
    iu = np.triu_indices(n, 1)
    pairs = [(terms[i], terms[j]) for i, j in zip(*iu)]
    logger.info(f"cluster test: {n} terms, {len(pairs)} pairs")
    Xc = pf.features(pairs)
    pc = primary.predict_proba(Xc)[:, 1]
    D = np.zeros((n, n))
    D[iu] = 1 - pc
    D = D + D.T
    Z = linkage(squareform(D, checks=False), method="average")
    res["cluster_test"] = {"n_terms": n, "n_descriptors": int(len(set(gold))), "string_conflicts_dropped": conflicts}
    for nm, t in (("p_merge", p_merge), ("p_merge_strict", p_merge_strict)):
        lab = fcluster(Z, t=1 - t, criterion="distance")
        res["cluster_test"][nm] = bcubed(lab, gold)
    # surface baseline clustering: normalised-equality components
    ne_lab = np.array([normalise(t) for t in terms])
    res["cluster_test"]["baseline_normalised_equal"] = bcubed(ne_lab, gold)
    lab_c = fcluster(linkage(squareform(np.where(np.eye(n) == 1, 0, 1 - _cos_matrix(pf, terms)), checks=False), method="average"),
                     t=1 - t_cos, criterion="distance")
    res["cluster_test"]["baseline_cos_minilm"] = bcubed(lab_c, gold)
    res["runtime_s"] = time.time() - t0
    write_json(RESULTS / "merger_results.json", res)
    write_json(RESULTS / "merger_test_predictions.json", PRED, indent=None)
    logger.info(f"cluster test {res['cluster_test']}")
    logger.info(f"done in {time.time() - t0:.0f}s")


def _cos_matrix(pf: PairFeaturizer, terms: list[str]) -> np.ndarray:
    from featlib import emb_text
    E = pf.mini.get([emb_text(t) for t in terms])
    S = np.clip(E @ E.T, -1, 1)
    return S


if __name__ == "__main__":
    main()
