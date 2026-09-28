#!/usr/bin/env python3
"""STEP 7 (part b): merging, acronym collision risk and linking for all 426 frame concepts (and D5 pool phrases as extra
linking queries). All thresholds are READ from models/*.json. UNLINKED concepts stay first-class nodes (node_id = concept_id)."""
from __future__ import annotations

import hashlib
import json
import time
from collections import Counter, defaultdict

import joblib
import numpy as np
import requests
from loguru import logger
from scipy.cluster.hierarchy import fcluster, linkage
from scipy.spatial.distance import squareform

from common import CACHE, DATA, MINI, MODELS, RESULTS, SENT_SPLIT, load_frame, match_form, normalise, read_json, schwartz_hearst, set_limits, setup_logging, write_json
from featlib import emb_text
from linklib import NN, Targets, is_broader
from mergelib import PairFeaturizer

WD_BAD = ("scholarly article", "scientific article", "journal", "family name", "given name", "disambiguation")
UA = "aii-emerging-concepts-grounding/0.2 (academic research on scientific concept emergence; python-requests)"


def concept_forms(c: dict) -> list[str]:
    return sorted({f for f in [c["phrase"]] + list(c.get("surface_forms") or []) if emb_text(f)}, key=lambda s: (s != c["phrase"], s))


def volume(c: dict) -> float:
    if c["arm"] == "main":
        return float(c.get("V") or 0)
    return float(sum((c.get("screen_counts_by_year") or {}).values()))


WD_STATE = {"n_throttled": 0, "skip": False, "live_calls": 0}


def wikidata_search(phrase: str) -> dict | None:
    """F7: on HTTP 429/403 back off 60 s and retry twice; after that, stop live Wikidata calls for the rest of the run
    (cached responses are still used; legacy-concept wikidata ids remain the other route)."""
    cp = CACHE / "wikidata" / (hashlib.sha1(phrase.encode()).hexdigest() + ".json")
    if cp.exists():
        return json.loads(cp.read_text())
    if WD_STATE["skip"]:
        return None
    for attempt in range(3):
        try:
            WD_STATE["live_calls"] += 1
            r = requests.get("https://www.wikidata.org/w/api.php",
                             params={"action": "wbsearchentities", "search": phrase, "language": "en", "type": "item",
                                     "limit": 10, "format": "json"}, headers={"User-Agent": UA}, timeout=30)
        except requests.RequestException as e:
            logger.warning(f"wikidata {phrase!r}: {e!r}")
            time.sleep(5)
            continue
        if r.status_code == 200:
            d = r.json()
            cp.write_text(json.dumps(d))
            time.sleep(1.0)
            return d
        if r.status_code in (429, 403):
            WD_STATE["n_throttled"] += 1
            if WD_STATE["n_throttled"] >= 3:
                logger.warning("FALLBACK F7: Wikidata throttled 3 times; no further live calls (cache only)")
                WD_STATE["skip"] = True
                return None
            logger.warning(f"wikidata HTTP {r.status_code}; backing off 60 s (attempt {attempt})")
            time.sleep(60)
            continue
        time.sleep(2)
    return None


