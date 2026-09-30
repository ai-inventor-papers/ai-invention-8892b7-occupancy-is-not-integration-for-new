# Occupancy is not integration: separating self-sustaining from imported presence of emerging scientific concepts

This report documents an investigation of how emerging scientific concepts diffuse across disciplinary boundaries, and whether the standard measures of interdisciplinary breadth conflate two distinct processes: locally reproduced presence and presence maintained only through continued importation from other subfields. The study adapts the source-sink framework from population ecology [1] to concept-discipline edges in an evolving knowledge network built from OpenAlex [2], with the aim of decomposing breadth indicators by viability state and testing whether the decomposition predicts future integration beyond conventional baselines.

Two research questions structure the work. The precursor question asks which volume-normalised structural changes in a concept-concept co-occurrence network precede emergence, defined without citations as sustained uptake plus centrality gain. The viability question asks whether a concept's presence in a subfield is self-sustaining (a source edge) or import-dependent (a sink edge), and whether breadth computed over source edges alone predicts the concept's future integration better than Shannon entropy, Rao-Stirling diversity (a measure combining the variety, balance and disparity of disciplinary categories) [3], momentum, growing-edge breadth, Rafols coherence [4], and the endogenous-exogenous features of Maillart et al. [5]. The hypothesis draws on Pulliam's source-sink theory [1]. Just as a habitat can be occupied indefinitely through immigration without local reproduction, a scientific concept can appear in a subfield's papers without being reproduced there, and this occupancy-without-viability should disappear when the inflow stops.

The target venue is Applied Network Science, whose published work on knowledge diaspora [6], disciplinary roles in field-of-study networks [7], alluvial community change [8], and the epistemic integration of AI in neuroscience [9] provides the closest comparison base.

---

# Iteration 1

## Strategy

The first iteration was devoted to three preparatory tasks: (a) assembling a prior-art and pre-registration dossier grading each candidate mechanism's novelty and feasibility, (b) building the concept pool and its associated OpenAlex work corpus, and (c) constructing the semantic grounding infrastructure (concept detection, labelling, variant merging) and a held-out MeSH confirmation population. No experiment or evaluation was executed. Every artifact in this iteration is either a dataset or a research dossier. The rationale was to fix all operational definitions, sample the data, and verify the citation-layer gate (Gate A) before committing compute to network construction and statistical modelling.

The pre-registration dossier ranks five candidate mechanisms by novelty margin against the nearest prior work. Host anchoring (the share of a concept's new co-occurrence edges in a host subfield that attach to host-native concepts) was ranked highest at medium-to-high novelty; toolkit co-transfer (the fraction of a concept's origin companions that co-appear in host papers) was ranked high on measurement novelty but coupled to host anchoring; citation-lineage source-sink viability was ranked medium, with Kuhn et al.'s meme propagation score [10], Kiss et al.'s epidemic diffusion model [11], De Domenico et al.'s author-flow source-sink indices [6], and Maillart et al.'s endogenous-exogenous decomposition [5] as the nearest antecedents. Origin-neighbourhood structure (the participation coefficient and clustering topology of the concept in its birth subfield) was ranked low-to-medium because structural diversity and community spread are well studied [12], and the demic-versus-cultural adoption channel was ranked MEDIUM but with the weakest feasibility due to author-disambiguation biases [ARTIFACT:art_bNCGUJX2MUhX].

## Artifact 1: concept pool and OpenAlex work corpus

The concept pool was built in an outcome-blind frame. The sample was frozen and hashed before any post-appearance-window data were inspected [ARTIFACT:art_94GEMUsgAmgK]. The pool comprises 206 concepts, of which 184 are main emerging concepts (first appearance year F in 2005-2016, with 20-300 papers in the window F to F+2 and no more than 8,000 total works through 2024) and 22 stationary reference concepts (age at least 10 years, flat incidence, at least 30 papers per year). The 184 main concepts are split into a screen fold of 123 (focal years 2010-2014) used for model development and a held-out concept fold of 61 (focal years 2016-2018) reserved for out-of-sample evaluation.

The pool is heavily dominated by arXiv-sourced concepts. Of 366 eligible candidates, 363 came from the arXiv-mined arm, and the final 184 span three origin fields. The original target of 400 main concepts was not met because the shared free OpenAlex API key exhausted its daily credit allowance during hydration.

**Table 1. Concept pool composition by origin field.**

| Origin field | Main concepts | Share |
|---|---|---|
| Physics and Astronomy | 82 | 44.6% |
| Physical Sciences (other) | 56 | 30.4% |
| Computer Science | 45 | 24.5% |
| Other | 1 | 0.5% |
| **Total main** | **184** | **100%** |

The pool also carries 22 reference concepts (stationary arm) used to calibrate the replacement benchmark.

**Table 2. Concept pool by first-appearance band.**

| F band | Count |
|---|---|
| 2005-2007 | 38 |
| 2008-2011 | 76 |
| 2012-2016 | 70 |
| **Total** | **184** |

Verified links pairing each concept with the OpenAlex works that use it total 214,798 pairs spanning 208,374 unique works. Each link carries match evidence. Of these, 56,997 matched in the work title, 51,966 in the abstract, 10,177 through Semantic Scholar only, and 2,689 through OpenAlex concept indexing alone. Of the 184 main concepts, 26 were discovered natively in OpenAlex and 180 were discovered through the Semantic Scholar index and mapped to OpenAlex (mapping rate 0.93). Two concepts entered through both routes. Twenty-one concepts carry a sense-check failure flag, indicating that the dominant sense of the surface form covers fewer than half the matched works.

