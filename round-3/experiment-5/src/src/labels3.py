"""Step 5: emergence labels, SCREEN fold only (vendored analysis_event.build_labels, unchanged).

The held-out ids are loaded into the vendored guard config.SEALED_IDS before anything is labelled; the vendored code
refuses held-out concepts and the sealed focal years 2016-18. prereg_v3.json must already exist (Step 0).
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
from loguru import logger

import common as K

LABEL_NOTE = ("E_up (sustained uptake: mean >= 20 c-papers/yr over t+1..t+5 and no fall > 30%) is PRIMARY. It was "
              "promoted POST HOC in iteration 2 after the primary E yield (4 onsets) was seen; only the iteration-4 "
              "held-out fold, frozen here, can remove this cost. E_alt (pool-only percentile) is secondary. The "
              "plan-literal E (uptake AND strength-percentile gain >= 20) is reported but infeasible (pool in the "
              "bottom ~5% of strength).")


def guard() -> set:
    import config as C
    pop = pd.read_parquet(K.WORK / "population.parquet")
    held = set(pop.loc[pop.fold == "heldout", "concept_id"])
    C.SEALED_IDS.clear()
    C.SEALED_IDS.update(held)
    assert (K.ROOT / "prereg_v3.json").exists(), "prereg_v3.json must be written before labels"
    return held


def pool_for_labels() -> pd.DataFrame:
    p = pd.read_parquet(K.WORK / "pool_active.parquet")
    p = p[p.fold.isin(["screen", "reference"])].copy()
    return p


def main() -> tuple[pd.DataFrame, dict]:
    import analysis_event as AE
    import config as C
    held = guard()
    ind = pd.read_parquet(K.RES / "indicators" / "concept_year_indicators_hydrated.parquet")
    assert not (set(ind.concept_id) & held), "held-out concept leaked into active indicators"
    pool = pool_for_labels()
    C.assert_not_sealed(pool.concept_id)
    lab, info = AE.build_labels(ind, pool)
    meta = pool.set_index("concept_id")
    for c in ("MAIN", "STRICT", "SENS", "old_new", "route", "hydration_batch"):
        lab[c] = lab.concept_id.map(meta[c])
    for tag in ("E_up", "E_alt", "E"):
        g = AE.assign_groups(lab, tag)
        lab[f"group_{tag}"] = g.group.values
        lab[f"onset_{tag}"] = g.onset.values
    out = K.RES / "labels"
    out.mkdir(parents=True, exist_ok=True)
    lab.to_parquet(out / "labels_screen.parquet", index=False)
    counts = {}
    for P in ("MAIN", "STRICT", "SENS"):
        for tag in ("E_up", "E_alt", "E"):
            d = lab[lab[P].astype(bool)]
            per = d.drop_duplicates("concept_id")
            for key, grp in [("all", per)] + [(f"{k}", g) for k, g in per.groupby("old_new")] + \
                            [(f"route={k}", g) for k, g in per.groupby("route")]:
                rows = d[d.concept_id.isin(set(grp.concept_id))]
                counts[f"{P}|{tag}|{key}"] = dict(
                    n_concepts=int(len(grp)), n_eligible_concept_years=int(len(rows)),
                    n_label_pos_concept_years=int(rows[tag].sum()),
                    n_onsets=int((grp[f"group_{tag}"] == "emerging").sum()),
                    n_never=int((grp[f"group_{tag}"] == "never").sum()),
                    n_other=int((grp[f"group_{tag}"] == "other").sum()),
                    onset_years={str(int(k)): int(v) for k, v in grp[f"onset_{tag}"].dropna().value_counts().sort_index().items()})
    res = dict(label_note=LABEL_NOTE, vendored_info=info, counts=counts)
    K.write_json(out / "label_counts.json", res)
    c = counts["MAIN|E_up|all"]
    logger.info(f"labels: MAIN E_up onsets {c['n_onsets']}, never {c['n_never']}, other {c['n_other']}; "
                f"old {counts.get('MAIN|E_up|old', {}).get('n_onsets')}, new {counts.get('MAIN|E_up|new', {}).get('n_onsets')}")
    return lab, res


if __name__ == "__main__":
    K.setup_logging("labels3")
    main()
