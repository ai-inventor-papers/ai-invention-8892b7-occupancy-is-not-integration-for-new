# Reproducibility log: how this dossier was actually produced

- **Date of execution:** 2026-09-28, in one session of about 70 minutes of tool time. Search results and the OpenAlex API drift over time.
- **Tools:**
  - The built-in `WebSearch` / `WebFetch`, loaded as deferred tools, as the `aii-web-tools` skill instructs.
  - The skill's own scripts, `aii_fast_web_fetch.py fetch|grep` (PyMuPDF/html2text), run with `/ai-inventor/.claude/skills/.ability_client_venv/bin/python`.
  - Plain `curl` against three public APIs: OpenAlex, Crossref and Europe PMC. Semantic Scholar returned HTTP 429 and was not used.
- **No code produced results** beyond these API queries.

## Credentials

- **OpenAlex:** the user-supplied key was passed only as the `api_key=` URL parameter to `api.openalex.org`. Its value is **not** stored in any file. To retrace, set your own key, e.g. `OPENALEX_API_KEY`, and append `&api_key=$OPENALEX_API_KEY`.
- **Crossref:** no key; `mailto=` parameter.
- **Europe PMC:** no key.
- **Web search/fetch:** no user-visible env vars. The skill may fall back to Serper; its key name is internal to the ability server.

## Ordered log of searches (WebSearch unless noted)

1. Maillart arXiv 2606.03919 endogenous exogenous diffusion concept pairs OpenAlex quantum computing
2. Kuhn Perc Helbing 2014 "Inheritance patterns in citation networks reveal scientific memes" meme score sticking sparking
3. Bettencourt Cintron-Arias Kaiser Castillo-Chavez 2006 "The power of a good idea" reproduction number Feynman diagrams
4. De Domenico Omodei Arenas "Quantifying the diaspora of knowledge in the last century" Applied Network Science
5. "source-sink" dynamics scientific ideas diffusion across disciplines citation (adversarial C0)
6. "reproduction number" scientific topics fields citation self-sustaining idea spread disciplines estimate (adversarial C0)
7. SEIZR model diffusion of research topics across disciplines Scientometrics 2022 (not located)
8. Hawkes process endogenous exogenous growth scientific topics self-exciting citation bursts Crane Sornette
9. Kiss Broom Craze Rafols 2010 "Can epidemic models describe the diffusion of topics across disciplines"
10. Bettencourt Kaiser Kaur 2009 "Scientific discovery and topological transitions in collaboration networks"
11. Cheng Smith Ren Cao Smith McFarland 2023 "How new ideas diffuse in science"
12. Chinazzi Goncalves Zhang Vespignani 2019 "Mapping the physics research space"
13. Guevara … 2016 "The research space"
14. semantic change of scientific concepts across disciplines word embeddings meaning shift …
15. Uzzi … 2013 "Atypical combinations and scientific impact"
16. Foster Rzhetsky Evans 2015 "Tradition and innovation …"
17. "co-occurrence" partners of a concept when it enters a new field … (adversarial C1)
18. methods travel together across scientific fields co-diffusion of techniques bundles citation analysis (adversarial C2)
19. Ugander … 2012 "Structural diversity in social contagion"
20. Weng Menczer Ahn 2013 "Virality prediction and community structure in social networks"
21. Fontaine Gargiulo Dubois Tubaro 2024 "Epistemic integration and social segregation of AI in neuroscience"
22. Sun Kaur Milojevic Flammini Menczer 2013 "Social dynamics of science"
23. Zeng … 2019 "Increasing trend of scientists to switch between topics"
24. researchers migrating between fields carry concepts … newcomers vs incumbents (adversarial C4)
25. "Embedding and customizing templates in cross-disciplinary modeling" Synthese
26. diffusion of research methods across disciplines co-adoption … (adversarial C2)
27. "Adapting to LLMs" insiders outsiders … arXiv 2505.12666
28. idea diffusion science via coauthorship social ties versus citation reading … (adversarial C4)
29. Chavalarias Cointet 2013 "Phylomemetic patterns in science evolution"
30. Krenn 2023 Science4Cast AUC baselines
31. Gu Krenn 2025 Impact4Cast
32. Rotolo Hicks Martin 2015 "What is an emerging technology?"
33. Small Boyack Klavans 2014 "Identifying emerging topics in science and technology"
34. Porter Garner Carley Newman 2019 emergence scoring
35. Xu Winnink … "Topic-linked innovation paths" / co-word emerging topics (the Xu et al. 2021 TFSC paper was not located)
36. typology of emergence trajectories … clustering temporal network indicators
37. keyword co-occurrence network emerging topic detection … precursor burst
38. OpenAlex topics classification CWTS citation clusters 4516 topics …
39. OpenAlex legacy concepts deprecated 2025 2026 …
40. Culbert reference coverage analysis of OpenAlex …
41. help.openalex.org search … stemming stop words boolean phrase no_stem semantic search
42. OpenAlex API filter OR values maximum 100 per_page 200 cursor paging group_by limit
43. help.openalex.org "Example costs" …
44. OpenAlex snapshot download free S3 2026 size
45. OpenAlex author disambiguation accuracy evaluation …
46. OpenAlex works mesh filter "mesh.descriptor_ui" …
47. help.openalex.org keywords works how keywords are assigned 2026
48. Applied Network Science collection "Networks for everyday life" call for papers
49. "Networks for everyday life" Applied Network Science guest editors deadline 2026
50. "Author Multidisciplinarity and Disciplinary Roles in Field of Study Networks" Applied Network Science
51. Applied Network Science s41109-023-00592-1; s41109-023-00572-5; s41109-025-00693-z
52. Applied Network Science submission guidelines …
53. Fontaine "Dynamical cartography" …
54. Leydesdorff Wagner Bornmann 2019 DIV; Stirling 2007 diversity framework
55. Chinazzi 2019 knowledge density … (effect size not found)
56. MeSH descriptor introduction year as ground truth emerging topics …
57. large-scale scientific concept extraction dataset linked to Wikidata OpenAlex …
58. Computer Science Ontology CSO classifier Salatino Augur …
59. concept crosses into new discipline … knowledge recombination host field (adversarial C1)
60. persistence of emerging research topics … "topic survival"
61. "methods" transferred between fields travel as package … (adversarial C2)
62. Cheng McFarland … "research traditions" measure (full text paywalled)
63. Crane Sornette 2008 PNAS; Kleinberg 2003 bursts; Centola 2010

