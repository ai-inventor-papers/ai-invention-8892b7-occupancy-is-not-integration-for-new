"""STAGE 8: robustness grid (screen only). Every row: spec, FE, N, G, b_A, se, b_CT, se, IRR per SD with CIs.

Each variant is fitted with the primary FE (concept x e + d x e) and the co-primary secondary FE (concept + e + d),
because fallback 3 made the secondary spec co-primary.
"""
from __future__ import annotations

from collections import Counter

import numpy as np
import pandas as pd
from loguru import logger

import models
import outcomes
from config import RESULTS, assert_not_sealed
from features import Nativeness, block_of, event_tags, partner_set

CTRL = models.EVENT_CONTROLS
SEC = models.SECONDARY_EXTRA


def _row(name: str, res: dict | None, a_var: str, ct_var: str, fe: str) -> dict:
    if res is None:
        return {"spec": name, "fe": fe, "N": None, "G": None, "note": "fit failed / too few observations"}
    out = {"spec": name, "fe": fe, "N": res["n_retained"], "N_input": res["n_input"], "G": res["G"]}
    for tag, v in (("A", a_var), ("CT", ct_var)):
        if v in res["coef"]:
            out.update({f"b_{tag}": res["coef"][v], f"se_{tag}": res["se"][v], f"p_{tag}": res["p"][v],
                        f"irr_sd_{tag}": res["irr_sd"][v], f"irr_sd_{tag}_lo": res["ci_irr_sd"][v][0],
                        f"irr_sd_{tag}_hi": res["ci_irr_sd"][v][1], f"var_{tag}": v})
    return out


def fit_both(name: str, s: pd.DataFrame, a_var: str = "A_cont", ct_var: str = "CT", y: str = "Y_strict",
             extra: list | None = None) -> list[dict]:
    rows = []
    xs = [v for v in [a_var, ct_var] if v] + (extra or [])
    s = s.dropna(subset=xs + CTRL + SEC).copy()
    for c in ["cxe", "dxe", "cfe", "efe", "dfe"]:
        s[c] = pd.factorize(s[c])[0]
    try:
        rows.append(_row(name, models.fit_one(s, y, xs + CTRL, "primary"), a_var, ct_var, "primary"))
    except (np.linalg.LinAlgError, ValueError) as ex:
        rows.append({"spec": name, "fe": "primary", "note": repr(ex)})
    try:
        rows.append(_row(name, models.fit_one(s, y, xs + CTRL + SEC, "secondary"), a_var, ct_var, "secondary"))
    except (np.linalg.LinAlgError, ValueError) as ex:
        rows.append({"spec": name, "fe": "secondary", "note": repr(ex)})
    return rows


def preperiod_nodes(G: dict, top: int = 1372) -> set:
    """Host co-occurrence ranking recomputed from host c-papers <= 2014 (corpus only); top-`top` nodes."""
    W = G["W"]
    ptr, idx = G["P"]
    con = G["concepts"].set_index("concept_id")
    cnt = Counter()
    for cid, c in con.iterrows():
        r, y = G["links"][cid]
        sub = W["sub_raw"][r]
        o = int(c.origin) if pd.notna(c.origin) else -999
        for row in r[(sub >= 0) & (sub != o) & (y <= 2014)]:
            cnt.update(idx[ptr[row]:ptr[row + 1]].tolist())
    ranked = [k for k, _ in sorted(cnt.items(), key=lambda kv: (-kv[1], kv[0]))[:top]]
    return set(ranked)


def recompute_A(G: dict, s: pd.DataFrame, keep_nodes: set | None = None, window: int = 0) -> pd.DataFrame:
    """A_cont and CT recomputed with a node filter (pre-period profile set) or a wider partner window [e, e+window].
    A wider window reads post-entry host papers, so it is guarded like an outcome computation (screen only)."""
    if window:
        assert_not_sealed(s.concept_id.unique())
    nat = Nativeness(G["prof"])
    con = G["concepts"].set_index("concept_id")
    W = G["W"]
    ptr, idx = G["P"]
    out = {}
    for ev in s.itertuples():
        c = con.loc[ev.concept_id]
        own = int(c.own_node) if pd.notna(c.own_node) else None
        r, y = G["links"][ev.concept_id]
        sub = W["sub"][r]
        d, e, o = int(ev.d), int(ev.e), int(ev.o)
        if window:
            rows = r[(sub == d) & (y >= e) & (y <= e + window)]
            nodes = np.concatenate([idx[ptr[k]:ptr[k + 1]] for k in rows]) if len(rows) else np.zeros(0, np.int64)
            if own is not None:
                nodes = nodes[nodes != own]
        else:
            _, _, nodes = event_tags(G, ev.concept_id, d, e, own)
        comp = partner_set(G, r[(sub == o) & (y >= e - 5) & (y <= e - 1)], own)
        blk = block_of(e)
        sh = []
        for j in nodes:
            if keep_nodes is not None and int(j) not in keep_nodes:
                continue
            v = nat.share(int(j), blk, d)
            if v is not None:
                sh.append(v)
        out[ev.Index] = {"A_cont_v": float(np.mean(sh)) if sh else np.nan,
                         "CT_v": float(np.mean([int(j) in comp for j in nodes])) if len(nodes) else np.nan,
                         "n_rows_window": int(len(rows)) if window else int(ev.n_entry_papers)}
    return pd.DataFrame.from_dict(out, orient="index")


