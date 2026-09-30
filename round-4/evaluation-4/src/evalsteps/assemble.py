"""STEP 7: eval_out.json (exp_eval_sol_out) with headline metrics_agg and three datasets."""
from __future__ import annotations

import json
import math

import numpy as np
import pandas as pd
from loguru import logger

from base import BROAD, E4, E7, E8, HO, RES, TYPE_SHORT, WS, clean

J = lambda p: json.loads((RES / p).read_text())


def num(x):
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) else None


def flat_metrics() -> dict:
    m = {}

    def put(k, v):
        v = num(v)
        if v is not None:
            m[k] = v
    conf = J("confirmation_report.json")["confirmation"]
    put("heldout_E1_success", conf["E1"]["success"])
    b = conf["E1"]["by_cluster"][BROAD]
    put("heldout_share_broad", b["heldout_share"]); put("heldout_share_broad_ci_lo", b["heldout_ci"][0]); put("heldout_share_broad_ci_hi", b["heldout_ci"][1])
    put("screen_share_broad", b["screen_share"])
    put("heldout_E2_success", conf["E2"]["success"])
    for v, r in conf["E2"]["by_V"].items():
        put(f"heldout_E2_{v}_eps2", r["heldout"]["eps2"]); put(f"heldout_E2_{v}_kw_p", r["heldout"]["kw_p"]); put(f"screen_E2_{v}_eps2", r["screen"]["eps2"])
    put("heldout_E3_success", conf["E3"]["success"]); put("heldout_E3_share_expansion_first", conf["E3"]["heldout_share"]); put("heldout_E3_n_both", conf["E3"]["n_both"])
    put("heldout_E4_same_sign_all", conf["E4"]["same_sign_all"])
    for k, v in conf["E4"]["heldout_robust_shares"].items():
        put(f"heldout_E4_robust_share_{k}", v)
    for k, v in conf["E4"]["heldout_ORs"].items():
        put(f"heldout_E4_OR_{k}", v["ratio"]); put(f"screen_E4_OR_{k}", conf["E4"]["screen_ORs"][k]["ratio"])
    put("heldout_E5_overlap_all", all(v["overlap"] for v in conf["E5"].values()))
    for k, v in conf["E5"].items():
        put(f"heldout_E5_{k}", v["heldout"])
    t = J("typology_extras.json")
    for pop in ("screen", "heldout"):
        d = t[pop]["distances"]
        put(f"{pop}_median_d1", d["d1_median"]); put(f"{pop}_median_margin", d["margin_median"])
        put(f"{pop}_ambiguous_share", d["ambiguous_margin_lt_0_05"]["share"]); put(f"{pop}_out_of_support_share", d["out_of_support_d1_gt_screen_p95"]["share"])
    put("heldout_ks_d1_vs_screen_p", t["heldout"]["distances"]["ks_vs_screen_d1"]["p"])
    put("screen_crosstab_gate_passed", t["screen_crosstab_gate"]["passed"])
    for pop in ("screen", "heldout", "pooled"):
        for v, r in t[pop]["crosstabs"].items():
            put(f"crosstab_p_perm_{pop}_{v}", r.get("p_perm")); put(f"crosstab_p_holm_{pop}_{v}", r.get("p_holm")); put(f"crosstab_V_{pop}_{v}", r.get("cramers_v"))
    put("pooled_share_broad", t["pooled"]["type_shares"][BROAD]["share"])
    r = J("rooting.json")
    for pop, key in (("screen", "screen"), ("heldout", "heldout"), ("pooled", "pooled_W1")):
        for mdl, nm in (("model_i_Acont", "typegap_Acont"), ("model_ii_CT", "typegap_CT")):
            x = r[key][mdl]
            put(f"{nm}_{pop}_adj", x["coef"]); put(f"{nm}_{pop}_adj_ci_lo", x["ci"][0]); put(f"{nm}_{pop}_adj_ci_hi", x["ci"][1]); put(f"{nm}_{pop}_adj_p", x["p"])
    for pop in ("screen", "heldout"):
        ds = r[pop]["descriptives"]
        for ty in ("BROAD", "LOCALISED"):
            put(f"entries_per_concept_{ty}_{pop}", ds["occupancy"][ty]["all_main_entries_per_concept"])
            for k in ("A_cont_mean", "A_cont_concept_avg", "CT_mean", "anchored_share", "EST_rate", "rooted_share", "Y_strict_mean", "Y_pos_share"):
                if k in ds[ty]:
                    put(f"{k}_{ty}_{pop}", ds[ty][k]["est"])
        for k, v in ds["diff_BROAD_minus_LOCALISED"].items():
            put(f"rawdiff_{k}_BROAD_minus_LOCAL_{pop}", v["diff"]); put(f"rawdiff_{k}_BROAD_minus_LOCAL_{pop}_ci_lo", v["ci"][0]); put(f"rawdiff_{k}_BROAD_minus_LOCAL_{pop}_ci_hi", v["ci"][1])
    put("heldout_Acont_typegap_prediction_holds", r["heldout"]["prediction_holds"])
    pp = r["screen"]["model_iii_ppml"]
    put("IRR_A_per_sd_BROAD", pp["BROAD"]["irr_per_sd"]); put("IRR_A_per_sd_LOCALISED", pp["LOCALISED"]["irr_per_sd"]); put("interaction_p", pp["interaction_p"])
    me = J("mesh_results.json")
    mt = me["typology"]
    put("mesh_share_broad", mt["type_shares"][BROAD]["share"]); put("mesh_share_broad_ci_lo", mt["type_shares"][BROAD]["wilson_ci"][0]); put("mesh_share_broad_ci_hi", mt["type_shares"][BROAD]["wilson_ci"][1])
    put("mesh_broad_minus_screen", mt["newcombe_broad_vs_screen"]["diff"]); put("mesh_broad_minus_heldout", mt["newcombe_broad_vs_heldout"]["diff"])
    put("mesh_rule_parity_share_broad", mt["rule_parity_subset"]["broad"]["share"])
    put("mesh_switch_rate_coverage", mt["coverage_bias"]["switch"]["share"])
    put("mesh_median_margin", mt["distances"]["margin_median"]); put("mesh_out_of_support_share", mt["distances"]["out_of_support_d1_gt_screen_p95"]["share"])
    put("mesh_ks_d1_vs_screen_p", mt["distances"]["ks_vs_screen_d1"]["p"])
    put("mesh_crosstab_branch_p", mt["crosstabs"]["branch_group"]["p_perm"]); put("mesh_crosstab_branch_V", mt["crosstabs"]["branch_group"]["cramers_v"])
    put("mesh_crosstab_Fband_p", mt["crosstabs"]["F_band"]["p_perm"])
    ml = me["leadlag"]["primary"]
    put("mesh_expansion_first_X", ml["category_counts"].get("expansion_first", 0)); put("mesh_expansion_first_N_both", ml["n_both_onsets"])
    put("mesh_share_expansion_first", ml["share_expansion_first"]); put("mesh_leadlag_null_p", me["leadlag"]["null"]["p_one_sided_greater"])
    mr = me["roles"]
    put("mesh_core_growing_share", mr["role_shares"]["CORE_GROWING"]["share"]); put("mesh_founder_share", mr["role_shares"]["FOUNDER"]["share"])
    put("mesh_core_growing_wilson_upper", mr["core_growing_wilson_upper"]); put("mesh_max_z_within", mr["necessary_condition"]["max_z_within"])
    put("mesh_bridge_share", mr["role_shares"]["BRIDGE"]["share"])
    for k, v in mr["GA_classes"].items():
        put(f"mesh_GA_{k}", v["share"])
    pf = me["patterns"]
    for pop, d in pf["frequencies"].items():
        for pat, v in d.items():
            put(f"pattern_{pat}_{pop}", v["freq"])
    for k, v in pf["newcombe"].items():
        kk = k.replace("|", "_").replace("-", "_minus_")
        put(f"newcombe_{kk}", v["diff"]); put(f"newcombe_{kk}_ci_lo", v["ci"][0]); put(f"newcombe_{kk}_ci_hi", v["ci"][1])
    ll = J("leadlag_table.json")
    for pop, x in ll.items():
        put(f"leadlag_{pop}_n", x["n"]); put(f"leadlag_{pop}_n_both", x["n_both"]); put(f"leadlag_{pop}_n_expansion_first", x["n_expansion_first"])
        put(f"leadlag_{pop}_share_expansion_first", x["share_expansion_first"])
        for c, n in x["counts"].items():
            put(f"leadlag_{pop}_count_{c}", n)
        rc = x["censoring"]["restricted_cohort_F_le_2012"]
        put(f"leadlag_{pop}_restricted_F_le_2012_share", rc["share_expansion_first"]); put(f"leadlag_{pop}_restricted_F_le_2012_n_both", rc["n_both"])
        put(f"leadlag_{pop}_logrank_p", x["censoring"]["logrank_expansion_vs_diffusion"]["p"])
    cs = J("cases_rooting.json")
    for cid, c in cs.items():
        nm = c["phrase"].replace(" ", "_")
        put(f"case_{nm}_rooted_minus_unrooted_Acont", c["rooted_vs_unrooted"]["diff"])
        put(f"case_{nm}_EST_rate", c["EST_rate"]); put(f"case_{nm}_n_entries", c["n_host_entries"])
    return m


