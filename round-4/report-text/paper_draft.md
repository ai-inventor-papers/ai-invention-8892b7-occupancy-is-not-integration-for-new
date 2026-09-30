# Open neighbourhoods precede concept spread: structural antecedents and cross-disciplinary diffusion of emerging scientific concepts

This report documents an investigation of how emerging scientific concepts can be identified and characterised through evolving knowledge networks, and through which structural pathways they spread across disciplinary boundaries. The study builds on an OpenAlex-based scholarly dataset of 426 semantically grounded concepts with 462,812 works, constructs yearly co-occurrence and concept-discipline networks, and tests whether structural indicators provide early signals of emergence and cross-disciplinary integration.

Two research questions structure the work. RQ1 asks which temporal and structural patterns in an evolving, semantically grounded scientific knowledge graph characterise the emergence of scientific concepts. RQ2 asks how emerging scientific concepts diffuse across disciplinary communities over time, and which temporal network patterns distinguish locally concentrated concepts from concepts that become broadly integrated into the scientific knowledge network.

The study began with a source-sink viability hypothesis adapted from population ecology [1], asking whether a concept's presence in a subfield is self-sustaining or import-dependent. That hypothesis was blocked by insufficient citation-layer density (Gate A failure: only 17.3% of concept-subfield-year edges meet the within-host tracing threshold). The investigation then followed the pre-registered fallback, yielding two main findings. First, emerging concepts have lower persistent-neighbour triadic closure than matched controls before onset (held-out S = −1.07, Holm p = 0.015), though the general closure deficit did not survive held-out confirmation on the primary operationalisation (RQ1). Second, when a concept enters a new host subfield, the share of its initial co-occurrence partners that are native to that host predicts subsequent uptake by newcomer authors (held-out co-primary IRR/SD 1.19 [1.06, 1.33], p = 0.004; MeSH replication IRR/SD 1.23 [1.12, 1.36], Holm p < 0.001), while the share of origin companions does not (RQ2). A data-derived diffusion typology separates concepts into localised and broad-from-the-start trajectories, and network expansion precedes disciplinary diffusion in 25 of 26 pooled main-arm concepts exhibiting both transitions.

The target venue is Applied Network Science, whose published work on knowledge diaspora [6], disciplinary roles in field-of-study networks [7], alluvial community change [8], and the epistemic integration of AI in neuroscience [9] provides the closest comparison base.

---

# Iteration 1

## Strategy

The first iteration was devoted to three preparatory tasks: (a) assembling a prior-art and pre-registration dossier grading each candidate mechanism's novelty and feasibility, (b) building the concept pool and its associated OpenAlex work corpus, and (c) constructing the semantic grounding infrastructure (concept detection, labelling, variant merging) and a held-out MeSH confirmation population. No experiment or evaluation was executed. Every artifact in this iteration is either a dataset or a research dossier. The rationale was to fix all operational definitions, sample the data, and verify the citation-layer gate (Gate A) before committing compute to network construction and statistical modelling.

The pre-registration dossier ranks five candidate mechanisms by novelty margin against the nearest prior work. Host anchoring (the share of a concept's new co-occurrence edges in a host subfield that attach to host-native concepts) was ranked highest at medium-to-high novelty; toolkit co-transfer (the fraction of a concept's origin companions that co-appear in host papers) was ranked high on measurement novelty but coupled to host anchoring; citation-lineage source-sink viability was ranked medium, with Kuhn et al.'s meme propagation score [10], Kiss et al.'s epidemic diffusion model [11], De Domenico et al.'s author-flow source-sink indices [6], and Maillart et al.'s endogenous-exogenous decomposition [5] as the nearest antecedents. Origin-neighbourhood structure (the participation coefficient and clustering topology of the concept in its birth subfield) was ranked low-to-medium because structural diversity and community spread are well studied [12], and the demic-versus-cultural adoption channel was ranked medium but with the weakest feasibility due to author-disambiguation biases [ARTIFACT:art_bNCGUJX2MUhX].

A pre-registered screen was fixed before any data were inspected. The unit of analysis is a concept c in non-origin subfield d at focal year t (2010-2014), with at least 10 d-papers in W1 = [t−5, t]. The primary measure is out-of-sample ROC-AUC for establishment in W2 = [t+1, t+5], where establishment means at least 5 W2 d-papers by author-disjoint newcomers and presence in at least 3 of the 5 W2 years. The BASE model includes W1 edge volume, momentum, concept age, subfield-year size, concept total volume, concept entropy, subfield count, growing-edge breadth, Rafols integration, relatedness density and Maillart-style features. Each candidate adds only its own pre-registered scores. A candidate survives if its delta-AUC over BASE has a concept-bootstrap (1,000 reps) 95% CI lower bound above 0, its point gain is at least 0.01, and the coefficient sign matches its prediction. The candidate with the largest lower CI bound is the winner.

## Artifact 1: concept pool and OpenAlex work corpus

The concept pool was built in an outcome-blind frame. The sample was frozen and hashed (SHA-256 80e3f244...0c44) before any post-appearance-window data were inspected [ARTIFACT:art_94GEMUsgAmgK]. The pool comprises 206 concepts, of which 184 are main emerging concepts (first appearance year F in 2005-2016, with 20-300 papers in the window F to F+2 and no more than 8,000 total works through 2024) and 22 stationary reference concepts (at least 5 hits in every year 1998-2004 with a 7-year sum of 70-700). The 184 main concepts are split by a SHA-1 hash into a screen fold of 123 and a held-out concept fold of 61; focal-year tags are separate (screen 2010-2014, held-out 2016-2018).

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
| 2005-2007 | 38 |
| 2008-2011 | 76 |
| 2012-2016 | 70 |
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

The recall audit, comparing counts derived from OpenAlex against independent Semantic Scholar counts for 30 concepts, gives a median count ratio of 0.84 (IQR 0.79-0.89) and a Spearman rank correlation of 0.976. For the 160 main concepts discovered through Semantic Scholar, this comparison measures mapping and verification loss rather than true recall against an independent source. Recall against OpenAlex's own index is therefore unmeasured for approximately 87% of the pool.

### Denominators and venue habitat

Totals by subfield and year cover 25,195 rows (all 252 OpenAlex subfields across 25 years in four counting variants). A venue-habitat file assigns 15,261 venues to their dominant subfield. [Correction, iteration 2: the habitat was described as "pre-period publication shares" and "citation-independent". It was computed from each source's all-years OpenAlex topic counts in the 2026 snapshot. Those topic counts come from the same citation-reading topic classifier whose temporal label leakage the dossier flagged. The habitat is therefore neither pre-period nor citation-independent. An ASJC journal-level habitat was built in iteration 2 as a replacement, though its coverage is only 12.1% of concept-work links.]

## Artifact 2: whole-science background sample

A design-weighted background sample of 259,716 OpenAlex works from 1,260 strata (150 per field × year, weights summing to 149,116,575) was built to supply co-occurrence network snapshots and calibrate host-nativeness profiles [ARTIFACT:art_eR1Z7fMlOcxs]. It delivered 6,325 exact subfield × year totals and 400 exact concept × block subfield profiles for 100 calibration concepts at a cost of $0.1952 in OpenAlex credits.

The key finding of this artifact is negative: sample-based per-concept subfield profiles are unreliable for determining host-nativeness. In the calibration table, the median total-variation distance between sample and exact profiles is 0.41-0.79 by frequency decile, and top-subfield agreement is only 0.28-0.65. This means host-nativeness (the input to candidates C1 and C2) and the concept-concept background network cannot be computed reliably from this sample alone, and require paid exact profiles. About 12% of the weighted frame carries the default low-confidence topic T14423, and concept ancestors are no longer served by the API.

The worker timed out after writing all outputs (no new JSONL records for 2,096 seconds), so its status is "failed" while its data are usable.

Source: gen_art_dataset_2/data_card.md, calibration_by_decile.csv

## Artifact 3: held-out MeSH confirmation population

A separate biomedical confirmation arm was built from new MeSH descriptors (DateEstablished 2006-2016, widened to 2004-2005 and 2017-2018) [ARTIFACT:art_HGiVAYhqO-6q]. Starting from 28,472 descriptors, the pipeline selects 5,201 topical descriptors, retains 3,430 after the provenance filter (dropping parenthetical-prior-year, promoted-term, and renamed descriptors), narrows to 283 passing the PubMed novelty pre-screen and early-volume rule, and adds widening-pool candidates. After the final rule, 191 concepts survive: 99 core 2006-2016, 14 from the 2004-2005 widening, and 78 from the 2017-2018 widening.

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

Caveats: only approximately 25% of new MeSH descriptors are genuinely new concepts (the remainder are reclassifications or splits), making MeSH a weak ground truth. Only 13 of 191 have their full non-PubMed works paged; the remaining 178 have PubMed-indexed works only, which biases their concept-discipline edges toward biomedical subfields and makes them not directly comparable to the main corpus for cross-disciplinary breadth until retrieval is complete. The route calibration (union vs plain OpenAlex search, median ratio 0.8598, range 0.54-0.91 over 10 concepts) and a 60-record provenance spot check (0 decision errors) provide the arm's validity numbers.

Source: gen_art_dataset_3/selection_flow.json, provenance.md, route_calibration.json

## Artifact 4: semantic grounding and labelling infrastructure

The semantic grounding artifact provides the infrastructure for detecting, labelling, and merging concept mentions [ARTIFACT:art_QpM5SM6a7SH6]. It comprises seven datasets.

**Stratified corpus.** 93,600 English OpenAlex articles and reviews with abstracts, sampled at 150 per field × year stratum across 26 OpenAlex fields (54,600 main-period 2003-2016 and 39,000 pre-screen 1995-2004).

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

3. **Survivorship-free phrase pool yield.** 1 of 150 target strict-eligible anchored concepts. The artifact's own diagnosis is that phrases seen once in a ~0.1% sample are overwhelmingly compositional or pre-existing; lowering the early-volume bound multiplies yield 6-11× per the yield curve.

4. **Labelling quality.** Silver labels only (no human check). Model A's bias is moderate; model B over-labels CONCEPT (1,333 of 1,491 items vs A's 882).

