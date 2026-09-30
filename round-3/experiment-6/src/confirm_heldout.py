#!/usr/bin/env python3
"""Iteration-4 held-out confirmation of RQ2-D1 under the frozen spec (results/heldout/heldout_spec.json).

Refuses to run unless (a) sha256(heldout_spec.json) equals results/heldout/heldout_spec.sha256 and
(b) the environment variable AII_OPEN_HELDOUT == 'iter4'. When allowed, it lifts the outcome guard ONLY for the
sealed held-out concept ids (sealed focal years stay sealed), computes the W2 outcomes with the same step-7
functions, runs the frozen estimator and writes results/heldout/confirmation.json.
Usage: AII_OPEN_HELDOUT=iter4 .venv/bin/python confirm_heldout.py
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import sys
from pathlib import Path

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_v, "1")
sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from loguru import logger  # noqa: E402

HDIR = Path(__file__).resolve().parent / "results" / "heldout"


class Refused(RuntimeError):
    pass


def check_allowed(spec_bytes: bytes, stored_hash: str, env_value: str | None) -> None:
    """Pure gate (unit-tested): raises Refused on a hash mismatch or without AII_OPEN_HELDOUT=iter4."""
    if hashlib.sha256(spec_bytes).hexdigest() != stored_hash.strip():
        raise Refused("heldout_spec.json does not match its frozen sha256; refusing")
    if env_value != "iter4":
        raise Refused("AII_OPEN_HELDOUT != 'iter4'; refusing to open the held-out fold")


def heldout_outcomes(H):
    import numpy as np
    import pandas as pd

    import common as K
    import outcomes as OC
    from indicators import load_rs
    cp = pd.read_parquet(K.WORK / "cp.parquet", columns=["concept_id", "work_id", "year", "subfield"])
    groups = dict(tuple(cp[cp.concept_id.isin(set(H.concept_id))].groupby("concept_id")))
    D, sidx = load_rs()
    AI = OC.AuthorIndex()
    rows = []
    for c, t in zip(H.concept_id, H.t):
        r = dict(concept_id=c, t=int(t))
        r.update(OC.breadth_outcomes(c, t, groups[c], D, sidx, 20))
        r.update(OC.newcomer_outcome(c, t, groups[c], AI))
        rows.append(r)
    O = pd.DataFrame(rows)
    O["log1p_Y3"] = np.log1p(O.Y3)
    return O


def estimate(spec: dict, H, O) -> dict:
    import numpy as np
    import pandas as pd

    import lib_metrics as lm
    import stats_core as S
    from models import model_rows
    d = H.merge(O, on=["concept_id", "t"])
    d = d[d.in_MAIN]
    scr = pd.read_parquet(Path(__file__).resolve().parent / "results" / "d1" / "panel_ct.parquet")
    scr = scr[scr.in_MAIN]
    seed = spec["inference"]["seed"]
    B = spec["inference"]["cluster_bootstrap_reps"]
    out = {}
    for ov in spec["openness_measures"]:
        per = {}
        for y in spec["descriptive_outcomes"]:
            ms = model_rows(scr, y, [ov], S.NUM_BASE)
            Xs, names, lv = S.design(ms, [ov])
            mh = model_rows(d, y, [ov], S.NUM_BASE)
            if mh.concept_id.nunique() < 5:
                per[y] = dict(n_rows=len(mh), note="too few held-out concepts")
                continue
            Xh_all, names_h, _ = S.design(mh, [ov], levels=lv)
            keep = [names_h.index(n) for n in names]
            Xh = Xh_all[:, keep]
            yh = mh[y].astype(float).values
            gh = mh.concept_id.values
            b = S.ols(Xh, yh)
            dr = S.cluster_boot(Xh, yh, gh, B, seed, 1)
            summ = S.boot_summary(b[1], dr)
            ys = ms[y].astype(float).values
            pf = Xh @ S.ols(Xs, ys)
            pb = np.delete(Xh, 1, axis=1) @ S.ols(np.delete(Xs, 1, axis=1), ys)
            tr = S.delta_r2_boot(yh, pb, pf, gh, B, seed + 1)
            per[y] = dict(n_rows=len(mh), n_concepts=int(mh.concept_id.nunique()), **summ, transfer=tr)
        carried = spec["estimands"]["carried_outcomes"]
        if carried:
            ps = [per[y]["p_boot"] for y in carried]
            for y, ph in zip(carried, lm.holm(ps)):
                per[y]["p_holm"] = ph
                per[y]["confirmed"] = bool(per[y]["coef"] < 0 and per[y]["ci_hi"] < 0 and ph < 0.05)
                per[y]["transfer_confirmed"] = bool(per[y]["transfer"]["ci_lo"] > 0)
        out[ov] = per
    return out


def main() -> None:
    spec_path = HDIR / "heldout_spec.json"
    stored = (HDIR / "heldout_spec.sha256").read_text()
    try:
        check_allowed(spec_path.read_bytes(), stored, os.environ.get("AII_OPEN_HELDOUT"))
    except Refused as e:
        logger.error(str(e))
        sys.exit(2)
    import pandas as pd

    import common as K
    K.setup_logging("confirm_heldout")
    spec = json.loads(spec_path.read_text())
    for rel, h in spec["population_files"].items():
        p = K.WS / rel.split(" (")[0]
        if K.sha256_file(p) != h:
            logger.error(f"frozen input changed: {rel}")
            sys.exit(3)
    sealed = K.load_sealed_ids()
    K.C.SEALED_IDS.difference_update(sealed)   # lift ONLY the concept guard; sealed focal years stay sealed
    H = pd.read_parquet(K.SEALED / "features_ct_heldout.parquet")
    O = heldout_outcomes(H)
    res = estimate(spec, H, O)
    carried = spec["estimands"]["carried_outcomes"]
    result = dict(spec_sha256=stored.strip(), carried_outcomes=carried, estimates=res,
                  status=("confirmation test" if carried else "descriptive only (D1 not supported on screen)"))
    (HDIR / "confirmation.json").write_text(json.dumps(result, indent=1, default=lambda o: None if isinstance(o, float) and math.isnan(o) else str(o)))
    O.to_parquet(HDIR / "heldout_outcomes.parquet", index=False)
    logger.info(f"confirmation written: {result['status']}")


if __name__ == "__main__":
    main()
