#!/usr/bin/env python3
"""PART 1: NUMBERS OF RECORD — every value the blocking review named, RECOMPUTED from item/row-level files where they exist,
with provenance (run-root-relative path + key), estimator, n, CI, and a drift flag against iter_3/gen_strat/current_report.md.

Outputs: results/record_of_numbers.{json,csv,md}, results/drift_flags.csv
"""
from __future__ import annotations

import glob
import json
import math
import re

from pathlib import Path

import numpy as np
import pandas as pd
from loguru import logger
from sklearn.metrics import average_precision_score, cohen_kappa_score, roc_auc_score

import common as K

FLAGS = ["OK", "DRIFT_VALUE", "WRONG_ESTIMATOR", "WRONG_UNITS", "WRONG_DEFINITION", "WRONG_N", "MISSING_IN_REPORT", "NOT_REDERIVABLE"]
REPORT_LINES = K.REPORT.read_text().splitlines()
ROWS: list[dict] = []


# ------------------------------------------------------------------ row helpers
def add(id_: str, block: str, claim: str, value, *, src, key: str, estimator: str, unit: str = "", n=None, ci=None,
        recomputed: bool = True, method: str = "", in_summary: bool | None = None, rx: str | None = None, scale: float = 1.0,
        mismatch: str = "DRIFT_VALUE", force: str | None = None, alt: dict | None = None, note: str = "", kw: list | None = None,
        auto: bool = False) -> dict:
    """rx: regex with ONE numeric group locating the report's number for this claim; force: flag applied when rx matches
    (label/definition errors that do not show up as a value difference); alt: {flag: value} explanations tried on mismatch."""
    r = dict(id=id_, block=block, claim=claim, value=None if value is None else float(value),
             ci_lo=None if ci is None else ci[0], ci_hi=None if ci is None else ci[1], n=n, unit=unit, estimator=estimator,
             source_path=K.rel(src) if src is not None else None, source_key=key, recomputed=bool(recomputed),
             recompute_method=method, reported_in_artifact_summary=in_summary, report_value=None, report_line=None,
             agrees=None, flag=None, note=note, _rx=rx, _scale=scale, _mismatch=mismatch, _force=force, _alt=alt or {},
             _kw=kw or [], _auto=auto)
    ROWS.append(r)
    return r


def _num(s: str) -> float:
    return float(s.replace(",", "").replace("~", "").replace("+", ""))


def _tol(s: str) -> float:
    s = s.replace(",", "").replace("+", "").replace("-", "")
    return 0.5 * 10 ** (-(len(s.split(".")[1]) if "." in s else 0))


def match_report(r: dict) -> None:
    hit = None
    if r["_rx"]:
        for i, line in enumerate(REPORT_LINES):
            m = re.search(r["_rx"], line)
            if m:
                hit = (i + 1, m.group(1).rstrip(".") if m.groups() and m.group(1) else None)
                break
    elif r["_auto"] and r["value"] is not None:
        v = r["value"] * r["_scale"]
        for fmt in ("{:.3f}", "{:.2f}", "{:.1f}"):
            s = fmt.format(v)
            for i, line in enumerate(REPORT_LINES):
                if re.search(r"(?<![0-9.])" + re.escape(s) + r"(?![0-9])", line) and (not r["_kw"] or any(k.lower() in line.lower() for k in r["_kw"])):
                    hit = (i + 1, s)
                    break
            if hit:
                break
    if hit is None:
        r["flag"] = "NOT_REDERIVABLE" if (not r["recomputed"] and r["value"] is None) else "MISSING_IN_REPORT"
        return
    r["report_line"], s = hit
    if s is None:  # regex locates a mislabelled sentence without a number
        r["flag"] = r["_force"] or "MISSING_IN_REPORT"
        return
    rv = _num(s)
    r["report_value"] = rv
    if r["value"] is None:
        r["agrees"] = False
        r["flag"] = "NOT_REDERIVABLE"
        return
    v = r["value"] * r["_scale"]
    r["agrees"] = bool(abs(rv - v) <= _tol(s) + 1e-12)
    if r["_force"]:
        r["flag"] = r["_force"]
    elif r["agrees"]:
        r["flag"] = "OK"
    else:
        r["flag"] = r["_mismatch"]
        for fl, av in r["_alt"].items():
            if av is not None and abs(rv - av * r["_scale"]) <= _tol(s) + 1e-12:
                r["flag"] = fl
                r["note"] = (r["note"] + f" Report value {s} equals the {fl} alternative ({av:.4g}).").strip()
                break


def boot_ci(fn, n: int, B: int = 2000, seed: int = 0) -> list[float]:
    rng = np.random.default_rng(seed)
    vals = [fn(rng.integers(0, n, n)) for _ in range(B)]
    return np.nanpercentile(np.array(vals, float), [2.5, 97.5]).tolist()


def prf(y: np.ndarray, yhat: np.ndarray) -> dict:
    tp, fp = int(((yhat == 1) & (y == 1)).sum()), int(((yhat == 1) & (y == 0)).sum())
    fn, tn = int(((yhat == 0) & (y == 1)).sum()), int(((yhat == 0) & (y == 0)).sum())
    p = tp / (tp + fp) if tp + fp else 0.0
    rc = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * p * rc / (p + rc) if p + rc else 0.0
    return dict(TP=tp, FP=fp, FN=fn, TN=tn, precision=p, recall=rc, f1=f1, accuracy=(tp + tn) / len(y),
                balanced_accuracy=0.5 * (rc + (tn / (tn + fp) if tn + fp else 0.0)),
                kappa=float(cohen_kappa_score(y, yhat)) if len(set(yhat)) > 1 or len(set(y)) > 1 else 0.0)