@logger.catch(reraise=True)
def main() -> None:
    setup_logging("s7b_merge_link")
    set_limits(40)
    t0 = time.time()
    frame = load_frame()
    cids = sorted(frame)
    mthr = read_json(MODELS / "merger_thresholds.json")
    lthr = read_json(MODELS / "link_thresholds.json")
    mres = read_json(RESULTS / "merger_results.json")
    # F5 choice rule (fixed in s4): if the primary merger fails on D3 test (F1 < 0.70) while doing well on MeSH, use the
    # model with the higher D3-OOF F1
    d3_f1 = mres["test"]["d3_test"]["primary"]["f1"]["point"]
    mesh_f1 = mres["test"]["heldout_mesh"]["primary"]["f1"]["point"]
    # Interpretation (documented in README): the plan's F5 scenario names 'while doing well on MeSH', but its fixed
    # choice rule is 'the frame merge uses the model with the higher D3-OOF F1'. The frame is physics/CS, i.e. D3-like,
    # so the rule is applied whenever the primary merger fails on D3 test; the comparison itself uses train OOF only.
    f5 = d3_f1 < 0.70
    f5_mesh_ok = mesh_f1 >= 0.70
    choice = read_json(MODELS / "merger_choice.json")  # s4b: F5 choice restricted to thresholds admissible on D3 AND MeSH
    if f5 and choice["choice"] == "lr_d3_only":
        mobj = joblib.load(MODELS / "merger_lr_d3only.joblib")
        merger, p_merge, merger_name = mobj["model"], choice["p_merge_choice"], "lr_d3_only"
        p_merge_strict = max(p_merge, mthr["p_merge_strict"])
    else:
        merger, p_merge, p_merge_strict, merger_name = joblib.load(MODELS / "merger_lr.joblib")["model"], mthr["p_merge"], mthr["p_merge_strict"], "lr_primary"
    logger.info(f"merger {merger_name} (F5 triggered={f5}); p_merge {p_merge:.3f} strict {p_merge_strict:.3f}")
    pf = PairFeaturizer()

    # ================= merging (concept-level: max p over surface-form pairs)
    forms = {c: concept_forms(frame[c]) for c in cids}
    pair_list, owners = [], []
    for i in range(len(cids)):
        for j in range(i + 1, len(cids)):
            for a in forms[cids[i]]:
                for b in forms[cids[j]]:
                    pair_list.append((a, b))
                    owners.append((i, j))
    logger.info(f"merge candidates: {len(cids) * (len(cids) - 1) // 2} concept pairs, {len(pair_list)} form pairs")
    P = np.zeros((len(cids), len(cids)))
    B = 200000
    for s in range(0, len(pair_list), B):
        X = pf.features(pair_list[s:s + B])
        p = merger.predict_proba(X)[:, 1]
        for (i, j), v in zip(owners[s:s + B], p):
            if v > P[i, j]:
                P[i, j] = P[j, i] = v
    np.fill_diagonal(P, 1.0)
    Z = linkage(squareform(1 - P, checks=False), method="average")
    merge = {}
    for nm, t in (("primary", p_merge), ("strict", p_merge_strict)):
        lab = fcluster(Z, t=1 - t, criterion="distance")
        clusters = defaultdict(list)
        for c, l in zip(cids, lab):
            clusters[l].append(c)
        info = {}
        for l, mem in clusters.items():
            canon = sorted(mem, key=lambda c: (-volume(frame[c]), int(frame[c].get("F") or 9999), frame[c]["phrase"]))[0]
            arms = sorted({frame[c]["arm"] for c in mem})
            for c in mem:
                info[c] = {"cluster_id": f"m_{canon}", "canonical_id": canon, "merged_into": None if c == canon else canon,
                           "cluster_size": len(mem), "cross_arm": len(arms) > 1, "members": sorted(mem)}
        merge[nm] = info
    multi = sorted({tuple(v["members"]) for v in merge["primary"].values() if v["cluster_size"] > 1})
    merge_pairs_top = sorted(((float(P[i, j]), cids[i], cids[j]) for i in range(len(cids)) for j in range(i + 1, len(cids)) if P[i, j] >= 0.3), reverse=True)[:60]
    logger.info(f"merge: {len(multi)} multi-member clusters at p_merge; ({time.time() - t0:.0f}s)")

    # ================= acronyms (flag for later retrieval; NOT used now)
    sh_pairs = []
    import pandas as pd
    d1 = pd.read_parquet(CACHE / "d1_corpus.parquet", columns=["abstract"])
    for a in d1["abstract"].tolist():
        for s in SENT_SPLIT.split(a or ""):
            if "(" in s:
                sh_pairs += schwartz_hearst(s)
    for r in read_json(DATA / "d4b.json"):
        sh_pairs += schwartz_hearst(r["sentence"])
    lf_by_sf: dict[str, Counter] = defaultdict(Counter)
    sf_by_lf: dict[str, Counter] = defaultdict(Counter)
    for sf, lf in sh_pairs:
        lf_by_sf[sf.lower()][match_form(lf)] += 1
        sf_by_lf[match_form(lf)][sf] += 1
    from wordfreq import zipf_frequency
    acr = {}
    for c in cids:
        sfs = set(a for a in (frame[c].get("acronyms") or []))
        for f in forms[c]:
            for sf, n in sf_by_lf.get(match_form(f), {}).items():
                sfs.add(sf)
        rows = []
        for sf in sorted(sfs):
            cnt = lf_by_sf.get(sf.lower(), Counter())
            tot = sum(cnt.values())
            dom = (cnt.most_common(1)[0][1] / tot) if tot else 1.0
            eng = zipf_frequency(sf.lower(), "en") > 3
            risk = min(1.0, (1 - dom) + (0.3 if len(sf) <= 3 else 0) + (0.2 if eng else 0))
            rows.append({"short_form": sf, "n_distinct_long_forms": len(cnt), "dominant_long_form_share": round(dom, 3),
                         "len": len(sf), "is_english_word": eng, "collision_risk": round(risk, 3), "flag_for_later_retrieval": True})
        acr[c] = rows
    logger.info(f"acronyms: {len(sh_pairs)} SH pairs; {sum(1 for v in acr.values() if v)} concepts with short forms")

    # ================= linking
    # the linker gate is the model/threshold the linker was calibrated with in s5 (primary merger, p_merge)
    link_merger, link_p = joblib.load(MODELS / "merger_lr.joblib")["model"], lthr["p_merge"]
    T = Targets()
    enc = lthr["encoder"]
    store = pf.mini if enc == "minilm" else pf.spec
    tau, tau_b = lthr["tau"], lthr["tau_broader"]
    stage2_ok = not lthr["stage2_failed_calibration"]
    if tau is None:  # F6: no calibrated tau; broader links still need a cosine floor -> use the top of the grid
        tau, tau_b = 0.98, 0.93
    if MINI:  # the mini pipeline embeds only a vocabulary sample
        T.strings = [x for x in T.strings if pf.mini.has(x) and pf.spec.has(x)]
    nn = NN(store, T.strings)
    d5 = read_json(DATA / "d5.json")
    queries = [(("frame", c), forms[c]) for c in cids]
    for r in d5:
        ph = r["input"].get("phrase") or r["input"].get("key") or ""
        if ph:
            queries.append((("d5", ph), [ph]))
    flat = [(qi, f) for qi, (_, fs_) in enumerate(queries) for f in fs_]
    Q = store.get([emb_text(f) for _, f in flat])
    sims, idxs = nn.topk(Q, k=10)
    best: dict[int, list] = defaultdict(list)
    for (qi, f), s_row, i_row in zip(flat, sims, idxs):
        for s, j in zip(s_row, i_row):
            best[qi].append((float(s), T.strings[int(j)], f))
    # merger gate on the top candidates
    gate_pairs = []
    for qi in range(len(queries)):
        best[qi].sort(key=lambda x: -x[0])
        best[qi] = best[qi][:10]
        for s, t, f in best[qi]:
            gate_pairs.append((qi, f, t))
    Xg = pf.features([(f, t) for _, f, t in gate_pairs])
    pg = link_merger.predict_proba(Xg)[:, 1]
    gate = {(qi, f, t): float(p) for (qi, f, t), p in zip(gate_pairs, pg)}
    links_out = {}
    for qi, (key, fs_) in enumerate(queries):
        links = T.exact(fs_)
        has_exact = bool(links)
        cand = best[qi]
        if stage2_ok and not has_exact and cand:
            s, t, f = cand[0]
            g = gate[(qi, f, t)]
            if s >= tau and g >= link_p:
                for rec in T.recs[t]:
                    links.append({**rec, "link_type": "exact_embed", "method": f"stage2_{enc}_cos+merger_gate", "score": round(s, 4),
                                  "merger_p": round(g, 4), "query_form": f, "target_string": t})
        if not any(l["link_type"] in ("exact", "exact_embed") for l in links):
            for s, t, f in cand:
                if s < tau_b:
                    break
                g = gate[(qi, f, t)]
                if is_broader(f, t) or g < link_p:
                    for rec in T.recs[t]:
                        links.append({**rec, "link_type": "broader", "method": f"stage2_{enc}_{'token_subset_same_head' if is_broader(f, t) else 'cos_ge_tau_broader_merger_below_p_merge'}",
                                      "score": round(s, 4), "merger_p": round(g, 4), "query_form": f, "target_string": t})
                    break
        links_out[key] = {"links": links, "top_candidates": [(round(s, 4), t, round(gate[(qi, f, t)], 4)) for s, t, f in cand[:3]]}
    logger.info(f"linking done ({time.time() - t0:.0f}s)")

    # ================= Wikidata for frame concepts (sequential, <= 1 req/s, cached)
    wd = {}
    wd_calls = 0
    wd_skipped = False
    fails = 0
    cand_strings = {}
    for c in cids:
        if MINI and len(wd) >= 10:
            break
        d = wikidata_search(frame[c]["phrase"])
        if d is None:
            fails += 1
            wd_skipped = WD_STATE["skip"]
            continue
        hits = [h for h in d.get("search", []) if not any(b in (h.get("description") or "").lower() for b in WD_BAD)]
        wd[c] = hits
        for h in hits:
            for s in [h.get("label") or ""] + list(h.get("aliases") or []) + [(h.get("match") or {}).get("text", "")]:
                if s:
                    cand_strings[emb_text(s)] = s
    need = [s for s in cand_strings if s and not store.has(s)]
    if need:
        from encoders import Encoder
        e = Encoder(enc)
        store.add(need, e.encode(need))
        other = pf.spec if enc == "minilm" else pf.mini
        need2 = [s for s in cand_strings if s and not other.has(s)]
        if need2:
            e2 = Encoder("specter2" if enc == "minilm" else "minilm")
            other.add(need2, e2.encode(need2))
    wd_links = {}
    for c, hits in wd.items():
        best_h = None
        for h in hits:
            strs = [s for s in [h.get("label") or ""] + list(h.get("aliases") or []) + [(h.get("match") or {}).get("text", "")] if s]
            for f in forms[c]:
                qv = store.get([emb_text(f)])[0]
                for s in strs:
                    cs = float(store.get([emb_text(s)])[0] @ qv)
                    if best_h is None or cs > best_h[0]:
                        best_h = (cs, h, s, f)
        if best_h and best_h[0] >= tau:
            g = float(link_merger.predict_proba(pf.features([(best_h[3], best_h[2])]))[:, 1][0])
            if g >= link_p or normalise(best_h[2]) == normalise(best_h[3]):
                wd_links[c] = {"vocab": "wikidata", "id": best_h[1].get("id"), "label": best_h[1].get("label"),
                               "description": best_h[1].get("description"), "link_type": "exact_embed" if normalise(best_h[2]) != normalise(best_h[3]) else "exact",
                               "method": f"wikidata_wbsearchentities+{enc}_cos+merger_gate", "score": round(best_h[0], 4), "merger_p": round(g, 4),
                               "matched_string": best_h[2]}
    logger.info(f"wikidata: {len(wd)} searched ({WD_STATE['live_calls']} live calls), {len(wd_links)} accepted ({time.time() - t0:.0f}s)")

    # ================= assemble per concept
    per = {}
    audit = []
    for c in cids:
        L = list(links_out[("frame", c)]["links"])
        if c in wd_links:
            L.append(wd_links[c])
        qid = wd_links.get(c, {}).get("id")
        if not qid:
            for l in L:
                if l["vocab"] == "openalex_legacy_concept" and l["link_type"] in ("exact", "exact_embed") and l.get("wikidata"):
                    qid = str(l["wikidata"]).rsplit("/", 1)[-1]
                    break
        types = {l["link_type"] for l in L}
        status = "LINKED_EXACT" if types & {"exact", "exact_embed"} else ("BROADER_ONLY" if "broader" in types else "UNLINKED")
        per[c] = {"node_id": c, "links": [{"target_vocab": l["vocab"], "target_id": l["id"], "target_label": l["label"], "link_type": l["link_type"],
                                           "method": l["method"], "score": l.get("score"), "merger_p": l.get("merger_p")} for l in L],
                  "wikidata_qid": qid, "link_status": status, "top_candidates": links_out[("frame", c)]["top_candidates"],
                  "acronyms": acr[c],
                  **{f"merge_{k}": v for k, v in merge["primary"][c].items() if k != "members"},
                  "merge_cluster_id_strict": merge["strict"][c]["cluster_id"], "merged_into_strict": merge["strict"][c]["merged_into"]}
        for l in L:
            if l["link_type"] in ("exact_embed", "broader"):
                audit.append({"id": f"{c}|{l['vocab']}|{l['id']}", "concept_id": c, "phrase": frame[c]["phrase"],
                              "target_vocab": l["vocab"], "target_id": l["id"], "target_label": l["label"], "link_type": l["link_type"]})
    for mem in multi:
        for a_ in mem:
            for b_ in mem:
                if a_ < b_:
                    audit.append({"id": f"MERGE|{a_}|{b_}", "concept_id": a_, "phrase": frame[a_]["phrase"], "target_vocab": "frame_merge",
                                  "target_id": b_, "target_label": frame[b_]["phrase"], "link_type": "merge"})
    d5_status = Counter()
    for qi, (key, _) in enumerate(queries):
        if key[0] == "d5":
            types = {l["link_type"] for l in links_out[key]["links"]}
            d5_status["LINKED_EXACT" if types & {"exact", "exact_embed"} else ("BROADER_ONLY" if "broader" in types else "UNLINKED")] += 1
    out = {"meta": {"merger": merger_name, "F5_triggered": f5, "F5_mesh_ok": f5_mesh_ok, "primary_d3_test_f1": d3_f1,
                    "primary_mesh_test_f1": mesh_f1, "p_merge": p_merge, "p_merge_strict": p_merge_strict,
                    "link_thresholds": lthr, "stage2_enabled": stage2_ok, "wikidata_live_calls": WD_STATE["live_calls"], "merger_choice": choice, "wikidata_skipped_F7": wd_skipped,
                    "wikidata_searched": len(wd), "wikidata_not_searched": len(cids) - len(wd), "wikidata_throttle_events": WD_STATE["n_throttled"],
                    "n_target_strings": len(T.strings), "n_sh_pairs": len(sh_pairs), "runtime_s": time.time() - t0},
           "concepts": per, "merge_multi_clusters_primary": [list(m) for m in multi],
           "merge_multi_clusters_strict": sorted({tuple(v["members"]) for v in merge["strict"].values() if v["cluster_size"] > 1}),
           "top_merge_pairs": merge_pairs_top, "d5_link_status": dict(d5_status),
           "d5_links": {key[1]: links_out[key]["links"][:3] for key in links_out if key[0] == "d5"}}
    write_json(RESULTS / "frame_merge_link.json", out, indent=None)
    write_json(RESULTS / "frame_links_for_audit.json", audit)
    logger.info(f"link status {Counter(v['link_status'] for v in per.values())}; D5 {dict(d5_status)}; {len(audit)} links for audit")


if __name__ == "__main__":
    main()
