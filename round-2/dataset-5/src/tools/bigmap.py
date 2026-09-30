import orjson, sqlite3, sys
from pathlib import Path
R = Path(__file__).resolve().parent.parent / "hyd"
fr = orjson.loads((R / "sample_frame_frozen.json").read_bytes())
for pos in map(int, sys.argv[1:]):
    c = fr["hydration_order"][pos]
    st = orjson.loads((R / f"retrieval/{c}.json").read_bytes())
    hits = [h for h in st["discovery"].get("s2_hits", []) if h.get("cid") and (h.get("s2_text_match", True) or not h.get("s2_has_abstract", False))]
    con = sqlite3.connect(R / "work_store/s2map.sqlite")
    cids = [h["cid"] for h in hits]; done = 0
    for i in range(0, len(cids), 900):
        ch = cids[i:i+900]; done += con.execute(f"SELECT COUNT(*) FROM s2map WHERE corpus_id IN ({','.join('?'*len(ch))})", ch).fetchone()[0]
    print(pos, c, "to map", len(cids), "mapped so far", done, "complete", st.get("complete"))
