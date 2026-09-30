#!/usr/bin/env python3
"""Writes sources.yaml: file aliases (artifact id + run-root-relative path) and registry keys (selectors).

This file holds ONLY addresses (pointers, CSV filters, regexes). No plotted number is typed here.
"""
from __future__ import annotations

from pathlib import Path

import yaml

WS = Path(__file__).resolve().parents[1]
I2, I3, I4 = ("round-2", "round-3",
              "round-4")

FILES = {
    # art_2Cd2JJypeGuA  (exp_7, D2 screen)
    "d2_summary": ("art_2Cd2JJypeGuA", f"{I3}/gen_art_experiment_7/results/d2_summary.json"),
    "d2_prereg": ("art_2Cd2JJypeGuA", f"{I3}/gen_art_experiment_7/results/d2_prereg.json"),
    # art_WZ8fbLn79nCq  (eval_2, sealed held-out + G rows)
    "ho_post": ("art_WZ8fbLn79nCq", f"{I4}/gen_art_evaluation_2/results/heldout_post.json"),
    "ho_conf": ("art_WZ8fbLn79nCq", f"{I4}/gen_art_evaluation_2/d2/results/heldout_confirmation.json"),
    "g_screen": ("art_WZ8fbLn79nCq", f"{I4}/gen_art_evaluation_2/results/g_screen_summary.json"),
    "g_heldout": ("art_WZ8fbLn79nCq", f"{I4}/gen_art_evaluation_2/results/g_heldout_summary.json"),
    "g_pooled": ("art_WZ8fbLn79nCq", f"{I4}/gen_art_evaluation_2/results/g_pooled_summary.json"),
    "grows_screen": ("art_WZ8fbLn79nCq", f"{I4}/gen_art_evaluation_2/results/g_screen_rows.csv"),
    "grows_heldout": ("art_WZ8fbLn79nCq", f"{I4}/gen_art_evaluation_2/results/g_heldout_rows.csv"),
    "grows_pooled": ("art_WZ8fbLn79nCq", f"{I4}/gen_art_evaluation_2/results/g_pooled_rows.csv"),
    "record": ("art_WZ8fbLn79nCq", f"{I4}/gen_art_evaluation_2/results/record_of_numbers.csv"),
    "robust_recount": ("art_WZ8fbLn79nCq", f"{I4}/gen_art_evaluation_2/results/robustness_recount.json"),
    "ho_robust": ("art_WZ8fbLn79nCq", f"{I4}/gen_art_evaluation_2/results/heldout_robustness.csv"),
    "audit_perm": ("art_WZ8fbLn79nCq", f"{I4}/gen_art_evaluation_2/audit/audit_perm.json"),
    "mech_label": ("art_WZ8fbLn79nCq", f"{I4}/gen_art_evaluation_2/results/mechanism_label.json"),
    # art_XGdzjWgi-a88  (exp_9, MeSH replication)
    "g4_summary": ("art_XGdzjWgi-a88", f"{I4}/gen_art_experiment_9/results/g4_summary.json"),
    "g4_models": ("art_XGdzjWgi-a88", f"{I4}/gen_art_experiment_9/results/g4_models.json"),
    "g4_compare": ("art_XGdzjWgi-a88", f"{I4}/gen_art_experiment_9/results/comparison_main_vs_mesh.csv"),
    "power_mesh": ("art_XGdzjWgi-a88", f"{I4}/gen_art_experiment_9/results/power_mesh.json"),
    "placebo_mesh": ("art_XGdzjWgi-a88", f"{I4}/gen_art_experiment_9/results/placebo_mesh.json"),
    "mesh_load": ("art_XGdzjWgi-a88", f"{I4}/gen_art_experiment_9/results/mesh_load_summary.json"),
    # art_zw_JJGsUFSnd  (eval_3, RQ1 held-out + D3)
    "r1_summary": ("art_zw_JJGsUFSnd", f"{I4}/gen_art_evaluation_3/results/r1/r1_summary.json"),
    "r1_panel": ("art_zw_JJGsUFSnd", f"{I4}/gen_art_evaluation_3/results/tables/r1_pooled_panel_screen_vs_heldout.csv"),
    "r1_es": ("art_zw_JJGsUFSnd", f"{I4}/gen_art_evaluation_3/results/tables/r1_event_study_screen_vs_heldout.csv"),
    "r1_iv": ("art_zw_JJGsUFSnd", f"{I4}/gen_art_evaluation_3/results/tables/r1_iv_synthesis_descriptive.csv"),
    "r1_balance": ("art_zw_JJGsUFSnd", f"{I4}/gen_art_evaluation_3/results/tables/r1_balance_smd.csv"),
    "r1_nflow": ("art_zw_JJGsUFSnd", f"{I4}/gen_art_evaluation_3/results/tables/r1_n_flow.csv"),
    "d3_results": ("art_zw_JJGsUFSnd", f"{I4}/gen_art_evaluation_3/results/d3/d3_results.json"),
    # art_mu0h0npvNX_u  (eval_4, rooting + cases)
    "rooting": ("art_mu0h0npvNX_u", f"{I4}/gen_art_evaluation_4/results/rooting.json"),
    "cases": ("art_mu0h0npvNX_u", f"{I4}/gen_art_evaluation_4/results/cases_rooting.json"),
    "case_entries": ("art_mu0h0npvNX_u", f"{I4}/gen_art_evaluation_4/results/case_entries.csv"),
    "case_interp": ("art_mu0h0npvNX_u", f"{I4}/gen_art_evaluation_4/results/case_interpretations.md"),
    # art_FZ2OCJwV6xHs  (eval_5, adopter mechanism)
    "enrich": ("art_FZ2OCJwV6xHs", f"{I4}/gen_art_evaluation_5/results/enrichment.json"),
    "vocab": ("art_FZ2OCJwV6xHs", f"{I4}/gen_art_evaluation_5/results/vocab_class.json"),
    "interact": ("art_FZ2OCJwV6xHs", f"{I4}/gen_art_evaluation_5/results/interaction.json"),
    "mech_results": ("art_FZ2OCJwV6xHs", f"{I4}/gen_art_evaluation_5/results/mechanism_results.json"),
    "frame": ("art_FZ2OCJwV6xHs", f"{I4}/gen_art_evaluation_5/results/frame_summary.json"),
    # art_htO_gJuUn6Pr  (exp_5, RQ1 screen)
    "exp5_pop": ("art_htO_gJuUn6Pr", f"{I3}/gen_art_experiment_5/results/main_population_hydrated.json"),
    "exp5_pred": ("art_htO_gJuUn6Pr", f"{I3}/gen_art_experiment_5/results/prediction.json"),
    # art_QKsLguxnGFQT  (exp_8, RQ2 typology/roles/cases)
    "typology": ("art_QKsLguxnGFQT", f"{I3}/gen_art_experiment_8/results/typology.json"),
    "roles": ("art_QKsLguxnGFQT", f"{I3}/gen_art_experiment_8/results/roles.json"),
    "leadlag": ("art_QKsLguxnGFQT", f"{I3}/gen_art_experiment_8/results/leadlag.json"),
    # F1-only optional sources
    "ds5_assemble": ("art_eR1Z7fMlOcxs", f"{I2}/gen_art_dataset_5/hyd/logs/assemble_summary.json"),
    "exp1_t0": ("art_BdBvbNuNU8E7", f"{I2}/gen_art_experiment_1/results/t0_counts.json"),
    "exp1_summary": ("art_BdBvbNuNU8E7", f"{I2}/gen_art_experiment_1/results/summary.json"),
    "exp2_gateA": ("art_yjFB8Spw2w6M", f"{I2}/gen_art_experiment_2/results/gate_a/gate_A_verdict.json"),
    "exp2_rederive": ("art_yjFB8Spw2w6M", f"{I2}/gen_art_experiment_2/results/audit/rederive.json"),
    "exp3_snap": ("art_mbFjmo5rbbf8", f"{I2}/gen_art_experiment_3/results/snapshot_summary.csv"),
    "exp6_d1": ("art_62TVG6A4f7Iy", f"{I3}/gen_art_experiment_6/results/d1/verdict.json"),
}
CASE_IDS_ALIAS = "cases"
for cid in ("c_3a8d31dc5fbf", "c_9cceb3c510be", "c_af9f1a649198", "c_1055d445e4c2"):
    for kind in ("ego", "alluvial"):
        FILES[f"img_{cid}_{kind}"] = ("art_QKsLguxnGFQT",
                                      f"{I3}/gen_art_experiment_8/figures/case_{cid}_{kind}.png")

