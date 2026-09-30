#!/usr/bin/env python3
"""S5/S6: select Track L / Track P candidates, label them with two cheap LLMs from different
families, split by variant cluster, adjudicate with a third-family model, run the human-anchored
check on SemEval-2017/SciERC and report agreement.

Usage: python s5_label.py select|label|split|adjudicate|anchor|report
All LLM calls are cached (cache/llm) so every stage is resumable.
"""
from __future__ import annotations

import asyncio
import json
import random
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from loguru import logger

sys.path.insert(0, str(Path(__file__).resolve().parent))
from llm import LLM, MODEL_A, MODEL_ADJ, MODEL_B, BudgetStop, system_prompt  # noqa: E402
from rawio import dump_pickle, load_pickle  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
LAB = ROOT / "labelling"
LAB.mkdir(exist_ok=True)
logger.remove()
logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
logger.add(ROOT / "logs" / "s5_label.log", rotation="30 MB", level="DEBUG")

SEED = 20260928
MAIN_FIRST, MAIN_LAST = 2005, 2016
BATCH = 20


def macro_domain(domain: str | None, field_id: int) -> str:
    if field_id in (17, 22):
        return "computing_engineering"
    return {"Life Sciences": "life", "Health Sciences": "health", "Physical Sciences": "physical",
            "Social Sciences": "social"}.get(domain or "", "physical")


def load_cands():
    return load_pickle("candidates"), load_pickle("docs_meta")


