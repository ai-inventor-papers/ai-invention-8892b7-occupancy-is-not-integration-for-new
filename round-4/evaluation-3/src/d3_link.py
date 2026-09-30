#!/usr/bin/env python3
"""S5 D3: across concepts, does lower EARLY closure (exp_6 openness, ages 3-5) go with a higher mean partner host share
at LATER host entries (exp_7 A_cont, e >= F+6)? Executes the frozen d3_spec.json (hash checked against
logs/eval_freeze_log.jsonl): screen first, then held-out (sealed W1 rows, sidecar hashes verified before reading).

Outputs: results/d3/d3_results.json, results/d3/d3_table.csv, results/d3/d3_concepts_{screen,heldout}.csv,
figures/F2_d3_scatter.{png,pdf}.
"""
from __future__ import annotations

import hashlib
import json
import math
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from loguru import logger
from scipy import stats

WS = Path(__file__).resolve().parent
sys.path.insert(0, str(WS / "src_eval"))
import d3core as D  # noqa: E402

logger.remove()
logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
logger.add(WS / "logs" / "d3_link.log", rotation="30 MB", level="DEBUG")
OUT = WS / "results" / "d3"
FIG = WS / "figures"


def check_spec() -> dict:
    p = WS / "d3_spec.json"
    h = hashlib.sha256(p.read_bytes()).hexdigest()
    logged = None
    for line in (WS / "logs" / "eval_freeze_log.jsonl").read_text().splitlines():
        r = json.loads(line)
        if r["file"] == "d3_spec.json":
            logged = r["sha256"]
    if h != logged:
        raise SystemExit(f"REFUSED: d3_spec.json sha {h[:12]} != frozen {str(logged)[:12]}")
    return json.loads(p.read_text()) | {"_sha256": h}


# ----------------------------------------------------------------------------- frames
def build(fold: str, pop: pd.DataFrame, spec: dict, volume: pd.Series, onset: dict | None = None) -> tuple[pd.DataFrame, dict]:
    a0, a1, lag, src = D.LADDER[spec["timing_level"]]
    P = pop[(pop.fold == fold) & pop.MAIN]
    o = D.openness(fold)
    ev = D.events(fold)
    ex = D.exported(fold).set_index("concept_id")
    X = D.exposure(o, P, "closure", a0, a1, onset)
    Y = D.outcome(ev, P, lag, spec["outcome"]["Y2_threshold"])
    Yex = D.outcome(ev, P, lag, None, col="A_cont_ex").rename(columns={"Y": "Y_ex", "n_events": "n_events_ex"})
    f = P.set_index("concept_id")[["F", "origin5", "origin_group", "route"]].join(X, how="left").join(Y, how="left").join(Yex, how="left")
    for col, name in (("closure_res", "X_res"), ("constraint", "X_constraint"), ("xcomm_exc", "X_xcomm")):
        f = f.join(D.exposure(o, P, col, a0, a1, onset)[["X"]].rename(columns={"X": name}), how="left")
    f = f.join(D.h_end(o, P, a0, a1), how="left")
    f["Y3"] = ex["mean_A_cont"].reindex(f.index)
    f["log_vol_early"] = volume.reindex(f.index)
    f["log_n_events"] = np.log(f.n_events)
    ids6, ids7 = set(o.concept_id), set(ev.concept_id)
    flow = dict(n_MAIN=len(P), n_hasX=int(f.X.notna().sum()), n_hasY=int(f.Y.notna().sum()),
                n_both=int((f.X.notna() & f.Y.notna()).sum()),
                overlap_exp6_exp7_all=len(ids6 & ids7), overlap_exp6_exp7_MAIN=len(ids6 & ids7 & set(P.concept_id)),
                n_exp6_concepts=len(ids6), n_exp7_main_arm_concepts=len(ids7))
    f["fold"] = fold
    return f.reset_index().rename(columns={"index": "concept_id"}), flow


def covariates(f: pd.DataFrame, extra: list[str] | None = None, fold_dummy: bool = False) -> tuple[pd.DataFrame, list[str]]:
    Dm, g = D.origin_dummies(f.origin5.reset_index(drop=True))
    Z = pd.DataFrame({"log_vol_early": f.log_vol_early.values, "log_n_events": f.log_n_events.values})
    Z = pd.concat([Z, Dm.reset_index(drop=True)], axis=1)
    rank_cols = ["log_vol_early"]
    for e in extra or []:
        Z[e] = f[e].values
        rank_cols.append(e)
    if fold_dummy:
        Z["fold_heldout"] = (f.fold.values == "heldout").astype(float)
    return Z, rank_cols


