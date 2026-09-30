"""STEP 3: viability layer (rho, m, rho~, bootstrap CIs, BH states) for every eligible (c, d != o, t) edge."""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
from loguru import logger

import benchmark
import io_load
from common import B, RESULTS, SEED
from labels import NMIN_BINS, assign_states, nmin_rule, reason_code

CACHE = RESULTS / "cache"
OUT = RESULTS / "viability"


def benchmark_tables(host: pd.DataFrame, refs: pd.DataFrame, field_of: dict) -> dict:
    cells, mode = benchmark.stationary_cells(refs)
    needed = sorted({(int(d), int(t)) for d, t in zip(host.d, host.t)})
    main = benchmark.rho0_table(cells, needed, field_of)
    past = benchmark.rho0_table(cells, needed, field_of, l3_window=(-4, 0))
    eb = benchmark.eb_table(cells, needed, field_of, main)
    logger.info(f"benchmark: {len(cells)} {mode} cells from {cells.ref_id.nunique()} refs; {len(needed)} (d,t) needed")
    boot = benchmark.refboot_table(cells, needed, field_of, B, SEED)
    three = sorted(cells.ref_id.unique())[:3]
    only3 = benchmark.rho0_table(cells[cells.ref_id.isin(three)], needed, field_of)
    return {"mode": mode, "n_cells": int(len(cells)), "n_refs": int(cells.ref_id.nunique()), "main": main, "past": past,
            "eb": eb, "boot": boot, "only3": only3, "cells": cells}


