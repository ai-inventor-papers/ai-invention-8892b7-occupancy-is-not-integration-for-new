#!/usr/bin/env python3
"""STAGE 11: method_out.json (exp_gen_sol_out) and results_summary.json (every headline number + the file it comes from).

Dataset 1 'screen_concept_trajectories': one example per screen MAIN concept; output = 3-channel diffusion type,
predict_method = 3-channel type, predict_baseline = entropy-only (B1) type, predict_volume_baseline = volume tercile (B2).
Dataset 2 'sensitivity_all_screen_mainarm': the unfiltered 247 main-arm screen concepts (same k, own B1 fit).
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
from loguru import logger

from common import RES, ROOT, TYP, WORK, C, load_sealed, setup_logging, write_json

AGES = (0, 3, 5, 8)


def r6(x):
    try:
        x = float(x)
    except (TypeError, ValueError):
        return None
    return None if not np.isfinite(x) else round(x, 6)


def examples(ids: list[str], asg: pd.DataFrame, ind: pd.DataFrame, pool: pd.DataFrame, extra: dict) -> list[dict]:
    pinfo = pool.set_index("concept_id")
    grp = pd.read_csv(RES / "labels" / "groups.csv").set_index("concept_id")
    ll = pd.read_csv(RES / "leadlag_by_concept.csv").set_index("concept_id")
    pats = pd.read_csv(RES / "patterns_by_concept.csv").set_index("concept_id")
    roles = pd.read_parquet(RES / "roles.parquet")
    roles = roles[roles.robust]
    rshare = {c: g.role_modal.value_counts(normalize=True).round(4).to_dict() for c, g in roles.groupby("concept_id")}
    imp = pd.read_csv(TYP / "imputed_share.csv").set_index("concept_id").imputed_share.to_dict()
    popj = json.loads((RES / "main_population_hydrated.json").read_text())["concepts"]
    a = asg.set_index("concept_id")
    out = []
    for c in ids:
        p = pinfo.loc[c]
        g = ind[(ind.concept_id == c) & (ind.year >= int(p.F))].sort_values("year")
        summ = {}
        for lab, row in [(f"age{k}", g[g.age == k]) for k in AGES] + [("last", g.tail(1))]:
            if len(row):
                r = row.iloc[0]
                summ[lab] = dict(year=int(r.year), H_rar=r6(r.H_rar), H=r6(r.H), RS=r6(r.RS), active_subfields_3y=int(r.active_subfields_3y),
                                 vol=int(r.vol), pct_alt=r6(r.pct_alt))
        inp = dict(concept_id=c, phrase=p.phrase, F=int(p.F), origin_group=p.origin_group, origin_subfield=p.origin_subfield,
                   route=p.route, n_papers_2000_2024=int(ind[ind.concept_id == c].vol.sum()), series_summary=summ,
                   imputed_share=r6(imp.get(c, extra.get("imputed", {}).get(c))))
        ex = dict(input=json.dumps(inp), output=str(a.loc[c, "cluster_name"]),
                  predict_method=str(a.loc[c, "cluster_name"]), predict_baseline=str(a.loc[c, "cluster_B1_name"]),
                  predict_volume_baseline=str(a.loc[c, "B2_vol_tercile"]) if "B2_vol_tercile" in a.columns and pd.notna(a.loc[c, "B2_vol_tercile"]) else "NA",
                  metadata_E_up_group=str(grp.loc[c, "group"]) if c in grp.index else "censored",
                  metadata_E_up_onset=r6(grp.loc[c, "onset"]) if c in grp.index else None,
                  metadata_closure_tercile=str(grp.loc[c, "closure_tercile"]) if c in grp.index else "NA",
                  metadata_leadlag_category=str(ll.loc[c, "category"]) if c in ll.index else "not_computed",
                  metadata_expansion_onset=r6(ll.loc[c, "exp_onset"]) if c in ll.index else None,
                  metadata_diffusion_onset=r6(ll.loc[c, "diff_onset"]) if c in ll.index else None,
                  metadata_role_share_json=json.dumps(rshare.get(c, {})),
                  metadata_patterns=({k: bool(pats.loc[c, k]) for k in ("INCUBATION_THEN_EXPANSION", "GRADUAL_CENTRALISATION", "EARLY_BRIDGING",
                                                                        "EARLY_BRIDGING_aligned")} if c in pats.index else {}),
                  metadata_population_flags=dict(MAIN=bool(popj.get(c, {}).get("MAIN")), STRICT=bool(popj.get(c, {}).get("STRICT")),
                                                  sense_check_fail=bool(p.sense_check_fail), route=p.route, fold="screen"),
                  metadata_is_medoid=bool(a.loc[c, "is_medoid"]) if "is_medoid" in a.columns else False,
                  metadata_cluster_k3_exploratory=str(a.loc[c, "cluster_k3_name"]) if "cluster_k3_name" in a.columns and pd.notna(a.loc[c, "cluster_k3_name"]) else None)
        out.append(ex)
    return out


def summary() -> dict:
    """Headline numbers read from result files (never typed by hand)."""
    typ = json.loads((RES / "typology.json").read_text())
    val = json.loads((RES / "validation.json").read_text())
    ll = json.loads((RES / "leadlag.json").read_text())
    ro = json.loads((RES / "roles.json").read_text())
    pat = json.loads((RES / "patterns.json").read_text())
    rep = json.loads((RES / "reproduction_check.json").read_text())
    lab = json.loads((RES / "labels" / "label_check.json").read_text())
    pc = pd.read_csv(RES / "patterns_contrast.csv")
    pc = pc[(pc.threshold_version == "recomputed_hydrated") & (pc.population == "screen_MAIN")].set_index("main_pattern")
    pp = pd.read_csv(RES / "patterns.csv")
    pp = pp[(pp.population == "screen_MAIN") & (pp.subset == "all") & (pp.threshold_version == "recomputed_hydrated")].set_index("pattern")
    pr = ro["predeclared"]
    H = {}

    def put(key, value, src):
        H[key] = dict(value=value, source=src)

    put("n_screen_MAIN", typ["n"], "results/typology.json:n")
    put("reproduction_closure_r", rep["gate"]["closure_r"], "results/reproduction_check.json:gate.closure_r")
    put("E_up_onsets_reproduced_old123", lab["identical"], "results/labels/label_check.json:identical")
    put("E_up_groups_MAIN", lab["group_counts_MAIN_screen"], "results/labels/label_check.json:group_counts_MAIN_screen")
    put("typology_status", typ["status"], "results/typology.json:status")
    put("typology_k", typ["k_selected"], "results/typology.json:k_selected")
    put("typology_min_jaccard_by_k", {k: v["min_jaccard"] for k, v in typ["by_k"].items()}, "results/typology.json:by_k.*.min_jaccard")
    put("typology_cluster_sizes_named", {typ["cluster_names"][k]: v for k, v in typ["cluster_sizes"].items()}, "results/typology.json:cluster_sizes")
    put("B1_reproduction_old123_min_jaccard", typ["B1_reproduction_old123"]["min_jaccard"], "results/typology.json:B1_reproduction_old123")
    put("B1_entropy_only_MAIN", {k: typ["B1_entropy_only_MAIN"][k] for k in ("k", "status", "min_jaccard", "n")}, "results/typology.json:B1_entropy_only_MAIN")
    put("AMI_3ch_vs_B1", typ["baselines"]["AMI_3ch_vs_B1"], "results/typology.json:baselines")
    put("AMI_3ch_vs_B2_tercile", typ["baselines"]["AMI_3ch_vs_B2_tercile"], "results/typology.json:baselines")
    put("volume_driven_flag", typ["volume_driven_flag"]["flag"], "results/typology.json:volume_driven_flag")
    put("typology_sensitivities_AMI", {k: v["AMI_vs_primary"] for k, v in typ["sensitivities"].items()}, "results/typology.json:sensitivities")
    put("exploratory_k3", {k: typ["exploratory_finer_k"]["3"][k] for k in ("status", "names", "sizes")} if "3" in typ.get("exploratory_finer_k", {}) else None,
        "results/typology.json:exploratory_finer_k.3")
    for v in ("V1_newcomer_share", "V2_pct_alt_gain", "V3_comm_touched", "V1_newcomer_share_res", "V2_pct_alt_gain_res", "V3_comm_touched_res"):
        r = val["results"][v]
        put(f"validation_{v}", dict(eps2_3ch=r["3ch"]["eps2"], eps2_3ch_ci=r["3ch"]["eps2_ci"], kw_p_3ch=r["3ch"]["kw_p"],
                                    eps2_B1=r["B1_entropy"]["eps2"], eps2_B2_tercile=r["B2_vol_tercile"]["eps2"],
                                    delta_vs_B1=r["delta_3ch_minus_B1_entropy"], delta_vs_B2=r["delta_3ch_minus_B2_vol_tercile"],
                                    medians_by_cluster=r["by_cluster_name"]), f"results/validation.json:results.{v}")
    put("roles_robust_share", pr["agreement"]["robust_share"], "results/roles.json:predeclared.agreement.robust_share")
    put("roles_robust_shares_predeclared", pr["robust_shares"], "results/roles.json:predeclared.robust_shares")
    put("roles_robust_shares_pool_relative", ro["pool_relative"]["robust_shares"], "results/roles.json:pool_relative.robust_shares")
    put("entry_OR_predeclared", {k: v for k, v in pr["entry_hazard"]["primary_logit_robust"]["terms"].items() if k.isupper()},
        "results/roles.json:predeclared.entry_hazard.primary_logit_robust.terms")
    put("entry_OR_pool_relative", {k: v for k, v in ro["pool_relative"]["entry_hazard"]["primary_logit_robust"]["terms"].items() if k.isupper()},
        "results/roles.json:pool_relative.entry_hazard.primary_logit_robust.terms")
    put("entry_model_n", {k: pr["entry_hazard"]["primary_logit_robust"][k] for k in ("n_rows", "n_concepts", "n_events")},
        "results/roles.json:predeclared.entry_hazard.primary_logit_robust")
    put("leadlag_primary", {k: ll["primary"][k] for k in ("n_both_onsets", "share_expansion_first", "share_expansion_first_ci", "category_counts",
                                                          "exp_from_start", "diff_from_start", "lag_median")}, "results/leadlag.json:primary")
    put("leadlag_null", ll["null"], "results/leadlag.json:null")
    put("leadlag_underpowered_F7", ll["F7_underpowered"], "results/leadlag.json:F7_underpowered")
    put("patterns_MAIN", {k: dict(freq=pp.loc[k, "freq"], ci=[pp.loc[k, "ci_lo"], pp.loc[k, "ci_hi"]]) for k in pp.index},
        "results/patterns.csv (screen_MAIN, all, recomputed_hydrated)")
    put("patterns_main_minus_mesh", {k: dict(diff=pc.loc[k, "diff"], boot_ci=[pc.loc[k, "boot_ci_lo"], pc.loc[k, "boot_ci_hi"]],
                                             newcombe=[pc.loc[k, "newcombe_lo"], pc.loc[k, "newcombe_hi"]]) for k in pc.index},
        "results/patterns_contrast.csv (recomputed_hydrated, screen_MAIN)")
    put("early_bridging_gap_diagnostic", pat["early_bridging_gap_diagnostic"], "results/patterns.json:early_bridging_gap_diagnostic")
    return H


def make_previews(full: dict) -> None:
    """mini = first 3 examples per dataset; preview = mini with every string truncated to 200 characters."""
    def trunc(o):
        if isinstance(o, str):
            return o[:200]
        if isinstance(o, dict):
            return {k: trunc(v) for k, v in o.items()}
        if isinstance(o, list):
            return [trunc(v) for v in o]
        return o
    mini = dict(metadata=full["metadata"], datasets=[dict(dataset=d["dataset"], examples=d["examples"][:3]) for d in full["datasets"]])
    (ROOT / "mini_method_out.json").write_text(json.dumps(mini, indent=1, default=str))
    (ROOT / "preview_method_out.json").write_text(json.dumps(trunc(mini), indent=1, default=str))


@logger.catch(reraise=True)
def main() -> None:
    from typology import build_series, entropy_only
    setup_logging("method_out")
    load_sealed()
    ind = pd.read_parquet(RES / "indicators" / "concept_year_indicators_hyd.parquet")
    pool = pd.read_parquet(WORK / "pool_active.parquet")
    asg = pd.read_csv(TYP / "assignments.csv")
    C.assert_not_sealed(asg.concept_id)
    ids = asg.concept_id.tolist()
    typ = json.loads((RES / "typology.json").read_text())
    ds = [dict(dataset="screen_concept_trajectories", examples=examples(ids, asg, ind, pool, {}))]
    # sensitivity dataset: all 247 main-arm screen concepts
    a2 = pd.read_csv(TYP / "assignments_all_screen_mainarm.csv")
    # map 247-run cluster ids to primary names through the concepts shared with the primary run (majority mapping)
    m = a2.merge(asg[["concept_id", "cluster_name"]], on="concept_id")
    cmap = m.groupby("cluster").cluster_name.agg(lambda s: s.value_counts().index[0]).to_dict()
    a2["cluster_name"] = a2.cluster.map(cmap)
    b1 = entropy_only(ind, a2.concept_id.tolist(), k=None, B=100)
    serH, _ = build_series(ind, b1["ids"], ["H"], ages=list(range(0, 9)))
    medH = {c: float(np.median([serH[x][:, 0].mean() for x, l in zip(b1["ids"], b1["labels"]) if l == c])) for c in set(b1["labels"])}
    order = sorted(medH, key=medH.get)
    nm = {c: f"entropy-{'low' if i == 0 else ('high' if i == len(order) - 1 else 'mid' + str(i))} (H median {medH[c]:.2f})" for i, c in enumerate(order)}
    a2["cluster_B1_name"] = a2.concept_id.map(dict(zip(b1["ids"], [nm[l] for l in b1["labels"]]))).fillna("excluded by B1 missingness rule")
    ex2 = examples(a2.concept_id.tolist(), a2, ind, pool, {})
    ds.append(dict(dataset="sensitivity_all_screen_mainarm", examples=ex2))
    meta = dict(method_name="3-channel multivariate-DTW + k-medoids diffusion typology (Hennig-stable k) with roles, lead-lag and patterns",
                baseline="entropy-only DTW typology (iteration-2 recipe, B1); volume terciles (B2) as predict_volume_baseline",
                k=typ["k_selected"], cluster_names=typ["cluster_names"], channels=typ["channels"], dtw=typ["dtw"],
                population="screen fold, MAIN rule (hydrated); held-out concepts sealed", n_primary=len(ids), n_sensitivity=len(a2),
                B1_sensitivity_247=dict(k=b1["k"], min_jaccard=b1["min_jaccard"], n=b1["n"]))
    (ROOT / "method_out.json").write_text(json.dumps(dict(metadata=meta, datasets=ds), indent=1, default=str))
    write_json(ROOT / "results_summary.json", summary())
    make_previews(dict(metadata=meta, datasets=ds))
    logger.info(f"method_out.json: {len(ds[0]['examples'])} + {len(ds[1]['examples'])} examples")


if __name__ == "__main__":
    main()
