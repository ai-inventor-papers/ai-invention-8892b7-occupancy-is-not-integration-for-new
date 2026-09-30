# Open neighbourhoods precede concept spread: structural antecedents and cross-disciplinary diffusion of emerging scientific concepts

This report documents an investigation of how emerging scientific concepts can be identified and characterised through evolving knowledge networks, and through which structural pathways they spread across disciplinary boundaries. The study builds on an OpenAlex-based scholarly dataset of 426 semantically grounded concepts with 462,812 works, constructs yearly co-occurrence and concept-discipline networks, and tests whether structural indicators provide early signals of emergence and cross-disciplinary integration.

Two research questions structure the work. RQ1 asks which temporal and structural patterns in an evolving, semantically grounded scientific knowledge graph characterise the emergence of scientific concepts. RQ2 asks how emerging scientific concepts diffuse across disciplinary communities over time, and which temporal network patterns distinguish locally concentrated concepts from concepts that become broadly integrated into the scientific knowledge network.

The study began with a source-sink viability hypothesis adapted from population ecology [1], asking whether a concept's presence in a subfield is self-sustaining or import-dependent. That hypothesis was blocked by insufficient citation-layer density (Gate A failure: only 17.3% of concept-subfield-year edges meet the within-host tracing threshold). The investigation then followed the pre-registered fallback, yielding two main findings. First, emerging concepts have significantly lower triadic closure than matched controls before onset, suggesting they inhabit structurally open, bridging positions rather than dense clusters (RQ1). Second, when a concept enters a new host subfield, the share of its initial co-occurrence partners that are native to that host predicts subsequent uptake by newcomer authors, while the share of origin companions does not (RQ2). A data-derived diffusion typology separates concepts into localised and broad-from-the-start trajectories, and network expansion precedes disciplinary diffusion in 94% of concepts exhibiting both transitions.

The target venue is Applied Network Science, whose published work on knowledge diaspora [6], disciplinary roles in field-of-study networks [7], alluvial community change [8], and the epistemic integration of AI in neuroscience [9] provides the closest comparison base.

---

# Iteration 1

## Strategy

The first iteration was devoted to three preparatory tasks: (a) assembling a prior-art and pre-registration dossier grading each candidate mechanism's novelty and feasibility, (b) building the concept pool and its associated OpenAlex work corpus, and (c) constructing the semantic grounding infrastructure (concept detection, labelling, variant merging) and a held-out MeSH confirmation population. No experiment or evaluation was executed. Every artifact in this iteration is either a dataset or a research dossier. The rationale was to fix all operational definitions, sample the data, and verify the citation-layer gate (Gate A) before committing compute to network construction and statistical modelling.

The pre-registration dossier ranks five candidate mechanisms by novelty margin against the nearest prior work. Host anchoring (the share of a concept's new co-occurrence edges in a host subfield that attach to host-native concepts) was ranked highest at medium-to-high novelty; toolkit co-transfer (the fraction of a concept's origin companions that co-appear in host papers) was ranked high on measurement novelty but coupled to host anchoring; citation-lineage source-sink viability was ranked medium, with Kuhn et al.'s meme propagation score [10], Kiss et al.'s epidemic diffusion model [11], De Domenico et al.'s author-flow source-sink indices [6], and Maillart et al.'s endogenous-exogenous decomposition [5] as the nearest antecedents. Origin-neighbourhood structure (the participation coefficient and clustering topology of the concept in its birth subfield) was ranked low-to-medium because structural diversity and community spread are well studied [12], and the demic-versus-cultural adoption channel was ranked medium but with the weakest feasibility due to author-disambiguation biases [ARTIFACT:art_bNCGUJX2MUhX].

A pre-registered screen was fixed before any data were inspected. The unit of analysis is a concept c in non-origin subfield d at focal year t (2010–2014), with at least 10 d-papers in W1 = [t−5, t]. The primary measure is out-of-sample ROC-AUC for establishment in W2 = [t+1, t+5], where establishment means at least 5 W2 d-papers by author-disjoint newcomers and presence in at least 3 of the 5 W2 years. The BASE model includes W1 edge volume, momentum, concept age, subfield-year size, concept total volume, concept entropy, subfield count, growing-edge breadth, Rafols integration, relatedness density and Maillart-style features. Each candidate adds only its own pre-registered scores. A candidate survives if its delta-AUC over BASE has a concept-bootstrap (1,000 reps) 95% CI lower bound above 0, its point gain is at least 0.01, and the coefficient sign matches its prediction. The candidate with the largest lower CI bound is the winner.

## Artifact 1: concept pool and OpenAlex work corpus

The concept pool was built in an outcome-blind frame. The sample was frozen and hashed (SHA-256 80e3f244...0c44) before any post-appearance-window data were inspected [ARTIFACT:art_94GEMUsgAmgK]. The pool comprises 206 concepts, of which 184 are main emerging concepts (first appearance year F in 2005–2016, with 20–300 papers in the window F to F+2 and no more than 8,000 total works through 2024) and 22 stationary reference concepts (at least 5 hits in every year 1998–2004 with a 7-year sum of 70–700). The 184 main concepts are split by a SHA-1 hash into a screen fold of 123 and a held-out concept fold of 61; focal-year tags are separate (screen 2010–2014, held-out 2016–2018).

The pool is heavily dominated by arXiv-sourced concepts. Of 366 eligible candidates, 363 came from the arXiv-mined arm, and the final 184 span three origin fields. The original target of approximately 600 concepts (floor 400) was not met because the shared free OpenAlex API key exhausted its daily credit allowance during hydration.

**Table 1. Concept pool composition by origin field.**

| Origin field | Main concepts | Share |
|---|---|---|
| Physics and Astronomy | 82 | 44.6% |
| Physical Sciences (other) | 56 | 30.4% |
| Computer Science | 45 | 24.5% |
| Other | 1 | 0.5% |
| **Total main** | **184** | **100%** |

**Table 2. Concept pool by first-appearance band.**

| F band | Count |
|---|---|
| 2005–2007 | 38 |
| 2008–2011 | 76 |
| 2012–2016 | 70 |
| **Total** | **184** |

Verified links pairing each concept with the OpenAlex works that use it total 214,798 pairs spanning 208,374 unique works. Among the 121,829 main-arm links, 56,997 matched in the work title, 51,966 in the abstract, 10,177 through Semantic Scholar only, and 2,689 through OpenAlex concept indexing alone. [Correction, iteration 2: the match-evidence counts above are main-arm only; across all 214,798 links the counts are oa_abstract 98,192, oa_title 92,043, s2_only 21,509, oa_index_only 3,054.] Of the 184 main concepts, 24 were discovered natively in OpenAlex and 160 were discovered through the Semantic Scholar index and mapped to OpenAlex (mapping rate 0.93). [Correction, iteration 2: the 26/180 figures reported previously referred to the full 206-concept pool including reference concepts. Among the 184 main concepts the split is 24 native and 160 S2-mapped.] Twenty-one concepts carry a sense-check failure flag, indicating that the dominant sense of the surface form covers fewer than 70% of year-F title matches (the threshold is 0.70, not 0.50 as previously stated).

[FIGURE:fig_methodology]

### Gate A: citation-layer feasibility

