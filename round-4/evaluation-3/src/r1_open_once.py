#!/usr/bin/env python3
"""S6 R1 OPEN ONCE. Run with the exp5 copy's interpreter:

    AII_INVENTION_LOOP=<.../3_invention_loop> deps_run/exp5/.venv/bin/python r1_open_once.py

Imports deps_run/exp5/confirm_heldout.py BY FILE PATH (the file stays byte-identical; its own integrity check re-hashes
it), wraps confirm_heldout.run_fold and analysis_event.match with recorders that only store their inputs / return values
(the LAST call is kept, i.e. the fallback call if the fallback triggers), then calls confirm_heldout.confirm(spec, sha)
exactly once. A guard file results/r1/.opened refuses a second opening. Afterwards the recorded matched sets are
written to results/r1/ and the balance diagnostics (SMDs) are computed from them.
"""
from __future__ import annotations

import importlib.util
import json
import math
import shutil
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

WS = Path(__file__).resolve().parent
E5 = WS / "deps_run" / "exp5"
OUT = WS / "results" / "r1"
GUARD = OUT / ".opened"
ATTEMPTS = WS / "logs" / "r1_attempts.jsonl"
REC: dict = {"run_fold_calls": [], "match_calls": []}


def utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def log_attempt(**kw) -> None:
    ATTEMPTS.parent.mkdir(exist_ok=True)
    with ATTEMPTS.open("a") as f:
        f.write(json.dumps(dict(utc=utc(), **kw)) + "\n")


