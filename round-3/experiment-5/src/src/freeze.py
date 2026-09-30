"""Step 8b: write heldout_spec.json (+ .sha256) and log its hash with a UTC stamp in results/freeze_log.jsonl.

Nothing held-out has been read at this point: the sealed W1 features exist on disk (hash-bound here) but no analysis
loads them; held-out labels are computed only inside confirm_heldout.py (iteration 4).
"""
from __future__ import annotations

import json

from loguru import logger

import common as K

HOLM_ROWS = ["closure_resT", "closure_persist", "constraint", "closure"]


def code_hashes() -> dict:
    files = sorted(K.SRC.glob("*.py")) + sorted(K.VENDOR.glob("*.py")) + [K.ROOT / "confirm_heldout.py", K.ROOT / "method.py"]
    return {str(p.relative_to(K.ROOT)): K.sha256_file(p) for p in files if p.exists()}


def main() -> dict:
    power = json.loads((K.RES / "power_mde.json").read_text())
    pf = json.loads((K.RES / "event_study" / "primary_family.json").read_text())
    betas = json.loads((K.RES / "indicators" / "r1a_betas.json").read_text())
    verdict = json.loads((K.RES / "verdict.json").read_text())
    prereg = (K.ROOT / "prereg_v3.sha256").read_text().strip()
    import config as C
    sealed_feat = "sealed/concept_year_indicators_heldout_le2015.parquet"
    pop_files = ["results/main_population_hydrated.json", "work/population.parquet", "work/pool_heldout.parquet",
                 "work/pool_active.parquet", sealed_feat, "sealed/cp_heldout.parquet",
                 "results/indicators/concept_year_indicators_hydrated.parquet", "results/indicators/r1a_betas.json",
                 "results/labels/labels_screen.parquet"]
    inputs = {}
    for y in range(2000, 2025):
        for kind in ("edges", "nodes"):
            p = K.EXP3_SNAP / f"{kind}_y{y}.parquet"
            inputs[f"exp3:work/snapshots/{p.name}"] = K.sha256_file(p)
        inputs[f"exp3:work/snapshots/info_y{y}.json"] = K.sha256_file(K.EXP3_SNAP / f"info_y{y}.json")
    for rel in ("work/communities/persistent_ids.parquet", "results/concept_subfield/rs_distance.parquet"):
        inputs[f"exp3:{rel}"] = K.sha256_file(K.EXP3 / rel)
    inputs["ds5:hyd/concept_work.parquet"] = K.sha256_file(K.DS5 / "hyd" / "concept_work.parquet")
    for p in sorted((K.DS5 / "hyd" / "works").glob("works_part_*.parquet")):
        inputs[f"ds5:hyd/works/{p.name}"] = K.sha256_file(p)
    inputs["ds5:hyd/context/subfield_year_totals.json"] = K.sha256_file(K.DS5 / "hyd" / "context" / "subfield_year_totals.json")
    rows = ["closure", "closure_resT", "closure_persist", "constraint", "xc_excess", "wmz"]
    spec = dict(
        title="Held-out confirmation spec: is pre-take-off openness brokerage or churn? (RQ1, iteration 3 -> 4)",
        entry_point="uv run confirm_heldout.py --spec heldout_spec.json --expected-sha256 <sha256 in heldout_spec.sha256>",
        run_once=True,
        estimands=dict(
            rows=rows + ["cdeg_diag", "effsize"],
            label_E_up="E_up(c,t) = 1 iff mean all-type c-papers/yr over t+1..t+5 >= 20 AND vol(t+5) >= 0.7*vol(t+1); "
                       "t in F+3..F+8, t <= 2019, t not in 2016-18; onset t0 = first t in 2008-2015 with E_up = 1; "
                       "never = eligible concept with no onset (vendored analysis_event.build_labels/assign_groups)",
            S_definition="mean over k in [-3, 0] of the per-k mean (treated - mean of matched controls); k = 0 is the onset "
                         "focal year t0 whose features use data <= t0",
            windows=dict(primary=K.SPEC3["es_primary_window"], sensitivity=K.SPEC3["es_sens_window"], path=K.SPEC3["es_rel_years"]),
            screen_observed_S={c: pf["rows"][c]["primary"]["S"] for c in rows + ["cdeg_diag", "effsize"]}),
        directions={c: ("negative" if K.SPEC3["screened_direction"].get(c, "-") == "-" else "positive") for c in
                    rows + ["effsize"]},
        direction_note="directions are the pre-registered SPEC3 (brokerage-hypothesis) directions frozen in prereg_v3.json "
                       "before labels; a row whose screen S has the opposite sign is still tested in the declared direction.",
        estimator_per_row={c: power["rows"][c]["heldout_primary_estimator"] for c in rows},
        estimator_rule="smaller MDE (80% power, one-sided alpha 0.05); ties within 5% -> event study",
        estimator_definitions=dict(
            event_study="vendored matching + es_matrix; event3.es_boot (B below, seed = stable_seed(row, 'MAIN|all|E_up|all', "
                        "20261001)); one-sided p = share of bootstrap S on the wrong side",
            pooled_panel="OLS row ~ futE + log_vol3 + age + year FE on held-out MAIN emerging+never concept-years (age >= 0, "
                         "2005-2015, post-onset years dropped); CR1 concept-cluster SE; one-sided normal p"),
        mde_table={c: dict(event_study=power["rows"][c]["es"]["mde"], event_study_sd=power["rows"][c]["es"]["mde_sd"],
                           pooled_panel=power["rows"][c]["panel"]["mde"], pooled_panel_sd=power["rows"][c]["panel"]["mde_sd"],
                           es_size_at_0=power["rows"][c]["es"]["size_at_0"], panel_size_at_0=power["rows"][c]["panel"]["size_at_0"])
                   for c in rows},
        expected_heldout_n=dict(n_h_concepts_MAIN=power["n_h_concepts_MAIN"], n_h_eligible=power["n_h_eligible"],
                                n_h_treated=power["n_h_treated"], band80=power["n_h_treated_80band"]),
        matching=dict(C.SPEC["match"], band=True, origin_group="ds5 stratum field group", within="held-out MAIN",
                      controls="held-out MAIN never"),
        heldout_fallback_min_matched=20,
        heldout_fallback_rule="if fewer than 20 matched treated, controls may also come from the screen MAIN never set",
        bootstrap=K.SPEC3["bootstrap"], seeds=K.SPEC3["seeds"],
        holm_family=HOLM_ROWS,
        decision_rules=dict(
            CONFIRMED="Holm-adjusted (over the 4 rows closure_resT, closure_persist, constraint, raw closure) one-sided p < 0.05 "
                      "in the declared direction, with the row's primary estimator",
            DEAD="otherwise; no subgroup search, no new rows, no relabelling",
            verdict="the BROKERAGE / TURNOVER / MIXED rule is applied again on the held-out event study",
            verdict_rule_text=K.SPEC3["verdict_rules"]),
        screen_verdict=verdict["verdict"],
        population_files={rel: K.sha256_file(K.ROOT / rel) for rel in pop_files},
        sealed_features=sealed_feat,
        sealed_pass=dict(status="run", years="2000-2015 (<= max screen onset year)",
                         note="W1 features of the 119 held-out main-arm concepts computed with the frozen code; percentiles are "
                              "insertion ranks against the active distribution; betweenness from a separate graph; residualisation "
                              "uses SCREEN betas (never refit on held-out)"),
        input_manifest=inputs,
        screen_residualisation_betas=dict(r1a=betas["r1a"], res=betas["res_betas"]),
        code_sha256=code_hashes(),
        prereg_v3_sha256=prereg, spec3_sha256=K.spec3_hash(),
        exp3_spec_sha256=json.loads((K.VENDOR / "spec.json").read_text())["sha256"],
        utc=K.utc_now())
    p = K.ROOT / "heldout_spec.json"
    p.write_text(json.dumps(K.clean(spec), indent=1, sort_keys=True))
    h = K.sha256_file(p)
    (K.ROOT / "heldout_spec.sha256").write_text(h + "\n")
    K.append_freeze_log("heldout_spec.json", h, "held-out confirmation spec frozen; nothing held-out read")
    logger.info(f"heldout_spec.json sha256 {h}")
    return dict(sha256=h, n_code_files=len(spec["code_sha256"]))


if __name__ == "__main__":
    K.setup_logging("freeze")
    main()