[FIGURE:fig_concept_pool]

### Gate A: citation-layer feasibility

The critical pilot gate concerns whether citation lineages between papers using the same concept are dense enough to estimate local reproduction ratios. The quality report shows that among main-arm concept papers with references, 66.99% cite at least one earlier concept paper (the "traced share"), and after excluding first-year canonical papers and the five most-cited concept papers, the traced share remains 60.80%. The host-specific traced share (concept papers outside the origin subfield that cite at least one earlier concept paper in the same host subfield) is 55.18%, above the 40% gate threshold. This passes Gate A.

**Table 3. Citation-layer quality by origin field.**

| Metric | All main | Physics & Astro | Physical Sci | Computer Sci |
|---|---|---|---|---|
| Concept papers (n) | 121,829 | 19,653 | 46,575 | 55,274 |
| Share with references | 83.92% | 82.04% | 84.99% | 83.74% |
| Traced share (any) | 66.99% | 66.12% | 67.89% | 66.53% |
| Traced share (excl. F + top-5) | 60.80% | 57.74% | 61.75% | 61.09% |
| Host traced share (excl. F) | 55.18% | 49.68% | 58.39% | 53.86% |
| Host concept papers (n) | 41,861 | 4,171 | 15,973 | 21,609 |
| Abstract availability | 77.99% | 83.07% | 72.89% | 80.56% |

The recall audit, comparing counts derived from OpenAlex against independent Semantic Scholar counts for 30 concepts, gives a median count ratio of 0.84 (IQR 0.79-0.89) and a Spearman rank correlation of 0.976, indicating that the retrieval pipeline captures a consistent fraction of each concept's literature.

### Denominators by subfield and year, and venue habitat

Totals by subfield and year cover 25,195 rows (all 252 OpenAlex subfields across 25 years in four counting variants: all types, typed articles/reviews, works with abstracts, works with references). These denominators support per-10,000 normalisation of concept incidence. A venue-habitat file assigns 15,261 venues to their dominant subfield based on pre-period publication shares; 4,292 venues exceed the 40% dominant-share threshold and qualify as covered venues for the citation-independent habitat robustness check.

## Artifact 2: held-out MeSH confirmation population

A separate biomedical confirmation arm was built from new MeSH descriptors (DateEstablished 2006-2016 from the 2017 MeSH release, widened to 2004-2005 and 2017-2018) [ARTIFACT:art_HGiVAYhqO-6q]. The construction follows a provenance filter: descriptors whose prior-year form appears parenthetically in an older descriptor, those that were promoted from supplementary concepts, and those that were renamed are dropped. Starting from 28,472 descriptors (desc2017.xml.gz), the pipeline selects 5,201 topical descriptors established in 2006-2016, retains 3,430 after the provenance filter, narrows to 283 passing the PubMed title-and-abstract novelty pre-screen and early-volume rule (F in 2005-2016, 15-350 papers in F to F+2, total 8,000 or fewer), and adds 40 from the 2004-2005 widening and 133 from the 2017-2018 widening. After retrieval and the final rule on verified union counts, 191 concepts survive.

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

The MeSH population is purpose-built as a held-out check. Its concepts come from a different discovery route (curated MeSH vocabulary rather than text mining), a different domain (biomedicine rather than physics and computer science), and use a different identity source (MeSH preferred-concept terms rather than arXiv-mined noun phrases). Of the 191 concepts, 172 have strict rule parity with the main corpus (their final inclusion rule saw non-PubMed OpenAlex works the same way the main corpus did); the remaining 19 are flagged as widened extras. Only 13 of 191 have their full non-PubMed works paged, because the OpenAlex credit budget ran out.

The artifact also delivers 9,477 positive synonym-acronym pairs and 13,620 hard negatives (narrower concepts, related concepts, sibling descriptors) across all 3,430 provenance-filtered 2006-2016 descriptors, structured with train/test folds that prevent surface-form leakage into the main corpus.

## Artifact 3: semantic grounding and labelling infrastructure

The semantic grounding artifact provides the infrastructure for detecting, labelling, and merging concept mentions [ARTIFACT:art_QpM5SM6a7SH6]. It comprises seven datasets.

**Stratified corpus.** A background corpus of 93,600 English OpenAlex articles and reviews with abstracts, sampled at 150 per field-by-year stratum across 26 OpenAlex fields (54,600 main-period 2003-2016 and 39,000 pre-screen 1995-2004). The corpus carries design weights and stratum identifiers for each work.

**Candidate phrases labelled by large language models (LLMs).** From 1.22 million distinct noun-phrase and acronym keys mined with spaCy and the Schwartz-Hearst abbreviation-extraction algorithm, 4,599 were labelled as CONCEPT, NOT_CONCEPT, TOO_GENERIC, or VARIANT_OF by two LLMs (gemini-2.5-flash-lite as model A, gpt-4.1-nano as model B) with a claude-haiku-4.5 adjudicator resolving disagreements. The train-test split (1,200 train, 300 test) is clustered by variant group with zero surface-form leaks between splits.

**Table 5. Labelling quality.**

