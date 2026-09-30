#!/usr/bin/env python3
"""Step 3 (post-opening): the frozen spec's robustness_to_rerun rows, secondary outcomes, the 500-draw
nativeness-permutation placebo, kill / confirmation flags, placebo-calibrated p, screen-vs-held-out heterogeneity
and a descriptive out-of-sample deviance row, all on the held-out fold. Runs only after the opening lock exists;
SEALED_IDS is cleared only here and in g_features.py --fold heldout.

Writes results/heldout_post.json, results/heldout_robustness.csv, results/heldout_placebo_draws.csv,
results/heldout_event_predictions.parquet
"""
from __future__ import annotations

import json
import multiprocessing as mp
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd
from scipy import stats

import g_lib as L
from g_lib import config, logger, models

LOCK = L.D2 / "results" / "HELDOUT_OPENED.lock"


def robustness_rows(df: pd.DataFrame, fold: str) -> pd.DataFrame:
    import robustness as R
    base = df[(df.arm == "main") & (df.fold == fold) & df.kw5].copy()
    base = base.dropna(subset=["A_cont", "CT"] + R.CTRL + R.SEC + ["Y_strict"])
    base["cxe"] = base.concept_id + "_" + base.e.astype(str)
    base["dxe"] = base.d.astype(str) + "_" + base.e.astype(str)
    base["cfe"], base["efe"], base["dfe"] = base.concept_id, base.e.astype(str), base.d.astype(str)
    base["offset"] = np.log(base.n_entry_papers.astype(float))
    main = base[base.MAIN]
    rows = []
    rows += R.fit_both("PRIMARY (MAIN)", main)
    rows += R.fit_both("STRICT population", base[base.STRICT])
    rows += R.fit_both("excess anchoring A_cont - A0_cont", main, a_var="A_cont_ex")
    rows += R.fit_both("bound A_cont_lo (unprofiled share 0)", main, a_var="A_cont_lo")
    rows += R.fit_both("bound A_cont_hi (unprofiled share 1)", main, a_var="A_cont_hi")
    rows += R.fit_both("outcome Y_lenient", main, y="Y_lenient")
    rows += R.fit_both("outcome Y_all", main, y="Y_all")
    out = pd.DataFrame(rows)
    for fg, g in main.groupby("field_group"):
        out = pd.concat([out, pd.DataFrame(R.fit_both(f"stratum {fg} (descriptive only; no subgroup search)", g))],
                        ignore_index=True)
    out["fold"] = fold
    return out


def perm_placebo(G: dict, s: pd.DataFrame, draws: int) -> tuple[pd.DataFrame, dict]:
    import placebo as PL
    arr = PL.build_arrays(G, s)
    diff = float(np.nanmax(np.abs(PL.a_cont(arr) - s.A_cont.to_numpy())))
    with ProcessPoolExecutor(config.detect_cpus(), mp_context=mp.get_context("spawn"), initializer=PL._init,
                             initargs=(s, arr)) as ex:
        res = pd.DataFrame(list(ex.map(PL._draw, [config.SEED + 91000 + i for i in range(draws)], chunksize=8)))
    summ = {"draws": draws, "A_cont_reconstruction_max_abs_diff": diff}
    for spec, xs in (("primary", models.EVENT_CONTROLS), ("secondary", models.EVENT_CONTROLS + models.SECONDARY_EXTRA)):
        r = models.fit_one(s, "Y_strict", ["A_cont", "CT"] + xs, spec)
        z = res[f"z_A_{spec}"].dropna()
        if r is None:
            summ[spec] = {"note": "observed fit failed"}
            continue
        zo = r["coef"]["A_cont"] / r["se"]["A_cont"]
        summ[spec] = {"z_A_obs": zo, "placebo_n_ok": int(len(z)), "placebo_z_mean": float(z.mean()),
                      "placebo_z_sd": float(z.std()),
                      "perm_p_two_sided_z": float((1 + (z.abs() >= abs(zo)).sum()) / (1 + len(z)))}
    return res, summ


