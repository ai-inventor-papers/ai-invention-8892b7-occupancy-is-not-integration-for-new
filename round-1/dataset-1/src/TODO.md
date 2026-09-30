# TODO (copied verbatim from task)
- [x] TODO 1. Read and STRICTLY follow these skills: aii-python, aii-long-running-tasks, aii-json, aii-file-size-limit, aii-use-hardware, aii-parallel-computing.
- [x] TODO 2. Read skill files for your data sources (see <available_data_sources>) and domain handbook if applicable (see <available_domain_handbooks>). Based on plan and context, decide which source(s) to use. Include everything specified in the artifact plan, but you may also collect additional relevant data beyond what's listed. Run 40 diverse searches across chosen source(s) — BROAD, GENERAL terms, not very specific. Parallelize where supported.
- [x] TODO 3. Identify the 20 most promising datasets. IMPORTANT: Only consider datasets under 300MB. Preview/inspect sample rows for each candidate. Parallelize previews.
- [x] TODO 4. Research each candidate BEFORE choosing which to download. For each, search the web (aii-web-tools skill): dataset name, papers citing it, original source/task, popularity. Red flags: no search results, no papers, anonymized features (F1, F2...), <100 downloads, no documentation. Green flags: papers using it, clear documentation, meaningful features, established benchmark. Also consider: will features/structure allow meaningful evaluation of the planned method?
- [x] TODO 5. Decide which to KEEP vs DISCARD. Look for: clear structure, relevant fields, quality examples matching requirements, confirmed provenance. Determine which 10 datasets have the most suitable data. Download and save to `temp/datasets/`. Parallelize downloads.

## Notes on how each TODO was satisfied
- TODO 2: 40 HF Hub searches (temp/hf_search_results.txt); sources chosen = OpenAlex API + S3 snapshot (plan-mandated), NLM MeSH, arXiv metadata (HF), Semantic Scholar bulk index; OWID not relevant.
- TODO 3: 20 HF candidates inspected via datasets-server (temp/hf_candidates_inspection.json; the skill preview script lacked the `datasets` module).
- TODO 4: provenance checked by web search (see README "Data sources and provenance").
- TODO 5: kept sources listed in README; small labelled grounding datasets downloaded to temp/datasets/.

# TODO (round 2, copied verbatim)
- [x] TODO 1. For the top 10 datasets, create data.py (uv inline script) that: loads from temp/datasets/, standardizes to exp_sel_data_out.json schema (aii-json skill), extracts all examples per dataset, handles domain requirements, saves to full_data_out.json.
- [x] TODO 2. Run 'uv run data.py' and fix errors. Validate full_data_out.json against exp_sel_data_out.json schema (aii-json skill) — fix errors. Generate preview, mini, full versions with aii-json skill's format script.
- [x] TODO 3. Read preview to inspect examples. Choose THE BEST 5 DATASETS based on domain requirements and artifact objective. Be very attentive to meticulously and exhaustively fix any errors in your code.
Notes: full_data_out.json exceeded 90 MB so it is split into full_data_out/full_data_out_{1,2}.json (aii-file-size-limit). Best 5 = D1-D5.

# TODO (round 3, copied verbatim)
- [x] TODO 1. Update data.py to only include the chosen 5 datasets and generate full_data_out.json. (split into full_data_out/ parts; root mini_data_out.json / preview_data_out.json)
- [x] TODO 2. Verify full_data_out.json, preview_data_out.json, and mini_data_out.json exist in your workspace (see <workspace>) and contain correct data.
- [x] TODO 3. Apply aii-file-size-limit skill's file size check procedure (100MB limit) to full_data_out.json.
- [x] TODO 4. Ensure a `pyproject.toml` exists in your workspace with ALL dependencies pinned to the exact versions installed in your .venv.
- [x] TODO 5. Write `reproducibility.md` in your workspace with COMPLETE step-by-step instructions.
