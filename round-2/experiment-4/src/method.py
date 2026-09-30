#!/usr/bin/env python3
"""RQ1 replication on the 191 held-out MeSH concepts: do network precursors of emergence replicate in biomedicine?

Stages (run in order; `--stage all` runs everything):
  snapshots  STEP 0-2  spec freeze, load, yearly whole-science co-occurrence snapshots + focal attachment
  features   STEP 3    concept-year indicators; features.parquet is hashed into prereg_spec.json (FREEZE)
  outcomes   STEP 4-9  labels, matching, event study, rolling-origin prediction, patterns, outputs
The outcomes stage refuses to run unless features.parquet exists and its sha256 is in prereg_spec.json.
"""

from __future__ import annotations

import argparse
import glob
import os
import json
import resource
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from loguru import logger

import analysis as A
import features as FT
import load
import rq1_spec as S

ROOT = Path(__file__).resolve().parent
RES = ROOT / "results"
FIG = ROOT / "figures"
PREREG = RES / "prereg_spec.json"
FEAT = RES / "features.parquet"
# sibling main-pool RQ1 artifact (gen_art_experiment_3); override with AII_MAINPOOL_DIR
MAINPOOL_DIR = Path(os.environ.get("AII_MAINPOOL_DIR", str(ROOT.parent / "experiment-3/src")))

logger.remove()
logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
logger.add(str(ROOT / "logs" / "run.log"), rotation="30 MB", level="DEBUG")


def _jsonable(o):
    if isinstance(o, dict):
        return {str(k): _jsonable(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_jsonable(v) for v in o]
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating, float)):
        return None if not np.isfinite(o) else float(o)
    if isinstance(o, np.bool_):
        return bool(o)
    return o


def write_json(p: Path, obj) -> None:
    p.write_text(json.dumps(_jsonable(obj), indent=1))


# ------------------------------------------------------------------ STEP 0
def find_main_pool() -> dict:
    """Look for a sibling main-pool RQ1 spec/feature module or results mentioning RQ1."""
    base = ROOT.parent
    hits = []
    for d in sorted(base.glob("*/")):
        if d.resolve() == ROOT:
            continue
        for pat in ("rq1_spec.py", "rq1_features.py", "*/rq1_spec.py", "*/rq1_features.py"):  # depth <= 1
            for f in d.glob(pat):
                if ".venv" not in str(f):
                    hits.append({"path": str(f.relative_to(base)), "sha256": load.sha256_file(f), "kind": "spec_module"})
        for name in ("README.md", "method_out.json", "full_method_out.json"):
            f = d / name
            if f.exists() and f.stat().st_size < 50_000_000 and "RQ1" in f.read_text(errors="ignore"):
                hits.append({"path": str(f.relative_to(base)), "sha256": load.sha256_file(f), "kind": "mentions_RQ1"})
    return {"searched": "iter_2/gen_art/*/", "at": datetime.now(timezone.utc).isoformat(), "hits": hits,
            "spec_module_found": any(h["kind"] == "spec_module" for h in hits)}


def spec_freeze() -> dict:
    spec = {k: getattr(S, k) for k in dir(S) if k.isupper()}
    pre = json.loads(PREREG.read_text()) if PREREG.exists() else {}
    h = load.sha256_file(ROOT / "rq1_spec.py")
    hist = pre.get("spec_sha256_history", [])
    if not hist or hist[-1]["sha256"] != h:
        hist.append({"sha256": h, "at": datetime.now(timezone.utc).isoformat()})
    pre.update({"population": S.POPULATION, "spec_file": "rq1_spec.py", "spec_sha256": h, "spec_sha256_history": hist,
                "spec_frozen_at": pre.get("spec_frozen_at") or datetime.now(timezone.utc).isoformat(),
                "constants": spec, "main_pool_search_start": pre.get("main_pool_search_start") or find_main_pool()})
    mp = MAINPOOL_DIR
    srcs = {f: load.sha256_file(mp / f) for f in ("spec.json", "lib_metrics.py", "stage_snapshots.py", "stage_indicators.py",
                                                  "analysis_event.py", "results_summary.json") if (mp / f).exists()}
    pre["main_pool_alignment"] = {
        "found": bool(srcs), "path": "round-2/experiment-4/src/../gen_art_experiment_3", "sha256": srcs,
        "vendored": {"vendor/mainpool_lib_metrics.py": load.sha256_file(ROOT / "vendor" / "mainpool_lib_metrics.py")}
        if (ROOT / "vendor" / "mainpool_lib_metrics.py").exists() else {},
        "note": ("The main-pool RQ1 run (not a rq1_spec.py module, but spec.json + config.py) was found during the "
                 "run, after this artifact's snapshots were built with the plan's spec. Its constants agree with "
                 "the plan on window, tag filter, Leiden, top-20 closure, rewiring reps, betweenness pivots, E "
                 "thresholds, ages, t_max, matching calipers and Kleinberg; its precursor operationalisations "
                 "(rarefied 3-year-slope accretion shift, weighted Chung-Lu closure, rarefied P), label variants "
                 "(E, E_alt, E_up) and event-study convention (rel -5..0, summary -3..0, never-emerging controls, "
                 "vol3 caliper) were added as a SECOND, aligned block (rq1_spec.MAINPOOL) before any outcome of this "
                 "population was computed. The plan-native block is reported unchanged."),
        "differences": {"leiden_n_iterations": "main pool: leidenalg default (n_iterations not set = 2); here 2 (declared)",
                        "kept_edges": "main pool: >= 2 RAW sample co-occurrences; here weighted W_ij >= 2 (plan text)",
                        "closure_neighbours": "main pool: all frame-type co-tags; aligned block uses the same",
                        "percentile_strength": "main pool: all frame tags; plan block: co-tags with W_cj >= 2",
                        "rewire_snapshots": "main pool: 2008/2013/2018 only; here 10% of all concept-years",
                        "bootstrap": "main pool 1000; here 2000",
                        "onset_window": "main pool: 2008-2015 (sealed 2016-18); here age 3..8 and t <= 2019 (no sealing)"}}
    write_json(PREREG, pre)
    return pre


# ------------------------------------------------------------------ STEP 1-2
def stage_snapshots(mini: bool, workers: int) -> None:
    import snapshots
    spec_freeze()
    info = snapshots.prepare(mini)
    write_json(RES / "load_checks.json", info)
    c = pd.read_parquet(load.INTER / "concepts.parquet")
    if mini:
        early = c.sort_values(["F", "concept_id"]).concept_id.head(5).tolist()
        rest = c[~c.concept_id.isin(early)].sample(5, random_state=S.SEED).concept_id.tolist()
        ids, years = early + rest, list(range(2008, 2013))
    else:
        ids, years = c.concept_id.tolist(), S.YEARS
    write_json(RES / "snapshot_scope.json", {"mini": mini, "concepts": ids, "years": years})
    snapshots.run_snapshots(ids, years, workers)