# ================================================================== B1 classifier
def b1() -> dict:
    src = K.E1 / "results/d2_test_predictions.json"
    cr_p = K.E1 / "results/classifier_results.json"
    items = K.load_json(src)
    cr = K.load_json(cr_p)
    y = np.array([it["y"] for it in items])
    p = np.array([it["p"] for it in items])
    tF1 = cr["thresholds"]["t_F1"]
    out = {}
    for tag, thr in (("tF1", tF1), ("t050", 0.5), ("tP90", cr["thresholds"]["t_P90"])):
        yhat = (p >= thr).astype(int)
        m = prf(y, yhat)
        cis = {k: boot_ci(lambda ii, k=k: prf(y[ii], yhat[ii])[k], len(y)) for k in ("precision", "recall", "f1", "accuracy", "kappa", "balanced_accuracy")}
        out[tag] = dict(m, ci=cis)
        pre = f"B1.clf.{tag}"
        est = f"L2 logistic classifier, frozen threshold {thr} on p (d2 test, item bootstrap B=2000)"
        tab = tag == "tF1"
        add(f"{pre}.confusion", "B1 classifier", f"Confusion matrix at threshold {thr} (TP/FP/FN/TN)", m["TP"], src=src, key="items[].y,p",
            estimator=est, unit="count", n=len(y), method="threshold p, count", note=f"TP={m['TP']} FP={m['FP']} FN={m['FN']} TN={m['TN']}")
        alt_p = {"WRONG_ESTIMATOR": out.get("tP90", {}).get("precision")} if tab else None
        add(f"{pre}.precision", "B1 classifier", f"Classifier precision at t={thr}", m["precision"], ci=cis["precision"], n=len(y), src=src,
            key="items[].y,p", estimator=est, unit="proportion", method="confusion matrix", in_summary=tab,
            rx=r"\| Precision \| ([0-9.]+) \|" if tab else None,
            note="Table 9 P/R/accuracy (0.812/0.824/0.843) are not reproduced at t_F1, t=0.5 or t_P90; the nearest known number is "
                 "the E2 human-anchor precision mean 0.813 (a different test set)." if tab else "")
        add(f"{pre}.recall", "B1 classifier", f"Classifier recall at t={thr}", m["recall"], ci=cis["recall"], n=len(y), src=src,
            key="items[].y,p", estimator=est, unit="proportion", method="confusion matrix", in_summary=tab,
            rx=r"\| Recall \| ([0-9.]+) \|" if tab else None)
        add(f"{pre}.accuracy", "B1 classifier", f"Classifier accuracy at t={thr}", m["accuracy"], ci=cis["accuracy"], n=len(y), src=src,
            key="items[].y,p", estimator=est, unit="proportion", method="confusion matrix", in_summary=tab,
            rx=r"\| Accuracy \| ([0-9.]+) \|" if tab else None)
        add(f"{pre}.f1", "B1 classifier", f"Classifier F1 at t={thr}", m["f1"], ci=cis["f1"], n=len(y), src=src, key="items[].y,p",
            estimator=est, unit="F1", method="confusion matrix", in_summary=tab, rx=r"\| F1 score \(binary: concept vs rest\) \| ([0-9.]+)" if tab else None)
        add(f"{pre}.kappa", "B1 classifier", f"Classifier Cohen's kappa vs silver labels at t={thr}", m["kappa"], ci=cis["kappa"], n=len(y),
            src=src, key="items[].y,p", estimator=est, unit="kappa", method="sklearn cohen_kappa_score")
        add(f"{pre}.balacc", "B1 classifier", f"Classifier balanced accuracy at t={thr}", m["balanced_accuracy"], ci=cis["balanced_accuracy"],
            n=len(y), src=src, key="items[].y,p", estimator=est, unit="proportion", method="confusion matrix")
    auc = roc_auc_score(y, p)
    ap = average_precision_score(y, p)
    add("B1.clf.auc", "B1 classifier", "Classifier ROC-AUC on D2 test", auc, ci=boot_ci(lambda ii: roc_auc_score(y[ii], p[ii]) if len(set(y[ii])) > 1 else np.nan, len(y)),
        n=len(y), src=src, key="items[].y,p", estimator="ROC-AUC of p (item bootstrap B=2000)", unit="AUC", method="sklearn roc_auc_score",
        in_summary=True, rx=r"\| ROC-AUC \| ([0-9.]+) \|")
    add("B1.clf.auprc", "B1 classifier", "Classifier AUPRC on D2 test", ap, n=len(y), src=src, key="items[].y,p", estimator="average precision",
        unit="AUPRC", method="sklearn average_precision_score")
    add("B1.clf.n_pos", "B1 classifier", "D2 test positives (CONCEPT)", int(y.sum()), n=len(y), src=src, key="items[].y", estimator="count", unit="count")
    # trivial baselines
    allpos = prf(y, np.ones_like(y))
    add("B1.base.all_positive_f1", "B1 classifier", "Majority-class (predict-all-CONCEPT) baseline F1; CONCEPT is the majority class",
        allpos["f1"], n=len(y), src=src, key="items[].y", estimator="predict-all-positive", unit="F1", method="confusion matrix",
        rx=r"majority-class baseline \(F1 score ([0-9.]+)\)", mismatch="WRONG_DEFINITION",
        note=f"predict-all-positive P={allpos['precision']:.3f}, R=1, F1={allpos['f1']:.3f}; the report's 0.000 is predict-all-NEGATIVE, "
             "which is not the majority class on a 167/300 positive test set.")
    add("B1.base.all_positive_precision", "B1 classifier", "Predict-all-positive precision (= positive share)", allpos["precision"], n=len(y), src=src,
        key="items[].y", estimator="predict-all-positive", unit="proportion")
    add("B1.base.all_negative_f1", "B1 classifier", "Predict-all-negative baseline F1", 0.0, n=len(y), src=src, key="items[].y",
        estimator="predict-all-negative", unit="F1", note="minority-class trivial baseline; not the majority class")
    add("B1.clf.delta_f1_vs_allpos", "B1 classifier", "Classifier F1 minus predict-all-positive F1 (paired item bootstrap)",
        out["tF1"]["f1"] - allpos["f1"], n=len(y), src=src, key="items[].y,p", estimator="paired item bootstrap B=2000",
        ci=boot_ci(lambda ii: prf(y[ii], (p[ii] >= tF1).astype(int))["f1"] - prf(y[ii], np.ones(len(ii), int))["f1"], len(y)), unit="delta F1")
    for k, v in cr["test_baselines"].items():
        if k.startswith("llm"):
            continue
        add(f"B1.base.{k}.f1", "B1 classifier", f"Baseline '{k}' F1 (transcribed; no item-level scores saved)", v["metrics"]["f1"]["point"],
            ci=v["metrics"]["f1"]["ci95"], n=v["metrics"]["n"], src=cr_p, key=f"test_baselines.{k}.metrics.f1", estimator=k, unit="F1",
            recomputed=False, method="summary file only (no item-level baseline scores in exp_1 results)")
    for k in ("lexical_only", "no_embeddings", "hgb"):
        v = cr["test_comparisons"][k]["metrics"]["f1"]
        add(f"B1.cmp.{k}.f1", "B1 classifier", f"Comparison model '{k}' F1 (transcribed)", v["point"], ci=v["ci95"], n=300, src=cr_p,
            key=f"test_comparisons.{k}.metrics.f1", estimator=k, unit="F1", recomputed=False, method="summary file only")
    add("B1.base.unigram_f1_report", "B1 classifier", "'Unigram-frequency baseline F1 0.689' quoted in the report", None, src=cr_p,
        key="test_baselines / test_comparisons (no such baseline)", estimator="unknown", unit="F1", recomputed=False,
        rx=r"unigram-frequency baseline \(F1 score ([0-9.]+)\)",
        note="No baseline with F1 0.689 exists in exp_1 classifier_results.json (baselines: majority 0.715, C-value 0.716, lexical-only 0.762).")
    # LLM A / B vs silver y
    for lab in ("A", "B"):
        yl = np.array([1 if it[f"label_{lab}"] == "CONCEPT" else 0 for it in items])
        m = prf(y, yl)
        yhat = (p >= tF1).astype(int)
        d = out["tF1"]["f1"] - m["f1"]
        ci = boot_ci(lambda ii: prf(y[ii], yhat[ii])["f1"] - prf(y[ii], yl[ii])["f1"], len(y))
        add(f"B1.llm{lab}.f1", "B1 classifier", f"LLM-{lab} F1 vs silver labels (CONCEPT vs rest)", m["f1"], n=len(y), src=src, key=f"items[].label_{lab}",
            estimator=f"LLM-{lab} label", unit="F1", method="confusion matrix", ci=boot_ci(lambda ii: prf(y[ii], yl[ii])["f1"], len(y)),
            note=f"P={m['precision']:.3f} R={m['recall']:.3f}" + ("; LLM-A co-produced the silver labels (circular)" if lab == "A" else ""))
        add(f"B1.clf_minus_llm{lab}.f1", "B1 classifier", f"Classifier F1 minus LLM-{lab} F1 (paired item bootstrap)", d, ci=ci, n=len(y), src=src,
            key=f"items[].p,label_{lab}", estimator="paired item bootstrap B=2000", unit="delta F1", auto=True,
            kw=["LLM", "model " + lab])
    # human anchors (no item-level file -> transcribed)
    ha = cr["human_anchors"]
    e1 = ha["E1_llm_anchor_rows"]
    add("B1.anchor.E1.clf_kappa", "B1 classifier", "Classifier binary kappa vs human anchors (E1, SemEval/SciERC)", e1["primary"]["kappa"]["point"],
        ci=e1["primary"]["kappa"]["ci95"], n=e1["n"], src=cr_p, key="human_anchors.E1_llm_anchor_rows.primary.kappa", estimator="classifier at t_F1",
        unit="kappa", recomputed=False, method="summary only (no item-level anchor file in exp_1 results)",
        rx=r"the classifier achieves a binary kappa of ([0-9.]+)", mismatch="WRONG_ESTIMATOR",
        alt={"WRONG_ESTIMATOR": e1["llm_A_same_rows"]["kappa"]},
        note="0.56 is LLM-A's anchor kappa (iteration-1 DS4 number, reproduced on the same rows), not the classifier's.")
    add("B1.anchor.E1.llmA_kappa", "B1 classifier", "LLM-A binary kappa vs human anchors (E1)", e1["llm_A_same_rows"]["kappa"], n=e1["n"], src=cr_p,
        key="human_anchors.E1_llm_anchor_rows.llm_A_same_rows.kappa", estimator="LLM-A", unit="kappa", recomputed=False,
        method="summary only", rx=r"A vs human anchors binary kappa \(SemEval/SciERC\) \| ([0-9.]+)")
    add("B1.anchor.E1.llmB_kappa", "B1 classifier", "LLM-B binary kappa vs human anchors (E1)", e1["llm_B_same_rows"]["kappa"], n=e1["n"], src=cr_p,
        key="human_anchors.E1_llm_anchor_rows.llm_B_same_rows.kappa", estimator="LLM-B", unit="kappa", recomputed=False, method="summary only")
    for met in ("precision", "recall", "f1", "auc"):
        add(f"B1.anchor.E1.clf_{met}", "B1 classifier", f"Classifier {met} vs human anchors (E1)", e1["primary"][met]["point"], ci=e1["primary"][met]["ci95"],
            n=e1["n"], src=cr_p, key=f"human_anchors.E1_llm_anchor_rows.primary.{met}", estimator="classifier at t_F1", unit=met, recomputed=False,
            method="summary only")
    for met in ("precision", "recall", "f1"):
        add(f"B1.anchor.E1.llmA_{met}", "B1 classifier", f"LLM-A {met} vs human anchors (E1)", e1["llm_A_same_rows"][met], n=e1["n"], src=cr_p,
            key=f"human_anchors.E1_llm_anchor_rows.llm_A_same_rows.{met}", estimator="LLM-A", unit=met, recomputed=False, method="summary only",
            auto=met in ("precision", "recall"), kw=["model A"])
    e2 = ha["E2_test_anchor_rows"]["all"]
    for met in ("precision", "recall", "f1", "auc"):
        add(f"B1.anchor.E2.clf_{met}", "B1 classifier", f"Classifier {met} vs human anchors (E2, balanced resamples)", e2[met]["mean"], ci=e2[met]["ci95"],
            n=ha["E2_test_anchor_rows"]["n_rows"], src=cr_p, key=f"human_anchors.E2_test_anchor_rows.all.{met}", estimator="classifier; mean over resamples",
            unit=met, recomputed=False, method="summary only")
    # merger
    mp = K.E1 / "results/merger_test_predictions.json"
    mt = K.load_json(mp)
    mr_p = K.E1 / "results/merger_results.json"
    mr = K.load_json(mr_p)
    thr = mr["thresholds"]["p_merge"]
    for part, lab in (("d3_test", "Variant pairs"), ("heldout_mesh", "Held-out MeSH synonyms")):
        yy = np.array([r["y"] for r in mt[part]])
        pp = np.array([r["p"] for r in mt[part]])
        yh = (pp >= thr).astype(int)
        m = prf(yy, yh)
        ci = boot_ci(lambda ii: prf(yy[ii], yh[ii])["f1"], len(yy))
        add(f"B1.merger.{part}.f1", "B1 merger", f"Merger pair F1 at p_merge={thr} ({part})", m["f1"], ci=ci, n=len(yy), src=mp, key=f"{part}[].y,p",
            estimator=f"pair LR, p >= {thr}", unit="F1", method="confusion matrix", in_summary=True,
            rx=rf"\| {lab} \| (0\.[0-9]+) \|", note=f"P={m['precision']:.3f} R={m['recall']:.3f} n_pos={int(yy.sum())}")
        add(f"B1.merger.{part}.precision", "B1 merger", f"Merger pair precision ({part})", m["precision"], n=len(yy), src=mp, key=f"{part}[].y,p",
            estimator=f"pair LR, p >= {thr}", unit="proportion", method="confusion matrix")
        add(f"B1.merger.{part}.recall", "B1 merger", f"Merger pair recall ({part})", m["recall"], n=len(yy), src=mp, key=f"{part}[].y,p",
            estimator=f"pair LR, p >= {thr}", unit="proportion", method="confusion matrix")
    ct = mr["cluster_test"]["p_merge"]
    add("B1.merger.bcubed_f1", "B1 merger", "Merger B-cubed F1 (MeSH descriptor clustering)", ct["f1"], n=ct["n_items"], src=mr_p, key="cluster_test.p_merge.f1",
        estimator="B-cubed F1 at p_merge", unit="F1", recomputed=False, method="summary only (cluster assignments not saved)",
        rx=r"\| B-cubed \(full clustering\) \| ([0-9.]+) \|", note=f"n_items={ct['n_items']} terms / {mr['cluster_test']['n_descriptors']} descriptors")
    lk_p = K.E1 / "results/link_calibration.json"
    lk = K.load_json(lk_p)
    fr = lk["frozen"]
    add("B1.linker.tau", "B1 linker", "NIL-aware linker threshold tau", fr["tau"], src=lk_p, key="frozen.tau", estimator="MiniLM gated", unit="cosine",
        recomputed=False, method="summary only")
    add("B1.linker.recall", "B1 linker", "Linker in-KB recall at tau", fr["recall_at_tau"], n=lk["n_queries"], src=lk_p, key="frozen.recall_at_tau",
        estimator="MiniLM gated", unit="proportion", recomputed=False, method="summary only (per-query calibration rows not saved)")
    pk = lk["encoders"]["minilm"]["pick"]["gated"]
    add("B1.linker.precision_nil09", "B1 linker", "Linker precision at NIL prior 0.9", pk["precision_pi0.9"], n=lk["n_queries"], src=lk_p,
        key="encoders.minilm.pick.gated.precision_pi0.9", estimator="MiniLM gated", unit="proportion", recomputed=False, method="summary only")
    return out


