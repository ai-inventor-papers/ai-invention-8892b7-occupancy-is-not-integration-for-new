"""Reproduction gate (runs BEFORE any iteration-3 label).

(a) REPRO_CODE: our attachment + vendored indicators on exp_3's own inputs vs exp_3 concept_year_indicators.parquet
    (123 old screen concepts); expected r = 1, max |diff| ~ 1e-6.
(b) REPRO_DATA: the same concepts with dataset_5 c-papers (isolates data drift; see data_change.json).
Then the vendored label + match + event-study code on the mode-(a) indicators with exp_3's pool must return
E_up 41 onsets / 21 matched and closure S = -0.837 [-1.26, -0.43] (B = 1000, exp_3 seed).
Stop rule: r(closure) < 0.99 in (a) -> code bug (raise); in (b) -> documented data drift (warn, continue).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from loguru import logger

import common as K

COLS = ["closure", "closure_obs", "closure_nK", "strength", "pct", "P_raw", "P_rar", "wmz", "btw_pct", "new_relation_rate",
        "novelty", "neigh_growth", "beta_sim_rar", "beta_sne_rar", "H", "RS", "burst_state", "log_vol3", "vol", "closure_res",
        "pct_alt", "btw", "P_rar_m5", "subfield_count"]


def compare(mine: pd.DataFrame, ref: pd.DataFrame, ids: set) -> dict:
    a = ref[ref.concept_id.isin(ids)].set_index(["concept_id", "year"])
    b = mine[mine.concept_id.isin(ids)].set_index(["concept_id", "year"])
    idx = a.index.intersection(b.index)
    out = dict(n_rows_ref=len(a), n_rows_mine=len(b), n_common=len(idx), columns={})
    for c in COLS:
        if c not in a.columns or c not in b.columns:
            continue
        x, y = a.loc[idx, c].astype(float).values, b.loc[idx, c].astype(float).values
        nan_agree = float((np.isfinite(x) == np.isfinite(y)).mean())
        ok = np.isfinite(x) & np.isfinite(y)
        r = float(np.corrcoef(x[ok], y[ok])[0, 1]) if ok.sum() > 2 and np.std(x[ok]) > 0 and np.std(y[ok]) > 0 else float("nan")
        out["columns"][c] = dict(pearson_r=r, max_abs_diff=float(np.abs(x[ok] - y[ok]).max()) if ok.any() else None,
                                 identical_share=float(np.isclose(x[ok], y[ok], rtol=1e-6, atol=1e-6).mean()) if ok.any() else None,
                                 nan_pattern_agree=nan_agree, n=int(ok.sum()))
    return out


def vendored_event_study(ind: pd.DataFrame, pool: pd.DataFrame, B: int = 1000) -> dict:
    import analysis_event as AE
    import lib_metrics as lm
    lab, info = AE.build_labels(ind, pool)
    out = {}
    for tag in ("E", "E_alt", "E_up"):
        lb = AE.assign_groups(lab, tag)
        m = AE.match(lb, ind)
        M, _ = AE.es_matrix(m, ind, "closure")
        st = AE.es_stats(M, B, seed=lm.stable_seed("closure") % 2 ** 31)
        out[tag] = dict(n_onsets=int(len(m)), n_matched=int((m.n_controls > 0).sum()), S_closure=st["S"], ci=st["ci"], p=st["p"])
    return out


def main() -> dict:
    ref = pd.read_parquet(K.EXP3 / "results" / "indicators" / "concept_year_indicators.parquet")
    pool3 = pd.read_parquet(K.EXP3 / "work" / "pool.parquet")
    old = set(pool3.loc[pool3.fold == "screen", "concept_id"])
    res = {}
    for mode in ("repro_code", "repro_data"):
        mine = pd.read_parquet(K.WORK / f"indicators_{mode}.parquet")
        res[mode] = compare(mine, ref, old)
        logger.info(f"[{mode}] closure r = {res[mode]['columns']['closure']['pearson_r']:.6f}, max|diff| "
                    f"{res[mode]['columns']['closure']['max_abs_diff']:.2e}")
    # event-study reproduction on mode (a) and on exp_3's own table (same code path)
    import config as C
    C.SEALED_IDS.clear()
    C.SEALED_IDS.update(set(pd.read_json(K.EXP3 / "work" / "sealed_ids.json", typ="series").tolist()))
    ind_a = pd.read_parquet(K.WORK / "indicators_repro_code.parquet")
    res["event_study_mode_a"] = vendored_event_study(ind_a, pool3)
    res["event_study_exp3_table"] = vendored_event_study(ref, pool3)
    ind_b = pd.read_parquet(K.WORK / "indicators_repro_data.parquet")
    res["event_study_mode_b"] = vendored_event_study(ind_b, pool3)
    C.SEALED_IDS.clear()
    tgt = dict(n_onsets=41, n_matched=21, S=-0.8369791710002537, ci=[-1.2600367131091341, -0.426840113999848])
    ea = res["event_study_mode_a"]["E_up"]
    res["target_iter2_E_up"] = tgt
    res["gate"] = dict(
        closure_r_code=res["repro_code"]["columns"]["closure"]["pearson_r"],
        closure_r_data=res["repro_data"]["columns"]["closure"]["pearson_r"],
        E_up_counts_reproduced=bool(ea["n_onsets"] == 41 and ea["n_matched"] == 21),
        S_reproduced=bool(abs(ea["S_closure"] - tgt["S"]) < 1e-4),
        ci_reproduced=bool(np.allclose(ea["ci"], tgt["ci"], atol=0.02)),
    )
    res["gate"]["passed_code"] = bool(res["gate"]["closure_r_code"] >= 0.99 and res["gate"]["E_up_counts_reproduced"]
                                      and res["gate"]["S_reproduced"])
    res["gate"]["data_drift_flag"] = bool(res["gate"]["closure_r_data"] < 0.99)
    K.write_json(K.RES / "repro" / "reproduction_check.json", res)
    logger.info(f"reproduction gate: {res['gate']}; mode-a E_up {ea}")
    if not res["gate"]["passed_code"]:
        raise RuntimeError(f"REPRODUCTION GATE FAILED (code mode): {res['gate']} -> invoke fallback F1")
    if res["gate"]["data_drift_flag"]:
        logger.warning("data mode (b) r(closure) < 0.99: documented data drift, see results/repro/data_change.json")
    return res


if __name__ == "__main__":
    K.setup_logging("repro")
    main()