# ------------------------------------------------------------------ STEP 3
def stage_features() -> None:
    spec_freeze()  # re-hash: the main-pool alignment block was added to rq1_spec.py before any outcome was opened
    scope = json.loads((RES / "snapshot_scope.json").read_text())
    feat = FT.build_features(scope["concepts"], scope["years"])
    feat.to_parquet(FEAT)
    write_json(RES / "indicator_columns.json", FT.indicator_columns())
    # T6 sanity: centrality percentile tracks volume
    net = feat[feat.k > 0]
    r = float(np.corrcoef(net.wdeg_pctl, np.log1p(net.W_c))[0, 1]) if len(net) > 2 else np.nan
    r_f = float(np.corrcoef(net.wdeg_pctl_focal, np.log1p(net.W_c))[0, 1]) if len(net) > 2 else np.nan
    # low-confidence-topic sensitivity snapshot
    sens = {}
    for f in sorted((RES / "snapshots").glob("focal_*_nolowconf.parquet")):
        y = int(f.stem.split("_")[1])
        a = pd.read_parquet(RES / "snapshots" / f"focal_{y}.parquet").set_index("concept_id")
        b = pd.read_parquet(f).set_index("concept_id")
        j = a.join(b, rsuffix="_nl", how="inner")
        sens[str(y)] = {c: float(j[[c, c + "_nl"]].corr(method="spearman").iloc[0, 1])
                        for c in ("wdeg_pctl", "closure_lr", "P", "z_within", "betw") if j[c].notna().sum() > 3}
    pre = json.loads(PREREG.read_text())
    pre.update({"features_file": "results/features.parquet", "features_sha256": load.sha256_file(FEAT),
                "features_frozen_at": datetime.now(timezone.utc).isoformat(),
                "features_rows": int(len(feat)), "features_scope_mini": scope["mini"],
                "T6_corr_wdeg_pctl_logW": r, "T6_corr_wdeg_pctl_focal_logW": r_f,
                "wdeg_pctl_allnodes_distribution_focal": {q: float(net.wdeg_pctl.quantile(q)) for q in (0.5, 0.9, 0.99, 1.0)}, "lowconf_sensitivity_spearman": sens})
    write_json(PREREG, pre)
    logger.info(f"FEATURES FROZEN sha256={pre['features_sha256'][:16]}... T6 corr(pctl, log W_c)={r:.3f}; "
                f"low-conf sensitivity {sens}")


# ------------------------------------------------------------------ STEP 4-9
def assert_frozen() -> None:
    if not FEAT.exists() or not PREREG.exists():
        raise RuntimeError("features.parquet / prereg_spec.json missing: run --stage features first")
    pre = json.loads(PREREG.read_text())
    if pre.get("features_sha256") != load.sha256_file(FEAT):
        raise RuntimeError("features.parquet sha256 does not match prereg_spec.json (features changed after freeze)")
    if pre.get("spec_sha256") != load.sha256_file(ROOT / "rq1_spec.py"):
        raise RuntimeError("rq1_spec.py changed after the spec freeze")


def run_event_studies(feat, lab, concepts, rng, variants) -> tuple[pd.DataFrame, dict]:
    cols = FT.indicator_columns()
    fidx = feat.set_index(["concept_id", "year"])
    unit_mask = (feat.age >= S.AGE_RANGE[0]) & (feat.age <= S.AGE_RANGE[1]) & (feat.year <= S.T_MAX)
    rows, match_info = [], {}
    for v in variants:
        sets, info = v["sets"], v["match_info"]
        match_info[v["key"]] = info
        prec_p = {}
        for ind, vers in cols.items():
            for ver, col in vers.items():
                if col not in feat.columns:
                    continue
                sd_ref = float(feat.loc[unit_mask, col].std())
                mats = A.set_matrices(sets, fidx, col)
                is_primary = ind in S.PRECURSORS and ver == "raw"
                es = A.event_study(mats, rng, sd_ref, do_mde=(is_primary or v["key"] == "PRIMARY|all"))
                base = {"population": S.POPULATION, "volume_def": v["volume_def"], "subset": v["subset"],
                        "outcome": v["outcome"], "indicator": ind, "version": ver, "column": col,
                        "n_emerging": es["n_sets"], "n_controls": es["n_controls"], "n_eff_window": es["n_eff"],
                        "precursor": ind in S.PRECURSORS}
                for j, k in enumerate(S.EVENT_REL):
                    rows.append({**base, "rel_year": str(k), "diff": es["d_k"][j], "ci_lo": es["ci_k"][j][0],
                                 "ci_hi": es["ci_k"][j][1], "p_boot": es["p_boot_k"][j], "p_holm": np.nan,
                                 "n_at_rel": es["n_at_rel"][j], "diff_sd": es["d_k"][j] / sd_ref if sd_ref > 0 else np.nan,
                                 "mde_sd": np.nan, "se": np.nan})
                rows.append({**base, "rel_year": "D_-3_-1", "diff": es["D"], "ci_lo": es["ci_D"][0], "ci_hi": es["ci_D"][1],
                             "p_boot": es["p_boot"], "p_holm": np.nan, "n_at_rel": int(np.sum(es["n_at_rel"][2:])),
                             "diff_sd": es["D_sd"], "mde_sd": es["mde_sd"], "se": es["se_D"]})
                if is_primary:
                    prec_p[ind] = (len(rows) - 1, es["p_boot"])
        adj = A.holm([p for _, p in prec_p.values()])
        for (ri, _), pa in zip(prec_p.values(), adj):
            rows[ri]["p_holm"] = pa
        logger.info(f"event study {v['key']}: n_emerging={info['n_emerging']} match3@20={info['match_rate_3_at_20pct']} "
                    + "; ".join(f"{k}: D={rows[i]['diff']:.3g} [{rows[i]['ci_lo']:.3g},{rows[i]['ci_hi']:.3g}] "
                                f"p_holm={rows[i]['p_holm']:.3g}" for k, (i, _) in prec_p.items()
                                if rows[i]['diff'] is not None and np.isfinite(rows[i]['diff'])))
    eff = pd.DataFrame(rows)
    # BH over all D rows (raw/pp/volres) within each analysis variant (secondary indicators)
    eff["q_bh_all_indicators"] = np.nan
    for key, g in eff[eff.rel_year == "D_-3_-1"].groupby(["volume_def", "subset", "outcome"]):
        eff.loc[g.index, "q_bh_all_indicators"] = A.bh(g.p_boot.tolist())
    return eff, match_info