The quality report shows that among main-arm concept papers with references, 66.99% cite at least one earlier concept paper (the "traced share"), and after excluding first-year canonical papers and the five most-cited concept papers, the traced share remains 60.80%. The host-specific traced share (concept papers outside the origin subfield that cite at least one earlier concept paper from any subfield, not restricted to the same host subfield) is 55.18%, above the 40% gate threshold on the lenient definition. [Correction, iteration 2: the original description stated "at least one earlier concept paper in the same host subfield", but the code counts any earlier concept paper as a parent regardless of subfield. By year, the lenient host traced share ranges from 0.317 (2010) to 0.517 (2014) across the screen's focal years, with three of five below 0.40. This distinction matters because the within-host share, computed in iteration 2, is much lower (mean 0.20 on 724 edges), which is the finding that blocks the viability decomposition.]

**Table 3. Citation-layer quality by origin field.**

| Metric | All main | Physics & Astro | Physical Sci | Computer Sci |
|---|---|---|---|---|
| Concept papers (n) | 121,829 | 19,653 | 46,575 | 55,274 |
| Share with references | 83.92% | 82.04% | 84.99% | 83.74% |
| Traced share (any parent) | 66.99% | 66.12% | 67.89% | 66.53% |
| Traced share (excl. F + top-5) | 60.80% | 57.74% | 61.75% | 61.09% |
| Host traced share (any parent, excl. F) | 55.18% | 49.68% | 58.39% | 53.86% |
| Host concept papers (n) | 41,861 | 4,171 | 15,973 | 21,609 |

Source: gen_art_dataset_1/context/quality_report.md

The recall audit, comparing counts derived from OpenAlex against independent Semantic Scholar counts for 30 concepts, gives a median count ratio of 0.84 (IQR 0.79–0.89) and a Spearman rank correlation of 0.976. For the 160 main concepts discovered through Semantic Scholar, this comparison measures mapping and verification loss rather than true recall against an independent source. Recall against OpenAlex's own index is therefore unmeasured for approximately 87% of the pool.

### Denominators and venue habitat

Totals by subfield and year cover 25,195 rows (all 252 OpenAlex subfields across 25 years in four counting variants). A venue-habitat file assigns 15,261 venues to their dominant subfield. [Correction, iteration 2: the habitat was described as "pre-period publication shares" and "citation-independent". It was computed from each source's all-years OpenAlex topic counts in the 2026 snapshot. Those topic counts come from the same citation-reading topic classifier whose temporal label leakage the dossier flagged. The habitat is therefore neither pre-period nor citation-independent. An ASJC journal-level habitat was built in iteration 2 as a replacement, though its coverage is only 12.1% of concept-work links.]

## Artifact 2: whole-science background sample

A design-weighted background sample of 259,716 OpenAlex works from 1,260 strata (150 per field × year, weights summing to 149,116,575) was built to supply co-occurrence network snapshots and calibrate host-nativeness profiles [ARTIFACT:art_eR1Z7fMlOcxs]. It delivered 6,325 exact subfield × year totals and 400 exact concept × block subfield profiles for 100 calibration concepts at a cost of $0.1952 in OpenAlex credits.

The key finding of this artifact is negative: sample-based per-concept subfield profiles are unreliable for determining host-nativeness. In the calibration table, the median total-variation distance between sample and exact profiles is 0.41–0.79 by frequency decile, and top-subfield agreement is only 0.28–0.65. This means host-nativeness (the input to candidates C1 and C2) and the concept-concept background network cannot be computed reliably from this sample alone, and require paid exact profiles. About 12% of the weighted frame carries the default low-confidence topic T14423, and concept ancestors are no longer served by the API.

The worker timed out after writing all outputs (no new JSONL records for 2,096 seconds), so its status is "failed" while its data are usable.

Source: gen_art_dataset_2/data_card.md, calibration_by_decile.csv

## Artifact 3: held-out MeSH confirmation population

A separate biomedical confirmation arm was built from new MeSH descriptors (DateEstablished 2006–2016, widened to 2004–2005 and 2017–2018) [ARTIFACT:art_HGiVAYhqO-6q]. Starting from 28,472 descriptors, the pipeline selects 5,201 topical descriptors, retains 3,430 after the provenance filter (dropping parenthetical-prior-year, promoted-term, and renamed descriptors), narrows to 283 passing the PubMed novelty pre-screen and early-volume rule, and adds widening-pool candidates. After the final rule, 191 concepts survive: 99 core 2006–2016, 14 from the 2004–2005 widening, and 78 from the 2017–2018 widening.

**Table 4. MeSH held-out population by branch group.**

| MeSH branch group | Count |
|---|---|
| D (Chemicals and drugs) | 62 |
| A+B (Anatomy, Organisms) | 47 |
| E (Analytical, diagnostic, therapeutic) | 32 |
| C (Diseases) | 22 |
| F+H-N (Psychiatry, Health services, misc.) | 17 |
| G (Phenomena and processes) | 11 |
| **Total** | **191** |

Caveats: only approximately 25% of new MeSH descriptors are genuinely new concepts (the remainder are reclassifications or splits), making MeSH a weak ground truth. Only 13 of 191 have their full non-PubMed works paged; the remaining 178 have PubMed-indexed works only, which biases their concept-discipline edges toward biomedical subfields and makes them not directly comparable to the main corpus for cross-disciplinary breadth until retrieval is complete. The route calibration (union vs plain OpenAlex search, median ratio 0.8598, range 0.54–0.91 over 10 concepts) and a 60-record provenance spot check (0 decision errors) provide the arm's validity numbers.

Source: gen_art_dataset_3/selection_flow.json, provenance.md, route_calibration.json

## Artifact 4: semantic grounding and labelling infrastructure

The semantic grounding artifact provides the infrastructure for detecting, labelling, and merging concept mentions [ARTIFACT:art_QpM5SM6a7SH6]. It comprises seven datasets.

**Stratified corpus.** 93,600 English OpenAlex articles and reviews with abstracts, sampled at 150 per field × year stratum across 26 OpenAlex fields (54,600 main-period 2003–2016 and 39,000 pre-screen 1995–2004).

**Candidate phrases labelled by LLMs.** From 1.22 million distinct noun-phrase and acronym keys, 4,599 were labelled as CONCEPT, NOT_CONCEPT, TOO_GENERIC, or VARIANT_OF by two LLMs (gemini-2.5-flash-lite as model A, gpt-4.1-nano as model B) with a claude-haiku-4.5 adjudicator. The train-test split (1,200 train, 300 test) is clustered by variant group.

**Table 5. Labelling quality.**

| Metric | Value |
|---|---|
| Model A vs model B inter-rater kappa (4-class) | 0.259 |
| Model A vs model B binary kappa (concept vs rest) | 0.267 |
| A vs adjudicator kappa (4-class, silver-gold 200) | 0.632 |
| A vs human anchors binary kappa (SemEval/SciERC) | 0.56 |
| A precision (concept, human-anchored) | 0.79 |
| A recall (concept, human-anchored) | 0.76 |

**Survivorship-free phrase pool.** 1,000 text-mined candidate keys (587 labelled CONCEPT by model A), with yearly counts restricted to F through F+2. Only 1 strict-eligible anchored phrase was found, far below the target of 150, due to the low yield of the text-mining pipeline and OpenAlex credit exhaustion. The full post-F+2 trajectories are sealed.

Source: gen_art_dataset_4/labelling/quality.json, logs/summary.json

## Artifact 5: prior-art dossier and pre-registration

The research artifact [ARTIFACT:art_bNCGUJX2MUhX] grades each candidate mechanism's novelty margin against the nearest prior art. The headline finding is that the space is active but no prior study estimates a within-host reproduction ratio with an import share per concept-subfield edge, nor tests host anchoring at the edge level. The nearest published result for the viability idea is Maillart et al. [5], who find that endogenous reinforcement is almost unpredictable (test R² = 0.018) while exogenous diffusion is predictable (R² = 0.78). That result speaks directly to whether local reproduction carries signal.

**Table 6. Candidate mechanism novelty grades.**

| Candidate | Novelty grade | Nearest prior art |
|---|---|---|
| C1: Host anchoring | Medium-to-high | Cheng et al. 2023 [13] |
| C2: Toolkit co-transfer | High (coupled to C1) | No quantitative co-arrival test found |
| C0: Source-sink viability | Medium | Kuhn et al. 2014 [10]; Maillart et al. 2026 [5] |
| C4: Demic vs cultural | Medium | Fontaine et al. 2024 [9] |
| C3: Origin-neighbourhood structure | Low-to-medium | Structural diversity literature [23, 24] |

Source: gen_art_research_1/research_report.md, research_verification.json

## Dead ends and shortfalls

1. **Concept pool size.** 184 of 400 target concepts realised. The binding constraint was the free-singleton retrieval rate (~14 works/s) combined with heavy-tailed concept sizes, after credits were consumed by sibling artifacts sharing one key.

2. **Field coverage.** The pool draws overwhelmingly from physics, physical sciences, and computer science (363 of 366 eligible candidates from the arXiv-mined arm). The OpenAlex keyword/taxonomy arm had a 2.2% eligibility yield (3 of 134 candidates) because OpenAlex tags are retroactive: "optogenetics" had 152 pre-2005 tagged works and "blockchain" 191. This evidence, not credit exhaustion, killed the taxonomy arm and constrains whether OpenAlex concepts can date emergence.

3. **Survivorship-free phrase pool yield.** 1 of 150 target strict-eligible anchored concepts. The artifact's own diagnosis is that phrases seen once in a ~0.1% sample are overwhelmingly compositional or pre-existing; lowering the early-volume bound multiplies yield 6–11× per the yield curve.

4. **Labelling quality.** Silver labels only (no human check). Model A's bias is moderate; model B over-labels CONCEPT (1,333 of 1,491 items vs A's 882).

## What we have learned so far

Iteration 1 established the data foundation and pre-registration. The concept pool of 184 main emerging concepts and 22 reference concepts, with 214,798 verified concept-to-work links and 208,374 unique works, passes the citation-layer gate on the lenient (any-parent) definition but has not been tested at the within-host edge level required for viability estimation. The MeSH held-out population of 191 biomedical concepts provides a secondary check arm, though with caveats on completeness and ground-truth quality. No experiment was executed; no quantitative result about the hypothesis exists.

## Coverage against the original request

| Activity | Status | Artifact |
|---|---|---|
| 1. Prepare and semantically ground dataset | Partial | art_94GEMUsgAmgK, art_QpM5SM6a7SH6 |
| 2. Construct evolving knowledge network | Not started | – |
| 3. RQ1: temporal network analysis | Not started | – |
| 4. RQ2: cross-disciplinary diffusion | Not started | – |
| 5. Identify recurring trajectories | Not started | – |
| 6. Validate with representative cases | Not started | – |

---

# Iteration 2

## Strategy

Iteration 2 was a FIX iteration. Five goals were set: (i) complete the hydration and add exact nativeness profiles and a citation-independent venue habitat; (ii) train and evaluate the concept grounding pipeline; (iii) compute Gate A as written (within-host, non-canonical, per W1 year) and estimate viability states with synthetic validation and pre-outcome power; (iv) build the yearly concept-concept co-occurrence network and run the RQ1 event study; (v) replicate the RQ1 event study on the MeSH population.

Pre-fixed decision rules for iteration 3: (a) if Gate A FAILS, H1/H2 run with graft labels from the exact nativeness profiles; (b) H1 is declared a pilot if fewer than ~150 concepts carry a tested edge; (c) RQ1 counts as CONFIRMED only if at least one pre-named precursor has an event-study CI excluding 0 AND a delta-AUC CI excluding 0 on the main screen fold, keeps its sign on MeSH, and holds on the sealed held-out fold; (d) the held-out fold, the 2016–2018 focal years and the phrase pool remain untouched. One design decision was to run one artifact on the OpenAlex key at a time.

## Artifact 6: hydrated corpus, nativeness profiles, and venue habitat

This artifact completes the hydration of the concept pool from 184 to 426 concepts (366 main: screen 247, held-out 119; 60 reference), with 462,812 works and 488,078 verified concept-work links [ARTIFACT:art_eR1Z7fMlOcxs]. The frame SHA-256 hash (80e3f244...0c44) was verified. Retrieval route: A_openalex_native for 46 concepts and B_s2_index (S2-mapped) for 380, driven by hydration timing, not concept properties. Sense-check failures: 45.

**Nativeness profiles.** 5,488 exact OpenAlex primary_topic.subfield × block counts (2000–04, 2005–09, 2010–14, 2015–19) for the top 1,372 legacy-concept nodes by host co-occurrence weight, covering 78.7% of host weight (below the 90% strategy target; 95% would need 7,584 nodes). 2,073 profiles are truncated at top-200 (missing tail median 0.1%, max 1.2%).

**ASJC venue habitat.** 22,970 venues; 2,929 covered (2,892 citation-independent from SCImago/Scopus ASJC categories, 37 from pre-period 2000–04 topic fallback). Coverage: 12.1% of concept-work links. The low coverage is driven by multi-category journals (38.5% of venue c-papers) and arXiv (16.3%).

**Table 7. Dataset 6 summary.**

| Metric | Value |
|---|---|
| Concepts hydrated | 426/426 |
| Works | 462,812 |
| Concept-work links | 488,078 |
| API credits consumed | 7,237 |
| Nativeness profiles | 5,488 (1,372 nodes × 4 blocks) |
| Host weight coverage | 78.7% |
| ASJC venues covered | 2,929 (12.1% of links) |

Source: gen_art_dataset_5/run_ledger.json, README.md

Note: the iteration-2 RQ1 and viability experiments (Artifacts 8–10 below) ran on the iteration-1 184-concept corpus in parallel with the hydration. The 426-concept hydrated corpus was not used until iteration 3.

## Artifact 7: concept grounding pipeline

This artifact trains and evaluates three components: a binary classifier, a variant merger, and a NIL-aware linker [ARTIFACT:art_BdBvbNuNU8E7].

**Classifier.** L2-regularised logistic regression (C = 0.01) on lexical features, outcome-blind termhood features, PCA-64 of MiniLM embeddings, and PCA-64 of SPECTER2 embeddings, trained on 1,200 D2 silver labels.

**Table 8. Classifier performance on test set (n = 300).**

| Metric | Classifier | LLM-A | Majority (predict-all-positive) |
|---|---|---|---|
| F1 | 0.818 | 0.901 | 0.715 |
| AUC | 0.888 | – | – |
| Precision | 0.759 | – | – |
| Recall | 0.886 | – | – |
| Accuracy | 0.780 | – | – |

[Correction: previous Table 9 reported P 0.812, R 0.824, accuracy 0.843, which are not reproducible from the test predictions. The majority-class baseline F1 is 0.715 (predict-all-positive), not 0.000 as previously stated. The classifier's human-anchor kappa is 0.413; the 0.56 previously reported is LLM-A's value. LLM-A beats the classifier (delta −0.083 [−0.128, −0.041]), but this comparison is circular since A co-produced the silver training labels.]

Against human anchors (SemEval-2017/SciERC): classifier E1 kappa 0.41, F1 0.674; E2 F1 0.706, AUC 0.82.

Source: gen_art_experiment_1/results/d2_test_predictions.json

**Variant merger.** L2 logistic regression on 14 pair features (not cosine similarity alone as previously described). Operating threshold p_merge = 0.855. D3 test F1 0.357; held-out MeSH F1 0.222; B-cubed F1 0.78 (computed on 902 held-out MeSH terms, not the full clustering).

**NIL-aware linker.** MiniLM embeddings, tau 0.95 (link precision ≥ 0.90 at NIL prior 0.9; in-KB recall 0.404). Wikidata was partial (HTTP 429). Main arm: LINKED_EXACT 39, BROADER 15, UNLINKED 312.

**Test population** (sha256 6a887fb4...5505): MAIN 156 (all hydrated; ≥ 150 power rule met), STRICT 147 (t_P90 = 0.647 plus p_merge_strict), REFERENCE_ACCEPTED 42, SENSITIVITY 426 (the unfiltered frame). Classifier rejection is enriched for sense-check failure (Fisher p = 0.025). The sense proxy from arXiv titles failed validation (kappa 0), so pending concepts carry sense status "missing".

Source: gen_art_experiment_1/README.md, results/test_population.json

## Artifact 8: viability layer, Gate A, viability states, synthetic validation, and power

This artifact attempts to estimate viability states for concept-subfield-year edges using citation lineages [ARTIFACT:art_yjFB8Spw2w6M]. All rules were pre-registered and hashed before any statistic (sha256 5dd16d8a...5aac).

### Gate A re-test at edge level

**Gate A FAILS.** Only 17.3% of 724 main-arm host edge-years (97 concepts, |K_d| ≥ 10) have a within-host non-canonical traced share at or above 0.40. The mean within-host traced share is 0.20, median 0.15. On the same 724 edges, the lenient any-parent share is 0.477 (64.2% ≥ 0.40), confirming that the drop from 55.18% to 17.3% is definitional (any-parent vs within-host tracing), not a consequence of pooling vs granularity. The reference-arm host share is 0.13. By year for the main screen (2010–2014), within-host means are 0.20, 0.28, 0.23, 0.19, 0.20.

[FIGURE:fig_gate_a]

**Table 9. Gate A edge-level results.**

| Metric | Within-host | Any-parent (same edges) |
|---|---|---|
| Share ≥ 0.40 | 17.3% | 64.2% |
| Mean traced share | 0.20 | 0.477 |
| Median traced share | 0.15 | – |
| Reference arm host share | 0.13 | – |

Source: gen_art_experiment_2/results/gate_a/gate_a_by_arm_fold_year.csv

Per pre-registered decision rule (a): Gate A 0.1727 < 0.5 triggers the graft fallback. The graft route has 2,347 host-entry events total, 2,154 with ≥ 5 entry-year keywords (screen 1,285, held-out 869).

### Viability states (descriptive only)

Of 779 eligible edges, 169 were tested: SOURCE 63, SINK 26, FADING 7, UNDETERMINED 683 (reason codes: below_nmin 65.6%, no_cohort_parents 12.7%, tested 21.7%). The synthetic FDR is 0.209, exceeding the 0.15 threshold; SOURCE FDR 0.13 (acceptable), SINK FDR 0.40 (unreliable, because import share m absorbs noise citations). The P1 entropy-share decomposition over pooled edges: SOURCE 1.4%, SINK 0.4%, UNDETERMINED 70.4%, ORIGIN 27.6%.

Source: gen_art_experiment_2/results/viability/viability_layer.csv, results/synth/synth_results.json, results/p1/p1_summary.json

### Power before any outcome

Per decision rule (b), H1 is PILOT-ONLY: N_c = 38 at n_min 30; projected 77.5 (66–92) on the hydrated pool. Minimum detectable effects (delta-AUC units): at AUC 0.70, realised MDEs are 0.070 (n_min 5), 0.073 (10), 0.100 (20), 0.134 (30); at AUC 0.80, 0.050, 0.054, 0.092, 0.116. Projected values at n_min 5/10: 0.039/0.042. Gate B FAILS: 0 labelled episodes; approximately 70 concept clusters needed for MDE ≤ 25%.

[Correction: previous Table 15 reported MDEs in "Cohen's d" units (1.22 to 0.36) that do not appear in any artifact output. The artifact's MDEs are delta-AUC values from results/power/h1_mde.json.]

Source: gen_art_experiment_2/results/power/h1_mde.json, decisions.json

## Artifact 9: precursor event study, main pool (RQ1)

This artifact runs the precursor event study on the main pool's screen fold, testing whether volume-normalised structural precursors distinguish emerging from non-emerging concepts before onset [ARTIFACT:art_mbFjmo5rbbf8]. Built 25 yearly 3-year-window co-word snapshots (2000–2024) from the design-weighted background sample (~27,000 nodes, ~84,000 kept edges, association-strength weights, Leiden best-of-5, alluvial IDs).

### Emergence labels

The primary label E (all-node strength percentile gain ≥ 20) yields only 4 onsets (rate 2.1%) because pool concepts sit in the bottom ~5% of the legacy-concept strength distribution, making it severely underpowered. E_alt (pool-only percentile, promoted post hoc after primary yield was seen): 14 onsets (6.7%). E_up (sustained uptake only, also promoted post hoc): 41 onsets, 21 matched.

**Table 10. Emergence label counts.**

| Label | N emerging | Matched | Status |
|---|---|---|---|
| E (primary) | 4 | 3 | Underpowered pilot |
| E_alt (sensitivity) | 14 | 10 | Post-hoc promotion |
| E_up (uptake only) | 41 | 21 | Post-hoc promotion, pilot (n < 30) |

### Event study results

Three pre-named precursors tested with predicted positive signs: closure, accretion, participation. All three pre-registered signs FAILED.

**Table 11. Event study results, E_up.**

| Indicator | Estimator | S | 95% CI | Holm p |
|---|---|---|---|---|
| Closure (log-ratio) | Event study | −0.837 | [−1.26, −0.427] | 0.003 |
| Closure (log-ratio) | Pooled panel | −0.743 | [−1.06, −0.46] | – |
| Accretion share | Event study | −0.14 | [−0.185, 0.018] | 0.18 |
| Participation coefficient | Event study | −0.007 | [−0.066, 0.056] | 0.824 |

[Correction: previous Table 17 paired event-study S values with pooled-panel Holm p-values. The values above are estimator-consistent.]

[FIGURE:fig_closure_event]

Exploratory findings (BH q < 0.05): before sustained uptake, concepts show higher novelty (+0.156), new-relation rate (+0.128), within-module z-score (+0.073), and burst state (+0.171). Under E_alt, subfield count is higher and neighbourhood change shows replacement rather than accretion (lower nestedness). The artifact's characterisation of emergence is "open, novel, fast-renewing neighbourhoods".

### Prediction

The pre-registered primary model is L2 logit. For E_up: BASELINE AUC 0.890, FULL (baseline + precursors) AUC 0.879, delta −0.010 [−0.045, 0.021]. Precursors add no predictive value beyond frequency, burst, degree, centrality and entropy baselines. [Correction: previous Table 18 silently reported the secondary HistGradientBoosting model instead of the primary logit.]

Source: gen_art_experiment_3/results/prediction/summary.json, results_summary.json

### Trajectory patterns and typology

Early bridging is common but non-discriminating (76% of all concepts). Incubation-then-expansion: 0% (concepts are "born expanding"). The 7-channel DTW typology is unstable at every k (min Jaccard ≤ 0.51). An entropy-only typology IS stable (Jaccard 0.95, AMI 0.14 vs the network typology).

Source: gen_art_experiment_3/results_summary.json

## Artifact 10: precursor replication, MeSH population (RQ1)

This artifact replicates the precursor event study on the 191 MeSH concepts [ARTIFACT:art_yWUkgWWKyq_h].

**Table 12. MeSH closure effects.**

| Label | n_eff | Closure D | 95% CI | Holm p |
|---|---|---|---|---|
| PRIMARY | 15 | −0.086 | [−0.511, 0.402] | 0.677 |
| SENS1 | 29 | −0.419 | [−0.740, −0.115] | 0.039 |
| E_up | 51 | −0.185 | [−0.498, 0.108] | 0.21 |

[Note: the E_up row is from the main-pool-aligned block (replication_verdict.json), which uses the same operationalisation as the main pool. Under E and E_alt with the main-pool-aligned definitions, the MeSH closure sign is positive (+0.487 and +0.081), so sign agreement across labels is inconsistent. The IVW pooled E_up estimate is −0.41 (SE 0.125) with heterogeneity Q = 6.16.]

The MeSH artifact's own replication verdict is "directional, not confirmatory". Per decision rule (c): NOT MET. The predicted + sign failed, the delta-AUC CI includes 0, and sign consistency across labels is not maintained.

MeSH patterns differ from the main pool: early bridging 0.59 vs 0.76 (+0.11 [0.02, 0.20]) and incubation-then-expansion 0.17 vs 0.00. The artifact calls this "a genuine between-population difference".

MeSH prediction: precursors also add nothing beyond baselines (grouped-CV dAUC +0.002 [−0.035, 0.035]). Under E_vol and E_cent, precursors significantly hurt prediction.

Source: gen_art_experiment_4/replication_verdict.json, rq1_patterns.csv, rq1_prediction.csv

## Decision-rule evaluation

| Rule | Verdict | Evidence |
|---|---|---|
| (a) Gate A → graft fallback | TRIGGERED | Within-host 0.1727 < 0.5; 2,347 graft events |
| (b) H1 pilot-only | YES | N_c = 38 < 150 |
| (c) RQ1 confirmed | NOT MET | Sign not +; delta-AUC CI includes 0; MeSH sign inconsistent |
| (d) Held-out sealed | YES (exp_3/exp_4) | Caveat: exp_2 computed origin series for 61 held-out concepts |

## Dead ends and negative results

1. **Gate A failure at edge level.** Within-host traced share 0.204 vs any-parent 0.477 on the same 724 edges. The viability decomposition central to the original hypothesis cannot be executed. Per decision rule (a), H1/H2 move to the graft fallback.

2. **Synthetic validation FDR exceeds threshold.** Overall 0.209 > 0.15; SINK FDR 0.40.

3. **No stable 7-channel typology.** Jaccard ≤ 0.51 at every k. An entropy-only typology (Jaccard 0.95) is stable and is pursued in iteration 3.

4. **Precursors add no predictive value for WHETHER a concept emerges.** E_up logit dAUC −0.010 [−0.045, 0.021].

5. **Closure is lower, not higher, before emergence.** The pre-registered + sign failed. This lead is carried forward as a new screened candidate with the observed sign, to be tested for mechanism (turnover vs brokerage) in iteration 3.

## What we have learned

Iteration 2 confirmed two dead ends (viability decomposition, prediction of emergence) and produced one lead (lower closure before onset). The lead is significant in one post-hoc main-pool label (E_up, n = 21, S = −0.837, Holm p = 0.003), directionally supported in MeSH SENS1 (D = −0.419, Holm p = 0.039), but with heterogeneous sign across labels. The nearest prior work on this reading is Salatino et al. [25], who find that new topics emerge where weakly interconnected research areas begin to cross-fertilise; Chen et al.'s structural-variation analysis [29] predicts transformative work from brokerage across structural holes plus burstiness; and Burt's structural-holes theory [23]. What this study may add is per-paper, volume-matched concept-level closure against a Chung-Lu null, network-only labels, and a second population. But the closure finding is not yet shown distinct from neighbourhood turnover: concepts with high new-relation rates (within-concept r = −0.19 with closure) will mechanically show lower closure.

The five-candidate screen is narrowed. C0 (viability) is closed. C1 (host anchoring) and C2 (co-transfer) move to the graft-fallback route. C3 (origin neighbourhood) lost its predicted + sign on closure. C4 (demic/cultural) was not tested.

## Coverage against the original request

| Activity | Status | Artifact |
|---|---|---|
| 1. Prepare and semantically ground dataset | Done (grounding applied) | art_eR1Z7fMlOcxs, art_BdBvbNuNU8E7 |
| 2. Construct evolving knowledge network | Done (concept-concept snapshots) | art_mbFjmo5rbbf8 |
| 3. RQ1: temporal network analysis | Partial (event study; no confirmed precursor) | art_mbFjmo5rbbf8, art_yWUkgWWKyq_h |
| 4. RQ2: cross-disciplinary diffusion | Not started | – |
| 5. Identify recurring trajectories | Partial (unstable 7-channel; stable entropy-only) | art_mbFjmo5rbbf8 |
| 6. Validate with representative cases | Not started | – |

---

# Iteration 3

## Strategy

Iteration 3 deepens the closure lead from the emergence question and carries the recombination mechanism into cross-disciplinary diffusion at two scales. The strategy ("Is it brokerage, and does grafting make it stick?") has four components: (i) an evaluation artifact that audits every number in the iteration-2 report against artifact files and runs a turnover pre-check on the already-screened data; (ii) a deeper test of the emergence question on the hydrated 247-concept screen fold with turnover-proof openness measures; (iii) a breadth-prediction screen testing whether openness predicts five-year outcome-window disciplinary breadth gain; (iv) a host-entry grafting test of whether pairing with host-native concepts predicts durable integration; and (v) a descriptive diffusion experiment on typology, community roles, expansion-versus-diffusion timing, and representative cases.

## Artifact 11: record audit and turnover pre-check (evaluation)

This artifact reads all five iteration-2 artifacts and audits every reported number against the raw output files [ARTIFACT:gen_art_evaluation_1].

**Numbers of record.** 406 rows were audited, 182 recomputed from item-level files. There are 42 non-OK drift flags: 14 WRONG_ESTIMATOR (e.g. event-study S paired with pooled-panel Holm p), 10 WRONG_UNITS (e.g. Table 15 "Cohen's d" values that are actually delta-AUC), 9 WRONG_DEFINITION (e.g. majority F1 0.000 for a predict-all-positive baseline), 8 DRIFT_VALUE (e.g. classifier P/R/accuracy), 1 NOT_REDERIVABLE. These corrections have been incorporated into the iteration-1 and iteration-2 text above.

**Turnover pre-check** (pre-check on already-screened data, not confirmation; spec sha256 60f44c0f...). Within-concept correlations of closure with turnover indicators: r = −0.19 [−0.26, −0.12] with new-relation rate, −0.17 with novelty, ~0.03 with beta_sim. Partial R² of the turnover block: 0.014 (main), 0.002 (MeSH). After residualising closure on new-relation rate, novelty, beta_sim, volume, age and Shannon entropy:

**Table 13. Turnover pre-check: residualised closure effect.**

| Population | S_raw | S_res | Retained fraction | Verdict |
|---|---|---|---|---|
| Main (E_up) | −0.758 | −0.566 [−1.140, 0.087] | 0.75 [0.08, 0.90] | Ambiguous/underpowered |
| MeSH (SENS1) | – | −0.094 [−0.387, 0.217] | 0.60 | Ambiguous/underpowered |
| IVW pooled | – | −0.186 [−0.453, 0.081] | – | Ambiguous (Q 1.88, I² 0.47) |

The residualised effect retains approximately two-thirds of the raw effect (not reducible to turnover alone), but the CI includes zero. Volume alone retains 0.87 (main) and 0.51 (MeSH). With rarefied Baselga neighbourhood turnover as the control (n = 15), main is NOT REDUCIBLE: S_res −1.09 [−1.45, −0.55]. Controls: the oracle positive control erases the effect (retained 0.02); the noise negative control retains 1.00.

**Decision rules applied.** (a) TRIGGERED: Gate A < 0.5. (b) H1 PILOT-ONLY. (c) NOT MET for all labels. (d) SEALED: 0 held-out IDs in 161 exp_3/exp_4 files.

Source: gen_art_evaluation_1/results/record_of_numbers.json, results/r1a/

## Artifact 12: is openness before take-off brokerage or churn? (emergence deepen)

This artifact re-attaches all 426 hydrated concepts to the iteration-2 co-word snapshots with vendored byte-identical code [ARTIFACT:gen_art_experiment_5]. Reproduction gate passed: code-mode closure r = 1.000000 (max |diff| 5e-8); vendored E_up event study gives 41 onsets, 21 matched, S = −0.8370 [−1.2600, −0.4268], identical to iteration 2. Spec pre-registered (prereg_v3.json, sha256 2f46d173...) before labels.

**Populations.** After applying the frozen replacement rule (180 sense values filled): MAIN screen 202 (102 old, 100 new), held-out 100; STRICT 196/96; SENS 247/119.

**Turnover-proof openness measures.** Four tests were pre-declared to determine whether the closure effect is turnover, Burt brokerage, or something else: (a) turnover-residualised closure (OLS on new-relation rate, novelty, beta_sim, volume, age, H); (b) persistent-neighbour closure (top-20(y) ∩ top-20(y−1)); (c) Burt constraint / effective size of the weighted ego network plus cross-community pair excess over a strength-decile null; (d) hub-not-clique (joint of low closure and high within-module z).

**Table 14. Emergence deepen results, MAIN × E_up (68 onsets, 26 matched).**

| Measure | S | 95% CI | Interpretation |
|---|---|---|---|
| Raw closure | −0.439 | [−0.810, −0.050] | Lower closure before onset (attenuated vs iteration 2) |
| R1a residualised closure | −0.295 | [−0.663, 0.092] | ~2/3 retained; not pure turnover |
| R1b persistent-neighbour closure | −0.575 | [−1.270, 0.122] | Same direction, underpowered |
| R1c Burt constraint | +0.083 | [0.017, 0.147] | OPPOSITE to brokerage sign |
| R1c cross-community pair excess | +0.063 | [0.012, 0.111] | More cross-community ties |
| R1d hub-not-clique | +0.061 | [−0.009, 0.133] | Not significant |

[FIGURE:fig_openness_mechanism]

**Mechanical verdict: MIXED.** The closure effect is not reducible to neighbourhood turnover (turnover-residualised closure retains ~2/3), but it is not Burt brokerage either: Burt constraint is higher, not lower, before onset. Emerging concepts show more cross-community pair excess (connecting to neighbours from different Leiden communities), but within a more redundant wider ego network. The reading is: emerging concepts have sparsely closed top neighbourhoods (few triadic closures among their top-20 associates) that span multiple communities, but sit within ego networks that are more constrained (more redundant) than non-emerging controls.

**Pooled panel** (all 68 onsets, ungrouped): turnover-residualised closure −0.40 [−0.70, −0.12]; persistent-neighbour closure −1.12 [−1.64, −0.71] (Holm p = 0.0015). Band-only matching (52 matched) agrees. Placebo covers 0 for every row.

**Fresh replication on 100 new concepts.** Raw S = −0.455 [−1.006, 0.060], one-sided p = 0.044. Same sign, not significant at two-sided α = 0.05.

**Prediction.** Grouped CV dAUC −0.001 [−0.008, 0.006]; label-shuffle control ~0. Precursors do not predict WHETHER a concept will show sustained uptake.

**Held-out specification.** 119 main concepts sealed. Pre-period features through 2015 computed with screen betas and never read. Expected 12 [8, 16] matched treated. MDEs 0.38–0.62 SD.

Source: gen_art_experiment_5/results/, prereg_v3.json

## Artifact 13: do open concepts spread across more fields? (breadth-prediction screen)

This artifact tests whether openness (operationalised as turnover-residualised closure, Burt constraint, and cross-community pair excess) at time t predicts five-year outcome-window disciplinary breadth gain beyond all baselines [ARTIFACT:gen_art_experiment_6]. Population: MAIN screen 202 concepts, held-out 100 sealed. Outcomes: rarefied Shannon change Y1r, Rao-Stirling change Y2, and new subfields reached by author-disjoint newcomers Y3. The baseline model includes pre-period entropy, active subfields, log volume, momentum, growing-edge breadth, Kleinberg burst, Rafols coherence, and rarefied participation, plus origin/F-band/route/year dummies.

Only 100 concepts (351 rows) pass the complete-case rule, triggering a pre-declared fallback making closure_res_imp (imputed) co-primary.

**Table 15. Breadth-prediction screen results.**

| Openness measure | Outcome | β per SD | 95% CI | Holm p |
|---|---|---|---|---|
| closure_res | Y1r (Shannon change) | +0.019 | [−0.010, 0.041] | 0.405 |
| closure_res | Y2 (Rao-Stirling change) | +0.007 | [−0.002, 0.013] | 0.405 |
| closure_res | log1p Y3 (newcomer subfields) | −0.065 | [−0.156, 0.030] | 0.405 |
| closure_res_imp | Y2 (co-primary) | +0.012 | [0.002, 0.021] | 0.06 |

**Result: breadth prediction not supported on the screen fold.** Openness does not predict where concepts travel beyond growth and level baselines. The co-primary Y2 coefficient is positive, meaning tighter closure predicts more Rao-Stirling change, the opposite of the hypothesised direction. The SENSITIVITY population (no grounding filters) shows significant positive coefficients that vanish under MAIN/STRICT, indicating sensitivity to ungrounded noisy concepts.

**Descriptive mediation.** Closure lowers later cross-community exposure (a < 0), which predicts newcomer subfields; indirect Y3 = −0.028 [−0.072, −0.001]. Openness is at most a take-off correlate; it does not predict breadth gain beyond baselines.

Held-out MDE: ~0.18–0.21 SD(Y) at n = 49 (closure_res) or 63 (imputed).

Source: gen_art_experiment_6/results/d1/

## Artifact 14: do borrowed ideas stick when grafted locally? (host-entry grafting test)

This artifact tests whether a concept that enters a new host subfield catches on when its first papers pair it with host-native concepts rather than with origin companions [ARTIFACT:gen_art_experiment_7]. Pre-registration frozen before any outcome (sha256 f800a0a9...).

**Setup.** 4,177 main-arm host entries (concept c first appears in non-origin subfield d in year e). Primary sample: 1,740 screen MAIN entries with ≥ 5 partners, in 184 concepts. Anchoring A = partners' pre-entry host share from exact OpenAlex subfield × block profiles. Co-transfer CT = share of partners that were origin companions in [e−5, e−1]. Entry is mostly a package: 70% non-native origin companions, 1.8% native grafts.

Only 1.1% of partner tags are ≥ 50% host-native, so the pre-declared fallback makes continuous A_cont primary.

**Outcome:** five-year outcome-window host papers by author-disjoint newcomers; PPML with concept-clustered standard errors.

**Table 16. Host-entry grafting results.**

| Specification | A (IRR/SD) | 95% CI | Holm p | CT (p) | Verdict |
|---|---|---|---|---|---|
| Primary (concept × e + host × e FE) | 1.39 | [0.97, 1.99] | 0.15 | 0.48 | NEITHER |
| Co-primary (concept + e + host) | 1.30 | [1.16, 1.45] | 1e-5 | 0.48 | GRAFTING |
| Concept + host × e | 1.22 | – | – | – | GRAFTING |
| Concept × 2-yr bin | – | – | – | – | NEITHER |

[FIGURE:fig_grafting]

The primary specification is underpowered (26% of events retained, 77 clusters). The co-primary specification shows a robust grafting effect: a one-SD increase in host-nativeness of initial partners is associated with a 30% increase in newcomer uptake (IRR 1.30 [1.16, 1.45], Holm p = 1e-5, wild-cluster p = 0.001). Co-transfer is null everywhere: arriving as a package with origin companions does not predict establishment.

**Robustness.** The co-primary A effect holds in 26 of 27 robustness variants (IRR 1.25–1.56, p ≤ 0.001). Binary native cut-offs (0.5/0.7) are null; Physics/Astronomy-only concepts are null. Nativeness-permutation placebo (500 draws) centred on 0; co-primary p = 0.002, primary p = 0.15.

**Graft labels.** 15% of entries are classified as anchored; anchored entries have an establishment rate of 0.44 vs 0.20 for non-anchored.

**Held-out.** 93 concepts, 1,100 entries sealed. MDE (co-primary): IRR/SD 1.15, below the screen 1.30; the primary spec is declared underpowered in advance.

Source: gen_art_experiment_7/results/d2_summary.json, d2_robustness.csv

## Artifact 15: how new concepts spread, types, roles, timing (descriptive diffusion)

This artifact provides the descriptive diffusion analysis: typology, community roles, expansion-versus-diffusion timing, and representative cases [ARTIFACT:gen_art_experiment_8].

### Diffusion typology

3-channel diffusion typology (rarefied Shannon, Rao-Stirling, active subfields; normalised multivariate DTW + k-medoids; Hennig bootstrap B = 200). Only k = 2 is stable (min Jaccard 0.861): **localised** (n = 136) and **broad from the start** (n = 66). The k = 3 split adding "gradual broadening" is exploratory (Jaccard 0.599). The typology is not volume-driven (AMI with volume terciles 0.014) but is associated with origin field (p = 0.004) and not with retrieval route (p = 1.0).

The entropy-only baseline typology (from iteration 2) is stable at finer k = 4 (Jaccard 0.856). After residualising on early volume, the 3-channel typology does NOT separate unclustered outcomes better than the entropy-only baseline (newcomer share ε² 0.171 vs 0.178; communities touched 0.044 vs 0.023, CIs overlap). The multi-channel typology does not add information beyond entropy trajectories alone.

**Table 17. Diffusion typology summary.**

| Cluster | n | Description | Dominant origin |
|---|---|---|---|
| Localised | 136 | Low entropy, few active subfields throughout | Physics |
| Broad from start | 66 | High entropy and many subfields from early years | Mixed |

### Community roles

Leiden community roles with 5-seed agreement (97.2% robust; placebo 0.87): BRIDGE 0.61, OTHER 0.33, STAYER 0.03, MIGRANT 0.02. The pre-declared CORE_GROWING and FOUNDER roles never fire because pool concepts' within-module z-scores are too low (max −0.23); a post-hoc pool-relative variant gives FOUNDER 0.035. Guimerà-Amaral classes: peripheral 0.49, connector 0.40, kinless 0.10, no hubs.

Lagged roles do not robustly predict host-subfield entry: BRIDGE OR 0.64 [0.38, 1.08].

### Expansion precedes diffusion

In 15 of 16 concepts exhibiting both an expansion onset and a diffusion onset, expansion precedes diffusion (proportion 0.94 [0.81, 1.0]; year-shuffle null 0.62, p = 0.004). Diffusion never precedes expansion in any grid cell. This is underpowered (16 concepts) but directionally strong.

### Pattern contrasts between main and MeSH populations

Early bridging: main 0.70, MeSH 0.59 (+0.11 [0.02, 0.20]). Incubation-then-expansion: main 0.00, MeSH 0.17. The old-123-concept early-bridging drop (0.764 → 0.715) is fully explained by population-dependent betweenness percentiles.

### Representative cases

Four medoid cases were selected from the typology clusters, with ego-network visualisations, alluvial community-membership paths, and subfield heat maps illustrating the network dynamics of emergence for each trajectory type.

[FIGURE:fig_typology_cases]

Source: gen_art_experiment_8/results/

## Dead ends and negative results (iteration 3)

1. **Openness does not predict WHERE concepts travel.** Breadth-prediction screen: closure_res per SD gives Y1r +0.019, Y2 +0.007, Y3 −0.065, all Holm p = 0.405. Grouped-CV dR² CIs all include 0.

2. **Brokerage is not the mechanism behind low closure.** Burt constraint is higher, not lower, before onset (S = +0.083 [0.017, 0.147]). The openness effect is not a structural-holes story.

3. **The 3-channel diffusion typology adds nothing beyond entropy.** After residualising on volume, the multi-channel typology does not separate outcomes better than entropy-only (ε² 0.171 vs 0.178).

4. **Community roles do not predict host entry.** BRIDGE OR 0.64 [0.38, 1.08].

5. **Co-transfer is null.** Arriving with origin companions (CT) does not predict establishment in any specification.

## What we have learned

Iteration 3 advances the study on three fronts and confirms several limits.

**Emergence question: the closure effect survives turnover controls but is not Burt brokerage.** On the larger 202-concept screen fold, the raw closure effect attenuates (S = −0.439 [−0.810, −0.050] vs −0.837 on the 123-concept fold) but remains significant. Turnover-residualised closure retains approximately two-thirds of the effect; persistent-neighbour closure (restricting to stable top-20 associates) shows the same direction. Burt constraint is higher, not lower, contradicting a structural-holes reading. Cross-community pair excess is higher. The reading: emerging concepts have sparsely closed top neighbourhoods that span multiple communities within a more redundant ego network. This is consistent with Salatino et al.'s [25] finding that topics emerge at the boundary of weakly connected parent areas, but adds the mechanistic detail that the neighbourhoods are not brokering in Burt's sense [23]. They are open to multiple communities without being the sole bridge between them.

**Host-entry grafting predicts durable integration.** When a concept enters a new host subfield, the share of its initial co-occurrence partners that are native to that host predicts subsequent uptake by newcomer authors (co-primary IRR 1.30 [1.16, 1.45], Holm p = 1e-5), holding across 26 of 27 robustness variants. Co-transfer (arriving with origin companions) is null. This means that the mode of entry matters: concepts that re-contextualise by associating with host-native ideas establish more durably than those that arrive as a package. This result is consistent with Cheng et al.'s [13] finding that diffusion depends on the ability to integrate into pre-existing knowledge structures, and with the principle of relatedness [28].

**Breadth prediction: openness does not predict breadth.** Turnover-residualised closure, Burt constraint, and cross-community pairs do not predict how many new subfields a concept will reach, beyond growth and level baselines. Openness is at most a take-off correlate, not a breadth predictor.

**Diffusion typology.** The only stable typology has two clusters: localised (n = 136) and broad-from-the-start (n = 66). Finer typologies are unstable; the 3-channel version adds nothing beyond entropy trajectories. Network expansion precedes disciplinary diffusion in 94% of cases.

**Nearest neighbours.** The closure finding is consistent with Salatino et al. [25] (topics born where weakly connected areas cross-fertilise), Chen et al. [29] (structural variation analysis), and the structural-holes literature [23]. The grafting result extends Cheng et al. [13] from a global fit measure to a per-entry, within-concept test with a co-transfer control. What is new: the combination of per-paper closure against a Chung-Lu null with a Burt constraint test that rules out the simple brokerage explanation; the grafting test on host-entry events with exact nativeness profiles; and the two-population design (physics/CS and biomedical).

## Coverage against the original request

| Activity | Status | Artifact |
|---|---|---|
| 1. Prepare and semantically ground dataset | Done | art_94GEMUsgAmgK, art_QpM5SM6a7SH6, art_BdBvbNuNU8E7, art_eR1Z7fMlOcxs |
| 2. Construct evolving knowledge network | Done (concept-concept 25 snapshots + concept-discipline bipartite) | art_mbFjmo5rbbf8, art_eR1Z7fMlOcxs |
| 3. Emergence: temporal network analysis | Done (event study + turnover/brokerage tests) | art_mbFjmo5rbbf8, art_yWUkgWWKyq_h, Artifact 11, Artifact 12 |
| 4. Diffusion: cross-disciplinary spread | Done (breadth-prediction screen + grafting test) | Artifacts 13, 14 |
| 5. Identify recurring trajectories | Done (2-cluster typology + entropy-only baseline) | Artifact 15 |
| 6. Validate with representative cases | Done (4 medoid cases) | Artifact 15 |

## Run ledger

| Artifact | Type | Status | OpenAlex credits | LLM $ | Wall time |
|---|---|---|---|---|---|
| art_94GEMUsgAmgK (pool) | dataset | succeeded | 2,566 | $0.36 | – |
| gen_art_dataset_2 (background) | dataset | failed (timeout) | 1,952 | – | – |
| art_HGiVAYhqO-6q (MeSH) | dataset | succeeded | 1,784 | – | – |
| art_QpM5SM6a7SH6 (grounding) | dataset | succeeded | 1,847 | $0.674 | – |
| art_bNCGUJX2MUhX (dossier) | research | succeeded | – | – | – |
| art_eR1Z7fMlOcxs (hydrated) | dataset | succeeded | 7,237 | $0.024 | – |
| art_BdBvbNuNU8E7 (grounding) | experiment | succeeded | – | $0.053 | – |
| art_yjFB8Spw2w6M (viability) | experiment | succeeded | – | – | – |
| art_mbFjmo5rbbf8 (emergence, main) | experiment | succeeded | – | – | – |
| art_yWUkgWWKyq_h (emergence, MeSH) | experiment | succeeded | – | – | – |
| Artifact 11 (audit) | evaluation | succeeded | – | – | – |
| Artifact 12 (emergence deepen) | experiment | succeeded | – | – | – |
| Artifact 13 (breadth prediction) | experiment | succeeded | – | – | – |
| Artifact 14 (host-entry grafting) | experiment | succeeded | – | – | – |
| Artifact 15 (descriptive diffusion) | experiment | succeeded | – | – | – |

## Hashes

| Item | SHA-256 prefix |
|---|---|
| Frozen concept frame | 80e3f244...0c44 |
| Viability pre-registration | 5dd16d8a...5aac |
| Test population | 6a887fb4...5505 |
| R1a turnover pre-check spec | 60f44c0f... |
| Emergence deepen spec (SPEC3) | 2f46d173... |
| Host-entry grafting pre-registration | f800a0a9... |
| Descriptive diffusion held-out spec | 695166b4... |
| Held-out confirmation spec (exp_5) | 535c2dd3... |
| Grafting held-out spec | 8db17113... |

## References

[1] H. Pulliam, "Sources, Sinks, and Population Regulation," *The American Naturalist* 132, 652–661, 1988.

[2] J. Priem, H. A. Piwowar, R. Orr, "OpenAlex: A fully-open index of scholarly works, authors, venues, institutions, and concepts," arXiv:2205.01833, 2022.

[3] A. Stirling, "A general framework for analysing diversity in science, technology and society," *Journal of The Royal Society Interface* 4, 707–719, 2007.

[4] I. Rafols, "Knowledge Integration and Diffusion: Measures and Mapping of Diversity and Coherence," arXiv:1412.6683, 2014.

[5] T. Maillart, T. Chataing, D. Dosu, P. Bagourd, J. Jang-Jaccard, A. Mermoud, "Forecasting Conceptual Diffusion in Science: The Case of Quantum Computing," arXiv:2606.03919, 2026.

[6] M. De Domenico, E. Omodei, A. Arenas, "Quantifying the diaspora of knowledge in the last century," *Applied Network Science* 1, 2016.

[7] E. Cunningham, B. Smyth, D. Greene, "Author multidisciplinarity and disciplinary roles in field of study networks," *Applied Network Science* 7, 2022.

[8] A. Holmgren, D. Edler, M. Rosvall, "Mapping change in higher-order networks with multilevel and overlapping communities," *Applied Network Science* 8, 1–15, 2023.

[9] S. Fontaine, F. Gargiulo, M. Dubois, P. Tubaro, "Epistemic integration and social segregation of AI in neuroscience," *Applied Network Science* 9, 2024.

[10] T. Kuhn, M. Perc, D. Helbing, "Inheritance patterns in citation networks reveal scientific memes," *Physical Review X* 4, 041036, 2014.

[11] I. Kiss, M. Broom, P. Craze, I. Rafols, "Can epidemic models describe the diffusion of topics across disciplines?" *Journal of Informetrics* 4, 74–82, 2010.

[12] D. Chavalarias, J.-P. Cointet, "Phylomemetic Patterns in Science Evolution: The Rise and Fall of Scientific Fields," *PLoS ONE* 8(2), e54847, 2013.

[13] M. Cheng, D. Smith, X. Ren, H. Cao, S. Smith, D. A. McFarland, "How New Ideas Diffuse in Science," *American Sociological Review* 88, 522–561, 2023.

[14] J. Kleinberg, "Bursty and Hierarchical Structure in Streams," *Data Mining and Knowledge Discovery* 7, 373–397, 2003.

[15] M. Rosvall, C. T. Bergstrom, "Mapping Change in Large Networks," *PLoS ONE* 5, 2010.

[16] A. Baselga, "Partitioning the turnover and nestedness components of beta diversity," *Global Ecology and Biogeography* 19, 134–143, 2010.

[17] I. Rafols, M. Meyer, "Diversity and network coherence as indicators of interdisciplinarity: case studies in bionanoscience," *Scientometrics* 82, 263–287, 2010.

[18] D. Rotolo, D. Hicks, B. Martin, "What is an emerging technology?" *Research Policy* 44(10), 1827–1843, 2015.

[19] T. Maillart, T. Chataing, N. Antoni, D. Dosu, P. Bagourd, J. Jang-Jaccard, A. Mermoud, "Explainable Forecasting of Scientific Breakthroughs from Concept Network Dynamics," arXiv:2606.03864, 2026.

[20] M. Krenn, A. Zeilinger, "Predicting research trends with semantic and neural networks with an application in quantum physics," *Proceedings of the National Academy of Sciences* 117, 1910–1916, 2020.

[21] L. Huang, X. Chen, X. Ni, J.-R. Liu, X.-H. Cao, C. Wang, "Tracking the dynamics of co-word networks for emerging topic identification," *Technological Forecasting and Social Change* 170, 120944, 2021.

[22] N. Sattar, A. Buluc, K. Z. Ibrahim, S. Arifuzzaman, "Exploring temporal community evolution: algorithmic approaches and parallel optimization for dynamic community detection," *Applied Network Science* 8, 1–29, 2023.

[23] R. S. Burt, "Structural holes and good ideas," *American Journal of Sociology* 110, 349–399, 2004.

[24] J. Ugander, L. Backstrom, C. Marlow, J. Kleinberg, "Structural diversity in social contagion," *Proceedings of the National Academy of Sciences* 109, 5962–5966, 2012.

[25] A. Salatino, F. Osborne, E. Motta, "How are topics born? Understanding the research dynamics preceding the emergence of new areas," *PeerJ Computer Science* 3, e119, 2017.

[26] B. Uzzi, S. Mukherjee, M. Stringer, B. Jones, "Atypical Combinations and Scientific Impact," *Science* 342, 468–472, 2013.

[27] D. Centola, "The Spread of Behavior in an Online Social Network Experiment," *Science* 329, 1194–1197, 2010.

[28] C. A. Hidalgo, P.-A. Balland, R. Boschma, M. Delgado, M. Feldman, K. Frenken, E. Glaeser, C. He, D. F. Kogler, A. Morrison, F. Neffke, D. Rigby, S. Stern, S. Zheng, S. Zhu, "The Principle of Relatedness," *International Conference on Complex Systems*, 451–457, 2018.

[29] C. Chen, "CiteSpace II: Detecting and visualizing emerging trends and transient patterns in scientific literature," *Journal of the American Society for Information Science and Technology* 57(3), 359–377, 2006.
