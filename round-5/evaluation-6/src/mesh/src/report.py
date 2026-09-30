"""STAGE 11: method_out.json (exp_gen_sol_out), figures F1-F6 and the final summary.

method_out.json: one example per MESH_MAIN event with outcomes. input = JSON of the W1 features; output = Y_strict.
predict_baseline / predict_method = grouped-by-concept 5-fold OUT-OF-FOLD predictions of a Poisson GLM without
concept FE (entry-year and host-domain dummies, the R2 controls, offset log n_entry_papers); the method model adds
A_cont and CT. This is a descriptive predictive check (concept FE cannot score unseen concepts); the inferential test
is the PPML table in g4_models.json. metadata_r2_fitted_mu = in-sample R2 fitted mean (null if pruned).
"""
from __future__ import annotations

import json
import warnings

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from loguru import logger  # noqa: E402
from scipy import stats  # noqa: E402

import common  # noqa: E402
from common import FIGS, MAIN_COPRIMARY, MAIN_NONPHYS, MAIN_PHYS, RESULTS, SEED, WS, dump  # noqa: E402

FEAT_COLS = ["A_cont", "A_cont_lo", "A_cont_hi", "A_cont_exact", "CT", "CT_any", "NATIVE", "ADJACENT", "FOREIGN",
             "A_placebo", "cov", "cov_exact", "n_tags", "n_prof_tags", "prox_od", "RD", "log_n_partner_tags", "demic",
             "mean_topic_score", "boundary_share", "abstract_share", "mom_d", "log_centrality", "log_W1",
             "n_entry_papers", "n_partners_distinct"]


def _glm_oof(s: pd.DataFrame, xvars: list[str], k: int = 5) -> np.ndarray:
    import statsmodels.api as sm
    rng = np.random.default_rng(SEED)
    conc = s.concept_id.unique()
    fold = dict(zip(conc, rng.permutation(len(conc)) % k))
    f = s.concept_id.map(fold).to_numpy()
    dm = pd.get_dummies(s[["e", "domain_d"]].astype(str), drop_first=True).astype(float)
    X = pd.concat([s[xvars].reset_index(drop=True), dm.reset_index(drop=True)], axis=1)
    X = sm.add_constant(X, has_constant="add")
    Xs = (X - X.mean()) / X.std().replace(0, 1)
    Xs["const"] = 1.0
    pred = np.zeros(len(s))
    for j in range(k):
        tr, te = f != j, f == j
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            m = sm.GLM(s.Y_strict.to_numpy()[tr], Xs[tr], family=sm.families.Poisson(),
                       offset=s.offset.to_numpy()[tr]).fit_regularized(alpha=1e-4, L1_wt=0.0, maxiter=300)
        pred[te] = np.exp(Xs[te].to_numpy() @ m.params.to_numpy() + s.offset.to_numpy()[te])
    return pred


def poisson_dev(y, mu):
    mu = np.maximum(mu, 1e-12)
    return 2 * (np.where(y > 0, y * np.log(np.where(y > 0, y, 1) / mu), 0) - (y - mu))