def null_check_event(feat, lab, concepts, onset, rng) -> dict:
    """T5: permute onsets across concepts within F-band; D_p must centre on 0."""
    fidx = feat.set_index(["concept_id", "year"])
    cm = concepts.set_index("concept_id")
    ids = concepts.concept_id.tolist()
    vals = {p: [] for p in S.PRECURSORS}
    for b in range(S.NULL_PERMS):
        perm_onset = {}
        for band, g in concepts.groupby("F_band"):
            o = [onset.get(c) for c in g.concept_id]
            sh = rng.permutation(len(o))
            for c, j in zip(g.concept_id, sh):
                if o[j] is not None:
                    perm_onset[c] = o[j]
        sets, _ = A.match_controls(lab, concepts, perm_onset, "PRIMARY", "E_PRIMARY", check_label=False)
        for p in S.PRECURSORS:
            mats = A.set_matrices(sets, fidx, p)
            w_idx = [S.EVENT_REL.index(k) for k in S.PRIMARY_EVENT_WINDOW]
            vals[p].append(A._summ(A._diffs(mats), w_idx)[1] if mats else np.nan)
    out = {}
    for p, v in vals.items():
        v = np.array(v, dtype=float)
        v = v[np.isfinite(v)]
        out[p] = {"mean_perm_D": float(v.mean()) if len(v) else None, "sd_perm_D": float(v.std()) if len(v) else None,
                  "n_perms": int(len(v))}
    _ = ids, cm
    return out


def prediction(feat, lab, concepts, rng) -> tuple[pd.DataFrame, dict, dict]:
    units_all = lab[lab.in_age_range].merge(feat.rename(columns={"year": "t"}), on=["concept_id", "t", "F", "age"], how="left")
    rows, meta, preds_store = [], {}, {}
    all_cols = A.ALL_NET
    for vd in ["PRIMARY", "SENS1", "SENS2"]:
        u = units_all if vd != "SENS2" else units_all[units_all.sens2_valid]
        fsets = A.feature_sets(vd, all_cols)
        outs = [f"E_{vd}", "E_cent", f"E_vol_{vd}"] + (["E_allnode_PRIMARY"] if vd == "PRIMARY" else [])
        for outcome in outs:
            if vd != "PRIMARY" and outcome == "E_cent":
                continue  # identical to PRIMARY's E_cent (network-only)
            for ev in ["rolling_origin", "grouped_cv"]:
                if ev == "rolling_origin":
                    P, info = A.rolling_origin(u, fsets, outcome)
                    meta[f"{vd}|{outcome}|{ev}"] = info
                    n_orig = len(info["origins_used"])
                else:
                    P = A.grouped_cv(u, fsets, outcome)
                    n_orig = S.GROUPED_CV_FOLDS
                preds_store[(vd, outcome, ev)] = P
                n_units = int(len(P))
                n_pos = int(P[outcome].sum()) if len(P) else 0
                for fs in fsets:
                    if fs == "A":
                        continue
                    r = A.auc_boot(P, outcome, "A", fs, rng) if len(P) else {}
                    rows.append({"population": S.POPULATION, "volume_def": vd, "outcome": outcome, "evaluation": ev,
                                 "feature_set": fs, "baseline": "A",
                                 "auc": r.get("auc_b", np.nan), "auc_ci_lo": r.get("auc_b_lo", np.nan),
                                 "auc_ci_hi": r.get("auc_b_hi", np.nan), "auc_baseline": r.get("auc_a", np.nan),
                                 "auc_baseline_ci_lo": r.get("auc_a_lo", np.nan), "auc_baseline_ci_hi": r.get("auc_a_hi", np.nan),
                                 "delta_auc": r.get("delta", np.nan), "delta_ci_lo": r.get("delta_lo", np.nan),
                                 "delta_ci_hi": r.get("delta_hi", np.nan), "p_delta_le0": r.get("p_delta_le0", np.nan),
                                 "prauc": r.get("prauc_b", np.nan), "prauc_baseline": r.get("prauc_a", np.nan),
                                 "n_units": n_units, "n_pos": n_pos, "origins_used": n_orig})
                if len(P):
                    s = A.auc_single(P, outcome, "A", rng)
                    rows.append({"population": S.POPULATION, "volume_def": vd, "outcome": outcome, "evaluation": ev,
                                 "feature_set": "A", "baseline": "-", "auc": s["auc"], "auc_ci_lo": s["lo"],
                                 "auc_ci_hi": s["hi"], "prauc": s["prauc"], "n_units": n_units, "n_pos": n_pos,
                                 "origins_used": n_orig})
                    # per-origin AUCs
                    if ev == "rolling_origin":
                        for T, g in P.groupby("origin"):
                            if g[outcome].nunique() == 2:
                                rows.append({"population": S.POPULATION, "volume_def": vd, "outcome": outcome,
                                             "evaluation": f"origin_{T}", "feature_set": "B", "baseline": "A",
                                             "auc": A._auc(g[outcome].to_numpy(), g["p_B"].to_numpy()),
                                             "auc_baseline": A._auc(g[outcome].to_numpy(), g["p_A"].to_numpy()),
                                             "n_units": int(len(g)), "n_pos": int(g[outcome].sum()), "origins_used": 1})
                logger.info(f"prediction {vd} {outcome} {ev}: units={n_units} pos={n_pos} origins={n_orig}")
    pred = pd.DataFrame(rows)
    pred["delta_auc"] = pred.get("delta_auc")
    pred["delta_auc"] = pred.delta_auc.where(pred.delta_auc.notna(),
                                             pred.auc - pred.auc_baseline if "auc_baseline" in pred else np.nan)
    # leaky-feature sanity (T3) and label-permutation null (T5) on grouped CV, PRIMARY
    u = units_all.copy()
    lead = feat[["concept_id", "year", "wdeg_pctl_focal"]].copy()
    lead["year"] = lead.year - S.HORIZON
    u = u.merge(lead.rename(columns={"year": "t", "wdeg_pctl_focal": "LEAKY_wdeg_pctl_t_plus_5"}), on=["concept_id", "t"], how="left")
    fs = A.feature_sets("PRIMARY", all_cols)
    leaky = {"B": fs["B"], "B_plus_leaky": fs["B"] + ["LEAKY_wdeg_pctl_t_plus_5"], "A": fs["A"]}
    checks = {}
    for outc in ["E_PRIMARY", "E_cent"]:
        P = A.grouped_cv(u, leaky, outc)
        checks[f"leaky_{outc}"] = {"auc_B": A._auc(P[outc].to_numpy(), P.p_B.to_numpy()),
                                   "auc_B_plus_leaky": A._auc(P[outc].to_numpy(), P.p_B_plus_leaky.to_numpy()),
                                   "note": "the leaky feature was used only here and removed afterwards"}
    nulls = []
    for b in range(5):
        up = units_all.copy()
        up["E_perm"] = up.groupby(up.F.map(load.f_band)).E_PRIMARY.transform(lambda s: rng.permutation(s.to_numpy()))
        P = A.grouped_cv(up, {"A": fs["A"], "B": fs["B"]}, "E_perm")
        nulls.append(A._auc(P.E_perm.to_numpy(), P.p_B.to_numpy()) - A._auc(P.E_perm.to_numpy(), P.p_A.to_numpy()))
    checks["label_permutation_delta_auc"] = {"deltas": nulls, "mean": float(np.nanmean(nulls))}
    checks["transfer_test"] = "not run: no main-pool RQ1 model file existed under iter_2/gen_art at run time"
    return pred, {"rolling": meta, "checks": checks}, preds_store


