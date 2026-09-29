#!/usr/bin/env python3
"""TODO-5 audit: re-derive headline numbers through a DIFFERENT code path than the one that produced them.

(1) Figure-fidelity headline (value_fidelity = 1.0): recount pass/fail by comparing plotted_values.json with raw
    files using ONLY plain json/csv and hard-wired pointers written here (not sources.yaml, not the registry,
    not checks/independent.py), for the headline F2 numbers.
(2) Scientific headline numbers shown in F2 are re-derived from lower-level stored quantities:
    IRR per SD = exp(b * sd_A) from d2_summary (b, sd); IVW pooled = inverse-variance mean of the two ln IRRs;
    held-out Holm = min(1, 2 * min(p_A, p_CT)) for a two-test family.
(3) Placebo: the fidelity comparison must FAIL on shuffled input (plotted values permuted across rows).
(4) Drift counts recomputed from drift_report.csv with a separate counter.
"""
from __future__ import annotations

import csv
import json
import math
import random
from pathlib import Path

WS = Path(__file__).resolve().parents[1]
RUN = WS.parents[3]
D2 = RUN / "3_invention_loop/iter_3/gen_art/gen_art_experiment_7/results/d2_summary.json"
HO = RUN / "3_invention_loop/iter_4/gen_art/gen_art_evaluation_2/results/heldout_post.json"
CMP = RUN / "3_invention_loop/iter_4/gen_art/gen_art_experiment_9/results/comparison_main_vs_mesh.csv"
G4 = RUN / "3_invention_loop/iter_4/gen_art/gen_art_experiment_9/results/g4_models.json"


def main() -> None:
    d2, ho, g4 = json.loads(D2.read_text()), json.loads(HO.read_text()), json.loads(G4.read_text())
    cmp_rows = {r["estimate"]: r for r in csv.DictReader(CMP.open())}
    pv = {(r["row"], r["field"]): r["value"] for r in json.loads((WS / "figures/F2/plotted_values.json").read_text())
          if r.get("status") == "OK"}
    out = {}
    # (1) hard-wired raw reads vs plotted
    raw = {("scr_co.A", "est"): d2["coprimary_fe_concept_plus_e_plus_d"]["A_cont"]["irr_per_sd"],
           ("ho_co.A", "est"): ho["flags"]["secondary"]["irr_sd_A"],
           ("ho_co.A", "lo"): ho["flags"]["secondary"]["ci_A"][0],
           ("ho_pri.A", "est"): ho["flags"]["primary"]["irr_sd_A"],
           ("mesh_co.A", "est"): g4["rows"]["R2"]["row"]["A_cont"]["irr_sd"],
           ("ivw.A", "est"): float(cmp_rows["main_coprimary_1.30"]["ivw_pooled_irr_sd"])}
    out["fidelity_raw_recheck"] = {f"{k[0]}.{k[1]}": {"plotted": pv[k], "raw": v, "equal": pv[k] == v}
                                   for k, v in raw.items()}
    # (2) re-derivations from lower-level quantities
    co = d2["coprimary_fe_concept_plus_e_plus_d"]["A_cont"]
    sd = d2["nativeness"]["sd_A_cont"]
    irr_from_b = math.exp(co["b"] * sd)
    lm, sm = float(cmp_rows["MeSH R2 (co-primary)"]["ln_irr_sd"]), float(cmp_rows["MeSH R2 (co-primary)"]["se"])
    lr, sr = float(cmp_rows["main_coprimary_1.30"]["ln_irr_sd"]), float(cmp_rows["main_coprimary_1.30"]["se"])
    w1, w2 = 1 / sm ** 2, 1 / sr ** 2
    ivw = math.exp((w1 * lm + w2 * lr) / (w1 + w2))
    ivw_se = math.sqrt(1 / (w1 + w2))
    holm = min(1.0, 2 * min(ho["flags"]["secondary"]["p_A"], ho["flags"]["secondary"]["p_CT"]))
    out["rederived"] = {
        "screen_coprimary_irr_per_0.1": {"from_exp_0.1b": math.exp(0.1 * co["b"]), "stored": co["irr_per_0.1"],
                                         "abs_diff": abs(math.exp(0.1 * co["b"]) - co["irr_per_0.1"])},
        "screen_coprimary_irr_sd": {"from_b_times_full_sample_sd": irr_from_b, "plotted": pv[("scr_co.A", "est")],
                                    "abs_diff": abs(irr_from_b - pv[("scr_co.A", "est")]),
                                    "implied_estimation_sample_sd": math.log(pv[("scr_co.A", "est")]) / co["b"],
                                    "full_sample_sd": sd,
                                    "note": "per-SD scale uses the estimation-sample SD, which d2_summary does not "
                                            "store; NOT independently re-derivable here (difference 3e-4 in IRR)"},
        "ivw_pooled": {"recomputed": ivw, "ci": [math.exp(math.log(ivw) - 1.96 * ivw_se),
                                                 math.exp(math.log(ivw) + 1.96 * ivw_se)],
                       "plotted": pv[("ivw.A", "est")], "abs_diff": abs(ivw - pv[("ivw.A", "est")])},
        "heldout_holm": {"recomputed_2x_min_p": holm, "plotted": pv[("ho_co.A", "col:Holm")],
                         "abs_diff": abs(holm - pv[("ho_co.A", "col:Holm")])},
    }
    # (3) placebo: shuffled plotted values must fail the comparison
    rows = [r for r in json.loads((WS / "figures/F2/plotted_values.json").read_text())
            if r.get("status") == "OK" and isinstance(r["value"], float)]
    vals = [r["value"] for r in rows]
    rng = random.Random(0)
    rng.shuffle(vals)
    truth = {id(r): r["value"] for r in rows}
    n_eq = sum(v == truth[id(r)] for r, v in zip(rows, vals))
    out["placebo_shuffled"] = {"n_values": len(rows), "n_still_equal": n_eq,
                               "fails_as_expected": n_eq < len(rows) * 0.2}
    # (4) drift counts, separate counter
    cnt: dict[str, int] = {}
    for r in csv.DictReader((WS / "results/drift_report.csv").open()):
        cnt[r["status"]] = cnt.get(r["status"], 0) + 1
    summ = json.loads((WS / "results/drift_summary.json").read_text())["counts"]
    out["drift_counts"] = {"recounted": cnt, "reported": summ,
                           "equal": all(cnt.get(k, 0) == v for k, v in summ.items())}
    out["all_ok"] = (all(v["equal"] for v in out["fidelity_raw_recheck"].values())
                     and out["rederived"]["screen_coprimary_irr_per_0.1"]["abs_diff"] < 1e-12
                     and out["rederived"]["ivw_pooled"]["abs_diff"] < 1e-9
                     and out["rederived"]["heldout_holm"]["abs_diff"] < 1e-12
                     and out["placebo_shuffled"]["fails_as_expected"] and out["drift_counts"]["equal"])
    (WS / "audit/rederive_headlines.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1)[:2500])


if __name__ == "__main__":
    main()