def method_out(spec: dict, src=None, out_path=None) -> dict:
    src = src or RESULTS
    out_path = out_path or (WS / "method_out.json")
    import models as vmodels
    import ppml
    from models_mesh import sample
    sc = spec["models"]["secondary_controls"]
    om = pd.read_parquet(src / "outcomes_mesh.parquet")
    s = sample(om, ["A_cont", "CT"] + sc)
    p0 = _glm_oof(s, sc)
    p1 = _glm_oof(s, ["A_cont", "CT"] + sc)
    r = ppml.fit(s.Y_strict.to_numpy(float), s[["A_cont", "CT"] + sc].to_numpy(float), vmodels.fe_arrays(s, "secondary"),
                 s.offset.to_numpy(), s.concept_id.to_numpy(), maxit=500, tol=1e-12)
    mu_full = np.full(len(s), np.nan)
    mu_full[r["keep"]] = r["mu"]
    y = s.Y_strict.to_numpy(float)
    d0, d1 = poisson_dev(y, p0), poisson_dev(y, p1)
    rng = np.random.default_rng(SEED)
    conc = s.concept_id.to_numpy()
    uc = np.unique(conc)
    idx = {c: np.flatnonzero(conc == c) for c in uc}
    boots = []
    for _ in range(1000):
        pick = np.concatenate([idx[c] for c in rng.choice(uc, len(uc))])
        boots.append(d1[pick].mean() - d0[pick].mean())
    oos = {"n_events": int(len(s)), "n_concepts": int(len(uc)), "mean_deviance_baseline": float(d0.mean()),
           "mean_deviance_method": float(d1.mean()), "deviance_diff_method_minus_baseline": float(d1.mean() - d0.mean()),
           "deviance_diff_ci95_concept_bootstrap": [float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5))],
           "spearman_baseline": float(stats.spearmanr(p0, y)[0]), "spearman_method": float(stats.spearmanr(p1, y)[0]),
           "note": "grouped-by-concept 5-fold out-of-fold predictions; descriptive predictive check, not the inferential test"}
    tax = json.loads((common.D5 / "hyd" / "taxonomy.json").read_text())
    ex = []
    for i, x in enumerate(s.itertuples()):
        feat = {"concept_id": x.concept_id, "o": int(x.o), "d": int(x.d), "e": int(x.e)}
        for c in FEAT_COLS:
            v = getattr(x, c, None)
            feat[c] = None if v is None or (isinstance(v, float) and not np.isfinite(v)) else (
                round(float(v), 6) if isinstance(v, (float, np.floating)) else int(v))
        ex.append({"input": json.dumps(feat, separators=(",", ":")), "output": str(int(x.Y_strict)),
                   "predict_baseline": f"{p0[i]:.6f}", "predict_method": f"{p1[i]:.6f}",
                   "metadata_fold": "heldout_mesh", "metadata_concept_id": x.concept_id, "metadata_host_subfield": int(x.d),
                   "metadata_host_subfield_name": tax["subfields"].get(str(int(x.d))),
                   "metadata_host_field": tax["fields"].get(str(int(x.field_d))), "metadata_entry_year": int(x.e),
                   "metadata_nat_source": x.nat_source, "metadata_cov": round(float(x.cov), 6),
                   "metadata_Y_lenient": int(x.Y_lenient), "metadata_Y_all": int(x.Y_all), "metadata_EST_bin": int(x.EST_bin),
                   "metadata_r2_fitted_mu": None if np.isnan(mu_full[i]) else round(float(mu_full[i]), 6),
                   "metadata_retrieval_complete": bool(x.retrieval_complete), "metadata_rule_parity": bool(x.rule_parity)})
    g4 = json.loads((src / "g4_verdict.json").read_text())
    out = {"metadata": {"method_name": "G4 MeSH replication of the D2 host-entry grafting test (PPML)",
                        "description": "One example per MeSH host-entry event (concept c enters PubMed-covered non-origin "
                                       "subfield d in year e). input = W1 features; output = Y_strict (W2 host papers by "
                                       "author-disjoint newcomers). predict_baseline = out-of-fold Poisson controls-only "
                                       "model; predict_method = + anchoring A_cont + co-transfer CT.",
                        "oos": oos, "g4_verdict": g4["verdict"], "R2_irr_per_sd_A_cont": g4["irr_sd"],
                        "R2_ci95": g4["ci95"],
                        "spec_sha256": (RESULTS / "mesh_spec.sha256").read_text().split()[0]
                        if (RESULTS / "mesh_spec.sha256").exists() else "DRY RUN"},
           "datasets": [{"dataset": "g4_mesh_host_entry_events", "examples": ex}]}
    out_path.write_text(json.dumps(out, indent=1))
    dump(src / "oos_check_mesh.json", oos)
    logger.info(f"method_out.json: {len(ex)} examples; oos {oos}")
    return oos


