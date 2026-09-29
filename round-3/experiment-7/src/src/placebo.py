"""STAGE 9: nativeness-permutation placebo (500 draws) and within-cell label shuffle (50 draws).

Placebo: for every profiled node j draw one permutation of the 252 subfield labels (the same for all 4 blocks of j,
so each node keeps its share distribution), recompute A_cont for every event and refit M1 (primary and co-primary
secondary FE). Label shuffle: permute Y_strict within concept x e cells (primary) or within concepts (secondary).
"""
from __future__ import annotations

import json
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd
from loguru import logger

import models
from config import RESULTS, SEED, detect_cpus
from features import block_of, event_tags

BLK = ["2000-2004", "2005-2009", "2010-2014", "2015-2019"]


def build_arrays(G: dict, s: pd.DataFrame) -> dict:
    """Dense share tensor S[node, block, label] and the profiled tags of every event in s (row order)."""
    subs = sorted(G["tax"]["sub_field"])
    lab = {x: i for i, x in enumerate(subs)}
    nodes = sorted({k[0] for k in G["prof"]})
    nid = {x: i for i, x in enumerate(nodes)}
    S = np.zeros((len(nodes), 4, len(subs)))
    for (j, b), (tot, counts, _) in G["prof"].items():
        if tot <= 0:
            continue
        for sf, n in counts.items():
            if sf in lab:
                S[nid[j], BLK.index(b), lab[sf]] = n / tot
    con = G["concepts"].set_index("concept_id")
    te, tn, tb, td = [], [], [], []
    for i, ev in enumerate(s.itertuples()):
        c = con.loc[ev.concept_id]
        own = int(c.own_node) if pd.notna(c.own_node) else None
        _, _, nn = event_tags(G, ev.concept_id, int(ev.d), int(ev.e), own)
        b = BLK.index(block_of(int(ev.e)))
        for j in nn:
            if int(j) in nid and (int(j), BLK[b]) in G["prof"]:
                te.append(i)
                tn.append(nid[int(j)])
                tb.append(b)
                td.append(lab[int(ev.d)])
    return {"S": S, "te": np.array(te), "tn": np.array(tn), "tb": np.array(tb), "td": np.array(td), "n": len(s),
            "n_labels": len(subs)}


def a_cont(arr: dict, perm: np.ndarray | None = None) -> np.ndarray:
    lab = arr["td"] if perm is None else perm[arr["tn"], arr["td"]]
    sh = arr["S"][arr["tn"], arr["tb"], lab]
    num = np.bincount(arr["te"], weights=sh, minlength=arr["n"])
    den = np.bincount(arr["te"], minlength=arr["n"])
    with np.errstate(invalid="ignore", divide="ignore"):
        return num / den


_S = {}


def _init(s: pd.DataFrame, arr: dict):
    _S["s"], _S["arr"] = s, arr


def _draw(seed: int) -> dict:
    s, arr = _S["s"], _S["arr"]
    rng = np.random.default_rng(seed)
    perm = np.stack([rng.permutation(arr["n_labels"]) for _ in range(arr["S"].shape[0])])
    ss = s.copy()
    ss["A_cont"] = a_cont(arr, perm)
    out = {"seed": seed}
    for spec, xs in (("primary", models.EVENT_CONTROLS), ("secondary", models.EVENT_CONTROLS + models.SECONDARY_EXTRA)):
        r = models.fit_one(ss, "Y_strict", ["A_cont", "CT"] + xs, spec)
        out[f"b_A_{spec}"] = None if r is None else r["coef"]["A_cont"]
        out[f"z_A_{spec}"] = None if r is None else r["coef"]["A_cont"] / r["se"]["A_cont"]
        out[f"lnirr_sd_A_{spec}"] = None if r is None else float(np.log(r["irr_sd"]["A_cont"]))
        out[f"b_CT_{spec}"] = None if r is None else r["coef"]["CT"]
    return out