def concept_examples() -> list:
    ex = []
    dist = pd.read_csv(RES / "typology_distances.csv")
    asg_s = pd.read_csv(E8 / "typology/assignments.csv").set_index("concept_id")
    llc = {"screen": pd.read_csv(E8 / "results/leadlag_by_concept.csv").set_index("concept_id"),
           "heldout": pd.read_csv(HO / "results/leadlag_by_concept.csv").set_index("concept_id"),
           "mesh": pd.read_csv(RES / "mesh/mesh_leadlag_by_concept.csv").set_index("concept_id")}
    pat = {"screen": pd.read_csv(E8 / "results/patterns_by_concept.csv").set_index("concept_id"),
           "heldout": pd.read_csv(HO / "results/patterns_by_concept.csv").set_index("concept_id"),
           "mesh": pd.read_csv(E4 / "results/rq1_patterns_by_concept.csv").set_index("concept_id")}
    roles = {"screen": pd.read_parquet(E8 / "results/roles.parquet"), "heldout": pd.read_parquet(HO / "results/roles.parquet"),
             "mesh": pd.read_parquet(RES / "mesh/mesh_roles.parquet").rename(columns={"primary": "role_modal"}).assign(robust=True)}
    rshare = {k: v[v.robust].groupby("concept_id").role_modal.value_counts(normalize=True).unstack(fill_value=0) for k, v in roles.items()}
    ent = {"screen": pd.read_parquet(RES / "rooting_screen_sample.parquet"), "heldout": pd.read_parquet(RES / "rooting_heldout_sample_W1.parquet")}
    ent_agg = {k: v.groupby("concept_id").agg(n=("A_cont", "size"), A=("A_cont", "mean"), CT=("CT", "mean")) for k, v in ent.items()}
    est_agg = ent["screen"].groupby("concept_id").EST_bin.mean()
    mesh_a = pd.read_csv(RES / "mesh/mesh_assignments.csv")
    mesh_a["population"] = "mesh"
    allrows = pd.concat([dist, mesh_a[["concept_id", "cluster", "cluster_name", "d1", "d2", "margin", "branch_group", "F_band", "population"]]], ignore_index=True)
    for r in allrows.itertuples(index=False):
        pop, cid = r.population, r.concept_id
        typ = TYPE_SHORT[r.cluster_name]
        inp = dict(population=pop, concept_id=cid, task="assign the concept's 3-channel diffusion trajectory (H_rar, RS, active subfields; F..2024) to the frozen k=2 medoids")
        e = dict(input=json.dumps(inp), output=typ, predict_typology_3ch_frozen=typ,
                 metadata_population=pop, metadata_concept_id=cid,
                 eval_d1=num(r.d1), eval_d2=num(r.d2), eval_margin=num(r.margin), eval_is_broad=float(typ == "BROAD"),
                 eval_ambiguous=float(r.margin < 0.05))
        if pop == "screen" and cid in asg_s.index and isinstance(asg_s.loc[cid, "cluster_B1_name"], str):
            e["predict_baseline_entropy_only"] = asg_s.loc[cid, "cluster_B1_name"]
        for col in ("origin_group", "F_band", "branch_group", "E_up_group"):
            v = getattr(r, col, None)
            if isinstance(v, str):
                e[f"metadata_{col}"] = v
        L = llc[pop]
        if cid in L.index:
            lr = L.loc[cid]
            e["metadata_leadlag_category"] = str(lr.category)
            e["metadata_exp_onset"] = num(lr.exp_onset)
            e["metadata_diff_onset"] = num(lr.diff_onset)
            if lr.category in ("expansion_first", "same_year", "diffusion_first"):
                e["eval_expansion_first"] = float(lr.category == "expansion_first")
        if cid in rshare[pop].index:
            e["metadata_role_shares"] = {k: round(float(v), 4) for k, v in rshare[pop].loc[cid].items()}
            if "BRIDGE" in rshare[pop].columns:
                e["eval_bridge_share"] = float(rshare[pop].loc[cid, "BRIDGE"])
        if cid in pat[pop].index:
            e["metadata_patterns"] = {k: bool(v) for k, v in pat[pop].loc[cid].items() if isinstance(v, (bool, np.bool_))}
        if pop in ent_agg and cid in ent_agg[pop].index:
            a = ent_agg[pop].loc[cid]
            e["eval_n_coprimary_entries"] = float(a.n)
            e["eval_mean_A_cont"] = num(a.A)
            e["eval_mean_CT"] = num(a.CT)
            if pop == "screen" and cid in est_agg.index:
                e["eval_rooted_share"] = num(est_agg.loc[cid])
        ex.append({k: v for k, v in e.items() if v is not None})
    return ex


