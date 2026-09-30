# Style notes

These papers use short, declarative sentences mixed with longer ones carrying qualifications. First person "we" is standard. Numbers are stated plainly, with units and comparisons in the same sentence. Citation density is high: 2-4 per paragraph in introductions, inline with claims. Hedging is moderate and specific ("suggests", "indicates") rather than blanket.

---

## Paper 1: Maillart et al. (2026) — "Forecasting Conceptual Diffusion in Science: The Case of Quantum Computing"
arXiv:2606.03919, 2026

### Abstract
"Understanding and anticipating scientific change requires models that distinguish between endogenous consolidation and exogenous diffusion of scientific concepts. Using the quantum computing subtree of concepts in OpenAlex, we construct a temporally resolved concept co-occurrence network and track each concept pair through its upstream citation lineage and downstream diffusion. We train LightGBM models on distributional and diversity-aware features to predict four outcomes: endogenous reinforcement, exogenous diffusion, their ratio, and diffusion entropy. After controlling for overall publication growth of the scientific body, endogenous reinforcement proves largely unpredictable in the primary quantum-computing benchmark. In contrast, exogenous diffusion and entropy are strongly predictable (R² up to 0.78) and are driven by upstream heterogeneity, citation breadth, and distributional dispersion, as shown by SHAP analyses; replications on robotics, advanced materials, and neuro implants confirm that exogenous diffusion remains the top-ranked target across fields (R²test ≈ 0.60–0.87), while endogenous predictability rises markedly in neuro implants (R²test = 0.83), indicating that the quantum-computing asymmetry does not generalise uniformly."

### First paragraph of introduction
"Scientific progress unfolds through the continual recombination and diffusion of ideas. Advances in large-scale bibliometrics and open knowledge graphs now make these processes observable at scale, enabling empirical analyses of how conceptual relationships emerge, consolidate, and propagate. Research in the field of science of science shows that innovation is shaped by structured patterns of conceptual integration, collaboration, and cumulative growth rather than isolated breakthroughs. Concepts interact and co-occur within an evolving knowledge ecosystem, producing the complex dynamics that characterize scientific change."

### Results paragraph
"Table 2 reports predictive performance on the censoring-free cohort (Methods, Appendix A) across four related tasks that capture complementary dimensions of conceptual propagation: endogenous count (self-reinforcement within the focal pair's downstream lineage), exogenous count (citations by papers with other concept pairs), the endo/exo ratio, and entropy (diffusion diversity). The reported metrics – R², mean absolute error (MAE), and root mean squared logarithmic error (RMSLE) – are evaluated on both training and held-out test sets. Overall, the model shows consistent generalisation, with only a modest drop from training to test performance, indicating appropriate regularisation and limited overfitting. Yet, predictive strength varies markedly across tasks, revealing asymmetries in the underlying conceptual dynamics. The model exhibits almost no explanatory power for endogenous citation activity (R²test = 0.0179), suggesting that self-referential reinforcement within a focal concept pair own lineage is largely unpredictable from available features."

### Limitations paragraph
"Several limitations qualify these findings. The analysis relies on OpenAlex concept annotations, which may introduce noise at fine semantic resolutions, and on yearly temporal aggregation, which can smooth short-lived dynamics. The focus on concept pairs is a deliberate first-order projection of the underlying co-occurrence hypergraph and excludes higher-order conceptual structures (concept triples, higher-arity simplices) that may capture additional aspects of scientific change. A further temporal limitation concerns right-censoring of the downstream window."

---

## Paper 2: Maillart et al. (2026) — "Explainable Forecasting of Scientific Breakthroughs from Concept Network Dynamics"
arXiv:2606.03864, 2026

### Abstract
"We introduce an explainable machine-learning approach that forecasts the structural precursors of scientific breakthroughs—the emergence and intensification of links between research concepts—by modelling how OpenAlex concept networks evolve over time. Using 59 semantic and topological features, a two-stage LightGBM model jointly predicts the formation and the future weight of concept pairs, adding a regression stage that quantifies expected intensity to prior link-existence forecasts. Relative to the state of the art, the approach improves accuracy and explainability at once: comparative validation across four technology and biomedical domains yields ROC–AUC in [0.954, 0.967] at all horizons without re-tuning, exceeding the ~0.90 of prior models, while every forecast rests on structural, auditable features rather than opaque embeddings."

