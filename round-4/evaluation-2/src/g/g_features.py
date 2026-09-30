#!/usr/bin/env python3
"""Build the G1 window sample, the co-primary sample with G2/G3 variables and outcomes, for one fold.

  python g/g_features.py --fold screen      # before the freeze (screen outcomes were already read in iteration 3)
  python g/g_features.py --fold heldout     # ONLY after d2/open_once.sh wrote the lock (post-opening, Step 5)
  python g/g_features.py --gate-r0c         # R0c: window builder at w=0 reproduces features_screen.parquet

Outputs: results/g_features_<fold>_window.parquet, results/g_features_<fold>_coprimary.parquet
"""
from __future__ import annotations

import argparse
import json
import time

import numpy as np
import pandas as pd

import g_lib as L
from g_lib import config, io_load_prepare, logger, models, outcomes  # noqa: F401

MODEL_COLS = ["A_cont", "CT", "prox_od", "RD", "log_n_partner_tags", "cov", "demic", "mean_topic_score",
              "boundary_share", "abstract_share", "mom_d", "log_centrality", "log_W1", "min_topic_score"]
LOCK = L.D2 / "results" / "HELDOUT_OPENED.lock"


def gate_r0c(G: dict) -> dict:
    fs = pd.read_parquet(L.D2 / "results" / "features_screen.parquet")
    ev = fs[(fs.arm == "main") & (fs.fold == "screen") & fs.kw5 & fs.MAIN].copy()
    t = time.time()
    wf = L.build_features_window(G, ev, 0)
    out = {"n_events": int(len(ev)), "seconds": round(time.time() - t, 1), "max_abs_diff": {}}
    for c in MODEL_COLS:
        a, b = ev[c].to_numpy(float), wf.loc[ev.index, c].to_numpy(float)
        both_nan = np.isnan(a) & np.isnan(b)
        out["max_abs_diff"][c] = float(np.nanmax(np.where(both_nan, 0, np.abs(a - b)))) if len(a) else 0.0
    nchk = (wf.loc[ev.index, "n_win"].to_numpy() == ev.n_entry_papers.to_numpy()).all()
    out["n_entry_papers_equal"] = bool(nchk)
    out["pass"] = bool(nchk and all(v < 1e-9 for v in out["max_abs_diff"].values()))
    (L.RES / "gate_r0c.json").write_text(json.dumps(out, indent=1))
    logger.info(f"R0c: {out}")
    return out


def build(G: dict, fold: str) -> None:
    if fold == "heldout":
        if not LOCK.exists():
            raise SystemExit("REFUSED: held-out G features need the opening lock (d2/results/HELDOUT_OPENED.lock)")
        L.assert_spec_frozen()
        config.SEALED_IDS.clear()
    else:
        config.load_sealed_ids()
    cai = outcomes.CoauthorIndex(G)
    # ---------------- G1 window sample: SENSITIVITY (superset of MAIN), main arm, e <= 2018
    ev = pd.read_parquet(L.D2 / "results" / "events_all.parquet")
    ev = ev[(ev.arm == "main") & (ev.fold == fold) & ev.SENSITIVITY & (ev.e <= 2018)].copy()
    t = time.time()
    wf = L.build_features_window(G, ev, 1)
    logger.info(f"[{fold}] window features for {len(ev)} events in {time.time() - t:.0f}s")
    keep = ["concept_id", "arm", "fold", "d", "e", "o", "F", "route_A", "MAIN", "STRICT", "SENSITIVITY",
            "n_entry_papers", "kw5"]
    win = ev[keep].rename(columns={"n_entry_papers": "n_entry_papers_e", "kw5": "kw5_e"}).join(wf)
    win["n_entry_papers"] = win.n_win
    win["kw5"] = win.n_partners_distinct_w >= 5
    win["single_paper_e"] = win.n_entry_papers_e == 1
    t = time.time()
    win["Y_strict"] = outcomes.compute_Y_shifted(G, win, cai, shift=1).reindex(win.index)
    logger.info(f"[{fold}] shifted outcome in {time.time() - t:.0f}s; multi share {win.multi.mean():.3f}")
    # iteration-3 bridge variant (entry-year controls, window A/CT) via the frozen robustness.recompute_A
    import robustness
    ven = L.load_venues(G)
    # ---------------- co-primary sample (entry year) + G3 variables + outcome-side circularity
    if fold == "screen":
        df = pd.read_parquet(L.D2 / "results" / "screen_events_with_outcomes.parquet")
    else:
        feats = pd.read_parquet(L.D2 / "sealed" / "heldout_features.parquet").reset_index(drop=True)
        base = feats[(feats.arm == "main") & (feats.fold == fold) & feats.kw5 & feats.MAIN]
        df = feats.join(outcomes.compute_Y(G, base, cai))
    mk = (df.arm == "main") & (df.fold == fold) & df.kw5
    g3 = L.g3_features(G, df[mk], ven)
    df = df.join(g3)
    df["Y_strict_hc"] = L.y_strict_hc(G, df[mk & df.MAIN], cai).reindex(df.index)
    if fold == "heldout":
        yn = df[mk & ~df.MAIN]
        if len(yn):  # STRICT / SENSITIVITY-only rows for the spec's 'STRICT population' robustness row
            yy = outcomes.compute_Y(G, yn, cai)
            for c in yy.columns:
                df.loc[yy.index, c] = yy[c]
    bm = df[mk & df.MAIN & (df.e + 6 <= 2024)].copy()
    rw = robustness.recompute_A(G, bm, window=1)
    bm = bm.join(rw)
    bm["Y_strict_shift"] = outcomes.compute_Y_shifted(G, bm, cai, shift=1).reindex(bm.index)
    df = df.join(bm[["A_cont_v", "CT_v", "n_rows_window", "Y_strict_shift"]])
    win.to_parquet(L.RES / f"g_features_{fold}_window.parquet")
    df.to_parquet(L.RES / f"g_features_{fold}_coprimary.parquet")
    logger.info(f"[{fold}] wrote window ({len(win)}) and co-primary ({len(df)}) feature tables")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fold", choices=["screen", "heldout"])
    ap.add_argument("--gate-r0c", action="store_true")
    a = ap.parse_args()
    L.setup_logging(f"g_features_{a.fold or 'r0c'}")
    G = io_load_prepare()
    if a.gate_r0c:
        gate_r0c(G)
    if a.fold:
        build(G, a.fold)


if __name__ == "__main__":
    main()