KEYS: dict[str, dict] = {}

CI_CRV1 = "95% CRV1 Wald, concept-clustered"
CI_BOOT_OR = "95% concept-bootstrap percentile, B=1,000"
CI_BOOT_ES = "95% concept-bootstrap percentile, B=2,000"
CI_BOOT_G3 = "95% concept-bootstrap percentile, B=499"
CI_PLAC = "2.5-97.5% quantiles of 100 placebo-host draws"


def jp(key, alias, ptr, fold="", ci=""):
    KEYS[key] = {"file": alias, "json_pointer": ptr, "fold_label": fold, "ci_type": ci}


def cr(key, alias, filters, column, fold="", ci=""):
    KEYS[key] = {"file": alias, "csv_row": {"filters": filters, "column": column},
                 "fold_label": fold, "ci_type": ci}


def dv(key, formula, inputs, fold="", ci=""):
    KEYS[key] = {"derived": {"formula": formula, "inputs": inputs}, "fold_label": fold, "ci_type": ci}


# ---------------- F2: D2 forest ----------------
for fe, blk in (("co", "coprimary_fe_concept_plus_e_plus_d"), ("pri", "primary_fe_concept_x_e_plus_d_x_e")):
    for t in ("A", "CT"):
        term = "A_cont" if t == "A" else "CT"
        p = f"/{blk}/{term}"
        jp(f"f2.scr_{fe}.{t}.est", "d2_summary", f"{p}/irr_per_sd", "SCREEN", CI_CRV1)
        jp(f"f2.scr_{fe}.{t}.lo", "d2_summary", f"{p}/irr_per_sd_ci95/0", "SCREEN", CI_CRV1)
        jp(f"f2.scr_{fe}.{t}.hi", "d2_summary", f"{p}/irr_per_sd_ci95/1", "SCREEN", CI_CRV1)
        jp(f"f2.scr_{fe}.{t}.p", "d2_summary", f"{p}/p_crv1", "SCREEN")
        jp(f"f2.scr_{fe}.{t}.pw", "d2_summary", f"{p}/p_wild", "SCREEN")
        jp(f"f2.scr_{fe}.{t}.holm", "d2_summary", f"/{blk}/decision/holm_p/{term}", "SCREEN")
        jp(f"f2.scr_{fe}.{t}.N", "d2_summary", f"/{blk}/N", "SCREEN")
        jp(f"f2.scr_{fe}.{t}.G", "d2_summary", f"/{blk}/G", "SCREEN")
    jp(f"f2.scr_{fe}.reading", "d2_summary", f"/{blk}/decision/reading", "SCREEN")
