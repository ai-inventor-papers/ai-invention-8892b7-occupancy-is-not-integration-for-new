"""Unit tests for the D2 host-entry pipeline: sealing (with mutation test), block mapping, anchoring/partition on a toy
event, the newcomer rule on a toy author graph, and 3-FE PPML recovery."""
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import config  # noqa: E402
import features  # noqa: E402
import outcomes  # noqa: E402
import ppml  # noqa: E402


# ---------------------------------------------------------------- toy corpus
def toy_G():
    """6 works, authors 0..5. Concept c: works 0,1 (origin 100, year 2008-2009), 2 (d=200, e=2010),
    3,4,5 (d=200, 2012). Work 6 is a non-concept corpus work linking author 1 and author 4 in 2009."""
    years = np.array([2008, 2009, 2010, 2012, 2012, 2012, 2009], np.int32)
    sub = np.array([100, 100, 200, 200, 200, 200, 300], np.int32)
    authors = [[0], [1], [0, 2], [3], [4], [0, 5], [1, 4]]
    ptr = np.zeros(len(authors) + 1, np.int64)
    ptr[1:] = np.cumsum([len(a) for a in authors])
    idx = np.concatenate([np.array(a, np.int64) for a in authors])
    G = {"W": {"year": years, "sub": sub}, "AU": (ptr, idx), "n_authors": 6,
         "links": {"c_toy": (np.arange(6, dtype=np.int64), years[:6])}}
    return G


def test_sealing_raises_for_heldout():
    config.SEALED_IDS.clear()
    config.SEALED_IDS.add("c_toy")
    G = toy_G()
    ev = pd.DataFrame({"concept_id": ["c_toy"], "d": [200], "e": [2010]})
    with pytest.raises(RuntimeError):
        outcomes.compute_Y(G, ev)
    config.SEALED_IDS.clear()


def test_sealing_mutation(monkeypatch):
    """If the guard is disabled, the sealing test above must FAIL (proves the test actually tests the guard)."""
    config.SEALED_IDS.clear()
    config.SEALED_IDS.add("c_toy")
    monkeypatch.setattr(outcomes, "assert_not_sealed", lambda ids: None)
    G = toy_G()
    ev = pd.DataFrame({"concept_id": ["c_toy"], "d": [200], "e": [2010]})
    raised = False
    try:
        outcomes.compute_Y(G, ev)
    except RuntimeError:
        raised = True
    assert not raised, "with the guard mutated away, compute_Y must run (so the real test detects its removal)"
    config.SEALED_IDS.clear()


def test_no_w2_access_outside_guarded_modules():
    """Only outcomes.py (guarded) and confirm_heldout.py may read W2 windows (e+1 .. e+5) of events."""
    pat = re.compile(r"e \+ 1|e\+1|e \+ 5|e\+5")
    allowed = {"outcomes.py", "confirm_heldout.py", "test_d2.py", "audit_rederive.py",
               "config.py", "robustness.py"}  # robustness.py: guarded [e, e+1] partner-window variant  # config.py only holds the SPEC text describing the window
    for p in list((ROOT / "src").glob("*.py")) + [ROOT / "method.py"]:
        if p.name in allowed or not p.exists():
            continue
        assert not pat.search(p.read_text()), f"{p.name} touches the W2 window"


def test_block_mapping():
    assert features.block_of(2009) == "2000-2004"
    assert features.block_of(2010) == "2005-2009"
    assert features.block_of(2014) == "2005-2009"
    assert features.block_of(2015) == "2010-2014"
    assert features.block_of(2019) == "2010-2014"
    with pytest.raises(ValueError):
        features.block_of(2004)


def test_anchoring_partition_toy():
    # profiles for block 2005-2009, host d = 200: node 1 share .8, node 2 share .1, node 3 share .6; node 9 unprofiled
    prof = {(1, "2005-2009"): (10, {200: 8}, False), (2, "2005-2009"): (10, {200: 1}, False),
            (3, "2005-2009"): (10, {200: 6, 100: 4}, False)}
    nat = features.Nativeness(prof)
    nodes = np.array([1, 2, 3, 9, 1, 2])  # 3 papers x 2 tags
    comp = {2, 3}
    f = features.anchoring(nodes, comp, nat, "2005-2009", 200)
    # profiled tags: 1,2,3,1,2 -> native (>=.5): 1,3,1 -> A = 3/5
    assert f["A"] == pytest.approx(3 / 5)
    assert f["cov"] == pytest.approx(5 / 6)
    assert f["A_lo"] <= f["A"] <= f["A_hi"]
    s = f["graft"] + f["native_companion"] + f["package"] + f["third_party"]
    assert s == pytest.approx(1.0)
    assert f["graft"] == pytest.approx(2 / 5)          # node 1 twice
    assert f["native_companion"] == pytest.approx(1 / 5)  # node 3
    assert f["package"] == pytest.approx(2 / 5)         # node 2 twice
    assert f["CT"] == pytest.approx(3 / 6)
    f2 = features.anchoring(np.array([1, 2]), set(), nat, "2005-2009", 200)
    assert f2["A"] == f2["A_lo"] == f2["A_hi"] == pytest.approx(0.5)
    assert f["A_cont"] == pytest.approx((.8 + .1 + .6 + .8 + .1) / 5)


def test_newcomer_rule_toy():
    """e = 2010, d = 200. Pset = authors of c-papers 2005-2010 {0,1,2} + co-authors on corpus works in 2005-2010:
    work 6 (2009) links author 1 with author 4 -> Pset = {0,1,2,4}. W2 papers (2012): [3] newcomer -> strict;
    [4] W1 co-author -> neither; [0,5] mixed -> lenient only."""
    config.SEALED_IDS.clear()
    G = toy_G()
    ev = pd.DataFrame({"concept_id": ["c_toy"], "d": [200], "e": [2010]})
    r = outcomes.compute_Y(G, ev)
    assert int(r.Y_strict.iloc[0]) == 1
    assert int(r.Y_lenient.iloc[0]) == 2
    assert int(r.Y_all.iloc[0]) == 3
    rd = outcomes.compute_Y(G, ev, direct_only=True)
    assert int(rd.Y_strict.iloc[0]) == 2  # without the co-author expansion author 4 counts as a newcomer


def test_ppml_three_fe_recovers_beta():
    rng = np.random.default_rng(7)
    n_c, per = 150, 12
    rows = []
    for c in range(n_c):
        ce = rng.normal(0, .5)
        for k in range(per):
            e = rng.integers(0, 4)
            d = rng.integers(0, 20)
            rows.append((c, e, d, ce))
    df = pd.DataFrame(rows, columns=["c", "e", "d", "ce"])
    df["A"] = rng.normal(0, 1, len(df))
    df["x"] = rng.normal(0, 1, len(df))
    df["off"] = np.log(rng.integers(1, 4, len(df)))
    mu = np.exp(0.3 * df.A - 0.2 * df.x + df.ce + 0.05 * df.d + df.off)
    df["y"] = rng.poisson(mu)
    fcxe = pd.factorize(df.c.astype(str) + "_" + df.e.astype(str))[0]
    fdxe = pd.factorize(df.d.astype(str) + "_" + df.e.astype(str))[0]
    r = ppml.fit(df.y.to_numpy(), df[["A", "x"]].to_numpy(float), [fcxe, fdxe], df.off.to_numpy(), df.c.to_numpy())
    assert abs(r["coef"][0] - 0.3) < 2 * r["se"][0]
    assert abs(r["coef"][1] + 0.2) < 2 * r["se"][1]