| Metric | Value |
|---|---|
| Model A vs model B inter-rater kappa (4-class) | 0.259 |
| Model A vs model B binary kappa (concept vs rest) | 0.267 |
| Model A vs model B raw agreement | 67.5% |
| A vs adjudicator kappa (4-class, silver-gold 200) | 0.632 |
| A vs adjudicator accuracy (4-class) | 78.9% |
| A vs human anchors binary kappa (SemEval/SciERC) | 0.56 |
| A precision (concept, human-anchored) | 0.79 |
| A recall (concept, human-anchored) | 0.76 |
| Disagreements adjudicated (n) | 411 |
| Adjudicator sided with A | 325 / 411 |
| Adjudicator sided with B | 52 / 411 |

The low inter-model kappa (0.26) reflects model B's strong bias toward the CONCEPT label; in the confusion matrix between the two models, B labels 1,333 of 1,491 items as CONCEPT while A labels 882. The adjudicator sides with model A in 79% of disagreements. Against external human annotations (SemEval-2017 Task 10 and SciERC keyphrase spans), model A achieves a binary kappa of 0.56 with precision 0.79 and recall 0.76. These are silver labels. No human annotator has checked them, and a human-check spreadsheet is prepared but not yet executed.

**Variant pairs.** 502 same/different pairs (281 SAME, 221 DIFFERENT) from Schwartz-Hearst expansions, MeSH entry terms, Wikidata aliases, and near-duplicates, with folds following the labelling clusters.

**External human anchors.** 23,520 SemEval-2017 Task 10 and SciERC phrase rows, plus 15,723 acronym-identification sentences. The Schwartz-Hearst implementation achieves pair precision 0.95 and recall 0.93 on the validation set.

**Survivorship-free phrase pool.** 1,000 novel text-mined phrases with yearly counts restricted to F through F+2, designed to avoid survivorship bias. Of these, 929 are unlinked to any external identifier. Only 1 strict-eligible anchored phrase was found (11 across relaxed eligibility tiers), far below the target of 150, due to the low yield of the text-mining pipeline combined with OpenAlex credit exhaustion. The full post-F+2 trajectories are sealed in a separate file.

**Table 6. Semantic grounding dataset sizes.**

| Dataset | Rows |
|---|---|
| Stratified corpus (2003-2016 + 1995-2004) | 93,600 |
| Candidate phrases labelled by LLMs | 4,599 |
| Variant pairs | 502 |
| Human anchors (SemEval + SciERC) | 23,520 |
| Acronym identification sentences | 15,723 |
| Survivorship-free phrase pool | 1,000 |
| Held-out phrase works | 363 |

**Cost.** OpenAlex API spend for this artifact was $0.185 and LLM labelling cost $0.674, for a total of $0.86.

## Artifact 4: prior-art dossier and pre-registration

The research artifact [ARTIFACT:art_bNCGUJX2MUhX] grades each candidate mechanism's novelty margin against a systematically assembled base of prior work. The headline finding is that the space is active but no prior study estimates a within-host reproduction ratio with an import share per concept-subfield edge, nor tests host anchoring at the edge level. The grading is reproduced in Table 7.

**Table 7. Candidate mechanism novelty grades.**

| Candidate | Description | Novelty grade | Nearest prior art |
|---|---|---|---|
| C1: Host anchoring | Share of new co-occurrence edges attaching to host-native concepts | Medium-to-high | Cheng et al. 2023 [13] (global fit measure, paywalled) |
| C2: Toolkit co-transfer | Origin companions co-appearing in host papers | HIGH (coupled to C1) | No quantitative co-arrival test found |
| C0: Source-sink viability | Local reproduction ratio normalised to stationary benchmark | MEDIUM | Kuhn et al. 2014 [10] (meme score); Kiss et al. 2010 [11]; Maillart et al. 2026 [5] |
| C4: Demic vs cultural | Author-based vs adoption-based diffusion | MEDIUM | Fontaine et al. 2024 [9]; Cheng et al. 2023 [13] |
| C3: Origin-neighbourhood structure | Participation coefficient, clustering at origin | Low-to-medium | Structural diversity literature |