for fe, blk, dec in (("co", "secondary", "decision_secondary"), ("pri", "primary", "decision_primary")):
    for t, sfx in (("A", "A"), ("CT", "CT")):
        p = f"/flags/{blk}"
        jp(f"f2.ho_{fe}.{t}.est", "ho_post", f"{p}/irr_sd_{sfx}", "CONFIRMATORY", CI_CRV1)
        jp(f"f2.ho_{fe}.{t}.lo", "ho_post", f"{p}/ci_{sfx}/0", "CONFIRMATORY", CI_CRV1)
        jp(f"f2.ho_{fe}.{t}.hi", "ho_post", f"{p}/ci_{sfx}/1", "CONFIRMATORY", CI_CRV1)
        jp(f"f2.ho_{fe}.{t}.p", "ho_post", f"{p}/p_{sfx}", "CONFIRMATORY")
        jp(f"f2.ho_{fe}.{t}.holm", "ho_conf", f"/{dec}/holm_p/{'A_cont' if t == 'A' else 'CT'}", "CONFIRMATORY")
        jp(f"f2.ho_{fe}.{t}.N", "ho_post", f"{p}/N", "CONFIRMATORY")
        jp(f"f2.ho_{fe}.{t}.G", "ho_post", f"{p}/G", "CONFIRMATORY")
    jp(f"f2.ho_{fe}.A.pw", "ho_post", f"/flags/{blk}/p_wild_A", "CONFIRMATORY")
    jp(f"f2.ho_{fe}.reading", "ho_post", f"/flags/{blk}/heldout_reading", "CONFIRMATORY")
jp("f2.retained_share", "d2_summary", "/fallback3_thin_cells/retained_share", "SCREEN")
dv("f2.retained_share_pct", "pct", ["f2.retained_share"], "SCREEN")
jp("f2.ho.kill_dead", "ho_post", "/flags/KILL_co_primary_dead", "CONFIRMATORY")
jp("f2.ho.primary_label", "ho_post", "/flags/primary_label", "CONFIRMATORY")
jp("f2.ho.mde_co", "d2_summary", "/power_heldout/MDE_irr_per_sd_power80/secondary", "SCREEN")
for fe, r in (("co", "R2"), ("pri", "R1")):
    for t in ("A", "CT"):
        term = "A_cont" if t == "A" else "CT"
        p = f"/rows/{r}/row/{term}"
        jp(f"f2.mesh_{fe}.{t}.est", "g4_models", f"{p}/irr_sd", "REPLICATION", CI_CRV1)
        jp(f"f2.mesh_{fe}.{t}.lo", "g4_models", f"{p}/ci_irr_sd/0", "REPLICATION", CI_CRV1)
        jp(f"f2.mesh_{fe}.{t}.hi", "g4_models", f"{p}/ci_irr_sd/1", "REPLICATION", CI_CRV1)
        jp(f"f2.mesh_{fe}.{t}.p", "g4_models", f"{p}/p_crv1", "REPLICATION")
        jp(f"f2.mesh_{fe}.{t}.pw", "g4_models", f"{p}/p_wild", "REPLICATION")
        jp(f"f2.mesh_{fe}.{t}.holm", "g4_summary", f"/holm_p_{r}/{term}", "REPLICATION")
        jp(f"f2.mesh_{fe}.{t}.N", "g4_models", f"/rows/{r}/row/N", "REPLICATION")
        jp(f"f2.mesh_{fe}.{t}.G", "g4_models", f"/rows/{r}/row/G", "REPLICATION")
    jp(f"f2.mesh_{fe}.mde", "g4_summary", f"/MDE80/{r}", "REPLICATION")
jp("f2.mesh.verdict", "g4_summary", "/g4_verdict", "REPLICATION")
ivw = {"estimate": "main_coprimary_1.30"}
cr("f2.ivw.A.est", "g4_compare", ivw, "ivw_pooled_irr_sd", "SUPPLEMENTARY/POOLED", "95% IVW fixed-effect")
cr("f2.ivw.A.lo", "g4_compare", ivw, "ivw_lo", "SUPPLEMENTARY/POOLED", "95% IVW fixed-effect")
cr("f2.ivw.A.hi", "g4_compare", ivw, "ivw_hi", "SUPPLEMENTARY/POOLED", "95% IVW fixed-effect")
cr("f2.ivw.A.I2", "g4_compare", ivw, "I2", "SUPPLEMENTARY/POOLED")
cr("f2.ivw.A.p_diff", "g4_compare", ivw, "p", "SUPPLEMENTARY/POOLED")
cr("f2.phys.A.est", "g4_compare", {"estimate": "main physics stratum (descriptive)"}, "irr_sd", "DESCRIPTIVE")
for fold, alias, lab in (("scr", "g_screen", "SCREEN"), ("ho", "g_heldout", "CONFIRMATORY"),
                         ("pool", "g_pooled", "SUPPLEMENTARY/POOLED")):
    jp(f"f2.plac_{fold}.A.est", alias, "/placebo_host/size/placebo_irr_sd_median", lab, CI_PLAC)
    jp(f"f2.plac_{fold}.A.lo", alias, "/placebo_host/size/placebo_irr_sd_q025_q975/0", lab, CI_PLAC)
    jp(f"f2.plac_{fold}.A.hi", alias, "/placebo_host/size/placebo_irr_sd_q025_q975/1", lab, CI_PLAC)
    jp(f"f2.plac_{fold}.A.N", alias, "/placebo_host/size/n_events", lab)
    jp(f"f2.plac_{fold}.A.share_sig", alias, "/placebo_host/size/share_pos_sig", lab)
