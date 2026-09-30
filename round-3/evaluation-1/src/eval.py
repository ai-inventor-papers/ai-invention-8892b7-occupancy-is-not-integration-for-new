#!/usr/bin/env python3
"""Iteration-3 evaluation: numbers of record (Part 1), R1a turnover pre-check on seen data (Part 2), decision rules and
tables (Part 3). Runs the three parts in dependency order and assembles eval_out.json (exp_eval_sol_out schema).

Usage:  uv run eval.py            (or .venv/bin/python eval.py)
All inputs are read-only iteration-2 artifacts; $0, CPU only, no network.
"""
from __future__ import annotations

import json
import math
import time

import numpy as np
from loguru import logger

import common as K


def num(x) -> float | None:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) else None


def evals(d: dict) -> dict:
    """eval_* fields must be numbers: keep finite numerics only (bools -> 0/1)."""
    out = {}
    for k, v in d.items():
        if isinstance(v, bool):
            out[f"eval_{k}"] = int(v)
        else:
            n = num(v)
            if n is not None:
                out[f"eval_{k}"] = n
    return out


@logger.catch(reraise=True)
def main() -> None:
    K.setup_logging("eval")
    t0 = time.time()
    import part1_record
    import part2_r1a
    import part3_rules
    logger.info("PART 2 (R1a) ...")
    r1a = part2_r1a.main()
    logger.info("PART 1 (numbers of record) ...")
    rec_sum = part1_record.main()
    K.setup_logging("eval")
    logger.info("PART 3 (rules and tables) ...")
    p3 = part3_rules.main()
    K.setup_logging("eval")
    rec = K.load_json(K.RES / "record_of_numbers.json")["rows"]
    byid = {r["id"]: r for r in rec}
    ev = {(r["population"], r["spec"]): r for r in r1a["event"]}
    corr = {(c["population"], c["pair"]): c for c in r1a["correlations"]}
    rules = p3["rules"]
    audit = p3["audit"]

    def rv(i: str) -> float | None:
        return num(byid[i]["value"]) if i in byid else None

    m = dict(record_n_rows=rec_sum["n_rows"], record_n_recomputed=rec_sum["n_recomputed"], record_n_not_rederivable=rec_sum["n_not_rederivable"],
             record_n_flags=rec_sum["n_flags"])
    for f, c in rec_sum["n_flags_by_type"].items():
        m[f"record_n_flag_{f}"] = c
    m.update(classifier_precision=rv("B1.clf.tF1.precision"), classifier_recall=rv("B1.clf.tF1.recall"), classifier_accuracy=rv("B1.clf.tF1.accuracy"),
             classifier_f1=rv("B1.clf.tF1.f1"), classifier_auc=rv("B1.clf.auc"), classifier_kappa=rv("B1.clf.tF1.kappa"),
             majority_all_positive_f1=rv("B1.base.all_positive_f1"), classifier_f1_minus_all_positive=rv("B1.clf.delta_f1_vs_allpos"),
             classifier_minus_llmA_f1=rv("B1.clf_minus_llmA.f1"), classifier_minus_llmB_f1=rv("B1.clf_minus_llmB.f1"),
             main_E_up_logit_delta_auc=rv("B3.E_up.logit.delta_auc"), main_E_up_hgb_delta_auc=rv("B3.E_up.hgb.delta_auc"))
    for pop in ("main", "mesh"):
        r = ev[(pop, "P")]
        m.update({f"{pop}_S_raw": r["S_raw"], f"{pop}_S_raw_cc": r["S_raw_cc"], f"{pop}_S_res": r["S_res"], f"{pop}_S_res_ci_lo": r["S_res_ci"][0],
                  f"{pop}_S_res_ci_hi": r["S_res_ci"][1], f"{pop}_S_fit": r["S_fit"], f"{pop}_retained": r["retained"],
                  f"{pop}_retained_ci_lo": r["retained_ci"][0], f"{pop}_retained_ci_hi": r["retained_ci"][1], f"{pop}_mde_res_sd": r["mde_res_in_sd"],
                  f"{pop}_n_treated_res": r["n_treated_res"], f"{pop}_gate_S_exact": int(r1a["gate"][pop]["S_exact"]),
                  f"{pop}_gate_passed": int(r1a["gate"][pop]["passed"]),
                  f"{pop}_verdict_not_reducible": int(r1a["verdicts"][pop]["verdict"].startswith("NOT REDUCIBLE")),
                  f"{pop}_verdict_largely_turnover": int(r1a["verdicts"][pop]["verdict"].startswith("LARGELY")),
                  f"{pop}_retained_volume_only_V0": ev[(pop, "V0")]["retained"], f"{pop}_retained_spec_R_rarefied": ev[(pop, "R")]["retained"],
                  f"{pop}_neg_control_retained_vs_V0": r1a["controls"][pop]["NEG"]["retained_vs_V0"],
                  f"{pop}_pos_oracle_retained": r1a["controls"][pop]["POS_ORACLE"]["retained"],
                  f"{pop}_pos_closure_raw_retained": r1a["controls"][pop]["POS"]["retained"]})
        for key in ("new_rel", "novelty", "beta_sim", "beta_sim_rar"):
            c = corr[(pop, f"closure~{key}")]
            m[f"{pop}_r_within_closure_{key}"] = c.get("r_within")
            m[f"{pop}_r_within_closure_{key}_ci_lo"] = c.get("r_within_ci", [None, None])[0]
            m[f"{pop}_r_within_closure_{key}_ci_hi"] = c.get("r_within_ci", [None, None])[1]
    pr = r1a["pooling"]
    m.update(ivw_S_res=pr["P"]["res"]["S_ivw"], ivw_se_res=pr["P"]["res"]["se_ivw"], ivw_S_res_ci_lo=pr["P"]["res"]["ci"][0],
             ivw_S_res_ci_hi=pr["P"]["res"]["ci"][1], Q_res=pr["P"]["res"]["Q"], p_Q_res=pr["P"]["res"]["p_Q"], I2_res=pr["P"]["res"]["I2"],
             ivw_S_raw_cc=pr["P"]["raw_cc"]["S_ivw"], Q_raw_cc=pr["P"]["raw_cc"]["Q"], ivw_S_raw_recorded=pr["raw_recorded_files"]["S_ivw"],
             Q_raw_recorded=pr["raw_recorded_files"]["Q"], pooled_retained=pr["pooled_verdict"]["retained"],
             pooled_retained_ci_lo=pr["pooled_verdict"]["retained_ci"][0], pooled_retained_ci_hi=pr["pooled_verdict"]["retained_ci"][1],
             main_placebo_S_res=r1a["controls"]["main"]["PLACEBO"]["S_res"],
             rule_a_triggered=int(rules["a"]["triggered"]), rule_b_pilot_only=int(rules["b"]["pilot_only"]), rule_c_met=int(rules["c"]["met"]),
             rule_d_sealed=int(rules["d"]["sealed"]), heldout_id_hits_exp3_exp4=audit["hits_exp3_exp4_total"],
             heldout_files_scanned=audit["files_scanned_exp3_exp4"], heldout_ids_dataset5=audit["id_sets"]["n_heldout_dataset5"],
             heldout_iter1_subset=int(audit["id_sets"]["iter1_subset_of_dataset5"]),
             aligned_n_interpretable=int(p3["aligned"].interpretable.sum()), aligned_n_file_reproduced=int(p3["aligned"].ivw_agrees_file.sum()),
             coverage_n_done=int((p3["coverage"].status == "done").sum()), coverage_n_partial=int((p3["coverage"].status == "partial").sum()),
             coverage_n_planned=int((p3["coverage"].status == "planned").sum()), runtime_s=time.time() - t0)
    metrics = {k: float(v) for k, v in m.items() if num(v) is not None}

    # ---------------- datasets
    ds_rec = []
    for r in rec:
        ex = {"input": r["claim"], "output": "" if r["value"] is None else f"{r['value']:.6g}",
              "metadata_id": r["id"], "metadata_block": r["block"], "metadata_flag": r["flag"], "metadata_unit": r["unit"],
              "metadata_estimator": r["estimator"], "metadata_source_path": r["source_path"], "metadata_source_key": r["source_key"],
              "metadata_recomputed": r["recomputed"], "metadata_recompute_method": r["recompute_method"], "metadata_note": r["note"],
              "metadata_report_line": r["report_line"], "predict_report_value": "" if r["report_value"] is None else f"{r['report_value']:g}"}
        if r.get("hash_hex"):
            ex["output"] = r["hash_hex"]
            ex["metadata_hash_match"] = r.get("hash_match")
        ex.update(evals(dict(value=r["value"], ci_lo=r["ci_lo"], ci_hi=r["ci_hi"], n=r["n"], report_value=r["report_value"],
                             agrees=r["agrees"] if r["agrees"] is not None else None, flag_ok=r["flag"] in ("OK", "MISSING_IN_REPORT"))))
        ds_rec.append(ex)
    ds_r1a = []
    for r in r1a["event"]:
        ex = {"input": f"R1a event study E_up closure, population={r['population']}, residualisation spec={r['spec']} ({K.HEADER})",
              "output": r["verdict_rule_applied"], "metadata_population": r["population"], "metadata_spec": r["spec"],
              "metadata_diff_k_raw": r["diff_k_raw"], "metadata_diff_k_res": r["diff_k_res"], "metadata_header": K.HEADER}
        ex.update(evals({k: r[k] for k in ("S_raw", "S_raw_cc", "S_res", "S_res_se", "S_res_p", "S_fit", "retained", "mde_res", "mde_res_in_sd",
                                           "n_treated_raw", "n_treated_res", "treated_lost", "retained_boot_dropped")}))
        ex.update(evals(dict(S_res_ci_lo=r["S_res_ci"][0], S_res_ci_hi=r["S_res_ci"][1], retained_ci_lo=r["retained_ci"][0],
                             retained_ci_hi=r["retained_ci"][1], S_fit_ci_lo=r["S_fit_ci"][0], S_fit_ci_hi=r["S_fit_ci"][1])))
        ds_r1a.append(ex)
    ds_corr = []
    for c in r1a["correlations"]:
        if "r_within" not in c:
            continue
        ex = {"input": f"Within-concept correlation {c['pair']} ({c['x']} vs {c['y']}), population={c['population']}",
              "output": f"{c['r_within']:.3f} [{c['r_within_ci'][0]:.3f}, {c['r_within_ci'][1]:.3f}]", "metadata_role": c["role"]}
        ex.update(evals(dict(r_within=c["r_within"], r_within_ci_lo=c["r_within_ci"][0], r_within_ci_hi=c["r_within_ci"][1],
                             rho_within=c["rho_within"], r_pooled=c["r_pooled"], n_concepts=c["n_concepts"], n_rows=c["n_rows"])))
        ds_corr.append(ex)
    ds_al = []
    for r in p3["aligned"].to_dict("records"):
        ex = {"input": f"Aligned block {r['label']} x {r['indicator']}: MeSH vs main S, IVW and Q",
              "output": f"S_mesh {r['S_mesh']:.3f}, S_main {r['S_main']:.3f}, IVW {r['S_ivw_ciwidth_se']:.3f}, Q {r['Q_ciwidth_se']:.2f}, "
                        f"interpretable={r['interpretable']}", "metadata_note": r["note"]}
        ex.update(evals({k: v for k, v in r.items() if k not in ("label", "indicator", "note")}))
        ds_al.append(ex)
    ds_rules = []
    for k in "abcd":
        rr = rules[k]
        ex = {"input": f"Decision rule ({k}): {rr.get('text') or rr.get('condition')}", "output": rr["verdict"],
              "metadata_text_status": rr["text_status"], "metadata_source": rr["source"]}
        flag = {"a": rr.get("triggered"), "b": rr.get("pilot_only"), "c": rr.get("met"), "d": rr.get("sealed")}[k]
        ex["eval_rule_outcome"] = int(bool(flag))
        if k == "a":
            ex.update(evals(dict(gate_a_share=rr["value"], graft_events_total=rr["graft_events"]["total"], graft_events_kw5=rr["graft_events"]["kw5"])))
        if k == "b":
            ex.update(evals(dict(realised_N_c=rr["realised_N_c"], mde_delta_auc_070=rr["mde_delta_auc_base070"], mde_delta_auc_080=rr["mde_delta_auc_base080"])))
        if k == "c":
            ex["metadata_per_precursor"] = rr["per_precursor"]
            ex.update(evals(dict(n_precursor_rows_all_met=sum(c["all_met"] for c in rr["per_precursor"]))))
        if k == "d":
            ex.update(evals(dict(hits_exp3_exp4=rr["hits_exp3_exp4"], files_scanned=rr["files_scanned"])))
            ex["metadata_exp2_caveat"] = rr["exp2_caveat"]
        ds_rules.append(ex)
    ds_cov = []
    for r in p3["coverage"].to_dict("records"):
        ds_cov.append({"input": f"Coverage of {r['item']}", "output": r["status"], "metadata_evidence": r["evidence"], "metadata_gap": r["gap"],
                       "metadata_scheduled": r["scheduled"], "eval_status_score": {"done": 1.0, "partial": 0.5, "planned": 0.0}[r["status"]]})
    out = {
        "metadata": {
            "evaluation_name": "Fix the record and test closure vs turnover (iteration 3, gen_art_evaluation_1)",
            "description": "Part 1 numbers of record with drift flags vs iter_3/gen_strat/current_report.md; Part 2 R1a turnover pre-check on the two "
                           "already-screened populations; Part 3 decision rules (a)-(d), aligned-block table, held-out seal audit, coverage.",
            "header": K.HEADER,
            "inputs": {k: v for k, v in K.ART_IDS.items()},
            "r1a_spec_sha256": r1a["spec_sha256"],
            "r1a_verdicts": {k: v["verdict"] for k, v in r1a["verdicts"].items()},
            "rules": {k: rules[k]["verdict"] for k in "abcd"},
            "record_flag_counts": rec_sum["n_flags_by_type"],
            "notes": ["All paths are relative to the run root.", "Q is underpowered at k = 2; it is not a test of agreement.",
                      "MeSH reproduction gate: S exact, CI off by 0.025 because exp_4's shared RNG stream cannot be replayed (recorded CI lies inside the "
                      "30-seed Monte-Carlo range).", "Deviation D1: MeSH SPEC P uses beta_sim_raw (the column computed with the main-pool code); "
                      "plan-literal beta_sim is sensitivity B_native."],
        },
        "metrics_agg": metrics,
        "datasets": [dict(dataset="numbers_of_record", examples=ds_rec), dict(dataset="r1a_results", examples=ds_r1a),
                     dict(dataset="r1a_within_concept_correlations", examples=ds_corr), dict(dataset="aligned_block", examples=ds_al),
                     dict(dataset="decision_rules", examples=ds_rules), dict(dataset="coverage", examples=ds_cov)],
    }
    K.dump(out, K.WS / "eval_out.json")
    logger.info(f"eval_out.json written: {len(metrics)} metrics, datasets {[len(d['examples']) for d in out['datasets']]}, {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
