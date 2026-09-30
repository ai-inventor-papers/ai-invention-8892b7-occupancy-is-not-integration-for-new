import orjson, os
from pathlib import Path
R = Path(__file__).resolve().parent.parent / "hyd"
fr = orjson.loads((R / "sample_frame_frozen.json").read_bytes()); o = fr["hydration_order"]
st = {c: (orjson.loads((R / f"retrieval/{c}.json").read_bytes()) if (R / f"retrieval/{c}.json").exists() else {}) for c in o}
k = 0
while k < len(o) and st[o[k]].get("complete"): k += 1
inflight = [i for i, c in enumerate(o) if st[c] and not st[c].get("complete")]
print("prefix", k, "complete", sum(1 for c in o if st[c].get("complete")), "in-flight positions", inflight,
      "routes(iter2 complete)", {r: sum(1 for c in o if st[c].get("hydration_batch") == "iter2" and st[c]["discovery"]["route"] == r) for r in ["A_openalex_native", "B_s2_index"]})