jp("f2.plac_mesh.A.est", "g4_models", "/rows/S3/row/A_placebo/irr_sd", "REPLICATION", CI_CRV1)
jp("f2.plac_mesh.A.lo", "g4_models", "/rows/S3/row/A_placebo/ci_irr_sd/0", "REPLICATION", CI_CRV1)
jp("f2.plac_mesh.A.hi", "g4_models", "/rows/S3/row/A_placebo/ci_irr_sd/1", "REPLICATION", CI_CRV1)
jp("f2.plac_mesh.A.p", "g4_models", "/rows/S3/row/A_placebo/p_crv1", "REPLICATION")
jp("f2.plac_mesh.A.N", "g4_models", "/rows/S3/row/N", "REPLICATION")
jp("f2.plac_mesh.A.G", "g4_models", "/rows/S3/row/G", "REPLICATION")

# ---------------- caveats table ----------------
CAV = [
    ("cav.ho_crv1_p", "ho_post", "/flags/secondary/p_A", "CONFIRMATORY"),
    ("cav.ho_holm", "ho_conf", "/decision_secondary/holm_p/A_cont", "CONFIRMATORY"),
    ("cav.ho_wild", "ho_post", "/flags/secondary/p_wild_A", "CONFIRMATORY"),
    ("cav.ho_nat_perm", "ho_post", "/nativeness_permutation_placebo/secondary/perm_p_two_sided_z", "CONFIRMATORY"),
    ("cav.ho_plac_cal_screen", "ho_post", "/flags/secondary/p_placebo_cal_screenSD", "CONFIRMATORY"),
    ("cav.ho_plac_cal_heldout", "ho_post", "/flags/secondary/p_placebo_cal_heldoutSD", "CONFIRMATORY"),
    ("cav.ho_ashuffle_perm", "audit_perm", "/perm_p_two_sided", "CONFIRMATORY"),
    ("cav.ho_crv1_null_rej", "audit_perm", "/share_crv1_p_lt_0.05", "CONFIRMATORY"),
    ("cav.mesh_crv1_null_size", "g4_summary", "/size_calibration_post_hoc/null_size_at_0.05", "REPLICATION"),
    ("cav.mesh_size_cal_p", "g4_summary", "/size_calibration_post_hoc/calibrated_p_R2", "REPLICATION"),
    ("cav.mesh_nat_perm", "placebo_mesh", "/R2/perm_p_two_sided_z", "REPLICATION"),
    ("cav.het_co", "ho_post", "/flags/secondary/heterogeneity_screen_vs_heldout/p", "CONFIRMATORY"),
    ("cav.het_pri", "ho_post", "/flags/primary/heterogeneity_screen_vs_heldout/p", "CONFIRMATORY"),
    ("cav.estbin_co", "ho_post", "/EST_bin_LPM/secondary/p/A_cont", "CONFIRMATORY"),
    ("cav.estbin_pri", "ho_post", "/EST_bin_LPM/primary/p/A_cont", "CONFIRMATORY"),
    ("cav.oos_main", "ho_post", "/oos/deviance_diff_with_minus_controls", "CONFIRMATORY"),
    ("cav.oos_main_lo", "ho_post", "/oos/ci95_concept_bootstrap/0", "CONFIRMATORY"),
    ("cav.oos_main_hi", "ho_post", "/oos/ci95_concept_bootstrap/1", "CONFIRMATORY"),
    ("cav.oos_mesh", "g4_summary", "/oos/deviance_diff_method_minus_baseline", "REPLICATION"),
    ("cav.oos_mesh_lo", "g4_summary", "/oos/deviance_diff_ci95_concept_bootstrap/0", "REPLICATION"),
    ("cav.oos_mesh_hi", "g4_summary", "/oos/deviance_diff_ci95_concept_bootstrap/1", "REPLICATION"),
    ("cav.rob_sig", "robust_recount", "/secondary/n_significant", "SCREEN"),
    ("cav.rob_n", "robust_recount", "/secondary/n_rows_with_A", "SCREEN"),
    ("cav.rob_sig_ex", "robust_recount", "/secondary/n_significant_excl_base_and_strata", "SCREEN"),
    ("cav.rob_n_ex", "robust_recount", "/secondary/n_rows_excl_base_and_strata", "SCREEN"),
    ("cav.scr_wild", "d2_summary", "/coprimary_fe_concept_plus_e_plus_d/A_cont/p_wild", "SCREEN"),
    ("cav.scr_nat_perm", "d2_summary", "/placebo/secondary/perm_p_two_sided_z (primary placebo p)", "SCREEN"),
]
for k, a, p, f in CAV:
    jp(k, a, p, f)
# held-out co-primary spec rows (excluding the descriptive field strata): significant = p<0.05 and CI lower > 1
_hr = {"filters": {"fe": "secondary"}, "exclude_regex": {"spec": "^stratum"}}
KEYS["cav.ho_spec_rows_n"] = {"file": "ho_robust", "csv_count": _hr, "fold_label": "CONFIRMATORY"}
KEYS["cav.ho_spec_rows_sig"] = {"file": "ho_robust", "csv_count": {**_hr, "lt": {"p_A": 0.05},
                                "gt": {"irr_sd_A_lo": 1.0}}, "fold_label": "CONFIRMATORY"}