def load_confirm():
    spec = importlib.util.spec_from_file_location("confirm_heldout", E5 / "confirm_heldout.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["confirm_heldout"] = mod
    spec.loader.exec_module(mod)
    return mod


def install_recorders(CH) -> None:
    import analysis_event as AE
    orig_run_fold, orig_match = CH.run_fold, AE.match

    def rec_match(lab_c, feat_m, *a, **kw):
        m = orig_match(lab_c, feat_m, *a, **kw)
        REC["match_calls"].append(dict(lab=lab_c, never=set(kw.get("never_set", set())), m=m))
        return m

    def rec_run_fold(feat, pool, vol, B, extra=None):
        res = orig_run_fold(feat, pool, vol, B, extra=extra)
        feat_m = feat if extra is None else pd.concat([feat, extra["feat"]], ignore_index=True)
        REC["run_fold_calls"].append(dict(feat=feat_m, matches=res["matches"], fallback=extra is not None,
                                          n_onsets=res["n_onsets"], n_matched=res["n_matched"], n_never=res["n_never"],
                                          H_matched_n=res["H_matched"]["n_matched"],
                                          closure_persist_na=res["closure_persist_na"]))
        return res

    CH.run_fold = rec_run_fold
    AE.match = rec_match


def smd_table(m: pd.DataFrame, feat: pd.DataFrame, screen: pd.DataFrame) -> list[dict]:
    """SMD at k = 0 and k = -3 (and closure at k = -5): treated mean minus mean over treated of the 1/n_c-weighted
    control means, divided by the SCREEN MAIN SD (fixed)."""
    val = feat.set_index(["concept_id", "year"])
    mm = m[m.n_controls > 0]
    specs = [(c, k) for c in ("log_vol3", "age", "H", "subfield_count") for k in (0, -3)] + [("closure", -5), ("closure", -3), ("closure", 0)]
    rows = []
    for col, k in specs:
        sd = float(screen[col].astype(float).std())
        tr, co = [], []
        for r in mm.itertuples():
            y = int(r.t0) + k
            try:
                tv = float(val.loc[(r.concept_id, y), col])
            except KeyError:
                tv = np.nan
            cv = []
            for n in r.controls:
                try:
                    cv.append(float(val.loc[(n, y), col]))
                except KeyError:
                    cv.append(np.nan)
            cv = [v for v in cv if np.isfinite(v)]
            if np.isfinite(tv) and cv:
                tr.append(tv)
                co.append(float(np.mean(cv)))
        smd = (np.mean(tr) - np.mean(co)) / sd if tr and sd > 0 else np.nan
        rows.append(dict(covariate=col, k=k, n_pairs=len(tr), mean_treated=float(np.mean(tr)) if tr else np.nan,
                         mean_controls=float(np.mean(co)) if co else np.nan, screen_sd=sd, smd=float(smd),
                         flag_abs_gt_0_25=bool(np.isfinite(smd) and abs(smd) > 0.25)))
    return rows


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    if GUARD.exists():
        print(f"REFUSED: the R1 held-out fold was already opened ({GUARD.read_text().strip()})", file=sys.stderr)
        sys.exit(2)
    if (E5 / "results_heldout" / "verdict_heldout.json").exists():
        print("REFUSED: results_heldout/verdict_heldout.json already exists in the exp5 copy", file=sys.stderr)
        sys.exit(2)
    CH = load_confirm()
    install_recorders(CH)
    expected = (E5 / "heldout_spec.sha256").read_text().strip()
    CH.K.setup_logging("confirm_heldout")
    t0 = time.time()
    log_attempt(event="start", expected_sha256=expected, mode="import+recorder")
    try:
        out = CH.confirm(E5 / "heldout_spec.json", expected)
    except SystemExit as e:  # refuse() before the sealed load -> not a look
        log_attempt(event="refused_or_exit", code=e.code, secs=round(time.time() - t0, 1))
        raise
    except Exception as e:
        log_attempt(event="crash", error=repr(e), trace=traceback.format_exc()[-2000:], secs=round(time.time() - t0, 1),
                    run_fold_calls=len(REC["run_fold_calls"]))
        raise
    GUARD.write_text(f"opened {utc()} spec {expected}\n")
    import pickle
    with (OUT / "r1_capture_raw.pkl").open("wb") as fh:  # raw recorder contents first, before any post-processing
        pickle.dump(dict(run_fold_calls=REC["run_fold_calls"], match_calls=REC["match_calls"]), fh)
    log_attempt(event="verdict_written", verdict=out["verdict_rule_on_heldout"], fallback=out["fallback_screen_controls"],
                secs=round(time.time() - t0, 1), run_fold_calls=len(REC["run_fold_calls"]))
    shutil.copy2(E5 / "results_heldout" / "verdict_heldout.json", OUT / "verdict_heldout.json")
    # ---------------- captured matched sets + balance
    last = REC["run_fold_calls"][-1]
    m = last["matches"].copy()
    m["controls_json"] = [json.dumps(list(c)) for c in m.controls]
    m.drop(columns=["controls"]).to_parquet(OUT / "r1_matches_capture.parquet", index=False)
    ids = set(m.concept_id) | {c for cs in m.controls for c in cs}
    keep = ["concept_id", "year", "fold", "log_vol3", "age", "H", "subfield_count", "closure", "closure_resT",
            "closure_persist", "constraint", "xc_excess", "wmz"]
    fc = last["feat"]
    fc[fc.concept_id.isin(ids)][[c for c in keep if c in fc.columns]].to_parquet(OUT / "r1_feat_capture.parquet", index=False)
    scr = pd.read_parquet(E5 / "results" / "indicators" / "concept_year_indicators_hydrated.parquet")
    scr = scr[(scr.fold == "screen") & scr.MAIN.astype(bool) & (scr.year <= 2015)]
    bal = smd_table(m, fc, scr)
    import analysis_event as AE
    mc = REC["match_calls"][-1]
    try:
        vend = AE.balance(m, fc, mc["lab"])
    except (KeyError, ValueError) as e:
        vend = [dict(error=repr(e))]
    calls = [dict(fallback=c["fallback"], n_onsets=c["n_onsets"], n_matched=c["n_matched"], n_never=c["n_never"],
                  H_matched_n=c["H_matched_n"]) for c in REC["run_fold_calls"]]
    cap = dict(run_fold_calls=calls, kept_call_index=len(calls) - 1, n_match_calls=len(REC["match_calls"]),
               n_treated=int(len(m)), n_matched=int((m.n_controls > 0).sum()),
               n_unique_controls=len({c for cs in m.controls for c in cs}),
               controls_from_screen=int(len({c for cs in m.controls for c in cs} & set(scr.concept_id))),
               widened_share=float(m.loc[m.n_controls > 0, "widened"].mean()) if ("widened" in m and (m.n_controls > 0).any()) else None,
               mean_controls_per_matched=float(m.loc[m.n_controls > 0, "n_controls"].mean()) if (m.n_controls > 0).any() else None,
               closure_persist_na=last["closure_persist_na"],
               smd_screen_sd=bal, smd_vendored=vend, secs=round(time.time() - t0, 1))
    (OUT / "r1_capture_balance.json").write_text(json.dumps(cap, indent=1, default=lambda o: None if isinstance(o, float) and math.isnan(o) else str(o)))
    print(json.dumps({k: cap[k] for k in ("run_fold_calls", "n_matched", "n_unique_controls", "controls_from_screen")}, default=str))


if __name__ == "__main__":
    main()
