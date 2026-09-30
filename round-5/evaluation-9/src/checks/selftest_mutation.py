#!/usr/bin/env python3
"""Mutation self-test: the checks must FAIL when a figure is built from a perturbed source.

(1) Copy heldout_post.json into the workspace with flags.secondary.irr_sd_A x 1.01, rebuild F2 from that copy
    (registry override), and re-check the result against the TRUE source: the check must report failures.
(2) Rebuild F2 from the true source into the same temp dir: the check must pass (control).
(3) Plant a typed plotted number in a probe plot module: the literal lint must fail; then remove the probe.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

WS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WS))
sys.path.insert(0, str(WS / "checks"))
from independent import run_figure  # noqa: E402
from src.plots import f2_d2_forest  # noqa: E402
from src.registry import Registry  # noqa: E402

FACTOR = 1.01


def main() -> int:
    tmp = WS / "results" / "mutation_tmp"
    shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir(parents=True)
    reg0 = Registry()
    src = reg0.path("ho_post")
    doc = json.loads(src.read_text())
    doc["flags"]["secondary"]["irr_sd_A"] *= FACTOR
    pert = tmp / "heldout_post_perturbed.json"
    pert.write_text(json.dumps(doc))
    f2_d2_forest.build(Registry(overrides={"ho_post": str(pert)}), tmp / "mutated")
    mutated = run_figure("F2", tmp / "mutated" / "F2" / "plotted_values.json")
    f2_d2_forest.build(Registry(), tmp / "control")
    control = run_figure("F2", tmp / "control" / "F2" / "plotted_values.json")
    probe = WS / "src" / "plots" / "_lint_probe.py"
    true_val = Registry().get("f2.ho_co.A.est")
    probe.write_text(f'CAPTION = "held-out IRR {true_val:.3f}"\n')
    lint = subprocess.run([sys.executable, str(WS / "checks" / "lint_no_literals.py")], capture_output=True)
    probe.unlink()
    res = {"mutation": {"perturbed_key": "ho_post:/flags/secondary/irr_sd_A", "factor": FACTOR,
                        "n_failed": mutated["n_failed"], "detected": mutated["n_failed"] > 0,
                        "failures": mutated["failures"][:5]},
           "control": {"n_failed": control["n_failed"], "passes": control["n_failed"] == 0},
           "lint_probe": {"planted": "string literal with the held-out IRR at 3 dp", "lint_exit": lint.returncode,
                          "detected": lint.returncode != 0}}
    res["selftest_pass"] = res["mutation"]["detected"] and res["control"]["passes"] and res["lint_probe"]["detected"]
    shutil.rmtree(tmp, ignore_errors=True)
    subprocess.run([sys.executable, str(WS / "checks" / "lint_no_literals.py")], capture_output=True)
    (WS / "results" / "check_selftest.json").write_text(json.dumps(res, indent=1, default=str))
    print(json.dumps({k: (v if k != "mutation" else {kk: vv for kk, vv in v.items() if kk != "failures"})
                      for k, v in res.items()}))
    return 0 if res["selftest_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
