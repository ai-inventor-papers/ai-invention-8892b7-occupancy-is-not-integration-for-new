#!/usr/bin/env python3
"""Independent re-derivation of the headline numbers through a DIFFERENT code path.

- Estimator: pyfixest.fepois (not the vendored ppml.fit); samples built with plain pandas filters; iterative
  singleton / all-zero pruning written here from scratch.
- G2 shares: recomputed tag by tag from the raw nativeness profiles via features.event_tags + a dict lookup (the G run
  used a dense share tensor from placebo.build_arrays).
- Robustness recount: plain csv module over d2_robustness.csv.
- Placebo checks: the same pyfixest test on shuffled regressors must NOT reject at the observed rate.
Writes audit/audit_headline.json.
"""
from __future__ import annotations

import csv
import json
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import pyfixest as pf

warnings.filterwarnings("ignore")
WS = Path(__file__).resolve().parents[1]
RES = WS / "results"
CTRL2 = ["prox_od", "RD", "log_n_partner_tags", "cov", "demic", "mean_topic_score", "boundary_share",
         "abstract_share", "mom_d", "log_centrality", "log_W1"]


def prune(d: pd.DataFrame, y: str, fes: list[str]) -> pd.DataFrame:
    d = d.copy()
    while True:
        n0 = len(d)
        for f in fes:
            g = d.groupby(f)[y]
            d = d[(g.transform("size") > 1) & (g.transform("sum") > 0)]
        if len(d) == n0:
            return d


def fit(d: pd.DataFrame, y: str, xs: list[str], target: str, fes=("concept_id", "e", "d")) -> dict:
    d = d.dropna(subset=xs + [y]).copy()
    d["off"] = np.log(d["n_entry_papers"].astype(float))
    d = prune(d, y, list(fes))
    for f in fes:
        d[f] = d[f].astype(str)
    m = pf.fepois(f"{y} ~ {' + '.join(xs)} | {' + '.join(fes)}", data=d, offset="off",
                  vcov={"CRV1": "concept_id"}, fixef_tol=1e-10, iwls_tol=1e-10, iwls_maxiter=500)
    b, se = float(m.coef()[target]), float(m.se()[target])
    sd = float(d[target].std())
    G = d.concept_id.nunique()
    from scipy import stats
    tq = stats.t.ppf(0.975, G - 1)
    p = float(2 * stats.t.sf(abs(b / se), G - 1))
    return {"irr_sd": float(np.exp(b * sd)), "ci": [float(np.exp((b - tq * se) * sd)), float(np.exp((b + tq * se) * sd))],
            "p": p, "N": int(len(d)), "G": int(G), "b": b}


def shuffled(d: pd.DataFrame, y: str, xs: list[str], target: str, reps: int = 20, within: str | None = None) -> dict:
    rng = np.random.default_rng(7)
    ps = []
    for _ in range(reps):
        s = d.copy()
        if within:
            s[target] = s.groupby(within)[target].transform(lambda v: rng.permutation(v.to_numpy()))
        else:
            s[target] = rng.permutation(s[target].to_numpy())
        try:
            ps.append(fit(s, y, xs, target)["p"])
        except Exception as ex:  # noqa: BLE001 - count a failed placebo fit, do not crash the audit
            print("placebo fit failed", repr(ex))
    ps = np.array(ps)
    return {"reps": int(len(ps)), "share_p_lt_0.05": float((ps < 0.05).mean()), "min_p": float(ps.min()),
            "median_p": float(np.median(ps))}