# ================================================================== B2 main event study
def b2() -> None:
    es = K.E3 / "results/event_study"
    for lab, fn, cf in (("E", "summary.json", "contrib.parquet"), ("E_alt", "summary_E_alt.json", "contrib_E_alt.parquet"),
                        ("E_up", "summary_E_up.json", "contrib_E_up.parquet")):
        sm = K.load_json(es / fn)
        ct = pd.read_parquet(es / cf)
        ct["d"] = ct.treated - ct.control_mean
        blk = f"B2 event study {lab}"
        for t in sm["table"]:
            if t["family"] not in ("accretion", "closure", "participation"):
                continue
            ind = t["indicator"]
            cc = ct[ct.indicator == ind]
            per_k = cc.groupby("k").d.mean()
            S_re = float(per_k[[k for k in (-3, -2, -1, 0) if k in per_k.index]].mean()) if len(cc) else np.nan
            idb = f"B2.{lab}.{ind}"
            rx = None
            force = None
            alt = {}
            if lab == "E_up" and ind == "closure":
                rx = r"\| Closure \(log-ratio\) \| (-?[0-9.]+) \|"
            if lab == "E" and ind == "closure":
                rx = r"closure S = (-?[0-9.]+), CI \[-0.656"
            if lab == "E_alt" and ind == "closure":
                rx = r"For E_alt \(14 emerging, 10 matched\), closure is S = (-?[0-9.]+)"
            if lab == "E_up" and ind == "accretion_shift_rar":
                rx = r"\| Accretion share \| (-?[0-9.]+) \|"
            if lab == "E_up" and ind == "P_rar":
                rx = r"\| Participation coefficient \| (-?[0-9.]+) \|"
            add(idb + ".S", blk, f"{lab} event-study S for {ind} ({t['version']}): mean treated-minus-control over k in [-3,0]", S_re,
                ci=t["ci"], n=t["n_treated"], src=es / cf, key=f"indicator=={ind}", estimator="event-study S (matched 1:3, treated-unit bootstrap B=1000)",
                unit="indicator units", method="mean over treated of (treated - control_mean) per k, then mean over k in [-3,0]", in_summary=True,
                rx=rx, note=f"file S={t['S']:.6f} (|diff|={abs(t['S'] - S_re):.1e}); p={t['p']}; MDE={t.get('mde', np.nan):.3f} "
                             f"({t.get('mde_in_sd', np.nan):.2f} SD)")
            if t["version"] == "primary":
                pp = sm["pooled_panel"].get(ind, {})
                rxh = None
                if lab == "E_up":
                    rxh = {"closure": r"\| Closure \(log-ratio\) \| -0.837 \| \[-1.26, -0.427\] \| ([0-9.]+) \|",
                           "accretion_shift_rar": r"\| Accretion share \| -0.140 \| \[-0.185, 0.018\] \| ([0-9.]+) \|",
                           "P_rar": r"\| Participation coefficient \| -0.007 \| \[-0.066, 0.056\] \| ([0-9.]+) \|"}[ind]
                if lab == "E_alt" and ind == "closure":
                    rxh = r"closure is S = -0.400, CI \[-0.919, 0.190\], with Holm p = ([0-9.]+)"
                add(idb + ".p_holm", blk, f"{lab} event-study Holm p for {ind} (family of 3 primaries)", t["p_holm"], n=t["n_treated"], src=es / fn,
                    key=f"table[indicator={ind},version=primary].p_holm", estimator="Holm over 3 pre-named primaries (event study)", unit="p",
                    recomputed=False, method="bootstrap p from summary (Holm re-applied below)", rx=rxh,
                    alt={"WRONG_ESTIMATOR": pp.get("p_holm"), "DRIFT_VALUE": t["p"]},
                    note=f"pooled-panel Holm p = {pp.get('p_holm')}; unadjusted event-study p = {t['p']}")
                add(idb + ".mde_sd", blk, f"{lab} MDE (SD units) for {ind}", t.get("mde_in_sd"), n=t["n_treated"], src=es / fn,
                    key=f"table[indicator={ind},version=primary].mde_in_sd", estimator="2.8 x bootstrap SE / pooled SD", unit="SD", recomputed=False)
                if pp:
                    add(f"B2.{lab}.pooled_panel.{ind}.coef", f"B2 pooled panel {lab}", f"{lab} pooled-panel coefficient on futE for {ind}", pp.get("coef"),
                        ci=pp.get("ci"), n=pp.get("n"), src=es / fn, key=f"pooled_panel.{ind}", estimator="OLS futE + log vol3 + age + year FE, concept-cluster bootstrap",
                        unit="indicator units", recomputed=False, method="summary only", note=f"Holm p={pp.get('p_holm')}; n_concepts={pp.get('n_concepts')}")
        # Holm re-applied as a consistency check
        prim = [t for t in sm["table"] if t.get("version") == "primary" and t["family"] in ("accretion", "closure", "participation")]
        ps = np.array([t["p"] for t in prim])
        order = np.argsort(ps)
        adj = np.empty(3)
        run = 0
        for rnk, i in enumerate(order):
            run = max(run, min(1, (3 - rnk) * ps[i]))
            adj[i] = run
        for t, a in zip(prim, adj):
            if abs(a - t["p_holm"]) > 1e-9:
                logger.warning(f"Holm mismatch {lab} {t['indicator']}: {a} vs {t['p_holm']}")
        # label-level rows
        add(f"B2.{lab}.n_treated", blk, f"{lab}: treated (onset) concepts", sm["n_treated"], src=es / fn, key="n_treated", estimator="count",
            unit="concepts", recomputed=False, auto=True, kw=[lab.replace("_", "_"), "emerging"])
        add(f"B2.{lab}.n_matched", blk, f"{lab}: treated with >= 1 control", sm["n_matched"], src=es / fn, key="n_matched", estimator="count", unit="concepts",
            recomputed=False)
        mt = pd.read_csv(es / ("matches.csv" if lab == "E" else f"matches_{lab}.csv"))
        mm = mt[mt.n_controls > 0]
        add(f"B2.{lab}.match_rate", blk, f"{lab}: match rate (share of treated with controls)", len(mm) / len(mt), n=len(mt), src=es / ("matches.csv" if lab == "E" else f"matches_{lab}.csv"),
            key="n_controls>0", estimator="share", unit="share of treated", method="recount from matches csv",
            rx=r"match rate ([0-9.]+)%\)" if lab == "E_up" else None, scale=100)
        add(f"B2.{lab}.widened_share", blk, f"{lab}: share of matched needing the widened caliper", mm.widened.mean(), n=len(mm), src=es / ("matches.csv" if lab == "E" else f"matches_{lab}.csv"),
            key="widened", estimator="share", unit="share of matched", rx=r"with ([0-9.]+)% requiring widened caliper" if lab == "E_up" else None, scale=100)
        add(f"B2.{lab}.mean_controls", blk, f"{lab}: mean controls per matched treated", mm.n_controls.mean(), n=len(mm), src=es / ("matches.csv" if lab == "E" else f"matches_{lab}.csv"),
            key="n_controls", estimator="mean", unit="controls", rx=r"mean of ([0-9.]+) controls per treated" if lab == "E_up" else None)
        pl = sm.get("placebo", {}).get("results", {})
        for ind, v in pl.items():
            add(f"B4.{lab}.placebo.{ind}", "B4 nulls", f"{lab} pseudo-onset placebo S for {ind} (never-emerging, pseudo t0)", v["S"], ci=v["ci"], n=v["n_treated"],
                src=es / fn, key=f"placebo.results.{ind}", estimator="event study on pseudo onsets", unit="indicator units", recomputed=False,
                note=f"covers zero: {v['covers_zero']}")
    # label rates from the label file
    lp = K.E3 / "results/labels/emergence_screen.parquet"
    lab = pd.read_parquet(lp)
    win = lab[lab.t.isin(range(2008, 2016))]
    elig = win.concept_id.nunique()
    for col, rxr, rxn in (("E", r"\| E \(primary\) \| 4 \| ([0-9.]+)% \|", None), ("E_alt", None, None), ("E_up", r"\| E_up \(uptake only\) \| 41 \| ([0-9.]+)% \|", None)):
        on = win[win[col] == 1].concept_id.nunique()
        add(f"B2.{col}.rate_concept_years", "B2 labels", f"{col} rate = positive concept-years / eligible concept-years", lab[col].mean(), n=len(lab), src=lp,
            key=col, estimator="mean of label over all eligible (c,t) rows", unit="share of concept-years", scale=100, rx=rxr,
            note=f"alternative definition onsets/eligible concepts = {on}/{elig} = {on / elig:.3f}; the report's N column counts concepts but the "
                 f"Rate column is a concept-year rate")
        add(f"B2.{col}.onsets", "B2 labels", f"{col}: concepts with an onset in the 2008-2015 screen window", on, n=elig, src=lp, key=col,
            estimator="count of concepts with label=1 in window", unit="concepts",
            rx={"E": r"\| E \(primary\) \| ([0-9]+) \|", "E_alt": r"\| E_alt \(sensitivity\) \| ([0-9]+) \|", "E_up": r"\| E_up \(uptake only\) \| ([0-9]+) \|"}[col])
    # wrong-estimator label: event-study S called a pooled-panel coefficient
    su = K.load_json(es / "summary_E_up.json")
    cl = [t for t in su["table"] if t["indicator"] == "closure" and t["version"] == "primary"][0]
    add("B2.E_up.closure.S_label", "B2 event study E_up", "The E_up closure S = -0.837 is the matched EVENT-STUDY mean difference, not the pooled-panel "
        "coefficient (-0.743)", cl["S"], ci=cl["ci"], n=cl["n_treated"], src=es / "summary_E_up.json", key="table[closure,primary].S",
        estimator="event-study S", unit="indicator units", recomputed=False, rx=r"the pooled panel coefficient for closure is S = (-?[0-9.]+)",
        force="WRONG_ESTIMATOR", note=f"pooled panel coef = {su['pooled_panel']['closure']['coef']:.3f} {np.round(su['pooled_panel']['closure']['ci'], 2).tolist()}, "
                                     f"Holm {su['pooled_panel']['closure']['p_holm']}, n = {su['pooled_panel']['closure']['n']} rows / "
                                     f"{su['pooled_panel']['closure']['n_concepts']} concepts; Table 17 header 'S (pooled)' is also mislabelled")


