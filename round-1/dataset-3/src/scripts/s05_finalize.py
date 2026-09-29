#!/usr/bin/env python3
"""Steps 7d/7e/8/10: local verification, final rule, concept table, works parts, pair set, flow, coverage QA.

usage: s05_finalize.py route_check   -> temp/pubmed_route_fail.json (concepts irrecoverably failing on PubMed-route
                                        verified counts alone: F < 2005 or total > 8,000), used to skip paid remainder
       s05_finalize.py final         -> data_out.json, works/works_part_XX.jsonl, mesh_synonym_pairs.json,
                                        selection_flow.json, coverage_qa.json, full/mini/preview files
"""
from __future__ import annotations

import json
import resource
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

from loguru import logger

sys.path.insert(0, str(Path(__file__).resolve().parent))
import oa  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
TEMP = ROOT / "temp"
CACHE = TEMP / "oa_cache"
WORKS_DIR = ROOT / "works"
logger.remove()
logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
logger.add(ROOT / "logs" / "s05_finalize.log", rotation="30 MB", level="DEBUG")
resource.setrlimit(resource.RLIMIT_AS, (22 * 1024**3, 22 * 1024**3))

YEARS = list(range(2000, 2025))
TARGET_N = 200
PART_BYTES = 90 * 1024**2
FOLD = "heldout_mesh"
UNION_ROUTES = ("pubmed_tiab", "openalex_nonpubmed_search", "both")
CONCEPT_MIN_SCORE = float(sys.argv[2]) if len(sys.argv) > 2 else 0.0   # legacy concepts trim if size forces


def load_pm_cache() -> dict[int, dict]:
    out = {}
    for src, p in (("singleton", CACHE / "pmid_works.jsonl"), ("batched", CACHE / "pmid_works_list.jsonl")):
        if p.exists():
            with p.open() as fh:
                for line in fh:
                    try:
                        d = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if d["pmid"] not in out or (d["status"] == 200 and out[d["pmid"]]["status"] != 200):
                        d["src"] = src
                        out[d["pmid"]] = d
    return out


def load_remainder() -> tuple[dict[str, list[dict]], dict]:
    by_ui: dict[str, list[dict]] = defaultdict(list)
    state = json.loads((CACHE / "remainder_state.json").read_text()) if (CACHE / "remainder_state.json").exists() else {"done": [], "skipped_budget": [], "batches": []}
    p = CACHE / "remainder_pages.jsonl"
    if p.exists():
        with p.open() as fh:
            for line in fh:
                d = json.loads(line)
                for u in d["uis"]:
                    by_ui[u].append(d)
    return by_ui, state


def loose_regex(forms: list[str]):
    import re
    out = []
    for f in forms:
        toks = oa.norm_text(f).split()
        if toks:
            out.append(re.compile(r"(?<![a-z0-9])" + r"[a-z]*\s".join(re.escape(t) for t in toks) + r"[a-z]*"))
    return out


def first_use(yc: dict[int, int]) -> int | None:
    for y in YEARS:
        if yc.get(y, 0) >= 5:
            return y
    return None


def spike_forms(rows: list[dict], forms: list[str], F: int | None) -> list[str]:
    """Transient single-year spikes (ambiguous sense) before F+2: count_y > 5x median of +-2 neighbours,
    >= 10 papers, and the next year falls below a third of the spike."""
    if F is None:
        return []
    flagged = []
    for f in forms:
        yc = Counter(r["publication_year"] for r in rows if f in r["matched_forms"])
        for y in range(2000, F + 3):
            neigh = [yc.get(z, 0) for z in (y - 2, y - 1, y + 1, y + 2)]
            med = statistics.median(neigh)
            if yc.get(y, 0) >= 10 and yc.get(y, 0) > 5 * max(med, 1) and yc.get(y + 1, 0) < yc.get(y, 0) / 3:
                flagged.append(f)
                break
    return flagged


