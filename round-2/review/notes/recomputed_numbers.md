# Numbers recomputed or looked up by the reviewer (iteration 2)

All paths are relative to `3_invention_loop/iter_2/gen_art/`.

| Report claim | Artifact value | Source | Verdict |
|---|---|---|---|
| Classifier F1 0.818, AUC 0.888 | F1 0.8177, AUC 0.8879 (recomputed from 300 test rows: TP148 FP47 FN19 TN86) | gen_art_experiment_1/results/d2_test_predictions.json | OK |
| Classifier P 0.812 / R 0.824 / acc 0.843 | P 0.759 / R 0.886 / acc 0.780 | same | MISMATCH |
| Majority-class F1 0.000 | 0.715 | same (recomputed) and README | MISMATCH |
| Unigram-frequency baseline F1 0.689 | no such baseline; C-value F1 0.716 | results/classifier_table.csv | UNTRACEABLE |
| Classifier human-anchor kappa 0.56 | classifier E1 kappa 0.41, F1 0.674 (0.56 is LLM A's value) | README human anchors | MISMATCH |
| Gate A 17.3% (mean 0.20, median 0.15) | 0.1727 of 724 edges, mean 0.2042, median 0.1538 | gen_art_experiment_2/results/gate_a/gate_A_verdict.json | OK |
| Discrepancy with 55% comes from pooling vs edge level | lenient any-parent share on the same 724 edges is 0.477 (64% >= 0.40), so the gap is definitional | same | CONTRADICTED |
| Verdict: viability is a dead end | "FAIL -> graft fallback supplies H1/H2 labels in iteration 3"; 2,347 host-entry events | gate_A_verdict.json, graft_fallback_summary.json | CONTRADICTED |
| Synthetic FDR 0.209; SOURCE 0.13, SINK 0.40 | FDR 0.2088 | results/synth/synth_results.json | OK |
| Table 15 MDE in Cohen's d (1.22, 0.89, ...) | MDEs are delta-AUC: n_min 30 realised 0.134 / 0.116; n_min 10 realised 0.073 / 0.054; n_min 5 projected 0.039 / 0.034 | results/power/h1_mde.json, decisions.json | NOT IN ANY OUTPUT |
| E_up closure S -0.837 [-1.26, -0.427], Holm 0.003 | identical | gen_art_experiment_3/results/event_study/summary_E_up.json | OK |
| E_up accretion Holm 0.272, participation Holm 0.782 | event-study Holm 0.18 / 0.824; 0.272 / 0.782 are pooled-panel Holm values | same (table vs pooled_panel) | MIXED ESTIMATORS |
| E_alt closure Holm 0.096 | event-study Holm 0.504; 0.096 is pooled-panel | summary_E_alt.json, results_summary verdicts | MIXED ESTIMATORS |
| Prediction E_up 0.859 -> 0.878 (+0.019) | HGB (secondary); primary L2-logit 0.890 -> 0.879, delta -0.010 [-0.045, 0.021] | results/prediction/summary.json | SECONDARY MODEL, UNLABELLED |
| E_alt delta -0.058; E +0.038 | HGB; primary logit E_alt +0.051 [0.000, 0.132], E -0.028 [-0.094, 0.019] | same | SECONDARY MODEL, UNLABELLED |
| Shuffle mean -0.015, SD 0.082 (E_up) | main-pool shuffle exists only for E (-0.021 +/- 0.127) and E_alt (-0.019 +/- 0.082); -0.015 is MeSH | same; gen_art_experiment_4/README | CONFLATED |
| MeSH closure PRIMARY/SENS1/SENS2 | -0.086 / -0.419 (Holm 0.039) / -0.858 | gen_art_experiment_4/results/replication_verdict.json | OK |
| MeSH dP SENS1 D 0.051, Holm 0.015 | SENS1 dP 0.010, Holm 1.0; 0.051 / 0.015 belongs to E_cent | results/rq1_effects.csv | MISATTRIBUTED |
| MeSH match 83.3% at 30% caliper (72.2% at 20%) | 72.2% at 30%, 38.9% at 20%, 83.3% any | results/analysis_summary.json match_info | MISMATCH |
| MeSH patterns similar to main pool | early bridging 0.59 vs 0.76; incubation->expansion 0.17 vs 0.00 | gen_art_experiment_4/README, rq1_patterns.csv | CONTRADICTED |
| Replicated closure (same indicators) | aligned E_up closure MeSH -0.185 [-0.50, 0.11], Holm 0.21, n = 51; E and E_alt signs disagree (+0.49, +0.08); IVW -0.41, Q 6.2 | replication_verdict.json mainpool_aligned | OVERCLAIM |
