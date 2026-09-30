"""STEP 5 (P1): W1-only entropy / Rao-Stirling state shares, curves over n_min, tercile moves; (c,t) features for power."""
from __future__ import annotations

import json
import pickle

import numpy as np
import pandas as pd
from loguru import logger

import io_load
from common import RESULTS, SEED
from labels import NMIN_BINS

OUT = RESULTS / "p1"
CACHE = RESULTS / "cache"
STATES = ["SOURCE", "SINK", "FADING", "UNDETERMINED", "ORIGIN"]


def distance_matrix(tax: dict) -> tuple[dict, dict]:
    w = io_load.load_works(["work_id", "publication_year", "subfield_id", "refs_in_corpus"])
    sub_of = dict(zip(w.work_id, w.subfield_id))
    b = w[(w.publication_year >= 2000) & (w.publication_year <= 2004) & w.subfield_id.notna()]
    x = b[["subfield_id", "refs_in_corpus"]].explode("refs_in_corpus").dropna()
    x["cited_sub"] = x.refs_in_corpus.map(sub_of)
    x = x.dropna(subset=["cited_sub"])
    C = x.groupby(["subfield_id", "cited_sub"]).size().unstack(fill_value=0)
    out_n = C.sum(1)
    good = out_n[out_n >= 50].index.astype(int).tolist()
    Cg = C.loc[[g for g in good]].astype(float)
    norm = np.sqrt((Cg ** 2).sum(1))
    cos = (Cg.to_numpy() @ Cg.to_numpy().T) / np.outer(norm, norm)
    cos_d = {(int(a), int(b_)): float(1 - cos[i, j]) for i, a in enumerate(Cg.index) for j, b_ in enumerate(Cg.index)}
    sf, fd = tax["sub_field"], tax["field_domain"]

    def tax_d(a: int, b_: int) -> float:
        if a == b_:
            return 0.0
        fa, fb = sf.get(a), sf.get(b_)
        if fa is not None and fa == fb:
            return 1 / 3
        if fa is not None and fb is not None and fd.get(fa) == fd.get(fb):
            return 2 / 3
        return 1.0
    return cos_d, {"tax_d": tax_d, "n_cosine_subfields": len(good), "n_citations": int(len(x))}


def dist(a: int, b: int, cos_d: dict, tax_d) -> tuple[float, str]:
    if (a, b) in cos_d:
        return cos_d[(a, b)], "cosine"
    return tax_d(a, b), "taxonomy"


def ct_table(ct: list[dict], e: pd.DataFrame, con: pd.DataFrame, cos_d: dict, tax_d, n_min: int | None) -> pd.DataFrame:
    """Per (c,t) shares by state. n_min None -> state_main, else state_nmin{n}."""
    col = "state_main" if n_min is None else f"state_nmin{n_min}"
    st = {(r.concept_id, r.t, r.d): getattr(r, col) for r in e.itertuples()}
    mom = e.groupby(["concept_id", "t"]).mom.mean()
    grow = e.groupby(["concept_id", "t"]).growing_edge.sum()
    meta = con.set_index("concept_id")
    rows = []
    src_counter = {"cosine": 0, "taxonomy": 0}
    for r in ct:
        cid, t, cnt = r["concept_id"], r["t"], r["counts"]
        o = int(meta.origin_sub[cid])
        tot = sum(cnt.values())
        if tot == 0:
            continue
        subs = np.array(list(cnt.keys()))
        p = np.array([cnt[s] for s in subs], float) / tot
        h = -p * np.log(p)
        H = float(h.sum())
        lab = np.array(["ORIGIN" if s == o else st.get((cid, t, int(s)), "UNDETERMINED") for s in subs])
        D = np.zeros((len(subs), len(subs)))
        for i, a in enumerate(subs):
            for j, b in enumerate(subs):
                if i != j:
                    D[i, j], src = dist(int(a), int(b), cos_d, tax_d)
                    src_counter[src] += 1
        rs_i = (D * np.outer(p, p)).sum(1)
        RS = float(rs_i.sum())
        rec = {"concept_id": cid, "t": t, "age": t - int(meta.F[cid]), "F_band": meta.F_band[cid], "fold": meta.fold[cid],
               "H": H, "RS": RS, "n_active": int(len(subs)), "w1_volume": int(tot),
               "mean_host_mom": float(mom.get((cid, t), 0.0)), "growing_breadth": int(grow.get((cid, t), 0)),
               "n_tested_or_labelled": int(sum(x in ("SOURCE", "SINK", "FADING") for x in lab))}
        for s in STATES:
            m = lab == s
            rec[f"H_share_{s}"] = float(h[m].sum() / H) if H > 0 else (1.0 if s == "ORIGIN" else 0.0)
            rec[f"RS_share_{s}"] = float(rs_i[m].sum() / RS) if RS > 0 else np.nan
        ms = (lab == "SOURCE") | (lab == "ORIGIN")
        ps = p[ms] / p[ms].sum()
        rec["H_S"] = float(-(ps * np.log(ps)).sum())
        rows.append(rec)
    df = pd.DataFrame(rows)
    df.attrs["dist_sources"] = src_counter
    return df


