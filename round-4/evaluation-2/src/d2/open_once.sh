#!/usr/bin/env bash
# Step 3: open the sealed D2 held-out fold EXACTLY ONCE with the frozen, hash-checked confirm_heldout.py.
# Refuses unless ../results/g_spec.json matches ../results/g_spec.sha256, and refuses if an opening was ever started.
set -euo pipefail
cd "$(dirname "$0")"
export AII_DEPS_ROOT="${AII_DEPS_ROOT:-$(cd ../../../.. && pwd)}"
LOCK=results/HELDOUT_OPENED.lock
STARTED=results/HELDOUT_OPENING_STARTED
[ -e "$LOCK" ] && { echo "REFUSED: held-out fold already opened ($LOCK)"; exit 3; }
[ -e "$STARTED" ] && { echo "REFUSED: an opening was already started ($STARTED); never rerun"; exit 3; }
[ -e results/heldout_confirmation.json ] && { echo "REFUSED: results/heldout_confirmation.json exists"; exit 3; }
[ -f ../results/g_spec.sha256 ] || { echo "REFUSED: g_spec.sha256 missing (freeze first)"; exit 3; }
want=$(cut -d' ' -f1 ../results/g_spec.sha256)
got=$(sha256sum ../results/g_spec.json | cut -d' ' -f1)
[ "$want" = "$got" ] || { echo "REFUSED: g_spec.json sha256 $got != frozen $want"; exit 3; }
echo "started_utc=$(date -u +%FT%TZ) g_spec_sha256=$got" > "$STARTED"
.venv/bin/python confirm_heldout.py --open-heldout 2>&1 | tee ../logs/open_heldout.log
[ -s results/heldout_confirmation.json ] || { echo "opening produced no result (NOT CONFIRMED; dead for the headline)"; exit 4; }
h=$(sha256sum results/heldout_confirmation.json | cut -d' ' -f1)
printf 'opened_utc=%s\nheldout_confirmation_sha256=%s\ng_spec_sha256=%s\nheldout_spec_sha256=%s\n' \
  "$(date -u +%FT%TZ)" "$h" "$got" "$(cut -d' ' -f1 heldout_spec.sha256)" > "$LOCK"
cat "$LOCK"
