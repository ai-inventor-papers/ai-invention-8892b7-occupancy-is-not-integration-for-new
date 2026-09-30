#!/usr/bin/env python3
"""RQ1 test: structural precursors of concept emergence in an evolving co-word knowledge network.

Pipeline (each stage is its own module; this script orchestrates, tests for leakage and writes all outputs):
  stage_prep.py        load + verify inputs (fold counts, tag-id overlap), compact tables in work/
  stage_snapshots.py   25 yearly 3-year-window concept-concept snapshots + pool attachment + alluvial ids
  stage_indicators.py  concept-subfield bipartite + per-(concept, year) indicators (raw / rarefied / residualised)
  stage_robust.py      Leiden bootstrap stability, rewiring null for closure, edge-filter and substrate checks
  method.py            spec hash -> leakage test -> labels -> matched event study -> rolling-origin prediction
                       (baselines vs precursor-augmented) -> patterns -> typology -> figures -> method_out.json

Usage:
  uv run method.py --all         # run every stage (prep, snapshots, indicators, robust) then the analysis
  uv run method.py               # analysis only (expects work/ and results/indicators/ to exist)
"""
from __future__ import annotations

import os

os.environ.setdefault("OMP_NUM_THREADS", "1")  # avoid OpenMP oversubscription (HGB) when stages run side by side

import argparse
import json
import math
import subprocess
import sys
import time

import numpy as np
import pandas as pd
from loguru import logger

import config as C

S = C.SPEC


def _clean(o):
    """JSON-safe conversion (NaN -> None, numpy -> python)."""
    if isinstance(o, dict):
        return {str(k): _clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_clean(v) for v in o]
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating, float)):
        return None if not np.isfinite(o) else float(o)
    if isinstance(o, np.bool_):
        return bool(o)
    if isinstance(o, np.ndarray):
        return _clean(o.tolist())
    return o


def run_stage(script: str) -> None:
    logger.info(f"running {script}")
    r = subprocess.run([sys.executable, str(C.ROOT / script)], cwd=C.ROOT)
    if r.returncode != 0:
        raise RuntimeError(f"{script} failed with code {r.returncode}")


# ----------------------------------------------------------------------------- leakage test
def leakage_test(lab: pd.DataFrame, ind: pd.DataFrame, n: int = 5) -> dict:
    """Recompute features for random (c, t) with all data after t removed; must equal the stored features."""
    import stage_indicators as SI
    from analysis_predict import FEATURE_SETS
    rs = pd.read_parquet(C.OUT / "concept_subfield" / "rs_distance.parquet")
    subs = np.sort(rs.subfield_i.unique())
    sidx = {int(s): i for i, s in enumerate(subs)}
    D = rs.pivot(index="subfield_i", columns="subfield_j", values="d").loc[subs, subs].values.astype(float)
    inp = SI.load_inputs()
    feats = sorted({f for fs in FEATURE_SETS.values() for f in fs} - {"log_strength", "band_2005_07", "band_2008_11",
                                                                       "og_F31", "og_F17", "og_D3", "age"})
    rng = np.random.default_rng(123)
    picks = lab.iloc[rng.choice(len(lab), size=min(n, len(lab)), replace=False)]
    out = []
    for r in picks.itertuples():
        c, t = r.concept_id, int(r.t)
        F = float(inp["pool"].set_index("concept_id").loc[c, "F"])
        rows, _ = SI.concept_indicators(c, F, inp["cp"][inp["cp"].concept_id == c], inp["pm"][inp["pm"].concept_id == c],
                                        inp["pid_map"], inp["totals"], D, sidx, max_year=t)
        trunc = pd.DataFrame(rows).set_index("year").loc[t]
        stored = ind[(ind.concept_id == c) & (ind.year == t)].iloc[0]
        bad = []
        for f in feats:
            a, b = float(trunc[f]), float(stored[f])
            if not ((np.isnan(a) and np.isnan(b)) or math.isclose(a, b, rel_tol=1e-6, abs_tol=1e-9)):
                bad.append((f, a, b))
        out.append(dict(concept_id=c, t=t, n_features=len(feats), mismatches=bad))
        if bad:
            raise AssertionError(f"LEAKAGE: features at ({c},{t}) change when data after t are removed: {bad[:5]}")
    logger.info(f"leakage test passed on {len(out)} concept-years x {len(feats)} features")
    return dict(passed=True, cases=out)