def analyse(f: pd.DataFrame, spec: dict, xcol: str = "X", ycol: str = "Y", extra: list[str] | None = None,
            fold_dummy: bool = False, label: str = "") -> dict:
    t0 = time.time()
    need = [xcol, ycol, "log_vol_early", "log_n_events"] + (extra or [])
    d = f[np.all(np.isfinite(f[need].astype(float).values), axis=1)].reset_index(drop=True)
    n = len(d)
    if n < 10:
        return dict(label=label, n=n, note="too few concepts")
    x, y = d[xcol].values.astype(float), d[ycol].values.astype(float)
    Z, rc = covariates(d, extra, fold_dummy)
    k = Z.shape[1]
    raw = stats.spearmanr(x, y)
    st = spec["statistic"]
    bt = D.boot_ci(x, y, Z, rc, st["bootstrap"]["B"], st["bootstrap"]["seed"])
    pm = D.freedman_lane(x, y, Z, rc, st["permutation"]["n"], st["permutation"]["seed"])
    rb = D.boot_ci(x, y, None, [], st["bootstrap"]["B"], st["bootstrap"]["seed"])
    res = dict(label=label, x=xcol, y=ycol, n=n, k_covariates=k, covariate_columns=list(Z.columns),
               origin_counts=d.origin5.value_counts().to_dict(),
               raw_rho=float(raw.statistic), raw_p_two=float(raw.pvalue), raw_ci=rb["ci"],
               partial_rho=bt["rho"], ci=bt["ci"], ci_bca=bt["ci_bca"], se_boot=bt["se_boot"],
               p_one_neg=pm["p_one_neg"], p_one_pos=pm["p_one_pos"], p_two_perm=pm["p_two"],
               perm_null_mean=pm["perm_mean"], perm_null_sd=pm["perm_sd"],
               mde_rho=D.mde_rho(n, k), power_at_screen_rho=None, secs=round(time.time() - t0, 2))
    assert abs(pm["rho_obs"] - bt["rho"]) < 1e-10, "partial rho mismatch between bootstrap and permutation paths"
    logger.info(f"[{label}] n={n} k={k} raw={res['raw_rho']:+.3f} partial={res['partial_rho']:+.3f} "
                f"CI[{res['ci'][0]:+.3f},{res['ci'][1]:+.3f}] p1={res['p_one_neg']:.4f} MDE={res['mde_rho']:.3f}")
    return res


def decide(scr: dict, ho: dict) -> dict:
    rev = [nm for nm, r in (("screen", scr), ("heldout", ho)) if r.get("n", 0) >= 10 and r["partial_rho"] > 0 and r["ci"][0] > 0]
    screen_pass = scr["partial_rho"] < 0 and scr["p_one_neg"] < 0.05
    ho_pass = ho.get("n", 0) >= 10 and ho["partial_rho"] < 0 and ho["p_one_neg"] < 0.05
    if rev:
        dec = "REVERSED"
    elif not screen_pass:
        dec = "NULL"
    elif ho_pass:
        dec = "KEPT"
    else:
        dec = "SCREEN_ONLY"
    note = {"KEPT": "'one mechanism at two scales' sentence retained",
            "SCREEN_ONLY": "sentence dropped; reported as a lead; held-out MDE quoted",
            "NULL": "sentence dropped; the paper reports two separate findings",
            "REVERSED": f"tension reported (fold(s) {rev} partial rho > 0 with CI excluding 0)"}[dec]
    if dec == "SCREEN_ONLY" and ho["partial_rho"] >= 0:
        note += "; held-out sign not replicated (rho >= 0, CI includes 0)"
    return dict(decision=dec, screen_pass=bool(screen_pass), heldout_pass=bool(ho_pass), reversed_folds=rev, consequence=note)