# ================================================================== B3 prediction
def b3() -> None:
    sp = K.E3 / "results/prediction/summary.json"
    s = K.load_json(sp)
    pp = K.E3 / "results/prediction/predictions.parquet"
    pr = pd.read_parquet(pp)
    rx_tab = {"E_h5": r"\| E \(primary\) \| 1 \| ([0-9.]+) \|", "E_alt_h5": r"\| E_alt \(sensitivity\) \| 1 \| ([0-9.]+) \|",
              "E_up_h5": r"\| E_up \(uptake only\) \| 2 \| ([0-9.]+) \|"}
    rx_full = {"E_h5": r"\| E \(primary\) \| 1 \| [0-9.]+ \| ([0-9.]+) \|", "E_alt_h5": r"\| E_alt \(sensitivity\) \| 1 \| [0-9.]+ \| ([0-9.]+) \|",
               "E_up_h5": r"FULL model \(baseline \+ precursors\) achieves AUC = ([0-9.]+)"}
    rx_d = {"E_h5": r"\| E \(primary\) \| 1 \| [0-9.]+ \| [0-9.]+ \| ([+-][0-9.]+) \|", "E_alt_h5": r"\| E_alt \(sensitivity\) \| 1 \| [0-9.]+ \| [0-9.]+ \| ([+-][0-9.]+) \|",
            "E_up_h5": r"giving a delta of ([+-][0-9.]+), CI"}
    for key, tgt in (("E_h5", "E"), ("E_alt_h5", "E_alt"), ("E_up_h5", "E_up")):
        used = [o["T"] for o in s[key]["origins"] if o["used"]]
        vals = {}
        for est in ("logit", "hgb"):
            sub = pr[(pr.target == tgt) & (pr.model == est) & (pr["T"].isin(used))]
            res = {}
            for fs in ("BASELINE", "FULL"):
                q = sub[sub.featureset == fs].sort_values(["T", "concept_id", "t"])
                res[fs] = q
            a_b = roc_auc_score(res["BASELINE"].y_true, res["BASELINE"].y_score)
            a_f = roc_auc_score(res["FULL"].y_true, res["FULL"].y_score)
            mb = res["BASELINE"].reset_index(drop=True)
            mf = res["FULL"].reset_index(drop=True)
            assert (mb.concept_id.values == mf.concept_id.values).all()
            conc = mb.concept_id.values
            uc = np.unique(conc)
            rows_by = {c: np.where(conc == c)[0] for c in uc}
            rng = np.random.default_rng(0)
            ds = []
            for _ in range(1000):
                ii = np.concatenate([rows_by[c] for c in rng.choice(uc, len(uc))])
                yt = mb.y_true.values[ii]
                if len(set(yt)) < 2:
                    continue
                ds.append(roc_auc_score(yt, mf.y_score.values[ii]) - roc_auc_score(yt, mb.y_score.values[ii]))
            ci = np.percentile(ds, [2.5, 97.5]).tolist()
            ev = s[key]["eval"][est]
            vals[est] = dict(base=a_b, full=a_f, d=a_f - a_b, ci=ci, file_d=ev["deltas"]["FULL_vs_BASELINE"])
            prim = est == "logit"
            other = "hgb" if prim else None
            n_te, n_pos = len(mb), int(mb.y_true.sum())
            blk = "B3 prediction"
            est_s = f"{'logit (PRIMARY)' if prim else 'HGB (secondary)'}; pooled test rows of used rolling origins {used}"
            note = f"n_test_rows={n_te}, n_test_pos={n_pos}, n_concepts={len(uc)}, origins={used}; file pooled AUC {ev['pooled'][fs]['metric']:.4f}"
            add(f"B3.{tgt}.{est}.baseline_auc", blk, f"{tgt}: BASELINE AUC ({est})", a_b, n=n_te, src=pp, key=f"target={tgt},model={est},featureset=BASELINE,T in {used}",
                estimator=est_s, unit="AUC", method="sklearn roc_auc_score on pooled test rows",
                rx=(rx_tab[key] if key != "E_up_h5" else r"BASELINE model achieves AUC = ([0-9.]+)") if prim else None, note=note)
            add(f"B3.{tgt}.{est}.full_auc", blk, f"{tgt}: FULL AUC ({est})", a_f, n=n_te, src=pp, key=f"target={tgt},model={est},featureset=FULL,T in {used}",
                estimator=est_s, unit="AUC", method="sklearn roc_auc_score on pooled test rows", rx=rx_full[key] if prim else None, note=note)
            add(f"B3.{tgt}.{est}.delta_auc", blk, f"{tgt}: FULL minus BASELINE AUC ({est})", a_f - a_b, ci=ci, n=n_te, src=pp,
                key=f"target={tgt},model={est}", estimator=est_s + "; concept bootstrap B=1000", unit="delta-AUC",
                method="difference of pooled AUCs; CI by concept-cluster bootstrap", rx=rx_d[key] if prim else None,
                note=note + f"; file delta {ev['deltas']['FULL_vs_BASELINE']['delta']:.4f} CI {np.round(ev['deltas']['FULL_vs_BASELINE']['ci'], 3).tolist()}")
        # attach WRONG_ESTIMATOR alternatives to the primary rows
        for r in ROWS[-6:]:
            if ".logit." in r["id"]:
                kk = {"baseline_auc": "base", "full_auc": "full", "delta_auc": "d"}[r["id"].split(".")[-1]]
                r["_alt"] = {"WRONG_ESTIMATOR": vals["hgb"][kk]}
    mesh_perm = K.load_json(K.E4 / "results/analysis_summary.json")["prediction_meta"]["checks"]["label_permutation_delta_auc"]["mean"]
    for k, v in s["shuffle_test"].items():
        add(f"B4.main.shuffle.{k}", "B4 nulls", f"Main-pool label-shuffle null, mean delta-AUC ({k})", v["mean_delta"], n=v["n"], src=sp, key=f"shuffle_test.{k}",
            estimator="label permutation, delta-AUC", unit="delta-AUC", recomputed=False,
            rx=r"shuffle test produces a mean delta of (-?[0-9.]+) with SD" if k == "E_alt_h5" else None,
            alt={"WRONG_ESTIMATOR": mesh_perm},
            note=f"sd={v['sd_delta']:.3f}; NO shuffle test exists for E_up in exp_3 — the report attaches this null to E_up" if k == "E_alt_h5" else f"sd={v['sd_delta']:.3f}")