### First paragraph of introduction
"Scientific breakthroughs increasingly emerge from combining ideas across rapidly evolving knowledge networks. This acceleration, amplified by open science and distributed collaboration, is reshaping how science is practised and governed, shifting discovery from isolated insight to machine-augmented, cross-disciplinary interaction. These dynamics challenge traditional foresight approaches such as expert panels, Delphi methods, and bibliometric trend analyses, which were originally designed for slower and more predictable innovation landscapes."

### Results paragraph
"The model accurately predicts the appearance of new conceptual links in the quantum computing domain. Classification performance remains high across prediction horizons, with accuracy decreasing only slightly from 0.975 at one year to 0.950 at five years, while ROC–AUC remains consistently strong (≥0.95). This stability indicates that signals associated with future link formation are present in the local and mesoscopic structure of the concept network before new connections become visible in the literature."

### Limitations paragraph
"Four limitations bound the present results. First, the framework forecasts structural precursors of breakthroughs (link emergence and intensification) rather than retrospective bibliometric impact; whether predicted precursors disproportionately give rise to high-disruption or high-citation works is an empirical question that should be tested by joining our predictions to OpenAlex-keyed impact data. Second, the primary quantum-computing evaluation uses the full in-paper protocol (stratified split, tuned hyperparameters); the comparative validation in Section 5.4 uses an OpenAlex validation subsample (~40% of snapshot volume), fixed hyperparameters, and a 2022–2023 label-year holdout—so absolute counts and RMSLE need not match the main results digit for digit."

---

## Paper 3: Chavalarias & Cointet (2013) — "Phylomemetic Patterns in Science Evolution—The Rise and Fall of Scientific Fields"
PLoS ONE 8(2):e54847, 2013

### Abstract
"We introduce an automated method for the bottom-up reconstruction of the cognitive evolution of science, based on big-data issued from digital libraries, and modeled as lineage relationships between scientific fields. We refer to these dynamic structures as phylomemetic networks or phylomemies, by analogy with biological evolution; and we show that they exhibit strong regularities, with clearly identifiable phylomemetic patterns. Some structural properties of the scientific fields - in particular their density -, which are defined independently of the phylomemy reconstruction, are clearly correlated with their status and their fate in the phylomemy (like their age or their short term survival). Within the framework of a quantitative epistemology, this approach raises the question of predictibility for science evolution, and sketches a prototypical life cycle of the scientific fields: an increase of their cohesion after their emergence, the renewal of their conceptual background through branching or merging events, before decaying when their density is getting too low."

### First paragraph of introduction
"How is science evolving? Is it possible to map the landscapes of science and its transformations? Can we automatically decipher the history of a research field, monitor emerging fields and detect research hybridization events? Numerous theories, and more or less conceptual models of science evolution have been contemplated in the philosophy of science—and in Science & Technology Studies."

### Results paragraph
"After the removal of interlocked clusters, the phylomemetic network of all fields of more than four elements features approximately 700 non-isolated nodes. It comprises different disconnected components, corresponding to large domains of embryology clustered in a time-consistent manner."

### Discussion paragraph
"Although further investigations would be required to appreciate the full range of evolutionary patterns and the various driving forces which define a field's destiny, these preliminary results demonstrate the importance of special events, and the need to study several levels of organization - from the micro-level of terms to the global structure of the phylomemy."

---

## Paper 4: Fontaine et al. (2024) — "Epistemic integration and social segregation of AI in neuroscience"
Applied Network Science 9, 8, 2024

