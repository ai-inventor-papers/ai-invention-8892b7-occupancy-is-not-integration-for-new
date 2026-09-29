#!/usr/bin/env python3
"""K2 Step 8: independent audit (separate code path from k2/k2_lib.py).

(a) 30 random entries (seed 20261001; 10 per fold): recompute H_p, F_p, K_B, s_dB, G_H, G_F, A_cont, A_lift with
    plain Python loops DIRECTLY from the raw files (dataset_5 p2/profiles.jsonl, exp_9 profiles_fetched.jsonl, the
    exp_9 bg shares, dataset_5 subfield_year_totals.json). The per-event tag multiset is read from the prepared
    partner CSR (the multiset itself was re-derived from raw works in iterations 3/4 and is gate-checked by GATE-A).
    Tolerance 1e-9 against results/partner_generality.parquet.
(b) pyfixest fepois (CRV1 concept) on the ppml-pruned K2 samples for M0-M3: |db| < 1e-4 per fold; pooled retention
    recomputed from the pyfixest coefficients / SEs.
(c) shuffled-G placebo: G_H and G_F permuted jointly across events within concept, 50 draws per fold: retention
    should centre on 1.0.
(d) oracle positive control: G_H := A_cont + N(0, (0.1 SD(A_cont))^2): retention should approach 0.
Output: audit/audit_k2.json.
"""
from __future__ import annotations

import json
import math
import os
import pickle
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

WS = Path(__file__).resolve().parents[1]
LOOP = Path(os.environ.get("AII_DEPS_ROOT", WS.parents[2]))
D5 = LOOP / "round-2" / "." / "gen_art_dataset_5"
sys.path.insert(0, str(WS / "d2" / "src"))
import ppml  # noqa: E402  (only for the pruning mask the headline fits used)
from loguru import logger  # noqa: E402

logger.remove()
logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
logger.add(WS / "logs" / "audit_k2.log", rotation="30 MB", level="DEBUG")
SEED = 20261001
CTRL = ["prox_od", "RD", "log_n_partner_tags", "cov", "demic", "mean_topic_score", "boundary_share",
        "abstract_share", "mom_d", "log_centrality", "log_W1"]
BLOCK = {2005: "2000-2004", 2010: "2005-2009", 2015: "2010-2014"}


def blk(e: int) -> str:
    return BLOCK[2005 if e < 2010 else (2010 if e < 2015 else 2015)]


def read_profiles(paths: list[Path]) -> dict:
    out = {}
    for p in paths:
        for line in p.read_text().splitlines():
            if not line.strip():
                continue
            r = json.loads(line)
            key = (int(r["node_id"][1:]), r["block"])
            if key in out:
                continue
            sc = r["subfield_counts"]
            unk = int(sc.get("unknown", 0))
            out[key] = (int(r["total"]) - unk, {int(k): int(v) for k, v in sc.items() if k != "unknown"})
    return out


def plain_entropy(counts: dict, K: int) -> float:
    tot = 0
    for v in counts.values():
        tot += v
    h = 0.0
    for v in counts.values():
        if v > 0:
            p = v / tot
            h -= p * math.log(p)
    return h / math.log(K)