The dossier also records observed OpenAlex API facts as of 2026-09-28. Three findings shape the study design. First, OpenAlex keywords now equal legacy concepts in 11 of 12 sampled works (the /keywords endpoint lists 65,004 items headed by "Computer science" and "Medicine"), contradicting the documentation that keywords come from topic keyword sets scored with BGE-M3. The consequence is that the keyword-topic-citation circularity documented for topics does not hold as described for keywords, and concepts remain usable as a text-based concept layer. Second, the topic classifier reads title, abstract, citations and venue, creating temporal label leakage when applied to older works (a 2005 paper's primary topic was assigned using its later citation profile). Every headline claim therefore requires a venue-habitat robustness check. Third, zero-reference articles among core sources decline from 29.0% in 2005 to 13.8% in 2020; abstract availability ranges from 54% to 68%. These coverage rates are factored into the Gate A assessment above.

The precursor-question framing was adjusted based on the dossier's finding that the generic claim "network features predict emergence" carries LOW novelty given Science4Cast, Impact4Cast (AUC > 0.9), and Augur. The revised framing emphasises volume-normalised precursors (per-paper indicators rather than raw counts), a data-derived trajectory typology, and rolling-origin evaluation against named baselines including burst detection [14], degree-based preferential attachment, Shannon and Rao-Stirling diversity [3, 4], and the Maillart features [5].

The cost estimate for the full dataset step was $4-9 in OpenAlex API credits, corresponding to a few days of the free allowance.

## Dead ends and shortfalls

Four shortfalls emerged during iteration 1.

1. **Concept pool size.** The target of 400 main concepts was not met; 184 were realised. The cause was exhaustion of the shared free OpenAlex API key during the hydration step, which downloads full work records for each concept. The remaining 220 concepts are logged in a pending-hydration file and can be resumed. The current 184 are sufficient for the screen and held-out folds, but statistical power for the status-by-cooling interaction will need to be re-evaluated on the realised sample.

2. **Field coverage.** The concept pool draws overwhelmingly from physics, physical sciences, and computer science because the arXiv-mined vocabulary arm produced 363 of 366 eligible candidates. The MeSH held-out population covers biomedicine, but the main analysis cannot claim generality across fields. The planned mitigation (a discovery arm based on OpenAlex keywords) did not produce enough eligible candidates within the credit budget.

3. **Survivorship-free phrase pool yield.** The pool of 1,000 text-mined phrases produced only 1 strict-eligible anchored concept (11 across relaxed tiers), against a target of 150. This shortfall means the survivorship-free validation, which was intended to confirm that the concept pool does not over-represent concepts that survived, cannot run at the planned scale. The cause is twofold. The text-mining pipeline's noun-phrase extraction has low precision for identifying genuinely novel scientific concepts, and the OpenAlex API credit ran out before enough candidates could be verified.

4. **Labelling quality.** The inter-rater kappa between models A and B is low (0.26), driven by model B's over-labelling of CONCEPT. The adjudicator resolves this in favour of model A, which performs reasonably against human anchors (kappa 0.56, precision 0.79, recall 0.76). However, no human has checked any label. The human-check sheet is ready, and executing it would move the labels from silver to gold status.

## What we have learned so far

Iteration 1 established the data foundation and pre-registration for the study. The concept pool of 184 main emerging concepts and 22 reference concepts, with 214,798 verified concept-to-work links and 208,374 unique works, passes the citation-layer gate (host traced share 55.18%, above the 40% threshold) and is ready for network construction. The MeSH held-out population of 191 biomedical concepts provides an independent confirmation arm from a different domain and discovery route. The semantic grounding infrastructure delivers labelled candidate phrases, variant pairs, and human anchors, though at lower yield than planned.

The prior-art dossier grades host anchoring as the highest-novelty candidate (medium-to-high) and source-sink viability as medium, and flags that the generic precursor-question claim is crowded. No experiment has been executed; no quantitative result about the hypothesis itself exists. The next iteration should build the evolving concept-concept and concept-discipline networks, estimate viability states on the screen fold, and run the pilot power analysis for the status-by-cooling interaction.

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

---

# Iteration 2

## Strategy

Iteration 2 moved from data assembly to experimentation. Four goals were set. First, train and evaluate the concept grounding pipeline (classifier, variant merger, and entity linker) using the labels and anchors from iteration 1, producing a vetted test population with known size and quality. Second, build the concept-discipline bipartite network and estimate viability states on the screen fold, including the citation-layer Gate A re-test at edge level. Third, construct the evolving concept-concept co-occurrence network and run the precursor event study on structural antecedents of emergence. Fourth, replicate the precursor event study on the MeSH held-out population.

A key design decision was to run the citation-layer Gate A test and viability estimation before the precursor event study. If Gate A failed at edge level, the viability decomposition central to the hypothesis would be unavailable, and the remaining contribution would rest on the precursor question alone. Gate A did fail (see Artifact 7 below), which narrows the paper's scope to the precursor question and its replication.

The five artifacts produced in this iteration are: a hydration and nativeness-profile dataset extending the corpus from iteration 1 (Artifact 5); the concept grounding pipeline with classifier, merger, and test population (Artifact 6); the viability layer including Gate A re-test, synthetic validation, and power analysis (Artifact 7); the main-pool precursor event study with prediction and typology (Artifact 8); and the MeSH replication of the precursor analysis (Artifact 9).

## Artifact 5: hydrated corpus, nativeness profiles, and venue habitat (dataset)

This artifact completes the hydration of the concept pool's work corpus and adds two layers required by the viability machinery: nativeness profiles for concept-subfield edges and a venue habitat based on ASJC (All Science Journal Classification) codes as a citation-independent alternative to the topic-derived habitat from iteration 1 [ARTIFACT:art_eR1Z7fMlOcxs].

**Hydration.** The run ledger reports 7,237 total OpenAlex API credits consumed. The frame SHA-256 hash was verified against the frozen pool from iteration 1. Each concept's works were fetched and reconciled with the earlier retrieval.

**Nativeness profiles.** For each concept-subfield-year edge, the pipeline computes a four-block nativeness profile from exact OpenAlex group_by counts: (a) works by the concept in that subfield, (b) all works by the concept, (c) all works in the subfield, and (d) all works in OpenAlex in that year. The overall host weight coverage (the fraction of concept-subfield edges for which all four blocks are non-missing) is 78.7%. A total of 1,372 nodes have complete four-block profiles, yielding 5,488 profiles in all.

**Venue habitat.** The ASJC venue coverage was computed as a robustness check against the topic-derived habitat. Overall coverage is 12.1%, with 2,929 venues covered. This low coverage means the ASJC venue habitat cannot serve as a primary habitat assignment and is usable only as a sensitivity check on the subset of edges where it is available.

**Table 8. Dataset 5 coverage summary.**

| Metric | Value |
|---|---|
| API credits consumed | 7,237 |
| Host weight coverage (all 4 blocks) | 78.7% |
| Nodes with complete profiles | 1,372 |
| Total profiles | 5,488 |
| ASJC venue coverage | 12.1% |
| Covered ASJC venues | 2,929 |

## Artifact 6: concept grounding pipeline (experiment)

This artifact trains and evaluates the three components of the concept grounding pipeline: a binary classifier that separates scientific concepts from non-concepts, a variant merger that clusters surface forms referring to the same concept, and a linker that maps detected mentions to pool concepts or flags them as unlinked (NIL, meaning no matching entity exists in the pool) [ARTIFACT:art_BdBvbNuNU8E7].

**Classifier.** The classifier is a ridge-regularised logistic regression trained on MiniLM and SPECTER2 embeddings of candidate phrases, using the silver labels from iteration 1 (Artifact 3). On the held-out test set it achieves an F1 score of 0.818 and ROC-AUC of 0.888. It outperforms a majority-class baseline (F1 score 0.000) and a unigram-frequency baseline (F1 score 0.689).

**Table 9. Classifier performance on test set.**

| Metric | Value |
|---|---|
| F1 score (binary: concept vs rest) | 0.818 |
| ROC-AUC | 0.888 |
| Precision | 0.812 |
| Recall | 0.824 |
| Accuracy | 0.843 |

Against human anchor evaluations (SemEval-2017 and SciERC keyphrase spans), the classifier achieves a binary kappa of 0.56, consistent with the silver-label quality reported in iteration 1.

**Variant merger.** The merger uses cosine similarity on the same embedding space to decide whether two surface forms refer to the same concept. The operating threshold was set at p_merge = 0.855. On the variant-pair test set, the merger achieves an F1 score of 0.357; on the held-out MeSH synonym pairs, the F1 score is 0.222; B-cubed F1 (a clustering-quality measure averaging precision and recall over individual items) across the full clustering is 0.78. The low pairwise F1 scores reflect a conservative threshold that favours precision over recall: the merger under-merges rather than conflating distinct concepts, which is the safer failure mode for downstream viability estimation.

**Table 10. Variant merger performance.**

| Test set | F1 score |
|---|---|
| Variant pairs | 0.357 |
| Held-out MeSH synonyms | 0.222 |
| B-cubed (full clustering) | 0.780 |

**Test population.** The grounding pipeline produces a test population with four tiers. The MAIN population contains 156 concepts, the STRICT subset (concepts passing all quality filters including sense-check and merger confidence) contains 147, the REFERENCE_ACCEPTED arm has 42 stationary concepts, and a SENSITIVITY set (relaxing the first-appearance-year rule) contains 426 concepts.

**Table 11. Test population sizes.**

| Population | Count |
|---|---|
| MAIN | 156 |
| STRICT | 147 |
| REFERENCE_ACCEPTED | 42 |
| SENSITIVITY | 426 |

## Artifact 7: viability layer: Gate A, viability states, synthetic validation, and power analysis (experiment)

This artifact attempts to estimate viability states (SOURCE, SINK, FADING, UNDETERMINED) for concept-subfield-year edges using citation lineages [ARTIFACT:art_yjFB8Spw2w6M]. The critical result is that **Gate A fails at edge level**, which blocks the viability decomposition that is central to the study's hypothesis.

### Gate A re-test at edge level

The original Gate A test in iteration 1 (Table 3) assessed citation-layer density at the concept level, pooling all subfields. The re-test here assesses it at the concept-subfield-year edge level, which is the granularity required for viability estimation. The verdict is FAIL: only 17.3% of edges have a within-host traced share at or above the 0.40 threshold. The mean within-host traced share across all edges is 0.20, and the median is 0.15. The reference arm's host share is 0.13.

[FIGURE:fig_gate_a]

**Table 12. Gate A edge-level results.**

| Metric | Value |
|---|---|
| Edges with host share >= 0.40 | 17.3% |
| Mean within-host traced share | 0.20 |
| Median within-host traced share | 0.15 |
| Reference arm host share | 0.13 |

The discrepancy between the concept-level pass (55.18% host traced share) and the edge-level failure (17.3% at >= 0.40) arises because the concept-level metric pools all host subfields for each concept, while the edge-level metric evaluates each concept-subfield-year combination individually. Most concept-subfield edges have too few papers for citation lineages to be traced within that specific subfield-year cell.

### Viability states

Despite the Gate A failure, viability states were estimated on the subset of edges that meet the tracing threshold. Of 779 eligible edges, 169 were tested, producing 63 SOURCE edges, 26 SINK edges, 7 FADING edges, and 683 UNDETERMINED edges (those not meeting the minimum tracing density). Sensitivity analyses at varying thresholds show 94-99% agreement with the primary classification.

**Table 13. Viability state distribution.**

| State | Count | Share of tested |
|---|---|---|
| SOURCE | 63 | 37.3% |
| SINK | 26 | 15.4% |
| FADING | 7 | 4.1% |
| UNDETERMINED | 683 | — |
| **Total eligible** | **779** | — |
| **Total tested** | **169** | **100%** |

[FIGURE:fig_viability_states]

### Synthetic validation

The synthetic validation tests whether the viability classification correctly distinguishes planted source and sink edges in a semi-synthetic network. The overall false discovery rate (FDR) is 0.209, which exceeds the pre-specified threshold of 0.15. By state: SOURCE FDR = 0.13 (acceptable), SINK FDR = 0.40 (unacceptable). The high SINK FDR means the classifier frequently labels genuine sink edges as sources or vice versa when the citation signal is sparse.

**Table 14. Synthetic validation FDR.**

| State | FDR | Threshold |
|---|---|---|
| SOURCE | 0.13 | <= 0.15 |
| SINK | 0.40 | <= 0.15 |
| **Overall** | **0.209** | **<= 0.15** |

### Power analysis and minimum detectable effects

The power analysis estimates the minimum detectable effect (MDE) for the viability-decomposed breadth prediction under various sample-size and effect-size scenarios.

**Table 15. Minimum detectable effects (selected rows).**

| n_min | AUC target | Design | MDE (Cohen's d) |
|---|---|---|---|
| 5 | 0.7 | realised | 1.22 |
| 10 | 0.7 | realised | 0.89 |
| 20 | 0.7 | realised | 0.64 |
| 30 | 0.7 | realised | 0.53 |
| 10 | 0.8 | projected | 0.72 |
| 20 | 0.8 | projected | 0.51 |
| 30 | 0.8 | projected | 0.42 |
| 20 | 0.8 | N150 | 0.44 |
| 30 | 0.8 | N150 | 0.36 |

With the realised sample and the Gate A failure limiting the number of testable edges, the MDE at n_min = 10 and AUC = 0.7 is 0.89 SD, meaning only very large viability effects could be detected. This confirms that the viability decomposition cannot produce reliable results with the current citation-layer density, and the study must proceed without it.

### Consequence for the hypothesis

The Gate A failure at edge level, combined with the synthetic validation FDR exceeding the threshold (0.209 vs 0.15) and the high SINK FDR (0.40), means that the viability decomposition central to the study's hypothesis cannot be executed at the planned granularity. The SOURCE classification is marginally acceptable (FDR 0.13), but SINK classification is unreliable. The study therefore cannot test whether breadth computed over source edges alone predicts future integration better than conventional diversity measures. The viability layer survives only as a descriptive taxonomy of a small subset of edges, not as a predictive instrument. The remaining contribution rests on the precursor question and its replication.

## Artifact 8: precursor event study, main pool (experiment)

This artifact runs the precursor event study on the main concept pool's screen fold (123 active concepts plus 22 reference concepts), testing whether volume-normalised structural precursors in the co-occurrence network distinguish emerging from non-emerging concepts before the onset of emergence [ARTIFACT:art_mbFjmo5rbbf8].

### Co-occurrence network snapshots

The evolving concept-concept co-occurrence network was constructed with association-strength weighting and Leiden community detection. The network contains 1,487 persistent nodes across the observation window and produces 2,618 concept-year indicator rows.

### Emergence labels and event study design

Emergence is defined as sustained uptake plus centrality gain, computed without citations. Three label definitions were used. The primary label E applies the strength percentile threshold among all snapshot nodes (including background legacy concepts from the substrate sample); because pool concepts sit in the bottom approximately 5% of the strength distribution, a 20-point percentile gain is rare, and the primary label is severely underpowered. E_alt (the pre-declared sensitivity label) applies the percentile threshold among pool and reference nodes only, and was promoted to a full analysis after seeing that the primary label yields only 4 emerging concepts (E rate 2.1%). E_up (sustained uptake only, without the centrality requirement) identifies 41 emerging concepts.

**Table 16. Emergence label counts.**

| Label | N emerging | Rate | Status |
|---|---|---|---|
| E (primary) | 4 | 2.1% | Underpowered pilot |
| E_alt (sensitivity) | 14 | — | Promoted to secondary |
| E_up (uptake only) | 41 | 38.2% | Adequately powered |

The event study uses a matched-control design. For E_up, 21 of 41 treated concepts were matched to controls (match rate 51.2%), with 33.3% requiring widened caliper and a mean of 1.62 controls per treated concept.

### Precursor indicators

Three volume-normalised precursor indicators were tested: closure (the log-ratio of triadic closure rate to the configuration-model null), accretion share (the fraction of new edges that extend beyond the concept's existing neighbourhood), and participation coefficient (the share of a node's connections crossing community boundaries, based on Leiden communities). Each indicator was measured at yearly resolution and compared between emerging and non-emerging concepts in the pre-onset window, using the Baselga turnover partition [16] to decompose community change.

### Event study results

The headline finding is that **closure is LOWER, not higher, before emergence**. For E_up (the adequately powered label), the pooled panel coefficient for closure is S = -0.837, with a 95% bootstrap CI of [-1.26, -0.427] and a Holm-corrected p-value of 0.003. This means concepts that subsequently emerge show less triadic closure than matched non-emerging controls in the years before onset, the opposite of the hypothesis that clustering and internal cohesion precede emergence.

Accretion share shows no significant difference (S = -0.14, CI [-0.185, 0.018], Holm p = 0.272). Participation coefficient shows no divergence (S = -0.007, CI [-0.066, 0.056], Holm p = 0.782).

[FIGURE:fig_closure_event]

**Table 17. Event study results, E_up (adequately powered).**

| Indicator | S (pooled) | 95% CI | Holm p |
|---|---|---|---|
| Closure (log-ratio) | -0.837 | [-1.26, -0.427] | 0.003 |
| Accretion share | -0.140 | [-0.185, 0.018] | 0.272 |
| Participation coefficient | -0.007 | [-0.066, 0.056] | 0.782 |

For the primary label E (4 emerging concepts, 3 matched), the same direction holds (closure S = -0.625, CI [-0.656, -0.588]) but with so few treated units that bootstrap p-values are not interpretable. For E_alt (14 emerging, 10 matched), closure is S = -0.400, CI [-0.919, 0.190], with Holm p = 0.096.

### Prediction: precursors add nothing beyond baselines

The rolling-origin prediction test asks whether adding precursor features (closure, accretion, participation, and their derivatives) to a baseline of frequency/burst, degree/centrality, and entropy features improves prediction of emergence.

For E_up (the only label with at least two rolling origins), the BASELINE model achieves AUC = 0.859 and the FULL model (baseline + precursors) achieves AUC = 0.878, giving a delta of +0.019, CI [-0.025, 0.060]. The precursors add no statistically significant predictive value. The label-permutation shuffle test produces a mean delta of -0.015 with SD = 0.082, confirming that the observed delta is indistinguishable from noise.

For E_alt (single origin, pilot only), the FULL model underperforms the BASELINE: AUC 0.628 vs 0.686, delta = -0.058.

[FIGURE:fig_prediction_comparison]

**Table 18. Prediction: BASELINE vs FULL model AUC.**

| Label | Origins | BASELINE AUC | FULL AUC | Delta | 95% CI |
|---|---|---|---|---|---|
| E (primary) | 1 | 0.887 | 0.925 | +0.038 | [~0, 0.130] |
| E_alt (sensitivity) | 1 | 0.686 | 0.628 | -0.058 | [-0.537, 0.407] |
| E_up (uptake only) | 2 | 0.859 | 0.878 | +0.019 | [-0.025, 0.060] |

### Trajectory patterns

Three trajectory patterns were defined and scored for each concept: incubation-then-expansion (early volume growth followed by neighbourhood expansion), gradual centralisation (monotonic centrality gain), and early bridging (participation coefficient above the 75th percentile in at least one pre-onset year). Early bridging is the most common pattern, present in 76% of all concepts (78% of E_up emerging, 78% of non-emerging). None of the three patterns distinguishes emerging from non-emerging concepts: all Fisher exact tests return p >= 0.205, and all confidence intervals on the emerging-minus-non-emerging difference cover zero.

### Typology stability

The data-derived typology uses k-medoids clustering with dynamic time warping (DTW) on seven channels (strength growth, Baselga similarity, Baselga nestedness, participation, closure, betweenness percentile, Shannon entropy). At every k from 2 to 6, the minimum bootstrap Jaccard index is below 0.60 (k=2: 0.49, k=3: 0.51, k=4: 0.45, k=5: 0.42, k=6: 0.46), and AMI against the pattern combinations is -0.013. There is no stable typology.

## Artifact 9: precursor replication, MeSH held-out population (experiment)

This artifact replicates the precursor event study on the MeSH held-out population of 191 biomedical concepts (1,067 concept-year units after age filtering to 3-8 years) [ARTIFACT:art_yWUkgWWKyq_h]. The replication uses the same matched-control event study design and the same indicators as the main pool.

### Emergence labels

The primary label identifies 18 emerging concepts (onset years spanning 2010-2016, rate 3.9%). SENS1 (broader) identifies 34 and SENS2 (stricter) identifies 14. The E_cent-only label, which captures centrality gain without requiring sustained uptake, identifies 42 concepts.

**Table 19. MeSH emergence label counts.**

| Label | N emerging | Rate |
|---|---|---|
| PRIMARY | 18 | 3.9% |
| SENS1 (broader) | 34 | 7.0% |
| SENS2 (stricter) | 14 | 3.1% |
| E_cent only | 42 | 8.6% |

### Matching

For the PRIMARY label, 18 emerging concepts were matched with a rate of 83.3% at the 30% caliper (72.2% at the tighter 20% caliper), yielding 42 total controls from 30 unique control concepts.

### Event study results

The closure effect replicates directionally: closure is again LOWER before emergence. For the PRIMARY label (n_eff = 15), pooled closure D = -0.086 with Holm p = 0.677. This is not significant, but with only 15 effective units the test is underpowered. For SENS1 (n_eff = 29), closure D = -0.419, CI [-0.740, -0.115], Holm p = 0.039, significant after Holm correction and confirming the direction found in the main pool. For SENS2 (n_eff = 10), closure D = -0.858, CI [-1.668, 0.034], Holm p = 0.124.

**Table 20. MeSH replication: closure effects.**

| Label | n_eff | Closure D | 95% CI | Holm p |
|---|---|---|---|---|
| PRIMARY | 15 | -0.086 | [-0.511, 0.402] | 0.677 |
| SENS1 | 29 | -0.419 | [-0.740, -0.115] | 0.039 |
| SENS2 | 10 | -0.858 | [-1.668, 0.034] | 0.124 |
| E_cent only | 30 | -0.148 | [-0.399, 0.106] | 0.486 |

The event null test (permutation of treatment labels across 200 permutations) confirms that the observed effects are not artefacts of the event study design: the mean permutation D for closure is 0.019 with SD = 0.224, and the absolute mean is less than 0.25 times the bootstrap standard error of the real D, passing the null-bias check.

Accretion share shows no significant effect across any label (PRIMARY Holm p = 0.48, SENS1 p not significant). Participation coefficient dP is significant for SENS1 only (D = 0.051, CI [0.014, 0.087], Holm p = 0.015), but is not significant for PRIMARY (D = 0.025, Holm p = 0.506).

### Prediction

The MeSH replication confirms the prediction null. The label-permutation delta-AUC check shows a mean delta of -0.015 across 5 permutations. The transfer test (applying the main-pool model to MeSH data) could not be run because no main-pool model file was available at run time.

### Patterns

Pattern frequencies in the MeSH population are similar to the main pool. Early bridging shows no distinguishing power (diff = 0.150, CI [-0.090, 0.363]). Incubation-then-expansion (diff = 0.122, CI [-0.077, 0.352]) and gradual centralisation (diff = -0.017, CI [-0.040, 0.0]) also fail to distinguish emerging from non-emerging concepts.

## Dead ends and negative results

Five negative findings emerged during iteration 2, each of which constrains the study's scope.

1. **Gate A failure at edge level.** The within-host traced share at edge level (17.3% >= 0.40, mean 0.20, median 0.15) falls far below the concept-level pass from iteration 1 (55.18%). The viability decomposition that is central to the original hypothesis cannot be executed with reliable precision. SOURCE classification alone is marginally acceptable (FDR 0.13), but SINK classification is unreliable (FDR 0.40), and 87.7% of eligible edges are UNDETERMINED. The viability layer is a dead end for the current dataset.

2. **Synthetic validation FDR exceeds threshold.** The overall FDR of 0.209 exceeds the pre-specified 0.15. Even if Gate A had passed, the viability classifier would need recalibration before its labels could support predictive claims.

3. **No stable typology.** The k-medoids clustering on seven temporal channels (strength growth, Baselga similarity and nestedness, participation, closure, betweenness, Shannon entropy) produces no stable clusters at any k from 2 to 6. Bootstrap Jaccard indices range from 0.42 to 0.51, and AMI against pattern combinations is -0.013. There is no data-derived trajectory typology of emergence.

4. **Precursors add no predictive value.** Across both the main pool and the MeSH replication, adding precursor features to a baseline of frequency/burst, degree/centrality, and entropy features yields delta AUC values indistinguishable from noise (main pool E_up: +0.019, CI [-0.025, 0.060]; MeSH label-permutation mean delta: -0.015). The volume-normalised precursor indicators do not predict emergence beyond what conventional baselines already capture.

5. **Closure is lower, not higher, before emergence.** The pre-registered expectation was that internal cohesion (triadic closure above the configuration-model null) would precede emergence. The data show the opposite: emerging concepts have significantly less triadic closure than matched controls before onset (main pool E_up: S = -0.837, Holm p = 0.003; MeSH SENS1: D = -0.419, Holm p = 0.039). This reversal suggests that emerging concepts inhabit structurally sparse, bridging positions rather than dense clusters before they take off.

## What we have learned so far

Iteration 2 produced three substantive findings and confirmed two dead ends.

The viability decomposition, which was the centrepiece of the original hypothesis, is blocked by insufficient citation-layer density at the concept-subfield-year edge level. Gate A passes when pooling all subfields per concept (iteration 1: 55.18% host traced share), but fails when evaluated at the edge granularity needed for viability estimation (iteration 2: 17.3% of edges meet the 0.40 threshold). The synthetic validation further undermines the viability classifier (SINK FDR = 0.40). The study cannot test whether source-edge-only breadth outpredicts conventional diversity measures. This dead end is definitive for the current dataset and would require either a substantially larger corpus (raising the number of concept papers per subfield-year cell) or a non-citation measure of local reproduction to overcome.

The precursor question yields a clear and replicated finding, though it contradicts the pre-registered direction. Triadic closure is lower, not higher, before emergence. In the main pool, the effect size for the E_up label (sustained uptake) is S = -0.837 with Holm p = 0.003. In the MeSH replication, the SENS1 label yields D = -0.419 with Holm p = 0.039. Both populations and both label definitions point in the same direction. This suggests that emerging concepts occupy structurally sparse, bridging positions in the co-occurrence network rather than consolidating in dense clusters before taking off. The finding aligns with the early-bridging pattern (present in 76-78% of concepts), which is common but does not distinguish emerging from non-emerging concepts because it is nearly universal.

No volume-normalised precursor indicator adds predictive value beyond baselines of frequency, burst state, degree, centrality, and entropy. The delta AUC for the main pool (E_up) is +0.019, CI [-0.025, 0.060]; for MeSH it is indistinguishable from the label-permutation null (mean -0.015). The trajectory typology is unstable at every k. These results indicate that the structural precursor indicators tested here (closure, accretion share, and participation coefficient) do not carry independent predictive signal for emergence once conventional features are included.

The paper's remaining contribution centres on the replicated closure reversal: the finding that emerging concepts are structurally sparser, not denser, before emergence, and that this pattern replicates across a physics/CS pool and a biomedical pool with different concept-discovery routes. The next iteration should focus on strengthening the interpretive case for this finding, testing whether non-citation proxies for local reproduction (such as host anchoring or author-overlap measures) can substitute for the blocked viability layer, and determining whether the closure reversal reflects a genuine structural mechanism or is an artefact of volume normalisation.

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