def mainpool_block(feat, lab, concepts, rng) -> tuple[list[dict], dict]:
    """Event study with the main pool's labels, controls, window and precursors (Holm over the 3 primaries)."""
    labm = A.mainpool_labels(lab)
    labm.to_parquet(RES / "labels_mainpool_aligned.parquet")
    unit = (feat.age >= S.AGE_RANGE[0]) & (feat.age <= S.AGE_RANGE[1]) & (feat.year <= S.T_MAX)
    rows, info = [], {}
    fam = S.MAINPOOL["families"]
    for lname, col in (("E", "MP_E"), ("E_alt", "MP_E_alt"), ("E_up", "MP_E_up")):
        onset, never = A.mainpool_groups(labm, col)
        m = A.mainpool_match(onset, never, concepts, feat)
        info[lname] = {"n_treated": len(m), "n_matched": int(sum(r["n_controls"] > 0 for r in m)),
                       "n_never": len(never), "widened_share": float(np.mean([r["widened"] for r in m if r["n_controls"]]))
                       if any(r["n_controls"] for r in m) else None,
                       "mean_controls": float(np.mean([r["n_controls"] for r in m if r["n_controls"]]))
                       if any(r["n_controls"] for r in m) else None,
                       "onset_year_counts": pd.Series(list(onset.values())).value_counts().sort_index().to_dict() if onset else {},
                       "matches": m}
        prim = []
        cols = [(f, v, c) for f, cs in fam.items() for v, c in zip(("primary", "raw", "res"), cs)]
        cols += [("exploratory", "-", c) for c in S.MAINPOOL["exploratory"]]
        for family, ver, c in cols:
            if c not in feat.columns:
                continue
            idx = {(a, int(y)): float(v) for a, y, v in zip(feat.concept_id, feat.year, feat[c].astype(float))}
            sd = float(feat.loc[unit, c].astype(float).std())
            st = A.mainpool_es(m, idx, c, rng, sd)
            row = {"population": S.POPULATION, "label": lname, "family": family, "version": ver, "indicator": c,
                   "S": st["S"], "ci_lo": st["ci"][0], "ci_hi": st["ci"][1], "p": st["p"], "p_holm": np.nan,
                   "q_bh": np.nan, "se": st["se"], "mde": st["mde"], "mde_in_sd": st["mde_in_sd"],
                   "S_in_sd": st["S"] / sd if sd and np.isfinite(st["S"]) else np.nan, "pooled_sd": sd,
                   "n_treated": st["n_treated"], "n_eff_window": st["n_eff"], "n_controls": st["n_controls"],
                   **{f"diff_k{k}": d for k, d in zip(S.MAINPOOL["es_rel_years"], st["diff_k"])},
                   **{f"n_k{k}": n for k, n in zip(S.MAINPOOL["es_rel_years"], st["n_k"])},
                   **{f"ci_k{k}": json.dumps([None if not np.isfinite(x) else float(x) for x in ci])
                      for k, ci in zip(S.MAINPOOL["es_rel_years"], st["ci_k"])}}
            rows.append(row)
            if ver == "primary":
                prim.append(len(rows) - 1)
        for i, a in zip(prim, A.holm([rows[i]["p"] for i in prim])):
            rows[i]["p_holm"] = a
            rows[i]["sign_as_predicted"] = bool(np.isfinite(rows[i]["S"]) and rows[i]["S"] > 0)
        ex = [i for i, r in enumerate(rows) if r["label"] == lname and r["family"] == "exploratory"]
        for i, q in zip(ex, A.bh([rows[i]["p"] if rows[i]["n_treated"] >= 10 else np.nan for i in ex])):
            rows[i]["q_bh"] = q
        logger.info(f"main-pool-aligned {lname}: treated {len(m)}, matched {info[lname]['n_matched']}; " + "; ".join(
            f"{rows[i]['indicator']} S={rows[i]['S']:.3g} [{rows[i]['ci_lo']:.3g},{rows[i]['ci_hi']:.3g}] "
            f"p_holm={rows[i]['p_holm']:.3g}" for i in prim if np.isfinite(rows[i]["S"])))
    return rows, info


def side_by_side(mp_tab: pd.DataFrame) -> pd.DataFrame:
    """Join with the main pool's event_study_table on (label, indicator); sign agreement and CI status."""
    f = MAINPOOL_DIR / "results_summary.json"
    main = []
    if f.exists():
        est = json.loads(f.read_text()).get("event_study_table", {})
        for lname, rows in est.items():
            for r in rows:
                main.append({"label": lname, "indicator": r.get("indicator"), "version": r.get("version"),
                             "S_main": r.get("S"), "ci_lo_main": (r.get("ci") or [None, None])[0],
                             "ci_hi_main": (r.get("ci") or [None, None])[1], "p_main": r.get("p"),
                             "p_holm_main": r.get("p_holm"), "q_bh_main": r.get("q_bh"),
                             "mde_in_sd_main": r.get("mde_in_sd"), "n_treated_main": r.get("n_treated")})
    main = pd.DataFrame(main)
    me = mp_tab.rename(columns={"S": "S_mesh", "ci_lo": "ci_lo_mesh", "ci_hi": "ci_hi_mesh", "p": "p_mesh",
                                "p_holm": "p_holm_mesh", "q_bh": "q_bh_mesh", "mde_in_sd": "mde_in_sd_mesh",
                                "n_treated": "n_treated_mesh"})
    keep = ["label", "family", "version", "indicator", "S_mesh", "ci_lo_mesh", "ci_hi_mesh", "p_mesh", "p_holm_mesh",
            "q_bh_mesh", "mde_in_sd_mesh", "n_treated_mesh", "n_eff_window", "S_in_sd"]
    out = me[keep]
    if len(main):
        out = out.merge(main.drop(columns=["version"]), on=["label", "indicator"], how="left")
        sgn = lambda x: np.sign(x) if x is not None and np.isfinite(x) else np.nan  # noqa: E731
        out["sign_agree"] = [(sgn(a) == sgn(b)) if np.isfinite(sgn(a)) and np.isfinite(sgn(b)) else np.nan
                             for a, b in zip(out.S_mesh, out.S_main.astype(float))]
        ex = lambda lo, hi: bool(np.isfinite(lo) and np.isfinite(hi) and (lo > 0 or hi < 0))  # noqa: E731
        out["ci_excl0_mesh"] = [ex(a, b) for a, b in zip(out.ci_lo_mesh, out.ci_hi_mesh)]
        out["ci_excl0_main"] = [ex(float(a) if a is not None else np.nan, float(b) if b is not None else np.nan)
                                for a, b in zip(out.ci_lo_main, out.ci_hi_main)]
        # inverse-variance pooled estimate from the two independent populations (bootstrap SEs from CI widths)
        se_m = (out.ci_hi_mesh - out.ci_lo_mesh) / (2 * 1.96)
        se_p = (out.ci_hi_main.astype(float) - out.ci_lo_main.astype(float)) / (2 * 1.96)
        w1, w2 = 1 / se_m ** 2, 1 / se_p ** 2
        out["S_pooled_ivw"] = (w1 * out.S_mesh + w2 * out.S_main.astype(float)) / (w1 + w2)
        out["se_pooled_ivw"] = np.sqrt(1 / (w1 + w2))
        out["Q_heterogeneity"] = w1 * (out.S_mesh - out.S_pooled_ivw) ** 2 + w2 * (out.S_main.astype(float) - out.S_pooled_ivw) ** 2
    return out