def run(pool_map) -> None:
    import edges
    OUT.mkdir(parents=True, exist_ok=True)
    G = io_load.prepare()
    con = G["concepts"]
    tax = G["tax"]
    field_of = tax["sub_field"]
    e0 = pd.read_parquet(CACHE / "main_edges_noboot.parquet")
    refs = pd.read_parquet(CACHE / "ref_cells.parquet")
    host0 = e0[e0.role == "host"]
    bt = benchmark_tables(host0, refs, field_of)
    bt["cells"].to_csv(OUT / "benchmark_stationary_cells.csv", index=False)
    rho0 = {"main": {k: v[0] for k, v in bt["main"].items()}, "past": {k: v[0] for k, v in bt["past"].items()},
            "eb": bt["eb"], "only3": {k: v[0] for k, v in bt["only3"].items()}}
    payload = {"totals": io_load.load_totals()}
    mains = sorted(host0.concept_id.unique())
    kw = {"boot": True, "B": B, "rho0": rho0, "rho0_boot": bt["boot"], "canon_w1": True}
    res = pool_map(edges.run_main_task, [(c, kw) for c in mains], payload, "viability")
    e = pd.DataFrame([r for x in res for r in x["rows"]])
    e = e[e.role == "host"].reset_index(drop=True)
    meta = con.set_index("concept_id")
    e["phrase"] = e.concept_id.map(meta.phrase)
    e["fold"] = e.concept_id.map(meta.fold)
    e["F"] = e.concept_id.map(meta.F).astype(int)
    e["F_band"] = e.concept_id.map(meta.F_band)
    e["origin_subfield"] = e.concept_id.map(meta.origin_sub)
    e["field_d"] = e.d.map(lambda x: field_of.get(int(x), -1))
    e["sense_check_fail"] = e.concept_id.map(meta.sense_check_fail)
    e["retrieval_route"] = e.concept_id.map(meta.route)
    e["out_of_time_2016_18"] = e.t.between(2016, 2018)
    key = list(zip(e.d.astype(int), e.t.astype(int)))
    e["rho0"] = [bt["main"][k][0] for k in key]
    e["rho0_level"] = [bt["main"][k][1] for k in key]
    e["rho0_n_cells"] = [bt["main"][k][2] for k in key]
    e["rho0_eb"] = [bt["eb"][k] for k in key]
    e["rho_tilde"] = e.rho / e.rho0
    e["rho_tilde_lo"] = e.get("rt_lo_main")
    e["rho_tilde_hi"] = e.get("rt_hi_main")
    e["growing_edge"] = e.mom_lo > 0
    for c in ["p_greater_main", "p_less_main", "log_ci_width", "m_lo", "m_hi", "rho_lo", "rho_hi"]:
        if c not in e:
            e[c] = np.nan
    nm = nmin_rule(e)
    n_main = nm["n_min_main"]
    logger.info(f"n_min rule: {nm}")
    # states: main + n_min curve + sensitivities (families = (c,t) tested at that n_min)
    e = assign_states(e, n_main, "p_greater_main", "p_less_main", "state_main")
    for k in NMIN_BINS:
        e = assign_states(e, k, "p_greater_main", "p_less_main", f"state_nmin{k}")
    e = assign_states(e, n_main, "p_greater_eb", "p_less_eb", "state_EB")
    e = assign_states(e, n_main, "p_greater_refboot", "p_less_refboot", "state_refboot")
    e = assign_states(e, n_main, "p_greater_past", "p_less_past", "state_pastL3")
    e = assign_states(e, n_main, "p_greater_only3", "p_less_only3", "state_only3refs")
    cw = e.copy()
    cw["n_parents"], cw["n_children"], cw["n_traced"] = cw.n_parents_cw1, cw.n_children_cw1, cw.n_traced_cw1
    cw["m_lo"] = cw.m_lo_cw1
    cw = assign_states(cw.fillna({"p_greater_cw1": 1.0, "p_less_cw1": 1.0, "n_parents": 0, "n_traced": 0}),
                       n_main, "p_greater_cw1", "p_less_cw1", "state_canonW1")
    e["state_canonW1"] = cw["state_canonW1"].to_numpy()
    e["q_greater"] = e["state_main__q_greater"]
    e["q_less"] = e["state_main__q_less"]
    e["tested_main"] = e["state_main__tested"]
    e["reason_code"] = [reason_code(r, n_main) for r in e.itertuples()]
    e["n_min_main"] = n_main
    e = e[[c for c in e.columns if "__" not in c]]
    for i, part in enumerate(np.array_split(np.arange(len(e)), max(1, len(e) // 5000 + 1))):
        e.iloc[part].to_parquet(OUT / f"viability_layer_part_{i:02d}.parquet", index=False)
    e.to_csv(OUT / "viability_layer.csv", index=False)
    summ = summarise(e, nm, bt)
    (OUT / "viability_summary.json").write_text(json.dumps(summ, indent=2, default=float))
    logger.info(f"viability: {len(e)} host edges; state_main shares {summ['label_shares_main']}")


def _shares(s: pd.Series) -> dict:
    return {k: round(float(v), 4) for k, v in s.value_counts(normalize=True).items()} | {"n": int(len(s))}


def summarise(e: pd.DataFrame, nm: dict, bt: dict) -> dict:
    tested = e[e.tested_main]
    out = {
        "status": "DESCRIPTIVE ONLY (Gate A FAIL)",
        "n_edges_eligible": int(len(e)), "n_concepts": int(e.concept_id.nunique()),
        "n_edges_tested_main": int(len(tested)), "n_concepts_with_tested_edge": int(tested.concept_id.nunique()),
        "n_ct_units_with_tested_edge": int(tested.groupby(["concept_id", "t"]).ngroups),
        "n_min": nm, "benchmark_mode": bt["mode"], "benchmark_n_cells": bt["n_cells"], "benchmark_n_refs": bt["n_refs"],
        "benchmark_level_shares_edges": _shares(e.rho0_level),
        "benchmark_level_shares_tested": _shares(tested.rho0_level),
        "reason_codes": _shares(e.reason_code),
        "label_shares_main": _shares(e.state_main), "label_shares_main_tested": _shares(tested.state_main),
        "label_shares_by_nmin": {k: _shares(e[f"state_nmin{k}"]) for k in NMIN_BINS},
        "concepts_with_tested_edge_by_nmin": {k: int(e[e[f"state_nmin{k}"] != "UNDETERMINED"].concept_id.nunique())
                                              for k in NMIN_BINS},
        "sensitivities": {s: _shares(e[s]) for s in ["state_EB", "state_refboot", "state_pastL3", "state_only3refs", "state_canonW1"]},
        "agreement_with_main": {s: round(float((e[s] == e.state_main).mean()), 4)
                                for s in ["state_EB", "state_refboot", "state_pastL3", "state_only3refs", "state_canonW1"]},
        "excluding_sense_flagged": _shares(e[~e.sense_check_fail].state_main),
        "route_A": _shares(e[e.retrieval_route.str.startswith("A")].state_main),
        "route_B": _shares(e[e.retrieval_route.str.startswith("B")].state_main),
        "by_fold_age": {f"{f}|{a}": _shares(g.state_main) for (f, a), g in e.groupby(["fold", "age"])},
        "rho_tilde_quantiles_tested": {q: float(tested.rho_tilde.quantile(q)) for q in [.1, .25, .5, .75, .9]} if len(tested) else {},
        "m_quantiles_tested": {q: float(tested.m.quantile(q)) for q in [.1, .25, .5, .75, .9]} if len(tested) else {},
        "bootstrap_nan_share_mean": float(e.nan_share.mean()) if "nan_share" in e else None,
        "max_t_used_le_t": bool((e.t_max_used <= e.t).all()),
    }
    return out
