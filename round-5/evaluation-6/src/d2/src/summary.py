"""STAGE 16: results/d2_summary.json — headline numbers, each traced to the file it comes from."""
from __future__ import annotations

import json

from loguru import logger

from config import RESULTS, WS


def _j(name: str) -> dict:
    p = RESULTS / name
    return json.loads(p.read_text()) if p.exists() else {}


def run() -> dict:
    m = _j("d2_models.json")
    pl = _j("placebo_summary.json")
    lb = _j("labels_summary.json")
    pw = _j("power_heldout.json")
    fs = _j("features_summary.json")
    ev = _j("events_summary.json")
    rp = _j("repro_events_iter1.json")
    oos = _j("oos_check.json")
    au = _j("audit_rederive.json")

    def coef(k):
        r = m[k]
        return {v: {"b": r["coef"][v], "se": r["se"][v], "p_crv1": r["p"][v],
                    "p_wild": (r.get("p_wild") or {}).get(v), "irr_per_sd": r["irr_sd"][v],
                    "irr_per_sd_ci95": r["ci_irr_sd"][v], "irr_per_0.1": r["irr_01"][v]}
                for v in ["A_cont", "CT"] if v in r["coef"]} | {"N": r["n_retained"], "G": r["G"]}

    s = {
        "question": "RQ2-D2: at host entry, does anchoring into host-native partners (grafting) or co-transfer of "
                    "origin companions (toolkit) predict newcomer uptake of the concept in the host over the next 5 years?",
        "reproduction_iter1_events": {"pass": rp.get("pass"), "counts": [rp.get("n_events_all"), rp.get("n_events_kw5"),
                                                                        rp.get("n_events_kw5_e_ge_F")],
                                      "source": "results/repro_events_iter1.json"},
        "exp3_indicator_reproduction": "N/A: this artifact uses distinct-partner centrality, not exp_3 snapshot "
                                       "indicators (plan fallback 2 path); D3 closure is available from exp_3 directly",
        "events": {**ev, "source": "results/events_summary.json"},
        "nativeness": {"native_share_at_0.5": fs.get("native_share_tags_main_kw5_at_0.5"),
                       "native_share_at_0.3": fs.get("native_share_tags_main_kw5_at_0.3"),
                       "fallback6_triggered": fs.get("fallback6_triggered"),
                       "primary_A": "A_cont (mean host share of partners' pre-entry works)",
                       "mean_A_cont": fs.get("mean_A_cont"), "sd_A_cont": fs.get("sd_A_cont"),
                       "mean_CT": fs.get("mean_CT"), "tag_weighted_coverage": fs.get("tag_weighted_cov"),
                       "partition_t03": fs.get("partition_means_t03"), "source": "results/features_summary.json"},
        "primary_fe_concept_x_e_plus_d_x_e": {**coef("M1"), "decision": m.get("decision_primary")},
        "coprimary_fe_concept_plus_e_plus_d": {**coef("M1_secondary"), "decision": m.get("decision_secondary")},
        "coarsening_concept_x_2yr_plus_d_x_e": {**coef("M1_coarse_cx2y"), "decision": m.get("decision_M1_coarse_cx2y")},
        "concept_plus_d_x_e": {**coef("M1_c_plus_dxe"), "decision": m.get("decision_M1_c_plus_dxe")},
        "fallback3_thin_cells": m.get("fallback3_thin_cells"),
        "secondary_outcomes": {k: coef(k) for k in ["M1_Y_all", "M1_Y_lenient", "M1_Y_all_secondary",
                                                    "M1_Y_lenient_secondary"]},
        "EST_bin_LPM": {"primary": m.get("EST_bin_LPM"), "secondary": m.get("EST_bin_LPM_secondary")},
        "pyfixest_crosscheck": {k: m.get("pyfixest_crosscheck", {}).get(k) for k in ["pass_coef_1e-4", "pass_se_rel_1e-3",
                                                                                       "n_pf"]},
        "placebo": {k: {kk: pl[k][kk] for kk in ["z_A_obs", "placebo_z_mean", "placebo_z_sd",
                                                   "perm_p_two_sided_z (primary placebo p)",
                                                   "perm_p_two_sided_per_sd_effect", "label_shuffle_p_two_sided_z"]}
                    for k in ["primary", "secondary"] if k in pl} | {"source": "results/placebo_summary.json"},
        "labels": {"anchored_share_screen": lb.get("labels", {}).get("screen", {}).get("anchored_share"),
                   "establishment_by_label": lb.get("establishment_by_label_screen_MAIN"),
                   "occupancy": lb.get("occupancy"), "integration_entropy": lb.get("integration_entropy"),
                   "source": "results/labels_summary.json"},
        "out_of_sample": {k: oos.get(k) for k in ["deviance_diff_M1_minus_M0", "deviance_diff_ci95_concept_bootstrap",
                                                  "spearman_M0", "spearman_M1"]} | {"source": "results/oos_check.json"},
        "power_heldout": {k: pw.get(k) for k in ["heldout_design", "MDE_irr_per_sd_power80", "screen_irr_per_sd",
                                                 "adequately_powered", "reps_per_cell"]} | {"source": "results/power_heldout.json"},
        "audit": {"all_match": au.get("all_match"), "headline_secondary": au.get("headline_secondary"),
                  "source": "results/audit_rederive.json"},
        "robustness_table": "results/d2_robustness.csv",
        "heldout_spec": {"file": "heldout_spec.json",
                         "sha256": (WS / "heldout_spec.sha256").read_text().split()[0]
                         if (WS / "heldout_spec.sha256").exists() else None},
    }
    (RESULTS / "d2_summary.json").write_text(json.dumps(s, indent=1, default=float))
    logger.info("d2_summary.json written")
    return s
