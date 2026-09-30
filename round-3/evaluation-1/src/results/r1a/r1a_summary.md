# R1a turnover check (Part 2)

**PRE-CHECK ON ALREADY-SCREENED DATA; NOT CONFIRMATION; E_up promoted post hoc**

Spec sha256 `60f44c0fb645a5cc19b7ec60f6a4b8c61b596c1220d9da160d268d1aa0ca614a` (results/r1a/r1a_spec.json, written before any statistic).

## Reproduction gate

| population | S reproduced | S recorded | CI reproduced | CI recorded | max CI diff | pass |
|---|---|---|---|---|---|---|
| main | -0.83698 | -0.83698 | [-1.2600, -0.4268] | [-1.2600, -0.4268] | 0.0000 | PASS |
| mesh | -0.18463 | -0.18463 | [-0.4733, 0.1248] | [-0.4979, 0.1082] | 0.0246 | FAIL on CI tolerance only (S exact; recorded CI inside the 30-seed Monte-Carlo range of CI endpoints) -> continue with reproduced S_raw per plan |

Source: exp_3 results/event_study/summary_E_up.json; exp_4 results/rq1_effects_mainpool_aligned.csv

## Within-concept correlations (closure vs turnover)

| population | pair | r within [95% CI] | rho within | r pooled | n concepts | n rows |
|---|---|---|---|---|---|---|
| main | closure~new_rel (new_relation_rate) | -0.187 [-0.263, -0.120] | -0.181 | -0.187 | 123 | 1194 |
| main | closure~novelty (novelty) | -0.166 [-0.255, -0.087] | -0.174 | -0.202 | 123 | 1180 |
| main | closure~beta_sim (beta_sim_raw) | 0.032 [-0.031, 0.098] | -0.015 | -0.037 | 122 | 1130 |
| main | closure~beta_sim_rar (beta_sim_rar) | -0.046 [-0.127, 0.041] | -0.042 | -0.178 | 83 | 593 |
| main | closure~closure_raw (closure_raw) | 0.378 [0.194, 0.508] | 0.091 | 0.367 | 123 | 1194 |
| main | closure~log_vol3 (log_vol3) | 0.319 [0.229, 0.425] | 0.381 | 0.134 | 123 | 1194 |
| mesh | closure~new_rel (new_rel_rate) | -0.145 [-0.198, -0.093] | -0.083 | -0.101 | 191 | 2177 |
| mesh | closure~novelty (nbr_novelty) | -0.030 [-0.085, 0.027] | 0.057 | 0.006 | 191 | 2177 |
| mesh | closure~beta_sim (beta_sim_raw) | 0.025 [-0.023, 0.077] | 0.011 | -0.095 | 191 | 2103 |
| mesh | closure~beta_sim_rar (beta_sim_rar) | -0.049 [-0.125, 0.038] | -0.045 | -0.183 | 116 | 927 |
| mesh | closure~closure_raw (closure_raw) | 0.375 [0.263, 0.474] | 0.225 | 0.336 | 191 | 2184 |
| mesh | closure~log_vol3 (log_vol3) | 0.300 [0.230, 0.369] | 0.319 | 0.322 | 191 | 2184 |
| mesh | closure~beta_sim_native (beta_sim) | 0.075 [0.026, 0.123] | 0.097 | 0.047 | 191 | 2178 |

Source: exp_3 results/indicators/concept_year_indicators.parquet; exp_4 results/features.parquet (concept-cluster bootstrap B=2000)

## Event study, raw vs residualised closure (E_up) — PRE-CHECK ON ALREADY-SCREENED DATA; NOT CONFIRMATION; E_up promoted post hoc