## Pages and PDFs fetched or grepped (full text, not snippets)

**arXiv PDFs, grepped with `aii_fast_web_fetch.py grep`:**
- 2606.03919 (Maillart: abstract, targets, Table 2 R²)
- 1404.3757 (Kuhn: P_m, M_m, δ)
- physics/0502067 (Bettencourt: text layer garbled, R₀ values not extractable)
- 1604.00696 (De Domenico: source/sink indices)
- 0905.3585 (Kiss)
- 2511.03378 (Fan et al.)
- 1201.0676 (knowledge epidemics review)
- 1602.08409 (Guevara)
- 2310.01046 (Fontaine 2024)
- 1306.0158 (Weng: precision/recall)
- 2404.05861 (Gates et al.)
- 2402.08640 (Impact4Cast: data counts, RAKE, OpenAlex)
- 2210.00881 (Science4Cast)
- 2401.16359 (Culbert)
- 1412.6683 (Rafols coherence)
- q-bio/0502035 (Guimerà–Amaral roles)
- 0708.2090 (Hidalgo φ)
- 1807.04115 (Leydesdorff DIV)

**Also grepped:** the Ugander 2012 PNAS PDF (pdodds.w3.uvm.edu mirror).

**arXiv abstract pages fetched:** 1912.08928, 2507.01651, 2603.17594, 2001.07199, 2302.13054, 1905.10960, 2608.28822, 2101.08293, 2406.18792, 2506.15959, 2404.05861, physics/0502067.

**WebFetch pages:**
- help.openalex.org: `/hc/en-us/articles/24736129405719-Topics`, `/data/topics/`, `/data/concepts/`, `/api/deprecations/` (also grepped), `/access/pricing/`, `/api/searching/`, `/api/filtering/`, `/access/example-costs/`
- blog.openalex.org/openalex-rewrite-walden-launch/

**Blocked** (303 to an idp login, or a JS page), so snippet-level only: link.springer.com (collection page, articles, PDFs), epjdatascience.springeropen.com, nature.com (HSSC), pmc.ncbi.nlm.nih.gov (reCAPTCHA).

