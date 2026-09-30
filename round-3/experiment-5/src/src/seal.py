"""Held-out seal guard.

* vendored config.SEALED_IDS holds the 119 held-out main-arm ids during every screen analysis (labels3.guard), so the
  vendored build_labels / assert_not_sealed refuse them and the sealed focal years 2016-18.
* load_sealed() is the ONLY loader of sealed feature tables. It raises unless AII_OPEN_HELDOUT == '1' AND the caller
  passes the spec hash that equals heldout_spec.sha256 (written by src/freeze.py). Only confirm_heldout.py calls it.
"""
from __future__ import annotations

import os
from pathlib import Path

import pandas as pd

import common as K


def expected_spec_hash() -> str | None:
    p = K.ROOT / "heldout_spec.sha256"
    return p.read_text().strip() if p.exists() else None


def load_sealed(path: Path, spec_hash: str) -> pd.DataFrame:
    if os.environ.get("AII_OPEN_HELDOUT") != "1":
        raise RuntimeError("sealed table requested without AII_OPEN_HELDOUT=1")
    exp = expected_spec_hash()
    if exp is None or spec_hash != exp:
        raise RuntimeError("sealed table requested with a spec hash that does not match heldout_spec.sha256")
    path = Path(path)
    sha_file = path.with_suffix(".sha256")
    if sha_file.exists() and K.sha256_file(path) != sha_file.read_text().strip():
        raise RuntimeError(f"sealed file {path.name} changed since it was written")
    return pd.read_parquet(path)