def mainpool_verdict(side: pd.DataFrame, mp_info: dict) -> dict:
    out = {"main_pool_results_file": "gen_art_experiment_3/results_summary.json (event_study_table)",
           "n_treated": {k: v["n_treated"] for k, v in mp_info.items()},
           "n_matched": {k: v["n_matched"] for k, v in mp_info.items()}, "precursors": {}}
    for lname in ("E", "E_alt", "E_up"):
        for p in S.MAINPOOL["precursors"]:
            r = side[(side.label == lname) & (side.indicator == p)]
            if r.empty:
                continue
            r = r.iloc[0]
            rec = {k: (None if (isinstance(v, float) and not np.isfinite(v)) else v) for k, v in r.items()
                   if k in ("S_mesh", "ci_lo_mesh", "ci_hi_mesh", "p_holm_mesh", "mde_in_sd_mesh", "n_treated_mesh",
                            "n_eff_window", "S_main", "ci_lo_main", "ci_hi_main", "p_holm_main", "n_treated_main", "sign_agree",
                            "ci_excl0_mesh", "ci_excl0_main", "S_pooled_ivw", "se_pooled_ivw", "Q_heterogeneity")}
            n = int(r.n_eff_window) if np.isfinite(r.n_eff_window) else 0
            nm = r.n_treated_main if r.n_treated_main == r.n_treated_main else None
            if n < 15:
                rec["verdict"] = (f"UNDERPOWERED in MeSH (effective n={n} treated with data in rel -3..0, < 15): "
                                  "no sign conclusion (F5)")
            else:
                ph_me = rec.get("p_holm_mesh")
                ph_ma = rec.get("p_holm_main")
                sig_me = bool(rec.get("ci_excl0_mesh")) and ph_me is not None and ph_me < 0.05
                sig_ma = bool(rec.get("ci_excl0_main")) and ph_ma is not None and float(ph_ma) < 0.05
                agree = rec.get("sign_agree")
                if sig_me and sig_ma and agree:
                    rec["verdict"] = "REPLICATED: same sign, significant (CI excludes 0, Holm p < 0.05) in both"
                elif sig_me and sig_ma and agree is False:
                    rec["verdict"] = "CONTRADICTED: significant with opposite signs"
                elif sig_ma and not sig_me:
                    rec["verdict"] = ("SAME SIGN, NOT SIGNIFICANT in MeSH" if agree else
                                      "NOT REPLICATED: main-pool effect absent (opposite-sign point estimate) in MeSH")
                elif sig_me and not sig_ma:
                    rec["verdict"] = "SIGNAL IN MeSH ONLY (main pool not significant)"
                else:
                    rec["verdict"] = ("NULL IN BOTH after Holm (" + ("MeSH CI excludes 0 but Holm p >= 0.05"
                                      if rec.get("ci_excl0_mesh") else "MeSH CI includes 0") + ")")
            if nm is not None and nm < 15:
                rec["verdict"] += f"; main pool also underpowered (n_treated={int(nm)})"
            out["precursors"][f"{lname}|{p}"] = rec
    return out


