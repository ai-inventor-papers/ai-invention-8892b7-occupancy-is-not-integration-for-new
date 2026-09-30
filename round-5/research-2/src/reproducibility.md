# Reproducibility: how this dossier was actually produced

- **Date:** 2026-09-29, UTC. One session of about 50 minutes of tool time.
- **Cost:** $0 in LLM/API spend.
- **Tools:**
  - the `aii-web-tools` skill scripts: `aii_fast_web_search.py` (search), `aii_fast_web_fetch.py fetch` and `grep`;
  - the built-in `WebSearch`/`WebFetch` tools;
  - direct keyless JSON APIs via `curl`/`urllib`: Semantic Scholar Graph API, Crossref REST, Unpaywall, Europe PMC.
- **Keys:** no API keys were used or needed. The skill scripts call the pipeline's ability server, which may itself use `SERPER_API_KEY` as a fallback, by name only. The OpenAlex key in the run request was **not** used: the plan forbids OpenAlex list queries because the run's credits are exhausted. Note that the skill's `--mode scholarly` search internally queries OpenAlex/Crossref through the ability server.
- **Helper scripts:** all in `tools/`.
  - `getdoc.sh <name> <url>` pages the fetch script in 50k-char chunks into `cache/<name>.md`.
  - `g.py <name> <regex>` greps a cached doc locally.
  - `s2title.py` does S2 title → abstract lookup.
  - `s2cites.py <label> <id> [citations|references]` does snowballing.
  - `crossref.py` validates DOIs.
  - `build_output.py` assembles the structured output and sources.

## Order of work

### 0. Prior work (iter-1 dossier)

The iter-1 dossier was read at `../../../round-1/research-1/src/`: `research_report.md`, `research_out.json` (81 sources) and `research_verification.json` (28 passages marked valid). Passages marked valid there were reused, not re-fetched: Kuhn [11], Rafols [17], De Domenico [74], Fontaine [75].

### 1. Nearest neighbours

**Cheng et al. 2023.** Routes tried, in order:

1. Stanford GSB Preserve page. Its attachment zip holds only a thumbnail PDF.
2. Semantic Scholar: `openAccessPdf` is empty.
3. Unpaywall: closed.
4. SAGE PDF: nothing returned.
5. `https://journals.sagepub.com/doi/full/10.1177/00031224231166955` via `aii_fast_web_fetch.py grep`: **works**, 231,050 chars.
   - Patterns grepped: `tradition`, `embeddedness`, `core concept`, `To measure an idea.s ideational embeddedness.{0,1500}`, `As suggested by the curve in Figure 3.{0,1400}`, `term-year|idea-year|unit of analysis`, `Hypothesis 6a…`, `Interdisciplinary\|…`.
   - Outputs are in `cache/cache_cheng{1,2,3}.txt`.
   - A full `fetch` of the same URL later returned nothing, possibly throttled, so remote `grep` is the reliable route.
6. Wayback `http://web.archive.org/web/2024/https://journals.sagepub.com/doi/full/…` also works.

**Other open full texts fetched into `cache/`:**

- Uzzi 2013: Kellogg PDF.
- Foster 2015: arXiv 1302.6906.
- Hofstra 2020: arXiv 1909.02063.
- Jia 2017: arXiv 1709.03319.
- Guevara 2016: arXiv 1602.08409.
- Hidalgo et al. 2018: Utrecht repository PDF. The plan's arXiv 1807.03148 was fetched first and is an unrelated video-segmentation paper.
- Rogers compatibility: Sahin 2006, ERIC ED501453.
- Cohen & Levinthal 1990: course-site PDF.
- Shi & Evans 2023: PMC10039062.
- Kuhn 2014: arXiv.
- Rotolo 2015: arXiv 1503.00673.
- Salatino 2017: PeerJ.
- Chen 2009: arXiv 0904.1439, found via the S2 externalIds.
- Burt 2004: Stony Brook course PDF, found via the S2 openAccessPdf.
- Stirling 2007: PMC2373389. The royalsocietypublishing.org page returned only citing-article lists.
- Wang, Veugelers & Stephan 2017: NBER w22180.
- Lin, Evans & Wu 2022: arXiv 2103.03398.
- Deichmann 2020: VU repository PDF.
- Candelon 2024: UCLouvain DIAL PDF.
- Cao 2020: arXiv 2010.06657.

**Failed:** Callon 1983 (HAL behind an Anubis anti-bot wall); Leydesdorff & Hellsten and Star & Griesemer (no open copy). These three are left at METADATA-ONLY.

### 2. Novelty search

- **14 queries (Q01-Q14, listed in `search_log/queries.txt`)** were run in both `--mode general` and `--mode scholarly`, with `--max-results 20`. That is 28 files in `search_log/`. All 571 titles are in `search_log/titles_all.txt`.
- **4 extra WebSearch queries:**
  - "borrowed concept adapted to host discipline vocabulary predicts adoption co-occurrence keywords scientometrics";
  - "semantic context of concept when it crosses disciplines predicts its diffusion into the new field word embeddings";
  - "\"Ideas with impact\" connectivity shapes idea diffusion Research Policy";
  - "\"Off the beaten path\" what drives scientists' entry into new fields".
