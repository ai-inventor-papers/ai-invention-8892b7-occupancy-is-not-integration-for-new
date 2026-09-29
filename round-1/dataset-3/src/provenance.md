# Provenance: held-out MeSH population (`metadata_fold = heldout_mesh`)

Reserved confirmation population 1. Concept identity and synonymy come only from NLM MeSH; incidence is text-matched on OpenAlex titles/abstracts; nothing here was produced by an LLM or by OpenAlex keyword/topic taggers.

## Sources, versions, licences

| source | version / URL | licence / terms | use |
|---|---|---|---|
| MeSH descriptors XML | `desc2017.xml` https://nlmpubs.nlm.nih.gov/projects/mesh/2017/xmlmesh/ | NLM terms (free; attribution: "Courtesy of the U.S. National Library of Medicine") | selection snapshot for DateEstablished 2004-2016 (outcome-blind: holds descriptors later deleted) |
| MeSH descriptors XML | `desc2019.xml` https://nlmpubs.nlm.nih.gov/projects/mesh/2019/xmlmesh/ | NLM terms | snapshot for the widening years 2017-2018 only |
| MeSH descriptors XML | `desc2026.xml` https://nlmpubs.nlm.nih.gov/projects/mesh/MESH_FILES/xmlmesh/ | NLM terms | `still_in_mesh_2026` (descriptive only) |
| ASCII MeSH | `d2003.bin` ... `d2018.bin` (`/projects/mesh/1999-2010/asciimesh/`, `/projects/mesh/<YEAR>/asciimesh/`) | NLM terms | prior-year term->descriptor maps (promoted-term / rename checks) |
| MeSH replace lists | `replace2004.txt` ... `replace2018.txt` (`.../newterms/`) | NLM terms | rename detection (MH OLD -> MH NEW) |
| PubMed | NCBI E-utilities esearch (tool=aii_mesh_pop), queried 2026-09-28 | NLM terms | [tiab] PMID sets, exact yearly counts, [MeSH Terms:noexp] sets |
| OpenAlex | api.openalex.org, queried 2026-09-28 | CC0 | work records (singleton + batched ids.pmid lists), non-PubMed search, group_by counts |

Raw MeSH downloads were reduced to in-memory maps; the files stay in `raw/` (marked delete/redownloadable in the manifest).

## Selection flow (counts after every filter)

