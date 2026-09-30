# Prior art and plan for concept-spread study

## Summary

Prior-art and pre-registration dossier for a five-candidate OpenAlex screen on how emerging concepts diffuse (locally concentrated vs broadly integrated), targeting the Applied Network Science collection "Networks for everyday life". Files: research_report.md (9 sections), research_out.json, reproducibility.md.

(1) Master table: candidate | formula | nearest prior art | novelty margin | predicted sign | confound | control.
- Ranking: C1 host anchoring (MEDIUM-HIGH), with C2 co-transfer (HIGH but coupled) as its opposite-sign contrast; then C0 citation-lineage source/sink viability (MEDIUM; closest: Kuhn 2014 propagation score, Bettencourt 2006 R0, Kiss 2010, De Domenico 2016 ANS, Maillart 2026 endo/exo R2 0.018 vs 0.78); then C4 demic/cultural (MEDIUM; Fontaine 2024 ANS, Cheng 2023); C3 neighbourhood structure is LOW-MEDIUM (Ugander 2012, Weng 2013, Centola 2010 contradicts) and should be a baseline.
- The generic RQ1 claim "network features predict emergence" is LOW (Science4Cast, Impact4Cast AUC>0.9, Augur); recast it as volume-normalised precursors plus a typology.

(2) Pre-registration sheet on unit (c, d != origin, t), W1=[t-5,t], W2=[t+1,t+5]: exact formulas, OpenAlex inputs, minimum counts, signs, pitfalls and controls for rho/m (C0), A* (C1), CT (C2), P/SD/closure (C3), demic/cultural shares (C4), Y1 (PPML newcomer uptake with offset, FE d×t and o×t, clustered by concept), Y2, and all baselines (Shannon rarefied, Rao-Stirling with fixed distance matrix, DIV, subfield count, momentum, Rafols coherence, Maillart 28 features, Kuhn P_m, Kleinberg, degree/PA, community spread).

(3) OpenAlex facts, OBSERVED 2026-09-28:
- keywords now equal legacy concepts in 11/12 works (/keywords = 65,004), contradicting the docs, so the keyword-topic-citation circularity no longer holds as documented.
- Concepts are still attached to 2026 works.
- Topics are citation clusters; the classifier reads title, abstract, citations and venue, so there is temporal label leakage and a venue-habitat control is needed.
- Zero-reference core articles: 29.0% (2005) to 13.8% (2020). Abstracts: 54-68%.
- mesh.descriptor_ui is not filterable (use has_pmid); per_page=200 works; the corpus param dates from Aug 2026.
- Cost table: about $4-9 for the whole dataset step.

(4) ANS: 16 verified ANS papers with comparison points, a Table-1 draft, and the section/declaration template (author-year references, 3-7 keywords, ~200-300-word abstract). Honest fit note: weak to moderate; frame as research-policy indicators with health cases; fallback is a general ANS submission.

(5) Emergence-evaluation checklist (10 items) and cheap falsification tests per risk.

## Research Findings

SCOPE. This dossier (full version in research_report.md) grades the novelty margin of five candidate mechanisms that separate locally concentrated from broadly integrated emerging concepts (C0-C4). It also grades the RQ1 "network-only emergence" framing and the "hollow breadth" claim (P1). It then pre-registers every score on one shared unit (concept c × non-origin subfield d × focal year t; W1 = [t-5, t], W2 = [t+1, t+5]), audits OpenAlex feasibility and cost, and assembles the Applied Network Science (ANS) venue base. Evidence levels are marked in the report: VERBATIM, ABSTRACT, SNIPPET, OBSERVED (my API calls on 2026-09-28), RECONSTRUCTED, UNVERIFIED.

1. RQ1 IS CROWDED; RECAST IT.
- That network features predict concept emergence is established:
  - Science4Cast: 64,719 AI concepts; hand-crafted network features outperform learned ones [27].
  - Impact4Cast: 21,165,421 OpenAlex papers and 368,825 RAKE concepts; AUC > 0.9 for most experiments [28].
  - Augur: emergence is preceded by faster collaboration between ancestor areas; gold standard of 1,408 debutant topics [29].
  - Phylomemies: field density correlates with field fate [20].
  - Maillart et al. 2026 on OpenAlex concept pairs: exogenous diffusion is highly predictable (test R2 = 0.78); endogenous reinforcement is not (test R2 = 0.018) once growth is normalised [1].
- The remaining margin is MEDIUM at best: volume- and age-matched precursors, a data-derived trajectory typology on the concept-subfield bipartite, and rolling-origin tests against named baselines (burst [38], momentum, degree growth/PA [27], Shannon, Rao-Stirling and DIV [36, 37], community spread [17]).
- "Neighbourhood novelty" is essentially the ego-subnetwork overlap index of an ANS paper [70].

2. C0, CITATION-LINEAGE SOURCE/SINK VIABILITY: MEDIUM margin.
- Prior art:
  - The meme propagation score P_m = sticking/sparking (delta = 3; time-preserving randomisation null) [2].
  - Epidemic R0 of Feynman diagrams [3].
  - Epidemic spread of a topic over a citation-based map of subject categories, with incubation periods of 4-15.5 years at disciplinary boundaries [5].
  - ANS source/sink indices for author flows [4].
  - Endogenous/exogenous citation weights [1], rooted in Crane & Sornette [7].
- None estimates a within-host reproduction ratio with an import share per (concept, host subfield).
- Risks:
  - OpenAlex topics are CWTS citation clusters, and subfields aggregate topics [44], so within-subfield citation is inflated by construction.
  - Zero-reference articles among core sources: 29.0% (2005), 26.7% (2010), 23.0% (2016), 13.8% (2020) (OBSERVED [54]; overall coverage is comparable to WoS/Scopus on a shared corpus [55]).
