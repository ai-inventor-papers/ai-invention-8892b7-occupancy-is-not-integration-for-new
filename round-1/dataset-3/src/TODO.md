# TODO (copied verbatim from task)
- [x] TODO 1. Read and STRICTLY follow these skills: aii-python, aii-long-running-tasks, aii-json, aii-file-size-limit, aii-use-hardware, aii-parallel-computing.
- [x] TODO 2. Read skill files for your data sources (see <available_data_sources>) and domain handbook if applicable (see <available_domain_handbooks>). Based on plan and context, decide which source(s) to use. Include everything specified in the artifact plan, but you may also collect additional relevant data beyond what's listed. Run 16 diverse searches across chosen source(s) — BROAD, GENERAL terms, not very specific. Parallelize where supported.
- [x] TODO 3. Identify the 8 most promising datasets. IMPORTANT: Only consider datasets under 300MB. Preview/inspect sample rows for each candidate. Parallelize previews.
- [x] TODO 4. Research each candidate BEFORE choosing which to download. For each, search the web (aii-web-tools skill): dataset name, papers citing it, original source/task, popularity. Red flags: no search results, no papers, anonymized features (F1, F2...), <100 downloads, no documentation. Green flags: papers using it, clear documentation, meaningful features, established benchmark. Also consider: will features/structure allow meaningful evaluation of the planned method?
- [x] TODO 5. Decide which to KEEP vs DISCARD. Look for: clear structure, relevant fields, quality examples matching requirements, confirmed provenance. Determine which 4 datasets have the most suitable data. Download and save to `temp/datasets/`. Parallelize downloads.

## Notes
- TODO 2-5: 16 HuggingFace searches (`temp/hf_search_results.txt`), 8 candidates previewed (`temp/previews/`), verdicts in
  `temp/datasets/SOURCE_SELECTION.md`. No HF dataset carries MeSH establishment/provenance data; the plan's primary sources
  (NLM MeSH XML/ASCII, PubMed E-utilities, OpenAlex API) were kept. Raw MeSH files are in `raw/` (not `temp/datasets/`,
  to keep bulky binaries in one manifest entry).

# TODO (stage 2, copied from task; done)
- [x] TODO 1. For the top 4 datasets, create data.py (uv inline script) that: loads from temp/datasets/, standardizes to exp_sel_data_out.json schema (aii-json skill), extracts all examples per dataset, handles domain requirements, saves to full_data_out.json.
- [x] TODO 2. Run 'uv run data.py' and fix errors. Validate full_data_out.json against exp_sel_data_out.json schema (aii-json skill) — fix errors. Generate preview, mini, full versions with aii-json skill's format script.
- [x] TODO 3. Read preview to inspect examples. Choose THE BEST 2 DATASETS based on domain requirements and artifact objective. Be very attentive to meticulously and exhaustively fix any errors in your code.
  Notes: 4 candidates built (`uv run data.py --candidates`: concepts 191, pairs, pre-screen table 5,012, works 122,645; schema PASSED).
  Selected: heldout_mesh_concepts + mesh_synonym_pairs. Fix found in review: 976 duplicate negative pairs (inverted vs
  natural-order spellings) removed at source (s01) -> 23,097 pairs, 0 duplicates, 0 label conflicts, 0 leakage.

# TODO (stage 3, copied from task; done)
- [x] TODO 1. Update data.py to only include the chosen 2 datasets and generate full_data_out.json. Re-run, validate (aii-json), format with --input full_data_out.json and rename to full/mini/preview_data_out.json.
- [x] TODO 2. Verify full_data_out.json, preview_data_out.json, and mini_data_out.json exist and contain correct data.
- [x] TODO 3. Apply aii-file-size-limit check (100MB) to full_data_out.json -> 18 MB, no split needed.
- [x] TODO 4. pyproject.toml with all dependencies pinned to the .venv versions (uv pip freeze; the uv venv has no pip binary).
- [x] TODO 5. reproducibility.md rewritten: clone/cd, system + Python 3.12.14 + pinned libs, downloads + env var names, exact commands actually run with seeds/runtimes/hardware, expected outputs and numbers.
  Also: OpenAlex key moved out of scripts/oa.py into env var OPENALEX_API_KEY; path-leaking preview tracebacks removed.