for _k, _num in (("scr_co.A", "D2 screen secondary A_cont IRR/SD (dry-run reproduction)"),
                 ("scr_pri.A", "D2 screen primary A_cont IRR/SD (dry-run reproduction)"),
                 ("ho_co.A", "D2 held-out secondary A_cont IRR/SD"), ("ho_pri.A", "D2 held-out primary A_cont IRR/SD"),
                 ("ho_co.CT", "D2 held-out secondary CT IRR/SD"), ("ho_pri.CT", "D2 held-out primary CT IRR/SD")):
    cr(f"f2.{_k}.record_label", "record", {"number": _num}, "label")

# ---------------- F3: mechanism ----------------
G1ROW, G1SINGLE = "G1-multi (co-primary FE)", "G1-single complement"
G2ROW = "G2a NATIVE+ADJACENT (native>=0.3, adjacent [0.05,0.3))"
FOLDS = (("scr", "grows_screen", "screen"), ("ho", "grows_heldout", "heldout"), ("pool", "grows_pooled", "pooled"))
for fk, alias, fname in FOLDS:
    for rid, row, var in (("g1", G1ROW, "A_cont"), ("g1s", G1SINGLE, "A_cont"), ("g2nat", G2ROW, "NAT"),
                          ("g2adj", G2ROW, "ADJ")):
        flt = {"row": row, "var": var, "fold": fname}
        for fld, col in (("est", "irr_sd"), ("lo", "irr_sd_lo"), ("hi", "irr_sd_hi"), ("p", "p"), ("N", "N"),
                         ("G", "G")):
            cr(f"f3.{rid}_{fk}.{fld}", alias, flt, col, "", CI_CRV1 if fld in ("est", "lo", "hi") else "")
    rec_flt = {"number": f"{G1ROW} | A_cont IRR/SD", "fold": fname}
    cr(f"f3.g1_{fk}.record_label", "record", rec_flt, "label")
    cr(f"f3.g1s_{fk}.record_label", "record", {"number": f"{G1SINGLE} | A_cont IRR/SD", "fold": fname}, "label")
    cr(f"f3.g2nat_{fk}.record_label", "record", {"number": f"{G2ROW} | NAT IRR/SD", "fold": fname}, "label")
    cr(f"f3.g2adj_{fk}.record_label", "record", {"number": f"{G2ROW} | ADJ IRR/SD", "fold": fname}, "label")
for rid, r, term in (("g1_mesh", "S1", "A_cont"), ("g2nat_mesh", "S2", "NATIVE"), ("g2adj_mesh", "S2", "ADJACENT")):
    jp(f"f3.{rid}.est", "g4_models", f"/rows/{r}/row/{term}/irr_sd", "REPLICATION", CI_CRV1)
    jp(f"f3.{rid}.lo", "g4_models", f"/rows/{r}/row/{term}/ci_irr_sd/0", "REPLICATION", CI_CRV1)
    jp(f"f3.{rid}.hi", "g4_models", f"/rows/{r}/row/{term}/ci_irr_sd/1", "REPLICATION", CI_CRV1)
    jp(f"f3.{rid}.p", "g4_models", f"/rows/{r}/row/{term}/p_crv1", "REPLICATION")
    jp(f"f3.{rid}.N", "g4_models", f"/rows/{r}/row/N", "REPLICATION")
    jp(f"f3.{rid}.G", "g4_models", f"/rows/{r}/row/G", "REPLICATION")
jp("f3.g1_mesh.mde", "power_mesh", "/MDE80_irr_per_sd/S1", "REPLICATION")
jp("f3.g1_ho.ratio", "g_heldout", "/G1_interaction/ratio_irr_multi_over_single", "CONFIRMATORY")
jp("f3.g1_ho.ratio_p", "g_heldout", "/G1_interaction/p_interaction", "CONFIRMATORY")
jp("f3.g1_ho.mde", "g_heldout", "/G1_status/mde", "CONFIRMATORY")
jp("f3.g1_ho.status", "g_heldout", "/G1_status/label", "CONFIRMATORY")
jp("f3.g2_ho.holm_nat", "g_heldout", f"/holm_G_family/{G2ROW}|NAT", "CONFIRMATORY")
jp("f3.g2_ho.holm_adj", "g_heldout", f"/holm_G_family/{G2ROW}|ADJ", "CONFIRMATORY")
jp("f3.g2_pool.wald_p", "g_pooled", "/G2a/wald_equal_per01/p", "SUPPLEMENTARY/POOLED")
G3KEYS = (("i", "G3(i+) + min_topic_score"), ("ii", "G3(ii) + host_topic_share + sec_host_share"),
          ("comb", "G3(combined)"))
for fk, alias, lab in (("scr", "g_screen", "SCREEN"), ("ho", "g_heldout", "CONFIRMATORY"),
                       ("pool", "g_pooled", "SUPPLEMENTARY/POOLED")):
    for gk, name in G3KEYS:
        jp(f"f3.g3_{fk}.{gk}.pct", alias, f"/G3_pct/{name}/pct", lab, CI_BOOT_G3)
        jp(f"f3.g3_{fk}.{gk}.lo", alias, f"/G3_pct/{name}/ci95/0", lab, CI_BOOT_G3)
        jp(f"f3.g3_{fk}.{gk}.hi", alias, f"/G3_pct/{name}/ci95/1", lab, CI_BOOT_G3)
    jp(f"f3.g3_{fk}.plac_size", alias, "/placebo_host/size/PASS", lab)
    jp(f"f3.g3_{fk}.plac_prox", alias, "/placebo_host/prox/PASS", lab)
    jp(f"f3.g3_{fk}.iii_cov", alias, "/G3_iii_coverage/share_events_with_covered_paper", lab)
