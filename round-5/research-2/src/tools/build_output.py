#!/usr/bin/env python3
"""Assemble the structured research output (.terminal_claude_agent_struct_out.json) and bib_ids.txt.

Sources are numbered exactly as cited in research_report.md. Supporting passages are copied from the
pages/PDFs fetched in this session (see cache/ and reproducibility.md). S2 = Semantic Scholar Graph API record
(abstract text), used where the publisher page was gated.
"""
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
S2 = "https://api.semanticscholar.org/graph/v1/paper/{}?fields=title,year,abstract"
CR = "https://api.crossref.org/works/{}"


def P(q, loc=None):
    return {"quote": q, "locator": loc}


# (index, url, title, authors|None, year|None, summary, [passages])
SRC = [
    (1, "https://journals.sagepub.com/doi/full/10.1177/00031224231166955", "How New Ideas Diffuse in Science (American Sociological Review 88(3):522-561, doi:10.1177/00031224231166955)",
     ["Mengjie Cheng", "Daniel Scott Smith", "Xiang Ren", "Hancheng Cao", "Sanne Smith", "Daniel A. McFarland"], 2023,
     "VERBATIM-FULLTEXT. Nearest neighbour. Unit = idea-year (56,540 new WoS terms, 995,945 idea-years); outcome = count of articles the idea diffuses into at t+1 (not binary 'core'); ideational embeddedness = mean pairwise cosine similarity of the focal term's neighbour terms in a GLOBAL word2vec embedding of the prior-decade co-occurrence network (+1 SD -> +25% articles); social embeddedness -> -15%; multilevel over-dispersed Poisson with random intercepts; 'Interdisciplinary' control = term entropy across NRC subject codes.",
     [P("We construct our dependent variable as the number of articles a new idea diffuses into the year ahead", "Data and Measures, dependent variable"),
      P("these 56,540 new ideas sum to 995,945 observations at the idea-year level", "Data and Measures"),
      P("we compute cosine similarities of these embedding dimensions on each neighbor-pair", "Measures: Ideational embeddedness"),
      P("we construct a semantic network for the prior decade", "Measures: Ideational embeddedness"),
      P("Therefore, we use an over-dispersed Poisson regression model to model the data", "Statistical Approach"),
      P("a one standard deviation change in social embeddedness is associated with a 15 percent", "Results: The Effects of Ideational and Social Ecology"),
      P("The more embedded it is within densely interconnected extant ideas, the more a new idea will diffuse.", "Hypothesis 6a"),
      P("computed as a term’s average entropy across NRC discipline subject codes", "Table 2, control 'Interdisciplinary'")]),
    (2, "https://www.kellogg.northwestern.edu/faculty/uzzi/htm/papers/science-2013-uzzi-468-72.pdf", "Atypical Combinations and Scientific Impact (Science 342:468-472, doi:10.1126/science.1240474)",
     ["Brian Uzzi", "Satyam Mukherjee", "Michael Stringer", "Benjamin Jones"], 2013,
     "VERBATIM-FULLTEXT. Paper-level reference journal-pair z-scores vs randomised null; hit = top-5% citations; conventional mass + atypical tail twice as likely to be a hit.",
     [P("Papers of this type were twice as likely to be highly cited works.", "Abstract"),
      P("a z score below zero represents a journal pair that occurs less often than expected by chance", "p. 469")]),
    (3, "https://arxiv.org/pdf/1302.6906", "Tradition and Innovation in Scientists' Research Strategies (ASR 80(5):875-908, doi:10.1177/0003122415601618)",
     ["Jacob G. Foster", "Andrey Rzhetsky", "James A. Evans"], 2015,
     "VERBATIM-FULLTEXT (arXiv version). Research strategies defined on chemical-relationship networks (MEDLINE); risky (innovative) strategies ignored more often but more likely to win high impact.",
     [P("They can consolidate existing knowledge clusters, or bridge distant ones.", "Abstract"),
      P("Research following a risky strategy is more likely to be ignored but also more likely to achieve high impact and recognition.", "Abstract")]),
    (4, "https://arxiv.org/pdf/1909.02063", "The Diversity-Innovation Paradox in Science (PNAS 117(17):9284-9291, doi:10.1073/pnas.1915378117)",
     ["Bas Hofstra", "Vivek V. Kulkarni", "Sebastian Munoz-Najar Galvez", "Bryan He", "Dan Jurafsky", "Daniel A. McFarland"], 2020,
     "VERBATIM-FULLTEXT. Unit = thesis and its new concept links; novelty = # new links; impactful novelty = uptake per new link; distal new links receive far less uptake.",
     [P("are adopted in ensuing documents of each year (uptake per new link)", "Innovation as Novelty and Impactful Novelty in Text"),
      P("more distal new links between concepts receive far less uptake", "Results")]),
    (5, "https://arxiv.org/pdf/1709.03319", "Quantifying patterns of research-interest evolution (Nature Human Behaviour 1:0078, doi:10.1038/s41562-017-0078)",
     ["Tao Jia", "Dashun Wang", "Boleslaw K. Szymanski"], 2017,
     "VERBATIM-FULLTEXT. Interest change is exponentially distributed; subject proximity drives moves (random-walk model). Rival 'topical proximity' reading of the adopter result.",
     [P("research interest change follows a reproducible pattern characterized by an exponential distribution", "Abstract"),
      P("she is more likely to choose a subject related to the current one than moving to a totally new", "Results")]),
    (6, "https://arxiv.org/pdf/1602.08409", "The research space: using career paths to predict the evolution of the research output of individuals, institutions, and nations (Scientometrics 109(3):1695-1709, doi:10.1007/s11192-016-2125-9)",
     ["Miguel R. Guevara", "Dominik Hartmann", "Manuel Aristarán", "Marcelo Mendoza", "César A. Hidalgo"], 2016,
     "VERBATIM-FULLTEXT. Relatedness (co-publication career paths) predicts which fields units ENTER; not post-entry uptake.",
     [P("significantly more accurate predictor of the fields that individuals and organizations will enter in the future than citation based science maps", "Abstract")]),
    (7, "https://research-portal.uu.nl/ws/files/54934557/Hidalgo2018_Chapter_ThePrincipleOfRelatedness.pdf", "The Principle of Relatedness (Springer Proceedings in Complexity, pp. 451-457, doi:10.1007/978-3-319-96661-8_46)",
     ["César A. Hidalgo", "Pierre-Alexandre Balland", "Ron Boschma", "Mercedes Delgado", "Maryann Feldman", "Koen Frenken"], 2018,
     "VERBATIM-FULLTEXT. Principle: probability a region enters/exits an activity grows with related activities present; 8-20x entry probability. (Plan's arXiv id 1807.03148 is wrong.)",
     [P("an empirical principle describing the probability that a region enters—or exits—an economic activity as a function of the number of related activities present in that location", "Abstract"),
      P("the probability of entering an activity rises between eight-fold and twenty-fold", "Sec. 2")]),
    (8, "https://files.eric.ed.gov/fulltext/ED501453.pdf", "Detailed review of Rogers' Diffusion of Innovations theory (Sahin 2006, TOJET; quoting Rogers 2003, Diffusion of Innovations, 5th ed.)",
     ["Ismail Sahin"], 2006,
     "SECONDARY-QUOTE of Rogers (2003, p. 15) compatibility definition; A_cont is an entry-level network operationalisation of compatibility with the host.",
     [P("compatibility is the degree to which an innovation is perceived as consistent with the existing values, past experiences, and needs of potential adopters", "Compatibility section, citing Rogers 2003 p. 15")]),
    (9, "https://josephmahoney.web.illinois.edu/BA545_Fall%202022/Cohen%20and%20Levinthal%20(1990).pdf", "Absorptive Capacity: A New Perspective on Learning and Innovation (ASQ 35(1):128-152, doi:10.2307/2393553)",
     ["Wesley M. Cohen", "Daniel A. Levinthal"], 1990,
     "VERBATIM-FULLTEXT. Absorptive capacity is largely a function of prior related knowledge: one of two readings of the adopter result.",
     [P("We label this capability a firm's absorptive capacity and suggest that it is largely a function of the firm's level of prior related knowledge.", "Abstract")]),
    (10, "https://www.nature.com/articles/s41467-023-36741-4", "Surprising combinations of research contents and contexts are related to impact and emerge with scientific outsiders from distant disciplines (Nat Commun 14:1641, doi:10.1038/s41467-023-36741-4)",
     ["Feng Shi", "James Evans"], 2023,
     "VERBATIM-FULLTEXT (nature.com open access). Content-context hypergraph surprise predicts top-10% citations; emerges when scientists publish to distant fields. Complementary tension: impact via distance vs our local uptake via familiarity.",
     [P("surprise in terms of unexpected combinations of contents and contexts predicts outsized impact (within the top 10% of citations)", "Abstract"),
      P("most commonly when scientists from one field publish problem-solving results to an audience from a distant field", "Abstract")]),
    (11, "https://arxiv.org/pdf/1404.3757", "Inheritance Patterns in Citation Networks Reveal Scientific Memes (PRX 4:041036, doi:10.1103/PhysRevX.4.041036)",
     ["Tobias Kuhn", "Matjaž Perc", "Dirk Helbing"], 2014,
     "VERBATIM-FULLTEXT. Meme propagation score pooled over science (iter-1 verified).",
     [P("as its sticking factor divided by its sparking factor", "Results")]),
    (12, "https://arxiv.org/pdf/1503.00673", "What is an emerging technology? (Research Policy 44(10):1827-1843, doi:10.1016/j.respol.2015.06.006)",
     ["Daniele Rotolo", "Diana Hicks", "Ben R. Martin"], 2015,
     "VERBATIM-FULLTEXT. Five attributes of emergence; RQ1 framing.",
     [P("(i) radical novelty, (ii) relatively fast growth, (iii) coherence, (iv) prominent impact, and (v) uncertainty and ambiguity", "Sec. 3")]),
    (13, "https://peerj.com/articles/cs-119/", "How are topics born? Understanding the research dynamics preceding the emergence of new areas (PeerJ CS 3:e119, doi:10.7717/peerj-cs.119)",
     ["Angelo A. Salatino", "Francesco Osborne", "Enrico Motta"], 2017,
     "VERBATIM-FULLTEXT. Emergence preceded by increase in collaboration pace between ancestor topics; RQ1 contrast (not confirmed at concept level in our data).",
     [P("the emergence of a new topic is anticipated by a significant increase in the pace of collaboration between relevant research areas", "Abstract")]),
    (14, "https://arxiv.org/pdf/0904.1439", "Towards an explanatory and computational theory of scientific discovery (J Informetrics 3(3):191-209, doi:10.1016/j.joi.2009.03.004)",
     ["Chaomei Chen", "Yue Chen", "Mark Horowitz", "Haiyan Hou", "Zeyuan Liu", "Donald Pellegrino"], 2009,
     "VERBATIM-FULLTEXT. Confirmed as the brokerage/structural-hole 'Chen 2009' paper; brokerage prediction ruled out in our data.",
     [P("The central premise is that connecting otherwise disparate patches of knowledge is a valuable mechanism of creative thinking", "Abstract")]),
    (15, "https://www.cs.stonybrook.edu/~leman/courses/12CSE590/readings/Burt04StructureHole.pdf", "Structural Holes and Good Ideas (AJS 110(2):349-399, doi:10.1086/421787)",
     ["Ronald S. Burt"], 2004,
     "VERBATIM-FULLTEXT. Brokers across structural holes have good ideas.",
     [P("people who stand near the holes in a social structure are at higher risk of having good ideas", "Introduction")]),
    (16, "https://pmc.ncbi.nlm.nih.gov/articles/PMC2373389/", "A general framework for analysing diversity in science, technology and society (J R Soc Interface 4:707-719, doi:10.1098/rsif.2007.0213)",
     ["Andy Stirling"], 2007,
     "Read in full text via PMC during this session (PMC now serves a stub to fetchers, so no exact passage is kept). Variety, balance, disparity; breadth indicators measure occupancy.",
     []),
    (17, "https://arxiv.org/pdf/1412.6683", "Knowledge Integration and Diffusion: Measures and Mapping of Diversity and Coherence",
     ["Ismael Rafols"], 2014,
     "VERBATIM-FULLTEXT (iter-1 verified). Diversity x coherence; coherence needed to speak of integration.",
     [P("More coherence can be interpreted as an increase in integration", "iter-1 verified passage")]),
    (18, "https://www.nber.org/system/files/working_papers/w22180/w22180.pdf", "Bias against novelty in science: A cautionary tale for users of bibliometric indicators (Research Policy 46(8):1416-1436, doi:10.1016/j.respol.2017.06.006; NBER w22180)",
     ["Jian Wang", "Reinhilde Veugelers", "Paula Stephan"], 2017,
     "VERBATIM-FULLTEXT (NBER). Novel papers more cited in foreign fields, not home field; delayed recognition. Tension with our host-familiar framing result.",
     [P("novel research is significantly more highly cited in “foreign” fields but not in its “home” field", "Abstract"),
      P("We also find strong evidence of delayed recognition of novel papers", "Abstract")]),
    (19, "https://arxiv.org/pdf/2103.03398", "New directions in science emerge from disconnection and discord (J Informetrics 16(1):101234, doi:10.1016/j.joi.2021.101234)",
     ["Yiling Lin", "James A. Evans", "Lingfei Wu"], 2022,
     "VERBATIM-FULLTEXT. Atypical papers ~2x more likely to disrupt; slow process.",
     [P("Atypical papers are nearly two times more likely to disrupt science than conventional papers", "Abstract")]),
    (20, "https://research.vu.nl/ws/portalfiles/portal/123105906/Ideas_with_impact.pdf", "Ideas with impact: How connectivity shapes idea diffusion (Research Policy 49(1):103881, doi:10.1016/j.respol.2019.103881)",
     ["Dirk Deichmann", "Christine Moser", "Julie M. Birkholz", "Adina Nerghes", "Peter Groenewegen", "Shenghui Wang"], 2020,
     "VERBATIM-FULLTEXT. PARTLY: paper-level content-network betweenness (shared title words) -> citations; CS conferences 2006-2012.",
     [P("operationalize connectivity by investigating an idea's betweenness centrality in a content network", "Sec. 2 hypotheses"),
      P("Our study focuses on academic conference publications and the co-authorship data of a community of computer science researchers from 2006 to 2012", "Abstract")]),
    (21, "https://research.dial.uclouvain.be/server/api/core/bitstreams/2e847eb3-54f9-4462-afc8-e3a26d629472/content", "What makes econometric ideas popular: The role of connectivity (Research Policy 53(7):105025, doi:10.1016/j.respol.2024.105025)",
     ["Bertrand Candelon", "Marc Joëts", "Valérie Mignon"], 2024,
     "VERBATIM-FULLTEXT. PARTLY: topic/social connectivity of econometrics papers -> citations via a hurdle count model; also a 2024 scientometric hurdle precedent (K1).",
     [P("Using a hurdle count model, we show that both content and social connectivity among the authors enhance the likelihood of non-zero citation counts", "Abstract")]),
    (22, "https://econpapers.repec.org/article/eeerespol/v_3a43_3ay_3a2014_3ai_3a1_3ap_3a107-114.htm", "Scientific knowledge dynamics and relatedness in biotech cities (Research Policy 43(1):107-114, doi:10.1016/j.respol.2013.07.009)",
     ["Ron Boschma", "Gaston Heimeriks", "Pierre-Alexandre Balland"], 2014,
     "ABSTRACT. PARTLY: host (city)-specific emergence of new topics depends on relatedness to the city's topic portfolio; entry, not newcomer uptake.",
     [P("We assess the extent to which the emergence of new research topics and the disappearance of existing topics in cities are dependent on their degree of scientific relatedness with existing topics in those cities.", "Abstract")]),
    (23, S2.format("DOI:10.1016/j.shpsa.2017.12.001"), "The diffusion of scientific innovations: A role typology (Studies in History and Philosophy of Science 77:64-80, doi:10.1016/j.shpsa.2017.12.001)",
     ["Catherine Herfeld", "Malte Doehne"], 2019,
     "ABSTRACT (S2). PARTLY: ideas must be conceptually translated to field-specific problems before adoption; conceptual + one case.",
     [P("novel ideas must be elaborated on and conceptually translated before they can be adopted and applied to field-specific problems", "Abstract")]),
    (24, S2.format("DOI:10.1016/j.socnet.2021.01.001"), "Adoption and adaptation: A computational case study of the spread of Granovetter's weak ties hypothesis (Social Networks 66:10-25, doi:10.1016/j.socnet.2021.01.001)",
     ["Anna Keuchenius", "Petter Törnberg", "Justus Uitermark"], 2021,
     "ABSTRACT (S2). PARTLY: communities adapt one idea differently; single case, no across-host uptake test.",
     [P("we study how different communities in this network interpret and develop Granovetter's hypothesis in distinct ways", "Abstract")]),
    (25, "https://www.nature.com/articles/s41598-020-71009-7", "Knowledge and social relatedness shape research portfolio diversification (Scientific Reports 10:14232, doi:10.1038/s41598-020-71009-7)",
     ["Giorgio Tripodi", "Francesca Chiaromonte", "Fabrizio Lillo"], 2020,
     "ABSTRACT. PARTLY: author-level diversification shaped by topic and social relatedness (bipartite networks).",
     [P("Using bipartite networks, we compute a measure of topic similarity and a measure of social proximity.", "Abstract")]),
    (26, "https://arxiv.org/pdf/2010.06657", "Will This Idea Spread Beyond Academia? Understanding Knowledge Transfer of Scientific Concepts across Text Corpora (Findings of EMNLP 2020, doi:10.18653/v1/2020.findings-emnlp.158)",
     ["Hancheng Cao", "Mengjie Cheng", "Zhepeng Cen", "Daniel A. McFarland", "Xiang Ren"], 2020,
     "VERBATIM-FULLTEXT. DIFFERENT (paper->patent/trial transfer); precedent for discipline-entropy term feature (K2).",
     [P("computed as a concept’s average entropy across NRC discipline subject codes", "Sec. 3 features")]),
    (27, "https://arxiv.org/abs/2212.09676", "Words as Gatekeepers: Measuring Discipline-specific Terms and Meanings in Scholarly Publications (arXiv 2212.09676)",
     None, 2022,
     "ABSTRACT. DIFFERENT: discipline-specific jargon (word types and senses) across subfields; relevant to K2 term specificity. Authors not confirmed this session.",
     [P("we use word sense induction to also identify words that are widespread but overloaded with different meanings across fields", "Abstract")]),
    (28, "https://arxiv.org/abs/cmp-lg/9509004", "The Development and Migration of Concepts from Donor to Borrower Disciplines: Sublanguage Term Use in Hard & Soft Sciences",
     ["Robert M. Losee"], 1995,
     "ABSTRACT. DIFFERENT: donor/borrower disciplines from term frequencies.",
     [P("Using term frequencies, the birth, growth, death, and migration of concepts and their associated terms are examined.", "Abstract")]),
    (29, S2.format("DOI:10.1162/rest.88.4.641"), "The Log of Gravity (REStat 88(4):641-658, doi:10.1162/rest.88.4.641)",
     ["J. M. C. Santos Silva", "Silvana Tenreyro"], 2006, "ABSTRACT. PPML rationale.",
     [P("under heteroskedasticity, the parameters of log-linearized models estimated by OLS lead to biased estimates of the true elasticities", "Abstract")]),
    (30, S2.format("DOI:10.1177/1536867X20909691"), "Fast Poisson estimation with high-dimensional fixed effects (Stata Journal 20(1):95-115, doi:10.1177/1536867X20909691)",
     ["Sergio Correia", "Paulo Guimarães", "Tom Zylkin"], 2020, "ABSTRACT. ppmlhdfe.",
     [P("a new command for estimation of (pseudo-)Poisson regression models with multiple high-dimensional fixed effects (HDFE)", "Abstract")]),
    (31, "https://arxiv.org/abs/1903.01633", "Verifying the existence of maximum likelihood estimates for generalized linear models (arXiv 1903.01633)",
     ["Sergio Correia", "Paulo Guimarães", "Tom Zylkin"], 2019, "ABSTRACT. Separation / existence of PPML estimates with FE.",
     [P("maximum likelihood estimates are not guaranteed to exist", "Abstract")]),
    (32, "https://arxiv.org/abs/1909.01327", "Bias and consistency in three-way gravity models (J Int Econ 132:103513, doi:10.1016/j.jinteco.2021.103513)",
     ["Martin Weidner", "Thomas Zylkin"], 2021, "ABSTRACT. Incidental-parameter problem for three-way PPML (volume corrected to 132).",
     [P("Despite the number and variety of fixed effects involved", "Abstract")]),
    (33, "http://cameron.econ.ucdavis.edu/research/Cameron_Miller_JHR_2015_February.pdf", "A Practitioner's Guide to Cluster-Robust Inference (JHR 50(2):317-372, doi:10.3368/jhr.50.2.317)",
     ["A. Colin Cameron", "Douglas L. Miller"], 2015, "VERBATIM-FULLTEXT. Few-cluster problem.",
     [P("There is no clear-cut definition of", "Sec. I (few clusters)")]),
    (34, S2.format("DOI:10.1002/jae.2508"), "Wild Bootstrap Inference for Wildly Different Cluster Sizes (J Applied Econometrics 32(2):233-254, doi:10.1002/jae.2508)",
     ["James G. MacKinnon", "Matthew D. Webb"], 2017, "ABSTRACT. Unbalanced clusters; wild cluster bootstrap; effective number of clusters.",
     [P("Rejection frequencies are higher for datasets with 50 clusters proportional to US state populations than with 50 balanced clusters.", "Summary")]),
    (35, CR.format("10.1162/REST_a_00639"), "Asymptotic Behavior of a t-Test Robust to Cluster Heterogeneity (REStat 99(4):698-709, doi:10.1162/REST_a_00639)",
     ["Andrew V. Carter", "Kevin T. Schnepel", "Douglas G. Steigerwald"], 2017, "METADATA-ONLY (Crossref). Effective number of clusters.", []),
    (36, S2.format("DOI:10.1016/j.jeconom.2022.04.001"), "Cluster-robust inference: A guide to empirical practice (J Econometrics 232(2):272-299, doi:10.1016/j.jeconom.2022.04.001)",
     ["James G. MacKinnon", "Morten Ørregaard Nielsen", "Matthew D. Webb"], 2023, "ABSTRACT. Current practice guide.",
     [P("Methods for cluster-robust inference are routinely used in economics and many other disciplines", "Abstract")]),
    (37, S2.format("DOI:10.1177/1536867X19830877"), "Fast and wild: Bootstrap inference in Stata using boottest (Stata Journal 19(1):4-60, doi:10.1177/1536867X19830877)",
     ["David Roodman", "Morten Ørregaard Nielsen", "James G. MacKinnon", "Matthew D. Webb"], 2019, "ABSTRACT. Wild bootstrap implementation.",
     [P("there may be few clusters, few treated clusters, or weak instruments", "Abstract")]),
    (38, S2.format("DOI:10.1111/caje.12661"), "Reworking wild bootstrap-based inference for clustered errors (Canadian J Econ 56(3):839-858, doi:10.1111/caje.12661)",
     ["Matthew D. Webb"], 2023, "ABSTRACT (QED WP 1315 text in S2). Webb six-point weights.",
     [P("a 6-point bootstrap weight distribution improves the reliability of inference", "Abstract")]),
    (39, "https://www.nber.org/system/files/working_papers/w16127/w16127.pdf", "A Score Based Approach to Wild Bootstrap Inference (J Econometric Methods 1(1):23-41, doi:10.1515/2156-6674.1006; NBER w16127)",
     ["Patrick M. Kline", "Andres Santos"], 2012, "VERBATIM-FULLTEXT (NBER). Score bootstrap for nonlinear M-estimators such as PPML.",
     [P("based upon perturbing the scores of M-estimators", "Abstract")]),
    (40, S2.format("DOI:10.1093/qje/qjy029"), "Channeling Fisher: Randomization Tests and the Statistical Insignificance of Seemingly Significant Experimental Results (QJE 134(2):557-598, doi:10.1093/qje/qjy029)",
     ["Alwyn Young"], 2019, "ABSTRACT. Randomisation inference is more conservative.",
     [P("In joint tests of multiple treatment effects appearing together in tables, randomization tests yield 33% to 49% fewer statistically significant results than conventional tests.", "Abstract")]),
    (41, CR.format("10.1080/07350015.1983.10509354"), "A Nonstochastic Interpretation of Reported Significance Levels (JBES 1(4):292-298)", ["David Freedman", "David Lane"], 1983, "METADATA-ONLY. Permutation scheme reference.", []),
    (42, CR.format("10.2307/1909582"), "Some Statistical Models for Limited Dependent Variables with Application to the Demand for Durable Goods (Econometrica 39(5):829)", ["John G. Cragg"], 1971, "METADATA-ONLY. Two-part model origin.", []),
    (43, S2.format("DOI:10.1016/0304-4076(86)90002-3"), "Specification and testing of some modified count data models (J Econometrics 33(3):341-365)", ["John Mullahy"], 1986, "ABSTRACT. Hurdle count models.",
     [P("These alternatives permit more flexible specification of the data-generating process (dgp) than do familiar count data models", "Abstract")]),
    (44, CR.format("10.1515/jem-2013-0005"), "Testing Competing Models for Non-negative Data with Many Zeros (J Econometric Methods 4(1):29-46)", ["J. M. C. Santos Silva", "Silvana Tenreyro", "Frank Windmeijer"], 2015, "METADATA-ONLY. PPML vs two-part models (K1's question).", []),
    (45, "https://ideas.repec.org/a/eee/infome/v7y2013i4p861-873.html", "Which factors help authors produce the highest impact research? Collaboration, journal and document properties (J Informetrics 7(4):861-873, doi:10.1016/j.joi.2013.08.006)",
     ["Fereshteh Didegah", "Mike Thelwall"], 2013, "ABSTRACT. Scientometric hurdle precedent (negative binomial-logit hurdle for citations).",
     [P("used a single negative binomial-logit hurdle model estimating the percentage change in the mean citation counts", "Abstract")]),
    (46, "https://arxiv.org/abs/1601.00473", "The discretised lognormal and hooked power law distributions for complete citation data (arXiv 1601.00473)", None, 2016,
     "ABSTRACT. Zero-inclusive citation distributions (plan: Thelwall 2016; author list not re-confirmed this session).",
     [P("adding 1 to citation counts in order to include zeros", "Abstract")]),
    (47, "https://arxiv.org/html/2505.15384v1", "A Two-Stage Model for Factors Influencing Citation Counts (Publications 13(2):29, doi:10.3390/publications13020029)",
     ["Pablo Dorta-González", "Emilio Gómez-Déniz"], 2025, "VERBATIM-FULLTEXT. Recent hurdle precedent for citation counts.",
     [P("A hurdle model for separating the documents with citations and those without citations is considered.", "Abstract")]),
    (48, CR.format("10.1111/j.1467-9957.1965.tb00050.x"), "Trade Liberalisation and 'Revealed' Comparative Advantage (Manchester School 33(2):99-123)", ["Bela Balassa"], 1965, "METADATA-ONLY. RCA / location quotient origin for K2 lift.", []),
    (49, "https://www.sciencedirect.com/science/article/abs/pii/S1751157712000053", "Reflections on the activity index and related indicators (J Informetrics 6(3):413-421, doi:10.1016/j.joi.2012.01.004)",
     ["Ronald Rousseau", "Liying Yang"], 2012, "ABSTRACT. Activity index = Balassa/RCA, introduced by Frame (1977); non-monotonicity caveat.",
     [P("such as the revealed comparative advantage index or Balassa index", "Abstract"),
      P("This index was introduced in informetrics by Frame (1977).", "Sec. 2 (article preview)")]),
    (50, CR.format("10.1002/sim.1186"), "Quantifying heterogeneity in a meta-analysis (Stat Med 21(11):1539-1558)", ["Julian P. T. Higgins", "Simon G. Thompson"], 2002, "METADATA-ONLY. I-squared.", []),
    (51, CR.format("10.1016/0197-2456(86)90046-2"), "Meta-analysis in clinical trials (Controlled Clinical Trials 7(3):177-188)", ["Rebecca DerSimonian", "Nan Laird"], 1986, "METADATA-ONLY. Random-effects pooling.", []),
    (52, CR.format("10.1056/NEJMsr077003"), "Statistics in Medicine — Reporting of Subgroup Analyses in Clinical Trials (NEJM 357(21):2189-2194)", ["Rui Wang", "Stephen W. Lagakos", "James H. Ware", "David J. Hunter", "Jeffrey M. Drazen"], 2007, "METADATA-ONLY. Pre-declared subgroup analyses.", []),
    (53, "http://www.stat.columbia.edu/~gelman/research/published/ForkingPaths.pdf", "The Statistical Crisis in Science (American Scientist 102(6):460, doi:10.1511/2014.111.460)", ["Andrew Gelman", "Eric Loken"], 2014, "VERBATIM-FULLTEXT. Garden of forking paths (K3 moderators).",
     [P("explains why many statistically significant comparisons", "Subtitle")]),
    (54, "https://papers.ssrn.com/sol3/papers.cfm?abstract_id=1425737", "When Do Covariates Matter? And Which Ones, and How Much? (J Labor Econ 34(2):509-543, doi:10.1086/683668)", ["Jonah B. Gelbach"], 2016, "ABSTRACT. Covariate-order-invariant decomposition.",
     [P("This is problematic, due to sequence-sensitivity when added covariates are intercorrelated.", "Abstract")]),
    (55, CR.format("10.1038/nature03288"), "Functional cartography of complex metabolic networks (Nature 433:895-900)", ["Roger Guimerà", "Luís A. Nunes Amaral"], 2005, "METADATA-ONLY (DOI verified; text verified in iter-1). Participation coefficient / roles.", []),
    (56, CR.format("10.1111/j.1466-8238.2009.00490.x"), "Partitioning the turnover and nestedness components of beta diversity (Global Ecology and Biogeography 19(1):134-143)", ["Andrés Baselga"], 2010, "METADATA-ONLY (DOI verified).", []),
    (57, CR.format("10.1038/s41598-019-41695-z"), "From Louvain to Leiden: guaranteeing well-connected communities (Sci Rep 9:5233)", ["V. A. Traag", "L. Waltman", "N. J. van Eck"], 2019, "METADATA-ONLY (DOI verified).", []),
    (58, CR.format("10.1016/j.csda.2006.11.025"), "Cluster-wise assessment of cluster stability (CSDA 52(1):258-271)", ["Christian Hennig"], 2007, "METADATA-ONLY (DOI verified).", []),
    (59, CR.format("10.1023/A:1024940629314"), "Bursty and Hierarchical Structure in Streams (DMKD 7(4):373-397)", ["Jon Kleinberg"], 2003, "METADATA-ONLY (DOI verified).", []),
    (60, CR.format("10.1073/pnas.252631999"), "The average distances in random graphs with given expected degrees (PNAS 99(25):15879-15882)", ["Fan Chung", "Linyuan Lu"], 2002, "METADATA-ONLY (DOI verified).", []),
    (61, "https://arxiv.org/abs/2205.01833", "OpenAlex: A fully-open index of scholarly works, authors, venues, institutions, and concepts (arXiv 2205.01833)", None, 2022, "METADATA-ONLY (not re-fetched; listed for the bibliography).", []),
    (62, "https://link.springer.com/collections/fgcaicgjah", "Applied Network Science collection: Networks for everyday life", None, 2026,
     "SNIPPET only (page 303-redirects to login). Scope: theory, methods, applications for health, mobility, education, politics and related societal domains; topics include innovation/collaboration/knowledge-exchange networks and information diffusion; submissions opened 24 Jun 2026, deadline 30 Nov 2026; editor named in snippet: Ronaldo Menezes (Exeter); no member articles listed.", []),
    (63, "http://web.archive.org/web/2025/https://appliednetsci.springeropen.com/submission-guidelines/preparing-your-manuscript/research", "Applied Network Science: Preparing your manuscript (Research article) — Wayback snapshot 2024-11-01", None, None,
     "VERBATIM (official guidelines): no abstract word limit; 3-10 keywords; mandatory Declarations list; figure/table titles <=15 words, legends <=300 words; Basic Springer reference style.",
     [P("Three to ten keywords representing the main content of the article.", "Keywords"),
      P("All manuscripts must contain the following sections under the heading 'Declarations'", "Declarations"),
      P("Figure titles (max 15 words) and legends (max 300 words)", "Figures")]),
    (64, "https://pmc.ncbi.nlm.nih.gov/articles/PMC9673898/", "Author multidisciplinarity and disciplinary roles in field of study networks (ANS 7:77, doi:10.1007/s41109-022-00517-4)",
     ["Eoghan Cunningham", "Barry Smyth", "Derek Greene"], 2022,
     "VERBATIM-FULLTEXT. ANS scientometric structure exemplar: 215-word abstract, 3 keywords, separate Related work, author-year citations (25 vs 1 numbered). Topic roles in FoS networks.",
     []),
    (65, "https://pmc.ncbi.nlm.nih.gov/articles/PMC8242290/", "Large-scale analysis of delayed recognition using sleeping beauty and the prince (ANS 6:48, doi:10.1007/s41109-021-00389-0)",
     ["Takahiro Miura", "Kimitaka Asatani", "Ichiro Sakata"], 2021,
     "VERBATIM-FULLTEXT. ANS exemplar: 247-word abstract, 7 keywords, 51 author-year citations; delayed recognition (slow uptake).",
     []),
    (66, "https://pmc.ncbi.nlm.nih.gov/articles/PMC12102006/", "Temporal dynamics of the friendship paradox in a smartphone communication network (ANS 2025)",
     ["Cheng Wang", "Omar Lizardo", "David S. Hachen"], 2025,
     "VERBATIM-FULLTEXT (structure only). 250-word abstract, 5 keywords, Materials and methods (Data, Analytical strategy), 22 author-year citations.", []),
    (67, S2.format("DOI:10.1007/s41109-017-0034-3"), "The weakness of weak ties for novel information diffusion (ANS 2:14, doi:10.1007/s41109-017-0034-3)", ["Jennifer M. Larson"], 2017,
     "ABSTRACT. Spanning weak ties are lower-capacity: accessibility vs familiarity reading.",
     [P("I argue that weak ties, especially the kind that span subgroups, are often also lower-capacity.", "Abstract")]),
    (68, S2.format("DOI:10.1007/s41109-019-0126-3"), "Community structure in co-inventor networks affects time to first citation for patents (ANS, doi:10.1007/s41109-019-0126-3)",
     ["William Doonan", "Kyle W. Higham", "Martina Governale"], 2019,
     "ABSTRACT. Same-community citers cite faster: social analogue of local uptake.",
     [P("A statistically significant difference in the time lag until first citation is linked to whether or not this citation comes from a patent whose listed inventors share membership in the same communities", "Abstract")]),
    (69, S2.format("DOI:10.1007/s41109-016-0010-3"), "Disconnected, fragmented, or united? a trans-disciplinary review of network science (ANS 1, doi:10.1007/s41109-016-0010-3)", ["César A. Hidalgo"], 2016,
     "ABSTRACT. Disciplinary fragmentation of network science (Introduction framing).",
     [P("During decades the study of networks has been divided between the efforts of social scientists and natural scientists", "Abstract")]),
    (70, S2.format("DOI:10.1007/s41109-023-00533-y"), "A methodology framework for bipartite network modeling (ANS 8:6, doi:10.1007/s41109-023-00533-y)", ["Chin-Ying Liew", "Jane Labadin", "Wo-On-Chee Kok"], 2023,
     "ABSTRACT. Bipartite modelling framework (concept-subfield view).",
     [P("The graph-theoretic based studies employing bipartite network approach mostly focus on surveying the statistical properties", "Abstract")]),
    (71, S2.format("DOI:10.1007/s41109-025-00749-0"), "Understanding the effect of knowledge graph extraction error on downstream graph analyses (ANS 10:64, doi:10.1007/s41109-025-00749-0)", ["Erica Cai", "Brendan T. O'Connor"], 2025,
     "ABSTRACT. Grounding/extraction-error caveat.",
     [P("the impacts of extraction errors on downstream analyses are poorly under", "Abstract")]),
    (72, S2.format("DOI:10.1007/s41109-024-00658-8"), "Large language models recover scientific collaboration networks from text (ANS 9:64, doi:10.1007/s41109-024-00658-8)", ["Rathin Jeyaram", "Robert N. Ward", "Marc Santolini"], 2024,
     "ABSTRACT. LLM-based network extraction (alternative grounding).",
     [P("We show that Large Language Models (LLMs) can solve this problem", "Abstract")]),
    (73, S2.format("DOI:10.1007/s41109-022-00518-3"), "Regional industrial growth and biopharma patent networks: empirical insights from the UK (ANS 7:77, doi:10.1007/s41109-022-00518-3)", ["Yuanhua Gao", "Zheng Hua Zhu"], 2022,
     "ABSTRACT. Regional (host) growth and network position.",
     [P("cross-border patenting collaboration", "Abstract")]),
    (74, "https://arxiv.org/abs/1604.00696", "Quantifying the diaspora of knowledge in the last century (ANS 1:15, doi:10.1007/s41109-016-0017-9)", ["Manlio De Domenico", "Elisa Omodei", "Alex Arenas"], 2016,
     "VERBATIM (iter-1 verified). Field-level author flows; sources/sinks.",
     [P("mainly act as sources of the diaspora", "Abstract (iter-1 verified)")]),
    (75, "https://arxiv.org/pdf/2310.01046", "Epistemic integration and social segregation of AI in neuroscience (ANS 9:8, doi:10.1007/s41109-024-00618-2)", ["Sylvain Fontaine", "Floriana Gargiulo", "Michel Dubois", "Paola Tubaro"], 2024,
     "VERBATIM (iter-1 verified). AI integrates epistemically into neuroscience but stays socially segregated; closest ANS RQ2 neighbour.",
     [P("only 3% contain AI-related keywords", "iter-1 verified")]),
    (76, S2.format("DOI:10.1007/s41109-018-0074-3"), "Co-occurrence simplicial complexes in mathematics: identifying the holes of knowledge (ANS 3, doi:10.1007/s41109-018-0074-3)", ["Vsevolod Salnikov", "Daniele Cassese", "Renaud Lambiotte"], 2018,
     "ABSTRACT. Higher-order word co-occurrence (RQ1 related work).",
     [P("we propose for the first time a simplicial complex approach to word co-occurrences", "Abstract")]),
    (77, S2.format("DOI:10.1007/s41109-018-0090-3"), "Community evolution in patent networks: technological change and network dynamics (ANS 3, doi:10.1007/s41109-018-0090-3)", ["Yuan Gao", "Zhen-Yan Zhu", "Raja Kali"], 2018,
     "ABSTRACT. Community evolution in patent networks.",
     [P("categorizing technologies based on the existing classification systems used by patent authorities could cause inaccuracy and misclassification", "Abstract")]),
    (78, S2.format("DOI:10.1007/s41109-020-00292-0"), "Shannon entropy in time-varying semantic networks of titles of scientific paper (ANS 5, doi:10.1007/s41109-020-00292-0)", ["Marcelo do Vale Cunha", "Carlos César Ribeiro Santos", "Marcelo A. Moret"], 2020,
     "ABSTRACT. Entropy of temporal title semantic networks.",
     [P("We propose a method for calculating the entropy of a clique network", "Abstract")]),
    (79, S2.format("DOI:10.1007/s41109-020-00279-x"), "The mobility network of scientists: analyzing temporal correlations in scientific careers (ANS 5, doi:10.1007/s41109-020-00279-x)", ["Giacomo Vaccario", "Luca Verginer", "Frank Schweitzer"], None,
     "ABSTRACT. 3.5M career trajectories; mobility constraints.",
     [P("we extract 3.5 million career trajectories of scientists from two large scale bibliographic data sets", "Abstract")]),
    (80, S2.format("DOI:10.1007/s41109-023-00572-5"), "Mapping change in higher-order networks with multilevel and overlapping communities (ANS 8, doi:10.1007/s41109-023-00572-5)", ["Anton Holmgren", "Daniel Edler", "Martin Rosvall"], 2023,
     "ABSTRACT. Alluvial diagrams for community change.",
     [P("alluvial diagrams, which visualize community splits and merges between networks", "Abstract")]),
    (81, S2.format("DOI:10.1007/s41109-023-00592-1"), "Exploring temporal community evolution: algorithmic approaches and parallel optimization for dynamic community detection (ANS 8, doi:10.1007/s41109-023-00592-1)", ["Naw Safrin Sattar", "Aydın Buluç", "Khaled Z. Ibrahim"], 2023,
     "ABSTRACT. Dynamic community detection.",
     [P("Community discovery is an extensively used graph analysis kernel", "Abstract")]),
    (82, S2.format("DOI:10.1007/s41109-025-00693-z"), "Statistically validated network for analysing textual data (ANS 10, doi:10.1007/s41109-025-00693-z)", ["Andrea Simonetti", "Alessandro Albano", "Michele Tumminello"], 2025,
     "ABSTRACT. SVN null backbone for word co-occurrence.",
     [P("represents the corpus as a bipartite network of words and documents to rigorously assess the statistical significance of word co-occurrences", "Abstract")]),
    (83, S2.format("DOI:10.1007/s41109-021-00408-0"), "Appraising discrepancies and similarities in semantic networks using concept-centered subnetworks (ANS 6, doi:10.1007/s41109-021-00408-0)", ["Darkhan Medeuov", "Camille Roth", "Kseniia A. Puzyreva"], 2021,
     "ABSTRACT. Concept-centred ego subnetworks (neighbourhood turnover).",
     [P("A concept-centered sub-network is defined as an induced network whose vertex set consists of the given concept (ego) and all its adjacent concepts (alters)", "Abstract")]),
    (84, S2.format("DOI:10.1007/s41109-017-0035-2"), "Multiplex flows in citation networks (ANS 2, doi:10.1007/s41109-017-0035-2)", ["Benjamin Renoust", "Vivek Claver", "Jean-François Baffier"], 2017,
     "ABSTRACT. Inheritance paths in citation networks.",
     [P("A citation network can be seen as a perfect example of one generative process leading to innovation.", "Abstract")]),
    (85, S2.format("DOI:10.1007/s41109-023-00597-w"), "Short- and long-term temporal network prediction based on network memory (ANS 8, doi:10.1007/s41109-023-00597-w)", ["Li Zou", "Alberto Ceria", "Huijuan Wang"], 2023,
     "ABSTRACT. Temporal network prediction baseline.",
     [P("The classic temporal network prediction problem aims to predict the temporal network one time step ahead", "Abstract")]),
    (86, S2.format("DOI:10.1007/s41109-024-00687-3"), "Detection of dynamic communities in temporal networks with sparse data (ANS, doi:10.1007/s41109-024-00687-3)", ["Nataša Djurdjevac Conrad", "Elisa Tonello", "Johannes Zonker"], 2025,
     "ABSTRACT. Dynamic communities with sparse data.",
     [P("detection of dynamic communities within these networks can help identify important cohesive structures", "Abstract")]),
    (87, S2.format("DOI:10.1007/s41109-025-00766-z"), "An agent-based model of citation behavior (ANS, doi:10.1007/s41109-025-00766-z)", ["George Chacko", "Minhyuk Park", "Vikram Ramavarapu"], 2026,
     "ABSTRACT. Generative citation ABM (null).",
     [P("We examine this motivation using a generative model of citation that is agent-based.", "Abstract")]),
    (88, S2.format("DOI:10.1007/s41109-025-00725-8"), "The impact factor game: an agent-based exploration of self-citation influence and interdisciplinary dynamics on impact metrics (ANS, doi:10.1007/s41109-025-00725-8)", ["Luiz Gabriel Correia", "Jesús P. Mena-Chalco"], 2025,
     "ABSTRACT. Indicator gaming ABM (policy framing).",
     [P("This work introduces an agent-based model simulating journals as rational agents competing for IF ranking positions", "Abstract")]),
    (89, S2.format("DOI:10.1007/s41109-022-00497-5"), "The role of highly intercited papers on scientific impact: the Mexican case (ANS 7, doi:10.1007/s41109-022-00497-5)", ["Rodrigo Dorantes-Gilardi", "Aurora A. Ramírez-Álvarez", "Diana Terrazas-Santamaría"], 2022,
     "ABSTRACT. k-max interconnection and author impact (optional RQ2 related work).",
     [P("explores the relationship between highly intercited papers in the k-max of citation networks", "Abstract")]),
    (90, S2.format("DOI:10.1007/s41109-023-00546-7"), "The risk of aggregating networks when diffusion is tie-specific (ANS 8, doi:10.1007/s41109-023-00546-7)", ["Jennifer M. Larson", "Pedro L. Rodriguez"], 2023,
     "ABSTRACT. Tie-specific diffusion; supports host-specific network views.",
     [P("Aggregating multiple measures of ties into", "Abstract")]),
    (91, CR.format("10.1177/030631289019003001"), "Institutional Ecology, 'Translations' and Boundary Objects (Social Studies of Science 19(3):387-420)", ["Susan Leigh Star", "James R. Griesemer"], 1989, "METADATA-ONLY. Boundary objects (theory pointer).", []),
    (92, CR.format("10.1177/053901883022002003"), "From translations to problematic networks: An introduction to co-word analysis (Social Science Information 22(2):191-235)", ["Michel Callon", "Jean-Pierre Courtial", "William A. Turner", "Serge Bauin"], 1983, "METADATA-ONLY. Origin of co-word analysis.", []),
    (93, CR.format("10.1177/1075547005278346"), "Metaphors and Diaphors in Science Communication (Science Communication 27(1):64-99)", ["Loet Leydesdorff", "Iina Hellsten"], 2005, "METADATA-ONLY (year corrected to 2005). Recontextualisation pointer.", []),
]

