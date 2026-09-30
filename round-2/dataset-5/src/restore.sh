#!/usr/bin/env bash
# Restore the files that .aii/manifest.yaml marks `delete` (all free). Run from this folder.
set -euo pipefail
cd "$(dirname "$0")"
uv venv .venv --python=3.12
uv pip install --python=.venv/bin/python -r pyproject.toml
(cd hyd && ../.venv/bin/python download_snapshot.py sources)
mkdir -p scimago_raw
for f in README.md data_dictionary.csv raw_file_manifest.csv LICENSE-DATA.txt sjr_category_panel.parquet; do
  curl -sSL -o "scimago_raw/$f" "https://zenodo.org/api/records/22954453/files/$f/content"
done
curl -sSL -o scimago_raw/asjc-codes_dhimmel.tsv https://raw.githubusercontent.com/dhimmel/scopus/main/data/asjc-codes.tsv
curl -sSL -o scimago_raw/scimago_lookup_zenodo4767023.csv "https://zenodo.org/api/records/4767023/files/scimago_lookup.csv/content"
.venv/bin/python p3_venue_habitat.py scimago
# hyd/raw_cache/ is NOT restored here: rebuilding it re-runs credit-priced OpenAlex calls (it is kept, see README "Restoring removed files").
