# Numbers of record (Part 1)

Every value is recomputed from item- or row-level files where they exist (`recomputed=true`); otherwise transcribed from the named summary file. `flag` compares against iter_3/gen_strat/current_report.md (|diff| <= half a unit of the report's last digit). MISSING_IN_REPORT is informational.


## B1 classifier

| id | claim | value | 95% CI | n | unit | report (line) | flag |
|---|---|---|---|---|---|---|---|
| B1.clf.tF1.confusion | Confusion matrix at threshold 0.5073 (TP/FP/FN/TN) | 148 |  | 300 | count |  | **MISSING_IN_REPORT** |
| B1.clf.tF1.precision | Classifier precision at t=0.5073 | 0.759 | [0.699, 0.818] | 300 | proportion | 0.812 (L267) | **DRIFT_VALUE** |
| B1.clf.tF1.recall | Classifier recall at t=0.5073 | 0.8862 | [0.837, 0.931] | 300 | proportion | 0.824 (L268) | **DRIFT_VALUE** |
| B1.clf.tF1.accuracy | Classifier accuracy at t=0.5073 | 0.78 | [0.733, 0.823] | 300 | proportion | 0.843 (L269) | **DRIFT_VALUE** |
| B1.clf.tF1.f1 | Classifier F1 at t=0.5073 | 0.8177 | [0.773, 0.859] | 300 | F1 | 0.818 (L265) | **OK** |
| B1.clf.tF1.kappa | Classifier Cohen's kappa vs silver labels at t=0.5073 | 0.5445 | [0.446, 0.635] | 300 | kappa |  | **MISSING_IN_REPORT** |
| B1.clf.tF1.balacc | Classifier balanced accuracy at t=0.5073 | 0.7664 | [0.717, 0.811] | 300 | proportion |  | **MISSING_IN_REPORT** |
| B1.clf.t050.confusion | Confusion matrix at threshold 0.5 (TP/FP/FN/TN) | 150 |  | 300 | count |  | **MISSING_IN_REPORT** |
| B1.clf.t050.precision | Classifier precision at t=0.5 | 0.7614 | [0.702, 0.82] | 300 | proportion |  | **MISSING_IN_REPORT** |
| B1.clf.t050.recall | Classifier recall at t=0.5 | 0.8982 | [0.852, 0.941] | 300 | proportion |  | **MISSING_IN_REPORT** |
| B1.clf.t050.accuracy | Classifier accuracy at t=0.5 | 0.7867 | [0.74, 0.833] | 300 | proportion |  | **MISSING_IN_REPORT** |
| B1.clf.t050.f1 | Classifier F1 at t=0.5 | 0.8242 | [0.782, 0.864] | 300 | F1 |  | **MISSING_IN_REPORT** |
| B1.clf.t050.kappa | Classifier Cohen's kappa vs silver labels at t=0.5 | 0.5576 | [0.457, 0.65] | 300 | kappa |  | **MISSING_IN_REPORT** |
| B1.clf.t050.balacc | Classifier balanced accuracy at t=0.5 | 0.7724 | [0.722, 0.818] | 300 | proportion |  | **MISSING_IN_REPORT** |
| B1.clf.tP90.confusion | Confusion matrix at threshold 0.6468 (TP/FP/FN/TN) | 127 |  | 300 | count |  | **MISSING_IN_REPORT** |
| B1.clf.tP90.precision | Classifier precision at t=0.6468 | 0.8411 | [0.781, 0.896] | 300 | proportion |  | **MISSING_IN_REPORT** |
| B1.clf.tP90.recall | Classifier recall at t=0.6468 | 0.7605 | [0.694, 0.822] | 300 | proportion |  | **MISSING_IN_REPORT** |
| B1.clf.tP90.accuracy | Classifier accuracy at t=0.6468 | 0.7867 | [0.74, 0.83] | 300 | proportion |  | **MISSING_IN_REPORT** |
| B1.clf.tP90.f1 | Classifier F1 at t=0.6468 | 0.7987 | [0.748, 0.842] | 300 | F1 |  | **MISSING_IN_REPORT** |
| B1.clf.tP90.kappa | Classifier Cohen's kappa vs silver labels at t=0.6468 | 0.573 | [0.48, 0.658] | 300 | kappa |  | **MISSING_IN_REPORT** |
| B1.clf.tP90.balacc | Classifier balanced accuracy at t=0.6468 | 0.79 | [0.745, 0.833] | 300 | proportion |  | **MISSING_IN_REPORT** |
| B1.clf.auc | Classifier ROC-AUC on D2 test | 0.8879 | [0.851, 0.92] | 300 | AUC | 0.888 (L266) | **OK** |
| B1.clf.auprc | Classifier AUPRC on D2 test | 0.9148 |  | 300 | AUPRC |  | **MISSING_IN_REPORT** |
| B1.clf.n_pos | D2 test positives (CONCEPT) | 167 |  | 300 | count |  | **MISSING_IN_REPORT** |
| B1.base.all_positive_f1 | Majority-class (predict-all-CONCEPT) baseline F1; CONCEPT is the majority class | 0.7152 |  | 300 | F1 | 0 (L259) | **WRONG_DEFINITION** |
| B1.base.all_positive_precision | Predict-all-positive precision (= positive share) | 0.5567 |  | 300 | proportion |  | **MISSING_IN_REPORT** |
| B1.base.all_negative_f1 | Predict-all-negative baseline F1 | 0 |  | 300 | F1 |  | **MISSING_IN_REPORT** |
| B1.clf.delta_f1_vs_allpos | Classifier F1 minus predict-all-positive F1 (paired item bootstrap) | 0.1025 | [0.0609, 0.144] | 300 | delta F1 |  | **MISSING_IN_REPORT** |
| B1.base.majority_class.f1 | Baseline 'majority_class' F1 (transcribed; no item-level scores saved) | 0.7152 | [0.664, 0.76] | 300 | F1 |  | **MISSING_IN_REPORT** |
| B1.base.cvalue_threshold.f1 | Baseline 'cvalue_threshold' F1 (transcribed; no item-level scores saved) | 0.7158 | [0.664, 0.761] | 300 | F1 |  | **MISSING_IN_REPORT** |
| B1.cmp.lexical_only.f1 | Comparison model 'lexical_only' F1 (transcribed) | 0.7624 | [0.712, 0.805] | 300 | F1 |  | **MISSING_IN_REPORT** |
| B1.cmp.no_embeddings.f1 | Comparison model 'no_embeddings' F1 (transcribed) | 0.7742 | [0.724, 0.82] | 300 | F1 |  | **MISSING_IN_REPORT** |
| B1.cmp.hgb.f1 | Comparison model 'hgb' F1 (transcribed) | 0.8146 | [0.769, 0.857] | 300 | F1 |  | **MISSING_IN_REPORT** |
| B1.base.unigram_f1_report | 'Unigram-frequency baseline F1 0.689' quoted in the report |  |  |  | F1 | 0.689 (L259) | **NOT_REDERIVABLE** |
| B1.llmA.f1 | LLM-A F1 vs silver labels (CONCEPT vs rest) | 0.9012 | [0.868, 0.931] | 300 | F1 |  | **MISSING_IN_REPORT** |
| B1.clf_minus_llmA.f1 | Classifier F1 minus LLM-A F1 (paired item bootstrap) | -0.08348 | [-0.127, -0.0402] | 300 | delta F1 |  | **MISSING_IN_REPORT** |
| B1.llmB.f1 | LLM-B F1 vs silver labels (CONCEPT vs rest) | 0.7731 | [0.731, 0.813] | 300 | F1 |  | **MISSING_IN_REPORT** |
| B1.clf_minus_llmB.f1 | Classifier F1 minus LLM-B F1 (paired item bootstrap) | 0.04453 | [0.00621, 0.0852] | 300 | delta F1 |  | **MISSING_IN_REPORT** |
| B1.anchor.E1.clf_kappa | Classifier binary kappa vs human anchors (E1, SemEval/SciERC) | 0.4133 | [0.315, 0.514] | 300 | kappa | 0.56 (L271) | **WRONG_ESTIMATOR** |
| B1.anchor.E1.llmA_kappa | LLM-A binary kappa vs human anchors (E1) | 0.56 |  | 300 | kappa | 0.56 (L109) | **OK** |
| B1.anchor.E1.llmB_kappa | LLM-B binary kappa vs human anchors (E1) | 0.3867 |  | 300 | kappa |  | **MISSING_IN_REPORT** |
| B1.anchor.E1.clf_precision | Classifier precision vs human anchors (E1) | 0.7583 | [0.677, 0.836] | 300 | precision |  | **MISSING_IN_REPORT** |
| B1.anchor.E1.clf_recall | Classifier recall vs human anchors (E1) | 0.6067 | [0.528, 0.686] | 300 | recall |  | **MISSING_IN_REPORT** |
| B1.anchor.E1.clf_f1 | Classifier f1 vs human anchors (E1) | 0.6741 | [0.608, 0.738] | 300 | f1 |  | **MISSING_IN_REPORT** |
| B1.anchor.E1.clf_auc | Classifier auc vs human anchors (E1) | 0.8371 | [0.791, 0.88] | 300 | auc |  | **MISSING_IN_REPORT** |
| B1.anchor.E1.llmA_precision | LLM-A precision vs human anchors (E1) | 0.7917 |  | 300 | precision | 0.79 (L116) | **OK** |
| B1.anchor.E1.llmA_recall | LLM-A recall vs human anchors (E1) | 0.76 |  | 300 | recall | 0.76 (L116) | **OK** |
| B1.anchor.E1.llmA_f1 | LLM-A f1 vs human anchors (E1) | 0.7755 |  | 300 | f1 |  | **MISSING_IN_REPORT** |
| B1.anchor.E2.clf_precision | Classifier precision vs human anchors (E2, balanced resamples) | 0.8131 | [0.795, 0.83] | 4939 | precision |  | **MISSING_IN_REPORT** |
| B1.anchor.E2.clf_recall | Classifier recall vs human anchors (E2, balanced resamples) | 0.6237 | [0.605, 0.642] | 4939 | recall |  | **MISSING_IN_REPORT** |
| B1.anchor.E2.clf_f1 | Classifier f1 vs human anchors (E2, balanced resamples) | 0.7058 | [0.69, 0.72] | 4939 | f1 |  | **MISSING_IN_REPORT** |
| B1.anchor.E2.clf_auc | Classifier auc vs human anchors (E2, balanced resamples) | 0.8231 | [0.81, 0.835] | 4939 | auc |  | **MISSING_IN_REPORT** |

Source: round-2/experiment-1/src/results/classifier_results.json; round-2/experiment-1/src/results/d2_test_predictions.json

## B1 merger

| id | claim | value | 95% CI | n | unit | report (line) | flag |
|---|---|---|---|---|---|---|---|
| B1.merger.d3_test.f1 | Merger pair F1 at p_merge=0.855 (d3_test) | 0.3571 | [0.222, 0.488] | 115 | F1 | 0.357 (L279) | **OK** |
| B1.merger.d3_test.precision | Merger pair precision (d3_test) | 0.9375 |  | 115 | proportion |  | **MISSING_IN_REPORT** |
| B1.merger.d3_test.recall | Merger pair recall (d3_test) | 0.2206 |  | 115 | proportion |  | **MISSING_IN_REPORT** |
| B1.merger.heldout_mesh.f1 | Merger pair F1 at p_merge=0.855 (heldout_mesh) | 0.2222 | [0.159, 0.286] | 769 | F1 | 0.222 (L280) | **OK** |
| B1.merger.heldout_mesh.precision | Merger pair precision (heldout_mesh) | 0.8462 |  | 769 | proportion |  | **MISSING_IN_REPORT** |
| B1.merger.heldout_mesh.recall | Merger pair recall (heldout_mesh) | 0.1279 |  | 769 | proportion |  | **MISSING_IN_REPORT** |
| B1.merger.bcubed_f1 | Merger B-cubed F1 (MeSH descriptor clustering) | 0.7799 |  | 902 | F1 | 0.78 (L281) | **OK** |

Source: round-2/experiment-1/src/results/merger_results.json; round-2/experiment-1/src/results/merger_test_predictions.json

## B1 linker

| id | claim | value | 95% CI | n | unit | report (line) | flag |
|---|---|---|---|---|---|---|---|
| B1.linker.tau | NIL-aware linker threshold tau | 0.95 |  |  | cosine |  | **MISSING_IN_REPORT** |
| B1.linker.recall | Linker in-KB recall at tau | 0.4037 |  | 3000 | proportion |  | **MISSING_IN_REPORT** |
| B1.linker.precision_nil09 | Linker precision at NIL prior 0.9 | 0.9153 |  | 3000 | proportion |  | **MISSING_IN_REPORT** |

Source: round-2/experiment-1/src/results/link_calibration.json

## B2 event study E

| id | claim | value | 95% CI | n | unit | report (line) | flag |
|---|---|---|---|---|---|---|---|
| B2.E.accretion_shift_rar.S | E event-study S for accretion_shift_rar (primary): mean treated-minus-control over k in [-3,0] | -0.1043 | [-0.12, -0.0155] | 3 | indicator units |  | **MISSING_IN_REPORT** |
| B2.E.accretion_shift_rar.p_holm | E event-study Holm p for accretion_shift_rar (family of 3 primaries) | 0.003 |  | 3 | p |  | **MISSING_IN_REPORT** |
| B2.E.accretion_shift_rar.mde_sd | E MDE (SD units) for accretion_shift_rar | 1.373 |  | 3 | SD |  | **MISSING_IN_REPORT** |
| B2.E.accretion_shift_raw.S | E event-study S for accretion_shift_raw (raw): mean treated-minus-control over k in [-3,0] | 0.08486 | [-0.159, 0.591] | 3 | indicator units |  | **MISSING_IN_REPORT** |
| B2.E.accretion_shift_rar_res.S | E event-study S for accretion_shift_rar_res (res): mean treated-minus-control over k in [-3,0] | -0.1037 | [-0.119, -0.0147] | 3 | indicator units |  | **MISSING_IN_REPORT** |
| B2.E.closure.S | E event-study S for closure (primary): mean treated-minus-control over k in [-3,0] | -0.6251 | [-0.656, -0.588] | 3 | indicator units | -0.625 (L410) | **OK** |
| B2.E.closure.p_holm | E event-study Holm p for closure (family of 3 primaries) | 0.003 |  | 3 | p |  | **MISSING_IN_REPORT** |
| B2.E.closure.mde_sd | E MDE (SD units) for closure | 0.0347 |  | 3 | SD |  | **MISSING_IN_REPORT** |
| B2.E.closure_raw.S | E event-study S for closure_raw (raw): mean treated-minus-control over k in [-3,0] | -1.741 | [-3.05, -1.01] | 3 | indicator units |  | **MISSING_IN_REPORT** |
| B2.E.closure_res.S | E event-study S for closure_res (res): mean treated-minus-control over k in [-3,0] | -0.5674 | [-0.707, -0.462] | 3 | indicator units |  | **MISSING_IN_REPORT** |
| B2.E.P_rar.S | E event-study S for P_rar (primary): mean treated-minus-control over k in [-3,0] | 0.1431 | [-0.119, 0.301] | 3 | indicator units |  | **MISSING_IN_REPORT** |
| B2.E.P_rar.p_holm | E event-study Holm p for P_rar (family of 3 primaries) | 0.074 |  | 3 | p |  | **MISSING_IN_REPORT** |
| B2.E.P_rar.mde_sd | E MDE (SD units) for P_rar | 1.629 |  | 3 | SD |  | **MISSING_IN_REPORT** |
| B2.E.P_raw.S | E event-study S for P_raw (raw): mean treated-minus-control over k in [-3,0] | 0.1612 | [-0.132, 0.367] | 3 | indicator units |  | **MISSING_IN_REPORT** |
| B2.E.P_rar_res.S | E event-study S for P_rar_res (res): mean treated-minus-control over k in [-3,0] | 0.1416 | [-0.123, 0.302] | 3 | indicator units |  | **MISSING_IN_REPORT** |
| B2.E.n_treated | E: treated (onset) concepts | 4 |  |  | concepts |  | **MISSING_IN_REPORT** |
| B2.E.n_matched | E: treated with >= 1 control | 3 |  |  | concepts |  | **MISSING_IN_REPORT** |
| B2.E.match_rate | E: match rate (share of treated with controls) | 0.75 |  | 4 | share of treated |  | **MISSING_IN_REPORT** |
| B2.E.widened_share | E: share of matched needing the widened caliper | 0.3333 |  | 3 | share of matched |  | **MISSING_IN_REPORT** |
| B2.E.mean_controls | E: mean controls per matched treated | 2 |  | 3 | controls |  | **MISSING_IN_REPORT** |

Source: round-2/experiment-3/src/results/event_study/contrib.parquet; round-2/experiment-3/src/results/event_study/matches.csv; round-2/experiment-3/src/results/event_study/summary.json

## B2 pooled panel E

| id | claim | value | 95% CI | n | unit | report (line) | flag |
|---|---|---|---|---|---|---|---|
| B2.E.pooled_panel.accretion_shift_rar.coef | E pooled-panel coefficient on futE for accretion_shift_rar | -0.03087 | [-0.0697, 0.00475] | 233 | indicator units |  | **MISSING_IN_REPORT** |
| B2.E.pooled_panel.closure.coef | E pooled-panel coefficient on futE for closure | -0.8706 | [-1.22, -0.555] | 639 | indicator units |  | **MISSING_IN_REPORT** |
| B2.E.pooled_panel.P_rar.coef | E pooled-panel coefficient on futE for P_rar | 0.1527 | [0.00559, 0.286] | 574 | indicator units |  | **MISSING_IN_REPORT** |

Source: round-2/experiment-3/src/results/event_study/summary.json

## B4 nulls

| id | claim | value | 95% CI | n | unit | report (line) | flag |
|---|---|---|---|---|---|---|---|
| B4.E.placebo.accretion_shift_rar | E pseudo-onset placebo S for accretion_shift_rar (never-emerging, pseudo t0) | 0.008574 | [-0.0153, 0.0351] | 72 | indicator units |  | **MISSING_IN_REPORT** |
| B4.E.placebo.closure | E pseudo-onset placebo S for closure (never-emerging, pseudo t0) | -0.02358 | [-0.268, 0.208] | 72 | indicator units |  | **MISSING_IN_REPORT** |
| B4.E.placebo.P_rar | E pseudo-onset placebo S for P_rar (never-emerging, pseudo t0) | 0.008767 | [-0.0372, 0.0488] | 72 | indicator units |  | **MISSING_IN_REPORT** |
| B4.E_alt.placebo.accretion_shift_rar | E_alt pseudo-onset placebo S for accretion_shift_rar (never-emerging, pseudo t0) | -0.02758 | [-0.0799, 0.0419] | 60 | indicator units |  | **MISSING_IN_REPORT** |
| B4.E_alt.placebo.closure | E_alt pseudo-onset placebo S for closure (never-emerging, pseudo t0) | 0.07114 | [-0.232, 0.375] | 60 | indicator units |  | **MISSING_IN_REPORT** |
| B4.E_alt.placebo.P_rar | E_alt pseudo-onset placebo S for P_rar (never-emerging, pseudo t0) | 0.008145 | [-0.0314, 0.0492] | 60 | indicator units |  | **MISSING_IN_REPORT** |
| B4.E_up.placebo.accretion_shift_rar | E_up pseudo-onset placebo S for accretion_shift_rar (never-emerging, pseudo t0) | 0.02874 | [-0.132, 0.0558] | 38 | indicator units |  | **MISSING_IN_REPORT** |
| B4.E_up.placebo.closure | E_up pseudo-onset placebo S for closure (never-emerging, pseudo t0) | -0.02862 | [-0.344, 0.283] | 38 | indicator units |  | **MISSING_IN_REPORT** |
| B4.E_up.placebo.P_rar | E_up pseudo-onset placebo S for P_rar (never-emerging, pseudo t0) | 0.001978 | [-0.0519, 0.0607] | 38 | indicator units |  | **MISSING_IN_REPORT** |
| B4.main.shuffle.E_alt_h5 | Main-pool label-shuffle null, mean delta-AUC (E_alt_h5) | -0.01861 |  | 20 | delta-AUC | -0.015 (L416) | **WRONG_ESTIMATOR** |
| B4.main.shuffle.E_h5 | Main-pool label-shuffle null, mean delta-AUC (E_h5) | -0.02089 |  | 11 | delta-AUC |  | **MISSING_IN_REPORT** |
| B4.mesh.label_perm_mean | MeSH label-permutation delta-AUC mean (5 permutations, grouped CV) | -0.01487 |  | 5 | delta-AUC | -0.015 (L478) | **OK** |
| B4.mesh.T5.accretion_share | MeSH T5 permutation null mean D (accretion_share) | 0.002026 |  | 200 | indicator units |  | **MISSING_IN_REPORT** |
| B4.mesh.T5.closure_lr | MeSH T5 permutation null mean D (closure_lr) | 0.01891 |  | 200 | indicator units | 0.019 (L472) | **OK** |
| B4.mesh.T5.dP | MeSH T5 permutation null mean D (dP) | -0.001505 |  | 200 | indicator units |  | **MISSING_IN_REPORT** |
| B4.mesh.shuffled_label_auc | MeSH shuffled-label (placebo) grouped-CV AUC of model A | 0.4564 |  | 1067 | AUC |  | **MISSING_IN_REPORT** |
| B4.main.rewire.2008 | Main-pool share of neighbourhoods denser than degree-preserving null (2008) | 0.7867 |  | 75 | share |  | **MISSING_IN_REPORT** |
| B4.main.rewire.2013 | Main-pool share of neighbourhoods denser than degree-preserving null (2013) | 0.7203 |  | 118 | share |  | **MISSING_IN_REPORT** |
| B4.main.rewire.2018 | Main-pool share of neighbourhoods denser than degree-preserving null (2018) | 0.6333 |  | 120 | share |  | **MISSING_IN_REPORT** |

Source: round-2/experiment-3/src/results/event_study/summary.json; round-2/experiment-3/src/results/event_study/summary_E_alt.json; round-2/experiment-3/src/results/event_study/summary_E_up.json; round-2/experiment-3/src/results/prediction/summary.json; round-2/experiment-3/src/results/robustness.json; round-2/experiment-4/src/results/analysis_summary.json ...

## B2 event study E_alt

| id | claim | value | 95% CI | n | unit | report (line) | flag |
|---|---|---|---|---|---|---|---|
| B2.E_alt.accretion_shift_rar.S | E_alt event-study S for accretion_shift_rar (primary): mean treated-minus-control over k in [-3,0] | -0.02088 | [-0.0335, 0.0925] | 10 | indicator units |  | **MISSING_IN_REPORT** |
| B2.E_alt.accretion_shift_rar.p_holm | E_alt event-study Holm p for accretion_shift_rar (family of 3 primaries) | 1 |  | 10 | p |  | **MISSING_IN_REPORT** |
| B2.E_alt.accretion_shift_rar.mde_sd | E_alt MDE (SD units) for accretion_shift_rar | 1.813 |  | 10 | SD |  | **MISSING_IN_REPORT** |
| B2.E_alt.accretion_shift_raw.S | E_alt event-study S for accretion_shift_raw (raw): mean treated-minus-control over k in [-3,0] | -0.07203 | [-0.235, 0.0928] | 10 | indicator units |  | **MISSING_IN_REPORT** |
| B2.E_alt.accretion_shift_rar_res.S | E_alt event-study S for accretion_shift_rar_res (res): mean treated-minus-control over k in [-3,0] | -0.02 | [-0.0326, 0.093] | 10 | indicator units |  | **MISSING_IN_REPORT** |
| B2.E_alt.closure.S | E_alt event-study S for closure (primary): mean treated-minus-control over k in [-3,0] | -0.4003 | [-0.919, 0.19] | 10 | indicator units | -0.4 (L410) | **OK** |
| B2.E_alt.closure.p_holm | E_alt event-study Holm p for closure (family of 3 primaries) | 0.504 |  | 10 | p | 0.096 (L410) | **WRONG_ESTIMATOR** |
| B2.E_alt.closure.mde_sd | E_alt MDE (SD units) for closure | 0.5944 |  | 10 | SD |  | **MISSING_IN_REPORT** |
| B2.E_alt.closure_raw.S | E_alt event-study S for closure_raw (raw): mean treated-minus-control over k in [-3,0] | -0.36 | [-1.38, 0.638] | 10 | indicator units |  | **MISSING_IN_REPORT** |
| B2.E_alt.closure_res.S | E_alt event-study S for closure_res (res): mean treated-minus-control over k in [-3,0] | -0.3266 | [-0.879, 0.203] | 10 | indicator units |  | **MISSING_IN_REPORT** |
| B2.E_alt.P_rar.S | E_alt event-study S for P_rar (primary): mean treated-minus-control over k in [-3,0] | -0.04439 | [-0.227, 0.102] | 10 | indicator units |  | **MISSING_IN_REPORT** |
| B2.E_alt.P_rar.p_holm | E_alt event-study Holm p for P_rar (family of 3 primaries) | 1 |  | 10 | p |  | **MISSING_IN_REPORT** |
| B2.E_alt.P_rar.mde_sd | E_alt MDE (SD units) for P_rar | 1.302 |  | 10 | SD |  | **MISSING_IN_REPORT** |
| B2.E_alt.P_raw.S | E_alt event-study S for P_raw (raw): mean treated-minus-control over k in [-3,0] | -0.008145 | [-0.2, 0.15] | 10 | indicator units |  | **MISSING_IN_REPORT** |
| B2.E_alt.P_rar_res.S | E_alt event-study S for P_rar_res (res): mean treated-minus-control over k in [-3,0] | -0.04698 | [-0.218, 0.107] | 10 | indicator units |  | **MISSING_IN_REPORT** |
| B2.E_alt.n_treated | E_alt: treated (onset) concepts | 14 |  |  | concepts |  | **MISSING_IN_REPORT** |
| B2.E_alt.n_matched | E_alt: treated with >= 1 control | 10 |  |  | concepts |  | **MISSING_IN_REPORT** |
| B2.E_alt.match_rate | E_alt: match rate (share of treated with controls) | 0.7143 |  | 14 | share of treated |  | **MISSING_IN_REPORT** |
| B2.E_alt.widened_share | E_alt: share of matched needing the widened caliper | 0.1 |  | 10 | share of matched |  | **MISSING_IN_REPORT** |
| B2.E_alt.mean_controls | E_alt: mean controls per matched treated | 1.8 |  | 10 | controls |  | **MISSING_IN_REPORT** |

Source: round-2/experiment-3/src/results/event_study/contrib_E_alt.parquet; round-2/experiment-3/src/results/event_study/matches_E_alt.csv; round-2/experiment-3/src/results/event_study/summary_E_alt.json

## B2 pooled panel E_alt

| id | claim | value | 95% CI | n | unit | report (line) | flag |
|---|---|---|---|---|---|---|---|
| B2.E_alt.pooled_panel.accretion_shift_rar.coef | E_alt pooled-panel coefficient on futE for accretion_shift_rar | -0.009763 | [-0.0518, 0.0345] | 212 | indicator units |  | **MISSING_IN_REPORT** |
| B2.E_alt.pooled_panel.closure.coef | E_alt pooled-panel coefficient on futE for closure | -0.529 | [-1.01, -0.0992] | 610 | indicator units |  | **MISSING_IN_REPORT** |
| B2.E_alt.pooled_panel.P_rar.coef | E_alt pooled-panel coefficient on futE for P_rar | 0.002214 | [-0.101, 0.1] | 545 | indicator units |  | **MISSING_IN_REPORT** |

Source: round-2/experiment-3/src/results/event_study/summary_E_alt.json

## B2 event study E_up

| id | claim | value | 95% CI | n | unit | report (line) | flag |
|---|---|---|---|---|---|---|---|
| B2.E_up.accretion_shift_rar.S | E_up event-study S for accretion_shift_rar (primary): mean treated-minus-control over k in [-3,0] | -0.1402 | [-0.185, 0.0184] | 21 | indicator units | -0.14 (L407) | **OK** |
| B2.E_up.accretion_shift_rar.p_holm | E_up event-study Holm p for accretion_shift_rar (family of 3 primaries) | 0.18 |  | 21 | p | 0.272 (L407) | **WRONG_ESTIMATOR** |
| B2.E_up.accretion_shift_rar.mde_sd | E_up MDE (SD units) for accretion_shift_rar | 2.106 |  | 21 | SD |  | **MISSING_IN_REPORT** |
| B2.E_up.accretion_shift_raw.S | E_up event-study S for accretion_shift_raw (raw): mean treated-minus-control over k in [-3,0] | -0.04714 | [-0.16, 0.0663] | 21 | indicator units |  | **MISSING_IN_REPORT** |
| B2.E_up.accretion_shift_rar_res.S | E_up event-study S for accretion_shift_rar_res (res): mean treated-minus-control over k in [-3,0] | -0.1396 | [-0.183, 0.0158] | 21 | indicator units |  | **MISSING_IN_REPORT** |
| B2.E_up.closure.S | E_up event-study S for closure (primary): mean treated-minus-control over k in [-3,0] | -0.837 | [-1.26, -0.427] | 21 | indicator units | -0.837 (L406) | **OK** |
| B2.E_up.closure.p_holm | E_up event-study Holm p for closure (family of 3 primaries) | 0.003 |  | 21 | p | 0.003 (L406) | **OK** |
| B2.E_up.closure.mde_sd | E_up MDE (SD units) for closure | 0.4533 |  | 21 | SD |  | **MISSING_IN_REPORT** |
| B2.E_up.closure_raw.S | E_up event-study S for closure_raw (raw): mean treated-minus-control over k in [-3,0] | -0.6882 | [-1.34, 0.00556] | 21 | indicator units |  | **MISSING_IN_REPORT** |
| B2.E_up.closure_res.S | E_up event-study S for closure_res (res): mean treated-minus-control over k in [-3,0] | -0.7313 | [-1.18, -0.288] | 21 | indicator units |  | **MISSING_IN_REPORT** |
| B2.E_up.P_rar.S | E_up event-study S for P_rar (primary): mean treated-minus-control over k in [-3,0] | -0.007085 | [-0.0661, 0.0562] | 21 | indicator units | -0.007 (L408) | **OK** |
| B2.E_up.P_rar.p_holm | E_up event-study Holm p for P_rar (family of 3 primaries) | 0.824 |  | 21 | p | 0.782 (L408) | **WRONG_ESTIMATOR** |
| B2.E_up.P_rar.mde_sd | E_up MDE (SD units) for P_rar | 0.4653 |  | 21 | SD |  | **MISSING_IN_REPORT** |
| B2.E_up.P_raw.S | E_up event-study S for P_raw (raw): mean treated-minus-control over k in [-3,0] | -0.02173 | [-0.0901, 0.045] | 21 | indicator units |  | **MISSING_IN_REPORT** |
| B2.E_up.P_rar_res.S | E_up event-study S for P_rar_res (res): mean treated-minus-control over k in [-3,0] | -0.009388 | [-0.0656, 0.0519] | 21 | indicator units |  | **MISSING_IN_REPORT** |
| B2.E_up.n_treated | E_up: treated (onset) concepts | 41 |  |  | concepts |  | **MISSING_IN_REPORT** |
| B2.E_up.n_matched | E_up: treated with >= 1 control | 21 |  |  | concepts |  | **MISSING_IN_REPORT** |
| B2.E_up.match_rate | E_up: match rate (share of treated with controls) | 0.5122 |  | 41 | share of treated | 51.2 (L388) | **OK** |
| B2.E_up.widened_share | E_up: share of matched needing the widened caliper | 0.3333 |  | 21 | share of matched | 33.3 (L388) | **OK** |
| B2.E_up.mean_controls | E_up: mean controls per matched treated | 1.619 |  | 21 | controls | 1.62 (L388) | **OK** |
| B2.E_up.closure.S_label | The E_up closure S = -0.837 is the matched EVENT-STUDY mean difference, not the pooled-panel coefficient (-0.743) | -0.837 | [-1.26, -0.427] | 21 | indicator units | -0.837 (L396) | **WRONG_ESTIMATOR** |
| B2.gate.main | R1a reproduction gate (main): E_up closure S re-run with the original estimator | -0.837 | [-1.26, -0.427] | 21 | indicator units |  | **OK** |
| B2.gate.mesh | R1a reproduction gate (mesh): E_up closure S re-run with the original estimator | -0.1846 | [-0.473, 0.125] | 51 | indicator units |  | **DRIFT_VALUE** |

Source: round-2/experiment-3/src/results/event_study/contrib_E_up.parquet; round-2/experiment-3/src/results/event_study/matches_E_up.csv; round-2/experiment-3/src/results/event_study/summary_E_up.json; round-2/experiment-4/src/results/rq1_effects_mainpool_aligned.csv

## B2 pooled panel E_up

| id | claim | value | 95% CI | n | unit | report (line) | flag |
|---|---|---|---|---|---|---|---|
| B2.E_up.pooled_panel.accretion_shift_rar.coef | E_up pooled-panel coefficient on futE for accretion_shift_rar | -0.03301 | [-0.0829, 0.0115] | 116 | indicator units |  | **MISSING_IN_REPORT** |
| B2.E_up.pooled_panel.closure.coef | E_up pooled-panel coefficient on futE for closure | -0.7426 | [-1.06, -0.464] | 514 | indicator units |  | **MISSING_IN_REPORT** |
| B2.E_up.pooled_panel.P_rar.coef | E_up pooled-panel coefficient on futE for P_rar | 0.008515 | [-0.0553, 0.0703] | 449 | indicator units |  | **MISSING_IN_REPORT** |

Source: round-2/experiment-3/src/results/event_study/summary_E_up.json

## B2 labels

| id | claim | value | 95% CI | n | unit | report (line) | flag |
|---|---|---|---|---|---|---|---|
| B2.E.rate_concept_years | E rate = positive concept-years / eligible concept-years | 0.02148 |  | 419 | share of concept-years | 2.1 (L384) | **OK** |
| B2.E.onsets | E: concepts with an onset in the 2008-2015 screen window | 4 |  | 90 | concepts | 4 (L384) | **OK** |
| B2.E_alt.rate_concept_years | E_alt rate = positive concept-years / eligible concept-years | 0.06683 |  | 419 | share of concept-years |  | **MISSING_IN_REPORT** |
| B2.E_alt.onsets | E_alt: concepts with an onset in the 2008-2015 screen window | 14 |  | 90 | concepts | 14 (L385) | **OK** |
| B2.E_up.rate_concept_years | E_up rate = positive concept-years / eligible concept-years | 0.3819 |  | 419 | share of concept-years | 38.2 (L386) | **OK** |
| B2.E_up.onsets | E_up: concepts with an onset in the 2008-2015 screen window | 41 |  | 90 | concepts | 41 (L386) | **OK** |

Source: round-2/experiment-3/src/results/labels/emergence_screen.parquet

## B3 prediction

| id | claim | value | 95% CI | n | unit | report (line) | flag |
|---|---|---|---|---|---|---|---|
| B3.E.logit.baseline_auc | E: BASELINE AUC (logit) | 0.9528 |  | 55 | AUC | 0.887 (L426) | **WRONG_ESTIMATOR** |
| B3.E.logit.full_auc | E: FULL AUC (logit) | 0.9245 |  | 55 | AUC | 0.925 (L426) | **OK** |
| B3.E.logit.delta_auc | E: FULL minus BASELINE AUC (logit) | -0.0283 | [-0.0943, 0.0189] | 55 | delta-AUC | 0.038 (L426) | **WRONG_ESTIMATOR** |
| B3.E.hgb.baseline_auc | E: BASELINE AUC (hgb) | 0.8868 |  | 55 | AUC |  | **MISSING_IN_REPORT** |
| B3.E.hgb.full_auc | E: FULL AUC (hgb) | 0.9245 |  | 55 | AUC |  | **MISSING_IN_REPORT** |
| B3.E.hgb.delta_auc | E: FULL minus BASELINE AUC (hgb) | 0.03774 | [-1.11e-16, 0.13] | 55 | delta-AUC |  | **MISSING_IN_REPORT** |
| B3.E_alt.logit.baseline_auc | E_alt: BASELINE AUC (logit) | 0.9359 |  | 55 | AUC | 0.686 (L427) | **WRONG_ESTIMATOR** |
| B3.E_alt.logit.full_auc | E_alt: FULL AUC (logit) | 0.9872 |  | 55 | AUC | 0.628 (L427) | **WRONG_ESTIMATOR** |
| B3.E_alt.logit.delta_auc | E_alt: FULL minus BASELINE AUC (logit) | 0.05128 | [0, 0.132] | 55 | delta-AUC | -0.058 (L427) | **WRONG_ESTIMATOR** |
| B3.E_alt.hgb.baseline_auc | E_alt: BASELINE AUC (hgb) | 0.6859 |  | 55 | AUC |  | **MISSING_IN_REPORT** |
| B3.E_alt.hgb.full_auc | E_alt: FULL AUC (hgb) | 0.6282 |  | 55 | AUC |  | **MISSING_IN_REPORT** |
| B3.E_alt.hgb.delta_auc | E_alt: FULL minus BASELINE AUC (hgb) | -0.05769 | [-0.537, 0.407] | 55 | delta-AUC |  | **MISSING_IN_REPORT** |
| B3.E_up.logit.baseline_auc | E_up: BASELINE AUC (logit) | 0.8898 |  | 131 | AUC | 0.859 (L416) | **WRONG_ESTIMATOR** |
| B3.E_up.logit.full_auc | E_up: FULL AUC (logit) | 0.8793 |  | 131 | AUC | 0.878 (L416) | **WRONG_ESTIMATOR** |
| B3.E_up.logit.delta_auc | E_up: FULL minus BASELINE AUC (logit) | -0.01043 | [-0.0453, 0.0213] | 131 | delta-AUC | 0.019 (L416) | **WRONG_ESTIMATOR** |
| B3.E_up.hgb.baseline_auc | E_up: BASELINE AUC (hgb) | 0.8593 |  | 131 | AUC |  | **MISSING_IN_REPORT** |
| B3.E_up.hgb.full_auc | E_up: FULL AUC (hgb) | 0.8781 |  | 131 | AUC |  | **MISSING_IN_REPORT** |
| B3.E_up.hgb.delta_auc | E_up: FULL minus BASELINE AUC (hgb) | 0.01886 | [-0.0245, 0.0604] | 131 | delta-AUC |  | **MISSING_IN_REPORT** |

Source: round-2/experiment-3/src/results/prediction/predictions.parquet

## B5 MeSH plan-native

| id | claim | value | 95% CI | n | unit | report (line) | flag |
|---|---|---|---|---|---|---|---|
| B5.mesh.PRIMARY.closure_lr.D | MeSH PRIMARY: D (closure_lr), mean diff over rel -3..-1 | -0.08614 | [-0.511, 0.402] | 15 | indicator units | -0.086 (L467) | **OK** |
| B5.mesh.PRIMARY.closure_lr.p_holm | MeSH PRIMARY: Holm p (closure_lr) | 0.677 |  | 15 | p | 0.677 (L467) | **OK** |
| B5.mesh.PRIMARY.n_eff | MeSH PRIMARY: n_eff (treated with a finite window diff) | 15 |  |  | concepts | 15 (L467) | **OK** |
| B5.mesh.PRIMARY.accretion_share.D | MeSH PRIMARY: D (accretion_share), mean diff over rel -3..-1 | 0.09369 | [-0.0364, 0.21] | 15 | indicator units |  | **MISSING_IN_REPORT** |
| B5.mesh.PRIMARY.accretion_share.p_holm | MeSH PRIMARY: Holm p (accretion_share) | 0.48 |  | 15 | p | 0.48 (L474) | **OK** |
| B5.mesh.PRIMARY.dP.D | MeSH PRIMARY: D (dP), mean diff over rel -3..-1 | 0.02531 | [-0.0168, 0.0735] | 15 | indicator units |  | **MISSING_IN_REPORT** |
| B5.mesh.PRIMARY.dP.p_holm | MeSH PRIMARY: Holm p (dP) | 0.506 |  | 15 | p | 0.506 (L474) | **OK** |
| B5.mesh.PRIMARY_E_cent_only.closure_lr.D | MeSH PRIMARY_E_cent_only: D (closure_lr), mean diff over rel -3..-1 | -0.1481 | [-0.399, 0.105] | 30 | indicator units | -0.148 (L470) | **OK** |
| B5.mesh.PRIMARY_E_cent_only.closure_lr.p_holm | MeSH PRIMARY_E_cent_only: Holm p (closure_lr) | 0.486 |  | 30 | p |  | **MISSING_IN_REPORT** |
| B5.mesh.PRIMARY_E_cent_only.n_eff | MeSH PRIMARY_E_cent_only: n_eff (treated with a finite window diff) | 30 |  |  | concepts | 30 (L470) | **OK** |
| B5.mesh.PRIMARY_E_cent_only.accretion_share.D | MeSH PRIMARY_E_cent_only: D (accretion_share), mean diff over rel -3..-1 | 0.07241 | [-0.0644, 0.206] | 30 | indicator units |  | **MISSING_IN_REPORT** |
| B5.mesh.PRIMARY_E_cent_only.accretion_share.p_holm | MeSH PRIMARY_E_cent_only: Holm p (accretion_share) | 0.486 |  | 30 | p |  | **MISSING_IN_REPORT** |
| B5.mesh.PRIMARY_E_cent_only.dP.D | MeSH PRIMARY_E_cent_only: D (dP), mean diff over rel -3..-1 | 0.0507 | [0.0143, 0.0871] | 30 | indicator units |  | **MISSING_IN_REPORT** |
| B5.mesh.PRIMARY_E_cent_only.dP.p_holm | MeSH PRIMARY_E_cent_only: Holm p (dP) | 0.015 |  | 30 | p |  | **MISSING_IN_REPORT** |
| B5.mesh.SENS1.closure_lr.D | MeSH SENS1: D (closure_lr), mean diff over rel -3..-1 | -0.4194 | [-0.74, -0.115] | 29 | indicator units | -0.419 (L468) | **OK** |
| B5.mesh.SENS1.closure_lr.p_holm | MeSH SENS1: Holm p (closure_lr) | 0.039 |  | 29 | p | 0.039 (L468) | **OK** |
| B5.mesh.SENS1.n_eff | MeSH SENS1: n_eff (treated with a finite window diff) | 29 |  |  | concepts | 29 (L468) | **OK** |
| B5.mesh.SENS1.accretion_share.D | MeSH SENS1: D (accretion_share), mean diff over rel -3..-1 | -0.02 | [-0.143, 0.0981] | 29 | indicator units |  | **MISSING_IN_REPORT** |
| B5.mesh.SENS1.accretion_share.p_holm | MeSH SENS1: Holm p (accretion_share) | 1 |  | 29 | p |  | **MISSING_IN_REPORT** |
| B5.mesh.SENS1.dP.D | MeSH SENS1: D (dP), mean diff over rel -3..-1 | 0.01026 | [-0.0288, 0.0507] | 29 | indicator units | 0.051 (L474) | **WRONG_DEFINITION** |
| B5.mesh.SENS1.dP.p_holm | MeSH SENS1: Holm p (dP) | 1 |  | 29 | p | 0.015 (L474) | **WRONG_DEFINITION** |
| B5.mesh.SENS2.closure_lr.D | MeSH SENS2: D (closure_lr), mean diff over rel -3..-1 | -0.8579 | [-1.67, 0.0337] | 10 | indicator units | -0.858 (L469) | **OK** |
| B5.mesh.SENS2.closure_lr.p_holm | MeSH SENS2: Holm p (closure_lr) | 0.124 |  | 10 | p |  | **MISSING_IN_REPORT** |
| B5.mesh.SENS2.n_eff | MeSH SENS2: n_eff (treated with a finite window diff) | 10 |  |  | concepts | 10 (L469) | **OK** |
| B5.mesh.SENS2.accretion_share.D | MeSH SENS2: D (accretion_share), mean diff over rel -3..-1 | -0.2488 | [-0.467, -0.0159] | 10 | indicator units |  | **MISSING_IN_REPORT** |
| B5.mesh.SENS2.accretion_share.p_holm | MeSH SENS2: Holm p (accretion_share) | 0.111 |  | 10 | p |  | **MISSING_IN_REPORT** |
| B5.mesh.SENS2.dP.D | MeSH SENS2: D (dP), mean diff over rel -3..-1 | -0.01718 | [-0.0621, 0.0261] | 10 | indicator units |  | **MISSING_IN_REPORT** |
| B5.mesh.SENS2.dP.p_holm | MeSH SENS2: Holm p (dP) | 0.467 |  | 10 | p |  | **MISSING_IN_REPORT** |

Source: round-2/experiment-4/src/results/rq1_effects.csv

## B5 MeSH matching

| id | claim | value | 95% CI | n | unit | report (line) | flag |
|---|---|---|---|---|---|---|---|
| B5.match.PRIMARY|all.rate3_20 | MeSH PRIMARY|all: share of treated with 3 controls at +-20% | 0.3889 |  | 18 | share of treated | 72.2 (L457) | **WRONG_DEFINITION** |
| B5.match.PRIMARY|all.rate3_30 | MeSH PRIMARY|all: share of treated with 3 controls at <= +-30% | 0.7222 |  | 18 | share of treated | 83.3 (L457) | **WRONG_DEFINITION** |
| B5.match.PRIMARY|all.rate_any | MeSH PRIMARY|all: share of treated with any control | 0.8333 |  | 18 | share of treated |  | **MISSING_IN_REPORT** |
| B5.match.SENS1|all.rate3_20 | MeSH SENS1|all: share of treated with 3 controls at +-20% | 0.5588 |  | 34 | share of treated |  | **MISSING_IN_REPORT** |
| B5.match.SENS1|all.rate3_30 | MeSH SENS1|all: share of treated with 3 controls at <= +-30% | 0.7059 |  | 34 | share of treated |  | **MISSING_IN_REPORT** |
| B5.match.SENS1|all.rate_any | MeSH SENS1|all: share of treated with any control | 0.8529 |  | 34 | share of treated |  | **MISSING_IN_REPORT** |
| B5.match.SENS2|all.rate3_20 | MeSH SENS2|all: share of treated with 3 controls at +-20% | 0 |  | 14 | share of treated |  | **MISSING_IN_REPORT** |
| B5.match.SENS2|all.rate3_30 | MeSH SENS2|all: share of treated with 3 controls at <= +-30% | 0.2143 |  | 14 | share of treated |  | **MISSING_IN_REPORT** |
| B5.match.SENS2|all.rate_any | MeSH SENS2|all: share of treated with any control | 0.7143 |  | 14 | share of treated |  | **MISSING_IN_REPORT** |
| B5.match.PRIMARY|rule_parity.rate3_20 | MeSH PRIMARY|rule_parity: share of treated with 3 controls at +-20% | 0.3529 |  | 17 | share of treated |  | **MISSING_IN_REPORT** |
| B5.match.PRIMARY|rule_parity.rate3_30 | MeSH PRIMARY|rule_parity: share of treated with 3 controls at <= +-30% | 0.7059 |  | 17 | share of treated |  | **MISSING_IN_REPORT** |
| B5.match.PRIMARY|rule_parity.rate_any | MeSH PRIMARY|rule_parity: share of treated with any control | 0.8235 |  | 17 | share of treated |  | **MISSING_IN_REPORT** |
| B5.match.PRIMARY|t_le_2018.rate3_20 | MeSH PRIMARY|t_le_2018: share of treated with 3 controls at +-20% | 0.3889 |  | 18 | share of treated |  | **MISSING_IN_REPORT** |
| B5.match.PRIMARY|t_le_2018.rate3_30 | MeSH PRIMARY|t_le_2018: share of treated with 3 controls at <= +-30% | 0.7222 |  | 18 | share of treated |  | **MISSING_IN_REPORT** |
| B5.match.PRIMARY|t_le_2018.rate_any | MeSH PRIMARY|t_le_2018: share of treated with any control | 0.8333 |  | 18 | share of treated |  | **MISSING_IN_REPORT** |
| B5.match.PRIMARY|domain_match.rate3_20 | MeSH PRIMARY|domain_match: share of treated with 3 controls at +-20% | 0.4444 |  | 18 | share of treated |  | **MISSING_IN_REPORT** |
| B5.match.PRIMARY|domain_match.rate3_30 | MeSH PRIMARY|domain_match: share of treated with 3 controls at <= +-30% | 0.7778 |  | 18 | share of treated |  | **MISSING_IN_REPORT** |
| B5.match.PRIMARY|domain_match.rate_any | MeSH PRIMARY|domain_match: share of treated with any control | 0.9444 |  | 18 | share of treated |  | **MISSING_IN_REPORT** |
| B5.match.PRIMARY|E_cent_only.rate3_20 | MeSH PRIMARY|E_cent_only: share of treated with 3 controls at +-20% | 0.2381 |  | 42 | share of treated |  | **MISSING_IN_REPORT** |
| B5.match.PRIMARY|E_cent_only.rate3_30 | MeSH PRIMARY|E_cent_only: share of treated with 3 controls at <= +-30% | 0.4286 |  | 42 | share of treated |  | **MISSING_IN_REPORT** |
| B5.match.PRIMARY|E_cent_only.rate_any | MeSH PRIMARY|E_cent_only: share of treated with any control | 0.7143 |  | 42 | share of treated |  | **MISSING_IN_REPORT** |

Source: round-2/experiment-4/src/results/matched_sets.json

## B11 structure

| id | claim | value | 95% CI | n | unit | report (line) | flag |
|---|---|---|---|---|---|---|---|
| B11.leiden_ami.2008 | Main-pool Leiden bootstrap AMI, snapshot 2008 | 0.6322 |  | 20 | AMI |  | **MISSING_IN_REPORT** |
| B11.leiden_ami.2013 | Main-pool Leiden bootstrap AMI, snapshot 2013 | 0.6249 |  | 20 | AMI |  | **MISSING_IN_REPORT** |
| B11.leiden_ami.2018 | Main-pool Leiden bootstrap AMI, snapshot 2018 | 0.6194 |  | 20 | AMI |  | **MISSING_IN_REPORT** |
| B11.main.nodes_median | Main-pool snapshot nodes (median over 25 yearly snapshots) | 2.723e+04 |  | 25 | nodes | 1487 (L374) | **DRIFT_VALUE** |
| B11.main.kept_edges_median | Main-pool kept edges (median over snapshots) | 8.388e+04 |  | 25 | edges |  | **MISSING_IN_REPORT** |
| B11.mesh.nodes_median | MeSH background snapshot nodes (median) | 2.727e+04 |  | 26 | nodes |  | **MISSING_IN_REPORT** |
| B11.typology.k2.min_jaccard | Typology min bootstrap Jaccard at k=2 | 0.4877 |  | 59 | Jaccard | 0.49 (L436) | **OK** |
| B11.typology.k3.min_jaccard | Typology min bootstrap Jaccard at k=3 | 0.5071 |  | 59 | Jaccard | 0.51 (L436) | **OK** |
| B11.typology.k4.min_jaccard | Typology min bootstrap Jaccard at k=4 | 0.4519 |  | 59 | Jaccard | 0.45 (L436) | **OK** |
| B11.typology.k5.min_jaccard | Typology min bootstrap Jaccard at k=5 | 0.4205 |  | 59 | Jaccard | 0.42 (L436) | **OK** |
| B11.typology.k6.min_jaccard | Typology min bootstrap Jaccard at k=6 | 0.4595 |  | 59 | Jaccard | 0.46 (L436) | **OK** |
| B11.pattern.INCUBATION_THEN_EXPANSION__age0_8 | Main-pool pattern frequency INCUBATION_THEN_EXPANSION__age0_8 (overall) | 0 | [0, 0] | 123 | share |  | **MISSING_IN_REPORT** |
| B11.pattern.GRADUAL_CENTRALISATION__age0_8 | Main-pool pattern frequency GRADUAL_CENTRALISATION__age0_8 (overall) | 0.03252 | [0.00813, 0.065] | 123 | share |  | **MISSING_IN_REPORT** |
| B11.pattern.EARLY_BRIDGING__age0_8 | Main-pool pattern frequency EARLY_BRIDGING__age0_8 (overall) | 0.7642 | [0.691, 0.837] | 123 | share | 76 (L432) | **OK** |
| B11.pattern.INCUBATION_THEN_EXPANSION__pre_onset | Main-pool pattern frequency INCUBATION_THEN_EXPANSION__pre_onset (overall) | 0 | [0, 0] | 123 | share |  | **MISSING_IN_REPORT** |
| B11.pattern.GRADUAL_CENTRALISATION__pre_onset | Main-pool pattern frequency GRADUAL_CENTRALISATION__pre_onset (overall) | 0.01626 | [0, 0.0407] | 123 | share |  | **MISSING_IN_REPORT** |
| B11.pattern.EARLY_BRIDGING__pre_onset | Main-pool pattern frequency EARLY_BRIDGING__pre_onset (overall) | 0.7236 | [0.634, 0.797] | 123 | share |  | **MISSING_IN_REPORT** |
| B11.pattern.INCUBATION_THEN_EXPANSION__age0_8_rawfallback | Main-pool pattern frequency INCUBATION_THEN_EXPANSION__age0_8_rawfallback (overall) | 0 | [0, 0] | 123 | share |  | **MISSING_IN_REPORT** |
| B11.pattern.EARLY_BRIDGING__age0_8_Prar | Main-pool pattern frequency EARLY_BRIDGING__age0_8_Prar (overall) | 0.6911 | [0.61, 0.772] | 123 | share |  | **MISSING_IN_REPORT** |
| B11.pattern.INCUBATION_THEN_EXPANSION__age0_8_ageadj | Main-pool pattern frequency INCUBATION_THEN_EXPANSION__age0_8_ageadj (overall) | 0.01626 | [0, 0.0407] | 123 | share |  | **MISSING_IN_REPORT** |
| B11.pattern.INCUBATION_THEN_EXPANSION__pre_onset_ageadj | Main-pool pattern frequency INCUBATION_THEN_EXPANSION__pre_onset_ageadj (overall) | 0 | [0, 0] | 123 | share |  | **MISSING_IN_REPORT** |
| B11.pattern.early_bridging_definition | Early-bridging DEFINITION: P > 0.6 (raw) or top-decile cross-community betweenness in the first 2 years (SPEC early_bridging P_raw=0.6, btw_pct=90) | 0.6 |  |  | P threshold | 75 (L432) | **WRONG_DEFINITION** |
| B11.mesh.pattern.incubation_expansion | MeSH pattern frequency incubation_expansion | 0.1675 | [0.12, 0.22] | 191 | share |  | **MISSING_IN_REPORT** |
| B11.mesh.pattern.gradual_centralisation | MeSH pattern frequency gradual_centralisation | 0.01571 | [0, 0.0366] | 191 | share |  | **MISSING_IN_REPORT** |
| B11.mesh.pattern.early_bridging | MeSH pattern frequency early_bridging | 0.5864 | [0.513, 0.654] | 191 | share |  | **MISSING_IN_REPORT** |
| B11.mesh.pattern.none | MeSH pattern frequency none | 0.3037 | [0.236, 0.367] | 191 | share |  | **MISSING_IN_REPORT** |

Source: round-2/experiment-3/src/config.py; round-2/experiment-3/src/results/patterns/summary_E_up.json; round-2/experiment-3/src/results/robustness.json; round-2/experiment-3/src/results/snapshot_summary.csv; round-2/experiment-3/src/results/typology/stability.json; round-2/experiment-4/src/results/rq1_patterns.csv ...

## B6 viability

| id | claim | value | 95% CI | n | unit | report (line) | flag |
|---|---|---|---|---|---|---|---|
| B6.state.SOURCE | Viability SOURCE edges at n_min 30 (of 779 eligible) | 63 |  | 779 | edges | 63 (L323) | **OK** |
| B6.share_tested.SOURCE | SOURCE share of tested edges | 0.3728 |  | 169 | share of tested | 37.3 (L323) | **OK** |
| B6.state.SINK | Viability SINK edges at n_min 30 (of 779 eligible) | 26 |  | 779 | edges | 26 (L324) | **OK** |
| B6.share_tested.SINK | SINK share of tested edges | 0.1538 |  | 169 | share of tested | 15.4 (L324) | **OK** |
| B6.state.FADING | Viability FADING edges at n_min 30 (of 779 eligible) | 7 |  | 779 | edges | 7 (L325) | **OK** |
| B6.share_tested.FADING | FADING share of tested edges | 0.04142 |  | 169 | share of tested | 4.1 (L325) | **OK** |
| B6.state.UNDETERMINED | Viability UNDETERMINED edges at n_min 30 (of 779 eligible) | 683 |  | 779 | edges | 683 (L326) | **OK** |
| B6.tested | Tested edges | 169 |  | 779 | edges | 169 (L317) | **OK** |
| B6.tested_undetermined | Tested but UNDETERMINED edges (the missing 43% of the 'share of tested' column) | 73 |  | 169 | edges |  | **MISSING_IN_REPORT** |
| B6.share_tested_sum | Sum of the SOURCE/SINK/FADING 'share of tested' column (Table 13 labels the tested total 100%) | 0.568 |  | 169 | share of tested | 100 (L328) | **WRONG_DEFINITION** |
| B6.reason.below_nmin | Reason-code share 'below_nmin' | 0.656 |  | 779 | share of eligible |  | **MISSING_IN_REPORT** |
| B6.reason.tested | Reason-code share 'tested' | 0.2169 |  | 779 | share of eligible |  | **MISSING_IN_REPORT** |
| B6.reason.no_cohort_parents | Reason-code share 'no_cohort_parents' | 0.1271 |  | 779 | share of eligible |  | **MISSING_IN_REPORT** |
| B6.nmin5.SOURCE | SOURCE edges at n_min 5 | 78 |  | 779 | edges |  | **MISSING_IN_REPORT** |
| B6.nmin5.SINK | SINK edges at n_min 5 | 154 |  | 779 | edges |  | **MISSING_IN_REPORT** |
| B6.nmin5.FADING | FADING edges at n_min 5 | 52 |  | 779 | edges |  | **MISSING_IN_REPORT** |
| B6.nmin10.SOURCE | SOURCE edges at n_min 10 | 77 |  | 779 | edges |  | **MISSING_IN_REPORT** |
| B6.nmin10.SINK | SINK edges at n_min 10 | 130 |  | 779 | edges |  | **MISSING_IN_REPORT** |
| B6.nmin10.FADING | FADING edges at n_min 10 | 50 |  | 779 | edges |  | **MISSING_IN_REPORT** |
| B6.nmin20.SOURCE | SOURCE edges at n_min 20 | 81 |  | 779 | edges |  | **MISSING_IN_REPORT** |
| B6.nmin20.SINK | SINK edges at n_min 20 | 45 |  | 779 | edges |  | **MISSING_IN_REPORT** |
| B6.nmin20.FADING | FADING edges at n_min 20 | 19 |  | 779 | edges |  | **MISSING_IN_REPORT** |
| B6.nmin30.SOURCE | SOURCE edges at n_min 30 | 63 |  | 779 | edges |  | **MISSING_IN_REPORT** |
| B6.nmin30.SINK | SINK edges at n_min 30 | 26 |  | 779 | edges |  | **MISSING_IN_REPORT** |
| B6.nmin30.FADING | FADING edges at n_min 30 | 7 |  | 779 | edges |  | **MISSING_IN_REPORT** |

Source: round-2/experiment-2/src/results/viability/viability_layer.csv

## B7 dataset_5

| id | claim | value | 95% CI | n | unit | report (line) | flag |
|---|---|---|---|---|---|---|---|
| B7.nativeness.weight_share | Share of host (non-origin) co-occurrence WEIGHT covered by the 1,372 profiled nodes | 0.7872 |  | 418 | share of host WEIGHT | 78.7 (L240) | **WRONG_DEFINITION** |
| B7.asjc.covered_venues | ASJC-covered venues | 2929 |  | 22970 | venues | 2929 (L253) | **OK** |
| B7.asjc.venue_share | Share of VENUES that are ASJC-covered | 0.1275 |  | 22970 | share of venues |  | **MISSING_IN_REPORT** |
| B7.asjc.link_share | Share of concept-work LINKS in ASJC-covered venues | 0.1158 |  | 488078 | share of LINKS | 12.1 (L252) | **WRONG_UNITS** |
| B7.links | Verified concept-work links | 4.881e+05 |  |  | links |  | **MISSING_IN_REPORT** |
| B7.credits | OpenAlex credits consumed by dataset_5 | 7237 |  |  | credits | 7237 (L248) | **OK** |

Source: round-2/dataset-5/src/full_data_out/full_data_out_*.json; round-2/dataset-5/src/run_ledger.json

## B8 H1 power

| id | claim | value | 95% CI | n | unit | report (line) | flag |
|---|---|---|---|---|---|---|---|
| B8.h1_mde.auc|nmin5|AUC0.7|realised | H1 MDE (auc) at n_min 5, target AUC0.7, design realised | 0.06961 |  | 325 | delta-AUC | 1.22 (L352) | **WRONG_UNITS** |
| B8.h1_mde.auc|nmin5|AUC0.7|projected | H1 MDE (auc) at n_min 5, target AUC0.7, design projected | 0.03868 |  | 325 | delta-AUC |  | **MISSING_IN_REPORT** |
| B8.h1_mde.auc|nmin5|AUC0.7|N150 | H1 MDE (auc) at n_min 5, target AUC0.7, design N150 | 0.05815 |  | 325 | delta-AUC |  | **MISSING_IN_REPORT** |
| B8.h1_mde.auc|nmin5|AUC0.8|realised | H1 MDE (auc) at n_min 5, target AUC0.8, design realised | 0.04983 |  | 325 | delta-AUC |  | **MISSING_IN_REPORT** |
| B8.h1_mde.auc|nmin5|AUC0.8|projected | H1 MDE (auc) at n_min 5, target AUC0.8, design projected | 0.03362 |  | 325 | delta-AUC |  | **MISSING_IN_REPORT** |
| B8.h1_mde.auc|nmin5|AUC0.8|N150 | H1 MDE (auc) at n_min 5, target AUC0.8, design N150 | 0.03906 |  | 325 | delta-AUC |  | **MISSING_IN_REPORT** |
| B8.h1_mde.r2|nmin5|R20.1|realised | H1 MDE (r2) at n_min 5, target R20.1, design realised | 0.08085 |  | 325 | delta-R2 |  | **MISSING_IN_REPORT** |
| B8.h1_mde.r2|nmin5|R20.1|projected | H1 MDE (r2) at n_min 5, target R20.1, design projected | 0.05306 |  | 325 | delta-R2 |  | **MISSING_IN_REPORT** |
| B8.h1_mde.r2|nmin5|R20.1|N150 | H1 MDE (r2) at n_min 5, target R20.1, design N150 | 0.06355 |  | 325 | delta-R2 |  | **MISSING_IN_REPORT** |
| B8.h1_mde.r2|nmin5|R20.3|realised | H1 MDE (r2) at n_min 5, target R20.3, design realised | 0.04741 |  | 325 | delta-R2 |  | **MISSING_IN_REPORT** |
| B8.h1_mde.r2|nmin5|R20.3|projected | H1 MDE (r2) at n_min 5, target R20.3, design projected | 0.02941 |  | 325 | delta-R2 |  | **MISSING_IN_REPORT** |
| B8.h1_mde.r2|nmin5|R20.3|N150 | H1 MDE (r2) at n_min 5, target R20.3, design N150 | 0.03999 |  | 325 | delta-R2 |  | **MISSING_IN_REPORT** |
| B8.h1_mde.auc|nmin10|AUC0.7|realised | H1 MDE (auc) at n_min 10, target AUC0.7, design realised | 0.07321 |  | 304 | delta-AUC | 0.89 (L353) | **WRONG_UNITS** |
| B8.h1_mde.auc|nmin10|AUC0.7|projected | H1 MDE (auc) at n_min 10, target AUC0.7, design projected | 0.04243 |  | 304 | delta-AUC |  | **MISSING_IN_REPORT** |
| B8.h1_mde.auc|nmin10|AUC0.7|N150 | H1 MDE (auc) at n_min 10, target AUC0.7, design N150 | 0.05568 |  | 304 | delta-AUC |  | **MISSING_IN_REPORT** |
| B8.h1_mde.auc|nmin10|AUC0.8|realised | H1 MDE (auc) at n_min 10, target AUC0.8, design realised | 0.05384 |  | 304 | delta-AUC |  | **MISSING_IN_REPORT** |
| B8.h1_mde.auc|nmin10|AUC0.8|projected | H1 MDE (auc) at n_min 10, target AUC0.8, design projected | 0.03707 |  | 304 | delta-AUC | 0.72 (L356) | **WRONG_UNITS** |
| B8.h1_mde.auc|nmin10|AUC0.8|N150 | H1 MDE (auc) at n_min 10, target AUC0.8, design N150 | 0.04064 |  | 304 | delta-AUC |  | **MISSING_IN_REPORT** |
| B8.h1_mde.r2|nmin10|R20.1|realised | H1 MDE (r2) at n_min 10, target R20.1, design realised | 0.08037 |  | 304 | delta-R2 |  | **MISSING_IN_REPORT** |
| B8.h1_mde.r2|nmin10|R20.1|projected | H1 MDE (r2) at n_min 10, target R20.1, design projected | 0.05879 |  | 304 | delta-R2 |  | **MISSING_IN_REPORT** |
| B8.h1_mde.r2|nmin10|R20.1|N150 | H1 MDE (r2) at n_min 10, target R20.1, design N150 | 0.06785 |  | 304 | delta-R2 |  | **MISSING_IN_REPORT** |
| B8.h1_mde.r2|nmin10|R20.3|realised | H1 MDE (r2) at n_min 10, target R20.3, design realised | 0.05106 |  | 304 | delta-R2 |  | **MISSING_IN_REPORT** |
| B8.h1_mde.r2|nmin10|R20.3|projected | H1 MDE (r2) at n_min 10, target R20.3, design projected | 0.03928 |  | 304 | delta-R2 |  | **MISSING_IN_REPORT** |
| B8.h1_mde.r2|nmin10|R20.3|N150 | H1 MDE (r2) at n_min 10, target R20.3, design N150 | 0.04235 |  | 304 | delta-R2 |  | **MISSING_IN_REPORT** |
| B8.h1_mde.auc|nmin20|AUC0.7|realised | H1 MDE (auc) at n_min 20, target AUC0.7, design realised | 0.09986 |  | 174 | delta-AUC | 0.64 (L354) | **WRONG_UNITS** |
| B8.h1_mde.auc|nmin20|AUC0.7|projected | H1 MDE (auc) at n_min 20, target AUC0.7, design projected | 0.06502 |  | 174 | delta-AUC |  | **MISSING_IN_REPORT** |
| B8.h1_mde.auc|nmin20|AUC0.7|N150 | H1 MDE (auc) at n_min 20, target AUC0.7, design N150 | 0.05873 |  | 174 | delta-AUC |  | **MISSING_IN_REPORT** |
| B8.h1_mde.auc|nmin20|AUC0.8|realised | H1 MDE (auc) at n_min 20, target AUC0.8, design realised | 0.09183 |  | 174 | delta-AUC |  | **MISSING_IN_REPORT** |
| B8.h1_mde.auc|nmin20|AUC0.8|projected | H1 MDE (auc) at n_min 20, target AUC0.8, design projected | 0.04259 |  | 174 | delta-AUC | 0.51 (L357) | **WRONG_UNITS** |
| B8.h1_mde.auc|nmin20|AUC0.8|N150 | H1 MDE (auc) at n_min 20, target AUC0.8, design N150 | 0.039 |  | 174 | delta-AUC | 0.44 (L359) | **WRONG_UNITS** |
| B8.h1_mde.r2|nmin20|R20.1|realised | H1 MDE (r2) at n_min 20, target R20.1, design realised | 0.14 |  | 174 | delta-R2 |  | **MISSING_IN_REPORT** |
| B8.h1_mde.r2|nmin20|R20.1|projected | H1 MDE (r2) at n_min 20, target R20.1, design projected | 0.08043 |  | 174 | delta-R2 |  | **MISSING_IN_REPORT** |
| B8.h1_mde.r2|nmin20|R20.1|N150 | H1 MDE (r2) at n_min 20, target R20.1, design N150 | 0.07328 |  | 174 | delta-R2 |  | **MISSING_IN_REPORT** |
| B8.h1_mde.r2|nmin20|R20.3|realised | H1 MDE (r2) at n_min 20, target R20.3, design realised | 0.08956 |  | 174 | delta-R2 |  | **MISSING_IN_REPORT** |
| B8.h1_mde.r2|nmin20|R20.3|projected | H1 MDE (r2) at n_min 20, target R20.3, design projected | 0.04703 |  | 174 | delta-R2 |  | **MISSING_IN_REPORT** |
| B8.h1_mde.r2|nmin20|R20.3|N150 | H1 MDE (r2) at n_min 20, target R20.3, design N150 | 0.0451 |  | 174 | delta-R2 |  | **MISSING_IN_REPORT** |
| B8.h1_mde.auc|nmin30|AUC0.7|realised | H1 MDE (auc) at n_min 30, target AUC0.7, design realised | 0.1343 |  | 112 | delta-AUC | 0.53 (L355) | **WRONG_UNITS** |
| B8.h1_mde.auc|nmin30|AUC0.7|projected | H1 MDE (auc) at n_min 30, target AUC0.7, design projected | 0.08379 |  | 112 | delta-AUC |  | **MISSING_IN_REPORT** |
| B8.h1_mde.auc|nmin30|AUC0.7|N150 | H1 MDE (auc) at n_min 30, target AUC0.7, design N150 | 0.05873 |  | 112 | delta-AUC |  | **MISSING_IN_REPORT** |
| B8.h1_mde.auc|nmin30|AUC0.8|realised | H1 MDE (auc) at n_min 30, target AUC0.8, design realised | 0.116 |  | 112 | delta-AUC |  | **MISSING_IN_REPORT** |
| B8.h1_mde.auc|nmin30|AUC0.8|projected | H1 MDE (auc) at n_min 30, target AUC0.8, design projected | 0.06887 |  | 112 | delta-AUC | 0.42 (L358) | **WRONG_UNITS** |
| B8.h1_mde.auc|nmin30|AUC0.8|N150 | H1 MDE (auc) at n_min 30, target AUC0.8, design N150 | 0.03905 |  | 112 | delta-AUC | 0.36 (L360) | **WRONG_UNITS** |
| B8.h1_mde.r2|nmin30|R20.1|realised | H1 MDE (r2) at n_min 30, target R20.1, design realised | 0.2022 |  | 112 | delta-R2 |  | **MISSING_IN_REPORT** |
| B8.h1_mde.r2|nmin30|R20.1|projected | H1 MDE (r2) at n_min 30, target R20.1, design projected | 0.1208 |  | 112 | delta-R2 |  | **MISSING_IN_REPORT** |
| B8.h1_mde.r2|nmin30|R20.1|N150 | H1 MDE (r2) at n_min 30, target R20.1, design N150 | 0.07223 |  | 112 | delta-R2 |  | **MISSING_IN_REPORT** |
| B8.h1_mde.r2|nmin30|R20.3|realised | H1 MDE (r2) at n_min 30, target R20.3, design realised | 0.1422 |  | 112 | delta-R2 |  | **MISSING_IN_REPORT** |
| B8.h1_mde.r2|nmin30|R20.3|projected | H1 MDE (r2) at n_min 30, target R20.3, design projected | 0.07833 |  | 112 | delta-R2 |  | **MISSING_IN_REPORT** |
| B8.h1_mde.r2|nmin30|R20.3|N150 | H1 MDE (r2) at n_min 30, target R20.3, design N150 | 0.0447 |  | 112 | delta-R2 |  | **MISSING_IN_REPORT** |
| B8.Nc.n_min_5.realised | Realised N_c at n_min_5 | 93 |  |  | concepts |  | **MISSING_IN_REPORT** |
| B8.Nc.n_min_5.projected | Projected N_c at n_min_5 | 189.7 |  |  | concepts |  | **MISSING_IN_REPORT** |
| B8.Nc.n_min_10.realised | Realised N_c at n_min_10 | 91 |  |  | concepts |  | **MISSING_IN_REPORT** |
| B8.Nc.n_min_10.projected | Projected N_c at n_min_10 | 184.7 |  |  | concepts |  | **MISSING_IN_REPORT** |
| B8.Nc.n_min_20.realised | Realised N_c at n_min_20 | 58 |  |  | concepts |  | **MISSING_IN_REPORT** |
| B8.Nc.n_min_20.projected | Projected N_c at n_min_20 | 117.6 |  |  | concepts |  | **MISSING_IN_REPORT** |
| B8.Nc.n_min_30.realised | Realised N_c at n_min_30 | 38 |  |  | concepts |  | **MISSING_IN_REPORT** |
| B8.Nc.n_min_30.projected | Projected N_c at n_min_30 | 77.5 | [66, 92] |  | concepts |  | **MISSING_IN_REPORT** |

Source: round-2/experiment-2/src/results/power/decisions.json; round-2/experiment-2/src/results/power/h1_mde.json

## B8 Gate B

| id | claim | value | 95% CI | n | unit | report (line) | flag |
|---|---|---|---|---|---|---|---|
| B8.gateB.mde_pct.10 | Gate B hypothetical design MDE% at 10 clusters | 56.38 |  |  | % change |  | **MISSING_IN_REPORT** |
| B8.gateB.mde_pct.30 | Gate B hypothetical design MDE% at 30 clusters | 32.47 |  |  | % change |  | **MISSING_IN_REPORT** |
| B8.gateB.mde_pct.60 | Gate B hypothetical design MDE% at 60 clusters | 26.67 |  |  | % change |  | **MISSING_IN_REPORT** |
| B8.gateB.mde_pct.120 | Gate B hypothetical design MDE% at 120 clusters | 18.48 |  |  | % change |  | **MISSING_IN_REPORT** |
| B8.gateB.episodes | Gate B labelled episodes (theta 0.7) | 0 |  |  | episodes |  | **MISSING_IN_REPORT** |

Source: round-2/experiment-2/src/results/power/gate_b.json

## B9 Gate A

| id | claim | value | 95% CI | n | unit | report (line) | flag |
|---|---|---|---|---|---|---|---|
| B9.gateA.within_host.share_ge_040 | Gate A within-host non-canonical traced share: share_ge_040 | 0.1727 |  | 724 | share | 17.3 (L308) | **OK** |
| B9.gateA.within_host.mean | Gate A within-host non-canonical traced share: mean | 0.2042 |  | 724 | share | 0.2 (L309) | **OK** |
| B9.gateA.within_host.median | Gate A within-host non-canonical traced share: median | 0.1538 |  | 724 | share | 0.15 (L310) | **OK** |
| B9.gateA.within_host.concept_weighted_mean | Gate A within-host non-canonical traced share: concept_weighted_mean | 0.2084 |  | 724 | share |  | **MISSING_IN_REPORT** |
| B9.gateA.within_host.concept_weighted_share_ge_040 | Gate A within-host non-canonical traced share: concept_weighted_share_ge_040 | 0.2022 |  | 724 | share |  | **MISSING_IN_REPORT** |
| B9.gateA.lenient.mean | Lenient ANY-parent traced share on the SAME 724 edges (mean) | 0.4771 |  | 724 | share |  | **MISSING_IN_REPORT** |
| B9.gateA.lenient.share_ge_040 | Lenient any-parent share >= 0.40 on the same edges | 0.6423 |  | 724 | share |  | **WRONG_DEFINITION** |
| B9.gateA.secondary.share_ge_040 | Within-host share >= 0.40, secondary denominator (children with refs) | 0.2448 |  | 723 | share |  | **MISSING_IN_REPORT** |
| B9.gateA.loader_check | Iteration-1 lenient loader check reproduced (main host share) | 0.5518 |  | 41861 | share | 55.18 (L313) | **OK** |
| B9.gateA.year.2008 | Gate A within-host share >= 0.40, focal year 2008 | 0 |  | 1 | share |  | **MISSING_IN_REPORT** |
| B9.gateA.year.2009 | Gate A within-host share >= 0.40, focal year 2009 | 0.1667 |  | 6 | share |  | **MISSING_IN_REPORT** |
| B9.gateA.year.2010 | Gate A within-host share >= 0.40, focal year 2010 | 0.0769 |  | 13 | share |  | **MISSING_IN_REPORT** |
| B9.gateA.year.2011 | Gate A within-host share >= 0.40, focal year 2011 | 0.1818 |  | 22 | share |  | **MISSING_IN_REPORT** |
| B9.gateA.year.2012 | Gate A within-host share >= 0.40, focal year 2012 | 0.1458 |  | 48 | share |  | **MISSING_IN_REPORT** |
| B9.gateA.year.2013 | Gate A within-host share >= 0.40, focal year 2013 | 0.1408 |  | 71 | share |  | **MISSING_IN_REPORT** |
| B9.gateA.year.2014 | Gate A within-host share >= 0.40, focal year 2014 | 0.191 |  | 89 | share |  | **MISSING_IN_REPORT** |
| B9.gateA.year.2015 | Gate A within-host share >= 0.40, focal year 2015 | 0.1875 |  | 96 | share |  | **MISSING_IN_REPORT** |
| B9.gateA.year.2016 | Gate A within-host share >= 0.40, focal year 2016 | 0.2235 |  | 85 | share |  | **MISSING_IN_REPORT** |
| B9.gateA.year.2017 | Gate A within-host share >= 0.40, focal year 2017 | 0.1724 |  | 87 | share |  | **MISSING_IN_REPORT** |
| B9.gateA.year.2018 | Gate A within-host share >= 0.40, focal year 2018 | 0.1633 |  | 98 | share |  | **MISSING_IN_REPORT** |
| B9.gateA.year.2019 | Gate A within-host share >= 0.40, focal year 2019 | 0.1574 |  | 108 | share |  | **MISSING_IN_REPORT** |
| B9.gateA.screen.2010 | Screen-fold mean within-host share, 2010 | 0.1959 |  | 10 | share |  | **MISSING_IN_REPORT** |
| B9.gateA.screen.2011 | Screen-fold mean within-host share, 2011 | 0.2767 |  | 15 | share |  | **MISSING_IN_REPORT** |
| B9.gateA.screen.2012 | Screen-fold mean within-host share, 2012 | 0.2263 |  | 33 | share |  | **MISSING_IN_REPORT** |
| B9.gateA.screen.2013 | Screen-fold mean within-host share, 2013 | 0.1902 |  | 48 | share |  | **MISSING_IN_REPORT** |
| B9.gateA.screen.2014 | Screen-fold mean within-host share, 2014 | 0.2001 |  | 54 | share |  | **MISSING_IN_REPORT** |
| B9.gateA.reference_mean | Reference-arm within-host share (edge-weighted mean over years) | 0.127 |  | 1766 | share | 0.13 (L311) | **OK** |
| B9.graft.all | Graft-fallback host-entry events (all) | 2347 |  |  | events |  | **MISSING_IN_REPORT** |
| B9.graft.kw5 | Graft-fallback host-entry events (kw5) | 2154 |  |  | events |  | **MISSING_IN_REPORT** |
| B9.graft.kw5_screen | Graft-fallback host-entry events (kw5_screen) | 1285 |  |  | events |  | **MISSING_IN_REPORT** |
| B9.graft.kw5_heldout | Graft-fallback host-entry events (kw5_heldout) | 869 |  |  | events |  | **MISSING_IN_REPORT** |

Source: round-2/experiment-2/src/results/gate_a/gate_A_verdict.json; round-2/experiment-2/src/results/gate_a/gate_a_by_arm_fold_year.csv; round-2/experiment-2/src/results/gate_a/graft_fallback_events.csv; round-2/experiment-2/src/results/gate_a/lenient_loader_check.json

## B10 exp_2

| id | claim | value | 95% CI | n | unit | report (line) | flag |
|---|---|---|---|---|---|---|---|
| B10.p1.SOURCE | P1 pooled entropy share of SOURCE | 0.0144 |  | 919 | share of H |  | **MISSING_IN_REPORT** |
| B10.p1.SINK | P1 pooled entropy share of SINK | 0.004 |  | 919 | share of H |  | **MISSING_IN_REPORT** |
| B10.p1.FADING | P1 pooled entropy share of FADING | 0.0018 |  | 919 | share of H |  | **MISSING_IN_REPORT** |
| B10.p1.UNDETERMINED | P1 pooled entropy share of UNDETERMINED | 0.7043 |  | 919 | share of H |  | **MISSING_IN_REPORT** |
| B10.p1.ORIGIN | P1 pooled entropy share of ORIGIN | 0.2755 |  | 919 | share of H |  | **MISSING_IN_REPORT** |
| B10.origin.onsets.0.6 | Origin cooling onsets at theta 0.6 | 33 |  | 184 | concepts |  | **MISSING_IN_REPORT** |
| B10.origin.onsets.0.7 | Origin cooling onsets at theta 0.7 | 51 |  | 184 | concepts |  | **MISSING_IN_REPORT** |
| B10.origin.onsets.0.8 | Origin cooling onsets at theta 0.8 | 83 |  | 184 | concepts |  | **MISSING_IN_REPORT** |
| B10.synth.fdr_overall | Synthetic validation realised FDR at n_min 30 (correct calibration) | 0.2088 |  | 20000 | FDR | 0.209 (L342) | **OK** |
| B10.synth.fdr.SOURCE | Synthetic FDR for SOURCE | 0.1296 |  | 2138 | FDR | 0.13 (L340) | **OK** |
| B10.synth.fdr.SINK | Synthetic FDR for SINK | 0.3955 |  | 708 | FDR | 0.4 (L341) | **OK** |
| B10.synth.fdr.FADING | Synthetic FDR for FADING | 0.281 |  | 516 | FDR |  | **MISSING_IN_REPORT** |
| B10.synth.rho_tilde_coverage | rho~ 90% CI coverage on tested synthetic edges | 0.7744 |  |  | share |  | **MISSING_IN_REPORT** |

Source: round-2/experiment-2/src/results/origin/cooling_onsets.csv; round-2/experiment-2/src/results/p1/p1_summary.json; round-2/experiment-2/src/results/synth/synth_results.json

## B12 hashes

| id | claim | value | 95% CI | n | unit | report (line) | flag |
|---|---|---|---|---|---|---|---|
| B12.exp3.spec_inner | exp_3 spec.json inner sha256 recomputed as sha256(json.dumps(SPEC, sort_keys=True)) |  |  |  | sha256 |  | **OK** |
| B12.dataset_5.sample_frame_frozen.json | sha256 of dataset_5 hyd/sample_frame_frozen.json |  |  |  | sha256 |  | **OK** |
| B12.exp_2.prereg_freeze.json | sha256 of exp_2 prereg/prereg_freeze.json |  |  |  | sha256 |  | **OK** |
| B12.exp_1.test_population.json | sha256 of exp_1 results/test_population.json |  |  |  | sha256 |  | **OK** |
| B12.exp_3.spec.json | sha256 of exp_3 spec.json (file) |  |  |  | sha256 |  | **OK** |
| B12.exp4prereg.features_sha256 | sha256 of round-2/experiment-4/src/results/features.parquet vs exp_4 prereg_spec.json features_sha256 |  |  |  | sha256 |  | **OK** |
| B12.exp4prereg.spec_sha256 | sha256 of round-2/experiment-4/src/rq1_spec.py vs exp_4 prereg_spec.json spec_sha256 (rq1_spec.py) |  |  |  | sha256 |  | **OK** |
| B12.exp4prereg.main_pool_alignment.sha256.spec.json | sha256 of round-2/experiment-3/src/spec.json vs exp_4 prereg_spec.json main_pool_alignment.sha256.spec.json |  |  |  | sha256 |  | **OK** |
| B12.exp4prereg.main_pool_alignment.sha256.lib_metrics.py | sha256 of round-2/experiment-3/src/lib_metrics.py vs exp_4 prereg_spec.json main_pool_alignment.sha256.lib_metrics.py |  |  |  | sha256 |  | **OK** |
| B12.exp4prereg.main_pool_alignment.sha256.stage_snapshots.py | sha256 of round-2/experiment-3/src/stage_snapshots.py vs exp_4 prereg_spec.json main_pool_alignment.sha256.stage_snapshots.py |  |  |  | sha256 |  | **DRIFT_VALUE** |
| B12.exp4prereg.main_pool_alignment.sha256.stage_indicators.py | sha256 of round-2/experiment-3/src/stage_indicators.py vs exp_4 prereg_spec.json main_pool_alignment.sha256.stage_indicators.py |  |  |  | sha256 |  | **OK** |
| B12.exp4prereg.main_pool_alignment.sha256.analysis_event.py | sha256 of round-2/experiment-3/src/analysis_event.py vs exp_4 prereg_spec.json main_pool_alignment.sha256.analysis_event.py |  |  |  | sha256 |  | **DRIFT_VALUE** |
| B12.exp4prereg.main_pool_alignment.sha256.results_summary.json | sha256 of round-2/experiment-3/src/results_summary.json vs exp_4 prereg_spec.json main_pool_alignment.sha256.results_summary.json |  |  |  | sha256 |  | **DRIFT_VALUE** |

Source: round-2/dataset-5/src/hyd/sample_frame_frozen.json; round-2/experiment-1/src/results/test_population.json; round-2/experiment-2/src/prereg/prereg_freeze.json; round-2/experiment-3/src/spec.json; round-2/experiment-4/src/results/prereg_spec.json

## B13 run ledger

| id | claim | value | 95% CI | n | unit | report (line) | flag |
|---|---|---|---|---|---|---|---|
| B13.exp_1 | Run ledger for exp_1 (art_BdBvbNuNU8E7) |  |  |  |  |  | **MISSING_IN_REPORT** |
| B13.exp_2 | Run ledger for exp_2 (art_yjFB8Spw2w6M) |  |  |  |  |  | **MISSING_IN_REPORT** |
| B13.exp_3 | Run ledger for exp_3 (art_mbFjmo5rbbf8) |  |  |  |  |  | **MISSING_IN_REPORT** |
| B13.exp_4 | Run ledger for exp_4 (art_yWUkgWWKyq_h) |  |  |  |  |  | **MISSING_IN_REPORT** |
| B13.dataset_5 | Run ledger for dataset_5 (art_eR1Z7fMlOcxs) |  |  |  |  |  | **MISSING_IN_REPORT** |

Source: round-2/dataset-5/src/README.md; round-2/experiment-1/src/README.md; round-2/experiment-2/src/README.md; round-2/experiment-3/src/README.md; round-2/experiment-4/src/README.md

## Drift flags (not OK / not MISSING)

- **DRIFT_VALUE** `B1.clf.tF1.precision` (report L267): Classifier precision at t=0.5073. Record value 0.759; report 0.812. Table 9 P/R/accuracy (0.812/0.824/0.843) are not reproduced at t_F1, t=0.5 or t_P90; the nearest known number is the E2 human-anchor precision mean 0.813 (a different test set).
- **DRIFT_VALUE** `B1.clf.tF1.recall` (report L268): Classifier recall at t=0.5073. Record value 0.8862; report 0.824. 
- **DRIFT_VALUE** `B1.clf.tF1.accuracy` (report L269): Classifier accuracy at t=0.5073. Record value 0.78; report 0.843. 
- **WRONG_DEFINITION** `B1.base.all_positive_f1` (report L259): Majority-class (predict-all-CONCEPT) baseline F1; CONCEPT is the majority class. Record value 0.7152; report 0.0. predict-all-positive P=0.557, R=1, F1=0.715; the report's 0.000 is predict-all-NEGATIVE, which is not the majority class on a 167/300 positive test set.
- **NOT_REDERIVABLE** `B1.base.unigram_f1_report` (report L259): 'Unigram-frequency baseline F1 0.689' quoted in the report. Record value ; report 0.689. No baseline with F1 0.689 exists in exp_1 classifier_results.json (baselines: majority 0.715, C-value 0.716, lexical-only 0.762).
- **WRONG_ESTIMATOR** `B1.anchor.E1.clf_kappa` (report L271): Classifier binary kappa vs human anchors (E1, SemEval/SciERC). Record value 0.4133; report 0.56. 0.56 is LLM-A's anchor kappa (iteration-1 DS4 number, reproduced on the same rows), not the classifier's. Report value 0.56 equals the WRONG_ESTIMATOR alternative (0.56).
- **WRONG_ESTIMATOR** `B2.E_alt.closure.p_holm` (report L410): E_alt event-study Holm p for closure (family of 3 primaries). Record value 0.504; report 0.096. pooled-panel Holm p = 0.096; unadjusted event-study p = 0.168 Report value 0.096 equals the WRONG_ESTIMATOR alternative (0.096).
- **WRONG_ESTIMATOR** `B2.E_up.accretion_shift_rar.p_holm` (report L407): E_up event-study Holm p for accretion_shift_rar (family of 3 primaries). Record value 0.18; report 0.272. pooled-panel Holm p = 0.272; unadjusted event-study p = 0.09 Report value 0.272 equals the WRONG_ESTIMATOR alternative (0.272).
- **WRONG_ESTIMATOR** `B2.E_up.P_rar.p_holm` (report L408): E_up event-study Holm p for P_rar (family of 3 primaries). Record value 0.824; report 0.782. pooled-panel Holm p = 0.782; unadjusted event-study p = 0.824 Report value 0.782 equals the WRONG_ESTIMATOR alternative (0.782).
- **WRONG_ESTIMATOR** `B2.E_up.closure.S_label` (report L396): The E_up closure S = -0.837 is the matched EVENT-STUDY mean difference, not the pooled-panel coefficient (-0.743). Record value -0.837; report -0.837. pooled panel coef = -0.743 [-1.06, -0.46], Holm 0.003, n = 514 rows / 90 concepts; Table 17 header 'S (pooled)' is also mislabelled
- **WRONG_ESTIMATOR** `B3.E.logit.baseline_auc` (report L426): E: BASELINE AUC (logit). Record value 0.9528; report 0.887. n_test_rows=55, n_test_pos=2, n_concepts=55, origins=[2019]; file pooled AUC 0.9245 Report value 0.887 equals the WRONG_ESTIMATOR alternative (0.8868).
- **WRONG_ESTIMATOR** `B3.E.logit.delta_auc` (report L426): E: FULL minus BASELINE AUC (logit). Record value -0.0283; report 0.038. n_test_rows=55, n_test_pos=2, n_concepts=55, origins=[2019]; file pooled AUC 0.9245; file delta -0.0283 CI [-0.094, 0.019] Report value +0.038 equals the WRONG_ESTIMATOR alternative (0.03774).
- **WRONG_ESTIMATOR** `B3.E_alt.logit.baseline_auc` (report L427): E_alt: BASELINE AUC (logit). Record value 0.9359; report 0.686. n_test_rows=55, n_test_pos=3, n_concepts=55, origins=[2019]; file pooled AUC 0.9872 Report value 0.686 equals the WRONG_ESTIMATOR alternative (0.6859).
- **WRONG_ESTIMATOR** `B3.E_alt.logit.full_auc` (report L427): E_alt: FULL AUC (logit). Record value 0.9872; report 0.628. n_test_rows=55, n_test_pos=3, n_concepts=55, origins=[2019]; file pooled AUC 0.9872 Report value 0.628 equals the WRONG_ESTIMATOR alternative (0.6282).
- **WRONG_ESTIMATOR** `B3.E_alt.logit.delta_auc` (report L427): E_alt: FULL minus BASELINE AUC (logit). Record value 0.05128; report -0.058. n_test_rows=55, n_test_pos=3, n_concepts=55, origins=[2019]; file pooled AUC 0.9872; file delta 0.0513 CI [0.0, 0.132] Report value -0.058 equals the WRONG_ESTIMATOR alternative (-0.05769).
- **WRONG_ESTIMATOR** `B3.E_up.logit.baseline_auc` (report L416): E_up: BASELINE AUC (logit). Record value 0.8898; report 0.859. n_test_rows=131, n_test_pos=42, n_concepts=109, origins=[2015, 2019]; file pooled AUC 0.8793 Report value 0.859 equals the WRONG_ESTIMATOR alternative (0.8593).
- **WRONG_ESTIMATOR** `B3.E_up.logit.full_auc` (report L416): E_up: FULL AUC (logit). Record value 0.8793; report 0.878. n_test_rows=131, n_test_pos=42, n_concepts=109, origins=[2015, 2019]; file pooled AUC 0.8793 Report value 0.878 equals the WRONG_ESTIMATOR alternative (0.8781).
- **WRONG_ESTIMATOR** `B3.E_up.logit.delta_auc` (report L416): E_up: FULL minus BASELINE AUC (logit). Record value -0.01043; report 0.019. n_test_rows=131, n_test_pos=42, n_concepts=109, origins=[2015, 2019]; file pooled AUC 0.8793; file delta -0.0104 CI [-0.045, 0.021] Report value +0.019 equals the WRONG_ESTIMATOR alternative (0.01886).
- **WRONG_ESTIMATOR** `B4.main.shuffle.E_alt_h5` (report L416): Main-pool label-shuffle null, mean delta-AUC (E_alt_h5). Record value -0.01861; report -0.015. sd=0.082; NO shuffle test exists for E_up in exp_3 — the report attaches this null to E_up Report value -0.015 equals the WRONG_ESTIMATOR alternative (-0.01487).
- **WRONG_DEFINITION** `B5.mesh.SENS1.dP.D` (report L474): MeSH SENS1: D (dP), mean diff over rel -3..-1. Record value 0.01026; report 0.051. n_emerging=29, n_eff=29, Holm p=1.0, MDE=0.34 SD The report's SENS1 dP numbers (D 0.051 [0.014, 0.087], Holm 0.015) are the E_cent-only dP row. Report value 0.051 equals the WRONG_DEFINITION alternative (0.0507).
- **WRONG_DEFINITION** `B5.mesh.SENS1.dP.p_holm` (report L474): MeSH SENS1: Holm p (dP). Record value 1; report 0.015. The report's SENS1 dP numbers (D 0.051 [0.014, 0.087], Holm 0.015) are the E_cent-only dP row. Report value 0.015 equals the WRONG_DEFINITION alternative (0.015).
- **WRONG_DEFINITION** `B5.match.PRIMARY|all.rate3_20` (report L457): MeSH PRIMARY|all: share of treated with 3 controls at +-20%. Record value 0.3889; report 72.2. 
- **WRONG_DEFINITION** `B5.match.PRIMARY|all.rate3_30` (report L457): MeSH PRIMARY|all: share of treated with 3 controls at <= +-30%. Record value 0.7222; report 83.3. Report value 83.3 equals the WRONG_DEFINITION alternative (0.8333).
- **WRONG_DEFINITION** `B6.share_tested_sum` (report L328): Sum of the SOURCE/SINK/FADING 'share of tested' column (Table 13 labels the tested total 100%). Record value 0.568; report 100.0. the remaining 43.2% of tested edges are tested-but-UNDETERMINED and are missing from the column
- **WRONG_DEFINITION** `B7.nativeness.weight_share` (report L240): Share of host (non-origin) co-occurrence WEIGHT covered by the 1,372 profiled nodes. Record value 0.7872; report 78.7. overall row in file: {"concept_id": "__OVERALL__", "origin_subfield": null} -> {"concept_id": "__OVERALL__", "n_concepts": 426, "host_weight": 2388779, "covered_weight_share": 0.7872, "n_nodes_complete_4_blocks": 1372, "n_profiles": 5488, ; the report defines it as a share of concept-subfield EDGES with 4 non-missing blocks
- **WRONG_UNITS** `B7.asjc.link_share` (report L252): Share of concept-work LINKS in ASJC-covered venues. Record value 0.1158; report 12.1. venue-level share is 0.128; the 12.1% in the dataset_5 README is a share of LINKS, the report calls it venue coverage
- **WRONG_UNITS** `B8.h1_mde.auc|nmin5|AUC0.7|realised` (report L352): H1 MDE (auc) at n_min 5, target AUC0.7, design realised. Record value 0.06961; report 1.22. report Table 15 labels these 'Cohen's d' and prints values that are not in h1_mde.json; realised concepts 93, beta 0.8106951584329697
- **WRONG_UNITS** `B8.h1_mde.auc|nmin10|AUC0.7|realised` (report L353): H1 MDE (auc) at n_min 10, target AUC0.7, design realised. Record value 0.07321; report 0.89. report Table 15 labels these 'Cohen's d' and prints values that are not in h1_mde.json; realised concepts 91, beta 0.8015702482488847
- **WRONG_UNITS** `B8.h1_mde.auc|nmin10|AUC0.8|projected` (report L356): H1 MDE (auc) at n_min 10, target AUC0.8, design projected. Record value 0.03707; report 0.72. report Table 15 labels these 'Cohen's d' and prints values that are not in h1_mde.json; realised concepts 91, beta 1.417886400072977
- **WRONG_UNITS** `B8.h1_mde.auc|nmin20|AUC0.7|realised` (report L354): H1 MDE (auc) at n_min 20, target AUC0.7, design realised. Record value 0.09986; report 0.64. report Table 15 labels these 'Cohen's d' and prints values that are not in h1_mde.json; realised concepts 58, beta 0.7720452161450434
- **WRONG_UNITS** `B8.h1_mde.auc|nmin20|AUC0.8|projected` (report L357): H1 MDE (auc) at n_min 20, target AUC0.8, design projected. Record value 0.04259; report 0.51. report Table 15 labels these 'Cohen's d' and prints values that are not in h1_mde.json; realised concepts 58, beta 1.3511652290509146
- **WRONG_UNITS** `B8.h1_mde.auc|nmin20|AUC0.8|N150` (report L359): H1 MDE (auc) at n_min 20, target AUC0.8, design N150. Record value 0.039; report 0.44. report Table 15 labels these 'Cohen's d' and prints values that are not in h1_mde.json; realised concepts 58, beta 1.3511652290509146
- **WRONG_UNITS** `B8.h1_mde.auc|nmin30|AUC0.7|realised` (report L355): H1 MDE (auc) at n_min 30, target AUC0.7, design realised. Record value 0.1343; report 0.53. report Table 15 labels these 'Cohen's d' and prints values that are not in h1_mde.json; realised concepts 38, beta 0.7666704853852115
- **WRONG_UNITS** `B8.h1_mde.auc|nmin30|AUC0.8|projected` (report L358): H1 MDE (auc) at n_min 30, target AUC0.8, design projected. Record value 0.06887; report 0.42. report Table 15 labels these 'Cohen's d' and prints values that are not in h1_mde.json; realised concepts 38, beta 1.3326875096204214
- **WRONG_UNITS** `B8.h1_mde.auc|nmin30|AUC0.8|N150` (report L360): H1 MDE (auc) at n_min 30, target AUC0.8, design N150. Record value 0.03905; report 0.36. report Table 15 labels these 'Cohen's d' and prints values that are not in h1_mde.json; realised concepts 38, beta 1.3326875096204214
- **WRONG_DEFINITION** `B9.gateA.lenient.share_ge_040` (report L313): Lenient any-parent share >= 0.40 on the same edges. Record value 0.6423; report . The drop 0.55 -> 0.17 is definitional (lenient any-parent tracing vs within-host non-canonical tracing on the SAME edges: lenient mean 0.4771, share>=0.40 0.6423), not subfield pooling.
- **DRIFT_VALUE** `B11.main.nodes_median` (report L374): Main-pool snapshot nodes (median over 25 yearly snapshots). Record value 2.723e+04; report 1487.0. nodes range 13813-28449, kept edges median 83875, kept nodes median 12733; no column equals 1,487 (persistent-node count not computed in exp_3)
- **WRONG_DEFINITION** `B11.pattern.early_bridging_definition` (report L432): Early-bridging DEFINITION: P > 0.6 (raw) or top-decile cross-community betweenness in the first 2 years (SPEC early_bridging P_raw=0.6, btw_pct=90). Record value 0.6; report 75.0. 
- **DRIFT_VALUE** `B12.exp4prereg.main_pool_alignment.sha256.stage_snapshots.py` (report L): sha256 of round-2/experiment-3/src/stage_snapshots.py vs exp_4 prereg_spec.json main_pool_alignment.sha256.stage_snapshots.py. Record value ; report . computed b85bdf89c8be77f164cb9e886724c7933c6079b06eaa6e3f6b39ea4e087a1bb7; recorded 95206463b3dbc4bf1f4d761a16b101406a90eb49b289e1b62cb5c3f47f236a0c; match=False; the exp_3 file was modified AFTER exp_4 recorded its hash for the aligned block (the aligned block used the earlier version)
- **DRIFT_VALUE** `B12.exp4prereg.main_pool_alignment.sha256.analysis_event.py` (report L): sha256 of round-2/experiment-3/src/analysis_event.py vs exp_4 prereg_spec.json main_pool_alignment.sha256.analysis_event.py. Record value ; report . computed 2a48e6c0747c53a1644782418db8f1d72508ccd1ed62c8db70db6a82d81a15a5; recorded 8a51cbc1a2b538b417a308da832e5c26809442dc4a8edf52afdbee775fd92f01; match=False; the exp_3 file was modified AFTER exp_4 recorded its hash for the aligned block (the aligned block used the earlier version)
- **DRIFT_VALUE** `B12.exp4prereg.main_pool_alignment.sha256.results_summary.json` (report L): sha256 of round-2/experiment-3/src/results_summary.json vs exp_4 prereg_spec.json main_pool_alignment.sha256.results_summary.json. Record value ; report . computed 56187ee56e5c6f81ea0fa74e0cdbc440a470a887f26a1428411de5746708ba50; recorded 595eb670722502703e65e4a34d08a329184af065d8d2f4b2e92699d50563b44f; match=False; the exp_3 file was modified AFTER exp_4 recorded its hash for the aligned block (the aligned block used the earlier version)
- **DRIFT_VALUE** `B2.gate.mesh` (report L): R1a reproduction gate (mesh): E_up closure S re-run with the original estimator. Record value -0.1846; report . FAIL on CI tolerance only (S exact; recorded CI inside the 30-seed Monte-Carlo range of CI endpoints) -> continue with reproduced S_raw per plan; recorded S -0.18463 CI [-0.4979, 0.1082]