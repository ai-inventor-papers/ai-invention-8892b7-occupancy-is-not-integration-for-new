"""Origin covariates: feedback-cleaned origin incidence O*(c,y) and cooling onsets.

This is the ONLY module that reads c-papers dated after a focal year t, and it reads only ORIGIN-subfield rows
(for cited parents only the boolean 'is origin' is used).
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
from loguru import logger

import io_load
from common import RESULTS

THETAS = [0.6, 0.7, 0.8]
OUT = RESULTS / "origin"


def o_star(papers: pd.DataFrame, cites: np.ndarray, o: int, F: int, totals: dict) -> pd.DataFrame:
    is_o = papers["sub"].to_numpy() == o
    rows_o = np.flatnonzero(is_o)
    assert (papers["sub"].to_numpy()[rows_o] == o).all()
    cites_non_o = np.zeros(len(papers), bool)
    if len(cites):
        sel = is_o[cites[:, 0]] & ~is_o[cites[:, 1]]
        cites_non_o[cites[sel, 0]] = True
    yr = papers.year.to_numpy()
    out = []
    for y in range(F, 2025):
        in_y = is_o & (yr == y)
        raw = int(in_y.sum())
        clean = int((in_y & ~cites_non_o).sum())
        T = totals.get((o, y), 0)
        out.append({"y": y, "O_raw": raw, "O_clean": clean, "T": T,
                    "O_raw_1e4": 1e4 * raw / T if T else np.nan, "O_star": 1e4 * clean / T if T else np.nan})
    return pd.DataFrame(out)


def cooling_onset(df: pd.DataFrame, F: int, theta: float) -> int | None:
    s = df.set_index("y").O_star
    for y in range(F + 3, 2025):
        if y - 3 < F or any(k not in s.index or np.isnan(s[k]) for k in (y, y - 1, y - 2, y - 3)):
            continue
        M = (s[y] + s[y - 1]) / 2
        if M <= theta * max(s[y - 3], s[y - 2], s[y - 1]) and s[y - 1] >= s[y - 2] >= s[y - 3]:
            return y
    return None


def run() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    G = io_load.prepare()
    totals = io_load.load_totals()
    con = G["concepts"]
    series, onsets = [], []
    for c in con[con.arm == "main"].itertuples():
        if pd.isna(c.origin_sub):
            continue
        o, F = int(c.origin_sub), int(c.F)
        cd = G["per"][c.concept_id]
        df = o_star(cd["papers"], cd["cites"], o, F, totals).assign(concept_id=c.concept_id)
        series.append(df)
        rec = {"concept_id": c.concept_id, "origin_subfield": o, "F": F, "fold": c.fold}
        for th in THETAS:
            rec[f"onset_{th}"] = cooling_onset(df, F, th)
        onsets.append(rec)
    s = pd.concat(series, ignore_index=True)
    s.to_csv(OUT / "origin_series.csv", index=False)
    on = pd.DataFrame(onsets)
    on.to_csv(OUT / "cooling_onsets.csv", index=False)
    summ = {f"theta_{th}": {"n_with_onset": int(on[f"onset_{th}"].notna().sum()), "n_concepts": int(len(on)),
                            "onset_year_quantiles": on[f"onset_{th}"].dropna().quantile([.25, .5, .75]).to_dict()}
            for th in THETAS}
    summ["O_star_vs_raw_share_clean"] = float(s.O_clean.sum() / max(s.O_raw.sum(), 1))
    (OUT / "origin_summary.json").write_text(json.dumps(summ, indent=2, default=float))
    logger.info(f"origin: {summ}")