| step | n | details |
|---|---|---|
| desc2017.xml.gz descriptors (all classes) | 28472 |  |
| DescriptorClass == 1 (topical) | 27921 |  |
| DateEstablished year in [2006, 2007, 2008, 2009, 2010, 2011, 2012, 2013, 2014, 2015, 2016] | 5201 | {"by_year": {"2006": 958, "2007": 508, "2008": 501, "2009": 434, "2010": 422, "2011": 577, "2012": 455, "2013": 306, "2014": 298, "2015": 309, "2016": 433}} |
| has tree numbers and not all in V/Z branches | 5201 |  |
| provenance filter (drop PRIOR_EXPLICIT, PROMOTED_TERM, RENAMED) | 3446 | {"class_counts": {"PRIOR_EXPLICIT": 1256, "NO_PRIOR": 1231, "PRIOR_IMPLICIT": 2215, "PROMOTED_TERM": 440, "RENAMED": 59}} |
| non-empty matchable surface-form set | 3430 | {"dropped_empty_forms": 16} |
| PubMed [tiab] esearch done | 3430 |  |
| PubMed total 1995-2024 in 15..9,999 | 2802 | {"dropped_total_gt_9999": 236, "dropped_total_lt_15": 392} |
| PMID-date prune: <= 45 PMIDs entered by 2003-12-31 (else F < 2005 certain) | 1355 | {"dropped": 1447} |
| F (first year with >=5 PubMed papers, all earlier <5) in 2005..2016 | 462 |  |
| 15 <= PubMed count(F..F+2) <= 350 | 286 |  |
| PubMed total <= 8,000 (pre-screen pass) | 283 | {"outcomes": {"fail_F_window": 893, "fail_F_window_pmid_prune": 1447, "fail_total_gt_9999": 236, "fail_early_volume": 176, "pass": 283, "fail_total_lt_15": 392, "fail_total_cap": 3}, "n_with_yearly": 1355} |
| stratified outcome-blind working list (seed 20260928) | 283 | {"passers": 283, "tercile_cuts_pubmed_early": [19.0, 30.0], "branch_group_sizes": {"D": 59, "C": 30, "F+H-N": 52, "G": 21, "E": 63, "A+B": 58}, "branch_group_allocation": {"D": 59, "C": 30, "F+H-N": 52, "G": 21, "E": 63, "A+B": 58}} |
| desc2017.xml.gz descriptors (all classes) [widening w1] | 28472 |  |
| DescriptorClass == 1 (topical) | 27921 |  |
| DateEstablished year in [2004, 2005] | 1171 | {"by_year": {"2004": 671, "2005": 500}} |
| has tree numbers and not all in V/Z branches | 1171 |  |
| provenance filter (drop PRIOR_EXPLICIT, PROMOTED_TERM, RENAMED) | 718 | {"class_counts": {"PRIOR_EXPLICIT": 125, "NO_PRIOR": 211, "RENAMED": 147, "PRIOR_IMPLICIT": 507, "PROMOTED_TERM": 181}} |
| non-empty matchable surface-form set | 714 | {"dropped_empty_forms": 4} |
| PubMed [tiab] esearch done | 714 |  |
| PubMed total 1995-2024 in 15..9,999 | 629 | {"dropped_total_gt_9999": 29, "dropped_total_lt_15": 56} |
| PMID-date prune: <= 45 PMIDs entered by 2003-12-31 (else F < 2005 certain) | 298 | {"dropped": 331} |
| F (first year with >=5 PubMed papers, all earlier <5) in 2005..2016 | 84 |  |
| 15 <= PubMed count(F..F+2) <= 350 | 40 |  |
| PubMed total <= 8,000 (pre-screen pass) | 40 | {"outcomes": {"fail_total_gt_9999": 29, "fail_F_window": 214, "pass": 40, "fail_F_window_pmid_prune": 331, "fail_total_lt_15": 56, "fail_early_volume": 44}, "n_with_yearly": 298} |
| desc2019.xml.gz descriptors (all classes) [widening w2] | 29351 |  |
| DescriptorClass == 1 (topical) | 28767 |  |
| DateEstablished year in [2017, 2018] | 1088 | {"by_year": {"2017": 625, "2018": 463}} |
| has tree numbers and not all in V/Z branches | 1088 |  |
| provenance filter (drop PRIOR_EXPLICIT, PROMOTED_TERM, RENAMED) | 868 | {"class_counts": {"PRIOR_IMPLICIT": 701, "NO_PRIOR": 167, "PRIOR_EXPLICIT": 142, "PROMOTED_TERM": 76, "RENAMED": 2}} |
| non-empty matchable surface-form set | 868 | {"dropped_empty_forms": 0} |
| PubMed [tiab] esearch done | 868 |  |
| PubMed total 1995-2024 in 15..9,999 | 749 | {"dropped_total_gt_9999": 52, "dropped_total_lt_15": 67} |
| PMID-date prune: <= 45 PMIDs entered by 2003-12-31 (else F < 2005 certain) | 433 | {"dropped": 316} |
| F (first year with >=5 PubMed papers, all earlier <5) in 2005..2016 | 183 |  |
| 15 <= PubMed count(F..F+2) <= 350 | 134 |  |
| PubMed total <= 8,000 (pre-screen pass) | 133 | {"outcomes": {"pass": 133, "fail_F_window": 250, "fail_F_window_pmid_prune": 316, "fail_early_volume": 49, "fail_total_gt_9999": 52, "fail_total_lt_15": 67, "fail_total_cap": 1}, "n_with_yearly": 433} |
| widening w1 (2004-2005) pre-screen passers appended | 40 |  |
| widening w2 (2017-2018) pre-screen passers appended | 133 |  |
| retrieval (PubMed-route singletons fetched) | 442 |  |
| non-PubMed remainder retrieved (retrieval_complete) | 26 | {"skipped_budget": ["D000068276"]} |
| final rule on verified union counts (F 2005-2016, 20<=early<=300, total<=8000), rank order until N=200 | 191 | {"outcomes": {"pass": 191, "fail_early_volume": 86, "fail_F_window": 160, "fail_total_cap_nonpubmed_groupby": 17, "fail_total_cap": 2}} |

