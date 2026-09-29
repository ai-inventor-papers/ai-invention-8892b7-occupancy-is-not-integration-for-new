#!/usr/bin/env python3
"""Iteration-4 confirmation on the sealed held-out fold. Run ONCE:

    uv run confirm_heldout.py --spec heldout_spec.json --expected-sha256 <hash>

1. Refuses (exit 2) unless sha256(spec) == --expected-sha256 == the last logged hash in results/freeze_log.jsonl, and
   every code / input hash recorded in the spec matches the files on disk.
2. Sets AII_OPEN_HELDOUT=1 and loads the sealed W1 features (src/seal.load_sealed).
3. Computes the held-out E_up labels HERE, from dataset_5 hyd/concept_work.parquet joined to the works' publication
   years (all types, the same vol definition as the screen). This is the only place W2 quantities of held-out
   concepts are ever computed.
4. Matches within held-out MAIN (controls = held-out never). Pre-declared: if fewer than 20 matched treated, controls may
   also come from the screen MAIN never set.
5. Runs the estimators fixed in the spec -> results_heldout/verdict_heldout.json.

    uv run confirm_heldout.py --self-test-on-screen

runs the identical code path on the screen fold (no unlock) and must reproduce the Step-6 primary S values to 1e-12.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))
import common as K  # noqa: E402  (also puts vendor/ on sys.path)
from loguru import logger  # noqa: E402

CONF_ROWS = ["closure", "closure_resT", "closure_persist", "constraint", "cdeg_diag", "xc_excess", "effsize", "wmz",
             "closure_resT_cc", "closure_resT_raw", "d_wmz", "d_closure"]
HOLM_ROWS = ["closure_resT", "closure_persist", "constraint", "closure"]
PRIMARY_CELL = "MAIN|all|E_up|all"


# ----------------------------------------------------------------------------- integrity
def refuse(msg: str) -> None:
    print(f"REFUSED: {msg}", file=sys.stderr)
    sys.exit(2)


def last_logged_hash(name: str = "heldout_spec.json") -> str | None:
    p = K.RES / "freeze_log.jsonl"
    if not p.exists():
        return None
    h = None
    for line in p.read_text().splitlines():
        rec = json.loads(line)
        if rec.get("file") == name:
            h = rec["sha256"]
    return h


def check_integrity(spec_path: Path, expected: str) -> dict:
    if not spec_path.exists():
        refuse(f"spec {spec_path} missing")
    got = K.sha256_file(spec_path)
    logged = last_logged_hash()
    if not (got == expected == logged):
        refuse(f"spec hash mismatch: file {got[:12]}, --expected {expected[:12]}, logged {str(logged)[:12]}")
    sidecar = spec_path.with_suffix(".sha256")
    if sidecar.exists() and sidecar.read_text().strip() != got:
        refuse("heldout_spec.sha256 sidecar differs from the spec file")
    spec = json.loads(spec_path.read_text())
    for rel, h in spec["code_sha256"].items():
        p = ROOT / rel
        if not p.exists() or K.sha256_file(p) != h:
            refuse(f"code file changed or missing: {rel}")
    for rel, h in spec["population_files"].items():
        p = ROOT / rel
        if not p.exists() or K.sha256_file(p) != h:
            refuse(f"population / sealed file changed or missing: {rel}")
    return spec


# ----------------------------------------------------------------------------- shared code path
def vol_from_links(concept_ids: set) -> pd.DataFrame:
    """Yearly all-type c-paper counts from dataset_5 links joined to the works' publication year."""
    links = pd.read_parquet(K.DS5 / "hyd" / "concept_work.parquet", columns=["concept_id", "work_id"])
    links = links[links.concept_id.isin(concept_ids)]
    wids = set(links.work_id)
    yrs = []
    for f in sorted((K.DS5 / "hyd" / "works").glob("works_part_*.parquet")):
        w = pd.read_parquet(f, columns=["work_id", "publication_year"])
        yrs.append(w[w.work_id.isin(wids)])
    yrs = pd.concat(yrs, ignore_index=True)
    cp = links.merge(yrs, on="work_id", how="inner")
    cp["year"] = cp.publication_year.astype(int)
    return cp.groupby(["concept_id", "year"]).size().rename("vol").reset_index()


