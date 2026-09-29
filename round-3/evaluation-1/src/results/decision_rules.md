# Decision rules (a)-(d)

Rule text: **verbatim**, from `3_invention_loop/iter_2/gen_strat/gen_strat_1/.terminal_claude_agent_struct_out.json`:

> DECISION RULES FOR ITERATION 3, fixed now. (a) If Gate A FAILS, H1/H2 run with graft labels computed from the new exact profiles (anchored if the lower CI of A exceeds the entry anchoring of stationary reference concepts), and the claim is restated as the grafting alternate. If it PASSES, H1/H2 run with Estimator A, and graft labels are a robustness row. (b) H1 runs on the grounded test population, screen fold, with the full baseline including Maillart and Rafols features, and is declared a pilot if fewer than ~150 concepts carry a tested edge. H2 is primary only if the Gate B MDE is <= 25%. (c) RQ1 counts as CONFIRMED for the paper only if at least one pre-named per-paper precursor has an event-study CI excluding 0 AND a rolling-origin delta-AUC CI excluding 0 on the main screen fold, keeps its sign on MeSH, and then holds on the sealed held-out sha1 fold and the 2016-18 focal years in iteration 3. If only raw indicators carry signal, the reportable result is that structural emergence indicators are volume in disguise. (d) The held-out sha1 fold, the 2016-18 out-of-time focal years and the phrase pool remain untouched this iteration.

| rule | condition | key values | verdict |
|---|---|---|---|
| (a) | Gate A share >= 0.40 must exceed 0.5 | share 0.1727; graft events {'total': 2347, 'kw5': 2154, 'kw5_screen': 1285, 'kw5_heldout': 869, 'kw5_e_ge_F': 2000} | **TRIGGERED: graft fallback supplies H1/H2 labels; claim restated as the grafting alternate** |
| (b) | N_c >= ~150 for H1; Gate B MDE <= 25% for H2 | N_c 38 (projected 77.5 [66.0, 92.0]); MDE dAUC 0.134/0.116; Gate B episodes 0 | **H1 PILOT-ONLY (N_c 38 < 150; MDE delta-AUC 0.134 / 0.116); H2 NOT primary (Gate B: 0 labelled episodes, MDE not estimable)** |
| (c) | c1 ES CI excl. 0 AND c2 rolling dAUC CI excl. 0 AND c3 MeSH same sign AND c4 held-out | see per-precursor table | **NOT MET: no pre-named precursor satisfies c1 AND c2 AND c3 AND c4 on the primary label; c2 fails for every label (logit delta-AUC CI covers 0), c1b fails (all significant effects are NEGATIVE, opposite to the pre-registered +), and c4 is not yet run** |
| (d) | held-out untouched | 0 hits in 161 exp_3/exp_4 files; 2016-18 label rows 0; 61 iter-1 ids subset of 119: True | **SEALED for exp_3/exp_4 label/W2 files (analysis-level); CAVEAT exp_2: exp_2 computed origin-subfield series through 2024 and cooling onsets for 61 held-out concepts (outcome-adjacent, post-t years); they are not RQ1 labels and are not read by exp_3/exp_4, but the held-out fold is no longer 'untouched' at the level of exp_2 descriptive outputs** |

## Rule (c), per condition

| label | precursor | n | S [95% CI] | c1 | c1b (+) | c2 (dAUC logit [CI]) | c3 MeSH sign (S_mesh) | c4 | met |
|---|---|---|---|---|---|---|---|---|---|
| E (PRIMARY (pre-registered)) | accretion_shift_rar | 3 | -0.104 [-0.120, -0.016] | PASS | FAIL | FAIL (-0.028 [-0.094, 0.019]) | FAIL (0.044) | NOT RUN | False |
| E (PRIMARY (pre-registered)) | closure | 3 | -0.625 [-0.656, -0.588] | PASS | FAIL | FAIL (-0.028 [-0.094, 0.019]) | FAIL (0.487) | NOT RUN | False |
| E (PRIMARY (pre-registered)) | P_rar | 3 | 0.143 [-0.119, 0.301] | FAIL | PASS | FAIL (-0.028 [-0.094, 0.019]) | FAIL (-0.026) | NOT RUN | False |
| E_up (post hoc (promoted)) | accretion_shift_rar | 21 | -0.140 [-0.185, 0.018] | FAIL | FAIL | FAIL (-0.010 [-0.045, 0.021]) | FAIL (0.043) | NOT RUN | False |
| E_up (post hoc (promoted)) | closure | 21 | -0.837 [-1.260, -0.427] | PASS | FAIL | FAIL (-0.010 [-0.045, 0.021]) | PASS (-0.185) | NOT RUN | False |
| E_up (post hoc (promoted)) | P_rar | 21 | -0.007 [-0.066, 0.056] | FAIL | FAIL | FAIL (-0.010 [-0.045, 0.021]) | FAIL (0.017) | NOT RUN | False |

E rows: n = 3 matched treated, bootstrap CIs are not interpretable. MeSH plan-native PRIMARY: accretion_share D=0.094 [-0.036, 0.210] Holm 0.480; closure_lr D=-0.086 [-0.511, 0.402] Holm 0.677; dP D=0.025 [-0.017, 0.073] Holm 0.506

Seal limitation: Analysis-level seal only: it shows no held-out id was ANALYSED (appears) in exp_3/exp_4 outputs. It cannot show that nobody looked at held-out raw data: dataset_5 holds full 2000-2024 works for all 426 concepts including the 119 held-out.

Source: 3_invention_loop/iter_2/gen_strat/gen_strat_1 (rule text); exp_2 results/gate_a, results/power; exp_3 results/event_study, results/prediction; exp_4 results/rq1_effects*.csv; results/heldout_audit.json