OR_TERMS = (("e_any", "enrich", "/m2/terms/E_any"), ("e_neg", "enrich", "/m2/terms/E_neg"),
            ("e_plac", "enrich", "/m_plac/terms/E_plac"), ("e_for", "vocab", "/m_voc/terms/E_for"),
            ("e_adj", "vocab", "/m_voc/terms/E_adj"), ("e_nat", "vocab", "/m_voc/terms/E_nat"),
            ("e_comp", "vocab", "/m_comp/terms/E_comp"), ("e_noncomp", "vocab", "/m_comp/terms/E_noncomp"),
            ("e_int", "interact", "/m_int/terms/E_any_x_zA"))
for k, a, p in OR_TERMS:
    jp(f"f3.or.{k}.est", a, f"{p}/OR", "MECHANISM", CI_BOOT_OR)
    jp(f"f3.or.{k}.lo", a, f"{p}/OR_ci95_boot/0", "MECHANISM", CI_BOOT_OR)
    jp(f"f3.or.{k}.hi", a, f"{p}/OR_ci95_boot/1", "MECHANISM", CI_BOOT_OR)
jp("f3.or.n_strata", "enrich", "/m2/n_strata", "MECHANISM")
jp("f3.or.prev_case", "mech_results", "/descriptives/prev_case_E_any", "MECHANISM")
jp("f3.or.prev_ctrl", "mech_results", "/descriptives/prev_control_E_any", "MECHANISM")
jp("f3.or.n_pairs", "frame", "/primary/adopters/n_adopter_pairs_total", "MECHANISM")
jp("f3.or.share_excl", "frame", "/primary/adopters/share_adopter_pairs_career_new_corpus", "MECHANISM")
dv("f3.or.pct_excl", "pct", ["f3.or.share_excl"], "MECHANISM")
jp("f3.mech_label", "mech_label", "/label", "SUPPLEMENTARY/POOLED")

# ---------------- F4: RQ1 ----------------
R1ROWS = ("closure", "closure_resT", "closure_persist", "constraint", "effsize", "wmz")
for r in R1ROWS:
    f = {"row": r}
    cr(f"f4.{r}.dir", "r1_es", f, "spec_direction")
    cr(f"f4.{r}.frozen", "r1_es", f, "estimator_frozen")
    for fld, col in (("scr", "S_screen"), ("scr_lo", "ci_screen_lo"), ("scr_hi", "ci_screen_hi"),
                     ("ho", "S_heldout"), ("ho_lo", "ci_heldout_lo"), ("ho_hi", "ci_heldout_hi"),
                     ("mde", "mde_es")):
        cr(f"f4.{r}.es.{fld}", "r1_es", f, col, "CONFIRMATORY" if fld.startswith("ho") else "SCREEN",
           CI_BOOT_ES)
    for fld, col in (("scr", "coef_screen"), ("scr_se", "se_screen"), ("ho", "coef_heldout"),
                     ("ho_lo", "ci_heldout_lo"), ("ho_hi", "ci_heldout_hi"), ("mde", "mde_panel")):
        cr(f"f4.{r}.pp.{fld}", "r1_panel", f, col, "CONFIRMATORY" if fld.startswith("ho") else "SCREEN",
           "95% Wald, concept-clustered")
    dv(f"f4.{r}.pp.scr_lo", "lin_lo", [f"f4.{r}.pp.scr", f"f4.{r}.pp.scr_se"], "SCREEN",
       "95% Wald (coef -/+ 1.96 se), derived")
    dv(f"f4.{r}.pp.scr_hi", "lin_hi", [f"f4.{r}.pp.scr", f"f4.{r}.pp.scr_se"], "SCREEN",
       "95% Wald (coef -/+ 1.96 se), derived")
for r in ("closure", "closure_resT", "closure_persist", "constraint"):
    jp(f"f4.{r}.decision", "r1_summary", f"/tests/{r}/decision", "CONFIRMATORY")
    jp(f"f4.{r}.holm", "r1_summary", f"/tests/{r}/p_one_holm", "CONFIRMATORY")
jp("f4.status", "r1_summary", "/status", "CONFIRMATORY")
jp("f4.reading", "r1_summary", "/reading_label", "CONFIRMATORY")
jp("f4.spec_sha", "r1_summary", "/spec_sha256", "CONFIRMATORY")
jp("f4.verdict", "r1_summary", "/verdict", "CONFIRMATORY")
for fld, col in (("est", "S_pooled"), ("lo", "ci_lo"), ("hi", "ci_hi")):
    cr(f"f4.iv_resT.{fld}", "r1_iv", {"row": "closure_resT"}, col, "DESCRIPTIVE", "95% IVW, descriptive")
cr("f4.bal_H_smd", "r1_balance", {"covariate": "H", "k": "0"}, "smd", "CONFIRMATORY")
KEYS["f4.bal_n_flag"] = {"file": "r1_balance", "csv_count": {"filters": {"flag_abs_gt_0_25": "True"}},
                         "fold_label": "CONFIRMATORY"}