def label_frame(feat: pd.DataFrame, vol: pd.DataFrame, ids: set) -> pd.DataFrame:
    """Frame for the vendored build_labels: vol from links for 2000-2024; pct / pct_alt / subfield_count from features
    (NaN where the feature frame has no row, e.g. held-out years > 2015; only E_up is used)."""
    grid = pd.MultiIndex.from_product([sorted(ids), range(2000, 2025)], names=["concept_id", "year"]).to_frame(index=False)
    g = grid.merge(vol, on=["concept_id", "year"], how="left").fillna({"vol": 0})
    f = feat[feat.concept_id.isin(ids)][["concept_id", "year", "pct", "pct_alt", "subfield_count"]]
    return g.merge(f, on=["concept_id", "year"], how="left")


def run_fold(feat: pd.DataFrame, pool: pd.DataFrame, vol: pd.DataFrame, B: int, extra: dict | None = None) -> dict:
    """Labels -> MAIN cell -> vendored matching -> event study (event3.es_boot with the Step-6 seeds) + CR1 panel."""
    import analysis_event as AE
    from event3 import DIRECTION, es_boot, na_share_by_k, match_H, panel_frame, seed_for
    from power import cluster_ols
    ids = set(pool.concept_id)
    # label-only relabel: vendored build_labels labels fold == 'screen'; reference concepts keep 'reference'
    lab_pool = pool.assign(fold=np.where(pool.fold == "reference", "reference", "screen"))
    lab, _ = AE.build_labels(label_frame(feat, vol, ids), lab_pool)
    g = AE.assign_groups(lab, "E_up")
    meta = pool.set_index("concept_id")
    g["MAIN"] = g.concept_id.map(meta.MAIN).astype(bool)
    g["route"] = g.concept_id.map(meta.route)
    d = g[g.MAIN]
    per = d.drop_duplicates("concept_id").set_index("concept_id")
    onsets = {c: int(per.loc[c, "onset"]) for c in per.index[per.group == "emerging"]}
    never = set(per.index[per.group == "never"])
    lab_c, feat_m = d.copy(), feat
    if extra is not None:  # pre-declared held-out fallback: add screen never controls
        never |= extra["never"]
        lab_c = pd.concat([lab_c, extra["lab"]], ignore_index=True)
        feat_m = pd.concat([feat, extra["feat"]], ignore_index=True)
    m = AE.match(lab_c, feat_m, treated_onsets=onsets, never_set=never)
    mm = m[m.n_controls > 0]
    rows = {}
    for col in CONF_ROWS:
        M, _ = AE.es_matrix(m, feat_m, col)
        st = es_boot(M, B, seed_for(col, PRIMARY_CELL))
        st["direction"] = DIRECTION.get(col, 0)
        rows[col] = st
    pfr = panel_frame(lab_c[lab_c.concept_id.isin(set(onsets) | never)], feat_m)
    panel = {}
    for col in CONF_ROWS:
        dd = pfr[np.isfinite(pfr[col].astype(float))].reset_index(drop=True)
        if len(dd) < 30 or dd.futE.sum() < 5:
            panel[col] = dict(n=len(dd), coef=np.nan, se=np.nan)
            continue
        years = sorted(dd.year.unique())
        X = np.column_stack([np.ones(len(dd)), dd.futE.values, dd.log_vol3.values, dd.age.values] +
                            [(dd.year == y).astype(float).values for y in years[1:]])
        b, se = cluster_ols(X, dd[col].astype(float).values, pd.factorize(dd.concept_id)[0])
        from scipy.stats import norm
        panel[col] = dict(n=len(dd), n_concepts=int(dd.concept_id.nunique()), coef=b, se=se,
                          p_one_neg=float(norm.cdf(b / se)) if se > 0 else np.nan,
                          p_one_pos=float(norm.sf(b / se)) if se > 0 else np.nan)
    scr = pd.read_parquet(K.RES / "indicators" / "concept_year_indicators_hydrated.parquet", columns=["fold", "year", "H"])
    sdH = float(scr.loc[(scr.fold == "screen") & (scr.year <= 2015), "H"].std())  # SCREEN SD (as Step 6), fixed
    mh = match_H(lab_c, feat_m, onsets, never, K.SPEC3["match_H_sensitivity_caliper_sd"] * sdH)
    Mh, _ = AE.es_matrix(mh, feat_m, "closure_resT")
    hrow = es_boot(Mh, B, seed_for("closure_resT", "Hmatch"))["primary"]
    return dict(n_onsets=len(m), n_matched=int(len(mm)), n_never=len(never), match_rate=float(len(mm) / len(m)) if len(m) else np.nan,
                rows=rows, panel=panel, closure_persist_na=na_share_by_k(m, feat_m, "closure_persist") if len(mm) else None,
                H_matched=dict(n_matched=int((mh.n_controls > 0).sum()), rows=dict(closure_resT=hrow)), matches=m)