def oos(screen: pd.DataFrame, ho: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Descriptive: iteration-3 assemble_out GLM (e, d one-hot + covariates, exposure) trained on the screen sample,
    evaluated on held-out events (unseen concepts)."""
    import assemble_out as AO
    tr, te = screen.copy(), ho.copy()
    for s in (tr, te):
        s["route_A_f"] = s.route_A.astype(float)
        s["e_s"], s["d_s"] = s.e.astype(str), s.d.astype(str)
        s["rate"] = s.Y_strict / s.n_entry_papers
    for name, num in (("mu0", AO.NUM0), ("mu1", AO.NUM1)):
        m = AO._model(num)
        m.fit(tr, tr["rate"], poissonregressor__sample_weight=tr["n_entry_papers"])
        te[name] = m.predict(te) * te["n_entry_papers"]
    y = te.Y_strict.to_numpy(float)
    d0, d1 = AO.poisson_dev(y, te.mu0.to_numpy()), AO.poisson_dev(y, te.mu1.to_numpy())
    rng = np.random.default_rng(L.SEED)
    cids = te.concept_id.to_numpy()
    grp = {c: np.flatnonzero(cids == c) for c in np.unique(cids)}
    uc = list(grp)
    diffs = []
    for _ in range(1000):
        ix = np.concatenate([grp[c] for c in rng.choice(uc, len(uc))])
        diffs.append(d1[ix].mean() - d0[ix].mean())
    res = {"n_events": int(len(te)), "n_concepts": len(uc), "mean_deviance_controls_only": float(d0.mean()),
           "mean_deviance_with_A_CT": float(d1.mean()), "deviance_diff_with_minus_controls": float(d1.mean() - d0.mean()),
           "ci95_concept_bootstrap": [float(np.quantile(diffs, .025)), float(np.quantile(diffs, .975))],
           "spearman_controls_only": float(stats.spearmanr(te.mu0, y).statistic),
           "spearman_with_A_CT": float(stats.spearmanr(te.mu1, y).statistic),
           "note": "descriptive only; trained on the screen sample, evaluated on held-out concepts (no concept FE)"}
    te["dev0"], te["dev1"] = d0, d1
    return te, res


def main() -> None:
    L.setup_logging("heldout_post")
    if not LOCK.exists():
        raise SystemExit("REFUSED: no opening lock")
    L.assert_spec_frozen()
    config.SEALED_IDS.clear()  # post-opening only
    conf = json.loads((L.D2 / "results" / "heldout_confirmation.json").read_text())
    spec = json.loads((L.D2 / "heldout_spec.json").read_text())
    scr = json.loads((L.D2 / "results" / "heldout_dryrun_on_screen.json").read_text())
    G = L.io_load_prepare()
    df = pd.read_parquet(L.RES / "g_features_heldout_coprimary.parquet")
    s = models.primary_sample(df, fold="heldout")
    out: dict = {"lock": LOCK.read_text(), "n_events": int(len(s)), "n_concepts": int(s.concept_id.nunique())}
    # consistency with the frozen opening
    chk = models.fit_one(s, "Y_strict", ["A_cont", "CT"] + models.EVENT_CONTROLS + models.SECONDARY_EXTRA, "secondary")
    out["consistency_with_confirmation"] = None if chk is None or conf.get("secondary") is None else {
        "irr_sd_A_here": chk["irr_sd"]["A_cont"], "irr_sd_A_confirm": conf["secondary"]["irr_sd"]["A_cont"],
        "abs_diff": abs(chk["irr_sd"]["A_cont"] - conf["secondary"]["irr_sd"]["A_cont"])}
    # flags
    flags = {}
    zsd = L.placebo_z_sd()
    for sp in ("primary", "secondary"):
        r = conf.get(sp)
        dec = conf.get(f"decision_{sp}")
        screen_reading = spec["screen_decisions"][sp]["reading"] if isinstance(spec["screen_decisions"][sp], dict) \
            else spec["screen_decisions"][sp]
        f = {"screen_reading": screen_reading, "heldout_reading": dec["reading"] if dec else None,
             "confirmed": bool(dec and dec["reading"] == screen_reading)}
        if r:
            b, se = r["coef"]["A_cont"], r["se"]["A_cont"]
            f.update({"irr_sd_A": r["irr_sd"]["A_cont"], "ci_A": r["ci_irr_sd"]["A_cont"], "p_A": r["p"]["A_cont"],
                      "p_wild_A": r["p_wild"]["A_cont"], "irr_sd_CT": r["irr_sd"]["CT"], "ci_CT": r["ci_irr_sd"]["CT"],
                      "p_CT": r["p"]["CT"], "N": r["n_retained"], "G": r["G"], "retained_share": r["retained_share"],
                      "z_A": b / se, "p_placebo_cal_screenSD": float(2 * stats.norm.sf(abs(b / se) / zsd[sp]))})
            bs, ses = scr[sp]["coef"]["A_cont"], scr[sp]["se"]["A_cont"]
            dz = (b - bs) / np.sqrt(se ** 2 + ses ** 2)
            f["heterogeneity_screen_vs_heldout"] = {"b_screen": bs, "b_heldout": b, "diff": b - bs,
                                                    "se": float(np.sqrt(se ** 2 + ses ** 2)),
                                                    "p": float(2 * stats.norm.sf(abs(dz)))}
        flags[sp] = f
    co = conf.get("secondary")
    dead = co is None or co["coef"]["A_cont"] < 0 or co["ci_irr_sd"]["A_cont"][0] <= 1 <= co["ci_irr_sd"]["A_cont"][1]
    flags["KILL_co_primary_dead"] = bool(dead)
    prim_null = conf.get("primary") is None or conf["primary"]["ci_irr_sd"]["A_cont"][0] <= 1
    flags["primary_label"] = ("inconclusive (underpowered)" if prim_null and not spec["power"]["adequately_powered"]["primary"]
                              else flags["primary"]["heldout_reading"])
    out["flags"] = flags
    # robustness_to_rerun + secondary outcomes
    rob = robustness_rows(df, "heldout")
    rob.to_csv(L.RES / "heldout_robustness.csv", index=False)
    out["robustness_rows"] = int(len(rob))
    out["EST_bin_LPM"] = {sp: models.lpm_fe(s, "EST_bin", ["A_cont", "CT"] + models.EVENT_CONTROLS +
                                            (models.SECONDARY_EXTRA if sp == "secondary" else []), sp)
                          for sp in ("primary", "secondary")}
    logger.info("robustness rows done")
    pl, ps = perm_placebo(G, s, 500)
    pl.to_csv(L.RES / "heldout_placebo_draws.csv", index=False)
    out["nativeness_permutation_placebo"] = ps
    if "secondary" in ps and "placebo_z_sd" in ps["secondary"] and flags["secondary"].get("z_A") is not None:
        flags["secondary"]["p_placebo_cal_heldoutSD"] = float(2 * stats.norm.sf(abs(flags["secondary"]["z_A"]) /
                                                                               ps["secondary"]["placebo_z_sd"]))
    logger.info(f"placebo: {ps}")
    # descriptive OOS + per-event predictions
    scr_df = pd.read_parquet(L.D2 / "results" / "screen_events_with_outcomes.parquet")
    ss = models.primary_sample(scr_df, fold="screen")
    te, oo = oos(ss, s)
    out["oos"] = oo
    te.to_parquet(L.RES / "heldout_event_predictions.parquet")
    # D3 hand-off hash
    p3 = L.D2 / "sealed" / "d3_concept_anchoring_heldout.parquet"
    out["d3_heldout_sha256"] = {"got": L.sha256_file(p3),
                                "want": spec["sealed_files"]["d3_concept_anchoring_heldout"]["sha256"]}
    out["d3_heldout_sha256"]["match"] = out["d3_heldout_sha256"]["got"] == out["d3_heldout_sha256"]["want"]
    (L.RES / "heldout_post.json").write_text(json.dumps(out, indent=1, default=float))
    logger.info(f"flags: {json.dumps(flags, default=float)[:1500]}")


if __name__ == "__main__":
    main()