# ================================================================== B4/B5 MeSH
def b5() -> None:
    ep = K.E4 / "results/rq1_effects.csv"
    e = pd.read_csv(ep)
    d = e[(e.rel_year == "D_-3_-1") & (e.subset == "all") & (e.version == "raw")]
    rx = {("PRIMARY", "E", "closure_lr"): r"\| PRIMARY \| 15 \| (-?[0-9.]+) \|", ("SENS1", "E", "closure_lr"): r"\| SENS1 \| 29 \| (-?[0-9.]+) \|",
          ("SENS2", "E", "closure_lr"): r"\| SENS2 \| 10 \| (-?[0-9.]+) \|", ("PRIMARY", "E_cent", "closure_lr"): r"\| E_cent only \| 30 \| (-?[0-9.]+) \|",
          ("SENS1", "E", "dP"): r"significant for SENS1 only \(D = (-?[0-9.]+)"}
    rxh = {("PRIMARY", "E", "closure_lr"): r"\| PRIMARY \| 15 \| -0.086 \| \[-0.511, 0.402\] \| ([0-9.]+) \|",
           ("SENS1", "E", "closure_lr"): r"\| SENS1 \| 29 \| -0.419 \| \[-0.740, -0.115\] \| ([0-9.]+) \|",
           ("PRIMARY", "E", "accretion_share"): r"PRIMARY Holm p = ([0-9.]+), SENS1", ("SENS1", "E", "dP"): r"CI \[0.014, 0.087\], Holm p = ([0-9.]+)",
           ("PRIMARY", "E", "dP"): r"not significant for PRIMARY \(D = 0.025, Holm p = ([0-9.]+)\)"}
    rxn = {("SENS1", "E", "closure_lr"): r"\| SENS1 \| ([0-9]+) \| -0.419", ("PRIMARY", "E", "closure_lr"): r"\| PRIMARY \| ([0-9]+) \| -0.086",
           ("SENS2", "E", "closure_lr"): r"\| SENS2 \| ([0-9]+) \| -0.858", ("PRIMARY", "E_cent", "closure_lr"): r"\| E_cent only \| ([0-9]+) \| -0.148"}
    for vd in ("PRIMARY", "SENS1", "SENS2"):
        for oc in ("E", "E_cent"):
            if oc == "E_cent" and vd != "PRIMARY":
                continue
            for ind in ("closure_lr", "accretion_share", "dP"):
                q = d[(d.volume_def == vd) & (d.outcome == oc) & (d.indicator == ind)]
                if q.empty:
                    continue
                r = q.iloc[0]
                tag = f"{vd}{'_E_cent_only' if oc == 'E_cent' else ''}"
                add(f"B5.mesh.{tag}.{ind}.D", "B5 MeSH plan-native", f"MeSH {tag}: D ({ind}), mean diff over rel -3..-1", r["diff"], ci=[r.ci_lo, r.ci_hi],
                    n=int(r.n_eff_window), src=ep, key=f"volume_def={vd},outcome={oc},indicator={ind},version=raw,rel_year=D_-3_-1,subset=all",
                    estimator="matched event study D (concept bootstrap B=2000)", unit="indicator units", recomputed=False,
                    method="summary row (per-set matrices not saved as rows)", rx=rx.get((vd, oc, ind)),
                    note=f"n_emerging={int(r.n_emerging)}, n_eff={int(r.n_eff_window)}, Holm p={r.p_holm}, MDE={r.mde_sd:.2f} SD")
                add(f"B5.mesh.{tag}.{ind}.p_holm", "B5 MeSH plan-native", f"MeSH {tag}: Holm p ({ind})", r.p_holm, n=int(r.n_eff_window), src=ep,
                    key=f"...{ind}.p_holm", estimator="Holm over 3 precursors", unit="p", recomputed=False, rx=rxh.get((vd, oc, ind)))
                if ind == "closure_lr":
                    add(f"B5.mesh.{tag}.n_eff", "B5 MeSH plan-native", f"MeSH {tag}: n_eff (treated with a finite window diff)", int(r.n_eff_window),
                        src=ep, key="n_eff_window", estimator="count", unit="concepts", recomputed=False, rx=rxn.get((vd, oc, ind)), mismatch="WRONG_N",
                        note=f"n_emerging={int(r.n_emerging)}")
    byid = {r["id"]: r for r in ROWS}
    for suf in ("D", "p_holm"):
        a_, b_ = byid.get(f"B5.mesh.SENS1.dP.{suf}"), byid.get(f"B5.mesh.PRIMARY_E_cent_only.dP.{suf}")
        if a_ and b_:
            a_["_alt"] = {"WRONG_DEFINITION": b_["value"]}
            a_["note"] += " The report's SENS1 dP numbers (D 0.051 [0.014, 0.087], Holm 0.015) are the E_cent-only dP row."
    msp = K.E4 / "results/matched_sets.json"
    ms = K.load_json(msp)
    for key, sets in ms.items():
        n = len(sets)
        r20 = sum(1 for s in sets if s["k"] == 3 and s["tol"] == 0.2) / n
        r30 = sum(1 for s in sets if s["k"] == 3 and s["tol"] <= 0.3) / n
        ra = sum(1 for s in sets if s["k"] > 0) / n
        prim = key == "PRIMARY|all"
        add(f"B5.match.{key}.rate3_20", "B5 MeSH matching", f"MeSH {key}: share of treated with 3 controls at +-20%", r20, n=n, src=msp, key=key,
            estimator="share k==3 & tol==0.2", unit="share of treated", scale=100, rx=r"\(([0-9.]+)% at the tighter 20% caliper\)" if prim else None,
            mismatch="WRONG_DEFINITION")
        add(f"B5.match.{key}.rate3_30", "B5 MeSH matching", f"MeSH {key}: share of treated with 3 controls at <= +-30%", r30, n=n, src=msp, key=key,
            estimator="share k==3 & tol<=0.3", unit="share of treated", scale=100, rx=r"rate of ([0-9.]+)% at the 30% caliper" if prim else None,
            mismatch="WRONG_DEFINITION", alt={"WRONG_DEFINITION": ra})
        add(f"B5.match.{key}.rate_any", "B5 MeSH matching", f"MeSH {key}: share of treated with any control", ra, n=n, src=msp, key=key,
            estimator="share k>0", unit="share of treated", scale=100)
    asp = K.E4 / "results/analysis_summary.json"
    a = K.load_json(asp)
    lp = a["prediction_meta"]["checks"]["label_permutation_delta_auc"]
    add("B4.mesh.label_perm_mean", "B4 nulls", "MeSH label-permutation delta-AUC mean (5 permutations, grouped CV)", lp["mean"], n=len(lp["deltas"]), src=asp,
        key="prediction_meta.checks.label_permutation_delta_auc.mean", estimator="grouped-CV delta-AUC under permuted labels", unit="delta-AUC",
        recomputed=True, method="mean of the 5 saved deltas", rx=r"label-permutation delta-AUC check shows a mean delta of (-?[0-9.]+)")
    for ind, v in a["event_null_T5"].items():
        add(f"B4.mesh.T5.{ind}", "B4 nulls", f"MeSH T5 permutation null mean D ({ind})", v["mean_perm_D"], n=v["n_perms"], src=asp, key=f"event_null_T5.{ind}",
            estimator="treated-label permutation within matched sets", unit="indicator units", recomputed=False,
            rx=r"mean permutation D for closure is (-?[0-9.]+)" if ind == "closure_lr" else None,
            note=f"sd={v['sd_perm_D']:.3f}; pass |mean| < 0.25 SE: {v['pass_abs_mean_lt_0.25_se']}")
    au = K.load_json(K.E4 / "results/audit_rederivation.json")
    add("B4.mesh.shuffled_label_auc", "B4 nulls", "MeSH shuffled-label (placebo) grouped-CV AUC of model A", au["gcv placebo AUC_A"], n=au["n_units"],
        src=K.E4 / "results/audit_rederivation.json", key="gcv placebo AUC_A", estimator="grouped CV on shuffled labels", unit="AUC", recomputed=False)
    rob = K.load_json(K.E3 / "results/robustness.json")
    for y, v in rob["leiden_stability"].items():
        add(f"B11.leiden_ami.{y}", "B11 structure", f"Main-pool Leiden bootstrap AMI, snapshot {y}", v["ami_mean"], n=v["n"], src=K.E3 / "results/robustness.json",
            key=f"leiden_stability.{y}.ami_mean", estimator="AMI of Leiden partitions over resamples", unit="AMI", recomputed=False)
    for v in rob["rewire"]:
        add(f"B4.main.rewire.{v['year']}", "B4 nulls", f"Main-pool share of neighbourhoods denser than degree-preserving null ({v['year']})",
            v["share_p_emp_lt_0_05"], n=v["n_pool_with_5_kept_neighbours"], src=K.E3 / "results/robustness.json", key=f"rewire[year={v['year']}]",
            estimator="configuration-model rewiring, 20 nulls", unit="share", recomputed=False)


# ================================================================== B6 viability
def b6() -> None:
    vp = K.E2 / "results/viability/viability_layer.csv"
    v = pd.read_csv(vp, usecols=["state_main", "tested_main", "reason_code", "state_nmin5", "state_nmin10", "state_nmin20", "state_nmin30"])
    n = len(v)
    cnt = v.state_main.value_counts()
    tested = int(v.tested_main.sum())
    for st, rxs in (("SOURCE", r"\| SOURCE \| ([0-9]+) \|"), ("SINK", r"\| SINK \| ([0-9]+) \|"), ("FADING", r"\| FADING \| ([0-9]+) \|"),
                    ("UNDETERMINED", r"\| UNDETERMINED \| ([0-9]+) \|")):
        add(f"B6.state.{st}", "B6 viability", f"Viability {st} edges at n_min 30 (of {n} eligible)", int(cnt.get(st, 0)), n=n, src=vp, key="state_main",
            estimator="BH q=0.10 within (c,t) families; n_min 30", unit="edges", method="value_counts of state_main", rx=rxs)
        if st != "UNDETERMINED":
            add(f"B6.share_tested.{st}", "B6 viability", f"{st} share of tested edges", int(cnt.get(st, 0)) / tested, n=tested, src=vp, key="state_main/tested_main",
                estimator="count / tested", unit="share of tested", scale=100, rx=rf"\| {st} \| [0-9]+ \| ([0-9.]+)% \|")
    tu = int(((v.state_main == "UNDETERMINED") & v.tested_main).sum())
    add("B6.tested", "B6 viability", "Tested edges", tested, n=n, src=vp, key="tested_main", estimator="count", unit="edges", rx=r"Of 779 eligible edges, ([0-9]+) were tested")
    add("B6.tested_undetermined", "B6 viability", "Tested but UNDETERMINED edges (the missing 43% of the 'share of tested' column)", tu, n=tested, src=vp,
        key="tested_main & state_main==UNDETERMINED", estimator="count", unit="edges",
        note=f"= {tu / tested:.3f} of tested; Table 13's three shares sum to {(tested - tu) / tested:.3f}, not 100%, and its UNDETERMINED row (683) mixes {tu} tested + {int(cnt.get('UNDETERMINED', 0)) - tu} untested edges")
    add("B6.share_tested_sum", "B6 viability", "Sum of the SOURCE/SINK/FADING 'share of tested' column (Table 13 labels the tested total 100%)",
        (tested - tu) / tested, n=tested, src=vp, key="state_main/tested_main", estimator="(SOURCE+SINK+FADING)/tested", unit="share of tested",
        rx=r"\| \*\*Total tested\*\* \| \*\*169\*\* \| \*\*([0-9.]+)%\*\* \|", scale=100, mismatch="WRONG_DEFINITION",
        note=f"the remaining {tu / tested:.1%} of tested edges are tested-but-UNDETERMINED and are missing from the column")
    for rc, c in v.reason_code.value_counts().items():
        add(f"B6.reason.{rc}", "B6 viability", f"Reason-code share '{rc}'", c / n, n=n, src=vp, key="reason_code", estimator="share", unit="share of eligible")
    for nm in (5, 10, 20, 30):
        vc = v[f"state_nmin{nm}"].value_counts()
        for st in ("SOURCE", "SINK", "FADING"):
            add(f"B6.nmin{nm}.{st}", "B6 viability", f"{st} edges at n_min {nm}", int(vc.get(st, 0)), n=n, src=vp, key=f"state_nmin{nm}", estimator="count", unit="edges")


