# Reproducing this artifact (Ubuntu, Python 3.12, uv)

Every paid API response is archived, so an exact rebuild costs **nothing**:
- OpenAlex: `cache/openalex_cache.tar.gz.part_*`, a 2-part split archive kept on the run volume.
- OpenRouter LLM: `cache/llm/`.
- Wikidata: `cache/wikidata/`.

The only nondeterministic element is OpenAlex data drift if the cache is missing (see step 6).

1. **Environment**
   ```bash
   uv venv .venv --python=3.12
   uv pip install --python .venv/bin/python aiohttp loguru pandas numpy scikit-learn rapidfuzz "spacy>=3.7" \
       datasets openai tenacity pyyaml orjson requests pyarrow huggingface_hub
   .venv/bin/python -m spacy download en_core_web_sm      # spaCy 3.8 / en_core_web_sm 3.8
   cat cache/openalex_cache.tar.gz.part_* | tar -xzf - -C cache           # restores cache/openalex/ (1,800 responses)
   ```
   Or run `./restore.sh`, which also does steps 2-3 and rebuilds the `raw/` intermediates.
2. **External human-labelled data (free)**: `.venv/bin/python scripts/s0_download_hf.py`, then
   `.venv/bin/python scripts/s0_convert_anchors.py`. This writes `raw/anchor_*.jsonl` and `labelling/sh_eval.json`.
3. **Vocabularies (free)**:
   - Fetch the snapshot manifests:
     `curl -s https://openalex.s3.amazonaws.com/data/jsonl/keywords/manifest.json -o temp/datasets/openalex_snapshot/keywords_manifest.json`,
     and the same for `concepts`.
   - Run `scripts/s3_fetch_snapshot_vocab.py`. The snapshot is dated 2026-09-23.
   - Download MeSH: `curl -L -o raw/mesh/desc2026.gz https://nlmpubs.nlm.nih.gov/projects/mesh/MESH_FILES/xmlmesh/desc2026.gz`.
   - Run `scripts/s3_parse_mesh.py`.
4. **Corpus**: set `OPENALEX_API_KEY` (any value works when the cache is present), then run `scripts/s1_fetch_corpus.py` and `scripts/s1b_coverage.py`.
   - Strata: 26 fields × years, `sample=150`.
   - Seed = `(field*10000+year)*(1 if main else 7) % 1000003`.
5. **Candidates**: `scripts/s2_candidates.py`, about 10 min on 4 cores. It is deterministic.
6. **Labelling**: set `OPENROUTER_BASE_URL` and `OPENROUTER_API_KEY`, then run
   `scripts/s5_label.py select`, `label`, `split`, `adjudicate`, `adjudicate_extra`, `anchor`, `report`,
   followed by `scripts/s5b_pairs.py` and `scripts/s5c_human_sheet.py`.
   - Seeds: 20260928 (selection and split), 20260929 (S8 order), 20260930 (pairs).
   - Models: `google/gemini-2.5-flash-lite` (A), `openai/gpt-4.1-nano` (B), `anthropic/claude-haiku-4.5` (adjudicator). All run at temperature 0 on 2026-09-28.
   - With `cache/llm/` present, every call is a cache hit. Without it, fresh LLM outputs may differ slightly, even at temperature 0.
7. **Pool and works**: `scripts/s7_counts.py --max-calls 1000`, then `scripts/s8_works.py --budget-credits 80`, then `scripts/s9_summary.py`.
   The counts depend on the OpenAlex state on 2026-09-28. Without the cache, a rerun returns current counts and may change eligibility.
8. **Package**: `.venv/bin/python data.py && .venv/bin/python scripts/split_output.py`. Then validate each part:
   ```bash
   /ai-inventor/.claude/skills/.ability_client_venv/bin/python \
     /ai-inventor/.claude/skills/aii-json/scripts/aii_json_validate_schema.py --format exp_sel_data_out --file "$PWD/full_data_out/full_data_out_1.json"
   ```
   The expected output is 7 parts containing 93,600 + 4,599 + 502 + 23,520 + 15,723 + 1,000 + 363 examples.

Spend of the original run: OpenAlex 1,847 credits ($0.185) and OpenRouter $0.674. Both are itemised in `logs/openalex_spend.csv` and `logs/llm_spend.jsonl`.
