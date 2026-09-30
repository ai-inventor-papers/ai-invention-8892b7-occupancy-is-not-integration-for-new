"""Step 10: method_out.json (exp_gen_sol_out) + results_summary.json.

One example per screen MAIN concept-year used in the prediction step: input = JSON of features <= t (BASE features
and the new openness columns), output = str(E_up), predict_baseline = out-of-fold BASE score, predict_method =
out-of-fold FULL score (BASE + closure_resT + constraint).
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
from loguru import logger

import common as K

FEATS_OUT = ["log_vol3", "growth1", "growth3", "burst_state", "yrs_since_burst", "log_strength", "strength_growth", "PA",
             "btw_pct", "btw_change", "pct", "subfield_count", "H", "RS", "subfield_count_growth3", "H_growth3", "RS_growth3",
             "closure", "closure_persist", "persist_n", "n_ego", "constraint", "effsize", "efficiency", "cdeg_diag", "xc_obs",
             "xc_exp", "xc_excess", "wmz", "new_relation_rate", "novelty", "beta_sim_rar"]


def _f(x):
    try:
        x = float(x)
    except (TypeError, ValueError):
        return None
    return None if not np.isfinite(x) else round(x, 6)


def method_out() -> dict:
    import analysis_predict as AP
    from predict3 import build
    ind = pd.read_parquet(K.RES / "indicators" / "concept_year_indicators_hydrated.parquet")
    lab = pd.read_parquet(K.RES / "labels" / "labels_screen.parquet")
    d = build(lab, ind)
    preds = pd.read_parquet(K.RES / "prediction" / "predictions.parquet")
    d = d.merge(preds[["concept_id", "t", "score_BASE", "score_FULL", "score_FULL_R1bc"]], on=["concept_id", "t"], how="left")
    phrase = pd.read_parquet(K.WORK / "population.parquet").set_index("concept_id").phrase
    exs = []
    for r in d.itertuples(index=False):
        feats = {f: _f(getattr(r, f)) for f in FEATS_OUT if hasattr(r, f)}
        inp = dict(concept_id=r.concept_id, phrase=phrase.get(r.concept_id), t=int(r.t), age=int(r.age), F_band=r.F_band,
                   origin_group=r.origin_group, features_le_t=feats)
        exs.append(dict(input=json.dumps(inp), output=str(int(r.E_up)),
                        predict_baseline=f"{r.score_BASE:.6f}", predict_method=f"{r.score_FULL:.6f}",
                        predict_method_r1bc=f"{r.score_FULL_R1bc:.6f}",
                        metadata_concept_id=r.concept_id, metadata_t=int(r.t), metadata_fold="screen",
                        metadata_old_new=r.old_new, metadata_route=r.route, metadata_group=r.group_E_up,
                        metadata_onset=None if not np.isfinite(r.onset_E_up) else int(r.onset_E_up)))
    v = json.loads((K.RES / "verdict.json").read_text())
    pr = json.loads((K.RES / "prediction.json").read_text())
    out = dict(metadata=dict(
        method_name="Openness before take-off: brokerage or churn? (RQ1 deepen, iteration 3)",
        description="Screen MAIN concept-years (t 2008-2015, ages 3-8). output = E_up (sustained uptake, POST-HOC primary "
                    "label). predict_baseline = out-of-fold L2-logistic score of the vendored BASELINE feature set; "
                    "predict_method = the same model + [closure_resT (fold-refit R1a), constraint]; predict_method_r1bc = "
                    "BASELINE + [closure_persist, xc_excess]. Prediction is REPORTED, NOT CLAIMED.",
        verdict=v["verdict"], verdict_flags={k: val for k, val in v["flags"].items() if isinstance(val, bool)},
        auc=pr["auc"], delta_auc_full_vs_base=pr["delta_FULL_vs_BASE"],
        feature_names=FEATS_OUT, base_features=AP.FEATURE_SETS["BASELINE"]),
        datasets=[dict(dataset="rq1_screen_concept_years", examples=exs)])
    K.write_json(K.ROOT / "method_out.json", out)
    logger.info(f"method_out.json: {len(exs)} examples")
    return out


def summary() -> dict:
    r = {}
    for name, p in [("reproduction", "repro/reproduction_check.json"), ("data_change", "repro/data_change.json"),
                    ("verdict", "verdict.json"), ("power", "power_mde.json"), ("prediction", "prediction.json"),
                    ("r1d", "r1d.json"), ("audit", "audit.json"), ("leakage", "leakage_test.json"),
                    ("confirm_selftest", "confirm_selftest.json")]:
        f = K.RES / p
        r[name] = json.loads(f.read_text()) if f.exists() else None
    pf = json.loads((K.RES / "event_study" / "primary_family.json").read_text())
    lc = json.loads((K.RES / "labels" / "label_counts.json").read_text())
    pop = json.loads((K.RES / "main_population_hydrated.json").read_text())
    rows = {c: dict(S=pf["rows"][c]["primary"]["S"], ci=pf["rows"][c]["primary"]["ci"], p=pf["rows"][c]["primary"]["p"],
                    S_sens_m5_m1=pf["rows"][c]["sens"]["S"], ci_sens=pf["rows"][c]["sens"]["ci"])
            for c in pf["rows"]}
    pw = r["power"]
    s = dict(
        headline=dict(verdict=r["verdict"]["verdict"], cell="MAIN x all x E_up x route all", n_onsets=pf["n_onsets"],
                      n_matched=pf["n_matched"], family=pf["family"], rows=rows,
                      flags=r["verdict"]["flags"]),
        population=pop["counts"], n_sense_replaced=pop["n_sense_replaced"],
        labels={k: v for k, v in lc["counts"].items() if k.startswith(("MAIN|E_up", "MAIN|E_alt", "MAIN|E|"))},
        label_note=lc["label_note"],
        reproduction_gate=r["reproduction"]["gate"] if r["reproduction"] else None,
        reproduction_E_up_mode_a=r["reproduction"]["event_study_mode_a"]["E_up"] if r["reproduction"] else None,
        data_change={k: v for k, v in (r["data_change"] or {}).items() if k != "worst"},
        sensitivities=dict(H_matched=pf["H_matched"], band_only=pf["band_only_matching"], placebo=pf["placebo"],
                           closure_persist_na=pf["closure_persist_na"]),
        pooled_panel=pf["pooled_panel"], extended_panel_closure=pf["extended_panel_closure"],
        partial_logit_closure=pf["partial_logit_closure"],
        balance=pf["balance"], r1d={k: v for k, v in (r["r1d"] or {}).items() if k != "joint_path"},
        power=dict(n_h_treated=pw["n_h_treated"], band80=pw["n_h_treated_80band"],
                   rows={c: dict(es_mde=v["es"]["mde"], es_mde_sd=v["es"]["mde_sd"], panel_mde=v["panel"]["mde"],
                                 panel_mde_sd=v["panel"]["mde_sd"], chosen=v["heldout_primary_estimator"],
                                 es_size=v["es"]["size_at_0"], panel_size=v["panel"]["size_at_0"],
                                 es_power_at_screen_S=v["es"]["power_at_screen_S"]) for c, v in pw["rows"].items()}),
        prediction=dict(auc=r["prediction"]["auc"], delta_FULL=r["prediction"]["delta_FULL_vs_BASE"],
                        delta_FULL_R1bc=r["prediction"]["delta_FULL_R1bc_vs_BASE"],
                        shuffle_mean=r["prediction"]["label_shuffle"]["mean_delta"]),
        audit=dict(verdict_agrees=r["audit"]["verdict_agrees"], max_abs_S_diff=r["audit"]["max_abs_S_diff"]) if r["audit"] else None,
        leakage_passed=bool(r["leakage"] and r["leakage"]["passed"]),
        confirm_selftest_passed=bool(r["confirm_selftest"] and r["confirm_selftest"]["passed"]),
        prereg_v3_sha256=(K.ROOT / "prereg_v3.sha256").read_text().strip(),
    )
    K.write_json(K.RES / "results_summary.json", s)
    return s


def main() -> None:
    method_out()
    summary()


if __name__ == "__main__":
    K.setup_logging("exports")
    main()
