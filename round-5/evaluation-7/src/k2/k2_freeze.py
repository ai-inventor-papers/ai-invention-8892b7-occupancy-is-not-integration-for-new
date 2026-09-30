#!/usr/bin/env python3
"""K2 Step 2: freeze results/k2_spec.json (sha256 + UTC timestamp in logs/freeze_log.txt) BEFORE any K2 coefficient.

Refuses to overwrite an existing frozen spec. Gate status and the outcome-free Step-1 descriptives are embedded.
"""
from __future__ import annotations

import json
import sys
import time

import k2_lib as L
from k2_lib import logger


def build_spec() -> dict:
    gates = json.loads((L.RES / "gates.json").read_text())
    desc = json.loads((L.RES / "k2_descriptives.json").read_text())
    return {
        "name": "K2: host-specific vs generic accessibility of the confirmed A_cont host-entry effect",
        "label": "POST-CONFIRMATION EXPLORATORY",
        "plan_id": "gen_plan_evaluation_2_idx2",
        "seed": L.SEED,
        "folds": {
            "screen": "main OpenAlex, co-primary sample (eval_2 g_samples.coprimary_sample, fold='screen')",
            "heldout": "main OpenAlex held-out fold (opened once in iteration 4; lock sha256 recorded in gates.json)",
            "mesh": "exp_9 MeSH replication: outcomes_mesh.parquet, dropna(A_cont, CT, secondary_controls)"},
        "k2_sample_rule": "co-primary input sample minus rows with missing G_H, G_F or A_lift; M0..M3 all fitted on "
                          "this IDENTICAL input sample (PPML pruning depends only on y and FE); M0 on the full "
                          "co-primary sample is the GATE-B row",
        "outcome": "Y_strict (W2 host papers by author-disjoint newcomers)", "offset": "log(n_entry_papers)",
        "fe": {"co-primary": ["concept", "e", "d"], "S1_primary": ["concept x e", "d x e"]},
        "controls": ["CT"] + L.CTRL,
        "estimator": "vendored exp_7 ppml.fit via models.fit_one (iterated singleton/separation pruning), CRV1 by "
                     "concept with t(G-1)",
        "definitions": {
            "block": "B = block_of(e): e 2005-09 -> 2000-2004, 2010-14 -> 2005-2009, 2015-19 -> 2010-2014",
            "tag_multiset": "entry-year d-paper partner tags (own node dropped), PROFILED tags only (as A_cont)",
            "H_p": "-sum_d P_pd ln P_pd / ln K_B, P over OBSERVED subfield counts excluding 'unknown'; K_B = #subfields "
                   "with > 0 works in subfield_year_totals 'all_types' summed over B's five years",
            "H_p_ub": "missing tail (total_known - observed) spread evenly over the K_B - n_observed unobserved subfields",
            "F_p": "ln(total_known), total_known = total - unknown",
            "s_dB": "sum_{y in B} totals(d,y) / sum_{y in B} sum_sf totals(sf,y), 'all_types'",
            "G_H, G_F": "tag-count-weighted entry means of H_p, F_p; MeSH: EXACT-profiled tags only (primary)",
            "G_H_bg": "MeSH sensitivity (S8): exact + bg tags, bg entropy from design-weighted shares",
            "A_lift": "ln((A_cont + c0) / s_dB); c0 = 0.5 x smallest positive A_cont in the fold if any A_cont == 0 "
                      "(else 0)",
            "split_generality": "GH_k = sum_{class-k tags} H_p / n_gen_tags (k: NATIVE s>=0.30, ADJACENT 0.05<=s<0.30, "
                                "FOREIGN s<0.05); same for F",
            "A_spec": "entry mean of residuals of tag-level OLS s_pd = a_B + b1 H_p + b2 F_p + b3 ln s_dB (per fold)",
            "retention": "ret = b_A(M1)/b_A(M0) (= ratio of log-IRR/SD: identical sample and SD); ret_lift = "
                         "b(M3)/b(M2); pct_removed = 100 (1 - ret)"},
        "models": {k: v + ["CT"] + L.CTRL for k, v in L.MODELS.items()},
        "inference": {
            "crv1": "t(G-1) CI and p", "wild": "ppml.wild_score_test, 999 Rademacher, focal term only",
            "placebo_calibrated": "2 * Phi(-|z| / SD_z) with SD_z of the recorded nativeness-permutation placebo z "
                                  "(main: d2 placebo_draws.csv z_A_secondary; MeSH: placebo_draws_mesh.csv z_A_R2)",
            "randomisation": "within-concept Freedman-Lane: residualise focal regressor on the other regressors + "
                             "concept/e/d FE (linear), permute residuals within concept, add back fitted part, "
                             "refit PPML; p = (1 + #{|z_perm| >= |z_obs|}) / (1 + R)",
            "randomisation_draws": {"M0": 2000, "M1": 2000, "M2": 2000, "M3": 2000},
            "bootstrap": "1000 concept-cluster draws (g_lib.resample_concepts), all models refit per draw; percentile CI",
            "holm_family_per_fold": ["A_cont in M1", "A_lift in M2", "A_lift in M3"],
            "holm_use": "reported, not used in the rule"},
        "ivw": {"quantity": "log-IRR/SD (b x SD_fold, SE x SD_fold) from CRV1; fixed-effect IVW; Cochran Q, I^2",
                "pooled_retention": "ret_pool = lnIRR1_pool / lnIRR0_pool; CI from 1000 combined draws: draw k of each "
                                    "fold (b_k x SD_fold) pooled with the SAME fixed IVW weights, ratio, percentiles",
                "pooled_ci_for_rule": "IVW normal 95% CI of the pooled A_lift log-IRR/SD in M3"},
        "decision_rule_verbatim": {
            "HOST-SPECIFIC": "A_lift CI excludes 1 (M3; CRV1 t(G-1) CI per fold, IVW CI pooled) AND retention >= 0.5",
            "GENERIC ACCESSIBILITY": "generality controls remove > 50% of the log-IRR (ret < 0.5)",
            "MIXED": "otherwise",
            "implementation": "'excludes 1' is read as CI entirely above 1 (a CI entirely below 1 is reported as a "
                              "negative lift and labelled MIXED unless ret < 0.5)",
            "qualifiers": ["retention CI includes 0.5 (not decisive)",
                           "fragile: randomisation p of the focal term (M1 A_cont or M3 A_lift) > 0.05 while CRV1 p "
                           "< 0.05",
                           "retention underpowered: Step-3 P(ret_hat >= 0.5 | DGP-S) < 0.8"],
            "reading": "the POOLED verdict is the paper's reading; fold verdicts are descriptive"},
        "power_step3": {"reps_per_dgp": 300, "mu0": "PPML fit of Y on CT + controls + G_H + G_F (no A term)",
                        "theta": "NB2 moment estimator as g_lib.mde_sim",
                        "DGP_S": "ln mu = ln mu0 + beta_rec (A_cont - mean); beta_rec = recorded co-primary b_A",
                        "DGP_G": "ln mu = ln mu0 + gamma (Ahat - mean), Ahat = linear within-FE projection of A_cont "
                                 "on G_H, G_F; gamma = beta_rec / R2_within so the implied M0 b_A = beta_rec; not "
                                 "constructible if R2_within < 0.02",
                        "design": "fixed observed design (no concept resampling), y ~ Poisson(Gamma(theta, mu/theta))",
                        "report": "P(ret >= 0.5 | S), P(ret < 0.5 | G), 2.5-97.5% of ret_hat per fold and IVW pool"},
        "supplementary": {
            "S1": "primary FE (concept x e + d x e) M0/M1 + retention; thin-cell flag G < 50 or retained < 0.30",
            "S2": "A_cont + GH_nat + GH_adj + GH_for + GF_nat + GF_adj + GF_for; retention of A_cont vs M0",
            "S3": "NAT + ADJ (FOREIGN reference) with and without G_H + G_F; retention of NAT and ADJ",
            "S4": "A_spec in place of A_cont", "S5": "A_cont residualised on G_H, G_F + FE, entered alone (interpreted "
                                                    "only if |within-FE r| > 0.8)",
            "S6": "G_H_ub in place of G_H (M1)", "S7": "events with cov >= 0.8 (M0/M1)",
            "S8": "MeSH only: G_H_bg in place of G_H (M1)", "S9": "zero-A events dropped (M2/M3)",
            "S10": "placebo host under M1: 100 size-decile draws (g_lib.placebo_candidates; MeSH also coverage rule "
                   "0.30), A_plac + CT + G_H + G_F + controls and joint; PASS if share_pos_sig <= 0.10 AND median "
                   "placebo IRR/SD < 1.10",
            "S11": "EST_bin LPM (secondary FE) with M0/M1 regressors: direction only",
            "bootstrap_S_rows": "S1, S2, S3, S6 retention CIs from the same 1000 bootstrap draws"},
        "audit": {"entries": "30 (10 per fold, seed 20261001), plain loops, tolerance 1e-9",
                  "pyfixest": "fepois on ppml-pruned samples, |db| < 1e-4", "shuffled_G": "50 draws per fold",
                  "oracle": "G_H := A_cont + N(0, 0.1 SD)"},
        "gate_values": {f: {"status": gates[f]["status"], "gate_B_recorded": gates[f]["gate_B"]["recorded"],
                            "gate_A_max_abs_diff": gates[f]["gate_A"]["max_abs_diff"]} for f in L.FOLDS},
        "heldout_lock_sha256": gates["heldout_lock"]["lock_sha256"],
        "step1_descriptives_outcome_free": {f: {"within_fe_R2_A_cont_on_G": desc[f]["within_fe_R2_A_cont_on_G"],
                                                "within_fe_r": desc[f]["within_fe_r"],
                                                "partial_residual_trigger": desc[f][
                                                    "partial_residual_trigger_abs_r_gt_0.8"],
                                                "lift": desc[f]["lift"], "N_k2_input": desc[f]["N_k2_input"]}
                                            for f in L.FOLDS},
        "sources": {f: L.source_paths(f) for f in L.FOLDS},
        "deviations_declared_before_coefficients": [
            "git commit of the spec replaced by sha256 + UTC timestamp (workspace is published as a folder of the run "
            "repository; a nested .git would break the publish)",
            "power simulation uses the fixed observed design instead of concept resampling (retention is a within-sample "
            "ratio)",
            "IVW pools log-IRR/SD rather than raw b (fold SDs differ: MeSH vs main)"],
    }


@logger.catch(reraise=True)
def main() -> None:
    L.setup_logging("k2_freeze")
    if L.SPEC_SHA.exists():
        raise SystemExit("REFUSED: k2_spec.json already frozen")
    spec = L.clean(build_spec())
    L.SPEC_PATH.write_text(json.dumps(spec, indent=1, sort_keys=True))
    h = L.sha256_file(L.SPEC_PATH)
    ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    L.SPEC_SHA.write_text(f"{h}  k2_spec.json  frozen {ts}\n")
    with open(L.LOGS / "freeze_log.txt", "a") as f:
        f.write(f"k2_spec.json sha256={h} frozen_utc={ts} (before any K2 coefficient; gates + outcome-free "
                f"descriptives only)\n")
    logger.info(f"frozen k2_spec.json sha256 {h} at {ts}")


if __name__ == "__main__":
    sys.exit(main())
