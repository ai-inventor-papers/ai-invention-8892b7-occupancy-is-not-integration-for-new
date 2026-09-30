"""Step 7: mechanical BROKERAGE / TURNOVER / MIXED verdict for MAIN x all x E_up x route all (rule text in SPEC3)."""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
from loguru import logger

import common as K


def excl0(ci) -> bool:
    return bool(ci is not None and np.isfinite(ci[0]) and np.isfinite(ci[1]) and (ci[0] > 0 or ci[1] < 0))


def incl0(ci) -> bool:
    return bool(ci is not None and np.isfinite(ci[0]) and np.isfinite(ci[1]) and ci[0] <= 0 <= ci[1])


def grid_row(grid: pd.DataFrame, cell: str, ind: str) -> dict | None:
    r = grid[(grid.cell == cell) & (grid.indicator == ind)]
    return None if r.empty else r.iloc[0].to_dict()


def decide(pf: dict, grid: pd.DataFrame) -> dict:
    rows = pf["rows"]
    S_raw, ci_raw = rows["closure"]["primary"]["S"], rows["closure"]["primary"]["ci"]
    S_res, ci_res = rows["closure_resT"]["primary"]["S"], rows["closure_resT"]["primary"]["ci"]
    S_p, ci_p = rows["closure_persist"]["primary"]["S"], rows["closure_persist"]["primary"]["ci"]
    S_c, ci_c = rows["constraint"]["primary"]["S"], rows["constraint"]["primary"]["ci"]
    r1b_n = pf["closure_persist_na"]["n_treated_with_finite_in_window"]
    r1b_estimable = r1b_n >= K.SPEC3["r1b_min_treated"]
    ratio_ok = bool(np.isfinite(S_res) and np.isfinite(S_raw) and abs(S_res) >= 0.5 * abs(S_raw))
    brokerage = dict(
        S_res_neg_and_CI_excludes_0=bool(np.isfinite(S_res) and S_res < 0 and excl0(ci_res)),
        abs_S_res_ge_half_abs_S_raw=ratio_ok,
        S_persist_neg=bool(r1b_estimable and np.isfinite(S_p) and S_p < 0),
        S_constraint_neg=bool(np.isfinite(S_c) and S_c < 0),
        persist_or_constraint_CI_excludes_0=bool((r1b_estimable and excl0(ci_p)) or excl0(ci_c)),
    )
    r1b_null = (not r1b_estimable) or incl0(ci_p)
    turnover = dict(CI_res_includes_0=incl0(ci_res),
                    abs_S_res_lt_half_abs_S_raw=bool(np.isfinite(S_res) and np.isfinite(S_raw) and abs(S_res) < 0.5 * abs(S_raw)),
                    R1b_null=bool(r1b_null))
    label = "BROKERAGE" if all(brokerage.values()) else ("TURNOVER" if all(turnover.values()) else "MIXED")
    # ---------------- flags (never change the label)
    flags = {}
    S_cd = rows["cdeg_diag"]["primary"]["S"]
    flags["R1c_degree_driven"] = bool(np.isfinite(S_c) and S_c < 0 and np.isfinite(S_cd) and S_cd >= 0)
    gap = pf["closure_persist_na"]["window_na_gap_points"]
    flags["R1b_selection"] = bool(np.isfinite(gap) and gap > K.SPEC3["r1b_selection_points"])
    hm = pf["H_matched"]["rows"]["closure_resT"]
    flags["H_sensitive"] = bool(np.isfinite(hm["S"]) and np.isfinite(S_res) and
                                (np.sign(hm["S"]) != np.sign(S_res) or abs(hm["S"]) < (1 - K.SPEC3["h_sensitive_loss"]) * abs(S_res)))
    flags["underpowered"] = bool(pf["n_matched"] < K.SPEC3["underpowered_n"])
    flags["F2_fallback_triggered"] = bool(pf["n_matched"] < 20)
    new = grid_row(grid, "MAIN|new|E_up|all", "closure")
    if new is not None and np.isfinite(new["S"]):
        flags["fresh_replication"] = dict(S=new["S"], ci=[new["ci_lo"], new["ci_hi"]], p_one_screened=new["p_one_neg"],
                                          n_matched=new["n_matched"],
                                          consistent=bool(new["S"] < 0), significant=bool(new["ci_hi"] < 0))
        nres = grid_row(grid, "MAIN|new|E_up|all", "closure_resT")
        if nres is not None:
            flags["fresh_replication"]["closure_resT"] = dict(S=nres["S"], ci=[nres["ci_lo"], nres["ci_hi"]])
    else:
        flags["fresh_replication"] = dict(S=None, note="no matched new treated")
    old = grid_row(grid, "MAIN|old|E_up|all", "closure")
    flags["old_subset_raw_closure"] = None if old is None else dict(S=old["S"], ci=[old["ci_lo"], old["ci_hi"]], n_matched=old["n_matched"])
    rb = {c: grid_row(grid, "MAIN|all|E_up|B_only", c) for c in ("closure", "closure_resT", "closure_persist", "constraint")}
    flags["route_B_only_agreement"] = {c: (None if v is None else dict(S=v["S"], ci=[v["ci_lo"], v["ci_hi"]], n_matched=v["n_matched"],
                                                                        same_sign=bool(np.sign(v["S"]) == np.sign(rows[c]["primary"]["S"]))))
                                       for c, v in rb.items()}
    cc, rw = rows["closure_resT_cc"]["primary"], rows["closure_resT_raw"]["primary"]
    dep = False
    for alt in (cc, rw):
        if np.isfinite(alt["S"]) and (np.sign(alt["S"]) != np.sign(S_res) or excl0(alt["ci"]) != excl0(ci_res)):
            dep = True
    flags["R1a_model_dependent"] = dep
    inputs = dict(S_raw=S_raw, ci_raw=ci_raw, S_res=S_res, ci_res=ci_res, S_persist=S_p, ci_persist=ci_p, S_constraint=S_c,
                  ci_constraint=ci_c, S_cdeg_diag=S_cd, ci_cdeg_diag=rows["cdeg_diag"]["primary"]["ci"],
                  S_xc_excess=rows["xc_excess"]["primary"]["S"], ci_xc_excess=rows["xc_excess"]["primary"]["ci"],
                  S_res_cc=cc["S"], ci_res_cc=cc["ci"], S_res_raw=rw["S"], ci_res_raw=rw["ci"],
                  S_res_H_matched=hm["S"], ci_res_H_matched=hm["ci"], n_matched_H=pf["H_matched"]["n_matched"],
                  r1b_treated_with_finite=r1b_n, r1b_estimable=r1b_estimable, r1b_na_gap_points=gap,
                  n_onsets=pf["n_onsets"], n_matched=pf["n_matched"], holm=pf["family"],
                  sens_window={c: dict(S=rows[c]["sens"]["S"], ci=rows[c]["sens"]["ci"]) for c in
                               ("closure", "closure_resT", "closure_persist", "constraint")})
    return dict(verdict=label, cell="MAIN x all x E_up x route all", rule_text=K.SPEC3["verdict_rules"],
                brokerage_conditions=brokerage, turnover_conditions=turnover, flags=flags, inputs=inputs,
                label_disclosure="E_up is a POST-HOC primary label (promoted in iteration 2); confirmation only via the "
                                 "iteration-4 sealed held-out fold.")


def main() -> dict:
    pf = json.loads((K.RES / "event_study" / "primary_family.json").read_text())
    grid = pd.read_csv(K.RES / "event_study" / "summary_grid.csv")
    v = decide(pf, grid)
    K.write_json(K.RES / "verdict.json", v)
    logger.info(f"VERDICT {v['verdict']}; brokerage {v['brokerage_conditions']}; turnover {v['turnover_conditions']}")
    return v


if __name__ == "__main__":
    K.setup_logging("verdict")
    main()
