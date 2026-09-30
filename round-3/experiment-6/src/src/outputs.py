"""Step 10: method_out.json (exp_gen_sol_out), figures and results_summary.json (every number read from result files)."""
from __future__ import annotations

import json
import math

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from loguru import logger  # noqa: E402

import common as K  # noqa: E402
from common import FIG, OUT, WS  # noqa: E402

import stats_core as S  # noqa: E402

D1 = OUT / "d1"
OUTC = ["Y1r", "Y2", "log1p_Y3"]
OLAB = {"Y1r": "Y1r: rarefied Shannon change", "Y2": "Y2: Rao-Stirling change", "log1p_Y3": "Y3: newcomer subfields (log1p)"}
MLAB = {"closure_res_z": "closure_res (primary)", "closure_res_imp_z": "closure_res_imp (co-primary)",
        "constraint_z": "Burt constraint", "esize_norm_z": "effective size / degree", "xcomm_exc_z": "cross-community pairs"}
plt.rcParams.update({"font.size": 9, "pdf.fonttype": 42, "axes.spines.top": False, "axes.spines.right": False})


def _save(fig, name: str) -> None:
    fig.tight_layout()
    fig.savefig(FIG / f"{name}.pdf")
    fig.savefig(FIG / f"{name}.png", dpi=200)
    plt.close(fig)


def _num(v):
    if isinstance(v, (np.floating, float)):
        return None if not math.isfinite(float(v)) else round(float(v), 6)
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, (np.bool_,)):
        return bool(v)
    return v


def method_out() -> dict:
    panel = pd.read_parquet(D1 / "panel_ct.parquet")
    datasets = []
    for y in OUTC:
        oof = pd.read_parquet(D1 / f"oof_{y}_closure_res_z.parquet")
        m = oof.merge(panel.drop(columns=[y]), on=["concept_id", "t"], how="left")
        ex = []
        for r in m.itertuples(index=False):
            inp = dict(concept_id=r.concept_id, phrase=r.phrase, t=int(r.t), age=_num(r.age), fold=r.fold, route=r.route,
                       in_MAIN=bool(r.in_MAIN), in_STRICT=bool(r.in_STRICT), in_SENSITIVITY=bool(r.in_SENSITIVITY),
                       origin_group=r.origin_group, F_band=r.F_band,
                       **{c: _num(getattr(r, c)) for c in S.NUM_BASE},
                       closure=_num(r.closure), closure_res=_num(r.closure_res), closure_res_imp=_num(r.closure_res_imp),
                       constraint=_num(r.constraint), esize_norm=_num(r.esize_norm), xcomm_exc=_num(r.xcomm_exc))
            ex.append(dict(input=json.dumps(inp), output=str(_num(getattr(r, y))),
                           predict_baseline=str(_num(r.oof_base)), predict_full=str(_num(r.oof_full)),
                           metadata_concept_id=r.concept_id, metadata_t=int(r.t), metadata_outcome=y,
                           metadata_E_up=bool(r.E_up), metadata_hydration_batch=r.hydration_batch, metadata_route=r.route))
        datasets.append(dict(dataset="d1_screen_concept_years" if y == "Y1r" else f"d1_screen_concept_years_{y}", examples=ex))
    verdict = json.loads((D1 / "verdict.json").read_text())
    meta = dict(method_name="RQ2-D1 openness -> W2 disciplinary breadth gain (screen fold)",
                description=("OLS with a concept-clustered bootstrap and grouped-by-concept CV. The BASE model is W1 level, "
                             "volume, momentum, growing-edge breadth, burst, Rafols coherence, participation and "
                             "origin/band/route/year dummies. FULL is BASE + residualised top-20 Chung-Lu closure (closure_res). "
                             "predict_baseline / predict_full are out-of-fold predictions averaged over 20 repeats of grouped 5-fold CV."),
                verdict=verdict["verdict"], outcomes_meeting_rule=verdict["outcomes_meeting_rule"],
                rule=verdict["rule_text_verbatim"])
    return dict(metadata=meta, datasets=datasets)