Per-concept final outcomes over the whole working list (456): `{'pass': 191, 'fail_early_volume': 86, 'fail_F_window': 160, 'fail_total_cap_nonpubmed_groupby': 17, 'fail_total_cap': 2}`.

**Final population: N = 191** (target 200; plan: acceptable 150-240, hard minimum 120).

- by establishment pool: `{'core_2006_2016': 99, 'w2': 78, 'w1': 14}`; by period: `{'2011-2016': 70, '2006-2010': 29, '2017-2018': 78, '2004-2005': 14}`
- by branch group: `{'F+H-N': 17, 'G': 11, 'E': 32, 'D': 62, 'C': 22, 'A+B': 47}`
- by final-rule basis: `{'verified_union': 13, 'pubmed_route_verified+nonpubmed_groupby_unverified': 159, 'pubmed_route_verified_only': 19}`
- retrieval_complete (non-PubMed works paged): 13 of 191
- **rule_parity** (final rule saw non-PubMed works, as in the main corpus): 172 of 191. The 19 concepts with `rule_parity = false` are widened concepts whose non-PubMed group_by count could not be bought after the shared key's budget was exhausted; use the `rule_parity = true` subset for strict confirmation.
- provenance classes: `{'NO_PRIOR': 64, 'PRIOR_IMPLICIT': 127}`; chemical_flag: 62; still_in_mesh_2026: 191

## Rules (identical to the main corpus where the plan requires)

