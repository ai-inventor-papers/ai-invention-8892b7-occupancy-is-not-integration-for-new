#!/usr/bin/env python3
"""G4 (iteration 4): does the D2 host-entry grafting result replicate on 191 MeSH biomedical concepts?

Stage runner. Every stage reads the outputs of earlier stages from results/ (resumable):

  .venv/bin/python method.py --stage gates        # 1-2  gate 1 + gate 2 on the main screen + harmonisation h1-h5
  .venv/bin/python method.py --stage load         # 3    MeSH concepts, works, partner/author structures, co-word substrate
  .venv/bin/python method.py --stage coverage     # 4    PubMed host-coverage rule (6 OpenAlex credits) + truncation audit
  .venv/bin/python method.py --stage events       # 5    MeSH host-entry events (W1 only) + G1 multi-team events
  .venv/bin/python method.py --stage nativeness   # 6    bg fallback check -> exact profiles (reuse + capped fetch)
  .venv/bin/python method.py --stage features     # 7    W1 features (+ entry-paper topic hydration) + leakage test
  .venv/bin/python method.py --stage freeze       # 8    MDE simulation + mesh_spec.json sha256 freeze
  .venv/bin/python method.py --stage outcomes     # 9    author-disjoint newcomer uptake (refuses to run unless frozen)
  .venv/bin/python method.py --stage models       # 10   PPML rows, bootstrap, Holm, placebo, crosscheck, verdict
  .venv/bin/python method.py --stage report       # 11   method_out.json, figures, comparison tables
  .venv/bin/python method.py --stage h6           # 12   harmonisation h6 on the main screen (needs the MeSH fetch coverage)
  .venv/bin/python method.py                      # all stages in order

  --mini  runs stages load..features on 10 MeSH concepts (5 largest + 5 random, seed 42) and never computes outcomes.
OPENALEX_API_KEY must be exported for the paid calls (coverage, nativeness fetch, topic hydration).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_v, "1")  # small dense problems; avoids BLAS oversubscription in the spawn workers

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from loguru import logger  # noqa: E402

import common  # noqa: E402

STAGES = ["gates", "load", "coverage", "events", "nativeness", "features", "freeze", "outcomes", "models", "report", "h6"]


@logger.catch(reraise=True)
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", default=None, choices=STAGES)
    ap.add_argument("--mini", action="store_true")
    a = ap.parse_args()
    common.setup_logging("method" + ("_mini" if a.mini else ""))
    common.set_ram_limit(26)
    stages = [a.stage] if a.stage else STAGES
    if a.mini:
        stages = [s for s in stages if s in ("load", "coverage", "events", "nativeness", "features")]
    timings = {}
    for st in stages:
        t = time.time()
        logger.info(f"===== stage {st} (mini={a.mini}) =====")
        if st == "gates":
            import gates
            gates.run()
        elif st == "load":
            import load_mesh
            load_mesh.run(mini=a.mini)
        elif st == "coverage":
            import coverage
            coverage.run(mini=a.mini)
        elif st == "events":
            import events_mesh
            events_mesh.run(mini=a.mini)
        elif st == "nativeness":
            import nativeness
            nativeness.run(mini=a.mini)
        elif st == "features":
            import features_mesh
            features_mesh.run(mini=a.mini)
        elif st == "freeze":
            import freeze
            freeze.run()
        elif st == "outcomes":
            import outcomes_mesh
            outcomes_mesh.run()
        elif st == "models":
            import models_mesh
            models_mesh.run()
        elif st == "report":
            import report
            report.run()
        elif st == "h6":
            import gates
            gates.harmonise_h6()
        timings[st] = round(time.time() - t, 1)
        logger.info(f"stage {st} done in {timings[st]} s")
    tp = common.LOGS / "timings.json"
    try:
        prev = json.loads(tp.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        prev = {}
    prev.update({("mini_" if a.mini else "") + k: v for k, v in timings.items()})
    tp.write_text(json.dumps(prev, indent=1))


if __name__ == "__main__":
    main()
