#!/usr/bin/env python3
"""STEP 5: NIL-aware calibration of the embedding linker on MeSH (heldout_mesh descriptors and every string in H excluded).
3,000 descriptors with >= 1 entry term; query = one random non-preferred entry term (un-inverted).
 (a) in-KB: strings with the query's match form removed from the index -> correct if the accepted top-1 is the query's descriptor
 (b) NIL: ALL strings of the query's descriptor removed -> any accepted link is a false link
precision_pi(tau) = (1-pi) TP / ((1-pi)(TP + wrong) + pi FL); PRIMARY pi = 0.9; tau = smallest tau with precision_pi >= 0.90.
Encoders: MiniLM, SPECTER2 (+ SapBERT for this biomedical calibration only, reported, not used for the frame).
Gate: merger p(SAME | query, target) >= p_merge (also reported without the gate)."""
from __future__ import annotations

import gc
import random
import time

import joblib
import matplotlib
import numpy as np
import torch
from loguru import logger

from common import DATA, MINI, MODELS, RESULTS, SEED, match_form, normalise, read_json, set_limits, setup_logging, write_json
from featlib import EmbStore, emb_text
from linklib import NN, Targets, _mesh_variants
from mergelib import PairFeaturizer

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

TAUS = np.round(np.arange(0.60, 0.981, 0.01), 2)
PIS = [0.5, 0.7, 0.9]


def prec_pi(tp, wrong, fl, pi):
    den = (1 - pi) * (tp + wrong) + pi * fl
    return (1 - pi) * tp / den if den > 0 else np.nan