def _trunc(o, n: int = 200):
    if isinstance(o, str):
        return o if len(o) <= n else o[:n] + "..."
    if isinstance(o, list):
        return [_trunc(x, n) for x in o]
    if isinstance(o, dict):
        return {k: _trunc(v, n) for k, v in o.items()}
    return o


def write_variants(mo: dict) -> None:
    """full = method_out.json; mini = first 3 examples per dataset; preview = mini with strings cut to 200 chars."""
    mini = dict(metadata=mo["metadata"], datasets=[dict(dataset=d["dataset"], examples=d["examples"][:3]) for d in mo["datasets"]])
    (WS / "full_method_out.json").write_text(json.dumps(mo, indent=1))
    (WS / "mini_method_out.json").write_text(json.dumps(mini, indent=1))
    (WS / "preview_method_out.json").write_text(json.dumps(_trunc(mini), indent=1))


def fig_reproduction() -> None:
    new = pd.read_parquet(OUT / "indicators" / "concept_year_indicators_hyd.parquet")
    ref = pd.read_parquet(K.REF_IND)
    ids = set(pd.read_parquet(K.EXP3_POOL).query("fold == 'screen'").concept_id)
    m = new[new.concept_id.isin(ids) & (new.year <= 2019)].merge(ref, on=["concept_id", "year"], suffixes=("", "_ref"))
    rep = json.loads((OUT / "reproduction" / "reproduction_check.json").read_text())
    fig, ax = plt.subplots(figsize=(3.6, 3.4))
    ax.scatter(m.closure_ref, m.closure, s=5, alpha=0.5, color="#1f77b4", lw=0)
    lim = [np.nanmin(m.closure_ref), np.nanmax(m.closure_ref)]
    ax.plot(lim, lim, color="grey", lw=0.8, ls="--")
    ax.set_xlabel("closure, exp_3 (iteration-1 corpus)")
    ax.set_ylabel("closure, this run (hydrated corpus)")
    ax.set_title(f"Reproduction on 123 concepts: r = {rep['r_closure_ds5']:.4f}", fontsize=9)
    _save(fig, "fig1_reproduction_closure")


def fig_forest() -> None:
    rob = pd.read_csv(D1 / "robustness.csv")
    prim = pd.read_csv(D1 / "coef_table_primary.csv")
    specs = ["MAIN (primary)", "STRICT", "SENSITIVITY (all main arm)", "turnover-augmented baseline",
             "one row per concept (first eligible t)", "route B only", "iteration-1 concepts (hydration_batch iter1)",
             "newly hydrated concepts (iter2)"]
    fig, axes = plt.subplots(1, 3, figsize=(10.5, 4.8), sharey=True)
    colors = {"closure_res_z": "#1f77b4", "closure_res_imp_z": "#ff7f0e", "constraint_z": "#2ca02c"}
    for ax, y in zip(axes, OUTC):
        yticks, ylabels = [], []
        pos = 0
        for sp in specs:
            for k, ov in enumerate(colors):
                if sp == "MAIN (primary)":
                    r = prim[(prim.openness == ov) & (prim.outcome == y)]
                else:
                    r = rob[(rob.spec == sp) & (rob.openness == ov) & (rob.outcome == y)]
                if len(r) and np.isfinite(r.iloc[0].coef):
                    r = r.iloc[0]
                    yy = pos + (k - 1) * 0.25
                    ax.errorbar(r.coef, yy, xerr=[[r.coef - r.ci_lo], [r.ci_hi - r.coef]], fmt="o", ms=3, color=colors[ov],
                                lw=1, label=MLAB[ov] if (pos == 0 and ax is axes[0]) else None)
            yticks.append(pos)
            ylabels.append(sp)
            pos -= 1
        ax.axvline(0, color="grey", lw=0.8, ls="--")
        ax.set_title(OLAB[y], fontsize=9)
        ax.set_xlabel("coef. per SD of openness")
        ax.set_yticks(yticks)
        ax.set_yticklabels(ylabels)
    fig.legend(*axes[0].get_legend_handles_labels(), loc="lower center", ncol=3, fontsize=8, frameon=False)
    fig.suptitle("Openness at t and W2 breadth gain: OLS coefficients with 95% concept-cluster bootstrap CIs", fontsize=9)
    fig.tight_layout(rect=(0, 0.06, 1, 0.97))
    fig.savefig(FIG / "fig2_forest_openness.pdf")
    fig.savefig(FIG / "fig2_forest_openness.png", dpi=200)
    plt.close(fig)