def audit_entries(pg: pd.DataFrame) -> dict:
    tot = json.loads((D5 / "hyd" / "context" / "subfield_year_totals.json").read_text())["variants"]["all_types"]
    K, size = {}, {}
    for b in ("2000-2004", "2005-2009", "2010-2014"):
        y0 = int(b[:4])
        acc = {}
        for y in range(y0, y0 + 5):
            for sf, n in tot[str(y)]["subfield"].items():
                acc[int(sf)] = acc.get(int(sf), 0) + int(n)
        K[b] = sum(1 for v in acc.values() if v > 0)
        allw = sum(acc.values())
        for sf, v in acc.items():
            size[(sf, b)] = v / allw
    prof_main = read_profiles([D5 / "p2" / "profiles.jsonl"])
    prof_mesh = read_profiles([D5 / "p2" / "profiles.jsonl", WS / "mesh" / "results" / "nativeness" /
                               "profiles_fetched.jsonl"])
    bg = pickle.loads((WS / "mesh" / "cache" / "bg_shares.pkl").read_bytes())
    Gm = pickle.loads((WS / "d2" / "results" / "cache" / "prepared.pkl").read_bytes())
    Gs = pickle.loads((WS / "mesh" / "cache" / "mesh_prepared.pkl").read_bytes())
    rng = np.random.default_rng(SEED)
    rows, worst = [], 0.0
    for fold in ("screen", "heldout", "mesh"):
        sub = pg[pg.fold == fold].reset_index(drop=True)
        G = Gs if fold == "mesh" else Gm
        con = G["concepts"].set_index("concept_id")
        ptr, idx = G["P"]
        prof = prof_mesh if fold == "mesh" else prof_main
        a_all = sub.A_cont.to_numpy(float)
        c0f = 0.5 * float(a_all[a_all > 0].min()) if (a_all == 0).any() else 0.0  # spec zero-handling, fold-wide
        for i in rng.choice(len(sub), 10, replace=False):
            ev = sub.iloc[int(i)]
            c = con.loc[ev.concept_id]
            own = set(c.own_nodes) if fold == "mesh" else ({int(c.own_node)} if pd.notna(c.own_node) else set())
            r, y = G["links"][ev.concept_id]
            b = blk(int(ev.e))
            shares, Hs, Fs = [], [], []
            for row, yy in zip(r.tolist(), y.tolist()):
                if yy != int(ev.e) or int(G["W"]["sub"][row]) != int(ev.d):
                    continue
                for j in idx[ptr[row]:ptr[row + 1]].tolist():
                    if j in own:
                        continue
                    p = prof.get((j, b))
                    if p is not None:
                        tk, counts = p
                        shares.append(counts.get(int(ev.d), 0) / tk if tk > 0 else 0.0)
                        Hs.append(plain_entropy(counts, K[b]))
                        Fs.append(math.log(tk))
                    elif fold == "mesh" and (j, b) in bg:
                        v = bg[(j, b)]
                        shares.append(v[2].get(int(ev.d), 0.0) / v[1])
            a = sum(shares) / len(shares)
            gh = sum(Hs) / len(Hs)
            gf = sum(Fs) / len(Fs)
            sdb = size[(int(ev.d), b)]
            lift = math.log((a + c0f) / sdb) if a + c0f > 0 else float("nan")
            d = {"fold": fold, "concept_id": ev.concept_id, "d": int(ev.d), "e": int(ev.e),
                 "A_cont": abs(a - ev.A_cont), "G_H": abs(gh - ev.G_H), "G_F": abs(gf - ev.G_F),
                 "s_dB": abs(sdb - ev.s_dB), "K_B": abs(K[b] - ev.K_B)}
            if a + c0f > 0:
                d["A_lift"] = abs(lift - ev.A_lift)
            rows.append(d)
            worst = max(worst, max(v for k, v in d.items() if k in ("A_cont", "G_H", "G_F", "s_dB", "K_B", "A_lift")))
    return {"n_entries": len(rows), "max_abs_diff": worst, "PASS": bool(worst <= 1e-9), "rows": rows}


def pf_fit(d: pd.DataFrame, xs: list[str]):
    import pyfixest as pf
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return pf.fepois(f"Y_strict ~ {' + '.join(xs)} | cfe + efe + dfe", data=d, offset="offset",
                         vcov={"CRV1": "concept_id"}, fixef_tol=1e-12, iwls_tol=1e-12, iwls_maxiter=500)


def ppml_b(s: pd.DataFrame, xs: list[str]) -> float | None:
    fes = [s[c].to_numpy() for c in ("cfe", "efe", "dfe")]
    r = ppml.fit(s.Y_strict.to_numpy(float), s[xs].to_numpy(float), fes, s.offset.to_numpy(),
                 s.concept_id.to_numpy(), maxit=500, tol=1e-12)
    return None if r is None else float(r["coef"][0])


