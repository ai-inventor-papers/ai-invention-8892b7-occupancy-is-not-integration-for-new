#!/usr/bin/env bash
# Restore everything marked `delete` in .aii/manifest.yaml.
set -euo pipefail
cd "$(dirname "$0")"
if [ ! -x .venv/bin/python ]; then
  uv venv .venv --python=3.12
  uv pip install --python .venv/bin/python aiohttp loguru pandas numpy scikit-learn rapidfuzz "spacy>=3.7" datasets openai tenacity pyyaml orjson requests pyarrow huggingface_hub
  .venv/bin/python -m spacy download en_core_web_sm
fi
[ -d cache/openalex ] || cat cache/openalex_cache.tar.gz.part_* | tar -xzf - -C cache
mkdir -p raw/mesh temp/datasets/openalex_snapshot
[ -f raw/mesh/desc2026.gz ] || curl -sL -o raw/mesh/desc2026.gz https://nlmpubs.nlm.nih.gov/projects/mesh/MESH_FILES/xmlmesh/desc2026.gz
.venv/bin/python scripts/s0_download_hf.py
for e in keywords concepts; do
  curl -s "https://openalex.s3.amazonaws.com/data/jsonl/$e/manifest.json" -o "temp/datasets/openalex_snapshot/${e}_manifest.json"
done
.venv/bin/python scripts/s3_fetch_snapshot_vocab.py
.venv/bin/python scripts/s3_parse_mesh.py
# intermediates (free: every paid response is in the cache)
export OPENALEX_API_KEY="${OPENALEX_API_KEY:-cache-only}"
ls raw/corpus_works/corpus_works_part_*.jsonl >/dev/null 2>&1 || .venv/bin/python scripts/s1_fetch_corpus.py
[ -f raw/candidates.pkl.gz ] || .venv/bin/python scripts/s2_candidates.py
[ -f raw/key_stats.pkl.gz ] || .venv/bin/python scripts/s5_label.py select
echo "restore complete"