def snippet(texts: list[str], di: int, s0: int, s1: int, surfaces: list[str], width: int = 260) -> str:
    t = texts[di][s0:s1].strip()
    if len(t) <= width:
        return t
    low = t.lower()
    pos = -1
    for s in surfaces:
        pos = low.find(s.lower())
        if pos >= 0:
            break
    pos = max(pos, 0)
    a = max(0, pos - width // 2)
    return ("…" if a else "") + t[a:a + width] + "…"


def key_stats(C, M) -> dict[str, dict]:
    meta = M["meta"]
    lf_of_sf = defaultdict(Counter)  # key of short form (lowercased) -> long-form keys
    for (sf, lk), n in C["acr_pairs"].items():
        lf_of_sf[sf.lower()][lk] += n
    acr_keys = {lk for (_, lk) in C["acr_pairs"]}
    out = {}
    for k, docs in C["docs_by_key"].items():
        main_years = [meta[d]["year"] for d in docs if meta[d]["corpus"] == "main"]
        pre = any(meta[d]["corpus"] == "prescreen" or meta[d]["year"] <= 2004 for d in docs)
        fields = Counter(meta[d]["field_id"] for d in docs)
        doms = Counter(macro_domain(meta[d]["domain"], meta[d]["field_id"]) for d in docs)
        out[k] = {
            "n_occ": len(docs),
            "n_occ_main": len(main_years),
            "first_main_year": min(main_years) if main_years else None,
            "last_main_year": max(main_years) if main_years else None,
            "in_pre": pre,
            "n_fields": len(fields),
            "macro_domain": doms.most_common(1)[0][0],
            "n_tokens": len(k.split(" ")),
            "is_acronym_long_form": k in acr_keys,
            "cvalue": round(C["cvalue"].get(k, 0.0), 4),
        }
    return out


def band(n: int) -> str:
    return "3-5" if n <= 5 else "6-20" if n <= 20 else "21-100" if n <= 100 else ">100"


def form(k: str, st: dict) -> str:
    if st["is_acronym_long_form"]:
        return "acronym"
    return "1tok" if st["n_tokens"] == 1 else "2tok" if st["n_tokens"] == 2 else "3+tok"


def stratified_draw(groups: dict[tuple, list[str]], total: int, rng: random.Random) -> list[str]:
    """Equal allocation across non-empty cells, redistributing leftover capacity."""
    cells = {g: sorted(v) for g, v in groups.items() if v}
    for v in cells.values():
        rng.shuffle(v)
    take = {g: 0 for g in cells}
    remaining = total
    while remaining > 0:
        open_cells = [g for g in cells if take[g] < len(cells[g])]
        if not open_cells:
            break
        per = max(1, remaining // len(open_cells))
        for g in open_cells:
            add = min(per, len(cells[g]) - take[g], remaining)
            take[g] += add
            remaining -= add
            if remaining <= 0:
                break
    out = []
    for g in sorted(cells):
        out.extend(cells[g][:take[g]])
    return out


def item_payload(k: str, C, M, st: dict) -> dict:
    surf = [s for s, _ in sorted(C["surfaces"][k].items(), key=lambda x: -x[1])][:3]
    texts = M["texts"]
    sn, seen_docs = [], set()
    for di, s0, s1 in C["snips"][k]:
        if di in seen_docs:
            continue
        seen_docs.add(di)
        sn.append({"work_id": M["meta"][di]["id"], "year": M["meta"][di]["year"],
                   "text": snippet(texts, di, s0, s1, surf)})
        if len(sn) >= 3:
            break
    acr = [sf for (sf, lk) in C["acr_pairs"] if lk == k][:3]
    return {"key": k, "surface_forms": surf, "acronym_short_forms": acr, "snippets": sn,
            "n_sample_occ": st["n_occ"], "first_sample_year": st["first_main_year"], "n_fields": st["n_fields"]}


# ------------------------------------------------------------------ select
def cmd_select() -> None:
    C, M = load_cands()
    ST = key_stats(C, M)
    rng = random.Random(SEED)
    # Track L (direction rule): first main-sample occurrence 2005-2016, >=3 occurrences, absent pre-2005
    L_novel = [k for k, s in ST.items() if s["n_occ"] >= 3 and not s["in_pre"] and s["first_main_year"]
               and MAIN_FIRST <= s["first_main_year"] <= MAIN_LAST]
    L_nonnovel = [k for k, s in ST.items() if s["n_occ"] >= 3 and s["in_pre"]]
    logger.info(f"Track L novel keys: {len(L_novel)}; non-novel >=3 occ keys: {len(L_nonnovel)}")
    groups = defaultdict(list)
    for k in L_novel:
        s = ST[k]
        groups[(band(s["n_occ"]), form(k, s), s["macro_domain"])].append(k)
    n_nov = 1200 if len(L_novel) >= 3000 else min(1500, len(L_novel))
    sel_L = stratified_draw(groups, n_nov, rng)
    # supplement (documented deviation): 300 non-novel frequent keys so TOO_GENERIC / frequent bands are represented
    g2 = defaultdict(list)
    for k in L_nonnovel:
        s = ST[k]
        g2[(band(s["n_occ"]), form(k, s), s["macro_domain"])].append(k)
    sel_L2 = stratified_draw(g2, 1500 - len(sel_L), rng)
    chosen_L = set(sel_L) | set(sel_L2)
    # Track P (pool): >=1 main occurrence 2005-2016, absent from all pre-2005 text, >=2 tokens or acronym long form
    P_all = [k for k, s in ST.items() if not s["in_pre"] and s["first_main_year"]
             and MAIN_FIRST <= s["first_main_year"] <= MAIN_LAST
             and (s["n_tokens"] >= 2 or s["is_acronym_long_form"]) and k not in chosen_L
             and re.search(r"[a-z]{3}", k) and not re.search(r"\d{3,}", k)]
    cv = np.array([ST[k]["cvalue"] for k in P_all])
    q25 = float(np.quantile(cv, 0.25)) if len(cv) else 0.0
    # ">= q25": 44% of Track-P keys tie exactly at q25 (2-token singletons, log2(3)); strict ">" would drop them all
    P_elig = [k for k in P_all if ST[k]["cvalue"] >= q25]
    logger.info(f"Track P: {len(P_all)} novel multi-token keys; C-value q25={q25:.3f}; {len(P_elig)} above")
    gp = defaultdict(list)
    for k in P_elig:
        gp[(ST[k]["first_main_year"], ST[k]["macro_domain"])].append(k)
    sel_P = stratified_draw(gp, 3000, rng)
    audit = rng.sample(sorted(P_elig), 100)  # label-blind audit arm: uniform over Track-P
    sel_P_set = set(sel_P) | set(audit)
    items = {}
    for k in sel_L:
        items[k] = {"track": "L", **item_payload(k, C, M, ST[k]), "stats": ST[k]}
    for k in sel_L2:
        items[k] = {"track": "L_nonnovel", **item_payload(k, C, M, ST[k]), "stats": ST[k]}
    for k in sorted(sel_P_set):  # sorted: set order depends on PYTHONHASHSEED
        items[k] = {"track": "P", **item_payload(k, C, M, ST[k]), "stats": ST[k], "audit_arm": k in audit}
    (LAB / "items.json").write_text(json.dumps(items, ensure_ascii=False))
    summary = {"seed": SEED, "track_L_novel_available": len(L_novel), "track_L_nonnovel_available": len(L_nonnovel),
               "track_L_selected_novel": len(sel_L), "track_L_selected_nonnovel_supplement": len(sel_L2),
               "track_P_available": len(P_all), "track_P_cvalue_q25": q25, "track_P_above_q25": len(P_elig),
               "track_P_selected": len(sel_P_set), "audit_arm": len(audit),
               "n_keys_total": len(ST)}
    (LAB / "selection_summary.json").write_text(json.dumps(summary, indent=2))
    dump_pickle(ST, "key_stats")
    logger.info(summary)


# ------------------------------------------------------------------ label
def head_group(k: str) -> str:
    return k.split(" ")[-1]


def make_batches(keys: list[str], items: dict) -> list[list[str]]:
    # group by shared head token (and acronym long form clusters) so variants can be resolved inside a batch
    ks = sorted(keys, key=lambda k: (head_group(k), k))
    return [ks[i:i + BATCH] for i in range(0, len(ks), BATCH)]


def render_batch(keys: list[str], items: dict) -> tuple[str, dict]:
    idmap, lines = {}, []
    for i, k in enumerate(keys, 1):
        it = items[k]
        iid = f"k{i}"
        idmap[iid] = k
        lines.append(json.dumps({"id": iid, "phrase": k, "surface_forms": it["surface_forms"],
                                 "acronym_short_forms": it.get("acronym_short_forms", []),
                                 "snippets": [s["text"] for s in it["snippets"]]}, ensure_ascii=False))
    user = "Label each item.\n" + "\n".join(lines)
    return user, idmap


def norm_label(x: str | None) -> str:
    x = (x or "").upper().replace("-", "_").strip()
    if x.startswith("VARIANT"):
        return "VARIANT_OF"
    return x if x in ("CONCEPT", "NOT_CONCEPT", "TOO_GENERIC") else "NOT_CONCEPT" if "NOT" in x else "INVALID"


async def label_keys(llm: LLM, model: str, keys: list[str], items: dict, tag: str, sysmsg: str) -> dict:
    batches = make_batches(keys, items)
    out: dict = {}

    async def run(bi, b):
        user, idmap = render_batch(b, items)
        try:
            d = await llm.call_json(model=model, system=sysmsg, user=user, tag=f"{tag}:{bi}")
        except BudgetStop as e:
            logger.error(f"budget stop: {e}")
            return
        except RuntimeError as e:
            logger.error(f"batch {bi} failed: {e}")
            return
        res = d.get("items") or []
        for r in res:
            if not isinstance(r, dict):
                continue
            k = idmap.get(str(r.get("id")))
            if not k:
                continue
            lab = norm_label(r.get("label"))
            vo = idmap.get(str(r.get("variant_of"))) if r.get("variant_of") else None
            if lab == "VARIANT_OF" and (not vo or vo == k):
                lab, vo = "CONCEPT", None  # invalid pointer: fall back (flagged via rationale)
            out[k] = {"label": lab, "variant_of": vo, "rationale": str(r.get("rationale", ""))[:150],
                      "confidence": r.get("confidence"), "model": d.get("_model"), "date": d.get("_date"),
                      "batch_cost": d.get("_cost")}

    await asyncio.gather(*[run(i, b) for i, b in enumerate(batches)])
    return out


def cmd_label(which: str = "all") -> None:
    items = json.loads((LAB / "items.json").read_text())
    sysmsg = system_prompt()
    L_keys = [k for k, v in items.items() if v["track"] in ("L", "L_nonnovel")]
    P_keys = [k for k, v in items.items() if v["track"] == "P"]

    async def go():
        llm = LLM(concurrency=12)
        res = {}
        for model, name in [(MODEL_A, "A"), (MODEL_B, "B")]:
            keys = L_keys if which == "L" else L_keys + P_keys
            res[name] = await label_keys(llm, model, keys, items, f"label{name}", sysmsg)
            logger.info(f"{name} labelled {len(res[name])}/{len(keys)}; spent ${llm.spent:.4f}")
        return res

    res = asyncio.run(go())
    (LAB / "labels_AB.json").write_text(json.dumps(res, ensure_ascii=False))


def cmd_probe() -> None:
    """Send ONE batch per model and extrapolate cost before any sweep."""
    items = json.loads((LAB / "items.json").read_text())
    keys = sorted(items)[:BATCH]
    sysmsg = system_prompt()

    async def go():
        llm = LLM()
        for m in (MODEL_A, MODEL_B, MODEL_ADJ):
            user, _ = render_batch(keys, items)
            d = await llm.call_json(model=m, system=sysmsg, user=user, tag="probe")
            n_b = (len(items) + BATCH - 1) // BATCH
            logger.info(f"{m}: batch cost ${d['_cost']:.5f} -> full sweep ~${d['_cost'] * n_b:.3f} ({n_b} batches)")
            logger.info(json.dumps(d.get('items', [])[:3])[:400])
    asyncio.run(go())


# ------------------------------------------------------------------ split
class UF:
    def __init__(self):
        self.p = {}

    def f(self, x):
        self.p.setdefault(x, x)
        while self.p[x] != x:
            self.p[x] = self.p[self.p[x]]
            x = self.p[x]
        return x

    def u(self, a, b):
        self.p[self.f(a)] = self.f(b)


def squash(k: str) -> str:
    return re.sub(r"[^a-z0-9]", "", k)


def cmd_split() -> None:
    from sklearn.model_selection import StratifiedGroupKFold
    items = json.loads((LAB / "items.json").read_text())
    AB = json.loads((LAB / "labels_AB.json").read_text())
    C, _ = load_cands()
    L_keys = sorted(k for k, v in items.items() if v["track"] in ("L", "L_nonnovel"))
    uf = UF()
    for k in L_keys:
        uf.f(k)
        for n in ("A", "B"):
            vo = AB[n].get(k, {}).get("variant_of")
            if vo and vo in items and items[vo]["track"] != "P":
                uf.u(k, vo)
    lset = set(L_keys)
    for (sf, lk) in C["acr_pairs"]:
        sk = sf.lower()
        if lk in lset and sk in lset:
            uf.u(lk, sk)
    by_sq = defaultdict(list)
    for k in L_keys:
        by_sq[squash(k)].append(k)
    for ks in by_sq.values():
        for k in ks[1:]:
            uf.u(ks[0], k)
    groups = [uf.f(k) for k in L_keys]
    gid = {g: i for i, g in enumerate(sorted(set(groups)))}
    y = []
    for k in L_keys:
        a, b = AB["A"].get(k, {}).get("label"), AB["B"].get(k, {}).get("label")
        maj = a if a == b else "DISAGREE"
        y.append(f"{maj}|{items[k]['stats']['macro_domain']}")
    # collapse rare strata so StratifiedGroupKFold can work
    cnt = Counter(y)
    y = [v if cnt[v] >= 10 else v.split("|")[0] for v in y]
    sgkf = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=SEED)
    tr, te = next(sgkf.split(L_keys, y, [gid[g] for g in groups]))
    split = {L_keys[i]: "train" for i in tr}
    split.update({L_keys[i]: "test" for i in te})
    cluster = {k: f"c{gid[uf.f(k)]}" for k in L_keys}
    # leakage check: no squashed surface form of a cluster in both splits
    sq_split = defaultdict(set)
    for k in L_keys:
        for s in items[k]["surface_forms"] + [k]:
            sq_split[squash(s.lower())].add(split[k])
    leaks = sum(1 for v in sq_split.values() if len(v) > 1)
    (LAB / "split.json").write_text(json.dumps({"split": split, "cluster": cluster, "n_clusters": len(gid),
                                                "surface_leaks": leaks}))
    logger.info(f"split: train={len(tr)} test={len(te)} clusters={len(gid)} surface-form leaks={leaks}")


# ------------------------------------------------------------------ adjudicate
def cmd_adjudicate() -> None:
    items = json.loads((LAB / "items.json").read_text())
    AB = json.loads((LAB / "labels_AB.json").read_text())
    sp = json.loads((LAB / "split.json").read_text())["split"]
    rng = random.Random(SEED + 1)
    test = sorted(k for k, s in sp.items() if s == "test")
    # (i) 200 test items stratified by (A label, macro-domain), blind to A/B
    g = defaultdict(list)
    for k in test:
        g[(AB["A"].get(k, {}).get("label", "NA"), items[k]["stats"]["macro_domain"])].append(k)
    silver = stratified_draw(g, 200, rng)
    # (ii) all L items with A != B, up to 300
    dis = sorted(k for k in sp if AB["A"].get(k, {}).get("label") != AB["B"].get(k, {}).get("label"))
    rng.shuffle(dis)
    dis = [k for k in dis if k not in set(silver)][:300]
    keys = silver + dis
    sysmsg = system_prompt()

    async def go():
        llm = LLM(concurrency=8)
        r = await label_keys(llm, MODEL_ADJ, keys, items, "adj", sysmsg)
        logger.info(f"adjudicated {len(r)}/{len(keys)}; spent ${llm.spent:.4f}")
        return r

    res = asyncio.run(go())
    (LAB / "labels_adj.json").write_text(json.dumps({"silver_gold_200": silver, "disagreements": dis,
                                                     "labels": res}, ensure_ascii=False))


# ------------------------------------------------------------------ anchor (human-referenced validity)
def cmd_anchor() -> None:
    rows = [json.loads(l) for l in (ROOT / "raw" / "anchor_phrases.jsonl").open()]
    rng = random.Random(SEED + 2)
    pick = []
    for src in ("semeval2017_task10", "scierc"):
        pos = [r for r in rows if r["source"] == src and r["fold"] == "test" and r["label"] == "CONCEPT"]
        neg = [r for r in rows if r["source"] == src and r["fold"] == "test" and r["label"] != "CONCEPT"]
        pick += rng.sample(pos, 75) + rng.sample(neg, 75)
    rng.shuffle(pick)
    items = {}
    for i, r in enumerate(pick):
        k = f"{r['phrase']}"
        kk = k if k not in items else f"{k} #{i}"
        items[kk] = {"surface_forms": [r["phrase"]], "acronym_short_forms": [],
                     "snippets": [{"text": r["sentence_context"][:300]}], "human": r}
    keys = list(items)
    sysmsg = system_prompt()

    async def go():
        llm = LLM(concurrency=12)
        out = {}
        for model, name in [(MODEL_A, "A"), (MODEL_B, "B")]:
            # random order batches (no head grouping) for the anchor check
            batches = [keys[i:i + BATCH] for i in range(0, len(keys), BATCH)]
            res = {}

            async def run(bi, b):
                user, idmap = render_batch(b, items)
                try:
                    d = await llm.call_json(model=model, system=sysmsg, user=user, tag=f"anchor{name}:{bi}")
                except (BudgetStop, RuntimeError) as e:
                    logger.error(f"anchor batch {bi}: {e}")
                    return
                for r in d.get("items") or []:
                    if not isinstance(r, dict):
                        continue
                    k = idmap.get(str(r.get("id")))
                    if k:
                        res[k] = {"label": norm_label(r.get("label")),
                                  "variant_of": idmap.get(str(r.get("variant_of"))) if r.get("variant_of") else None,
                                  "confidence": r.get("confidence"), "model": d.get("_model")}
            await asyncio.gather(*[run(i, b) for i, b in enumerate(batches)])
            out[name] = res
        logger.info(f"anchor check spent so far ${llm.spent:.4f}")
        return out

    res = asyncio.run(go())
    (LAB / "anchor_labels.json").write_text(json.dumps({"items": {k: v["human"] for k, v in items.items()},
                                                        "llm": res}, ensure_ascii=False))


# ------------------------------------------------------------------ report
def kappa(a, b):
    from sklearn.metrics import cohen_kappa_score
    if not a:
        return None
    return round(float(cohen_kappa_score(a, b)), 4)


def resolve_variant(lbl: dict, labels: dict) -> str:
    """For binary views, a VARIANT_OF item inherits its target's label (CONCEPT if unknown)."""
    if lbl["label"] != "VARIANT_OF":
        return lbl["label"]
    t = labels.get(lbl.get("variant_of") or "", {})
    return t.get("label") if t.get("label") in ("CONCEPT", "NOT_CONCEPT", "TOO_GENERIC") else "CONCEPT"


def cmd_report() -> None:
    from sklearn.metrics import confusion_matrix
    items = json.loads((LAB / "items.json").read_text())
    AB = json.loads((LAB / "labels_AB.json").read_text())
    sp = json.loads((LAB / "split.json").read_text())
    ADJ = json.loads((LAB / "labels_adj.json").read_text()) if (LAB / "labels_adj.json").exists() else None
    q: dict = {"models": {"A": MODEL_A, "B": MODEL_B, "adjudicator": MODEL_ADJ}}
    classes = ["CONCEPT", "NOT_CONCEPT", "TOO_GENERIC", "VARIANT_OF"]
    for scope, keys in [("track_L", [k for k in items if items[k]["track"] != "P"]),
                        ("track_P_pool_screen", [k for k in items if items[k]["track"] == "P"])]:
        ks = [k for k in keys if k in AB["A"] and k in AB["B"]]
        a = [AB["A"][k]["label"] for k in ks]
        b = [AB["B"][k]["label"] for k in ks]
        per = {}
        for c in classes:
            per[c] = kappa([x == c for x in a], [x == c for x in b])
        ab = [resolve_variant(AB["A"][k], AB["A"]) == "CONCEPT" for k in ks]
        bb = [resolve_variant(AB["B"][k], AB["B"]) == "CONCEPT" for k in ks]
        cm = confusion_matrix(a, b, labels=classes).tolist()
        q[scope] = {"n_both_labelled": len(ks), "n_items": len(keys), "kappa_AB_4class": kappa(a, b),
                    "kappa_AB_per_class_one_vs_rest": per, "kappa_AB_binary_concept_vs_rest": kappa(ab, bb),
                    "raw_agreement": round(float(np.mean([x == y for x, y in zip(a, b)])), 4) if ks else None,
                    "confusion_A_rows_B_cols": {"labels": classes, "matrix": cm},
                    "label_dist_A": dict(Counter(a)), "label_dist_B": dict(Counter(b)),
                    "share_low_confidence_A": round(float(np.mean([AB["A"][k].get("confidence") in (1, "1") for k in ks])), 4) if ks else None,
                    "share_low_confidence_B": round(float(np.mean([AB["B"][k].get("confidence") in (1, "1") for k in ks])), 4) if ks else None}
    if ADJ:
        adj = ADJ["labels"]
        s = [k for k in ADJ["silver_gold_200"] if k in adj and k in AB["A"] and k in AB["B"]]
        g = [adj[k]["label"] for k in s]
        res = {"n": len(s)}
        for n in ("A", "B"):
            p = [AB[n][k]["label"] for k in s]
            gb = [resolve_variant(adj[k], adj) == "CONCEPT" for k in s]
            pb = [resolve_variant(AB[n][k], AB[n]) == "CONCEPT" for k in s]
            res[n] = {"kappa_4class_vs_adj": kappa(p, g), "accuracy_4class_vs_adj": round(float(np.mean([x == y for x, y in zip(p, g)])), 4),
                      "kappa_binary_vs_adj": kappa(pb, gb), "accuracy_binary_vs_adj": round(float(np.mean([x == y for x, y in zip(pb, gb)])), 4),
                      "confusion_vs_adj": {"labels": classes, "matrix": confusion_matrix(g, p, labels=classes).tolist()}}
        res["adj_label_dist"] = dict(Counter(g))
        q["silver_gold_200_vs_adjudicator"] = res
        d = [k for k in ADJ["disagreements"] if k in adj]
        q["disagreements_adjudicated"] = {"n": len(d), "adj_sided_with_A": int(sum(adj[k]["label"] == AB["A"].get(k, {}).get("label") for k in d)),
                                          "adj_sided_with_B": int(sum(adj[k]["label"] == AB["B"].get(k, {}).get("label") for k in d))}
    if (LAB / "anchor_labels.json").exists():
        an = json.loads((LAB / "anchor_labels.json").read_text())
        hr = an["items"]
        out = {"note": "ONLY human-referenced validity number in this artifact: LLM labels vs SemEval-2017 Task 10 / SciERC human annotations "
                       "(a related construct: annotated keyphrase/entity span vs not-annotated noun chunk).",
               "n": len(hr)}
        for n in ("A", "B"):
            L = an["llm"].get(n, {})
            ks = [k for k in hr if k in L]
            h = [hr[k]["label"] == "CONCEPT" for k in ks]
            p = [resolve_variant(L[k], L) == "CONCEPT" for k in ks]
            tp = sum(1 for x, y in zip(h, p) if x and y)
            prec = tp / max(1, sum(p))
            rec = tp / max(1, sum(h))
            per_src = {}
            for src in ("semeval2017_task10", "scierc"):
                kk = [k for k in ks if hr[k]["source"] == src]
                per_src[src] = {"n": len(kk), "accuracy": round(float(np.mean([(hr[k]["label"] == "CONCEPT") == (resolve_variant(L[k], L) == "CONCEPT") for k in kk])), 4) if kk else None,
                                "kappa": kappa([hr[k]["label"] == "CONCEPT" for k in kk], [resolve_variant(L[k], L) == "CONCEPT" for k in kk])}
            gen = [k for k in ks if hr[k].get("entity_type") == "Generic"]
            out[n] = {"n_labelled": len(ks), "kappa_binary": kappa(h, p),
                      "accuracy_binary": round(float(np.mean([x == y for x, y in zip(h, p)])), 4) if ks else None,
                      "precision_concept": round(prec, 4), "recall_concept": round(rec, 4),
                      "f1_concept": round(2 * prec * rec / max(1e-9, prec + rec), 4), "per_source": per_src,
                      "scierc_generic_labelled_too_generic_or_not": f"{sum(L[k]['label'] != 'CONCEPT' for k in gen)}/{len(gen)}",
                      "label_dist": dict(Counter(L[k]["label"] for k in ks))}
        q["human_anchor_check"] = out
    q["split"] = {"n_train": sum(v == "train" for v in sp["split"].values()), "n_test": sum(v == "test" for v in sp["split"].values()),
                  "n_clusters": sp["n_clusters"], "surface_form_leaks_between_splits": sp["surface_leaks"]}
    (LAB / "quality.json").write_text(json.dumps(q, indent=2))
    logger.info(json.dumps(q, indent=1)[:3000])


if __name__ == "__main__":
    cmd = sys.argv[1]
    {"select": cmd_select, "probe": cmd_probe, "label": cmd_label, "split": cmd_split, "adjudicate": cmd_adjudicate,
     "anchor": cmd_anchor, "report": cmd_report, "adjudicate_extra": lambda: None}[cmd]()


def cmd_adjudicate_extra() -> None:
    """Adjudicate the remaining A/B disagreements beyond the first 300 (budget permitting); merged into labels_adj.json."""
    items = json.loads((LAB / "items.json").read_text())
    AB = json.loads((LAB / "labels_AB.json").read_text())
    sp = json.loads((LAB / "split.json").read_text())["split"]
    ADJ = json.loads((LAB / "labels_adj.json").read_text())
    done = set(ADJ["labels"])
    extra = sorted(k for k in sp if AB["A"].get(k, {}).get("label") != AB["B"].get(k, {}).get("label") and k not in done)
    sysmsg = system_prompt()

    async def go():
        llm = LLM(concurrency=8)
        r = await label_keys(llm, MODEL_ADJ, extra, items, "adj_extra", sysmsg)
        logger.info(f"extra adjudicated {len(r)}/{len(extra)}; spent ${llm.spent:.4f}")
        return r

    res = asyncio.run(go())
    ADJ["labels"].update(res)
    ADJ["disagreements"] = ADJ["disagreements"] + [k for k in extra if k in res]
    ADJ["note"] = "first 300 disagreements adjudicated in stage 'adjudicate', the remainder in 'adjudicate_extra'"
    (LAB / "labels_adj.json").write_text(json.dumps(ADJ, ensure_ascii=False))


if __name__ == "__main__" and sys.argv[1] == "adjudicate_extra":
    cmd_adjudicate_extra()
