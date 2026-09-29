"""T1 unit tests for the G4 MeSH replication (run: .venv/bin/python -m pytest -q tests/test_mesh.py)."""
from __future__ import annotations

import json
import pickle
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

WS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WS / "src"))

import common  # noqa: E402,F401  (puts vendor/ on sys.path)
from features import block_of  # noqa: E402  (vendored)


def _csr(lists):
    from io_load import _csr as c
    return c(lists)


def toy_G():
    """5 works of concept c (origin 10, host 20) + 1 non-c work; authors 0..6; partners 101..105."""
    W = {"work_id": np.arange(6, dtype=np.int64), "year": np.array([2008, 2010, 2010, 2012, 2013, 2009], np.int32),
         "sub": np.array([10, 20, 20, 20, 20, 30], np.int32), "sub_raw": np.array([10, 20, 20, 20, 20, 30], np.int32),
         "has_abstract": np.array([1, 1, 0, 1, 1, 1], bool), "topic_score": np.full(6, np.nan, np.float32)}
    P = _csr([[101, 102], [101, 103, 199], [104, 105], [101], [102], [101]])
    AU = _csr([[0, 1], [1, 2], [3], [4], [], [2, 5]])
    concepts = pd.DataFrame([{"concept_id": "c", "origin": 10, "own_nodes": [199], "F": 2008, "overlap_main": False,
                              "retrieval_complete": True, "rule_parity": True}])
    return {"W": W, "P": P, "AU": AU, "n_authors": 6, "concepts": concepts,
            "links": {"c": (np.arange(5, dtype=np.int64), W["year"][:5])},
            "totals": {(20, 2010): 200, (20, 2007): 100}, "tax": {"sub_field": {10: 1, 20: 2, 30: 3}}}


class FakeNat:
    def __init__(self, table):
        self.table = table

    def share(self, node, blk, d):
        v = self.table.get((node, blk))
        return (None, None) if v is None else (v, "exact")


def test_block_of():
    assert block_of(2005) == "2000-2004" and block_of(2009) == "2000-2004"
    assert block_of(2010) == "2005-2009" and block_of(2014) == "2005-2009"
    assert block_of(2015) == "2010-2014" and block_of(2019) == "2010-2014"
    with pytest.raises(ValueError):
        block_of(2004)


def test_anchoring_hand_example():
    from features_mesh import event_features
    G = toy_G()
    c = G["concepts"].iloc[0]
    # entry e = 2010: entry-year host papers rows 1, 2 -> tags 101, 103 (199 = own, dropped), 104, 105
    nat = FakeNat({(101, "2005-2009"): 0.40, (103, "2005-2009"): 0.10, (104, "2005-2009"): 0.02})  # 105 unprofiled
    r, y = G["links"]["c"]
    f = event_features(G, nat, {(10, 20): 0.25}, None, c, 20, 2010, 2010, 2010, 2010, r, y, None)
    assert f["n_tags"] == 4 and f["n_prof_tags"] == 3
    assert f["A_cont"] == pytest.approx((0.40 + 0.10 + 0.02) / 3)
    assert f["A_cont_lo"] == pytest.approx((0.52) / 4) and f["A_cont_hi"] == pytest.approx((0.52 + 1) / 4)
    # companions: origin papers in [2005, 2009] = row 0 -> {101, 102}; entry tags 101,103,104,105 -> 1/4
    assert f["CT"] == pytest.approx(0.25)
    assert f["NATIVE"] == pytest.approx(1 / 3) and f["ADJACENT"] == pytest.approx(1 / 3)
    assert f["FOREIGN"] == pytest.approx(1 / 3)
    assert f["prox_od"] == pytest.approx(0.75)
    assert f["mom_d"] == pytest.approx(np.log(2.0))
    assert f["demic"] == pytest.approx(1 / 3)  # entry authors {1, 2, 3}; prior origin authors {0, 1}


def test_own_node_drop():
    from events_mesh import entry_partners
    G = toy_G()
    out = entry_partners(G, np.array([1]), {199})
    assert out[0].tolist() == [101, 103]


