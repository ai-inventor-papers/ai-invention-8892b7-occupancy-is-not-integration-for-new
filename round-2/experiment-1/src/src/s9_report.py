#!/usr/bin/env python3
"""STEP 9: reports -> method_out.json (exp_gen_sol_out schema) + results/*.csv.
Frame audit (classifier vs model A and vs adjudicated silver labels, bootstrap over the 426 concepts), classifier
rejection x sense_check_fail with Fisher exact tests, rejected MAIN phrases, named-fragment check, population counts,
link-status distribution, budget and wall time."""
from __future__ import annotations

import csv
import json
import time
from collections import Counter, defaultdict

import numpy as np
from loguru import logger
from scipy.stats import fisher_exact
from sklearn.metrics import cohen_kappa_score, confusion_matrix

from clfdata import boot_metrics, point_metrics
from common import MINI, WORK, LOGS, MODELS, RESULTS, ROOT, read_json, setup_logging, write_json

METHOD_OUT = (ROOT / "mini_run" / "method_out.json") if MINI else (ROOT / "method_out.json")
NAMED_FRAGMENTS = ["modulo theory", "detector in pp collision", "multi label image"]


def fmt(m: dict | float | None) -> str:
    if isinstance(m, dict) and "point" in m:
        return f"{m['point']:.3f} [{m['ci95'][0]:.3f}, {m['ci95'][1]:.3f}]"
    return "" if m is None else (f"{m:.3f}" if isinstance(m, float) else str(m))


def write_csv(path, rows: list[dict]) -> None:
    if not rows:
        return
    keys = list(rows[0].keys())
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        for r in rows:
            w.writerow(r)