# ================================================================== B7 dataset_5
def b7() -> None:
    files = sorted(glob.glob(str(K.D5 / "full_data_out/full_data_out_*.json")))
    cov, ven, n_links, pool = [], [], 0, []
    for f in files:
        d = K.load_json(f)
        for ds in d["datasets"]:
            nm = ds["dataset"]
            if nm == "nativeness_coverage":
                for ex in ds["examples"]:
                    cov.append((json.loads(ex["input"]), json.loads(ex["output"]), ex.get("metadata_arm")))
            elif nm == "venue_habitat_asjc":
                for ex in ds["examples"]:
                    o = json.loads(ex["output"])
                    ven.append(dict(covered=o["habitat_subfield"] != "UNCOVERED", n=ex.get("metadata_n_c_papers") or 0,
                                    ci=ex.get("metadata_citation_independent"), reason=ex.get("metadata_uncovered_reason")))
            elif nm == "concept_work_links":
                n_links += len(ds["examples"])
            elif nm == "concept_pool_2005_2016":
                for ex in ds["examples"]:
                    pool.append((ex["metadata_concept_id"], ex["metadata_fold"], ex.get("metadata_arm")))
        del d
    K.dump({"pool": pool}, K.RES / "cache_d5_pool.json")
    src1 = K.D5 / "full_data_out/full_data_out_*.json"
    per = [(i, o) for i, o, _ in cov if str(i.get("concept_id", "")).startswith("c_")]
    ov = [(i, o) for i, o, _ in cov if not str(i.get("concept_id", "")).startswith("c_")]
    hw = np.array([o.get("host_weight", 0) or 0 for _, o in per], float)
    sh = np.array([o.get("covered_weight_share", np.nan) for _, o in per], float)
    ok = np.isfinite(sh) & (hw > 0)
    rec = float((sh[ok] * hw[ok]).sum() / hw[ok].sum())
    overall = ov[0][1] if ov else {}
    add("B7.nativeness.weight_share", "B7 dataset_5", "Share of host (non-origin) co-occurrence WEIGHT covered by the 1,372 profiled nodes",
        rec, n=int(ok.sum()), src=src1, key="nativeness_coverage per-concept rows", estimator="sum(covered_share x host_weight) / sum(host_weight)",
        unit="share of host WEIGHT", scale=100, method="recomputed from per-concept rows",
        rx=r"The overall host weight coverage \(the fraction of concept-subfield edges[^)]*\) is ([0-9.]+)%", force="WRONG_DEFINITION",
        note=f"overall row in file: {json.dumps(ov[0][0])[:80] if ov else ''} -> {json.dumps(overall)[:160]}; the report defines it as a share of concept-subfield EDGES with 4 non-missing blocks")
    vd = pd.DataFrame(ven)
    cvd = vd[vd.covered]
    add("B7.asjc.covered_venues", "B7 dataset_5", "ASJC-covered venues", len(cvd), n=len(vd), src=src1, key="venue_habitat_asjc habitat_subfield != UNCOVERED",
        estimator="count", unit="venues", rx=r"\| Covered ASJC venues \| ([0-9,]+) \|",
        note=f"citation-independent {int((cvd.ci == True).sum())} + not {int((cvd.ci != True).sum())}")  # noqa: E712
    add("B7.asjc.venue_share", "B7 dataset_5", "Share of VENUES that are ASJC-covered", len(cvd) / len(vd), n=len(vd), src=src1,
        key="venue_habitat_asjc", estimator="covered / all venues", unit="share of venues", scale=100)
    link_share = cvd.n.sum() / n_links
    add("B7.asjc.link_share", "B7 dataset_5", "Share of concept-work LINKS in ASJC-covered venues", link_share, n=n_links, src=src1,
        key="sum(metadata_n_c_papers | covered) / n concept_work_links", estimator="c-papers in covered venues / all links", unit="share of LINKS",
        scale=100, method="approximation: venue c-paper counts over all links (links without a venue count as uncovered)",
        rx=r"\| ASJC venue coverage \| ([0-9.]+)% \|", force="WRONG_UNITS",
        note=f"venue-level share is {len(cvd) / len(vd):.3f}; the 12.1% in the dataset_5 README is a share of LINKS, the report calls it venue coverage")
    add("B7.links", "B7 dataset_5", "Verified concept-work links", n_links, src=src1, key="concept_work_links", estimator="count", unit="links")
    rl = K.load_json(K.D5 / "run_ledger.json")
    cr = sum(v["credits"] for v in rl["credit_ledger_by_step"].values())
    add("B7.credits", "B7 dataset_5", "OpenAlex credits consumed by dataset_5", cr, src=K.D5 / "run_ledger.json", key="credit_ledger_by_step.*.credits",
        estimator="sum", unit="credits", rx=r"\| API credits consumed \| ([0-9,]+) \|")


# ================================================================== B8 power, B9 Gate A, B10 exp_2 other
def b8_b10() -> None:
    hp = K.E2 / "results/power/h1_mde.json"
    h = K.load_json(hp)
    tab15 = {(5, "0.7", "realised"), (10, "0.7", "realised"), (20, "0.7", "realised"), (30, "0.7", "realised"), (10, "0.8", "projected"),
             (20, "0.8", "projected"), (30, "0.8", "projected"), (20, "0.8", "N150"), (30, "0.8", "N150")}
    for k, v in h.items():
        kind, nm, tgt, des = k.split("|")
        nmin = int(nm.replace("nmin", ""))
        tv = tgt.replace("AUC", "").replace("R2", "")
        rx = None
        if kind == "auc" and (nmin, tv, des) in tab15:
            rx = rf"\| {nmin} \| {tv} \| {des} \| ([0-9.]+) \|"
        cell = v
        v = cell["MDE"]
        add(f"B8.h1_mde.{k}", "B8 H1 power", f"H1 MDE ({kind}) at n_min {nmin}, target {tgt}, design {des}", v, src=hp, key=f"{k}.MDE",
            n=cell.get("realised_units"),
            estimator="simulation under the pre-registered selection-rule pipeline", unit="delta-AUC" if kind == "auc" else "delta-R2",
            recomputed=False, method="summary grid", rx=rx, mismatch="WRONG_UNITS",
            note=("report Table 15 labels these 'Cohen's d' and prints values that are not in h1_mde.json; " if rx else "")
                 + f"realised concepts {cell.get('realised_concepts')}, beta {cell.get('beta')}")
    dp = K.E2 / "results/power/decisions.json"
    dcs = K.load_json(dp)
    for nm, v in dcs["realised_and_projected_by_nmin"].items():
        add(f"B8.Nc.{nm}.realised", "B8 H1 power", f"Realised N_c at {nm}", v["realised"], src=dp, key=f"realised_and_projected_by_nmin.{nm}.realised",
            estimator="count of concepts with >=1 tested edge", unit="concepts", recomputed=False)
        add(f"B8.Nc.{nm}.projected", "B8 H1 power", f"Projected N_c at {nm}", v["projected"], src=dp, key=f"realised_and_projected_by_nmin.{nm}.projected",
            estimator="projection to full 426 frame", unit="concepts", recomputed=False,
            ci=dcs["projected_N_c_90"] if nm == "n_min_30" else None)
    gp = K.E2 / "results/power/gate_b.json"
    gb = K.load_json(gp)
    for cl in (10, 30, 60, 120):
        dd = gb["designs"][f"hypothetical_{cl}_clusters"]
        add(f"B8.gateB.mde_pct.{cl}", "B8 Gate B", f"Gate B hypothetical design MDE% at {cl} clusters", dd.get("MDE_pct"), src=gp,
            key=f"designs.hypothetical_{cl}_clusters.MDE_pct", estimator="simulated PPML power", unit="% change", recomputed=False,
            note=f"CRV1 two-sided size {dd.get('size_b2_0_two_sided_crv')}, wild-bootstrap size {dd.get('wild_size_005')}")
    add("B8.gateB.episodes", "B8 Gate B", "Gate B labelled episodes (theta 0.7)", gb["episode_counts"]["theta_0.7"]["labelled"]["episodes"], src=gp,
        key="episode_counts.theta_0.7.labelled.episodes", estimator="count", unit="episodes", recomputed=False)
    # Gate A
    gap = K.E2 / "results/gate_a/gate_A_verdict.json"
    ga = K.load_json(gap)
    ps = ga["pooled_summary"]
    for k, rx in (("share_ge_040", r"\| Edges with host share >= 0.40 \| ([0-9.]+)% \|"), ("mean", r"\| Mean within-host traced share \| ([0-9.]+) \|"),
                  ("median", r"\| Median within-host traced share \| ([0-9.]+) \|"), ("concept_weighted_mean", None), ("concept_weighted_share_ge_040", None)):
        add(f"B9.gateA.within_host.{k}", "B9 Gate A", f"Gate A within-host non-canonical traced share: {k}", ps[k], n=ps["n_edges"], src=gap,
            key=f"pooled_summary.{k}", estimator="per edge (c,d,t), |Kd|>=10", unit="share", recomputed=False,
            scale=100 if k == "share_ge_040" else 1, rx=rx, note=f"{ps['n_edges']} edges / {ps['n_concepts']} concepts")
    la = ga["lenient_any_parent_same_edges"]
    add("B9.gateA.lenient.mean", "B9 Gate A", "Lenient ANY-parent traced share on the SAME 724 edges (mean)", la["mean"], n=la["n_edges"], src=gap,
        key="lenient_any_parent_same_edges.mean", estimator="any-parent tracing", unit="share", recomputed=False)
    add("B9.gateA.lenient.share_ge_040", "B9 Gate A", "Lenient any-parent share >= 0.40 on the same edges", la["share_ge_040"], n=la["n_edges"], src=gap,
        key="lenient_any_parent_same_edges.share_ge_040", estimator="any-parent tracing", unit="share", recomputed=False,
        rx=r"because the concept-level metric pools all host subfields", force="WRONG_DEFINITION",
        note="The drop 0.55 -> 0.17 is definitional (lenient any-parent tracing vs within-host non-canonical tracing on the SAME edges: "
             f"lenient mean {la['mean']}, share>=0.40 {la['share_ge_040']}), not subfield pooling.")
    sd = ga["pooled_summary_secondary_denominator"]
    add("B9.gateA.secondary.share_ge_040", "B9 Gate A", "Within-host share >= 0.40, secondary denominator (children with refs)", sd["share_ge_040"],
        n=sd["n_edges"], src=gap, key="pooled_summary_secondary_denominator.share_ge_040", estimator="per edge", unit="share", recomputed=False)
    lc = K.load_json(K.E2 / "results/gate_a/lenient_loader_check.json")
    add("B9.gateA.loader_check", "B9 Gate A", "Iteration-1 lenient loader check reproduced (main host share)", lc["reproduced"]["main_host"][0],
        n=lc["reproduced"]["main_host"][1], src=K.E2 / "results/gate_a/lenient_loader_check.json", key="reproduced.main_host", estimator="iter-1 assemble.py definition",
        unit="share", recomputed=False, rx=r"concept-level pass \(([0-9.]+)% host traced share\)", scale=100)
    for y, v in ga["per_year_descriptive"].items():
        add(f"B9.gateA.year.{y}", "B9 Gate A", f"Gate A within-host share >= 0.40, focal year {y}", v["share_ge_040"], n=v["n_edges"], src=gap,
            key=f"per_year_descriptive.{y}", estimator="per edge", unit="share", recomputed=False, note=f"mean {v['mean']}")
    gy_p = K.E2 / "results/gate_a/gate_a_by_arm_fold_year.csv"
    gy = pd.read_csv(gy_p)
    sc = gy[(gy.arm == "main") & (gy.fold == "screen") & gy.t.between(2010, 2014)]
    for r in sc.itertuples():
        add(f"B9.gateA.screen.{r.t}", "B9 Gate A", f"Screen-fold mean within-host share, {r.t}", r.within_host_share_mean, n=int(r.n_edges), src=gy_p,
            key=f"arm=main,fold=screen,t={r.t}", estimator="mean over edges", unit="share", note=f"lenient mean {r.lenient_share_mean:.3f}")
    ref = gy[gy.arm == "reference"]
    add("B9.gateA.reference_mean", "B9 Gate A", "Reference-arm within-host share (edge-weighted mean over years)",
        float((ref.within_host_share_mean * ref.n_edges).sum() / ref.n_edges.sum()), n=int(ref.n_edges.sum()), src=gy_p, key="arm=reference",
        estimator="edge-weighted mean", unit="share", method="recomputed from year rows", rx=r"\| Reference arm host share \| ([0-9.]+) \|")
    # graft fallback recount
    gf_p = K.E2 / "results/gate_a/graft_fallback_events.csv"
    gf = pd.read_csv(gf_p)
    for nm, val in (("all", len(gf)), ("kw5", int((gf.n_kw >= 5).sum())), ("kw5_screen", int(((gf.n_kw >= 5) & (gf.fold == "screen")).sum())),
                    ("kw5_heldout", int(((gf.n_kw >= 5) & (gf.fold == "heldout_concept")).sum()))):
        add(f"B9.graft.{nm}", "B9 Gate A", f"Graft-fallback host-entry events ({nm})", val, src=gf_p, key=nm, estimator="recount of rows", unit="events")
    # B10
    p1p = K.E2 / "results/p1/p1_summary.json"
    p1 = K.load_json(p1p)
    for st, v in p1["pooled_H_share_main"].items():
        add(f"B10.p1.{st}", "B10 exp_2", f"P1 pooled entropy share of {st}", v, n=p1["n_ct_units"], src=p1p, key=f"pooled_H_share_main.{st}",
            estimator="entropy decomposition over (c,t)", unit="share of H", recomputed=False)
    orp = K.E2 / "results/origin/cooling_onsets.csv"
    oc = pd.read_csv(orp)
    for th in ("0.6", "0.7", "0.8"):
        add(f"B10.origin.onsets.{th}", "B10 exp_2", f"Origin cooling onsets at theta {th}", int(oc[f"onset_{th}"].notna().sum()), n=len(oc), src=orp,
            key=f"onset_{th}", estimator="count non-null", unit="concepts")
    syp = K.E2 / "results/synth/synth_results.json"
    sy = K.load_json(syp)
    c30 = sy["correct"]["n_min_30"]
    add("B10.synth.fdr_overall", "B10 exp_2", "Synthetic validation realised FDR at n_min 30 (correct calibration)", c30["realised_FDR"], n=c30["n_edges"],
        src=syp, key="correct.n_min_30.realised_FDR", estimator="known-truth synthetic edges", unit="FDR", recomputed=False,
        rx=r"\| \*\*Overall\*\* \| \*\*([0-9.]+)\*\*")
    for st, v in c30["per_state"].items():
        add(f"B10.synth.fdr.{st}", "B10 exp_2", f"Synthetic FDR for {st}", v["fdr"], n=v["n_labelled"], src=syp, key=f"correct.n_min_30.per_state.{st}.fdr",
            estimator="known truth", unit="FDR", recomputed=False, rx=rf"\| {st} \| ([0-9.]+) \| <= 0.15 \|" if st in ("SOURCE", "SINK") else None)
    cov = sy["correct"].get("coverage_rho_tilde_tested")
    add("B10.synth.rho_tilde_coverage", "B10 exp_2", "rho~ 90% CI coverage on tested synthetic edges", cov if isinstance(cov, (int, float)) else (cov or {}).get("coverage") if isinstance(cov, dict) else None,
        src=syp, key="correct.coverage_rho_tilde_tested", estimator="coverage", unit="share", recomputed=False, note=json.dumps(cov)[:200])


