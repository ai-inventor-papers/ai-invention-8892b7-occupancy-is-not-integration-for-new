"""Unit tests (4)-(8): seal guard, label-free R1a, fold rule, population rule, confirm_heldout refusal."""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import common as K  # noqa: E402

HAVE_POP = (K.WORK / "population.parquet").exists()
HAVE_SPEC = (ROOT / "heldout_spec.json").exists()


# (4) seal guard -------------------------------------------------------------------------------------------------
@pytest.mark.skipif(not HAVE_POP, reason="population not built")
def test_assert_not_sealed_refuses_heldout_and_focal_years():
    import config as C
    from labels3 import guard
    held = guard()
    assert len(held) == 119
    with pytest.raises(RuntimeError):
        C.assert_not_sealed([sorted(held)[0]])
    for t in (2016, 2017, 2018):
        with pytest.raises(RuntimeError):
            C.assert_not_sealed([], [t])
    C.assert_not_sealed(["c_not_a_heldout_id"], [2015])


def test_load_sealed_requires_env_and_hash(tmp_path, monkeypatch):
    from seal import load_sealed
    p = tmp_path / "x.parquet"
    pd.DataFrame(dict(a=[1])).to_parquet(p)
    monkeypatch.delenv("AII_OPEN_HELDOUT", raising=False)
    with pytest.raises(RuntimeError):
        load_sealed(p, "anything")
    monkeypatch.setenv("AII_OPEN_HELDOUT", "1")
    with pytest.raises(RuntimeError):
        load_sealed(p, "wrong-hash")


def test_only_confirm_uses_sealed_loader():
    users = []
    for f in list((ROOT / "src").glob("*.py")) + [ROOT / "method.py", ROOT / "confirm_heldout.py"]:
        if f.name == "seal.py" or not f.exists():
            continue
        if re.search(r"\bload_sealed\b", f.read_text()):
            users.append(f.name)
    assert users == ["confirm_heldout.py"], users


# (5) R1a is label-free ---------------------------------------------------------------------------------------------
def _toy(n=400, seed=0):
    rng = np.random.default_rng(seed)
    df = pd.DataFrame(dict(concept_id=[f"c{i % 40}" for i in range(n)], fold="screen", age=rng.integers(-2, 10, n)))
    for c in K.SPEC3["r1a_covariates"]:
        if c != "age":
            df[c] = rng.normal(size=n)
    df.loc[rng.random(n) < 0.5, "beta_sim_rar"] = np.nan
    df["beta_sim_raw"] = rng.normal(size=n)
    df["closure"] = 0.5 * df.new_relation_rate - 0.3 * df.novelty + rng.normal(size=n)
    return df


def test_r1a_refuses_label_columns_and_ignores_labels():
    from indicators3 import r1a_apply, r1a_fit
    df = _toy()
    fm = np.ones(len(df), bool)
    with pytest.raises(AssertionError):
        r1a_fit(df.assign(E_up=1), fm, K.SPEC3["r1a_covariates"], True)
    a = r1a_fit(df, fm, K.SPEC3["r1a_covariates"], True)
    shuffled = df.sample(frac=1.0, random_state=3).reset_index(drop=True)  # shuffling rows (and any label) changes nothing
    b = r1a_fit(shuffled, fm, K.SPEC3["r1a_covariates"], True)
    assert np.allclose(a["beta"], b["beta"])
    assert "beta_sim_rar_isNA" in a["names"]
    assert np.isfinite(r1a_apply(df, a)).all()


# (6) fold rule ---------------------------------------------------------------------------------------------------
@pytest.mark.skipif(not HAVE_POP, reason="population not built")
def test_fold_rule_reproduces_ds5_counts():
    from population import fold_sha1
    pop = pd.read_parquet(K.WORK / "population.parquet")
    main = pop[pop.arm == "main"]
    folds = main.concept_id.map(fold_sha1)
    assert (folds == "screen").sum() == 247 and (folds == "heldout").sum() == 119
    assert (folds.values == main.fold.values).all()


# (7) population rule ---------------------------------------------------------------------------------------------
@pytest.mark.skipif(not HAVE_POP, reason="population not built")
def test_replacement_rule_keeps_frozen_membership():
    tp = json.loads(K.TESTPOP.read_text())
    frozen = {c["concept_id"]: c for c in tp["concepts"]}
    pop = pd.read_parquet(K.WORK / "population.parquet").set_index("concept_id")
    for cid, rec in frozen.items():
        if rec["sense_status"] != "missing":
            assert bool(pop.loc[cid, "MAIN"]) == rec["in_MAIN"]
            assert bool(pop.loc[cid, "STRICT"]) == rec["in_STRICT"]
    kept = [c for c, r in frozen.items() if r["sense_status"] != "missing"]
    assert int(pop.loc[kept, "MAIN"].sum()) == 156 and int(pop.loc[kept, "STRICT"].sum()) == 147


# (8) confirm_heldout refuses -------------------------------------------------------------------------------------
@pytest.mark.skipif(not HAVE_SPEC, reason="heldout_spec.json not frozen yet")
def test_confirm_refuses_changed_spec(tmp_path):
    spec = ROOT / "heldout_spec.json"
    h = (ROOT / "heldout_spec.sha256").read_text().strip()
    bad = ROOT / "tests" / "_tmp_spec.json"
    try:
        b = bytearray(spec.read_bytes())
        b[-2] = ord(" ") if b[-2] != ord(" ") else ord("\n")
        bad.write_bytes(bytes(b))
        r = subprocess.run([sys.executable, str(ROOT / "confirm_heldout.py"), "--spec", str(bad.relative_to(ROOT)),
                            "--expected-sha256", h], cwd=ROOT, capture_output=True, env={**os.environ, "AII_OPEN_HELDOUT": ""})
        assert r.returncode == 2, r.stderr.decode()[-500:]
    finally:
        bad.unlink(missing_ok=True)


@pytest.mark.skipif(not HAVE_SPEC, reason="heldout_spec.json not frozen yet")
def test_confirm_refuses_changed_code(monkeypatch):
    sys.path.insert(0, str(ROOT))
    import confirm_heldout as CH
    spec = json.loads((ROOT / "heldout_spec.json").read_text())
    first = sorted(spec["code_sha256"])[0]
    spec["code_sha256"][first] = "0" * 64  # as if that code file had changed on disk
    tmp = ROOT / "tests" / "_tmp_spec_code.json"
    try:
        tmp.write_text(json.dumps(spec))
        h = K.sha256_file(tmp)
        monkeypatch.setattr(CH, "last_logged_hash", lambda name="heldout_spec.json": h)
        with pytest.raises(SystemExit) as e:
            CH.check_integrity(tmp, h)
        assert e.value.code == 2
    finally:
        tmp.unlink(missing_ok=True)