# --------------------------------------------------------------------------------------------------------- figures
def figures(src=None, figs=None) -> None:
    src = src or RESULTS
    figs = figs or FIGS
    figs.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({"font.size": 9, "pdf.fonttype": 42})
    m = json.loads((src / "g4_models.json").read_text())
    rows = m["rows"]
    # F1 forest
    items = []
    for key in ["R2", "R1", "R3", "R4", "S1", "S3", "S4", "S5", "S6", "S8", "S9", "S10", "S11", "S12", "S13",
                "S14_health", "S14_life", "S16", "S17", "S18"]:
        rr = (rows.get(key) or {}).get("row")
        if not rr:
            continue
        a = "A_placebo" if key == "S3" else ("A_cont_lo" if key == "S4" else ("A_cont_hi" if key == "S5" else
                                                                               ("A_cont_exact" if key == "S16" else "A_cont")))
        if a not in rr:
            continue
        lab = rows[key]["label"]
        lab = lab if len(lab) <= 46 else lab[:44].rsplit(" ", 1)[0] + " ..."
        items.append((f"MeSH {key}: {lab}", rr[a]["irr_sd"], *rr[a]["ci_irr_sd"], "C0"))
    items.append(("MAIN co-primary (iteration 3)", MAIN_COPRIMARY["irr_sd"], *MAIN_COPRIMARY["ci"], "C3"))
    gj = RESULTS / "gates.json"
    if gj.exists():
        hz = json.loads(gj.read_text()).get("harmonisation", {})
        for hk, hl in (("h4_mesh_rules", "MAIN h4: MeSH data rules (harmonisation)"),
                       ("h6b_ranking_rule_plus_bg", "MAIN h6b: + MeSH nativeness rule (harmonisation)")):
            if hk in hz and hz[hk]["coprimary"]:
                a_ = hz[hk]["coprimary"]["A_cont"]
                items.append((hl, a_["irr_sd"], *a_["ci_irr_sd"], "C3"))
    items.append(("MAIN non-physics stratum", MAIN_NONPHYS["irr_sd"], *MAIN_NONPHYS["ci"], "C3"))
    items.append(("MAIN physics stratum", MAIN_PHYS["irr_sd"], *MAIN_PHYS["ci"], "C7"))
    fig, ax = plt.subplots(figsize=(7.2, 0.28 * len(items) + 1))
    for i, (lab, est, lo, hi, col) in enumerate(items[::-1]):
        ax.plot([lo, hi], [i, i], color=col, lw=1.4)
        ax.plot(est, i, "o", color=col, ms=4 if "R2" not in lab else 7)
    ax.set_yticks(range(len(items)))
    ax.set_yticklabels([x[0] for x in items[::-1]], fontsize=7)
    ax.axvline(1, color="k", lw=0.8, ls="--")
    ax.set_xscale("log")
    from matplotlib.ticker import FixedLocator, NullLocator, ScalarFormatter
    lo_ = min(x[2] for x in items)
    hi_ = max(x[3] for x in items)
    ticks = [t for t in (0.5, 0.67, 0.8, 1.0, 1.25, 1.5, 2.0, 3.0, 4.0) if lo_ * 0.9 <= t <= hi_ * 1.1]
    ax.xaxis.set_major_locator(FixedLocator(ticks))
    ax.xaxis.set_minor_locator(NullLocator())
    ax.xaxis.set_major_formatter(ScalarFormatter())
    ax.set_xlabel("IRR per SD of the anchoring measure (95% CI, CRV1 by concept)")
    ax.set_title("F1  MeSH replication rows vs the main pool", fontsize=9)
    fig.tight_layout()
    fig.savefig(figs / "F1_forest.png", dpi=200)
    fig.savefig(figs / "F1_forest.pdf")
    plt.close(fig)
    # F2 binned A_cont vs Y_strict per entry paper
    om = pd.read_parquet(src / "outcomes_mesh.parquet")
    om = om.dropna(subset=["A_cont"])
    om["bin"] = pd.qcut(om.A_cont, 10, labels=False, duplicates="drop")
    g = om.groupby("bin").apply(lambda x: pd.Series({"A": x.A_cont.mean(), "y": (x.Y_strict / x.n_entry_papers).mean(),
                                                     "se": (x.Y_strict / x.n_entry_papers).std() / np.sqrt(len(x))}),
                                include_groups=False)
    fig, ax = plt.subplots(figsize=(4.6, 3.4))
    ax.errorbar(g.A, g.y, yerr=1.96 * g.se, fmt="o-", color="C0", capsize=2)
    ax.set_xlabel("A_cont (decile means)")
    ax.set_ylabel("Y_strict per entry paper")
    ax.set_title("F2  Newcomer uptake by anchoring decile (MeSH, raw)")
    fig.tight_layout()
    fig.savefig(figs / "F2_binned_A_cont.png", dpi=200)
    plt.close(fig)
    # F3 placebo z
    pl = pd.read_csv(src / "placebo_draws_mesh.csv")
    pj = json.loads((src / "placebo_mesh.json").read_text())
    fig, axs = plt.subplots(1, 2, figsize=(7.2, 3))
    for ax, k in zip(axs, ("R2", "R1")):
        z = pl[f"z_A_{k}"].dropna()
        ax.hist(z, bins=30, color="C7")
        if k in pj:
            ax.axvline(pj[k]["z_obs"], color="C3", lw=2, label=f"observed z = {pj[k]['z_obs']:.2f}\nperm p = {pj[k]['perm_p_two_sided_z']:.3f}")
            ax.legend(fontsize=7)
        ax.set_title(f"F3  {k}: nativeness-permutation placebo z")
        ax.set_xlabel("z of A_cont")
    fig.tight_layout()
    fig.savefig(figs / "F3_placebo_z.png", dpi=200)
    plt.close(fig)
    # F4 MDE curve
    pw = json.loads((RESULTS / "power_mesh.json").read_text())
    fig, ax = plt.subplots(figsize=(4.6, 3.4))
    for k, col in (("R2", "C0"), ("R1", "C1"), ("S1", "C2")):
        c = pw["power_curve"].get(k)
        if c:
            xs = sorted(float(a) for a in c)
            ax.plot(xs, [c[str(x)] if str(x) in c else c[f"{x:.1f}"] for x in xs], "o-", color=col,
                    label=f"{k} (MDE80 {pw['MDE80_irr_per_sd'].get(k)})")
    ax.axhline(0.8, color="k", ls=":", lw=0.8)
    ax.axvline(1.29, color="C3", ls="--", lw=0.8, label="main non-physics 1.29")
    ax.set_xlabel("true IRR per SD of A_cont")
    ax.set_ylabel("power (b > 0, p < 0.025)")
    ax.set_title("F4  Simulated power on the MeSH W1 design")
    ax.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(figs / "F4_mde_curve.png", dpi=200)
    plt.close(fig)
    # F5 entries by host field kept vs removed
    ec = pd.read_csv(RESULTS / "entry_counts_by_host_field.csv")
    ec = ec.rename(columns={"False": "removed", "True": "kept"})
    for c in ("removed", "kept"):
        if c not in ec:
            ec[c] = 0
    ec = ec.sort_values("kept")
    fig, ax = plt.subplots(figsize=(6, 5))
    ax.barh(ec.field_name, ec.kept, color="C0", label="kept (PubMed-covered host)")
    ax.barh(ec.field_name, ec.removed, left=ec.kept, color="C7", label="removed by coverage rule")
    ax.set_xlabel("MeSH entry events (partner rule met)")
    ax.set_title("F5  Host fields of MeSH entries")
    ax.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(figs / "F5_entries_by_host_field.png", dpi=200)
    plt.close(fig)
    # F6 G2 decomposition
    fig, ax = plt.subplots(figsize=(4.6, 3.2))
    xs, labs = [], []
    for j, key in enumerate(("S2", "S2_primary")):
        rr = (rows.get(key) or {}).get("row")
        if not rr:
            continue
        for k, v in enumerate(("NATIVE", "ADJACENT")):
            if v in rr:
                x = j * 3 + k
                ax.bar(x, rr[v]["irr_sd"], color=["C2", "C1"][k])
                ax.plot([x, x], rr[v]["ci_irr_sd"], color="k")
                xs.append(x)
                labs.append(f"{v}\n{'co-prim.' if key == 'S2' else 'primary'}")
    ax.axhline(1, color="k", ls="--", lw=0.8)
    ax.set_xticks(xs)
    ax.set_xticklabels(labs, fontsize=7)
    ax.set_ylabel("IRR per SD (95% CI)")
    ax.set_title("F6  G2: which partner band carries the effect")
    fig.tight_layout()
    fig.savefig(figs / "F6_g2_decomposition.png", dpi=200)
    plt.close(fig)
    logger.info("figures F1-F6 written")