@logger.catch(reraise=True)
def main() -> None:
    setup_logging("s5_link_calib")
    set_limits(40)
    t0 = time.time()
    mp = read_json(DATA / "mesh_pairs.json")
    hm = read_json(DATA / "heldout_mesh_concepts.json")
    held = [r for r in mp if r["metadata_fold"] == "heldout_mesh"]
    H = set()
    for r in held:
        H |= {normalise(r["term_a"]), normalise(r["term_b"])}
    for c in hm:
        H |= {normalise(x) for x in [c["preferred_term"]] + c["surface_forms"] + c["acronyms"]}
    held_ui = {r["metadata_descriptor_ui"] for r in held} | {r["metadata_descriptor_ui_b"] for r in held} | {c["descriptor_ui"] for c in hm}
    T = Targets(mesh_only=True, exclude_ui=held_ui)
    # drop descriptors that carry any H string
    bad = {ui for ui, r in T.mesh_desc.items() if any(normalise(t) in H for t in [r["heading"]] + r["entry_terms"])}
    strings = [s for s in T.strings if not any(rec["id"] in bad for rec in T.recs[s])]
    pf = PairFeaturizer()
    if MINI:  # the mini pipeline embeds only a vocabulary sample
        strings = [s for s in strings if pf.mini.has(s)]
    s_ui = [{rec["id"] for rec in T.recs[s]} for s in strings]
    s_mf = [match_form(s) for s in strings]
    mf_idx: dict[str, list[int]] = {}
    for j, m in enumerate(s_mf):
        mf_idx.setdefault(m, []).append(j)
    logger.info(f"MeSH calibration index: {len(strings)} strings, {len(T.mesh_desc) - len(bad)} descriptors (excluded {len(held_ui)} heldout + {len(bad)} H-string)")
    rng = random.Random(SEED)
    cands = sorted(ui for ui, r in T.mesh_desc.items() if ui not in bad and r["entry_terms"])
    samp = rng.sample(cands, min(300 if MINI else 3000, len(cands)))
    queries = []
    for ui in samp:
        r = T.mesh_desc[ui]
        t = rng.choice(r["entry_terms"])
        q = _mesh_variants(t)[-1]
        if pf.mini.has(emb_text(q)):
            queries.append({"ui": ui, "query": q, "q_emb": emb_text(q), "q_mf": match_form(q)})
    merger = joblib.load(MODELS / "merger_lr.joblib")["model"]
    mthr = read_json(MODELS / "merger_thresholds.json")
    p_merge = mthr["p_merge"]
    # queries must be embedded: they are MeSH entry-term variants, all in the embedding store already
    stores = {"minilm": pf.mini, "specter2": pf.spec}
    if not MINI:
        from encoders import Encoder
        try:
            enc = Encoder("sapbert")
            need = sorted(set(strings) | {q["q_emb"] for q in queries})
            M = enc.encode(need, batch=1024)
            sap = EmbStore.__new__(EmbStore)
            sap.name, sap.strings, sap.idx, sap.mat, sap.extra = "sapbert", need, {s: i for i, s in enumerate(need)}, M.astype(np.float16), {}
            stores["sapbert"] = sap
            del enc
            gc.collect()
            torch.cuda.empty_cache()
        except (OSError, RuntimeError, ValueError) as e:
            logger.warning(f"SapBERT comparison skipped: {e!r}")
    res: dict = {"n_queries": len(queries), "n_index_strings": len(strings), "p_merge": p_merge, "encoders": {}}
    for ename, st in stores.items():
        nn = NN(st, strings)
        Q = st.get([q["q_emb"] for q in queries])
        sims, idxs = nn.topk(Q, k=60)
        del nn
        torch.cuda.empty_cache()
        rows = {"a": [], "b": []}
        for qi, q in enumerate(queries):
            for cond in ("a", "b"):
                top = None
                for s, j in zip(sims[qi], idxs[qi]):
                    if cond == "a" and s_mf[j] == q["q_mf"]:
                        continue
                    if cond == "b" and q["ui"] in s_ui[j]:
                        continue
                    top = (float(s), int(j))
                    break
                if top is None:
                    rows[cond].append((0.0, False, strings[0]))
                    continue
                correct = q["ui"] in s_ui[top[1]]
                rows[cond].append((top[0], correct, strings[top[1]]))
        # merger gate probabilities for (query, top-1 string)
        gate = {}
        for cond in ("a", "b"):
            X = pf.features([(q["query"], rows[cond][i][2]) for i, q in enumerate(queries)])
            gate[cond] = merger.predict_proba(X)[:, 1]
        # stage-1 exact on the reduced index (ambiguous entry terms shared with another descriptor)
        ex_b = np.array([any(s_ui[j] - {q["ui"]} for j in mf_idx.get(q["q_mf"], [])) for q in queries])
        curves = {}
        for gated in (True, False):
            cur = []
            for tau in TAUS:
                acc_a = np.array([r[0] >= tau for r in rows["a"]])
                acc_b = np.array([r[0] >= tau for r in rows["b"]])
                if gated:
                    acc_a &= gate["a"] >= p_merge
                    acc_b &= gate["b"] >= p_merge
                corr = np.array([r[1] for r in rows["a"]])
                tp = float(np.mean(acc_a & corr))
                wrong = float(np.mean(acc_a & ~corr))
                fl = float(np.mean(acc_b | ex_b))
                cur.append({"tau": float(tau), "tp_rate": tp, "wrong_rate": wrong, "falselink_rate": fl,
                            **{f"precision_pi{pi}": prec_pi(tp, wrong, fl, pi) for pi in PIS}})
            curves["gated" if gated else "ungated"] = cur
        # choose tau at pi = 0.9 (gated primary)
        pick = {}
        for g in ("gated", "ungated"):
            ok = [c for c in curves[g] if c["precision_pi0.9"] == c["precision_pi0.9"] and c["precision_pi0.9"] >= 0.90]
            pick[g] = {"tau": ok[0]["tau"], "recall_at_tau": ok[0]["tp_rate"], "falselink_rate": ok[0]["falselink_rate"],
                       "precision_pi0.9": ok[0]["precision_pi0.9"]} if ok else None
        res["encoders"][ename] = {"curves": curves, "pick": pick, "stage1_falselink_rate_nil": float(ex_b.mean()),
                                  "top1_accuracy_inKB_no_threshold": float(np.mean([r[1] for r in rows["a"]]))}
        logger.info(f"{ename}: pick {pick}; top1 acc {res['encoders'][ename]['top1_accuracy_inKB_no_threshold']:.3f}")
    # encoder choice (frame encoders only: MiniLM vs SPECTER2), higher recall at precision 0.90 (gated); tie -> MiniLM
    def rec(e):
        p = res["encoders"].get(e, {}).get("pick", {}).get("gated")
        return p["recall_at_tau"] if p else -1
    enc = "minilm" if rec("minilm") >= rec("specter2") else "specter2"
    pk = res["encoders"][enc]["pick"]["gated"]
    failed = pk is None
    tau = pk["tau"] if pk else None
    link_thr = {"encoder": enc, "tau": tau, "tau_broader": (round(tau - 0.05, 2) if tau else None), "gate": "merger p >= p_merge",
                "p_merge": p_merge, "pi_primary": 0.9, "stage2_failed_calibration": failed,
                "recall_at_tau": pk["recall_at_tau"] if pk else None, "falselink_rate_at_tau": pk["falselink_rate"] if pk else None,
                "rule": "choose encoder with higher in-KB recall at precision_pi(0.9) >= 0.90 (gated); tie -> MiniLM; SapBERT reported only",
                "frozen_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    if failed:
        logger.warning("FALLBACK F6: calibration never reached precision 0.90 at pi=0.9; stage-2 exact_embed links disabled")
    write_json(MODELS / "link_thresholds.json", link_thr)
    res["frozen"] = link_thr
    # ---------------- T4 sanity signals (chosen encoder, full MeSH calibration index)
    from encoders import Encoder
    probes = ["follicular dendritic cell", "blorfen quantum zebrafy pudding lattice"]
    pe = [emb_text(x) for x in probes]
    for nm_, st_ in (("minilm", pf.mini), ("specter2", pf.spec)):
        new = [x for x in pe if not st_.has(x)]
        if new:
            st_.add(new, Encoder(nm_).encode(new))
    st = stores[enc]
    Qp = st.get(pe)
    nn = NN(st, strings)
    sp_, ip_ = nn.topk(Qp, k=1)
    san = {}
    for k, ph in enumerate(probes):
        tgt = strings[int(ip_[k][0])]
        g = float(merger.predict_proba(pf.features([(ph, tgt)]))[:, 1][0])
        acc = bool(tau is not None and sp_[k][0] >= tau and g >= p_merge)
        san[ph] = {"top1": tgt, "top1_descriptors": sorted(s_ui[int(ip_[k][0])]), "cos": float(sp_[k][0]), "merger_p": g, "accepted": acc}
    mm = Encoder("minilm").encode(["massive mimo", "massive multiple-input multiple-output", "massive star"])
    san["minilm_cos_mimo_long"] = float(mm[0] @ mm[1])
    san["minilm_cos_mimo_star"] = float(mm[0] @ mm[2])
    heads = [T.mesh_desc[u]["heading"] for u in san[probes[0]]["top1_descriptors"] if u in T.mesh_desc]
    san[probes[0]]["top1_headings"] = heads
    san["stage1_exact_fdc"] = [x["label"] for x in T.exact([probes[0]])]
    san["pass_fdc_linked"] = bool(san[probes[0]]["accepted"] and any("follicular" in h.lower() for h in heads)) or \
        any("follicular" in x.lower() for x in san["stage1_exact_fdc"])
    san["pass_nonsense_nil"] = not san[probes[1]]["accepted"]
    san["pass_mimo"] = san["minilm_cos_mimo_long"] > san["minilm_cos_mimo_star"]
    res["sanity"] = san
    logger.info(f"T4 sanity: {san}")
    # figure
    fig, axes = plt.subplots(1, 2, figsize=(9, 3.6))
    for e, c in res["encoders"].items():
        cur = c["curves"]["gated"]
        axes[0].plot([x["tau"] for x in cur], [x["precision_pi0.9"] for x in cur], label=e)
        axes[1].plot([x["tau"] for x in cur], [x["tp_rate"] for x in cur], label=e)
    for pi, ls in zip(PIS[:2], [":", "--"]):
        cur = res["encoders"][enc]["curves"]["gated"]
        axes[0].plot([x["tau"] for x in cur], [x[f"precision_pi{pi}"] for x in cur], ls, color="grey", label=f"{enc} pi={pi}")
    axes[0].axhline(0.9, color="k", lw=0.8)
    axes[0].set_xlabel("cosine threshold tau")
    axes[0].set_ylabel("link precision at NIL prior pi=0.9")
    axes[1].set_xlabel("cosine threshold tau")
    axes[1].set_ylabel("in-KB recall (correct accepted links)")
    axes[0].legend(fontsize=7)
    plt.tight_layout()
    plt.savefig(RESULTS / "fig_link_calibration.png", dpi=150)
    plt.close()
    res["runtime_s"] = time.time() - t0
    write_json(RESULTS / "link_calibration.json", res)
    logger.info(f"frozen link thresholds {link_thr} ({time.time() - t0:.0f}s)")


if __name__ == "__main__":
    main()
