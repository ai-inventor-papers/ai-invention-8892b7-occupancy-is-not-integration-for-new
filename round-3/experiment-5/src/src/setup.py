"""Step 0: vendor exp_3 code byte-identical, hash it, verify the exp_3 spec hash, write prereg_v3.json.

prereg_v3.json (SPEC3 + exp_3 spec hash + vendor hashes + UTC) and its sha256 are written BEFORE any label is
computed; the hash is appended to results/freeze_log.jsonl.
"""
from __future__ import annotations

import hashlib
import json
import shutil

from loguru import logger

import common as K


def vendor() -> dict:
    missing = [f for f in K.VENDOR_FILES if not (K.EXP3 / f).exists()]
    if missing:
        raise FileNotFoundError(f"exp_3 files missing (plan stops at Step 0): {missing}")
    K.VENDOR.mkdir(exist_ok=True)
    hashes = {}
    for f in K.VENDOR_FILES:
        src, dst = K.EXP3 / f, K.VENDOR / f
        if not dst.exists() or K.sha256_file(dst) != K.sha256_file(src):
            shutil.copy2(src, dst)
        hashes[f] = K.sha256_file(dst)
        assert hashes[f] == K.sha256_file(src), f"vendored {f} differs from exp_3"
    spec = json.loads((K.VENDOR / "spec.json").read_text())
    h = hashlib.sha256(json.dumps(spec["spec"], sort_keys=True).encode()).hexdigest()
    assert h == spec["sha256"], f"exp_3 spec hash mismatch {h} != {spec['sha256']}"
    import config as C  # vendored
    assert C.spec_hash() == spec["sha256"], "vendored config.SPEC differs from spec.json"
    for d in ("work", "snapshots"):
        must = K.EXP3 / "work" / (d if d == "snapshots" else "")
        if not must.exists():
            raise FileNotFoundError(f"exp_3 {must} missing")
    out = dict(files=hashes, exp3_spec_sha256=spec["sha256"], exp3_path_relative="../../../round-2/experiment-3/src")
    (K.VENDOR / "vendor_sha256.json").write_text(json.dumps(out, indent=1))
    logger.info(f"vendored {len(hashes)} files; exp_3 spec sha256 {spec['sha256'][:12]}")
    return out


def write_prereg(vend: dict) -> str:
    p = K.ROOT / "prereg_v3.json"
    if p.exists():
        old = json.loads(p.read_text())
        if old.get("spec3_sha256") == K.spec3_hash():
            logger.info(f"prereg_v3.json exists with the same SPEC3 hash {old['spec3_sha256'][:12]}; kept (utc {old['utc']})")
            return K.sha256_file(p)
        raise RuntimeError("prereg_v3.json exists with a DIFFERENT SPEC3 -- refusing to overwrite a pre-registration")
    obj = dict(SPEC3=K.SPEC3, spec3_sha256=K.spec3_hash(), exp3_spec_sha256=vend["exp3_spec_sha256"],
               vendor_sha256=vend["files"], utc=K.utc_now(),
               note="written before any label (Step 5) is computed; labels, matches and outcomes come later")
    p.write_text(json.dumps(obj, indent=1, sort_keys=True))
    h = K.sha256_file(p)
    (K.ROOT / "prereg_v3.sha256").write_text(h + "\n")
    K.append_freeze_log("prereg_v3.json", h, "pre-registration of SPEC3 before labels")
    logger.info(f"prereg_v3.json sha256 {h}")
    return h


def main() -> dict:
    v = vendor()
    h = write_prereg(v)
    return dict(vendor=v, prereg_sha256=h)


if __name__ == "__main__":
    K.setup_logging("setup")
    main()