- Controls: rho normalised by same-(d,t) reference concepts, a venue-habitat subfield, has_references filtering, and a time-preserving shuffle.

3. C1, HOST ANCHORING: MEDIUM-HIGH margin; best novelty × feasibility.
- No study found measures, at entry into a host, the share of a concept's new co-occurrence edges that attach to host-native concepts, and relates it to durability in the host.
- Nearest:
  - Cheng et al. 2023: new ideas become core when they reach unrelated authors and "fit with extant research traditions", measured globally; the exact fit measure is paywalled [8].
  - Relatedness/research-space work predicts UNITS entering fields [11, 12, 13].
  - Uzzi's conventional + atypical combinations [9].
  - Houkes' theory of "conceptual embedding" in template transfer [14].
  - Single-concept case studies, e.g. entropy from physics to economics [15].
  - Atypicality as extension into new areas [42].
- Formula: A* = A - E_d[A], with relatedness density (Hidalgo phi = min of the conditional probabilities [11]) as a covariate.

4. C2, TOOLKIT CO-TRANSFER: HIGH margin on measurement, weak theory.
- No quantitative co-arrival test was found; the "package deal" is only theorised [14].
- It is mechanically coupled to C1 on the same entry events. Pre-register the opposite-sign discriminating screen: Y1 ~ A* + CT.

5. C3, ORIGIN-NEIGHBOURHOOD STRUCTURE: LOW-MEDIUM margin.
- Structural diversity (connected components of the ego network) controls contagion; neighbourhood size turns negative once it is controlled [16].
- Early spread across communities gives about 7× the precision of random guessing and more than 3× community-blind prediction [17].
- Guimera-Amaral role thresholds: hubs z >= 2.5; non-hub connectors 0.62 < P <= 0.80; connector hubs 0.30 < P <= 0.75 [18].
- Contradicting evidence: clustered networks spread behaviour better (54% vs 38%) [19].
- Pre-register two-sided; use C3 as a baseline family.

6. C4, DEMIC VS CULTURAL: MEDIUM margin, weakest feasibility.
- ANS prior art finds AI in neuroscience integrated epistemically but socially segregated; only 3% of 855k neuroscience papers carry AI keywords [21]. AI tools stay confined to subfields [22].
- Author "diaspora" flows [4], social origins of disciplines [23], explorers vs exploiters [25].
- Author disambiguation (about 85M to 53M author records; duplicate profiles) biases the demic share (SNIPPET [57, 58]). Use an ORCID-only robustness subset.

7. P1, HOLLOW BREADTH: MEDIUM margin.
- Diversity vs coherence [35] and DIV [37] exist; tying breadth to host-level source/sink viability is new.
- Baselines must fix the Rao-Stirling distance matrix in advance and rarefy Shannon entropy, which rises mechanically with volume.

RANKING FOR THE SCREEN
1. C1, with C2 as its contrast.
2. C0.
3. C4 (ORCID arm).
4. C3 (as a baseline).
5. RQ1 generic claim (do not headline).

OPENALEX FACTS THAT CHANGE THE PLAN (OBSERVED 2026-09-28 [54])
(a) keywords = concepts. The documentation says keywords come from topic keyword sets scored with BGE-M3 [45]. In the live API, work.keywords equals work.concepts (same labels and scores) in 11 of 12 sampled works, and /keywords lists 65,004 items headed by "Computer science" and "Medicine". So the keywords -> topics -> citations circularity does NOT hold as documented. Tags come from the text-based, Wikidata-linked concept tagger, with its artefacts (e.g. "Quality (philosophy)").
(b) Concepts are still assigned. They are documented as frozen and not tagged on new works [46], yet 10,514,189 of 32,364,822 works dated 2026 carry concepts.id C41008148. The concepts.id filter still works [47].
(c) MeSH exists in work.mesh, but mesh.descriptor_ui is not a valid filter; use has_pmid. Only about 25% of new MeSH descriptors are genuinely new concepts, so MeSH is a weak ground truth [39].
(d) Abstract availability among core-source articles: 54.3% (2005) to 67.7% (2020). Extraction must be titles-first.
(e) per_page=200 is accepted; OR filters take up to 100 values [49]; corpus=core|expansion|all was added in August 2026 [47]; the Walden rewrite added 190M works [53].
(f) Topic hierarchy: 4 domains, 26 fields, 252 subfields, 4,516 topics (confirmed by the API). The classifier reads title, abstract, citations and journal name [44]. Because labels on old papers use later citation structure (label leakage), every key result needs a venue-habitat robustness check.

COST
- Unit prices: singleton free; list/filter $0.10 per 1k; search $1 per 1k; semantic $1 per 1k; content $10 per 1k; $1/day free [48, 50, 51].
- Full dataset step (about 30k calls): about $4-9, i.e. a few days of the free allowance.
- The free S3 snapshot (about 626M records, about 330 GB; SNIPPET [52]) only pays off at far larger scale.

SEMANTIC GROUNDING (existing resources before training models)
- OpenAlex concepts: about 65k, Wikidata-linked, free [46, 54].
- Impact4Cast knowledge graph and benchmark on Zenodo [28].
- Augur gold standard [29].
- MeSH for health cases.
- Keep ID-less surface forms (Kuhn meme score [2] or RAKE [28]) for post-freeze emergers. Validate on about 300 hand-labelled mentions.

