#!/usr/bin/env python3
"""R0a gate: sha256 of heldout_spec.json, the 7 frozen code files, the 3 sealed files and the spec's data_files."""
import hashlib
import json
import sys
from pathlib import Path

EVAL = Path(__file__).resolve().parents[1]
D2 = EVAL / "d2"
RUN = Path(__import__("os").environ.get("AII_DEPS_ROOT", EVAL.parents[2])).resolve().parent  # run root


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for ch in iter(lambda: f.read(1 << 20), b""):
            h.update(ch)
    return h.hexdigest()


def main() -> None:
    spec_p = D2 / "heldout_spec.json"
    spec = json.loads(spec_p.read_text())
    want = (D2 / "heldout_spec.sha256").read_text().split()[0]
    rows = [{"kind": "spec", "path": "d2/heldout_spec.json", "want": want, "got": sha(spec_p)}]
    for rel, h in spec["code_sha256"].items():
        rows.append({"kind": "code", "path": f"d2/{rel}", "want": h, "got": sha(D2 / rel)})
    for k, v in spec["sealed_files"].items():
        rows.append({"kind": "sealed", "path": f"d2/{v['path']}", "want": v["sha256"], "got": sha(D2 / v["path"])})
    for v in spec["data_files"]:
        p = RUN / v["path"]
        rows.append({"kind": "data", "path": v["path"], "want": v["sha256"], "got": sha(p) if p.exists() else None})
    for r in rows:
        r["match"] = r["want"] == r["got"]
    out = {"n_checked": len(rows), "n_match": sum(r["match"] for r in rows),
           "counts": {k: sum(1 for r in rows if r["kind"] == k) for k in ("spec", "code", "sealed", "data")},
           "all_match": all(r["match"] for r in rows), "files": rows}
    (EVAL / "results" / "gate_hashes.json").write_text(json.dumps(out, indent=1))
    print(json.dumps({k: out[k] for k in ("n_checked", "n_match", "counts", "all_match")}))
    sys.exit(0 if out["all_match"] else 1)


if __name__ == "__main__":
    main()