| pop | spec | S_raw (full) | S_raw_cc | S_res [95% CI] | S_fit | retained [95% CI] | n treated raw/res | MDE_res (SD) | verdict rule |
|---|---|---|---|---|---|---|---|---|---|
| main | P | -0.837 | -0.758 | -0.566 [-1.140, 0.087] | -0.192 | 0.746 [0.080, 0.895] | 21/21 | 0.864 (0.702) | AMBIGUOUS / UNDERPOWERED |
| main | R | -0.837 | -1.037 | -1.086 [-1.451, -0.550] | 0.049 | 1.047 [0.740, 1.192] | 21/15 | 0.625 (0.478) | NOT REDUCIBLE TO TURNOVER (seen data) |
| main | V | -0.837 | -0.837 | -0.709 [-1.134, -0.293] | -0.128 | 0.847 [0.678, 0.927] | 21/21 | 0.616 (0.501) | NOT REDUCIBLE TO TURNOVER (seen data) |
| main | V0 | -0.837 | -0.837 | -0.729 [-1.156, -0.325] | -0.108 | 0.871 [0.740, 0.934] | 21/21 | 0.607 (0.492) | NOT REDUCIBLE TO TURNOVER (seen data) |
| main | D_new_rel | -0.837 | -0.837 | -0.674 [-1.109, -0.246] | -0.163 | 0.805 [0.565, 0.911] | 21/21 | 0.625 (0.503) | NOT REDUCIBLE TO TURNOVER (seen data) |
| main | D_novelty | -0.837 | -0.837 | -0.593 [-1.043, -0.154] | -0.244 | 0.708 [0.351, 0.872] | 21/21 | 0.642 (0.529) | AMBIGUOUS / UNDERPOWERED |
| main | D_beta_sim | -0.837 | -0.758 | -0.651 [-1.222, -0.004] | -0.107 | 0.859 [0.465, 0.957] | 21/21 | 0.865 (0.694) | AMBIGUOUS / UNDERPOWERED |
| main | POS | -0.837 | -0.837 | -0.368 [-0.971, 0.235] | -0.469 | 0.440 [-0.520, 0.852] | 21/21 | 0.864 (0.745) | AMBIGUOUS / UNDERPOWERED |
| main | POS_ORACLE | -0.837 | -0.837 | -0.013 [-0.047, 0.023] | -0.824 | 0.016 [-0.031, 0.062] | 21/21 | 0.049 (0.379) | LARGELY TURNOVER |
| main | NEG | -0.837 | -0.837 | -0.730 [-1.157, -0.326] | -0.107 | 0.872 [0.737, 0.937] | 21/21 | 0.608 (0.493) | NOT REDUCIBLE TO TURNOVER (seen data) |
| mesh | P | -0.185 | -0.156 | -0.094 [-0.387, 0.217] | -0.062 | 0.604 [-1.277, 2.852] | 51/51 | 0.425 (0.351) | AMBIGUOUS / UNDERPOWERED |
| mesh | R | -0.185 | -0.139 | -0.053 [-0.876, 0.743] | -0.087 | 0.378 [-1.763, 3.835] | 51/23 | 1.164 (0.893) | AMBIGUOUS / UNDERPOWERED |
| mesh | V | -0.185 | -0.185 | -0.095 [-0.377, 0.201] | -0.090 | 0.514 [-1.826, 3.292] | 51/51 | 0.408 (0.336) | AMBIGUOUS / UNDERPOWERED |
| mesh | V0 | -0.185 | -0.185 | -0.095 [-0.377, 0.201] | -0.090 | 0.514 [-1.826, 3.292] | 51/51 | 0.408 (0.336) | AMBIGUOUS / UNDERPOWERED |
| mesh | D_new_rel | -0.185 | -0.176 | -0.090 [-0.374, 0.211] | -0.086 | 0.512 [-1.982, 3.349] | 51/51 | 0.409 (0.337) | AMBIGUOUS / UNDERPOWERED |
| mesh | D_novelty | -0.185 | -0.176 | -0.097 [-0.378, 0.204] | -0.079 | 0.550 [-1.727, 3.240] | 51/51 | 0.410 (0.338) | AMBIGUOUS / UNDERPOWERED |
| mesh | D_beta_sim | -0.185 | -0.156 | -0.096 [-0.395, 0.218] | -0.060 | 0.616 [-1.167, 2.910] | 51/51 | 0.430 (0.355) | AMBIGUOUS / UNDERPOWERED |
| mesh | POS | -0.185 | -0.185 | -0.014 [-0.252, 0.248] | -0.171 | 0.076 [-3.665, 4.120] | 51/51 | 0.358 (0.364) | LARGELY TURNOVER |
| mesh | POS_ORACLE | -0.185 | -0.185 | -0.012 [-0.040, 0.016] | -0.173 | 0.065 [-0.358, 0.535] | 51/51 | 0.040 (0.282) | LARGELY TURNOVER |
| mesh | NEG | -0.185 | -0.185 | -0.092 [-0.373, 0.204] | -0.092 | 0.499 [-1.937, 3.273] | 51/51 | 0.408 (0.336) | AMBIGUOUS / UNDERPOWERED |
| mesh | H_mesh | -0.185 | -0.156 | -0.094 [-0.387, 0.216] | -0.061 | 0.605 [-1.210, 2.888] | 51/51 | 0.425 (0.351) | AMBIGUOUS / UNDERPOWERED |
| mesh | B_native | -0.185 | -0.176 | -0.086 [-0.372, 0.208] | -0.090 | 0.487 [-2.068, 3.390] | 51/51 | 0.408 (0.337) | AMBIGUOUS / UNDERPOWERED |

Source: this artifact, results/r1a/r1a_results.json (matched sets: exp_3 matches_E_up.csv; exp_4 analysis_summary.json mainpool_block.E_up.matches)

## IVW pooling across populations (k = 2; Q is underpowered)