- **Provenance filter** (Nentidis, Krithara, Tsoumakas & Paliouras 2021, arXiv:2101.08293): DROP `PRIOR_EXPLICIT` (HistoryNote/PublicMeSHNote parenthetical year earlier than establishment, e.g. `2010 (1998)`), `PROMOTED_TERM` (any preferred-concept term was a term of a different descriptor in the prior-year file), `RENAMED` (MeSH replace list names it as MH NEW, a deleted descriptor's heading is reused, or the HistoryNote says `was X yyyy-yyyy` / points at its own term). KEEP `PRIOR_IMPLICIT` (PreviousIndexing to broader headings, or PublicMeSHNote 'indexed under') and `NO_PRIOR`. `use BROADER-HEADING yyyy-yyyy` notes are ordinary previous indexing, not renames.
- **Surface forms**: preferred concept only, non-permuted, un-inverted single-comma forms (not when the head is numeric e.g. `46, XX ...`); excluded from matching (kept in the record): acronyms < 5 chars (LexicalTag ABB/ACR/ABX), forms < 4 chars, special characters, single words with wordfreq zipf >= 4.0.
- **Pre-screen (PubMed, free)**: `("form1"[tiab] OR "form1 with hyphens as spaces"[tiab] OR ...) AND 1995:2024[dp]`; drop total > 9,999 or < 15; exact yearly counts 1995-2018 by intersecting each descriptor's PMID set with per-year PMID sets of OR-chunks of descriptors (`(chunk) AND YYYY[dp]`, chunk totals < 9,000); a conservative PMID-date prune drops descriptors with > 45 PMIDs <= 14,699,652 (EDAT <= 2003-12-31, i.e. some year 1995-2004 >= 5 papers, F < 2005). Pass: F in 2005..2016, 15 <= count(F..F+2) <= 350, total <= 8,000.
- **Sample**: strata branch group x PubMed early-volume tercile x establishment period; seed 20260928; floor 8 per branch group; D-branch cap 35%. Because only 283 descriptors passed the pre-screen, the working list is the full census of passers in seeded random order (`selection_prob = 1`); widened passers are appended after rank 283 (seed 20260929).
- **Final rule** (main corpus): F = first year 2000..2024 with >= 5 papers and all earlier < 5; F in 2005..2016; 20 <= count(F..F+2) <= 300; total 2000-2024 <= 8,000. Counts: verified union works (`final_rule_basis = verified_union`) when the non-PubMed remainder was paged; otherwise verified PubMed-route works + exact OpenAlex group_by counts of non-PubMed works (`pubmed_route_verified+nonpubmed_groupby_unverified`); if even group_by counts could not be bought (key budget exhausted), PubMed-route only (`pubmed_route_verified_only`, flagged). Failing concepts are dropped whole.
- **Local verification** (every work): OpenAlex title + abstract reconstructed in memory from `abstract_inverted_index`, lower-cased, hyphen/dash/slash/comma = space, Greek letters spelled out, word boundaries, last word singular/plural-insensitive. The abstract is discarded. Works whose OpenAlex record has no abstract can only be verified on the title (the main corpus's plain OpenAlex search has the same blind spot); `yearly_counts_textmatch_plus_pubmed_unverifiable` additionally counts PubMed [tiab] hits without an OpenAlex abstract (not used for selection).

## Query templates

```
PubMed  : ("<form>"[tiab] OR ...) AND 1995:2024[dp]            (esearch, retmax 10000)
PubMed  : (<chunk of descriptor queries>) AND <YYYY>[dp]        (esearch, yearly PMID sets)
PubMed  : "<Preferred Term>"[MeSH Terms:noexp]                  (indexed PMID set) + AND <YYYY>[dp] chunks
OpenAlex: /works/pmid:<PMID>?select=<fields>                     (singleton, free)
OpenAlex: /works?filter=ids.pmid:<p1|...|p100>&per_page=100       (list, 1 credit per call)
OpenAlex: /works?filter=title_and_abstract.search:("f1" OR "f2" ...),has_pmid:false,publication_year:2000-2024&group_by=publication_year  (1 credit)
OpenAlex: same filter, OR-batched over several concepts, &per_page=200&cursor=*   (10 credits per page)
OpenAlex: title_and_abstract.search:(forms),publication_year:2000-2024  [main-corpus plain query, calibration]
```

select = `id,ids,doi,title,publication_year,publication_date,type,language,primary_topic,primary_location,referenced_works,authorships,keywords,concepts,cited_by_count,mesh,abstract_inverted_index,indexed_in`

## OpenAlex cost (read from X-RateLimit-Credits-Used on every call; ledger `logs/openalex_credit_ledger.jsonl`)

Key: free tier, 10,000 credits/day ($1/day). This artifact's ceiling: 20% = 2,000 credits; paid calls stop at 90% (1,800).

| call type | calls | credits |
|---|---|---|
| search | 76 | 760 |
| group_by | 423 | 423 |
| list | 601 | 601 |
| **total** | 1100 | **1784** (= $0.1784) |

Free calls (not in the ledger): all `/works/pmid:X` singletons and all NCBI E-utilities calls. Measured prices: singleton 0, list 1, group_by 1, search page 10 credits. The shared key was exhausted key-wide (by all concurrent artifacts) at ~13:00 UTC; afterwards only free singletons were possible. The key-wide 30 req/s rate limit (shared with sibling runs) held singletons to ~13-14 req/s, which is why 700 credits were spent on 1-credit batched `ids.pmid` lists (60,000 PMIDs) for the back of the rank order.

Non-PubMed remainder: paged for 26 concepts in rank order (12083 works in 8 OR-batches); stopped in rank order at concept ['D000068276']; 16 concepts skipped because their non-PubMed OpenAlex count alone exceeds the 8,000 cap. group_by non-PubMed counts exist for 413 of 456 working-list concepts.

## Route calibration (step 9; `route_calibration.json`)

Summary: `{"n_calibration_concepts": 10, "n_in_final_population": 5, "ratio_union_to_plain_median": 0.8598, "ratio_union_to_plain_min": 0.5422, "ratio_union_to_plain_max": 0.9123, "F_agreement": 8, "F_within_1y": 10, "artifact_openalex_credits_spent_total": 1784}`

| concept | in final | plain OpenAlex total | union verified total | ratio | F plain | F union | Jaccard (plain vs union verified) |
|---|---|---|---|---|---|---|---|
| O'nyong-nyong Virus | False | 107 | 92 | 0.8598 | 2006 | 2006 | 0.8598 |
| Extensively Drug-Resistant Tuberculosis | False | 4118 | 3295 | 0.8001 | 2006 | 2006 |  |
| Type V Secretion Systems | False | 96 | 83 | 0.8646 | 2007 | 2007 | 0.8646 |
| Serum Bactericidal Antibody Assay | False | 57 | 52 | 0.9123 | 2015 | 2015 | 0.9123 |
| Trauma and Stressor Related Disorders | True | 640 | 347 | 0.5422 | 2012 | 2013 |  |
| Reflex, Trigeminocardiac | True | 445 | 402 | 0.9034 | 2005 | 2005 |  |
| Eupenicillium | False | 383 | 328 | 0.8564 | 2001 | 2001 |  |
| Mammary Analogue Secretory Carcinoma | True | 309 | 255 | 0.8252 | 2011 | 2011 |  |
| Class I Phosphatidylinositol 3-Kinases | True | 210 | 177 | 0.8429 | 2007 | 2007 |  |
| Piezosurgery | True | 1020 | 904 | 0.8863 | 2004 | 2005 |  |

The plain query stems (e.g. `Texting` -> `text`) and matches any title/abstract occurrence; the union route uses PubMed's exact phrase index for PubMed records plus OpenAlex search for the rest, and then applies one strict local match. Downstream code that needs main-corpus comparability should use the rows with `verified_text_match = true`.

## Coverage QA (unique verified union works of the final population, per year)

| year | works | share with PMID | has abstract | has references | author ids | primary topic |
|---|---|---|---|---|---|---|
| 2000 | 43 | 0.9767 | 0.8605 | 0.6977 | 0.9767 | 1.0 |
| 2001 | 60 | 0.9333 | 0.9 | 0.8833 | 1.0 | 1.0 |
| 2002 | 62 | 0.9677 | 0.8226 | 0.8226 | 1.0 | 1.0 |
| 2003 | 83 | 0.9518 | 0.7831 | 0.8434 | 0.9759 | 1.0 |
| 2004 | 134 | 0.9478 | 0.8433 | 0.8433 | 0.9851 | 1.0 |
| 2005 | 278 | 0.9101 | 0.7986 | 0.8201 | 0.9784 | 0.9892 |
| 2006 | 464 | 0.9353 | 0.7522 | 0.8405 | 0.9828 | 0.9892 |
| 2007 | 821 | 0.8989 | 0.782 | 0.8173 | 0.9854 | 0.9878 |
| 2008 | 1154 | 0.9029 | 0.7851 | 0.8388 | 0.9887 | 0.9957 |
| 2009 | 1659 | 0.9397 | 0.7908 | 0.8704 | 0.9892 | 0.9934 |
| 2010 | 2153 | 0.9224 | 0.8035 | 0.8727 | 0.9861 | 0.9954 |
| 2011 | 2597 | 0.9395 | 0.8179 | 0.8883 | 0.9935 | 0.9946 |
| 2012 | 3133 | 0.9307 | 0.8327 | 0.8717 | 0.9895 | 0.9933 |
| 2013 | 3844 | 0.9285 | 0.8377 | 0.8972 | 0.9896 | 0.9943 |
| 2014 | 4380 | 0.9338 | 0.8315 | 0.8979 | 0.9913 | 0.9961 |
| 2015 | 4776 | 0.9326 | 0.8614 | 0.8953 | 0.9885 | 0.9977 |
| 2016 | 5064 | 0.9417 | 0.8547 | 0.8957 | 0.9913 | 0.9986 |
| 2017 | 5370 | 0.9391 | 0.867 | 0.9028 | 0.9912 | 0.9998 |
| 2018 | 5797 | 0.9396 | 0.8751 | 0.92 | 0.9926 | 0.9998 |
| 2019 | 6230 | 0.9392 | 0.8854 | 0.9207 | 0.9936 | 0.9995 |
| 2020 | 7377 | 0.9492 | 0.9027 | 0.9326 | 0.9925 | 0.9995 |
| 2021 | 7746 | 0.9524 | 0.9118 | 0.9459 | 0.9804 | 0.9996 |
| 2022 | 8229 | 0.9554 | 0.9232 | 0.9426 | 0.9784 | 0.999 |
| 2023 | 8758 | 0.8989 | 0.9245 | 0.9071 | 0.9933 | 0.996 |
| 2024 | 9619 | 0.9118 | 0.9087 | 0.9237 | 0.9871 | 0.9972 |

Rows: 122645 (unique works 117253); by route `{'pubmed_tiab': 113347, 'openalex_nonpubmed_search': 6026, 'mesh_indexed_only': 3272}`; verified 92220; match field `{'none_local': 30425, 'abstract': 51061, 'title': 18210, 'both': 22949}`; descriptor indexed (OpenAlex mesh) 44826; descriptor indexed (PubMed [MeSH:noexp]) 42078.

## Provenance-class spot check (60 records, seed 606; sample in `temp/spotcheck_sample.txt`)

30 random KEEP and 30 random DROP records (2006-2016 pool) were read by hand against their HistoryNote, PublicMeSHNote, PreviousIndexing and the prior-year match.
- KEEP/DROP decision errors under the stated rules: **0 / 60**.
- Sub-class label errors: 2 KEEP records labelled NO_PRIOR whose PublicMeSHNote says 'was indexed under ...' (should be PRIOR_IMPLICIT) -> rule added (PublicMeSHNote 'indexed under' => PRIOR_IMPLICIT; 142 labels changed, no selection change).
- Surface-form defect: `46, XX ...` was wrongly un-inverted -> fixed (numeric heads and number lists are not inversions; 6 descriptors' forms changed and were re-queried).
- Caveat: several KEEP records are well-known older concepts (e.g. Janus Kinases 2007) newly given a descriptor; as the plan intends, the text-novelty rule (F >= 2005), not the notes, removes them.

## Synonym pair set (`mesh_synonym_pairs.json`)

Positive pairs: 9477; negative pairs: 13620; by label|type: `{'0|non_preferred_concept_brd': 45, '0|non_preferred_concept_nrw': 2730, '0|non_preferred_concept_rel': 624, '0|sibling_descriptor': 10221, '1|acronym_expansion': 1506, '1|synonym': 7971}`. Built for all provenance-filtered new descriptors of the 2006-2016 pool (3,430 with matchable forms), max 40 positives per descriptor, 4 sibling negatives per descriptor. `in_heldout_population` marks pairs touching a final-population descriptor (exclude them from training); `in_working_list` is the stricter flag (any descriptor examined for this population).

## Usefulness sanity check (`sanity_check.json`, descriptive only)

Over 191 concepts (verified works): median later-6-year / early-3-year volume ratio 3.94; 86% grow; median distinct OpenAlex subfields 4 in F..F+2 vs 12 in F+3..F+8 (92% expand their disciplinary reach); median fields touched 2000-2024 8. Spearman(early subfield reach, later volume) = 0.17 (p=0.0207); Spearman(early volume, later volume) = 0.70. The population therefore has variance in growth and in cross-disciplinary diffusion, as RQ1/RQ2 require.

## Known limitations

- Biomedical population only (MeSH); cross-field generality rests on the other populations.
- Non-PubMed works were paged only for the first concepts in rank order (credit ceiling, then key exhaustion); for the rest the final rule uses exact but locally unverified OpenAlex group_by counts, and those works are absent from the works parts (`retrieval_complete = false`, `retrieval_gap = nonpubmed_missing`). Network analyses on these concepts see only their PubMed-indexed neighbourhood.
- PubMed [tiab] also searches author keywords; such hits without the phrase in the OpenAlex title/abstract are kept with `verified_text_match = false`.
- MeSH-indexed-only works (indexed with the descriptor but not text-matched) are not fetched; their PMIDs are in `output.mesh_indexed_only_pmids`, and `yearly_counts_mesh_indexed` (from DateEstablished on) covers them.
- After 2022 MEDLINE indexing is automated: rows carry `indexing_regime`.
- Live APIs: re-running gives slightly different counts.
