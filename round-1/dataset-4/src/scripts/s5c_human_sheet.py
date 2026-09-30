#!/usr/bin/env python3
"""Write labelling/human_check_sheet.csv: the 200 silver_gold items with A, B, adjudicator labels and an empty human_label column."""
import csv, json
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
LAB = ROOT / "labelling"
items = json.loads((LAB / "items.json").read_text())
AB = json.loads((LAB / "labels_AB.json").read_text())
ADJ = json.loads((LAB / "labels_adj.json").read_text())
with (LAB / "human_check_sheet.csv").open("w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["key", "surface_forms", "snippet_1", "snippet_2", "snippet_3", "label_A", "label_B", "label_adjudicator",
                "adjudicator_rationale", "human_label", "human_checked", "human_notes"])
    for k in ADJ["silver_gold_200"]:
        it = items[k]
        sn = [s["text"] for s in it["snippets"]] + ["", "", ""]
        w.writerow([k, " | ".join(it["surface_forms"]), sn[0], sn[1], sn[2], AB["A"].get(k, {}).get("label"),
                    AB["B"].get(k, {}).get("label"), ADJ["labels"].get(k, {}).get("label"),
                    ADJ["labels"].get(k, {}).get("rationale"), "", "false", ""])
print("rows", len(ADJ["silver_gold_200"]))