def run(G: dict, df: pd.DataFrame, cai: outcomes.CoauthorIndex | None = None) -> pd.DataFrame:
    base = df[(df.arm == "main") & (df.fold == "screen") & df.kw5].copy()
    base = base.dropna(subset=["A_cont", "CT"] + CTRL + SEC)
    base["cxe"] = base.concept_id + "_" + base.e.astype(str)
    base["dxe"] = base.d.astype(str) + "_" + base.e.astype(str)
    base["cfe"], base["efe"], base["dfe"] = base.concept_id, base.e.astype(str), base.d.astype(str)
    base["offset"] = np.log(base.n_entry_papers.astype(float))
    main = base[base.MAIN]
    rows = []
    rows += fit_both("PRIMARY (MAIN)", main)
    rows += fit_both("STRICT population", base[base.STRICT])
    rows += fit_both("SENSITIVITY (all main-arm)", base)
    rows += fit_both("route B only", main[~main.route_A])
    m2 = main.copy()
    m2["A_x_routeA"] = m2.A_cont * m2.route_A.astype(float)
    rows += fit_both("route interaction (A x routeA)", m2, extra=["A_x_routeA"])
    rows += fit_both("excess anchoring A_cont - A0_cont", main, a_var="A_cont_ex")
    rows += fit_both("binary A, native >= 0.5", main, a_var="A")
    rows += fit_both("binary A, native >= 0.3", main, a_var="A_t03")
    rows += fit_both("binary A, native >= 0.7", main, a_var="A_t07")
    rows += fit_both("A_distinct (0.5)", main, a_var="A_distinct")
    rows += fit_both("bound A_cont_lo (unprofiled share 0)", main, a_var="A_cont_lo")
    rows += fit_both("bound A_cont_hi (unprofiled share 1)", main, a_var="A_cont_hi")
    rows += fit_both("subset cov >= 0.6", main[main["cov"] >= 0.6])
    rows += fit_both("entry papers topic_score >= 0.9", main[main.min_topic_score >= 0.9])
    rows += fit_both("e <= 2018", main[main.e <= 2018])
    rows += fit_both("CT_any (any earlier c-paper)", main, ct_var="CT_any")
    rows += fit_both("exclude n_entry_papers == 1", main[main.n_entry_papers > 1])
    rows += fit_both("A only (M1a)", main, ct_var=None)
    rows += fit_both("CT only (M1b)", main, a_var=None)
    rows += fit_both("outcome Y_lenient", main, y="Y_lenient")
    rows += fit_both("outcome Y_all", main, y="Y_all")
    # pre-period-selected profile set
    keep = preperiod_nodes(G) & {k[0] for k in G["prof"]}
    rc = recompute_A(G, main, keep_nodes=keep)
    mp = main.join(rc)
    rows += fit_both(f"pre-period profile set ({len(keep)} nodes)", mp, a_var="A_cont_v")
    # entry window [e, e+1] for partners; W2 shifted to [e+2, e+6] only if e+6 <= 2024
    mw = main[main.e + 6 <= 2024].copy()
    rw = recompute_A(G, mw, window=1)
    mw = mw.join(rw)
    cai = cai or outcomes.CoauthorIndex(G)
    mw["Y_strict_shift"] = outcomes.compute_Y_shifted(G, mw, cai, shift=1).reindex(mw.index)
    rows += fit_both("partner window [e, e+1], W2 [e+2, e+6]", mw, a_var="A_cont_v", ct_var="CT_v", y="Y_strict_shift")
    # co-author-free (direct-author) newcomer rule
    yd = outcomes.compute_Y(G, main, cai, direct_only=True)
    md = main.copy()
    md["Y_strict_direct"] = yd.Y_strict.reindex(md.index)
    rows += fit_both("newcomer rule: direct authors only (no co-author expansion)", md, y="Y_strict_direct")
    out = pd.DataFrame(rows)
    # field-group strata (descriptive)
    for fg, g in main.groupby("field_group"):
        out = pd.concat([out, pd.DataFrame(fit_both(f"stratum {fg} (descriptive)", g))], ignore_index=True)
    out.to_csv(RESULTS / "d2_robustness.csv", index=False)
    logger.info(f"robustness: {len(out)} rows written")
    return out