def _shuffle(seed: int) -> dict:
    s = _S["s"]
    rng = np.random.default_rng(seed)
    out = {"seed": seed}
    for spec, cell, xs in (("primary", "cxe", models.EVENT_CONTROLS),
                           ("secondary", "cfe", models.EVENT_CONTROLS + models.SECONDARY_EXTRA)):
        ss = s.copy()
        y = ss.Y_strict.to_numpy().copy()
        for _, ix in ss.groupby(cell).indices.items():
            y[ix] = y[ix][rng.permutation(len(ix))]
        ss["Y_strict"] = y
        r = models.fit_one(ss, "Y_strict", ["A_cont", "CT"] + xs, spec)
        out[f"b_A_{spec}"] = None if r is None else r["coef"]["A_cont"]
        out[f"z_A_{spec}"] = None if r is None else r["coef"]["A_cont"] / r["se"]["A_cont"]
    return out


def run(G: dict, df: pd.DataFrame, draws: int = 500, shuffles: int = 50) -> dict:
    s = models.primary_sample(df)
    arr = build_arrays(G, s)
    chk = a_cont(arr)
    diff = np.nanmax(np.abs(chk - s.A_cont.to_numpy()))
    if not diff < 1e-9:
        raise RuntimeError(f"placebo A_cont reconstruction differs from features by {diff}")
    obs = {spec: models.fit_one(s, "Y_strict", ["A_cont", "CT"] + xs, spec)
           for spec, xs in (("primary", models.EVENT_CONTROLS),
                            ("secondary", models.EVENT_CONTROLS + models.SECONDARY_EXTRA))}
    seeds = [SEED + 1000 + i for i in range(draws)]
    with ProcessPoolExecutor(detect_cpus(), initializer=_init, initargs=(s, arr)) as ex:
        res = list(ex.map(_draw, seeds, chunksize=8))
        sh = list(ex.map(_shuffle, [SEED + 5000 + i for i in range(shuffles)], chunksize=4))
    pl = pd.DataFrame(res)
    pl.to_csv(RESULTS / "placebo_draws.csv", index=False)
    ls = pd.DataFrame(sh)
    ls.to_csv(RESULTS / "label_shuffle_draws.csv", index=False)
    summ = {"draws": draws, "shuffles": shuffles, "A_cont_reconstruction_max_abs_diff": float(diff)}
    for spec in ("primary", "secondary"):
        b = pl[f"b_A_{spec}"].dropna()
        z = pl[f"z_A_{spec}"].dropna()
        e = pl[f"lnirr_sd_A_{spec}"].dropna()
        bo = obs[spec]["coef"]["A_cont"]
        zo = bo / obs[spec]["se"]["A_cont"]
        eo = float(np.log(obs[spec]["irr_sd"]["A_cont"]))
        lb = ls[f"b_A_{spec}"].dropna()
        lz = ls[f"z_A_{spec}"].dropna()
        summ[spec] = {"b_A_obs": bo, "z_A_obs": zo, "lnirr_sd_A_obs": eo, "placebo_n_ok": int(len(b)),
                      "placebo_z_mean": float(z.mean()), "placebo_z_sd": float(z.std()),
                      "perm_p_two_sided_z (primary placebo p)": float((1 + (z.abs() >= abs(zo)).sum()) / (1 + len(z))),
                      "placebo_lnirr_sd_mean": float(e.mean()), "placebo_lnirr_sd_sd": float(e.std()),
                      "perm_p_two_sided_per_sd_effect": float((1 + (e.abs() >= abs(eo)).sum()) / (1 + len(e))),
                      "placebo_b_mean": float(b.mean()), "placebo_b_sd": float(b.std()),
                      "perm_p_two_sided_raw_b": float((1 + (b.abs() >= abs(bo)).sum()) / (1 + len(b))),
                      "placebo_b_q025_q975": [float(b.quantile(.025)), float(b.quantile(.975))],
                      "label_shuffle_b_mean": float(lb.mean()), "label_shuffle_b_sd": float(lb.std()),
                      "label_shuffle_z_mean": float(lz.mean()), "label_shuffle_z_sd": float(lz.std()),
                      "label_shuffle_p_two_sided_z": float((1 + (lz.abs() >= abs(zo)).sum()) / (1 + len(lz)))}
    summ["note"] = ("permuted A_cont has a much smaller SD than the observed A_cont (a random label rarely carries a "
                    "node's mass), so raw b is not scale-comparable; the z statistic is the primary placebo "
                    "statistic (deviations.md #5); raw-b and per-SD-effect p values are reported too")
    (RESULTS / "placebo_summary.json").write_text(json.dumps(summ, indent=1))
    logger.info(f"placebo: {summ}")
    return summ