def test_pset_and_y_strict_toy():
    from outcomes_mesh import compute_Y_window
    G = toy_G()
    # add W2 papers for e = 2010 (d = 20): years 2012 (author 4, new), 2013 (no authors)
    ev = pd.DataFrame([{"concept_id": "c", "d": 20, "e": 2010}])
    y = compute_Y_window(G, ev, "e", (1, 5), (-5, 0))
    # Pset(2010) = authors of c-papers in [2005, 2010] = {0,1,2,3} U co-authors on any work in [2005, 2010]:
    # work 5 (2009) has authors {2, 5} -> 5 enters; author 4 is a newcomer
    assert y.Y_strict.iloc[0] == 1 and y.n_w2_noauthor.iloc[0] == 1 and y.Y_all.iloc[0] == 2
    assert y.pset_size.iloc[0] == 5


def test_g1_finder():
    from events_mesh import g1_time
    G = toy_G()
    r, y = G["links"]["c"]
    sub = G["W"]["sub"][r]
    # [2010, 2011]: rows 1 {1,2} and 2 {3} -> author-disjoint -> t = 2010
    assert g1_time(G, r, y, sub, 20, 2010) == 2010
    # shared author 2 in [2010, 2011]; [2012, 2013] has one authored paper (row 4 has none) -> no G1 event
    G2 = toy_G()
    G2["AU"] = _csr([[0, 1], [1, 2], [2], [4], [], [2, 5]])
    assert g1_time(G2, r, y, sub, 20, 2010) is None
    # [2012, 2013] with authors {4} and {5} -> disjoint -> t = 2012
    G3 = toy_G()
    G3["AU"] = _csr([[0, 1], [1, 2], [2], [4], [5], [2, 5]])
    assert g1_time(G3, r, y, sub, 20, 2010) == 2012
    # same author on both -> none
    G4 = toy_G()
    G4["AU"] = _csr([[0, 1], [1, 2], [2], [4], [4], [2, 5]])
    assert g1_time(G4, r, y, sub, 20, 2010) is None


def test_coverage_rule_mock():
    from coverage import covered, parse_groups
    d = {"group_by": [{"key": "https://openalex.org/subfields/2725", "count": 60},
                      {"key": "https://openalex.org/subfields/1702", "count": 5}, {"key": "unknown", "count": 9}]}
    g = parse_groups(d)
    assert g == {2725: 60, 1702: 5}
    pm = {(2725, "2010-2014"): 0.6, (1702, "2010-2014"): 0.1}
    assert covered(pm, 2725, 2012) and not covered(pm, 1702, 2012) and covered(pm, 1702, 2012, 0.05)
    assert not covered(pm, 2725, 2016)


def test_profile_parsing():
    from nativeness import parse_profile
    tot, counts, trunc = parse_profile({"total": 100, "subfield_counts": {"2725": 30, "unknown": 20, "1702": 50},
                                        "truncated_top200": True})
    assert tot == 80 and counts == {2725: 30, 1702: 50} and trunc


def test_spec_hash_guard(tmp_path, monkeypatch):
    import outcomes_mesh
    spec = {"a": 1, "hashes": {"features": {}}}
    p = tmp_path / "mesh_spec.json"
    p.write_text(json.dumps(spec))
    (tmp_path / "mesh_spec.sha256").write_text(common.sha256_json(spec) + "  mesh_spec.json\n")
    monkeypatch.setattr(outcomes_mesh, "SPEC", p)
    monkeypatch.setattr(outcomes_mesh, "SPEC_SHA", tmp_path / "mesh_spec.sha256")
    assert outcomes_mesh.verify_freeze()["a"] == 1
    p.write_text(json.dumps({"a": 2, "hashes": {"features": {}}}))
    with pytest.raises(RuntimeError):
        outcomes_mesh.verify_freeze()


@pytest.mark.skipif(not (WS / "results" / "cache" / "prepared.pkl").exists(), reason="main prepared cache missing")
def test_window_outcome_equals_vendored_on_main_screen():
    import config as vconfig
    import outcomes as voutcomes
    from outcomes_mesh import compute_Y_window
    G = pickle.loads((WS / "results" / "cache" / "prepared.pkl").read_bytes())
    vconfig.load_sealed_ids()
    df = pd.read_parquet(WS / "results" / "gate" / "gate2" / "screen_events_with_outcomes.parquet",
                         columns=["concept_id", "d", "e", "Y_strict", "Y_lenient", "Y_all"])
    ev = df[["concept_id", "d", "e"]].head(400)
    a = voutcomes.compute_Y(G, ev)
    b = compute_Y_window(G, ev, "e", (1, 5), (-5, 0))
    for k in ("Y_strict", "Y_lenient", "Y_all", "n_w2_noauthor", "pset_size"):
        assert (a[k].sort_index().to_numpy() == b[k].sort_index().to_numpy()).all(), k
