"""Sample construction for the G rows (shared by the freeze, the screen run and the post-opening runs)."""
from __future__ import annotations

import pandas as pd

import g_lib as L

A_NEED = ["A_cont", "CT"] + L.CTRL2


def refac(s: pd.DataFrame) -> pd.DataFrame:
    s = s.reset_index(drop=True).copy()
    for c, key in (("cxe", s.concept_id + "_" + s.e.astype(str)), ("dxe", s.d.astype(str) + "_" + s.e.astype(str)),
                   ("cfe", s.concept_id), ("efe", s.e.astype(str)), ("dfe", s.d.astype(str))):
        s[c] = pd.factorize(key)[0]
    return s


def load(fold: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """(window table, co-primary table) for 'screen', 'heldout' or 'pooled' (fold column set to 'pooled')."""
    if fold == "pooled":
        w = pd.concat([pd.read_parquet(L.RES / f"g_features_{f}_window.parquet") for f in ("screen", "heldout")],
                      ignore_index=True)
        c = pd.concat([pd.read_parquet(L.RES / f"g_features_{f}_coprimary.parquet") for f in ("screen", "heldout")],
                      ignore_index=True)
        w["fold_orig"], c["fold_orig"] = w.fold, c.fold
        w["fold"], c["fold"] = "pooled", "pooled"
        return w, c
    return (pd.read_parquet(L.RES / f"g_features_{fold}_window.parquet"),
            pd.read_parquet(L.RES / f"g_features_{fold}_coprimary.parquet"))


def window_samples(win: pd.DataFrame, fold: str) -> dict[str, pd.DataFrame]:
    sw = L.prep_sample(win, pop="SENSITIVITY", fold=fold, need=A_NEED)
    sw["multi_f"] = sw.multi.astype(float)
    sw["A_x_multi"] = sw.A_cont * sw.multi_f
    return {"G1_all_window": sw, "G1_multi": refac(sw[sw.multi]), "G1_single": refac(sw[~sw.multi]),
            "G1_multi_MAIN": refac(sw[sw.multi & sw.MAIN])}


def coprimary_sample(cop: pd.DataFrame, fold: str) -> pd.DataFrame:
    return L.prep_sample(cop, pop="MAIN", fold=fold, need=A_NEED)
