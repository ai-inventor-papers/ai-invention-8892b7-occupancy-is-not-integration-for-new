#!/usr/bin/env python3
"""S9 summary: spend totals, pool yield curve, and the ONE aggregate figure from the sealed file
(share of pool phrases with < 5 papers/yr averaged over 2020-2024, audit arm vs LLM arm)."""
import csv, json
from collections import Counter
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
pool = json.loads((ROOT / "data_out" / "pool_early.json").read_text())
sealed = json.loads((ROOT / "data_out" / "pool_outcomes_SEALED.json").read_text())
def dead(k):
    v = sealed[k]["yearly_counts_1980_2026"]
    return sum(int(v[str(y)] if str(y) in v else v.get(y, 0)) for y in range(2020, 2025)) / 5 < 5
out = {}
for tier_set, name in [(("strict",), "strict"), (("strict", "relaxed_plan"), "strict+relaxed_plan"),
                       (("strict", "relaxed_plan", "relaxed_low_volume"), "all_tiers")]:
    for arm in ("audit", "llm"):
        ks = [p["key"] for p in pool if p["eligibility_tier"] in tier_set and p["audit_arm"] == (arm == "audit")]
        out[f"{name}|{arm}_arm"] = {"n": len(ks), "later_dead_share": round(sum(dead(k) for k in ks) / len(ks), 3) if ks else None}
yield_curve = {}
for lo in (20, 10, 5):
    for hi in (300, 500):
        for Fr in ((2005, 2016), (2004, 2017)):
            e = [p for p in pool if p["F"] and Fr[0] <= p["F"] <= Fr[1] and p["n_early"] and lo <= p["n_early"] <= hi
                 and p["pre_F"] <= max(2, 0.05 * p["n_early"])]
            yield_curve[f"n_early[{lo},{hi}] F{Fr[0]}-{Fr[1]}"] = {"eligible_before_anchor": len(e),
                                                                     "anchor_ok": sum(p["anchor_ok"] for p in e)}
oa_cred = 0
with (ROOT / "logs" / "openalex_spend.csv").open() as f:
    for r in csv.DictReader(f):
        try:
            oa_cred += int(r["credits_used"] or 0)
        except ValueError:
            pass
llm = Counter()
for l in (ROOT / "logs" / "llm_spend.jsonl").open():
    r = json.loads(l); llm[r["model"]] += r["cost"]
summ = {"later_dead_share_from_sealed_file": out, "pool_yield_curve_1000_counted": yield_curve,
        "eligibility_reasons": Counter(p["eligibility_reason"] for p in pool).most_common(),
        "tiers": Counter(f"{p['eligibility_tier']}|anchor_ok={p['anchor_ok']}" for p in pool),
        "link_status": Counter(p["link_status"] for p in pool),
        "link_status_all_tiers_eligible": Counter(p["link_status"] for p in pool if p["eligibility_tier"] != "not_eligible"),
        "openalex_credits_this_artifact": oa_cred, "openalex_usd_this_artifact": round(oa_cred * 0.0001, 4),
        "llm_usd_by_model": {k: round(v, 4) for k, v in llm.items()}, "llm_usd_total": round(sum(llm.values()), 4)}
(ROOT / "logs" / "summary.json").write_text(json.dumps(summ, indent=1))
print(json.dumps(summ, indent=1))