ANSWER = """**Verdict: partly anticipated (0 ANTICIPATES, 11 PARTLY among 25 graded candidates).** No located work measures how host-specific the vocabulary is that a concept is combined with when it enters a new subfield, and relates that, within concepts and across hosts, to later uptake by the host's own newcomers. The ingredients exist separately:
- global embeddedness of a new idea among established ideas, with a yearly article-count outcome [1];
- paper-level content connectivity, with a citation outcome [20, 21];
- proximal new concept links, which receive more uptake [4];
- conventional-plus-atypical combinations, which predict impact [2];
- host-specific relatedness, which predicts entry into fields or topics, not post-entry uptake [6, 7, 22];
- qualitative accounts of ideas being translated to field-specific problems [23, 24].

**Cheng et al. 2023, now read in full text, corrects the plan [1].**
- Their outcome is "the number of articles a new idea diffuses into the year ahead" (56,540 ideas, 995,945 idea-years), estimated with a multilevel over-dispersed Poisson model. It is not a binary "core" status.
- "Fit with research traditions" is ideational embeddedness: the mean cosine similarity between the focal term's neighbours in a single global word2vec embedding of the prior-decade co-occurrence network. +1 SD gives about +25% articles. Social embeddedness gives about -15% [1].
- Fit is therefore global and pooled over all adopters. That leaves our margin intact: host-specific context at entry, concept fixed effects across hosts, author-disjoint newcomer outcome, sealed-fold confirmation and MeSH replication.
- The sentence "consistent with Cheng for volume, not for a binary threshold" must be dropped. Cheng has no binary outcome.

**Paper-ready sentence.** "To our knowledge, no prior study tests, within concepts and across the host subfields they enter, whether the host-specificity of the vocabulary a concept is first combined with predicts uptake by the host's own newcomers. The nearest work measures embeddedness globally (Cheng et al. 2023), connectivity at the paper level (Deichmann et al. 2020; Candelon et al. 2024), recombination at the paper or link level (Uzzi et al. 2013; Hofstra et al. 2020), or uses relatedness to predict entry (Boschma et al. 2014; Guevara et al. 2016; Hidalgo et al. 2018)."

**Forbidden over-claims:**
- "first to show fit matters" [1, 8, 20];
- "predicts establishment";
- "Cheng studies binary core status";
- "novel hurdle decomposition";
- a single absorptive-capacity reading of the adopter result. Topical proximity is an equally good reading [5, 9].

**Further neighbours and framing references.**
- Foster et al. show risky strategies are more often ignored but more likely to reach high impact [3].
- Meme propagation scores are pooled over all of science [11].
- Rotolo et al.'s five attributes frame RQ1 [12].
- Author diversification follows topic and social relatedness [25].
- Discipline-specific jargon has been measured across subfields [27], and donor/borrower disciplines have been measured from term frequencies [28].
- Boundary objects, co-word translation and "diaphors" remain metadata-level theory pointers only [91, 92, 93].

**ANS related work beyond the core rows:**
- delayed recognition [65];
- structure exemplar [66];
- low-capacity spanning ties [67];
- fragmentation of network science [69];
- bipartite modelling [70];
- knowledge-graph extraction error [71];
- LLM-recovered collaboration networks [72];
- regional patent networks [73];
- co-occurrence simplicial complexes [76];
- patent community evolution [77];
- entropy of title networks [78];
- scientist mobility [79];
- alluvial community change [80];
- dynamic community detection [81, 86];
- statistically validated text networks [82];
- concept-centred ego networks [83];
- citation flows [84];
- temporal network prediction [85];
- citation ABMs [87, 88];
- k-max intercitation [89];
- tie-specific diffusion [90].

**Tensions to present as complementary.** Surprise and novelty pay off in impact, often through distant audiences [10, 18, 19]. Host-familiar framing pays off in local newcomer uptake. Brokerage predictions [14, 15] and pre-emergence collaboration signals [13] are not supported at concept level here. Breadth indicators [16, 17] measure occupancy, not integration.

**Methods.**
- K1 is standard practice on a new unit. Scientometric hurdle models appear in [45], [21] and [47]; the econometric bases are [42], [43] and [44].
- K2 lift is Balassa RCA / Frame's activity index [48, 49]. Term-generality entropy has direct precedent [1, 26].
- Inference references are DOI-verified:
  - PPML [29], estimation with high-dimensional fixed effects [30], separation / existence of estimates [31], incidental-parameter bias with three-way fixed effects [32];
  - few or unbalanced clusters [33, 34], effective number of clusters [35], current practice guide [36], wild bootstrap implementation [37], Webb weights [38];
  - score bootstrap [39]; randomisation inference [40, 41];
  - zero-inclusive citation distributions [46];
  - pooling and heterogeneity [50, 51]; pre-declared subgroups [52]; forking paths [53]; covariate decomposition [54].
- DOIs of tools the run already uses were verified: participation coefficient [55], beta-diversity partitioning [56], Leiden [57], cluster-wise stability [58], burst detection [59], Chung-Lu null [60], OpenAlex [61].

**Venue.**
- The collection page is login-gated. Snippets give the scope (health, mobility, education, politics), a topic on innovation, collaboration and knowledge-exchange networks, and a deadline of 30 Nov 2026 [62].
- ANS guidelines require 3-10 keywords and a Declarations block, with no abstract word limit [63]. Three full texts confirm author-year citations and abstracts of 215-250 words [64, 65, 66].
- A 27-paper ANS base is assembled. It includes Fontaine 2024 [75], De Domenico 2016 [74], Cunningham 2022 [64] and Doonan 2019 [68]; Doonan is a social analogue of local uptake.

**Confidence.**
- High for Cheng's operationalisation, the K1 status and all DOIs.
- Medium for the novelty verdict. There was no WoS/Scopus access and a single screener. It would become "anticipated" if a study were found measuring the host-share of a concept's co-occurrence partners at entry against later host uptake.
- Low for collection membership and editors."""