def fig_delta_r2() -> None:
    cv = pd.read_csv(D1 / "cv_delta_r2.csv")
    cv = cv[cv.model == "b_grouped_cv"]
    ovs = list(MLAB)
    fig, ax = plt.subplots(figsize=(7, 3.2))
    w = 0.16
    for k, ov in enumerate(ovs):
        r = cv[cv.openness == ov].set_index("outcome").reindex(OUTC)
        x = np.arange(3) + (k - 2) * w
        ax.bar(x, r.delta_r2, width=w, label=MLAB[ov])
        ax.errorbar(x, r.delta_r2, yerr=[r.delta_r2 - r.ci_lo, r.ci_hi - r.delta_r2], fmt="none", color="k", lw=0.8)
    ax.axhline(0, color="grey", lw=0.8)
    ax.set_xticks(range(3))
    ax.set_xticklabels([OLAB[y] for y in OUTC], fontsize=8)
    ax.set_ylabel("out-of-fold delta R2 (FULL - BASE)")
    ax.legend(fontsize=7, frameon=False, ncol=3)
    _save(fig, "fig3_cv_delta_r2")


def fig_pdp() -> None:
    p = pd.read_csv(D1 / "partial_dependence.csv")
    fig, axes = plt.subplots(1, 3, figsize=(10, 3))
    for ax, y in zip(axes, OUTC):
        r = p[p.outcome == y]
        ax.errorbar(r.decile, r.y_resid_mean, yerr=[r.y_resid_mean - r.ci_lo, r.ci_hi - r.y_resid_mean], fmt="o-", ms=3)
        ax.axhline(0, color="grey", lw=0.8, ls="--")
        ax.set_xlabel("decile of closure_res | BASE (1 = most open)")
        ax.set_ylabel("mean residual outcome | BASE")
        ax.set_title(OLAB[y], fontsize=9)
    _save(fig, "fig4_partial_dependence")


def fig_mediation() -> None:
    med = json.loads((D1 / "mediation.json").read_text())["closure_res_z"]["per_outcome"]
    fig, axes = plt.subplots(1, 3, figsize=(10, 2.8))
    for ax, y in zip(axes, OUTC):
        r = med[y]
        ax.axis("off")
        box = dict(boxstyle="round", fc="#eef3fa", ec="#1f77b4")
        ax.text(0.05, 0.2, "closure_res\n(t)", ha="center", va="center", bbox=box, fontsize=8)
        ax.text(0.5, 0.85, "M_W2: cross-community\npairs (t+1..t+5)", ha="center", va="center", bbox=box, fontsize=8)
        ax.text(0.95, 0.2, f"{y}\n(W2)", ha="center", va="center", bbox=box, fontsize=8)
        ax.annotate("", xy=(0.4, 0.75), xytext=(0.1, 0.32), arrowprops=dict(arrowstyle="->"))
        ax.annotate("", xy=(0.9, 0.32), xytext=(0.6, 0.75), arrowprops=dict(arrowstyle="->"))
        ax.annotate("", xy=(0.83, 0.2), xytext=(0.17, 0.2), arrowprops=dict(arrowstyle="->"))
        f = lambda k: f"{r[k]['est']:+.3f} [{r[k]['ci'][0]:+.3f}, {r[k]['ci'][1]:+.3f}]"
        ax.text(0.0, 0.52, f"a =\n{f('a_path')}", fontsize=7, ha="left")
        ax.text(1.0, 0.52, f"b =\n{f('b_path')}", fontsize=7, ha="right")
        ax.text(0.5, 0.08, f"direct c' = {f('direct_c_prime')}", ha="center", fontsize=7)
        ax.text(0.5, -0.08, f"indirect ab = {f('indirect_ab')}", ha="center", fontsize=7)
        ax.set_title(f"{OLAB[y]} (n={r['n_rows']})", fontsize=8)
    _save(fig, "fig5_mediation")


