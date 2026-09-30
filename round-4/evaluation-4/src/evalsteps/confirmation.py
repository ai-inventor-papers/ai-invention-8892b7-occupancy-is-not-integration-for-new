"""STEP 1c: E1-E5 exactly as evaluated by the frozen confirm_heldout.evaluate_rules, with MDE context."""
from __future__ import annotations

import json

from base import HO, RES, write_json


def run() -> dict:
    conf = json.loads((HO / "results/confirmation.json").read_text())
    pw = json.loads((RES / "power_mde.json").read_text())
    marker = json.loads((HO / "OPENED").read_text())
    e1 = conf["E1"]
    hw = pw["wilson_halfwidth"]
    ctx = dict(
        E1=dict(success=e1["success"], note=f"held-out Wilson half-width at n=100 is {list(hw.values())[0]['100']:.3f}; with the screen half-width (~0.065) the E1 overlap rule fails only for share shifts of about 0.15 or more"),
        E2=dict(success=conf["E2"]["success"], n_same_order=conf["E2"]["n_same_order"], n_sig=conf["E2"]["n_sig"]),
        E3=dict(success=conf["E3"]["success"], n_both=conf["E3"]["n_both"], expected_n_both=pw["leadlag"]["expected_n_both_heldout"],
                note="E3 success = CI overlap with screen AND same side of the 0.619 null; with n_both ~ 8-10 the CI is wide and "
                     "the rule is weak (a 10/10 share gives a degenerate bootstrap CI [1,1])"),
        E4=dict(same_sign_all=conf["E4"]["same_sign_all"], note="robust role shares match closely; the lagged-role entry-hazard ORs flip sign "
                "(screen ORs < 1 with CIs spanning 1; held-out ORs > 1) -> the null 'roles do not predict entry' is not stable in direction"),
        E5=dict(overlap_all=all(v["overlap"] for v in conf["E5"].values())))
    out = dict(opened_marker=marker, confirmation=conf, summary=ctx,
               n_heldout_main=json.loads((HO / "results/typology.json").read_text())["n"],
               expected_sha="695166b465d36f3311d13bdc7d315204a849ab96dc28c0c36fa002f4ad217d2a")
    write_json(RES / "confirmation_report.json", out)
    return out