# ================================================================== B11 structure
def b11() -> None:
    sp = K.E3 / "results/snapshot_summary.csv"
    s = pd.read_csv(sp)
    add("B11.main.nodes_median", "B11 structure", "Main-pool snapshot nodes (median over 25 yearly snapshots)", float(s.n_nodes.median()), n=len(s), src=sp,
        key="n_nodes", estimator="median", unit="nodes", rx=r"The network contains ([0-9,]+) persistent nodes", mismatch="DRIFT_VALUE",
        note=f"nodes range {int(s.n_nodes.min())}-{int(s.n_nodes.max())}, kept edges median {int(s.n_kept_edges.median())}, kept nodes median "
             f"{int(s.n_kept_nodes.median())}; no column equals 1,487 (persistent-node count not computed in exp_3)")
    add("B11.main.kept_edges_median", "B11 structure", "Main-pool kept edges (median over snapshots)", float(s.n_kept_edges.median()), n=len(s), src=sp,
        key="n_kept_edges", estimator="median", unit="edges")
    st4 = K.load_json(K.E4 / "results/snapshot_stats.json")
    add("B11.mesh.nodes_median", "B11 structure", "MeSH background snapshot nodes (median)", float(np.median([r["n_nodes"] for r in st4])), n=len(st4),
        src=K.E4 / "results/snapshot_stats.json", key="[].n_nodes", estimator="median", unit="nodes")
    tp = K.E3 / "results/typology/stability.json"
    ty = K.load_json(tp)
    for k, v in ty["by_k"].items():
        add(f"B11.typology.k{k}.min_jaccard", "B11 structure", f"Typology min bootstrap Jaccard at k={k}", v["min_jaccard"], n=ty["n_concepts"], src=tp,
            key=f"by_k.{k}.min_jaccard", estimator="k-medoids DTW, bootstrap", unit="Jaccard", recomputed=False, rx=rf"k={k}: ([0-9.]+)")
    pp = K.E3 / "results/patterns/summary_E_up.json"
    pa = K.load_json(pp)
    for k, v in ((k, v) for k, v in pa["frequencies"].items() if isinstance(v, dict) and "overall" in v):
        add(f"B11.pattern.{k}", "B11 structure", f"Main-pool pattern frequency {k} (overall)", v["overall"], ci=v.get("overall_ci"), n=v["n"], src=pp,
            key=f"frequencies.{k}.overall", estimator="share of concepts", unit="share", recomputed=False,
            rx=r"present in ([0-9.]+)% of all concepts" if k == "EARLY_BRIDGING__age0_8" else None, scale=100,
            note=f"emerging {v.get('emerging')}, never {v.get('never')}, fisher p {v.get('fisher_p')}")
    add("B11.pattern.early_bridging_definition", "B11 structure", "Early-bridging DEFINITION: P > 0.6 (raw) or top-decile cross-community betweenness in "
        "the first 2 years (SPEC early_bridging P_raw=0.6, btw_pct=90)", 0.6, src=K.E3 / "config.py", key="SPEC['early_bridging']",
        estimator="definition", unit="P threshold", recomputed=False, rx=r"participation coefficient above the ([0-9.]+)th percentile", force="WRONG_DEFINITION")
    rp = K.E4 / "results/rq1_patterns.csv"
    rq = pd.read_csv(rp)
    for r in rq[rq.group == "all"].itertuples():
        add(f"B11.mesh.pattern.{r.pattern}", "B11 structure", f"MeSH pattern frequency {r.pattern}", r.freq, ci=[r.ci_lo, r.ci_hi], n=int(r.n), src=rp,
            key=f"group=all,pattern={r.pattern}", estimator="share of concepts", unit="share", recomputed=False)


