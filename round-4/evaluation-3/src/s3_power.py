#!/usr/bin/env python3
"""S3 POWER TABLE (before any held-out quantity or D3 association is computed).

R1: projected power to detect the screen-sized effect per row, from the frozen mde_table of the R1 spec:
    power = Phi(|S_screen| / (MDE / 2.487) - 1.645)   (2.487 = z_0.95 + z_0.80)
    event-study rows use S_screen (primary_family.json) and the event_study MDE; pooled-panel rows use the screen pooled
    coefficient (confirm_selftest.json panel) and the pooled_panel MDE.
D3: join COUNTS only (presence of an exposure value and of >= 1 qualifying event per concept; no X or Y value is read into
    any statistic) per timing-ladder level; choose the first level with >= 80 screen MAIN concepts; projected MDE.
Writes results/pre_open_power.json.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from loguru import logger
from scipy.stats import norm

WS = Path(__file__).resolve().parent
sys.path.insert(0, str(WS / "src_eval"))
import d3core as D  # noqa: E402

logger.remove()
logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
logger.add(WS / "logs" / "s3_power.log", rotation="30 MB", level="DEBUG")
Z_SUM = 1.645 + 0.842
MIN_SCREEN_N = 80


def r1_power() -> dict:
    E5 = WS / "deps_run" / "exp5"
    spec = json.loads((E5 / "heldout_spec.json").read_text())
    pf = json.loads((E5 / "results" / "event_study" / "primary_family.json").read_text())
    st = json.loads((E5 / "results" / "confirm_selftest.json").read_text())
    ppanel = pf["pooled_panel"]
    out = {}
    for row, m in spec["mde_table"].items():
        S_es = pf["rows"][row]["primary"]["S"]
        coef = ppanel.get(row, {}).get("coef", st["panel"].get(row, {}).get("coef"))
        est = spec["estimator_per_row"].get(row, "event_study")
        p_es = float(norm.cdf(abs(S_es) / (m["event_study"] / Z_SUM) - 1.645))
        p_pp = float(norm.cdf(abs(coef) / (m["pooled_panel"] / Z_SUM) - 1.645)) if coef is not None else np.nan
        out[row] = dict(primary_estimator=est, S_screen_es=S_es, mde_es=m["event_study"], power_es=p_es,
                        coef_screen_panel=coef, mde_panel=m["pooled_panel"], power_panel=p_pp,
                        power_primary=p_pp if est == "pooled_panel" else p_es,
                        screen_sign=("+" if (coef if est == "pooled_panel" else S_es) > 0 else "-"),
                        declared_direction=spec["directions"].get(row))
    return dict(rows=out, expected_heldout_n=spec["expected_heldout_n"],
                reading_test_expectation=("constraint and xc_excess event-study power about "
                                          f"{out['constraint']['power_es']:.2f} / {out['xc_excess']['power_es']:.2f}: "
                                          "SIGN-CONSISTENT is the likely ceiling of the R1-8 reading test"))


def d3_counts() -> dict:
    pop = D.population()
    levels = {}
    for fold in ("screen", "heldout"):
        P = pop[(pop.fold == fold) & pop.MAIN]
        o = D.openness(fold)
        ev = D.events(fold)
        ex = D.exported(fold)
        for lv, (a0, a1, lag, src) in D.LADDER.items():
            hasX = set(D.exposure(o, P, "closure", a0, a1).index)
            hasY = set(D.outcome(ev, P, lag).index) if src == "events" else set(ex.concept_id) & set(P.concept_id)
            both = hasX & hasY
            levels.setdefault(lv, {})[fold] = dict(n_MAIN=len(P), n_hasX=len(hasX), n_hasY=len(hasY), n_both=len(both),
                                                  origin_counts=P[P.concept_id.isin(both)].origin5.value_counts().to_dict())
    chosen = next((lv for lv in D.LADDER if levels[lv]["screen"]["n_both"] >= MIN_SCREEN_N), "L4")
    proj = {}
    for fold in ("screen", "heldout"):
        c = levels[chosen][fold]
        n_groups = sum(1 for v in c["origin_counts"].values() if v >= 5) + (1 if any(v < 5 for v in c["origin_counts"].values()) else 0)
        k = 1 + max(n_groups - 1, 0) + 1
        proj[fold] = dict(n=c["n_both"], k_covariates=k, mde_rho=D.mde_rho(c["n_both"], k))
    return dict(levels=levels, chosen_level=chosen, rule=f"first of L1..L4 with >= {MIN_SCREEN_N} screen MAIN concepts having both X and Y",
                projected=proj)


@logger.catch(reraise=True)
def main() -> None:
    r1 = r1_power()
    for k, v in r1["rows"].items():
        logger.info(f"R1 {k:16s} est={v['primary_estimator']:12s} power_primary={v['power_primary']:.3f} (es {v['power_es']:.3f})")
    d3 = d3_counts()
    for lv, v in d3["levels"].items():
        logger.info(f"D3 {lv}: screen both={v['screen']['n_both']} heldout both={v['heldout']['n_both']}")
    logger.info(f"D3 chosen level {d3['chosen_level']}; projected {d3['projected']}")
    out = dict(note="computed before eval_spec.json / d3_spec.json freeze; no held-out outcome and no D3 association read",
               R1=r1, D3=d3)
    (WS / "results" / "pre_open_power.json").write_text(json.dumps(out, indent=1, default=float))


if __name__ == "__main__":
    main()