SUMMARY = """Positioning dossier (web-only, $0) for the iteration-5 ANS paper. It covers the confirmed claim that host-leaning entry vocabulary (A_cont) raises W2 uptake by host newcomers beyond RD, volume and momentum, with co-transfer null and binary establishment null.

**Novelty verdict: PARTLY ANTICIPATED** (0 ANTICIPATES / 11 PARTLY / 25 graded).
- Evidence: 14 queries in general and scholarly mode (571 titles screened), 4 extra queries, and forward-citation snowballing of Cheng 2023 (33 citing papers), Hofstra 2020 (856), Uzzi 2013 (937), Guevara 2016 (123) and Deichmann 2020 (31). Backward chasing used Cheng's 167 Crossref references.
- The report gives a paper-ready novelty sentence and a list of forbidden over-claims.

**Key correction: Cheng et al. 2023 (ASR 88(3):522-561), read in full text.**
- Unit = idea-year. Outcome = yearly article COUNT, not binary 'core'.
- Fit = ideational embeddedness: mean cosine similarity of neighbour terms in a GLOBAL word2vec embedding (+25% per SD). Social embeddedness is -15%.
- Model: multilevel over-dispersed Poisson.
- Our margin therefore holds (host-specific, entry-level, within-concept FE, newcomer outcome, sealed fold, MeSH replication). Drop any 'binary threshold' contrast with Cheng.
- New PARTLY neighbours to cite: Deichmann et al. 2020 (Res Policy); Candelon et al. 2024 (Res Policy, hurdle); Boschma et al. 2014 (city-level relatedness); Herfeld & Doehne 2019; Keuchenius et al. 2021; Tripodi et al. 2020.
- Tensions to frame as complementary: Wang, Veugelers & Stephan 2017 (novelty cited in foreign, not home, fields); Shi & Evans 2023.

**Methods.**
- K1 hurdle = standard: Didegah & Thelwall 2013; Candelon 2024; Dorta-González 2025.
- K2 lift = Balassa/activity index (Rousseau & Yang 2012 caveat). Term entropy has precedent in Cheng's 'Interdisciplinary' control and in Cao et al. 2020.
- 26 methods references with sentence and quote; DOIs checked for 65 references in total.
- Corrections: Weidner & Zylkin is J Int Econ 132; Leydesdorff & Hellsten is 2005; Cheng pages are 522-561; the Hidalgo 2018 arXiv id in the plan is wrong.

**Venue.**
- Collection page is login-gated. Snippets give the scope, the topic 'innovation, collaboration, and knowledge exchange networks across sectors', dates 24 Jun to 30 Nov 2026, and editor R. Menezes. No member articles. Fit upgraded to moderate.
- ANS guidelines (Wayback): 3-10 keywords, mandatory Declarations, no abstract limit, figure titles 15 words or fewer.
- Author-year citation style confirmed on 3 full texts. A 27-paper ANS related-work table maps each paper to a section.

**Files:** research_report.md (11 sections incl. Table 1 draft and nearest-neighbour table), bib_ids.txt (identifiers for aii-semscholar-bib), search_log/, snowball/, reproducibility.md."""

