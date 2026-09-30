"""Assemble method_out.json (exp_gen_sol_out schema) + final T5 checks."""
from __future__ import annotations

import hashlib
import json

import numpy as np
import pandas as pd
from loguru import logger

from common import RESULTS, WS


def _j(p):
    return json.loads(p.read_text()) if p.exists() else None


def _clean(x):
    if isinstance(x, dict):
        return {str(k): _clean(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_clean(v) for v in x]
    if isinstance(x, (np.integer,)):
        return int(x)
    if isinstance(x, (np.floating, float)):
        return None if not np.isfinite(x) else round(float(x), 6)
    if isinstance(x, np.bool_):
        return bool(x)
    return x


def fmt(x) -> str:
    return "NA" if x is None or (isinstance(x, float) and not np.isfinite(x)) else (f"{x:.6g}" if isinstance(x, float) else str(x))


def baseline_comparison(e: pd.DataFrame) -> dict:
    """Is the citation-lineage label more than W1 momentum? Cross-tab state_main vs growing_edge (baseline)."""
    t = e[e.tested_main]
    ct = pd.crosstab(t.state_main, t.growing_edge.map({True: "growing", False: "not_growing"}))
    rho_vs_mom = t[["rho_tilde", "mom"]].replace([np.inf, -np.inf], np.nan).dropna()
    from scipy.stats import spearmanr
    r = spearmanr(rho_vs_mom.rho_tilde, rho_vs_mom.mom) if len(rho_vs_mom) > 3 else None
    lg = pd.crosstab(e.within_host_share >= 0.4, e.lenient_share >= 0.4)
    return {"tested_state_x_growing_edge": ct.to_dict(), "spearman_rho_tilde_vs_W1_momentum": {
        "rho": float(r.correlation) if r else None, "p": float(r.pvalue) if r else None, "n": int(len(rho_vs_mom))},
        "gate_edge_pass_within_x_lenient": {f"within>=.4={a}": {f"lenient>=.4={b}": int(v) for b, v in row.items()}
                                            for a, row in lg.to_dict("index").items()}}


def run() -> None:
    e = pd.read_csv(RESULTS / "viability" / "viability_layer.csv")
    ga = pd.read_parquet(RESULTS / "gate_a" / "gate_a_host_edges.parquet")
    syn = _j(RESULTS / "synth" / "synth_results.json")
    prereg = WS / "prereg" / "prereg_freeze.json"
    sha = hashlib.sha256(prereg.read_bytes()).hexdigest()
    recorded = (WS / "prereg" / "prereg_freeze.sha256").read_text().split()[0]
    assert sha == recorded, "prereg hash mismatch"
    # T5 checks
    states = {"SOURCE", "SINK", "FADING", "UNDETERMINED"}
    assert e.state_main.isin(states).all() and e.reason_code.notna().all()
    assert (e.t_max_used <= e.t).all(), "edge used papers after t"
    ex_v = []
    for r in e.itertuples():
        ex_v.append({
            "input": json.dumps({"concept_id": r.concept_id, "phrase": r.phrase, "d": int(r.d), "t": int(r.t), "age": int(r.age),
                                 "origin_subfield": int(r.origin_subfield), "n_W1_dpapers": int(r.n_w1),
                                 "n_children": int(r.n_children), "n_parents": int(r.n_parents), "n_traced": int(r.n_traced)}),
            "output": r.state_main,
            "predict_state_nmin5": r.state_nmin5, "predict_state_nmin10": r.state_nmin10, "predict_state_nmin20": r.state_nmin20,
            "predict_state_canonW1": r.state_canonW1, "predict_state_EB": r.state_EB, "predict_state_refboot": r.state_refboot,
            "predict_rho_tilde": fmt(r.rho_tilde),
            "predict_baseline_growing_edge": "GROWING" if r.growing_edge else "NOT_GROWING",
            "metadata_fold": r.fold, "metadata_age": int(r.age), "metadata_F_band": r.F_band,
            "metadata_rho": fmt(r.rho), "metadata_rho_ci90": [fmt(r.rho_lo), fmt(r.rho_hi)],
            "metadata_rho_tilde_ci90": [fmt(r.rho_tilde_lo), fmt(r.rho_tilde_hi)],
            "metadata_m": fmt(r.m), "metadata_m_ci90": [fmt(r.m_lo), fmt(r.m_hi)],
            "metadata_rho0": fmt(r.rho0), "metadata_rho0_level": r.rho0_level,
            "metadata_q_greater": fmt(r.q_greater), "metadata_q_less": fmt(r.q_less),
            "metadata_reason_code": r.reason_code, "metadata_untraced_share": fmt(r.untraced_share),
            "metadata_within_host_share": fmt(r.within_host_share), "metadata_momentum": fmt(r.mom),
            "metadata_sense_check_fail": bool(r.sense_check_fail), "metadata_retrieval_route": r.retrieval_route,
            "metadata_status": "DESCRIPTIVE ONLY (Gate A FAIL)"})
    ex_g = []
    for r in ga.itertuples():
        ex_g.append({
            "input": json.dumps({"concept_id": r.concept_id, "d": int(r.d), "t": int(r.t), "age": int(r.age),
                                 "n_children": int(r.n_children), "n_W1_dpapers": int(r.n_w1)}),
            "output": fmt(r.within_host_share),
            "predict_within_host_ge_040": str(bool(r.within_host_share >= 0.4)),
            "predict_baseline_lenient_share": fmt(r.lenient_share),
            "predict_baseline_lenient_ge_040": str(bool(r.lenient_share >= 0.4)),
            "metadata_within_host_share_refs_denominator": fmt(r.within_host_share_refs),
            "metadata_untraced_share": fmt(r.untraced_share), "metadata_background_only_share": fmt(r.background_only_share),
            "metadata_in_verdict_set": bool(r.n_children >= 10), "metadata_fold": r.fold})
    ex_s = []
    if syn:
        nm = syn["n_min_main"]
        for c in syn["correct"]["cells"]:
            ex_s.append({"input": json.dumps({k: c[k] for k in ["R", "iota", "n_p"]}), "output": c["truth"],
                         "predict_share_correct_main": fmt(c[f"share_{c['truth']}"] if c["truth"] != "NULL" else c["share_UNDETERMINED"]),
                         "predict_share_correct_nmin5": fmt(c["share_correct_nmin5"]),
                         "metadata_n_edges": c["n_edges"], "metadata_median_n_children": c["median_n_children"],
                         "metadata_tested_share": c["tested_share"],
                         "metadata_label_shares_main": {s: c[f"share_{s}"] for s in ["SOURCE", "SINK", "FADING", "UNDETERMINED"]},
                         "metadata_n_min_main": nm})
    meta = {
        "method_name": "Citation gate, viability labels and power check (iteration 2)",
        "description": ("Gate A (within-host non-canonical traced share) vs the iteration-1 lenient any-parent share (baseline); "
                        "citation-lineage viability states (SOURCE/SINK/FADING) with paper-cluster bootstrap + BH, benchmarked "
                        "against stationary reference concepts; synthetic validation with known truth; simulation MDEs for H1 "
                        "(delta-AUC under the pre-registered SELECTION RULE) and Gate B (PPML) before any W2 outcome."),
        "prereg": {"sha256": sha, "file": "prereg/prereg_freeze.json",
                   "timestamp": (WS / "prereg" / "prereg_freeze.sha256").read_text().split("frozen_at_utc")[-1].strip(),
                   "deviations": "prereg/deviations.md"},
        "lenient_loader_check": _j(RESULTS / "gate_a" / "lenient_loader_check.json"),
        "gate_A": _j(RESULTS / "gate_a" / "gate_A_verdict.json"),
        "graft_fallback": _j(RESULTS / "gate_a" / "graft_fallback_summary.json"),
        "reconciliation_audit": _j(RESULTS / "audit" / "audit_summary.json"),
        "viability": _j(RESULTS / "viability" / "viability_summary.json"),
        "baseline_comparison": baseline_comparison(e),
        "synthetic_validation": {k: v for k, v in (syn or {}).items() if k not in ("correct", "pi_host_0.8x", "pi_host_1.25x", "pi_drift_10pct", "rho0_3refs")}
        | {k: {kk: vv for kk, vv in v.items() if kk not in ("cells",)} for k, v in (syn or {}).items()
           if k in ("correct", "pi_host_0.8x", "pi_host_1.25x", "pi_drift_10pct", "rho0_3refs")},
        "p1": _j(RESULTS / "p1" / "p1_summary.json"),
        "origin_cooling": _j(RESULTS / "origin" / "origin_summary.json"),
        "power_projection": _j(RESULTS / "power" / "projection.json"),
        "power_h1": _j(RESULTS / "power" / "h1_mde.json"),
        "power_gate_b": _j(RESULTS / "power" / "gate_b.json"),
        "decisions": _j(RESULTS / "power" / "decisions.json"),
        "leakage": {"t_max_used_le_t_all_edges": True, "tests": "tests/test_leakage.py (mutation + static)",
                    "host_W2_counts_computed": False},
        "no_api_no_llm": True,
    }
    out = {"metadata": _clean(meta), "datasets": [
        {"dataset": "viability_layer_edges", "examples": ex_v},
        {"dataset": "gate_a_edges", "examples": ex_g}] + ([{"dataset": "synthetic_validation_cells", "examples": ex_s}] if ex_s else [])}
    (WS / "method_out.json").write_text(json.dumps(_clean(out), indent=1))
    logger.info(f"method_out.json: {len(ex_v)} edges, {len(ex_g)} gate edges, {len(ex_s)} synthetic cells; "
                f"{(WS / 'method_out.json').stat().st_size / 1e6:.2f} MB")