def figure(frames: dict, res: dict) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from statsmodels.nonparametric.smoothers_lowess import lowess
    fig, axes = plt.subplots(2, 2, figsize=(10, 8.4))
    for j, fold in enumerate(("screen", "heldout")):
        f = frames[fold]
        d = f[np.isfinite(f.X) & np.isfinite(f.Y) & np.isfinite(f.log_vol_early)].reset_index(drop=True)
        r = res["primary"][fold]
        ax = axes[0, j]
        for g, sub in d.groupby("origin5"):
            ax.scatter(sub.X, sub.Y, s=16, alpha=0.7, label=f"{g} ({len(sub)})")
        lw = lowess(d.Y, d.X, frac=0.6)
        ax.plot(lw[:, 0], lw[:, 1], color="k", lw=2)
        ax.set_xlabel("early closure X (mean top-20 Chung-Lu log-ratio, ages 3-5)")
        ax.set_ylabel("later anchoring Y (mean A_cont, entries e >= F+6)")
        ax.set_title(f"{fold}: n={r['n']}, raw rho={r['raw_rho']:+.2f}")
        ax.legend(fontsize=7, loc="upper right")
        # partial residual ranks
        Z, rc = covariates(d)
        Xd = D.design(D.prep_Z(Z, rc), len(d))
        ex, ey = D.resid(D.avg_rank(d.X.values), Xd), D.resid(D.avg_rank(d.Y.values), Xd)
        ax = axes[1, j]
        ax.scatter(ex, ey, s=16, alpha=0.7, color="tab:gray")
        lw = lowess(ey, ex, frac=0.6)
        ax.plot(lw[:, 0], lw[:, 1], color="tab:red", lw=2)
        ax.axhline(0, color="k", lw=0.5)
        ax.axvline(0, color="k", lw=0.5)
        ax.set_xlabel("rank(X) residual | volume, origin, log n events")
        ax.set_ylabel("rank(Y) residual")
        ax.set_title(f"partial rho={r['partial_rho']:+.2f} [{r['ci'][0]:+.2f},{r['ci'][1]:+.2f}], "
                     f"p1={r['p_one_neg']:.3f}, MDE={r['mde_rho']:.2f}", fontsize=9)
    fig.suptitle(f"F2. D3: early closure vs later host-entry anchoring (decision: {res['decision']['decision']})")
    fig.tight_layout()
    FIG.mkdir(exist_ok=True)
    fig.savefig(FIG / "F2_d3_scatter.png", dpi=150)
    fig.savefig(FIG / "F2_d3_scatter.pdf")
    plt.close(fig)


def describe(f: pd.DataFrame) -> dict:
    d = f[np.isfinite(f.X) & np.isfinite(f.Y)]
    q = lambda s: {k: float(v) for k, v in zip(["min", "q25", "median", "q75", "max"], np.quantile(s, [0, .25, .5, .75, 1]))} | {"mean": float(s.mean()), "sd": float(s.std(ddof=1))}
    return dict(X=q(d.X), Y=q(d.Y), n_events=q(d.n_events), n_X_years=q(d.n_X_years))