def screen_inputs() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Screen + reference concepts (reference needed by the vendored build_labels negative-control block)."""
    feat = pd.read_parquet(K.RES / "indicators" / "concept_year_indicators_hydrated.parquet")
    pool = pd.read_parquet(K.WORK / "pool_active.parquet")
    return feat, pool


# ----------------------------------------------------------------------------- modes
def self_test(B: int) -> dict:
    import config as C
    from labels3 import guard
    guard()  # held-out ids stay sealed during the self-test
    feat, pool = screen_inputs()
    C.assert_not_sealed(pool.concept_id)
    vol = vol_from_links(set(pool.concept_id))
    res = run_fold(feat, pool, vol, B)
    pf = json.loads((K.RES / "event_study" / "primary_family.json").read_text())
    cmp = {}
    ok = res["n_onsets"] == pf["n_onsets"] and res["n_matched"] == pf["n_matched"]
    for col in CONF_ROWS:
        a = res["rows"][col]["primary"]["S"]
        b = pf["rows"][col]["primary"]["S"]
        b = np.nan if b is None else b
        same = (np.isnan(a) and np.isnan(b)) or abs(a - b) <= 1e-12
        ci_same = np.allclose(np.array(res["rows"][col]["primary"]["ci"], float),
                              np.array([np.nan if x is None else x for x in pf["rows"][col]["primary"]["ci"]], float), equal_nan=True)
        cmp[col] = dict(S_selftest=a, S_step6=b, identical=bool(same), ci_identical=bool(ci_same))
        ok &= bool(same)
    out = dict(passed=bool(ok), n_onsets=res["n_onsets"], n_matched=res["n_matched"], rows=cmp,
               panel={c: {k: v for k, v in res["panel"][c].items()} for c in HOLM_ROWS})
    K.write_json(K.RES / "confirm_selftest.json", out)
    logger.info(f"self-test on screen: passed={ok} (onsets {res['n_onsets']}, matched {res['n_matched']})")
    return out


def confirm(spec_path: Path, expected: str) -> dict:
    import lib_metrics as lm
    from seal import load_sealed
    from verdict import decide
    spec = check_integrity(spec_path, expected)
    import config as C
    C.SEALED_IDS.clear()
    os.environ["AII_OPEN_HELDOUT"] = "1"
    feat = load_sealed(K.ROOT / spec["sealed_features"], expected)
    ref_feat, ref_pool = screen_inputs()
    ref_pool = ref_pool[ref_pool.fold == "reference"]
    feat = pd.concat([feat, ref_feat[ref_feat.concept_id.isin(set(ref_pool.concept_id))]], ignore_index=True)
    pool = pd.concat([pd.read_parquet(K.WORK / "pool_heldout.parquet"), ref_pool], ignore_index=True)
    B = spec["bootstrap"]
    vol = vol_from_links(set(pool.concept_id))
    res = run_fold(feat, pool, vol, B)
    fallback = False
    if res["n_matched"] < spec["heldout_fallback_min_matched"]:
        fallback = True
        sfeat, spool = screen_inputs()
        svol = vol_from_links(set(spool.concept_id))
        import analysis_event as AE
        slab, _ = AE.build_labels(label_frame(sfeat, svol, set(spool.concept_id)), spool)
        sg = AE.assign_groups(slab, "E_up")
        sg = sg[sg.concept_id.isin(set(spool.loc[spool.MAIN.astype(bool), "concept_id"]))]
        extra = dict(never=set(sg.loc[sg.group == "never", "concept_id"]), lab=sg, feat=sfeat)
        res = run_fold(feat, pool, vol, B, extra=extra)
    tests = {}
    for col in HOLM_ROWS:
        est = spec["estimator_per_row"].get(col, "event_study")
        direction = spec["directions"][col]
        if est == "event_study":
            st = res["rows"][col]["primary"]
            p1 = st["p_one_neg"] if direction == "negative" else st["p_one_pos"]
            tests[col] = dict(estimator=est, S=st["S"], ci=st["ci"], p_one=p1)
        else:
            pp = res["panel"][col]
            p1 = pp.get("p_one_neg") if direction == "negative" else pp.get("p_one_pos")
            tests[col] = dict(estimator=est, coef=pp.get("coef"), se=pp.get("se"), p_one=p1)
    adj = lm.holm([tests[c]["p_one"] if tests[c]["p_one"] is not None else np.nan for c in HOLM_ROWS])
    for c, a in zip(HOLM_ROWS, adj):
        tests[c]["p_one_holm"] = a
        tests[c]["decision"] = "CONFIRMED" if (a is not None and np.isfinite(a) and a < 0.05) else "DEAD"
    pf_like = dict(rows=res["rows"], closure_persist_na=res["closure_persist_na"] or dict(n_treated_with_finite_in_window=0,
                   window_na_gap_points=np.nan), H_matched=res["H_matched"], n_matched=res["n_matched"],
                   n_onsets=res["n_onsets"], family={})
    v = decide(pf_like, pd.DataFrame(columns=["cell", "indicator"]))
    out = dict(spec_sha256=expected, fallback_screen_controls=fallback, n_onsets=res["n_onsets"], n_matched=res["n_matched"],
               tests=tests, verdict_rule_on_heldout=v["verdict"], verdict_detail=v,
               rows={c: res["rows"][c]["primary"] for c in CONF_ROWS}, panel=res["panel"],
               note="one run only; no subgroup search (spec decision rules)")
    outd = K.ROOT / "results_heldout"
    outd.mkdir(exist_ok=True)
    K.write_json(outd / "verdict_heldout.json", out)
    logger.info(f"held-out verdict {v['verdict']}; tests { {c: t['decision'] for c, t in tests.items()} }")
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--spec", default="heldout_spec.json")
    ap.add_argument("--expected-sha256", default=None)
    ap.add_argument("--self-test-on-screen", action="store_true")
    ap.add_argument("--B", type=int, default=K.SPEC3["bootstrap"])
    a = ap.parse_args()
    K.setup_logging("confirm_heldout")
    if a.self_test_on_screen:
        r = self_test(a.B)
        sys.exit(0 if r["passed"] else 1)
    if not a.expected_sha256:
        refuse("--expected-sha256 is required")
    confirm(ROOT / a.spec, a.expected_sha256)


if __name__ == "__main__":
    main()