def fig_power() -> None:
    p = OUT / "power" / "mde.json"
    if not p.exists():
        return
    mde = json.loads(p.read_text())["per_measure"]["closure_res_z"]
    fig, axes = plt.subplots(1, 2, figsize=(8, 3))
    for y in OUTC:
        o = mde["outcomes"][y]
        c = pd.DataFrame(o["power_curve_heldout"])
        axes[0].plot(c.beta_sd, c.power, "o-", ms=3, label=f"{y} (MDE {o['mde_heldout_sd']:.2f})")
        t = pd.DataFrame(o["transfer_delta_r2_power_curve"])
        axes[1].plot(t.beta_sd, t.power, "o-", ms=3, label=f"{y} (MDE {o['transfer_mde_sd']:.2f})")
    for ax, ttl in zip(axes, [f"held-out coefficient test (n = {mde['n_ho_effective']} concepts)",
                              "held-out transfer delta-R2 test"]):
        ax.axhline(0.8, color="grey", ls="--", lw=0.8)
        ax.set_xlabel("true effect (SD of Y per SD of closure_res)")
        ax.set_ylabel("power")
        ax.set_title(ttl, fontsize=9)
        ax.legend(fontsize=7, frameon=False)
    _save(fig, "fig6_mde_power")


def summary() -> dict:
    verdict = json.loads((D1 / "verdict.json").read_text())
    rep = json.loads((OUT / "reproduction" / "reproduction_check.json").read_text())
    pop = json.loads((OUT / "population" / "main_population_hydrated.json").read_text())
    r1a = json.loads((OUT / "openness" / "r1a_fit.json").read_text())
    prim = pd.read_csv(D1 / "coef_table_primary.csv")
    cv = pd.read_csv(D1 / "cv_delta_r2.csv")
    eup = json.loads((D1 / "within_E_up.json").read_text())
    med = json.loads((D1 / "mediation.json").read_text())
    san = json.loads((D1 / "sanity_checks.json").read_text())
    vc = json.loads((D1 / "volume_check.json").read_text())
    oc = json.loads((D1 / "outcomes_summary.json").read_text())
    dec = json.loads((D1 / "rowcount_decision.json").read_text())
    mde = json.loads((OUT / "power" / "mde.json").read_text()) if (OUT / "power" / "mde.json").exists() else {}
    spec_hash = (OUT / "heldout" / "heldout_spec.sha256").read_text().strip() if (OUT / "heldout" / "heldout_spec.sha256").exists() else None
    rob = pd.read_csv(D1 / "robustness.csv")
    lbl = json.loads((OUT / "indicators" / "labels_info.json").read_text())
    s = dict(
        verdict=verdict["verdict"], outcomes_meeting_rule=verdict["outcomes_meeting_rule"],
        opposite_direction_outcomes=verdict["opposite_direction_outcomes"], interpretation=verdict["interpretation"],
        rule_per_measure=verdict["per_measure"],
        population=dict(counts={k: v["by_fold"] for k, v in pop["counts"].items()},
                        replacement_rule_applied_to=pop["replacement_rule_applied_to"]),
        row_count_decision=dec,
        reproduction=dict(r_closure_hydrated=rep["r_closure_ds5"], gate_passed=rep["gate_passed"],
                          r_closure_code_equality=rep["r_closure_ds1"], changed_paper_sets=rep["n_concepts_with_changed_paper_sets"]),
        r1a=dict(n_fit_rows=r1a["primary"]["n_fit_rows"], n_fit_concepts=r1a["primary"]["n_fit_concepts"], r2=r1a["primary"]["r2"],
                 beta=r1a["primary"]["beta"]),
        primary_estimates=prim[["openness", "outcome", "coef", "ci_lo", "ci_hi", "p_boot", "p_holm", "q_bh_secondary", "se_cr1",
                                "p_cr1", "n_rows", "n_concepts", "coef_in_sd_y"]].to_dict("records"),
        cv_delta_r2=cv[["model", "openness", "outcome", "r2_base", "r2_full", "delta_r2", "ci_lo", "ci_hi", "n_rows",
                        "n_concepts"]].to_dict("records"),
        within_E_up=dict(n_concepts=eup["n_concepts"], n_rows=eup["n_rows"], label=eup["label"],
                         estimates=[{k: e.get(k) for k in ("openness", "outcome", "coef", "ci_lo", "ci_hi", "p_boot", "n_rows",
                                                          "n_concepts", "cv_delta_r2", "cv_ci_lo", "cv_ci_hi")}
                                    for e in eup["estimates"]]),
        E_up_onsets_screen=lbl["E_up_onsets"],
        mediation={ov: {y: dict(indirect=v["indirect_ab"], proportion=v["proportion_mediated"], total=v["total_c"])
                        for y, v in m["per_outcome"].items()} for ov, m in med.items()},
        robustness_sign_agreement={ov: {y: dict(n_specs=int(len(g)), share_negative=float((g.coef < 0).mean()),
                                                share_ci_excl_0=float(((g.ci_hi < 0) | (g.ci_lo > 0)).mean()))
                                        for y, g in rob[rob.openness == ov].groupby("outcome")}
                                   for ov in ["closure_res_z", "closure_res_imp_z", "constraint_z"]},
        outcomes=oc, volume_check=vc, sanity_checks=san,
        mde={ov: dict(n_ho=per["n_ho_effective"], **{y: dict(mde_heldout_sd=o["mde_heldout_sd"], mde_screen_sd=o["mde_screen_sd"],
                                                            transfer_mde_sd=o["transfer_mde_sd"],
                                                            bootstrap_rule_power_at_mde=o["bootstrap_rule_power_at_mde"])
                                                   for y, o in per["outcomes"].items()})
             for ov, per in mde.get("per_measure", {}).items()},
        heldout_spec_sha256=spec_hash, spec_sha256_vendored=K.SPEC_SHA,
    )
    return s