def _tax_fn(G):
    sf, fd = G["tax"]["sub_field"], G["tax"]["field_domain"]

    def tax_d(a, b):
        if a == b:
            return 0.0
        fa, fb = sf.get(a), sf.get(b)
        if fa is not None and fa == fb:
            return 1 / 3
        if fa is not None and fb is not None and fd.get(fa) == fd.get(fb):
            return 2 / 3
        return 1.0
    return tax_d


def ensure_distance(G) -> tuple[dict, callable, dict]:
    p = CACHE / "distance.pkl"
    if p.exists():
        cos_d, meta = pickle.loads(p.read_bytes())
    else:
        cos_d, info = distance_matrix(G["tax"])
        meta = {k: v for k, v in info.items() if k != "tax_d"}
        p.write_bytes(pickle.dumps((cos_d, meta)))
    return cos_d, _tax_fn(G), meta


def features(n_min: int | None) -> pd.DataFrame:
    """(c,t) units with >= 1 tested edge at n_min (None = main); BASE + S features (W1 only)."""
    G = io_load.prepare()
    ct = pickle.loads((CACHE / "ct_counts.pkl").read_bytes())
    e = pd.read_csv(RESULTS / "viability" / "viability_layer.csv")
    cos_d, tax_d, _ = ensure_distance(G)
    df = ct_table(ct, e, G["concepts"], cos_d, tax_d, n_min)
    nm = int(e.n_min_main.iloc[0]) if n_min is None else n_min
    tested = e[(e.n_children >= nm) & (e.n_parents >= 1) & (e.n_traced >= 1)]
    keys = set(zip(tested.concept_id, tested.t))
    df = df[[k in keys for k in zip(df.concept_id, df.t)]].copy()
    df["log_w1_volume"] = np.log(df.w1_volume)
    df["S_source_breadth"] = df.H_S
    df["S_sink_share"] = df.H_share_SINK
    return df.reset_index(drop=True)


def _boot_ci(g: pd.DataFrame, col: str, rng: np.random.Generator, B: int = 1000) -> tuple[float, float]:
    cids = g.concept_id.unique()
    means = g.groupby("concept_id")[col].agg(["sum", "count"])
    s, n = means["sum"].to_numpy(), means["count"].to_numpy()
    idx = rng.integers(0, len(cids), (B, len(cids)))
    with np.errstate(invalid="ignore"):
        bs = s[idx].sum(1) / n[idx].sum(1)
    return float(np.nanpercentile(bs, 2.5)), float(np.nanpercentile(bs, 97.5))