def case_examples() -> list:
    cs = J("cases_rooting.json")
    ex = []
    for cid, c in cs.items():
        for r in c["entries"]:
            inp = dict(concept_id=cid, phrase=c["phrase"], type=c["cluster"], host_subfield=r["host_subfield"], host_id=int(r["d"]), entry_year=int(r["e"]))
            e = dict(input=json.dumps(inp), output="rooted" if r["EST_bin"] == 1 else "not_rooted", metadata_case=c["phrase"], predict_d2_graft_label=r["graft_label"],
                     metadata_graft_label=r["graft_label"], metadata_in_coprimary_sample=bool(r["in_coprimary_sample"]),
                     eval_A_cont=num(r["A_cont"]), eval_A0_cont=num(r["A0_cont"]), eval_CT=num(r["CT"]), eval_RD=num(r["RD"]),
                     eval_n_entry_papers=num(r["n_entry_papers"]), eval_n_partners=num(r["n_partners_distinct"]),
                     eval_Y_strict=num(r["Y_strict"]), eval_Y_all=num(r["Y_all"]), eval_EST_bin=num(r["EST_bin"]))
            ex.append({k: v for k, v in e.items() if v is not None})
    return ex


def rule_examples() -> list:
    conf = J("confirmation_report.json")
    c = conf["confirmation"]
    ex = []
    for rule in ("E1", "E2", "E3", "E4", "E5"):
        x = c[rule]
        if rule == "E5":
            succ = all(v["overlap"] for v in x.values())
        elif rule == "E4":
            succ = x["same_sign_all"]
        else:
            succ = x["success"]
        e = dict(input=json.dumps(dict(rule=rule, spec_sha256=conf["expected_sha"], population="held-out MAIN (n=100)")),
                 output="success" if succ else "fail", predict_frozen_rule_evaluation="success" if succ else "fail", metadata_detail=json.dumps(clean(x))[:6000],
                 metadata_context=json.dumps(clean(conf["summary"].get(rule, {}))), eval_success=float(bool(succ)))
        ex.append(e)
    return ex


