#!/usr/bin/env python3
"""Fit every G row (G1 multi-team window, G2 native/adjacent/foreign, G3 classifier circularity + placebo host)
for one fold, under the frozen g_spec.json (refuses if its sha256 or the G code hashes changed).

  python g/g_run.py --fold screen     # Step 2
  python g/g_run.py --fold heldout    # Step 5 (supplementary; needs the opening lock and held-out G features)
  python g/g_run.py --fold pooled     # Step 5 (screen + held-out; the concept FE absorbs the fold)

Writes results/g_<fold>_rows.csv, results/g_<fold>_summary.json, results/g_placebo_host_draws_<fold>.csv
"""
from __future__ import annotations

import argparse
import json
import time

import numpy as np
import pandas as pd

import g_lib as L
import g_samples as S
from g_lib import logger

X2 = ["A_cont", "CT"] + L.CTRL2
X1 = ["A_cont", "CT"] + L.CTRL


def check_code(spec: dict) -> list[str]:
    """G code hashes at the freeze; a change (bug fix) is recorded as a deviation, never silently."""
    changed = [rel for rel, h in spec["code_sha256_at_freeze"].items() if L.sha256_file(L.EVAL / rel) != h]
    for rel in changed:
        logger.warning(f"{rel} changed after the freeze (see results/deviations_g.md)")
    return changed


