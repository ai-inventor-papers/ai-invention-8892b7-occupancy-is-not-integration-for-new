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