def refac(s: pd.DataFrame) -> pd.DataFrame:
    s = s.reset_index(drop=True).copy()
    for c, k in (("cfe", s.concept_id), ("efe", s.e.astype(str)), ("dfe", s.d.astype(str))):
        s[c] = pd.factorize(k)[0]
    return s


@logger.catch(reraise=True)
def main() -> None:
    out = {}
    pg = pd.read_parquet(WS / "results" / "partner_generality.parquet")
    out["a_entries"] = audit_entries(pg)
    logger.info(f"(a) max |diff| {out['a_entries']['max_abs_diff']:.2e} PASS {out['a_entries']['PASS']}")
    cache = pickle.loads((WS / "cache" / "k2_samples.pkl").read_bytes())
    summ = json.loads((WS / "results" / "k2_summary.json").read_text())
    models = {"M0": ["A_cont"], "M1": ["A_cont", "G_H", "G_F"], "M2": ["A_lift"], "M3": ["A_lift", "G_H", "G_F"]}
    key = {"M0": "M0_A_cont", "M1": "M1_A_cont", "M2": "M2_A_lift", "M3": "M3_A_lift"}
    b_pf, ok_all = {}, True
    rngd = np.random.default_rng(SEED)
    out["b_pyfixest"], out["c_shuffled_G"], out["d_oracle"] = {}, {}, {}
    for fold in ("screen", "heldout", "mesh"):
        s = refac(cache[fold]["k2"])
        fes = [s[c].to_numpy() for c in ("cfe", "efe", "dfe")]
        keep = ppml.fit(s.Y_strict.to_numpy(float), s[["A_cont", "CT"] + CTRL].to_numpy(float), fes,
                        s.offset.to_numpy(), s.concept_id.to_numpy(), maxit=500, tol=1e-12)["keep"]
        d = s[keep].copy()
        fo = {}
        for m, x0 in models.items():
            xs = x0 + ["CT"] + CTRL
            mm = pf_fit(d, xs)
            bp, sp = float(mm.coef()[x0[0]]), float(mm.se()[x0[0]])
            own = summ["folds"][fold][key[m]]
            fo[m] = {"b_pf": bp, "se_pf": sp, "b_own": own["b"], "se_own": own["se"], "abs_db": abs(bp - own["b"]),
                     "se_rel_diff": abs(sp - own["se"]) / sp, "sd": float(d[x0[0]].std())}
            ok_all &= fo[m]["abs_db"] < 1e-4
        fo["ret_pf"] = fo["M1"]["b_pf"] / fo["M0"]["b_pf"]
        fo["ret_own"] = summ["folds"][fold]["ret"]
        out["b_pyfixest"][fold] = fo
        b_pf[fold] = fo
        logger.info(f"(b) {fold}: max |db| {max(fo[m]['abs_db'] for m in models):.2e}; ret pf {fo['ret_pf']:.4f} "
                    f"own {fo['ret_own']:.4f}")
        # (c) shuffled G within concept
        x0 = ["A_cont", "CT"] + CTRL
        b0 = ppml_b(s, x0)
        rets = []
        groups = list(s.groupby("cfe").indices.values())
        for k in range(50):
            ss = s.copy()
            gh, gf = ss.G_H.to_numpy().copy(), ss.G_F.to_numpy().copy()
            for ix in groups:
                p = ix[rngd.permutation(len(ix))]
                gh[ix], gf[ix] = gh[p], gf[p]
            ss["G_H"], ss["G_F"] = gh, gf
            b1 = ppml_b(ss, ["A_cont", "G_H", "G_F", "CT"] + CTRL)
            if b1 is not None and b0:
                rets.append(b1 / b0)
        rets = np.array(rets)
        out["c_shuffled_G"][fold] = {"n": int(len(rets)), "ret_mean": float(rets.mean()), "ret_sd": float(rets.std()),
                                     "ret_q025_q975": [float(np.quantile(rets, .025)), float(np.quantile(rets, .975))],
                                     "PASS": bool(abs(rets.mean() - 1) < 0.05)}
        # (d) oracle
        ss = s.copy()
        ss["G_H"] = ss.A_cont + rngd.normal(0, 0.1 * ss.A_cont.std(), len(ss))
        fes = [ss[c].to_numpy() for c in ("cfe", "efe", "dfe")]
        xs = ["A_cont", "G_H", "G_F", "CT"] + CTRL
        ro = ppml.fit(ss.Y_strict.to_numpy(float), ss[xs].to_numpy(float), fes, ss.offset.to_numpy(),
                      ss.concept_id.to_numpy(), maxit=500, tol=1e-12)
        b1, bgh = float(ro["coef"][0]), float(ro["coef"][1])
        r_or = float(np.corrcoef(ss.A_cont, ss.G_H)[0, 1])
        out["d_oracle"][fold] = {
            "ret": b1 / b0, "se_A_oracle": float(ro["se"][0]), "se_A_M0": None, "corr_A_oracle_G_H": r_or,
            "PASS": bool(abs(b1 / b0) < 0.25),
            "d2_total_conserved_(b_A+b_GH)/b0": (b1 + bgh) / b0,
            "d2_PASS": bool(0.8 <= (b1 + bgh) / b0 <= 1.25),
            "note": "as specified the oracle is near-collinear (r ~ 0.995): the split between A_cont and the oracle "
                    "is not identified (SE inflated ~10x), so ret is noise around any value; d2 checks that the "
                    "total effect is conserved; the well-posed positive control is the Step-3 DGP-G simulation "
                    "(outcome generated by generality), see d3"}
        logger.info(f"(c) {fold}: shuffled-G ret mean {rets.mean():.3f}; (d) oracle ret {b1 / b0:.3f}")
    # pooled retention from pyfixest numbers (IVW of log-IRR/SD with CRV1 SEs)
    num = den = w0s = w1s = 0.0
    for f, fo in b_pf.items():
        w0 = 1 / (fo["M0"]["se_pf"] * fo["M0"]["sd"]) ** 2
        w1 = 1 / (fo["M1"]["se_pf"] * fo["M1"]["sd"]) ** 2
        den += w0 * fo["M0"]["b_pf"] * fo["M0"]["sd"]
        num += w1 * fo["M1"]["b_pf"] * fo["M1"]["sd"]
        w0s += w0
        w1s += w1
    ret_pool_pf = (num / w1s) / (den / w0s)
    out["b_pyfixest"]["pooled_ret_pf"] = ret_pool_pf
    out["b_pyfixest"]["pooled_ret_own"] = summ["pooled"]["ret"]
    out["b_pyfixest"]["PASS"] = bool(ok_all and abs(ret_pool_pf - summ["pooled"]["ret"]) < 1e-3)
    pw = json.loads((WS / "results" / "k2_power.json").read_text())
    out["d3_positive_control_step3_DGP_G"] = {f: pw["folds"][f]["DGP_G"] for f in ("screen", "heldout", "mesh")}
    out["d3_PASS"] = bool(all(pw["folds"][f]["DGP_G"]["P_ret_lt_0.5"] >= 0.95 for f in ("screen", "heldout", "mesh")))
    out["summary"] = {"a_entries": out["a_entries"]["PASS"], "b_pyfixest": out["b_pyfixest"]["PASS"],
                      "c_shuffled_G": all(v["PASS"] for v in out["c_shuffled_G"].values()),
                      "d_oracle_as_specified": all(v["PASS"] for v in out["d_oracle"].values()),
                      "d2_oracle_total_conserved": all(v["d2_PASS"] for v in out["d_oracle"].values()),
                      "d3_positive_control_DGP_G": out["d3_PASS"]}
    (WS / "audit" / "audit_k2.json").write_text(json.dumps(out, indent=1, default=float))
    logger.info(f"audit summary: {out['summary']}; pooled ret pf {ret_pool_pf:.4f} own {summ['pooled']['ret']:.4f}")


if __name__ == "__main__":
    sys.exit(main())