KEYS["f4.bal_n"] = {"file": "r1_balance", "csv_count": {"filters": {}}, "fold_label": "CONFIRMATORY"}
KEYS["f4.fallback_screen_never"] = {"file": "r1_summary", "json_regex": {
    "pointer": "/disclosures", "regex": r"contains (\d+) screen never-concepts"}, "fold_label": "CONFIRMATORY"}
cr("f4.n_matched", "r1_nflow", {"step": "n_matched"}, "value", "CONFIRMATORY")
cr("f4.n_onsets", "r1_nflow", {"step": "n_onsets"}, "value", "CONFIRMATORY")
jp("f4.dauc", "exp5_pred", "/delta_FULL_vs_BASE/delta", "SCREEN", "95% grouped-CV bootstrap")
jp("f4.dauc_lo", "exp5_pred", "/delta_FULL_vs_BASE/ci/0", "SCREEN", "95% grouped-CV bootstrap")
jp("f4.dauc_hi", "exp5_pred", "/delta_FULL_vs_BASE/ci/1", "SCREEN", "95% grouped-CV bootstrap")

# ---------------- F5: rooting ----------------
for fold, lab in (("screen", "SCREEN"), ("heldout", "CONFIRMATORY")):
    for ty in ("BROAD", "LOCALISED"):
        jp(f"f5.{fold}.{ty}.entries_pc", "rooting", f"/{fold}/descriptives/occupancy/{ty}/all_main_entries_per_concept",
           "DESCRIPTIVE")
        jp(f"f5.{fold}.{ty}.n_concepts", "rooting", f"/{fold}/descriptives/{ty}/n_concepts", "DESCRIPTIVE")
        jp(f"f5.{fold}.{ty}.n_entries", "rooting", f"/{fold}/descriptives/{ty}/n_entries", "DESCRIPTIVE")
        for m in ("A_cont_mean", "CT_mean") + (("EST_rate",) if fold == "screen" else ()):
            for fld, sub in (("est", "est"), ("lo", "ci/0"), ("hi", "ci/1")):
                jp(f"f5.{fold}.{ty}.{m}.{fld}", "rooting", f"/{fold}/descriptives/{ty}/{m}/{sub}", "DESCRIPTIVE",
                   "95% concept bootstrap, B=2,000")
    for mdl in ("model_i_Acont", "model_ii_CT"):
        for fld, sub in (("est", "coef"), ("lo", "ci/0"), ("hi", "ci/1"), ("p", "p"), ("n", "n")):
            jp(f"f5.{fold}.{mdl}.{fld}", "rooting", f"/{fold}/{mdl}/{sub}", lab,
               "95% Wald, concept-clustered, host x year FE")
jp("f5.heldout.declared", "rooting", "/heldout/prediction_direction_declared", "CONFIRMATORY")
jp("f5.heldout.confirmed", "rooting", "/heldout/declared_direction_confirmed", "CONFIRMATORY")
for ty in ("BROAD", "LOCALISED"):
    for fld, sub in (("est", "irr_per_sd"), ("lo", "ci/0"), ("hi", "ci/1"), ("p", "p")):
        jp(f"f5.ppml.{ty}.{fld}", "rooting", f"/screen/model_iii_ppml/{ty}/{sub}", "SCREEN", CI_CRV1)
    for q in range(1, 6):
        jp(f"f5.estq.{ty}.q{q}", "rooting", f"/screen/EST_by_Aq_type/{ty}_q{q}/EST_rate", "DESCRIPTIVE")
        jp(f"f5.estq.{ty}.q{q}.n", "rooting", f"/screen/EST_by_Aq_type/{ty}_q{q}/n", "DESCRIPTIVE")
jp("f5.ppml.int_p", "rooting", "/screen/model_iii_ppml/interaction_p", "SCREEN")
jp("f5.ppml.N", "rooting", "/screen/model_iii_ppml/n_retained", "SCREEN")
jp("f5.ppml.G", "rooting", "/screen/model_iii_ppml/G", "SCREEN")

# ---------------- F6: cases (dynamic pointers go through Registry.select on alias 'cases') -------------
KEYS["f6.delta_wireless"] = {"file": "case_interp", "md_regex": r"rooted entry had the higher host share \(\+([0-9]+\.[0-9]+)\)",
                             "fold_label": "DESCRIPTIVE"}
KEYS["f6.delta_epr"] = {"file": "case_interp", "md_regex": r"Rooted-minus-unrooted A_cont is \+([0-9]+\.[0-9]+)",
                        "fold_label": "DESCRIPTIVE"}

