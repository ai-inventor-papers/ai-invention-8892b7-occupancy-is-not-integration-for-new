# T_table18

| item | claimed | status | evidence_lines | still_open |
|---|---|---|---|---|
| M1 | iterations 1-3 carried verbatim; inline [Correction] markers | PARTIAL | iteration-4 correction markers at lines [486]; drift lines in iterations 1-3 without a marker: [7, 50, 77, 477, 551] | add [Correction, iteration 4/5] markers at every drift line listed in report_drift.csv before line 606 |
| M2 | Holm columns and detail rows added to iteration-3 tables | NOT DONE | Table 14 header at line [417] has no Holm column | add Holm column to Table 14 (T_rq1 has the held-out Holm values) |
| M3 | robustness count corrected inline (26/27 -> 20/26) with null | PARTIAL | correction note at [486]; '26 of 27' still at [486, 551, 863]; the note mis-defines 20/26 as excluding base and strata | replace at line 551; restate '20 of 26 incl.; 18 of 22 excl.' |
| M4 | closure claim graded by held-out outcome | PARTIAL | Artifact 18 body says 'not confirmed' (line [736]); summary line 7 and heading line [843, 867] rescue R1; 'R1_DEAD' at [] | state R1_DEAD and the volume/churn sentence in summary, heading and fig_methodology |
| M5 | full lead-lag category-count table added (Table 21) | DONE | Table 21 at [768]; all 24 counts re-derived (ll.* rows OK); MeSH null p 0.43, log-rank, Granger still missing | add MeSH null (p 0.43), log-rank p 0.005, F<=2012 cohort 12, Granger b -0.0013 p 0.068 |
| M6 | iteration-3 Strategy expanded; iteration-4 decision rules ar | NOT DONE | 'DECISION RULES FOR THE PAPER' at []; iteration-4 Strategy is 5 lines | copy the iteration-4 decision rules verbatim (T_decision) into the Strategy |
| M7 | coverage table updated with caveats | DONE | coverage header with Caveats at [877]; activity 6 status still Partial (line [884]) | set activity 6 to Done (cases.md) |
| M8 | all [ARTIFACT:] markers use artifact IDs | PARTIAL | Artifact 2 marker at [77] points to dataset_5's id | cite 3_invention_loop/iter_1/gen_art/gen_art_dataset_2 for Artifact 2 |
| M9 | prior-review must-fix items incorporated where data are avai | NOT DONE | SENS2 at [], Granger at [], MISSING_IN_REPORT count at [] | transcribe T_missing (292 rows) incl. SENS2, r1a correlations, Granger |
| M10 | nearest-neighbour comparison two-sided (Cheng tension, Gueva | DONE | Guevara at [627, 865, 971], Cheng tension at [865] | add Jia 2017 / Hofstra 2020 for the adopter result |
| m1 | minor slips corrected: robustness count, Holm p precision, d | NOT DONE | S_raw_cc at []; fresh-replication n_matched 14 at [] | label Table 13 S_raw as S_raw_cc; give n_matched = 14 at line 432 |

Sources (run-root-relative): 3_invention_loop/iter_5/gen_strat/current_report.md
Assertion: every sourced cell re-read by audit_tables.py (11 cells, 0 failures).