### Abstract
"In recent years, Artificial Intelligence (AI) shows a spectacular ability of insertion inside a variety of disciplines which use it for scientific advancements and which sometimes improve it for their conceptual and methodological needs. According to the transverse science framework originally conceived by Shinn and Joerges, AI can be seen as an instrument which is progressively acquiring a universal character through its diffusion across science. In this paper we address empirically one aspect of this diffusion, namely the penetration of AI into a specific field of research. Taking neuroscience as a case study, we conduct a scientometric analysis of the development of AI in this field. We especially study the temporal egocentric citation network around the articles included in this literature, their represented journals and their authors linked together by a temporal collaboration network. We find that AI is driving the constitution of a particular disciplinary ecosystem in neuroscience which is distinct from other subfields, and which is gathering atypical scientific profiles who are coming from neuroscience or outside it."

### First paragraph of introduction
"In recent years, Artificial Intelligence (AI) has been continuously spreading across science. The associated worldwide scientific production and the amount of dedicated funding programs for technological developments supported both by academia and industry, are spectacularly growing (Baruffaldi et al., 2020; Gao & Wang, 2023; Liu, Shapira, & Yue, 2021), and the outputs of such research are touching many aspects of various scientific disciplines."

### Results paragraph (with numbers)
"The share of AI publications in neuroscience reaches only 10% of the number of publications at its highest stage situated at the end of the studied period, which means that the use of the AI keywords of our list in neuroscience remains rather limited, even today."

"By considering neuroscience as the subset of disciplines composed of the WOS disciplines Neurosciences, Clinical Neurology and Neuroimaging, we observe that Q and Q0 are more involved in that field of research, with respectively 77% of the authors in the first and 78% of those in the second with a disciplinary profile that includes one or more of the fields of research associated with neuroscience. On the contrary, 45% of the authors in Q1 and 42% of the authors in Q2 have a disciplinary profile that includes such JSCs."

### Discussion paragraph
"Under such an hypothesis, we could explore more precisely on the one hand the expansion of adjacent possible of neuroscience caused directly by AI, and on the other hand..."

---

## Section outlines

### Maillart et al. (2026a) — "Forecasting Conceptual Diffusion in Science"
1. Introduction
2. Background
3. Model & Hypotheses
4. Methods & Predictive Models
5. Results
6. Discussion & Implications
7. Conclusion

Method organised by: pipeline stage (data → network construction → feature engineering → model).
Results organised by: prediction target (endogenous, exogenous, ratio, entropy), then cross-domain replication.

### Maillart et al. (2026b) — "Explainable Forecasting of Scientific Breakthroughs"
1. Introduction
2. Related Work
3. Theoretical Approach
4. Methods (4.1 Comparative validation protocol)
5. Results (5.1 Pair appearance, 5.2 Regression, 5.3 Use cases, 5.4 Cross-domain robustness)
6. Discussion (6.1 Policy architecture, 6.2 Limitations)
7. Conclusion

Method organised by: model stage (classification → regression → validation protocol).
Results organised by: task type, then cross-domain validation, then case studies.

### Chavalarias & Cointet (2013) — "Phylomemetic Patterns in Science Evolution"
1. Introduction
2. Materials and Methods
3. Key-phrase Extraction
4. Measuring Proximities
5. Clustering
6. Tracking Meso-dynamics
7. Phylomemetic Branches
8. Related Work
9. Results
10. Phylomemetic Patterns and Cluster Density Index
11. The Jolting Routes of Paradigms
12. Discussion

Method organised by: pipeline component (extraction → proximity → clustering → tracking).
Results organised by: phenomenon (patterns → density → paradigm routes).

### Fontaine et al. (2024) — "Epistemic integration and social segregation of AI in neuroscience"
1. Introduction
2. Literature Review
3. Data and Methods (3.1 Corpus, 3.2 Disciplinary landscape, 3.3 Authors and collaborations)
4. Results (4.1 AI literature growth, 4.2 Disciplinary proximity, 4.3 Journal confinement, 4.4 Collaboration patterns)
5. Discussion
6. Conclusion

Method organised by: data layer (corpus → disciplines → authors).
Results organised by: analytical dimension (growth → proximity → journals → collaboration).
