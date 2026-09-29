# T_design

| construct | definition | source |
|---|---|---|
| E_up (emergence label) | sustained-uptake onset label; POST-HOC primary promoted in iteration 2; confirmation only via the iteration-4 sealed fold | art_zw_JJGsUFSnd results/r1/verdict_heldout.json |
| A_cont (host anchoring) | mean pre-entry host share of the entry-year partners (exact OpenAlex subfield x block profiles); continuous primary after fallback 6 | art_2Cd2JJypeGuA results/d2_summary.json |
| CT (co-transfer) | share of entry partners that were origin companions in [e-5, e-1] | art_2Cd2JJypeGuA results/d2_summary.json |
| Y_strict (outcome) | W2 = [e+1, e+5] host papers by author-disjoint newcomers (count; PPML, concept-clustered) | art_2Cd2JJypeGuA results/d2_prereg.json |
| EST_bin (binary establishment) | iteration-1 establishment: >= 5 W2 newcomer papers and presence in >= 3 of 5 W2 years; NULL on held-out (co-primary p 0.165) | art_WZ8fbLn79nCq results/heldout_post.json |
| Persistent-neighbour closure (R1b) | triadic closure among top-20 neighbours present in both y and y-1; secondary Holm-family row | art_zw_JJGsUFSnd results/tables/r1_holm_decisions.csv |
| Folds | sha1 concept fold: MAIN 202 screen / 100 held-out (426-concept frame); each sealed fold opened once in iteration 4 behind hash-checked runners | art_htO_gJuUn6Pr results/main_population_hydrated.json |
| MeSH second population | 191 MeSH concepts never screened for D2; G4 covers biomedicine -> biomedicine host entries only | art_XGdzjWgi-a88 README.md |
| Adopter design | W2 newcomer adopters vs exact-matched risk-set controls on bins (prior works, team size, host activity, first year); conditional logit m2 is the pre-declared primary | art_FZ2OCJwV6xHs results/match_balance.json |
| RQ1 status | R1_DEAD: pooled-panel held-out closure -0.391 [-0.855, 0.072], Holm 0.147. Structural precursors of sustained uptake are volume/churn correlates. | art_zw_JJGsUFSnd results_note.md |

Sources (run-root-relative): 3_invention_loop/iter_3/gen_art/gen_art_experiment_5/results/main_population_hydrated.json; 3_invention_loop/iter_3/gen_art/gen_art_experiment_7/results/d2_prereg.json; 3_invention_loop/iter_3/gen_art/gen_art_experiment_7/results/d2_summary.json; 3_invention_loop/iter_4/gen_art/gen_art_evaluation_2/results/heldout_post.json; 3_invention_loop/iter_4/gen_art/gen_art_evaluation_3/results/r1/verdict_heldout.json; 3_invention_loop/iter_4/gen_art/gen_art_evaluation_3/results/tables/r1_holm_decisions.csv; 3_invention_loop/iter_4/gen_art/gen_art_evaluation_3/results_note.md; 3_invention_loop/iter_4/gen_art/gen_art_evaluation_5/results/match_balance.json; 3_invention_loop/iter_4/gen_art/gen_art_experiment_9/README.md
Assertion: every sourced cell re-read by audit_tables.py (10 cells, 0 failures).