def figures(eff: pd.DataFrame, pred: pd.DataFrame, pat_tab: pd.DataFrame) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    FIG.mkdir(exist_ok=True)
    # event study panel
    fig, axes = plt.subplots(1, 3, figsize=(13, 3.8), sharex=True)
    colors = {"PRIMARY": "#1f4e79", "SENS1": "#c55a11", "SENS2": "#548235"}
    for ax, p in zip(axes, S.PRECURSORS):
        for i, vd in enumerate(["PRIMARY", "SENS1", "SENS2"]):
            g = eff[(eff.indicator == p) & (eff.version == "raw") & (eff.volume_def == vd) & (eff.subset == "all")
                    & (eff.outcome == "E") & (eff.rel_year != "D_-3_-1")]
            if g.empty:
                continue
            x = g.rel_year.astype(int).to_numpy() + (i - 1) * 0.12
            y = g["diff"].to_numpy(dtype=float)
            ax.errorbar(x, y, yerr=[y - g.ci_lo.to_numpy(dtype=float), g.ci_hi.to_numpy(dtype=float) - y], fmt="o-",
                        color=colors[vd], capsize=3, lw=1.2, ms=4, label=f"{vd} (n={int(g.n_emerging.iloc[0])})")
        ax.axhline(0, color="grey", lw=0.8)
        ax.set_title(p)
        ax.set_xlabel("event time (0 = first W2 year)")
    axes[0].set_ylabel("emerging - matched controls")
    axes[0].legend(fontsize=7, frameon=False)
    fig.suptitle("Held-out MeSH population: precursor event study (95% concept-bootstrap CIs)", fontsize=10)
    fig.tight_layout()
    fig.savefig(FIG / "event_study_precursors.png", dpi=180)
    fig.savefig(FIG / "event_study_precursors.pdf")
    plt.close(fig)
    # side-by-side main pool vs MeSH (aligned block)
    sbs = RES / "side_by_side_mainpool_vs_mesh.csv"
    if sbs.exists():
        sd_ = pd.read_csv(sbs)
        sd_ = sd_[sd_.version == "primary"]
        if len(sd_):
            fig, axes = plt.subplots(1, 3, figsize=(13, 3.6))
            for ax, p in zip(axes, S.MAINPOOL["precursors"]):
                g = sd_[sd_.indicator == p].set_index("label").reindex(["E", "E_alt", "E_up"])
                yy = np.arange(3)
                for off, pre, colr, nm in ((-0.12, "main", "#c55a11", "main pool"), (0.12, "mesh", "#1f4e79", "MeSH held-out")):
                    if f"S_{pre}" not in g:
                        continue
                    x = g[f"S_{pre}"].astype(float).to_numpy()
                    lo = g[f"ci_lo_{pre}"].astype(float).to_numpy()
                    hi = g[f"ci_hi_{pre}"].astype(float).to_numpy()
                    n = g[f"n_treated_{pre}"].to_numpy()
                    ax.errorbar(x, yy + off, xerr=[x - lo, hi - x], fmt="o", color=colr, capsize=3, label=nm)
                    for xi, yi, ni in zip(x, yy + off, n):
                        if np.isfinite(xi):
                            ax.annotate(f"n={int(ni) if ni == ni else 0}", (xi, yi), fontsize=6, xytext=(3, 3),
                                        textcoords="offset points")
                ax.axvline(0, color="grey", lw=0.8)
                ax.set_yticks(yy)
                ax.set_yticklabels(["E", "E_alt", "E_up"])
                ax.set_title(p)
                ax.set_xlabel("S (treated - matched controls, rel -3..0)")
            axes[0].legend(fontsize=7, frameon=False)
            fig.suptitle("Main-pool-aligned precursors: main pool vs held-out MeSH population (95% CIs)", fontsize=10)
            fig.tight_layout()
            fig.savefig(FIG / "side_by_side_mainpool_vs_mesh.png", dpi=180)
            fig.savefig(FIG / "side_by_side_mainpool_vs_mesh.pdf")
            plt.close(fig)
    # delta-AUC forest
    g = pred[(pred.feature_set == "B") & pred.evaluation.isin(["rolling_origin", "grouped_cv"])].copy()
    g = g[g.delta_auc.notna()]
    if len(g):
        fig, ax = plt.subplots(figsize=(7, 0.35 * len(g) + 1.2))
        lab_ = [f"{r.volume_def} | {r.outcome} | {r.evaluation} (pos={r.n_pos})" for r in g.itertuples()]
        yy = np.arange(len(g))[::-1]
        ax.errorbar(g.delta_auc, yy, xerr=[g.delta_auc - g.delta_ci_lo, g.delta_ci_hi - g.delta_auc], fmt="o",
                    color="#1f4e79", capsize=3)
        ax.axvline(0, color="grey", lw=0.8)
        ax.set_yticks(yy)
        ax.set_yticklabels(lab_, fontsize=7)
        ax.set_xlabel("delta AUC (B = A + 3 precursors) - (A = frequency/burst + degree/centrality)")
        fig.tight_layout()
        fig.savefig(FIG / "delta_auc_forest.png", dpi=180)
        fig.savefig(FIG / "delta_auc_forest.pdf")
        plt.close(fig)
    # pattern bars
    if len(pat_tab):
        pt = pat_tab[pat_tab.group.isin(["all", "emerging_PRIMARY", "non_emerging_PRIMARY"])]
        fig, ax = plt.subplots(figsize=(7, 3.5))
        pats = pt.pattern.unique()
        for i, grp in enumerate(["all", "emerging_PRIMARY", "non_emerging_PRIMARY"]):
            q = pt[pt.group == grp].set_index("pattern").reindex(pats)
            x = np.arange(len(pats)) + (i - 1) * 0.27
            ax.bar(x, q.freq, width=0.26, label=f"{grp} (n={int(q.n.max()) if q.n.notna().any() else 0})",
                   yerr=[q.freq - q.ci_lo, q.ci_hi - q.freq], capsize=3)
        ax.set_xticks(np.arange(len(pats)))
        ax.set_xticklabels(pats, fontsize=8)
        ax.set_ylabel("share of concepts")
        ax.legend(fontsize=7, frameon=False)
        fig.tight_layout()
        fig.savefig(FIG / "pattern_frequencies.png", dpi=180)
        fig.savefig(FIG / "pattern_frequencies.pdf")
        plt.close(fig)