# ---------------- F1: methodology flow ----------------
F1 = [
    ("f1.frame_total", "exp1_t0", "/frame/total"), ("f1.frame_main", "exp1_t0", "/frame/arms/main"),
    ("f1.frame_ref", "exp1_t0", "/frame/arms/reference"), ("f1.n_works", "ds5_assemble", "/n_works"),
    ("f1.unlinked", "exp1_summary", "/frame_application/link_status_by_arm/main/UNLINKED"),
    ("f1.mesh_concepts", "mesh_load", "/n_concepts"), ("f1.gateA_share", "exp2_gateA", "/share_edges_ge_040"),
    ("f1.gateA_verdict", "exp2_gateA", "/verdict"), ("f1.gateB_episodes", "exp2_rederive", "/gate_B_labelled_episodes"),
    ("f1.screen_concepts", "exp5_pop", "/counts/MAIN/by_fold/screen"),
    ("f1.heldout_concepts", "exp5_pop", "/counts/MAIN/by_fold/heldout"),
    ("f1.d2_scr_N", "d2_summary", "/coprimary_fe_concept_plus_e_plus_d/N"),
    ("f1.d2_scr_G", "d2_summary", "/coprimary_fe_concept_plus_e_plus_d/G"),
    ("f1.d2_scr_entries", "d2_summary", "/events/MAIN_kw5_by_fold/screen/events"),
    ("f1.d2_ho_N", "ho_post", "/flags/secondary/N"), ("f1.d2_ho_G", "ho_post", "/flags/secondary/G"),
    ("f1.mesh_N", "g4_summary", "/R2/N"), ("f1.mesh_G", "g4_summary", "/R2/G"),
    ("f1.mesh_verdict", "g4_summary", "/g4_verdict"), ("f1.ho_confirmed", "ho_post", "/flags/secondary/confirmed"),
    ("f1.adopter_or", "enrich", "/m2/terms/E_any/OR"),
    ("f1.d1_holm", "exp6_d1", "/per_measure/closure_res_z/Y1r/p_holm"), ("f1.d1_verdict", "exp6_d1", "/verdict"),
    ("f1.d3_decision", "d3_results", "/decision/decision"),
    ("f1.ct_holm", "d2_summary", "/coprimary_fe_concept_plus_e_plus_d/decision/holm_p/CT"),
    ("f1.ct_mesh_holm", "g4_summary", "/holm_p_R2/CT"),
    ("f1.r1_status", "r1_summary", "/status"),
    ("f1.typ_k", "typology", "/k_selected"), ("f1.typ_jacc", "typology", "/by_k/2/min_jaccard"),
    ("f1.roles_bridge", "roles", "/predeclared/robust_shares/BRIDGE"),
    ("f1.ll_share", "leadlag", "/primary/share_expansion_first"),
    ("f1.ll_n", "leadlag", "/primary/n_both_onsets"),
    ("f1.n_cases", "cases", "/c_3a8d31dc5fbf/rule"),
]
for k, a, p in F1:
    jp(k, a, p, "DESCRIPTIVE")
cr("f1.snap_nodes_2023", "exp3_snap", {"year": "2023"}, "n_nodes", "DESCRIPTIVE")
cr("f1.snap_kept_edges_2023", "exp3_snap", {"year": "2023"}, "n_kept_edges", "DESCRIPTIVE")
cr("f1.snap_nodes_2000", "exp3_snap", {"year": "2000"}, "n_nodes", "DESCRIPTIVE")
# F1 side-panel definitions (strings taken from the source artifacts' own spec/summary files)
jp("f1.def.A_cont", "d2_summary", "/nativeness/primary_A", "DESCRIPTIVE")
jp("f1.def.fallback3", "d2_summary", "/fallback3_thin_cells/rule", "DESCRIPTIVE")
jp("f1.def.leadlag_exp", "leadlag", "/primary/definition/expansion", "DESCRIPTIVE")
jp("f1.def.leadlag_diff", "leadlag", "/primary/definition/diffusion", "DESCRIPTIVE")
jp("f1.def.CT", "d2_prereg", "/spec/co_transfer/companions", "DESCRIPTIVE")
jp("f1.def.Y_strict", "d2_prereg", "/spec/outcomes/Y_strict", "DESCRIPTIVE")
jp("f1.def.EST_bin", "d2_prereg", "/spec/outcomes/EST_bin", "DESCRIPTIVE")
jp("f1.def.folds", "d2_prereg", "/spec/fold_rule", "DESCRIPTIVE")
jp("f1.def.inference", "d2_prereg", "/spec/models/inference", "DESCRIPTIVE")
jp("f1.def.E_up", "exp5_pop", "/definitions/E_up", "DESCRIPTIVE")
jp("f1.def.closure_persist", "exp5_pop", "/definitions/closure_persist", "DESCRIPTIVE")
jp("f1.def.oos_note", "g4_summary", "/oos/note", "DESCRIPTIVE")


# ---------------- drift-only keys (compared against the record; not plotted) ----------------
jp("drift.rooting_screen_n_entries", "rooting", "/screen/n_entries", "DESCRIPTIVE")
jp("drift.g4_R2_holm", "g4_summary", "/holm_p_R2/A_cont", "REPLICATION")
jp("drift.g1_scr_share_single", "g_screen", "/G1_descriptive/share_single_paper_entry_year", "SCREEN")
jp("drift.ll_share_ci_lo", "leadlag", "/primary/share_expansion_first_ci/0", "DESCRIPTIVE")
jp("drift.labels_anchored_share", "d2_summary", "/labels/anchored_share_screen", "SCREEN")
jp("drift.est_anchored", "d2_summary", "/labels/establishment_by_label/EST_bin/anchored", "SCREEN")
jp("drift.est_unanchored", "d2_summary", "/labels/establishment_by_label/EST_bin/unanchored", "SCREEN")
jp("drift.oos_screen", "d2_summary", "/out_of_sample/deviance_diff_M1_minus_M0", "SCREEN")


def main() -> None:
    files = {a: {"artifact": art, "path": p} for a, (art, p) in FILES.items()}
    out = {"run_root_note": "paths are relative to the run root (env AII_RUN_ROOT; default: 4 levels above "
                            "this workspace)", "files": files, "keys": KEYS}
    (WS / "sources.yaml").write_text(yaml.safe_dump(out, sort_keys=False, width=140))
    print(f"wrote sources.yaml: {len(files)} files, {len(KEYS)} keys")


if __name__ == "__main__":
    main()