FOLLOW = [
    "Does any economic-geography or science-of-science study measure the host-share (location quotient) of an entering technology's or concept's co-occurring partners at entry and relate it to post-entry growth or survival in that region/field? This is the most likely place for an ANTICIPATES item that our keyword and forward-citation search missed.",
    "Can Cheng et al.'s global ideational-embeddedness measure be computed on our OpenAlex/MeSH entry events and entered alongside A_cont, to show empirically that host-specific context adds explanatory power beyond global embeddedness?",
    "Can the two readings of the adopter result (absorptive capacity vs topical proximity, Jia et al. 2017) be separated, e.g. by conditioning on adopters' prior topical distance to the concept's origin?",
]


def main() -> None:
    sources = []
    for idx, url, title, authors, year, summary, passages in SRC:
        sources.append({"index": idx, "url": url, "title": title, "summary": summary,
                        "authors": authors, "year": year, "supporting_passages": passages})
    idxs = [s["index"] for s in sources]
    assert idxs == list(range(1, len(idxs) + 1)), "indices must be 1..N"
    out = {
        "title": "Where the host-vocabulary finding sits in the literature",
        "layman_summary": "Checks how new our finding is (a new idea spreads more in a field when it arrives dressed in that field's own words) against the closest published studies, and collects verified journal and methods references for the paper.",
        "summary": SUMMARY,
        "out_expected_files": {"output": "research_out.json", "reproducibility": "reproducibility.md"},
        "upload_ignore_regexes": ["(^|/)cache/"],
        "answer": ANSWER,
        "sources": sources,
        "follow_up_questions": FOLLOW,
    }
    assert 500 <= len(SUMMARY) <= 5000, len(SUMMARY)
    (ROOT / ".terminal_claude_agent_struct_out.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print("sources:", len(sources), "summary chars:", len(SUMMARY), "answer words:", len(ANSWER.split()))


if __name__ == "__main__":
    main()
