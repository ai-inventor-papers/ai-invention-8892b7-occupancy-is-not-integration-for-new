# Deviations and post-freeze notes (G4 MeSH replication)

Frozen deviations (verbatim from results/mesh_spec.json, sha256 b7cdabf8144581ab7903ea29c3a8e9d03e047e45e7f343c0dec1cb4a05a47c91):

- D-M1 (data-forced) MeSH works carry legacy concepts at score >= 0.3 only, no topic score and no dup_group: partner floor 0.3 (main 0.2), no known-sub topic-score filter, no dup_group dedup. Harmonisation rows h1-h5 apply exactly these rules to the main screen (results/harmonisation_rows.csv).
- D-M2 (declared) entries restricted to PubMed-covered hosts (has_pmid share of the host subfield in the entry block); non-biomedical hosts are dropped (results/entry_counts_by_host_field.csv).
- D-M3 topic-score controls use the entry papers' LIVE OpenAlex topics hydrated in this run (main used stored scores); kept = True (hydrated event share 1.000).
- D-M4 coverage group_by split by OpenAlex domain because group_by returns <= 200 of 252 subfields: 24 list calls instead of the planned 6.
- D-M5 (pre-declared F6 widening, W1 counts only) the declared kw5 + coverage 0.50 design had 46 non-singleton concepts (< 50); chosen step F6b: kw3 + coverage 0.3 (2267 events, 187 concepts).
- D-M6 the $0 background-sample fallback was ADMITTED (r = 0.927, bg coverage 0.654); exact profiles are primary and bg shares fill only pairs without an exact profile (nat_source column; S16 = exact only).
- D-M7 exact profile fetch limited by the key's remaining daily credits (not the 3,000 cap): 2512 calls, stop reason 'plan complete'; tag-weighted coverage of the model sample 0.833.
- D-M8 power: rejection = b > 0 and two-sided CRV1 p < 0.025 (Holm level for the smaller p); the wild bootstrap is simulated only for T3 size (first 50 reps at 1.00 and 1.30, 399 draws).
- D-M9 the co-primary (concept + e + d) decides G4 (hypothesis restricts the claim to across entries); R1 is reported with its MDE and the thin-cell rule.
- D-M10 own-node matching also uses MeSH acronyms; only exact casefolded display-name matches are dropped.
- D-M11 co-authorship prior set limited to the MeSH corpus (117,253 works), as the main pool is within-corpus.
- D-M12 S12 (union c-paper set) runs without topic controls (union-only entry papers were not hydrated).
- D-M13 the workspace is not a git repository: the freeze is recorded by sha256 + UTC in logs/freeze_log.txt.

Post-freeze notes (none changes an outcome, a model, or the verdict rule):

- P1 src/report.py forest-plot tick/label formatting edited about 20 s after the code hashes were taken (logged in logs/freeze_log.txt).
- P2 harmonisation rows h6a/h6b (main screen, already seen) were computed after the MeSH look because they need the MeSH fetch coverage; they cannot change the frozen G4 verdict.
- P3 results/truncation_audit.json gained the audit at the chosen 0.30 coverage threshold (W1 entry years only) after the F6 widening fired.
- P4 results/g4_summary.json adds a POST-HOC size-calibrated p for R2 (observed CRV1 p referred to the 200 simulated null p values), because T3 found CRV1 size 0.105 at alpha .05. It is labelled post hoc and is not part of the verdict rule.
- P5 T3 size check failed (CRV1 0.105, wild 0.10 on 50 reps, target 0.03-0.08); the bias check passed (+0.004 at 1.00, -0.005 at 1.30). The pre-declared permutation placebo and within-concept outcome shuffle are reported next to CRV1 and wild.
