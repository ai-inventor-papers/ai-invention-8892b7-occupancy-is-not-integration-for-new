#!/usr/bin/env python3
"""Step 0a: sha256 of every vendored file vs its source on the run volume -> results/vendor_hashes.json."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

WS = Path(__file__).resolve().parents[1]
LOOP = WS.parents[2]
SRC = {"d2/src": LOOP / "iter_4/gen_art/gen_art_evaluation_2/d2/src",
       "g": LOOP / "iter_4/gen_art/gen_art_evaluation_2/g",
       "mesh/src": LOOP / "iter_4/gen_art/gen_art_experiment_9/src",
       "mesh/vendor": LOOP / "iter_4/gen_art/gen_art_experiment_9/vendor",
       "inputs": None, "mesh/results": LOOP / "iter_4/gen_art/gen_art_experiment_9/results"}
EXP7 = LOOP / "iter_3/gen_art/gen_art_experiment_7/src"


def h(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


out, ok = {}, True
for d, src in SRC.items():
    for f in sorted((WS / d).glob("*")):
        if not f.is_file():
            continue
        rec = {"sha256": h(f)}
        if src is not None and (src / f.name).exists():
            rec["source"] = str((src / f.name).relative_to(LOOP.parent))
            rec["identical_to_source"] = rec["sha256"] == h(src / f.name)
            ok &= rec["identical_to_source"]
        if d == "d2/src" and (EXP7 / f.name).exists():
            rec["identical_to_exp7_art_2Cd2JJypeGuA"] = rec["sha256"] == h(EXP7 / f.name)
        out[f"{d}/{f.name}"] = rec
e2 = LOOP / "iter_4/gen_art/gen_art_evaluation_2"
for f in sorted((WS / "inputs").glob("*")):
    cand = [p for p in (e2 / "results" / f.name, e2 / "d2" / "results" / f.name) if p.exists()]
    out[f"inputs/{f.name}"] = {"sha256": h(f), "source": str(cand[0].relative_to(LOOP.parent)) if cand else None,
                               "identical_to_source": bool(cand) and h(f) == h(cand[0])}
    ok &= out[f"inputs/{f.name}"]["identical_to_source"]
(WS / "results" / "vendor_hashes.json").write_text(json.dumps({"all_identical": ok, "files": out}, indent=1))
print("all identical:", ok, len(out))
print({k: v for k, v in out.items() if v.get("identical_to_exp7_art_2Cd2JJypeGuA") is False})
