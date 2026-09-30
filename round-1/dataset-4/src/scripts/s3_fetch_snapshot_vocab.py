#!/usr/bin/env python3
"""S3: download OpenAlex keywords + legacy concepts from the free public S3 snapshot (no API credits)."""
import gzip, json, sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import requests
ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "temp" / "datasets" / "openalex_snapshot"
OUT.mkdir(parents=True, exist_ok=True)
def get(url):
    u = url.replace("s3://openalex/", "https://openalex.s3.amazonaws.com/")
    r = requests.get(u, timeout=120); r.raise_for_status()
    return [json.loads(l) for l in gzip.decompress(r.content).decode().splitlines() if l.strip()]
for ent in ["keywords", "concepts"]:
    man = json.loads((OUT / f"{ent}_manifest.json").read_text())
    with ThreadPoolExecutor(16) as ex:
        parts = list(ex.map(get, [f["url"] for f in man["files"]]))
    recs = {}
    for p in parts:
        for r in p:
            recs[r["id"]] = r  # later updated_date partitions overwrite older ones
    rows = []
    for r in recs.values():
        if ent == "keywords":
            rows.append({"id": r["id"].rsplit("/", 1)[-1], "display_name": r.get("display_name"), "works_count": r.get("works_count")})
        else:
            rows.append({"id": r["id"].rsplit("/", 1)[-1], "display_name": r.get("display_name"), "level": r.get("level"),
                         "wikidata": (r.get("wikidata") or "").rsplit("/", 1)[-1] or None, "works_count": r.get("works_count"),
                         "description": (r.get("description") or "")[:200]})
    (OUT / f"{ent}.json").write_text(json.dumps(rows, ensure_ascii=False))
    print(ent, "manifest records", man["record_count"], "parsed", len(rows))
