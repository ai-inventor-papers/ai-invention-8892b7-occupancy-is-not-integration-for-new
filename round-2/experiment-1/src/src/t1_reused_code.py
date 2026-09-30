#!/usr/bin/env python3
"""T1: the vendored Schwartz-Hearst must reproduce DS4 labelling/sh_eval.json pair precision (0.95 +- 0.01) on the
acronym_identification validation sentences (D4b), with DS4's exact scoring rule; normalise() variant check;
grep check that only the guard mentions the sealed file."""
import json
import re

from loguru import logger

from common import DATA, RESULTS, SRC, normalise, read_json, schwartz_hearst, setup_logging, write_json


@logger.catch(reraise=True)
def main() -> None:
    setup_logging("t1_reused_code")
    rows = [r for r in read_json(DATA / "d4b.json") if r["fold"] == "validation"]
    tp_pair = fp_pair = tp_sf = fp_sf = 0
    for r in rows:
        sent = r["sentence"]
        shorts, longs = r["gold"]["short_forms"], r["gold"]["long_forms"]
        pred = schwartz_hearst(sent)
        pred_sf, gold_sf = {p[0] for p in pred}, set(shorts)
        tp_sf += len(pred_sf & gold_sf)
        fp_sf += len(pred_sf - gold_sf)
        gl = {normalise(x) for x in longs}
        for sf, lf in pred:
            if sf in gold_sf and normalise(lf) in gl:
                tp_pair += 1
            else:
                fp_pair += 1
    pp = tp_pair / max(1, tp_pair + fp_pair)
    ref = json.loads((DATA / "sh_eval.json").read_text())
    ok_sh = abs(pp - ref["pair_precision"]) <= 0.01
    ok_norm = normalise("Weyl semimetals") == normalise("weyl-semimetal")
    sealed_mentions = []
    for p in sorted((SRC).rglob("*.py")):
        for i, line in enumerate(p.read_text().splitlines(), 1):
            if "SEALED" in line:
                sealed_mentions.append(f"{p.relative_to(SRC)}:{i}")
    ok_guard = all(m.startswith("common.py") or m.startswith("t1_reused_code.py") for m in sealed_mentions)
    out = {"n_validation_sentences": len(rows), "pair_precision": round(pp, 4), "reference_pair_precision": ref["pair_precision"],
           "short_form_precision": round(tp_sf / max(1, tp_sf + fp_sf), 4), "sh_reproduced_within_0.01": ok_sh,
           "normalise_weyl_check": ok_norm, "sealed_mentions": sealed_mentions, "only_guard_mentions_sealed": ok_guard}
    write_json(RESULTS / "t1_reused_code.json", out)
    logger.info(out)
    assert ok_sh and ok_norm and ok_guard, out


if __name__ == "__main__":
    main()