def run() -> None:
    mo = method_out()
    txt = json.dumps(mo, indent=1)
    (WS / "method_out.json").write_text(txt)
    logger.info(f"method_out.json: {sum(len(d['examples']) for d in mo['datasets'])} examples, {len(txt) / 1e6:.1f} MB")
    for f in (fig_reproduction, fig_forest, fig_delta_r2, fig_pdp, fig_mediation, fig_power):
        try:
            f()
        except (KeyError, ValueError, FileNotFoundError, IndexError) as e:
            logger.exception(f"figure {f.__name__} failed: {e}")
            raise
    write_variants(mo)
    s = summary()
    K.write_json(WS / "results_summary.json", s)
    build_readme(json.loads((WS / "results_summary.json").read_text()))
    logger.info("outputs written")


# ----------------------------------------------------------------------------- README (numbers filled from files)
def _f(x, nd=3) -> str:
    if x is None or (isinstance(x, float) and not math.isfinite(x)):
        return "n/a"
    return f"{float(x):.{nd}f}"


def headline_tables(s: dict) -> str:
    prim = pd.DataFrame(s["primary_estimates"])
    cv = pd.DataFrame(s["cv_delta_r2"])
    cvm = cv[cv.model == "b_grouped_cv"].set_index(["openness", "outcome"])
    fw = cv[cv.model == "b_grouped_cv_foldwise_R1a"].set_index(["openness", "outcome"])
    L = ["**Table 1. Openness at t → W2 breadth gain (screen, MAIN population).** OLS on BASE + openness_z. The "
         "coefficient is per SD of openness, with a 95 % concept-cluster bootstrap CI (2,000 reps). p_boot is the "
         "two-sided bootstrap p. Holm is taken over the 3 outcomes (co-primary measures); BH q over the secondary "
         "measures. ΔR² is out-of-fold (grouped 5-fold CV × 20 repeats) with a concept-bootstrap CI.", "",
         "| openness | outcome | coef [95% CI] | coef / SD(Y) | p_boot | Holm p / BH q | CR1 p | ΔR² [95% CI] | rows / concepts |",
         "|---|---|---|---|---|---|---|---|---|"]
    for r in prim.itertuples(index=False):
        c = cvm.loc[(r.openness, r.outcome)]
        adj = r.p_holm if isinstance(r.p_holm, float) and math.isfinite(r.p_holm) else r.q_bh_secondary
        adj = f"{adj:.3f}" if isinstance(adj, float) and math.isfinite(adj) else "– (not in a family)"
        L.append(f"| {MLAB.get(r.openness, r.openness)} | {r.outcome} | {r.coef:+.4f} [{r.ci_lo:+.4f}, {r.ci_hi:+.4f}] | "
                 f"{r.coef_in_sd_y:+.3f} | {r.p_boot:.3f} | {adj} | {r.p_cr1:.3f} | "
                 f"{c.delta_r2:+.4f} [{c.ci_lo:+.4f}, {c.ci_hi:+.4f}] | {r.n_rows} / {r.n_concepts} |")
    L += ["", "Fold-internal residualisation (R1a refit on the training folds only), closure_res: " +
          "; ".join(f"{y}: ΔR² {fw.loc[('closure_res_z', y)].delta_r2:+.4f} [{fw.loc[('closure_res_z', y)].ci_lo:+.4f}, "
                    f"{fw.loc[('closure_res_z', y)].ci_hi:+.4f}]" for y in OUTC), ""]
    e = s["within_E_up"]
    L += [f"**Table 2. Within E_up concepts** (onset ≤ 2015, rows t ∈ [onset−3, onset]; {e['n_concepts']} concepts, "
          f"{e['n_rows']} rows; {e['label']}).", "", "| openness | outcome | coef [95% CI] | p_boot | CV ΔR² [95% CI] |",
          "|---|---|---|---|---|"]
    for r in e["estimates"]:
        if r.get("coef") is None or not math.isfinite(r["coef"]):
            continue
        L.append(f"| {MLAB.get(r['openness'], r['openness'])} | {r['outcome']} | {r['coef']:+.4f} [{r['ci_lo']:+.4f}, {r['ci_hi']:+.4f}] | "
                 f"{r['p_boot']:.3f} | {_f(r.get('cv_delta_r2'), 4)} [{_f(r.get('cv_ci_lo'), 4)}, {_f(r.get('cv_ci_hi'), 4)}] |")
    L += ["", "**Table 3. Robustness grid** (the share of specifications with a negative coefficient, i.e. the D1 "
          "direction, and with a CI excluding 0 in either direction; the alternative outcomes Y1, Y1r20, log1p_Y3b and the PPML Y3 "
          "row are single specifications; all rows are in `results/d1/robustness.csv`).", "",
          "| openness | outcome | specs | share negative | share CI excl. 0 |", "|---|---|---|---|---|"]
    for ov, d in s["robustness_sign_agreement"].items():
        for y, v in d.items():
            L.append(f"| {MLAB.get(ov, ov)} | {y} | {v['n_specs']} | {v['share_negative']:.2f} | {v['share_ci_excl_0']:.2f} |")
    L += ["", "**Table 4. Mediation through W2 cross-community neighbour pairs** (descriptive; concept-bootstrap 95 % CI).",
          "", "| openness | outcome | total c | indirect a·b |", "|---|---|---|---|"]
    for ov, d in s["mediation"].items():
        for y, v in d.items():
            L.append(f"| {MLAB.get(ov, ov)} | {y} | {v['total']['est']:+.4f} [{v['total']['ci'][0]:+.4f}, {v['total']['ci'][1]:+.4f}] | "
                     f"{v['indirect']['est']:+.4f} [{v['indirect']['ci'][0]:+.4f}, {v['indirect']['ci'][1]:+.4f}] |")
    if s.get("mde"):
        L += ["", "**Table 5. Minimum detectable effect** (80 % power, one-sided CR1 test in the D1 direction; SD(Y) per SD "
              "of openness; 'n/a' = not reached within 0.5 SD).", "",
              "| openness | outcome | MDE screen | MDE held-out (n concepts) | bootstrap-rule power at held-out MDE | transfer-ΔR² MDE |",
              "|---|---|---|---|---|---|"]
        for ov, d in s["mde"].items():
            for y in OUTC:
                v = d[y]
                L.append(f"| {MLAB.get(ov, ov)} | {y} | {_f(v['mde_screen_sd'])} | {_f(v['mde_heldout_sd'])} ({d['n_ho']}) | "
                         f"{_f(v['bootstrap_rule_power_at_mde'], 2)} | {_f(v['transfer_mde_sd'])} |")
    return "\n".join(L)


