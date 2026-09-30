#!/usr/bin/env python3
"""Permutation p for the held-out co-primary A_cont via pyfixest: shuffle A_cont within concept (200 draws),
compare |z| with the observed |z|. Writes audit/audit_perm.json."""
import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import pyfixest as pf

from audit_headline import CTRL2, prune

warnings.filterwarnings("ignore")
WS = Path(__file__).resolve().parents[1]
ho = pd.read_parquet(WS / "results" / "g_features_heldout_coprimary.parquet")
s = ho[(ho.arm == "main") & (ho.fold == "heldout") & ho.kw5 & ho.MAIN].dropna(subset=["A_cont", "CT"] + CTRL2)
s = s.assign(off=np.log(s.n_entry_papers.astype(float)))
s = prune(s, "Y_strict", ["concept_id", "e", "d"])
for f in ("concept_id", "e", "d"):
    s[f] = s[f].astype(str)
fml = f"Y_strict ~ A_cont + CT + {' + '.join(CTRL2)} | concept_id + e + d"


def z(d):
    m = pf.fepois(fml, data=d, offset="off", vcov={"CRV1": "concept_id"}, fixef_tol=1e-10, iwls_tol=1e-10)
    return float(m.coef()["A_cont"] / m.se()["A_cont"])


zo = z(s)
rng = np.random.default_rng(11)
zs = []
for i in range(200):
    d = s.copy()
    d["A_cont"] = d.groupby("concept_id").A_cont.transform(lambda v: rng.permutation(v.to_numpy()))
    try:
        zs.append(z(d))
    except Exception as ex:  # noqa: BLE001
        print("fail", repr(ex))
zs = np.array(zs)
out = {"z_obs": zo, "draws": int(len(zs)), "z_sd": float(zs.std()), "z_mean": float(zs.mean()),
       "share_crv1_p_lt_0.05": float((np.abs(zs) > 1.993).mean()),
       "perm_p_two_sided": float((1 + (np.abs(zs) >= abs(zo)).sum()) / (1 + len(zs)))}
(WS / "audit" / "audit_perm.json").write_text(json.dumps(out, indent=1))
print(out)
