#!/usr/bin/env python3
"""STAGE 3: E_up emergence groups (vendored analysis_event.build_labels / assign_groups) and closure terciles.

Onset years 2008-2015 only; build_labels calls config.assert_not_sealed(ids, [t]) for every label and never labels
focal years 2016-2018. Group 'other' of assign_groups (no eligible year in the onset window) is reported as 'censored'.
Outputs: results/labels/emergence_screen_hyd.parquet, results/labels/groups.csv, results/labels/label_check.json.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from loguru import logger

from common import RES, WORK, X3, C, load_sealed, setup_logging, write_json

LAB = RES / "labels"
LAB.mkdir(parents=True, exist_ok=True)


@logger.catch(reraise=True)
def main() -> None:
    import analysis_event as AE
    setup_logging("labels")
    load_sealed()
    pool = pd.read_parquet(WORK / "pool_active.parquet")
    ind = pd.read_parquet(RES / "indicators" / "concept_year_indicators_hyd.parquet")
    assert not (set(ind.concept_id) & C.SEALED_IDS)
    lab, info = AE.build_labels(ind, pool)
    lab_up = AE.assign_groups(lab, "E_up")
    lab_up.to_parquet(LAB / "emergence_screen_hyd.parquet", index=False)
    grp = lab_up.drop_duplicates("concept_id")[["concept_id", "group", "onset"]].copy()
    grp["group"] = grp.group.replace({"other": "censored"})
    scr = pool[pool.fold == "screen"]
    miss = sorted(set(scr.concept_id) - set(grp.concept_id))
    grp = pd.concat([grp, pd.DataFrame(dict(concept_id=miss, group="censored", onset=np.nan))], ignore_index=True)
    # closure tercile (MAIN screen) of mean closure over ages 3-5
    mc = ind[(ind.age >= 3) & (ind.age <= 5)].groupby("concept_id").closure.agg(lambda v: v.mean() if np.isfinite(v).sum() >= 2 else np.nan)
    grp["closure_mean_age3_5"] = grp.concept_id.map(mc)
    main_ids = set(scr.loc[scr.MAIN, "concept_id"])
    ref = grp[grp.concept_id.isin(main_ids) & grp.closure_mean_age3_5.notna()].closure_mean_age3_5
    q1, q2 = np.quantile(ref, [1 / 3, 2 / 3])
    grp["closure_tercile"] = np.where(grp.closure_mean_age3_5.isna(), "NA",
                                      np.where(grp.closure_mean_age3_5 <= q1, "T1_low",
                                               np.where(grp.closure_mean_age3_5 <= q2, "T2_mid", "T3_high")))
    grp.to_csv(LAB / "groups.csv", index=False)
    # verification on the 123 iteration-2 concepts
    x3m = pd.read_csv(X3 / "results" / "event_study" / "matches_E_up.csv")
    x3_on = {(c, int(t)) for c, t in zip(x3m.concept_id, x3m.t0)}
    old = set(pool.loc[pool.iter2_active & (pool.fold == "screen"), "concept_id"])
    mine = {(c, int(t)) for c, t in zip(grp.concept_id, grp.onset) if c in old and np.isfinite(t)}
    chk = dict(n_onsets_iter2=len(x3_on), n_onsets_hydrated_old=len(mine), identical=mine == x3_on,
               only_iter2=sorted(map(list, x3_on - mine)), only_hydrated=sorted(map(list, mine - x3_on)),
               group_counts_all_screen=grp.group.value_counts().to_dict(),
               group_counts_MAIN_screen=grp[grp.concept_id.isin(main_ids)].group.value_counts().to_dict(),
               closure_tercile_cuts=[float(q1), float(q2)],
               closure_tercile_counts_MAIN=grp[grp.concept_id.isin(main_ids)].closure_tercile.value_counts().to_dict(),
               E_up_variant_counts=info["variants"]["E_up"], reference_arm=info["reference_arm"])
    write_json(LAB / "label_check.json", chk)
    logger.info(f"labels: {chk['group_counts_MAIN_screen']}; iteration-2 onsets reproduced: {chk['identical']} "
                f"({len(mine)} vs {len(x3_on)})")


if __name__ == "__main__":
    main()
