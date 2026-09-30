# Aligned-block table (main-pool labels/precursors on both populations)

**PRE-CHECK ON ALREADY-SCREENED DATA; NOT CONFIRMATION; E_up promoted post hoc** — both populations already screened.

| label | indicator | S_mesh [95% CI] | n_mesh | n_eff | Holm mesh | S_main [95% CI] | n_main | Holm main | sign agree | S_ivw (se) [boot SE] | Q (p_Q) [boot SE] | S_ivw / Q [CI-width SE = file method] | file reproduced | interpretable |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| E | accretion_shift_rar | 0.044 [0.004, 0.129] | 5 | 5 | 0.002 | -0.104 [-0.120, -0.016] | 3 | 0.003 | False | -0.027 (0.023) | 10.73 (0.001) | -0.043 / 12.68 | True | False |
| E | closure | 0.487 [-0.606, 1.581] | 5 | 5 | 0.594 | -0.625 [-0.656, -0.588] | 3 | 0.003 | False | -0.624 (0.017) | 3.82 (0.051) | -0.624 / 3.97 | True | False |
| E | P_rar | -0.026 [-0.076, 0.021] | 5 | 5 | 0.594 | 0.143 [-0.119, 0.301] | 3 | 0.074 | False | -0.017 (0.025) | 2.38 (0.123) | -0.017 / 2.36 | True | False |
| E_alt | accretion_shift_rar | 0.049 [0.010, 0.095] | 17 | 3 | 0.002 | -0.021 [-0.033, 0.093] | 10 | 1.000 | False | 0.034 (0.020) | 2.07 (0.151) | 0.027 / 3.24 | True | False |
| E_alt | closure | 0.081 [-0.296, 0.479] | 17 | 17 | 0.704 | -0.400 [-0.919, 0.190] | 10 | 0.504 | False | -0.077 (0.162) | 1.94 (0.164) | -0.077 / 1.94 | True | True |
| E_alt | P_rar | 0.029 [0.001, 0.059] | 17 | 17 | 0.088 | -0.044 [-0.227, 0.102] | 10 | 1.000 | False | 0.026 (0.015) | 0.71 (0.398) | 0.026 / 0.73 | True | True |
| E_up | accretion_shift_rar | 0.043 [0.007, 0.069] | 51 | 12 | 0.060 | -0.140 [-0.185, 0.018] | 21 | 0.180 | False | 0.031 (0.013) | 12.57 (0.000) | 0.028 / 11.42 | True | True |
| E_up | closure | -0.185 [-0.498, 0.108] | 51 | 51 | 0.210 | -0.837 [-1.260, -0.427] | 21 | 0.003 | True | -0.407 (0.126) | 6.02 (0.014) | -0.410 / 6.16 | True | True |
| E_up | P_rar | 0.017 [-0.004, 0.037] | 51 | 51 | 0.210 | -0.007 [-0.066, 0.056] | 21 | 0.824 | False | 0.014 (0.010) | 0.56 (0.455) | 0.015 / 0.53 | True | True |

IVW and Q re-derived twice: (i) with bootstrap SEs (main: exp_3 summary*.json 'se'; MeSH: rq1_effects_mainpool_aligned.csv 'se'); (ii) with SE = CI width / 3.92, which reproduces the side-by-side file exactly (the file's method). The two differ where bootstrap distributions are skewed (accretion rows with n_eff 3-12). Q (df = 1) has very low power at k = 2; a small Q is not evidence of homogeneity.

Source: round-2/experiment-4/src/results/side_by_side_mainpool_vs_mesh.csv; round-2/experiment-4/src/results/rq1_effects_mainpool_aligned.csv; round-2/experiment-3/src/results/event_study/summary*.json