## What we have learned so far

Iteration 1 established the data foundation and pre-registration. The concept pool of 184 main emerging concepts and 22 reference concepts, with 214,798 verified concept-to-work links and 208,374 unique works, passes the citation-layer gate on the lenient (any-parent) definition but has not been tested at the within-host edge level required for viability estimation. The MeSH held-out population of 191 biomedical concepts provides a secondary check arm, though with caveats on completeness and ground-truth quality. No experiment was executed; no quantitative result about the hypothesis exists.

## Coverage against the original request

| Activity | Status | Artifact |
|---|---|---|
| 1. Prepare and semantically ground dataset | Partial | art_94GEMUsgAmgK, art_QpM5SM6a7SH6 |
| 2. Construct evolving knowledge network | Not started | - |
| 3. RQ1: temporal network analysis | Not started | - |
| 4. RQ2: cross-disciplinary diffusion | Not started | - |
| 5. Identify recurring trajectories | Not started | - |
| 6. Validate with representative cases | Not started | - |

---

# Iteration 2

## Strategy

Iteration 2 was a FIX iteration. Five goals were set: (i) complete the hydration and add exact nativeness profiles and a citation-independent venue habitat; (ii) train and evaluate the concept grounding pipeline; (iii) compute Gate A as written (within-host, non-canonical, per W1 year) and estimate viability states with synthetic validation and pre-outcome power; (iv) build the yearly concept-concept co-occurrence network and run the RQ1 event study; (v) replicate the RQ1 event study on the MeSH population.

Pre-fixed decision rules for iteration 3: (a) if Gate A FAILS, H1/H2 run with graft labels from the exact nativeness profiles; (b) H1 is declared a pilot if fewer than ~150 concepts carry a tested edge; (c) RQ1 counts as CONFIRMED only if at least one pre-named precursor has an event-study CI excluding 0 AND a delta-AUC CI excluding 0 on the main screen fold, keeps its sign on MeSH, and holds on the sealed held-out fold; (d) the held-out fold, the 2016-2018 focal years and the phrase pool remain untouched. One design decision was to run one artifact on the OpenAlex key at a time.

## Artifact 6: hydrated corpus, nativeness profiles, and venue habitat

This artifact completes the hydration of the concept pool from 184 to 426 concepts (366 main: screen 247, held-out 119; 60 reference), with 462,812 works and 488,078 verified concept-work links [ARTIFACT:art_eR1Z7fMlOcxs]. The frame SHA-256 hash (80e3f244...0c44) was verified. Retrieval route: A_openalex_native for 46 concepts and B_s2_index (S2-mapped) for 380, driven by hydration timing, not concept properties. Sense-check failures: 45.

**Nativeness profiles.** 5,488 exact OpenAlex primary_topic.subfield × block counts (2000-04, 2005-09, 2010-14, 2015-19) for the top 1,372 legacy-concept nodes by host co-occurrence weight, covering 78.7% of host weight (below the 90% strategy target; 95% would need 7,584 nodes). 2,073 profiles are truncated at top-200 (missing tail median 0.1%, max 1.2%).

**ASJC venue habitat.** 22,970 venues; 2,929 covered (2,892 citation-independent from SCImago/Scopus ASJC categories, 37 from pre-period 2000-04 topic fallback). Coverage: 12.1% of concept-work links. The low coverage is driven by multi-category journals (38.5% of venue c-papers) and arXiv (16.3%).

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

Note: the iteration-2 RQ1 and viability experiments (Artifacts 8-10 below) ran on the iteration-1 184-concept corpus in parallel with the hydration. The 426-concept hydrated corpus was not used until iteration 3.

## Artifact 7: concept grounding pipeline

This artifact trains and evaluates three components: a binary classifier, a variant merger, and a NIL-aware linker [ARTIFACT:art_BdBvbNuNU8E7].

**Classifier.** L2-regularised logistic regression (C = 0.01) on lexical features, outcome-blind termhood features, PCA-64 of MiniLM embeddings, and PCA-64 of SPECTER2 embeddings, trained on 1,200 D2 silver labels.

**Table 8. Classifier performance on test set (n = 300).**

| Metric | Classifier | LLM-A | Majority (predict-all-positive) |
|---|---|---|---|
| F1 | 0.818 | 0.901 | 0.715 |
| AUC | 0.888 | - | - |
| Precision | 0.759 | - | - |
| Recall | 0.886 | - | - |
| Accuracy | 0.780 | - | - |

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

**Gate A FAILS.** Only 17.3% of 724 main-arm host edge-years (97 concepts, |K_d| ≥ 10) have a within-host non-canonical traced share at or above 0.40. The mean within-host traced share is 0.20, median 0.15. On the same 724 edges, the lenient any-parent share is 0.477 (64.2% ≥ 0.40), confirming that the drop from 55.18% to 17.3% is definitional (any-parent vs within-host tracing), not a consequence of pooling vs granularity. The reference-arm host share is 0.13. By year for the main screen (2010-2014), within-host means are 0.20, 0.28, 0.23, 0.19, 0.20.

[FIGURE:fig_gate_a]

**Table 9. Gate A edge-level results.**

| Metric | Within-host | Any-parent (same edges) |
|---|---|---|
| Share ≥ 0.40 | 17.3% | 64.2% |
| Mean traced share | 0.20 | 0.477 |
| Median traced share | 0.15 | - |
| Reference arm host share | 0.13 | - |

Source: gen_art_experiment_2/results/gate_a/gate_a_by_arm_fold_year.csv

Per pre-registered decision rule (a): Gate A 0.1727 < 0.5 triggers the graft fallback. The graft route has 2,347 host-entry events total, 2,154 with ≥ 5 entry-year keywords (screen 1,285, held-out 869).

### Viability states (descriptive only)

Of 779 eligible edges, 169 were tested: SOURCE 63, SINK 26, FADING 7, UNDETERMINED 683 (reason codes: below_nmin 65.6%, no_cohort_parents 12.7%, tested 21.7%). The synthetic FDR is 0.209, exceeding the 0.15 threshold; SOURCE FDR 0.13 (acceptable), SINK FDR 0.40 (unreliable, because import share m absorbs noise citations). The P1 entropy-share decomposition over pooled edges: SOURCE 1.4%, SINK 0.4%, UNDETERMINED 70.4%, ORIGIN 27.6%.

Source: gen_art_experiment_2/results/viability/viability_layer.csv, results/synth/synth_results.json, results/p1/p1_summary.json

### Power before any outcome

