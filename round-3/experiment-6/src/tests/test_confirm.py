"""confirm_heldout refuses without the frozen hash and the iteration-4 switch; the estimator runs on a screen surrogate."""
import hashlib
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))
import confirm_heldout as CH  # noqa: E402

SPEC = b'{"frozen": true}'
H = hashlib.sha256(SPEC).hexdigest()


def test_refuses_on_hash_mismatch():
    with pytest.raises(CH.Refused, match="sha256"):
        CH.check_allowed(SPEC + b" ", H, "iter4")


def test_refuses_without_env():
    with pytest.raises(CH.Refused, match="AII_OPEN_HELDOUT"):
        CH.check_allowed(SPEC, H, None)
    with pytest.raises(CH.Refused):
        CH.check_allowed(SPEC, H, "iter3")


def test_allows_with_hash_and_env():
    CH.check_allowed(SPEC, H + "\n", "iter4")


def test_real_spec_refuses_without_env(monkeypatch):
    p = ROOT / "results" / "heldout" / "heldout_spec.json"
    if not p.exists():
        pytest.skip("spec not frozen yet")
    monkeypatch.delenv("AII_OPEN_HELDOUT", raising=False)
    with pytest.raises(SystemExit) as e:
        CH.main()
    assert e.value.code == 2


def test_estimator_on_screen_surrogate():
    p = ROOT / "results" / "d1" / "panel_ct.parquet"
    if not p.exists():
        pytest.skip("models not run yet")
    d = pd.read_parquet(p)
    spec = dict(inference=dict(seed=1, cluster_bootstrap_reps=30), openness_measures=["closure_res_z"],
                descriptive_outcomes=["Y1r", "log1p_Y3"], estimands=dict(carried_outcomes=["Y1r", "log1p_Y3"]))
    H = d.drop(columns=["Y1r", "log1p_Y3", "Y2", "Y3"])
    O = d[["concept_id", "t", "Y1r", "log1p_Y3", "Y2", "Y3"]]
    res = CH.estimate(spec, H, O)
    assert "p_holm" in res["closure_res_z"]["Y1r"]
    assert abs(res["closure_res_z"]["Y1r"]["transfer"]["delta_r2"]) < 1   # in-sample surrogate, finite