@logger.catch(reraise=True)
def main() -> None:
    setup_logging("s9_report")
    t0 = time.time()
    cls = read_json(RESULTS / "classifier_results.json")
    mer = read_json(RESULTS / "merger_results.json")
    cal = read_json(RESULTS / "link_calibration.json")
    tp = json.loads((RESULTS / "test_population.json").read_text())
    tp_sha = (RESULTS / "test_population.sha256").read_text().strip()
    audit = read_json(RESULTS / "frame_llm_audit.json")
    ml = read_json(RESULTS / "frame_merge_link.json")
    la = read_json(RESULTS / "link_audit.json") if (RESULTS / "link_audit.json").exists() else {"items": {}}
    t1p = (ROOT / "results" / "t1_reused_code.json")  # T1 runs on the full inputs only
    t1 = read_json(t1p) if t1p.exists() else None
    concepts = tp["concepts"]
    byid = {c["concept_id"]: c for c in concepts}

    # ---------------- classifier table
    rows = []
    def add(name, m, note=""):
        rows.append({"model": name, "precision": fmt(m.get("precision")), "recall": fmt(m.get("recall")), "f1": fmt(m.get("f1")),
                     "auc": fmt(m.get("auc")), "auprc": fmt(m.get("auprc")), "brier": fmt(m.get("brier")),
                     "accuracy": fmt(m.get("accuracy")), "balanced_accuracy": fmt(m.get("balanced_accuracy")), "note": note})
    add("PRIMARY LR (t_F1)", cls["test_primary_tF1"], "pre-registered")
    add("PRIMARY LR (t_P90, strict)", cls["test_primary_tP90"])
    for k, v in cls["test_comparisons"].items():
        add(f"comparison: {k}", v["metrics"], f"F1 diff primary-this {fmt(v['paired_primary_minus_this']['f1_diff'])}")
    for k, v in cls["test_baselines"].items():
        add(f"baseline: {k}", v["metrics"], f"F1 diff primary-this {fmt(v['paired_primary_minus_this']['f1_diff'])}")
    add("secondary: train D2+D4a", cls["secondary_train_plus_d4a"]["metrics"])
    write_csv(RESULTS / "classifier_table.csv", rows)
    # ---------------- merger table
    mrows = []
    for ts, out in mer["test"].items():
        for k, v in out.items():
            if k in ("by_stratum", "baseline_note"):
                continue
            m = v.get("metrics", v)
            mrows.append({"test_set": ts, "model": k, "precision": fmt(m.get("precision")), "recall": fmt(m.get("recall")),
                          "f1": fmt(m.get("f1")), "auc": fmt(m.get("auc"))})
    write_csv(RESULTS / "merger_table.csv", mrows)

    # ---------------- frame audit (in-domain silver)
    labA = {c: v["label"] for c, v in audit.get("labels_A", {}).items()}
    labAdj = {c: v["label"] for c, v in audit.get("labels_adj", {}).items()}
    fa: dict = {"note": ("In-domain SILVER check: model A (gemini-2.5-flash-lite, DS4 codebook) labels on all frame phrases; "
                         "classifier/A disagreements adjudicated by claude-haiku-4.5. Silver = A where classifier and A agree, "
                         "adjudicator label where they disagree (optimistic for the classifier by design: agreement items "
                         "cannot count against it). The classifier's predictions were frozen before labels were requested.")}
    ids = [c["concept_id"] for c in concepts if c["concept_id"] in labA]
    if ids:
        yA = np.array([labA[i] == "CONCEPT" for i in ids], dtype=int)
        h = np.array([byid[i]["accepted_primary"] for i in ids], dtype=int)
        p = np.array([byid[i]["p_concept"] for i in ids])
        fa["n_labelled_A"] = len(ids)
        fa["label_dist_A"] = dict(Counter(labA[i] for i in ids))
        fa["classifier_vs_A"] = {"kappa": float(cohen_kappa_score(yA, h)), "confusion_A_rows_clf_cols": confusion_matrix(yA, h).tolist(),
                                 "metrics": boot_metrics(yA, p, h)}
        sil = []
        for i in ids:
            if (labA[i] == "CONCEPT") == bool(byid[i]["accepted_primary"]):
                sil.append(labA[i])
            else:
                sil.append(labAdj.get(i, labA[i]))
        ys = np.array([s == "CONCEPT" for s in sil], dtype=int)
        n_dis = int((yA != h).sum())
        n_adj = sum(1 for i in ids if i in labAdj)
        fa["n_disagreements"] = n_dis
        fa["n_adjudicated"] = n_adj
        fa["adjudicator_sided_with_classifier"] = int(sum(1 for i in ids if i in labAdj and (labAdj[i] == "CONCEPT") == bool(byid[i]["accepted_primary"])))
        fa["classifier_vs_adjudicated_silver"] = boot_metrics(ys, p, h)
        fa["llmA_vs_adjudicated_silver"] = point_metrics(ys, None, yA)
        for arm in ("main", "reference"):
            ii = np.array([byid[i]["arm"] == arm for i in ids])
            if ii.sum() > 5:
                fa[f"classifier_vs_adjudicated_silver_{arm}"] = point_metrics(ys[ii], p[ii] if len(set(ys[ii])) > 1 else None, h[ii])
        hs = np.array([byid[i]["accepted_strict"] for i in ids], dtype=int)
        fa["strict_vs_adjudicated_silver"] = point_metrics(ys, None, hs)
    # ---------------- rejection x sense_check_fail
    sc: dict = {}
    hyd = [c for c in concepts if c["hydrated"] and c["arm"] == "main"]
    def fisher(rows_, flag_key):
        a = sum(1 for c in rows_ if not c["accepted_primary"] and c[flag_key])
        b = sum(1 for c in rows_ if not c["accepted_primary"] and not c[flag_key])
        c_ = sum(1 for c in rows_ if c["accepted_primary"] and c[flag_key])
        d = sum(1 for c in rows_ if c["accepted_primary"] and not c[flag_key])
        orr, pv = fisher_exact([[a, b], [c_, d]])
        return {"table_rows_rejected_accepted_cols_flag_noflag": [[a, b], [c_, d]], "odds_ratio": float(orr), "fisher_p": float(pv), "n": len(rows_)}
    sc["hydrated_main_vs_DS1_sense_check_fail"] = fisher(hyd, "sense_check_fail_flag")
    for c in concepts:
        c["_proxy_fail"] = c["sense_proxy"] is not None and c["sense_proxy"] < 0.70
    sc["all_with_proxy_vs_proxy_fail"] = fisher([c for c in concepts if c["sense_proxy"] is not None], "_proxy_fail")
    # ---------------- rejected MAIN phrases + named fragments
    rej = [{"concept_id": c["concept_id"], "phrase": c["phrase"], "p_concept": c["p_concept"], "hydrated": c["hydrated"],
            "frame_llm_label_A": c["frame_llm_label_A"], "frame_llm_label_adj": c["frame_llm_label_adj"],
            "sense_final": c["sense_final"], "reason_top5": "; ".join(f"{n}:{v:+.2f}" for n, v in c["reason_top5"])}
           for c in sorted(concepts, key=lambda c: c["p_concept"]) if c["arm"] == "main" and not c["accepted_primary"]]
    write_csv(RESULTS / "rejected_main_phrases.csv", rej)
    named = {}
    for ph in NAMED_FRAGMENTS:
        m = [c for c in concepts if c["phrase"] == ph]
        named[ph] = ({"concept_id": m[0]["concept_id"], "p_concept": m[0]["p_concept"], "accepted_primary": m[0]["accepted_primary"],
                      "in_MAIN": m[0]["in_MAIN"], "frame_llm_label_A": m[0]["frame_llm_label_A"], "reason_top5": m[0]["reason_top5"]}
                     if m else "not in frame")
    # ---------------- counts
    def grp(c):
        of = c["origin_field"] or "unknown(pending)"
        return of if of in ("Physics and Astronomy", "Computer Science") else ("unknown(pending)" if of == "unknown(pending)" else "other")
    counts = {}
    for L in ("MAIN", "STRICT", "REFERENCE_ACCEPTED"):
        mem = [byid[i] for i in tp["lists"][L]]
        counts[L] = {"n": len(mem), "hydrated": sum(c["hydrated"] for c in mem), "pending": sum(not c["hydrated"] for c in mem),
                     "by_fold_hydrated_Fband": dict(Counter(f"{c['fold']}|{'hyd' if c['hydrated'] else 'pend'}|{c['F_band']}" for c in mem)),
                     "by_origin_group": dict(Counter(grp(c) for c in mem))}
    link_by_arm = {arm: dict(Counter(c["link_status"] for c in concepts if c["arm"] == arm)) for arm in ("main", "reference")}
    link_types = Counter(l["link_type"] + ":" + l["target_vocab"] for c in concepts for l in c["links"])
    la_items = la.get("items", {})
    la_summary = dict(Counter(la_items.values()))
    la_by_type = defaultdict(Counter)
    for c in concepts:
        for l in c["links"]:
            k = f"{c['concept_id']}|{l['target_vocab']}|{l['target_id']}"
            if k in la_items:
                la_by_type[l["link_type"]][la_items[k]] += 1
    spend = 0.0
    if (LOGS / "llm_spend.jsonl").exists():
        spend = sum(json.loads(l).get("cost", 0.0) for l in (LOGS / "llm_spend.jsonl").read_text().splitlines() if l.strip())
    wall = {}
    for f in ("s1_corpus", "s2_features", "s3_classifier", "s4_merger", "s5_link_calib", "s7b_merge_link"):
        for name, path in (("s1_corpus", "termhood_meta.json"),):
            pass
    wall = {"termhood_s": read_json(WORK / "termhood_meta.json").get("runtime_s") if (WORK / "termhood_meta.json").exists() else None,
            "embeddings_s": read_json(WORK / "emb" / "meta.json").get("runtime_s") if (WORK / "emb" / "meta.json").exists() else None,
            "classifier_s": cls.get("runtime_s"), "merger_s": mer.get("runtime_s"), "link_calibration_s": cal.get("runtime_s"),
            "merge_link_s": ml["meta"].get("runtime_s")}
    summary = {
        "test_population_sha256": tp_sha, "test_population_counts": tp["meta"]["counts"],
        "main_hydrated_now": tp["meta"]["main_hydrated_now"], "main_pending": tp["meta"]["main_pending"],
        "classifier": {"thresholds": cls["thresholds"], "primary_config": cls["primary_config"],
                       "test_primary_tF1": cls["test_primary_tF1"], "test_primary_tP90": cls["test_primary_tP90"],
                       "test_baselines": {k: v["metrics"] | {"paired_primary_minus_this": v["paired_primary_minus_this"]} for k, v in cls["test_baselines"].items()},
                       "test_comparisons": {k: v["metrics"] | {"paired_primary_minus_this": v["paired_primary_minus_this"]} for k, v in cls["test_comparisons"].items()},
                       "baseline_note": cls["baseline_note"], "silver_gold_200": cls.get("silver_gold_200"),
                       "secondary_3class": cls["secondary_3class"], "secondary_train_plus_d4a": cls["secondary_train_plus_d4a"],
                       "per_macro_domain": cls["per_macro_domain"], "human_anchors": cls["human_anchors"],
                       "label_status": "D2 targets are LLM-adjudicated SILVER labels (gemini-2.5-flash-lite + gpt-4.1-nano, haiku adjudication); no human gold on D2. Only the SemEval-2017/SciERC anchors are human-labelled."},
        "merger": {"thresholds": mer["thresholds"], "test": mer["test"], "cluster_test": mer["cluster_test"],
                   "leakage_guard": mer["leakage_guard"], "lr_coefficients": mer["lr_coefficients"]},
        "linker": {"frozen": cal["frozen"], "picks": {e: v["pick"] for e, v in cal["encoders"].items()},
                   "stage1_nil_falselink": {e: v["stage1_falselink_rate_nil"] for e, v in cal["encoders"].items()},
                   "top1_inKB_accuracy": {e: v["top1_accuracy_inKB_no_threshold"] for e, v in cal["encoders"].items()},
                   "sanity": cal.get("sanity"), "n_queries": cal["n_queries"]},
        "frame_application": {"shift_diagnostic": tp["meta"]["shift_diagnostic"], "frame_audit": fa,
                              "sense_validation": audit.get("sense_validation"), "rejection_vs_sense_fail": sc,
                              "named_fragments": named, "n_rejected_main": len(rej), "counts": counts,
                              "link_status_by_arm": link_by_arm, "link_types": dict(link_types), "link_audit": la_summary,
                              "link_audit_by_link_type": {k: dict(v) for k, v in la_by_type.items()},
                              "d5_link_status": ml.get("d5_link_status"), "merge_multi_clusters_primary": ml.get("merge_multi_clusters_primary"),
                              "merge_multi_clusters_strict": ml.get("merge_multi_clusters_strict"), "merge_meta": ml["meta"]},
        "t1_reused_code": t1,
        "budget": {"llm_usd_total_this_artifact": round(spend, 5), "wikidata_live_calls": ml["meta"].get("wikidata_live_calls"),
                   "openalex_calls": 0, "wall_time_s": wall},
    }
    write_json(RESULTS / "summary.json", summary)

    # ---------------- method_out.json (exp_gen_sol_out)
    ds = []
    cv_t = cls["test_baselines"]["cvalue_threshold"].get("t")
    ex = []
    for c in concepts:
        e = {"input": c["phrase"], "output": "ACCEPTED" if c["accepted_primary"] else "REJECTED",
             "predict_concept_lr_p": f"{c['p_concept']:.4f}",
             "predict_concept_lr": "ACCEPTED" if c["accepted_primary"] else "REJECTED",
             "predict_concept_lr_strict": "ACCEPTED" if c["accepted_strict"] else "REJECTED",
             "predict_concept_lr_notermhood": "ACCEPTED" if c["accepted_primary_notermhood"] else "REJECTED",
             "predict_llm_label_A": str(c["frame_llm_label_A"]),
             "predict_link_status": c["link_status"]}
        for k, v in c.items():
            if k.startswith("_") or k == "phrase":
                continue
            e[f"metadata_{k}"] = v
        ex.append(e)
    ds.append({"dataset": "frozen_frame_426_grounded", "examples": ex})
    d2p = read_json(RESULTS / "d2_test_predictions.json")
    ex = [{"input": r["key"], "output": r["silver"], "predict_concept_lr": "CONCEPT" if r["accept_tF1"] else "NOT_CONCEPT",
           "predict_concept_lr_p": f"{r['p']:.4f}", "predict_llm_label_A": str(r["label_A"]), "predict_llm_label_B": str(r["label_B"]),
           "metadata_macro_domain": r["macro_domain"], "metadata_accept_strict": r["accept_tP90"]} for r in d2p]
    ds.append({"dataset": "d2_test_silver_300", "examples": ex})
    mp = read_json(RESULTS / "merger_test_predictions.json")
    for name, rows_ in mp.items():
        ex = [{"input": json.dumps({"a": r["a"], "b": r["b"]}, ensure_ascii=False), "output": "SAME" if r["y"] else "DIFFERENT",
               "predict_merger_lr": "SAME" if r["merge"] else "DIFFERENT", "predict_merger_lr_p": f"{r['p']:.4f}",
               "predict_baseline_normalised_equal": "SAME" if r["norm_equal"] else "DIFFERENT",
               "predict_baseline_cos_minilm": "SAME" if r["cos_ge_t"] else "DIFFERENT",
               "predict_baseline_token_set_85": "SAME" if r["token_set"] >= 0.85 else "DIFFERENT",
               "metadata_stratum": r["stratum"]} for r in rows_]
        ds.append({"dataset": f"merger_{name}", "examples": ex})
    method_out = {"metadata": {"method_name": "concept-cleaning models (classifier + variant merger + NIL-aware linker) applied to the frozen frame",
                               "test_population_sha256": tp_sha, "summary": summary,
                               "artifacts": {"test_population": "results/test_population.json", "models": "models/",
                                             "figures": ["results/fig_reliability.png", "results/fig_link_calibration.png"]}},
                  "datasets": ds}
    (METHOD_OUT).write_text(json.dumps(method_out, ensure_ascii=False, indent=1, default=str))
    logger.info(f"method_out.json written ({time.time() - t0:.0f}s); MAIN {tp['meta']['counts']}")


if __name__ == "__main__":
    main()