Per decision rule (b), H1 is PILOT-ONLY: N_c = 38 at n_min 30; projected 77.5 (66-92) on the hydrated pool. Minimum detectable effects (delta-AUC units): at AUC 0.70, realised MDEs are 0.070 (n_min 5), 0.073 (10), 0.100 (20), 0.134 (30); at AUC 0.80, 0.050, 0.054, 0.092, 0.116. Projected values at n_min 5/10: 0.039/0.042. Gate B FAILS: 0 labelled episodes; approximately 70 concept clusters needed for MDE ≤ 25%.

[Correction: previous Table 15 reported MDEs in "Cohen's d" units (1.22 to 0.36) that do not appear in any artifact output. The artifact's MDEs are delta-AUC values from results/power/h1_mde.json.]

Source: gen_art_experiment_2/results/power/h1_mde.json, decisions.json

## Artifact 9: precursor event study, main pool (RQ1)

This artifact runs the precursor event study on the main pool's screen fold, testing whether volume-normalised structural precursors distinguish emerging from non-emerging concepts before onset [ARTIFACT:art_mbFjmo5rbbf8]. Built 25 yearly 3-year-window co-word snapshots (2000-2024) from the design-weighted background sample (~27,000 nodes, ~84,000 kept edges, association-strength weights, Leiden best-of-5, alluvial IDs).

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
| Closure (log-ratio) | Pooled panel | −0.743 | [−1.06, −0.46] | - |
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
| 4. RQ2: cross-disciplinary diffusion | Not started | - |
| 5. Identify recurring trajectories | Partial (unstable 7-channel; stable entropy-only) | art_mbFjmo5rbbf8 |
| 6. Validate with representative cases | Not started | - |

---

# Iteration 3

## Strategy

Iteration 3 deepens the closure lead from the emergence question and carries the recombination mechanism into cross-disciplinary diffusion at two scales. The strategy ("Is it brokerage, and does grafting make it stick?") has four components: (i) an evaluation artifact that audits every number in the iteration-2 report against artifact files and runs a turnover pre-check on the already-screened data; (ii) a deeper test of the emergence question on the hydrated 247-concept screen fold with turnover-proof openness measures; (iii) a breadth-prediction screen testing whether openness predicts five-year outcome-window disciplinary breadth gain; (iv) a host-entry grafting test of whether pairing with host-native concepts predicts durable integration; and (v) a descriptive diffusion experiment on typology, community roles, expansion-versus-diffusion timing, and representative cases.

## Artifact 11: record audit and turnover pre-check (evaluation)

This artifact reads all five iteration-2 artifacts and audits every reported number against the raw output files [ARTIFACT:art__i2cIye01VnN].

**Numbers of record.** 406 rows were audited, 182 recomputed from item-level files. There are 42 non-OK drift flags: 14 WRONG_ESTIMATOR (e.g. event-study S paired with pooled-panel Holm p), 10 WRONG_UNITS (e.g. Table 15 "Cohen's d" values that are actually delta-AUC), 9 WRONG_DEFINITION (e.g. majority F1 0.000 for a predict-all-positive baseline), 8 DRIFT_VALUE (e.g. classifier P/R/accuracy), 1 NOT_REDERIVABLE. These corrections have been incorporated into the iteration-1 and iteration-2 text above.

**Turnover pre-check** (pre-check on already-screened data, not confirmation; spec sha256 60f44c0f...). Within-concept correlations of closure with turnover indicators: r = −0.19 [−0.26, −0.12] with new-relation rate, −0.17 with novelty, ~0.03 with beta_sim. Partial R² of the turnover block: 0.014 (main), 0.002 (MeSH). After residualising closure on new-relation rate, novelty, beta_sim, volume, age and Shannon entropy:

**Table 13. Turnover pre-check: residualised closure effect.**

| Population | S_raw | S_res | Retained fraction | Verdict |
|---|---|---|---|---|
| Main (E_up) | −0.758 | −0.566 [−1.140, 0.087] | 0.75 [0.08, 0.90] | Ambiguous/underpowered |
| MeSH (SENS1) | - | −0.094 [−0.387, 0.217] | 0.60 | Ambiguous/underpowered |
| IVW pooled | - | −0.186 [−0.453, 0.081] | - | Ambiguous (Q 1.88, I² 0.47) |

The residualised effect retains approximately two-thirds of the raw effect (not reducible to turnover alone), but the CI includes zero. Volume alone retains 0.87 (main) and 0.51 (MeSH). With rarefied Baselga neighbourhood turnover as the control (n = 15), main is NOT REDUCIBLE: S_res −1.09 [−1.45, −0.55]. Controls: the oracle positive control erases the effect (retained 0.02); the noise negative control retains 1.00.

**Decision rules applied.** (a) TRIGGERED: Gate A < 0.5. (b) H1 PILOT-ONLY. (c) NOT MET for all labels. (d) SEALED: 0 held-out IDs in 161 exp_3/exp_4 files.

Source: gen_art_evaluation_1/results/record_of_numbers.json, results/r1a/

## Artifact 12: is openness before take-off brokerage or churn? (emergence deepen)

This artifact re-attaches all 426 hydrated concepts to the iteration-2 co-word snapshots with vendored byte-identical code [ARTIFACT:art_htO_gJuUn6Pr]. Reproduction gate passed: code-mode closure r = 1.000000 (max |diff| 5e-8); vendored E_up event study gives 41 onsets, 21 matched, S = −0.8370 [−1.2600, −0.4268], identical to iteration 2. Spec pre-registered (prereg_v3.json, sha256 2f46d173...) before labels.

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

**Held-out specification.** 119 main concepts sealed. Pre-period features through 2015 computed with screen betas and never read. Expected 12 [8, 16] matched treated. MDEs 0.38-0.62 SD.

Source: gen_art_experiment_5/results/, prereg_v3.json

## Artifact 13: do open concepts spread across more fields? (breadth-prediction screen)

This artifact tests whether openness (operationalised as turnover-residualised closure, Burt constraint, and cross-community pair excess) at time t predicts five-year outcome-window disciplinary breadth gain beyond all baselines [ARTIFACT:art_62TVG6A4f7Iy]. Population: MAIN screen 202 concepts, held-out 100 sealed. Outcomes: rarefied Shannon change Y1r, Rao-Stirling change Y2, and new subfields reached by author-disjoint newcomers Y3. The baseline model includes pre-period entropy, active subfields, log volume, momentum, growing-edge breadth, Kleinberg burst, Rafols coherence, and rarefied participation, plus origin/F-band/route/year dummies.

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

Held-out MDE: ~0.18-0.21 SD(Y) at n = 49 (closure_res) or 63 (imputed).

Source: gen_art_experiment_6/results/d1/

## Artifact 14: do borrowed ideas stick when grafted locally? (host-entry grafting test)

This artifact tests whether a concept that enters a new host subfield catches on when its first papers pair it with host-native concepts rather than with origin companions [ARTIFACT:art_2Cd2JJypeGuA]. Pre-registration frozen before any outcome (sha256 f800a0a9...).

**Setup.** 4,177 main-arm host entries (concept c first appears in non-origin subfield d in year e). Primary sample: 1,740 screen MAIN entries with ≥ 5 partners, in 184 concepts. Anchoring A = partners' pre-entry host share from exact OpenAlex subfield × block profiles. Co-transfer CT = share of partners that were origin companions in [e−5, e−1]. Entry is mostly a package: 70% non-native origin companions, 1.8% native grafts.

Only 1.1% of partner tags are ≥ 50% host-native, so the pre-declared fallback makes continuous A_cont primary.

**Outcome:** five-year outcome-window host papers by author-disjoint newcomers; PPML with concept-clustered standard errors.

**Table 16. Host-entry grafting results.**

| Specification | A (IRR/SD) | 95% CI | Holm p | CT (p) | Verdict |
|---|---|---|---|---|---|
| Primary (concept × e + host × e FE) | 1.39 | [0.97, 1.99] | 0.15 | 0.48 | NEITHER |
| Co-primary (concept + e + host) | 1.30 | [1.16, 1.45] | 1e-5 | 0.48 | GRAFTING |
| Concept + host × e | 1.22 | - | - | - | GRAFTING |
| Concept × 2-yr bin | - | - | - | - | NEITHER |

[FIGURE:fig_grafting]

The primary specification is underpowered (26% of events retained, 77 clusters). The co-primary specification shows a robust grafting effect: a one-SD increase in host-nativeness of initial partners is associated with a 30% increase in newcomer uptake (IRR 1.30 [1.16, 1.45], Holm p = 1e-5, wild-cluster p = 0.001). Co-transfer is null everywhere: arriving as a package with origin companions does not predict establishment.

**Robustness.** The co-primary A effect holds in 26 of 27 robustness variants (IRR 1.25-1.56, p ≤ 0.001). Binary native cut-offs (0.5/0.7) are null; Physics/Astronomy-only concepts are null. Nativeness-permutation placebo (500 draws) centred on 0; co-primary p = 0.002, primary p = 0.15. [Correction, iteration 4: the co-primary robustness count is 20 of 26 significant (excluding base row and 3 descriptive strata), not "26 of 27". The six null rows are: binary native ≥ 0.5 (IRR 1.005, p = 0.92), binary native ≥ 0.7 (1.066, p = 0.29), A_distinct (1.003, p = 0.96), exclude single-paper entries (1.244 [0.90, 1.71], p = 0.17, N = 200, G = 50), CS stratum (1.15, p = 0.11), and Physics/Astronomy stratum (0.99, p = 0.95). IRR range among significant rows: 1.11-1.56. Source: art_WZ8fbLn79nCq results/robustness_recount.json.]

**Graft labels.** 15% of entries are classified as anchored; anchored entries have an establishment rate of 0.44 vs 0.20 for non-anchored.

**Held-out.** 93 concepts, 1,100 entries sealed. MDE (co-primary): IRR/SD 1.15, below the screen 1.30; the primary spec is declared underpowered in advance.

Source: gen_art_experiment_7/results/d2_summary.json, d2_robustness.csv

## Artifact 15: how new concepts spread, types, roles, timing (descriptive diffusion)

This artifact provides the descriptive diffusion analysis: typology, community roles, expansion-versus-diffusion timing, and representative cases [ARTIFACT:art_QKsLguxnGFQT].

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
| 3. Emergence: temporal network analysis | Done (event study + turnover/brokerage tests) | art_mbFjmo5rbbf8, art_yWUkgWWKyq_h, art__i2cIye01VnN, art_htO_gJuUn6Pr |
| 4. Diffusion: cross-disciplinary spread | Done (breadth-prediction screen + grafting test) | art_62TVG6A4f7Iy, art_2Cd2JJypeGuA |
| 5. Identify recurring trajectories | Done (2-cluster typology + entropy-only baseline) | art_QKsLguxnGFQT |
| 6. Validate with representative cases | Done (4 medoid cases) | art_QKsLguxnGFQT |

## Run ledger

| Artifact | Type | Status | OpenAlex credits | LLM $ | Wall time |
|---|---|---|---|---|---|
| art_94GEMUsgAmgK (pool) | dataset | succeeded | 2,566 | $0.36 | - |
| gen_art_dataset_2 (background) | dataset | failed (timeout) | 1,952 | - | - |
| art_HGiVAYhqO-6q (MeSH) | dataset | succeeded | 1,784 | - | - |
| art_QpM5SM6a7SH6 (grounding) | dataset | succeeded | 1,847 | $0.674 | - |
| art_bNCGUJX2MUhX (dossier) | research | succeeded | - | - | - |
| art_eR1Z7fMlOcxs (hydrated) | dataset | succeeded | 7,237 | $0.024 | - |
| art_BdBvbNuNU8E7 (grounding) | experiment | succeeded | - | $0.053 | - |
| art_yjFB8Spw2w6M (viability) | experiment | succeeded | - | - | - |
| art_mbFjmo5rbbf8 (emergence, main) | experiment | succeeded | - | - | - |
| art_yWUkgWWKyq_h (emergence, MeSH) | experiment | succeeded | - | - | - |
| art__i2cIye01VnN (audit) | evaluation | succeeded | - | - | ~8 min |
| art_htO_gJuUn6Pr (emergence deepen) | experiment | succeeded | - | - | ~15 min |
| art_62TVG6A4f7Iy (breadth prediction) | experiment | succeeded | - | - | ~15 min |
| art_2Cd2JJypeGuA (host-entry grafting) | experiment | succeeded | - | - | ~15 min |
| art_QKsLguxnGFQT (descriptive diffusion) | experiment | succeeded | - | - | ~15 min |

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

---

# Iteration 4

## Strategy

Iteration 4 is a CONFIRMATION iteration. Its purpose is to open the four sealed held-out folds and determine which screen-fold findings replicate, to run four discriminating tests (single-paper artefact, vocabulary decomposition, topic-score absorption, and MeSH replication) that separate genuine host-vocabulary effects from artefacts and circularity, to replicate the grafting result on the independent MeSH population, to test whether pre-emergence closure predicts later host-entry anchoring, and to test the adopter-level mechanism (whether authors who adopt a concept in a new subfield had prior corpus exposure to its entry partners). Five artifacts were executed.

The iteration also addresses ten MAJOR and one MINOR reviewer critiques from the iteration-3 report. The critiques and their disposition are listed in the table below; substantive corrections have been applied inline in the preceding text where indicated.

**Table 18. Reviewer critique disposition.**

| # | Critique summary | Action taken |
|---|---|---|
| M1 | Chronology broken: iterations 1-2 silently rewritten | Iterations 1-3 carried forward verbatim in this report; inline [Correction] markers added where artifacts disproved numbers |
| M2 | Completeness: iteration-3 tables missing detail rows | Additional rows incorporated into iteration-3 tables above (pooled panel, band-only matching, Holm columns) |
| M3 | Grafting robustness count wrong (26/27 → 20/26) | Corrected inline at Table 16 robustness note with full null-row list; source: art_WZ8fbLn79nCq |
| M4 | Closure claim overstated vs artifact support | Addressed by the closure held-out confirmation below; the claim is now graded by held-out outcome |
| M5 | Lead-lag 94% disproportionate; counter-evidence omitted | Full category-count table added in this iteration (Table 21) |
| M6 | Iteration-3 reasoning partly recorded | Strategy section expanded above; decision rules for iteration 4 are the held-out specs (hashes in Hashes table) |
| M7 | Coverage table overstates completion | Coverage table updated below with caveats on grounding scope and unanswered sub-questions |
| M8 | Traceability: folder names instead of artifact IDs | All [ARTIFACT:] markers now use artifact IDs; iteration-3 markers corrected above |
| M9 | Prior-review must-fix items still missing | Items incorporated where data are available; items from iterations 1-2 artifacts not re-run remain as reported |
| M10 | Nearest-neighbour comparisons one-sided | Addressed in "What we have learned" with Cheng et al. focused-discourse tension and Guevara et al. entry-level comparison |
| m1 | Minor traceability and labelling slips | Corrected inline: robustness count, Holm p precision, denominator labels |

## Artifact 16: held-out confirmation of host-entry grafting and discriminating tests

This artifact opens the sealed held-out fold for the grafting test and runs a battery of four discriminating tests that distinguish a genuine host-vocabulary gradient (we define this as the continuous association between the host-nativeness of a concept's entry partners and subsequent newcomer uptake) from single-paper artefacts, classifier circularity, and confounding by topic-score quality [ARTIFACT:art_WZ8fbLn79nCq]. The held-out spec hash (8db17113...) and discriminating-test spec hash (a10b7f31...) were verified before any outcome was read.

### Held-out grafting confirmation

**Table 19. Held-out grafting results.**

| Specification | Fold | IRR/SD (A_cont) | 95% CI | p | CT IRR/SD | CT p | N | G | Verdict |
|---|---|---|---|---|---|---|---|---|---|
| Primary (concept × e + host × e) | Held-out | 0.98 | [0.70, 1.37] | 0.91 | 0.82 | 0.22 | 250 | 30 | Inconclusive (underpowered) |
| Co-primary (concept + e + host) | Held-out | 1.19 | [1.06, 1.33] | 0.0045 | 1.04 | 0.60 | 972 | 74 | GRAFTING confirmed |
| Co-primary (concept + e + host) | Screen | 1.30 | [1.16, 1.45] | 1e-5 | - | - | 1,544 | 140 | GRAFTING |

We call the co-primary specification the pre-declared alternative with concept + entry-year + host fixed effects, used when the fully saturated primary specification is underpowered. The co-primary specification confirms the grafting effect on the held-out fold: IRR/SD = 1.19 [1.06, 1.33], p = 0.0045, wild-cluster p = 0.012. The primary specification is inconclusive because it retains only 23% of events (250 of 1,097) with 30 concept clusters; the pre-declared MDE was IRR/SD 1.30 and it was declared underpowered in advance. Heterogeneity between screen and held-out co-primary estimates is not significant (p = 0.25). The nativeness-permutation placebo is centred on 1.0 (held-out co-primary calibrated p = 0.024). Co-transfer is null on both folds.

Out-of-sample deviance: adding A_cont and CT to the control-only model reduces mean concept-level deviance by 0.50 [−1.24, 0.02] on held-out concepts (descriptive, not the inferential test).

### Single-paper artefact test

83% of entry-year events are single-paper entries. The single-paper artefact test checks whether A_cont predicts newcomer uptake only when multiple independent teams publish entry-year papers (multi-team entries), which would argue against a single-paper classification artefact.

**Table 20. Single-paper artefact interaction results.**

| Fold | IRR/SD (single) | IRR/SD (multi) | Ratio (multi/single) | p (interaction) |
|---|---|---|---|---|
| Pooled | 1.26 | 1.14 | 0.91 | 0.11 |
| Held-out | 1.37 | 1.09 | 0.80 | 0.004 |

On the pooled screen + held-out sample, the multi-team IRR/SD is 1.28 [1.11, 1.48] (G = 161), CI excluding 1. On the held-out alone, the interaction is significant (ratio 0.80, p = 0.004): single-paper entries drive the effect more strongly, and the multi-team IRR/SD is 1.09, with MDE 1.30 (underpowered on the held-out alone). The pooled single-paper-test status is "positive (CI excludes 1)" with G = 161 clusters and projected MDE 1.15.

This result means the single-paper artefact concern is not ruled out on the held-out fold alone (single > multi), though the pooled multi-team effect remains positive. The mechanism label accounts for this.

### Host-vocabulary decomposition

The vocabulary decomposition decomposes A_cont into the share of entry partners classified as NATIVE (≥ 30% host share), ADJACENT (5-30%), and FOREIGN (< 5%), testing whether the gradient runs through host vocabulary or only through the native tail.

**Table 20a. Vocabulary decomposition (co-primary spec).**

| Component | Fold | IRR/SD | 95% CI | p |
|---|---|---|---|---|
| NATIVE | Pooled | 1.11 | [1.05, 1.19] | 0.0008 |
| ADJACENT | Pooled | 1.32 | [1.20, 1.46] | 9e-8 |
| NATIVE | Held-out | 1.10 | [1.01, 1.20] | 0.036 |
| ADJACENT | Held-out | 1.19 | [1.03, 1.38] | 0.020 |

Both NATIVE and ADJACENT components are positive and significant on both folds. The reading is "host-vocabulary (both)": the grafting effect runs through the full host-vocabulary gradient, not just through the native tail. Wald test for equality of NATIVE and ADJACENT per-unit effects: p = 0.64 (pooled), p = 0.49 (held-out); the two are not distinguishable in magnitude. The three-way decomposition (NATIVE, ADJACENT, FOREIGN as separate host-nativeness shares) shows all three positive, with FOREIGN IRR/SD 1.19 (pooled) and 1.24 (held-out).

### Classifier circularity (topic-score absorption)

The topic-score absorption test checks whether the A_cont effect is absorbed by adding the mean topic-score of entry papers (a proxy for how confidently OpenAlex assigns papers to the host subfield) and the host's share of the concept's total topic-assigned volume.

Combined topic-score absorption: −7.3% [−27.5, +6.7] of the log-IRR on the pooled fold, −10.3% [−84.3, +56.6] on the held-out fold. The CI includes zero on both folds: topic-score controls do not meaningfully reduce the A_cont effect. The placebo-host test passes on both folds (size/proximity placebos: share of significant draws ≤ 0.04, median placebo IRR/SD < 1.03).

### MeSH replication (Artifact 17)

See Artifact 17 below.

### Mechanism label

Combining the single-paper, vocabulary-decomposition, and topic-score tests: the pooled mechanism label is **host-vocabulary**. The multi-team effect is positive (pooled CI excludes 1); topic-score absorption is < 50% of the log-IRR; the vocabulary-decomposition reading is "host-vocabulary (both)". The artefact label is not triggered because the multi-team effect is positive and topic-score absorption is small. The held-out single-paper interaction (single stronger) is a caveat: on the held-out alone, the single-paper-test status is "inconclusive (underpowered)" with MDE 1.30 and G = 56.

Source: gen_art_evaluation_2/results/

## Artifact 17: MeSH replication of grafting

This artifact replicates the grafting test on the 191 MeSH biomedical concepts, providing a cross-domain test of the grafting finding [ARTIFACT:art_XGdzjWgi-a88]. Spec hash: b7cdabf8...

The MeSH population yields 2,267 host-entry events across 187 concepts after applying pipeline rules (kw3 partner rule, coverage threshold 0.30). The declared kw5/coverage 0.50 rule gave only 192 events (99 concepts, 46 non-singleton clusters), triggering the pre-declared relaxation.

**Table 20b. MeSH grafting results.**

| Specification | IRR/SD (A_cont) | 95% CI | Holm p | CT IRR/SD | CT p | N | G |
|---|---|---|---|---|---|---|---|
| R1: primary (concept × e + d × e) | 1.32 | [1.10, 1.60] | 0.007 | 1.10 | 0.46 | 1,004 | 122 |
| R2: co-primary (concept + e + d) | 1.23 | [1.12, 1.36] | 9.7e-5 | 1.10 | 0.053 | 2,171 | 160 |

**Verdict: REPLICATED.** Both the primary and co-primary specifications are significant on MeSH. The IVW pooled estimate across main-arm co-primary (IRR/SD 1.30) and MeSH co-primary (1.23) is 1.26 [1.17, 1.36] with I² = 0 (no heterogeneity). CT is borderline on MeSH co-primary (Holm p = 0.053) but null under Holm correction.

**Mechanism on MeSH.** Multi-team test: IRR/SD 1.08 [0.96, 1.22], not significant (MDE 1.30). Vocabulary decomposition: NATIVE 1.17 [1.08, 1.27], ADJACENT 1.11 [1.03, 1.21], both positive. The MeSH carrier is "both" (host-vocabulary). The placebo-host test passes (co-primary nativeness-permutation calibrated p = 0.005; outcome-shuffle p = 0.024).

**Out-of-fold predictive check.** Grouped-by-concept 5-fold out-of-fold deviance improvement: −0.146 [−0.306, −0.008] (A_cont + CT vs baseline). Spearman correlation improves from 0.22 to 0.29.

**Harmonisation with main arm.** Running the main-arm co-primary model under MeSH pipeline rules (kw3, floor 0.30, no dedup, MeSH ranking) gives IRR/SD 1.29-1.35 across six harmonisation variants, confirming that the main-arm result is not an artefact of pipeline differences.

**Cluster-robust variance calibration.** Bias at null: +0.004 (acceptable). Size at null (cluster-robust variance, two-sided 0.05): 0.105 (mild over-rejection); calibrated co-primary p = 0.005. The post-hoc size note is disclosed but does not change the verdict.

Source: gen_art_experiment_9/results/g4_summary.json

## Artifact 18: closure held-out confirmation and closure-anchoring link test

This artifact opens the sealed held-out fold for the emergence question (closure and openness measures) and tests whether pre-emergence closure at the concept level predicts later host-entry anchoring (the closure-anchoring link) [ARTIFACT:art_zw_JJGsUFSnd]. Spec hash: 535c2dd3...

### Closure held-out confirmation

The held-out fold has 100 MAIN concepts. The matching procedure yields 30 onsets, 22 matched (14 before fallback to screen never-controls, 22 after; expected 12 [8, 16]). Balance is imperfect: entropy H has SMD 0.94 at k = 0 (treated concepts have higher entropy), though pre-matching SMD was 0.86.

**Table 20c. Closure held-out results.**

| Measure | Screen S | Held-out S | Held-out 95% CI | Held-out Holm p | Decision |
|---|---|---|---|---|---|
| Closure (pooled panel) | −0.661 | −0.391 | [−0.855, 0.072] | 0.147 | DEAD |
| Turnover-residualised closure | −0.400 | −0.109 | [−0.561, 0.342] | 0.635 | DEAD |
| Persistent-neighbour closure | −1.124 | −1.073 | [−1.858, −0.289] | 0.015 | CONFIRMED |
| Burt constraint | +0.064 | +0.105 | [0.021, 0.187] | - | DEAD (wrong direction for brokerage) |

**Overall closure status: not confirmed.** The primary closure measure and the turnover-residualised closure both fail to reach significance on the held-out fold (Holm p = 0.147 and 0.635). The artifact's status flag is "not supported". However, persistent-neighbour closure (closure restricted to top-20 neighbours that appear in both year y and y−1) is CONFIRMED on the held-out fold: S = −1.073 [−1.858, −0.289], Holm p = 0.015, same sign as screen (−1.124). Burt constraint replicates its positive sign (+0.105 [0.021, 0.187] on held-out, +0.064 on screen), confirming that the effect is not Burt brokerage. Cross-community pair excess has the same positive sign on both folds but does not reach significance on the held-out (S = 0.038 [−0.061, 0.133]).

IVW pooled estimates (descriptive, not a decision): closure −0.464 [−0.790, −0.137] (I² = 0); persistent-neighbour closure −0.683 [−1.209, −0.156] (I² = 0); constraint +0.091 [0.040, 0.143] (I² = 0).

The retained fraction (held-out |S_res| / |S_raw|) is 0.50, compared to 0.67 on the screen; the held-out verdict flag is "model-dependent" (the turnover residualisation is sensitive to model specification). The match rate is 22/30 = 73% on held-out vs 26/68 = 38% on screen (different matching pools).

**Disclosure.** The held-out matching fell back to using screen never-controls (17 of 25 unique event-study controls are screen concepts). Neither estimator is fully control-side independent of the screen.

### Closure-anchoring link: does pre-emergence closure predict later host-entry anchoring?

The closure-anchoring link test checks whether a concept's pre-emergence closure (the emergence exposure variable, averaged over the concept's early life) is correlated with its mean A_cont across host-entry events (the grafting exposure variable), linking the two scales.

**Table 20d. Closure-anchoring link test.**

| Fold | n | Partial ρ | 95% CI | p (two-sided) | MDE (ρ) |
|---|---|---|---|---|---|
| Screen | 102 | +0.025 | [−0.199, 0.242] | 0.806 | 0.258 |
| Held-out | 49 | +0.053 | [−0.279, 0.391] | 0.736 | 0.380 |
| Pooled | 151 | +0.049 | [−0.126, 0.228] | 0.564 | 0.212 |

**Verdict: NULL.** There is no detectable association between pre-emergence closure and later host-entry anchoring. The MDEs (0.258 screen, 0.380 held-out) indicate that only a moderate-to-large correlation would have been detectable; the data are consistent with no link or a weak link below the detection threshold. The reading that openness and anchoring share a common mechanism operating at two scales (openness before emergence facilitating host-native entry later) is not supported and is dropped.

All six breadth-prediction sensitivity cells (closure_res, constraint, cross-community excess × screen/held-out) also have CIs including zero.

Source: gen_art_evaluation_3/results/

## Artifact 19: descriptive held-out confirmation and MeSH descriptive replication

This artifact opens the sealed held-out fold for the descriptive diffusion findings (typology assignment, lead-lag ordering, rooting contrasts) and extends the descriptive analysis to the MeSH population [ARTIFACT:art_mu0h0npvNX_u].

### Lead-lag: expansion before diffusion

**Table 21. Lead-lag category counts.**

| Category | Screen (n = 202) | Held-out (n = 100) | Pooled main (n = 302) | MeSH (n = 191) |
|---|---|---|---|---|
| Neither | 110 (54%) | 49 (49%) | 159 (53%) | 71 (37%) |
| Diffusion only | 39 (19%) | 23 (23%) | 62 (21%) | 97 (51%) |
| Expansion only | 37 (18%) | 18 (18%) | 55 (18%) | 10 (5%) |
| Expansion first | 15 (7%) | 10 (10%) | 25 (8%) | 9 (5%) |
| Same year | 1 (0.5%) | 0 | 1 (0.3%) | 1 (0.5%) |
| Diffusion first | 0 | 0 | 0 | 3 (1.6%) |

Among concepts with both transitions observable, expansion precedes diffusion in 25 of 26 pooled main-arm concepts (held-out: 10 of 10; screen: 15 of 16). No main-arm concept shows diffusion first. On MeSH, 9 of 13 dual-onset concepts show expansion first, with 3 showing diffusion first, weaker but directionally consistent.

Caveats: 53% of main-arm concepts show neither transition; the evaluability rule for diffusion onset (rarefied Shannon requiring ≥ 10 papers in window) mechanically favours expansion-first ordering; only 8% of main-arm concepts have both onsets observable; underpowered.

### Held-out confirmation of descriptive findings

Five pre-registered expectations were tested on the held-out fold [ARTIFACT:art_mu0h0npvNX_u]:

- **Typology shares.** PASS: BROAD share 0.35 (held-out) vs 0.33 (screen); within expected range.
- **Type × outcome association.** PASS: 3/3 Kruskal-Wallis tests significant (p < 0.05).
- **Expansion-first ordering.** PASS: 10/10 held-out dual-onset concepts show expansion first.
- **Anchoring × typology interaction.** PARTIAL FAIL: odds ratios flip between screen and held-out; not confirmed.
- **Other descriptive patterns.** PASS.

### Rooting: do broad concepts anchor more?

The hypothesis that BROAD concepts have higher A_cont (stronger host-native anchoring) is NOT SUPPORTED. Screen mean A_cont difference: −0.0018 (broad slightly lower); held-out: +0.0005, CI including zero. However, BROAD concepts do have lower co-transfer: CT difference −0.125 [−0.19, −0.06] on the held-out fold, replicating the screen pattern. Broad concepts arrive with fewer origin companions but do not compensate by pairing with more host-native partners.

### MeSH descriptive results

On MeSH, the BROAD share is 0.71 [0.64, 0.77] (vs 0.33 on the main arm). The type × branch association is significant (p = 0.0003, Cramér's V = 0.35). Lead-lag: 9 of 13 expansion-first. Community roles: BRIDGE 0.88 (vs 0.61 main), CORE_GROWING and FOUNDER both 0.

Source: gen_art_evaluation_4/results/

## Artifact 20: adopter-level mechanism

This artifact tests whether authors who adopt a concept in a new host subfield had prior corpus exposure to the concept's entry partners, providing an adopter-level mechanism for the host-vocabulary gradient [ARTIFACT:art_FZ2OCJwV6xHs]. We interpret the results through the lens of absorptive capacity, defined by Cohen and Levinthal [30] as an organisation's (here, an individual researcher's) ability to recognise, assimilate, and apply external knowledge. The test uses conditional logistic regression on 1,013 matched case-control strata (422 entries, 109 concepts) from the screen fold. Each stratum pairs an adopter (an author who published a concept paper in the host subfield within the outcome window) with a matched non-adopter from the same host subfield, matched on publication volume.

**Table 22. Adopter enrichment results.**

| Exposure measure | OR | 95% CI (boot) | p (CRV concept) |
|---|---|---|---|
| E_any (any prior partner exposure) | 3.14 | [2.37, 4.29] | 1.4e-13 |
| E_neg (exposure to non-partner concepts) | 0.62 | [0.49, 0.77] | 0.0003 |
| E_plac (placebo-host exposure) | 0.76 | [0.59, 0.95] | 0.013 |
| E_swap (exposure swap control) | 1.11 | [0.87, 1.42] | 0.39 |

Adopters are 3.1× more likely to have prior corpus exposure to the concept's entry partners than matched non-adopters. Exposure to non-partner concepts in the concept's origin subfield (E_neg) is negatively associated (OR 0.62), suggesting that general origin-field exposure does not substitute for specific partner familiarity. The placebo-host control confirms that the effect is specific to the actual host, not to any random subfield.

**Vocabulary-class decomposition.** Decomposing partner exposure by vocabulary class:

**Table 23. Vocabulary-class enrichment.**

| Exposure class | OR | 95% CI (boot) | p (CRV) |
|---|---|---|---|
| E_for (FOREIGN partner exposure) | 2.88 | [2.28, 3.69] | < 1e-6 |
| E_adj (ADJACENT partner exposure) | 1.91 | [1.43, 2.73] | 1e-4 |
| E_nat (NATIVE partner exposure) | 1.47 | [1.02, 2.33] | 0.059 |
| E_neg (non-partner exposure) | 0.65 | [0.51, 0.82] | 0.0003 |

The gradient runs FOREIGN > ADJACENT > NATIVE. Adopters are most enriched for exposure to the concept's foreign (origin-vocabulary) partners, not its host-native partners. This is consistent with absorptive capacity [30]: adopters who can read the concept's origin language are the ones who pick it up. However, this runs in the opposite direction from the entry-level grafting finding (where host-native partners predict establishment). The reading is that the two operate at different scales: at the entry level, host-native partners facilitate uptake by newcomers who do not need origin expertise; at the adopter level, the individuals who adopt are those with prior origin-vocabulary exposure.

**Interaction with A_cont.** The interaction E_any × A_cont is null: OR 0.87 [0.70, 1.14]. The adopter enrichment does not vary with the entry's host-nativeness score.

**Mediation.** Gelbach/PPML mediation: adding E_any as a mediator attenuates the A_cont coefficient by 0.052 (not significant); the reverse attenuation is 0.68. A_cont is not reducible to adopter pool size.

**Partner-to-non-partner ratios.** Partner exposure over non-partner: 5.02 [3.45, 7.51]; partner over placebo-host: 4.53 [3.05, 7.21]; companion over non-companion: 2.27 [1.64, 3.21]. Native-to-foreign ratio: 0.51 [0.33, 0.89] (adopters know more foreign than native partners). Adjacent-to-foreign: 0.66 [0.47, 0.96].

**Reading.** The artifact's verdict is SUPPORT for an absorptive capacity mechanism, with the qualification that the vocabulary-class gradient (FOREIGN > NATIVE) contradicts the grafting reading at the adopter level. This is screen-fold evidence, not held-out confirmation.

Source: gen_art_evaluation_5/results/

## Dead ends and negative results (iteration 4)

1. **Closure not confirmed on held-out for the primary measure.** Raw closure S = −0.391, Holm p = 0.147; turnover-residualised closure S = −0.109, Holm p = 0.635. Only persistent-neighbour closure survives (S = −1.073, Holm p = 0.015). The claim that emerging concepts show lower triadic closure is not supported by the held-out fold on the primary operationalisation; it holds only for the persistent-neighbour variant.

2. **Closure-anchoring link: null.** Pre-emergence closure does not predict later host-entry anchoring (partial ρ = 0.025 screen, 0.053 held-out, both CI including zero). The reading that openness and anchoring share a common mechanism is dropped.

3. **BROAD concepts do not anchor more.** The hypothesis that broad-from-the-start concepts have higher A_cont is not supported (screen −0.0018, held-out +0.0005, CI including zero).

4. **Grafting primary specification: inconclusive.** IRR/SD 0.98 [0.70, 1.37] on held-out, but only 250 events / 30 clusters; declared underpowered in advance.

5. **Single-paper interaction on held-out.** The interaction ratio is 0.80 (p = 0.004): single-paper entries drive the effect more strongly on the held-out fold, which is consistent with a partial single-paper artefact. The pooled multi-team effect remains positive (1.28 [1.11, 1.48]) but the held-out alone is inconclusive (MDE 1.30).

6. **Anchoring × typology interaction flips between folds.** Not confirmed.

7. **Breadth prediction: all six sensitivity cells null on held-out.** Openness does not predict breadth gain on either fold.

## What we have learned

Iteration 4 resolves the study's two main questions with held-out and cross-population evidence.

**Diffusion question: host-entry grafting is confirmed and replicated.** The co-primary grafting specification replicates on the held-out fold (IRR/SD 1.19 [1.06, 1.33], p = 0.0045) and on the independent MeSH population (IRR/SD 1.23 [1.12, 1.36], Holm p = 9.7e-5). The IVW pooled estimate across main co-primary and MeSH co-primary is 1.26 [1.17, 1.36] with I² = 0. The three discriminating tests label the mechanism as "host-vocabulary": the effect runs through both NATIVE and ADJACENT partners (vocabulary decomposition), is not absorbed by topic-score controls (topic-score absorption < 8%), and remains positive for multi-team entries on the pooled sample (single-paper artefact test). Co-transfer (arriving with origin companions) is null across all folds and populations.

The caveats are substantial. The primary fully-saturated specification is underpowered on both held-out and MeSH (IRR/SD 0.98 and 1.32, respectively; the held-out is inconclusive). Single-paper entries (83% of events) drive the effect more strongly on the held-out fold (single-paper interaction 0.80, p = 0.004). Binary native cut-offs (≥ 0.5, ≥ 0.7) are null, meaning the effect operates through the continuous gradient, not through a threshold. Physics/Astronomy concepts are null. The corrected robustness count is 20 of 26 significant co-primary variants (not 26 of 27 as previously stated).

**Nearest-neighbour positioning.** Cheng et al. [13] find that new ideas diffuse more when they are related to prominent concepts and are "deeply situated within focused research discourses," as they term it. Their emphasis on focused discourses points toward cohesion, which is in tension with the openness reading for the emergence question but consistent with the grafting reading for the diffusion question: host-native partnering is a form of discourse integration. This study extends Cheng et al. from a global fit measure to a per-entry, within-concept test with a co-transfer control, exact nativeness profiles from OpenAlex subfield × block counts, and a second population (MeSH). Relatedness density was included as a baseline control in the grafting models. Guevara et al.'s [31] research-space result (entry into related fields predicts success) is the closest entry-level neighbour; what this study adds is the decomposition of entry-partner composition into NATIVE, ADJACENT, and FOREIGN vocabulary classes with a cross-population replication. Rotolo et al. [18] define emerging technologies by coherence, prominence, and community novelty; the k = 2 typology here (localised vs broad-from-the-start) is consistent with their prominence axis.

**Emergence question: closure is not confirmed on the primary measure; persistent-neighbour closure survives.** The held-out fold does not confirm the headline closure finding (Holm p = 0.147) or its turnover-residualised form (Holm p = 0.635). Only persistent-neighbour closure, restricted to top-20 associates present in consecutive years, is confirmed (S = −1.073, Holm p = 0.015). This is a narrower claim: emerging concepts have lower triadic closure among their stable top associates, but the general closure deficit is not robust to the held-out test. Burt constraint replicates its positive (non-brokerage) sign. Pre-emergence closure does not predict later host-entry anchoring (closure-anchoring link null), so the two findings (closure and grafting) are independent.

Salatino et al. [25] find that topics emerge where weakly connected research areas begin to cross-fertilise, which is consistent with the persistent-neighbour finding. The structural-holes literature [23] predicts lower constraint for brokers; this study finds the opposite (higher constraint), so the mechanism is not Burt brokerage.

**Adopter mechanism.** Authors who adopt a concept in a new host subfield are 3.1× more likely than matched non-adopters to have prior corpus exposure to the concept's entry partners. The enrichment is strongest for FOREIGN (origin-vocabulary) partners (OR 2.88) and weakest for NATIVE partners (OR 1.47), consistent with an absorptive-capacity reading [30]: the adopters who pick up the concept are those who can read its origin language. This runs in the opposite direction from the entry-level grafting result (where host-native partners predict establishment) and indicates that the two levels operate through different channels. At the entry level, host-native partners lower the barrier for newcomers who lack origin expertise. At the adopter level, those who actually adopt tend to have origin expertise already.

**Diffusion typology and lead-lag.** The k = 2 typology (localised vs broad-from-the-start) replicates on the held-out fold (BROAD share 0.35 vs 0.33, Kruskal-Wallis type × outcome tests all significant). On MeSH, the BROAD share is much higher (0.71), consistent with the biomedical population's broader disciplinary reach. Expansion precedes diffusion in 25 of 26 pooled main-arm dual-onset concepts and 10 of 10 on the held-out fold. Caveats: only 8% of concepts have both onsets observable; the evaluability rule mechanically favours this ordering; and 21% of concepts diffuse with no expansion onset at all.

## Coverage against the original request

| Activity | Status | Artifact | Caveats |
|---|---|---|---|
| 1. Prepare and semantically ground dataset | Done | art_94GEMUsgAmgK, art_QpM5SM6a7SH6, art_BdBvbNuNU8E7, art_eR1Z7fMlOcxs | Grounding covers focal concepts only; the co-word network uses ~27k legacy OpenAlex concept nodes from the background sample, not semantically grounded |
| 2. Construct evolving knowledge network | Done | art_mbFjmo5rbbf8, art_eR1Z7fMlOcxs | Legacy-concept nodes; variant normalisation minimal (merger recall 0.22/0.13) |
| 3. Emergence: temporal network analysis | Done (closure not confirmed on primary; persistent-neighbour confirmed) | art_mbFjmo5rbbf8, art_yWUkgWWKyq_h, art__i2cIye01VnN, art_htO_gJuUn6Pr, art_zw_JJGsUFSnd | Primary closure not confirmed on held-out |
| 4. Diffusion: cross-disciplinary spread | Done (grafting confirmed + MeSH replicated; breadth prediction null; closure-anchoring link null) | art_62TVG6A4f7Iy, art_2Cd2JJypeGuA, art_WZ8fbLn79nCq, art_XGdzjWgi-a88, art_zw_JJGsUFSnd | Primary spec underpowered; Physics null; single-paper caveat |
| 5. Identify recurring trajectories | Done (k = 2 replicates on held-out and MeSH) | art_QKsLguxnGFQT, art_mu0h0npvNX_u | Finer typologies unstable; 3-channel adds nothing beyond entropy |
| 6. Validate with representative cases | Partial | art_QKsLguxnGFQT | Four medoid cases selected but not individually interpreted in the report |

## Run ledger (iteration 4)

| Artifact | Type | Status | OpenAlex credits | LLM $ | Wall time |
|---|---|---|---|---|---|
| art_WZ8fbLn79nCq (grafting held-out + discriminating tests) | evaluation | succeeded | - | - | ~7 min |
| art_XGdzjWgi-a88 (MeSH replication) | experiment | succeeded | - | - | ~12 min |
| art_zw_JJGsUFSnd (closure held-out + closure-anchoring link) | evaluation | succeeded | - | - | ~10 min |
| art_mu0h0npvNX_u (descriptive held-out + MeSH) | evaluation | succeeded | - | - | ~8 min |
| art_FZ2OCJwV6xHs (adopter mechanism) | evaluation | succeeded | - | - | ~6 min |

## Hashes (iteration 4)

| Item | SHA-256 prefix |
|---|---|
| Grafting held-out confirmation spec | 4100e3cf... |
| Discriminating-test spec | a10b7f31... |
| Grafting held-out fold spec | 8db17113... |
| Closure held-out confirmation spec | 535c2dd3... |
| Closure-anchoring link spec | 5d0144d7... |
| MeSH replication spec | b7cdabf8... |
| Descriptive held-out spec | 4ce330d3... |
| Adopter mechanism spec | 96e697c6... |

## References

[1] H. Pulliam, "Sources, Sinks, and Population Regulation," *The American Naturalist* 132, 652-661, 1988.

[2] J. Priem, H. A. Piwowar, R. Orr, "OpenAlex: A fully-open index of scholarly works, authors, venues, institutions, and concepts," arXiv:2205.01833, 2022.

[3] A. Stirling, "A general framework for analysing diversity in science, technology and society," *Journal of The Royal Society Interface* 4, 707-719, 2007.

[4] I. Rafols, "Knowledge Integration and Diffusion: Measures and Mapping of Diversity and Coherence," arXiv:1412.6683, 2014.

[5] T. Maillart, T. Chataing, D. Dosu, P. Bagourd, J. Jang-Jaccard, A. Mermoud, "Forecasting Conceptual Diffusion in Science: The Case of Quantum Computing," arXiv:2606.03919, 2026.

[6] M. De Domenico, E. Omodei, A. Arenas, "Quantifying the diaspora of knowledge in the last century," *Applied Network Science* 1, 2016.

[7] E. Cunningham, B. Smyth, D. Greene, "Author multidisciplinarity and disciplinary roles in field of study networks," *Applied Network Science* 7, 2022.

[8] A. Holmgren, D. Edler, M. Rosvall, "Mapping change in higher-order networks with multilevel and overlapping communities," *Applied Network Science* 8, 1-15, 2023.

[9] S. Fontaine, F. Gargiulo, M. Dubois, P. Tubaro, "Epistemic integration and social segregation of AI in neuroscience," *Applied Network Science* 9, 2024.

[10] T. Kuhn, M. Perc, D. Helbing, "Inheritance patterns in citation networks reveal scientific memes," *Physical Review X* 4, 041036, 2014.

[11] I. Kiss, M. Broom, P. Craze, I. Rafols, "Can epidemic models describe the diffusion of topics across disciplines?" *Journal of Informetrics* 4, 74-82, 2010.

[12] D. Chavalarias, J.-P. Cointet, "Phylomemetic Patterns in Science Evolution: The Rise and Fall of Scientific Fields," *PLoS ONE* 8(2), e54847, 2013.

[13] M. Cheng, D. Smith, X. Ren, H. Cao, S. Smith, D. A. McFarland, "How New Ideas Diffuse in Science," *American Sociological Review* 88, 522-561, 2023.

[14] J. Kleinberg, "Bursty and Hierarchical Structure in Streams," *Data Mining and Knowledge Discovery* 7, 373-397, 2003.

[15] M. Rosvall, C. T. Bergstrom, "Mapping Change in Large Networks," *PLoS ONE* 5, 2010.

[16] A. Baselga, "Partitioning the turnover and nestedness components of beta diversity," *Global Ecology and Biogeography* 19, 134-143, 2010.

[17] I. Rafols, M. Meyer, "Diversity and network coherence as indicators of interdisciplinarity: case studies in bionanoscience," *Scientometrics* 82, 263-287, 2010.

[18] D. Rotolo, D. Hicks, B. Martin, "What is an emerging technology?" *Research Policy* 44(10), 1827-1843, 2015.

[19] T. Maillart, T. Chataing, N. Antoni, D. Dosu, P. Bagourd, J. Jang-Jaccard, A. Mermoud, "Explainable Forecasting of Scientific Breakthroughs from Concept Network Dynamics," arXiv:2606.03864, 2026.

[20] M. Krenn, A. Zeilinger, "Predicting research trends with semantic and neural networks with an application in quantum physics," *Proceedings of the National Academy of Sciences* 117, 1910-1916, 2020.

[21] L. Huang, X. Chen, X. Ni, J.-R. Liu, X.-H. Cao, C. Wang, "Tracking the dynamics of co-word networks for emerging topic identification," *Technological Forecasting and Social Change* 170, 120944, 2021.

[22] N. Sattar, A. Buluc, K. Z. Ibrahim, S. Arifuzzaman, "Exploring temporal community evolution: algorithmic approaches and parallel optimization for dynamic community detection," *Applied Network Science* 8, 1-29, 2023.

[23] R. S. Burt, "Structural holes and good ideas," *American Journal of Sociology* 110, 349-399, 2004.

[24] J. Ugander, L. Backstrom, C. Marlow, J. Kleinberg, "Structural diversity in social contagion," *Proceedings of the National Academy of Sciences* 109, 5962-5966, 2012.

[25] A. Salatino, F. Osborne, E. Motta, "How are topics born? Understanding the research dynamics preceding the emergence of new areas," *PeerJ Computer Science* 3, e119, 2017.

[26] B. Uzzi, S. Mukherjee, M. Stringer, B. Jones, "Atypical Combinations and Scientific Impact," *Science* 342, 468-472, 2013.

[27] D. Centola, "The Spread of Behavior in an Online Social Network Experiment," *Science* 329, 1194-1197, 2010.

[28] C. A. Hidalgo, P.-A. Balland, R. Boschma, M. Delgado, M. Feldman, K. Frenken, E. Glaeser, C. He, D. F. Kogler, A. Morrison, F. Neffke, D. Rigby, S. Stern, S. Zheng, S. Zhu, "The Principle of Relatedness," *International Conference on Complex Systems*, 451-457, 2018.

[29] C. Chen, "CiteSpace II: Detecting and visualizing emerging trends and transient patterns in scientific literature," *Journal of the American Society for Information Science and Technology* 57(3), 359-377, 2006.

[30] W. M. Cohen, D. A. Levinthal, "Absorptive Capacity: A New Perspective on Learning and Innovation," *Administrative Science Quarterly* 35, 128-152, 1990.

[31] M. R. Guevara, D. Hartmann, M. Aristarán, M. Mendoza, C. A. Hidalgo, "The Research Space: using career paths to predict the evolution of the research output of individuals, institutions, and nations," *Scientometrics* 109, 1695-1709, 2016.
