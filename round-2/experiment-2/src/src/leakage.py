"""Leakage guard. Every edge-year function accepts ONLY a W1View and asserts its t_max.

origin.py is the only module allowed to read c-papers with year > t (and only origin-subfield rows).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class W1View:
    papers: pd.DataFrame      # c-papers with year <= t (row order = original order, prefix of a year-sorted table)
    cites: np.ndarray         # (child_idx, parent_idx) with BOTH endpoints inside the view
    t_max: int
    n_total: int              # rows in the underlying table (only used for mapping, never for statistics)


def w1_view(cdata: dict, t: int) -> W1View:
    p = cdata["papers"]
    keep = (p["year"].to_numpy() <= t)
    idx = np.flatnonzero(keep)
    remap = -np.ones(len(p), np.int64)
    remap[idx] = np.arange(len(idx))
    view = p.iloc[idx].reset_index(drop=True).copy()
    view.attrs["t_max"] = t
    c = cdata["cites"]
    if len(c):
        ok = keep[c[:, 0]] & keep[c[:, 1]]
        cc = np.stack([remap[c[ok, 0]], remap[c[ok, 1]]], axis=1).astype(np.int64)
    else:
        cc = np.zeros((0, 2), np.int64)
    v = W1View(papers=view, cites=cc, t_max=t, n_total=len(p))
    check_view(v, t)
    return v


def check_view(v: W1View, t: int) -> None:
    assert isinstance(v, W1View), "edge-year functions accept only a W1View"
    assert v.t_max == t, f"view t_max {v.t_max} != t {t}"
    assert v.papers.attrs.get("t_max") == t
    if len(v.papers):
        assert int(v.papers["year"].max()) <= t, "view contains papers after t"