def summary(oos: dict) -> dict:
    """Consolidated key numbers for downstream steps (every number is read from a results file)."""
    m = json.loads((RESULTS / "g4_models.json").read_text())
    pw = json.loads((RESULTS / "power_mesh.json").read_text())
    gates = json.loads((RESULTS / "gates.json").read_text())
    ev = json.loads((RESULTS / "events_mesh_summary.json").read_text())
    fs = json.loads((RESULTS / "features_mesh_summary.json").read_text())
    nat = json.loads((RESULTS / "nativeness_ledger_summary.json").read_text())
    r2 = m["rows"]["R2"]["row"]
    reps = pd.read_csv(RESULTS / "power_reps_mesh.csv")
    null_p = reps.loc[reps.irr == 1.0, "p_R2"].dropna().to_numpy()
    p_obs = r2["A_cont"]["p_crv1"]
    cal = {"note": "POST-HOC (not in the frozen spec): CRV1 over-rejects in the T3 null simulation (size 0.105 at "
                   "alpha .05), so the observed R2 CRV1 p is also referred to the 200 simulated null p values",
           "n_null": int(len(null_p)), "null_size_at_0.05": float((null_p < 0.05).mean()),
           "calibrated_p_R2": float((1 + (null_p <= p_obs).sum()) / (1 + len(null_p))),
           "null_p_q05": float(np.quantile(null_p, 0.05))}
    hz = gates["harmonisation"]

    def hrow(k):
        a = hz[k]["coprimary"]["A_cont"]
        return {"irr_sd": a["irr_sd"], "ci": a["ci_irr_sd"], "N": hz[k]["coprimary"]["N"], "G": hz[k]["coprimary"]["G"]}

    rows = {}
    for k, v in m["rows"].items():
        rr = v.get("row")
        if not isinstance(rr, dict) or "N" not in rr:
            continue
        a = next((x for x in ("A_cont", "A_placebo", "A_cont_lo", "A_cont_hi", "A_cont_exact", "NATIVE") if x in rr), None)
        rows[k] = {"label": v["label"], "N": rr["N"], "G": rr["G"], "var": a, "irr_sd": rr[a]["irr_sd"],
                   "ci": rr[a]["ci_irr_sd"], "p_crv1": rr[a]["p_crv1"], "p_wild": rr[a]["p_wild"],
                   "CT_irr_sd": rr.get("CT", {}).get("irr_sd"), "CT_p": rr.get("CT", {}).get("p_crv1")}
    out = {"g4_verdict": m["g4"]["verdict"], "reading_R2": m["g4"]["reading_R2"], "reading_R1": m["g4"]["reading_R1"],
           "R2": rows.get("R2"), "R1": rows.get("R1"), "rows": rows,
           "holm_p_R2": m["decisions"]["R2"]["holm_p"], "holm_p_R1": m["decisions"]["R1"]["holm_p"],
           "thin_cell_rule": m["decisions"]["thin_cell_rule"],
           "placebo": {k: m["placebo"][k] for k in ("R1", "R2", "outcome_shuffle_within_concept_R2") if k in m["placebo"]},
           "comparison": m["comparison_main_vs_mesh"], "mechanism": m["g4"]["mechanism"],
           "MDE80": pw["MDE80_irr_per_sd"], "T3": pw["T3_synthetic_recovery"], "size_calibration_post_hoc": cal,
           "gates": {"gate1_pass": gates["gate1"]["pass"], "gate2_pass": gates["gate2"]["pass"],
                     "gate2_coprimary_irr_sd": gates["gate2"]["coprimary"]["A_cont"]["irr_sd"]},
           "harmonisation_main": {k: hrow(k) for k in hz},
           "design": {"events": ev["MESH_MAIN"]["events"], "concepts": ev["MESH_MAIN"]["concepts"],
                      "chosen_rule": ev["chosen"], "declared_rule_design": ev["widening_steps"][0],
                      "removed_by_coverage": ev["removed_by_coverage_among_kw"]},
           "nativeness": {"tag_weighted_cov": fs["tag_weighted_cov"], "exact_only": fs["tag_weighted_cov_exact_only"],
                          "calls": nat["calls_this_run"], "fallback_admitted": nat["fallback_admitted"]},
           "oos": oos, "pyfixest_crosscheck": {k: v for k, v in (m["pyfixest_crosscheck"] or {}).items() if k != "per_var"},
           "spec_sha256": m["spec_sha256"]}
    au = RESULTS / "audit_rederive.json"
    if au.exists():
        a = json.loads(au.read_text())
        out["audit_rederive_all_match"] = a["all_match"]
    dump(RESULTS / "g4_summary.json", out)
    logger.info(f"summary: verdict {out['g4_verdict']}; calibrated p {cal['calibrated_p_R2']}")
    return out


def run() -> dict:
    spec = json.loads((RESULTS / "mesh_spec.json").read_text())
    oos = method_out(spec)
    figures()
    summary(oos)
    return oos