def _ci(rob: pd.DataFrame, y: str) -> str:
    r = rob[(rob.spec == "SENSITIVITY (all main arm)") & (rob.openness == "closure_res_z") & (rob.outcome == y)].iloc[0]
    return f"{r.coef:+.4f} [{r.ci_lo:+.4f}, {r.ci_hi:+.4f}]"


def build_readme(s: dict) -> None:
    tpl = (WS / "docs" / "README_template.md").read_text()
    tab = headline_tables(s)
    (OUT / "headline_tables.md").write_text(tab + "\n")
    prim = pd.DataFrame(s["primary_estimates"]).set_index(["openness", "outcome"])
    rob = pd.read_csv(D1 / "robustness.csv")
    sens = rob[(rob.spec == "SENSITIVITY (all main arm)") & (rob.openness == "closure_res_z") & (rob.outcome == "Y1r")].iloc[0]
    med3 = s["mediation"]["closure_res_z"]["log1p_Y3"]["indirect"]
    vif = pd.read_csv(D1 / "vif.csv").set_index("variable").vif
    san = s["sanity_checks"]
    mde = s.get("mde", {}).get("closure_res_z", {})
    audit_p = OUT / "audit_rederive.json"
    audit = json.loads(audit_p.read_text())["all_match"] if audit_p.exists() else "run audit_rederive.py"
    pop = s["population"]["counts"]
    mp = OUT / "power" / "mde.json"
    eum = json.loads(mp.read_text()).get("E_up_subset", {}) if mp.exists() else {}
    vals = {
        "VERDICT": s["verdict"], "MET": ", ".join(s["outcomes_meeting_rule"]) or "none",
        "OPP": ", ".join(s["opposite_direction_outcomes"]) or "none", "RULE": json.loads((D1 / "verdict.json").read_text())["rule_text_verbatim"],
        "CC_CONCEPTS": s["row_count_decision"]["closure_res_complete_concepts"], "CC_ROWS": s["row_count_decision"]["closure_res_complete_rows"],
        "HEADLINE": tab, "SENS_ROWS": int(sens.n_rows),
        "MED_Y3": f"{med3['est']:+.4f} [{med3['ci'][0]:+.4f}, {med3['ci'][1]:+.4f}]",
        "SP_VOL": f"{s['volume_check']['spearman_closure_res_vs_log_vol_W1']:.2f}", "VIF": f"{vif['closure_res_z']:.2f}",
        "N_SCREEN": int(prim.loc[("closure_res_z", "Y1r"), "n_concepts"]),
        "MDE_SCREEN": _f(mde.get("Y1r", {}).get("mde_screen_sd")), "N_HO": mde.get("n_ho"),
        "MDE_HO": _f(mde.get("Y1r", {}).get("mde_heldout_sd")),
        "PLACEBO_Y1R": f"{san['Y1r']['observed_percentile_in_placebo']:.0f}", "PLACEBO_Y2": f"{san['Y2']['observed_percentile_in_placebo']:.0f}",
        "PLACEBO_Y3": f"{san['log1p_Y3']['observed_percentile_in_placebo']:.0f}",
        "SHUF": f"{np.mean([v['label_shuffle_delta_r2_mean'] for v in san.values()]):+.4f}",
        "LEAK_Y3_BASE": f"{san['log1p_Y3']['leaky_r2_full']:.3f}", "LEAK_Y3": f"{san['log1p_Y3']['leaky_r2_with_W2_volume']:.3f}",
        "LEAK_Y1_BASE": f"{san['Y1r']['leaky_r2_full']:.3f}", "LEAK_Y1": f"{san['Y1r']['leaky_r2_with_W2_breadth_level']:.3f}",
        "BOOTCHG": f"{100 * max(v['boot_ci_width_rel_change'] for v in san.values()):.1f}",
        "DETERM": all(v["deterministic"] for v in san.values()), "AUDIT": audit,
        "N_REPL": s["population"]["replacement_rule_applied_to"],
        "MAIN_COUNTS": f"{pop['in_MAIN'].get('screen')} screen + {pop['in_MAIN'].get('heldout_concept')} held-out concepts "
                       f"(STRICT {pop['in_STRICT'].get('screen')} + {pop['in_STRICT'].get('heldout_concept')})",
        "REP_R": f"{s['reproduction']['r_closure_hydrated']:.5f}", "REP_PASS": "PASS" if s["reproduction"]["gate_passed"] else "FAIL",
        "REP_CODE": f"{s['reproduction']['r_closure_code_equality']:.6f}", "REP_CHANGED": s["reproduction"]["changed_paper_sets"],
        "R1A_N": s["r1a"]["n_fit_rows"], "R1A_R2": f"{s['r1a']['r2']:.3f}", "N_ROB": len(rob),
        "SPEC_SHA": s["heldout_spec_sha256"],
        "MAIN_ROWS": s["row_count_decision"]["main_screen_eligible_rows"],
        "MAIN_CONCEPTS": s["row_count_decision"]["main_screen_eligible_concepts"],
        "IMP_Y2": (lambda r: f"coef {r['coef']:+.4f} [{r['ci_lo']:+.4f}, {r['ci_hi']:+.4f}], p_boot {r['p_boot']:.3f}, "
                   f"Holm p {r['p_holm']:.3f}")(prim.loc[("closure_res_imp_z", "Y2")]),
        "SENS_Y1R": _ci(rob, "Y1r"), "SENS_Y2": _ci(rob, "Y2"),
        "EUP_MDE": " / ".join(_f(eum.get(y, {}).get("mde_sd"), 2) for y in OUTC),
        "EUP_ROWS": s["within_E_up"]["n_rows"], "EUP_CONCEPTS": s["within_E_up"]["n_concepts"],
    }
    for k, v in vals.items():
        tpl = tpl.replace("{{" + k + "}}", str(v))
    assert "{{" not in tpl, [x for x in tpl.split("{{")[1:]][:3]
    (WS / "README.md").write_text(tpl)
    logger.info("README.md written from results")