def build_concept(r: dict, tiab: list[int], idx: dict, pm: dict, rem_pages: list[dict], rem_done: bool,
                  drop_forms: set[str] | None = None) -> dict:
    forms = [f for f in r["surface_forms"] if not drop_forms or f not in drop_forms]
    regs = oa.form_regex(forms)
    lregs = loose_regex(forms)
    ui = r["descriptor_ui"]
    idx_set = set(idx.get("pmids", []))
    rows: dict[int, dict] = {}
    n404, n_pre2000, n_err = 0, 0, 0
    src_count: Counter = Counter()

    def add(w: dict, t: str, a: str, route: str, strict_only: bool) -> None:
        ok, field, mf = oa.match_work(t, a, regs)
        if not ok and strict_only is False:
            if not any(l.search(t) or l.search(a) for l in lregs):
                return
        wid = w["work_id"]
        if wid in rows:
            if rows[wid]["match_route"] != route and route != "mesh_indexed_only":
                rows[wid]["match_route"] = "both"
            return
        rows[wid] = {
            "concept_id": r["concept_id"], "metadata_fold": FOLD, "match_route": route,
            "verified_text_match": ok, "match_field": field, "matched_forms": mf,
            "descriptor_indexed_openalex": any(m["descriptor_ui"] == ui for m in w["mesh"]),
            "descriptor_indexed_pubmed": (w["pmid"] in idx_set) if w["pmid"] else False,
            "indexing_regime": "automated" if (w["publication_year"] or 0) >= 2022 else "manual_or_assisted",
            **w,
        }

    for p in tiab:
        d = pm.get(p)
        if d is None:
            n_err += 1
            continue
        if d["status"] == 404:
            n404 += 1
            continue
        if d["status"] != 200:
            n_err += 1
            continue
        y = d["w"]["publication_year"]
        if y is None or y < 2000 or y > 2024:
            n_pre2000 += 1
            continue
        add(d["w"], d["t"], d["a"], "pubmed_tiab", strict_only=True)
        src_count[d.get("src", "singleton")] += 1
    n_rem_seen = 0
    for d in rem_pages:
        y = d["w"]["publication_year"]
        if y is None or y < 2000 or y > 2024:
            continue
        before = len(rows)
        add(d["w"], d["t"], d["a"], "openalex_nonpubmed_search", strict_only=False)
        n_rem_seen += len(rows) - before
    mesh_only_pmids = [p for p in idx_set if p not in set(tiab)]
    for p in mesh_only_pmids:
        d = pm.get(p)
        if d and d["status"] == 200 and 2000 <= (d["w"]["publication_year"] or 0) <= 2024 and d["w"]["work_id"] not in rows:
            add(d["w"], d["t"], d["a"], "mesh_indexed_only", strict_only=True)  # kept even if not text-matched
    union = [x for x in rows.values() if x["match_route"] in UNION_ROUTES and x["verified_text_match"]]
    # alternative (NOT used for selection): also count PubMed [tiab] hits whose OpenAlex record has no abstract,
    # i.e. PubMed matched the phrase in an abstract OpenAlex does not expose (unverifiable locally)
    alt = union + [x for x in rows.values() if x["match_route"] in ("pubmed_tiab", "both")
                   and not x["verified_text_match"] and not x["has_abstract"]]
    yalt = Counter(x["publication_year"] for x in alt)
    yc = Counter(x["publication_year"] for x in union)
    yearly = {y: yc.get(y, 0) for y in YEARS}
    F = first_use(yearly)
    early = sum(yearly[y] for y in range(F, min(F + 3, 2025))) if F else 0
    total = sum(yearly.values())
    return {"rows": list(rows.values()), "yearly": yearly, "F": F, "early": early, "total": total, "forms": forms,
            "src_count": dict(src_count), "yearly_alt": {y: yalt.get(y, 0) for y in YEARS},
            "n404": n404, "n_pre2000": n_pre2000, "n_err": n_err, "mesh_only_pmids": mesh_only_pmids,
            "n_pubmed_route": sum(1 for x in union if x["match_route"] in ("pubmed_tiab", "both")),
            "n_nonpubmed_route": sum(1 for x in union if x["match_route"] in ("openalex_nonpubmed_search", "both"))}