def stage_outcomes() -> None:
    assert_frozen()
    t0 = time.time()
    rng = np.random.default_rng(S.SEED)
    feat = pd.read_parquet(FEAT)
    concepts = pd.read_parquet(load.INTER / "concepts.parquet")
    concepts = concepts[concepts.concept_id.isin(feat.concept_id.unique())].reset_index(drop=True)
    tax = pd.read_parquet(load.DS2 / "data" / "taxonomy_fields.parquet")
    concepts["origin_domain"] = concepts.origin_field.map(dict(zip(tax.field_id, tax.domain_id))).fillna(-1).astype(int)

    # STEP 4 labels
    lab = A.label_table(feat, concepts)
    lab.to_parquet(RES / "labels.parquet")
    on = {vd: A.onsets(lab, vd) for vd in ["PRIMARY", "SENS1", "SENS2"]}
    on_cent = A.onsets(lab, "PRIMARY", outcome="E_cent")
    on_2018 = A.onsets(lab, "PRIMARY", t_max=2018)
    label_summary = {
        "n_units_age_3_8": int(lab.in_age_range.sum()),
        **{f"n_emerging_{vd}": len(o) for vd, o in on.items()},
        "n_emerging_E_cent_only": len(on_cent), "n_emerging_PRIMARY_t_le_2018": len(on_2018),
        "n_emerging_PRIMARY_rule_parity": sum(1 for c in on["PRIMARY"] if c in set(concepts[concepts.rule_parity].concept_id)),
        "unit_positive_rates": {c: float(lab.loc[lab.in_age_range, c].mean()) for c in
                                ["E_PRIMARY", "E_SENS1", "E_SENS2", "E_cent", "E_cent_allnodes", "E_vol_PRIMARY", "E_vol_SENS1", "E_vol_SENS2"]},
        "sens2_units_dropped_before_DateEstablished": int((lab.in_age_range & ~lab.sens2_valid).sum()),
        "onset_years_PRIMARY": pd.Series(on["PRIMARY"]).value_counts().sort_index().to_dict(),
    }
    logger.info(f"labels: {label_summary}")

    # STEP 5 matching variants
    parity = set(concepts[concepts.rule_parity].concept_id)
    variants = []
    for vd in ["PRIMARY", "SENS1", "SENS2"]:
        sets, info = A.match_controls(lab, concepts, on[vd], vd, f"E_{vd}")
        variants.append({"key": f"{vd}|all", "volume_def": vd, "subset": "all", "outcome": "E", "sets": sets, "match_info": info})
    sets, info = A.match_controls(lab, concepts, on["PRIMARY"], "PRIMARY", "E_PRIMARY", eligible=parity)
    variants.append({"key": "PRIMARY|rule_parity", "volume_def": "PRIMARY", "subset": "rule_parity", "outcome": "E",
                     "sets": sets, "match_info": info})
    sets, info = A.match_controls(lab, concepts, on_2018, "PRIMARY", "E_PRIMARY")
    variants.append({"key": "PRIMARY|t_le_2018", "volume_def": "PRIMARY", "subset": "t_le_2018", "outcome": "E",
                     "sets": sets, "match_info": info})
    sets, info = A.match_controls(lab, concepts, on["PRIMARY"], "PRIMARY", "E_PRIMARY", group_col="origin_domain")
    variants.append({"key": "PRIMARY|domain_match", "volume_def": "PRIMARY", "subset": "domain_match", "outcome": "E",
                     "sets": sets, "match_info": info})
    sets, info = A.match_controls(lab, concepts, on_cent, "PRIMARY", "E_cent")
    variants.append({"key": "PRIMARY|E_cent_only", "volume_def": "PRIMARY", "subset": "all", "outcome": "E_cent",
                     "sets": sets, "match_info": info})
    write_json(RES / "matched_sets.json", {v["key"]: v["sets"] for v in variants})

    # STEP 6 event study
    eff, match_info = run_event_studies(feat, lab, concepts, rng, variants)
    eff.to_csv(RES / "rq1_effects.csv", index=False)
    null_ev = null_check_event(feat, lab, concepts, on["PRIMARY"], rng)
    Dp = eff[(eff.rel_year == "D_-3_-1") & (eff.version == "raw") & (eff.volume_def == "PRIMARY") & (eff.subset == "all")
             & (eff.outcome == "E")].set_index("indicator")
    for p_, v in null_ev.items():
        se = float(Dp.at[p_, "se"]) if p_ in Dp.index else np.nan
        v["boot_se_real_D"] = se
        v["pass_abs_mean_lt_0.25_se"] = bool(v["mean_perm_D"] is not None and np.isfinite(se)
                                            and abs(v["mean_perm_D"]) < 0.25 * se)
    logger.info(f"T5 event null: {null_ev}")

    # main-pool-aligned block (rq1_spec.MAINPOOL)
    mp_rows, mp_info = mainpool_block(feat, lab, concepts, rng)
    mp_tab = pd.DataFrame(mp_rows)
    mp_tab.to_csv(RES / "rq1_effects_mainpool_aligned.csv", index=False)
    side = side_by_side(mp_tab)
    side.to_csv(RES / "side_by_side_mainpool_vs_mesh.csv", index=False)

    # STEP 7 prediction
    pred, pred_meta, preds_store = prediction(feat, lab, concepts, rng)
    pred.to_csv(RES / "rq1_prediction.csv", index=False)

    # STEP 8 patterns
    pat, ref = A.patterns(feat)
    em = set(on["PRIMARY"])
    em_cent = set(on_cent)
    pat["emerging_PRIMARY"] = pat.concept_id.isin(em)
    pat["emerging_E_cent"] = pat.concept_id.isin(em_cent)
    pat.to_csv(RES / "rq1_patterns_by_concept.csv", index=False)
    prow = []
    names = ["incubation_expansion", "gradual_centralisation", "early_bridging"]
    groups = {"all": pat, "emerging_PRIMARY": pat[pat.emerging_PRIMARY], "non_emerging_PRIMARY": pat[~pat.emerging_PRIMARY],
              "emerging_E_cent": pat[pat.emerging_E_cent], "non_emerging_E_cent": pat[~pat.emerging_E_cent]}
    for gname, g in groups.items():
        for p in names:
            f_, lo, hi = A.boot_freq(g[p].astype(float).to_numpy(), rng)
            prow.append({"population": S.POPULATION, "group": gname, "pattern": p, "freq": f_, "ci_lo": lo, "ci_hi": hi,
                         "n": int(len(g)), "count": int(g[p].sum())})
        f_, lo, hi = A.boot_freq((~g[names].any(axis=1)).astype(float).to_numpy(), rng)
        prow.append({"population": S.POPULATION, "group": gname, "pattern": "none", "freq": f_, "ci_lo": lo, "ci_hi": hi,
                     "n": int(len(g)), "count": int((~g[names].any(axis=1)).sum())})
    pat_tab = pd.DataFrame(prow)
    pat_tab.to_csv(RES / "rq1_patterns.csv", index=False)
    overlap = {f"{a}&{b}": int((pat[a] & pat[b]).sum()) for i, a in enumerate(names) for b in names[i + 1:]}
    overlap["all_three"] = int(pat[names].all(axis=1).sum())
    # difference emerging vs non-emerging (concept bootstrap)
    pat_diff = {}
    for p in names:
        e = pat.loc[pat.emerging_PRIMARY, p].astype(float).to_numpy()
        ne = pat.loc[~pat.emerging_PRIMARY, p].astype(float).to_numpy()
        if len(e) and len(ne):
            b = [rng.choice(e, len(e)).mean() - rng.choice(ne, len(ne)).mean() for _ in range(S.BOOT)]
            pat_diff[p] = {"diff": float(e.mean() - ne.mean()), "ci": [float(np.percentile(b, 2.5)), float(np.percentile(b, 97.5))]}

    # STEP 9 verdict
    verdict = {"population": S.POPULATION, "main_pool_available": False,
               "main_pool_note": "No main-pool RQ1 results existed under iter_2/gen_art at run time; agreement is to be "
                                 "filled in by iteration 3 by joining rq1_effects.csv on (indicator, version, rel_year, volume_def).",
               "precursors": {}}
    D = eff[eff.rel_year == "D_-3_-1"]
    for p in S.PRECURSORS:
        rec = {}
        for key in ["PRIMARY|all", "SENS1|all", "SENS2|all", "PRIMARY|rule_parity", "PRIMARY|t_le_2018",
                    "PRIMARY|domain_match", "PRIMARY|E_cent_only"]:
            vd, sub = key.split("|")
            outc = "E_cent" if sub == "E_cent_only" else "E"
            sub_ = "all" if sub == "E_cent_only" else sub
            r = D[(D.indicator == p) & (D.version == "raw") & (D.volume_def == vd) & (D.subset == sub_) & (D.outcome == outc)]
            if r.empty:
                continue
            r = r.iloc[0]
            n = int(r.n_eff_window)
            rec[key] = {"n_matched_sets": int(r.n_emerging),"D": r["diff"], "D_sd_units": r.diff_sd, "ci": [r.ci_lo, r.ci_hi], "p_boot": r.p_boot,
                        "p_holm": r.p_holm, "mde_sd_units": r.mde_sd, "n_eff_window": n,
                        "sign": (None if not np.isfinite(r["diff"]) else ("+" if r["diff"] > 0 else "-" if r["diff"] < 0 else "0")),
                        "ci_excludes_0": bool(np.isfinite(r.ci_lo) and (r.ci_lo > 0 or r.ci_hi < 0)),
                        "underpowered_F5": n < 15}
        prim = rec.get("PRIMARY|all", {})
        signs = [v["sign"] for v in rec.values() if v.get("sign")]
        rec["sign_consistency_across_variants"] = (f"{sum(s == prim.get('sign') for s in signs)}/{len(signs)} variants share "
                                                   f"the PRIMARY sign" if prim.get("sign") else None)
        if prim.get("underpowered_F5", True):
            rec["verdict"] = ("UNDERPOWERED (F5): fewer than 15 matched emerging concepts with data in rel -3..-1 "
                              "under PRIMARY; no sign conclusion")
        elif prim["ci_excludes_0"] and (prim.get("p_holm") or 1) < 0.05:
            rec["verdict"] = f"SUPPORTED in this population (sign {prim['sign']}, Holm p < 0.05)"
        else:
            rec["verdict"] = (f"NOT DETECTED (sign {prim.get('sign')}, CI includes 0; MDE = {prim.get('mde_sd_units')} SD)")
        verdict["precursors"][p] = rec
    pB = pred[(pred.volume_def == "PRIMARY") & (pred.outcome == "E_PRIMARY") & (pred.feature_set == "B")]
    verdict["prediction_PRIMARY_delta_auc"] = pB[["evaluation", "auc", "auc_baseline", "delta_auc", "delta_ci_lo",
                                                  "delta_ci_hi", "n_units", "n_pos", "origins_used"]].to_dict(orient="records")
    write_json(RES / "replication_verdict.json", verdict)

    verdict["mainpool_aligned"] = mainpool_verdict(side, mp_info)
    write_json(RES / "replication_verdict.json", verdict)
    summary = {"labels": label_summary, "match_info": match_info, "event_null_T5": null_ev, "mainpool_block": mp_info,
               "prediction_meta": pred_meta, "patterns_reference": ref, "pattern_overlap": overlap,
               "pattern_emerging_minus_nonemerging": pat_diff, "runtime_outcomes_s": time.time() - t0}
    write_json(RES / "analysis_summary.json", summary)
    figures(eff, pred, pat_tab)
    build_method_out(feat, lab, concepts, preds_store, verdict, summary)
    logger.info(f"outcomes stage done in {time.time() - t0:.0f}s")