# ----------------------------------------------------------------------------- figures
def _fig_event(plt, es: dict, path, title: str) -> None:
    ks = S["es_rel_years"]
    fam_rows = {(t["family"], t["version"]): t for t in es.get("table", [])}
    fig, axes = plt.subplots(1, 3, figsize=(13, 3.8), sharex=True)
    for ax, fam, ttl in zip(axes, ("accretion", "closure", "participation"),
                            ("Accretion shift (rarefied)", "Closure (log obs/Chung-Lu)", "Participation P (rarefied)")):
        for ver, col, ls in (("primary", "#1f5fa8", "-"), ("res", "#c0504d", "--")):
            t = fam_rows.get((fam, ver))
            if not t or t.get("diff_k") is None:
                continue
            d = np.array([np.nan if x is None else x for x in t["diff_k"]], dtype=float)
            ci = np.array([[np.nan if y is None else y for y in x] if x is not None else [np.nan, np.nan] for x in t["ci_k"]], dtype=float)
            s_val = t.get("S")
            ax.plot(ks, d, ls, color=col, marker="o", label=f"{ver} (S={s_val:.3g})" if s_val is not None else ver)
            ax.fill_between(ks, ci[:, 0], ci[:, 1], color=col, alpha=0.15)
        ax.axhline(0, color="k", lw=0.8)
        ax.axvspan(S["es_summary_window"][0] - 0.5, S["es_summary_window"][1] + 0.3, color="grey", alpha=0.07)
        ax.set_title(ttl, fontsize=10)
        ax.set_xlabel("years relative to onset t0")
        ax.legend(fontsize=7)
    axes[0].set_ylabel("treated - matched controls")
    fig.suptitle(title, fontsize=10)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def figures(es: dict, pred: dict, pat_res: dict, typ: dict, snaps: pd.DataFrame, events: pd.DataFrame) -> list[str]:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    made = []
    for tag, e in es.items():
        _fig_event(plt, e, C.FIG / f"es_precursors{'' if tag == 'E' else '_' + tag}.png",
                   f"Event study [{tag}]: {e.get('n_matched', 0)} matched emerging concepts (95% concept-bootstrap CI)")
        made.append(f"figures/es_precursors{'' if tag == 'E' else '_' + tag}.png")
    # 2. delta-AUC / delta-R2 forest
    items = []
    for key, lab in (("E_h5", "E primary (h=5)"), ("E3_h3", "E3 (h=3)"), ("E_alt_h5", "E_alt pool-pct (h=5)"),
                     ("E_up_h5", "E_up uptake-only (h=5)"), ("subfield_gain_reg", "subfield gain R2"),
                     ("cent_gain_reg", "centrality gain R2"), ("secondary_drop_sense_fail_E_alt_h5", "E_alt, no sense-fail")):
        ev = pred.get(key, {}).get("eval", {})
        for mdl in ("logit", "hgb"):
            dd = ev.get(mdl, {}).get("deltas", {}).get("FULL_vs_BASELINE")
            if dd and dd["delta"] is not None and np.isfinite(dd["delta"]):
                items.append((f"{lab} [{mdl}]", dd["delta"], dd["ci"]))
    if items:
        fig, ax = plt.subplots(figsize=(7, 0.45 * len(items) + 1.2))
        for i, (n, d, ci) in enumerate(items):
            ax.errorbar(d, i, xerr=[[d - ci[0]], [ci[1] - d]] if ci[0] is not None and np.isfinite(ci[0]) else None,
                        fmt="o", color="#1f5fa8", capsize=3)
        ax.axvline(0, color="k", lw=0.8)
        ax.set_yticks(range(len(items)))
        ax.set_yticklabels([x[0] for x in items], fontsize=8)
        ax.set_xlabel("FULL - BASELINE (AUC or R2), 95% concept-bootstrap CI")
        fig.tight_layout()
        fig.savefig(C.FIG / "delta_auc.png", dpi=150)
        plt.close(fig)
        made.append("figures/delta_auc.png")
    # 3. pattern bars
    fr = pat_res.get("frequencies", {})
    names = ["INCUBATION_THEN_EXPANSION", "GRADUAL_CENTRALISATION", "EARLY_BRIDGING"]
    fig, ax = plt.subplots(figsize=(7, 3.5))
    w = 0.25
    for j, (grp, col) in enumerate((("overall", "#777777"), ("emerging", "#c0504d"), ("never", "#1f5fa8"))):
        vals = [fr.get(f"{n}__pre_onset", {}).get(grp, np.nan) if grp != "overall" else fr.get(f"{n}__age0_8", {}).get(grp, np.nan) for n in names]
        vals = [np.nan if v is None else v for v in vals]
        ax.bar(np.arange(3) + (j - 1) * w, vals, w, color=col, label=grp)
    ax.set_xticks(range(3))
    ax.set_xticklabels(["incubation->expansion", "gradual centralisation", "early bridging"], fontsize=8)
    ax.set_ylabel("share of screen concepts")
    ax.set_title("overall: ages 0-8; emerging vs never: pre-onset window (E_up groups)", fontsize=8)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(C.FIG / "pattern_bars.png", dpi=150)
    plt.close(fig)
    made.append("figures/pattern_bars.png")
    # 4. typology cluster mean series
    cms = typ.get("cluster_mean_series", {})
    if cms:
        chans = typ["channels"]
        fig, axes = plt.subplots(1, len(chans), figsize=(2.2 * len(chans), 2.8), sharex=True)
        for ci, (cl, ser) in enumerate(sorted(cms.items())):
            ser = np.array(ser)
            for k, ax in enumerate(axes):
                ax.plot(S["typology"]["ages"], ser[:, k], marker=".", label=f"cluster {cl}")
                ax.set_title(chans[k], fontsize=8)
        axes[0].legend(fontsize=7)
        axes[0].set_ylabel("z-score")
        fig.suptitle(f"Preliminary typology: cluster mean series by age (k={typ.get('k_selected')}, {typ.get('status')})", fontsize=9)
        fig.tight_layout()
        fig.savefig(C.FIG / "typology_series.png", dpi=150)
        plt.close(fig)
        made.append("figures/typology_series.png")
    # 5. alluvial / snapshot summary
    fig, ax1 = plt.subplots(figsize=(8, 3.3))
    ax1.plot(snaps.year, snaps.n_comm_ge5, "o-", color="#1f5fa8", label="communities (>=5 nodes)")
    ev = events.groupby(["year", "event"]).size().unstack(fill_value=0) if len(events) else pd.DataFrame()
    for e, col in (("continue", "#2e8b57"), ("birth", "#c0504d"), ("death", "#777777")):
        if e in ev:
            ax1.plot(ev.index, ev[e], ".--", color=col, label=e)
    ax2 = ax1.twinx()
    ax2.plot(snaps.year, snaps.modularity, "s:", color="k", label="modularity")
    ax1.set_xlabel("snapshot year")
    ax1.legend(fontsize=7, loc="upper left")
    ax2.set_ylabel("modularity")
    fig.tight_layout()
    fig.savefig(C.FIG / "alluvial_summary.png", dpi=150)
    plt.close(fig)
    made.append("figures/alluvial_summary.png")
    # 6. methodology diagram
    fig, ax = plt.subplots(figsize=(12, 4.2))
    ax.axis("off")
    boxes = [
        (0.02, 0.62, "Inputs\nconcept pool (123 screen +\n22 reference; held-out sealed)\nc-papers (208k works)\nbackground sample (260k)"),
        (0.22, 0.62, "Snapshots 2000-2024\n3-yr windows, co-word\nassociation strength\nLeiden + alluvial ids\npool attached exactly"),
        (0.42, 0.62, "Indicators (c, y), data <= y\nstrength, pct, betweenness\nBaselga, novelty, closure\nparticipation, z, diversity\nraw / rarefied / residualised"),
        (0.62, 0.62, "Emergence label E(c,t), ages 3-8\nuptake >= 20/yr (t+1..t+5)\nAND strength-pct gain >= 20\nsecondary: E_alt (pool pct),\nE_up (uptake only)"),
        (0.82, 0.62, "Robustness\nbootstrap AMI, rewiring z\nedge-filter, D4 substrate\nsensitivity grid"),
        (0.12, 0.12, "Event study\nonset vs 1:3 matched\nnever-emerging (band, field,\n+-20% volume); Holm; placebo"),
        (0.37, 0.12, "Rolling-origin prediction\nbaselines: freq/burst, degree/\ncentrality, entropy\nvs FULL (+ precursors)"),
        (0.62, 0.12, "Patterns + typology\nincubation, centralisation,\nbridging; DTW k-medoids\nbootstrap Jaccard"),
    ]
    for x, y, txt in boxes:
        ax.add_patch(plt.Rectangle((x, y), 0.17, 0.33, fill=True, fc="#eef3fa", ec="#1f5fa8", lw=1.2, transform=ax.transAxes))
        ax.text(x + 0.085, y + 0.165, txt, ha="center", va="center", fontsize=7.5, transform=ax.transAxes)
    for x0 in (0.19, 0.39, 0.59, 0.79):
        ax.annotate("", xy=(x0 + 0.03, 0.785), xytext=(x0, 0.785), xycoords="axes fraction",
                    arrowprops=dict(arrowstyle="->", color="#1f5fa8"))
    for xt in (0.205, 0.455, 0.705):
        ax.annotate("", xy=(xt, 0.45), xytext=(0.705, 0.62), xycoords="axes fraction",
                    arrowprops=dict(arrowstyle="->", color="#c0504d", lw=0.8))
    ax.set_title("RQ1 methodology: evolving co-word network -> volume-normalised precursors -> tests", fontsize=10)
    fig.savefig(C.FIG / "methodology.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    made.append("figures/methodology.png")
    return made


def fig_trajectories(ind: pd.DataFrame, labs: dict) -> list[str]:
    """Median indicator trajectories by concept age: emerging vs never-emerging (per label variant)."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    cols = [("log_vol3", "log(1+vol3)"), ("pct", "strength percentile"), ("closure", "closure (log obs/CL)"),
            ("novelty", "neighbourhood novelty"), ("new_relation_rate", "new-relation rate"), ("P_rar", "participation (rar.)"),
            ("wmz", "within-module z"), ("H", "subfield entropy H")]
    made = []
    for tag, lb in labs.items():
        g = lb.drop_duplicates("concept_id").set_index("concept_id").group
        d = ind[(ind.fold == "screen") & (ind.age >= -2) & (ind.age <= 12)].copy()
        d["grp"] = d.concept_id.map(g)
        d = d[d.grp.isin(["emerging", "never"])]
        fig, axes = plt.subplots(2, 4, figsize=(13, 5.5), sharex=True)
        for ax, (c, name) in zip(axes.ravel(), cols):
            for grp, colr in (("emerging", "#c0504d"), ("never", "#1f5fa8")):
                q = d[d.grp == grp].groupby("age")[c].quantile([0.25, 0.5, 0.75]).unstack()
                ax.plot(q.index, q[0.5], color=colr, label=f"{grp} (n={d[d.grp == grp].concept_id.nunique()})")
                ax.fill_between(q.index, q[0.25], q[0.75], color=colr, alpha=0.12)
            ax.set_title(name, fontsize=9)
        axes[0, 0].legend(fontsize=7)
        for ax in axes[1]:
            ax.set_xlabel("concept age (years since F)")
        fig.suptitle(f"Indicator trajectories (median, IQR) by label {tag}: emerging vs never-emerging screen concepts", fontsize=10)
        fig.tight_layout()
        path = C.FIG / f"trajectories_{tag}.png"
        fig.savefig(path, dpi=140)
        plt.close(fig)
        made.append(f"figures/trajectories_{tag}.png")
    return made


# ----------------------------------------------------------------------------- verdicts
def verdicts(es_all: dict, pred: dict, pat_all: dict, typ: dict) -> dict:
    out = {}
    for tag, es in es_all.items():
        out[f"[{tag}]"] = _verdicts_one(es, pred, pat_all[tag], typ, tag)
    out["[global]"] = verdicts_global(pred, typ)
    return out


def _g(x) -> str:
    return "NA" if x is None else f"{x:.3g}"


def _fmt_ci(ci) -> str:
    return "[" + ", ".join("NA" if x is None else f"{x:.3g}" for x in (ci or [None, None])) + "]"


def _pred_verdict(pred: dict, key: str) -> str:
    ev = pred.get(key, {}).get("eval", {}).get("logit", {}) if key else {}
    dd = ev.get("deltas", {}).get("FULL_vs_BASELINE")
    if not dd or dd.get("delta") is None or dd["ci"][0] is None:
        return "NOT RUN (no usable rolling origin)"
    lo, hi = dd["ci"]
    n_or = pred.get("origins_used", {}).get(key, 2)
    base = ev["pooled"]["BASELINE"]["metric"]
    txt = f"delta={dd['delta']:.3f}, CI [{lo:.3f},{hi:.3f}], BASELINE={base:.3f}, n_test={ev.get('n_test_rows')}, pos={ev.get('n_test_pos')}, origins={n_or}"
    if n_or < 2 or (ev.get("n_test_pos") is not None and ev["n_test_pos"] < 10):
        return f"UNDERPOWERED PILOT ({txt})"
    if lo > 0:
        return f"CONFIRMED ({txt})"
    if hi < 0:
        return f"DISCONFIRMED (precursors hurt out of sample; {txt})"
    if hi - lo > 0.10:
        return f"UNDERPOWERED PILOT ({txt})"
    return f"DISCONFIRMED (no added value beyond baselines; {txt})"


def _verdicts_one(es: dict, pred: dict, pat_res: dict, typ: dict, tag: str) -> dict:
    v = {}
    tab = {(t["family"], t["version"]): t for t in es.get("table", [])}
    pooled = es.get("pooled_panel", {})
    for fam, col in (("accretion", "accretion_shift_rar"), ("closure", "closure"), ("participation", "P_rar")):
        p, r = tab.get((fam, "primary")), tab.get((fam, "res"))
        pp = pooled.get(col, {})
        ptxt = (f"; pooled panel coef={pp['coef']:.3g} CI {_fmt_ci(pp.get('ci'))} p={_g(pp.get('p'))} Holm p={_g(pp.get('p_holm'))}"
                if pp.get("coef") is not None else "")
        if not p or p.get("S") is None:
            v[f"event_study_{fam}"] = "NOT RUN (no matched treated concepts)" + ptxt
            continue
        n = p.get("n_treated") or 0
        mde_sd = p.get("mde_in_sd")
        base = f"S={p['S']:.3g} CI {_fmt_ci(p['ci'])}, n matched treated={n}, MDE={p['mde'] if p['mde'] is None else round(p['mde'], 3)}"
        if n < 10:
            v[f"event_study_{fam}"] = f"UNDERPOWERED PILOT ({base}; bootstrap p not interpretable with n<10){ptxt}"
            continue
        sig = p.get("p_holm") is not None and p["p_holm"] < 0.05
        res_excl = r and r.get("ci") and r["ci"][0] is not None and (r["ci"][0] > 0 or r["ci"][1] < 0)
        pilot = " [pilot: n<30]" if n < 30 else ""
        if sig and p["S"] > 0 and res_excl and r["S"] > 0:
            v[f"event_study_{fam}"] = f"CONFIRMED{pilot} ({base}, Holm p={p['p_holm']:.3g}, residualised CI excludes 0){ptxt}"
        elif sig and p["S"] > 0:
            v[f"event_study_{fam}"] = f"DISCONFIRMED (volume in disguise){pilot} ({base}; residualised CI {_fmt_ci(r['ci'] if r else None)}){ptxt}"
        elif sig and p["S"] < 0:
            v[f"event_study_{fam}"] = f"DISCONFIRMED (opposite sign){pilot} ({base}, Holm p={p['p_holm']:.3g}){ptxt}"
        elif mde_sd is not None and mde_sd > 0.5:
            v[f"event_study_{fam}"] = f"UNDERPOWERED PILOT ({base} = {mde_sd:.2f} SD){ptxt}"
        else:
            v[f"event_study_{fam}"] = f"DISCONFIRMED (no divergence with adequate power; {base}){ptxt}"
    key = pred.get("headline") if tag == "E" else f"{tag}_h5"
    v["prediction_delta_auc"] = _pred_verdict(pred, key)
    v["exploratory_indicators_q_lt_0.05"] = [f"{t['indicator']}: S={t['S']:.3g} CI {_fmt_ci(t['ci'])} q={t['q_bh']:.3g}"
                                              for t in es.get("table", []) if t.get("q_bh") is not None and t["q_bh"] < 0.05]
    fr = pat_res.get("frequencies", {})
    for k in ("INCUBATION_THEN_EXPANSION", "GRADUAL_CENTRALISATION", "EARLY_BRIDGING"):
        f = fr.get(f"{k}__pre_onset", {})
        if f.get("diff") is None:
            v[f"pattern_{k}"] = "NOT RUN"
            continue
        lo, hi = f["diff_ci"]
        tagtxt = ("DISTINGUISHES emerging (CI excludes 0)" if (lo is not None and (lo > 0 or hi < 0))
                  else "does not distinguish emerging from never (CI covers 0)")
        v[f"pattern_{k}"] = (f"{tagtxt}: overall {fr.get(f'{k}__age0_8', {}).get('overall', float('nan')):.2f}; emerging "
                             f"{f['emerging']:.2f} (n={f['n_emerging']}) vs never {f['never']:.2f} (n={f['n_never']}) pre-onset, "
                             f"Fisher p={f['fisher_p']:.3g}")
    return v


def verdicts_global(pred: dict, typ: dict) -> dict:
    return {"prediction_sustained_uptake_E_up": _pred_verdict(pred, "E_up_h5"),
            "prediction_subfield_gain_R2": _pred_verdict(pred, "subfield_gain_reg"),
            "prediction_centrality_gain_R2": _pred_verdict(pred, "cent_gain_reg"),
            "typology": f"{typ.get('status')} (k={typ.get('k_selected')}, min bootstrap Jaccard by k="
                        f"{ {k: round(x['min_jaccard'], 2) for k, x in typ.get('by_k', {}).items()} }, "
                        f"AMI vs pattern combos={typ.get('ami_vs_pattern_combo')})"}


@logger.catch(reraise=True)
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true", help="run prep, snapshots, indicators and robust stages first")
    a = ap.parse_args()
    C.setup_logging("method")
    C.set_ram_limit(24)
    t0 = time.time()
    h = C.write_spec()
    logger.info(f"spec.json written, sha256={h}")
    if a.all:
        for sc in ("stage_prep.py", "stage_snapshots.py", "stage_indicators.py", "stage_robust.py"):
            run_stage(sc)
    import analysis_event as AE
    import analysis_patterns as AP
    import analysis_predict as APr
    C.SEALED_IDS.update(json.loads((C.WORK / "sealed_ids.json").read_text()))
    pool = pd.read_parquet(C.WORK / "pool.parquet")
    ind = pd.read_parquet(C.OUT / "indicators" / "concept_year_indicators.parquet")
    assert not (set(ind.concept_id) & C.SEALED_IDS), "held-out concept leaked into indicators"
    logger.info(f"indicators: {len(ind)} rows, {ind.concept_id.nunique()} concepts")

    # ---- 5. labels (primary E; E_alt = pre-declared pool-only-percentile sensitivity used as the secondary label)
    lab, lab_info = AE.build_labels(ind, pool)
    (C.OUT / "labels").mkdir(exist_ok=True)
    lab.to_parquet(C.OUT / "labels" / "emergence_screen.parquet", index=False)
    lab.to_csv(C.OUT / "labels" / "emergence_screen.csv", index=False)
    labs = {"E": lab, "E_alt": AE.assign_groups(lab, "E_alt"), "E_up": AE.assign_groups(lab, "E_up")}
    # ---- leakage test (fails loudly)
    leak = leakage_test(lab, ind)
    # ---- 6. event study, 8. patterns per label variant
    (C.OUT / "event_study").mkdir(exist_ok=True)
    (C.OUT / "patterns").mkdir(exist_ok=True)
    es_all, pat_all, pats, match_all = {}, {}, {}, {}
    for tag, lb in labs.items():
        sfx = "" if tag == "E" else f"_{tag}"
        es, contrib, matches = AE.run_event_study(lb, ind)
        es["label"] = tag
        es_all[tag], match_all[tag] = es, matches
        contrib.to_parquet(C.OUT / "event_study" / f"contrib{sfx}.parquet", index=False)
        matches.assign(controls=matches.controls.map("|".join)).to_csv(C.OUT / "event_study" / f"matches{sfx}.csv", index=False)
        (C.OUT / "event_study" / f"summary{sfx}.json").write_text(json.dumps(_clean(es), indent=1))
        pat_res, pat = AP.run_patterns(lb, ind, matches)
        pat_all[tag], pats[tag] = pat_res, pat
        pat.to_csv(C.OUT / "patterns" / f"concept_patterns{sfx}.csv", index=False)
        (C.OUT / "patterns" / f"summary{sfx}.json").write_text(json.dumps(_clean(pat_res), indent=1))
    # ---- 7. prediction
    pred, preds = APr.run_prediction(lab, ind)
    (C.OUT / "prediction").mkdir(exist_ok=True)
    if not preds.empty:
        preds.to_parquet(C.OUT / "prediction" / "predictions.parquet", index=False)
    (C.OUT / "prediction" / "summary.json").write_text(json.dumps(_clean(pred), indent=1))
    agree = {}
    for key in ("E_h5", "E_alt_h5", "E_up_h5", "subfield_gain_reg", "cent_gain_reg"):
        ev = pred.get(key, {}).get("eval", {})
        dl = [ev.get(mm, {}).get("deltas", {}).get("FULL_vs_BASELINE", {}).get("delta") for mm in ("logit", "hgb")]
        if all(x is not None and np.isfinite(x) for x in dl):
            agree[key] = dict(logit=dl[0], hgb=dl[1], same_sign=bool(np.sign(dl[0]) == np.sign(dl[1])))
    pred["logit_hgb_sign_agreement"] = agree
    (C.OUT / "prediction" / "summary.json").write_text(json.dumps(_clean(pred), indent=1))
    # ---- 9. typology (emerging rates reported for every label variant)
    typ, asg = AP.run_typology(ind, lab, pats["E"])
    if not asg.empty:
        for tag in ("E_alt", "E_up"):
            gv = labs[tag].drop_duplicates("concept_id").set_index("concept_id").group
            asg[f"group_{tag}"] = asg.concept_id.map(gv)
            er = asg[asg[f"group_{tag}"].isin(["emerging", "never"])]
            typ[f"emerging_rate_by_cluster_{tag}"] = {str(k): dict(n=len(g), rate=float((g[f"group_{tag}"] == "emerging").mean()))
                                                      for k, g in er.groupby("cluster")}
    (C.OUT / "typology").mkdir(exist_ok=True)
    if not asg.empty:
        asg.to_parquet(C.OUT / "typology" / "assignments.parquet", index=False)
        asg.to_csv(C.OUT / "typology" / "assignments.csv", index=False)
    (C.OUT / "typology" / "medoids.json").write_text(json.dumps(_clean(dict(medoids=typ.get("medoids"),
                                                                           cluster_mean_series=typ.get("cluster_mean_series"))), indent=1))
    (C.OUT / "typology" / "stability.json").write_text(json.dumps(_clean({k: v for k, v in typ.items()
                                                                          if k not in ("medoids", "cluster_mean_series")}), indent=1))
    # ---- snapshot / robustness summaries
    snaps = pd.DataFrame([json.loads((C.WORK / "snapshots" / f"info_y{y}.json").read_text()) for y in S["years"]])
    snaps.to_csv(C.OUT / "snapshot_summary.csv", index=False)
    events = pd.read_parquet(C.WORK / "communities" / "alluvial_events.parquet")
    robust = json.loads((C.OUT / "robustness.json").read_text()) if (C.OUT / "robustness.json").exists() else {}
    ind_summ = json.loads((C.OUT / "indicators" / "indicator_summary.json").read_text())
    figs = figures(_clean(es_all), _clean(pred), _clean(pat_all["E_up"]), _clean(typ), snaps, events)
    figs += fig_trajectories(ind, labs)

    # ---- 10. method_out.json (exp_gen_sol_out)
    d = APr.build_rows(lab, ind)
    feat_cols = sorted({f for fs in APr.FEATURE_SETS.values() for f in fs})
    hk = pred["headline"]
    targets = {"E": pred[hk]["target"] if hk else "E", "Ealt": "E_alt", "Eup": "E_up"}
    sc = {}
    if not preds.empty:
        for short, tgt in targets.items():
            pp = preds[preds.target == tgt]
            for (mdl, fs), g in pp.groupby(["model", "featureset"]):
                sc[(short, mdl, fs)] = {(c, int(tt)): float(s) for c, tt, s in zip(g.concept_id, g.t, g.y_score)}
    patd = pats["E"].set_index("concept_id").to_dict("index")
    clu = asg.set_index("concept_id").cluster.to_dict() if not asg.empty else {}
    phrase = pool.set_index("concept_id").phrase.to_dict()
    lab_alt = labs["E_alt"].drop_duplicates("concept_id").set_index("concept_id")
    examples = []
    for r in d.itertuples(index=False):
        rd = r._asdict()
        key = (r.concept_id, int(r.t))
        feats = {f: (None if not np.isfinite(float(rd[f])) else round(float(rd[f]), 6)) for f in feat_cols}
        ex = dict(input=json.dumps(dict(concept_id=r.concept_id, phrase=phrase.get(r.concept_id), t=int(r.t), features_le_t=feats)),
                  output=str(int(r.E)))
        for short in targets:
            for mdl in ("logit", "hgb"):
                for fs, nm in (("BASELINE", "baseline"), ("FULL", "full"), ("A_freq_burst", "freq_burst"),
                               ("B_degree_centrality", "degree_centrality"), ("C_entropy", "entropy"), ("PREC_only", "prec_only")):
                    v = sc.get((short, mdl, fs), {}).get(key)
                    suffix = "" if short == "E" else f"_{short}"
                    ex[f"predict_{nm}_{mdl}{suffix}"] = "NA" if v is None else f"{v:.6f}"
        pr = patd.get(r.concept_id, {})
        on_alt = lab_alt.onset.get(r.concept_id, np.nan)
        ex.update(metadata_concept_id=r.concept_id, metadata_t=int(r.t), metadata_age=int(r.age), metadata_fold="screen",
                  metadata_F_band=r.F_band, metadata_origin_group=r.origin_group,
                  metadata_onset=None if not np.isfinite(r.onset) else int(r.onset), metadata_group=r.group,
                  metadata_onset_E_alt=None if not np.isfinite(on_alt) else int(on_alt),
                  metadata_group_E_alt=lab_alt.group.get(r.concept_id),
                  metadata_E_up=int(r.E_up), metadata_E_cg=int(r.E_cg), metadata_E3=int(r.E3), metadata_E_alt=int(r.E_alt),
                  metadata_subfield_gain=None if not np.isfinite(r.subfield_gain) else float(r.subfield_gain),
                  metadata_cent_gain=None if not np.isfinite(r.cent_gain) else float(r.cent_gain),
                  metadata_sense_check_fail=bool(r.sense_check_fail), metadata_prediction_target=targets["E"],
                  metadata_patterns={k: bool(pr.get(f"{k}__age0_8", False)) for k in AP.PATS},
                  metadata_cluster=None if r.concept_id not in clu else int(clu[r.concept_id]))
        examples.append(ex)
    mo = dict(metadata=dict(method_name="RQ1 volume-normalised structural precursors of concept emergence",
                            description="Rolling-origin prediction of network-only emergence (screen fold). output = primary E(c,t). "
                                        "predict_<featureset>_<model>[_Ealt|_Eup] are pooled out-of-sample scores at test origins for "
                                        "the primary label, the pool-percentile label E_alt and uptake-only E_up ('NA' = training-only row). "
                                        "BASELINE = frequency/burst + degree/centrality growth + entropy growth; FULL = BASELINE + precursors.",
                            spec_sha256=h, headline=hk, feature_sets=APr.FEATURE_SETS),
              datasets=[dict(dataset="rq1_concept_years", examples=examples)])
    (C.ROOT / "method_out.json").write_text(json.dumps(_clean(mo), indent=1))

    # ---- results summary
    ver = verdicts(_clean(es_all), _clean(pred), _clean(pat_all), _clean(typ))
    summary = dict(
        spec_sha256=h, substrate="gen_art_dataset_2 background sample (primary); dataset_4 corpus used as substrate cross-check",
        label_note=("Primary E uses the strength percentile among ALL snapshot nodes (background legacy concepts + pool); pool "
                    "concepts sit in the bottom ~5% so a 20-point gain is rare -> primary results are an UNDERPOWERED PILOT. "
                    "E_alt (pre-declared sensitivity: percentile among pool+reference nodes only) is reported as the secondary label; "
                    "it was promoted to a full analysis AFTER seeing primary n_emerging, which is disclosed here."),
        counts=dict(n_active=len(pool), n_screen=int((pool.fold == "screen").sum()), n_reference=int((pool.fold == "reference").sum()),
                    n_heldout_sealed=len(C.SEALED_IDS), n_indicator_rows=len(ind)),
        snapshots=dict(per_year=snaps[["year", "n_works", "n_nodes", "n_edges", "n_kept_edges", "n_kept_nodes", "n_comm",
                                       "n_comm_ge5", "modularity", "btw_nodes", "n_pool_active"]].to_dict("records"),
                       alluvial_events=events.event.value_counts().to_dict(), n_persistent=int(events[events.event == "birth"].pid.nunique())),
        robustness=robust, indicator_checks=ind_summ, labels=lab_info, leakage_test=leak,
        event_study={tag: {k: v for k, v in es.items() if k != "table"} for tag, es in es_all.items()},
        event_study_table={tag: [{k: t.get(k) for k in ("family", "version", "indicator", "S", "ci", "p", "p_holm", "mde", "mde_in_sd",
                                                        "n_treated", "n_k", "diff_k", "ci_k", "sign_as_predicted", "q_bh",
                                                        "ci_change_500_vs_1000")} for t in es["table"]] for tag, es in es_all.items()},
        prediction=pred, patterns=pat_all, typology={k: v for k, v in typ.items() if k not in ("medoids",)},
        figures=figs, verdicts=ver, runtime_min=round((time.time() - t0) / 60, 1))
    (C.ROOT / "results_summary.json").write_text(json.dumps(_clean(summary), indent=1))
    logger.info(f"VERDICTS: {json.dumps(_clean(ver), indent=1)}")
    logger.info(f"method done in {(time.time()-t0)/60:.1f} min")

if __name__ == "__main__":
    main()
