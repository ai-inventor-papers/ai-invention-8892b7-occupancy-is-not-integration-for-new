"""Builds .terminal_claude_agent_struct_out.json (iteration-1 audit of the internal research report).

Every number cited below was recomputed from the artifact workspaces under ../../gen_art/ (read-only);
see README.md for the exact files and commands.
"""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent / ".terminal_claude_agent_struct_out.json"

critiques = [
    {
        "category": "evidence",
        "severity": "major",
        "description": (
            "An executed artifact is missing from the record. gen_art/gen_art_dataset_2 ('Weighted sample of 260k OpenAlex "
            "science papers', the WHOLE-SCIENCE BACKGROUND CONCEPT-NETWORK SUBSTRATE that the strategy ordered as artifact "
            "direction 2) ran to completion and wrote schema-valid outputs (expected_files_valid=true). Its worker is flagged "
            "failed only because of a REPL stall timeout ('no new JSONL records for 2096s') after the outputs were written. The "
            "report never mentions it: no section, no [ARTIFACT] marker, no dead-end entry. It holds 259,716 design-weighted works from 1,260 strata "
            "(weights sum to the frame population, 149,116,575); 6,325 exact subfield x year totals; 400 exact concept x block "
            "subfield profiles for 100 calibration concepts; and 69,824 taxonomy rows. OpenAlex cost was $0.1952. Its KEY FINDING "
            "is a negative result that constrains iteration 2: sample-based per-concept subfield profiles are unreliable. In "
            "data/calibration_by_decile.csv the median share TV distance is 0.41-0.79 by frequency decile, and top-subfield "
            "agreement is only 0.28-0.65. Host-nativeness (C1 and C2, the dossier's top-ranked candidates) and the concept-concept "
            "background network were supposed to come from this substrate. So the record currently hides that the top candidate's "
            "key input cannot be computed from the sample and needs paid exact profiles "
            "(scripts/fetch_concept_profiles.py, $0.0001 per concept-block). Its 6,325-row totals table also coexists with "
            "dataset_1's 25,195-row table, and the two use different frames (dataset_2 excludes conference papers). The report "
            "does not say which denominator the analysis will use."
        ),
        "suggested_action": (
            "Add an 'Artifact 5: whole-science background sample' subsection with an id for gen_art_dataset_2. Include the "
            "full calibration_by_decile table (10 rows: median exact total, median sample raw count, relative error, TV, "
            "top-subfield agreement) and the stratification/weighting design. Also state the hazards from data_card.md: about "
            "12% of the weighted frame has default low-confidence topic T14423, and concept ancestors are no longer served. Record "
            "the worker's 'failed' status and why the outputs are nonetheless usable. Add a dead-end line: 'sample-based host "
            "nativeness ruled out (TV 0.41-0.79); exact profiles required'. State which subfield-year denominator (dataset_1 or "
            "dataset_2 frame) iteration 2 will use."
        ),
    },
    {
        "category": "methodology",
        "severity": "major",
        "description": (
            "The pre-registration is not in the record. The strategy (gen_strat_1) fixed a complete screen before any data. "
            "UNIT: concept c x non-origin subfield d x focal year t in 2010-2014, with >=10 d-papers in W1=[t-5,t]. PRIMARY "
            "MEASURE: out-of-sample ROC-AUC for establishment in W2=[t+1,t+5], where establishment means >=5 W2 d-papers by "
            "author-disjoint newcomers AND presence in >=3 of 5 W2 years, under concept-grouped 5-fold CV. BASE model: volume, "
            "momentum, age, subfield size, entropy, subfield count, growing-edge breadth, Rafols, relatedness density and Maillart "
            "features. SELECTION RULE: delta-AUC concept-bootstrap 95% CI lower bound > 0 AND point gain >= 0.01 AND predicted "
            "sign, with a joint-carry rule within 0.005. CONFIRMATION: held-out concepts x 2016-2018, plus sign retention in "
            "MeSH or phrase populations and under the venue habitat. NULL OUTCOME: if no candidate survives, report that "
            "breadth/momentum indicators already carry the signal and pivot to RQ1. The report says the dossier 'ranks five "
            "candidate mechanisms' but records none of this, nor the dossier's exact formulas (rho/m, A*, CT, P/SD/closure, "
            "demic share, Y1 PPML with d x t and o x t fixed effects). A pre-registration that exists only in a strategy JSON "
            "cannot protect the iteration-2 screen from tuning-after-looking, and the paper step cannot cite it."
        ),
        "suggested_action": (
            "Insert a 'Pre-registered screen (fixed before data)' subsection in Iteration 1 that reproduces the unit, windows, "
            "establishment definition, BASE covariates, candidate scores with predicted signs, selection rule, tie rule, "
            "confirmation rule and null-outcome pivot verbatim from gen_strat_1. Include the dossier's formula table from "
            "research_report.md section (2), with a timestamp and a pointer to gen_strat_1/.terminal_claude_agent_struct_out.json."
        ),
    },
    {
        "category": "rigor",
        "severity": "major",
        "description": (
            "Gate A is misdefined, and its pass is overstated. (i) The report says the host traced share counts papers 'outside "
            "the origin subfield that cite at least one earlier concept paper in the same host subfield'. The code "
            "(gen_art_dataset_1/assemble.py lines 369-374) counts ANY earlier c-paper of the concept as a parent, from any "
            "subfield, and the quality-report notes say the same. The measured 55.18% therefore includes citations to "
            "origin-subfield and other-host papers, which is exactly the importation the source/sink construct must separate "
            "from local reproduction. It does not show that within-host lineages are dense enough to estimate a local "
            "reproduction ratio. (ii) The pooled 0.5518 is dominated by 2016-2024 papers. In context/quality_report.md the "
            "main-arm host traced share by year is 0.317 (2010), 0.361 (2011), 0.348 (2012), 0.413 (2013) and 0.517 (2014), and "
            "0.08-0.31 in 2005-2009. These are exactly the W1 windows of the pre-registered screen (t = 2010-2014, "
            "W1 = [t-5, t]), and three of the five focal years are below the 0.40 marker. (iii) The quality report states that the "
            "0.40 threshold was 'marked, NOT applied'; the report converts this into 'This passes Gate A'. (iv) The reference arm's "
            "traced share (0.5311, n=92,969 c-papers) is omitted, although it is the benchmark that rho is to be normalised "
            "against."
        ),
        "suggested_action": (
            "Correct the definition to match the code. Recompute a true within-host traced share (parent restricted to the same "
            "host subfield d, excluding F and the top-5) from works/*.parquet plus concept_work.parquet, pooled and by year, over "
            "W1 windows for t=2010-2014 only. Report the full by-year table and the reference-arm row. Restate Gate A as "
            "'passes pooled, fails in 3/5 screen focal years' unless the recomputation shows otherwise. Record the consequence "
            "for C0: either the network-only graft fallback, or restricting C0 to later focal years."
        ),
    },
    {
        "category": "evidence",
        "severity": "major",
        "description": (
            "The realised pool cannot support the pre-registered screen, but the report says it can ('The current 184 are "
            "sufficient for the screen and held-out folds'). I counted units from gen_art_dataset_1 works/*.parquet + "
            "concept_work.parquet: (c, d != origin subfield, t) edges with >=10 d-papers in W1=[t-5,t]. The screen fold "
            "yields 13 / 23 / 40 / 54 / 63 units for t = 2010 / 2011 / 2012 / 2013 / 2014 (193 unit-years, largely repeated "
            "edges), from at most 9 / 17 / 23 / 27 / 34 distinct concepts. The held-out fold yields 73 / 84 / 93 for "
            "2016 / 2017 / 2018. A concept-grouped 5-fold CV with a 1,000-rep concept bootstrap on ~34 concepts cannot deliver "
            "a delta-AUC CI lower bound above 0 for a 0.01 gain. There is also an unreported cohort confound. "
            "logs/assemble_summary.json shows the period split is confounded with cohort: 2005-07 concepts have no held-out "
            "focal years (38/0), and 2012-16 concepts have no screen focal years (0/65). Screen and held-out therefore compare "
            "different concept ages and F-bands. The report also misdescribes the folds. It presents 'screen fold of 123 (focal "
            "years 2010-2014)' and 'held-out fold of 61 (focal years 2016-2018)' as if fold implied period, but the fold is a "
            "sha1 concept split and focal-year tags are separate."
        ),
        "suggested_action": (
            "Add a table of eligible screen units by fold x focal year (units, distinct concepts, distinct host subfields) and "
            "the fold x F-band table from assemble_summary.json. State the cohort confound explicitly. Replace 'sufficient' with "
            "a pilot power statement based on these counts. Before any new metric is added in iteration 2, spend budget on "
            "SAMPLES: resume the 220 pending concepts (uv run hydrate.py --resume) and relax the >=10 W1 threshold only as a "
            "pre-declared sensitivity. Do not add candidate readouts over a panel this size."
        ),
    },
    {
        "category": "evidence",
        "severity": "major",
        "description": (
            "Several descriptive numbers in the report do not match the artifact when recomputed. (a) Match evidence: the report "
            "says 'Of these [214,798 links], 56,997 matched in the work title, 51,966 in the abstract, 10,177 through Semantic "
            "Scholar only, and 2,689 through OpenAlex concept indexing alone'. These four counts sum to 121,829, which is the "
            "MAIN-arm link count (116,576 unique works). Across all 214,798 links, concept_work.parquet gives oa_abstract "
            "98,192, oa_title 92,043, s2_only 21,509 and oa_index_only 3,054. (b) Routes: the report says 'Of the 184 main "
            "concepts, 26 ... natively ... and 180 ... through Semantic Scholar ... Two concepts entered through both routes'. "
            "26+180 = 206 is the WHOLE pool, including reference concepts. Among the 184 main concepts it is 24 native and 160 "
            "S2-mapped. No 'both routes' category exists in any output, so that sentence is untraceable. (c) Sense check: the "
            "report says 'the dominant sense ... covers fewer than half the matched works'. assemble.py line 444 flags "
            "dominant_share < 0.7 on year-F titles, and the 21 flagged concepts have a median share of 0.50 (range 0.14-0.69). "
            "(d) Reference arm: the report defines it as 'age at least 10 years, flat incidence, at least 30 papers per year'. "
            "screen.py line 29 requires >=5 hits in every year 1998-2004 with a 7-year sum of 70-700, and 22 of the 60 sampled "
            "were hydrated. (e) MeSH: 3,446 descriptors survive the provenance filter and 3,430 remain after dropping empty "
            "surface forms (selection_flow.json). (f) Target size: the strategy targeted ~600 concepts with a 400 floor, and the "
            "report calls 400 the 'target'."
        ),
        "suggested_action": (
            "Correct each sentence in place with a marked correction note. Relabel the evidence mix as main-arm (121,829 links) "
            "and add the all-links row. Give routes as main 24/160 and reference 2/20, and delete the 'both routes' claim. Use the "
            "code's 0.70 sense threshold and list the 21 flagged phrases. State the reference rule as coded. Name the source "
            "file for every count (logs/assemble_summary.json, concept_work.parquet, selection_flow.json)."
        ),
    },
    {
        "category": "methodology",
        "severity": "major",
        "description": (
            "The venue habitat is described as something it is not. The report says the venue-habitat file 'assigns 15,261 venues "
            "to their dominant subfield based on pre-period publication shares' and calls it the 'citation-independent habitat "
            "robustness check'. The README (Deviation 4) and assemble.py venue_table() show that shares come from each source's "
            "ALL-YEARS OpenAlex topic counts in the 2026 snapshot. The pre-period variant was never computed because credits ran "
            "out. Those topic counts are produced by the same citation-reading topic classifier whose temporal label leakage the "
            "dossier flagged (the reason every headline claim needs this check). As built, the habitat is neither pre-period nor "
            "citation-independent. The dossier's key control is therefore weaker than recorded."
        ),
        "suggested_action": (
            "State the actual construction and label the habitat 'all-years, topic-derived (not citation-independent)'. Add a "
            "dead-end/shortfall entry. Either compute the 2000-2004 source x subfield group_by (a few hundred 1-credit calls) or "
            "use a genuinely citation-independent assignment such as ASJC/ISSN journal classification, and record which one "
            "iteration 2 uses."
        ),
    },
    {
        "category": "evidence",
        "severity": "major",
        "description": (
            "Dead ends are present in the artifacts but missing from, or mis-explained in, the report. (1) The taxonomy "
            "vocabulary arm (OpenAlex keywords, legacy concepts, new MeSH terms) had a 2.2% eligibility yield (3/134). It was "
            "stopped deliberately because pre-2005 tag counts are uninformative: 'optogenetics' had 152 pre-2005 tagged works and "
            "'blockchain' 191, since the tagger is retroactive (dataset_1 README, Deviation 1). The report instead says the "
            "keyword arm 'did not produce enough eligible candidates within the credit budget'. The evidence that killed it is "
            "about retroactive tagging, not money, and it bears directly on whether OpenAlex concepts can date emergence. "
            "(2) The pricing probe: a paged list call with a search filter costs 10 credits, so the planned cursor-paging "
            "retrieval was abandoned in favour of group_by=ids.openalex and then Semantic Scholar discovery. This is why 160/184 "
            "main concepts are S2-mapped, and it is not recorded. (3) The phrase-pool yield failure is attributed to 'low "
            "precision of noun-phrase extraction'. The artifact's own diagnosis (dataset_4 README) is different: phrases seen "
            "once in a ~0.1% sample are overwhelmingly compositional or pre-2005 (408 'never >=3 papers/yr', ~430 pre-existing). "
            "The recorded fix is lowering the n_early bound, which multiplies yield 6-11x per the yield curve in logs/summary.json. "
            "(4) The main shortfall (184/400) is attributed only to credit exhaustion. The README says the binding constraint "
            "after credits ran out was the free-singleton rate (~14 works/s) combined with heavy-tailed concept sizes, and that "
            "most credits were consumed by sibling artifacts sharing the key."
        ),
        "suggested_action": (
            "Add each of the four items to 'Dead ends and shortfalls' with its killing evidence and source file: "
            "screen/screen_results.jsonl yield and the optogenetics/blockchain tag counts; probes/ credit prices; the "
            "logs/summary.json yield curve and rejection-reason counts; and credit_ledger.jsonl with the hydration throughput. "
            "State the decision each one forces for iteration 2."
        ),
    },
    {
        "category": "rigor",
        "severity": "major",
        "description": (
            "Claims of validation overreach what ran. (a) Recall audit: the report says it shows 'the retrieval pipeline captures "
            "a consistent fraction of each concept's literature'. But 160/184 main concepts were DISCOVERED through Semantic "
            "Scholar, so comparing their counts with S2 counts measures only mapping and verification loss, not recall. The "
            "artifact says so ('for route-B concepts it measures mapping and verification loss'), and it says the "
            "OpenAlex-native comparison could not run. Recall against OpenAlex is therefore unmeasured for ~87% of the pool. "
            "(b) The dossier's own confidence section states that the novelty grades rest on 'targeted, not systematic, "
            "searches' and that Cheng et al. 2023's full text was not read. The report calls it 'a systematically assembled base "
            "of prior work'. (c) The dossier notes 'Only about 25% of new MeSH descriptors are genuinely new concepts, so MeSH is "
            "a weak ground truth'. The report omits this while presenting MeSH as an independent confirmation arm. (d) For "
            "178/191 MeSH concepts only PubMed-indexed works were retrieved. Network analyses 'see only their PubMed-indexed "
            "neighbourhood' (provenance.md), so their concept-discipline edges are structurally biased toward biomedical "
            "subfields and not comparable to the main corpus. (e) The route_calibration result (union vs plain OpenAlex search, "
            "median ratio 0.8598, range 0.54-0.91 over 10 concepts) and the 60-record provenance spot check (0 errors) are "
            "missing, although they are the MeSH arm's only validity numbers."
        ),
        "suggested_action": (
            "Rewrite the recall-audit sentence to state what it measures, split by route. Replace 'systematically assembled' with "
            "the dossier's own confidence statement. Add the MeSH weak-ground-truth caveat, the route_calibration and spot-check "
            "numbers, and an explicit statement that 178/191 MeSH concepts lack non-PubMed works and cannot be used for "
            "concept-discipline breadth until retrieval_complete is true."
        ),
    },
    {
        "category": "scope",
        "severity": "major",
        "description": (
            "Coverage against the user's request is partial, and the record hides part of the gap. The request asks for "
            "semantically grounded concepts: extraction, normalisation of alternative expressions, linking to OpenAlex, "
            "taxonomies or knowledge bases, and retaining unlinked concepts. It also asks to 'create training-test labelled "
            "datasets and then train your own models'. In the realised main pool, concept identity is a surface-form match on "
            "arXiv-mined n-grams. Only 1 of 184 main concepts carries any external link (the input.links field in data_out.json), "
            "acronyms are 'stored_not_used', and none of the grounding artifact's labels, variant pairs or classifiers were "
            "applied to the main pool. The labelling itself is nearly blind to variants: model A labelled VARIANT_OF on 1 of "
            "1,491 items, and the per-class A-B kappa for VARIANT_OF is -0.0007. Sampled main phrases include fragments such as "
            "'modulo theory', 'detector in pp collision', 'multi label image', 'lhc signature' and 'high dimensional gaussian'. "
            "Nothing yet addresses RQ1 structural indicators, community detection across snapshots, the data-derived typology, "
            "representative cases, or the concept-concept and concept-discipline networks. That is expected after a data-only "
            "iteration, but the report should say it. Its framing (source/sink breadth vs Shannon/Rao-Stirling) is also narrower "
            "than RQ1+RQ2 as posed."
        ),
        "suggested_action": (
            "Add a coverage paragraph mapping each of the user's six activities to done / partial / not started, with the "
            "artifact for each. State plainly that the main pool is surface-form grounded with 1/184 linked, and that no "
            "normalisation model has been trained. Commit iteration 2 to training and evaluating the concept/variant classifier "
            "on the D2/D3 splits and to building the yearly concept-concept and concept-subfield snapshots, so that RQ1 does not "
            "fall away behind the RQ2 mechanism screen."
        ),
    },
    {
        "category": "clarity",
        "severity": "major",
        "description": (
            "The reasoning behind the run's framing is not recorded and conflicts with its own evidence. The title, introduction "
            "and 'viability question' centre on C0 source/sink viability ('occupancy is not integration'). The dossier the "
            "report cites ranks C1 host anchoring first and C0 second. It grades the 'hollow breadth' claim P1 as only MEDIUM, "
            "because Rafols diversity-vs-coherence and DIV already separate presence from integration. The report never says why "
            "the write-up headlines C0 anyway. The strategy's explicit rationale is also missing: a five-way screen on one "
            "shared corpus, rather than a deep build of C0, because C0 'might turn out to be relabelled momentum'. The nearest "
            "published result for the viability idea is also left out: Maillart et al. 2026 find that endogenous reinforcement "
            "is almost unpredictable (test R2 = 0.018) while exogenous diffusion is predictable (R2 = 0.78). That result speaks "
            "directly to whether local reproduction carries signal, and it is verified in research_verification.json."
        ),
        "suggested_action": (
            "Add a short 'Why this iteration did what it did' paragraph quoting the strategy rationale and the five-candidate "
            "framing. State that C0 is one of five screened candidates, not the adopted hypothesis, and record the Maillart "
            "R2 = 0.018 vs 0.78 result, plus the dossier's statement of what would lower each grade, as the bar a C0 or C1 win "
            "must clear."
        ),
    },
    {
        "category": "evidence",
        "severity": "minor",
        "description": (
            "Tables and diagnostics that exist on disk are left out. From dataset_1: the by-year Gate-A table (25 rows), "
            "author-id coverage (0.9019; 0.8456 in Physics & Astronomy, relevant to the C4 newcomer definition), dup-group share "
            "0.0539, traced share excluding F only (0.6493), flags dup_groups_present=154 and burst_start=1, and cost (2,566 "
            "credits, $0.36 LLM). From dataset_3: the final pool mix (99 core 2006-2016, 14 w1, 78 w2, so 41% of the held-out "
            "set comes from the widening pools), the F distribution (129/191 with F in 2005-2009), the 122,645-row / "
            "117,253-work works table, and 1,784 credits. From dataset_4: the survivorship-free pool is not 1,000 'novel' "
            "concepts. 413 of the 1,000 are labelled NOT_CONCEPT (401) or TOO_GENERIC (12) by model A (including a 100-phrase audit arm), "
            "only 71 are linked, and the sealed later-dead share among 17 eligible LLM-arm phrases is 0.588. Among the eligible "
            "'concepts' are 'cut anddried answer', 'image proplus software' and 'mgimo university'. Also missing are model B's "
            "human-anchor numbers (kappa 0.39, P 0.63, R 0.94) and the per-class kappas."
        ),
        "suggested_action": (
            "Append these as tables under each artifact subsection with file paths (context/quality_report.md, "
            "logs/assemble_summary.json, selection_flow.json, coverage_qa.json, data_out/pool_early.json, logs/summary.json, "
            "labelling/quality.json). Relabel the phrase pool as '1,000 text-mined candidate keys (587 CONCEPT-labelled)'."
        ),
    },
    {
        "category": "rigor",
        "severity": "minor",
        "description": (
            "Traceability is at the artifact level only. The report tags each subsection with an [ARTIFACT] marker but names "
            "almost no output files. There is no workspace path for Tables 3, 5 and 6 or for the Gate-A, recall, or "
            "cost numbers, and the frame hash (sha256 80e3f244...0c44) that makes the 'outcome-blind' claim checkable is not "
            "quoted. Run bookkeeping is also absent: worker statuses (dataset_2 failed on timeout; others succeeded), "
            "per-artifact OpenAlex credits (2,566 + 1,952 + 1,784 + 1,847), and the fact that four artifacts raced on one free "
            "key."
        ),
        "suggested_action": (
            "After each table, add 'Source: <artifact>/<file>'. Quote the frame sha256 and its freeze time (11:55 UTC). Add a "
            "run-ledger table: artifact, status, OpenAlex credits, LLM $, wall time."
        ),
    },
]

