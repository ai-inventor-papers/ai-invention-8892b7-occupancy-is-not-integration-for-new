"""STAGE 9: author-disjoint newcomer uptake on MeSH (computed ONCE, only after the spec freeze).

Guard: refuses to run unless sha256(results/mesh_spec.json) equals results/mesh_spec.sha256 AND the features file
hashes recorded in the spec match the files on disk.

Entry events (vendored exp_7 outcomes.compute_Y, unchanged):
  Pset(c, e) = authors of c-papers in [e-5, e] U their co-authors on ANY MeSH-corpus work (117,253) in [e-5, e]
  Y_strict = W2 = {e+k : k = 1..5} d-papers of c with no author in Pset (papers without author ids excluded, counted);
  Y_lenient (>= 1 author not in Pset), Y_all, EST_bin (Y_strict >= 3 and d-papers in >= 3 of the 5 W2 years)
G1 events: same outcome with W2 = [t+2, t+6] and the Pset window [t-5, t+1] (compute_Y_window below; it equals the
vendored compute_Y for offsets (1, 5, -5, 0), which tests/test_mesh.py checks on the main screen).
"""
from __future__ import annotations

import json
import time

import numpy as np
import pandas as pd
from loguru import logger
from scipy import sparse

import common
from common import RESULTS, dump, sha256_file

SPEC = RESULTS / "mesh_spec.json"
SPEC_SHA = RESULTS / "mesh_spec.sha256"


def verify_freeze() -> dict:
    if not SPEC.exists() or not SPEC_SHA.exists():
        raise RuntimeError("mesh_spec.json is not frozen: outcomes refused")
    spec = json.loads(SPEC.read_text())
    want = SPEC_SHA.read_text().split()[0]
    got = common.sha256_json(spec)
    if want != got:
        raise RuntimeError(f"mesh_spec.json hash {got} != frozen {want}: outcomes refused")
    for name, h in spec["hashes"]["features"].items():
        if sha256_file(RESULTS / name) != h:
            raise RuntimeError(f"{name} changed after the freeze: outcomes refused")
    return spec


class WindowCoauthor:
    def __init__(self, G: dict):
        ptr, idx = G["AU"]
        n = len(ptr) - 1
        self.M = sparse.csr_matrix((np.ones(len(idx), np.int8), idx, ptr), shape=(n, G["n_authors"]))
        self.year = G["W"]["year"]
        self.cache: dict = {}

    def prior_set(self, authors: np.ndarray, lo: int, hi: int) -> np.ndarray:
        if (lo, hi) not in self.cache:
            self.cache[(lo, hi)] = self.M[np.flatnonzero((self.year >= lo) & (self.year <= hi))]
        Mw = self.cache[(lo, hi)]
        v = np.zeros(self.M.shape[1], np.int8)
        v[authors] = 1
        hit = np.flatnonzero(Mw @ v)
        mask = np.zeros(self.M.shape[1], bool)
        mask[authors] = True
        if len(hit):
            mask[np.unique(Mw[hit].indices)] = True
        return mask


def compute_Y_window(G: dict, events: pd.DataFrame, tcol: str, w2: tuple[int, int], pwin: tuple[int, int],
                     links: dict | None = None, cai: WindowCoauthor | None = None) -> pd.DataFrame:
    """Y for events at reference year t = events[tcol]: W2 = [t + w2[0], t + w2[1]], Pset window [t + pwin[0], t + pwin[1]]."""
    W = G["W"]
    AUp, AUi = G["AU"]
    links = links or G["links"]
    cai = cai or WindowCoauthor(G)
    out = []
    for cid, g in events.groupby("concept_id"):
        r, y = links[cid]
        sub = W["sub"][r]
        cache = {}
        for ev in g.itertuples():
            d, t = int(ev.d), int(getattr(ev, tcol))
            if t not in cache:
                lo, hi = t + pwin[0], t + pwin[1]
                seeds = np.unique(np.concatenate([AUi[AUp[k]:AUp[k + 1]] for k in r[(y >= lo) & (y <= hi)]]
                                                 or [np.zeros(0, np.int64)]))
                cache[t] = cai.prior_set(seeds, lo, hi)
            ps = cache[t]
            m2 = (sub == d) & (y >= t + w2[0]) & (y <= t + w2[1])
            strict = lenient = noauth = 0
            for k in r[m2]:
                a = AUi[AUp[k]:AUp[k + 1]]
                if len(a) == 0:
                    noauth += 1
                    continue
                inp = ps[a]
                if not inp.any():
                    strict += 1
                if not inp.all():
                    lenient += 1
            yrs = len(set((y[m2] - t).tolist()))
            out.append({"index": ev.Index, "Y_strict": strict, "Y_lenient": lenient, "Y_all": int(m2.sum()),
                        "n_w2_noauthor": noauth, "w2_years_present": yrs, "EST_bin": int(strict >= 3 and yrs >= 3),
                        "pset_size": int(ps.sum())})
    return pd.DataFrame(out).set_index("index")


def run() -> dict:
    import load_mesh
    import outcomes as voutcomes  # vendored exp_7
    spec = verify_freeze()
    t0 = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    logger.info(f"OUTCOMES START {t0} (spec {SPEC_SHA.read_text().split()[0][:12]})")
    with open(common.LOGS / "outcome_log.txt", "a") as f:
        f.write(f"first outcome computation started {t0}\n")
    G = load_mesh.prepare()
    fm = pd.read_parquet(RESULTS / "features_mesh.parquet")
    y = voutcomes.compute_Y(G, fm)
    om = fm.join(y)
    om.to_parquet(RESULTS / "outcomes_mesh.parquet", index=False)
    g1 = pd.read_parquet(RESULTS / "features_mesh_g1.parquet")
    cai = WindowCoauthor(G)
    yg = compute_Y_window(G, g1, "g1_t", (2, 6), (-5, 1), cai=cai)
    og = g1.join(yg)
    og.to_parquet(RESULTS / "outcomes_mesh_g1.parquet", index=False)
    fu = pd.read_parquet(RESULTS / "features_mesh_union.parquet")
    yu = compute_Y_window(G, fu, "e", (1, 5), (-5, 0), links=G["links_union"], cai=cai)
    ou = fu.join(yu)
    ou.to_parquet(RESULTS / "outcomes_mesh_union.parquet", index=False)
    summ = {"started_utc": t0, "n_events": int(len(om)), "Y_strict_zero_share": float((om.Y_strict == 0).mean()),
            "Y_strict_mean": float(om.Y_strict.mean()), "Y_all_mean": float(om.Y_all.mean()),
            "n_w2_noauthor_total": int(om.n_w2_noauthor.sum()), "EST_bin_share": float(om.EST_bin.mean()),
            "g1": {"n": int(len(og)), "Y_strict_zero_share": float((og.Y_strict == 0).mean())},
            "union": {"n": int(len(ou)), "Y_strict_zero_share": float((ou.Y_strict == 0).mean())}}
    dump(RESULTS / "outcomes_mesh_summary.json", summ)
    logger.info(f"outcomes: {summ}")
    return summ