# ================================================================== B12 hashes, B13 ledger
def b12_b13() -> None:
    items = []
    p = K.D5 / "hyd/sample_frame_frozen.json"
    rec = (K.D5 / "hyd/sample_frame_frozen.json.sha256") if (K.D5 / "hyd/sample_frame_frozen.json.sha256").exists() else (K.D5 / "hyd/sample_frame_frozen.sha256")
    items.append(("dataset_5 hyd/sample_frame_frozen.json", p, rec.read_text().split()[0] if rec.exists() else None, "sha256 of file bytes vs .sha256 file"))
    pf = K.E2 / "prereg/prereg_freeze.json"
    items.append(("exp_2 prereg/prereg_freeze.json", pf, (K.E2 / "prereg/prereg_freeze.sha256").read_text().split()[0], "sha256 of file bytes vs prereg_freeze.sha256"))
    tp = K.E1 / "results/test_population.json"
    items.append(("exp_1 results/test_population.json", tp, (K.E1 / "results/test_population.sha256").read_text().split()[0], "sha256 of file bytes vs test_population.sha256"))
    sp = K.E3 / "spec.json"
    sj = K.load_json(sp)
    items.append(("exp_3 spec.json (file)", sp, None, "sha256 of file bytes (no external record)"))
    inner = hashlib_spec(sj["spec"])
    ROWS.append(dict(id="B12.exp3.spec_inner", block="B12 hashes", claim="exp_3 spec.json inner sha256 recomputed as sha256(json.dumps(SPEC, sort_keys=True))",
                     value=None, ci_lo=None, ci_hi=None, n=None, unit="sha256", estimator="hashlib", source_path=K.rel(sp), source_key="sha256",
                     recomputed=True, recompute_method="config.spec_hash procedure", reported_in_artifact_summary=None, report_value=None, report_line=None,
                     agrees=inner == sj["sha256"], flag="OK" if inner == sj["sha256"] else "DRIFT_VALUE",
                     note=f"recomputed {inner}; recorded {sj['sha256']}; match={inner == sj['sha256']}", _rx=None, _scale=1, _mismatch="", _force=None,
                     _alt={}, _kw=[], _auto=False, hash_hex=inner, hash_match=inner == sj["sha256"]))
    pr = K.load_json(K.E4 / "results/prereg_spec.json")
    for label, path, recd, meth in items:
        h = K.sha256_file(path)
        match = (h == recd) if recd else None
        ROWS.append(dict(id=f"B12.{label.split()[0]}.{path.name}", block="B12 hashes", claim=f"sha256 of {label}", value=None, ci_lo=None, ci_hi=None, n=None,
                         unit="sha256", estimator="hashlib.sha256", source_path=K.rel(path), source_key="file bytes", recomputed=True, recompute_method=meth,
                         reported_in_artifact_summary=None, report_value=None, report_line=None, agrees=match,
                         flag="OK" if match in (True, None) else "DRIFT_VALUE", note=f"computed {h}; recorded {recd}; match={match}",
                         _rx=None, _scale=1, _mismatch="", _force=None, _alt={}, _kw=[], _auto=False, hash_hex=h, hash_match=match))
    # exp_4 prereg: features hash, spec hash, and the exp_3 files it vendored (recorded in prereg_spec.json)
    checks = [(K.E4 / "results" / Path(pr.get("features_file", "features.parquet")).name, pr["features_sha256"], "features_sha256"),
              (K.E4 / "rq1_spec.py", pr["spec_sha256"], "spec_sha256 (rq1_spec.py)")]
    for fn, hv in pr["main_pool_alignment"]["sha256"].items():
        checks.append((K.E3 / fn, hv, f"main_pool_alignment.sha256.{fn}"))
    for path, recd, keyname in checks:
        h = K.sha256_file(path) if path.exists() else None
        match = h == recd
        ROWS.append(dict(id=f"B12.exp4prereg.{keyname.split(' ')[0]}", block="B12 hashes", claim=f"sha256 of {K.rel(path)} vs exp_4 prereg_spec.json {keyname}",
                         value=None, ci_lo=None, ci_hi=None, n=None, unit="sha256", estimator="hashlib.sha256", source_path=K.rel(K.E4 / "results/prereg_spec.json"),
                         source_key=keyname, recomputed=True, recompute_method="file bytes", reported_in_artifact_summary=None, report_value=None,
                         report_line=None, agrees=match, flag="OK" if match else "DRIFT_VALUE", note=f"computed {h}; recorded {recd}; match={match}" + ("" if match else "; the exp_3 file was modified AFTER exp_4 recorded its hash "
                              "for the aligned block (the aligned block used the earlier version)" if "main_pool_alignment" in keyname else ""),
                         _rx=None, _scale=1, _mismatch="", _force=None, _alt={}, _kw=[], _auto=False, hash_hex=h, hash_match=match))
    # B13 run ledger
    arts = {"exp_1": K.E1, "exp_2": K.E2, "exp_3": K.E3, "exp_4": K.E4, "dataset_5": K.D5}
    for nm, d in arts.items():
        txt = ""
        for f in ("README.md", "reproducibility.md"):
            if (d / f).exists():
                txt += (d / f).read_text(errors="ignore") + "\n"
        cred = re.findall(r"([0-9][0-9,]*)\s*(?:OpenAlex\s*)?credits", txt, flags=re.I)
        usd = re.findall(r"\$\s?([0-9]+\.[0-9]+)", txt)
        wall = re.findall(r"(?:wall[- ]?(?:clock|time)?|runtime)[^0-9\n]{0,30}([0-9][0-9.,]*\s*(?:s|sec|secs|min|h|hours|minutes)\b)", txt, flags=re.I)
        ROWS.append(dict(id=f"B13.{nm}", block="B13 run ledger", claim=f"Run ledger for {nm} ({K.ART_IDS[nm]})", value=None, ci_lo=None, ci_hi=None, n=None,
                         unit="", estimator="regex over README/reproducibility.md", source_path=K.rel(d / "README.md"), source_key="grep credit|$|wall",
                         recomputed=False, recompute_method="text grep (first hits)", reported_in_artifact_summary=None, report_value=None, report_line=None,
                         agrees=None, flag="MISSING_IN_REPORT",
                         note=json.dumps({"openalex_credits": cred[:3] or None, "llm_usd": usd[:3] or None, "wall_time": wall[:3] or None}),
                         _rx=None, _scale=1, _mismatch="", _force=None, _alt={}, _kw=[], _auto=False))


def hashlib_spec(spec: dict) -> str:
    import hashlib
    return hashlib.sha256(json.dumps(spec, sort_keys=True).encode()).hexdigest()


# ================================================================== write
def write() -> dict:
    for r in ROWS:
        if r.get("flag") is None:
            match_report(r)
    pub = [{k: v for k, v in r.items() if not k.startswith("_")} for r in ROWS]
    K.dump({"header": "Numbers of record, recomputed from item/row-level files where they exist; paths relative to the run root",
            "report": K.rel(K.REPORT), "flags": FLAGS, "rows": pub}, K.RES / "record_of_numbers.json")
    df = pd.DataFrame(pub)
    df.to_csv(K.RES / "record_of_numbers.csv", index=False)
    df[df.flag != "OK"].to_csv(K.RES / "drift_flags.csv", index=False)
    L = ["# Numbers of record (Part 1)\n", "Every value is recomputed from item- or row-level files where they exist (`recomputed=true`); "
         "otherwise transcribed from the named summary file. `flag` compares against iter_3/gen_strat/current_report.md "
         "(|diff| <= half a unit of the report's last digit). MISSING_IN_REPORT is informational.\n"]
    for blk, g in df.groupby("block", sort=False):
        L += [f"\n## {blk}\n", "| id | claim | value | 95% CI | n | unit | report (line) | flag |", "|---|---|---|---|---|---|---|---|"]
        for r in g.itertuples():
            v = "" if r.value is None or (isinstance(r.value, float) and not math.isfinite(r.value)) else f"{r.value:.4g}"
            ci = "" if r.ci_lo is None or pd.isna(r.ci_lo) else f"[{r.ci_lo:.3g}, {r.ci_hi:.3g}]"
            rep = "" if r.report_value is None or pd.isna(r.report_value) else f"{r.report_value:g} (L{int(r.report_line)})"
            L.append(f"| {r.id} | {r.claim} | {v} | {ci} | {'' if r.n is None or pd.isna(r.n) else int(r.n)} | {r.unit} | {rep} | **{r.flag}** |")
        srcs = sorted(set(g.source_path.dropna()))
        L.append("\nSource: " + "; ".join(srcs[:6]) + (" ..." if len(srcs) > 6 else ""))
    L.append("\n## Drift flags (not OK / not MISSING)\n")
    for r in df[~df.flag.isin(["OK", "MISSING_IN_REPORT"])].itertuples():
        L.append(f"- **{r.flag}** `{r.id}` (report L{'' if pd.isna(r.report_line) else int(r.report_line)}): {r.claim}. Record value "
                 f"{'' if r.value is None or pd.isna(r.value) else f'{r.value:.4g}'}; report {'' if pd.isna(r.report_value) else r.report_value}. {r.note}")
    (K.RES / "record_of_numbers.md").write_text("\n".join(L))
    counts = df.flag.value_counts().to_dict()
    return dict(n_rows=len(df), n_recomputed=int(df.recomputed.sum()), n_not_rederivable=int((df.flag == "NOT_REDERIVABLE").sum()),
                n_flags_by_type={f: int(counts.get(f, 0)) for f in FLAGS}, n_flags=int((~df.flag.isin(["OK", "MISSING_IN_REPORT"])).sum()))


@logger.catch(reraise=True)
def main() -> dict:
    K.setup_logging("part1_record")
    K.set_ram_limit(20)
    for fn in (b1, b2, b3, b5, b6, b7, b8_b10, b11, b12_b13):
        logger.info(f"block {fn.__name__} ...")
        fn()
        logger.info(f"  rows so far {len(ROWS)}")
    # also turn the Part 2 reproduction gate into record rows (DRIFT_VALUE on failure, per plan)
    r1 = K.R1A / "r1a_results.json"
    if r1.exists():
        g = K.load_json(r1)["gate"]
        for pop, v in g.items():
            ROWS.append(dict(id=f"B2.gate.{pop}", block="B2 event study E_up", claim=f"R1a reproduction gate ({pop}): E_up closure S re-run with the original estimator",
                             value=v["S_reproduced"], ci_lo=v["ci_reproduced"][0], ci_hi=v["ci_reproduced"][1], n=v["n_treated"], unit="indicator units",
                             estimator=v["estimator"], source_path=v["source"].split("#")[0].split("[")[0], source_key=v["source"], recomputed=True,
                             recompute_method="original code re-run on original matched sets", reported_in_artifact_summary=True, report_value=None,
                             report_line=None, agrees=v["passed"], flag="OK" if v["passed"] else "DRIFT_VALUE",
                             note=v.get("gate_status", "") + f"; recorded S {v['S_recorded']:.5f} CI {np.round(v['ci_recorded'], 4).tolist()}",
                             _rx=None, _scale=1, _mismatch="", _force=None, _alt={}, _kw=[], _auto=False))
    summ = write()
    K.dump(summ, K.RES / "record_summary.json")
    logger.info(f"record: {summ}")
    return summ


if __name__ == "__main__":
    main()