def main() -> None:
    out = {}
    # 1. held-out co-primary A_cont (confirmatory headline)
    ho = pd.read_parquet(RES / "g_features_heldout_coprimary.parquet")
    s = ho[(ho.arm == "main") & (ho.fold == "heldout") & ho.kw5 & ho.MAIN].dropna(subset=["A_cont", "CT"] + CTRL2)
    conf = json.loads((WS / "d2" / "results" / "heldout_confirmation.json").read_text())["secondary"]
    r = fit(s, "Y_strict", ["A_cont", "CT"] + CTRL2, "A_cont")
    out["heldout_coprimary"] = {"rederived": r, "reported": {"irr_sd": conf["irr_sd"]["A_cont"], "ci": conf["ci_irr_sd"]["A_cont"],
                                                             "p": conf["p"]["A_cont"], "N": conf["n_retained"], "G": conf["G"]},
                                "placebo_shuffle_all": shuffled(s, "Y_strict", ["A_cont", "CT"] + CTRL2, "A_cont"),
                                "placebo_shuffle_within_concept": shuffled(s, "Y_strict", ["A_cont", "CT"] + CTRL2, "A_cont",
                                                                           within="concept_id")}
    print("held-out", json.dumps(out["heldout_coprimary"], default=float)[:900])
    # 2. pooled G1-multi
    w = pd.concat([pd.read_parquet(RES / f"g_features_{f}_window.parquet") for f in ("screen", "heldout")])
    w = w[(w.arm == "main") & w.SENSITIVITY & (w.n_partners_distinct_w >= 5) & w.multi & (w.e <= 2018)]
    w = w.dropna(subset=["A_cont", "CT"] + CTRL2 + ["Y_strict"])
    g1 = fit(w, "Y_strict", ["A_cont", "CT"] + CTRL2, "A_cont")
    rep = pd.read_csv(RES / "g_pooled_rows.csv")
    rr = rep[(rep.row == "G1-multi (co-primary FE)") & (rep["var"] == "A_cont")].iloc[0]
    out["pooled_G1_multi"] = {"rederived": g1, "reported": {"irr_sd": rr.irr_sd, "ci": [rr.irr_sd_lo, rr.irr_sd_hi],
                                                            "N": int(rr.N), "G": int(rr.G)},
                              "placebo_shuffle_all": shuffled(w, "Y_strict", ["A_cont", "CT"] + CTRL2, "A_cont", reps=10)}
    print("G1", json.dumps(out["pooled_G1_multi"], default=float)[:600])
    # 3. pooled G2a NATIVE / ADJACENT with shares rebuilt tag by tag from the raw profiles
    sys.path.insert(0, str(WS / "g"))
    import g_lib as L
    from features import Nativeness, block_of, event_tags
    G = L.io_load_prepare()
    nat = Nativeness(G["prof"])
    con = G["concepts"].set_index("concept_id")
    c = pd.concat([pd.read_parquet(RES / f"g_features_{f}_coprimary.parquet") for f in ("screen", "heldout")],
                  ignore_index=True)
    c = c[(c.arm == "main") & c.kw5 & c.MAIN].dropna(subset=["A_cont", "CT"] + CTRL2 + ["Y_strict"]).copy()
    NAT, ADJ, AC = [], [], []
    for ev in c.itertuples():
        own = con.loc[ev.concept_id].own_node
        own = int(own) if pd.notna(own) else None
        _, _, nodes = event_tags(G, ev.concept_id, int(ev.d), int(ev.e), own)
        sh = [nat.share(int(j), block_of(int(ev.e)), int(ev.d)) for j in nodes]
        sh = np.array([x for x in sh if x is not None])
        NAT.append((sh >= 0.3).mean() if len(sh) else np.nan)
        ADJ.append(((sh >= 0.05) & (sh < 0.3)).mean() if len(sh) else np.nan)
        AC.append(sh.mean() if len(sh) else np.nan)
    c["NAT"], c["ADJ"], c["AC_chk"] = NAT, ADJ, AC
    out["A_cont_rebuild_max_abs_diff"] = float(np.nanmax(np.abs(c.AC_chk - c.A_cont)))
    xs = ["NAT", "ADJ", "CT"] + CTRL2
    rn, ra = fit(c, "Y_strict", xs, "NAT"), fit(c, "Y_strict", xs, "ADJ")
    rp = rep[rep.row == "G2a NATIVE+ADJACENT (native>=0.3, adjacent [0.05,0.3))"].set_index("var")
    out["pooled_G2a"] = {"NAT": {"rederived": rn, "reported": [rp.loc["NAT", "irr_sd"], rp.loc["NAT", "irr_sd_lo"], rp.loc["NAT", "irr_sd_hi"]]},
                         "ADJ": {"rederived": ra, "reported": [rp.loc["ADJ", "irr_sd"], rp.loc["ADJ", "irr_sd_lo"], rp.loc["ADJ", "irr_sd_hi"]]},
                         "reading_rederived": ("host-vocabulary" if ra["ci"][0] > 1 and ra["irr_sd"] >= rn["irr_sd"] else
                                               "grafting" if rn["ci"][0] > 1 and rn["irr_sd"] >= ra["irr_sd"] else "unresolved"),
                         "placebo_shuffle_ADJ": shuffled(c, "Y_strict", xs, "ADJ", reps=10)}
    # 4. pooled G3(combined) % change in log-IRR on the identical sample
    x3 = ["min_topic_score", "host_topic_share", "sec_host_share"]
    c3 = c.dropna(subset=x3)
    bb = fit(c3, "Y_strict", ["A_cont", "CT"] + CTRL2, "A_cont")["b"]
    bw = fit(c3, "Y_strict", ["A_cont", "CT"] + CTRL2 + x3, "A_cont")["b"]
    sm = json.loads((RES / "g_pooled_summary.json").read_text())["G3_pct"]["G3(combined)"]
    out["pooled_G3_combined_pct"] = {"rederived": 100 * (1 - bw / bb), "reported": sm["pct"]}
    print("G2/G3", json.dumps({k: out[k] for k in ("pooled_G2a", "pooled_G3_combined_pct", "A_cont_rebuild_max_abs_diff")}, default=float)[:1200])
    # 5. robustness recount with the csv module
    cnt = {"secondary": [0, 0], "primary": [0, 0]}
    with open(WS / "d2" / "results" / "d2_robustness.csv") as f:
        for row in csv.DictReader(f):
            if row["irr_sd_A"] in ("", "nan") or row["fe"] not in cnt:
                continue
            cnt[row["fe"]][1] += 1
            if float(row["irr_sd_A_lo"]) > 1 and float(row["p_A"]) < 0.05:
                cnt[row["fe"]][0] += 1
    out["robustness_recount"] = {k: {"significant": v[0], "rows_with_A": v[1]} for k, v in cnt.items()}
    print("recount", out["robustness_recount"])
    (WS / "audit" / "audit_headline.json").write_text(json.dumps(out, indent=1, default=float))


if __name__ == "__main__":
    main()
