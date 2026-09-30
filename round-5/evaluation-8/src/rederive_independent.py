#!/usr/bin/env python3
"""Independent second code path (M6). Shares NO code with audit_core/checks/eval:
plain json + pandas readers and its own implementations of every recomputation.
Input: a JSON list of {id, src, kind, report_value}. Output: the same list with
'indep_value' (or 'indep_error'). The comparison is done by eval.py afterwards.

Usage: python rederive_independent.py sample.json out.json
"""
import json
import os
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(os.environ.get("AII_RUN_ROOT", str(Path(__file__).resolve().parents[4])))
I3 = ROOT / "." / "round-3" / "."
I4 = ROOT / "." / "round-4" / "."


def jget(path, dotted):
    obj = json.load(open(ROOT / path))
    for k in dotted.split("/"):
        if k == "":
            continue
        obj = obj[int(k)] if isinstance(obj, list) else obj[k]
    return float(obj) if not isinstance(obj, str) else float(obj)


def cget(path, spec):
    df = pd.read_csv(ROOT / path, dtype=str, keep_default_na=False)
    cond, col = spec.rsplit("|", 1)
    for c in cond.split(";"):
        k, v = c.split("=", 1)
        df = df[df[k].str.strip() == v]
    if col == "#count":
        return float(len(df))
    return float(df.iloc[0][col])


def holm_first(ps, idx=0):
    order = np.argsort(ps)
    m = len(ps)
    adj = np.empty(m)
    run = 0.0
    for r, i in enumerate(order):
        run = max(run, min(1.0, (m - r) * ps[i]))
        adj[i] = run
    return float(adj[idx])


def rob():
    return pd.read_csv(I3 / "experiment-7/src/results/d2_robustness.csv")


