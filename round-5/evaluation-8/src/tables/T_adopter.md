# T_adopter

| exposure | OR | lo | hi | note |
|---|---|---|---|---|
| E_any, pre-declared primary m2 | 3.09 | 2.32 | 4.28 | prevalence 0.79 vs 0.61; risk ratio ~1.30; NOT '3.1x more likely' |
| E_any, m1 (not primary) | 3.14 | 2.37 | 4.29 | value the report printed |
| E_neg (frequency-matched negative-control concepts), m2 | 0.62 | 0.49 | 0.77 |  |
| E_plac (partners of another concept's entry into the same host), m_plac | 0.72 | 0.57 | 0.90 |  |
| E_swap | 1.11 | 0.86 | 1.39 |  |
| E_for (FOREIGN partners) | 2.88 | 2.28 | 3.69 |  |
| E_adj (ADJACENT) | 1.91 | 1.43 | 2.73 |  |
| E_nat (NATIVE) | 1.47 | 1.02 | 2.33 |  |
| E_any x A_cont interaction | 0.87 | 0.70 | 1.14 |  |
| Robustness: 1:3 matched | 2.96 |  |  |  |
| Robustness: expanded frame (no concept cap) | 2.62 |  |  |  |
| Robustness: Physics/Astro | 3.87 |  |  |  |
| Robustness: CS | 3.46 |  |  |  |
| Robustness: single-paper entries | 3.59 |  |  |  |
| Robustness: multi-paper entries | 2.33 |  |  |  |
| Post-hoc origin-subfield check: partner OR given origin | 2.52 |  |  | post-hoc |
| Native/foreign exposure ratio | 0.51 | 0.33 | 0.89 |  |
| Coverage: adopter pairs without prior corpus work (excluded) | 86.9% |  |  | of 21,941 pairs; exposure is corpus-only (0 OpenAlex credits spent: api_results.json) |
| Reading | consistent with absorptive capacity OR topical proximity |  |  | Jia, Wang & Szymanski 2017 local interest drift is the rival |

Sources (run-root-relative): round-4/evaluation-5/src/results/enrichment.json; round-4/evaluation-5/src/results/frame_summary.json; round-4/evaluation-5/src/results/interaction.json; round-4/evaluation-5/src/results/ratios.json; round-4/evaluation-5/src/results/supplementary.json; round-4/evaluation-5/src/results/vocab_class.json
Assertion: every sourced cell re-read by audit_tables.py (38 cells, 0 failures).
