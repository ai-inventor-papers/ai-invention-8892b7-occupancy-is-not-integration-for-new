#!/usr/bin/env python3
"""R1-6 balance diagnostics from the recorder capture of the ONE held-out run (results/r1/r1_capture_raw.pkl).

Does not open anything: it only reads what r1_open_once.py recorded. It exists because the in-wrapper post-processing
crashed after the verdict was written (duplicate (concept_id, year) rows: with the fallback, the run's feature frame
holds the reference concepts twice, once from the held-out call and once from the screen-controls block). The frame is
de-duplicated here after verifying that the duplicated rows are identical. Run with the exp5 copy's interpreter
(vendored analysis_event is imported for the comparability table):

    AII_INVENTION_LOOP=<loop> deps_run/exp5/.venv/bin/python r1_balance.py
"""
from __future__ import annotations

import json
import math
import pickle
import sys
from pathlib import Path

import numpy as np
import pandas as pd

WS = Path(__file__).resolve().parent
E5 = WS / "deps_run" / "exp5"
OUT = WS / "results" / "r1"
sys.path.insert(0, str(E5 / "src"))
import common as K  # noqa: E402,F401  (puts vendor/ on sys.path)
import analysis_event as AE  # noqa: E402

sys.path.insert(0, str(WS))
from r1_open_once import smd_table  # noqa: E402


def main() -> None:
    with (OUT / "r1_capture_raw.pkl").open("rb") as fh:
        rec = pickle.load(fh)
    calls = rec["run_fold_calls"]
    last = calls[-1]
    feat = last["feat"]
    dup = feat.duplicated(["concept_id", "year"], keep=False)
    dd = feat[dup]
    n_dup_keys = int(dd.drop_duplicates(["concept_id", "year"]).shape[0])
    identical = bool(dd.drop_duplicates().shape[0] == n_dup_keys) if n_dup_keys else True
    num = [c for c in feat.columns if pd.api.types.is_numeric_dtype(feat[c])]
    if n_dup_keys and not identical:  # tolerate float-noise-only differences
        g = dd.groupby(["concept_id", "year"])[num].agg(lambda s: float(np.nanmax(s) - np.nanmin(s)) if s.notna().any() else 0.0)
        identical = bool(np.nanmax(g.values) < 1e-9)
    fe = feat.drop_duplicates(["concept_id", "year"], keep="first").reset_index(drop=True)
    m = last["matches"]
    scr = pd.read_parquet(E5 / "results" / "indicators" / "concept_year_indicators_hydrated.parquet")
    scr = scr[(scr.fold == "screen") & scr.MAIN.astype(bool) & (scr.year <= 2015)]
    bal = smd_table(m, fe, scr)
    try:
        vend = AE.balance(m, fe, rec["match_calls"][-1]["lab"])
    except (KeyError, ValueError) as e:
        vend = [dict(error=repr(e))]
    ctrl = {c for cs in m.controls for c in cs}
    held_ids = set(pd.read_parquet(E5 / "work" / "pool_heldout.parquet").concept_id)
    mm = m[m.n_controls > 0]
    cap = dict(source="results/r1/r1_capture_raw.pkl (recorder of the single held-out run)",
               run_fold_calls=[dict(fallback=c["fallback"], n_onsets=c["n_onsets"], n_matched=c["n_matched"], n_never=c["n_never"],
                                    H_matched_n=c["H_matched_n"]) for c in calls],
               kept_call_index=len(calls) - 1, n_match_calls=len(rec["match_calls"]),
               duplicate_keys_in_feature_frame=n_dup_keys, duplicates_identical=identical,
               n_treated=int(len(m)), n_matched=int(len(mm)), n_unique_controls=len(ctrl),
               controls_from_heldout=len(ctrl & held_ids), controls_from_screen=len(ctrl - held_ids),
               matched_treated_with_any_screen_control=int(sum(1 for cs in mm.controls if set(cs) - held_ids)),
               widened_share=float(mm["widened"].mean()) if "widened" in mm and len(mm) else None,
               mean_controls_per_matched=float(mm.n_controls.mean()) if len(mm) else None,
               closure_persist_na=last["closure_persist_na"], smd_screen_sd=bal, smd_vendored=vend)
    (OUT / "r1_capture_balance.json").write_text(json.dumps(cap, indent=1, default=lambda o: None if isinstance(o, float) and math.isnan(o) else str(o)))
    for r in bal:
        print(f"{r['covariate']:15s} k={r['k']:+d} n={r['n_pairs']:3d} smd={r['smd']:+.3f} flag={r['flag_abs_gt_0_25']}")
    print({k: cap[k] for k in ("n_treated", "n_matched", "n_unique_controls", "controls_from_heldout", "controls_from_screen",
                               "duplicate_keys_in_feature_frame", "duplicates_identical")})


if __name__ == "__main__":
    main()