VENUE
- "Networks for everyday life" welcomes theory, methods and applications for health, mobility, education, politics and related societal domains, reviewed on a rolling basis [60] (SNIPPET; the page is JS-gated; editors and deadline UNVERIFIED).
- Fit is moderate to weak. Frame the paper as research- and education-policy evidence (breadth indicators steer funders; hollow breadth misleads them) and anchor the cases in health subfields. Fallback: a regular ANS research article.
- Verified ANS citation base: [4, 21] plus Salnikov et al. 2018 (co-occurrence simplicial complexes) [62], Gao et al. 2018 (patent community evolution) [63], Vale Cunha et al. 2020 (entropy of title semantic networks) [64], Vaccario et al. 2020 (scientist mobility) [65], Cunningham et al. 2022 (topic roles) [66], Holmgren et al. 2023 (alluvial community change) [67], Sattar et al. 2023 (temporal communities) [68], Simonetti et al. 2025 (statistically validated text networks) [69], Medeuov et al. 2021 [70], Renoust et al. 2017 (citation flows) [71], Zou et al. 2023 (temporal link prediction) [72], Djurdjevac Conrad et al. 2025 (sparse dynamic communities) [73], Chacko et al. 2026 (citation ABM, a generative null for C0) [74] and Correia & Mena-Chalco 2025 (indicator gaming) [75].
- Template, from 2025-2026 ANS articles [76, 77, 78, 79] and [66]:
  - Abstract of about 195-305 words, unstructured; 3-7 keywords.
  - Introduction; Related work (separate in [66]); Methods with a Data subsection; Results; Discussion with Limitations; Conclusions.
  - Back matter: Abbreviations, Acknowledgements, Author contributions, Funding, Availability of data and materials (mandatory [61]), Declarations with Competing interests.
  - Author-year references; Springer Nature LaTeX template.

EVALUATION NORMS
- Rolling-origin temporal hold-out.
- AP / precision@k alongside AUC.
- Equally tuned named baselines.
- Volume matching.
- Null models (configuration, time-preserving [2], SVN backbone [69]).
- Ground-truth proxies with caveats [29, 30, 31, 39].
- Right-censoring as in [1].
- BH-controlled pre-stated signs.
- Cases chosen from the clusters.

FURTHER RELATED WORK (for the related-work section)
- Emergence and field formation: topological transitions in collaboration networks as fields mature [6]; tradition vs innovation strategies [10]; the emergence-scoring indicator (novelty, persistence, growth, community) [32]; TrendNets bursty co-word decomposition [33]; interdisciplinary emergence via category co-occurrence plus BERTopic [34]; persistent-homology "holes" in concept space (Aug 2026) [41]; field-to-field knowledge-flow networks in physics [43].
- Mobility and social channels: rising topic switching [24]; insiders vs outsiders adapting to LLMs [26].
- MeSH as a knowledge-evolution signal [40].
- Idea diffusion beyond citations: from research into journalism and policy [80]; national citation preferences shaping international idea diffusion [81].
- Data caveats and access: open-abstract removals [56]; the API-key and usage-based pricing change [59].

CONFIDENCE
- High for the novelty grades of C3 and RQ1 (well-documented prior art).
- Medium for C0, C1 and C2: absence of evidence comes from targeted, not systematic, searches, and Cheng et al.'s full text [8] was not read.
- High for the OpenAlex observations, but they are dated and may change.
- What would change the grades: a paper measuring host-native attachment at entry (would lower C1), or a host-specific reproduction measure (would lower C0).

## Sources