def run() -> dict:
    m = flat_metrics()
    out = dict(metadata=dict(evaluation_name="RQ2 descriptive layer: one-time held-out confirmation, MeSH second population, type x rooting",
                             heldout_spec_sha256="695166b465d36f3311d13bdc7d315204a849ab96dc28c0c36fa002f4ad217d2a",
                             mesh_spec_file="results/mesh_spec.json", rooting_spec_file="results/rooting_spec.json",
                             freeze_log="logs/freeze_log.txt", power_mde="results/power_mde.json",
                             kept_irreproducible="exp8_frozen/heldout_run/ (one-time opening; stays on the run volume)",
                             notes="screen rows descriptive; held-out W1 type x A_cont is the out-of-sample association test; MeSH roles are a population contrast"),
               metrics_agg=m,
               datasets=[dict(dataset="concept_level", examples=concept_examples()),
                         dict(dataset="case_entries", examples=case_examples()),
                         dict(dataset="confirmation_rules", examples=rule_examples())])
    (WS / "eval_out.json").write_text(json.dumps(clean(out), indent=1))
    (WS / "full_eval_out.json").write_text(json.dumps(clean(out), indent=1))
    mini = dict(clean(out), datasets=[dict(ds, examples=ds["examples"][:3]) for ds in clean(out)["datasets"]])

    def trunc(o):
        return o[:200] if isinstance(o, str) else ([trunc(x) for x in o] if isinstance(o, list) else ({k: trunc(v) for k, v in o.items()} if isinstance(o, dict) else o))
    (WS / "mini_eval_out.json").write_text(json.dumps(mini, indent=1))
    (WS / "preview_eval_out.json").write_text(json.dumps(trunc(mini), indent=1))
    logger.info(f"eval_out.json: {len(m)} metrics; datasets {[len(d['examples']) for d in out['datasets']]}")
    return out
