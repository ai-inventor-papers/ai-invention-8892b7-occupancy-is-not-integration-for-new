#!/usr/bin/env python3
"""One-time held-out confirmation for the RQ2 experiment.

  --dry-run                      verify the spec hash (against results/heldout_spec_hashlog.jsonl AND --expected-sha) and all
                                 code / frozen-artefact hashes; touch nothing.
  --open-heldout                 (iteration 4 only) after the same checks, write the irreversible marker heldout_run/OPENED
                                 (refuses if it exists), run every stage with AII_HELDOUT_OPEN=1 into heldout_run/, and
                                 evaluate the frozen decision rules -> heldout_run/results/confirmation.json.
Exit code 2 = refused.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SPEC = ROOT / "sealed" / "heldout_spec.json"
HASHLOG = ROOT / "results" / "heldout_spec_hashlog.jsonl"
STAGES = ["prep", "attach", "indicators", "labels", "leiden_seeds", "typology", "roles", "leadlag", "patterns", "validation"]


def canon_sha(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()


def refuse(msg: str) -> None:
    print(f"REFUSED: {msg}", file=sys.stderr)
    sys.exit(2)


def check(spec_path: Path, expected: str | None, root: Path = ROOT) -> dict:
    try:
        spec = json.loads(spec_path.read_text())
    except (OSError, json.JSONDecodeError) as e:
        refuse(f"spec unreadable: {e!r}")
    h = canon_sha(spec)
    logged = [json.loads(line)["sha256"] for line in HASHLOG.read_text().splitlines() if line.strip()] if HASHLOG.exists() else []
    if not logged or h != logged[-1]:
        refuse(f"spec sha256 {h} does not match the last hashlog entry {logged[-1] if logged else None}")
    if expected is None or h != expected:
        refuse(f"spec sha256 {h} != --expected-sha {expected}")
    for rel, want in {**spec["code_sha256"], **spec["frozen_artifacts_sha256"]}.items():
        p = root / rel
        got = hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None
        if got != want:
            refuse(f"hash mismatch for {rel}: {got} != {want}")
    return spec


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--expected-sha", default=None)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--open-heldout", action="store_true")
    ap.add_argument("--spec", default=str(SPEC))
    ap.add_argument("--simulate", action="store_true",
                    help="rehearsal: 40 screen MAIN concepts play the held-out role (real held-out stays sealed); output heldout_sim/")
    a = ap.parse_args()
    if a.simulate:
        env = dict(os.environ, AII_HELDOUT_SIMULATE="1")
        for st in STAGES:
            r = subprocess.run([sys.executable, str(ROOT / "src" / f"{st}.py")], cwd=ROOT / "src", env=env)
            if r.returncode != 0:
                refuse(f"simulated stage {st} failed with exit code {r.returncode}")
        spec = json.loads(Path(a.spec).read_text()) if Path(a.spec).exists() else None
        if spec:
            res = evaluate_rules(spec, ROOT / "heldout_sim" / "results")
            (ROOT / "heldout_sim" / "results" / "confirmation_rehearsal.json").write_text(json.dumps(res, indent=1, default=str))
            print(json.dumps(res, indent=1, default=str)[:4000])
        return
    spec = check(Path(a.spec), a.expected_sha)
    if a.dry_run or not a.open_heldout:
        print(f"OK: spec {canon_sha(spec)} verified; {len(spec['code_sha256'])} code files and "
              f"{len(spec['frozen_artifacts_sha256'])} frozen artefacts match. Held-out NOT opened.")
        return
    marker = ROOT / "heldout_run" / "OPENED"
    marker.parent.mkdir(exist_ok=True)
    try:
        fd = os.open(marker, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        refuse("held-out set was already opened (heldout_run/OPENED exists); a second opening is not allowed")
    os.write(fd, json.dumps(dict(spec_sha256=canon_sha(spec))).encode())
    os.close(fd)
    env = dict(os.environ, AII_HELDOUT_OPEN="1")
    for st in STAGES:
        r = subprocess.run([sys.executable, str(ROOT / "src" / f"{st}.py")], cwd=ROOT / "src", env=env)
        if r.returncode != 0:
            refuse(f"stage {st} failed with exit code {r.returncode} (the opening is recorded; fix and rerun stages by hand)")
    res = evaluate_rules(spec, ROOT / "heldout_run" / "results")
    (ROOT / "heldout_run" / "results" / "confirmation.json").write_text(json.dumps(res, indent=1, default=str))
    print(json.dumps(res, indent=1, default=str))


def _wilson(k: int, n: int, z: float = 1.959964) -> tuple[float, float]:
    import math
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return (c - h, c + h)


def _overlap(a, b) -> bool:
    return a[0] is not None and b[0] is not None and a[0] <= b[1] and b[0] <= a[1]


def evaluate_rules(spec: dict, hr: Path) -> dict:
    ref = spec["screen_reference"]
    out: dict = {}
    typ = json.loads((hr / "typology.json").read_text())
    n_ho = typ["n"]
    n_sc = sum(v["n"] for v in ref["E1_cluster_shares"].values())
    e1 = {}
    for name, r in ref["E1_cluster_shares"].items():
        k = typ["shares"].get(name, {}).get("n", 0)
        ci_h, ci_s = _wilson(k, n_ho), _wilson(r["n"], n_sc)
        e1[name] = dict(heldout_share=k / n_ho if n_ho else None, heldout_ci=ci_h, screen_share=r["share"], screen_ci=ci_s,
                        overlap=_overlap(ci_h, ci_s))
    out["E1"] = dict(by_cluster=e1, success=all(v["overlap"] for v in e1.values()))
    val = json.loads((hr / "validation.json").read_text())
    same, sig = 0, 0
    e2 = {}
    for v, r in ref["E2"].items():
        h = val["results"][v]["3ch"]
        so = h["median_rank_order"] == r["median_rank_order_by_cluster_id"]
        same += so
        sig += (h["kw_p"] is not None and h["kw_p"] < 0.05)
        e2[v] = dict(heldout=h, screen=r, same_order=so)
    out["E2"] = dict(by_V=e2, n_same_order=same, n_sig=sig, success=bool(same >= 2 and sig >= 1))
    ll = json.loads((hr / "leadlag.json").read_text())["primary"]
    s_h, ci_h = ll["share_expansion_first"], ll["share_expansion_first_ci"]
    r3 = ref["E3"]
    side = (s_h is not None and ((s_h - r3["null_mean"]) * (r3["share"] - r3["null_mean"]) > 0))
    out["E3"] = dict(heldout_share=s_h, heldout_ci=ci_h, n_both=ll["n_both_onsets"], screen=r3,
                     success=bool(ci_h[0] is not None and _overlap(ci_h, r3["ci"]) and side))
    roles = json.loads((hr / "roles.json").read_text())["predeclared"]
    ors = roles["entry_hazard"]["primary_logit_robust"]["terms"]
    common_l = [k for k in ors if k.isupper() and k in ref["E4"]["entry_ORs"]]
    import math
    out["E4"] = dict(heldout_robust_shares=roles["robust_shares"], screen_robust_shares=ref["E4"]["robust_shares"],
                     heldout_ORs={k: ors[k] for k in common_l}, screen_ORs={k: ref["E4"]["entry_ORs"][k] for k in common_l},
                     same_sign_all=all(math.copysign(1, ors[k]["coef"]) == math.copysign(1, ref["E4"]["entry_ORs"][k]["coef"]) for k in common_l))
    import csv
    rows = [r for r in csv.DictReader((hr / "patterns.csv").open()) if r["population"] == "screen_MAIN" and r["subset"] == "all"
            and r["threshold_version"] == "recomputed_hydrated"]
    e5 = {}
    for r in rows:
        s = ref["E5"].get(r["pattern"])
        if s:
            ci = [float(r["ci_lo"]), float(r["ci_hi"])]
            e5[r["pattern"]] = dict(heldout=float(r["freq"]), heldout_ci=ci, screen=s["freq"], screen_ci=s["ci"], overlap=_overlap(ci, s["ci"]))
    out["E5"] = e5
    return out


if __name__ == "__main__":
    main()