def own_recompute(name):
    if name == "holm_screen_coprimary":
        d = json.load(open(I3 / "experiment-7/src/results/d2_summary.json"))["coprimary_fe_concept_plus_e_plus_d"]
        return holm_first([d["A_cont"]["p_crv1"], d["CT"]["p_crv1"]])
    if name == "holm_heldout_coprimary":
        d = json.load(open(I4 / "evaluation-2/src/results/heldout_post.json"))["flags"]["secondary"]
        return holm_first([d["p_A"], d["p_CT"]])
    if name in ("holm_mesh_R1", "holm_mesh_R2"):
        d = json.load(open(I4 / "experiment-9/src/results/g4_summary.json"))[name[-2:]]
        return holm_first([d["p_crv1"], d["CT_p"]])
    if name.startswith("holm_rq1_"):
        t = pd.read_csv(I4 / "evaluation-3/src/results/tables/r1_holm_decisions.csv")
        row = name[len("holm_rq1_"):]
        idx = list(t["row"]).index(row)
        return holm_first(list(t["p_one"].astype(float)), idx)
    if name.startswith("robust_") or name.startswith("single_paper") or name == "screen_primary_retained":
        r = rob()
        sec = r[(r.fe == "secondary") & r.irr_sd_A.notna()]
        core = sec[(sec.spec != "PRIMARY (MAIN)") & (~sec.spec.str.lower().str.contains("stratum"))]
        sig = lambda d: int(((d.irr_sd_A_lo > 1) & (d.p_A < 0.05)).sum())
        base_n = float(r[(r.spec == "PRIMARY (MAIN)") & (r.fe == "secondary")].N.iloc[0])
        excl_n = float(r[(r.spec == "exclude n_entry_papers == 1") & (r.fe == "secondary")].N.iloc[0])
        out = {"robust_sig_incl": sig(sec), "robust_rows_incl": len(sec), "robust_sig_excl": sig(core),
               "robust_irr_min": float(core[(core.irr_sd_A_lo > 1) & (core.p_A < 0.05)].irr_sd_A.min()),
               "single_paper_share_coprimary": (base_n - excl_n) / base_n, "single_paper_n_coprimary": base_n - excl_n,
               "screen_primary_retained": float(r[(r.spec == "PRIMARY (MAIN)") & (r.fe == "primary")].N.iloc[0]) /
                                          float(r[(r.spec == "PRIMARY (MAIN)") & (r.fe == "primary")].N_input.iloc[0])}
        return float(out[name])
    if name == "single_paper_share_all_screen_kw5":
        ev = pd.read_parquet(I3 / "experiment-7/src/results/screen_events_with_outcomes.parquet")
        ev = ev.loc[(ev["fold"] == "screen") & (ev["MAIN"] == True) & (ev["kw5"] == True)]  # noqa: E712
        return float((ev["n_entry_papers"] == 1).sum() / len(ev))
    if name == "heldout_robust_sig":
        r = pd.read_csv(I4 / "evaluation-2/src/results/heldout_robustness.csv")
        r = r[(r.fe == "secondary") & (~r.spec.str.contains("stratum")) & r.irr_sd_A_lo.notna()]
        return float(((r.irr_sd_A_lo > 1) & (r.p_A < 0.05)).sum())
    if name.startswith("ivw_main_mesh"):
        s = json.load(open(I3 / "experiment-7/src/results/d2_summary.json"))["coprimary_fe_concept_plus_e_plus_d"]["A_cont"]
        g = json.load(open(I4 / "experiment-9/src/results/g4_summary.json"))["R2"]
        b = np.log([s["irr_per_sd"], g["irr_sd"]])
        se = np.array([(np.log(s["irr_per_sd_ci95"][1]) - np.log(s["irr_per_sd_ci95"][0])) / 3.919927969,
                       (np.log(g["ci"][1]) - np.log(g["ci"][0])) / 3.919927969])
        w = 1 / se ** 2
        m = (w * b).sum() / w.sum()
        sm = w.sum() ** -0.5
        q = (w * (b - m) ** 2).sum()
        return {"ivw_main_mesh": math.exp(m), "ivw_main_mesh_lo": math.exp(m - 1.959963985 * sm), "ivw_main_mesh_hi": math.exp(m + 1.959963985 * sm),
                "ivw_main_mesh_i2": max(0.0, (q - 1) / q) if q > 0 else 0.0}[name]
    if name == "ivw_rq1_closure":
        t = pd.read_csv(I4 / "evaluation-3/src/results/tables/r1_iv_synthesis_descriptive.csv").set_index("row").loc["closure"]
        w = np.array([1 / t.se_screen ** 2, 1 / t.se_heldout ** 2])
        return float((w * np.array([t.S_screen, t.S_heldout])).sum() / w.sum())
    if name == "rq1_smd_flag_count":
        t = pd.read_csv(I4 / "evaluation-3/src/results/tables/r1_balance_smd.csv")
        return float((t.smd.abs() > 0.25).sum())
    if name.startswith("rq1_retained_"):
        t = pd.read_csv(I4 / "evaluation-3/src/results/tables/r1_event_study_screen_vs_heldout.csv").set_index("row")
        col = "S_heldout" if name.endswith("heldout") else "S_screen"
        return float(abs(t.loc["closure_resT", col]) / abs(t.loc["closure", col]))
    if name.startswith("leadlag_screen_n_") or name.startswith("leadlag_mesh_n_"):
        cat = name.split("_n_", 1)[1]
        f = (I3 / "experiment-8/src/results/leadlag_by_concept.csv") if "screen" in name else (I4 / "evaluation-4/src/results/mesh/mesh_leadlag_by_concept.csv")
        return float((pd.read_csv(f)["category"] == cat).sum())
    if name == "leadlag_share_both_pooled":
        t = pd.read_csv(I4 / "evaluation-4/src/results/leadlag_denominator_table.csv").set_index("population").loc["pooled_main"]
        return float(t.n_both / t.n)
    if name.startswith("adopter_"):
        x = pd.read_parquet(I4 / "evaluation-5/src/results/exposures_primary.parquet")
        x = x[x.role.isin(["case", "control"])]
        pc, pk = x[x.case == 1].E_any.mean(), x[x.case == 0].E_any.mean()
        return float({"adopter_prev_case": pc, "adopter_prev_ctrl": pk, "adopter_rr": pc / pk}[name])
    if name.startswith("case_diff_"):
        t = pd.read_csv(I4 / "evaluation-4/src/results/case_entries.csv")
        t = t[t.in_coprimary_sample == True]  # noqa: E712
        key = "wireless" if name.endswith("wireless") else "steering"
        t = t[t.phrase.str.lower().str.contains(key)]
        return float(t[t.EST_bin == 1].A_cont.mean() - t[t.EST_bin != 1].A_cont.mean())
    if name in ("n_frame_concepts", "n_main_screen", "n_main_heldout"):
        c = pd.DataFrame(json.load(open(I3 / "experiment-5/src/results/main_population_hydrated.json"))["concepts"])
        if name == "n_frame_concepts":
            return float(len(c))
        return float(((c.MAIN == True) & (c.fold == ("screen" if name.endswith("screen") else "heldout"))).sum())  # noqa: E712
    raise KeyError(f"no independent implementation for {name}")


def resolve(src):
    if src.startswith("recompute:"):
        return own_recompute(src.split(":", 1)[1])
    path, key = src.split("::", 1)
    if key.startswith("csv:"):
        return cget(path, key[4:])
    return jget(path, key)


def main():
    items = json.load(open(sys.argv[1]))
    for it in items:
        try:
            it["indep_value"] = resolve(it["src"])
        except Exception as e:  # report every failure, never swallow
            it["indep_value"] = None
            it["indep_error"] = f"{type(e).__name__}: {e}"
            print(f"FAILED {it['id']}: {it['indep_error']}", file=sys.stderr)
    json.dump(items, open(sys.argv[2], "w"), indent=1)
    print(f"re-derived {sum(1 for i in items if i.get('indep_value') is not None)}/{len(items)}")


if __name__ == "__main__":
    main()