def g2_reading(nat: dict, adj: dict) -> str:
    if nat.get("irr_sd") is None or adj.get("irr_sd") is None:
        return "unresolved (fit failed)"
    nsig, asig = nat["irr_sd_lo"] > 1, adj["irr_sd_lo"] > 1
    if nsig and asig:
        return ("grafting" if nat["irr_sd"] >= adj["irr_sd"] else "host-vocabulary") + " (both)"
    if nsig and nat["irr_sd"] >= adj["irr_sd"]:
        return "grafting"
    if asig and adj["irr_sd"] >= nat["irr_sd"]:
        return "host-vocabulary"
    if nsig or asig:  # significant but with the smaller per-SD effect: the frozen rule gives no label
        return "unresolved (significant term has the smaller per-SD effect)"
    return "unresolved"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fold", required=True, choices=["screen", "heldout", "pooled"])
    ap.add_argument("--smoke", action="store_true", help="code test on RANDOM outcomes against the draft spec")
    a = ap.parse_args()
    fold = a.fold
    L.setup_logging(f"g_run_{fold}{'_smoke' if a.smoke else ''}")
    if a.smoke:
        spec = json.loads((L.RES / "g_spec_draft.json").read_text())
        changed = []
    else:
        spec = L.assert_spec_frozen()
        changed = check_code(spec)
    if fold != "screen" and not (L.D2 / "results" / "HELDOUT_OPENED.lock").exists():
        raise SystemExit("REFUSED: held-out / pooled G rows need the opening lock")
    P = dict(spec["parameters"])
    if a.smoke:
        P.update(pct_bootstrap_reps=12, placebo_host_draws=6)
    boot = P["pct_bootstrap_reps"]
    rng = np.random.default_rng(L.SEED)
    zsd = L.placebo_z_sd()
    G = L.io_load_prepare()
    win, cop = S.load(fold)
    if a.smoke:  # random outcomes: exercises every code path without reading a real coefficient
        rs_ = np.random.default_rng(1)
        win["Y_strict"] = rs_.poisson(np.log1p(win.n_win.fillna(1)) * 2)
        for c in ("Y_strict", "Y_strict_hc", "Y_strict_shift"):
            cop[c] = np.where(cop[c].notna(), rs_.poisson(np.log1p(cop.n_entry_papers) * 2, len(cop)), np.nan)
    out_dir = L.RES / "smoke" if a.smoke else L.RES
    out_dir.mkdir(exist_ok=True)
    ws = S.window_samples(win, fold)
    sc = S.coprimary_sample(cop, fold)
    rows: list[dict] = []
    summ: dict = {"fold": fold, "smoke": a.smoke, "g_spec_sha256": None if a.smoke else L.sha256_file(L.G_SPEC),
                  "code_changed_after_freeze": changed, "placebo_z_sd_used": zsd}
    t0 = time.time()

    def add(name, s, y, xs, spec_name, targets, family="", extra=None):
        r = L.fit_row(name, s, y, xs, spec_name, targets, fold=fold, family=family, zsd=zsd, rng=rng, extra=extra)
        rows.extend(r)
        return {x["var"]: x for x in r}

    # ------------------------------------------------------------------ G1
    g1 = {}
    g1["multi"] = add("G1-multi (co-primary FE)", ws["G1_multi"], "Y_strict", X2, "secondary", ["A_cont", "CT"],
                      family="G_headline", extra={"test": "G1"})
    g1["multi_cdxe"] = add("G1-multi (concept + d x e FE)", ws["G1_multi"], "Y_strict", X1, "c_plus_dxe",
                           ["A_cont", "CT"], extra={"test": "G1"})
    g1["multi_primary"] = add("G1-multi (primary FE concept x e + d x e)", ws["G1_multi"], "Y_strict", X1, "primary",
                              ["A_cont", "CT"], extra={"test": "G1"})
    g1["multi_main"] = add("G1-multi, MAIN only", ws["G1_multi_MAIN"], "Y_strict", X2, "secondary", ["A_cont", "CT"],
                           extra={"test": "G1"})
    g1["single"] = add("G1-single complement", ws["G1_single"], "Y_strict", X2, "secondary", ["A_cont", "CT"],
                       extra={"test": "G1"})
    g1["all"] = add("G1-all-window", ws["G1_all_window"], "Y_strict", X2, "secondary", ["A_cont", "CT"],
                    extra={"test": "G1"})
    gi = add("G1-interaction (A_cont x multi)", ws["G1_all_window"], "Y_strict",
             ["A_cont", "A_x_multi", "multi_f", "CT"] + L.CTRL2, "secondary", ["A_cont", "A_x_multi", "multi_f"],
             extra={"test": "G1"})
    if gi["A_x_multi"].get("b") is not None:
        sd = gi["A_cont"]["sd_retained"]
        summ["G1_interaction"] = {"irr_sd_single": float(np.exp(gi["A_cont"]["b"] * sd)),
                                  "irr_sd_multi": float(np.exp((gi["A_cont"]["b"] + gi["A_x_multi"]["b"]) * sd)),
                                  "ratio_irr_multi_over_single": float(np.exp(gi["A_x_multi"]["b"] * sd)),
                                  "p_interaction": gi["A_x_multi"]["p"], "p_wild_interaction": gi["A_x_multi"]["p_wild"],
                                  "sd_A_used": sd}
    mw = S.refac(L.prep_sample(cop, pop="MAIN", fold=fold, need=S.A_NEED + ["A_cont_v", "CT_v", "Y_strict_shift"]))
    mw = S.refac(mw[mw.e + 6 <= 2024])
    add("G1-bridge: iteration-3 row (partner window [e,e+1], W2 [e+2,e+6], entry-year controls)", mw,
        "Y_strict_shift", ["A_cont_v", "CT_v"] + L.CTRL2, "secondary", ["A_cont_v"], extra={"test": "G1"})
    sw = ws["G1_all_window"]
    summ["G1_descriptive"] = {"n_window_events": int(len(sw)), "n_multi": int(sw.multi.sum()),
                              "share_multi": float(sw.multi.mean()),
                              "share_multi_among_MAIN": float(sw[sw.MAIN].multi.mean()),
                              "n_concepts_multi": int(sw[sw.multi].concept_id.nunique()),
                              "share_single_paper_entry_year": float(sw.single_paper_e.mean())}
    m = g1["multi"]["A_cont"]
    mde_key = {"screen": "G1_multi_screen", "heldout": "G1_multi_heldout_projected",
               "pooled": "G1_multi_pooled_projected"}[fold]
    mde = spec["mde"][mde_key]["MDE_irr_sd_power80"]
    g1_null = m.get("irr_sd_lo") is None or (m["irr_sd_lo"] <= 1 <= m["irr_sd_hi"])
    summ["G1_status"] = {"mde_key": mde_key, "mde": mde, "G": m.get("G"), "null": bool(g1_null),
                         "underpowered_G_lt_30": bool((m.get("G") or 0) < 30),
                         "label": ("inconclusive (underpowered)" if g1_null and (mde is None or mde > 1.20)
                                   else ("null with adequate power" if g1_null else "positive (CI excludes 1)"))}
    logger.info(f"G1 done {time.time() - t0:.0f}s: {summ['G1_status']}")

    # ------------------------------------------------------------------ G2
    import placebo as PL
    arr = PL.build_arrays(G, sc)
    rec = float(np.nanmax(np.abs(PL.a_cont(arr) - sc.A_cont.to_numpy())))
    summ["G2_A_cont_reconstruction_max_abs_diff"] = rec
    grid = []
    for nc in P["g2_native_cuts"]:
        for al in P["g2_adjacent_lower_cuts"]:
            sh = L.g2_shares(arr, nc, al)
            s2 = sc.copy()
            for c in sh.columns:
                s2[c] = sh[c].to_numpy()
            head = (nc == P["g2_headline"][0] and al == P["g2_headline"][1])
            r = add(f"G2a NATIVE+ADJACENT (native>={nc}, adjacent [{al},{nc}))", s2, "Y_strict",
                    ["NAT", "ADJ", "CT"] + L.CTRL2, "secondary", ["NAT", "ADJ"],
                    family="G_headline" if head else "", extra={"test": "G2", "nat_cut": nc, "adj_lo": al})
            wd = L.wald_equal_01(s2, "Y_strict", "NAT", "ADJ", ["CT"] + L.CTRL2, "secondary")
            cell = {"nat_cut": nc, "adj_lo": al, "NAT": r["NAT"], "ADJ": r["ADJ"], "wald_equal_per01": wd,
                    "corr_NAT_ADJ": float(s2[["NAT", "ADJ"]].corr().iloc[0, 1]),
                    "mean_NAT": float(s2.NAT.mean()), "mean_ADJ": float(s2.ADJ.mean()),
                    "vif": L.vif(s2, ["NAT", "ADJ", "CT"] + L.CTRL2), "reading": g2_reading(r["NAT"], r["ADJ"])}
            grid.append(cell)
            if head:
                summ["G2a"] = cell
                rb = add("G2b exact decomposition A_nat + A_adj + A_for", s2, "Y_strict",
                         ["A_nat", "A_adj", "A_for", "CT"] + L.CTRL2, "secondary", ["A_nat", "A_adj", "A_for"],
                         extra={"test": "G2", "nat_cut": nc, "adj_lo": al})
                summ["G2b"] = {k: {kk: v.get(kk) for kk in ("irr_sd", "irr_sd_lo", "irr_sd_hi", "irr_01", "p", "p_wild")}
                               for k, v in rb.items()}
    summ["G2_grid"] = [{"nat_cut": c["nat_cut"], "adj_lo": c["adj_lo"], "reading": c["reading"],
                        "NAT_irr_sd": c["NAT"].get("irr_sd"), "NAT_ci": [c["NAT"].get("irr_sd_lo"), c["NAT"].get("irr_sd_hi")],
                        "ADJ_irr_sd": c["ADJ"].get("irr_sd"), "ADJ_ci": [c["ADJ"].get("irr_sd_lo"), c["ADJ"].get("irr_sd_hi")],
                        "N": c["NAT"].get("N"), "G": c["NAT"].get("G"), "wald_p": c["wald_equal_per01"].get("p"),
                        "corr": c["corr_NAT_ADJ"]} for c in grid]
    logger.info(f"G2 done {time.time() - t0:.0f}s: reading {summ['G2a']['reading']}")

    # ------------------------------------------------------------------ G3
    base = add("G3 base: co-primary (reports mean_topic_score = G3(i))", sc, "Y_strict", X2, "secondary",
               ["A_cont", "CT", "mean_topic_score"], extra={"test": "G3"})
    summ["G3_i_mean_topic_score"] = base["mean_topic_score"]
    blocks = {"G3(i+) + min_topic_score": ["min_topic_score"],
              "G3(ii) + host_topic_share + sec_host_share": ["host_topic_share", "sec_host_share"],
              "G3(combined)": ["min_topic_score", "host_topic_share", "sec_host_share"]}
    summ["G3_pct"] = {}
    for name, extra in blocks.items():
        s3 = S.refac(sc.dropna(subset=extra))
        fam = "G_headline" if name == "G3(combined)" else ""
        add(name, s3, "Y_strict", X2 + extra, "secondary", ["A_cont"] + extra, family=fam, extra={"test": "G3"})
        summ["G3_pct"][name] = L.pct_removed(s3, "Y_strict", X2, X2 + extra, "secondary", reps=boot)
        logger.info(f"{name}: pct {summ['G3_pct'][name].get('pct')} ({time.time() - t0:.0f}s)")
    s9 = S.refac(sc[sc.min_topic_score >= 0.9])
    add("G3 restriction: entry papers topic_score >= 0.9", s9, "Y_strict", X2, "secondary", ["A_cont"],
        extra={"test": "G3"})
    sv = S.refac(sc[sc.n_venue_covered_papers > 0].dropna(subset=["venue_d_share"]))
    add("G3(iii) venue agreement (coverage-limited)", sv, "Y_strict", X2 + ["venue_d_share"], "secondary",
        ["A_cont", "venue_d_share"], extra={"test": "G3"})
    add("G3(iii) base on venue-covered events", sv, "Y_strict", X2, "secondary", ["A_cont"], extra={"test": "G3"})
    summ["G3_pct"]["G3(iii) + venue_d_share"] = L.pct_removed(sv, "Y_strict", X2, X2 + ["venue_d_share"],
                                                               "secondary", reps=boot)
    summ["G3_iii_coverage"] = {"share_events_with_covered_paper": float((sc.n_venue_covered_papers > 0).mean()),
                               "share_entry_papers_covered": float(sc.n_venue_covered_papers.sum() / sc.n_entry_papers.sum()),
                               "N_input": int(len(sv)), "G_input": int(sv.concept_id.nunique())}
    add("G3(iv) outcome Y_strict_hc (W2 papers with topic_score >= 0.9)", sc, "Y_strict_hc", X2, "secondary",
        ["A_cont"], extra={"test": "G3"})
    logger.info(f"G3 regressions done {time.time() - t0:.0f}s")
    ph = []
    summ["placebo_host"] = {}
    for k, strat in enumerate(("size", "prox")):
        d, sm = L.placebo_host(G, sc, P["placebo_host_draws"], strat, seed=L.SEED + 7000 + 1000 * k)
        ph.append(d)
        summ["placebo_host"][strat] = sm
        logger.info(f"placebo host [{strat}]: {sm}")
    pd.concat(ph).to_csv(out_dir / f"g_placebo_host_draws_{fold}.csv", index=False)

    # ------------------------------------------------------------------ Holm over the 4 headline tests
    rdf = pd.DataFrame(rows)
    hf = rdf[(rdf.family == "G_headline") & rdf["var"].isin(["A_cont", "NAT", "ADJ"])]
    pv = {f"{r.row}|{r['var']}": r.p for _, r in hf.iterrows() if pd.notna(r.get("p"))}
    hol = L.models.holm(pv)
    rdf["p_holm_G"] = [hol.get(f"{r.row}|{r['var']}") for _, r in rdf.iterrows()]
    summ["holm_G_family"] = hol
    summ["G_code_seconds"] = round(time.time() - t0, 1)
    rdf.to_csv(out_dir / f"g_{fold}_rows.csv", index=False)
    (out_dir / f"g_{fold}_summary.json").write_text(json.dumps(summ, indent=1, default=float))
    logger.info(f"[{fold}] {len(rdf)} rows written in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