@logger.catch(reraise=True)
def main() -> None:
    t_start = time.time()
    spec = check_spec()
    logger.info(f"d3_spec sha256 {spec['_sha256'][:12]} verified; timing level {spec['timing_level']}")
    OUT.mkdir(parents=True, exist_ok=True)
    pop = D.population()
    main_ids = set(pop.loc[pop.MAIN, "concept_id"])
    volume = D.early_volume(main_ids, pop.set_index("concept_id").F.to_dict())
    lab = pd.read_parquet(D.EXP5C / "results" / "labels" / "labels_screen.parquet", columns=["concept_id", "group_E_up", "onset_E_up"])
    lab = lab.drop_duplicates("concept_id")
    onset = {c: int(o) for c, g, o in zip(lab.concept_id, lab.group_E_up, lab.onset_E_up) if g == "emerging" and np.isfinite(o)}
    res: dict = dict(spec_sha256=spec["_sha256"], timing_level=spec["timing_level"], primary={}, raw={}, sensitivities={},
                     flow={}, descriptives={}, secondary={})
    frames = {}
    # ---------------- screen first, then held-out (sealed sidecars verified inside d3core)
    for fold in ("screen", "heldout"):
        f, flow = build(fold, pop, spec, volume)
        frames[fold] = f
        res["flow"][fold] = flow
        res["descriptives"][fold] = describe(f)
        f.to_csv(OUT / f"d3_concepts_{fold}.csv", index=False)
        res["primary"][fold] = analyse(f, spec, label=f"primary|{fold}")
        S = res["sensitivities"].setdefault(fold, {})
        res["secondary"][fold] = dict(Y2=analyse(f, spec, ycol="Y2", label=f"Y2|{fold}"),
                                      Y3=analyse(f, spec, ycol="Y3", label=f"Y3|{fold}"))
        S["S1_closure_res"] = analyse(f, spec, xcol="X_res", label=f"S1|{fold}")
        if fold == "screen":
            f2, _ = build(fold, pop, spec, volume, onset=onset)
            S["S2_pre_onset"] = analyse(f2, spec, label=f"S2|{fold}")
            S["S2_pre_onset"]["n_emerging_in_sample"] = int(f2[np.isfinite(f2.X) & np.isfinite(f2.Y)].concept_id.isin(set(onset)).sum())
        S["S3_plus_H_W1"] = analyse(f, spec, extra=["H_end"], label=f"S3|{fold}")
        S["S4_A_cont_ex"] = analyse(f, spec, ycol="Y_ex", label=f"S4|{fold}")
        S["S5_no_physics"] = analyse(f[f.origin5 != "Physics&Astronomy"], spec, label=f"S5|{fold}")
        S["S6_min2_events"] = analyse(f[f.n_events >= 2], spec, label=f"S6|{fold}")
        S["S7_constraint_EXPLORATORY"] = analyse(f, spec, xcol="X_constraint", label=f"S7c|{fold}")
        S["S7_xcomm_exc_EXPLORATORY"] = analyse(f, spec, xcol="X_xcomm", label=f"S7x|{fold}")
    pooled = pd.concat([frames["screen"], frames["heldout"]], ignore_index=True)
    res["sensitivities"]["pooled"] = {"S8_fold_pooled": analyse(pooled, spec, fold_dummy=True, label="S8|pooled")}
    res["decision"] = decide(res["primary"]["screen"], res["primary"]["heldout"])
    ho = res["primary"]["heldout"]
    res["heldout_power_at_screen_rho"] = D.power_rho(res["primary"]["screen"]["partial_rho"], ho["n"], ho["k_covariates"])
    res["wall_secs"] = round(time.time() - t_start, 1)
    res["disclosures"] = [
        "exposure is an early-life window (ages 3-5), not literally pre-onset; S2 gives the literal pre-onset version on the screen",
        "cross-sectional across concepts: supports an association, not a mechanism",
        "held-out early volume (F..F+5) reads dataset_5 link counts that may extend past 2015 for late-F concepts; it is a single "
        "per-concept mean, no E_up label is computed here",
        "Y3 (exported mean) has no timing restriction and overlaps the exposure window",
        "population is arXiv-skewed (physics/CS); S5 reports the non-physics subset"]
    logger.info(f"D3 decision: {res['decision']}")
    (OUT / "d3_results.json").write_text(json.dumps(res, indent=1, default=float))
    rows = []
    for fold in ("screen", "heldout"):
        allr = {"primary": res["primary"][fold], **{f"secondary_{k}": v for k, v in res["secondary"][fold].items()},
                **res["sensitivities"][fold]}
        for nm, r in allr.items():
            rows.append(dict(fold=fold, analysis=nm, **{k: r.get(k) for k in ("x", "y", "n", "k_covariates", "raw_rho", "partial_rho",
                                                                             "p_one_neg", "p_two_perm", "mde_rho")},
                             ci_lo=r.get("ci", [None, None])[0], ci_hi=r.get("ci", [None, None])[1],
                             bca_lo=r.get("ci_bca", [None, None])[0], bca_hi=r.get("ci_bca", [None, None])[1]))
    r = res["sensitivities"]["pooled"]["S8_fold_pooled"]
    rows.append(dict(fold="pooled", analysis="S8_fold_pooled", x="X", y="Y", n=r["n"], k_covariates=r["k_covariates"],
                     raw_rho=r["raw_rho"], partial_rho=r["partial_rho"], p_one_neg=r["p_one_neg"], p_two_perm=r["p_two_perm"],
                     mde_rho=r["mde_rho"], ci_lo=r["ci"][0], ci_hi=r["ci"][1], bca_lo=r["ci_bca"][0], bca_hi=r["ci_bca"][1]))
    pd.DataFrame(rows).to_csv(OUT / "d3_table.csv", index=False)
    figure(frames, res)
    logger.info(f"D3 done in {res['wall_secs']} s")


if __name__ == "__main__":
    main()