| spec | S_ivw_res [95% CI] | se | Q (df=1) | p_Q | I^2 [Q-profile CI] | S_ivw_raw_cc |
|---|---|---|---|---|---|---|
| P | -0.186 [-0.453, 0.081] | 0.136 | 1.88 | 0.170 | 0.47 [0.000, 0.999] | -0.286 |
| R | -0.855 [-1.240, -0.470] | 0.197 | 4.80 | 0.028 | 0.79 [0.000, 1.000] | -0.921 |
| V | -0.282 [-0.520, -0.044] | 0.122 | 5.41 | 0.020 | 0.82 [0.071, 1.000] | -0.405 |
| V0 | -0.292 [-0.529, -0.055] | 0.121 | 5.90 | 0.015 | 0.83 [0.148, 1.000] | -0.405 |
| D_new_rel | -0.265 [-0.505, -0.025] | 0.122 | 4.79 | 0.029 | 0.79 [0.000, 1.000] | -0.400 |
| D_novelty | -0.240 [-0.482, 0.002] | 0.123 | 3.32 | 0.068 | 0.70 [0.000, 1.000] | -0.400 |
| D_beta_sim | -0.206 [-0.476, 0.064] | 0.138 | 2.58 | 0.108 | 0.61 [0.000, 1.000] | -0.286 |
| POS | -0.066 [-0.298, 0.166] | 0.118 | 1.12 | 0.289 | 0.11 [0.000, 0.999] | -0.405 |
| POS_ORACLE | -0.012 [-0.034, 0.009] | 0.011 | 0.00 | 0.962 | 0.00 [0.000, 0.569] | -0.405 |
| NEG | -0.290 [-0.527, -0.053] | 0.121 | 5.96 | 0.015 | 0.83 [0.157, 1.000] | -0.405 |

Raw closure IVW from recorded file values: -0.407 (SE 0.126), Q = 6.02; side-by-side file: -0.410 (SE 0.125), Q = 6.16.

## Verdicts (pre-declared rule, SPEC P)

- **main**: AMBIGUOUS / UNDERPOWERED  (S_res -0.566, retained 0.746 [0.080, 0.895])
- **mesh**: AMBIGUOUS / UNDERPOWERED  (S_res -0.094, retained 0.604 [-1.277, 2.852])
- **pooled**: AMBIGUOUS / UNDERPOWERED  (S_res -0.186, retained 0.651 [-0.627, 0.864])

## Controls

```
{
 "main": {
  "POS": {
   "retained": 0.43983290514190426,
   "retained_ci": [
    -0.5204407701641097,
    0.8522562695239423
   ],
   "r_within_closure_closure_raw": 0.37770467247396844
  },
  "POS_ORACLE": {
   "retained": 0.015573492208192756,
   "passed": true
  },
  "NEG": {
   "retained_vs_raw": 0.8723963381392363,
   "retained_vs_V0": 1.0011668212837792,
   "retained_vs_V0_ci": [
    0.9891417615624911,
    1.0134000560069332
   ],
   "passed": true
  },
  "PLACEBO": {
   "regenerated_S_raw": -0.028621120165581694,
   "recorded_S_raw": -0.028621120165581694,
   "regenerated_n": 38,
   "recorded_n": 38,
   "regeneration_exact": true,
   "S_res": 0.006433672019184806,
   "S_res_ci": [
    -0.3452726961390337,
    0.35393891711912556
   ],
   "passed": true
  }
 },
 "mesh": {
  "POS": {
   "retained": 0.0756250963243989,
   "retained_ci": [
    -3.6650580955289365,
    4.119953012887999
   ],
   "r_within_closure_closure_raw": 0.3746201994055988
  },
  "POS_ORACLE": {
   "retained": 0.06472925637200283,
   "passed": true
  },
  "NEG": {
   "retained_vs_raw": 0.4994525026827222,
   "retained_vs_V0": 0.9725619824166511,
   "retained_vs_V0_ci": [
    0.7732489738301972,
    1.1751777842129878
   ],
   "passed": true
  },
  "PLACEBO": {
   "skipped": true,
   "reason": "exp_4 did not save pseudo-onset matched sets for the main-pool-aligned block; its own placebo (plan-native) is transcribed in Part 1 B4"
  }
 }
}
```


Bad-control caveat: turnover may be part of the brokerage MECHANISM rather than a confounder; partialling it out then understates brokerage, so S_res is a conservative lower bound; S_fit = S_raw_cc - S_res and the single-covariate decompositions show which covariate carries the shared part.

Deviation D1: The plan lists MeSH 'beta_sim' as aligned. In features.parquet the column computed with the vendored main-pool code is 'beta_sim_raw' (Spearman/Pearson with plan-native 'beta_sim' only r = 0.16). SPEC P therefore uses beta_sim_raw in BOTH populations (like-for-like); plan-literal 'beta_sim' is run as sensitivity SPEC B_native. Declared before any statistic was computed.
