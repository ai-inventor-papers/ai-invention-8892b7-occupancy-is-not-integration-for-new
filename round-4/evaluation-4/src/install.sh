#!/usr/bin/env bash
# Rebuild the environment and the regenerable bulk of this workspace.
set -euo pipefail
cd "$(dirname "$0")"
LOOP="${AII_LOOP_ROOT:-$(cd ../../.. && pwd)}"
# 1. copy of the frozen RQ2 experiment (art_QKsLguxnGFQT); keeps an existing heldout_run/ untouched
mkdir -p exp8_frozen
(cd "$LOOP/round-3/experiment-8/src" && tar --exclude=.venv --exclude=__pycache__ --exclude=./heldout_sim --exclude=./mini_run --exclude=./heldout_run -cf - .) | tar -xf - -C exp8_frozen
# 2. environment (pinned by exp8_frozen/pyproject.toml) + the two extra evaluation packages
(cd exp8_frozen && uv venv .venv --python 3.12 && uv pip install --python .venv/bin/python -r pyproject.toml && uv pip install --python .venv/bin/python pyfixest==0.60.0 lifelines==0.30.3)