## API queries (2026-09-28)

**OpenAlex.** 36 calls in total: 29 list/filter or entity calls at `cost_usd` 0.0001 each (≈ $0.003), plus 7 free singleton DOI lookups for ANS abstracts. List/filter queries were `https://api.openalex.org/works?filter=…&per_page=1&select=id`, with filters:
- `publication_year:2015&per_page=200`, to test per_page = 200: accepted.
- `mesh.descriptor_ui:D003920,publication_year:2015`: error; the response lists valid filter fields.
- `concepts.id:C41008148,publication_year:2015` → 3,558,312.
- `publication_year:2010,type:article` → 5,407,188. With `referenced_works_count:0` → 3,515,223. With `has_abstract:true` → 3,119,128.
- For y in 2005, 2010, 2016, 2020, with `publication_year:y,type:article,primary_location.source.is_core:true` [+ `referenced_works_count:0` | + `has_abstract:true`]:
  - 2005: 1,484,420 / 430,176 / 805,565
  - 2010: 1,937,677 / 517,436 / 1,143,531
  - 2016: 2,528,086 / 580,829 / 1,541,457
  - 2020: 2,957,439 / 408,771 / 2,002,355
- `publication_year:2016,type:article,primary_location.source.is_core:true,has_references:true` → 1,947,257.
- `concepts.id:C41008148,publication_year:2025` → 5,380,708.
- 2026: `publication_year:2026` → 32,364,822; with `concepts.id:C41008148` → 10,514,189; with `concepts_count:0` → 0.
- `publication_year:2020&group_by=primary_topic.subfield.id` → 200 groups returned on the first page.
- `/subfields?per_page=1` → 252; `/topics` → 4,516; `/keywords` → 65,004 (first items "Computer science", "Medicine"); `/concepts` → 65,026.
- One 2025 PubMed article (`has_pmid:true`) with `select=concepts,mesh,keywords,topics`: keywords identical to concepts; mesh present.
- Two random samples, `sample=6&seed=7&select=id,title,concepts,keywords`, for 2012 and 2024: keywords equal concepts in 11 of 12 works.
- 16 free singleton lookups, `works/doi:10.1007/s41109-…?select=…abstract_inverted_index`, for the ANS abstracts, plus 5 more for Cheng 2023, Kim 2024, Macasaet 2026, Small 2014 and Uzzi 2013.

**Crossref.** `https://api.crossref.org/journals/2364-8228/works?query.bibliographic=<q>&rows=10–15`, with q in {scientific knowledge network evolution; citation network science disciplines; co-occurrence network keywords topics; interdisciplinary research network; diffusion of ideas; emerging topics research fields; science of science collaboration; concept network semantic; OpenAlex; research topics evolution; fields of study network; novelty scientific papers network; knowledge graph link prediction science; technological convergence patents; Microsoft Academic Graph; Web of Science network; bibliographic coupling; keyword network; participation coefficient; temporal community detection evolution; emergence network}. One query returned non-JSON and was skipped.

**Europe PMC.**
- `rest/search?query=JOURNAL:"Appl Netw Sci" AND PUB_YEAR:[2023 TO 2026] AND IN_EPMC:Y`.
- `rest/{PMCID}/fullTextXML` for PMC12775101, PMC12102006, PMC11926000, PMC12279612 and PMC9673898, parsed for section titles, keywords, abstract length and back matter.
- `rest/PMC12018473/fullTextXML`: this editorial turned out to be in *Frontiers in Research Metrics and Analytics*, not ANS, and was **not** used as ANS evidence.

**dblp** (`search/publ/api … venue:Appl._Netw._Sci.`): timed out or returned nothing, so it was not used.

## How to retrace

1. Run the search list above in order; expect ranking drift.
2. Grep the listed arXiv PDFs with the same patterns, e.g. `grep --pattern "endogenous|exogenous|R2 test"` on 2606.03919.
3. Re-issue the OpenAlex queries with your own key. Counts will change as OpenAlex updates, and the keywords = concepts behaviour and concepts on 2026 works should be re-checked with the same two sample queries.
4. The conclusions (novelty grades and ranking) rest mostly on items verified at VERBATIM/ABSTRACT level. Snippet-level items are flagged in `research_report.md`.
