#!/usr/bin/env python3
"""Split full_data_out.json into full_data_out/full_data_out_<i>.json parts (<= LIMIT bytes each, schema-valid
exp_sel_data_out files), and write a combined mini (3 rows/dataset) and preview (3 rows/dataset, strings <= 200 chars).
Readers: for f in sorted(glob('full_data_out/full_data_out_*.json')): merge f['datasets'] by 'dataset' name."""
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
LIMIT = int(sys.argv[1]) if len(sys.argv) > 1 else 45_000_000
src = ROOT / "full_data_out.json"
d = json.loads(src.read_text())
def trunc(x):
    if isinstance(x, str): return x[:200]
    if isinstance(x, list): return [trunc(i) for i in x[:5]]
    if isinstance(x, dict): return {k: trunc(v) for k, v in x.items()}
    return x
mini = {"metadata": d.get("metadata", {}), "datasets": [{"dataset": g["dataset"], "examples": g["examples"][:3]} for g in d["datasets"]]}
(ROOT / "mini_data_out.json").write_text(json.dumps(mini, ensure_ascii=False, indent=1))
(ROOT / "preview_data_out.json").write_text(json.dumps(trunc(mini), ensure_ascii=False, indent=1))
out = ROOT / "full_data_out"; out.mkdir(exist_ok=True)
for f in out.glob("full_data_out_*.json"): f.unlink()
parts, cur, cur_size = [], {}, 0
order = []
for g in d["datasets"]:
    for e in g["examples"]:
        sz = len(json.dumps(e, ensure_ascii=False).encode()) + 2
        if cur_size + sz > LIMIT and cur_size > 0:
            parts.append((cur, order)); cur, cur_size, order = {}, 0, []
        if g["dataset"] not in cur:
            cur[g["dataset"]] = []; order.append(g["dataset"])
        cur[g["dataset"]].append(e); cur_size += sz
parts.append((cur, order))
for i, (p, order) in enumerate(parts, 1):
    obj = {"metadata": {**d.get("metadata", {}), "part": i, "n_parts": len(parts)},
           "datasets": [{"dataset": n, "examples": p[n]} for n in order]}
    (out / f"full_data_out_{i}.json").write_text(json.dumps(obj, ensure_ascii=False))
    print(i, {n: len(p[n]) for n in order})
src.unlink()
print("parts", len(parts))
