#!/usr/bin/env python3
"""S1 INTEGRITY: recompute sha256 of every frozen code / population / input / sealed file before any fold is opened.

Checks (all must pass, otherwise the affected part is not opened):
  exp5 (R1)  heldout_spec.json code_sha256 + population_files against the byte-copy deps_run/exp5;
             input_manifest (ds5:, exp3:) against the ORIGINAL dependency paths;
             heldout_spec.sha256 == sha256(spec) == last heldout_spec.json record of results/freeze_log.jsonl, prefix 535c2dd3.
  exp6 (D1)  results/heldout/heldout_spec.json code_sha256 + population_files against deps_run/exp6; sidecar == sha256(spec).
  exp7 (D3)  sealed/*.parquet against their .sha256 sidecars (original workspace, read-only).
Writes results/integrity_report.json.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

from loguru import logger

WS = Path(__file__).resolve().parent
LOOP = WS.parents[2]  # .../3_invention_loop
EXP5, EXP6 = WS / "deps_run" / "exp5", WS / "deps_run" / "exp6"
ORIG5 = LOOP / "round-3" / "." / "experiment-5/src"
ORIG6 = LOOP / "round-3" / "." / "experiment-6/src"
EXP7 = LOOP / "round-3" / "." / "experiment-7/src"
DS5 = LOOP / "round-2" / "." / "dataset-5/src"
EXP3 = LOOP / "round-2" / "." / "experiment-3/src"
R1_PREFIX = "535c2dd3"

logger.remove()
logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
(WS / "logs").mkdir(exist_ok=True)
logger.add(WS / "logs" / "s1_integrity.log", rotation="30 MB", level="DEBUG")


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def check_map(base: Path, mapping: dict, label: str) -> list[dict]:
    out = []
    for rel, h in mapping.items():
        p = base / rel.split(" (")[0]
        got = sha(p) if p.exists() else None
        out.append(dict(group=label, file=rel, expected=h, got=got, ok=got == h))
    return out


@logger.catch(reraise=True)
def main() -> None:
    rep: dict = {"parts": {}}
    # ---------------- exp5 / R1
    spec5_p = EXP5 / "heldout_spec.json"
    spec5 = json.loads(spec5_p.read_text())
    side5 = (EXP5 / "heldout_spec.sha256").read_text().strip()
    logged = None
    for line in (EXP5 / "results" / "freeze_log.jsonl").read_text().splitlines():
        rec = json.loads(line)
        if rec.get("file") == "heldout_spec.json":
            logged = rec["sha256"]
    got5 = sha(spec5_p)
    checks = [dict(group="spec", file="heldout_spec.json", expected=side5, got=got5,
                   ok=bool(got5 == side5 == logged and side5.startswith(R1_PREFIX)), logged=logged,
                   original_sha=sha(ORIG5 / "heldout_spec.json"))]
    checks += check_map(EXP5, spec5["code_sha256"], "code_sha256")
    checks += check_map(EXP5, spec5["population_files"], "population_files")
    for key, h in spec5["input_manifest"].items():
        pre, rel = key.split(":", 1)
        base = DS5 if pre == "ds5" else EXP3
        p = base / rel
        got = sha(p) if p.exists() else None
        checks.append(dict(group=f"input_manifest:{pre}", file=rel, expected=h, got=got, ok=got == h))
    rep["parts"]["R1_exp5"] = dict(n_checked=len(checks), n_ok=sum(c["ok"] for c in checks),
                                   all_ok=all(c["ok"] for c in checks), spec_sha256=got5,
                                   failures=[c for c in checks if not c["ok"]], checks=checks)
    # ---------------- exp6 / D1
    spec6_p = EXP6 / "results" / "heldout" / "heldout_spec.json"
    spec6 = json.loads(spec6_p.read_text())
    side6 = (EXP6 / "results" / "heldout" / "heldout_spec.sha256").read_text().strip()
    got6 = sha(spec6_p)
    c6 = [dict(group="spec", file="results/heldout/heldout_spec.json", expected=side6, got=got6, ok=got6 == side6,
               original_sha=sha(ORIG6 / "results" / "heldout" / "heldout_spec.json"))]
    c6 += check_map(EXP6, spec6["code_sha256"], "code_sha256")
    c6 += check_map(EXP6, spec6["population_files"], "population_files")
    rep["parts"]["D1_exp6"] = dict(n_checked=len(c6), n_ok=sum(c["ok"] for c in c6), all_ok=all(c["ok"] for c in c6),
                                   spec_sha256=got6, failures=[c for c in c6 if not c["ok"]], checks=c6)
    # ---------------- exp7 sealed + exp6 sealed sidecars (D3 inputs)
    c7 = []
    for side in sorted((EXP7 / "sealed").glob("*.sha256")) + sorted((ORIG6 / "sealed").glob("*.sha256")):
        exp_h = side.read_text().split()[0].strip()
        p = side.with_suffix(".parquet")
        got = sha(p) if p.exists() else None
        c7.append(dict(group=f"sealed_sidecar:{side.parent.parent.name}", file=p.name, expected=exp_h, got=got, ok=got == exp_h))
    rep["parts"]["D3_sealed"] = dict(n_checked=len(c7), n_ok=sum(c["ok"] for c in c7), all_ok=all(c["ok"] for c in c7),
                                     failures=[c for c in c7 if not c["ok"]], checks=c7)
    rep["all_ok"] = all(v["all_ok"] for v in rep["parts"].values())
    rep["r1_spec_prefix_ok"] = got5.startswith(R1_PREFIX)
    (WS / "results").mkdir(exist_ok=True)
    (WS / "results" / "integrity_report.json").write_text(json.dumps(rep, indent=1))
    for k, v in rep["parts"].items():
        logger.info(f"{k}: {v['n_ok']}/{v['n_checked']} ok")
        for f in v["failures"]:
            logger.error(f"MISMATCH {k} {f['group']} {f['file']}")
    logger.info(f"integrity all_ok={rep['all_ok']}  R1 spec sha {got5[:12]}  D1 spec sha {got6[:12]}")


if __name__ == "__main__":
    main()
