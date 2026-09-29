"""Iteration-4 held-out confirmation of the D2 grafting test. Runs the FROZEN spec exactly once on the held-out fold.

  .venv/bin/python confirm_heldout.py --open-heldout          # the real confirmation (writes results/heldout_confirmation.json)
  .venv/bin/python confirm_heldout.py --dry-run               # same code path on SCREEN events; must reproduce the screen M1
  .venv/bin/python confirm_heldout.py --dry-run --spec X.json # dry run against a spec copy (used to test the hash refusal)

Refuses to run if sha256(heldout_spec.json) differs from heldout_spec.sha256, or if any frozen code file hash differs.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

WS = Path(__file__).resolve().parent
sys.path.insert(0, str(WS / "src"))


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def verify(spec_path: Path) -> dict:
    sha_path = spec_path.with_suffix(".sha256")
    want = sha_path.read_text().split()[0]
    got = sha(spec_path)
    if got != want:
        raise SystemExit(f"REFUSED: sha256({spec_path.name}) = {got} != frozen {want}")
    spec = json.loads(spec_path.read_text())
    for rel, h in spec["code_sha256"].items():
        if sha(WS / rel) != h:
            raise SystemExit(f"REFUSED: code file {rel} changed since the freeze")
    return spec


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--spec", default=str(WS / "heldout_spec.json"))
    ap.add_argument("--open-heldout", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    if a.open_heldout == a.dry_run:
        raise SystemExit("choose exactly one of --open-heldout / --dry-run")
    spec = verify(Path(a.spec))
    import numpy as np
    import pandas as pd

    import config
    import io_load
    import models
    import outcomes
    config.setup_logging("confirm_heldout")
    G = io_load.prepare()
    if a.open_heldout:
        config.SEALED_IDS.clear()  # explicit opening of the held-out fold
        feats = pd.read_parquet(WS / spec["sealed_files"]["heldout_features"]["path"])
        if sha(WS / spec["sealed_files"]["heldout_features"]["path"]) != spec["sealed_files"]["heldout_features"]["sha256"]:
            raise SystemExit("REFUSED: sealed feature file changed")
        fold, out_name = "heldout", "heldout_confirmation.json"
    else:
        config.load_sealed_ids()  # the held-out fold stays sealed in a dry run
        feats = pd.read_parquet(config.RESULTS / "features_screen.parquet")
        feats = feats[(feats.arm == "main") & (feats.fold == "screen")].reset_index(drop=True)
        fold, out_name = "screen", "heldout_dryrun_on_screen.json"
    feats = feats.reset_index(drop=True)
    base = feats[(feats.arm == "main") & (feats.fold == fold) & feats.kw5 & feats.MAIN]
    Y = outcomes.compute_Y(G, base)
    df = feats.join(Y)
    s = models.primary_sample(df, fold=fold)
    res = {"fold": fold, "spec_sha256": sha(Path(a.spec)), "n_events": int(len(s)), "n_concepts": int(s.concept_id.nunique())}
    est = spec["estimator"]
    rng = np.random.default_rng(spec["seed"])
    for spec_name in est["fe_specs"]:
        xs = est["x"] + (est["controls"] if spec_name == "primary" else est["controls_secondary"])
        r = models.fit_one(s, spec["estimand"]["outcome"], xs, spec_name, wild=True, wild_vars=tuple(est["x"]), rng=rng)
        res[spec_name] = {k: r[k] for k in ["n_retained", "G", "coef", "se", "p", "irr_sd", "ci_irr_sd", "p_wild",
                                            "retained_share"]} if r else None
        res[f"decision_{spec_name}"] = models.decide(r) if r else None
    res["reading_rule"] = spec["decision_rule"]
    res["underpowered_declaration"] = spec["power"]
    (config.RESULTS / out_name).write_text(json.dumps(res, indent=1, default=float))
    print(json.dumps({k: res[k] for k in res if k.startswith("decision") or k in ("fold", "n_events")}, default=float))


if __name__ == "__main__":
    main()