def slim(x: dict) -> dict:
    """Size control: OpenAlex repeats a MeSH descriptor once per qualifier -> one entry per descriptor
    (is_major_topic = any); legacy concepts kept only with score >= CONCEPT_MIN_SCORE; scores rounded to 2 dp."""
    x = dict(x)
    mesh: dict[str, bool] = {}
    for m in x["mesh"]:
        mesh[m["descriptor_ui"]] = mesh.get(m["descriptor_ui"], False) or bool(m["is_major_topic"])
    x["mesh"] = [{"descriptor_ui": k, "is_major_topic": v} for k, v in mesh.items()]
    if CONCEPT_MIN_SCORE > 0:
        x["concepts"] = [k for k in x["concepts"] if k["score"] >= CONCEPT_MIN_SCORE]
    x["concepts"] = [{**k, "score": round(k["score"], 2)} for k in x["concepts"]]
    x["keywords"] = [{**k, "score": round(k["score"], 2)} for k in x["keywords"]]
    return x


def final_rule(c: dict) -> str:
    if c["F"] is None or not (2005 <= c["F"] <= 2016):
        return "fail_F_window"
    if not (20 <= c["early"] <= 300):
        return "fail_early_volume"
    if c["total"] > 8000:
        return "fail_total_cap"
    return "pass"


def mode_of(vals: list) -> int | None:
    vals = [v for v in vals if v is not None]
    return Counter(vals).most_common(1)[0][0] if vals else None


def route_check() -> None:
    wl = json.loads((TEMP / "working_list.json").read_text())
    tiab = json.loads((TEMP / "pubmed_tiab_pmids.json").read_text())
    idx = json.loads((TEMP / "mesh_indexed.json").read_text())
    pm = load_pm_cache()
    fails = []
    for r in wl:
        c = build_concept(r, tiab[r["descriptor_ui"]], idx[r["descriptor_ui"]], pm, [], False)
        if (c["F"] is not None and c["F"] < 2005) or c["total"] > 8000:
            fails.append(r["descriptor_ui"])
    logger.info(f"route_check: {len(fails)}/{len(wl)} irrecoverable on PubMed route")
    (TEMP / "pubmed_route_fail.json").write_text(json.dumps(fails))


def write_parts(rows_iter, prefix: str) -> list[str]:
    """gzip-compressed JSONL parts (one JSON object per line); each part holds <= PART_BYTES of UNcompressed JSON,
    so every part stays far below the 95 MB file limit and the deliverable below 300 MB."""
    import gzip
    WORKS_DIR.mkdir(exist_ok=True)
    for old in list(WORKS_DIR.glob(f"{prefix}_*.jsonl")) + list(WORKS_DIR.glob(f"{prefix}_*.jsonl.gz")):
        old.unlink()
    parts, k, size, fh = [], 0, 0, None
    for row in rows_iter:
        line = json.dumps(row, separators=(",", ":")) + "\n"
        if fh is None or size + len(line) > PART_BYTES:
            if fh:
                fh.close()
            k += 1
            path = WORKS_DIR / f"{prefix}_{k:02d}.jsonl.gz"
            parts.append(str(path.relative_to(ROOT)))
            fh = gzip.open(path, "wt", compresslevel=6)
            size = 0
        fh.write(line)
        size += len(line)
    if fh:
        fh.close()
    return parts


def truncate(o, n=200):
    if isinstance(o, str):
        return o[:n]
    if isinstance(o, list):
        return [truncate(x, n) for x in o]
    if isinstance(o, dict):
        return {k: truncate(v, n) for k, v in o.items()}
    return o


def write_variants(obj: dict, stem: str) -> None:
    """exp_sel_data_out full/mini/preview (mini = first 3 examples per dataset, preview = 10 examples, strings <= 200 chars)."""
    (ROOT / f"full_{stem}.json").write_text(json.dumps(obj, indent=1))
    mini = {**obj, "datasets": [{**d, "examples": d["examples"][:3]} for d in obj["datasets"]]}
    (ROOT / f"mini_{stem}.json").write_text(json.dumps(mini, indent=1))
    prev = {**obj, "datasets": [{**d, "examples": truncate(d["examples"][:10])} for d in obj["datasets"]]}
    (ROOT / f"preview_{stem}.json").write_text(json.dumps(prev, indent=1))


