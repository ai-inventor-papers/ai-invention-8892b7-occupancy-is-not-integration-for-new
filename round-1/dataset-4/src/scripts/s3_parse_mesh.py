#!/usr/bin/env python3
"""S3c: parse NLM MeSH 2026 descriptor XML (desc2026.gz) into heading + entry terms JSON."""
import gzip, json
import xml.etree.ElementTree as ET
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
src = ROOT / "raw" / "mesh" / "desc2026.gz"
out = ROOT / "temp" / "datasets" / "mesh" ; out.mkdir(parents=True, exist_ok=True)
rows = []
with gzip.open(src) as f:
    for ev, el in ET.iterparse(f, events=("end",)):
        if el.tag == "DescriptorRecord":
            ui = el.findtext("DescriptorUI")
            mh = el.findtext("DescriptorName/String")
            terms = sorted({t.findtext("String") for t in el.iter("Term") if t.findtext("String")} - {mh})
            trees = [t.text for t in el.iter("TreeNumber")]
            rows.append({"ui": ui, "heading": mh, "entry_terms": terms, "tree_numbers": trees})
            el.clear()
(out / "mesh_descriptors_2026.json").write_text(json.dumps(rows, ensure_ascii=False))
print(len(rows), sum(len(r["entry_terms"]) for r in rows), rows[100])