- **Abstract screening:** `tools/s2title.py` (S2 `/paper/search/match`) was run on 12 candidate titles.
- **Forward snowballing:** S2 `/paper/{id}/citations`. Results are in `snowball/*_citations.json`:
  - Cheng: 33;
  - Hofstra: 856;
  - Uzzi: 937, equal to S2's citationCount;
  - Guevara: 123 via `ARXIV:1602.08409`, because the DOI record returned 0;
  - Deichmann: 31.
- **Regex filter:** `(discipl|field|domain|communit).{0,80}(adopt|uptake|diffus|transfer|borrow|migrat|spread)|` plus its reverse, year ≥ 2016. It gave 41 hits, printed and screened by abstract.
- **Backward chasing:** S2 returns null references for Cheng (publisher-elided). The Crossref `reference` array was used instead: 167 references, 125 DOIs resolved to titles (`snowball/cheng_ref_titles.txt`).
- **Grading** followed the plan's rule (ANTICIPATES / PARTLY / DIFFERENT; section 4 of the report).

### 3. ANS venue

- **Collection page:**
  - `https://link.springer.com/collections/fgcaicgjah`: the fetch script got a JS wall, and WebFetch got a 303 to `idp.springer.com`;
  - Wayback `web/2026/`: empty;
  - collections index: JS wall.
  - Scope, dates and editor therefore come from WebSearch snippets only (queries: "\"Networks for everyday life\" Applied Network Science collection"; the same with "guest editors \"innovation, collaboration, and knowledge exchange networks\""; and "site:link.springer.com \"Networks for everyday life\" …").
- **ANS paper discovery:** 9 Crossref queries on `https://api.crossref.org/journals/2364-8228/works?query=<terms>&rows=25`, logged in `ans/crossref_ans_queries.txt`. Abstracts came from an S2 `/paper/batch` call (`ans/ans_s2_batch.json`).
- **Structure norms:**
  - PMC9673898, PMC8242290 and PMC12102006 were fetched. Author-year vs numbered citation patterns were counted by regex.
  - A later attempt to read back-matter headings failed: PMC returned a 133-char stub, and Europe PMC `fullTextXML` returned 503.
  - The official guidelines came from Wayback snapshot 20241101142310 of `appliednetsci.springeropen.com/submission-guidelines/preparing-your-manuscript/research`, via the fetch script. The WebFetch tool cannot fetch web.archive.org.

### 4. Methods references

- **DOI validation:** 65 DOIs checked with `tools/crossref.py` (with polite `mailto`, sequential, backoff), giving `snowball/doi_validation.txt`. A first parallel burst at `-P 10` was rate-limited and was redone.
- **Abstracts:** an S2 `/paper/batch` call (`snowball/methods_s2_batch.json`).
- **Open copies fetched:** Cameron & Miller (UC Davis PDF), Kline & Santos (NBER w16127), Gelbach (SSRN abstract page), Gelman & Loken (Columbia PDF), Weidner & Zylkin (arXiv abs 1909.01327), Didegah & Thelwall (IDEAS/RePEc abstract; the first ScienceDirect PII guessed was a different paper), Dorta-González & Gómez-Déniz (arXiv 2505.15384), Rousseau & Yang (ScienceDirect preview).
- **Not usable:** PubMed pages for Higgins & Thompson and DerSimonian & Laird returned no abstract, so both stay METADATA-ONLY.

### 5. Passage check

Every `supporting_passage` in the output was string-matched after whitespace and case normalisation. The match was against the locally cached source text (`cache/`, `snowball/`, `ans/`) or against the iter-1 valid passages. 2 misses were found, re-fetched and confirmed: Losee on arXiv abs, Tripodi on nature.com.

## How to retrace

1. Run the queries in `search_log/queries.txt` in both modes, plus the 4 extra queries above.
2. Re-run `tools/s2cites.py` for the 5 seeds.
3. Apply the regex filter above and grade the hits against the construct definition in report section 4a.
4. Re-grep Cheng with `aii_fast_web_fetch.py grep --url https://journals.sagepub.com/doi/full/10.1177/00031224231166955 --pattern "To measure an idea.s ideational embeddedness.{0,1500}"` and `"We construct our dependent variable"`.

Search engines drift over time, so snippet-level venue facts may change. Crossref and S2 results are stable except for citation counts.

## Verification round 1 (same day)

The pipeline's passage checker could not find three passages:

- [64] and [65] came from Semantic Scholar abstracts, but their URLs point to PMC pages, which now serve a stub to fetchers. The exact passages were removed; the structure claims stay, backed by the session's earlier PMC fetch (`cache/pmc_*.md`).
- [89]: the quote was shortened to drop a curly apostrophe.
- [31]: repointed to the arXiv abstract page, where the passage was re-confirmed.

The answer now cites all 93 sources explicitly. Ranges such as [29-32] were expanded, because the checker does not expand them.
- Round 2: removed the [16] Stirling passage, because PMC2373389 now serves a stub to the checker. The claim stays, based on the session's earlier full-text read (`cache/stirling.md`).
- Round 2: pre-emptively moved [10] Shi & Evans from PMC to nature.com (open access), where both passages were re-confirmed.