def final() -> None:
    wl = sorted(json.loads((TEMP / "working_list.json").read_text()), key=lambda r: r["sample_rank"])
    tiab = json.loads((TEMP / "pubmed_tiab_pmids.json").read_text())
    idx = json.loads((TEMP / "mesh_indexed.json").read_text())
    pm = load_pm_cache()
    rem, rstate = load_remainder()
    rem_done = set(rstate["done"])
    nc = json.loads((TEMP / "nonpubmed_counts.json").read_text()) if (TEMP / "nonpubmed_counts.json").exists() else {}
    fetched_tiab = {r["descriptor_ui"] for r in wl if all(p in pm for p in tiab[r["descriptor_ui"]])}
    logger.info(f"working list {len(wl)}; tiab fully fetched for {len(fetched_tiab)}; remainder done for {len(rem_done)}")
    accepted, outcomes, concept_rows, all_work_rows = [], [], [], []
    for r in wl:
        ui = r["descriptor_ui"]
        if nc.get(ui, {}).get("total", 0) > 8000:
            outcomes.append({"descriptor_ui": ui, "sample_rank": r["sample_rank"], "outcome": "fail_total_cap_nonpubmed_groupby",
                             "nonpubmed_total": nc[ui]["total"]})
            continue
        if ui not in fetched_tiab:
            outcomes.append({"descriptor_ui": ui, "sample_rank": r["sample_rank"], "outcome": "not_retrieved_time"})
            continue
        c = build_concept(r, tiab[ui], idx[ui], pm, rem.get(ui, []), ui in rem_done)
        spikes = spike_forms([x for x in c["rows"] if x["verified_text_match"] and x["match_route"] in UNION_ROUTES],
                             c["forms"], c["F"])
        dropped_spikes = []
        if spikes and len(spikes) < len(c["forms"]):
            dropped_spikes = spikes
            c = build_concept(r, tiab[ui], idx[ui], pm, rem.get(ui, []), ui in rem_done, drop_forms=set(spikes))
        npc = nc.get(ui)
        np_yearly = {y: int((npc or {}).get("yearly", {}).get(str(y), 0)) for y in YEARS}
        if ui in rem_done:
            basis = "verified_union"
            rule_yearly = dict(c["yearly"])
        elif npc is not None:
            basis = "pubmed_route_verified+nonpubmed_groupby_unverified"
            rule_yearly = {y: c["yearly"][y] + np_yearly[y] for y in YEARS}
        else:
            basis = "pubmed_route_verified_only"
            rule_yearly = dict(c["yearly"])
        rF = first_use(rule_yearly)
        c_rule = {"F": rF, "early": sum(rule_yearly[y] for y in range(rF, min(rF + 3, 2025))) if rF else 0,
                  "total": sum(rule_yearly.values())}
        outcome = final_rule(c_rule)
        c["F"], c["early"] = c_rule["F"], c_rule["early"]
        if outcome == "pass" and len(accepted) >= TARGET_N:
            outcome = "pass_surplus_not_needed"
        outcomes.append({"descriptor_ui": ui, "sample_rank": r["sample_rank"], "outcome": outcome, "F": c_rule["F"],
                         "early": c_rule["early"], "total": c_rule["total"], "final_rule_basis": basis,
                         "total_verified_retrieved": c["total"], "retrieval_complete": ui in rem_done,
                         "spike_forms_flagged": spikes})
        if outcome != "pass":
            continue
        accepted.append(ui)
        union = [x for x in c["rows"] if x["match_route"] in UNION_ROUTES and x["verified_text_match"]]
        early_w = [x for x in union if c["F"] <= x["publication_year"] <= c["F"] + 2]
        n_single, n_batch = c["src_count"].get("singleton", 0), c["src_count"].get("batched", 0)
        broute = "pubmed+singleton" if n_batch == 0 else ("pubmed+batched" if n_single == 0 else "pubmed+singleton+batched")
        est_y = r["mesh_year_established"]
        iyear = idx[ui].get("yearly", {})
        excluded = list(r["excluded_forms"]) + [{"form": f, "reason": "transient_spike_ambiguous_sense"} for f in dropped_spikes]
        concept_rows.append({
            "input": {
                "concept_id": r["concept_id"], "descriptor_ui": ui, "preferred_term": r["preferred_term"],
                "surface_forms": c["forms"], "excluded_forms": excluded, "acronyms": r["acronyms"],
                "narrower_concept_terms": r["narrower_concept_terms"], "tree_numbers": r["tree_numbers"],
                "tree_branch_primary": r["tree_branch_primary"], "date_established": r["date_established"],
                "mesh_year_established": est_y, "history_note": r["history_note"],
                "public_mesh_note": r["public_mesh_note"], "previous_indexing": r["previous_indexing"],
                "provenance_class": r["provenance_class"], "chemical_flag": r["chemical_flag"],
                "F": c["F"], "early_count_F_to_F2": c["early"],
                "origin_field": mode_of([(x["primary_topic"] or {}).get("field_id") for x in early_w]),
                "origin_subfield": mode_of([(x["primary_topic"] or {}).get("subfield_id") for x in early_w]),
                "pubmed_query": r["pubmed_query"],
            },
            "output": {
                "yearly_counts_textmatch": {str(y): c["yearly"][y] for y in YEARS},
                "yearly_counts_mesh_indexed": {str(y): (int(iyear.get(str(y), 0)) if y >= est_y else 0) for y in YEARS},
                "yearly_counts_textmatch_plus_pubmed_unverifiable": {str(y): c["yearly_alt"][y] for y in YEARS},
                "yearly_counts_nonpubmed_openalex_groupby": {str(y): np_yearly[y] for y in YEARS} if npc is not None else None,
                "yearly_counts_final_rule": {str(y): rule_yearly[y] for y in YEARS},
                "final_rule_basis": basis,
                "total_2000_2024": c["total"],
                "total_final_rule_2000_2024": c_rule["total"],
                "n_works_retrieved": len(c["rows"]),
                "n_verified_union": len(union),
                "n_pubmed_route": c["n_pubmed_route"],
                "n_nonpubmed_route": c["n_nonpubmed_route"],
                "n_pmid_not_in_openalex": c["n404"],
                "n_pubmed_pre2000_or_undated": c["n_pre2000"],
                "n_mesh_indexed_pubmed_total": idx[ui]["count"],
                "mesh_indexed_only_pmids": sorted(c["mesh_only_pmids"]),
            },
            "metadata_fold": FOLD,
            "metadata": {
                "stratum": r["stratum"], "branch_group": r["branch_group"], "volume_tercile": r["volume_tercile"],
                "establishment_period": r["period"], "selection_prob": r["selection_prob"],
                "sample_rank": r["sample_rank"], "selection_seed": r["selection_seed"],
                "widening_tag": r.get("widening_tag"),
                "still_in_mesh_2026": r["still_in_mesh_2026"], "retrieval_complete": ui in rem_done,
                "retrieval_gap": None if ui in rem_done else "nonpubmed_missing",
                "rule_parity": basis != "pubmed_route_verified_only",   # final rule saw non-PubMed works (paged or counted)
                "budget_route": broute, "n_pubmed_route_via_singleton": n_single, "n_pubmed_route_via_batched": n_batch,
                "calibration_member": False,
                "pubmed_prescreen": {"F_pubmed": r["F_pubmed"], "early_pubmed_F_F2": r["early_pubmed_F_F2"],
                                     "total_pubmed_1995_2024": r["total_pubmed_1995_2024"]},
                "spike_forms_dropped": dropped_spikes,
            },
        })
        for x in sorted(c["rows"], key=lambda x: x["work_id"]):
            all_work_rows.append(slim(x))
    oc = Counter(o["outcome"] for o in outcomes)
    logger.info(f"Final outcomes: {dict(oc)}; accepted {len(accepted)}")

    # calibration membership (written by s06 if it ran)
    calib = TEMP / "calibration_members.json"
    if calib.exists():
        cm = set(json.loads(calib.read_text()))
        for cr in concept_rows:
            cr["metadata"]["calibration_member"] = cr["input"]["descriptor_ui"] in cm

    (ROOT / "data_out.json").write_text(json.dumps(concept_rows, indent=1))
    parts = write_parts(iter(all_work_rows), "works_part")
    logger.info(f"works rows {len(all_work_rows)} in {len(parts)} parts: {parts}")
    # mini_works.json / preview_works.json (exp_sel_data_out schema) are written by data.py

    # coverage QA over unique works of accepted concepts
    uniq = {x["work_id"]: x for x in all_work_rows if x["match_route"] in UNION_ROUTES and x["verified_text_match"]}
    cov = {}
    for y in YEARS:
        ws = [w for w in uniq.values() if w["publication_year"] == y]
        n = len(ws)
        cov[str(y)] = {"n_works": n,
                       "share_pmid": round(sum(1 for w in ws if w["pmid"]) / n, 4) if n else None,
                       "share_has_abstract": round(sum(1 for w in ws if w["has_abstract"]) / n, 4) if n else None,
                       "share_referenced_works": round(sum(1 for w in ws if w["referenced_works"]) / n, 4) if n else None,
                       "share_author_ids": round(sum(1 for w in ws if any(a["author_id"] for a in w["authorships"])) / n, 4) if n else None,
                       "share_primary_topic": round(sum(1 for w in ws if w["primary_topic"]) / n, 4) if n else None}
    rows_all = [x for x in all_work_rows]
    qa = {"per_year_unique_verified_union_works": cov,
          "n_rows": len(rows_all), "n_unique_works": len({x["work_id"] for x in rows_all}),
          "rows_by_route": dict(Counter(x["match_route"] for x in rows_all)),
          "rows_verified": sum(1 for x in rows_all if x["verified_text_match"]),
          "rows_match_field": dict(Counter(x["match_field"] for x in rows_all)),
          "rows_descriptor_indexed_openalex": sum(1 for x in rows_all if x["descriptor_indexed_openalex"]),
          "rows_descriptor_indexed_pubmed": sum(1 for x in rows_all if x["descriptor_indexed_pubmed"])}
    (ROOT / "coverage_qa.json").write_text(json.dumps(qa, indent=1))

    # ---- synonym pairs with leakage flags
    pr = json.loads((TEMP / "pairs_raw.json").read_text())
    acc = set(accepted)
    wl_set = {r["descriptor_ui"] for r in wl}
    pairs = []
    for p in pr["positive"] + pr["negative"]:
        p = dict(p)
        p["in_heldout_population"] = p["descriptor_ui"] in acc or p["descriptor_ui_b"] in acc
        p["in_working_list"] = p["descriptor_ui"] in wl_set or p["descriptor_ui_b"] in wl_set
        pairs.append(p)
    pc = Counter((p["label"], p["pair_type"]) for p in pairs)
    (ROOT / "mesh_synonym_pairs.json").write_text(json.dumps(
        {"description": "MeSH (desc2017) preferred-concept synonym pairs (label 1) and hard negatives (label 0) for all "
                        "provenance-filtered new descriptors established 2006-2016. Exclude in_heldout_population=true "
                        "(or in_working_list=true, stricter) when training/tuning.",
         "n_positive": sum(1 for p in pairs if p["label"] == 1), "n_negative": sum(1 for p in pairs if p["label"] == 0),
         "counts_by_label_type": {f"{k[0]}|{k[1]}": v for k, v in sorted(pc.items())},
         "pairs": pairs}, indent=0))

    # ---- selection flow
    flow = []
    for f in ("flow_step1_4.json", "flow_step5.json", "flow_step6.json", "flow_step1_4_w1.json", "flow_step5_w1.json",
              "flow_step1_4_w2.json", "flow_step5_w2.json", "flow_step6_ext.json"):
        if (TEMP / f).exists():
            flow.extend(json.loads((TEMP / f).read_text()))
    flow.append({"step": "retrieval (PubMed-route singletons fetched)", "n": len(fetched_tiab)})
    flow.append({"step": "non-PubMed remainder retrieved (retrieval_complete)", "n": len(rem_done & {r['descriptor_ui'] for r in wl}),
                 "skipped_budget": rstate.get("skipped_budget", [])})
    flow.append({"step": "final rule on verified union counts (F 2005-2016, 20<=early<=300, total<=8000), rank order until N=200",
                 "n": len(accepted), "outcomes": dict(oc)})
    (ROOT / "selection_flow.json").write_text(json.dumps({"flow": flow, "per_concept_outcomes": outcomes}, indent=1))

    # schema-format outputs (full/mini/preview_data_out.json) are written by data.py from temp/datasets/
    logger.info(f"Wrote {len(concept_rows)} concepts, {len(pairs)} pairs")


if __name__ == "__main__":
    mode = sys.argv[1]
    logger.catch(reraise=True)(route_check if mode == "route_check" else final)()
