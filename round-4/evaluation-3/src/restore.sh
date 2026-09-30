#!/usr/bin/env bash
# Restore everything .aii/manifest.yaml marks as `delete`: the three uv venvs and the byte copies of the exp_5/exp_6
# workspaces (only files that are missing are copied back; one-look outputs already in deps_run/ are never overwritten).
set -euo pipefail
WS="$(cd "$(dirname "$0")" && pwd)"
LOOP="${AII_LOOP_ROOT:-$(cd "$WS/../../.." && pwd)}"
cd "$WS"
for n in 5 6; do
  src="$LOOP/iter_3/gen_art/gen_art_experiment_$n"
  mkdir -p "deps_run/exp$n"
  # --skip-old-files: never overwrite files already present (keeps results_heldout/ and confirmation.json)
  tar -C "$src" --exclude=.venv --exclude=__pycache__ --exclude=.pytest_cache --exclude='./.aii*' \
      --exclude=./.repl_agent.ptylog --exclude=./.terminal_claude_agent_struct_out.json -cf - . \
    | tar -C "deps_run/exp$n" --skip-old-files -xpf -
  if [ ! -x "deps_run/exp$n/.venv/bin/python" ]; then
    (cd "deps_run/exp$n" && uv venv .venv --python=3.12 -q && uv pip install -q --python=.venv/bin/python -r pyproject.toml)
  fi
done
if [ ! -x .venv/bin/python ]; then
  uv venv .venv --python=3.12 -q && uv pip install -q --python=.venv/bin/python -r pyproject.toml
fi
echo "restored"
