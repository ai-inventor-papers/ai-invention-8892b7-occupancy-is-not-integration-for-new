"""Final audit: re-derive the primary-family S values, the verdict and the Holm p through an INDEPENDENT path.

* S: pandas merge of matches x indicators -> per (treated, k) control mean -> treated - control -> per-k mean ->
  window mean (no vendored es_matrix / es_stats).
* CI / p: a separate bootstrap implementation (resampling treated ids with numpy choice, a different seed and a
  groupby-based mean), so CIs agree only up to Monte-Carlo error.
* Verdict: re-evaluated from the audit numbers with an independent implementation of the rule text.
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
from loguru import logger

import common as K

ROWS = ["closure", "closure_resT", "closure_persist", "constraint", "cdeg_diag", "xc_excess"]


def diffs(m: pd.DataFrame, ind: pd.DataFrame, col: str) -> pd.DataFrame:
    mm = m[m.n_controls > 0].copy()
    ks = pd.DataFrame(dict(k=K.SPEC3["es_rel_years"]))
    t = mm[["concept_id", "t0"]].merge(ks, how="cross")
    t["year"] = t.t0 + t.k
    v = ind[["concept_id", "year", col]].rename(columns={col: "v"})
    tv = t.merge(v, on=["concept_id", "year"], how="left").rename(columns={"v": "tv"})
    ctl = mm[["concept_id", "t0", "controls"]].explode("controls").rename(columns={"concept_id": "treated", "controls": "ctl"})
    ctl = ctl.merge(ks, how="cross")
    ctl["year"] = ctl.t0 + ctl.k
    ctl = ctl.merge(v.rename(columns={"concept_id": "ctl"}), on=["ctl", "year"], how="left")
    cm = ctl.groupby(["treated", "k"]).v.mean().rename("cm").reset_index()   # pandas mean skips NaN (= nanmean)
    out = tv.merge(cm, left_on=["concept_id", "k"], right_on=["treated", "k"], how="left")
    out["d"] = out.tv - out.cm
    return out[["concept_id", "k", "d"]]


def S_of(dd: pd.DataFrame, lo: int, hi: int) -> float:
    perk = dd.groupby("k").d.mean()
    w = perk[(perk.index >= lo) & (perk.index <= hi)].dropna()
    return float(w.mean()) if len(w) else np.nan


def main(B: int = 2000) -> dict:
    import lib_metrics as lm
    ind = pd.read_parquet(K.RES / "indicators" / "concept_year_indicators_hydrated.parquet")
    m = pd.read_parquet(K.RES / "event_study" / "matches_primary.parquet")
    m["controls"] = m.controls.map(lambda s: [x for x in s.split("|") if x])
    pf = json.loads((K.RES / "event_study" / "primary_family.json").read_text())
    ver = json.loads((K.RES / "verdict.json").read_text())
    lo, hi = K.SPEC3["es_primary_window"]
    rng = np.random.default_rng(987654)
    res = {}
    for col in ROWS:
        dd = diffs(m, ind, col)
        S = S_of(dd, lo, hi)
        ids = dd.concept_id.unique()
        groups = {c: g for c, g in dd.groupby("concept_id")}
        bs = []
        for _ in range(B):
            pick = rng.choice(ids, len(ids), replace=True)
            bd = pd.concat([groups[c] for c in pick], ignore_index=True)
            bs.append(S_of(bd, lo, hi))
        bs = np.array(bs)
        bs = bs[np.isfinite(bs)]
        p = float(max(2 * min(np.mean(bs <= 0), np.mean(bs >= 0)), 1 / len(bs)))
        main_S = pf["rows"][col]["primary"]["S"]
        res[col] = dict(S_audit=S, S_main=main_S, abs_diff=abs(S - main_S) if main_S is not None else None,
                        ci_audit=np.percentile(bs, [2.5, 97.5]).tolist(), ci_main=pf["rows"][col]["primary"]["ci"],
                        p_audit=p, p_main=pf["rows"][col]["primary"]["p"])
    holm_a = lm.holm([res[c]["p_audit"] for c in ("closure_resT", "closure_persist", "constraint")])
    for c, h in zip(("closure_resT", "closure_persist", "constraint"), holm_a):
        res[c]["p_holm_audit"] = h
        res[c]["p_holm_main"] = pf["family"][c]["p_holm"]

    # independent verdict
    def ex0(ci):
        return ci[0] > 0 or ci[1] < 0
    S_raw, S_res = res["closure"]["S_audit"], res["closure_resT"]["S_audit"]
    r1b_ok = pf["closure_persist_na"]["n_treated_with_finite_in_window"] >= K.SPEC3["r1b_min_treated"]
    brk = (S_res < 0 and ex0(res["closure_resT"]["ci_audit"]) and abs(S_res) >= 0.5 * abs(S_raw) and r1b_ok
           and res["closure_persist"]["S_audit"] < 0 and res["constraint"]["S_audit"] < 0
           and ((r1b_ok and ex0(res["closure_persist"]["ci_audit"])) or ex0(res["constraint"]["ci_audit"])))
    trn = (not ex0(res["closure_resT"]["ci_audit"]) and abs(S_res) < 0.5 * abs(S_raw)
           and ((not r1b_ok) or not ex0(res["closure_persist"]["ci_audit"])))
    v_audit = "BROKERAGE" if brk else ("TURNOVER" if trn else "MIXED")
    out = dict(rows=res, verdict_audit=v_audit, verdict_main=ver["verdict"], verdict_agrees=v_audit == ver["verdict"],
               max_abs_S_diff=float(max(r["abs_diff"] for r in res.values() if r["abs_diff"] is not None)),
               note="independent pandas-merge S and a separate bootstrap (different RNG and resampling code)")
    K.write_json(K.RES / "audit.json", out)
    logger.info(f"audit: max |S diff| {out['max_abs_S_diff']:.2e}; verdict audit {v_audit} vs main {ver['verdict']}")
    return out


if __name__ == "__main__":
    K.setup_logging("audit")
    main()
