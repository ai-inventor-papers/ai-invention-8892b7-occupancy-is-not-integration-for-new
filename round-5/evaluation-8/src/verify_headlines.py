#!/usr/bin/env python3
"""Short, separate re-derivation of the headline audit metrics from the raw output
CSV/JSON files (not from audit_summary.json), plus a placebo: with source values
shuffled across claims, report-vs-source agreement must collapse; otherwise the
match rule would be vacuous. Writes results/verify_headlines.json.
"""
import csv
import json
import random
from pathlib import Path

WS = Path(__file__).resolve().parent
R = WS / "results"


def num(s):
    try:
        return float(str(s).replace(",", "").replace("−", "-").replace("%", ""))
    except ValueError:
        return None


def agrees(rep: str, src: float) -> bool:
    """Loose independent rule: half-unit of the last shown decimal (percent -> source*100)."""
    t = rep.replace("−", "-").replace(",", "").strip()
    pct = t.endswith("%")
    v = num(t)
    if v is None or src is None:
        return False
    s = src * 100 if pct else src
    if "e" in t.lower():
        return abs(s - v) <= abs(v) * 0.5 + 1e-15
    dec = len(t.rstrip("%").split(".")[1]) if "." in t else 0
    return abs(s - v) <= 0.5 * 10 ** (-dec) + 1e-9 or abs(abs(s) - abs(v)) <= 0.5 * 10 ** (-dec) + 1e-9


rows = list(csv.DictReader(open(R / "record_of_numbers_final.csv")))
stated = [r for r in rows if r["report_value"] and num(r["source_value"]) is not None]
ok_rule = [agrees(r["report_value"], num(r["source_value"])) for r in stated]
ok_flag = [r["flag"] == "OK" for r in stated]
consistent = sum(a == b for a, b in zip(ok_rule, ok_flag))

rng = random.Random(1)
placebo = []
for _ in range(200):
    vals = [num(r["source_value"]) for r in stated]
    rng.shuffle(vals)
    placebo.append(sum(agrees(r["report_value"], v) for r, v in zip(stated, vals)) / len(stated))

drift = list(csv.DictReader(open(R / "report_drift.csv")))
known_gate = {"K01_rq1_rescue_summary", "K02_learned_heading", "K03_fig_methodology", "K04_26of27", "K05_primary_CT_p", "K06_83pct",
              "K08_table20", "K09_or_31x", "K10_neg_plac_matching", "K11_k2_mesh", "K12_mesh_leadlag", "K14_establishment"}
inj = json.load(open(R / "seeded_injection.json"))
ind = json.load(open(R / "indep_rederived.json"))
ta = json.load(open(R / "table_assertions.json"))
rec_missing = sum(1 for r in csv.DictReader(open(WS.parents[3] / "3_invention_loop/iter_3/gen_art/gen_art_evaluation_1/results/record_of_numbers.csv"))
                  if r["flag"] == "MISSING_IN_REPORT") if (WS.parents[3] / ".").exists() else None
out = dict(
    n_stated_numeric=len(stated),
    agreement_by_independent_rule=sum(ok_rule) / len(stated),
    agreement_by_audit_flag=sum(ok_flag) / len(stated),
    rule_vs_flag_consistency=consistent / len(stated),
    placebo_shuffled_agreement_mean=sum(placebo) / len(placebo), placebo_shuffled_agreement_max=max(placebo),
    drift_rows=len(drift), drift_lines=len({r["line"] for r in drift}),
    severity={s: sum(r["severity"] == s for r in drift) for s in ("VERDICT-CHANGING", "NUMBER-ONLY", "WORDING")},
    known_recall=len(known_gate & {r["known"] for r in drift}) / len(known_gate),
    seeded_recall=sum(p["detected"] for p in inj["perturbations"]) / len(inj["perturbations"]),
    independent_agree=sum(abs(float(i["audit_value"]) - float(i["indep_value"])) <= 1e-9 * max(1, abs(float(i["audit_value"]))) for i in ind if i.get("indep_value") is not None),
    independent_n=len(ind),
    tables_pass=sum(t["n_fail"] == 0 for t in ta["tables"].values()), tables_n=len(ta["tables"]),
    missing_in_report_rows=rec_missing,
)
(R / "verify_headlines.json").write_text(json.dumps(out, indent=1))
print(json.dumps(out, indent=1))