def run() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    G = io_load.prepare()
    ct = pickle.loads((CACHE / "ct_counts.pkl").read_bytes())
    e = pd.read_csv(RESULTS / "viability" / "viability_layer.csv")
    cos_d, tax_d, dmeta = ensure_distance(G)
    rng = np.random.default_rng([SEED, 5])
    curves = []
    main_df = None
    for k in [None] + NMIN_BINS:
        df = ct_table(ct, e, G["concepts"], cos_d, tax_d, k)
        if k is None:
            main_df = df
            dmeta["pair_sources_in_ct_tables"] = df.attrs["dist_sources"]
            df.to_csv(OUT / "p1_ct_shares_main.csv", index=False)
            continue
        for (fb, a), g in df.groupby(["F_band", "age"]):
            for s in STATES:
                for kind in ["H", "RS"]:
                    col = f"{kind}_share_{s}"
                    lo, hi = _boot_ci(g, col, rng)
                    curves.append({"n_min": k, "F_band": fb, "age": int(a), "state": s, "measure": kind,
                                   "mean": float(g[col].mean()), "ci95_lo": lo, "ci95_hi": hi, "n_ct": int(len(g)),
                                   "n_concepts": int(g.concept_id.nunique())})
        pooled = {s: float(df[f"H_share_{s}"].mean()) for s in STATES}
        curves.append({"n_min": k, "F_band": "ALL", "age": -1, "state": "ALL", "measure": "H_pooled_json",
                       "mean": np.nan, "ci95_lo": np.nan, "ci95_hi": np.nan, "n_ct": int(len(df)),
                       "n_concepts": int(df.concept_id.nunique()), "pooled": json.dumps(pooled)})
    cv = pd.DataFrame(curves)
    cv.to_csv(OUT / "p1_share_curves.csv", index=False)
    # tercile transitions (main labels): within F_band x age cells
    df = main_df.copy()
    trans = np.zeros((3, 3), int)
    for _, g in df.groupby(["F_band", "age"]):
        if len(g) < 3:
            continue
        th = pd.qcut(g.H.rank(method="first"), 3, labels=False)
        ts = pd.qcut(g.H_S.rank(method="first"), 3, labels=False)
        for a, b in zip(th, ts):
            trans[int(a), int(b)] += 1
    # broad-but-hollow candidates: top tercile of SINK share within cell (W2 comparison deferred)
    bbh = []
    for _, g in df.groupby(["F_band", "age"]):
        if len(g) < 3 or g.H_share_SINK.max() <= 0:
            continue
        cut = g.H_share_SINK.quantile(2 / 3)
        bbh.append(g[(g.H_share_SINK >= cut) & (g.H_share_SINK > 0)])
    bb = pd.concat(bbh) if bbh else pd.DataFrame()
    if len(bb):
        bb = bb.assign(phrase=bb.concept_id.map(G["concepts"].set_index("concept_id").phrase))
        bb.sort_values("H_share_SINK", ascending=False).to_csv(OUT / "broad_but_hollow_candidates.csv", index=False)
    summ = {"status": "DESCRIPTIVE ONLY (Gate A FAIL)", "distance_matrix": dmeta,
            "n_ct_units": int(len(df)), "n_concepts": int(df.concept_id.nunique()),
            "pooled_H_share_main": {s: round(float(df[f"H_share_{s}"].mean()), 4) for s in STATES},
            "pooled_RS_share_main": {s: round(float(df[f"RS_share_{s}"].mean()), 4) for s in STATES},
            "tercile_transition_H_rows_HS_cols": trans.tolist(),
            "tercile_diagonal_share": float(np.trace(trans) / trans.sum()) if trans.sum() else None,
            "n_broad_but_hollow_candidates": int(len(bb)),
            "H_mean": float(df.H.mean()), "RS_mean": float(df.RS.mean())}
    (OUT / "p1_summary.json").write_text(json.dumps(summ, indent=2, default=float))
    logger.info(f"P1: {summ['pooled_H_share_main']} diag={summ['tercile_diagonal_share']}")
