#!/usr/bin/env python3
"""STEP 4b: admissibility of the F5 alternative merger under the plan's own threshold rule.
The plan fixes p_merge as the smallest probability with OOF pair precision >= 0.90 on the D3 subset AND on the MeSH
subset (max of the two). s4 chose the D3-only model's threshold on D3-OOF alone. Here the same two-subset rule is
applied to the D3-only model: its D3 threshold comes from D3 OOF, its MeSH threshold from the MeSH train pairs (which
it never saw, so they are held-out validation for it; no test pair is used). The frame merge then uses the model with
the higher D3-OOF F1 at its admissible threshold (the F5 choice rule). Writes models/merger_choice.json."""
from __future__ import annotations

import numpy as np
import joblib
from loguru import logger
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

from clfdata import _prf, precision_threshold
from common import DATA, MODELS, normalise, read_json, setup_logging, write_json
from mergelib import PairFeaturizer


@logger.catch(reraise=True)
def main() -> None:
    setup_logging("s4b_merger_choice")
    thr = read_json(MODELS / "merger_thresholds.json")
    d3 = read_json(DATA / "d3.json")
    mp = read_json(DATA / "mesh_pairs.json")
    hm = read_json(DATA / "heldout_mesh_concepts.json")
    held = [r for r in mp if r["metadata_fold"] == "heldout_mesh"]
    H = {normalise(x) for r in held for x in (r["term_a"], r["term_b"])} | {normalise(x) for c in hm for x in [c["preferred_term"]] + c["surface_forms"] + c["acronyms"]}
    held_ui = {r["metadata_descriptor_ui"] for r in held} | {r["metadata_descriptor_ui_b"] for r in held} | {c["descriptor_ui"] for c in hm}
    mtr = [r for r in mp if r["metadata_fold"] in ("train_eligible", "working_list") and normalise(r["term_a"]) not in H
           and normalise(r["term_b"]) not in H and r["metadata_descriptor_ui"] not in held_ui and r["metadata_descriptor_ui_b"] not in held_ui]
    d3tr = [r for r in d3 if r["metadata_fold"] == "train" and normalise(r["phrase_1"]) not in H and normalise(r["phrase_2"]) not in H]
    pf = PairFeaturizer()
    Xm = pf.features([(r["term_a"], r["term_b"]) for r in mtr])
    ym = np.array([r["y"] for r in mtr])
    Xd = pf.features([(r["phrase_1"], r["phrase_2"]) for r in d3tr])
    yd = np.array([r["output"] == "SAME" for r in d3tr], dtype=int)
    gd = np.array([str(r.get("metadata_cluster_1") or r.get("metadata_key_1")) for r in d3tr])
    d3only = joblib.load(MODELS / "merger_lr_d3only.joblib")["model"]
    C = thr["config"]["C"]
    p_d3 = np.zeros(len(yd))
    for tr, va in GroupKFold(5).split(Xd, yd, gd):
        m = Pipeline([("sc", StandardScaler()), ("clf", LogisticRegression(C=C, class_weight="balanced", max_iter=5000))]).fit(Xd[tr], yd[tr])
        p_d3[va] = m.predict_proba(Xd[va])[:, 1]
    p_mesh = d3only.predict_proba(Xm)[:, 1]
    t_d3 = precision_threshold(yd, p_d3, 0.90)
    t_me = precision_threshold(ym, p_mesh, 0.90)
    admissible = t_d3 is not None and t_me is not None
    t_adm = max(t_d3, t_me) if admissible else None
    f1_d3only = _prf(yd, (p_d3 >= t_adm).astype(int))[2] if admissible else 0.0
    f1_primary = thr["oof_f1_d3_at_threshold"]["primary"]
    choice = "lr_d3_only" if admissible and f1_d3only > f1_primary else "lr_primary"
    out = {"d3only_threshold_d3_oof_p90": t_d3, "d3only_threshold_mesh_train_p90": t_me, "d3only_admissible_threshold": t_adm,
           "d3only_precision_on_mesh_train_at_d3_threshold": _prf(ym, (p_mesh >= thr["d3only_threshold"]).astype(int))[0],
           "d3only_oof_f1_d3_at_admissible_threshold": f1_d3only, "primary_oof_f1_d3_at_p_merge": f1_primary,
           "choice": choice, "p_merge_choice": t_adm if choice == "lr_d3_only" else thr["p_merge"],
           "rule": "F5 choice (higher D3-OOF F1) among models whose threshold meets OOF precision >= 0.90 on BOTH D3 and MeSH (plan's p_merge rule)",
           "why": "the D3-only threshold alone (0.506) merged topically related frame phrases into clusters of up to 70 members"}
    write_json(MODELS / "merger_choice.json", out)
    logger.info(out)


if __name__ == "__main__":
    main()
