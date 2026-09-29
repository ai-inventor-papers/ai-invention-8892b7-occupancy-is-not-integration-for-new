"""T0 unit tests (run: .venv/bin/python -m pytest -q tests)."""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import common  # noqa: E402
from common import C, WORK, X3  # noqa: E402


# (a) sealing guard ---------------------------------------------------------------------------------------------------
def test_assert_not_sealed_blocks_heldout_ids_and_years():
    ids = common.load_sealed()
    assert len(ids) == 119
    with pytest.raises(RuntimeError):
        C.assert_not_sealed([sorted(ids)[0]])
    for t in (2016, 2017, 2018):
        with pytest.raises(RuntimeError):
            C.assert_not_sealed([], [t])
    C.assert_not_sealed(["c_not_sealed"], [2015])


def test_entry_points_call_the_guard():
    for mod in ("typology", "leadlag", "roles", "validation", "patterns", "labels", "attach", "indicators", "cases", "method_out"):
        src = (ROOT / "src" / f"{mod}.py").read_text()
        assert "assert_not_sealed" in src, mod


def test_mutation_heldout_id_in_population_is_refused():
    """Mutation: a held-out id slipped into an analysed population must raise before any statistic is computed."""
    common.load_sealed()
    pool = pd.read_parquet(WORK / "pool_active.parquet")
    bad = sorted(json.loads((WORK / "sealed_ids.json").read_text()))[0]
    ids = pool.concept_id.tolist() + [bad]
    with pytest.raises(RuntimeError):
        C.assert_not_sealed(ids)
    assert not set(pool.concept_id) & C.SEALED_IDS


# (b) CoGraph reconstruction --------------------------------------------------------------------------------------------
@pytest.mark.parametrize("y", [2008, 2013, 2018])
def test_cograph_reconstruction(y):
    import attach
    chk = attach.check_cograph(y)
    assert all(chk[k] for k in ("n_nodes", "n_edges", "n_kept_edges", "n_kept_nodes", "n_comm"))
    assert chk["strength_rowsum_maxrel"] < 1e-6


# (c) vendored files byte-identical ---------------------------------------------------------------------------------------
def test_vendor_byte_identical():
    for p in sorted((ROOT / "vendor").glob("*.py")):
        a = hashlib.sha256(p.read_bytes()).hexdigest()
        b = hashlib.sha256((X3 / p.name).read_bytes()).hexdigest()
        assert a == b, p.name


# (d) alluvial reproduction -----------------------------------------------------------------------------------------------
def test_alluvial_reproduces_iteration2():
    import leiden_seeds
    rep = leiden_seeds.verify_seed0_alluvial()
    assert rep["persistent_ids_identical"] and rep["events_identical_counts"]


# (e) role rules on a toy sequence --------------------------------------------------------------------------------------
def test_role_rules_toy():
    import roles
    d = pd.DataFrame(dict(
        concept_id=["x"] * 5, year=[2010, 2011, 2012, 2013, 2014], seed=0,
        dom=[1, 1, 2, 2, 3], dom_prev=[np.nan, 1, 1, 2, 2], P=[0.1, 0.1, 0.4, 0.7, 0.2],
        dom_existed_prev=[False, True, True, True, False], n_comm_25pct=[1, 1, 1, 1, 1],
        wmz=[0, 0, 0, 0, 2.0], size=[10, 10, 10, 12, 20], size_prev=[np.nan, 10, 10, 10, np.nan],
        birth_year=[2000, 2000, 2000, 2000, 2014], first_attach=[2013] * 5, founder_rank=[50, 50, 50, 50, 2]))
    d.loc[3, "wmz"] = 1.5  # dom 2 grew 10 -> 12 and wmz >= 1 -> CORE_GROWING (outranks BRIDGE)
    f = roles.assign_roles(d)
    assert f.primary.tolist() == ["OTHER", "STAYER", "MIGRANT", "CORE_GROWING", "FOUNDER"]
    assert f.BRIDGE.tolist() == [False, False, False, True, False]


# (f) onset detection -----------------------------------------------------------------------------------------------------
def _g(pct, H):
    ys = list(range(2005, 2005 + len(pct)))
    return pd.DataFrame(dict(year=ys, pct_alt=pct, pct=pct, H_rar=H))


def test_onsets_synthetic():
    import leadlag
    g = _g([10, 11, 12, 25, 40, 41, 42, 43], [0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.5, 0.6])
    r = leadlag.onsets_for(g, fa=2005, new_act={2011}, gain=10, rise=0.2)
    assert r["exp_onset"] == 2008 and not r["exp_from_start"]
    assert r["diff_onset"] == 2011
    assert leadlag.categorise(r) == "expansion_first"
    g2 = _g([10, 30, 50, 51, 52, 53], [0.1] * 6)  # expansion at the first evaluable year -> left-censored
    r2 = leadlag.onsets_for(g2, fa=2005, new_act=set(), gain=10, rise=0.2)
    assert r2["exp_onset"] == 2006 and r2["exp_from_start"] and leadlag.categorise(r2) == "neither"
    r3 = leadlag.onsets_for(_g([10] * 6, [0.1] * 6), fa=2005, new_act=set(), gain=10, rise=0.2)
    assert r3["exp_onset"] is None and r3["diff_onset"] is None


# (g) DTW and stability ---------------------------------------------------------------------------------------------------
def test_dtw_and_stability():
    import typology
    rng = np.random.default_rng(0)
    a, b = rng.normal(size=(12, 3)), rng.normal(size=(9, 3))
    assert typology.dtw_norm(a, a) == pytest.approx(0.0, abs=1e-12)
    assert typology.dtw_norm(a, b) == pytest.approx(typology.dtw_norm(b, a))
    from analysis_patterns import _cluster, _stability
    X = np.concatenate([rng.normal(loc=m, scale=0.2, size=(20, 2)) for m in (0, 5, 10)])
    D = np.sqrt(((X[:, None] - X[None]) ** 2).sum(-1))
    lb = _cluster(D, 3)
    assert min(_stability(D, lb, 3, 50)) > 0.95
    Xn = rng.uniform(size=(60, 2))
    Dn = np.sqrt(((Xn[:, None] - Xn[None]) ** 2).sum(-1))
    assert min(_stability(Dn, _cluster(Dn, 5), 5, 50)) < 0.6


# (h) held-out confirmation refuses a modified spec -----------------------------------------------------------------------
def test_confirm_refuses_modified_spec(tmp_path):
    spec = ROOT / "sealed" / "heldout_spec.json"
    if not spec.exists():
        pytest.skip("spec not frozen yet")
    h = (ROOT / "sealed" / "heldout_spec.sha256").read_text().strip()
    ok = subprocess.run([sys.executable, str(ROOT / "confirm_heldout.py"), "--dry-run", "--expected-sha", h], capture_output=True)
    assert ok.returncode == 0, ok.stderr
    txt = spec.read_text()
    i = txt.index('"title"') + 12
    bad = tmp_path / "spec.json"
    bad.write_text(txt[:i] + ("X" if txt[i] != "X" else "Y") + txt[i + 1:])
    r = subprocess.run([sys.executable, str(ROOT / "confirm_heldout.py"), "--dry-run", "--expected-sha", h, "--spec", str(bad)],
                       capture_output=True)
    assert r.returncode == 2
    r2 = subprocess.run([sys.executable, str(ROOT / "confirm_heldout.py"), "--dry-run", "--expected-sha", "0" * 64], capture_output=True)
    assert r2.returncode == 2
    assert not (ROOT / "heldout_run" / "OPENED").exists()