[1] [Forecasting Conceptual Diffusion in Science: The Case of Quantum Computing](https://arxiv.org/pdf/2606.03919) (Thomas Maillart, Thibaut Chataing, David Dosu, Paul Bagourd, Julian Jang-Jaccard, Alain Mermoud; 2026) — Closest prior art for C0/RQ1: OpenAlex quantum-computing concept pairs, upstream/downstream citation lineage, LightGBM on 28 upstream features; endogenous count test R2=0.0179, exogenous 0.7804, ratio 0.4715; focal years 1996-2018 (n=6,978 pair-years); random 80/20 split.

> almost no explanatory power for endogenous citation activity

Locator: Sec. 5.1

> the exogenous count task achieves strong and consistent predictive power

Locator: Sec. 5.1

> Growth-normalised targets; stratified 80/20 train–test split; Optuna-tuned

Locator: Table 2 caption

[2] [Inheritance patterns in citation networks reveal scientific memes](https://arxiv.org/pdf/1404.3757) (Tobias Kuhn, Matjaž Perc, Dirk Helbing; 2014) — Meme propagation score P_m = sticking/sparking with noise delta=3 and meme score M_m=f_m P_m on ~50M records (WoS, PMC, APS); time-preserving randomization null. Baseline and null for C0.

> as its sticking factor divided by its sparking factor

Locator: Results

[3] [The power of a good idea: quantitative modeling of the spread of ideas from epidemiological models](https://arxiv.org/abs/physics/0502067) (Luís M. A. Bettencourt, Ariel Cintrón-Arias, David I. Kaiser, Carlos Castillo-Chávez; 2006) — Epidemic models (incl. reproductive number R0) fitted to spread of Feynman diagrams in USA, Japan, USSR; closest prior art for rho-as-R. Numerical R0 not extractable (garbled PDF).

> We estimate the effectiveness of adoption of the idea in the three communities

Locator: Abstract

[4] [Quantifying the diaspora of knowledge in the last century (Applied Network Science 1:15, doi:10.1007/s41109-016-0017-9)](https://arxiv.org/abs/1604.00696) (Manlio De Domenico, Elisa Omodei, Alex Arenas; 2016) — ANS precedent for source/sink terminology: author flows between 306 SCImago topics; sink/source indices; Medicine, Physics, Chemistry mainly sources.

> mainly act as sources of the diaspora

Locator: Abstract

[5] [Can epidemic models describe the diffusion of topics across disciplines?](https://arxiv.org/abs/0905.3585) (Istvan Z. Kiss, Mark Broom, Paul G. Craze, Ismael Rafols; 2010) — Epidemic model of kinesin research over a citation-based ISI subject-category contact network; incubation 4-15.5 years at disciplinary boundaries.

> they face difficulties to overcome disciplinary boundaries

Locator: Abstract

[6] [Scientific discovery and topological transitions in collaboration networks](https://web.mit.edu/dikaiser/www/BKK.Topological.pdf) (Luís M. A. Bettencourt, David I. Kaiser, Jasleen Kaur; 2009) — Eight fields undergo a topological transition (giant component) in co-authorship as they mature (snippet-level).

[7] [Robust dynamic classes revealed by measuring the response function of a social system](https://www.pnas.org/doi/10.1073/pnas.0803685105) (Riley Crane, Didier Sornette; 2008) — Endogenous vs exogenous burst relaxation classes (YouTube); conceptual root of endo/exo split (snippet-level).

[8] [How New Ideas Diffuse in Science](https://journals.sagepub.com/doi/10.1177/00031224231166955) (Mengjie Cheng, Daniel Scott Smith, Xiang Ren, Hancheng Cao, Sanne Smith, Daniel A. McFarland; 2023) — ~60,000 new ideas (WoS 1993-2016) across 38M papers; core-concept status predicted by reaching unrelated authors, consistent usage, association with prominent ideas, fit with traditions. Nearest prior art for C1/C4 (global level); exact fit measure paywalled.

> fit with extant research traditions

Locator: Abstract

[9] [Atypical Combinations and Scientific Impact](https://www.science.org/doi/10.1126/science.1240474) (Brian Uzzi, Satyam Mukherjee, Michael J. Stringer, Benjamin F. Jones; 2013) — 17.9M papers; high-impact work = conventional combinations plus intrusion of atypical ones; twice as likely highly cited.

[10] [Tradition and Innovation in Scientists' Research Strategies](https://arxiv.org/abs/1302.6906) (Jacob G. Foster, Andrey Rzhetsky, James A. Evans; 2015) — Chemical knowledge networks from MEDLINE; tradition vs innovation strategies (snippet-level).

[11] [The product space conditions the development of nations](https://arxiv.org/pdf/0708.2090) (César A. Hidalgo, Bailey Klinger, Albert-László Barabási, Ricardo Hausmann; 2007) — Proximity phi = min of pairwise conditional probabilities of RCA; basis for relatedness density (density formula reconstructed).

> take the minimum of the pairwise conditional probabilities

Locator: p. 3

[12] [The Research Space: using career paths to predict the evolution of the research output of individuals, institutions, and nations](https://arxiv.org/pdf/1602.08409) (Miguel R. Guevara, Dominik Hartmann, Manuel Aristarán, Marcelo Mendoza, César A. Hidalgo; 2016) — Author co-publication-based field map predicts which fields individuals/organizations enter better than citation maps (ROC validation); unit-level relatedness prior art for C1.

> significantly more accurate predictor of the fields that

Locator: Abstract

[13] [Mapping the physics research space: a machine learning approach](https://link.springer.com/article/10.1140/epjds/s13688-019-0210-z) (Matteo Chinazzi, Bruno Gonçalves, Qian Zhang, Alessandro Vespignani; 2019) — Embedding-based physics research space; knowledge density and research capacity fingerprints (snippet-level; effect size unverified).

[14] [Embedding and customizing templates in cross-disciplinary modeling](https://link.springer.com/article/10.1007/s11229-023-04076-8) (Wybo Houkes; 2023) — Template transfer creates conceptual pressure; mitigation by conceptual embedding and customization (theory anchor for C1/C2; snippet-level).

[15] [Beyond borrowed concepts: a semantic analysis of entropy's half-century cross-disciplinary journey between physics and economics](https://link.springer.com/article/10.1007/s11192-025-05489-7) (Bea Treena Macasaet, Justin J W Powell; 2026) — Single-concept case of boundary-crossing via abstract embeddings; validation case for C1 typology (abstract via OpenAlex).

[16] [Structural diversity in social contagion](https://pdodds.w3.uvm.edu/research/papers/others/2012/ugander2012a.pdf) (Johan Ugander, Lars Backstrom, Cameron Marlow, Jon Kleinberg; 2012) — Contagion probability controlled by number of connected components in contact neighbourhood; size becomes negative predictor once controlled (C3 prior art).

> rather than by the actual size of the neighborhood

Locator: Abstract

[17] [Virality Prediction and Community Structure in Social Networks](https://arxiv.org/pdf/1306.0158) (Lilian Weng, Filippo Menczer, Yong-Yeol Ahn; 2013) — Early community concentration predicts meme virality; ~7x precision over random, >3x over community-blind (C3/RQ2 baseline).

> about seven times as precise as random guess and over three times as precise as prediction

Locator: Results

[18] [Functional cartography of complex metabolic networks](https://arxiv.org/pdf/q-bio/0502035) (Roger Guimerà, Luís A. Nunes Amaral; 2005) — Participation coefficient and within-module z; role thresholds R1-R7 (hubs z>=2.5; non-hub connector 0.62<P<=0.80; connector hub 0.30<P<=0.75).

> connector hubs, i.e., hubs with many links to most of the other modules

Locator: p. 3-4

[19] [The Spread of Behavior in an Online Social Network Experiment](https://www.science.org/doi/10.1126/science.1185231) (Damon Centola; 2010) — Behaviour spreads more on clustered networks (54% vs 38%); contradicting prediction for C3 (snippet-level).

[20] [Phylomemetic Patterns in Science Evolution—The Rise and Fall of Scientific Fields](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0054847) (David Chavalarias, Jean-Philippe Cointet; 2013) — Phylomemy; field density correlates with status and fate (RQ1 prior art; snippet-level).

[21] [Epistemic integration and social segregation of AI in neuroscience (Applied Network Science 9:8, doi:10.1007/s41109-024-00618-2)](https://arxiv.org/pdf/2310.01046) (Sylvain Fontaine, Floriana Gargiulo, Michel Dubois, Paola Tubaro; 2024) — ANS; MAG neuroscience 1970-2019; AI integrates epistemically but is socially segregated; collaboration z-scores vs randomization. Closest ANS prior art for C4/RQ2.

> only 3% contain AI-related keywords

Locator: Sec. 3.1

[22] [A Dynamical Cartography of the Epistemic Diffusion of Artificial Intelligence in Neuroscience](https://arxiv.org/abs/2507.01651) (Sylvain Fontaine; 2025) — AI technologies remain confined within neuroscience subfields (evidence of locally concentrated diffusion).

> remain confined in the different subfields and are not transferred from one subfield to another

Locator: Abstract

[23] [Social Dynamics of Science](https://www.nature.com/articles/srep01069) (Xiaoling Sun, Jasleen Kaur, Staša Milojević, Alessandro Flammini, Filippo Menczer; 2013) — Disciplines emerge from splitting/merging of social communities; ABM validated empirically (snippet-level).

[24] [Increasing trend of scientists to switch between topics](https://www.nature.com/articles/s41467-019-11401-8) (2019) — Topic switching increasing over time (snippet-level).

[25] [Charting mobility patterns in the scientific knowledge landscape](https://arxiv.org/abs/2302.13054) (Chakresh Kumar Singh, Liubov Tupikina, Fabrice Lécuyer, Michele Starnini, Marc Santolini; 2023) — Researcher knowledge mobility follows gravity model; explorers vs exploiters (C4 context).

> interdisciplinary explorers who pioneer new fields

Locator: Abstract

[26] [Adapting to LLMs: How Insiders and Outsiders Reshape Scientific Knowledge Production](https://arxiv.org/abs/2505.12666) (2025) — Insider vs outsider responses to LLMs (C4 context; snippet-level).

[27] [Forecasting the future of artificial intelligence with machine learning-based link prediction in an exponentially growing knowledge network (Science4Cast)](https://arxiv.org/pdf/2210.00881) (2023) — 64,719 AI concepts, 17.9M edges; link prediction delta years ahead with AUC; hand-crafted network features beat learned ones (RQ1 prior art).

> outperform methods that attempt to learn features

Locator: Introduction

[28] [Forecasting high-impact research topics via machine learning on evolving knowledge graphs (Impact4Cast)](https://arxiv.org/pdf/2402.08640) (Xuemei Gu, Mario Krenn; 2025) — OpenAlex-based evolving KG: 21,165,421 papers forming edges, 368,825 RAKE concepts from preprint servers; AUC>0.9 for most experiments; reusable Zenodo datasets.

> There are 21,165,421 out of 92,764,635 papers

Locator: Fig. 1 caption

[29] [Early Detection of Research Trends (Augur)](https://arxiv.org/abs/1912.08928) (Angelo Antonio Salatino; 2019) — Emergence anticipated by increased collaboration pace between ancestor areas; gold standard of 1,408 debutant topics (2000-2011); usable ground truth.

> outperformed four alternative approaches in terms of both precision and recall

Locator: Abstract

[30] [What Is an Emerging Technology?](https://arxiv.org/pdf/1503.00673) (Daniele Rotolo, Diana Hicks, Ben R. Martin; 2015) — Five attributes of emergence: radical novelty, relatively fast growth, coherence, prominent impact, uncertainty/ambiguity (snippet-level).

[31] [Identifying emerging topics in science and technology](https://www.sciencedirect.com/science/article/pii/S0048733314000298) (Henry Small, Kevin W. Boyack, Richard Klavans; 2014) — Direct-citation + co-citation Scopus models; drivers discovery 62%, technological innovation 38%, exogenous events 54% (snippet-level).

[32] [Emergence scoring to identify frontier R&D topics and key players](https://par.nsf.gov/servlets/purl/10076502) (Alan L. Porter, Jon Garner, Stephen F. Carley, Nils C. Newman; 2019) — Emergence indicator from novelty, persistence, growth, community (snippet-level).

[33] [TrendNets: Mapping Emerging Research Trends From Dynamic Co-Word Networks via Sparse Representation](https://arxiv.org/abs/1905.10960) (Marie Katsurai, Shunsuke Ono) — Smooth+sparse decomposition of dynamic co-word networks for bursty topics.

[34] [Identifying interdisciplinary emergence in the science of science: combination of network analysis and BERTopic](https://www.nature.com/articles/s41599-024-03044-y) (Keungoui Kim, Dieter F. Kogler, Sira Maliphol; 2024) — WoS category co-occurrence network across periods + BERTopic to detect interdisciplinary emergence (abstract via OpenAlex).

[35] [Knowledge Integration and Diffusion: Measures and Mapping of Diversity and Coherence](https://arxiv.org/pdf/1412.6683) (Ismael Rafols; 2014) — Diversity (variety, balance, disparity) x coherence framework; coherence measurement tentative.

> More coherence can be interpreted as an increase in integration

Locator: Sec. 2

[36] [A general framework for analysing diversity in science, technology and society](https://royalsocietypublishing.org/doi/10.1098/rsif.2007.0213) (Andy Stirling; 2007) — Rao-Stirling diversity heuristic (snippet-level).

[37] [Interdisciplinarity as Diversity in Citation Patterns among Journals: Rao-Stirling Diversity, Relative Variety, and the Gini coefficient](https://arxiv.org/pdf/1807.04115) (Loet Leydesdorff, Caroline S. Wagner, Lutz Bornmann; 2019) — DIV indicator combining variety, balance (Gini) and disparity ex post; RS anomalies.

> Using Rao-Stirling (RS) Diversity produces sometimes anomalous results.

Locator: Abstract

[38] [Bursty and Hierarchical Structure in Streams](https://link.springer.com/article/10.1023/A:1024940629314) (Jon Kleinberg; 2003) — Kleinberg burst detection automaton (baseline; snippet-level).

[39] [What is all this new MeSH about? Exploring the semantic provenance of new descriptors in the MeSH thesaurus](https://arxiv.org/abs/2101.08293) (Anastasios Nentidis, Anastasia Krithara, Grigorios Tsoumakas, Georgios Paliouras; 2021) — Only ~25% of new MeSH descriptors correspond to new emerging concepts: MeSH introduction is a weak ground truth.

> only about 25% of new MeSH descriptors correspond to new emerging concepts

Locator: Abstract

[40] [MeSH Concept Relevance and Knowledge Evolution: A Data-driven Perspective](https://arxiv.org/abs/2406.18792) (Jenny Copara, Nona Naderi, Gilles Falquet, Douglas Teodoro; 2024) — Citation-network-based relevance of MeSH concepts tracks terminology change.

[41] [Filling holes in science draws collective attention, but most higher-order holes remain unexplored](https://arxiv.org/abs/2608.28822) (Jiajie Luo, James A. Evans; 2026) — Very recent: persistent homology on concept embeddings; filling anticipated holes draws attention.

[42] [Can Recombination Displace Dominant Scientific Ideas](https://arxiv.org/abs/2506.15959) (Linzhuo Li, Yiling Lin, Lingfei Wu; 2025) — 41M papers; atypicality = extending established concepts into new topical areas, distinct from disruption.

> Atypicality is characteristic of work that extends established concepts into new topical areas

Locator: Abstract

[43] [The evolution of knowledge within and across fields in modern physics](https://arxiv.org/abs/2001.07199) (Ye Sun, Vito Latora; 2020) — Time-varying field-to-field knowledge-flow network; absorbing vs mutual vs back-nurture relations.

[44] [OpenAlex Help Center: Topics](https://help.openalex.org/data/topics/) — Topics from CWTS citation clustering; classifier on title, abstract, citations, journal; 4 domains, 26 fields, 252 subfields, 4,516 topics; ~12% of works lack topics.

> works that cite each other frequently land in the same cluster

Locator: Topics page

[45] [OpenAlex Help Center: Keywords](https://help.openalex.org/hc/en-us/articles/24736201130391-Keywords) — Documented: keywords drawn from topics' keyword sets, BGE-M3 scored, up to 5 per work (planning-verified; contradicted by live API on 2026-09-28).

[46] [OpenAlex Help Center: Concepts (deprecated)](https://help.openalex.org/data/concepts/) — Concepts documented as frozen, not assigned to new works, ~65k Wikidata-linked levels 0-5 (contradicted in part by API).

> New works are not tagged with them

Locator: Concepts page

[47] [OpenAlex Help Center: Deprecations](https://help.openalex.org/api/deprecations/) (2026) — Concepts deprecated in favour of topics; x_concepts to be removed; corpus parameter (Aug 2026) replaces include_xpac; last updated 22 Sep 2026.

> The legacy corpus controls are deprecated in favor of the first-class

Locator: include_xpac section

[48] [OpenAlex Help Center: Search](https://help.openalex.org/api/searching/) — search / search.exact / search.semantic; stemming and stop words; boolean, phrase, proximity, fuzzy; search $1 per 1k calls vs filter $0.10.

[49] [OpenAlex Help Center: Filter](https://help.openalex.org/api/filtering/) — Up to 100 OR values per filter; has_abstract filter exists.

> You can combine up to 100 values with

Locator: OR section

[50] [OpenAlex Help Center: Example costs](https://help.openalex.org/access/example-costs/) — Unit prices: singleton free; list+filter $0.10/1k; search $1/1k; semantic $1/1k; content $10/1k; $1/day free.

[51] [OpenAlex Help Center: Pricing overview](https://help.openalex.org/access/pricing/) (2026) — $1 free API usage per day per account; paid plans (page dated 11 Aug 2026).

[52] [OpenAlex Help Center: Snapshot](https://help.openalex.org/access/snapshot/) — Free S3 snapshot, no AWS account; ~626M records per format (Sept 2026); ~330 GB (snippet-level).

[53] [OpenAlex rewrite ("Walden") launch!](https://blog.openalex.org/openalex-rewrite-walden-launch/) (2025) — Nov 3 2025 rewrite; 190 million new works incl. datasets/software; faster fixes.

[54] [OpenAlex API live queries (executor observations, 2026-09-28)](https://api.openalex.org/works) (2026) — Observed: per_page=200 accepted; mesh.descriptor_ui invalid filter; /subfields=252, /topics=4,516, /keywords=65,004, /concepts=65,026; keywords==concepts in 11/12 sampled works; 10,514,189 of 32,364,822 2026 works carry concepts.id C41008148; core-source article zero-reference shares 29.0% (2005), 26.7% (2010), 23.0% (2016), 13.8% (2020); has_abstract 54.3%, 59.0%, 61.0%, 67.7%.

[55] [Reference Coverage Analysis of OpenAlex compared to Web of Science and Scopus](https://arxiv.org/abs/2401.16359) (Jack H. Culbert, Anne Hobert, Najko Jahn; 2025) — On 16.8M shared publications, OpenAlex reference counts and internal coverage comparable to WoS/Scopus; fewer abstracts.

> internal coverage rates comparable to both Web of Science and Scopus

Locator: Abstract

[56] [Sesame Open Science: open abstracts note](https://bmkramer.github.io/SesameOpenScience_site/thought/202411_open_abstracts/) (Bianca Kramer; 2024) — Springer Nature then Elsevier (Nov 2024) abstract removals in OpenAlex (planning-verified).

[57] [OpenAlex: Features, advantages and limitations of an open database for retrieving and analysing scholarly outputs](https://arxiv.org/pdf/2512.16434) — Abstract availability and author-disambiguation caveats (author records ~85M to ~53M; snippet-level).

[58] [Accuracy Assessment of OpenAlex and Clarivate Scholar ID with an LLM-Assisted Benchmark](https://arxiv.org/abs/2502.11610) (2025) — LLM-assisted benchmark of author ID accuracy (snippet-level; numbers not extracted).

[59] [OpenAlex blog: New features and usage-based pricing](https://blog.openalex.org/openalex-api-new-features-and-usage-based-pricing/) (2026) — API key required; usage-based pricing (planning-verified).

[60] [Applied Network Science collection: Networks for everyday life](https://link.springer.com/collections/fgcaicgjah) — Scope: theory, methods, applications for challenges in health, mobility, education, politics and related societal domains; rolling basis (snippet-level; page JS-gated).

[61] [Applied Network Science submission guidelines](https://link.springer.com/journal/41109/submission-guidelines) — Availability of data and materials statement required; Springer Nature LaTeX template (snippet-level).

[62] [Co-occurrence simplicial complexes in mathematics: identifying the holes of knowledge](https://doi.org/10.1007/s41109-018-0074-3) (Vsevolod Salnikov, Daniele Cassese, Renaud Lambiotte, Nick S. Jones; 2018) — ANS; higher-order word co-occurrence in mathematics.

[63] [Community evolution in patent networks: technological change and network dynamics](https://doi.org/10.1007/s41109-018-0090-3) (Yuan Gao, Zhen Cai Zhu, Raja Kali, Massimo Riccaboni; 2018) — ANS; stabilized Louvain community evolution in patent class networks.

[64] [Shannon entropy in time-varying semantic networks of titles of scientific paper](https://doi.org/10.1007/s41109-020-00292-0) (Marcelo do Vale Cunha, Carlos César Ribeiro Santos, Marcelo Albano Moret, Hernane Borges de Barros Pereira; 2020) — ANS; entropy of clique networks of title words over time.

[65] [The mobility network of scientists: analyzing temporal correlations in scientific careers](https://doi.org/10.1007/s41109-020-00279-x) (Giacomo Vaccario, Luca Verginer, Frank Schweitzer; 2020) — ANS; 3.5M career trajectories, higher-order mobility networks.

[66] [Author multidisciplinarity and disciplinary roles in field of study networks (ANS, doi:10.1007/s41109-022-00517-4)](https://europepmc.org/article/PMC/PMC9673898) (Eoghan Cunningham, Barry Smyth, Derek Greene; 2022) — ANS; FoS networks and topic role analysis; structure exemplar with separate Related work section.

[67] [Mapping change in higher-order networks with multilevel and overlapping communities](https://doi.org/10.1007/s41109-023-00572-5) (Anton Holmgren, Daniel Edler, Martin Rosvall; 2023) — ANS; alluvial diagrams for community change incl. organization of science.

[68] [Exploring temporal community evolution: algorithmic approaches and parallel optimization for dynamic community detection](https://doi.org/10.1007/s41109-023-00592-1) (Naw Safrin Sattar, Aydın Buluç, Khaled Z. Ibrahim, Shaikh Arifuzzaman; 2023) — ANS; dynamic community detection methods.

[69] [Statistically validated network for analysing textual data](https://doi.org/10.1007/s41109-025-00693-z) (Andrea Simonetti, Alessandro Albano, Michele Tumminello, Tiziana Di Matteo; 2025) — ANS; word-document SVN + Leiden topic model; null-model backbone for co-occurrence.

[70] [Appraising discrepancies and similarities in semantic networks using concept-centered subnetworks](https://doi.org/10.1007/s41109-021-00408-0) (Darkhan Medeuov, Camille Roth, Kseniia A. Puzyreva, Nikita Basov; 2021) — ANS; ego-subnetwork overlap indices = neighbourhood turnover measures.

[71] [Multiplex flows in citation networks](https://doi.org/10.1007/s41109-017-0035-2) (Benjamin Renoust, Vivek Claver, Jean-François Baffier; 2017) — ANS; stream-of-knowledge inheritance in citation networks.

[72] [Short- and long-term temporal network prediction based on network memory](https://doi.org/10.1007/s41109-023-00597-w) (Li Kun Zou, Alberto Ceria, Huijuan Wang; 2023) — ANS; memory-based temporal link prediction baseline.

[73] [Detection of dynamic communities in temporal networks with sparse data](https://doi.org/10.1007/s41109-024-00687-3) (Nataša Djurdjevac Conrad, Elisa Tonello, Johannes Zonker, Heike Siebert; 2025) — ANS; dynamic communities under sparse data.

[74] [An agent-based model of citation behavior](https://doi.org/10.1007/s41109-025-00766-z) (George Chacko, Minhyuk Park, Vikram Ramavarapu, Ananth Grama, Pablo Robles-Granda; 2026) — ANS; generative citation ABM with PA, recency, fitness, community (null for C0).

[75] [The impact factor game: an agent-based exploration of self-citation influence and interdisciplinary dynamics on impact metrics](https://doi.org/10.1007/s41109-025-00725-8) (Luiz Gabriel Correia, Jesús Pascual Mena-Chalco; 2025) — ANS; indicator gaming ABM (policy framing).

[76] [Changes in patient-sharing patterns after oncologist departures in rural and urban settings (ANS 2026)](https://europepmc.org/article/PMC/PMC12775101) (2026) — Structure exemplar: Introduction, Methods, Results, Discussion(+Limitations), Conclusions; Abbreviations, Acknowledgements, Author contributions, Funding, Data availability, Declarations/Competing interests; 3 keywords; ~195-word abstract.

[77] [Navigation on temporal networks (ANS 2025)](https://europepmc.org/article/PMC/PMC11926000) (2025) — Structure exemplar incl. Availability of data and materials and Declarations/Competing interests.

[78] [Temporal dynamics of the friendship paradox in a smartphone communication network (ANS 2025)](https://europepmc.org/article/PMC/PMC12102006) (2025) — Structure exemplar with Materials and methods/Data and Declarations incl. ethics and consent.

[79] [The association of prescriber prominence in a shared-patient physician network with their patients' risky prescribing (ANS 2025)](https://europepmc.org/article/PMC/PMC12279612) (2025) — Structure exemplar; 7 keywords; ~296-word abstract.

[80] [Beyond Citations: Measuring Idea-level Knowledge Diffusion from Research to Journalism and Policy-making](https://arxiv.org/pdf/2511.03378) (Yangliu Fan, Kilian Buehling, Volker Stocker; 2025) — Idea-level diffusion via mentions and embedding regression across domains.

[81] [The increasing fragmentation of global science limits the diffusion of ideas](https://arxiv.org/abs/2404.05861) (Alexander J. Gates, Jianjian Gao, Indraneel Mane; 2025) — Signed national citation-preference network influences international diffusion of ideas.

## Verification

Numbered citations resolve to unique listed sources. Passage checks test text occurrence, not claim truth or entailment. Author/year metadata and locators are not independently verified. Details: `research_verification.json`.

- Source [1]: text found — almost no explanatory power for endogenous citation activity
- Source [1]: text found — the exogenous count task achieves strong and consistent predictive power
- Source [1]: text found — Growth-normalised targets; stratified 80/20 train–test split; Optuna-tuned
- Source [2]: text found — as its sticking factor divided by its sparking factor
- Source [3]: text found — We estimate the effectiveness of adoption of the idea in the three communities
- Source [4]: text found — mainly act as sources of the diaspora
- Source [5]: text found — they face difficulties to overcome disciplinary boundaries
- Source [8]: text found — fit with extant research traditions
- Source [11]: text found — take the minimum of the pairwise conditional probabilities
- Source [12]: text found — significantly more accurate predictor of the fields that
- Source [16]: text found — rather than by the actual size of the neighborhood
- Source [17]: text found — about seven times as precise as random guess and over three times as precise as prediction
- Source [18]: text found — connector hubs, i.e., hubs with many links to most of the other modules
- Source [21]: text found — only 3% contain AI-related keywords
- Source [22]: text found — remain confined in the different subfields and are not transferred from one subfield to another
- Source [25]: text found — interdisciplinary explorers who pioneer new fields
- Source [27]: text found — outperform methods that attempt to learn features
- Source [28]: text found — There are 21,165,421 out of 92,764,635 papers
- Source [29]: text found — outperformed four alternative approaches in terms of both precision and recall
- Source [35]: text found — More coherence can be interpreted as an increase in integration
- Source [37]: text found — Using Rao-Stirling (RS) Diversity produces sometimes anomalous results.
- Source [39]: text found — only about 25% of new MeSH descriptors correspond to new emerging concepts
- Source [42]: text found — Atypicality is characteristic of work that extends established concepts into new topical areas
- Source [44]: text found — works that cite each other frequently land in the same cluster
- Source [46]: text found — New works are not tagged with them
- Source [47]: text found — The legacy corpus controls are deprecated in favor of the first-class
- Source [49]: text found — You can combine up to 100 values with
- Source [55]: text found — internal coverage rates comparable to both Web of Science and Scopus

## Follow-up Questions

- Does host anchoring (A*) predict newcomer uptake Y1 net of relatedness density, momentum and the co-transfer score CT, and is the sign stable when subfields are defined by venue habitat instead of OpenAlex's citation-derived topics?
- Is the OpenAlex keywords == legacy-concepts behaviour (observed 2026-09-28) a stable post-Walden design choice or a transient regression, and how precise are level-2-5 concept tags on titles-only works compared with surface-form (RAKE / meme-score) concepts?
- What exact operationalisation and effect sizes did Cheng et al. (2023, ASR) use for 'fit with extant research traditions'? Obtaining the full text decides whether C1's margin is MEDIUM-HIGH or only MEDIUM.

---
*Generated by AI Inventor Pipeline*