review = {
    "overall_assessment": (
        "Iteration 1 is a data-and-pre-registration iteration. No hypothesis test ran, and the report says so honestly. The "
        "headline descriptive numbers are real and come from executed artifacts. I recomputed them from the workspaces. The "
        "counts reconcile: 206 concepts (184 main + 22 reference), folds 123/61, 214,798 links / 208,374 works, host traced "
        "share 0.5518 over 41,861 host c-papers, recall ratio 0.84 / Spearman 0.976, MeSH 191 with branch groups "
        "62/47/32/22/17/11, stratified corpus 93,600, and the labelling kappas and precision/recall. results_reported is "
        "therefore true. As a RECORD, however, the report has five serious defects. (1) An executed artifact, gen_art_dataset_2 "
        "(the 259,716-work background network substrate), is entirely absent, together with its negative calibration finding "
        "(sample-based subfield profiles TV 0.41-0.79) that undermines host-nativeness for the top-ranked candidate. (2) The "
        "pre-registered screen (unit, establishment outcome, BASE model, delta-AUC selection rule, confirmation rule, null pivot) "
        "fixed in the strategy is not written down. (3) Gate A is described with a definition the code does not implement. "
        "Parents are any earlier c-paper, not same-host ones, and by year the host traced share is 0.32-0.52 across the "
        "screen's 2010-2014 focal years, below 0.40 in three of five. (4) The claim that 184 concepts are 'sufficient' is "
        "contradicted by the data: my count of pre-registered screen units is 13-63 per focal year from at most 34 concepts, "
        "and fold is confounded with cohort. (5) Several numbers and definitions are wrong on inspection: evidence mix "
        "attributed to all links but actually main-arm, routes 26/180 vs 24/160 among main, a fabricated 'two concepts via "
        "both routes', sense-check threshold 0.7 not 0.5, the reference-arm rule, and a venue habitat called pre-period and "
        "citation-independent when it is all-years and topic-derived. Dead ends (taxonomy arm yield 2.2% due to retroactive "
        "tagging, search-paging cost, phrase-pool diagnosis) are missing or mis-explained. No positive result is claimed, so "
        "no novelty credit is at stake yet. The nearest neighbour the record should carry for C0 is Maillart et al. 2026 "
        "(endogenous R2 0.018 vs exogenous 0.78). Coverage of the user's request is partial. Grounding of the main pool is "
        "surface-form only (1/184 linked, no trained normaliser), and RQ1 networks, typology, communities and cases have not "
        "started. None of these problems requires new compute to fix in the record, except the within-host Gate-A "
        "recomputation and the unit count, which are cheap local computations. Soundness is 2, not 1: the Gate-A pass holds "
        "under the strategy's own pre-registered definition; the report misdescribes that definition rather than contradicting "
        "its evidence."
    ),
    "strengths": [
        "Honest top-line framing: the report states that no experiment or hypothesis test was executed and that no "
        "quantitative result about the hypothesis exists yet.",
        "Most headline counts recompute exactly from the artifacts: 206/184/22 concepts, 123/61 folds, 214,798 links, 208,374 "
        "works, Table 3 per-field Gate-A figures, recall 0.84/0.976, MeSH 191 and branch groups, the 93,600-row corpus and "
        "the labelling-quality table (kappa 0.259/0.267, 325/411 adjudications with A).",
        "Real outcome-blind design in the underlying artifact: the frame was frozen and sha256-hashed before post-F+2 data, "
        "screening truncated to <=F+2 on receipt, and validate.py asserts it. The report correctly mentions the freeze.",
        "Shortfalls are acknowledged rather than hidden: 184 vs 400 concepts, arXiv/physics skew (363/366), 13/191 MeSH "
        "concepts fully retrieved, 1 strict phrase vs 150 target, and silver-only labels.",
        "The labelling-quality reporting is candid: low inter-model kappa, B's CONCEPT bias with a confusion-matrix "
        "explanation, and a human-anchored check against SemEval-2017/SciERC reported as the only human-referenced number.",
        "Useful OpenAlex facts are preserved (keywords = legacy concepts in 11/12 works; topic label leakage; zero-reference "
        "shares by year) with a stated consequence for design.",
    ],
    "dimension_scores": [
        {
            "dimension": "soundness",
            "score": 2,
            "justification": (
                "Numbers come from executed artifacts and mostly recompute. But Gate A is misdefined relative to the code, "
                "and its pooled pass hides sub-threshold values in the screen's focal years. The claim that 184 concepts "
                "suffice is contradicted by a unit count of 13-63 per year from <=34 concepts. The venue habitat is "
                "misdescribed as pre-period and citation-independent, and the recall audit is over-read for S2-discovered "
                "concepts."
            ),
            "improvements": [
                "Recompute a same-host traced share by year over W1 windows and restate Gate A (+1 soundness if handled honestly).",
                "Add the screen-unit count table and the cohort-confound table, and replace 'sufficient' with a power statement.",
                "Correct the venue-habitat and recall-audit descriptions to what was built.",
            ],
        },
        {
            "dimension": "presentation",
            "score": 3,
            "justification": (
                "Clear, chronological, well-organised prose with sensible tables. Traceability stops at the artifact level "
                "(no file paths), and several definitions are paraphrased incorrectly."
            ),
            "improvements": [
                "Add 'Source: <artifact>/<file>' under every table and quote the frame hash.",
                "Add a run-ledger table (artifact, status, credits, $).",
            ],
        },
        {
            "dimension": "contribution",
            "score": 2,
            "justification": (
                "One of five executed artifacts (gen_art_dataset_2) is missing entirely along with a decisive negative "
                "finding. The pre-registered screen is not recorded, several on-disk tables are missing, and four dead ends "
                "are dropped or mis-explained."
            ),
            "improvements": [
                "Write up gen_art_dataset_2 with its calibration table (largest single gain).",
                "Transcribe the pre-registration and dossier formula sheet.",
                "Add the four dead ends with their evidence files.",
            ],
        },
    ],
    "critiques": critiques,
    "results_reported": True,
    "coverage": "partial",
    "blocking": False,
    "score": 3,
    "confidence": 4,
}

OUT.write_text(json.dumps(review, indent=1, ensure_ascii=False))
print("wrote", OUT, len(critiques), "critiques")
