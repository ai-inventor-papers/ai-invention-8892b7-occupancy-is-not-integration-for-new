"""RQ2-D2 host-entry test: does anchoring into the host (grafting) or co-transfer of origin companions (toolkit)
predict that a concept's entry into a new subfield is followed by newcomer uptake there?

  .venv/bin/python method.py                 # all stages 0-16 in order
  .venv/bin/python method.py --stage 7       # a single stage (earlier outputs must exist)
  .venv/bin/python method.py --mini          # smoke run: 10 screen concepts + 3 reference concepts, stages 0-7

Stages: 0 prereg freeze, 1 load, 2 population, 3 reproduction, 4 events, 5 features (W1), 6 outcomes (screen only),
7 models, 8 robustness, 9 placebo, 10-11 labels + D3, 12 out-of-sample + method_out.json, 13 power, 14 held-out freeze,
15 figures, 16 summary.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

import pandas as pd  # noqa: E402
from loguru import logger  # noqa: E402

import config  # noqa: E402
from config import RESULTS, SEALED, setup_logging  # noqa: E402


def screen_features() -> pd.DataFrame:
    fs = pd.read_parquet(RESULTS / "features_screen.parquet")
    return fs


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", type=int, default=None)
    ap.add_argument("--mini", action="store_true")
    a = ap.parse_args()
    setup_logging("method")
    config.set_ram_limit(26)
    stages = [a.stage] if a.stage is not None else list(range(17))
    if a.mini:
        stages = [s for s in stages if s <= 7]
    import io_load
    t0 = time.time()
    timings = {}
    G = None

    def need_G():
        nonlocal G
        if G is None:
            G = io_load.prepare()
        return G

    for st in stages:
        t = time.time()
        if st == 0:
            import prereg
            prereg.freeze()
        elif st == 1:
            G = io_load.prepare(force=True)
            (RESULTS / "origin_check.json").write_text(json.dumps(io_load.origin_counter_check(G), indent=1,
                                                                  default=str))
        elif st == 2:
            import population
            population.build(need_G())
        elif st == 3:
            import events
            r = events.reproduce_iter1(need_G())
            if not r["pass"]:
                raise RuntimeError("3a event reproduction failed; see results/repro_events_iter1.json")
        elif st == 4:
            import events
            pop = json.loads((RESULTS / "main_population_hydrated.json").read_text())
            ev = events.build_events(need_G(), pop)
            if a.mini:
                keep = sorted(ev[(ev.arm == "main") & (ev.fold == "screen")].concept_id.unique())[:10] + \
                    sorted(ev[ev.arm == "reference"].concept_id.unique())[:3]
                ev[ev.concept_id.isin(keep)].to_parquet(RESULTS / "events_all.parquet", index=False)
        elif st == 5:
            import features
            features.build_features(need_G(), pd.read_parquet(RESULTS / "events_all.parquet"))
        elif st == 6:
            import outcomes
            config.load_sealed_ids()
            f = screen_features()
            m = f[(f.arm == "main") & (f.fold == "screen")].reset_index(drop=True)
            y = outcomes.compute_Y(need_G(), m)
            out = m.join(y)
            out.to_parquet(RESULTS / "screen_events_with_outcomes.parquet", index=False)
            p = out[out.MAIN & out.kw5]
            dec = {"n_primary_sample": int(len(p)), "Y_strict_zero_share": float((p.Y_strict == 0).mean()),
                   "Y_lenient_zero_share": float((p.Y_lenient == 0).mean()),
                   "Y_all_zero_share": float((p.Y_all == 0).mean()),
                   "rule": "switch primary to Y_lenient iff Y_strict zero share > 0.85 (decided before any coefficient)"}
            dec["switch_to_lenient"] = dec["Y_strict_zero_share"] > 0.85
            (RESULTS / "outcome_sparsity_decision.json").write_text(json.dumps(dec, indent=1))
        elif st == 7:
            import models
            models.run_models(pd.read_parquet(RESULTS / "screen_events_with_outcomes.parquet"), crosscheck=True)
        elif st == 8:
            import robustness
            config.load_sealed_ids()
            robustness.run(need_G(), pd.read_parquet(RESULTS / "screen_events_with_outcomes.parquet"))
        elif st == 9:
            import placebo
            placebo.run(need_G(), pd.read_parquet(RESULTS / "screen_events_with_outcomes.parquet"))
        elif st in (10, 11):
            if st == 11:
                continue  # stage 11 runs inside labels.run
            import labels
            config.load_sealed_ids()
            fs = screen_features()
            so = pd.read_parquet(RESULTS / "screen_events_with_outcomes.parquet")
            fsm = fs[(fs.arm == "main") & (fs.fold == "screen")].reset_index(drop=True)
            assert (fsm.concept_id.to_numpy() == so.concept_id.to_numpy()).all()
            fs = pd.concat([fsm, fs[fs.arm == "reference"]], ignore_index=True)
            fh = pd.read_parquet(SEALED / "heldout_features.parquet").reset_index(drop=True)
            labels.run(need_G(), fs, fh, so)
        elif st == 12:
            import assemble_out
            meta = {"prereg_sha256": json.loads((RESULTS / "d2_prereg.json").read_text())["sha256"]}
            assemble_out.run(pd.read_parquet(RESULTS / "screen_events_with_outcomes.parquet"),
                             pd.read_parquet(RESULTS / "graft_labels_screen.parquet"), meta)
        elif st == 13:
            import power
            power.run(pd.read_parquet(RESULTS / "screen_events_with_outcomes.parquet"))
        elif st == 14:
            import freeze
            freeze.freeze(json.loads((RESULTS / "d2_models.json").read_text()),
                          json.loads((RESULTS / "power_heldout.json").read_text()))
        elif st == 15:
            import figures
            figures.run()
        elif st == 16:
            import summary
            summary.run()
        timings[st] = round(time.time() - t, 1)
        logger.info(f"stage {st} done in {timings[st]} s")
    tp = config.LOGS / "timings.json"
    try:
        prev = json.loads(tp.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        prev = {"stages": {}}
    prev["stages"].update({str(k): v for k, v in timings.items()})
    prev["last_invocation"] = {"stages": sorted(timings), "total_s": round(time.time() - t0, 1), "mini": a.mini}
    tp.write_text(json.dumps(prev, indent=1))


if __name__ == "__main__":
    main()