def build_method_out(feat, lab, concepts, preds_store, verdict, summary) -> None:
    """method_out.json in exp_gen_sol_out format: one example per (concept, t) unit (age 3..8, t <= 2019)."""
    fs = A.feature_sets("PRIMARY", A.ALL_NET)
    in_cols = fs["B_all"]
    units = lab[lab.in_age_range].merge(feat.rename(columns={"year": "t"}), on=["concept_id", "t", "F", "age"], how="left")
    ro = preds_store.get(("PRIMARY", "E_PRIMARY", "rolling_origin"), pd.DataFrame())
    cv = preds_store.get(("PRIMARY", "E_PRIMARY", "grouped_cv"), pd.DataFrame())
    ro = ro.set_index(["concept_id", "t"]) if len(ro) else ro
    cv = cv.set_index(["concept_id", "t"]) if len(cv) else cv
    cm = concepts.set_index("concept_id")
    ex = []
    for r in units.itertuples(index=False):
        rd = r._asdict()
        key = (rd["concept_id"], rd["t"])
        x = {c: (None if pd.isna(rd.get(c)) else float(rd.get(c))) for c in in_cols}
        e = {"input": json.dumps(x), "output": str(int(rd["E_PRIMARY"]))}
        src = None
        if len(ro) and key in ro.index:
            q = ro.loc[key]
            e["predict_baseline_A"] = f"{q.p_A:.6f}"
            e["predict_method_B"] = f"{q.p_B:.6f}"
            src = f"rolling_origin_T{int(q.origin)}"
        elif len(cv) and key in cv.index:
            q = cv.loc[key]
            e["predict_baseline_A"] = f"{q.p_A:.6f}"
            e["predict_method_B"] = f"{q.p_B:.6f}"
            src = f"grouped_cv_fold{int(q.fold)}"
        if len(cv) and key in cv.index:
            q = cv.loc[key]
            e["predict_baseline_A_groupedcv"] = f"{q.p_A:.6f}"
            e["predict_method_B_groupedcv"] = f"{q.p_B:.6f}"
            e["predict_B_all_groupedcv"] = f"{q.p_B_all:.6f}"
        e.update({"metadata_concept_id": rd["concept_id"], "metadata_t": int(rd["t"]), "metadata_age": int(rd["age"]),
                  "metadata_F": int(rd["F"]), "metadata_prediction_source": src,
                  "metadata_rule_parity": bool(cm.at[rd["concept_id"], "rule_parity"]),
                  "metadata_volume_def": "PRIMARY_tm", "metadata_E_cent": int(rd["E_cent"]),
                  "metadata_E_vol": int(rd["E_vol_PRIMARY"]), "metadata_E_SENS1": int(rd["E_SENS1"]),
                  "metadata_E_SENS2": int(rd["E_SENS2"]) if rd["sens2_valid"] else None,
                  "metadata_preferred_term": cm.at[rd["concept_id"], "preferred_term"]})
        ex.append(e)
    out = {"metadata": {"method_name": "RQ1 network-precursor replication (held-out MeSH population)",
                        "description": "Per (concept, t) unit: input = frozen feature vector (JSON, features at <= t); "
                                       "output = network-only emergence E(c,t) under PRIMARY volume; predict_baseline_A = "
                                       "P(E) from frequency/burst + degree/centrality-growth logistic model; predict_method_B "
                                       "= P(E) from A + 3 pre-named precursors (accretion share, closure over Chung-Lu null, "
                                       "participation rise). Rolling-origin predictions where the origin was usable, "
                                       "grouped-CV (labelled secondary) otherwise.",
                        "feature_names": in_cols, "spec": "rq1_spec.py", "replication_verdict": verdict,
                        "label_summary": summary["labels"]},
           "datasets": [{"dataset": "mesh_heldout_rq1_units", "examples": ex}]}
    write_json(ROOT / "method_out.json", out)
    logger.info(f"method_out.json: {len(ex)} examples")


@logger.catch(reraise=True)
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", choices=["snapshots", "features", "outcomes", "all"], default="all")
    ap.add_argument("--mini", action="store_true")
    ap.add_argument("--workers", type=int, default=4)
    a = ap.parse_args()
    resource.setrlimit(resource.RLIMIT_AS, (26 * 1024**3, 26 * 1024**3))
    RES.mkdir(exist_ok=True)
    if a.stage in ("snapshots", "all"):
        stage_snapshots(a.mini, a.workers)
    if a.stage in ("features", "all"):
        stage_features()
    if a.stage in ("outcomes", "all"):
        stage_outcomes()
        pre = json.loads(PREREG.read_text())
        pre["main_pool_search_end"] = find_main_pool()
        write_json(PREREG, pre)


if __name__ == "__main__":
    _ = glob
    main()
