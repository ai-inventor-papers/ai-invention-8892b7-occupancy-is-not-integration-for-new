"""Fast PPML (src/ppml.py) equals pyfixest.fepois (scipy demeaner) on a simulated Gate-B-like panel."""
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import ppml  # noqa: E402


def test_ppml_matches_pyfixest():
    import pyfixest as pf
    rng = np.random.default_rng(3)
    n_ep, n_h, n_d = 40, 4, 12
    rows = []
    for ep in range(n_ep):
        onset = rng.integers(1, 6)
        hosts = rng.choice(n_d, n_h, replace=False)
        for h in hosts:
            v, mom, sink = rng.uniform(10, 60), rng.normal(), int(rng.uniform() < .5)
            for tau in range(1, 6):
                rows.append({"ep": f"e{ep}", "cid": f"c{ep // 2}", "d": int(h), "tau": tau, "cool": int(tau >= onset),
                             "sink": sink, "mom": mom, "lv": np.log(v / 6)})
    p = pd.DataFrame(rows)
    mu = np.exp(p.lv + 0.2 * p.sink - 0.2 * p.sink * p.cool + rng.normal(0, .2, len(p)))
    p["y"] = rng.poisson(mu)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        m = pf.fepois("y ~ sink + sink:cool + mom + mom:cool | ep^tau + d^tau", data=p, offset="lv",
                      vcov={"CRV1": "cid"}, demeaner_backend="scipy")
    X = np.column_stack([p.sink, p.sink * p.cool, p.mom, p.mom * p.cool]).astype(float)
    f1 = pd.factorize(p.ep + "_" + p.tau.astype(str))[0]
    f2 = pd.factorize(p.d.astype(str) + "_" + p.tau.astype(str))[0]
    r = ppml.fit(p.y.to_numpy(), X, [f1, f2], p.lv.to_numpy(), p.cid.to_numpy())
    names = ["sink", "sink:cool", "mom", "mom:cool"]
    assert np.allclose(r["coef"], m.coef()[names].to_numpy(), atol=5e-3)
    assert np.allclose(r["se"], m.se()[names].to_numpy(), rtol=0.05)
