#!/bin/bash
# usage: tools/getdoc.sh <name> <url>  -> cache/<name>.md ; pages through aii-web-tools fetch in 50k-char chunks
SKILL_DIR=/ai-inventor/.claude/skills/aii-web-tools
PY="$SKILL_DIR/../.ability_client_venv/bin/python"
OUT="$(dirname "$0")/../cache/$1.md"; : > "$OUT"
off=0
while [ $off -lt 600000 ]; do
  chunk=$(timeout 240 $PY $SKILL_DIR/scripts/aii_fast_web_fetch.py fetch --url "$2" --max-chars 50000 --char-offset $off 2>/dev/null)
  echo "$chunk" >> "$OUT"
  echo "$chunk" | head -5 | grep -q "truncated" || break
  off=$((off+50000))
done
echo "$1 $(wc -c < "$OUT") bytes <- $2"
